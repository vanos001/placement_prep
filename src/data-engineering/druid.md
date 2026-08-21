# Apache Druid

Apache Druid is an open-source real-time analytics database, originally developed at Metamarkets in 2011 and donated to Apache in 2018. It's designed for sub-second queries on large event-driven datasets (click streams, logs, sensor data), combining real-time ingestion with historical analytics. This page covers the segment-based storage model, the columnar compression, the real-time and historical node split, and the production use cases.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Coordinator (master)                                       │
│  - Manages segment assignment to historical nodes           │
│  - Balances load across the cluster                          │
└─────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Overlord              │    │  Broker               │
│  - Manages ingestion   │    │  - Routes queries to   │
│    tasks               │    │    historical + real-time│
│  - Schedules tasks     │    │    nodes                │
└──────────────────────┘    └──────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Middle Manager        │    │  Historical           │
│  - Real-time ingestion │    │  - Historical segments │
│    tasks (peon)         │    │    loaded from deep    │
│  - Real-time queries    │    │    storage             │
└──────────────────────┘    └──────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────┐
│  Deep Storage (S3, HDFS, GCS)                              │
│  - Persistent segment storage                             │
└──────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────┐
│  Metadata Storage (PostgreSQL or MySQL)                   │
│  - Segment metadata, supervisor state, audit logs         │
└──────────────────────────────────────────────────────────┘
```

Druid has many node types:
- **Coordinator**: assigns segments to historical nodes.
- **Overlord**: manages ingestion tasks (Middle Manager).
- **Broker**: routes queries to historical + real-time nodes; merges results.
- **Historical**: serves queries from segments in deep storage.
- **Middle Manager**: real-time ingestion and queries.
- **Indexer**: a newer unified node type (since 0.21) that combines Middle Manager and Historical.

## The Segment

A Druid segment is the unit of data storage — a columnar, immutable, time-partitioned chunk:

```text
Segment: events_2024-01-01_2024-01-02_v1
  Partition: by hash of primary key (e.g., user_id)
  Granularity: hour (configurable)

Columns in the segment:
  timestamp (LONG, sorted, indexed)
  dimensions: user_id, country, event_type (string, dictionary-encoded)
  metrics: count, sum_amount, avg_duration (numeric, pre-aggregated)

Files in the segment:
  version.json
  meta.json (schema, column types)
  timestamp-column (compressed)
  user_id-column (dictionary + bitmaps)
  country-column (dictionary + bitmaps)
  metrics (compressed)
  index.drd (sparse index)
```

A segment typically holds 1-5M rows (~1 GB compressed). Segments are immutable; new data creates new segments.

## Real-time Ingestion

Druid's real-time ingestion uses the "peon" task on Middle Managers:

```text
1. A streaming ingestion supervisor (e.g., Kafka) starts peon tasks.
2. Each peon task reads from a Kafka partition.
3. The peon maintains an in-memory window of recent events (e.g., 1 hour).
4. Queries to the peon hit the in-memory window (and on-disk segments it has
   finalized).
5. Periodically (e.g., every 10 minutes), the peon writes a finalized segment
   to deep storage and starts a new window.
```

The trade-off: real-time ingestion enables sub-second query latency for new data, but the in-memory window can be lost if the peon fails (the window must be re-read from Kafka).

## Historical Nodes

Historical nodes load segments from deep storage on demand:

```text
1. Coordinator tells Historical 0: load segment S.
2. Historical 0 downloads S from S3.
3. Historical 0 maps S into memory (mmap).
4. Queries for S's time range are routed to Historical 0.
5. When the segment ages out (e.g., >7 days old), the Coordinator tells
   Historical 0 to drop S.
```

Historical nodes can serve from on-disk segments (via mmap) or fully in-memory segments. The latter is for hot data; the former for cold data.

## Columnar Compression

Druid's columnar storage uses several compression techniques:

1. **Dictionary encoding** (for string columns): each unique value gets an ID. The column stores IDs (4 bytes each, or smaller with bit-packing). For high-cardinality columns, this is bad (the dictionary is large); for low-cardinality, it's great.

2. **Bitmap indexes** (for dimensions): for each unique value, a bitmap of which rows have that value. Query: `WHERE country = 'US'` → bitmap lookup → row indices.

3. **Run-length encoding** (for sorted columns): consecutive identical values are stored as (value, count). For timestamps sorted by time, this is highly effective.

4. **LZ4 compression** (for everything else): generic compression on top of the above.

Combined, Druid's segments are typically 10-30× smaller than the raw JSON events.

## Production Performance

Druid's published performance on a 4-node cluster (16-core CPU, 64 GB RAM each):

| Query | Dataset size | Latency |
|-------|--------------|---------|
| Group-by country (200 countries) | 1B events | 50 ms |
| Top-N products by sales | 1B events | 100 ms |
| Time-series (5-min buckets, 1 year) | 100B events | 200 ms |
| Filtered scan (1% selectivity) | 1B events | 30 ms |

Druid excels at time-series and group-by queries on event data, with consistently sub-second latency even for very large datasets.

## Production Use Cases

### Click Stream Analytics

Druid's primary use case: real-time dashboards for click streams.

```json
// Event
{
  "timestamp": "2024-01-15T12:34:56.789Z",
  "user_id": "alice123",
  "page": "/products/123",
  "action": "view",
  "duration_ms": 4500,
  "country": "US"
}
```

Ingest via Kafka → Druid. Dashboards query "top pages by view count in last 24 hours" in <100 ms.

### Ad Tech Analytics

Impression and click tracking for ad networks. Druid's group-by and top-N queries are ideal for "top performing ads in last hour" queries.

### Network Monitoring

Network device telemetry: bytes/sec, packet count, error rate. Druid's time-series support handles this well.

### APM (Application Performance Monitoring)

Distributed traces: span duration, error rate per service.

## Comparison to ClickHouse

| Aspect | Druid | ClickHouse |
|--------|-------|------------|
| Origin | Metamarkets 2011 | Yandex 2009 |
| Focus | Real-time event analytics | General OLAP |
| Storage | Segments (immutable) | Parts (merge tree) |
| Real-time ingestion | Excellent (peon tasks) | Good (Buffer tables) |
| Query latency (real-time) | Sub-second | Sub-second (smaller data) |
| Best for | Click streams, ad tech | General analytics, dashboards |
| Production users | Netflix, Airbnb, Adobe | Cloudflare, Uber, Bloomberg |

Druid is the choice for real-time event ingestion with sub-second query needs. ClickHouse is the choice for general OLAP with high-throughput batch ingestion.

## Common Pitfalls

1. **Forgetting that high-cardinality dimensions hurt Druid.** A dimension with 1M+ unique values (e.g., user IDs) generates large bitmaps. Use approximate distinct (HyperLogLog) for counts.

2. **Forgetting that segments are immutable.** Updates require re-ingestion; deletes require "kill" tasks. Druid is for append-mostly workloads.

3. **Forgetting the segment size tuning.** Too small segments (100K rows) cause too many segments; too large (>5M rows) cause memory pressure during ingestion. Aim for 1-5M rows per segment.

4. **Forgetting that real-time ingestion windows are volatile.** A peon failure loses the in-memory window. Use replication (multiple peons per Kafka partition) for high-availability.

5. **Forgetting that group-by queries can be expensive.** Group-by on a high-cardinality column (e.g., user_id) creates many groups. Use sub-queries or top-N to limit.

6. **Forgetting that Druid's broker can be a SPOF.** The broker routes queries; if it fails, queries fail. Use multiple brokers behind a load balancer.

## References

- [Apache Druid documentation](https://druid.apache.org/docs/latest/design/)
- Yang et al., "[Druid: A Real-time Analytical Data Store](https://www.eecs.harvard.edu/~cahoon/cicde/papers/p1495-yang.pdf)" (CIDR 2013)
- [Druid GitHub repository](https://github.com/apache/druid)
- [Druid vs ClickHouse comparison (Imply blog)](https://imply.io/blog/real-time-analytics-comparison-druid-vs-clickhouse/)
- [Druid production case studies (Netflix)](https://netflixtechblog.com/scaling-time-series-data-storage-and-analytics-using-apache-druid-part-1-3a4f9d6cae0)
- [LWN: Apache Druid overview (2020)](https://lwn.net/Articles/820053/)
