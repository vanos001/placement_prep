# Topic Backlog

> Auto-maintained by research agents. Topics discovered during expansion that need coverage.
> Priority: HIGH (interview-critical) | MEDIUM (important) | LOW (nice-to-have)
> Last updated: 2026-08-12 (research loop batch 2)

## Integration completed — 2026-08-12

- **Linux deep dive (`lb2`)** — integrated 444 educational pages under
  `src/linux/`, with source navigation adapted to the parent Summary.
- **Linux tools** — added a focused guide for `find`, `xargs`, text filters,
  process/system-call tools, storage inspection, networking, HTTP debugging,
  SSH/rsync, `jq`, `make`, and `tmux`, including interview questions,
  safety notes, and official references.
- **DSA track (`dsa_book_2`)** — integrated 193 educational pages and
  appendices under `src/dsa/`, from foundations to advanced algorithms.
- **Integrity gate** — 0 broken links, Summary navigation OK, and 4,387/4,387
  Mermaid diagrams pass both the heuristic and Mermaid v11 parser checks.

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
- **Linux Tracing Deep Dive** — ftrace, kprobes, perf, eBPF, and advanced tracing are covered in the integrated Linux track; an LTTng comparison remains optional
- **Memory Barriers Deep Dive** — C++20/Java/Go memory models (acquire/release, seq_cst) — dedicated page missing, currently in OS sync

### Networks — Partially Done
- ~~HTTP/3 QPACK — header compression specifics~~ ✅ Done `networks/http/qpack.md`
- ~~Service Mesh internals — Istio/Envoy xDS protocol, sidecar dataplane~~ ✅ Done `backend/containers/xds-protocol.md`
- **eBPF Networking Deep Dive** — XDP, TC, sockmap, and Cilium datapath are covered in `linux/kernel/networking/`; add a focused comparison only if interviews require it

### Languages / Frameworks — Partially Done
- ~~Go web frameworks — Gin/Echo/Fiber comparison~~ ✅ Done `languages/go/web-frameworks.md`
- **Rust Async Runtimes** — Tokio vs async-std vs smol comparison — dedicated page missing, Tokio exists but comparison missing
- **Python Free-Threaded (3.13t) Deep Dive** — GIL removal, free-threaded build
- **Java Loom Virtual Threads** — expand java.md with Project Loom

### Backend / Storage / Concurrency — Newly Discovered
- ~~Storage: SSTable Format — data blocks, index, bloom, footer, compression~~ ✅ Done `storage/sstable.md` (2026-08-09): BlockBasedTable diagram, Index/Bloom/Footer 48 bytes magic, partitioned index/filter, read path, compression
- ~~Storage: BlobDB — separation of small vs large values~~ ✅ Done `storage/blobdb.md` (2026-08-09): WiscKey, BlobIndex file_no/offset/size, GC age cutoff 0.25, WA 1.4-1.7 vs 6.1-6.8 75% lower, options enable_blob_files/min_blob_size
- **Storage: Ceph CRUSH/RADOS Deep Dive** — CRUSH algorithm, placement groups, RADOS (still TODO)
- ~~Storage: NVMe over Fabrics~~ ✅ Done `storage/nvmeof.md` (2026-08-12): TCP/RDMA, discovery, queues, multipathing, security, observability
- ~~Concurrency: Work-Stealing Scheduler — Go scheduler work-stealing, Java ForkJoinPool, Rust Tokio~~ ✅ Done `concurrency/work-stealing.md` (2026-08-09): LIFO owner head vs FIFO thief tail, Go GMP P local 256 + global, Java ForkJoinPool WorkQueue 4096, Tokio 256 ring + injection queue
- ~~Concurrency: ABA Problem & Memory Reclamation~~ ✅ Done `concurrency/aba-problem.md` (2026-08-12): tagged pointers, hazard pointers, EBR, RCU, reference counting, memory ordering, C++26 safe-reclamation references
- ~~Concurrency: Memory Model — C++/Java/Go memory models, acquire/release, data races~~ ✅ Done `concurrency/memory-model.md` (2026-08-09): TSO vs weak ARM, DRF-SC happens-before, C++11 6 orders, Java volatile total order vs VarHandle acq/rel, Go channel happens-before, Rust Send/Sync, store buffering litmus

### Interview / System Design — Newly Discovered
- ~~API Versioning Strategies — URL vs header vs content negotiation, Stripe example~~ ✅ Done `backend/api/versioning.md` (2026-08-09): 6 strategies table, URL path safest default, date-based Stripe pinning compatibility layer, decision flowchart, Deprecation/Sunset headers
- ~~Rate Limiting Algorithms Deep Dive — token bucket vs leaky bucket vs sliding window logs vs sliding window counter~~ ✅ Done `backend/api/rate-limiting.md` (2026-08-09): 5 algos fixed vs sliding log O(n) exact vs sliding counter 2 keys ~1% err vs token bucket HASH burst vs leaky queue steady, comparison table, Redis Lua token bucket script, decision tree
- **Distributed Lock Deep Dive** — Redlock controversy, fenced tokens, etcd locks (distributed-lock.md exists, could expand)
- ~~Change Data Capture & Outbox Pattern~~ ✅ Done `backend/patterns/cdc-outbox.md` (2026-08-12): dual-write failure, Debezium, WAL retention, idempotency, ordering

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
