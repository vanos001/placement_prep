# Knowledge Graph

> Cross-topic relationships for navigation and study planning.
> Auto-updated by research agents.
> Last updated: 2026-08-12

## Core Relationships

### Operating Systems ↔ Other Topics

```
Virtual Memory
  → Paging (OS/Memory)
  → TLB (OS/Memory)
  → Cache Hierarchy (Architecture)
  → Page Replacement (OS/Virtual Memory)
  → Linux mmap() (OS/Memory)
  → NUMA (OS/Memory)
  → Copy-on-Write (OS/Virtual Memory)

Process Scheduling
  → CPU Scheduling Algorithms (OS/Scheduling)
  → Context Switching (OS/Processes)
  → Linux CFS (OS/Scheduling)
  → Real-time Systems (OS/Scheduling)
  → Goroutine Scheduler (Go) → Go Channels, Work-Stealing, GMP
  → JVM Thread Model (Java) → Loom Virtual Threads

File Systems
  → VFS (OS/Filesystems)
  → ext4/XFS/Btrfs (OS/Filesystems)
  → Inode Structure (OS/Filesystems)
  → Journaling (OS/Filesystems)
  → RAID (Storage)
  → Distributed File Systems (Distributed)
  → WAL (Storage/WAL) → ARIES, Checkpointing

Kernel Extensions
  → Kernel Modules (OS/Kernel/Modules) → insmod/modprobe, params, taint, signing
  → eBPF (OS/Kernel/eBPF) → XDP, TC, tracing, uprobes, CO-RE
  → io_uring (OS/Kernel/io_uring) → async I/O, SQ/CQ rings
  → Tracing (OS/Kernel/Tracing) → ftrace, kprobes 0.05us vs 0.5us, tracepoints, perf, bpftrace
  → RCU (Concurrency/RCU) → grace period, publish-subscribe, quiescent states
```

### DBMS ↔ Storage ↔ Other Topics

```
Transactions
  → ACID Properties (DBMS/Transactions)
  → Isolation Levels (DBMS/Transactions)
  → MVCC (DBMS/Transactions)
  → 2PL (DBMS/Concurrency Control)
  → Distributed Transactions (Distributed) → 2PC/3PC/Saga
  → Saga Pattern (Backend Engineering) → Choreography vs Orchestration
  → WAL (Storage/WAL) → LSN/pageLSN, STEAL/NO-FORCE, group commit

Storage Engines
  → B-Tree (DBMS/Indexing) → B+Tree, Write Amplification low
  → Hash Index (DBMS/Indexing)
  → LSM-Tree (DBMS/Internals/LSM) → MemTable, SSTable, Bloom Filter
  → WAL (Storage/WAL) → durability before MemTable
  → Compaction (Storage/LSM-Compaction) → Leveled (10-30x WA) vs Tiered (2-4x) vs Hybrid (UCS), SAG, RocksDB tuning knobs
  → SSTable Format (Storage) → data blocks, index, bloom, footer, compression
  → Write Amplification (Storage) → affects SSD endurance
  → Read Amplification (Storage) → bloom reduces
  → Space Amplification (Storage) → tombstone reclamation

Query Processing
  → Parser (DBMS/Internals)
  → Optimizer (DBMS/Internals) → cost model, join algorithms
  → Executor (DBMS/Internals)
  → Join Algorithms (DBMS/Query) → nested loop, hash, sort-merge
```

### Networks ↔ Backend ↔ Other Topics

```
TCP
  → Three-Way Handshake (Networks/TCP)
  → Congestion Control (Networks/TCP) → Slow Start, CUBIC, BBR, Reno
  → Congestion Control Overview (Networks/TCP/Congestion-Control/README) → NEW
  → Flow Control (Networks/TCP)
  → QUIC (Networks/HTTP/QUIC) → 0-RTT, connection migration via Connection ID
  → Socket Programming (Networks/Sockets) → TCP/UDP/Unix Domain, epoll

HTTP
  → TLS/HTTPS (Networks/Security) → TLS 1.3 handshake, mTLS, CT
  → HTTP/1.1, HTTP/2 (Networks/HTTP) → HPACK
  → HTTP/3 (Networks/HTTP) → QUIC, QPACK (RFC 9204), 0-RTT, HOL blocking eliminated
  → QPACK (Networks/HTTP/QPACK) → static 99 vs dynamic table, encoder/decoder streams 0x02/0x03, RIC/Base, blocking
  → QUIC (Networks/HTTP/QUIC)
  → REST API (Backend/API/REST) → versioning, idempotency
  → gRPC (Backend/API/gRPC) → protobuf, HTTP/2, streaming
  → GraphQL (Backend/API/GraphQL) → federation
  → WebSocket (Networks/HTTP/WebSocket)

Service Mesh
  → xDS Protocol (Backend/Containers/xDS-Protocol) → LDS/RDS/CDS/EDS/SDS, ADS, protobuf not YAML, SotW vs Delta, Pilot, go-control-plane
  → Service Mesh (Backend/Containers/Service-Mesh) → sidecar pattern (Envoy), mTLS via Citadel SPIFFE, VirtualService/DestinationRule/Gateway
  → Envoy Proxy → listeners, filter chains, clusters, outlier detection

Wireless
  → WiFi (Networks/Wireless/WiFi)
  → Bluetooth (Networks/Wireless/Bluetooth) → NEW: PAN, A2DP/HID/GATT, Classic vs BLE
  → 5G (Networks/Wireless/5G)
```

### Architecture ↔ Other Topics

```
Cache Hierarchy
  → L1/L2/L3 Cache (Architecture)
  → Cache Coherence (Architecture/MESI) → MSI/MESI/MOESI/MESIF, directory-based, false sharing
  → False Sharing (Concurrency)
  → TLB (OS/Memory)
  → NUMA (OS/Memory)
  → Storage Hierarchy (Storage/Overview) → Registers → L1 → RAM → NVMe ~25us → HDD 5-10ms → S3 50-200ms

CPU Pipeline
  → Branch Prediction (Architecture)
  → Out-of-Order Execution (Architecture)
  → Speculative Execution (Architecture)
  → SIMD/AVX (Architecture)
  → GPU Architecture (Parallelism/GPU) → CUDA (Parallelism/CUDA) → Thread Hierarchy, Memory Model, Kernels
  → Modern Processors (Arch/Modern) → x86-64 Xeon/EPYC, ARM Neoverse Graviton, RISC-V, Apple Silicon M3/M4

Storage Performance
  → IOPS vs Throughput vs Latency (Storage)
  → RAID (Storage) → 0/1/5/6/10
  → Erasure Coding (Storage/Erasure-Coding) → Reed-Solomon, 10+4
  → Ceph (Storage/Ceph) → RADOS, CRUSH, PGs
```

### Machine Learning ↔ Systems ↔ Other Topics

```
Neural Networks
  → Backpropagation (ML/NN)
  → Gradient Descent (ML/Optimization) → SGD, Adam
  → CNN (ML/CNN) → ResNet, ViT
  → RNN (ML/RNN) → LSTM, GRU
  → Transformer (ML/Transformer) → Self-Attention O(n²), Positional Encoding
  → Attention Mechanism (ML/Deep-Learning/Attention)

LLMs
  → Transformer Architecture (ML/Transformer)
  → Tokenization (LLM-Serving/Tokenization) → BPE, SentencePiece
  → Embeddings (LLM-Serving/Embeddings)
  → Fine-tuning (LLM-Serving/SFT) → LoRA, QLoRA
  → RLHF/DPO (LLM-Serving/RLHF) → PPO, GRPO
  → Inference Optimization → KV Cache (LLM-Serving/KV-Cache), Quantization (Quant), Speculative Decoding, Batching, vLLM/TensorRT/ TGI/Ollama
  → RAG (LLM-Serving/RAG) → Vector DBs (Vector-Databases) → HNSW, IVF, PQ
  → Probabilistic Data Structures (Interview/System-Design/Probabilistic) → Bloom for cache penetration, HLL for distinct count, CMS for heavy hitters

GPU Computing
  → CUDA (Parallelism/CUDA) → Thread Hierarchy (Thread/Block/Grid), Memory Model (global/shared/registers), Kernels
  → Thread Hierarchy (ML/GPU)
  → Memory Model (ML/GPU)
  → Tensor Cores (ML/GPU) → Mixed Precision Training (ML/Distributed) → FP16/BF16, DDP/FSDP/ZeRO
```

### Programming Languages ↔ Frameworks ↔ Backend

```
Memory Management
  → C malloc/free (C) → Undefined Behavior, POSIX
  → C++ RAII/Smart Pointers (C++) → move semantics, STL, templates, concurrency
  → Rust Ownership (Rust) → borrow checker, lifetimes, traits, unsafe, async Tokio
  → Java GC (Java/GC) → Serial/Parallel/G1/ZGC 0.5ms/Shenandoah, generational ZGC JDK21
  → Python Reference Counting (Python) → GIL, asyncio, typing, 3.13 free-threaded
  → Go GC (Go) → GMP scheduler, channels, memory model, Web Frameworks (Gin/Echo/Fiber) → net/http compat vs fasthttp 89k rps vs 76k vs 72k
  → Virtual Memory (OS)

Concurrency
  → C pthreads (C)
  → C++ std::thread (C++) → std::jthread, memory model
  → Rust Send/Sync (Rust) → Tokio work-stealing
  → Java synchronized/ReentrantLock (Java) → Loom virtual threads
  → Python asyncio/GIL (Python) → free-threaded 3.13t
  → Go goroutines/channels (Go) → work-stealing scheduler, channels
  → JavaScript Event Loop (JS) → V8, Node.js, libuv

Web Frameworks
  → Go: Gin (minimal, 1000+ middleware, net/http), Echo (batteries included, radix), Fiber (Express-inspired, fasthttp, 0-1 alloc, 89k rps) → Decision: need compat → Gin, need built-ins → Echo, need max perf → Fiber
  → Rust: Tokio (async runtime), Axum/Actix (web)
  → Python: FastAPI (async, Pydantic), Django (batteries), Flask, Pydantic
  → Java: Spring Boot, Quarkus, Micronaut, Hibernate
  → JS/TS: React, Next.js, Vue & Angular (combined), Express.js

Backend Patterns
  → API Design (Backend/API) → REST (versioning, idempotency), gRPC (protobuf, streaming), GraphQL (federation), Webhooks, Connection Pools
  → Messaging (Backend/Messaging) → Kafka (log), RabbitMQ (queue), Redis (pub/sub + streams + Bloom/HLL), NATS (subject-based)
  → Auth (Backend/Auth) → JWT RS256, OAuth2 PKCE, mTLS (Service Mesh mTLS via Citadel SPIFFE), Session Management
  → Containers (Backend/Containers) → Docker, Kubernetes (Pods, Services, Deployments, Ingress, Operators CRD/reconciliation), Service Mesh (sidecar Envoy), xDS (ADS, LDS/RDS/CDS/EDS/SDS)
  → Observability (Backend/Observability) → Logs, Metrics Prometheus, Tracing Jaeger/Zipkin, Kiali
  → Patterns (Backend/Patterns) → Circuit Breaker (Closed/Open/HalfOpen), Retry + Exponential Backoff + Jitter, Idempotency Keys, Saga (Choreography vs Orchestration), CQRS (read/write separation), Event Sourcing, Distributed Transactions, Bulkhead
  → Probabalistic (Interview/Probabilistic) → Bloom for negative cache, HLL for cardinality, CMS for frequency
```

### System Design ↔ All

```
Scalability
  → Vertical vs Horizontal, Stateless vs Stateful, Consistent Hashing (Distributed/Partitioning), Load Balancing L4 vs L7 (Networks/Load-Balancing), Caching Strategy (Cache-Aside, Write-Through, LRU/LFU/TTL), CDN (Networks/CDN/How-It-Works + Edge)

Data Structures for System Design
  → Bloom Filter (Interview/Probabilistic) → membership, 10 bits/elem @1% FP, Cassandra SSTable skip 90% IO, cache penetration prevention, safe-browsing
  → HyperLogLog (Interview/Probabilistic) → distinct counting 12KB fixed ~2% err, mergeable via max, Redis PFADD/PFCOUNT, BigQuery APPROX_COUNT_DISTINCT
  → Count-Min Sketch (Interview/Probabilistic) → frequency, overestimates, heavy hitters, ε/δ sizing

Storage & Retrieval
  → WAL (Storage/WAL) → LSN/pageLSN, group commit, fuzzy checkpoint
  → LSM Compaction (Storage/LSM-Compaction) → leveled vs tiered vs hybrid, RocksDB tuning, write stall
  → SSTable → bloom, index, data blocks

Real-World Designs
  → URL Shortener, Chat, News Feed, Rate Limiter (token bucket/leaky/sliding), KV Store, Search Engine, Video Streaming, Notifications, Distributed FS, Web Crawler, Pastebin, Social Graph, Typeahead, Metrics, Payment (idempotency keys), Ad Click Aggregation, Stock Exchange, Google Maps
  → Netflix (CDN + microservices), Twitter (fanout), Uber (geo), WhatsApp (presence), YouTube (transcoding), Instagram (feed), Dropbox (sync), Distributed Lock (Redlock/etcd/fencing tokens), Streaming Pipeline (Kafka + Flink/Spark + stateful processing), Probabilistic (Bloom/HLL/CMS for scale)
```

## Cross-Language Relationships (Updated)

```
Memory Management
  → C malloc/free (C) → ecosystem & tooling (CMake, Conan, GDB)
  → C++ RAII/Smart Pointers (C++) → move semantics, STL, templates, ecosystem (Boost, CMake, Catch2)
  → Rust Ownership (Rust) → borrow checker, lifetimes, traits, error handling, async Tokio, unsafe, ecosystem (Serde, Rayon, Axum)
  → Java GC (Java) → G1 default 200ms, ZGC <1ms colored pointers load barriers, Shenandoah Brooks pointers, generational ZGC JDK21
  → Python (Python) → CPython internals, GIL 3.13 free-threaded, asyncio, typing, data model, packaging
  → Go (Go) → scheduler GMP work-stealing, channels, memory model, web frameworks Gin 76k rps vs Echo vs Fiber 89k rps
  → Virtual Memory (OS/Virtual Memory) → paging, TLB, NUMA

Concurrency
  → C pthreads (C) → POSIX
  → C++ std::thread (C++) → memory model acquire/release
  → Rust Send/Sync (Rust) → ownership ensures thread safety
  → Java (Java) → synchronized/ReentrantLock, Loom virtual threads
  → Python (Python) → asyncio, GIL
  → Go (Go) → goroutines/channels, work-stealing
  → JavaScript (JS) → Event Loop, V8, Node.js libuv
  → Kernel (OS/Kernel) → RCU grace period, publish-subscribe, tracing ftrace/kprobes
```

## Linux and DSA Integration Edges — 2026-08-12

### Linux track

- [Linux Tools](../linux/tools.md) → shell quoting, NUL-delimited pipelines,
  `find`/`xargs`, text processing, process inspection, sockets, HTTP, storage,
  tracing, and incident response.
- Shell → [system programming](../linux/sysprog/syscalls.md) → system calls,
  file descriptors, IPC, `epoll`, `io_uring`, ELF, and dynamic linking.
- Processes and threads → [kernel scheduling and synchronization](../linux/kernel/processes/scheduler.md)
  → per-CPU data, atomics, RCU, lock ordering, and lock contention.
- `ip`/`ss`/`tcpdump` → [Linux networking](../linux/networking/fundamentals.md)
  → TCP/IP, DNS, routing, TLS, WireGuard, and kernel eBPF hooks.
- `/proc`, perf, ftrace, eBPF → [performance](../linux/performance/overview.md)
  → USE method, flame graphs, cache behavior, NUMA, and production diagnosis.
- Namespaces + cgroups + seccomp → [containers](../linux/containers/overview.md)
  → OCI runtimes, rootless isolation, Kubernetes, and security boundaries.
- Block I/O and filesystems → [Linux storage](../linux/storage/overview.md)
  → LVM, RAID, NVMe-oF, Ceph, multipath, and filesystem internals.

### DSA track

- [DSA overview](../dsa/README.md) → foundations → arrays, sorting, searching,
  hashing, recursion, and complexity analysis.
- Arrays and hashing → [problem-solving patterns](../dsa/chapters/ch34-two-pointers.md)
  → two pointers, sliding windows, prefix sums, monotonic structures, and
  divide and conquer.
- Trees → heaps, tries, DSU, segment trees, Fenwick trees, sparse tables, and
  binary lifting; these feed range-query and graph problem strategies.
- [Graph fundamentals](../dsa/chapters/ch22-graph-fundamentals.md) → DFS/BFS
  → topological sort, shortest paths, MST, SCC, network flow, and tree
  decompositions.
- DP fundamentals → DP patterns → digit/profile/optimization DP; correctness
  proofs and complexity analysis provide the explanation expected in interviews.
- String algorithms → rolling hash, KMP, Z, tries, suffix arrays/automata,
  Aho–Corasick, BWT/FM-index, and palindromic structures.
- DSA engineering chapters → [architecture](../arch/modern/README.md), C++ memory and
  STL, cache hierarchy, profiling, branch prediction, SIMD, and undefined
  behavior.

### ABA and safe-reclamation edges — 2026-08-12

- [ABA Problem](../concurrency/aba-problem.md) → CAS/compare-exchange, tagged
  pointers, memory ordering, lock-free stacks and queues.
- ABA → [Hazard Pointers](../concurrency/aba-problem.md) → per-pointer reader
  reservations, retire lists, scans, and delayed reclamation.
- ABA → [Epoch Reclamation](../concurrency/aba-problem.md) → pinning,
  participant advancement, stalled-reader memory growth, and Crossbeam Epoch.
- ABA → [RCU](../concurrency/rcu.md) → grace periods, unlink-before-free,
  Linux kernel quiescent states, and read-mostly data structures.
- ABA → C++ safe reclamation → current C++ working draft `hazard_pointer` and
  `rcu_obj_base`, with implementation availability still compiler-dependent.
- Safe reclamation → [Memory Model](../concurrency/memory-model.md) →
  acquire/release publication, CAS success/failure orderings, and lifetime
  safety as a separate proof obligation.

### Cross-track placement edges

- Linux `perf`/cache hierarchy ↔ DSA complexity and [cache-aware engineering](../dsa/chapters/ch89-engineering-cache.md).
- Linux kernel trees, hash tables, allocators, and schedulers ↔ DSA trees,
  hashing, heaps, graphs, and amortized analysis.
- `epoll`/`io_uring` readiness queues ↔ DSA queues and event-driven systems.
- Consistent hashing ↔ Linux/network service discovery and DSA's advanced
  hashing chapter; this is also relevant to distributed-system interviews.

### Provenance and integrity

- Source learning tracks: [lb2](https://github.com/Abhinav-Kumar012/lb2) and
  [dsa_book_2](https://github.com/Abhinav-Kumar012/dsa_book_2).
- Parent navigation: [`src/SUMMARY.md`](../SUMMARY.md).
- Validation edges: Markdown links → Summary reachability → Mermaid v11 parser
  → mdBook build.

## New Edges Added 2026-08-09

- Go Web Frameworks → net/http compatibility ↔ observability (prometheus, pprof, otelhttp) vs fasthttp incompatibility
- Probabilistic Data Structures → Caching Strategy (negative cache), Redis (BF.ADD, PFADD), LSM (SSTable bloom), Kafka (heavy hitters), BigQuery
- Kernel Tracing → eBPF (bpftrace kprobe:do_sys_open, hist(retval)), ftrace (function_graph), perf (record), cgroups filtering
- WAL → ARIES (Analysis/REDO/UNDO), Checkpointing (sharp vs fuzzy), LSM Trees (MemTable replay), RocksDB/Kafka/etcd Raft
- LSM Compaction → WAL, SSTable, Bloom Filter, RocksDB tuning, Write Amplification, Space Amplification Goal, Time-Window Compaction for time-series
- RCU → Lock-free (ABA, hazard pointers), Memory Barriers (acquire/release, smp_mb), Kernel Modules (rcu_barrier for unload), cgroups traversal
- Storage → Distributed (Ceph CRUSH, RADOS), Erasure Coding (Reed-Solomon)
- Links fixed: introduction.md revision/README → revision/os.md, os/README → os/overview.md, etc., congestion-control README and bluetooth added
