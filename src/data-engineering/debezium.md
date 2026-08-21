# Debezium (Change Data Capture)

Debezium is an open-source platform for Change Data Capture (CDC), originally developed at Red Hat and donated to the CNCF (becoming a graduated project in 2024). Debezium reads change events from databases (inserts, updates, deletes) and streams them to Kafka topics, enabling real-time data pipelines without modifying the source applications. This page covers the architecture, the per-database CDC mechanisms, the connector ecosystem, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Source Database (PostgreSQL, MySQL, MongoDB, etc.)          │
│  - WAL / binlog / change stream                             │
└─────────────────────────────────────────────────────────────┘
        │
        │ CDC events (inserts, updates, deletes)
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Debezium Source Connector (running in Kafka Connect)       │
│  - Reads from database's replication log                    │
│  - Translates to Kafka messages                             │
│  - Tracks position (offset)                                 │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Kafka Topics                                                │
│  - One topic per database table                              │
│  - Each message = one row change                            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Downstream consumers                                       │
│  - Sink to Elasticsearch (search index)                     │
│  - Sink to ClickHouse (analytics)                           │
│  - Sink to Snowflake (data warehouse)                      │
│  - Stream processing (Kafka Streams, Flink)                │
└─────────────────────────────────────────────────────────────┘
```

Debezium is built on Kafka Connect; it's a set of source connectors for various databases. The connectors read from the database's native CDC mechanism.

## CDC Mechanisms per Database

### PostgreSQL: Logical Replication

PostgreSQL writes a Write-Ahead Log (WAL) for crash recovery. Debezium uses PostgreSQL's "logical replication" feature to subscribe to row-level changes:

```sql
-- Enable logical replication in postgresql.conf
wal_level = logical
max_wal_senders = 4
max_replication_slots = 4

-- Create a replication slot for Debezium
SELECT * FROM pg_create_logical_replication_slot('debezium', 'pgoutput');

-- Create a publication for the tables
CREATE PUBLICATION debezium_publication FOR TABLE orders, customers;
```

Debezium connects as a replication subscriber, receives the row change events, and produces them to Kafka.

### MySQL: Binary Log (binlog)

MySQL's binlog records every row change for replication. Debezium parses the binlog directly:

```sql
-- Enable row-based binlog in my.cnf
[mysqld]
log_bin = mysql-bin
binlog_format = ROW
binlog_row_image = FULL

-- Create a user with replication privileges
CREATE USER 'debezium'@'%' IDENTIFIED BY '...';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'debezium'@'%';
GRANT SELECT ON mydb.* TO 'debezium'@'%';
```

Debezium acts as a MySQL replication slave, receives the binlog events, and translates them.

### MongoDB: Change Streams

MongoDB's change streams API exposes database changes since MongoDB 3.6:

```javascript
// Enable replica set (required for change streams)
rs.initiate()

// Watch a collection for changes
const changeStream = db.collection('orders').watch();
changeStream.on('change', (next) => {
  console.log('Change:', next);
});
```

Debezium uses this API; the change stream events are translated to Kafka messages.

### SQL Server: Change Tracking or CDC

SQL Server has two CDC options:
- **Change Tracking**: lightweight, only tracks that a row changed (not the values).
- **CDC (Change Data Capture)**: heavier, captures the row values.

Debezium uses CDC, which requires enabling per-table:

```sql
-- Enable CDC for the database
EXEC sys.sp_cdc_enable_db;

-- Enable CDC for a table
EXEC sys.sp_cdc_enable_table
    @source_schema = 'dbo',
    @source_name = 'orders',
    @role_name = 'debezium';
```

### Oracle: LogMiner (commercial)

Oracle's CDC requires LogMiner, an Oracle feature. Debezium's Oracle connector is part of the commercial Debezium distribution; the open-source version uses XStream (which requires an Oracle license).

## The Event Format

A Debezium event is an Envelope record:

```json
{
  "before": {
    "id": 123,
    "customer_id": "alice",
    "amount": 99.99,
    "status": "pending"
  },
  "after": {
    "id": 123,
    "customer_id": "alice",
    "amount": 99.99,
    "status": "shipped"
  },
  "source": {
    "version": "2.4.0",
    "connector": "postgresql",
    "name": "mydb",
    "db": "mydb",
    "ts_usec": 1692616800000000,
    "txId": 12345,
    "lsn": 67890,
    "schema": "public",
    "table": "orders",
    "ts_ms": 1692616800000
  },
  "op": "u",  // c=create, u=update, d=delete, r=snapshot
  "ts_ms": 1692616800123,
  "transaction": {
    "id": "txn-1",
    "total_order": 5,
    "data_collection_order": 1
  }
}
```

Key fields:
- `before`: the row's state before the change (null for inserts).
- `after`: the row's state after the change (null for deletes).
- `source`: metadata about the source database, transaction, and log position.
- `op`: the operation type (c/u/d/r).
- `transaction`: for transaction-bound events, the transaction ID and order.

## Initial Snapshots

When a Debezium connector starts for the first time, it does an "initial snapshot" — reads the entire table and produces one event per row:

```text
1. Debezium queries the database for current rows.
2. For each row, produces a "snapshot" event (op=r, for "read").
3. After the snapshot, switches to streaming mode (op=c/u/d).
```

The snapshot ensures the Kafka topic has the full current state, not just changes since the connector started.

Snapshots are expensive (full table scan, one Kafka message per row). For a 1B-row table, the snapshot can take hours.

## Production Patterns

### Database → Search Index

```text
PostgreSQL → Debezium → Kafka → Elasticsearch Sink → Elasticsearch
```

When a row changes in PostgreSQL, Debezium produces a Kafka message; the Elasticsearch sink updates the search index. Users see new data in search results within seconds.

### Database → Analytics Warehouse

```text
PostgreSQL → Debezium → Kafka → S3 Sink → Snowflake (external table)
```

Database changes are exported to S3 as Parquet files. Snowflake's external table reads them as a real-time view of the source database.

### Stream Processing

```text
PostgreSQL → Debezium → Kafka → Flink (enrichment, aggregation) → Kafka → Sink
```

Flink reads from Kafka, enriches the data with reference data, aggregates, and writes back to Kafka for downstream consumers.

### Multi-Region Replication

```text
US-East PostgreSQL → Debezium → Kafka → US-West PostgreSQL (via JDBC Sink)
```

US-East is the source of truth; US-West is a read replica kept in sync via CDC. Reads are local; writes go to US-East.

## Common Pitfalls

1. **Forgetting that Debezium reads from the replication log, not the database.** A long-running transaction fills the log; Debezium falls behind. Set `max_slot_wal_keep_size` to limit retention.

2. **Forgetting that schema changes break Debezium.** Adding a column to a table requires the new column to be in the replication slot's output. PostgreSQL needs the slot's `include_generated_columns` updated.

3. **Forgetting that initial snapshots are expensive.** A 1B-row table snapshot produces 1B Kafka messages. Plan disk and bandwidth.

4. **Forgetting that Debezium is not transactional across tables.** Multi-table transactions may appear as separate Kafka messages in different topics. Use the `transaction` metadata to correlate.

5. **Forgetting to monitor replication slot lag.** A PostgreSQL replication slot that Debezium doesn't consume from grows the WAL; eventually the disk fills. Monitor `pg_replication_slots` and Debezium's lag metrics.

6. **Forgetting that Debezium needs the source DB's permission.** PostgreSQL requires `REPLICATION` privilege; MySQL requires `REPLICATION SLAVE`. Production DBAs may resist granting these.

## References

- [Debezium documentation](https://debezium.io/documentation/)
- [Debezium GitHub repository](https://github.com/debezium/debezium)
- [Debezium Connector for PostgreSQL](https://debezium.io/documentation/reference/stable/connectors/postgresql.html)
- [Debezium Connector for MySQL](https://debezium.io/documentation/reference/stable/connectors/mysql.html)
- [PostgreSQL logical replication documentation](https://www.postgresql.org/docs/current/logical-replication.html)
- [MySQL binary log documentation](https://dev.mysql.com/doc/refman/8.0/en/binary-log.html)
- [Debezium: Practical patterns (Red Hat blog)](https://www.redhat.com/en/topics/data-storage/change-data-capture)
- [Debezium + Kafka Connect tutorial](https://debezium.io/documentation/reference/tutorial/)
