# Architecture Cheatsheet

## 🏗️ Architecture Styles

```
Monolith: Single deployable unit, shared DB
SOA: Services share resources via ESB
Microservices: Independent services, own data
Serverless: Functions as a Service (Lambda)
```

## 📈 Scaling

```
Vertical (Scale Up): Bigger machine
Horizontal (Scale Out): More machines

Stateless Services: Easy horizontal scaling
Stateful Services: Need sticky sessions or shared state
```

## 🗄️ Database Selection

```
SQL (PostgreSQL, MySQL):
  Structured data, ACID, complex queries, relationships

NoSQL - Document (MongoDB):
  Flexible schema, hierarchical data, rapid development

NoSQL - Key-Value (Redis, DynamoDB):
  Simple lookups, caching, session storage

NoSQL - Column (Cassandra, HBase):
  Time-series, write-heavy, high availability

NoSQL - Graph (Neo4j):
  Relationships, social networks, fraud detection
```

## 📨 Communication Patterns

```
REST: HTTP, stateless, CRUD operations, public APIs
gRPC: HTTP/2 + protobuf, fast, typed, internal services
WebSocket: Full-duplex, real-time, persistent
Message Queue: Async, decoupled, reliable (Kafka, RabbitMQ)
GraphQL: Client queries, single endpoint, flexible
```

## 🗃️ Caching

```
Strategies:
  Cache-Aside: App checks cache → DB on miss → Update cache
  Write-Through: Write to cache + DB simultaneously
  Write-Behind: Write to cache → Async write to DB
  Read-Through: Cache handles DB reads automatically

Eviction: LRU, LFU, TTL, FIFO

Cache Levels:
  Client → CDN → API Gateway → App → Database
```

## 📊 Message Queues

```
Kafka: High-throughput, event streaming, log aggregation
RabbitMQ: Task queues, request-reply
SQS: Managed, simple
Redis Streams: Lightweight, in-memory

Patterns:
  Point-to-Point: One producer, one consumer
  Pub/Sub: One producer, many consumers
  Fan-out: One message → multiple queues
```

## 🔒 Reliability Patterns

```
Circuit Breaker: Stop calling failing service
  CLOSED → OPEN (failures > threshold) → HALF-OPEN (timeout) → CLOSED

Bulkhead: Isolate components (separate thread pools)
Retry + Backoff: Retry with exponential delay
Timeout: Don't wait forever
Rate Limiting: Throttle requests per client
Idempotency: Same operation, same result (safe retries)
```

## 🎯 Design Patterns

```
CQRS: Separate read/write models
Event Sourcing: Store events, not state
Saga: Distributed transactions via compensating actions
  - Choreography: Events trigger next step
  - Orchestration: Central coordinator
Strangler Fig: Incrementally replace monolith
Blue-Green: Two identical environments, instant switch
Canary: Gradual rollout to subset of users
Feature Flag: Toggle features without deployment
```

## 🌐 Distributed Systems Concepts

```
CAP Theorem: Choose 2: Consistency, Availability, Partition Tolerance
  CP: Consistent but may reject (HBase, MongoDB)
  AP: Available but may be stale (Cassandra, DynamoDB)

Consistency Models:
  Strong: Read always returns latest write
  Eventual: Replicas converge eventually
  Causal: Preserves causal ordering

Consensus: Raft, Paxos (leader election, log replication)
Consistent Hashing: Even distribution, minimal reshuffling
Sharding: Horizontal partitioning (hash, range, geographic)
Replication: Master-slave, master-master, multi-region
```

## 📱 Deployment Strategies

```
Rolling: Update instances one by one
Blue-Green: Switch traffic to new environment
Canary: Route small % to new version, monitor, increase
Shadow: New version receives traffic but responses discarded
A/B Testing: Different versions for different user segments
```

## 🔧 Microservices Communication

```
Synchronous: REST, gRPC (request-response)
Asynchronous: Message queues, events (fire-and-forget)

Service Mesh: Infrastructure for service communication
  - Sidecar proxy pattern
  - Examples: Istio, Linkerd
  - Handles: Load balancing, encryption, observability

API Gateway: Centralized entry point
  - Routing, auth, rate limiting, SSL termination
  - Examples: Kong, AWS API Gateway, Envoy
```

## 📊 Observability

```
Three Pillars:
  Logs: What happened (ELK stack, Loki)
  Metrics: How much (Prometheus, Grafana, Datadog)
  Traces: Request flow (Jaeger, Zipkin, OpenTelemetry)

Key Metrics:
  Latency: p50, p95, p99
  Throughput: Requests per second
  Error Rate: 4xx, 5xx percentage
  Saturation: Resource utilization
```

## 🛡️ Security

```
Authentication: Who are you? (JWT, OAuth, SAML)
Authorization: What can you do? (RBAC, ABAC)
Encryption: In transit (TLS) + at rest (AES)
Rate Limiting: Prevent abuse
Input Validation: Prevent injection
CORS: Cross-origin policy
OWASP Top 10: Common vulnerabilities
```

## ⚡ Quick Facts

- **Idempotent**: Same request, same result (PUT, DELETE)
- **Not idempotent**: Different result each time (POST)
- **Back-pressure**: Slow down producers when consumers can't keep up
- **Chaos Engineering**: Intentionally inject failures (Netflix Chaos Monkey)
- **12-Factor App**: Best practices for cloud-native apps
- **Twelve-Factor**: Codebase, Dependencies, Config, Backing Services, Build/Release/Run, Processes, Port Binding, Concurrency, Disposability, Dev/Prod Parity, Logs, Admin

## 🔗 Cross-References

- [Architecture Interview Questions](../interview/arch-questions.md) — Detailed answers
- [Architecture Revision](../revision/architecture.md) — Quick summary
- [System Design](../interview/system-design/README.md) — Apply these concepts
