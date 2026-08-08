# Topic Backlog

> Auto-maintained by research agents. Topics discovered during expansion that need coverage.
> Priority: HIGH (interview-critical) | MEDIUM (important) | LOW (nice-to-have)
> Last updated: 2026-08-09 (autonomous loop, after dev merge + new chapters)

## Completed (since 2026-08-05) — Updated 2026-08-09

The following previously-backlogged topics now have dedicated coverage:

- **Languages**: C (8 files incl. ecosystem), C++ (8 incl. ecosystem), Rust (9 + ecosystem), Java (incl. GC `java/gc.md` + ecosystem), Python (9 + ecosystem), Go (6 incl. scheduler 5 files → 6 with web-frameworks), JavaScript/Node/V8 (3 → expanded nodejs 414 lines, v8 363 lines), OCaml (incl. ecosystem/tooling), **TypeScript** (type system, generics), **Go Web Frameworks** (NEW 2026-08-09: Gin/Echo/Fiber comparison with prod benchmarks, allocation analysis, decision flowchart)
- **Frameworks**: Spring Boot, FastAPI, **Django**, Express.js, **React**, **Next.js**, Tokio, PyTorch, **Vue & Angular** (combined page exists, could split)
- **Backend**: REST, gRPC, GraphQL, JWT/OAuth/sessions, Docker, Kubernetes, CI/CD (GitHub Actions, GitOps), Redis, Kafka, RabbitMQ, NATS, service mesh (`service-mesh.md` + NEW `xds-protocol.md` 2026-08-08: ADS, LDS/RDS/CDS/EDS/SDS, protobuf not YAML, SotW vs Delta), event sourcing, CQRS, idempotency, webhooks, connection pools, testing, **xDS Protocol** (NEW)
- **ML/LLM**: Transformers, attention, GPT/BERT, fine-tuning, RLHF/DPO, inference optimization (KV cache, quantization, speculative decoding, batching), RAG, vector databases, LLM security (OWASP Top 10), distributed training (DDP/FSDP/ZeRO/TP/PP), diffusion, MoE, **Probabilistic Data Structures** (NEW 2026-08-09: Bloom 10 bits/elem @1%, HLL 12KB fixed ~2%, CMS overestimates, use cases Cassandra/Chrome/BigQuery)
- **OS**: eBPF, io_uring, Linux kernel internals, namespaces, cgroups v2, **kernel modules** (NEW 2026-08-08: LKM lifecycle, insmod/modprobe, params, sysfs, signing/taint), **kernel tracing** (NEW 2026-08-09: ftrace, kprobes/kretprobes 0.05us vs 0.5us, tracepoints, perf, eBPF bpftrace one-liners), **RCU** (NEW 2026-08-09: grace period, publish-subscribe, quiescent states, checklist)
- **Networks**: QUIC, HTTP/3 (`http3.md`), **QPACK RFC 9204** (NEW 2026-08-08: static 99 vs dynamic table, encoder/decoder streams, RIC/Base, blocking), TLS deep dive (1.3 handshake, ECDHE, mTLS, CT), **Bluetooth** (NEW: PAN profiles), eBPF networking
- **DBMS**: query optimization (cost model, join algorithms), storage engines (WAL, LSM), distributed SQL (CockroachDB/TiDB/Spanner), OLTP vs OLAP, **WAL** (NEW 2026-08-09: LSN/pageLSN, ARIES 3 phases, CLR, group commit, fuzzy checkpoint), **LSM Compaction** (NEW 2026-08-09: leveled vs tiered vs hybrid, WA 10-30× leveled, RocksDB tuning knobs, SAG), **Congestion Control Overview** (NEW: congestion-control/README.md wired)
- **Cloud**: autoscaling, disaster recovery & multi-region, IAM & secrets management, Kubernetes operators, **Kubernetes operators** (already done)
- **Arch**: CUDA programming (parallelism/cuda.md), **Modern Processors** expanded (x86-64 Xeon/EPYC, ARM Neoverse, RISC-V) via dev merge
- **Interview**: streaming analytics pipeline system design (real-world/streaming-pipeline.md), **Probabilistic Data Structures for System Design** (NEW), real-world examples Netflix/Twitter/Uber/WhatsApp/YouTube/Instagram/Dropbox/Google Search/distributed lock
- **Storage**: HDD/SSD/NVMe/object/block/file/distributed/Ceph/erasure-coding (10 files) → 12 files with **WAL** + **LSM Compaction** + Bluetooth fix, still low coverage (45%)
- **Concurrency**: fork-join/thread-pools/producer-consumer/readers-writers/async-await/futures/coroutines/lock-free/transactional-memory/go-channels/rust-ownership/java/python-gil (14) → 15 with **RCU**, still low (48%)
- **OOP**: coupling, cohesion & design principles (lld/coupling-cohesion-principles.md)
- **Security**: TLS deep dive, mTLS, certificate transparency already; auth expanded (OAuth, JWT, session, mTLS)

## REMAINING — MEDIUM Priority (Updated)

### Operating Systems — Partially Done
- ~~Linux Kernel Modules — loading, unloading, parameters (covered briefly; expand into a page)~~ ✅ Done `os/kernel/modules.md`
- **Linux Tracing Deep Dive** — ftrace function_graph advanced, LTTng comparison (partially done `tracing.md`, could add LTTng page)
- **Memory Barriers Deep Dive** — C++20/Java/Go memory models (acquire/release, seq_cst) — dedicated page missing, currently in OS sync

### Networks — Partially Done
- ~~HTTP/3 QPACK — header compression specifics~~ ✅ Done `networks/http/qpack.md`
- ~~Service Mesh internals — Istio/Envoy xDS protocol, sidecar dataplane~~ ✅ Done `backend/containers/xds-protocol.md`
- **eBPF Networking Deep Dive** — XDP, TC, sockmap, Cilium datapath — could be `networks/ebpf-networking.md` or expand `os/kernel/ebpf.md`

### Languages / Frameworks — Partially Done
- ~~Go web frameworks — Gin/Echo/Fiber comparison~~ ✅ Done `languages/go/web-frameworks.md`
- **Rust Async Runtimes** — Tokio vs async-std vs smol comparison — dedicated page missing, Tokio exists but comparison missing
- **Python Free-Threaded (3.13t) Deep Dive** — GIL removal, free-threaded build
- **Java Loom Virtual Threads** — expand java.md with Project Loom

### Backend / Storage / Concurrency — Newly Discovered
- **Storage: SSTable Format** — data blocks, index, bloom, footer, compression (currently referenced as ./sstable.md → fixed to file-organization.md, but should be dedicated `storage/sstable.md`)
- **Storage: BlobDB** — separation of small vs large values in LSM to reduce WA
- **Storage: Ceph CRUSH/RADOS Deep Dive** — CRUSH algorithm, placement groups, RADOS
- **Storage: NVMe over Fabrics** — NVMe-oF TCP/RDMA
- **Concurrency: Work-Stealing Scheduler** — Go scheduler work-stealing, Java ForkJoinPool, Rust Tokio work-stealing
- **Concurrency: ABA Problem & Memory Reclamation** — hazard pointers vs RCU vs epoch
- **Concurrency: Memory Model** — C++/Java/Go memory models, acquire/release, data races

### Interview / System Design — Newly Discovered
- **API Versioning Strategies** — URL vs header vs content negotiation, Stripe example
- **Rate Limiting Algorithms Deep Dive** — token bucket vs leaky bucket vs sliding window logs vs sliding window counter, Redis Cell
- **Distributed Lock Deep Dive** — Redlock controversy, fenced tokens, etcd locks (distributed-lock.md exists, could expand)
- **Change Data Capture & Outbox Pattern** — Debezium, transactional outbox

## LOW Priority

- **Quantum Computing** — qubits, gates, algorithms (curiosity, not interview-critical)
- **Blockchain** — consensus PoW/PoS, smart contracts, Merkle trees (could be `arch/blockchain.md` or separate)
- **Edge Computing** — CDN compute, edge functions (covered in cdn/edge.md; could expand with Cloudflare Workers, Fastly Compute@Edge)
- **Observability Deep Dive** — OpenTelemetry traces/metrics/logs correlation, exemplar

## Decisions / Notes

- Keep autonomous loop adding topics based on coverage lowest first: Storage (45%) and Concurrency (48%) still lowest → prioritize WAL, LSM compaction (done), next SSTable, BlobDB, RCU (done), memory barriers, work-stealing.
- After storage/concurrency reaches 60%, move to Frameworks (60%) and Distributed (55%) and Cloud (60%)
- Update knowledge graph each batch to keep cross-links
- Maintain 100% mermaid pass, 0 broken links, build clean — fix regressions immediately after merging dev
