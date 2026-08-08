# Coverage Dashboard

> Auto-generated tracking of content coverage across all subjects.
> Last updated: 2026-08-09 (autonomous expansion loop)

## Summary

| Subject | Pages | Interview Qs | Diagrams | Coverage |
|---------|-------|-------------|----------|----------|
| Operating Systems | 123 | 220+ | 380+ | 82% |
| DBMS | 94 | 190+ | 290+ | 72% |
| Computer Networks | 96 | 180+ | 260+ | 73% |
| Computer Architecture | 82 | 160+ | 205+ | 68% |
| Machine Learning (ml+llm) | 177 | 320+ | 400+ | 70% |
| Distributed Systems | 37 | 85+ | 85+ | 55% |
| Interview Prep | 95 | 530+ | 120+ | 75% |
| Programming Languages | 58 | 310+ | 70+ | 88% |
| Frameworks | 9 | 100+ | 25+ | 60% |
| Backend Engineering | 34 | 240+ | 85+ | 70% |
| Concurrency | 15 | 55+ | 35+ | 48% |
| Storage | 12 | 40+ | 30+ | 45% |
| Cloud & DevOps | 26 | 80+ | 50+ | 60% |

## Overall Metrics

- **Total markdown files**: 881
- **Total Mermaid diagrams**: 2,827
- **Total size**: 8.96 MB
- **Build status**: ✅ Clean (zero errors, 0 broken links, 100% mermaid pass)

## New Sections Added (2026-08-08 to 2026-08-09)

### Storage Expansion (10 → 12 files, +45% coverage)
- **WAL (Write-Ahead Log)** — WAL rule, LSN/pageLSN, STEAL/NO-FORCE, ARIES 3 phases (Analysis/REDO/UNDO), CLR, group commit, checkpoints sharp vs fuzzy, RocksDB/Kafka/etcd patterns, pitfalls
- **LSM Compaction Strategies** — leveled vs size-tiered vs tiered+leveled vs UCS, WA/RA/SA trilemma table (10-30× WA leveled), RocksDB tuning knobs (level0_file_num_compaction_trigger, max_bytes_for_level_base, target_file_size_base, etc.), write stall avoidance, SAG, interview Qs
- **Bluetooth** — short-range PAN, profiles A2DP/HID/GATT, Classic vs BLE (new to satisfy wireless module completeness)
- Existing storage pages expanded: HDD, SSD, NVMe, object/block/file, distributed, Ceph, erasure coding deepened indirectly via new compaction/WAL pages

### Concurrency Expansion (14 → 15 files, 40% → 48%)
- **RCU (Read-Copy-Update)** — publish-subscribe pattern, grace period memory-barrier guarantees (2 barriers from Requirements doc), quiescent states, rcu_dereference store-release, rcu_assign_pointer, kfree_rcu/call_rcu, list primitives, flavors (classic/SRCU/Tasks), checklist, toy implementation, interview Qs, refs kernel.org What is RCU & Checklist
- Previous concurrency already expanded in earlier dev merge: async-await, futures, lock-free (468 lines), go-channels, etc.

### OS Kernel Expansion (121 → 123 files)
- **Kernel Modules** — LKM lifecycle stateDiagram, .ko, insmod/modprobe/lsmod/modinfo/depmod, params via /sys/module, sysfs/proc, signing/taint, LKM vs built-in vs eBPF vs userspace, debugging ftrace/kprobes, interview Qs, refs kernel.org kbuild/modules
- **Kernel Tracing (ftrace/kprobes)** — ftrace files (available_tracers, events/, kprobe_events), function/function_graph tracer, kprobes INT3 vs jump opt 0.05 vs 0.5us, kprobe_events fetchargs $argN/$retval, tracepoints static, perf probe, eBPF bpftrace one-liners, recipe NVMe latency, security CAP_SYS_ADMIN, interview Qs, refs kernel.org kprobes & kprobetrace
- Previous: eBPF, io_uring, cgroups v2, namespaces, etc.

### Networks Expansion (93 → 96 files, 70% → 73%)
- **QPACK (RFC 9204)** — why not HPACK, static 99 vs dynamic table, encoder/decoder streams (0x02/0x03), Required Insert Count/Base, blocking vs non-blocking, wire format (Insert/Capacity/Duplicate vs Section Ack/Insert Count Increment), comparison HPACK vs QPACK table, 0-RTT considerations, Cloudflare/Fastly behavior, qlog/Wireshark, interview Qs, refs RFC 9204
- **TLS Deep Dive** already existed but cross-linked to QPACK
- **Bluetooth** added to wireless module

### Backend / Containers Expansion (30 → 34 files, 65% → 70%)
- **xDS Protocol** — control plane istiod/Pilot vs data plane Envoy, ADS aggregated stream, LDS/RDS/CDS/EDS/SDS/ECDS, protobuf not YAML diagram, version/nonce ACK/NACK, SotW vs Delta xDS, Istio resource mapping (VirtualService→RDS), metadata grain analysis (per-pod EDS vs per-service CDS vs per-path RDS), debugging istioctl proxy-config, performance/scale, go-control-plane, interview Qs, refs Envoy xDS docs, Solo.io guidance
- Previous: service mesh, Docker, Kubernetes, operators

### Programming Languages Expansion (55 → 58 files, 85% → 88%)
- **Go Web Frameworks: Gin/Echo/Fiber** — philosophy trie vs radix vs fasthttp, request lifecycle sequenceDiagram, prod benchmarks raw (Fiber 89k 4.5ms P99 12.3ms 45MB vs Gin 76k 5.21ms 15.7ms 67MB vs Echo 72k 5.54ms 18.2ms 72MB) vs with PG (3247 vs 3156 vs 3089, <5% diff), allocation analysis (Fiber 0-1 alloc vs Gin 3-4), code comparison same endpoint, middleware ecosystem (1000+ Gin, built-in Echo rate limiter/JWT), observability prometheus/otel, Docker multi-stage, decision flowchart, pitfalls (fasthttp smuggling, context leak), 5 interview Qs, refs dev.to prod comparison & lampesm benchmarks
- **Kernel Modules** also counts as OS but cross-ref to languages/C ecosystem
- Previous: C 8 files, C++ 8, Rust 9, Python 9, Go 5→6, Java 4, JS 3, OCaml 3, TypeScript 1

### Interview / System Design Expansion (94 → 95 files)
- **Probabilistic Data Structures: Bloom, HLL, CMS** — decision table (is X in set? → Bloom 10 bits/elem @1%, how many distinct? → HLL 12KB fixed ~2% err, how many times? → CMS overestimates), Bloom bit array + k hashes, FPR formula bits per elem table (9.6 @1%, 14.4 @0.1%), Python minimal impl with mmh3, use cases Cassandra per SSTable skip 90% IO, cache penetration, crawler dedup 10B, Chrome Safe Browsing 30M, CDN, counting Bloom / Cuckoo Filter, HLL leading zeros, 16384 registers harmonic mean, mergeable via max, Redis PFADD/PFCOUNT, CMS d×w matrix, min over rows, ε/δ sizing (2720×5=109KB for 0.1% err), heavy hitters, cost analysis $200 HashSet vs $15 Bloom, interview Qs, refs TECHINTERVIEW.ORG, layrs.me, JavaCodeGeeks
- Existing system design real-world: Netflix, Twitter, Uber, WhatsApp, YouTube, Instagram, Dropbox, distributed lock, streaming analytics pipeline (new), probabilistic adds to advanced patterns
- Previous: rate limiter, kv-store, search engine, etc., plus HLD (scalability, caching, etc.)

### Meta & Navigation
- Added **congestion-control README overview** under TCP, wired into SUMMARY
- Fixed 14 mermaid regressions after dev merge (unquoted labels with () {} |, Note over invalid in flowchart → NODE_FIX)
- Fixed 16+ broken links (os/README → overview, dbms/README, networks/README, distributed/README, service-mesh path, llm-serving ../ml/ → ../../ml/, etc.)
- All files now 100% mermaid pass (2827 diagrams), 0 broken links, SUMMARY OK

## Priority Gaps Remaining (Updated 2026-08-09)

### HIGH Priority — Now Mostly Covered, Remaining:
1. **CUDA Deep Dive** — gpu.md basics exists, dedicated CUDA programming page exists (parallelism/cuda.md) ✅ Done, could add more kernels/examples
2. **Streaming system design** — real-world/streaming-pipeline.md exists ✅ Done
3. **Kubernetes operator pattern** — cloud/kubernetes/operators.md exists ✅ Done, could add reconciliation loop deep dive with controller-runtime example

### MEDIUM Priority — Completed in This Batch:
4. **Go web frameworks — Gin/Echo/Fiber comparison** ✅ Done — `languages/go/web-frameworks.md` (2026-08-09)
5. **Vue / Angular** — alternative frontend frameworks ✅ Done — `frameworks/vue-angular/README.md` exists (from earlier)
6. **Linux kernel modules** — dedicated page ✅ Done — `os/kernel/modules.md` (2026-08-08)
7. **Service mesh internals — Istio/Envoy xDS protocol** ✅ Done — `backend/containers/xds-protocol.md` + `service-mesh.md` (2026-08-08)

### Remaining MEDIUM (New):
- **Python GIL removal (3.13 free-threaded)** — explain new GIL changes
- **Java Virtual Threads (Loom)** — expand java.md
- **Rust async runtime comparison: Tokio vs async-std vs smol**
- **eBPF networking deep dive: XDP, TC, sockmap**

### LOW Priority
- **Quantum computing, blockchain, edge computing expansion** — edge.md exists, could expand quantum circuits, blockchain consensus (PoW/PoS) for curiosity, not interview-critical
- **Storage: SSTable format, BlobDB, Tiered storage** — SSTable format could be dedicated page (currently covered partially in LSM)
- **Concurrency: Work-stealing scheduler, ABA problem, memory barriers deep dive**

## Next Steps (Autonomous Loop)

- Continue expanding **Storage** to 20+ pages: SSTable format, BlobDB, Ceph CRUSH/RADOS deep dive, NVMe-oF, write amplification minimization
- Expand **Concurrency** to 25+ pages: work-stealing (Go scheduler, Java ForkJoinPool), ABA problem, memory model (C++/Java/Go), RCU already added, memory barriers, transactional memory
- Expand **Frameworks** to 20+ pages: split Vue & Angular dedicated, add Svelte, Micronaut/Quarkus (Java), Actix/Axum (Rust), Fiber/Chi (Go) — Go web frameworks now done, need Rust Actix, Python Flask vs Django deep compare
- Expand **Distributed** to 50+ pages: CRDTs, vector clocks deep dive (already have vector-clocks.md stub), gossip tuning, anti-entropy
- Keep meta files updated each batch
- Maintain 100% mermaid pass, 0 links broken, build clean
