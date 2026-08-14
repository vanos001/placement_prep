# Topic Backlog

> Auto-maintained by research agents. Topics discovered during expansion that need coverage.
> Priority: HIGH (interview-critical) | MEDIUM (important) | LOW (nice-to-have)
> Last updated: 2026-08-13 (dev pull audit)

## Dev pull audit — 2026-08-13

- Pulled the latest `dev` expansion and repaired ten missing Summary targets
  plus four stale relative links. All pulled pages are now Summary-reachable.
- Remaining work is content depth/references review, not broken navigation.

## Software Engineering pages — 2026-08-13

- Added dedicated `testing.md`, `devops.md`, and `CONTRIBUTING.md` under
  `src/software-engineering/` (previously those links were redirected to the
  general `testing/` and `cloud/cicd/` sections and a GitHub URL).

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

## Completed (since 2026-08-05) — Updated 2026-08-13

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

## NEWLY COMPLETED (2026-08-13 — Parallel Agent Batch)

### Completely New Sections Added:
- **Git** ✅ `src/git/` — 15 files: internals, fundamentals, branching, rebasing, stashing, advanced ops, remotes, tags, hooks, workflows, GitHub, interview questions, cheat sheet
- **Software Engineering** ✅ `src/software-engineering/` — 10 files: SDLC, Agile, requirements, design (SOLID), code quality, documentation, project management, metrics, team dynamics
- **Programming Fundamentals** ✅ `src/programming-fundamentals/` — 10 files: variables/types, scope/lifetime, functions, error handling, type systems, memory model, I/O, modules
- **Security & Cryptography** ✅ `src/security/` — 7 files: authentication (OAuth/OIDC/JWT), authorization (RBAC/ABAC), web security (OWASP), cryptography (AES/RSA/TLS), secrets management
- **Machine Coding** ✅ `src/machine-coding/` — 10 files: parking lot, elevator, library, splitwise, rate limiter, LRU cache, task scheduler
- **Data Engineering** ✅ `src/data-engineering/` — 7 files: Spark, Kafka, Airflow, Parquet/Avro/ORC, data quality
- **Search Engines** ✅ `src/search/` — 5 files: inverted indexes, TF-IDF/BM25, Elasticsearch, vector search
- **Aptitude** ✅ `src/aptitude/` — 11 files: percentages, ratios, averages, profit/loss, time/work, speed/distance, probability, number systems, logical reasoning, data interpretation
- **Placement Preparation** ✅ `src/placement-preparation/` — 6 files: campus process, OA, technical/HR interview, group discussion
- **Resume & Career** ✅ `src/resume/` — 7 files: structure, bullet writing, projects, ATS optimization
- **Behavioral Interviews** ✅ `src/behavioral-interviews/` — 5 files: STAR method, 30+ questions, company fit, scenarios
- **Communication** ✅ `src/communication/` — 4 files: technical, interview, written communication
- **Practical Programming Problems** ✅ `src/practical-problems/` — 6 files: parsers, CLI tools, file processing, concurrent problems
- **DBMS Interview Problems** ✅ `src/dbms/interview-problems/` — 6 files: classic SQL, window functions, joins, optimization, concurrency

## REMAINING — MEDIUM Priority (Updated)

### Operating Systems — Partially Done
- ~~Linux Kernel Modules — loading, unloading, parameters (covered briefly; expand into a page)~~ ✅ Done `os/kernel/modules.md`
- **Linux Tracing Deep Dive** — ftrace, kprobes, perf, eBPF, and advanced tracing are covered in the integrated Linux track; an LTTng comparison remains optional
- **Memory Barriers Deep Dive** — C++20/Java/Go memory models (acquire/release, seq_cst) — dedicated page missing, currently in OS sync

### Networks — Partially Done
- ~~HTTP/3 QPACK — header compression specifics~~ ✅ Done `networks/http/qpack.md`
- ~~Service Mesh internals — Istio/Envoy xDS protocol, sidecar dataplane~~ ✅ Done `backend/containers/xds-protocol.md`
- ~~eBPF Networking Deep Dive~~ ✅ Done `networks/ebpf-networking.md` (2026-08-12): XDP, TC, socket hooks, maps, AF_XDP, Cilium, CO-RE, and observability

### Languages / Frameworks — Partially Done
- ~~Go web frameworks — Gin/Echo/Fiber comparison~~ ✅ Done `languages/go/web-frameworks.md`
- ~~Rust Async Runtimes~~ ✅ Done `languages/rust/async-runtimes.md` (2026-08-12): Tokio, smol, async-std, Glommio, Monoio, Embassy, blocking and cancellation
- **Python Free-Threaded (3.13t) Deep Dive** — GIL removal, free-threaded build
- **Java Loom Virtual Threads** — expand java.md with Project Loom

### Backend / Storage / Concurrency — Newly Discovered
- ~~Tiered Storage and Data Temperature~~ ✅ Done `storage/tiered-storage.md` (2026-08-12): hot/warm/cold, RocksDB, object lifecycle, caches, recovery
- ~~Storage: SSTable Format — data blocks, index, bloom, footer, compression~~ ✅ Done `storage/sstable.md` (2026-08-09): BlockBasedTable diagram, Index/Bloom/Footer 48 bytes magic, partitioned index/filter, read path, compression
- ~~Storage: BlobDB — separation of small vs large values~~ ✅ Done `storage/blobdb.md` (2026-08-09): WiscKey, BlobIndex file_no/offset/size, GC age cutoff 0.25, WA 1.4-1.7 vs 6.1-6.8 75% lower, options enable_blob_files/min_blob_size
- **Storage: Ceph CRUSH/RADOS Deep Dive** — CRUSH algorithm, placement groups, RADOS (still TODO)
- ~~Storage: NVMe over Fabrics~~ ✅ Done `storage/nvmeof.md` (2026-08-12): TCP/RDMA, discovery, queues, multipathing, security, observability
- ~~Concurrency: Work-Stealing Scheduler — Go scheduler work-stealing, Java ForkJoinPool, Rust Tokio~~ ✅ Done `concurrency/work-stealing.md` (2026-08-09): LIFO owner head vs FIFO thief tail, Go GMP P local 256 + global, Java ForkJoinPool WorkQueue 4096, Tokio 256 ring + injection queue
- ~~Concurrency: ABA Problem & Memory Reclamation~~ ✅ Done `concurrency/aba-problem.md` (2026-08-12): tagged pointers, hazard pointers, EBR, RCU, reference counting, memory ordering, C++26 safe-reclamation references
- ~~Concurrency: Memory Model — C++/Java/Go memory models, acquire/release, data races~~ ✅ Done `concurrency/memory-model.md` (2026-08-09): TSO vs weak ARM, DRF-SC happens-before, C++11 6 orders, Java volatile total order vs VarHandle acq/rel, Go channel happens-before, Rust Send/Sync, store buffering litmus

### Interview / System Design — Newly Discovered
- ~~GraphQL Federation~~ ✅ Done `backend/api/graphql-federation.md` (2026-08-12): entities, composition, directives, query planning, governance
- ~~API Versioning Strategies — URL vs header vs content negotiation, Stripe example~~ ✅ Done `backend/api/versioning.md` (2026-08-09): 6 strategies table, URL path safest default, date-based Stripe pinning compatibility layer, decision flowchart, Deprecation/Sunset headers
- ~~Rate Limiting Algorithms Deep Dive — token bucket vs leaky bucket vs sliding window logs vs sliding window counter~~ ✅ Done `backend/api/rate-limiting.md` (2026-08-09): 5 algos fixed vs sliding log O(n) exact vs sliding counter 2 keys ~1% err vs token bucket HASH burst vs leaky queue steady, comparison table, Redis Lua token bucket script, decision tree
- ~~Distributed Lock Deep Dive~~ ✅ Done `distributed/fundamentals/distributed-locks.md` (2026-08-12): leases, fencing tokens, Redis/Redlock, ZooKeeper, etcd, and alternatives
- ~~Change Data Capture & Outbox Pattern~~ ✅ Done `backend/patterns/cdc-outbox.md` (2026-08-12): dual-write failure, Debezium, WAL retention, idempotency, ordering

## LOW Priority

- **Quantum Computing** — qubits, gates, algorithms (curiosity, not interview-critical)
- **Blockchain** — consensus PoW/PoS, smart contracts, Merkle trees (could be `arch/blockchain.md` or separate)
- **Edge Computing** — CDN compute, edge functions (covered in cdn/edge.md; could expand with Cloudflare Workers, Fastly Compute@Edge)
- ~~Observability Deep Dive~~ ✅ Done `backend/observability/opentelemetry.md` (2026-08-12): signals, propagation, Collector, semantic conventions, sampling, cardinality

## NEWLY COMPLETED (2026-08-15 — OpenClaw expansion batch)

- **Master topic index** ✅ `src/index.md` — added the 1 660-line master topic database
  that was previously missing from the repo, covering all 50 sections from Algorithms
  through Interview Meta Topics. Wired into `SUMMARY.md` at the top navigation and the
  Meta section.
- **Java Virtual Threads deep dive** ✅ `src/languages/java/virtual-threads.md`
  expanded from 139 → 261 lines. Added JEP timeline (JDK 19 through 25), continuation-
  on-heap internals, three creation patterns, structured-concurrency API churn note
  (JEP 499 / 505), scoped-values rationale, migration playbook, comparison table vs
  goroutines / Kotlin coroutines / Reactor, 8 interview questions.
- **Python Free-Threaded deep dive** ✅ `src/languages/python/free-threaded.md`
  expanded from 148 → 235 lines. Added PEP 779, biased-locking internals, immortal
  objects (PEP 683), per-object critical sections (`Py_BEGIN_CRITICAL_SECTION`),
  Cython `freethreading=True` directive, C-extension compatibility table, runtime
  introspection (`sys._is_gil_enabled`, `-X gil=0`), comparison vs Java Loom / Go /
  Ruby Ractor, 7 interview questions.
- **Ceph CRUSH/RADOS deep dive** ✅ `src/storage/ceph-crush.md` expanded from
  181 → 340 lines. Added straw2 bucket algorithm explanation, CRUSH rule step
  semantics, upmap balancer override, PG peering state machine (Mermaid state
  diagram), Bluestore internals (WAL/BlockDB/blob sharing), replication vs erasure
  coding table, upper-layer services (RBD/CephFS/RGW), performance characteristics,
  comparison vs HDFS/MinIO/S3, 9 interview questions, references to Weil SC 2006
  paper and doctoral dissertation.
- **Formal Methods** ✅ `src/cs-theory/formal-methods.md` — new 282-line page
  covering index.md Section 36. TLA+ (with Counter example, AWS DynamoDB case
  study), Alloy (with file-system example), Coq (CompCert, Four Colour Theorem),
  Lean (Mathlib, Verdi), Isabelle/HOL (seL4), Dafny (binary search auto-active
  verification), model checking (BDD, BMC, partial-order, symmetry), symbolic
  execution (KLEE/angr/SAGE), abstract interpretation (Astrée, Rust borrow
  checker), distributed-systems verification workflow, trade-offs table, 8
  interview questions.

## Decisions / Notes

- Keep autonomous loop adding topics based on coverage lowest first: Storage (45%) and Concurrency (48%) still lowest → prioritize WAL, LSM compaction (done), next SSTable, BlobDB, RCU (done), memory barriers, work-stealing.
- After storage/concurrency reaches 60%, move to Frameworks (60%) and Distributed (55%) and Cloud (60%)
- Update knowledge graph each batch to keep cross-links
- Maintain 100% mermaid pass, 0 broken links, build clean — fix regressions immediately after merging dev
- Next candidates: Serialization (index §39, partially covered — protobuf/Avro/Cap'n Proto comparison page would unify scattered content); API versioning is already covered; Quantum Computing (§35) is low-priority.
