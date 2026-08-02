# Architecture Interview Questions

> Comprehensive architecture and design questions with detailed answers.

---

## Q1: What is a microservices architecture?

**Answer:**

**Microservices** is an architecture where an application is built as a collection of small, independent services.

```
Monolith vs Microservices:

Monolith:                    Microservices:
┌──────────────────┐        ┌────────┐ ┌────────┐ ┌────────┐
│  User Service    │        │  User  │ │ Order  │ │Payment │
│  Order Service   │        │ Service│ │ Service│ │ Service│
│  Payment Service │        └───┬────┘ └───┬────┘ └───┬────┘
│  Notification    │            │          │          │
│  Service         │        ┌───▼──────────▼──────────▼────┐
│                  │        │     API Gateway               │
│  [Single DB]     │        └──────────────────────────────┘
└──────────────────┘
One codebase, one DB           Separate DBs per service
```

**Microservices Principles:**
- **Single Responsibility:** Each service does one thing well
- **Independent Deployment:** Deploy without affecting others
- **Decentralized Data:** Each service owns its database
- **Communication:** REST, gRPC, or message queues
- **Fault Isolation:** One service failure doesn't crash everything

**Pros vs Cons:**
| Pros | Cons |
|------|------|
| Independent scaling | Distributed system complexity |
| Technology diversity | Network latency between services |
| Team autonomy | Data consistency challenges |
| Fault isolation | Operational overhead |
| Faster deployment | Debugging difficulty |

---

## Q2: What is the difference between horizontal and vertical scaling?

**Answer:**

```
Vertical Scaling (Scale Up):
┌──────────┐         ┌──────────┐
│  Server  │         │  Server  │
│  4 CPU   │   →     │  16 CPU  │
│  8 GB    │         │  64 GB   │
└──────────┘         └──────────┘
Bigger machine

Horizontal Scaling (Scale Out):
┌──────────┐         ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Server  │    →    │  Server  │ │  Server  │ │  Server  │
│          │         │          │ │          │ │          │
└──────────┘         └──────────┘ └──────────┘ └──────────┘
More machines
```

| Aspect | Vertical | Horizontal |
|--------|----------|------------|
| Limit | Hardware maximum | Theoretically unlimited |
| Complexity | Simple | Complex (distributed) |
| Cost | Diminishing returns | Linear scaling |
| Downtime | Required for upgrade | Zero downtime |
| Single Point of Failure | Yes | No (with redundancy) |
| Data Consistency | Easy (shared memory) | Hard (distributed) |

---

## Q3: What is the CAP theorem and how does it apply?

**Answer:**

**CAP Theorem:** In a distributed system, you can only guarantee **2 out of 3**:

```
C (Consistency): Every read gets the most recent write
A (Availability): Every request gets a response (success/failure)
P (Partition Tolerance): System works despite network failures

Since network partitions are inevitable, the real choice is:
├── CP: Consistency over Availability
│   └── May reject requests to maintain consistency
│       Examples: ZooKeeper, etcd, HBase
│
└── AP: Availability over Consistency
    └── May return stale data to stay available
        Examples: Cassandra, DynamoDB, CouchDB
```

**PACELC Extension:**
```
If Partition:
  Choose A or C (same as CAP)
Else (normal operation):
  Choose between Latency and Consistency
```

---

## Q4: What is eventual consistency?

**Answer:**

**Eventual Consistency:** Given no new updates, all replicas will eventually converge to the same value.

```
Timeline:
  t=0: Write x=5 to Node A
  t=1: Node A has x=5, Node B has x=3 (old value)
  t=2: Replication propagates
  t=3: Node B has x=5 (consistent!)

Trade-off:
  Strong Consistency: Read always returns latest write
  ├── Pros: Simple mental model
  └── Cons: Higher latency, lower availability

  Eventual Consistency: Read may return stale data
  ├── Pros: Lower latency, higher availability
  └── Cons: Complex application logic

Use Cases:
├── Strong: Banking, inventory, booking systems
├── Eventual: Social media feeds, product catalogs, DNS
```

---

## Q5: What is a message queue and when to use it?

**Answer:**

**Message Queue** enables asynchronous communication between services.

```
Without Queue (Synchronous):
  Service A ──request──→ Service B ──request──→ Service C
  A waits for B, B waits for C
  Total time = A→B + B→C

With Queue (Asynchronous):
  Service A ──publish──→ Queue → Service B (processes independently)
  Service A continues immediately
  Total time = A→Queue (fast)
```

**When to use:**
- **Decoupling:** Services don't need to know about each other
- **Buffering:** Handle traffic spikes gracefully
- **Reliability:** Messages persisted until processed
- **Fan-out:** One message → multiple consumers
- **Ordering:** Guarantee message processing order

**Popular Systems:**
| System | Best For |
|--------|----------|
| Kafka | High-throughput event streaming, log aggregation |
| RabbitMQ | Task queues, request-reply patterns |
| SQS | Managed, simple queue |
| Redis Streams | Lightweight, in-memory |

---

## Q6: What is a circuit breaker?

**Answer:**

**Circuit Breaker** prevents cascading failures by stopping calls to a failing service.

```
States:
  CLOSED (normal) → OPEN (failing) → HALF-OPEN (testing)

┌──────────┐  failures > threshold  ┌──────────┐
│  CLOSED  │───────────────────────→│   OPEN   │
│ (normal) │                        │ (block)  │
└──────────┘                        └────┬─────┘
     ↑                                   │ timeout
     │            ┌───────────┐          │
     └────────────│ HALF-OPEN │◄─────────┘
     success      │ (testing) │
                  └───────────┘

Implementation:
  if circuit.state == OPEN:
      if now > circuit.last_failure + timeout:
          circuit.state = HALF_OPEN
      else:
          raise CircuitOpenError()

  try:
      response = call_service()
      circuit.record_success()
      circuit.state = CLOSED
  except Failure:
      circuit.record_failure()
      if circuit.failure_count > threshold:
          circuit.state = OPEN
```

---

## Q7: What is CQRS?

**Answer:**

**CQRS (Command Query Responsibility Segregation):** Separate the read and write models.

```
Traditional:
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  Client  │────→│  App     │────→│  Single  │
  │          │◄────│  Server  │◄────│  Database│
  └──────────┘     └──────────┘     └──────────┘
  Read and write use same model

CQRS:
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  Client  │────→│  Write   │────→│  Write   │
  │          │     │  Model   │     │  DB      │
  │          │     └──────────┘     └────┬─────┘
  │          │                          │ sync
  │          │     ┌──────────┐     ┌────▼─────┐
  │          │◄────│  Read    │◄────│  Read    │
  └──────────┘     │  Model   │     │  DB      │
                   └──────────┘     └──────────┘
  Separate models for reads and writes

Benefits:
├── Read model optimized for queries (denormalized)
├── Write model optimized for consistency (normalized)
├── Independent scaling
└── Different databases for reads vs writes
```

---

## Q8: What is event sourcing?

**Answer:**

**Event Sourcing:** Store all state changes as a sequence of events instead of current state.

```
Traditional (State-Based):
  Account: { id: 1, balance: 150 }

Event Sourcing:
  Events:
  1. AccountCreated { id: 1, balance: 0 }
  2. MoneyDeposited { amount: 200 }
  3. MoneyWithdrawn { amount: 50 }
  → Current state: 0 + 200 - 50 = 150

Benefits:
├── Complete audit trail
├── Can reconstruct state at any point in time
├── Can replay events to build projections
└── Natural fit for CQRS

Trade-offs:
├── Complexity (event schema evolution)
├── Storage (all events ever)
├── Querying current state requires replay/projections
└── Eventual consistency between write and read models
```

---

## Q9: What is a reverse proxy?

**Answer:**

A **reverse proxy** sits in front of web servers and forwards client requests.

```
Client → Reverse Proxy → Backend Servers

Functions:
├── Load Balancing: Distribute traffic across servers
├── SSL Termination: Handle HTTPS at proxy level
├── Caching: Cache responses to reduce backend load
├── Compression: Gzip responses
├── Security: Hide backend servers, DDoS protection
├── Rate Limiting: Throttle requests per client
└── Logging: Centralized access logs

Examples: Nginx, HAProxy, AWS ALB, Envoy
```

---

## Q10: What is the difference between monolith, SOA, and microservices?

**Answer:**

```
Monolith:
├── Single deployable unit
├── Shared database
├── Simple to develop and deploy initially
└── Problems at scale: deployment bottleneck, team coupling

SOA (Service-Oriented Architecture):
├── Services share resources (ESB, shared DB)
├── Service bus for communication
├── Coarser-grained services
└── Problems: ESB becomes bottleneck, heavy middleware

Microservices:
├── Fully independent services
├── Each service owns its data
├── Lightweight communication (REST, gRPC)
├── Fine-grained services
└── Problems: Distributed system complexity

Evolution:
  Monolith → Modular Monolith → SOA → Microservices
  (Don't jump to microservices unless you need to!)
```

---

## Q11-30: Quick-Fire Questions

**Q11: What is an API Gateway?**
Centralized entry point for all client requests. Handles: routing, authentication, rate limiting, request transformation, logging. Examples: Kong, AWS API Gateway, Envoy.

**Q12: What is service mesh?**
Infrastructure layer for service-to-service communication. Handles: load balancing, encryption, observability, traffic management. Examples: Istio, Linkerd. Sidecar proxy pattern.

**Q13: What is blue-green deployment?**
Two identical environments (blue = current, green = new). Deploy to green, test, switch traffic. Instant rollback by switching back. Trade-off: 2x infrastructure cost.

**Q14: What is canary deployment?**
Gradually roll out to small percentage of users. Monitor metrics, increase traffic if healthy. Safer than big-bang release. Used by: Google, Netflix.

**Q15: What is a feature flag?**
Toggle features on/off without deployment. Enables: A/B testing, gradual rollouts, kill switches. Tools: LaunchDarkly, Unleash.

**Q16: What is idempotency?**
Operation produces same result regardless of how many times it's executed. Critical for: retries, message processing. Example: PUT is idempotent, POST is not.

**Q17: What is eventual consistency vs strong consistency?**
Eventual: Replicas converge eventually (AP systems). Strong: Read always returns latest write (CP systems). Trade-off: latency vs correctness.

**Q18: What is a distributed transaction?**
Transaction spanning multiple services/databases. Patterns: 2PC (slow, blocking), Saga (compensating transactions), eventual consistency.

**Q19: What is the Saga pattern?**
Sequence of local transactions. Each publishes event triggering next. If failure: compensating transactions undo previous steps. Types: Choreography (events), Orchestration (central coordinator).

**Q20: What is database sharding?**
Horizontal partitioning across databases. Shard key determines placement. Challenges: cross-shard queries, rebalancing, hotspots.

**Q21: What is a content delivery network (CDN)?**
Distributed network of edge servers. Caches content closer to users. Reduces latency, origin load. Examples: CloudFront, Cloudflare, Akamai.

**Q22: What is caching? Where to cache?**
├── Client-side: Browser cache, mobile cache
├── CDN: Static assets
├── API Gateway: Response cache
├── Application: In-memory (Redis, Memcached)
├── Database: Query cache, buffer pool
└── Cache invalidation strategies: TTL, write-through, write-behind

**Q23: What is the Strangler Fig pattern?**
Incrementally migrate from monolith to microservices. New features built as services. Old features gradually extracted. No big-bang rewrite.

**Q24: What is observability?**
Three pillars: Logs (what happened), Metrics (how much), Traces (request flow). Tools: ELK (logs), Prometheus/Grafana (metrics), Jaeger (traces).

**Q25: What is chaos engineering?**
Intentionally inject failures to test system resilience. Netflix's Chaos Monkey. Build confidence in system's ability to handle production failures.

**Q26: What is the bulkhead pattern?**
Isolate components so failure doesn't cascade. Like bulkheads in a ship. Implementation: separate thread pools, connection pools per service.

**Q27: What is back-pressure?**
Mechanism to slow down producers when consumers can't keep up. Prevents overload. Examples: TCP flow control, reactive streams, message queue limits.

**Q28: What is a distributed cache?**
Cache spread across multiple nodes. Consistent hashing for key distribution. Examples: Redis Cluster, Memcached. Challenges: consistency, invalidation.

**Q29: What is twelve-factor app methodology?**
Best practices for SaaS apps: 1) Codebase, 2) Dependencies, 3) Config, 4) Backing services, 5) Build/release/run, 6) Processes, 7) Port binding, 8) Concurrency, 9) Disposability, 10) Dev/prod parity, 11) Logs, 12) Admin processes.

**Q30: What is the difference between REST and gRPC?**
REST: HTTP/1.1, JSON, human-readable, flexible. gRPC: HTTP/2, Protocol Buffers, binary, strongly typed, streaming. gRPC is faster, REST is more accessible.

## 🔗 Cross-References

- [Architecture Cheatsheet](../cheatsheets/architecture.md) — Quick reference for all architecture concepts
- [Architecture Revision](../revision/architecture.md) — Quick summary before interviews
- [System Design](./system-design/README.md) — Apply these concepts in design problems
- [OS Questions](./os-questions.md) — Concurrency, scheduling concepts
