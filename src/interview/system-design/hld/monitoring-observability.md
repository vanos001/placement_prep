# Monitoring and Observability

## What is Observability?

Observability is the ability to understand a system's internal state from its external outputs. It answers: **"What's happening inside the system?"**

The three pillars of observability:

```
┌─────────────────────────────────────────┐
│           Observability                 │
├───────────┬───────────┬─────────────────┤
│  Metrics  │  Logs     │  Traces         │
│ (What)    │ (Why)     │ (Where)         │
│ Numbers   │ Details   │ Request flow    │
│ over time │ of events │ across services │
└───────────┴───────────┴─────────────────┘
```

## Metrics

### What are Metrics?
Numerical measurements collected over time.

```
┌─────────────────────────────────────┐
│         Metrics Over Time           │
│  100│      ┌──┐                     │
│     │   ┌──┘  │  ┌──┐              │
│   50│───┘     └──┘  └───            │
│     │                               │
│     └───────────────────────────→   │
│     12:00  12:05  12:10  12:15      │
└─────────────────────────────────────┘
```

### Types of Metrics

| Type | Description | Example |
|------|-------------|---------|
| **Counter** | Monotonically increasing | Total requests, errors |
| **Gauge** | Current value | CPU usage, memory, queue size |
| **Histogram** | Distribution of values | Request latency percentiles |
| **Summary** | Similar to histogram | Request duration |

### Key Metrics to Monitor (RED Method)

```
R - Rate:      Requests per second
E - Errors:    Error rate (%)
D - Duration:  Request latency (p50, p95, p99)
```

### Key Metrics to Monitor (USE Method)

```
U - Utilization: % of resource used (CPU, memory, disk)
S - Saturation:  Degree of queuing (ready queue, disk queue)
E - Errors:      Error count (disk errors, network errors)
```

### Golden Signals (Google SRE)

| Signal | Description | Example |
|--------|-------------|---------|
| **Latency** | Time to serve request | p99 latency |
| **Traffic** | Demand on system | Requests/sec |
| **Errors** | Rate of failed requests | 5xx errors/sec |
| **Saturation** | How full the system is | CPU 90%, queue depth |

### Metrics Tools

| Tool | Type | Use Case |
|------|------|----------|
| **Prometheus** | Open-source | Pull-based metrics collection |
| **Grafana** | Visualization | Dashboards, alerting |
| **Datadog** | SaaS | Full-stack monitoring |
| **CloudWatch** | AWS | AWS-specific metrics |
| **InfluxDB** | Time-series DB | High-cardinality metrics |

## Logging

### What are Logs?
Discrete events with timestamp and context.

### Structured Logging
```json
// ❌ Unstructured (hard to parse)
"User login failed for user@example.com at 2024-01-15"

// ✅ Structured (machine-parseable)
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "WARN",
  "service": "auth-service",
  "event": "login_failed",
  "user_email": "user@example.com",
  "reason": "invalid_password",
  "request_id": "req_abc123",
  "ip": "192.168.1.100"
}
```

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| **DEBUG** | Development details | Variable values, function entry |
| **INFO** | Normal operations | User logged in, order created |
| **WARN** | Potential issues | High latency, low disk space |
| **ERROR** | Failures that need attention | DB connection failed |
| **FATAL** | System cannot continue | Out of memory, corrupt data |

### Centralized Logging Architecture

```
[App Server 1] ──┐
[App Server 2] ──┼──→ [Log Aggregator] ──→ [Storage] ──→ [Query UI]
[App Server 3] ──┘     (Fluentd/Filebeat)   (Elasticsearch)  (Kibana)
```

### Logging Tools

| Tool | Type | Use Case |
|------|------|----------|
| **ELK Stack** | Open-source | Elasticsearch + Logstash + Kibana |
| **Fluentd** | Log collector | Kubernetes-native logging |
| **Splunk** | Enterprise | Large-scale log analysis |
| **Loki** | Grafana | Lightweight log aggregation |
| **CloudWatch Logs** | AWS | AWS-native logging |

### Logging Best Practices
```
✅ Use structured logging (JSON)
✅ Include correlation IDs (request_id)
✅ Log at appropriate levels
✅ Don't log sensitive data (passwords, tokens)
✅ Include context (user_id, service_name)
✅ Use correlation IDs for distributed tracing
✅ Set retention policies
✅ Sample high-volume logs
```

## Distributed Tracing

### What is Tracing?
Following a request across multiple services.

```
User Request → API Gateway → User Service → DB
                    ↓
              Order Service → Payment Service → External API
                    ↓
              Notification Service → Email Provider

Trace ID: abc123
├── Span 1: API Gateway (5ms)
├── Span 2: User Service (15ms)
│   └── Span 3: DB Query (10ms)
├── Span 4: Order Service (25ms)
│   ├── Span 5: Payment Service (20ms)
│   │   └── Span 6: External API (15ms)
│   └── Span 7: Notification Service (30ms)
│       └── Span 8: Email Provider (25ms)
└── Total: 85ms
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Trace** | Complete journey of a request |
| **Span** | Single unit of work within a trace |
| **Context** | Propagated metadata (trace_id, span_id) |
| **Sampling** | Which traces to collect (cost vs visibility) |

### Tracing Tools

| Tool | Type | Use Case |
|------|------|----------|
| **Jaeger** | Open-source | Distributed tracing |
| **Zipkin** | Open-source | Twitter's tracing system |
| **AWS X-Ray** | Managed | AWS-native tracing |
| **Datadog APM** | SaaS | Full observability |
| **OpenTelemetry** | Standard | Vendor-neutral instrumentation |

## Alerting

### Alert Design Principles

```
Good Alert:
- Actionable: Someone needs to do something
- Contextual: Includes what's wrong and what to check
- Urgency-matched: PagerDuty for critical, Slack for warning
- Has runbook: Link to resolution steps

Bad Alert:
- "CPU is high" → So what? Is it a problem?
- "Something is wrong" → What specifically?
- Alert fatigue: Too many non-actionable alerts
```

### Alert Severity Levels

| Severity | Response Time | Channel | Example |
|----------|--------------|---------|---------|
| **Critical** | Immediate | PagerDuty, phone | Service down, data loss |
| **Warning** | Within hours | Slack, email | High error rate, disk filling |
| **Info** | Next business day | Dashboard | Slow queries, minor degradation |

### Alerting Best Practices
```
✅ Alert on symptoms, not causes
  - ✅ "Error rate > 5%"
  - ❌ "CPU > 80%"

✅ Include context and runbooks
  - "Error rate 5.2%, see runbook: wiki/alerts/high-error-rate"

✅ Use appropriate thresholds
  - Based on historical data, not arbitrary numbers

✅ Implement alert fatigue prevention
  - Group related alerts
  - Suppress during maintenance
  - Escalation policies
```

## Observability Stack

### Modern Observability Architecture

```
┌─────────────────────────────────────────────────┐
│                  Applications                    │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐       │
│  │ App1 │  │ App2 │  │ App3 │  │ App4 │       │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘       │
└─────┼────────┼────────┼────────┼───────────────┘
      │        │        │        │
      ▼        ▼        ▼        ▼
┌─────────────────────────────────────────────────┐
│            Collection Layer                      │
│  Prometheus │ Fluentd/Filebeat │ OpenTelemetry  │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              Storage Layer                       │
│  InfluxDB │ Elasticsearch │ Jaeger/Tempo        │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│            Visualization Layer                   │
│              Grafana / Kibana                    │
│  [Dashboards] [Alerts] [Explore]                │
└─────────────────────────────────────────────────┘
```

### Popular Observability Stacks

| Stack | Components | Best For |
|-------|-----------|----------|
| **Prometheus + Grafana** | Metrics + Dashboards | Kubernetes, cloud-native |
| **ELK** | Logs + Search + Visualization | Log-heavy applications |
| **Datadog** | All-in-one SaaS | Enterprise, multi-cloud |
| **New Relic** | APM + Infrastructure | Full-stack monitoring |
| **AWS Native** | CloudWatch + X-Ray | AWS-only workloads |

## SLI/SLO Monitoring

### Defining SLIs

```yaml
# Example SLI definitions
availability:
  sli: "successful_requests / total_requests"
  slo: "99.9%"
  
latency:
  sli: "requests completing under 200ms / total_requests"
  slo: "99% under 200ms"
  
error_rate:
  sli: "non_5xx_responses / total_responses"
  slo: "99.95% non-5xx"
```

### Error Budget

```
SLO: 99.9% availability
Error Budget: 0.1% = 43.8 minutes/month

If error budget exhausted:
→ Freeze deployments
→ Focus on reliability
→ No new features until budget recovers
```

## Interview Tips

1. **Always mention monitoring** — "We need to monitor this system"
2. **Discuss all three pillars** — Metrics, logs, and traces
3. **Mention specific tools** — "Prometheus for metrics, ELK for logs, Jaeger for traces"
4. **Define SLIs/SLOs** — "99.9% availability, p99 latency under 200ms"
5. **Include alerting** — "Alert on symptoms, not causes"
6. **Consider cost** — "Sample high-volume traces to reduce cost"
7. **Think about dashboards** — "Golden signals dashboard for each service"
8. **Discuss runbooks** — "Each alert links to a runbook"

## Common Mistakes

- ❌ Alerting on everything (alert fatigue)
- ❌ Not using structured logging
- ❌ Missing correlation IDs across services
- ❌ No sampling strategy (cost explosion)
- ❌ Monitoring infrastructure but not user experience
- ❌ No defined SLOs

## Cross-References

- [Availability](./availability.md) — SLO/SLA definitions
- [Security Design](./security-design.md) — Security logging and audit trails
- [Load Balancing](./load-balancing-design.md) — Health checks
- [API Design](./api-design.md) — API metrics and rate limiting
- [Capacity Planning](./capacity-planning.md) — Metrics for capacity decisions
- [Cloud Observability](../../cloud/observability/README.md)
- [MLOps Monitoring](../../ml/mlops/monitoring.md)
- [Metrics](../metrics.md)

