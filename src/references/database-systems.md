# Database Systems Reference Library

This page is a verified index of primary sources for database management systems: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Relational engines, analytical and columnar systems, storage engines, lakehouse table formats, and a two-track learning path from CMU 15-445 to reading query optimizers and LSM internals.

**68 entries** across 8 categories, plus **53 education & reference-implementation resources** (23 basic / 30 advanced), plus **14 video resources** and **6 conference sources**.

Every link HTTP-verified on **2026-10-07**.

> dev.mysql.com, IBM Docs and the ACM Digital Library return 403 to automated clients; both load normally in a browser.

## Contents

- [1. Relational databases — open source](#1-relational-databases--open-source) — 9
- [2. Relational databases — commercial](#2-relational-databases--commercial) — 4
- [3. Analytical & columnar engines](#3-analytical--columnar-engines) — 8
- [4. Storage engines & embedded key-value stores](#4-storage-engines--embedded-key-value-stores) — 7
- [5. Lakehouse table formats](#5-lakehouse-table-formats) — 3
- [6. Reference material & tooling](#6-reference-material--tooling) — 6
- [7. Query engines, streaming and the surrounding ecosystem](#7-query-engines-streaming-and-the-surrounding-ecosystem) — 10
- [8. Research papers & open-access literature](#8-research-papers--open-access-literature) — 21
- [Education & reference implementations](#education--reference-implementations) — 53 (23 basic / 30 advanced)
- [Video courses, channels & talks](#video-courses-channels--talks) — 14
- [Conference videos, notes & archives](#conference-videos-notes--archives) — 6


## 1. Relational databases — open source

### PostgreSQL

- **Docs:** [postgresql.org/docs/current](https://www.postgresql.org/docs/current/)
- **Developer / API:** [postgresql.org/docs/current/libpq.html](https://www.postgresql.org/docs/current/libpq.html)
- **Source:** [git.postgresql.org/gitweb/?p=postgresql.git](https://git.postgresql.org/gitweb/?p=postgresql.git)
- **SDKs & repos:** libpq, psycopg, pgx, JDBC; extensions via the contrib tree
- **Downloadable / offline:** Full manual as PDF and HTML tarball per version: [postgresql.org/docs/manuals](https://www.postgresql.org/docs/manuals/)
- *Note:* The documentation is the benchmark the rest of the industry is measured against. The internals chapters and the source README files are real architecture documentation.

### PostgreSQL Wiki

- **Docs:** [wiki.postgresql.org/wiki/Main_Page](https://wiki.postgresql.org/wiki/Main_Page)
- **Developer / API:** [wiki.postgresql.org/wiki/Developer_FAQ](https://wiki.postgresql.org/wiki/Developer_FAQ)
- **SDKs & repos:** Developer FAQ, todo lists, performance guidance
- **Downloadable / offline:** Wiki
- *Note:* The Developer FAQ is the entry point for reading the source.

### MySQL

- **Docs:** [dev.mysql.com/doc](https://dev.mysql.com/doc/)
- **Developer / API:** [dev.mysql.com/doc/refman/8.4/en](https://dev.mysql.com/doc/refman/8.4/en/)
- **Source:** [github.com/mysql/mysql-server](https://github.com/mysql/mysql-server)
- **SDKs & repos:** Connector/J, Connector/Python, X DevAPI
- **Downloadable / offline:** Reference Manual downloadable as PDF, EPUB and HTML per version
- *Note:* Site 403s to bots; fine in a browser. The InnoDB chapters are the valuable part.

### MariaDB

- **Docs:** [mariadb.com/kb/en/documentation](https://mariadb.com/kb/en/documentation/)
- **Developer / API:** [mariadb.com/kb/en/connectors](https://mariadb.com/kb/en/connectors/)
- **Source:** [github.com/MariaDB/server](https://github.com/MariaDB/server)
- **SDKs & repos:** Multiple storage engines: InnoDB, Aria, ColumnStore, MyRocks
- **Downloadable / offline:** Knowledge Base, exportable
- *Note:* The MySQL fork with the more open governance. Storage-engine variety makes it instructive.

### SQLite

- **Docs:** [sqlite.org/docs.html](https://www.sqlite.org/docs.html)
- **Developer / API:** [sqlite.org/c3ref/intro.html](https://www.sqlite.org/c3ref/intro.html)
- **Source:** [github.com/sqlite/sqlite](https://github.com/sqlite/sqlite)
- **SDKs & repos:** Amalgamation build — the entire database as one C file
- **Downloadable / offline:** Complete docs downloadable as a single archive; source amalgamation too
- *Note:* The most deployed database in the world and among the most readable. See `arch.html` for the architecture overview and `whyc.html` for the design rationale.

### SQLite architecture

- **Docs:** [sqlite.org/arch.html](https://www.sqlite.org/arch.html)
- **Developer / API:** [sqlite.org/whyc.html](https://www.sqlite.org/whyc.html)
- **Source:** [github.com/sqlite/sqlite](https://github.com/sqlite/sqlite)
- **SDKs & repos:** VDBE, pager, B-tree — each layer documented separately
- **Downloadable / offline:** Online
- *Note:* Read `arch.html` before the source. It saves days.

### CockroachDB

- **Docs:** [cockroachlabs.com/docs](https://www.cockroachlabs.com/docs/)
- **Developer / API:** [cockroachlabs.com/docs/…](https://www.cockroachlabs.com/docs/stable/sql-feature-support)
- **Source:** [github.com/cockroachdb/cockroach](https://github.com/cockroachdb/cockroach)
- **SDKs & repos:** PostgreSQL wire-compatible; Raft-based distribution
- **Downloadable / offline:** Docs site + in-repo RFCs
- *Note:* The `docs/RFCS/` directory in the repo is an exceptional record of distributed-SQL design decisions.

### YugabyteDB

- **Docs:** [docs.yugabyte.com](https://docs.yugabyte.com/)
- **Developer / API:** [docs.yugabyte.com/preview/api](https://docs.yugabyte.com/preview/api/)
- **Source:** [github.com/yugabyte/yugabyte-db](https://github.com/yugabyte/yugabyte-db)
- **SDKs & repos:** PostgreSQL-compatible SQL layer over a distributed store; Cassandra-compatible API too
- **Downloadable / offline:** Docs site
- *Note:* Reuses the actual PostgreSQL query layer — interesting as an architectural choice.

### TiDB

- **Docs:** [docs.pingcap.com/tidb/stable](https://docs.pingcap.com/tidb/stable)
- **Developer / API:** [docs.pingcap.com/tidb/…](https://docs.pingcap.com/tidb/stable/dev-guide-overview)
- **Source:** [github.com/pingcap/tidb](https://github.com/pingcap/tidb)
- **SDKs & repos:** MySQL-compatible; TiKV storage layer is a separate readable project
- **Downloadable / offline:** Docs site; PingCAP publishes extensive design blogs
- *Note:* PingCAP's engineering writing, and `awesome-database-learning`, are among the best free distributed-database education.


## 2. Relational databases — commercial

### Oracle Database

- **Docs:** [docs.oracle.com/en/database](https://docs.oracle.com/en/database/)
- **Developer / API:** [oracle.com/database/technologies](https://www.oracle.com/database/technologies/)
- **SDKs & repos:** OCI, JDBC, ODP.NET, python-oracledb
- **Downloadable / offline:** Full documentation library downloadable per release
- *Note:* The Concepts guide is genuinely good and free; worth reading regardless of what you run.

### Microsoft SQL Server

- **Docs:** [learn.microsoft.com/en-us/sql](https://learn.microsoft.com/en-us/sql/)
- **Developer / API:** [learn.microsoft.com/en-us/sql/connect](https://learn.microsoft.com/en-us/sql/connect/)
- **Source:** [github.com/MicrosoftDocs/sql-docs](https://github.com/MicrosoftDocs/sql-docs)
- **SDKs & repos:** Drivers for most languages; T-SQL reference
- **Downloadable / offline:** Microsoft Learn offers offline/PDF export
- *Note:* Documentation is open-source on GitHub — you can file issues against it.

### Google Cloud Spanner

- **Docs:** [cloud.google.com/spanner/docs](https://cloud.google.com/spanner/docs)
- **Developer / API:** [cloud.google.com/spanner/docs/reference/rest](https://cloud.google.com/spanner/docs/reference/rest)
- **SDKs & repos:** Client libraries in all major languages
- **Downloadable / offline:** Docs site; the Spanner papers are free PDFs
- *Note:* Read the 2012 OSDI paper and the 2017 SIGMOD paper together — external consistency via TrueTime is the central idea.

### IBM Db2

- **Docs:** [ibm.com/docs/en/db2](https://www.ibm.com/docs/en/db2)
- **SDKs & repos:** CLI, JDBC, pureQuery
- **Downloadable / offline:** IBM Docs supports PDF export
- *Note:* IBM Docs 403s to automated clients; loads normally in a browser.


## 3. Analytical & columnar engines

### DuckDB

- **Docs:** [duckdb.org/docs](https://duckdb.org/docs/)
- **Developer / API:** [duckdb.org/docs/stable/clients/overview](https://duckdb.org/docs/stable/clients/overview)
- **Source:** [github.com/duckdb/duckdb](https://github.com/duckdb/duckdb)
- **SDKs & repos:** In-process analytics; Python, R, C++, WASM, CLI
- **Downloadable / offline:** Docs downloadable; single-binary distribution
- *Note:* The SQLite of analytics. Also an unusually readable modern vectorized engine.

### ClickHouse

- **Docs:** [clickhouse.com/docs](https://clickhouse.com/docs)
- **Developer / API:** [clickhouse.com/docs/en/interfaces](https://clickhouse.com/docs/en/interfaces)
- **Source:** [github.com/ClickHouse/ClickHouse](https://github.com/ClickHouse/ClickHouse)
- **SDKs & repos:** HTTP and native protocols; clients everywhere
- **Downloadable / offline:** Docs site; repo cloneable
- *Note:* Extremely fast columnar OLAP. The source is a good study of vectorized execution and compression.

### Apache Druid

- **Docs:** [druid.apache.org/docs/latest](https://druid.apache.org/docs/latest/)
- **Developer / API:** [druid.apache.org/docs/latest/api-reference](https://druid.apache.org/docs/latest/api-reference/)
- **Source:** [github.com/apache/druid](https://github.com/apache/druid)
- **SDKs & repos:** Real-time analytics with sub-second queries over streams
- **Downloadable / offline:** Docs site

### Apache Pinot

- **Docs:** [docs.pinot.apache.org](https://docs.pinot.apache.org/)
- **Developer / API:** [docs.pinot.apache.org/users/api](https://docs.pinot.apache.org/users/api)
- **Source:** [github.com/apache/pinot](https://github.com/apache/pinot)
- **SDKs & repos:** Low-latency OLAP serving, LinkedIn origin
- **Downloadable / offline:** Docs site

### Snowflake

- **Docs:** [docs.snowflake.com](https://docs.snowflake.com/)
- **Developer / API:** [docs.snowflake.com/en/developer](https://docs.snowflake.com/en/developer)
- **SDKs & repos:** Snowpark, connectors, SQL REST API
- **Downloadable / offline:** Docs site
- *Note:* The 2016 SIGMOD paper on the architecture is the best explanation of storage/compute separation.

### Google BigQuery

- **Docs:** [cloud.google.com/bigquery/docs](https://cloud.google.com/bigquery/docs)
- **Developer / API:** [cloud.google.com/bigquery/docs/reference](https://cloud.google.com/bigquery/docs/reference)
- **SDKs & repos:** Client libraries; Storage Read API
- **Downloadable / offline:** Docs site
- *Note:* Dremel's descendant; the Dremel paper is still the key reading.

### Amazon Redshift

- **Docs:** [docs.aws.amazon.com/redshift](https://docs.aws.amazon.com/redshift/)
- **Developer / API:** [docs.aws.amazon.com/redshift/…](https://docs.aws.amazon.com/redshift/latest/APIReference/)
- **SDKs & repos:** JDBC/ODBC, Data API
- **Downloadable / offline:** AWS docs downloadable as PDF per guide

### Databricks

- **Docs:** [docs.databricks.com](https://docs.databricks.com/)
- **Developer / API:** [docs.databricks.com/api/workspace/introduction](https://docs.databricks.com/api/workspace/introduction)
- **SDKs & repos:** Spark, Delta Lake, Unity Catalog
- **Downloadable / offline:** Docs site


## 4. Storage engines & embedded key-value stores

### RocksDB

- **Docs:** [rocksdb.org/docs/getting-started.html](https://rocksdb.org/docs/getting-started.html)
- **Developer / API:** [github.com/facebook/rocksdb/wiki](https://github.com/facebook/rocksdb/wiki)
- **Source:** [github.com/facebook/rocksdb](https://github.com/facebook/rocksdb)
- **SDKs & repos:** C++, Java, Rust, Go bindings; used inside dozens of other databases
- **Downloadable / offline:** Wiki is the real documentation and it is extensive
- *Note:* The LSM-tree implementation most systems build on. The wiki's tuning guide is a distributed-systems education in itself.

### LevelDB

- **Docs:** [github.com/google/leveldb](https://github.com/google/leveldb)
- **Source:** [github.com/google/leveldb](https://github.com/google/leveldb)
- **SDKs & repos:** The original compact LSM store from Google
- **Downloadable / offline:** In-repo docs
- *Note:* Small enough to read completely. Read before RocksDB.

### LMDB

- **Docs:** [lmdb.tech/doc](http://www.lmdb.tech/doc/)
- **Source:** [github.com/LMDB/lmdb](https://github.com/LMDB/lmdb)
- **SDKs & repos:** Memory-mapped B+tree with MVCC, single writer
- **Downloadable / offline:** Doxygen docs
- *Note:* The counterpoint to LSM trees. ~10k lines, copy-on-write B+tree.

### WiredTiger

- **Docs:** [source.wiredtiger.com](https://source.wiredtiger.com/)
- **Source:** [github.com/wiredtiger/wiredtiger](https://github.com/wiredtiger/wiredtiger)
- **SDKs & repos:** MongoDB's storage engine; both B-tree and LSM modes
- **Downloadable / offline:** Docs site

### Apache Arrow

- **Docs:** [arrow.apache.org/docs](https://arrow.apache.org/docs/)
- **Developer / API:** [arrow.apache.org/docs/format/Columnar.html](https://arrow.apache.org/docs/format/Columnar.html)
- **Source:** [github.com/apache/arrow](https://github.com/apache/arrow)
- **SDKs & repos:** In-memory columnar standard; implementations in 12+ languages
- **Downloadable / offline:** Docs site; format spec separately
- *Note:* The columnar format spec is short and worth reading directly — it underpins most modern analytics.

### Apache Parquet

- **Docs:** [parquet.apache.org/docs](https://parquet.apache.org/docs/)
- **Developer / API:** [parquet.apache.org/docs/file-format](https://parquet.apache.org/docs/file-format/)
- **Source:** [github.com/apache/parquet-format](https://github.com/apache/parquet-format)
- **SDKs & repos:** The on-disk columnar format; encodings and statistics documented in the spec
- **Downloadable / offline:** Spec in-repo
- *Note:* Read the encoding section — dictionary and RLE encoding explain most of the compression wins.

### Apache ORC

- **Docs:** [orc.apache.org/docs](https://orc.apache.org/docs/)
- **Developer / API:** [orc.apache.org/specification](https://orc.apache.org/specification/)
- **Source:** [github.com/apache/orc](https://github.com/apache/orc)
- **SDKs & repos:** Columnar format from the Hive lineage
- **Downloadable / offline:** Spec online


## 5. Lakehouse table formats

### Apache Iceberg

- **Docs:** [iceberg.apache.org/docs/latest](https://iceberg.apache.org/docs/latest/)
- **Developer / API:** [iceberg.apache.org/spec](https://iceberg.apache.org/spec/)
- **Source:** [github.com/apache/iceberg](https://github.com/apache/iceberg)
- **SDKs & repos:** Java, Python, Rust, Go implementations; REST catalog spec
- **Downloadable / offline:** Table spec is a single readable document
- *Note:* Currently the de facto open table format. Read the spec — snapshot isolation over object storage is the whole trick.

### Delta Lake

- **Docs:** [docs.delta.io/latest/index.html](https://docs.delta.io/latest/index.html)
- **Developer / API:** [github.com/delta-io/…](https://github.com/delta-io/delta/blob/master/PROTOCOL.md)
- **Source:** [github.com/delta-io/delta](https://github.com/delta-io/delta)
- **SDKs & repos:** Spark-native plus delta-rs for Rust/Python
- **Downloadable / offline:** Protocol document in-repo
- *Note:* The transaction log protocol is the thing to read.

### Apache Hudi

- **Docs:** [hudi.apache.org/docs/overview](https://hudi.apache.org/docs/overview)
- **Developer / API:** [hudi.apache.org/docs/quick-start-guide](https://hudi.apache.org/docs/quick-start-guide)
- **Source:** [github.com/apache/hudi](https://github.com/apache/hudi)
- **SDKs & repos:** Copy-on-write and merge-on-read tables
- **Downloadable / offline:** Docs site


## 6. Reference material & tooling

### Use The Index, Luke

- **Docs:** [use-the-index-luke.com](https://use-the-index-luke.com/)
- **SDKs & repos:** SQL indexing explained for developers, across five database engines
- **Downloadable / offline:** Free online; book available
- *Note:* The single most useful practical resource on indexing. Most query performance problems end here.

### Modern SQL

- **Docs:** [modern-sql.com](https://modern-sql.com/)
- **SDKs & repos:** What SQL has gained since 1992 — window functions, CTEs, JSON, MATCH_RECOGNIZE
- **Downloadable / offline:** Online
- *Note:* Same author as Use The Index, Luke. Corrects the assumption that SQL stopped evolving.

### PostgreSQL Exercises

- **Docs:** [pgexercises.com](https://pgexercises.com/)
- **SDKs & repos:** Graded SQL exercises against a real schema
- **Downloadable / offline:** Online

### explain.depesz.com

- **Docs:** [explain.depesz.com](https://explain.depesz.com/)
- **SDKs & repos:** Makes PostgreSQL EXPLAIN output readable
- **Downloadable / offline:** Web tool

### SQL Style Guide

- **Docs:** [sqlstyle.guide](https://www.sqlstyle.guide/)
- **SDKs & repos:** Consistent SQL formatting conventions
- **Downloadable / offline:** Online

### DB-Engines Ranking

- **Docs:** [db-engines.com/en/ranking](https://db-engines.com/en/ranking)
- **SDKs & repos:** Popularity tracking across 400+ systems
- **Downloadable / offline:** Web
- *Note:* Methodology is popularity-based, not technical. Useful for trends, not for selection.


## 7. Query engines, streaming and the surrounding ecosystem

### Apache DataFusion

- **Docs:** [datafusion.apache.org](https://datafusion.apache.org/)
- **Developer / API:** [docs.rs/datafusion](https://docs.rs/datafusion)
- **Source:** [github.com/apache/datafusion](https://github.com/apache/datafusion)
- **SDKs & repos:** Extensible query engine in Rust built on Arrow; used as a component inside other databases
- **Downloadable / offline:** Docs site
- *Note:* The easiest modern query engine to read and embed. Good entry point to vectorized execution in Rust.

### Apache Calcite

- **Docs:** [calcite.apache.org/docs](https://calcite.apache.org/docs/)
- **Developer / API:** [calcite.apache.org/javadocAggregate](https://calcite.apache.org/javadocAggregate/)
- **Source:** [github.com/apache/calcite](https://github.com/apache/calcite)
- **SDKs & repos:** SQL parser, planner and cost-based optimizer as a reusable library
- **Downloadable / offline:** Docs site
- *Note:* Used by Flink, Druid, Hive and others. The rule-based optimizer is the part worth studying.

### Trino

- **Docs:** [trino.io/docs/current](https://trino.io/docs/current/)
- **Developer / API:** [trino.io/docs/current/develop.html](https://trino.io/docs/current/develop.html)
- **Source:** [github.com/trinodb/trino](https://github.com/trinodb/trino)
- **SDKs & repos:** Distributed SQL over many data sources; connector SPI
- **Downloadable / offline:** Docs per version
- *Note:* The Presto fork that most of the community moved to. The connector architecture is well documented.

### Polars

- **Docs:** [docs.pola.rs](https://docs.pola.rs/)
- **Developer / API:** [docs.pola.rs/api/python/stable/reference](https://docs.pola.rs/api/python/stable/reference/)
- **Source:** [github.com/pola-rs/polars](https://github.com/pola-rs/polars)
- **SDKs & repos:** Arrow-backed DataFrame library in Rust with Python bindings; lazy query optimization
- **Downloadable / offline:** Docs site
- *Note:* Shows query-optimizer ideas applied to DataFrames. Faster than pandas and architecturally more interesting.

### Materialize

- **Docs:** [materialize.com/docs](https://materialize.com/docs/)
- **Source:** [github.com/MaterializeInc/materialize](https://github.com/MaterializeInc/materialize)
- **SDKs & repos:** Incremental view maintenance over streams, built on timely/differential dataflow
- **Downloadable / offline:** Docs site
- *Note:* Differential dataflow is one of the genuinely novel ideas in this space. Worth reading even if you never deploy it.

### RisingWave

- **Docs:** [docs.risingwave.com](https://docs.risingwave.com/)
- **Source:** [github.com/risingwavelabs/risingwave](https://github.com/risingwavelabs/risingwave)
- **SDKs & repos:** Streaming database with PostgreSQL wire compatibility
- **Downloadable / offline:** Docs site

### Debezium

- **Docs:** [debezium.io/documentation](https://debezium.io/documentation/)
- **Developer / API:** [debezium.io/documentation/reference/stable](https://debezium.io/documentation/reference/stable/)
- **Source:** [github.com/debezium/debezium](https://github.com/debezium/debezium)
- **SDKs & repos:** Change data capture from databases into Kafka
- **Downloadable / offline:** Docs per version
- *Note:* The connector internals teach you a lot about how replication logs actually work in each database.

### Vitess

- **Docs:** [vitess.io/docs](https://vitess.io/docs/)
- **Developer / API:** [vitess.io/docs/reference](https://vitess.io/docs/reference/)
- **Source:** [github.com/vitessio/vitess](https://github.com/vitessio/vitess)
- **SDKs & repos:** Horizontal sharding middleware for MySQL, built at YouTube
- **Downloadable / offline:** Docs site
- *Note:* The reference implementation of sharding a single-node database without rewriting it.

### pgvector

- **Docs:** [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)
- **Source:** [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)
- **SDKs & repos:** Vector similarity search as a PostgreSQL extension
- **Downloadable / offline:** In-repo docs
- *Note:* Readable C, and a good example of how PostgreSQL’s extension and index APIs work.

### SQLGlot

- **Docs:** [github.com/tobymao/sqlglot](https://github.com/tobymao/sqlglot)
- **Developer / API:** [sqlglot.com](https://sqlglot.com/)
- **Source:** [github.com/tobymao/sqlglot](https://github.com/tobymao/sqlglot)
- **SDKs & repos:** SQL parser, transpiler and optimizer in pure Python across 20+ dialects
- **Downloadable / offline:** Docs site
- *Note:* A readable SQL parser and optimizer you can actually step through in a debugger.


## 8. Research papers & open-access literature

### arXiv

- **Docs:** [arxiv.org](https://arxiv.org/)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Preprints across all of CS; most systems, ML and PL work appears here before publication
- **Downloadable / offline:** Every paper is a free PDF. Bulk access documented at [info.arxiv.org/help/bulk_data/index.html](https://info.arxiv.org/help/bulk_data/index.html); a full-text API at export.arxiv.org
- *Note:* Not peer-reviewed. Treat an arXiv-only paper as a claim, not a result — but it is where you will read almost everything first.

### ar5iv

- **Docs:** [ar5iv.labs.arxiv.org](https://ar5iv.labs.arxiv.org/)
- **SDKs & repos:** Renders any arXiv paper as responsive HTML instead of PDF
- **Downloadable / offline:** Free; swap `arxiv.org/abs/ID` for `ar5iv.labs.arxiv.org/html/ID`
- *Note:* Makes papers readable on a phone and searchable in-page. Underused.

### alphaXiv

- **Docs:** [alphaxiv.org](https://www.alphaxiv.org/)
- **SDKs & repos:** arXiv papers with a public comment and discussion layer
- **Downloadable / offline:** Free
- *Note:* Useful when a paper is contested — the discussion often contains the critique you were looking for.

### Semantic Scholar

- **Docs:** [semanticscholar.org](https://www.semanticscholar.org/)
- **Developer / API:** [api.semanticscholar.org/graph/v1](https://api.semanticscholar.org/graph/v1)
- **SDKs & repos:** 200M+ papers with citation graph, influential-citation scoring and TLDR summaries
- **Downloadable / offline:** Free Graph API ([semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)), bulk datasets available on request
- *Note:* The best free citation graph. 'Highly influential citations' is a genuinely useful filter for finding what actually mattered.

### OpenAlex

- **Docs:** [openalex.org](https://openalex.org/)
- **Developer / API:** [api.openalex.org/works](https://api.openalex.org/works)
- **SDKs & repos:** Fully open catalogue of works, authors, venues and institutions; successor to Microsoft Academic Graph
- **Downloadable / offline:** Entirely free API with no key required; complete database snapshots downloadable
- *Note:* The only large-scale bibliographic database that is open all the way down, including bulk snapshots.

### DBLP

- **Docs:** [dblp.org](https://dblp.org/)
- **Developer / API:** [dblp.org/faq/13501473.html](https://dblp.org/faq/13501473.html)
- **SDKs & repos:** Authoritative CS bibliography — complete author and venue listings
- **Downloadable / offline:** Free; full XML dump downloadable
- *Note:* The fastest way to find everything a given researcher has published, and to see a conference's full programme by year.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **Source:** [github.com/openreview](https://github.com/openreview)
- **SDKs & repos:** ICLR, NeurIPS, COLM and dozens of other venues — papers plus the full review threads
- **Downloadable / offline:** Free; REST API
- *Note:* Reading the reviews and author rebuttals teaches you how the field evaluates work. Nothing else exposes this.

### CORE

- **Docs:** [core.ac.uk](https://core.ac.uk/)
- **Developer / API:** [core.ac.uk/services/api](https://core.ac.uk/services/api)
- **SDKs & repos:** Aggregates 300M+ open-access papers from repositories worldwide
- **Downloadable / offline:** Free API and bulk datasets
- *Note:* Good for finding the green open-access copy when a publisher's version is paywalled.

### Unpaywall

- **Docs:** [unpaywall.org](https://unpaywall.org/)
- **Developer / API:** [api.unpaywall.org](https://api.unpaywall.org/)
- **SDKs & repos:** Finds legal free copies of paywalled papers via DOI
- **Downloadable / offline:** Free API; browser extension
- *Note:* Legal, author-deposited copies only. Install the extension and most paywalls simply stop appearing.

### Papers We Love

- **Docs:** [paperswelove.org](https://paperswelove.org/)
- **Source:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **SDKs & repos:** A curated, categorised repository of classic CS papers with local meetup talks
- **Downloadable / offline:** Repo cloneable; many PDFs mirrored in-repo
- *Note:* The best starting point if you do not yet know which papers matter in a subfield.

### The Morning Paper (archive)

- **Docs:** [blog.acolyer.org](https://blog.acolyer.org/)
- **SDKs & repos:** Adrian Colyer's daily paper summaries, 2014-2021
- **Downloadable / offline:** Free archive, still online
- *Note:* No longer updated, but the back catalogue of ~1000 summarised papers is one of the great free CS resources.

### USENIX Proceedings

- **Docs:** [usenix.org/publications/proceedings](https://www.usenix.org/publications/proceedings)
- **SDKs & repos:** OSDI, SOSP (co-published), NSDI, ATC, FAST, Security — the core systems venues
- **Downloadable / offline:** Every paper free, immediately, with no membership. Often with recorded talks
- *Note:* USENIX made everything open access years before the rest of the field. If a systems paper exists, check here first.

### ACM Digital Library

- **Docs:** [dl.acm.org](https://dl.acm.org/)
- **SDKs & repos:** SIGMOD, ASPLOS, PLDI, POPL, SoCC and the ACM journals
- **Downloadable / offline:** Partly open: ACM Open and author-paid OA papers are free; others are paywalled
- *Note:* 403s to automated clients; loads in a browser. For paywalled items, check arXiv, the author's homepage or Unpaywall first — the free copy usually exists.

### IEEE Xplore

- **Docs:** [ieeexplore.ieee.org](https://ieeexplore.ieee.org/)
- **SDKs & repos:** ISCA, MICRO, HPCA and the IEEE journals
- **Downloadable / offline:** Mostly paywalled; abstracts free
- *Note:* Almost always worth searching the author's page or arXiv instead. Architecture authors in particular post preprints widely.

### DROPS / LIPIcs (Dagstuhl)

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **SDKs & repos:** ECOOP, ITP, CONCUR, SAT and many theory venues
- **Downloadable / offline:** 100% open access, free PDFs, Creative Commons licensed
- *Note:* A fully open publisher. Every paper, always free, no exceptions.

### arXiv cs.DB (Databases)

- **Docs:** [arxiv.org/list/cs.DB/recent](https://arxiv.org/list/cs.DB/recent)
- **SDKs & repos:** Database preprints
- **Downloadable / offline:** Free
- *Note:* Most PVLDB submissions appear here first.

### PVLDB

- **Docs:** [vldb.org/pvldb](https://www.vldb.org/pvldb/)
- **SDKs & repos:** Proceedings of the VLDB Endowment — the main database venue
- **Downloadable / offline:** 100% open access, every volume, free PDFs
- *Note:* Fully open since inception. The single best free database paper archive.

### CIDR

- **Docs:** [cidrdb.org](https://www.cidrdb.org/)
- **SDKs & repos:** Conference on Innovative Data Systems Research — biennial, visionary, short papers
- **Downloadable / offline:** All papers free
- *Note:* Often the most interesting reading of the three main venues. Industry systems get described here first.

### ACM SIGMOD

- **Docs:** [sigmod.org](https://sigmod.org/)
- **SDKs & repos:** The other flagship database venue
- **Downloadable / offline:** Proceedings via ACM DL; many authors post preprints
- *Note:* Check arXiv or the author's page before hitting the ACM paywall.

### Database of Databases (dbdb.io)

- **Docs:** [dbdb.io](https://dbdb.io/)
- **Source:** [github.com/cmu-db/dbdb.io](https://github.com/cmu-db/dbdb.io)
- **SDKs & repos:** A catalogue of 1000+ database systems with their architectural properties and references
- **Downloadable / offline:** Free; data in the repo
- *Note:* CMU-maintained. Filter by storage model, concurrency control or query interface to find comparable systems fast.

### The Red Book

- **Docs:** [redbook.io](http://www.redbook.io/)
- **SDKs & repos:** Readings in Database Systems, 5th edition — classic papers with editorial commentary
- **Downloadable / offline:** Free online
- *Note:* Stonebraker and Hellerstein telling you why each paper mattered. Read the commentary even if you skip the papers.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*23 resources across 6 topics.*


#### The course to do first

- **[CMU 15-445 Database Systems](https://15445.courses.cs.cmu.edu/)** — Andy Pavlo's undergraduate course. Full video lectures, slides, and C++ projects where you build a buffer pool, B+tree, query executor and concurrency control. Free and complete — better than most paid programmes.
- **[CMU Database Group YouTube](https://www.youtube.com/@CMUDatabaseGroup)** — Every lecture, plus the seminar series where real system architects explain their designs.
- **[db.cs.cmu.edu](https://db.cs.cmu.edu/)** — The group's hub: courses, seminars, the Database of Databases.
- **[Berkeley CS186](https://cs186berkeley.net/)** — The other strong public undergraduate course. Different emphasis, good second pass.


#### Foundations worth the time

- **[Use The Index, Luke](https://use-the-index-luke.com/)** — Learn indexing properly before learning anything else about performance.
- **[Modern SQL](https://modern-sql.com/)** — Window functions and CTEs will change how you write queries.
- **[PostgreSQL Exercises](https://pgexercises.com/)** — Practise against a real schema with immediate feedback.
- **[SQL Style Guide](https://www.sqlstyle.guide/)** — Short. Adopt it and stop arguing about formatting.


#### Start with a readable system

- **[SQLite architecture overview](https://www.sqlite.org/arch.html)** — Short, precise, and describes a complete database. The best first look inside one.
- **[Why SQLite is written in C](https://www.sqlite.org/whyc.html)** — Engineering rationale stated plainly. Instructive about trade-offs.
- **[SQLite source](https://github.com/sqlite/sqlite)** — Approachable, heavily commented, heavily tested.
- **[DuckDB docs](https://duckdb.org/docs/)** — Install in one line and have a modern vectorized engine on your laptop.


#### The reference documentation to learn to navigate

- **[PostgreSQL manual](https://www.postgresql.org/docs/current/)** — The gold standard. Learn its structure; you will return for years.
- **[MySQL reference manual](https://dev.mysql.com/doc/)** — Specifically the InnoDB chapters.
- **[SQLite documentation](https://www.sqlite.org/docs.html)** — Unusually complete for a project of its size.


#### Build intuition about systems

- **[databass.dev](https://databass.dev/)** — Companion site to Database Internals — storage engines and distributed systems, clearly explained.
- **[Designing Data-Intensive Applications](https://dataintensive.net/)** — Kleppmann's book. The chapters on replication, partitioning and consistency are the standard shared reference.
- **[The Red Book (Readings in Database Systems)](http://www.redbook.io/)** — Curated classic papers with editorial commentary. Free online, 5th edition.


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which papers matter. Curated by subfield, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language. No longer updated; still one of the best free CS resources.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. The 'highly influential citations' filter is the fastest way to find what a paper actually changed.
- **[Unpaywall](https://unpaywall.org/)** — Install the extension. Most paywalls stop appearing, legally, because the author deposited a copy.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF. Swap arxiv.org/abs for ar5iv.labs.arxiv.org/html.


### Advanced

*30 resources across 6 topics.*


#### Graduate coursework

- **[CMU 15-721 Advanced Database Systems](https://15721.courses.cs.cmu.edu/)** — In-memory, columnar, vectorized and compiled query execution. Paper-driven, all video online. The best advanced database course available free.
- **[CMU 15-445](https://15445.courses.cs.cmu.edu/)** — Do the projects even if you only watch 15-721. The implementation work is where the learning is.
- **[CMU Database Group seminar series](https://www.youtube.com/@CMUDatabaseGroup)** — Architects of real systems explaining their internals — Snowflake, DuckDB, TiDB and dozens more.
- **[Berkeley CS186](https://cs186berkeley.net/)** — Public projects with a solid concurrency-control component.


#### Query processing & optimization

- **[DuckDB source](https://github.com/duckdb/duckdb)** — Modern vectorized execution in readable C++. The best codebase to study push-based execution.
- **[ClickHouse source](https://github.com/ClickHouse/ClickHouse)** — Extreme-performance columnar execution; aggressive specialization everywhere.
- **[Apache Arrow columnar spec](https://arrow.apache.org/docs/format/Columnar.html)** — Short spec that explains why everything in analytics converged on this layout.
- **[Parquet format spec](https://parquet.apache.org/docs/file-format/)** — Encodings, statistics, predicate pushdown — all in one document.
- **[Apache Calcite](https://calcite.apache.org/docs/)** — Cost-based optimization as a reusable component. Read the rule system.


#### Storage engines

- **[RocksDB wiki](https://github.com/facebook/rocksdb/wiki)** — LSM compaction strategies, write stalls, tuning. Deeper than most textbooks.
- **[RocksDB source](https://github.com/facebook/rocksdb)** — The reference LSM implementation.
- **[LevelDB](https://github.com/google/leveldb)** — Read this first — same ideas, a fraction of the code.
- **[LMDB](http://www.lmdb.tech/doc/)** — Copy-on-write B+tree with MVCC. The intellectual opposite of LSM; study both.
- **[WiredTiger](https://source.wiredtiger.com/)** — B-tree and LSM in one engine, in production under MongoDB.
- **[databass.dev](https://databass.dev/)** — Ties the storage-engine literature together coherently.


#### Transactions, concurrency & distributed SQL

- **[CockroachDB RFCs](https://github.com/cockroachdb/cockroach)** — The `docs/RFCS/` directory records real distributed-SQL design arguments in detail. Rare and valuable.
- **[TiDB](https://github.com/pingcap/tidb)** — Percolator-style transactions over a separate TiKV storage layer.
- **[awesome-database-learning](https://github.com/pingcap/awesome-database-learning)** — PingCAP's curated path through papers, courses and source. Excellent.
- **[YugabyteDB](https://github.com/yugabyte/yugabyte-db)** — Reuses PostgreSQL's query layer over a distributed store.
- **[Cloud Spanner docs](https://cloud.google.com/spanner/docs)** — TrueTime and external consistency, documented by the people who shipped it.
- **[Designing Data-Intensive Applications](https://dataintensive.net/)** — Chapter 7 and 9 on transactions and consistency remain the clearest treatment.


#### Lakehouse & modern data architecture

- **[Apache Iceberg spec](https://iceberg.apache.org/spec/)** — Read the spec, not the marketing. Snapshot isolation over object storage.
- **[Delta Lake protocol](https://github.com/delta-io/delta/blob/master/PROTOCOL.md)** — The transaction log design, stated precisely.
- **[Apache Hudi](https://hudi.apache.org/docs/overview)** — Copy-on-write versus merge-on-read trade-offs.
- **[Snowflake docs](https://docs.snowflake.com/)** — Separation of storage and compute as realised commercially.


#### Papers & research venues

- **[The Red Book](http://www.redbook.io/)** — Start here. Classic papers with commentary explaining why each mattered.
- **[VLDB / PVLDB](https://www.vldb.org/pvldb/)** — All papers free. The main database research venue.
- **[ACM SIGMOD](https://dl.acm.org/conference/sigmod)** — The other main venue. ACM DL 403s to bots; accessible in a browser, and most papers are also on authors' pages.
- **[CIDR](https://www.cidrdb.org/)** — Biennial, visionary, short papers. Often the most interesting reading of the three.
- **[awesome-database-learning](https://github.com/pingcap/awesome-database-learning)** — Also a good paper index organised by subsystem.


---

## Video courses, channels & talks

*14 resources across 2 groups.* Every channel and playlist below was fetched and title-verified on **2026-10-09**. Handles drift and several plausible-looking handles resolve to the wrong channel, so a 200 response is not proof of identity — the links here were each checked against the channel title.

### Channels & conference recordings

- **[Hussein Nasser](https://www.youtube.com/@HusseinNasser)** — Database internals — indexing, isolation levels, replication — explained from first principles.
- **[MySQL](https://www.youtube.com/@MySQL)** — Official MySQL channel: product deep dives and conference talks.
- **[MongoDB](https://www.youtube.com/@MongoDB)** — Official MongoDB channel: internals, aggregation, Atlas talks.
- **[Redis](https://www.youtube.com/@RedisInc)** — Official Redis channel: internals, modules, and Redis University material.
- **[Confluent](https://www.youtube.com/@Confluent)** — Kafka Summit talks and stream-processing design sessions — the canonical Kafka video record.
- **[USENIX](https://www.youtube.com/@USENIX)** — Conference recordings for most USENIX papers — free video, the fastest route into a systems paper.
- **[InfoQ](https://www.youtube.com/@InfoQ)** — Conference keynotes and architecture talks — good for orientation, verify specifics elsewhere.
- **[Papers We Love](https://www.youtube.com/@PapersWeLove)** — Recorded paper walkthroughs — watch one before you read the PDF.
- **[VLDB](https://www.youtube.com/@vldb)** — VLDB conference recordings; the channel only holds one edition, so treat it as a sample, not an archive.
- **[Percona](https://www.youtube.com/@Percona)** — Percona Live talks on MySQL, PostgreSQL and MongoDB internals — practitioner depth, engine-specific.
- **[ClickHouse](https://www.youtube.com/@ClickHouseDB)** — Vendor channel, but unusually technical: columnar storage internals and query-execution talks.
- **[Yugabyte](https://www.youtube.com/@YugabyteDB)** — Distributed SQL internals, including consensus and transaction-design talks.

### Lectures & playlists

- **[CMU 15-445/645 — Intro to Database Systems (Fall 2022)](https://www.youtube.com/playlist?list=PLSE8ODhjZXjaKScG3l0nuOiDTTqpfnWFf)** — The standard free database-internals course; pair it with the course site and the labs below.
- **[CMU 15-445/645 — Intro to Database Systems (Fall 2019)](https://www.youtube.com/playlist?list=PLSE8ODhjZXjbohkNBWQs_otTrBTrjyohi)** — An earlier run; useful when the 2022 recording of a topic is missing.

*Note:* Vendor channels are useful for internals of their own engine and useless for anything else; pair them with the USENIX and paper-walkthrough material.

## Conference videos, notes & archives

*6 resources across 2 groups.* Conference recordings are the primary-source tier of video: the speaker is usually an author of the paper, and where a talk exists the proceedings entry is often open at the same link. Every URL here returned 200 on **2026-10-09** unless the note says otherwise.

Database conferences are unusually open — PVLDB is fully open access, and the vendor conferences publish good internals talks.

### Conference channels & video archives

- **[VLDB](https://www.vldb.org/)** — PVLDB is fully open access, which is why it is the citation you can actually read.
- **[USENIX FAST '25](https://www.usenix.org/conference/fast25)** — Storage conference, but the storage-engine papers here are database internals.
- **[Percona Live](https://www.percona.com/live)** — Practitioner conference on MySQL, PostgreSQL and MongoDB; talks published on the Percona channel.
- **[CMU 15-445 course site](https://15445.courses.cs.cmu.edu/fall2025/)** — Slides, notes and open labs to go with the playlist above; the homework is the point.
- **[FOSDEM video archive](https://video.fosdem.org/)** — Databases and PostgreSQL devrooms.

### Notes, proceedings & paper-adjacent archives

- **[USENIX ;login:](https://www.usenix.org/publications/login/)** — Where the operational side of database work gets written up.

## If you only do three things

1. **Do CMU 15-445.** Videos, slides and C++ projects, all free. Build a buffer pool and a B+tree yourself.
2. **Read `sqlite.org/arch.html`, then the SQLite source.** A complete database you can actually hold in your head.
3. **Work through Use The Index, Luke.** Most real-world query performance problems are solved by this one resource.

## Honest notes

- **PostgreSQL's manual is the best documentation in this field.** Learn to navigate it; it rewards the investment for years.
- **RocksDB's wiki is better than most database textbooks** on LSM trees, compaction and write amplification.
- **Read LevelDB before RocksDB, and LMDB alongside both.** LSM versus copy-on-write B+tree is the central storage trade-off.
- **The Iceberg and Delta specs are short.** Read them directly rather than vendor explainers.
- **DB-Engines ranks by popularity, not merit.** Useful for trends only.

---

## Related sections of this book

- [Database Management Systems](../dbms/overview.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other topic indexes
