# Distributed Transactions

> **Reference papers**: Gray (1978) — two-phase commit; Skeen (1981) — three-phase commit; Garcia-Molina & Salem (1987) — Sagas; Patell et al. (2003) — TCC

## Two-Phase Commit (2PC)

2PC is the workhorse protocol for ensuring atomicity across multiple participants (databases, message queues, etc.) in a distributed transaction. A **coordinator** orchestrates the protocol.

### Phase 1: Prepare (Voting Phase)

The coordinator asks all participants to vote on whether they can commit:

```
  Coordinator              P1              P2              P3
     │                     │               │               │
     │── PREPARE(T) ───────>│               │               │
     │── PREPARE(T) ───────────────────────>│               │
     │── PREPARE(T) ──────────────────────────────────────>│
     │                     │               │               │
     │<── VOTE_COMMIT ──────│               │               │
     │<── VOTE_COMMIT ──────────────────────│               │
     │<── VOTE_COMMIT ─────────────────────────────────────│
```

Each participant:
1. Writes an **intent** record to its stable storage (WAL)
2. Acquires all necessary locks
3. Responds VOTE_COMMIT (yes) or VOTE_ABORT (no)

### Phase 2: Commit/Abort (Decision Phase)

If all participants voted commit, the coordinator decides COMMIT. Otherwise, it decides ABORT.

```
  Coordinator              P1              P2              P3
     │                     │               │               │
     │── COMMIT(T) ────────>│               │               │
     │── COMMIT(T) ───────────────────────>│               │
     │── COMMIT(T) ───────────────────────────────────────>│
     │                     │               │               │
     │<── ACK ──────────────│               │               │
     │<── ACK ─────────────────────────────│               │
     │<── ACK ────────────────────────────────────────────│
```

### 2PC Failure Scenarios

| Failure Point | Recovery Action |
|--------------|-----------------|
| Participant crashes before voting | Coordinator times out → ABORT (no vote = no) |
| Participant crashes after voting COMMIT | On recovery, participant asks coordinator for decision |
| Coordinator crashes after Phase 1 | Participants are **blocked** — they hold locks but don't know the decision. Must wait for coordinator recovery. |
| Coordinator crashes after Phase 2 (some committed) | Coordinator recovery reads its decision log and re-sends to uncommitted participants |

### The Blocking Problem

2PC's critical flaw: if the coordinator crashes between Phase 1 and Phase 2, participants are **blocked** holding locks. This can cascade — if other transactions need those locks, the entire system grinds to a halt.

## Three-Phase Commit (3PC)

3PC (Skeen, 1981) adds a third phase to eliminate blocking under crash failures (but not network partitions). It requires the **partially synchronous** model.

### Phases

```
Phase 1: CanCommit (like Prepare, but participants can also vote ABORT)
Phase 2: PreCommit (coordinator tells all to prepare to commit — writes intent to log)
Phase 3: DoCommit (actual commit)
```

### Why 3PC is Non-Blocking

If the coordinator crashes, participants can safely decide:
- If any participant voted ABORT → ABORT
- If all voted COMMIT and no PreCommit was received → ABORT (coordinator may not have decided)
- If PreCommit was received → COMMIT (the coordinator decided COMMIT before sending PreCommit, and at least one participant got it, so another coordinator can learn the decision)

The key insight: the **PreCommit phase acts as a synchronization barrier**. Once a participant receives PreCommit, it knows that *all* participants voted commit, so the decision must be commit.

### Why 3PC is Rarely Used

1. **Still blocks under network partitions**: if a partition separates the coordinator from a participant after Phase 1, both sides may independently decide (coordinator: ABORT due to timeout; partitioned participant: COMMIT if it received PreCommit) — violating atomicity.
2. **Extra latency**: one more round trip compared to 2PC.
3. **Practical alternative**: use 2PC with coordinator replication (e.g., Paxos for the coordinator log), which achieves non-blocking behavior more simply.

### Presumed Abort / Presumed Commit

Optimizations that reduce the coordinator's log I/O:

- **Presumed Abort**: the coordinator does **not** log the abort decision (since abort is the default). Participants that don't hear from the coordinator eventually time out and abort.
- **Presumed Commit**: the coordinator does **not** log the commit decision to stable storage before sending it. Instead, after all participants ACK, it writes a single "all done" record. On recovery, if there's no record, the coordinator assumes commit and re-sends.

| Optimization | Log Writes | Risk | Used When |
|-------------|-----------|------|-----------|
| None | 3 (start, decision, end) | None | Safety-critical |
| Presumed Abort | 2 (start, end-if-commit) | Minimal (abort is default) | Most systems |
| Presumed Commit | 2 (start, end-if-abort) | Minimal (commit is expected) | Low-abort-rate workloads |

## Distributed Deadlock Detection

### Wait-For Graph (WFG)

A directed graph where nodes are transactions and an edge `T1 → T2` means T1 is waiting for a lock held by T2. A **cycle** in the WFG indicates a deadlock.

```
  T1 ──waits for──> T2 ──waits for──> T3
                      ^                │
                      └────────────────┘  cycle → deadlock!
```

### Centralized Detection

A single deadlock detector maintains the global WFG by collecting local WFGs from all nodes. It periodically runs cycle detection (DFS).

### Distributed Detection

Each node maintains a local WFG. When a transaction on node A waits for a lock on node B, node A sends a **probe** to node B, which forwards it to the next waiter. If a probe returns to its origin, a cycle is detected.

```
  Node 1: T1 waits for lock on Node 2
  → Probe(T1) sent to Node 2
  Node 2: T2 (holder) waits for lock on Node 3
  → Probe(T1, T2) sent to Node 3
  Node 3: T3 (holder) waits for lock on Node 1
  → Probe(T1, T2, T3) sent to Node 1
  Node 1: T3 is waiting for T1 (which originated the probe) → CYCLE DETECTED!
```

## Saga Pattern

A **Saga** (Garcia-Molina & Salem, 1987) breaks a distributed transaction into a sequence of **local transactions**, each with a **compensating action** that undoes its effect. If any step fails, the saga executes compensating actions for all previously completed steps.

### Saga Types

#### Choreography-Based Saga

Each local transaction publishes an event when it completes. The next transaction listens for that event and starts. No central coordinator.

```
  Order Service          Payment Service       Inventory Service
       │                       │                     │
       │── OrderCreated ───────>│                     │
       │                       │── PaymentProcessed →│
       │                       │                     │── InventoryReserved
       │<── OrderCompleted ─────│<────────────────────│
```

#### Orchestration-Based Saga

A central **saga orchestrator** invokes each step and handles failures by triggering compensations.

```
  Saga Orchestrator
       │
       │── createOrder() ──→ Order Service
       │<── orderCreated ────┘
       │
       │── processPayment() → Payment Service
       │<── paymentProcessed ─┘
       │
       │── reserveInventory() → Inventory Service
       │     (if fails: ──> compensatePayment())
```

### Comparison

| Aspect | 2PC | Saga |
|--------|-----|------|
| Isolation | Full (locks held) | None (intermediate state visible) |
| Atomicity | Atomic (all or nothing) | Eventually consistent (compensations) |
| Locking | Yes (blocks) | No (non-blocking) |
| Availability | Lower (locks) | Higher (no locks) |
| Failure recovery | Coordinator decides | Compensating transactions |
| Used by | Traditional databases | Microservices, event-driven |

## Try-Confirm/Cancel (TCC)

TCC is a variant of the Saga pattern where each participant implements three operations:

1. **Try**: reserve resources (e.g., freeze account balance)
2. **Confirm**: commit the reserved resources (e.g., actually deduct balance)
3. **Cancel**: release the reserved resources (e.g., unfreeze balance)

```python
class PaymentTCC:
    def try(self, order_id, amount):
        # Freeze the amount in the user's account
        account = db.get_account(user_id)
        if account.available >= amount:
            account.frozen += amount
            account.available -= amount
            db.save(account)
            return TCCStatus.TRY_SUCCESS
        return TCCStatus.TRY_FAILED
    
    def confirm(self, order_id, amount):
        # Deduct the frozen amount permanently
        account = db.get_account(user_id)
        account.frozen -= amount
        account.total -= amount
        db.save(account)
    
    def cancel(self, order_id, amount):
        # Unfreeze the amount
        account = db.get_account(user_id)
        account.frozen -= amount
        account.available += amount
        db.save(account)
```

TCC provides stronger isolation than choreography Sagas (the Try phase reserves resources) but still doesn't provide full serializability.

## Transactional Outbox Pattern

The **outbox pattern** solves the dual-write problem: when you need to update a database table **and** publish a message/event atomically, you can't do both in a single transaction across different systems.

### Solution

Write both the data change and the event to the **same database transaction** into an **outbox table**. A separate process (polling or CDC) reads the outbox and publishes the events to the message broker.

```
  1. Application code:
     BEGIN TRANSACTION
       INSERT INTO orders (id, status, ...) VALUES (...)
       INSERT INTO outbox (event_type, payload, created_at)
         VALUES ('ORDER_CREATED', '{...}', NOW())
     COMMIT

  2. Outbox relay (separate process):
     Poll: SELECT * FROM outbox WHERE published = FALSE LIMIT 100
     For each row:
       Publish to Kafka/SQS/...
       UPDATE outbox SET published = TRUE WHERE id = ?
```

### Debezium / CDC Approach

Instead of polling, use **Change Data Capture (CDC)** — Debezium reads the database's transaction log (binlog, WAL, redo log) and publishes changes as events. The outbox table changes are captured automatically.

```
  DB WAL ──> Debezium ──> Kafka topic ──> Consumer services
  (outbox changes are just regular table changes captured by CDC)
```

## Inbox Pattern

The **inbox pattern** is the consumer-side counterpart to the outbox. A consumer:
1. Receives a message from the broker
2. Writes it to a local **inbox table** (within a DB transaction)
3. Acknowledges the message to the broker
4. Processes the inbox entry in a local transaction with the business data

This provides **idempotent consumption** — if processing fails, the inbox entry remains and can be retried. If the consumer crashes mid-processing, the inbox entry is reprocessed on restart.

## Idempotency & Exactly-Once Semantics

### The Exactly-Once Problem

In a distributed system, messages may be delivered: zero times (lost), once (ideal), or multiple times (duplicated). True "exactly-once" delivery is impossible to guarantee (a message might be lost right before the consumer processes it). Instead, systems provide **effectively-once** semantics.

### Idempotency Keys

Every operation carries an **idempotency key** — a unique identifier. The receiver checks if it has already processed a request with that key and skips duplicates.

```python
class IdempotentHandler:
    def handle(self, idempotency_key, operation):
        # Check if already processed
        if db.exists('processed', idempotency_key):
            return db.get('results', idempotency_key)
        
        # Process (within a transaction that also records the key)
        result = do_operation(operation)
        db.put('processed', idempotency_key, True)
        db.put('results', idempotency_key, result)
        return result
```

### Exactly-Once in Kafka

Kafka's "exactly-once semantics" (EOS) combines:
1. **Idempotent producer**: producer assigns a sequence number per partition; broker deduplicates
2. **Transactional reads**: consumer reads only from committed transactions
3. **Atomic write-to-multiple-partitions**: producer's writes to multiple partitions are committed atomically

This achieves **effectively-once** end-to-end: each message is processed exactly once by the consumer, assuming the consumer uses the transactional API and commits offsets within the same transaction as its processing.

### Deduplication Strategies

| Strategy | Where | Overhead | Consistency |
|----------|-------|----------|-------------|
| Idempotency key table | Consumer DB | One DB lookup per op | Strong |
| Set-based (Bloom filter) | Consumer memory | O(1) with small false positive rate | Probabilistic |
| Time-window dedup | Consumer | O(1) | Weak (misses late duplicates) |
| Natural key constraint | Consumer DB | DB constraint check | Strong |

## Distributed Tracing

### OpenTelemetry Model

Distributed tracing tracks a request as it flows through multiple services:

```
[Trace ID: abc123]
  Span 1: API Gateway (12ms)
    Span 2: Auth Service (3ms)
    Span 3: Order Service (45ms)
      Span 4: DB Query (20ms)
      Span 5: Payment Service (18ms)
```

A **trace** is the full request journey. A **span** is a single operation. Spans are nested to show parent-child relationships. Context propagation (trace ID, span ID, flags) is carried in request headers.

### Sampling Strategies

- **Head-based sampling**: decide at the trace root whether to sample (e.g., 1% of requests)
- **Tail-based sampling**: collect all spans, decide after completion based on latency/errors (requires buffering)
- **Priority/rules-based**: always sample errors, slow requests, and a random subset of normal requests

### Trace Propagation Formats

- **W3C Trace Context**: `traceparent` and `tracestate` headers
- **B3** (Zipkin): `X-B3-TraceId`, `X-B3-SpanId`, `X-B3-ParentSpanId`

## Distributed Garbage Collection

In systems like distributed object stores or actor frameworks, objects may be shared across nodes. Determining when an object is no longer referenced by any node requires distributed GC.

### Reference Counting

Maintain a distributed reference count. Each node tracks references to remote objects and periodically syncs reference counts. Challenges: cycles, message loss, and race conditions between increment and decrement.

### Trace-Based (Distributed Mark-Sweep)

A tracing GC pauses all mutators, marks all reachable objects from roots, and sweeps unreachable objects. In a distributed setting, this requires global coordination (a Chandy-Lamport snapshot to find the consistent state).

> **Interview Angle**: "How does the outbox pattern compare to using Kafka transactions?" The outbox pattern works with any database and any message broker — it's database-centric (write to outbox table, relay publishes). Kafka transactions are Kafka-centric (producer writes to Kafka topics atomically). Outbox is more flexible but adds relay infrastructure; Kafka transactions are simpler if you're already committed to Kafka. Both solve the dual-write problem. The inbox pattern complements both by providing idempotent consumption on the consumer side. Cross-reference: [consensus](../consensus/raft.md) for the coordination underlying distributed transactions.