# Prometheus and Grafana

## Introduction

Prometheus and Grafana are the de facto standard for metrics-based monitoring in the Linux ecosystem. Prometheus scrapes metrics from targets, stores them in a time-series database, and provides a powerful query language (PromQL). Grafana connects to Prometheus and other data sources to create rich, interactive dashboards and alerting rules.

Together, they form the observability backbone for everything from single servers to massive Kubernetes clusters.

## Architecture

```mermaid
graph TD
    subgraph "Targets"
        NE["node_exporter<br>:9100"]
        APP["Application<br>:8080/metrics"]
        MY["mysqld_exporter<br>:9104"]
        NG["nginx_exporter<br>:9113"]
    end
    subgraph "Prometheus"
        PROM["Prometheus Server<br>:9090"]
        TSDB["TSDB Storage"]
        RULE["Alert Rules"]
        AM["Alertmanager<br>:9093"]
    end
    subgraph "Visualization"
        GRAF["Grafana<br>:3000"]
    end
    subgraph "Notification"
        SLACK["Slack"]
        PAGER["PagerDuty"]
        EMAIL["Email"]
    end

    NE -->|scrape| PROM
    APP -->|scrape| PROM
    MY -->|scrape| PROM
    NG -->|scrape| PROM
    PROM --> TSDB
    PROM --> RULE
    RULE --> AM
    PROM --> GRAF
    AM --> SLACK
    AM --> PAGER
    AM --> EMAIL
```

## Prometheus Configuration

### Installation

```bash
# Download Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.50.0/prometheus-2.50.0.linux-amd64.tar.gz
tar xvf prometheus-2.50.0.linux-amd64.tar.gz
cp prometheus-2.50.0.linux-amd64/{prometheus,promtool} /usr/local/bin/

# Create user and directories
useradd --no-create-home --shell /bin/false prometheus
mkdir -p /etc/prometheus /var/lib/prometheus
chown prometheus:prometheus /var/lib/prometheus

# Systemd service
cat > /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus
After=network.target

[Service]
Type=simple
User=prometheus
ExecStart=/usr/local/bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/var/lib/prometheus \
    --storage.tsdb.retention.time=30d \
    --web.enable-lifecycle
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus
```

### prometheus.yml

```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

# Alert rules
rule_files:
  - "rules/*.yml"

# Alertmanager
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093

# Scrape targets
scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node exporter (Linux hosts)
  - job_name: 'node'
    static_configs:
      - targets:
        - 'server1:9100'
        - 'server2:9100'
        - 'server3:9100'
    relabel_configs:
      - source_labels: [__address__]
        regex: '(.*):(.*)'
        target_label: instance
        replacement: '${1}'

  # MySQL exporter
  - job_name: 'mysql'
    static_configs:
      - targets: ['db-server:9104']

  # Nginx exporter
  - job_name: 'nginx'
    static_configs:
      - targets: ['web-server:9113']

  # File-based service discovery
  - job_name: 'file-sd'
    file_sd_configs:
      - files:
        - '/etc/prometheus/targets/*.json'
        refresh_interval: 30s
```

### File-Based Service Discovery

```json
// /etc/prometheus/targets/hosts.json
[
  {
    "targets": ["server1:9100", "server2:9100"],
    "labels": {
      "env": "production",
      "region": "us-east-1"
    }
  },
  {
    "targets": ["server3:9100"],
    "labels": {
      "env": "staging",
      "region": "us-west-2"
    }
  }
]
```

### Kubernetes Service Discovery

```yaml
# Kubernetes SD (auto-discovers pods, services, endpoints)
scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Only scrape pods with prometheus.io/scrape annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      # Use custom port from annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: (.+)
        replacement: $1
      # Add pod name as label
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
```

### Relabeling

Relabeling modifies labels before scraping:

```yaml
relabel_configs:
  # Keep only targets with specific label
  - source_labels: [__meta_kubernetes_pod_label_app]
    action: keep
    regex: myapp

  # Drop targets matching a pattern
  - source_labels: [__address__]
    action: drop
    regex: '.*localhost.*'

  # Rewrite instance label
  - source_labels: [__meta_kubernetes_pod_name]
    target_label: instance

  # Add static label
  - target_label: environment
    replacement: production

  # Extract port from address
  - source_labels: [__address__]
    regex: '(.+):(\d+)'
    target_label: __address__
    replacement: '$1:9100'
```

## PromQL

PromQL (Prometheus Query Language) is the query language for Prometheus:

### Basic Queries

```promql
# CPU utilization (percentage)
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage percentage
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# Disk usage percentage
(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100

# Network throughput (bytes/sec)
rate(node_network_receive_bytes_total{device="eth0"}[5m])
rate(node_network_transmit_bytes_total{device="eth0"}[5m])

# Disk IOPS
rate(node_disk_reads_completed_total{device="sda"}[5m])
rate(node_disk_writes_completed_total{device="sda"}[5m])
```

### Aggregation Functions

```promql
# Average CPU across all cores
avg(rate(node_cpu_seconds_total{mode="user"}[5m]))

# Max CPU by instance
max by(instance) (100 - (avg by(instance, cpu) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))

# Sum of network bytes across all interfaces
sum by(instance) (rate(node_network_receive_bytes_total[5m]))

# Top 5 memory consumers
topk(5, node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes)

# Count of running processes
node_procs_running
```

### Rate and Increase

```promql
# Per-second rate (for counters)
rate(http_requests_total[5m])

# Per-second rate, accounting for counter resets
irate(http_requests_total[5m])

# Total increase over time range
increase(http_requests_total[1h])

# Derivative (rate for gauges)
deriv(node_load1[5m])
```

### Histograms

```promql
# Request duration 95th percentile
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Request duration 99th percentile by endpoint
histogram_quantile(0.99, sum by(le, endpoint) (rate(http_request_duration_seconds_bucket[5m])))

# Request rate by status code
sum by(status) (rate(http_requests_total[5m]))
```

## Alert Rules

### Alert Rule Syntax

```yaml
# /etc/prometheus/rules/node_alerts.yml
groups:
  - name: node_alerts
    rules:
      # High CPU usage
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value }}% (threshold: 80%)"

      # High memory usage
      - alert: HighMemoryUsage
        expr: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value }}% (threshold: 90%)"

      # Disk space low
      - alert: DiskSpaceLow
        expr: (1 - node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes) * 100 > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space on {{ $labels.instance }}:{{ $labels.mountpoint }}"
          description: "Disk usage is {{ $value }}% (threshold: 85%)"

      # Disk will fill in 24 hours
      - alert: DiskWillFillIn24h
        expr: predict_linear(node_filesystem_avail_bytes{fstype!="tmpfs"}[6h], 24*3600) < 0
        for: 30m
        labels:
          severity: critical
        annotations:
          summary: "Disk will fill in 24h on {{ $labels.instance }}"
          description: "Disk {{ $labels.mountpoint }} predicted to fill within 24 hours"

      # High I/O wait
      alert: HighIOWait
      expr: avg by(instance) (rate(node_cpu_seconds_total{mode="iowait"}[5m])) * 100 > 20
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High I/O wait on {{ $labels.instance }}"
        description: "I/O wait is {{ $value }}%"

      # Node down
      - alert: NodeDown
        expr: up{job="node"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Node {{ $labels.instance }} is down"
```

### Validate and Reload

```bash
# Validate rules
promtool check rules /etc/prometheus/rules/*.yml
# Checking /etc/prometheus/rules/node_alerts.yml
# SUCCESS: 6 rules found

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload
```

## Grafana

### Installation

```bash
# Install Grafana
apt install -y apt-transport-https software-properties-common
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" > /etc/apt/sources.list.d/grafana.list
apt update
apt install grafana

# Start and enable
systemctl enable grafana-server
systemctl start grafana-server

# Default credentials: admin/admin
# Access: http://localhost:3000
```

### Adding Prometheus Data Source

```bash
# Via API
curl -X POST http://admin:admin@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://localhost:9090",
    "access": "proxy",
    "isDefault": true
  }'
```

### Dashboard JSON Example

```json
{
  "dashboard": {
    "title": "Linux Server Overview",
    "panels": [
      {
        "title": "CPU Usage",
        "type": "timeseries",
        "targets": [
          {
            "expr": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "{{ instance }}"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "gauge",
        "targets": [
          {
            "expr": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100",
            "legendFormat": "{{ instance }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 70, "color": "yellow"},
                {"value": 90, "color": "red"}
              ]
            }
          }
        }
      }
    ]
  }
}
```

### Useful Dashboard Panels

```bash
# CPU usage over time
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory breakdown
node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes
node_memory_Buffers_bytes
node_memory_Cached_bytes

# Disk I/O throughput
rate(node_disk_read_bytes_total[5m])
rate(node_disk_write_bytes_total[5m])

# Network throughput
rate(node_network_receive_bytes_total{device="eth0"}[5m])
rate(node_network_transmit_bytes_total{device="eth0"}[5m])

# Load average
node_load1
node_load5
node_load15

# Uptime
time() - node_boot_time_seconds
```

## Alertmanager

### Configuration

```yaml
# /etc/alertmanager/alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/xxx/yyy/zzz'

route:
  group_by: ['alertname', 'instance']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'
  
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'

  - name: 'slack'
    slack_configs:
      - channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'xxx'
```

## Best Practices

```bash
# 1. Label everything consistently
# Good: {env="prod", region="us-east", role="web"}
# Bad: inconsistent labels across targets

# 2. Use recording rules for expensive queries
# /etc/prometheus/rules/recording_rules.yml
groups:
  - name: recording_rules
    rules:
      - record: instance:node_cpu_utilization:ratio
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 3. Set appropriate retention
prometheus --storage.tsdb.retention.time=30d

# 4. Monitor Prometheus itself
prometheus_tsdb_head_series
prometheus_tsdb_head_chunks
prometheus_engine_query_duration_seconds
```

### Recording Rules

Recording rules precompute expensive queries and store results as new time series:

```yaml
# /etc/prometheus/rules/recording_rules.yml
groups:
  - name: node_recording
    interval: 30s  # Evaluate every 30s (default: global evaluation_interval)
    rules:
      # CPU utilization ratio
      - record: instance:node_cpu_utilization:ratio
        expr: |
          1 - avg by(instance) (
            rate(node_cpu_seconds_total{mode="idle"}[5m])
          )

      # Memory utilization ratio
      - record: instance:node_memory_utilization:ratio
        expr: |
          1 - (
            node_memory_MemAvailable_bytes
            / node_memory_MemTotal_bytes
          )

      # Disk I/O utilization
      - record: instance:node_disk_io_utilization:ratio
        expr: |
          rate(node_disk_io_time_seconds_total{device=~"sd.*"}[5m])

      # Network throughput (Mbps)
      - record: instance:node_network_receive_mbps:rate
        expr: |
          rate(node_network_receive_bytes_total{device!~"lo|veth.*"}[5m]) * 8 / 1000000

      # Request rate by status code
      - record: job:http_requests:rate5m
        expr: |
          sum by(job, status) (
            rate(http_requests_total[5m])
          )

      # P99 latency
      - record: job:http_request_duration:p99
        expr: |
          histogram_quantile(0.99,
            sum by(job, le) (
              rate(http_request_duration_seconds_bucket[5m])
            )
          )
```

```bash
# Validate recording rules
promtool check rules /etc/prometheus/rules/recording_rules.yml

# Test recording rule queries
promtool test rules test_cases.yml

# Use recording rules in queries (much faster than raw queries)
instance:node_cpu_utilization:ratio{instance="server1:9100"}
```

### Recording Rules Naming Convention

```
level:metric_name:operations
│       │           │
│       │           └── aggregation/rate (ratio, rate5m, p99, etc.)
│       └── base metric name
└── aggregation level (instance, job, cluster)

Examples:
  instance:node_cpu_utilization:ratio
  job:http_requests:rate5m
  cluster:node_memory_available:min
```

## Grafana Provisioning

### Automated Dashboard Provisioning

```yaml
# /etc/grafana/provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: false
```

```yaml
# /etc/grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1
providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

```bash
# Place dashboard JSON files in /var/lib/grafana/dashboards/
# They'll be auto-imported on Grafana restart

# Export existing dashboard via API
curl -s http://admin:admin@localhost:3000/api/dashboards/uid/abc123 \
    | jq '.dashboard' > /var/lib/grafana/dashboards/my-dashboard.json

# Import dashboard via API
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @/var/lib/grafana/dashboards/my-dashboard.json
```

### Grafana Alerting (Unified Alerting)

```yaml
# Grafana 9+ unified alerting
# /etc/grafana/provisioning/alerting/rules.yml
apiVersion: 1
groups:
  - orgId: 1
    name: Linux Server Alerts
    folder: Alerts
    interval: 1m
    rules:
      - uid: high-cpu-alert
        title: High CPU Usage
        condition: C
        data:
          - refId: A
            datasourceUid: prometheus
            model:
              expr: instance:node_cpu_utilization:ratio > 0.9
              intervalMs: 60000
          - refId: C
            datasourceUid: __expr__
            model:
              type: threshold
              conditions:
                - evaluator:
                    type: gt
                    params: [0.9]
```

## Long-Term Storage

Prometheus stores data locally (default 15-90 days). For longer retention:

### Thanos

```mermaid
graph TD
    PROM1["Prometheus 1<br>+ Thanos Sidecar"] --> OBJ["Object Storage<br>(S3/GCS/MinIO)"]
    PROM2["Prometheus 2<br>+ Thanos Sidecar"] --> OBJ
    QUERY["Thanos Query"] --> PROM1
    QUERY --> PROM2
    QUERY --> STORE["Thanos Store Gateway"]
    STORE --> OBJ
    GRAFANA[Grafana] --> QUERY
```

### VictoriaMetrics

```bash
# VictoriaMetrics as Prometheus long-term storage
# Drop-in replacement with better compression and longer retention

# Start VictoriaMetrics
victoria-metrics-prod \
    -retentionPeriod=1y \
    -storageDataPath=/var/lib/victoria-metrics

# Remote write from Prometheus
# prometheus.yml:
# remote_write:
#   - url: http://victoria-metrics:8428/api/v1/write
```

## Common Exporters

| Exporter | Port | Metrics | Use Case |
|----------|------|---------|----------|
| node_exporter | 9100 | CPU, memory, disk, network | Linux hosts |
| mysqld_exporter | 9104 | Queries, connections, replication | MySQL/MariaDB |
| postgres_exporter | 9187 | Queries, connections, locks | PostgreSQL |
| redis_exporter | 9121 | Commands, memory, keys | Redis |
| blackbox_exporter | 9115 | HTTP, TCP, ICMP probes | Endpoint monitoring |
| nginx_exporter | 9113 | Requests, connections | Nginx |
| process_exporter | 9256 | Per-process CPU, memory | Process monitoring |
| cadvisor | 8080 | Container CPU, memory, network | Docker/K8s |

### Blackbox Exporter Configuration

```yaml
# /etc/blackbox_exporter/config.yml
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: [200]
      method: GET
      follow_redirects: true
      preferred_ip_protocol: "ip4"

  tcp_connect:
    prober: tcp
    timeout: 5s

  icmp:
    prober: icmp
    timeout: 5s
```

```yaml
# Prometheus scrape config for blackbox
scrape_configs:
  - job_name: 'blackbox-http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - https://example.com
        - https://api.example.com/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9115  # Blackbox exporter address
```

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Alertmanager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- <https://prometheus.io/docs/practices/> - Prometheus best practices
- <https://grafana.com/docs/grafana/latest/> - Grafana documentation
- <https://promlabs.com/> - PromLabs (Prometheus training)
- <https://www.robustperception.io/> - Robust Perception blog (Prometheus experts)

## Related Topics

- [Observability Overview](overview.md)
- [Metrics Collection](metrics.md)
- [proc Filesystem](proc.md)
