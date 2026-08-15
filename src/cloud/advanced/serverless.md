# Advanced Serverless Computing

## Serverless Scheduling Internals

Serverless platforms (AWS Lambda, Google Cloud Functions, Azure Functions) abstract away infrastructure management, but this abstraction is built on sophisticated scheduling systems. Understanding what happens under the hood is critical for performance optimization and interview depth.

**Serverless request lifecycle:**

```
User Request
    │
    ▼
API Gateway / Function URL
    │
    ▼
Load Balancer (per-region)
    │
    ▼
┌─────────────────────────────────────────┐
│         Worker Placement Engine           │
│                                          │
│  1. Check: Is there a warm instance?      │
│     ├── YES → Route to it                │
│     └── NO  → Provision new instance      │
│                                          │
│  2. Provisioning:                         │
│     a. Select host machine (scheduling)   │
│     b. Create microVM / container         │
│     c. Mount code + layers                │
│     d. Initialize runtime                │
│     e. Invoke handler                    │
└─────────────────────────────────────────┘
```

The **worker placement engine** is the unsung hero. It must balance: (1) minimizing cold starts by reusing warm instances, (2) packing workers efficiently on host machines, (3) ensuring fair resource allocation across customers/accounts, and (4) respecting per-account concurrency limits. AWS uses a two-level scheduler: a global scheduler assigns capacity to availability zones, and per-AZ schedulers place workers on specific hosts.

## Cold Starts: The Definitive Analysis

A cold start is the latency incurred when a new function instance must be provisioned before handling a request. It's the single most discussed serverless performance issue.

**Cold start breakdown (AWS Lambda, Node.js runtime):**

| Phase | Duration | Optimizable? |
-------|----------|-------------|
| VM/Container provisioning | 50–200ms | Partially (microVM snapshot) |
| Runtime download/init | 100–500ms | Yes (custom runtime) |
| Application code load | 50–300ms | Yes (minification, lazy imports) |
| Static initialization (module-level code) | 0–5000ms+ | Yes (minimize heavy init) |
| Handler invocation setup | 5–20ms | No |
| **Total** | **200ms–6s** | |

**Provisioned Concurrency** (AWS Lambda) pre-initializes a specified number of instances, eliminating cold starts for up to that concurrency level. Cost: you pay for the provisioned instances whether or not they receive traffic. This is the nuclear option — effective but expensive.

### Warm Pools
Warm pools maintain a buffer of pre-initialized function instances. When traffic arrives, instances from the warm pool are assigned immediately. When an instance finishes handling a request, it returns to the warm pool rather than being terminated.

**Warm pool management strategies:**
1. **Fixed-size**: Keep N instances always warm. Simple but wasteful for variable traffic.
2. **Traffic-predictive**: Scale the warm pool based on historical traffic patterns. AWS uses this internally.
3. **Event-driven**: Pre-warm functions based on upstream events (e.g., pre-warm the order-processing function when a payment event is detected).

### Snapshotting Serverless Functions
**Firecracker microVM snapshotting** enables fast cold starts by restoring from a memory snapshot rather than booting from scratch. The flow:

1. Function instance is initialized and warmed up.
2. The entire microVM memory state is serialized to a snapshot (~50–200ms).
3. Snapshot is stored in the host machine's local SSD.
4. On cold start, the snapshot is loaded into a new microVM (~5–20ms).

This reduces cold start time by 5–10x compared to full initialization. AWS uses this for SnapStart (Java Lambda) and internally for all Lambda runtimes.

> **Interview Angle**: "How would you reduce P99 cold start latency from 3 seconds to under 500ms?" (1) Use Firecracker snapshotting to skip runtime init, (2) minimize static initialization code, (3) use provisioned concurrency for the critical path, (4) consider switching to a compiled language with faster startup, (5) implement a client-side keep-alive pattern.

## MicroVMs and Firecracker

Traditional serverless platforms used containers (Docker) for isolation, but container startup is slow (~1–2 seconds) and the attack surface is large. **AWS Firecracker** addresses both problems.

**Firecracker** is a lightweight virtual machine monitor (VMM) that creates microVMs in ~125ms with <5MB of memory overhead. Each microVM runs a minimal Linux kernel (crosvm-based) with no unnecessary kernel modules, reducing the attack surface to ~60K lines of code (vs. millions in a full VM or container).

```
Traditional Container Isolation:         Firecracker MicroVM:
┌───────────────────────────┐         ┌─────────────────────┐
│ Host Kernel (shared)      │         │ Host Kernel         │
│  ┌───────────────────┐    │         │  ┌───────────────┐  │
│  │ Container Runtime │    │         │  │ Firecracker   │  │
│  │ ┌───────────────┐│    │         │  │ VMM           │  │
│  │ │ App A  App B  ││    │         │  │ ┌───────────┐ │  │
│  │ │ (shared kernel││    │         │  │ │Guest      │ │  │
│  │ │  risk!)      ││    │         │  │ │Kernel     │ │  │
│  │ └───────────────┘│    │         │  │ │ ┌───────┐ │ │  │
│  └───────────────────┘    │         │  │ │ │Guest  │ │ │  │
└───────────────────────────┘         │  │ │ │App A  │ │ │  │
                                       │  │ │ └───────┘ │ │  │
Attack surface: large                  │  │ └───────────┘ │  │
                                       │  ├───────────────┤  │
                                       │  │Firecracker VMM │  │
                                       │  │ ┌───────────┐ │  │
                                       │  │ │Guest      │ │  │
                                       │  │ │Kernel     │ │  │
                                       │  │ │ ┌───────┐ │ │  │
                                       │  │ │ │Guest  │ │ │  │
                                       │  │ │ │App B  │ │ │  │
                                       │  │ │ └───────┘ │ │  │
                                       │  │ └───────────┘ │  │
                                       │  └───────────────┘  │
                                       │ Attack surface: ~60K LOC
                                       └─────────────────────┘
```

**Key Firecracker properties:**
- Boot time: ~125ms (vs. ~1–2s for containers)
- Memory overhead: <5MB per microVM (vs. ~10–50MB for containers)
- Isolation: Full VM-level (kernel-level separation)
- Device model: Minimal — only virtio-net, virtio-block, serial console, and a minimal MMIO device
- Security: Seccomp filters, jailing the Firecracker process itself

Firecracker's limitation is that it only supports Linux guests and has minimal device support. For production serverless, this is sufficient because functions don't need GPUs, USB devices, or complex networking.

## Function Placement and Migration

Serverless function placement determines which physical host runs a given function instance. This matters for:

- **Data locality**: Placing a function near its database or cache reduces network latency.
- **Resource affinity**: Functions that share state (e.g., via a local cache) benefit from co-location.
- **Load balancing**: Distributing function instances across hosts prevents hot spots.

**Function migration** moves a running function from one host to another. This is rare in public cloud serverless (functions are stateless, so you just start a new instance elsewhere), but important in edge computing where a mobile user's function might need to follow them across edge locations.

## Stateful Serverless and Durable Execution

### The Statefulness Problem
Pure serverless functions are stateless — all state must live in external services (DynamoDB, S3, Redis). This works for simple request-response patterns but breaks for:
- Multi-step workflows that span minutes or hours
- Processes that need to resume after failures
- Human-in-the-loop approvals
- Long-running orchestrations (ETL pipelines, ML training)

### Durable Execution
Durable execution systems (AWS Step Functions, Temporal, Azure Durable Functions) provide stateful, reliable execution on top of stateless infrastructure. The key insight: **persist every step's input/output to durable storage before executing it**.

```
Durable Execution Model:

┌─────────────────────────────────────────────────┐
│               Workflow Engine                     │
│                                                  │
│  1. Receive task (persist to DB)                 │
│  2. Dispatch to worker                           │
│  3. Worker executes, returns result              │
│  4. Persist result (write-ahead log)             │
│  5. Determine next step                          │
│  6. Repeat until workflow complete               │
│                                                  │
│  On worker crash:                                │
│  - Workflow engine detects timeout               │
│  - Re-dispatch task to new worker                │
│  - Worker loads persisted state and resumes      │
└─────────────────────────────────────────────────┘
```

### Temporal Workflows
**Temporal** is an open-source durable execution platform originally developed at Uber. It's become the standard for stateful workflows in microservice architectures.

**Key Temporal concepts:**
- **Workflow**: A deterministic function that defines the orchestration logic. Workflows must be deterministic because they may be replayed from the beginning during recovery.
- **Activity**: A non-deterministic operation (API call, DB query, file I/O) that produces a side effect. Activities are retried individually on failure.
- **Task queue**: A durable message queue connecting workflow workers to activity workers.
- **Workflow history**: The complete, append-only log of every event in a workflow's lifetime. This is the source of truth for recovery.

**Temporal workflow determinism** is the most important concept. Workflow code must be deterministic because Temporal may replay the workflow from the beginning when recovering from a failure. All non-deterministic operations (random number generation, current time, network calls) must be done inside activities, not workflows.

```python
# Pseudocode: Temporal workflow for order processing
@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, order: Order):
        # 1. Reserve inventory (activity — retriable)
        await workflow.execute_activity(
            reserve_inventory, order.items,
            start_to_close_timeout=timedelta(seconds=30)
        )

        # 2. Charge payment (activity — retriable)
        payment_result = await workflow.execute_activity(
            charge_payment, order.payment_info,
            retry_policy=RetryPolicy(max_attempts=3)
        )

        # 3. Wait for human approval (durable timer)
        await workflow.start_timer(timedelta(hours=24))

        # 4. Ship order (activity)
        await workflow.execute_activity(ship_order, order)

        # 5. Send confirmation (activity)
        await workflow.execute_activity(send_confirmation, order.email)
```

> **Interview Angle**: "How would you implement a payment processing workflow that handles retries, timeouts, and human approvals?" Use Temporal: define a workflow that calls payment activity (with retry policy), waits on a signal for human approval (durable timer as fallback), and continues. The workflow history provides audit trail. Activities are retried independently.

## Serverless Databases and Storage

Serverless databases automatically scale capacity (and cost) with demand:

| Service | Model | Scale Mechanism | Cold Start? |
|---------|-------|-----------------|-------------|
| AWS Aurora Serverless v2 | Relational | Instant capacity scaling (ACU) | Minimal (~seconds) |
| DynamoDB On-Demand | Key-value/Doc | No provisioning, pay per request | No |
| PlanetScale | MySQL-compatible | Scale to zero, autoscale | Yes (~30s) |
| Neon | PostgreSQL | Scale to zero, autoscale | Yes (~1s) |
| Cloudflare D1 | SQLite at edge | Global replicas, scale to zero | No |
| Upstash Redis | Key-value | Pay per request, scale to zero | No |

**The cold start problem extends to databases.** Serverless databases that scale to zero (Neon, PlanetScale) have their own cold starts while provisioning compute for the query engine. This can add 1–30 seconds to the first query after idle. Solutions: keep a minimal warm connection pool, use connection pooling services (PgBouncer, AWS RDS Proxy).

## Event-Driven Compute

Event-driven architectures and serverless are natural companions. The pattern: an event triggers a function, which may produce more events.

**Event delivery guarantees:**
- **At-least-once**: The event will be delivered, possibly multiple times. Functions must be idempotent. SQS, SNS, and most event buses provide this.
- **At-most-once**: The event may be lost. Faster but unreliable. Some IoT systems use this.
- **Exactly-once**: The event is processed exactly once. Requires idempotent consumers with deduplication, or transactional event processing. Kafka with idempotent producer + transactional consumer can achieve this.

## Edge Functions and Edge Runtimes

Edge functions run at CDN edge locations (200–400+ globally) to minimize latency for end users. The trade-off: edge runtimes are constrained (limited runtime support, smaller memory, shorter execution timeouts).

**Major edge platforms:**

| Platform | Runtime | Max Duration | Cold Start | Key Differentiator |
|----------|---------|-------------|------------|-------------------|
| Cloudflare Workers | V8 isolate (JS/WASM) | 30s (paid: unlimited) | <5ms | Global, V8 speed |
| Vercel Edge Functions | V8 isolate | 60s | <5ms | Next.js integration |
| AWS Lambda@Edge | Node.js/Python | 5–30s | 50–200ms | Lambda ecosystem |
| Deno Deploy | Deno runtime | 60s | <10ms | TypeScript native |
| Fastly Compute@Edge | WASM | 300ms (free) | <5ms | WASM-native, lowest latency |

**V8 isolates** (used by Cloudflare Workers) are faster to start than microVMs because they don't include a full OS — they're a single process with isolated V8 JavaScript contexts. Startup time: ~5ms vs. ~125ms for Firecracker.

## WASM at the Edge

**WebAssembly (WASM)** is emerging as the runtime of choice for edge computing. WASM provides:

- **Near-native performance**: WASM compiles to machine code, executing 1–2x slower than native C++ (vs. 5–10x slower for JavaScript).
- **Language diversity**: Write in Rust, C++, Go, or any WASM-targeting language, run anywhere.
- **Sandboxed execution**: WASM's linear memory model provides strong isolation without VM overhead.
- **Tiny cold start**: WASM modules are ~100KB–5MB and start in <1ms.
- **Deterministic execution**: WASM has no undefined behavior, making it ideal for reproducible edge logic.

**WASM at the edge is used for:**
- A/B testing and feature flags at the edge (Cloudflare Workers, Fastly)
- Image transformation and optimization at the edge
- Authentication and authorization token validation
- Request routing and header manipulation
- Geolocation-based personalization

```
Edge Request Processing with WASM:

  User (Tokyo) ──► Edge PoP (Tokyo) ──► WASM Module
  User (London) ──► Edge PoP (London) ──► Same WASM Module
  User (NYC)    ──► Edge PoP (NYC)    ──► Same WASM Module

  All edge PoPs run identical WASM code.
  Latency to user: 5–20ms (vs. 100–300ms to origin).
```

> **Interview Angle**: "When would you use edge functions vs. a centralized serverless function?" Edge functions for latency-sensitive, read-heavy operations (auth, routing, A/B testing, personalization) where the logic is small and stateless. Centralized serverless for compute-heavy, stateful, or long-running operations (ML inference, database writes, video processing).

## Key Takeaways

1. **Cold starts are a multi-phase problem** — each phase (VM provisioning, runtime init, app init) offers different optimization opportunities.
2. **Firecracker's innovation is minimalism** — a 60K-line VMM that boots in 125ms with full VM isolation.
3. **Durable execution bridges stateless and stateful** — Temporal/Step Functions persist workflow state, enabling reliable multi-step processes on serverless.
4. **WASM at the edge is the future** — sub-millisecond cold starts, multi-language support, and deterministic execution.
5. **Serverless databases can have cold starts too** — scaling to zero is great for cost, but the first query after idle may be slow.