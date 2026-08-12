# Coverage Dashboard

> Auto-generated tracking of content coverage across all subjects.
> Last updated: 2026-08-12 (integration batch)

## Summary

| Subject | Pages | Interview Qs | Diagrams | Coverage |
|---------|-------|-------------|----------|----------|
| Operating Systems | 123 | 220+ | 385+ | 82% |
| DBMS | 94 | 190+ | 295+ | 72% |
| Computer Networks | 96 | 180+ | 265+ | 73% |
| Computer Architecture | 82 | 160+ | 205+ | 68% |
| Machine Learning (ml+llm) | 177 | 320+ | 400+ | 70% |
| Distributed Systems | 38 | 85+ | 85+ | 58% |
| Interview Prep | 96 | 540+ | 125+ | 76% |
| Programming Languages | 58 | 310+ | 75+ | 88% |
| Frameworks | 9 | 100+ | 25+ | 60% |
| Backend Engineering | 37 | 250+ | 250+ | 76% |
| Concurrency | 18 | 65+ | 47+ | 58% |
| Storage | 16 | 50+ | 42+ | 55% |
| Cloud & DevOps | 26 | 80+ | 50+ | 60% |
| Linux Deep Dive (`lb2`) | 446 | — | 1,531 | Integrated |
| DSA Track (`dsa_book_2`) | 194 | — | 16 | Integrated |

## Overall Metrics

- **Total markdown files**: 1,538
- **Total Mermaid diagrams**: 4,394
- **Total size**: 26 MB (src/)
- **Build status**: ✅ Full constrained build clean (mdBook 0.4.52, search index disabled for sandbox); normal search-enabled build is OOM-limited in this sandbox

## New Sections Added (2026-08-08 to 2026-08-09)

### Batch 1 — Kernel, Networks, Backend, Lang, Interview (3 files)
- **Kernel Modules** (`os/kernel/modules.md`) — LKM lifecycle, insmod/modprobe, taint, eBPF vs LKM
- **QPACK RFC 9204** (`networks/http/qpack.md`) — static 99 vs dynamic, encoder/decoder streams, RIC/Base, HPACK vs QPACK
- **xDS Protocol** (`backend/containers/xds-protocol.md`) — ADS, LDS/RDS/CDS/EDS/SDS, protobuf not YAML, SotW vs Delta, Istio mapping

### Batch 2 — Go, Probabilistic, Tracing (3 files)
- **Go Web Frameworks** (`languages/go/web-frameworks.md`) — Gin 76k rps vs Echo 72k vs Fiber 89k raw, 3.2k with DB (<5% diff), 0-1 alloc Fiber vs 3-4 Gin, decision flowchart
- **Probabilistic Data Structures** (`interview/system-design/probabilistic-data-structures.md`) — Bloom 10 bits/elem @1% 1B=1.2GB vs HashSet 50GB, HLL 12KB fixed ~2% err, CMS overestimates, Python impl, Cassandra/Chrome/BigQuery use cases
- **Kernel Tracing** (`os/kernel/tracing.md`) — ftrace, kprobes 0.05us vs 0.5us, tracepoints, perf, bpftrace one-liners `kprobe:do_sys_open`

### Batch 3 — Storage & Concurrency Core (3 files)
- **WAL** (`storage/wal.md`) — rule LSN/pageLSN, STEAL/NO-FORCE, ARIES Analysis/REDO/UNDO, CLR, group commit, fuzzy checkpoints
- **LSM Compaction** (`storage/lsm-compaction.md`) — leveled 10-30× WA vs tiered 2-4×, RA/SA trilemma, RocksDB knobs table, SAG, write stall
- **RCU** (`concurrency/rcu.md`) — publish-subscribe, grace period 2 barriers, quiescent states, rcu_dereference store-release, checklist

### Batch 4 — Backend API & Storage Deep Dive (3 files) — Latest
- **API Versioning** (`backend/api/versioning.md`) — 6 strategies table URL Path dominant (safest default) vs query param vs header vs Accept vs date-based Stripe pinning vs no versioning evolution, caching Vary header, decision flowchart, Gin groups & Echo middleware & Deprecation/Sunset RFC 9745, 5 Qs, refs apiscout.dev & knowledgelib.io & oneuptime
- **Rate Limiting Algorithms** (`backend/api/rate-limiting.md`) — 5 algos fixed window 1 key approx 2× burst vs sliding log SORTED SET O(n) exact vs sliding counter 2 keys near-exact ~1% err best balance vs token bucket HASH 2 fields burst tolerant Stripe 100/sec burst 1000 vs leaky bucket queue steady, comparison table, distributed Redis Lua atomic token bucket script, local+sync hybrid, gateway Envoy RateLimitService 429, decision tree flowchart, refs Redis official tutorial & AlgoMaster & Layrs.me
- **SSTable Format** (`storage/sstable.md`) — BlockBasedTable diagram Data Block 4KB compressed, Index Block last key+offset, Filter Block Bloom per block, Footer 48 bytes magic, read path flowchart Index→Bloom→Data, building flush sequenceDiagram, partitioned index/filter for 256MB SST 0.5/5MB on-demand, tuning table, 5 Qs, refs Adam Comer blog & LevelDB Explained & RocksDB wiki partitioned filters

### Batch 7 — NVMe-oF, CRDTs, and CDC/outbox (3 files) — 2026-08-12
- **NVMe over Fabrics** (`storage/nvmeof.md`) — NVMe/TCP and NVMe/RDMA
  transport trade-offs, discovery, queueing, multipathing, security, and
  Linux operations.
- **Conflict-Free Replicated Data Types** (`distributed/fundamentals/crdts.md`)
  — SEC, CvRDT/CmRDT/delta CRDTs, causality, deletes, local-first, and OT
  comparison.
- **CDC and Transactional Outbox** (`backend/patterns/cdc-outbox.md`) —
  atomic local events, Debezium, logical decoding, idempotency, ordering,
  WAL retention, cleanup, and polling alternatives.

### Batch 6 — Safe Memory Reclamation (1 file) — 2026-08-12
- **ABA Problem and Safe Memory Reclamation** (`concurrency/aba-problem.md`) —
  CAS ABA interleaving, tagged/versioned pointers, hazard pointers, EBR,
  RCU, reference counting, memory ordering, implementation choices, and
  interview questions; references Linux kernel docs, WG21 C++ safe-reclamation
  papers/current draft, IBM, Boost, Folly, and Crossbeam.

### Batch 5 — Concurrency Advanced & BlobDB (3 files) — Latest
- **Work-Stealing Scheduler** (`concurrency/work-stealing.md`) — LIFO owner head hot cache vs FIFO thief tail cold, Go GMP P local 256 + global lock + random steal, Java ForkJoinPool WorkQueue 4096, Rust Tokio per-worker 256 ring + injection queue half-move cooperative, fairness random victim + barrier, global queue vs work-stealing table, Qs, refs Wikipedia Cilk/Java ForkJoin/.NET/Tokio, dev.to pattern, rustz2h deep dive, Andrew Odendaal architecture
- **Memory Model** (`concurrency/memory-model.md`) — TSO vs weak ARM/RISC-V, store buffering litmus r1=0 r2=0 on x86 YES, DRF-SC happens-before, C++11 6 orders relaxed/acquire/release/acq_rel/seq_cst/consume deprecated, release synchronizes with acquire example n=23, modification order, SC-DRF, Java volatile total order vs VarHandle acq/rel, Go channel send happens-before recv + race detector, Rust Send/Sync Ordering, acq/rel vs seq_cst weakness store buffering allowed, fences, Qs, refs Grokipedia, Russ Cox PLMM, Modernes C++, Boehm SC proof
- **BlobDB** (`storage/blobdb.md`) — KV separation for large values, WiscKey insight, RocksDB Integrated BlobDB design flush if V>=min_blob_size → blob file + SST K+BlobIndex file_no/offset/size, GC age cutoff 0.25 oldest files relocation, options enable_blob_files/min_blob_size/blob_file_size/enable_blob_garbage_collection, leveled recommended, performance bulk load 2.3-4.7× faster WA 1.0-1.02 vs 1.6, overwrite 1.4-1.7 vs 6.1-6.8 75-78% lower, trade-offs RA extra I/O SA higher via garbage, WiscKey vs Badger vs RocksDB, Qs, refs RocksDB Wiki BlobDB + Integrated Blob Blog + Pebble Issue 112
- **Meta fixes**: 14 mermaid regressions after dev merge fixed (unquoted labels () {} |, Note over → NODE_FIX), 16 broken links fixed, bluetooth + congestion-control README added

## Integration Batch — 2026-08-12

- **Linux book (`lb2`)**: 444 source chapters integrated under `src/linux/`,
  plus a track overview and the original [Linux Tools study component](../linux/tools.md).
  Its navigation is adapted into this book's Summary; repository workflows,
  generated output, and source deployment assets were excluded.
- **DSA book (`dsa_book_2`)**: 193 source chapters and appendices integrated
  under `src/dsa/`, plus a track overview and references. The source's
  anchor-named filesystem artifacts were excluded.
- **Navigation**: 1,538 Markdown files are present and 1,537 are linked from
  `SUMMARY.md` (the Summary file is the only excluded Markdown file).
- **Link repair**: 0 broken relative Markdown or image links.
- **Mermaid repair**: 4,387/4,387 pass the repository heuristic and Mermaid v11
  parser validators.
- **Branch safety**: integration commits are on `dev`; `main` was not changed.
- **mdBook build note**: the full source tree builds to 1,579 files with search
  indexing disabled in the constrained sandbox. The normal search-enabled
  build was attempted twice and terminated by the environment with exit 137;
  `book.toml` was not changed to hide that limitation.

## Priority Gaps Remaining (Updated 2026-08-12)

### HIGH Priority — Covered:
1. CUDA Deep Dive — exists `arch/parallelism/cuda.md` ✅
2. Streaming system design — `interview/system-design/real-world/streaming-pipeline.md` ✅
3. Kubernetes operator pattern — `cloud/kubernetes/operators.md` ✅

### MEDIUM Priority — Completed:
4. Go web frameworks ✅ `languages/go/web-frameworks.md` (2026-08-09)
5. Vue / Angular ✅ `frameworks/vue-angular/README.md` exists
6. Linux kernel modules ✅ `os/kernel/modules.md` (2026-08-08)
7. Service mesh internals xDS ✅ `backend/containers/xds-protocol.md` (2026-08-08)
8. QPACK ✅ `networks/http/qpack.md`
9. Kernel Tracing ✅ `os/kernel/tracing.md`
10. Probabilistic Data Structures ✅ `interview/system-design/probabilistic-data-structures.md`
11. WAL ✅ `storage/wal.md`
12. LSM Compaction ✅ `storage/lsm-compaction.md`
13. API Versioning ✅ `backend/api/versioning.md`
14. Rate Limiting ✅ `backend/api/rate-limiting.md`
15. SSTable ✅ `storage/sstable.md`
16. RCU ✅ `concurrency/rcu.md`
17. Work-Stealing ✅ `concurrency/work-stealing.md`
18. Memory Model ✅ `concurrency/memory-model.md`
19. BlobDB ✅ `storage/blobdb.md`

### Remaining MEDIUM (Next Loop):
- Python GIL 3.13 free-threaded deep dive (`languages/python/free-threaded.md`)
- Java Loom Virtual Threads (`languages/java/virtual-threads.md`)
- Rust async runtimes comparison Tokio vs async-std vs smol (`languages/rust/async-runtimes.md`)
- eBPF Networking Deep Dive: XDP, TC, sockmap, Cilium (`networks/ebpf-networking.md` or `os/kernel/ebpf-networking.md`)
- Storage: Ceph CRUSH/RADOS deep dive (`storage/ceph-crush.md`) remains; NVMe-oF is complete in `storage/nvmeof.md` ✅
- Concurrency: ABA Problem & Hazard Pointers ✅ `concurrency/aba-problem.md`; transactional memory expansion remains
- Backend: GraphQL Federation (`backend/api/graphql-federation.md`) remains; CDC and Outbox are complete in `backend/patterns/cdc-outbox.md` ✅
- Distributed: CRDTs are complete in `distributed/fundamentals/crdts.md` ✅; Vector Clocks can still be expanded

### LOW Priority:
- Quantum computing, blockchain (PoW/PoS, Merkle), edge computing (Cloudflare Workers, Fastly Compute@Edge)
- Observability Deep Dive: OpenTelemetry correlation traces/metrics/logs
- SSTable already done, BlobDB done — remaining tiered storage could be done

## Next Steps (Loop Continues)

- Expand Storage to 20+ pages: currently 16 → add Ceph CRUSH, NVMe-oF, tiered storage, BlobDB done, SSTable done, WAL done, compaction done — need Ceph RADOS, write amplification minimization, erasure coding deep dive already exists but could expand
- Expand Concurrency to 25+ pages: currently 18 → ABA, memory barriers, work-stealing, RCU, and memory-model coverage are present — need transactional memory expansion, work-stealing already done, maybe add lock-free queue, wait-free
- Expand Frameworks to 20+ pages: currently 9 → split Vue & Angular dedicated, add Svelte, Micronaut/Quarkus, Actix/Axum, Fiber/Chi done via Go web frameworks, need Rust Actix
- Expand Distributed to 50+ pages: currently 38 → CRDTs complete; add vector clocks deep dive and gossip tuning
- Keep meta updated each batch; current checks are 100% Mermaid and 0 broken links.
- Run and record the full mdBook build before declaring a future batch complete. The constrained build for this batch passed; the production search-enabled build is memory-limited here.
- Push incremental work to `dev` only for this task; do not modify `main`.
