# Data-Intensive Application Design

## What is Data-Intensive?

A data-intensive application is one where **data volume, complexity, or velocity** is the primary challenge, rather than computation. Examples: analytics platforms, log processing, recommendation engines, search engines.

## Batch vs Stream Processing

### Batch Processing
Process large volumes of data at scheduled intervals.

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Data    │────→│  Batch   │────→│  Results │
│  Source  │     │  Job     │     │  Store   │
│ (HDFS, S3)│    │ (Spark,  │     │(Data     │
│          │     │  Hadoop) │     │ Warehouse)│
└──────────┘     └──────────┘     └──────────┘
Schedule: Every night at 2 AM
Latency: Minutes to hours
```

**Use Cases**:
- Daily sales reports
- Monthly billing
- Data warehouse ETL
- Machine learning model training

**Technologies**: Apache Spark, Hadoop MapReduce, Apache Hive, AWS EMR

### Stream Processing
Process data in real-time as it arrives.

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Event   │────→│  Stream  │────→│  Real-   │
│  Source  │     │ Processor│     │  time DB │
│ (Kafka,  │     │ (Flink,  │     │          │
│  Kinesis)│     │  Storm)  │     │          │
└──────────┘     └──────────┘     └──────────┘
Latency: Milliseconds to seconds
```

**Use Cases**:
- Real-time fraud detection
- Live dashboards
- IoT sensor processing
- Real-time recommendations

**Technologies**: Apache Kafka Streams, Apache Flink, Apache Storm, Spark Streaming

### Batch vs Stream Comparison

| Aspect | Batch | Stream |
|--------|-------|--------|
| Latency | Minutes-hours | Milliseconds-seconds |
| Throughput | Very high | High |
| Data size | All historical data | Recent window |
| Complexity | Simpler | More complex |
| Ordering | Global ordering possible | Per-partition ordering |
| Correctness | Easier to guarantee | Harder (late events) |
| Use case | Reports, ETL, ML training | Real-time analytics, alerts |

### Lambda Architecture
Combines batch and stream processing.

```
                    ┌─────────────────────────┐
                    │       Serving Layer      │
                    │    (Query Interface)     │
                    └───────────┬─────────────┘
              ┌─────────────────┼─────────────────┐
              ▼                                   ▼
    ┌─────────────────┐                 ┌─────────────────┐
    │   Batch Layer   │                 │  Speed Layer    │
    │   (Spark)       │                 │  (Flink/Kafka)  │
    │   Complete,     │                 │  Real-time,     │
    │   accurate      │                 │  approximate    │
    └────────┬────────┘                 └────────┬────────┘
             │                                    │
             └──────────────┬─────────────────────┘
                            ▼
                    ┌───────────────┐
                    │  Data Source  │
                    └───────────────┘
```

### Kappa Architecture
Stream-only, simpler alternative to Lambda.

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Event   │────→│  Stream  │────→│  Serving │
│  Log     │     │ Processor│     │  Layer   │
│ (Kafka)  │     │ (Flink)  │     │          │
└──────────┘     └──────────┘     └──────────┘

Reprocessing: Replay events from log
```

## ETL (Extract, Transform, Load)

### ETL Pipeline
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Extract │────→│Transform │────→│  Load    │
│          │     │          │     │          │
│ Databases│     │ Clean    │     │ Data     │
│ APIs     │     │ Aggregate│     │ Warehouse│
│ Files    │     │ Enrich   │     │          │
└──────────┘     └──────────┘     └──────────┘
```

### ETL vs ELT

| Aspect | ETL | ELT |
|--------|-----|-----|
| Order | Extract → Transform → Load | Extract → Load → Transform |
| Where transform happens | Before loading (ETL server) | After loading (in data warehouse) |
| Best for | Small data, complex transforms | Big data, cloud warehouses |
| Tools | Informatica, Talend | dbt, Spark, SQL in warehouse |

### Modern Data Pipeline
```
Sources → Ingestion → Storage → Processing → Serving → Consumers

Sources: DBs, APIs, files, streams
Ingestion: Kafka, Kinesis, Airbyte
Storage: S3, HDFS, Data Lake
Processing: Spark, Flink, dbt
Serving: Data Warehouse, OLAP DB
Consumers: BI tools, ML, APIs
```

## Data Lakes vs Data Warehouses vs Data Marts

### Data Lake
Stores raw data in its native format.

```
┌─────────────────────────────────────┐
│           Data Lake                  │
│  ┌──────┐ ┌──────┐ ┌──────┐       │
│  │Raw   │ │JSON  │ │CSV   │       │
│  │Events│ │Logs  │ │Files │       │
│  └──────┘ └──────┘ └──────┘       │
│  Schema-on-read (apply when query)  │
└─────────────────────────────────────┘
Storage: S3, HDFS, Azure Data Lake
```

**Characteristics**:
- Stores all data (structured, semi-structured, unstructured)
- Schema-on-read
- Low cost storage
- Requires governance (data swamp risk)

### Data Warehouse
Stores processed, structured data optimized for queries.

```
┌─────────────────────────────────────┐
│        Data Warehouse               │
│  ┌──────────┐ ┌──────────┐        │
│  │Sales Fact│ │Customer  │        │
│  │Table     │ │Dimension │        │
│  └──────────┘ └──────────┘        │
│  Schema-on-write (structured)       │
│  Optimized for analytical queries   │
└─────────────────────────────────────┘
Storage: Snowflake, BigQuery, Redshift
```

**Characteristics**:
- Structured, cleaned data
- Schema-on-write
- Optimized for complex queries
- Higher cost, better performance

### Data Mart
Subset of data warehouse for specific department.

```
Data Warehouse
├── Marketing Data Mart (campaigns, leads)
├── Sales Data Mart (revenue, pipeline)
└── Engineering Data Mart (incidents, deployments)
```

### Comparison

| Aspect | Data Lake | Data Warehouse | Data Mart |
|--------|-----------|---------------|-----------|
| Data type | All types | Structured | Structured |
| Schema | On-read | On-write | On-write |
| Users | Data engineers | Analysts | Business teams |
| Cost | Low | High | Medium |
| Query speed | Slow | Fast | Fastest |
| Flexibility | High | Low | Lowest |

## Data Warehouse Schema Design

### Star Schema
```
         ┌──────────┐
         │  Date    │
         │ Dimension│
         └────┬─────┘
              │
┌──────────┐  │  ┌──────────┐
│ Product  │──┼──│ Customer │
│Dimension │  │  │Dimension │
└────┬─────┘  │  └────┬─────┘
     │        │       │
     └────────┼───────┘
              ▼
        ┌──────────┐
        │  Sales   │
        │ Fact     │
        │ Table    │
        └──────────┘
```

- One fact table in center
- Dimension tables around it
- Simple, fast queries
- Denormalized (redundancy)

### Snowflake Schema
```
Dimension tables are normalized

Product Dimension:
Products → Categories → Departments

More storage efficient, but more JOINs needed
```

## Column-Oriented Storage

### Row vs Column Storage

```
Row-oriented (PostgreSQL, MySQL):
Row 1: [1, "Alice", 25, "Engineer"]
Row 2: [2, "Bob", 30, "Designer"]
Row 3: [3, "Charlie", 35, "Manager"]

Column-oriented (ClickHouse, Parquet):
IDs:      [1, 2, 3]
Names:    ["Alice", "Bob", "Charlie"]
Ages:     [25, 30, 35]
Roles:    ["Engineer", "Designer", "Manager"]
```

### When to Use Column Storage

| Scenario | Row Store | Column Store |
|----------|-----------|--------------|
| OLTP (transactions) | ✅ | ❌ |
| OLAP (analytics) | ❌ | ✅ |
| SELECT * queries | ✅ | ❌ |
| SELECT AVG(age) | ❌ | ✅ (reads one column) |
| Frequent updates | ✅ | ❌ |
| Compression | Low | High (same type) |

**Column stores**: ClickHouse, Apache Parquet, Amazon Redshift, Google BigQuery

## Stream Processing Concepts

### Windowing

```
Tumbling Window (non-overlapping):
|---Window 1---|---Window 2---|---Window 3---|
0              5              10             15

Sliding Window (overlapping):
|---Window 1---|
    |---Window 2---|
        |---Window 3---|
0    2    4    6    8

Session Window (activity-based):
|---Session 1---|     |---Session 2---|
active    inactive   active    inactive
```

### Event Time vs Processing Time

```
Event Time: When the event actually occurred
Processing Time: When the event is processed

Problem: Events may arrive out of order

Event at T=100 → arrives at processing T=105
Event at T=101 → arrives at processing T=103 (network delay)

Solution: Watermarks (allow some lateness)
```

### Exactly-Once Semantics in Streaming

```
Challenge: What if consumer crashes after processing but before ACK?

Solution 1: Idempotent writes
  - Write with unique ID, skip duplicates

Solution 2: Transactional outbox
  - Write to DB + outbox in same transaction
  - Read outbox, publish to stream, mark as sent

Solution 3: Kafka transactions
  - Atomic read-process-write across partitions
```

## Real-World Data Architectures

### Netflix Data Pipeline
```
Events → Kafka → Flink (real-time) → Serving (Cassandra)
                → Spark (batch) → Data Warehouse (Redshift)
                → S3 (data lake)
```

### Uber Data Architecture
```
Ride Events → Kafka → Real-time (Flink) → Matching, Pricing
                   → Batch (Spark) → Analytics, ML Training
                   → Data Lake (S3) → Ad-hoc queries
```

### LinkedIn Data Infrastructure
```
Activity → Kafka → Samza (stream processing) → Voldemort (serving)
                → Hadoop (batch) → Data Warehouse
```

## Interview Tips

1. **Identify data characteristics** — Volume, velocity, variety
2. **Choose batch vs stream** — "Do we need real-time or is daily OK?"
3. **Mention specific technologies** — "Kafka for ingestion, Spark for batch, Flink for stream"
4. **Discuss data modeling** — "Star schema for analytics, document model for OLTP"
5. **Consider data lifecycle** — "Raw → Processed → Aggregated → Archived"
6. **Think about cost** — "S3 for cold data, SSD for hot data"
7. **Include monitoring** — "Track pipeline lag, data freshness, error rates"
8. **Discuss governance** — "Data catalog, lineage tracking, access control"

## Common Mistakes

- ❌ Using batch when real-time is needed (or vice versa)
- ❌ Not considering data ordering in streaming
- ❌ Ignoring late-arriving events
- ❌ Using data lake without governance (data swamp)
- ❌ Not planning for data growth
- ❌ Mixing OLTP and OLAP on same database

## Cross-References

- [Database Design](./database-design.md) — OLTP database selection
- [Messaging Systems](./messaging-systems.md) — Kafka, event streaming
- [Scalability](./scalability.md) — Scaling data systems
- [Capacity Planning](./capacity-planning.md) — Storage estimation
- [Monitoring](./monitoring-observability.md) — Pipeline monitoring
