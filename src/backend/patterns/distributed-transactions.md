# Distributed Transactions

## Overview

Distributed transactions span multiple services or databases. Unlike local transactions (ACID), distributed transactions must coordinate across network boundaries, handling failures, partial commits, and consistency.

## The Problem

```mermaid
flowchart TD
    ORDER[Order Service] -->|1. Create order| ORDER_DB[(Order DB)]
    ORDER -->|2. Reserve payment| PAYMENT[Payment Service]
    PAYMENT -->|3. Debit| PAYMENT_DB[(Payment DB)]
    ORDER -->|4. Reserve inventory| INVENTORY[Inventory Service]
    INVENTORY -->|5. Deduct| INVENTORY_DB[(Inventory DB)]
    
    subgraph "What if step 4 fails?"
        ISSUE[Order created, payment taken, but inventory unavailable!]
    end
```

## Two-Phase Commit (2PC)

### How It Works

```mermaid
sequenceDiagram
    participant C as Coordinator
    participant A as Participant A
    participant B as Participant B
    
    Note over C,B: Phase 1: Prepare
    C->>A: Prepare
    C->>B: Prepare
    A-->>C: Yes (ready)
    B-->>C: Yes (ready)
    
    Note over C,B: Phase 2: Commit
    C->>A: Commit
    C->>B: Commit
    A-->>C: Done
    B-->>C: Done
```

### 2PC Problems

| Problem | Description |
|---------|-------------|
| **Blocking** | Participants hold locks during prepare |
| **Single point of failure** | Coordinator failure blocks all |
| **Performance** | 2 round trips, lock contention |
| **Partial failure** | Some commit, some don't |

## Saga Pattern

A saga is a sequence of local transactions. Each publishes an event that triggers the next. If one fails, compensating transactions undo previous steps.

### Choreography-Based Saga

```mermaid
sequenceDiagram
    participant O as Order Service
    participant P as Payment Service
    participant I as Inventory Service
    participant S as Shipping Service
    
    O->>P: OrderCreated event
    P->>I: PaymentProcessed event
    I->>S: InventoryReserved event
    S->>O: ShippingScheduled event
    
    Note over O,S: If inventory fails
    I->>P: InventoryFailed event
    P->>O: PaymentRefunded event
```

### Orchestration-Based Saga

```mermaid
flowchart TD
    ORCH[Saga Orchestrator] -->|1. Create order| ORDER[Order Service]
    ORCH -->|2. Process payment| PAYMENT[Payment Service]
    ORCH -->|3. Reserve inventory| INVENTORY[Inventory Service]
    ORCH -->|4. Schedule shipping| SHIPPING[Shipping Service]
    
    INVENTORY -->|Fail| ORCH
    ORCH -->|Compensate: refund| PAYMENT
    ORCH -->|Compensate: cancel| ORDER
```

### Choreography vs Orchestration

| Choreography | Orchestration |
|--------------|---------------|
| No central coordinator | Central orchestrator |
| Events trigger next step | Orchestrator calls services |
| Loose coupling | Clear flow |
| Hard to understand flow | Easy to understand |
| Good for simple flows | Better for complex flows |

## Transactional Outbox Pattern

### Problem

Service needs to update database AND publish event atomically. Can't do both in one transaction if message broker is separate.

### Solution: Outbox Table

```mermaid
flowchart TD
    APP[Application] -->|Single transaction| DB[(Database)]
    DB -->|Write| TABLE[Main Table]
    DB -->|Write| OUTBOX[Outbox Table]
    POLLER[Poller/Debezium] -->|Read| OUTBOX
    POLLER -->|Publish| BROKER[Message Broker]
```

```python
# Single transaction
def create_order(order):
    with transaction():
        db.insert("orders", order)
        db.insert("outbox", {
            "event_type": "OrderCreated",
            "payload": order.to_json(),
            "published": False
        })
    # Separate process polls outbox and publishes
```

### Debezium (CDC)

```yaml
# Debezium connector captures changes from outbox table
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: outbox-connector
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  config:
    database.hostname: postgres
    database.dbname: orders
    table.include.list: public.outbox
    transforms: outbox
    transforms.outbox.type: io.debezium.transforms.outbox.EventRouter
```

## TCC (Try-Confirm-Cancel)

### How It Works

```mermaid
sequenceDiagram
    participant C as Coordinator
    participant P as Payment
    participant I as Inventory
    
    Note over C,I: Try Phase
    C->>P: Try: Reserve $100
    C->>I: Try: Reserve 5 units
    
    Note over C,I: Confirm Phase (if all succeed)
    C->>P: Confirm: Charge $100
    C->>I: Confirm: Deduct 5 units
    
    Note over C,I: Cancel Phase (if any fail)
    C->>P: Cancel: Release reservation
    C->>I: Cancel: Release reservation
```

### TCC vs Saga

| TCC | Saga |
|-----|------|
| Reserve resources first | Execute transactions first |
| Confirm or cancel | Compensate on failure |
| Pessimistic (lock resources) | Optimistic (compensate later) |
| Stronger consistency | Better availability |

## Eventually Consistent Patterns

### Polling Publisher

```python
# Background job polls for unprocessed events
def poll_outbox():
    while True:
        events = db.query("SELECT * FROM outbox WHERE published = false")
        for event in events:
            broker.publish(event)
            db.execute("UPDATE outbox SET published = true WHERE id = ?", event.id)
        time.sleep(1)
```

### Listen to Yourself

Consumer processes event, then publishes confirmation event. Original service listens for confirmation.

## Interview Questions

1. **2PC vs Saga?** — 2PC: strong consistency, blocking, synchronous. Saga: eventual consistency, non-blocking, async.
2. **When to use choreography vs orchestration?** — Choreography: simple flows, few services. Orchestration: complex flows, many services.
3. **How to handle partial failures in Saga?** — Compensating transactions. Each step must have a compensating action.
4. **What is the outbox pattern?** — Write events to a local outbox table in the same transaction as business data. Poller publishes to broker.
5. **How to make a saga idempotent?** — Idempotency keys, deduplication tables, event versioning
6. **TCC vs Saga?** — TCC: reserve resources first (pessimistic). Saga: execute and compensate (optimistic).
7. **How to test distributed transactions?** — Contract testing, chaos engineering, fault injection

## Related Topics

- [Microservices](./microservices.md) — Service decomposition
- [Event-Driven](./event-driven.md) — Event sourcing, CQRS
- [Kafka](../messaging/kafka.md) — Event streaming
- [Consensus](../../distributed/consensus/) — Coordination
