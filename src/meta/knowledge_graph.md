# Knowledge Graph

> Cross-topic relationships for navigation and study planning.
> Auto-updated by research agents.

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
  → Goroutine Scheduler (Go)
  → JVM Thread Model (Java)

File Systems
  → VFS (OS/Filesystems)
  → ext4/XFS/Btrfs (OS/Filesystems)
  → Inode Structure (OS/Filesystems)
  → Journaling (OS/Filesystems)
  → RAID (Storage)
  → Distributed File Systems (Distributed)
```

### DBMS ↔ Other Topics

```
Transactions
  → ACID Properties (DBMS/Transactions)
  → Isolation Levels (DBMS/Transactions)
  → MVCC (DBMS/Transactions)
  → 2PL (DBMS/Concurrency Control)
  → Distributed Transactions (Distributed)
  → Saga Pattern (Backend Engineering)

Indexing
  → B-Tree (DBMS/Indexing)
  → Hash Index (DBMS/Indexing)
  → LSM-Tree (Storage)
  → Query Optimization (DBMS/Query)
  → Covering Index (DBMS/Indexing)

Query Processing
  → Parser (DBMS/Internals)
  → Optimizer (DBMS/Internals)
  → Executor (DBMS/Internals)
  → Join Algorithms (DBMS/Query)
  → Sort-Merge (DBMS/Query)
```

### Networks ↔ Other Topics

```
TCP
  → Three-Way Handshake (Networks/TCP)
  → Congestion Control (Networks/TCP)
  → Flow Control (Networks/TCP)
  → QUIC (Networks/HTTP)
  → Socket Programming (Networks/Sockets)

HTTP
  → TLS/HTTPS (Networks/Security)
  → HTTP/2 (Networks/HTTP)
  → HTTP/3 (Networks/HTTP)
  → REST API (Backend Engineering)
  → gRPC (Backend Engineering)
  → GraphQL (Backend Engineering)

DNS
  → Recursive Resolution (Networks/DNS)
  → Load Balancing (System Design)
  → CDN (System Design)
  → Service Discovery (System Design)
```

### Architecture ↔ Other Topics

```
Cache Hierarchy
  → L1/L2/L3 Cache (Architecture)
  → Cache Coherence (Architecture/MESI)
  → False Sharing (Concurrency)
  → TLB (OS/Memory)
  → NUMA (OS/Memory)

CPU Pipeline
  → Branch Prediction (Architecture)
  → Out-of-Order Execution (Architecture)
  → Speculative Execution (Architecture)
  → SIMD/AVX (Architecture)
  → GPU Architecture (ML/GPU)
```

### Machine Learning ↔ Other Topics

```
Neural Networks
  → Backpropagation (ML/NN)
  → Gradient Descent (ML/Optimization)
  → CNN (ML/CNN)
  → RNN (ML/RNN)
  → Transformer (ML/Transformer)
  → Attention Mechanism (ML/Transformer)

LLMs
  → Transformer Architecture (ML/Transformer)
  → Tokenization (ML/NLP)
  → Fine-tuning (ML/LLM)
  → RLHF (ML/LLM)
  → Quantization (ML/Inference)
  → Distributed Training (ML/Distributed)

GPU Computing
  → CUDA (ML/GPU)
  → Thread Hierarchy (ML/GPU)
  → Memory Model (ML/GPU)
  → Tensor Cores (ML/GPU)
  → Mixed Precision Training (ML/Distributed)
```

## Cross-Language Relationships

```
Memory Management
  → C malloc/free (C)
  → C++ RAII/Smart Pointers (C++)
  → Rust Ownership (Rust)
  → Java GC (Java)
  → Python Reference Counting (Python)
  → Go GC (Go)
  → Virtual Memory (OS)

Concurrency
  → C pthreads (C)
  → C++ std::thread (C++)
  → Rust Send/Sync (Rust)
  → Java synchronized/ReentrantLock (Java)
  → Python asyncio/GIL (Python)
  → Go goroutines/channels (Go)
  → JavaScript Event Loop (JS)
```
