# Data Engineering Interview Questions

## Fundamentals

**Q: What is the difference between ETL and ELT?**
A: ETL transforms data before loading into the warehouse (traditional). ELT loads raw data first, then transforms within the warehouse (modern, leverages warehouse compute). ELT is preferred with cloud warehouses (BigQuery, Snowflake) that can scale compute independently.

**Q: When would you use a data lake vs a data warehouse?**
A: Warehouse for structured, queryable data used by analysts (SQL, dashboards). Lake for raw data of all types (logs, images, JSON) used by data scientists (ML, exploration). Lakehouse combines both.

## Spark

**Q: What is an RDD in Spark?**
A: Resilient Distributed Dataset — an immutable, partitioned collection of elements that can be operated on in parallel. "Resilient" because Spark can recompute lost partitions using the lineage (DAG of transformations). RDDs are the low-level API; DataFrames/Datasets are preferred.

**Q: What is the difference between `map` and `flatMap`?**
A: `map` applies a function to each element, returning one output per input. `flatMap` applies a function that can return zero or more outputs per input (flattens the result). Example: `flatMap(line => line.split(" "))` produces one word per output.

**Q: Explain narrow vs wide transformations in Spark.**
A: Narrow: each input partition maps to at most one output partition (map, filter, union). Wide: requires shuffling data across partitions (groupBy, join, repartition). Wide transformations are expensive because they involve network I/O.

## Kafka

**Q: How does Kafka achieve high throughput?**
A: (1) Sequential I/O (append-only log), (2) batching messages, (3) zero-copy transfer (sendfile), (4) compression, (5) partitioning for parallelism, (6) page cache utilization.

**Q: What is a consumer group in Kafka?**
A: A group of consumers that cooperatively consume a topic. Each partition is assigned to exactly one consumer in the group. If a consumer fails, its partitions are rebalanced to others. Multiple consumer groups can read the same topic independently.

**Q: How does Kafka achieve exactly-once semantics?**
A: (1) Idempotent producer (deduplicates by sequence number), (2) transactional API (atomic writes across partitions), (3) consumer reads committed messages only (`isolation.level=read_committed`).

## Airflow

**Q: What is a DAG in Airflow?**
A: Directed Acyclic Graph — a workflow of tasks with dependencies. Defined in Python. Tasks are nodes, dependencies are edges. Airflow schedules DAG runs and executes tasks in dependency order.

**Q: How do you handle task failures in Airflow?**
A: (1) `retries` parameter (auto-retry N times), (2) `retry_delay` (wait between retries), (3) `email_on_failure` (alert), (4) `on_failure_callback` (custom handler), (5) `depends_on_past` (sequential execution), (6) SLA monitoring.

## References

- [Fundamentals of Data Engineering](https://www.oreilly.com/library/view/fundamentals-of-data/9781098108298/)
- [Spark: The Definitive Guide](https://www.oreilly.com/library/view/spark-the-definitive/9781491912201/)
