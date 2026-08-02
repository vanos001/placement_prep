# Architecture - Quick Revision

> 📌 Last-minute revision before interviews. Scan these points quickly.

---

## Architecture Styles

- **Monolith**: Single deployable, shared DB, simple but inflexible
- **SOA**: Services share resources via ESB, coarser-grained
- **Microservices**: Independent services, own data, complex but scalable
- **Serverless**: FaaS (Lambda), pay-per-use, no server management

## Scaling

- **Vertical**: Bigger machine (simple, limited)
- **Horizontal**: More machines (complex, unlimited)
- **Stateless**: Easy horizontal scaling
- **Stateful**: Need sticky sessions or shared state

## Database Selection

- **SQL**: Structured, ACID, joins, relationships
- **Document (MongoDB)**: Flexible schema, hierarchical
- **Key-Value (Redis)**: Simple lookups, caching
- **Column (Cassandra)**: Time-series, write-heavy, HA
- **Graph (Neo4j)**: Relationships, social networks

## Communication

- **REST**: HTTP, stateless, CRUD, public APIs
- **gRPC**: HTTP/2 + protobuf, fast, typed, internal
- **WebSocket**: Full-duplex, real-time, persistent
- **Message Queue**: Async, decoupled (Kafka, RabbitMQ)
- **GraphQL**: Client queries, single endpoint

## Caching

- **Cache-Aside**: App checks cache → DB on miss
- **Write-Through**: Write to cache + DB simultaneously
- **Write-Behind**: Write to cache → Async to DB
- **Eviction**: LRU, LFU, TTL
- **Levels**: Client → CDN → API Gateway → App → DB

## Message Queues

- **Kafka**: High-throughput, event streaming
- **RabbitMQ**: Task queues, request-reply
- **Patterns**: Point-to-point, Pub/Sub, Fan-out

## Reliability Patterns

- **Circuit Breaker**: CLOSED → OPEN → HALF-OPEN
- **Bulkhead**: Isolate components
- **Retry + Backoff**: Exponential delay
- **Rate Limiting**: Throttle requests
- **Idempotency**: Same operation, same result

## Design Patterns

- **CQRS**: Separate read/write models
- **Event Sourcing**: Store events, not state
- **Saga**: Distributed transactions via compensating actions
- **Strangler Fig**: Incrementally replace monolith
- **Blue-Green**: Two environments, instant switch
- **Canary**: Gradual rollout

## Distributed Systems

- **CAP**: Consistency, Availability, Partition Tolerance (choose 2)
- **Consistency**: Strong (always latest) vs Eventual (converge eventually)
- **Sharding**: Horizontal partitioning (hash, range)
- **Replication**: Master-slave, master-master
- **Consistent Hashing**: Even distribution, minimal reshuffling
- **Consensus**: Raft, Paxos

## Deployment

- **Rolling**: Update one by one
- **Blue-Green**: Switch traffic
- **Canary**: Route small % first
- **Feature Flag**: Toggle without deployment

## Observability

- **Logs**: What happened (ELK, Loki)
- **Metrics**: How much (Prometheus, Grafana)
- **Traces**: Request flow (Jaeger, Zipkin)
- **Key metrics**: Latency (p50/p95/p99), throughput, error rate, saturation

## Security

- **AuthN**: Who are you? (JWT, OAuth)
- **AuthZ**: What can you do? (RBAC)
- **Encryption**: In transit (TLS) + at rest (AES)
- **OWASP Top 10**: Common vulnerabilities

## Microservices Communication

- **Synchronous**: REST, gRPC (request-response)
- **Asynchronous**: Message queues, events
- **Service Mesh**: Istio, Linkerd (sidecar proxy)
- **API Gateway**: Centralized entry point

## Key Concepts

- **Back-pressure**: Slow down producers when consumers can't keep up
- **Chaos Engineering**: Inject failures (Chaos Monkey)
- **12-Factor App**: Cloud-native best practices
- **Blue-green vs Canary**: Blue-green = instant switch, Canary = gradual

## System Design Framework

```
1. Requirements (5 min): Functional + Non-functional + Capacity
2. High-Level Design (10 min): Components + Data flow + API
3. Deep Dive (20 min): DB schema + Caching + Scaling
4. Trade-offs (10 min): Pros/cons + Alternatives
```

## 🔗 Cross-References

- [Architecture Cheatsheet](../cheatsheets/architecture.md) — Detailed reference
- [Architecture Interview Questions](../interview/arch-questions.md) — Full Q&A
- [System Design](../interview/system-design/README.md) — Apply these concepts
