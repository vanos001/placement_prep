# Loki (Log Aggregation)

Loki is an open-source log aggregation system, originally developed at Grafana Labs in 2018. It is designed as a "Prometheus for logs" — a horizontally-scalable, multi-tenant, log storage and query system that integrates tightly with Grafana for visualization. This page covers the architecture, the index-vs-blob split, the LogQL query language, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Loki Cluster (multiple components, HA)                    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Distributor                                            │ │
│  │  - Receives logs from agents (Promtail, Fluent Bit)    │ │
│  │  - Validates and forwards to ingesters                 │ │
│  └────────────────────────────────────────────────────────┘ │
│              │                                                │
│              ▼                                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Ingester (multiple, HA via consistent hashing)         │ │
│  │  - Buffers recent logs in memory                       │ │
│  │  - Writes logs to object storage (S3)                   │ │
│  │  - Writes index to key-value store (Cassandra, etc.)   │ │
│  └────────────────────────────────────────────────────────┘ │
│              │                                                │
│              ▼                                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Querier                                               │ │
│  │  - Serves LogQL queries                                 │ │
│  │  - Reads from ingesters (recent) + storage (old)       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  Storage (S3, GCS, etc.)  │    │  Index (Cassandra, etc.) │
│  - Log chunks (compressed) │    │  - Series → chunk IDs    │
└──────────────────────────┘    └──────────────────────────┘
```

Loki separates logs (large, append-only, in object storage) from the index (small, in a database). This is the key architectural choice — logs are cheap to store in S3; the index is small (just metadata).

## The Label-based Index

Loki's index is similar to Prometheus's: each log stream is identified by a set of labels.

```text
Stream: {job="nginx", env="prod", instance="web-1"}
  Logs:
    2024-01-15T12:34:56Z GET /api/orders 200 12ms
    2024-01-15T12:34:57Z POST /api/orders 201 8ms
    ...
```

The index stores the mapping `(labels) → (chunk_ids)`. To query logs for a specific stream, Loki:
1. Looks up the labels in the index → gets chunk IDs.
2. Fetches the chunks from object storage.
3. Decompresses and returns the logs.

This is much cheaper than Elasticsearch's full-text index (which indexes every word in every log line). Loki only indexes labels, not log contents.

## LogQL

LogQL is Loki's query language, similar to PromQL:

```text
# Filter logs by label
{job="nginx", env="prod"}

# Filter by content
{job="nginx"} |= "error"

# Extract fields and aggregate
sum by (status) (
  rate({job="nginx"} | regexp `HTTP (?P<status>\d{3})`[5m])
)

# Complex queries
sum(count_over_time({job="nginx"} |~ "error|fail"[5m])) by (instance)
```

LogQL has two parts:
- **Stream selector**: `{job="nginx"}` — picks the streams to query.
- **Filter pipeline**: `|= "error" | regexp "..." | json` — processes the log lines.

After filtering, you can:
- Count lines: `count_over_time(...[5m])`.
- Extract fields: `| regexp` or `| json`.
- Aggregate: `sum by (...)`, `avg`, etc.

LogQL is less powerful than Elasticsearch's query DSL (no full-text search, no fuzzy matching), but it's much faster for label-based queries.

## The Ingestion Path

Logs are ingested via agents:
- **Promtail** (Loki's native agent): tails log files, parses with pipeline configs, sends to Loki.
- **Fluent Bit / Fluentd**: with Loki output plugin.
- **Vector**: with Loki sink.
- **OpenTelemetry Collector**: with Loki exporter.

```yaml
# promtail.yaml
scrape_configs:
  - job_name: nginx
    static_configs:
      - targets: [localhost]
        labels:
          job: nginx
          env: prod
          __path__: /var/log/nginx/*.log
    pipeline_stages:
      - regex:
          expression: '^(?P<timestamp>\S+) (?P<method>\S+) (?P<path>\S+) (?P<status>\d{3}) (?P<duration>\d+)ms'
      - labels:
          status:
          method:
```

The agent:
1. Tails the log files.
2. Parses each line with the pipeline stages.
3. Adds labels (job, env, status, etc.).
4. Sends batches to Loki's distributor.

## Production Performance

Loki's published performance on a 4-node cluster:
- Ingestion: 1M+ log lines/sec.
- Storage: ~1 KB per log line compressed (vs ~5 KB uncompressed).
- Query latency (1 hour of logs): ~100 ms.
- Query latency (1 day of logs): ~500 ms.
- Query latency (1 month of logs): ~5 sec.

For comparison, Elasticsearch on the same hardware would be ~10× slower for label-based queries (full-text index overhead) but ~10× faster for full-text searches.

## Production Deployment

```yaml
# loki-values.yaml (Helm chart)
loki:
  schemaConfig:
    configs:
      - from: 2024-01-01
        store: tsdb
        object_store: s3
        index:
          prefix: index_
          period: 24h
  storageConfig:
    aws:
      s3: s3://my-loki-bucket
  limits_config:
    retention_period: 30d
    ingestion_rate_mb: 10
    max_streams_per_user: 10000
  compactor:
    retention_enabled: true
    retention_delete_delay: 2h
```

Loki's single-binary deployment is for dev; for production, use the distributed mode with separate distributor, ingester, querier, and compactor.

## Common Patterns

### Pattern 1: Kubernetes Logs

Loki is the standard for Kubernetes logs. The Grafana Loki stack (Loki + Promtail + Grafana) is the "Kubernetes-native" alternative to the ELK stack.

```yaml
# DaemonSet (Promtail) on each node
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: promtail
spec:
  template:
    spec:
      containers:
        - name: promtail
          image: grafana/promtail:latest
          args: [-config.file=/etc/promtail/promtail.yaml]
          volumeMounts:
            - { name: config, mountPath: /etc/promtail }
            - { name: varlog, mountPath: /var/log }
            - { name: varlibdockercontainers, mountPath: /var/lib/docker/containers, readOnly: true }
```

Each node's Promtail tails `/var/log/*` and the Docker container logs, sending to Loki.

### Pattern 2: Application Logs

For structured application logs (e.g., Python's `json` logs):

```python
import json
import logging

logger = logging.getLogger("myapp")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('{"ts": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s", "service": "myapp"}'))
logger.addHandler(handler)

logger.info("Order processed", extra={"order_id": 123, "customer": "alice"})
# Outputs: {"ts": "2024-01-15T12:34:56Z", "level": "INFO", "msg": "Order processed", "service": "myapp", "order_id": 123, "customer": "alice"}
```

Promtail's `json` pipeline stage parses this; Loki indexes `service` and `level` as labels.

### Pattern 3: Alerting

Loki integrates with Grafana's alerting system. Rules can fire on log patterns:

```yaml
groups:
  - name: error-alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate({job="myapp"} |= "error"[5m])) by (instance)
            > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.instance }}"
```

If a service logs more than 1 "error" per second for 2+ minutes, alert.

## Comparison to ELK Stack

| Aspect | Loki | ELK Stack |
|--------|------|-----------|
| Storage | Object storage (S3) | Elasticsearch indices |
| Index | Labels only | Full-text (every word) |
| Compression | ~10× | ~3-5× |
| Cost | Low (S3) | High (SSD-bound ES) |
| Full-text search | Limited (regex/substring) | Excellent |
| Log volume | Massive (TB/day) | Limited by ES capacity |
| Best for | High-volume, label-based queries | Full-text search |

For most Kubernetes deployments, Loki is sufficient and cheaper. For full-text search (e.g., legal compliance), ELK is still needed.

## Common Pitfalls

1. **High-cardinality labels.** A label like `user_id` (1M distinct values) creates 1M streams, blowing up the index. Use low-cardinality labels only.

2. **Forgetting to set retention.** Logs accumulate indefinitely; set `retention_period` to limit cost.

3. **Forgetting that Loki's index is per-stream.** Adding streams (new label combinations) is fast, but each stream has its own chunk files. Too many streams = too many chunk files = slow queries.

4. **Forgetting that query performance depends on time range.** A 30-day query is slow because it must scan many chunks. Use a shorter time range.

5. **Forgetting that Loki doesn't support full-text search.** If you need "find all logs containing 'DatabaseError'", use ELK or Loki's regex matching (slower).

6. **Forgetting that the Promtail pipeline parses lazily.** A bad regex pattern in the pipeline silently drops logs. Test the pipeline with `promtail --debug` first.

## References

- [Loki documentation](https://grafana.com/docs/loki/latest/)
- [Loki GitHub repository](https://github.com/grafana/loki)
- Grafana Labs, "[Loki: Like Prometheus, but for logs](https://grafana.com/blog/2018/12/12/loki-prometheus-inspired-open-source-logging-for-cloud-natives/)" (2018)
- [LogQL documentation](https://grafana.com/docs/loki/latest/logql/)
- [Promtail pipeline stages](https://grafana.com/docs/loki/latest/clients/promtail/pipelines/)
- [Loki vs ELK comparison (Grafana)](https://grafana.com/blog/2021/01/25/loki-vs-elasticsearch-whats-the-difference/)
- [LWN: Loki overview (2021)](https://lwn.net/Articles/856775/)
