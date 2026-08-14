# Master Topic Index

> Authoritative topic inventory for the Placement Preparation Knowledge Base.
> Every section here is a roadmap, not a checklist: existing pages may already
> cover a topic (search before creating), and missing topics should be added
> to `index.md` whenever they are discovered during research.
>
> Status legend used elsewhere in `meta/`:
> `[ ]` Not started · `[-]` Partial · `[x]` Substantially covered · `[~]` Needs review
>
> Last updated: 2026-08-15

## 1. Algorithms — advanced

* Amortized analysis
* Potential method
* Aggregate method
* Randomized algorithms
* Las Vegas algorithms
* Monte Carlo algorithms
* Approximation algorithms
* Online algorithms
* Streaming algorithms
* External-memory algorithms
* Cache-oblivious algorithms
* Cache-aware algorithms
* Parallel algorithms
* Distributed algorithms
* Dynamic algorithms
* Incremental algorithms
* Decremental algorithms
* Parameterized algorithms
* Fixed-parameter tractability
* NP-completeness
* NP-hardness
* Reductions
* P vs NP
* SAT
* 2-SAT
* 3-SAT
* Max-SAT
* Constraint satisfaction
* Backtracking optimization
* Branch and bound
* Integer programming
* Linear programming
* Min-cost flow
* Max-flow/min-cut
* Matching algorithms
* Bipartite matching
* Hungarian algorithm
* Stable matching
* Matroid algorithms
* Computational geometry
* Line sweep
* Convex hull
* Closest pair
* Voronoi diagrams
* KD trees
* Range searching
* String algorithms
* KMP
* Z algorithm
* Rabin-Karp
* Aho-Corasick
* Suffix arrays
* Suffix trees
* Suffix automata
* Rolling hash
* Edit distance
* Sequence alignment
* Computational number theory
* Modular arithmetic
* Fast exponentiation
* Extended Euclidean algorithm
* Chinese remainder theorem
* Fermat/Euler theorem
* Primality testing
* Sieve algorithms
* FFT
* NTT
* Polynomial multiplication
* Matrix algorithms
* Fast matrix multiplication
* Sparse matrices
* Numerical algorithms
* Graph coloring
* Strongly connected components
* Articulation points
* Bridges
* Eulerian paths
* Hamiltonian paths
* Minimum spanning trees
* Shortest paths
* Johnson's algorithm
* A*
* Bidirectional search
* Flow networks
* Topological sorting
* DAG DP
* Tree algorithms
* Centroid decomposition
* Heavy-light decomposition
* Binary lifting
* Lowest common ancestor
* Link-cut trees
* Persistent data structures
* Wavelet trees
* Fenwick trees
* Segment trees
* Sparse tables
* Disjoint-set union
* Treaps
* Skip lists

---

## 2. Advanced Data Structures

* B-trees
* B+ trees
* LSM trees
* SSTables
* Bloom filters
* Cuckoo filters
* Count-min sketch
* HyperLogLog
* Merkle trees
* Interval trees
* R-trees
* Patricia tries
* Radix trees
* HAMTs
* Persistent trees
* Finger trees
* Rope data structures
* Bitsets
* Roaring bitmaps
* Succinct data structures
* Compressed data structures
* Memory-efficient data structures
* Lock-free data structures
* Wait-free data structures
* Concurrent queues
* Concurrent hash tables
* Skip-list internals

---

## 3. Compilers

This is a **major missing category** worth adding.

* Compiler architecture
* Lexing
* Parsing
* AST
* CST
* Symbol tables
* Semantic analysis
* Type checking
* Intermediate representations
* SSA
* Three-address code
* Control-flow graphs
* Data-flow analysis
* Dominators
* Liveness analysis
* Reaching definitions
* Constant propagation
* Dead-code elimination
* Common subexpression elimination
* Loop optimization
* Inlining
* Tail-call optimization
* Register allocation
* Instruction selection
* Instruction scheduling
* Peephole optimization
* Escape analysis
* Alias analysis
* Partial evaluation
* JIT compilation
* AOT compilation
* Static compilation
* Dynamic compilation
* Bytecode
* Virtual machines
* Garbage collectors
* Runtime systems
* Linkers
* Loaders
* Relocations
* Symbol resolution
* Object files
* ELF
* DWARF
* ABI
* Calling conventions
* Name mangling
* Dynamic linking
* Static linking
* LTO
* PGO
* Cross compilation
* WebAssembly
* LLVM
* GCC internals
* Clang
* MLIR
* Cranelift
* compiler bootstrapping
* self-hosting compilers

---

## 4. Programming Language Theory

* Type theory
* Type inference
* Hindley-Milner
* Parametric polymorphism
* Ad-hoc polymorphism
* Higher-kinded types
* Algebraic data types
* Dependent types
* Refinement types
* Linear types
* Affine types
* Structural typing
* Nominal typing
* Gradual typing
* Duck typing
* Type erasure
* Variance
* Covariance
* Contravariance
* Existential types
* Universal types
* Monads
* Functors
* Applicatives
* Algebraic effects
* Effect systems
* Continuations
* CPS
* Closures
* Lexical scoping
* Dynamic scoping
* Evaluation strategies
* Lazy evaluation
* Strict evaluation
* Call-by-value
* Call-by-name
* Call-by-need
* Pattern matching
* Macros
* Hygienic macros
* Reflection
* Metaprogramming
* Dependent pattern matching
* Language semantics
* Operational semantics
* Denotational semantics
* Formal semantics
* Lambda calculus
* Calculus of constructions
* Category theory for programmers

---

## 5. Runtime Systems

* Process runtime
* Language runtime
* Virtual machines
* Bytecode interpreters
* JITs
* Garbage collectors
* Reference counting
* Tracing GC
* Generational GC
* Mark-and-sweep
* Mark-and-compact
* Concurrent GC
* Incremental GC
* Region-based memory
* Arena allocation
* Memory allocators
* malloc internals
* jemalloc
* tcmalloc
* mimalloc
* Stack allocation
* Heap allocation
* Escape analysis
* Object layout
* vtables
* RTTI
* ABI
* stack frames
* exception handling
* unwinding
* coroutines
* fibers
* green threads

---

## 6. Concurrency — much deeper

* Thread models
* Processes vs threads
* User-level threads
* Kernel threads
* Green threads
* Fibers
* Coroutines
* Async/await
* Futures
* Promises
* Executors
* Thread pools
* Work stealing
* Actor model
* CSP
* channels
* message passing
* shared-memory concurrency
* memory ordering
* sequential consistency
* acquire/release
* relaxed atomics
* fences
* CAS
* ABA problem
* lock-free programming
* wait-free programming
* RCU
* hazard pointers
* epoch-based reclamation
* transactional memory
* false sharing
* cache-line contention
* priority inversion
* starvation
* livelock
* lock contention
* concurrent garbage collection

---

## 7. Linux Internals

* Linux kernel architecture
* kernel modules
* syscalls
* VFS
* ext4
* XFS
* Btrfs
* procfs
* sysfs
* cgroups
* namespaces
* capabilities
* seccomp
* eBPF
* io_uring
* epoll
* select
* poll
* signals
* ptrace
* perf
* ftrace
* kprobes
* uprobes
* kernel scheduling
* CFS
* memory reclaim
* page cache
* slab allocator
* buddy allocator
* NUMA
* Linux networking stack
* netfilter
* iptables
* nftables
* namespaces
* containers internals
* overlay filesystems
* device drivers
* udev
* systemd
* boot process

---

## 8. Security

This should be a **huge section**.

* Security fundamentals
* CIA triad
* threat modeling
* attack surfaces
* trust boundaries
* authentication
* authorization
* RBAC
* ABAC
* ACLs
* IAM
* least privilege
* zero trust
* cryptography
* symmetric encryption
* AES
* ChaCha20
* asymmetric cryptography
* RSA
* ECC
* Diffie-Hellman
* ECDH
* digital signatures
* hashing
* SHA-2
* SHA-3
* HMAC
* password hashing
* Argon2
* bcrypt
* scrypt
* key management
* PKI
* certificates
* TLS
* certificate chains
* secure boot
* hardware security
* TPM
* HSM
* secrets management
* vulnerability management
* CVE
* CVSS
* supply-chain security
* SBOM
* dependency security
* software signing

### Web security

* XSS
* CSRF
* SSRF
* SQL injection
* command injection
* path traversal
* request smuggling
* HTTP desync
* clickjacking
* CORS
* CSP
* cookie security
* session security
* OAuth attacks
* JWT pitfalls
* authentication vulnerabilities
* authorization bugs
* race conditions
* insecure deserialization

### Application security

* secure coding
* memory safety
* buffer overflows
* use-after-free
* double-free
* integer overflow
* format-string vulnerabilities
* sandboxing
* fuzzing
* static analysis
* dynamic analysis
* exploit mitigation
* ASLR
* DEP/NX
* stack canaries
* Control Flow Integrity

---

## 9. Cryptography

Go deeper than normal security sections.

* Number theory
* finite fields
* groups
* rings
* elliptic curves
* cryptographic randomness
* PRNGs
* CSPRNGs
* stream ciphers
* block ciphers
* modes of operation
* CBC
* CTR
* GCM
* authenticated encryption
* key derivation
* HKDF
* password-based KDFs
* commitments
* zero-knowledge proofs
* ZK-SNARKs
* ZK-STARKs
* MPC
* threshold cryptography
* secret sharing
* Shamir secret sharing
* homomorphic encryption
* differential privacy
* post-quantum cryptography
* lattice cryptography
* hash-based signatures

---

## 10. Software Engineering

* Software architecture
* architecture styles
* modularity
* coupling
* cohesion
* dependency management
* API design
* API versioning
* backwards compatibility
* semantic versioning
* technical debt
* refactoring
* code smells
* clean architecture
* hexagonal architecture
* onion architecture
* domain-driven design
* bounded contexts
* aggregates
* repositories
* domain events
* event storming
* ADRs
* RFC processes
* design reviews
* code reviews
* engineering productivity
* documentation engineering
* developer experience

---

## 11. Testing

Expand testing dramatically.

* Unit testing
* Integration testing
* End-to-end testing
* System testing
* Acceptance testing
* Regression testing
* Smoke testing
* Sanity testing
* Contract testing
* Consumer-driven contracts
* Property-based testing
* Generative testing
* Mutation testing
* Snapshot testing
* Golden tests
* Fuzz testing
* Differential testing
* Metamorphic testing
* Chaos testing
* Load testing
* Stress testing
* Soak testing
* Performance testing
* Benchmarking
* Race detection
* Static analysis
* Dynamic analysis
* Symbolic execution
* Model checking
* formal verification

---

## 12. DevOps

* CI/CD
* build systems
* artifact management
* release engineering
* semantic versioning
* deployment strategies
* blue-green deployment
* canary deployment
* rolling deployment
* feature flags
* infrastructure as code
* configuration management
* secrets management
* GitOps
* platform engineering
* internal developer platforms
* environment management
* immutable infrastructure
* golden images
* reproducible builds
* hermetic builds

---

## 13. Build Systems

A surprisingly valuable topic.

* Make
* CMake
* Ninja
* Bazel
* Buck
* Meson
* Gradle
* Maven
* Cargo
* npm
* pnpm
* Yarn
* Poetry
* uv
* pip
* Go modules
* Nix
* reproducible builds
* dependency graphs
* incremental builds
* remote caching
* distributed builds
* build isolation
* hermetic builds

---

## 14. Git Internals

* Git object model
* blobs
* trees
* commits
* refs
* HEAD
* branches
* tags
* packfiles
* delta compression
* index
* reflog
* garbage collection
* merge algorithms
* three-way merge
* rebase internals
* cherry-pick
* bisect
* hooks
* submodules
* worktrees
* Git LFS
* partial clone
* shallow clone
* sparse checkout
* Git protocol
* Git hosting architecture

---

## 15. Observability

* Logging
* structured logging
* log levels
* log aggregation
* metrics
* counters
* gauges
* histograms
* percentiles
* tracing
* distributed tracing
* spans
* trace context
* OpenTelemetry
* correlation IDs
* RED methodology
* USE methodology
* SLI
* SLO
* SLA
* error budgets
* alerting
* incident response
* debugging distributed systems
* profiling
* continuous profiling

---

## 16. Performance Engineering

* CPU profiling
* memory profiling
* I/O profiling
* flame graphs
* cache behavior
* branch prediction
* SIMD
* vectorization
* memory bandwidth
* CPU affinity
* NUMA
* lock contention
* false sharing
* allocation profiling
* garbage collection tuning
* latency analysis
* throughput analysis
* tail latency
* p50/p90/p95/p99/p999
* benchmarking methodology
* microbenchmarks
* macrobenchmarks
* workload characterization
* Amdahl's law
* Gustafson's law
* Little's law
* queueing theory

---

## 17. Storage Systems

* HDD
* SSD
* NVMe
* flash memory
* NAND
* wear leveling
* FTL
* RAID
* erasure coding
* object storage
* block storage
* file storage
* distributed storage
* Ceph
* GlusterFS
* HDFS
* distributed filesystems
* WAL
* journaling
* copy-on-write
* snapshots
* deduplication
* compression
* storage tiers
* cold storage

---

## 18. Distributed Databases

* Spanner
* CockroachDB
* TiDB
* YugabyteDB
* FoundationDB
* distributed SQL
* consensus-backed replication
* quorum reads
* quorum writes
* leaderless replication
* vector clocks
* Lamport clocks
* hybrid logical clocks
* conflict resolution
* CRDTs
* anti-entropy
* hinted handoff
* read repair
* gossip protocols

---

## 19. Distributed Algorithms

* Lamport clocks
* vector clocks
* logical clocks
* causal ordering
* total ordering
* leader election
* failure detectors
* consensus
* Paxos
* Multi-Paxos
* Raft
* Zab
* Viewstamped Replication
* Byzantine fault tolerance
* PBFT
* quorum systems
* gossip
* epidemic protocols
* CRDTs
* distributed snapshots
* Chandy-Lamport
* distributed deadlocks
* distributed transactions
* 2PC
* 3PC
* sagas

---

## 20. Messaging / Streaming

* message queues
* Kafka
* Pulsar
* RabbitMQ
* NATS
* Redis Streams
* AMQP
* MQTT
* JMS
* delivery semantics
* at-most-once
* at-least-once
* exactly-once
* ordering
* partitioning
* consumer groups
* offsets
* replay
* retention
* backpressure
* stream processing
* windowing
* event time
* processing time
* watermarks
* Kafka Streams
* Flink
* Spark Streaming
* stream joins

---

## 21. Frontend Engineering

The original prompt was backend-heavy, so add:

* browser architecture
* DOM
* CSS architecture
* rendering pipeline
* layout
* painting
* compositing
* JavaScript runtime
* event loop
* microtasks
* macrotasks
* Web APIs
* Web Workers
* Service Workers
* WebSockets
* WebRTC
* browser storage
* IndexedDB
* cookies
* caching
* HTTP caching
* hydration
* SSR
* SSG
* ISR
* SPA
* accessibility
* frontend performance
* Core Web Vitals
* security
* bundlers
* tree shaking
* code splitting
* lazy loading
* module federation
* frontend testing

---

## 22. Mobile Engineering

Add:

### Android

* Android architecture
* Activity
* Fragment
* lifecycle
* ViewModel
* Jetpack
* Compose
* Kotlin coroutines
* Room
* WorkManager
* networking
* background execution
* Android security

### iOS

* Swift
* SwiftUI
* UIKit
* Combine
* async/await
* app lifecycle
* memory management
* Core Data
* networking
* iOS security

---

## 23. WebAssembly

* WASM architecture
* WASM bytecode
* WASI
* WASM runtimes
* Rust + WASM
* C/C++ + WASM
* JavaScript interoperability
* WASM GC
* WASM components
* server-side WASM
* sandboxing
* WASM performance

---

## 24. GPUs / High Performance Computing

* GPU architecture
* CUDA
* CUDA kernels
* memory hierarchy
* shared memory
* warps
* occupancy
* synchronization
* GPU scheduling
* OpenCL
* SYCL
* Vulkan compute
* ROCm
* Triton
* tensor cores
* GPU programming
* distributed GPU training
* NCCL
* MPI
* OpenMP
* HPC clusters
* parallel computing

---

## 25. ML Systems / MLOps

Go beyond ML theory.

* ML pipelines
* feature stores
* model registries
* experiment tracking
* data versioning
* model versioning
* training infrastructure
* distributed training
* data parallelism
* tensor parallelism
* pipeline parallelism
* model parallelism
* checkpointing
* gradient accumulation
* mixed precision
* FP16
* BF16
* quantization
* pruning
* distillation
* inference optimization
* batching
* serving
* model gateways
* model monitoring
* drift detection
* data drift
* concept drift
* ML observability
* ML testing
* model evaluation

---

## 26. LLM Infrastructure

Especially valuable now.

* tokenizer internals
* BPE
* WordPiece
* SentencePiece
* KV cache
* paged attention
* continuous batching
* prefix caching
* speculative decoding
* quantization
* GPTQ
* AWQ
* GGUF
* tensor parallelism
* pipeline parallelism
* expert parallelism
* Mixture of Experts
* distributed inference
* model serving
* vLLM
* TensorRT-LLM
* SGLang
* llama.cpp
* inference scheduling
* GPU memory management
* context caching
* prompt caching
* model routing
* model gateways

---

## 27. AI Agents

* agent architectures
* ReAct
* planning
* tool use
* function calling
* memory
* episodic memory
* semantic memory
* agent loops
* reflection
* planning vs execution
* multi-agent systems
* agent orchestration
* workflow engines
* tool permissions
* agent security
* prompt injection
* indirect prompt injection
* tool poisoning
* data exfiltration
* agent evaluation
* agent observability
* deterministic workflows vs autonomous agents

---

## 28. Databases — Specialized

* time-series databases
* spatial databases
* vector databases
* graph databases
* search engines
* inverted indexes
* full-text search
* Elasticsearch
* OpenSearch
* Lucene
* vector indexing
* HNSW
* IVF
* PQ
* ANN
* hybrid search
* geospatial indexes
* temporal databases
* ledger databases

---

## 29. Search Engines

Entire dedicated topic.

* crawling
* robots.txt
* indexing
* inverted indexes
* tokenization
* stemming
* ranking
* TF-IDF
* BM25
* PageRank
* link analysis
* autocomplete
* spelling correction
* query expansion
* faceted search
* distributed search
* shard routing
* relevance evaluation
* semantic search
* vector search
* hybrid search

---

## 30. Computer Graphics

* rasterization
* vector graphics
* transformations
* matrices
* coordinate systems
* cameras
* lighting
* shading
* textures
* ray tracing
* path tracing
* GPUs
* rendering pipelines
* OpenGL
* Vulkan
* DirectX
* WebGPU
* shaders
* GLSL
* HLSL
* compute shaders

---

## 31. Embedded Systems

* microcontrollers
* interrupts
* timers
* DMA
* UART
* SPI
* I2C
* CAN
* GPIO
* ADC
* DAC
* RTOS
* FreeRTOS
* Zephyr
* embedded Linux
* firmware
* bootloaders
* OTA updates
* memory-constrained programming
* real-time systems
* hard vs soft real time
* scheduling
* watchdogs
* hardware debugging

---

## 32. IoT

* IoT architecture
* MQTT
* CoAP
* device provisioning
* device identity
* telemetry
* edge computing
* gateways
* OTA
* fleet management
* device security
* time-series storage
* edge ML

---

## 33. Real-Time Systems

* real-time scheduling
* rate-monotonic scheduling
* earliest-deadline-first
* priority inversion
* WCET
* hard real-time
* soft real-time
* deadlines
* jitter
* deterministic systems
* RTOS
* real-time networking

---

## 34. Robotics

* robotics fundamentals
* kinematics
* inverse kinematics
* dynamics
* motion planning
* SLAM
* localization
* mapping
* sensor fusion
* Kalman filters
* particle filters
* computer vision
* path planning
* reinforcement learning
* ROS
* ROS2
* robot middleware

---

## 35. Quantum Computing

Useful as an advanced CS topic.

* qubits
* quantum gates
* superposition
* entanglement
* measurement
* quantum circuits
* quantum algorithms
* Grover
* Shor
* quantum error correction
* surface codes
* quantum cryptography
* quantum complexity
* Qiskit
* Cirq

---

## 36. Formal Methods

* formal verification
* model checking
* theorem proving
* SAT solving
* SMT solving
* temporal logic
* Hoare logic
* weakest preconditions
* refinement
* TLA+
* Alloy
* Coq
* Lean
* Isabelle
* Dafny
* model checking distributed systems

---

## 37. Reliability Engineering

* fault tolerance
* failure modes
* FMEA
* fault trees
* redundancy
* replication
* graceful degradation
* bulkheads
* circuit breakers
* retries
* exponential backoff
* jitter
* timeouts
* health checks
* chaos engineering
* disaster recovery
* RPO
* RTO
* backup strategies
* incident management
* postmortems

---

## 38. API / Protocol Design

* REST constraints
* RPC
* gRPC
* GraphQL
* WebSockets
* Webhooks
* SSE
* protocol versioning
* backward compatibility
* schema evolution
* protobuf
* Avro
* JSON Schema
* OpenAPI
* AsyncAPI
* idempotency
* pagination
* rate limiting
* API gateways
* service-to-service authentication

---

## 39. Serialization

* JSON
* XML
* YAML
* MessagePack
* CBOR
* Protocol Buffers
* Avro
* Thrift
* Cap'n Proto
* FlatBuffers
* serialization costs
* schema evolution
* backward compatibility
* zero-copy serialization

---

## 40. Developer Tools

* debuggers
* GDB
* LLDB
* Valgrind
* AddressSanitizer
* ThreadSanitizer
* UndefinedBehaviorSanitizer
* strace
* ltrace
* perf
* bpftrace
* tcpdump
* Wireshark
* objdump
* readelf
* nm
* ldd
* objcopy
* hexdump
* core dumps
* crash debugging
* postmortem debugging

---

## 41. Shell / Unix

* shell internals
* Bash
* Zsh
* pipes
* redirection
* process substitution
* signals
* job control
* environment variables
* file descriptors
* stdin/stdout/stderr
* Unix permissions
* ACLs
* cron
* systemd
* shell scripting
* awk
* sed
* grep
* xargs
* find
* command pipelines

---

## 42. Networking — Advanced

* BGP
* OSPF
* IS-IS
* MPLS
* VXLAN
* EVPN
* SDN
* network namespaces
* virtual networking
* bridges
* bonds
* tunneling
* GRE
* IPsec
* WireGuard
* DNSSEC
* Anycast
* multicast
* IGMP
* IPv6 routing
* ECMP
* DDoS mitigation
* network load balancing
* service mesh networking

---

## 43. Cloud Internals

Instead of only learning cloud products:

* virtualization internals
* hypervisors
* KVM
* Xen
* VM scheduling
* virtual networking
* virtual switches
* SR-IOV
* cloud storage architecture
* object storage internals
* autoscaling
* control plane vs data plane
* cloud metadata services
* cloud IAM architecture
* multi-tenancy
* noisy neighbors
* cloud economics
* FinOps
* serverless internals
* cold starts
* managed databases

---

## 44. Kubernetes Internals

* Kubernetes architecture
* API server
* etcd
* scheduler
* controller manager
* kubelet
* kube-proxy
* controllers
* reconciliation loops
* operators
* CRDs
* admission controllers
* RBAC
* networking
* CNI
* CSI
* storage
* scheduling
* taints/tolerations
* affinity
* autoscaling
* HPA
* VPA
* cluster autoscaler
* service discovery
* ingress
* Gateway API
* service mesh
* Kubernetes security

---

## 45. Infrastructure / Platform Engineering

* Terraform
* Pulumi
* Ansible
* Helm
* Argo CD
* Flux
* Crossplane
* Packer
* Vault
* Consul
* service discovery
* configuration management
* secrets management
* internal platforms
* developer portals
* golden paths
* platform APIs

---

## 46. Data Engineering

* ETL
* ELT
* data pipelines
* batch processing
* streaming
* data warehouses
* data lakes
* lakehouses
* Apache Spark
* Apache Flink
* Beam
* Airflow
* Dagster
* dbt
* Kafka
* schema registry
* data quality
* data lineage
* data governance
* CDC
* Debezium
* dimensional modeling
* star schema
* snowflake schema
* slowly changing dimensions

---

## 47. Analytics

* OLAP
* cubes
* columnar storage
* vectorized execution
* query engines
* Presto
* Trino
* DuckDB
* ClickHouse
* Druid
* materialized views
* approximate queries
* bitmap indexes
* analytical joins

---

## 48. Operating Systems — Advanced

* microkernels
* monolithic kernels
* hybrid kernels
* exokernels
* unikernels
* schedulers
* real-time kernels
* memory allocators
* virtual memory internals
* TLB
* huge pages
* NUMA
* copy-on-write
* memory-mapped files
* asynchronous I/O
* io_uring
* kernel bypass
* DPDK
* RDMA
* zero-copy networking

---

## 49. Hardware / Low-Level

* CPU microarchitecture
* ISA vs microarchitecture
* x86
* ARM
* RISC-V
* branch predictors
* speculative execution
* Spectre
* Meltdown
* cache attacks
* side channels
* memory ordering
* MESI
* MOESI
* cache coherence
* interconnects
* PCIe
* DMA
* NVMe
* NUMA
* accelerators
* TPUs
* NPUs

---

## 50. Interview-Specific Meta Topics

Create a section specifically about **engineering interview problem solving**.

* requirements clarification
* complexity analysis
* trade-off analysis
* designing under constraints
* estimation
* capacity planning
* debugging interviews
* code review interviews
* machine-coding interviews
* low-level design
* high-level design
* behavioral engineering interviews
* project deep dives
* production incident interviews
* OS interview patterns
* DBMS interview patterns
* networking interview patterns
* concurrency interview patterns
* ML system-design interviews
* backend interviews
* language-specific interviews


