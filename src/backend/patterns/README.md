# Design Patterns

Backend design patterns are proven solutions to recurring architectural problems. This section covers patterns essential for building scalable, resilient distributed systems.

## In This Section

- [Microservices](./microservices.md) — Service decomposition and communication
- [Event-Driven Architecture](./event-driven.md) — Event-driven design
- [Event Sourcing](./event-sourcing.md) — History as the source of truth
- [CQRS](./cqrs.md) — Separating read and write models
- [Idempotency](./idempotency.md) — Safe retries and exactly-once effects
- [Distributed Transactions](./distributed-transactions.md) — Consistency across services

## Pattern Selection Guide

| Problem | Pattern |
|---------|---------|
| Tight coupling between services | Microservices + Messaging |
| Complex queries on event data | CQRS |
| Audit trail requirements | Event Sourcing |
| Cross-service consistency | Saga Pattern |
| Unreliable downstream services | Circuit Breaker |
| High read-to-write ratio | CQRS + Read Replicas |
