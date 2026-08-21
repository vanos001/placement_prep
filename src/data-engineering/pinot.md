# Apache Pinot

Apache Pinot is an open-source real-time distributed OLAP datastore, originally developed at LinkedIn in 2013 and donated to Apache in 2018. It's designed for real-time analytics at scale, with sub-second queries on billions of rows. Pinot is used at LinkedIn for features like "Who Viewed My Profile" and "View" analytics, and at Microsoft, Uber, and Slack for similar real-time analytics use cases. This page covers the architecture, the segment model, the star-tree index, and the comparison to Druid.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Controller (cluster manager)                               │
│  - Manages table → segment assignment                       │
│  - Schema management                                       │
│  - REST API for management                                  │
└─────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Broker               │    │  Server                │
│  - Routes queries     │    │  - Hosts segments      │
│  - Merges results     │    │  - Serves real-time    │
│    from servers       │    │    and historical       │
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
│  Cluster Coordinator (Apache Helix + ZooKeeper)            │
│  - Cluster membership                                      │
│  - Segment → server assignment                             │
└──────────────────────────────────────────────────────────┘
```

Pinot uses Apache Helix (LinkedIn's cluster manager) and ZooKeeper for cluster coordination. The Controller manages metadata; the Broker routes queries; the Server hosts data.

## The Table and Segment Model

```sql
CREATE TABLE events (
    event_id STRING,
    user_id INT,
    timestamp LONG,
    event_type STRING,
    amount DOUBLE
) PARTITION_BY = "user_id"
SEGMENT_FLUSH_INTERVAL = "1h"
);

CREATE INDEX star_tree ON events (
    dimensions = ["user_id", "event_type"],
    function = ["SUM(amount)", "COUNT"],
    maxLeafRecords = 10000
);
```

Pinot's table model:
- **Schema**: defines columns (dimensions + metrics).
- **Table**: instantiates the schema with a partitioning strategy.
- **Segment**: a horizontal slice of the table, containing rows for one partition+time range.

Segments are immutable (like Druid). Real-time ingestion creates new segments periodically; old segments are uploaded to deep storage.

## The Star-Tree Index

Pinot's signature feature: the **star-tree**. It's a multi-dimensional index that pre-aggregates data for common query patterns:

```text
Star-tree structure:
  Root node: splits on dimension A (e.g., country)
    Child nodes: splits on dimension B (e.g., event_type)
      Leaf nodes: pre-aggregated values
        "star" node: aggregates all (used when query doesn't filter on this dimension)

Example: star-tree on (country, event_type) for SUM(amount):
  Root (country)
    ├── 'US' → SUM(amount) = $1000
    ├── 'UK' → SUM(amount) = $500
    └── *    → SUM(amount) = $1500  (all countries aggregated)

Query: SELECT SUM(amount) FROM events WHERE country = 'US'
  → Use star-tree: lookup 'US' node, get $1000. No scan.
```

The star-tree enables group-by queries to run in O(log N) time (where N is the segment size) instead of O(N) (full scan).

The trade-off: star-trees increase segment size (each star-node is a duplicate aggregation). The user must choose which dimensions to star-tree (the common query patterns).

## Real-time Ingestion

Pinot's real-time ingestion uses the "consuming" segment model:

```text
1. A Kafka topic with N partitions has N Pinot "consuming" segments.
2. Each segment is hosted by a Pinot Server (with replication).
3. The server consumes events from Kafka in real-time, appending to the segment.
4. Queries hit both consuming segments (real-time, in-memory) and completed
   segments (historical, on-disk).
5. Periodically (e.g., every hour), a consuming segment is "finalized":
   - The segment is uploaded to deep storage.
   - A new consuming segment starts.
   - Historical nodes load the finalized segment.
```

The consuming segment's in-memory state can be lost on server failure. The server re-consumes from Kafka's last committed offset on restart.

## Columnar Storage and Indexes

Pinot's segment format:

```text
Segment: events_2024-01-15_0
  Files:
    - columns: per-column compressed data
      - dimension columns: dictionary + bitmaps + value-indexes
      - metric columns: raw values, possibly compressed
      - timestamp columns: sorted, with RLE
    - indexes:
      - star-tree (if defined)
      - bloom filter (for high-cardinality IN-list queries)
      - inverted index (for low-cardinality equality queries)
      - range index (for range queries)
      - text index (Lucene-based, for full-text search)
    - metadata:
      - segment metadata (column types, statistics)
      - column metadata (cardinality, min/max, null count)
```

Pinot supports multiple index types per column; the query planner picks the best index for each query.

## Production Performance

Pinot's published performance on a 6-node cluster (16-core CPU, 64 GB RAM each):

| Query | Dataset size | Latency |
|-------|---------------|---------|
| Group-by country (200 countries) | 1B events | 60 ms |
| Top-N events by count (10 countries) | 1B events | 30 ms (with star-tree) |
| Filter + count (high selectivity) | 1B events | 20 ms |
| Time-series (hourly buckets, 1 year) | 100B events | 250 ms |

Pinot's star-tree makes top-N queries very fast; without it, performance is similar to Druid.

## Production Use Cases

### LinkedIn (origin)

- Who Viewed My Profile: real-time tracking of profile views.
- View analytics: dashboards for content engagement.
- Audience counts: real-time unique viewer counts.

### Microsoft

- Azure usage analytics: real-time dashboards for Azure service usage.

### Uber

- Real-time metrics for trip and driver analytics.

### Slack

- Message analytics: per-channel message counts, engagement.

### Stripe

- Payment fraud detection: real-time aggregation of suspicious patterns.

## Comparison to Druid

| Aspect | Pinot | Druid |
|--------|-------|-------|
| Origin | LinkedIn 2013 | Metamarkets 2011 |
| Real-time ingestion | Kafka ingestion | Kafka, Kinesis, etc. |
| Star-tree index | Yes (signature feature) | No |
| Inverted index | Yes | Yes |
| Best for | High-cardinality group-by | Time-series, click streams |
| Production users | LinkedIn, Microsoft, Stripe | Netflix, Airbnb, Adobe |
| Active community | Smaller | Larger |

Pinot's star-tree gives it an edge for "group-by on multiple dimensions" queries that Druid doesn't accelerate as well. Druid has more index types and a richer query language.

## Common Pitfalls

1. **Forgetting that star-trees increase segment size.** Each star-node is a duplicate aggregation. Don't star-tree high-cardinality dimensions.

2. **Forgetting that real-time ingestion requires Kafka offset management.** Pinot tracks offsets; if the offset is wrong on restart, data is lost or duplicated.

3. **Forgetting the segment size tuning.** Too small segments cause overhead; too large segments slow ingestion. Aim for 1-5M rows per segment.

4. **Forgetting that Pinot's schema is rigid.** Adding a column requires a schema migration; existing segments don't have the new column (queries must handle the null case).

5. **Forgetting that high-cardinality group-by is slow.** Without a star-tree, group-by on user_id (1M+ distinct) is slow. Use approximate distinct (HyperLogLog).

6. **Forgetting that Pinot's broker can be a SPOF.** Multiple brokers behind a load balancer are essential for HA.

## References

- [Apache Pinot documentation](https://docs.pinot.apache.org/)
- Kishore et al., "[Apache Pinot: A Real-time Analytical Data Store](https://www.cidrdb.org/cidr2021/papers/p35-kishore.pdf)" (CIDR 2021)
- [Pinot GitHub repository](https://github.com/apache/pinot)
- [Star-Tree index documentation](https://docs.pinot.apache.org/basics/components/star-tree-index)
- [LinkedIn: Pinot case study](https://engineering.linkedin.com/analytics/real-time-deep-dive-apache-pinot)
- [Pinot vs Druid comparison](https://docs.pinot.apache.org/basics/comparisons/pinot-vs-druid)
- [LWN: Apache Pinot overview (2021)](https://lwn.net/Articles/865099/)
