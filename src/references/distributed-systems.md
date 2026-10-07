# NoSQL & Distributed Systems Reference Library

This page is a verified index of primary sources for distributed systems: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Document, wide-column, key-value, graph, time-series and search stores; consensus libraries; messaging and stream processing; verification tooling; and a two-track path from Gossip Glomers to implementing Raft and model-checking your own protocols.

**74 entries** across 8 categories, plus **54 education & reference-implementation resources** (23 basic / 31 advanced).

Every link HTTP-verified on **2026-10-07**.

## Contents

- [1. Document, wide-column & key-value stores](#1-document-wide-column--key-value-stores) — 9
- [2. Graph, time-series & search](#2-graph-time-series--search) — 6
- [3. Coordination, consensus & configuration](#3-coordination-consensus--configuration) — 7
- [4. Messaging, streaming & distributed compute](#4-messaging-streaming--distributed-compute) — 9
- [5. Correctness, verification & chaos](#5-correctness-verification--chaos) — 5
- [6. Reference, reading lists & theory](#6-reference-reading-lists--theory) — 7
- [7. Replication, CRDTs, chaos & deterministic testing](#7-replication-crdts-chaos--deterministic-testing) — 8
- [8. Research papers & open-access literature](#8-research-papers--open-access-literature) — 23
- [Education & reference implementations](#education--reference-implementations) — 54 (23 basic / 31 advanced)


## 1. Document, wide-column & key-value stores

### MongoDB

- **Docs:** [mongodb.com/docs](https://www.mongodb.com/docs/)
- **Developer / API:** [mongodb.com/docs/drivers](https://www.mongodb.com/docs/drivers/)
- **Source:** [github.com/mongodb/mongo](https://github.com/mongodb/mongo)
- **SDKs & repos:** Official drivers for 12+ languages; Atlas Data API; Compass
- **Downloadable / offline:** Docs downloadable per version; MongoDB University courses free
- *Note:* Document store with a mature query language. Read the replica-set election and write-concern docs — that is where the distributed-systems content lives.

### Apache Cassandra

- **Docs:** [cassandra.apache.org/doc/latest](https://cassandra.apache.org/doc/latest/)
- **Developer / API:** [cassandra.apache.org/doc/…](https://cassandra.apache.org/doc/latest/cassandra/developing/)
- **Source:** [github.com/apache/cassandra](https://github.com/apache/cassandra)
- **SDKs & repos:** DataStax drivers; CQL
- **Downloadable / offline:** Docs per version online
- *Note:* The canonical Dynamo-style wide-column store. Tunable consistency makes the quorum maths concrete.

### ScyllaDB

- **Docs:** [docs.scylladb.com](https://docs.scylladb.com/)
- **Developer / API:** [docs.scylladb.com/stable/using-scylla/drivers](https://docs.scylladb.com/stable/using-scylla/drivers/)
- **Source:** [github.com/scylladb/scylladb](https://github.com/scylladb/scylladb)
- **SDKs & repos:** Cassandra-compatible drivers; Seastar framework underneath
- **Downloadable / offline:** Docs site; Scylla University free
- *Note:* C++ rewrite of Cassandra on a shard-per-core architecture. The Seastar design docs are excellent on thread-per-core.

### Redis

- **Docs:** [redis.io/docs/latest](https://redis.io/docs/latest/)
- **Developer / API:** [redis.io/docs/latest/develop](https://redis.io/docs/latest/develop/)
- **Source:** [github.com/redis/redis](https://github.com/redis/redis)
- **SDKs & repos:** Clients in every language; Redis Stack modules
- **Downloadable / offline:** Docs site; source is famously readable C
- *Note:* Read the source — `t_string.c`, `dict.c`, `ae.c` are a short course in systems C.

### Valkey

- **Docs:** [valkey.io/topics](https://valkey.io/topics/)
- **Developer / API:** [valkey.io/docs](https://valkey.io/docs/)
- **Source:** [github.com/valkey-io/valkey](https://github.com/valkey-io/valkey)
- **SDKs & repos:** Redis-compatible clients
- **Downloadable / offline:** Docs site
- *Note:* The Linux Foundation fork created after Redis's 2024 licence change. Now the default in several distributions.

### Amazon DynamoDB

- **Docs:** [docs.aws.amazon.com/dynamodb](https://docs.aws.amazon.com/dynamodb/)
- **Developer / API:** [docs.aws.amazon.com/amazondynamodb/…](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/)
- **SDKs & repos:** AWS SDKs; DynamoDB Local for offline development
- **Downloadable / offline:** AWS docs downloadable as PDF
- *Note:* Read the original Dynamo paper and the 2022 USENIX ATC paper on the production system together.

### Couchbase

- **Docs:** [docs.couchbase.com/home/index.html](https://docs.couchbase.com/home/index.html)
- **Developer / API:** [docs.couchbase.com/home/sdk.html](https://docs.couchbase.com/home/sdk.html)
- **Source:** [github.com/couchbase](https://github.com/couchbase)
- **SDKs & repos:** SDKs for most languages; N1QL/SQL++
- **Downloadable / offline:** Docs site

### Apache HBase

- **Docs:** [hbase.apache.org/book.html](https://hbase.apache.org/book.html)
- **Developer / API:** [hbase.apache.org/apidocs](https://hbase.apache.org/apidocs/)
- **Source:** [github.com/apache/hbase](https://github.com/apache/hbase)
- **SDKs & repos:** Java API, Thrift, REST
- **Downloadable / offline:** The HBase book as a single HTML page — also downloadable
- *Note:* The open Bigtable implementation. Read with the Bigtable paper.

### FoundationDB

- **Docs:** [apple.github.io/foundationdb](https://apple.github.io/foundationdb/)
- **Developer / API:** [apple.github.io/foundationdb/api-general.html](https://apple.github.io/foundationdb/api-general.html)
- **Source:** [github.com/apple/foundationdb](https://github.com/apple/foundationdb)
- **SDKs & repos:** Bindings for C, Python, Java, Go, Ruby
- **Downloadable / offline:** Docs site
- *Note:* Strictly serializable distributed transactions, plus a deterministic simulation testing approach that is the most interesting part of the project.


## 2. Graph, time-series & search

### Neo4j

- **Docs:** [neo4j.com/docs](https://neo4j.com/docs/)
- **Developer / API:** [neo4j.com/docs/create-applications](https://neo4j.com/docs/create-applications/)
- **Source:** [github.com/neo4j/neo4j](https://github.com/neo4j/neo4j)
- **SDKs & repos:** Bolt drivers; Cypher; GDS library
- **Downloadable / offline:** Docs downloadable as PDF per manual
- *Note:* Cypher became the basis for the ISO GQL standard.

### ArangoDB

- **Docs:** [docs.arangodb.com/stable](https://docs.arangodb.com/stable/)
- **Developer / API:** [docs.arangodb.com/stable/develop](https://docs.arangodb.com/stable/develop/)
- **Source:** [github.com/arangodb/arangodb](https://github.com/arangodb/arangodb)
- **SDKs & repos:** Multi-model: document, graph and key-value in one engine
- **Downloadable / offline:** Docs site

### InfluxDB

- **Docs:** [docs.influxdata.com](https://docs.influxdata.com/)
- **Developer / API:** [docs.influxdata.com/influxdb3/core/api](https://docs.influxdata.com/influxdb3/core/api/)
- **Source:** [github.com/influxdata/influxdb](https://github.com/influxdata/influxdb)
- **SDKs & repos:** Client libraries; line protocol
- **Downloadable / offline:** Docs site
- *Note:* Version 3 is a substantial rewrite on Arrow and DataFusion — check which version documentation you are reading.

### TimescaleDB

- **Docs:** [docs.tigerdata.com](https://docs.tigerdata.com/)
- **Source:** [github.com/timescale/timescaledb](https://github.com/timescale/timescaledb)
- **SDKs & repos:** PostgreSQL extension — all PostgreSQL clients work
- **Downloadable / offline:** Docs site
- *Note:* Now branded TigerData; the extension remains Timescale.

### Elasticsearch

- **Docs:** [elastic.co/docs](https://www.elastic.co/docs)
- **Developer / API:** [elastic.co/docs/api](https://www.elastic.co/docs/api/)
- **Source:** [github.com/elastic/elasticsearch](https://github.com/elastic/elasticsearch)
- **SDKs & repos:** Official clients in 8+ languages
- **Downloadable / offline:** Docs site per version
- *Note:* Distributed search with a real sharding and replication model underneath.

### OpenSearch

- **Docs:** [docs.opensearch.org/latest](https://docs.opensearch.org/latest/)
- **Developer / API:** [docs.opensearch.org/latest/api-reference](https://docs.opensearch.org/latest/api-reference/)
- **Source:** [github.com/opensearch-project/OpenSearch](https://github.com/opensearch-project/OpenSearch)
- **SDKs & repos:** Elasticsearch-compatible clients
- **Downloadable / offline:** Docs site
- *Note:* The Apache 2.0 fork maintained after Elastic's licence change.


## 3. Coordination, consensus & configuration

### etcd

- **Docs:** [etcd.io/docs](https://etcd.io/docs/)
- **Developer / API:** [etcd.io/docs/latest/dev-guide](https://etcd.io/docs/latest/dev-guide/)
- **Source:** [github.com/etcd-io/etcd](https://github.com/etcd-io/etcd)
- **SDKs & repos:** gRPC API; clientv3 in Go and others
- **Downloadable / offline:** Docs site
- *Note:* The Raft store behind Kubernetes. `etcd-io/raft` is a separate, very readable library.

### etcd Raft library

- **Docs:** [github.com/etcd-io/raft](https://github.com/etcd-io/raft)
- **Developer / API:** [pkg.go.dev/go.etcd.io/raft/v3](https://pkg.go.dev/go.etcd.io/raft/v3)
- **Source:** [github.com/etcd-io/raft](https://github.com/etcd-io/raft)
- **SDKs & repos:** Production Raft as a standalone Go library
- **Downloadable / offline:** Godoc + in-repo design notes
- *Note:* The best-documented production Raft implementation. Read it after the Raft paper.

### Apache ZooKeeper

- **Docs:** [zookeeper.apache.org/doc/current](https://zookeeper.apache.org/doc/current/)
- **Developer / API:** [zookeeper.apache.org/doc/…](https://zookeeper.apache.org/doc/current/javaExample.html)
- **Source:** [github.com/apache/zookeeper](https://github.com/apache/zookeeper)
- **SDKs & repos:** Java and C clients; Curator recipes
- **Downloadable / offline:** Docs per version
- *Note:* ZAB rather than Raft. The recipes document (locks, barriers, leader election) is the practical part.

### HashiCorp Consul

- **Docs:** [developer.hashicorp.com/consul/docs](https://developer.hashicorp.com/consul/docs)
- **Developer / API:** [developer.hashicorp.com/consul/api-docs](https://developer.hashicorp.com/consul/api-docs)
- **Source:** [github.com/hashicorp/consul](https://github.com/hashicorp/consul)
- **SDKs & repos:** HTTP API, DNS interface, service mesh
- **Downloadable / offline:** Docs site

### hashicorp/raft

- **Docs:** [github.com/hashicorp/raft](https://github.com/hashicorp/raft)
- **Developer / API:** [pkg.go.dev/github.com/hashicorp/raft](https://pkg.go.dev/github.com/hashicorp/raft)
- **Source:** [github.com/hashicorp/raft](https://github.com/hashicorp/raft)
- **SDKs & repos:** The other widely deployed Go Raft library
- **Downloadable / offline:** Godoc
- *Note:* Compare with etcd's — the design differences are instructive.

### braft

- **Docs:** [github.com/baidu/braft](https://github.com/baidu/braft)
- **Source:** [github.com/baidu/braft](https://github.com/baidu/braft)
- **SDKs & repos:** Industrial C++ Raft from Baidu
- **Downloadable / offline:** In-repo docs

### raft.github.io

- **Docs:** [raft.github.io](https://raft.github.io/)
- **Source:** [github.com/raft/raft.github.io](https://github.com/raft/raft.github.io)
- **SDKs & repos:** The Raft homepage: paper, visualization, and a list of 100+ implementations
- **Downloadable / offline:** Extended paper PDF: [raft.github.io/raft.pdf](https://raft.github.io/raft.pdf)
- *Note:* The interactive visualization teaches leader election faster than any text.


## 4. Messaging, streaming & distributed compute

### Apache Kafka

- **Docs:** [kafka.apache.org/documentation](https://kafka.apache.org/documentation/)
- **Developer / API:** [kafka.apache.org/documentation/#api](https://kafka.apache.org/documentation/#api)
- **Source:** [github.com/apache/kafka](https://github.com/apache/kafka)
- **SDKs & repos:** Java client, librdkafka, Connect, Streams
- **Downloadable / offline:** Single-page documentation — downloadable as one HTML file
- *Note:* The design section of the docs is a genuine distributed-systems paper. KRaft has replaced ZooKeeper.

### Apache Pulsar

- **Docs:** [pulsar.apache.org/docs](https://pulsar.apache.org/docs/)
- **Developer / API:** [pulsar.apache.org/docs/next/client-libraries](https://pulsar.apache.org/docs/next/client-libraries/)
- **Source:** [github.com/apache/pulsar](https://github.com/apache/pulsar)
- **SDKs & repos:** Clients in many languages; BookKeeper underneath
- **Downloadable / offline:** Docs per version
- *Note:* Separates serving from storage. Worth studying as a contrast to Kafka's design.

### NATS

- **Docs:** [docs.nats.io](https://docs.nats.io/)
- **Developer / API:** [docs.nats.io/using-nats/developer](https://docs.nats.io/using-nats/developer)
- **Source:** [github.com/nats-io/nats-server](https://github.com/nats-io/nats-server)
- **SDKs & repos:** Clients in 40+ languages; JetStream for persistence
- **Downloadable / offline:** Docs site
- *Note:* Small, fast, operationally simple. The server source is readable Go.

### RabbitMQ

- **Docs:** [rabbitmq.com/docs](https://www.rabbitmq.com/docs)
- **Developer / API:** [rabbitmq.com/client-libraries](https://www.rabbitmq.com/client-libraries)
- **Source:** [github.com/rabbitmq/rabbitmq-server](https://github.com/rabbitmq/rabbitmq-server)
- **SDKs & repos:** AMQP 0-9-1, MQTT, STOMP
- **Downloadable / offline:** Docs site
- *Note:* The tutorials are the best introduction to messaging patterns generally.

### Apache Spark

- **Docs:** [spark.apache.org/docs/latest](https://spark.apache.org/docs/latest/)
- **Developer / API:** [spark.apache.org/docs/latest/api/python](https://spark.apache.org/docs/latest/api/python/)
- **Source:** [github.com/apache/spark](https://github.com/apache/spark)
- **SDKs & repos:** Scala, Java, Python, R, SQL
- **Downloadable / offline:** Docs per version

### Apache Flink

- **Docs:** [nightlies.apache.org/flink/flink-docs-stable](https://nightlies.apache.org/flink/flink-docs-stable/)
- **Developer / API:** [nightlies.apache.org/flink/…](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/overview/)
- **Source:** [github.com/apache/flink](https://github.com/apache/flink)
- **SDKs & repos:** DataStream and Table APIs; Java, Scala, Python
- **Downloadable / offline:** Docs per version
- *Note:* The checkpointing and exactly-once chapters are the valuable reading.

### Apache Beam

- **Docs:** [beam.apache.org/documentation](https://beam.apache.org/documentation/)
- **Developer / API:** [beam.apache.org/documentation/sdks/java](https://beam.apache.org/documentation/sdks/java/)
- **Source:** [github.com/apache/beam](https://github.com/apache/beam)
- **SDKs & repos:** Unified batch/streaming model across runners
- **Downloadable / offline:** Docs site
- *Note:* The Dataflow model paper behind it is the clearest treatment of event time and watermarks.

### Ray

- **Docs:** [docs.ray.io/en/latest](https://docs.ray.io/en/latest/)
- **Developer / API:** [docs.ray.io/en/latest/ray-core/api](https://docs.ray.io/en/latest/ray-core/api/)
- **Source:** [github.com/ray-project/ray](https://github.com/ray-project/ray)
- **SDKs & repos:** Python-first distributed compute; Train, Tune, Serve
- **Downloadable / offline:** Docs site
- *Note:* Also central to the ML ecosystem — see the ML/AI index.

### Temporal

- **Docs:** [docs.temporal.io](https://docs.temporal.io/)
- **Developer / API:** [docs.temporal.io/develop](https://docs.temporal.io/develop)
- **Source:** [github.com/temporalio/temporal](https://github.com/temporalio/temporal)
- **SDKs & repos:** SDKs for Go, Java, Python, TypeScript, .NET
- **Downloadable / offline:** Docs site
- *Note:* Durable execution — the most interesting recent idea in distributed application design.


## 5. Correctness, verification & chaos

### Jepsen

- **Docs:** [jepsen.io](https://jepsen.io/)
- **Developer / API:** [jepsen.io/analyses](https://jepsen.io/analyses)
- **Source:** [github.com/jepsen-io/jepsen](https://github.com/jepsen-io/jepsen)
- **SDKs & repos:** Clojure testing framework; the analyses are the real artefact
- **Downloadable / offline:** All analyses free online
- *Note:* Kyle Kingsbury's reports on real databases under partition. Read three of them and your trust calibration changes permanently.

### Maelstrom

- **Docs:** [github.com/jepsen-io/maelstrom](https://github.com/jepsen-io/maelstrom)
- **Source:** [github.com/jepsen-io/maelstrom](https://github.com/jepsen-io/maelstrom)
- **SDKs & repos:** A workbench for writing toy distributed systems and having them tested properly
- **Downloadable / offline:** In-repo docs and a full tutorial
- *Note:* The best hands-on way to learn distributed systems. Start here, not with a book.

### Gossip Glomers (fly.io)

- **Docs:** [fly.io/dist-sys](https://fly.io/dist-sys/)
- **SDKs & repos:** A guided challenge series built on Maelstrom: broadcast, CRDTs, Kafka-style logs, transactions
- **Downloadable / offline:** Free, self-paced
- *Note:* Probably the single best free practical distributed-systems course. Six challenge sets, real verification.

### TLA+

- **Docs:** [lamport.azurewebsites.net/tla/tla.html](https://lamport.azurewebsites.net/tla/tla.html)
- **Source:** [github.com/tlaplus/tlaplus](https://github.com/tlaplus/tlaplus)
- **SDKs & repos:** TLA+ Toolbox, TLC model checker, PlusCal
- **Downloadable / offline:** Lamport's video course and the Hyperbook, both free
- *Note:* Used at AWS and Microsoft to find real protocol bugs before implementation.

### Learn TLA+

- **Docs:** [learntla.com](https://learntla.com/)
- **SDKs & repos:** A much gentler entry point than Lamport's own materials
- **Downloadable / offline:** Free online book
- *Note:* Start here if TLA+ has bounced off you before.


## 6. Reference, reading lists & theory

### Raft paper

- **Docs:** [raft.github.io/raft.pdf](https://raft.github.io/raft.pdf)
- **Developer / API:** [raft.github.io](https://raft.github.io/)
- **SDKs & repos:** The extended Raft paper
- **Downloadable / offline:** PDF
- *Note:* Read this before any consensus implementation. It was written to be understandable, and it is.

### Paxos Made Simple

- **Docs:** [microsoft.com/en-us/…](https://www.microsoft.com/en-us/research/publication/paxos-made-simple/)
- **Developer / API:** [lamport.azurewebsites.net/pubs/pubs.html](https://lamport.azurewebsites.net/pubs/pubs.html)
- **SDKs & repos:** Lamport's attempt at an accessible Paxos explanation
- **Downloadable / offline:** Free PDF
- *Note:* Still harder than Raft. Read it second, for the lineage.

### Lamport's publications

- **Docs:** [lamport.azurewebsites.net/pubs/pubs.html](https://lamport.azurewebsites.net/pubs/pubs.html)
- **SDKs & repos:** Time/Clocks, Byzantine Generals, Paxos — with retrospective commentary on each
- **Downloadable / offline:** All free
- *Note:* The commentary explaining why each paper was written is as useful as the papers.

### crdt.tech

- **Docs:** [crdt.tech](https://crdt.tech/)
- **SDKs & repos:** The CRDT reference: papers, implementations, talks
- **Downloadable / offline:** Web index
- *Note:* Start here for conflict-free replicated data types rather than with a single library.

### Distributed Systems (van Steen & Tanenbaum)

- **Docs:** [distributed-systems.net/index.php/books/ds4](https://www.distributed-systems.net/index.php/books/ds4/)
- **Developer / API:** [distributed-systems.net](https://www.distributed-systems.net/)
- **SDKs & repos:** Full textbook, 4th edition
- **Downloadable / offline:** Free PDF from the authors
- *Note:* A proper textbook, legitimately free.

### awesome-distributed-systems

- **Docs:** [github.com/theanalyst/…](https://github.com/theanalyst/awesome-distributed-systems)
- **Source:** [github.com/theanalyst/…](https://github.com/theanalyst/awesome-distributed-systems)
- **SDKs & repos:** Curated papers, books, talks and systems
- **Downloadable / offline:** Repo

### dancres/Pages

- **Docs:** [dancres.github.io/Pages](https://dancres.github.io/Pages/)
- **Source:** [github.com/dancres/Pages](https://github.com/dancres/Pages)
- **SDKs & repos:** A large annotated reading list of distributed-systems papers
- **Downloadable / offline:** Web
- *Note:* One of the best-curated paper lists available.


## 7. Replication, CRDTs, chaos & deterministic testing

### TigerBeetle

- **Docs:** [docs.tigerbeetle.com](https://docs.tigerbeetle.com/)
- **Source:** [github.com/tigerbeetle/tigerbeetle](https://github.com/tigerbeetle/tigerbeetle)
- **SDKs & repos:** Financial accounting database in Zig; Viewstamped Replication consensus; deterministic simulation testing
- **Downloadable / offline:** Docs site
- *Note:* The most rigorous open testing methodology currently shipping. The simulator and the design docs are the reason to read it.

### Automerge

- **Docs:** [automerge.org](https://automerge.org/)
- **Developer / API:** [automerge.org/docs](https://automerge.org/docs/)
- **Source:** [github.com/automerge/automerge](https://github.com/automerge/automerge)
- **SDKs & repos:** CRDT library for local-first applications; Rust core with JS and Swift bindings
- **Downloadable / offline:** Docs site
- *Note:* The most approachable production CRDT implementation. Read with crdt.tech.

### Yjs

- **Docs:** [docs.yjs.dev](https://docs.yjs.dev/)
- **Developer / API:** [docs.yjs.dev/api](https://docs.yjs.dev/api/)
- **Source:** [github.com/yjs/yjs](https://github.com/yjs/yjs)
- **SDKs & repos:** High-performance CRDT for collaborative editing
- **Downloadable / offline:** Docs site
- *Note:* Powers a lot of real collaborative software. Benchmarks and internals are documented openly.

### Apache BookKeeper

- **Docs:** [bookkeeper.apache.org/docs/overview](https://bookkeeper.apache.org/docs/overview/)
- **Developer / API:** [bookkeeper.apache.org/docs/api/overview](https://bookkeeper.apache.org/docs/api/overview)
- **Source:** [github.com/apache/bookkeeper](https://github.com/apache/bookkeeper)
- **SDKs & repos:** Replicated log storage; the durability layer under Pulsar
- **Downloadable / offline:** Docs per version
- *Note:* A distributed write-ahead log as a standalone service. Useful to study separately from Pulsar.

### Dapr

- **Docs:** [docs.dapr.io](https://docs.dapr.io/)
- **Developer / API:** [docs.dapr.io/reference/api](https://docs.dapr.io/reference/api/)
- **Source:** [github.com/dapr/dapr](https://github.com/dapr/dapr)
- **SDKs & repos:** Portable building blocks for distributed applications: state, pub/sub, bindings, actors
- **Downloadable / offline:** Docs site
- *Note:* An opinionated abstraction over the patterns. Read the component model before adopting it.

### Hazelcast

- **Docs:** [docs.hazelcast.com](https://docs.hazelcast.com/)
- **Developer / API:** [docs.hazelcast.com/hazelcast/latest](https://docs.hazelcast.com/hazelcast/latest/)
- **Source:** [github.com/hazelcast/hazelcast](https://github.com/hazelcast/hazelcast)
- **SDKs & repos:** In-memory data grid with distributed data structures and CP subsystem
- **Downloadable / offline:** Docs per version
- *Note:* The CP subsystem is a Raft implementation worth reading alongside etcd’s.

### Chaos Mesh

- **Docs:** [chaos-mesh.org/docs](https://chaos-mesh.org/docs/)
- **Source:** [github.com/chaos-mesh/chaos-mesh](https://github.com/chaos-mesh/chaos-mesh)
- **SDKs & repos:** Kubernetes-native fault injection: network partitions, latency, pod kills
- **Downloadable / offline:** Docs site
- *Note:* The practical way to apply Jepsen-style thinking to your own cluster.

### LitmusChaos

- **Docs:** [docs.litmuschaos.io](https://docs.litmuschaos.io/)
- **Source:** [github.com/litmuschaos/litmus](https://github.com/litmuschaos/litmus)
- **SDKs & repos:** CNCF chaos engineering framework with a public experiment hub
- **Downloadable / offline:** Docs site


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

### arXiv cs.DC (Distributed Computing)

- **Docs:** [arxiv.org/list/cs.DC/recent](https://arxiv.org/list/cs.DC/recent)
- **SDKs & repos:** Distributed, parallel and cluster computing preprints
- **Downloadable / offline:** Free

### USENIX NSDI

- **Docs:** [usenix.org/conference/nsdi25](https://www.usenix.org/conference/nsdi25)
- **SDKs & repos:** Networked Systems Design and Implementation
- **Downloadable / offline:** Every paper free
- *Note:* Where most large-scale distributed infrastructure work is published.

### USENIX OSDI

- **Docs:** [usenix.org/conference/osdi26](https://www.usenix.org/conference/osdi26)
- **SDKs & repos:** Systems and distributed systems, free and open
- **Downloadable / offline:** All papers free
- *Note:* Raft, Spanner-adjacent work and most consensus systems research lands here or at SOSP.

### PODC

- **Docs:** [podc.org](https://www.podc.org/)
- **SDKs & repos:** Principles of Distributed Computing — the theory side
- **Downloadable / offline:** Via ACM DL; most authors post preprints
- *Note:* This is where impossibility results and lower bounds live. Harder reading, but foundational.

### DISC

- **Docs:** [disc-conference.org](https://www.disc-conference.org/)
- **SDKs & repos:** International Symposium on Distributed Computing
- **Downloadable / offline:** Proceedings open via LIPIcs/DROPS
- *Note:* Fully open access through Dagstuhl. Theory-focused.

### The Paper Trail

- **Docs:** [the-paper-trail.org](https://www.the-paper-trail.org/)
- **SDKs & repos:** Henry Robinson's distributed systems writing, including the classic consensus explainers
- **Downloadable / offline:** Free
- *Note:* The 'Paxos made abstract' material is clearer than most formal treatments.

### Metadata (Murat Demirbas)

- **Docs:** [muratbuffalo.blogspot.com](https://muratbuffalo.blogspot.com/)
- **SDKs & repos:** Long-running paper review blog from a distributed systems researcher
- **Downloadable / offline:** Free
- *Note:* Reviews of both classic and current papers, with honest criticism.

### Jepsen analyses

- **Docs:** [jepsen.io/analyses](https://jepsen.io/analyses)
- **SDKs & repos:** Empirical consistency testing reports on real databases
- **Downloadable / offline:** All free
- *Note:* Not peer-reviewed and more consequential than most papers that are.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*23 resources across 6 topics.*


#### Start by building, not reading

- **[Gossip Glomers](https://fly.io/dist-sys/)** — Six challenge sets — unique IDs, broadcast, CRDT counters, a Kafka-style log, distributed transactions — each verified by a real checker. Free. Do this before any textbook.
- **[Maelstrom](https://github.com/jepsen-io/maelstrom)** — The workbench underneath Gossip Glomers. Write a node in any language; it injects partitions and checks linearizability.
- **[MIT 6.824 / 6.5840 Distributed Systems](https://pdos.csail.mit.edu/6.824/)** — Labs where you implement MapReduce, Raft, a fault-tolerant KV store and sharding — in Go, with public tests. The best university course in the field, entirely free.


#### The core reading

- **[Designing Data-Intensive Applications](https://dataintensive.net/)** — Kleppmann's book is the common vocabulary of the field. Chapters 5-9 are the heart of it.
- **[Distributed Systems, 4th edition](https://www.distributed-systems.net/index.php/books/ds4/)** — A free, complete textbook if you want formal treatment alongside DDIA.
- **[Raft paper](https://raft.github.io/raft.pdf)** — Deliberately written to be understandable. Read it once properly and consensus stops being mysterious.
- **[raft.github.io visualization](https://raft.github.io/)** — Watch leader election and log replication happen. Ten minutes well spent before the paper.


#### Understand what breaks

- **[Jepsen analyses](https://jepsen.io/analyses)** — Real databases, real partitions, documented failures. Read the Cassandra, MongoDB and etcd reports.
- **[Jepsen framework](https://github.com/jepsen-io/jepsen)** — How the testing actually works.
- **[Fallacies of distributed computing](https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing)** — Eight assumptions that are always wrong. Short, and worth revisiting periodically.


#### First systems to run and read

- **[etcd](https://etcd.io/docs/)** — A small, real, Raft-backed store you can run locally and inspect.
- **[Redis](https://redis.io/docs/latest/)** — Readable C, clear docs, and the clustering model is a good first look at sharding.
- **[NATS](https://docs.nats.io/)** — Simplest serious messaging system to get running.
- **[RabbitMQ tutorials](https://www.rabbitmq.com/docs)** — The six tutorials cover messaging patterns better than most books.
- **[Apache Kafka documentation](https://kafka.apache.org/documentation/)** — Read the 'Design' section specifically — it is effectively a paper.


#### Academic grounding, early

- **[Lamport's publications](https://lamport.azurewebsites.net/pubs/pubs.html)** — Start with 'Time, Clocks and the Ordering of Events'. Short, and foundational to everything after.
- **[Kleppmann's Cambridge lecture notes](https://www.cl.cam.ac.uk/teaching/2122/ConcDisSys/dist-sys-notes.pdf)** — A complete free course text, more formal than DDIA and much shorter than a textbook.
- **[crdt.tech](https://crdt.tech/)** — The entry point for eventual consistency done properly.


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which papers matter. Curated by subfield, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language. No longer updated; still one of the best free CS resources.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. The 'highly influential citations' filter is the fastest way to find what a paper actually changed.
- **[Unpaywall](https://unpaywall.org/)** — Install the extension. Most paywalls stop appearing, legally, because the author deposited a copy.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF. Swap arxiv.org/abs for ar5iv.labs.arxiv.org/html.


### Advanced

*31 resources across 6 topics.*


#### Implement consensus yourself

- **[MIT 6.824 Raft labs](https://pdos.csail.mit.edu/6.824/)** — Lab 2 is Raft from scratch against an adversarial test suite. Difficult and worth it.
- **[etcd Raft library](https://github.com/etcd-io/raft)** — Read this after your own implementation works. The gap is educational.
- **[hashicorp/raft](https://github.com/hashicorp/raft)** — A second production implementation with different design choices.
- **[braft](https://github.com/baidu/braft)** — Industrial C++ Raft, for a third perspective.
- **[Raft extended paper](https://raft.github.io/raft.pdf)** — Return to sections 5-8 once you have implementation scars.
- **[Paxos Made Simple](https://www.microsoft.com/en-us/research/publication/paxos-made-simple/)** — Understand the lineage Raft reacted against.


#### Formal methods & verification

- **[TLA+](https://lamport.azurewebsites.net/tla/tla.html)** — Specify your protocol and let the model checker find the interleaving you missed.
- **[Learn TLA+](https://learntla.com/)** — The practical on-ramp. Start here, then go to Lamport's materials.
- **[TLA+ tools](https://github.com/tlaplus/tlaplus)** — TLC, the Toolbox, and the standard modules.
- **[Jepsen](https://github.com/jepsen-io/jepsen)** — Empirical verification as the complement to formal specification.
- **[FoundationDB](https://github.com/apple/foundationdb)** — Deterministic simulation testing — arguably the most rigorous testing approach in any open database.


#### Production system internals

- **[Cassandra source](https://github.com/apache/cassandra)** — Dynamo-style replication, gossip and hinted handoff in a mature codebase.
- **[ScyllaDB](https://github.com/scylladb/scylladb)** — The same model rebuilt shard-per-core on Seastar. Read the Seastar design notes.
- **[Kafka](https://github.com/apache/kafka)** — KRaft replaced ZooKeeper; read the KIPs for the migration reasoning.
- **[Pulsar](https://github.com/apache/pulsar)** — Storage and serving separated via BookKeeper. A deliberate contrast to Kafka.
- **[FoundationDB docs](https://apple.github.io/foundationdb/)** — Strictly serializable transactions over a distributed store, documented honestly about limits.
- **[MongoDB source](https://github.com/mongodb/mongo)** — Replica set elections and the write-concern machinery.


#### Stream processing & state

- **[Apache Flink](https://nightlies.apache.org/flink/flink-docs-stable/)** — The checkpointing and exactly-once semantics chapters are the real material.
- **[Apache Beam](https://beam.apache.org/documentation/)** — Event time, watermarks and triggers, formalized.
- **[Temporal](https://docs.temporal.io/)** — Durable execution — read the architecture docs, not just the SDK tutorials.
- **[Ray](https://docs.ray.io/en/latest/)** — Distributed compute with a task and actor model; readable architecture docs.
- **[Apache Spark](https://spark.apache.org/docs/latest/)** — Shuffle, lineage and recovery.


#### Consistency models & theory

- **[Kleppmann's Cambridge notes](https://www.cl.cam.ac.uk/teaching/2122/ConcDisSys/dist-sys-notes.pdf)** — Precise definitions of the consistency models that blog posts blur together.
- **[crdt.tech](https://crdt.tech/)** — The research index for CRDTs and their implementations.
- **[Lamport publications](https://lamport.azurewebsites.net/pubs/pubs.html)** — Byzantine Generals and the sequential consistency papers.
- **[dancres/Pages](https://dancres.github.io/Pages/)** — An annotated paper list organised by topic — use it to plan reading.
- **[awesome-distributed-systems](https://github.com/theanalyst/awesome-distributed-systems)** — Broader index including talks and books.
- **[PingCAP talent-plan](https://github.com/pingcap/talent-plan)** — Structured courses building a distributed KV store in Rust and Go.


#### Research venues

- **[USENIX OSDI](https://www.usenix.org/conference/osdi25)** — Free papers, and the main venue for systems work.
- **[ACM SOSP](https://sosp.org/)** — Alternates with OSDI.
- **[Jepsen analyses](https://jepsen.io/analyses)** — Not peer-reviewed, but more consequential in practice than most papers.


---

## If you only do three things

1. **Do Gossip Glomers** (fly.io/dist-sys). Six verified challenges on Maelstrom. Free, and more effective than any book.
2. **Do MIT 6.824's Raft lab.** Implement consensus against an adversarial test suite until it passes.
3. **Read three Jepsen analyses.** Your intuitions about what databases guarantee will not survive, and that is the point.

## Honest notes

- **Build before you read.** Distributed systems theory sticks only after you have debugged a partition yourself.
- **Kafka's 'Design' documentation section is effectively a research paper.** Most people skip it and read tutorials instead.
- **Read the Raft paper, not a summary.** It was explicitly written for understandability and summaries lose the parts that matter.
- **Valkey, not Redis, is now the default** in several Linux distributions following the 2024 licence change. Check which you are documenting.
- **FoundationDB's deterministic simulation testing** is the most underappreciated engineering idea in this list.
- **TLA+ is less intimidating than it looks** if you start at learntla.com rather than with Lamport's own materials.

---

## Related sections of this book

- [Distributed Systems](../distributed/overview.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other six topic indexes
