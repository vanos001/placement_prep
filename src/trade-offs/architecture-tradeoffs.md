# Architecture Trade-offs

Architecture decisions shape the trajectory of a codebase for years. Unlike a library upgrade, an architectural choice is difficult to reverse. This section covers the most common and consequential trade-offs evaluated in system design interviews.

## Monolith vs Microservices

### When to Choose Monolith
- Team size is small (under ~10 developers).
- The domain is well-understood with clear boundaries (or not yet understood enough to define service boundaries).
- Time-to-market is the priority over independent scalability.
- You are building an MVP or early-stage product.

### When to Choose Microservices
- Teams are large (20+ developers) and independently organized (Conway's Law).
- Different services have vastly different scaling requirements.
- Failure isolation is critical (one subsystem crashing must not bring down others).
- Polyglot requirements exist (ML service in Python, API in Go, etc.).

### Key Trade-offs

| Dimension | Monolith | Microservices |
|-----------|----------|--------------|
| Development Speed | Fast initially, slows as code grows | Slower initially (infrastructure setup), faster per-service iteration |
| Deployment | All-or-nothing | Independent deployments |
| Scaling | Vertical, or scale entire monolith | Per-service horizontal scaling |
| Data Management | Single database, easy joins | Per-service databases, eventual consistency required |
| Operational Complexity | Low | High (service discovery, circuit breakers, distributed tracing) |
| Testing | Simple unit/integration | Complex contract testing, integration testing across services |

### Interview Tip
Mention the "monolith-first" pattern: start with a well-structured monolith, extract services when clear scaling or organizational boundaries emerge. Premature microservices create distributed monoliths—worst of both worlds.

---

## Synchronous vs Asynchronous Communication

### When to Choose Synchronous
- The caller needs an immediate response to proceed (user-facing request).
- The operation is fast and latency-sensitive.
- Error handling requires immediate feedback.

### When to Choose Asynchronous
- The operation is long-running (video processing, report generation).
- You want to decouple services for independent scaling.
- You need to handle traffic spikes with a buffer (queue-based backpressure).
- The caller does not need the result immediately.

### Key Trade-offs
| Dimension | Synchronous | Asynchronous |
|-----------|------------|-------------|
| Latency | Immediate, blocks caller | Decoupled, non-blocking |
| Coupling | Tight (temporal) | Loose |
| Error Handling | Direct, immediate | Requires dead-letter queues, retry logic |
| Complexity | Lower | Higher (message ordering, idempotency, exactly-once) |
| Throughput | Limited by slowest dependency | Bounded by queue capacity + consumer speed |

---

## REST vs GraphQL vs gRPC

### When to Choose REST
- Public APIs with broad client diversity (mobile, web, third-party).
- Caching is critical (HTTP caching, CDN-friendly).
- Simple CRUD operations.

### When to Choose GraphQL
- Clients need flexible, self-service queries (avoid over/under-fetching).
- Aggregating data from multiple services (BFF pattern).
- Rapidly evolving frontend requirements.

### When to Choose gRPC
- Internal service-to-service communication.
- High performance is critical (binary protocol, HTTP/2 multiplexing).
- Strongly-typed contracts with code generation (Protobuf).

### Comparison Table

| Dimension | REST | GraphQL | gRPC |
|-----------|------|---------|------|
| Protocol | HTTP/1.1 (text) | HTTP (text) | HTTP/2 (binary) |
| Contract | OpenAPI (optional) | Schema (required) | Protobuf (required) |
| Caching | HTTP-native | Limited (requires persisted queries) | No built-in |
| Streaming | Server-sent (limited) | Subscriptions | Bidirectional |
| Overhead | Higher (JSON text) | Higher (JSON text) | Lower (binary) |
| Browser Support | Native | Native | Requires gRPC-Web proxy |

---

## Polling vs WebSockets vs Server-Sent Events (SSE)

### When to Choose Polling
- Simplicity is paramount.
- Updates are infrequent (status checks every 30 seconds).
- HTTP infrastructure constraints (proxies, firewalls block WebSocket upgrades).

### When to Choose WebSockets
- Bidirectional real-time communication (chat, gaming, collaborative editing).
- High-frequency updates (sub-second latency).
- Both client and server send messages frequently.

### When to Choose SSE
- Server-to-client streaming only (notifications, live feeds, stock prices).
- You want HTTP-native simplicity (auto-reconnection, works through proxies).
| Dimension | Polling | WebSockets | SSE |
|-----------|---------|-----------|-----|
| Direction | Client → Server | Bidirectional | Server → Client |
| Latency | High (interval-dependent) | Low | Low |
| Overhead | High (repeated connections) | Low (persistent) | Low (persistent) |
| Browser Support | Universal | Universal | Universal except IE |
| Complexity | Lowest | Highest (connection management) | Medium |
| Scalability | Easy (stateless) | Hard (stateful connections per client) | Medium |

---

## Vertical vs Horizontal Scaling

### When to Choose Vertical
- Quick scaling for short-term needs.
- Applications that are not designed for distribution (stateful in-memory data).
- Budget allows for powerful machines (databases often scale vertically).

### When to Choose Horizontal
- Stateless services (web servers, API gateways).
- Workloads that exceed single-machine capacity.
- Cost-efficient scaling: many cheap machines vs. one expensive machine.
- High availability requirements (eliminate single point of failure).

### Key Trade-offs
| Dimension | Vertical | Horizontal |
|-----------|----------|-----------|
| Cost | Exponential (high-end hardware) | Linear (commodity hardware) |
| Complexity | Low | High (load balancing, state management, consistency) |
| Limit | Hardware ceiling | Architectural ceiling (CAP theorem, coordination cost) |
| Availability | Single point of failure | Fault-tolerant with redundancy |

---

## Containers vs VMs

### When to Choose Containers
- Rapid deployment and rollback.
- Resource efficiency (shared OS kernel, lower overhead).
- Microservices architecture (small, isolated workloads).
- CI/CD pipelines requiring reproducible builds.

### When to Choose VMs
- Strong isolation requirements (multi-tenant, untrusted code).
- Running heterogeneous OS types (Windows + Linux).
- Legacy applications not designed for containers.
- Full OS control needed (custom kernels, kernel modules).

### Key Trade-offs
| Dimension | Containers | VMs |
|-----------|-----------|-----|
| Isolation | Process-level (shared kernel) | Hardware-level (separate kernel) |
| Boot Time | Seconds | Minutes |
| Resource Overhead | Low (~MB per container) | High (~GB per VM) |
| Density | High (many per host) | Low (few per host) |
| Security | Lower (kernel attack surface shared) | Higher (hardware isolation) |

---

## Kubernetes vs Serverless

### When to Choose Kubernetes
- Long-running, predictable workloads.
- Complex orchestration needs (stateful sets, daemon sets, custom operators).
- You need fine-grained control over networking, storage, and scheduling.
- Hybrid/multi-cloud requirements.

### When to Choose Serverless
- Event-driven, sporadic workloads (API endpoints triggered by requests).
- Rapid prototyping with minimal ops overhead.
- Cost optimization for low-traffic or bursty workloads (pay-per-invocation).
- Small team without dedicated platform engineering.

### Key Trade-offs
| Dimension | Kubernetes | Serverless |
|-----------|-----------|-----------|
| Control | Full (configurable everything) | Minimal (managed runtime) |
| Cost | Fixed (cluster nodes always running) | Variable (pay per use) |
| Cold Start | N/A (always warm) | Yes (up to seconds) |
| Ops Burden | High | Near-zero |
| Vendor Lock-in | Low (portable) | High (Lambda, Cloud Functions, etc.) |

---

## Threads vs Processes vs Coroutines

### When to Choose Threads
- CPU-bound parallelism on multi-core systems.
- Shared-memory data structures.
- Languages with native thread support (Java, C++, Go goroutines are threads).

### When to Choose Processes
- Maximum isolation (crash in one process does not affect others).
- Languages without thread safety or with a GIL (Python multiprocessing).
- Sandboxing untrusted code.

### When to Choose Coroutines
- I/O-bound workloads with high concurrency (thousands of concurrent connections).
- You need cooperative multitasking with low memory overhead.
- Languages with async/await support (Python asyncio, JavaScript, Rust async).

### Key Trade-offs
| Dimension | Threads | Processes | Coroutines |
|-----------|---------|----------|-----------|
| Memory Overhead | ~1-2 MB per thread | ~10s MB per process | ~KB per coroutine |
| Concurrency | OS-managed, preemptive | OS-managed, preemptive | User-managed, cooperative |
| Communication | Shared memory (needs synchronization) | IPC (pipes, sockets, shared memory) | Through event loop (channels) |
| Parallelism | True (multi-core) | True (multi-core) | Single-threaded (unless combined with threads) |
| Complexity | High (race conditions, deadlocks) | Medium (IPC complexity) | Low (sequential reasoning) |

---

## Queues vs Streams

### When to Choose Queues (Message Queues)
- Discrete work items (job processing, email sending, image resizing).
- At-least-once delivery semantics are sufficient.
- Consumers compete for messages (competing consumer pattern).
- Throughput with backpressure (buffer bursts).

### When to Choose Streams (Event Streams)
- Continuous data flows (user activity logs, sensor data, financial transactions).
- Replayability matters (consume from arbitrary offsets).
| Dimension | Queues | Streams |
|-----------|--------|---------|
| Delivery Model | Point-to-point | Publish-subscribe |
| Retention | Until consumed | Configurable time-based |
| Ordering | Per-queue or per-partition | Per-partition guaranteed |
| Replay | Generally no | Yes (offset-based) |
| Processing | Once per consumer group | Multiple consumer groups independently |
| Examples | RabbitMQ, SQS, Celery | Kafka, Kinesis, Pulsar |

---

## Shared Database vs Database per Service

### When to Choose Shared Database
- Microservices are early-stage and boundaries are unclear.
- Cross-service reporting and analytics are primary needs.
- You need ACID transactions across service domains.

### When to Choose Database per Service
- Services have distinct data models and access patterns.
| Dimension | Shared Database | Database per Service |
|-----------|----------------|---------------------|
| Coupling | Schema coupling (changes affect all services) | Loose coupling |
| Transactions | ACID across services | Requires Sagas or 2PC |
| Scalability | Shared bottleneck | Independent scaling |
| Data Ownership | Ambiguous | Clear ownership per service |
| Migration Risk | High (coordinated migrations) | Low (independent migrations) |

---

## Interview Questions

1. **"When should a startup choose microservices over a monolith?"**
   Answer: Almost never at inception. Choose microservices when team size, scaling requirements, or deployment independence demands it. Premature adoption creates operational overhead that diverts from product development.

2. **"Design a real-time chat system. Which communication protocol do you use?"**
   Answer: WebSockets for the core messaging (bidirectional, low latency), SSE for presence/typing indicators (server push only), and REST for profile/management APIs (CRUD with caching).

3. **"Compare Kubernetes and serverless for a new API gateway."**
   Answer: If traffic is predictable and you need consistent latency, Kubernetes. If traffic is bursty, the API is simple, and you want minimal ops, serverless. In practice, many systems use both—Kubernetes for core services, serverless for event handlers.

4. **"Why would you use coroutines instead of threads for a web crawler?"**
   Answer: A crawler makes thousands of concurrent HTTP requests, most of which are I/O-bound (waiting for network responses). Coroutines provide massive concurrency with minimal memory overhead (KB vs MB per thread) and avoid synchronization complexity.

5. **"When does a shared database become a problem in microservices?"**
   Answer: When schema changes in one service require coordinated deployments with others, when one service's heavy queries impact another's latency, or when you cannot independently scale data storage per service.
