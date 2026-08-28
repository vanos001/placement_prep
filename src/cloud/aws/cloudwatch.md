# AWS CloudWatch

Amazon CloudWatch is AWS's observability platform, launched in 2009. It provides metrics collection, log aggregation, dashboards, alerting, and event-driven automation. CloudWatch is the standard observability layer for AWS-native applications, with deep integrations with all AWS services. This page covers the architecture, the metrics model, the logs service, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  CloudWatch (managed, multi-tenant)                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Metrics service                                         │ │
│  │  - Stores time-series data (per AWS service, custom)     │ │
│  │  - 1-minute resolution (default), 1-second (high-res)    │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Logs service                                           │ │
│  │  - Aggregates logs from CloudWatch agent, Lambda, etc.  │ │
│  │  - Search via CloudWatch Logs Insights                  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Alarms                                                  │ │
│  │  - Threshold-based alerts → SNS, EC2 actions             │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Events (EventBridge)                                   │ │
│  │  - AWS service events, schedule triggers, custom events  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ put metric/log              │ alarm state changes
        ▼                              ▼
    Applications                  SNS topic → alerts
```

CloudWatch is integrated with all AWS services: EC2, Lambda, RDS, S3, etc. automatically publish metrics to CloudWatch. Custom applications can also publish via the API or the CloudWatch agent.

## Metrics

CloudWatch metrics are time-series data points with a namespace, name, dimensions, and timestamp:

```python
import boto3
cw = boto3.client('cloudwatch')

# Publish a custom metric
cw.put_metric_data(
    Namespace='MyApp',
    MetricData=[
        {
            'MetricName': 'OrdersProcessed',
            'Dimensions': [{'Name': 'Service', 'Value': 'order-api'}],
            'Value': 42,
            'Unit': 'Count',
            'Timestamp': datetime.now(),
        }
    ]
)

# Query a metric
response = cw.get_metric_statistics(
    Namespace='MyApp',
    MetricName='OrdersProcessed',
    Dimensions=[{'Name': 'Service', 'Value': 'order-api'}],
    StartTime=datetime.now() - timedelta(hours=1),
    EndTime=datetime.now(),
    Period=60,  # 1-minute buckets
    Statistics=['Sum', 'Average', 'Maximum'],
)
```

Each AWS service publishes its own metrics namespace:
- `AWS/EC2`: CPU utilization, network I/O, disk I/O.
- `AWS/Lambda`: invocations, errors, duration, throttles.
- `AWS/RDS`: CPU, memory, connections, queries/sec.
- `AWS/S3`: bucket size, request count.

Resolution:
- **Standard (1-minute)**: free for most AWS service metrics.
- **High-resolution (1-second)**: paid, useful for fast-changing metrics (e.g., queue length, active connections).

## Logs

CloudWatch Logs aggregates log data:

```python
import boto3
logs = boto3.client('logs')

# Create a log group
logs.create_log_group(logGroupName='/aws/lambda/my-function')

# Create a log stream
logs.create_log_stream(logGroupName='/aws/lambda/my-function',
                      logStreamName='2024-01-15')

# Put log events
logs.put_log_events(
    logGroupName='/aws/lambda/my-function',
    logStreamName='2024-01-15',
    logEvents=[
        {'timestamp': int(time.time() * 1000), 'message': 'Order 123 processed'},
        {'timestamp': int(time.time() * 1000), 'message': 'Order 124 processed'},
    ]
)
```

For non-Lambda sources, install the CloudWatch agent on EC2/ECS, or use FireLens (Fluent Bit) to ship container logs.

### Logs Insights

CloudWatch Logs Insights is a SQL-like query language for logs:

```text
fields @timestamp, @message
| filter @message like /ERROR/
| parse @message "* - *: *" as timestamp, level, message
| filter level = "ERROR"
| stats count() by message
| sort @timestamp desc
| limit 20
```

Insights queries are fast (the logs are pre-indexed). For complex queries, export to S3 and use Athena.

## Alarms

CloudWatch Alarms trigger actions based on metric thresholds:

```python
cw.put_metric_alarm(
    AlarmName='HighErrorRate',
    AlarmDescription='Error rate > 5% for 5 minutes',
    Namespace='MyApp',
    MetricName='ErrorRate',
    Dimensions=[{'Name': 'Service', 'Value': 'order-api'}],
    Statistic='Average',
    Period=60,  # 1-minute buckets
    EvaluationPeriods=5,  # 5 consecutive periods
    Threshold=5.0,
    ComparisonOperator='GreaterThanThreshold',
    TreatMissingData='notBreaching',
    AlarmActions=['arn:aws:sns:us-east-1:123:my-alerts'],
)
```

The alarm transitions through states:
- `OK`: metric is below threshold.
- `ALARM`: metric is above threshold for `EvaluationPeriods` consecutive periods.
- `INSUFFICIENT_DATA`: not enough data to evaluate.

On state change, CloudWatch invokes the AlarmActions (SNS topics, EC2 auto-scaling actions, Lambda).

## Dashboards

CloudWatch Dashboards are customizable visualizations of metrics:

```text
Dashboard: order-service
  Widget 1: Error rate (line chart, last 1 hour)
  Widget 2: Latency P50/P95/P99 (line chart, last 1 hour)
  Widget 3: Throughput (number, last 5 minutes)
  Widget 4: Active instances (number)
```

Dashboards can be shared with users without AWS console access (via a public URL, with a temporary token).

## Production Use Cases

### Application Metrics

```python
# Per-request metrics
import time
from cloudwatch import metrics

def handler(event, context):
    start = time.time()
    try:
        result = process(event)
        metrics.publish('RequestCount', 1, dimensions=[('Endpoint', '/orders')])
        metrics.publish('Latency', (time.time() - start) * 1000, unit='Milliseconds')
        return result
    except Exception as e:
        metrics.publish('ErrorCount', 1, dimensions=[('Endpoint', '/orders'), ('Error', type(e).__name__)])
        raise
```

The application publishes custom metrics; CloudWatch aggregates for dashboards and alarms.

### Auto-Scaling

EC2 Auto-Scaling Groups and ECS Service Auto-Scaling use CloudWatch alarms to scale:

```text
Alarm: CPU > 70% for 5 minutes → scale up
Alarm: CPU < 30% for 10 minutes → scale down
```

The auto-scaler reads the alarm state and adjusts the instance count.

### Alerting

CloudWatch Alarms → SNS → Lambda (PagerDuty, Slack, email):

```text
CloudWatch Alarm (state change) → SNS topic → Lambda → PagerDuty
```

The Lambda transforms the SNS message into a PagerDuty API call (with custom routing by severity).

## Production Performance

CloudWatch performance:
- Metric ingestion latency: ~1-5 seconds (eventual consistency).
- Logs ingestion latency: ~5-30 seconds (batched).
- Alarm evaluation: every minute (standard) or every 10 seconds (high-resolution).
- Logs query latency: ~1-5 seconds (last 5 minutes), longer for larger time ranges.

For real-time alerting, CloudWatch may be too slow; consider Prometheus + Grafana for sub-second alerting.

## Common Pitfalls

1. **Forgetting that custom metrics cost money.** Each custom metric is ~$0.30/month (region-dependent); each data point is ~$0.001. For 1000 metrics × 1000 data points per day, costs add up.

2. **Forgetting that CloudWatch Logs charges by ingestion.** $0.50 per GB ingested; $0.03 per GB/month stored. For high-volume logs, this is significant. Filter aggressively before ingesting.

3. **Forgetting that 1-minute resolution may miss fast spikes.** A spike that lasts 30 seconds may not be captured. Use high-resolution (1-second) for critical metrics.

4. **Forgetting that alarm evaluation has delays.** An alarm fires 1-2 minutes after the threshold breach (the metric must propagate, then the alarm evaluates). For faster alerting, use CloudWatch Composite Alarms or external systems.

5. **Forgetting that CloudWatch Logs Insights is slow for long time ranges.** A query over 30 days scans a lot of data. For long-range analysis, export to S3 + Athena.

6. **Forgetting that the CloudWatch agent needs IAM permissions.** The agent must have `cloudwatch:PutMetricData` and `logs:PutLogEvents`. Misconfigured IAM = no metrics/logs.

## Comparison to Other Observability Systems

| Aspect | CloudWatch | Prometheus+Grafana | Datadog | New Relic |
|--------|-----------|---------------------|---------|-----------|
| AWS integration | First-class | Limited | First-class | First-class |
| Cost model | Per-metric + per-GB logs | Free (self-hosted) | Per-host | Per-host |
| Multi-cloud | Limited | Excellent | Yes | Yes |
| Custom metrics cost | `$$$` | Free | `$` | `$$` |
| Best for | AWS-native | Multi-cloud, self-hosted | Enterprise | APM |

CloudWatch is the choice for AWS-only deployments; Prometheus for multi-cloud self-hosted; Datadog for enterprise with budget.

## References

- [AWS CloudWatch documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)
- [CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Agent (for EC2/ECS)](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/InstallCloudWatchAgent.html)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [CloudWatch vs Prometheus (AWS blog)](https://aws.amazon.com/blogs/mt/monitoring-cloudwatch-vs-prometheus/)
- [LWN: CloudWatch overview (2021)](https://lwn.net/Articles/820133/)
