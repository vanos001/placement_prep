# ELK Stack (Elasticsearch, Logstash, Kibana)

The ELK Stack is a collection of three open-source tools — Elasticsearch (search and analytics), Logstash (data ingestion and processing), and Kibana (visualization) — that together provide an end-to-end log management and analytics platform. Originally developed by Elastic (2010), it became the de facto standard for log aggregation and search in the 2010s. This page covers the architecture, the ingestion pipeline, the search capabilities, and the production deployment patterns.

## The Architecture

```text
Sources (apps, servers, agents)
   │
   │ logs (syslog, JSON, plain text)
   ▼
┌─────────────────────────────────────────────────────────────┐
│  Beats (lightweight agents)                                  │
│  - Filebeat: tails files                                     │
│  - Metricbeat: collects metrics                              │
│  - Packetbeat: network traffic                                │
│  - Heartbeat: uptime monitoring                              │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Logstash (data processing pipeline)                          │
│  - Input: receive from Beats, Kafka, etc.                  │
│  - Filter: parse, transform, enrich                         │
│  - Output: send to Elasticsearch (and others)              │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Elasticsearch Cluster                                       │
│  - Distributed, RESTful search engine                       │
│  - Stores logs as JSON documents (sharded + replicated)     │
│  - Full-text search with Lucene                             │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Kibana (visualization)                                      │
│  - Dashboards, charts, maps                                  │
│  - Kibana Query Language (KQL) for searching                 │
│  - Kibana Dev Tools (DSL queries, console)                  │
└─────────────────────────────────────────────────────────────┘
```

The full pipeline: agents → Logstash → Elasticsearch → Kibana. Some modern setups skip Logstash (agents send directly to Elasticsearch).

## Elasticsearch: The Search Engine

Elasticsearch is the heart of the ELK stack. It's a distributed, RESTful search engine built on Apache Lucene.

### Index and Shard

Each "index" is a logical namespace for a collection of documents. Each index is split into "shards" (typically 1-10 GB each) that can be on different nodes:

```text
Index: logs-2024-01-15 (10 shards, 1 replica each)
  Shard 0 (primary on Node A, replica on Node B)
  Shard 1 (primary on Node B, replica on Node A)
  ...
  Shard 9 (primary on Node C, replica on Node D)
```

Shards are the unit of parallelism — each shard can be queried independently; results are merged.

### The Document Model

Each log is a JSON document:

```json
{
  "@timestamp": "2024-01-15T12:34:56.789Z",
  "level": "INFO",
  "service": "myapp",
  "message": "Order processed",
  "order_id": 123,
  "customer": "alice",
  "duration_ms": 45
}
```

Elasticsearch indexes every field:
- Text fields: full-text indexed (tokenized, lowercased, stemmed).
- Keyword fields: exact-match indexed (no tokenization).
- Numeric fields: range-query indexed (B-tree).
- Date fields: range-query indexed.

This dual indexing is what makes Elasticsearch powerful: you can search `level: "ERROR"` (exact) and `message: "Order"` (full-text) on the same field.

### The Query DSL

Elasticsearch queries are JSON-based:

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "message": "Order processed" } },
        { "range": { "duration_ms": { "gte": 100 } } }
      ],
      "filter": [
        { "term": { "level": "INFO" } },
        { "range": { "@timestamp": { "gte": "now-1h" } } }
      ]
    }
  },
  "sort": [{ "@timestamp": "desc" }],
  "size": 100
}
```

`match` is a full-text query (tokenized); `term` is an exact match; `range` is numeric/date range.

### Aggregations

Elasticsearch supports complex aggregations:

```json
{
  "aggs": {
    "by_service": {
      "terms": { "field": "service" },
      "aggs": {
        "avg_duration": { "avg": { "field": "duration_ms" } },
        "error_count": {
          "filter": { "term": { "level": "ERROR" } }
        }
      }
    }
  }
}
```

This groups by service, computes the average duration, and counts errors per service — all in one query.

## Logstash: The Processing Pipeline

Logstash is a data processing pipeline with three stages:

```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:message}" }
  }
  date {
    match => [ "timestamp", "ISO8601" ]
  }
  mutate {
    add_field => { "service" => "myapp" }
  }
  if [level] == "ERROR" {
    elasticsearch {
      ... # enrich with error reference
    }
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }
}
```

- **Input**: receives data from Beats, Kafka, file tailing, syslog, etc.
- **Filter**: parses (grok pattern matching), transforms (mutate), enriches (geoip, elasticsearch).
- **Output**: sends to Elasticsearch (and others — S3, Kafka, file, etc.).

Logstash is heavy (~500 MB RAM per instance); modern setups use lighter alternatives (Fluent Bit) for ingestion, with Logstash only for complex parsing.

## Kibana: The Visualization

Kibana provides:
- **Discover**: search logs with KQL (Kibana Query Language).
- **Visualize**: charts (line, bar, pie, heatmap, gauge).
- **Dashboard**: combine multiple visualizations.
- **Dev Tools**: REST API console (for DSL queries).
- **Alerting**: rules trigger on query patterns (since 7.x).

```text
# KQL example
level: "ERROR" and service: "myapp" and duration_ms > 1000

# Translated to DSL (Kibana does this)
{
  "query": {
    "bool": {
      "must": [
        { "term": { "level": "ERROR" } },
        { "term": { "service": "myapp" } },
        { "range": { "duration_ms": { "gt": 1000 } } }
      ]
    }
  }
}
```

## Production Deployment

For high-throughput log ingestion (TB/day), the recommended pattern:

```text
Agents → Kafka (buffer) → Logstash → Elasticsearch → Kibana
```

Kafka buffers the logs (handling ES backpressure); Logstash processes them; ES stores them. Without Kafka, ES backpressure can cause Logstash to drop logs.

### Index Lifecycle Management (ILM)

ILM automates index lifecycle:

```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": { "rollover": { "max_size": "50gb", "max_age": "1d" } }
      },
      "warm": {
        "min_age": "1d",
        "actions": { "forcemerge": { "max_num_segments": 1 } }
      },
      "cold": {
        "min_age": "7d",
        "actions": { "freeze": {} }
      },
      "delete": {
        "min_age": "30d",
        "actions": { "delete": {} }
      }
    }
  }
}
```

- Hot: actively written, on fast SSD, replicas for HA.
- Warm: read-only, on slower disk, no replicas.
- Cold: frozen (depends on search; cheap).
- Delete: removed.

ILM keeps storage costs under control — logs older than 30 days are deleted.

## Production Performance

Typical ELK performance on a 5-node cluster (16-core CPU, 64 GB RAM each, NVMe SSDs):
- Ingestion: 100K events/sec sustained.
- Search latency: <100 ms for recent indices (1 day).
- Search latency: 1-5 sec for historical indices (30 days).
- Storage: 1-5 KB per event (compressed).

For comparison, Loki on the same hardware: 1M+ events/sec ingestion, but no full-text search.

## Common Pitfalls

1. **Using too many shards.** Each shard has overhead (~50 MB heap); a 1000-shard index wastes memory. Aim for ~50 GB per shard.

2. **Forgetting to use ILM.** Without ILM, indices accumulate; eventually disk fills.

3. **Forgetting to set field mappings.** Elasticsearch auto-detects field types (text vs. keyword), which can lead to wrong mappings. Set explicit mappings in the index template.

4. **Forgetting that Elasticsearch is heavy.** Each instance uses 50% of RAM for the JVM heap. Plan capacity carefully.

5. **Forgetting to use replicas.** A single-replica index can be lost on node failure. Use 1 replica minimum for production.

6. **Forgetting to monitor cluster health.** `cluster_health` should be `green`; `yellow` means a replica is unassigned; `red` means a primary is unassigned (data loss risk).

## Comparison to Loki

| Aspect | ELK Stack | Loki |
|--------|-----------|------|
| Storage | Elasticsearch (Lucene) | Object storage (S3) |
| Index | Full-text (every word) | Labels only |
| Cost | High (SSD-bound) | Low (S3) |
| Full-text search | Excellent | Limited (regex/substring) |
| Log volume | Limited by ES | Massive |
| Best for | Compliance, full-text queries | High-volume, label-based queries |

For most Kubernetes deployments, Loki is sufficient. For compliance (e.g., legal log retention), ELK remains.

## References

- [Elastic Stack documentation](https://www.elastic.co/guide/index.html)
- [Elasticsearch: The Definitive Guide](https://www.elastic.co/guide/en/elasticsearch/guide/current/index.html)
- [Logstash documentation](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Kibana documentation](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Index Lifecycle Management](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-lifecycle-management.html)
- [Elastic Beats documentation](https://www.elastic.co/guide/en/beats/libbeat/current/index.html)
- [Elasticsearch performance tuning](https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-for-search-speed.html)
- [LWN: ELK Stack overview (2020)](https://lwn.net/Articles/820130/)
