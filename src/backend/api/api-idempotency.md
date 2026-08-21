# API Idempotency Deep Dive — Idempotency Keys, Dedup Tables, and the At-Least-Once Problem

## Overview

Networks are unreliable. Clients time out, retry, and timeout-retry again.
If a server executes the requested work for each retry, the user gets
double-charged, double-emailed, or has two duplicate orders. The defense
is **idempotency**: a guarantee that *executing the same logical operation
multiple times has the same effect as executing it once*. In an interview
this is the answer to "how do you make a payment API safe" and "how do you
handle retries in distributed systems." This page covers the
idempotency-key pattern (Stripe-style), the dedup table, the idempotency
window, replay-safe design, the difference between `POST` and `PUT`
semantics, and how at-least-once delivery and exactly-once processing
relate to each other.

> Related: [Idempotency (patterns)](../patterns/idempotency.md) (short
> form), [REST](./rest.md) (HTTP method semantics), [Retries and
> Backoff](../patterns/retry-timeout.md), [Event-Driven](../patterns/event-driven.md)
> (at-least-once consumers), [Exactly-Once](../patterns/exactly-once.md),
> [Payment System Design](../../interview/system-design/payment.md),
> [Kafka](../messaging/kafka.md).

## Why Idempotency Matters

A client sends `POST /payments` for $100. The server charges $100. The
network packet carrying the response is lost in flight. The client's
timeout fires, the client retries. The server charges $100 again. The user
is $200 poorer for a single logical intent.

```
   Client                          Server
     │                                │
     │── POST /payments ────────────→│  ← charge $100 (1)
     │                                │
     │   ⏱ timeout, response lost    │
     │                                │
     │── POST /payments (retry) ────→│  ← charge $100 (2)
     │                                │
     │   ⏱ timeout, response lost    │
     │                                │
     │── POST /payments (retry) ────→│  ← charge $100 (3)
     │                                │
     │   ✅ 200 OK                   │
     │←──────────────────────────────│
     │                                │
   total: $300 charged, $100 intended
```

Without idempotency, every retry is a potential double-charge. With
idempotency, retries (2) and (3) are recognized as duplicates of (1) and
return the original response without re-executing.

## HTTP Method Semantics — POST vs PUT vs PATCH vs DELETE

[RFC 7231](https://www.rfc-editor.org/rfc/rfc7231) §4.2.2 defines:

| Method | Safe? | Idempotent? | Why |
|---|---|---|---|
| GET, HEAD, OPTIONS | Yes | Yes | Pure reads |
| PUT | No | **Yes** | Replaces the resource at the URL with the supplied representation; applying twice leaves the same state |
| DELETE | No | **Yes** | Deletes by URL; deleting twice leaves the same state (deleted) |
| POST | No | **No** | Creates a new resource (server assigns URL); each call appends |
| PATCH | No | No (default) | Depends on patch semantics; can be idempotent (e.g., set-to-X patch) or not (e.g., append-X patch) |

The intuition: **idempotent methods are state-equalizers**. `PUT /users/42 {name: "x"}`
twice leaves the resource in the same state it would be in after one
application. `POST /users {name: "x"}` twice creates two users.

The interview trap: **POST is *not* idempotent by spec**. If you want POST
to be replay-safe (which you almost always do for non-trivial POSTs like
payment, registration, order placement), you must add an idempotency
mechanism on top — the idempotency key.

PUT's idempotency holds only if the operation is a *full replacement*. A
PUT that increments a counter, appends to a list, or partially updates is
*not* idempotent — it just happens to be transported via PUT. The
semantics come from what the server does, not the verb.

## The Idempotency Key (Stripe-Style)

The pattern, as Stripe documents at
[*Making requests idempotent*](https://docs.stripe.com/api/idempotent_requests),
is for the client to attach a unique-per-logical-operation key to every
non-safe request:

```http
POST /v1/charges HTTP/1.1
Idempotency-Key: 8f6a3c2e-9b1d-4e7e-a5f4-2c1b8e9d7f3a
Content-Type: application/json
{
  "amount": 1000,
  "currency": "usd",
  "source": "tok_visa"
}
```

The server:

1. Looks up the key in its idempotency store (Redis, a DB table).
2. **Miss** → execute the operation, store `key → response`, return the
   response.
3. **Hit** → return the stored response *without re-executing*.

The key is **client-generated** (typically UUIDv4 or a content hash),
stable across retries of the same logical operation, and never reused for
a different operation.

```
   Client                                   Server
     │                                        │
     │── POST /charges ─────────────────────→ │
     │   Idempotency-Key: 8f6a3c2e-...        │
     │                                        │
     │                                  ┌─────┴──────┐
     │                                  │ lookup key │
     │                                  └─────┬──────┘
     │                                        │
     │                              miss ────┼──── hit
     │                                        │
     │                              ┌─────────┴─────────┐
     │                              │ execute operation │     ┌────────────┐
     │                              │ store key→resp    │     │ return     │
     │                              └─────────┬─────────┘     │ stored     │
     │                                        │               │ response   │
     │                                        │               └─────┬──────┘
     │                                        │                     │
     │←────────────────────────── 200 OK ─────┤─────────────────────┘
     │   response (cached)
     │
     │── POST /charges (retry, same key) ────→ │
     │   Idempotency-Key: 8f6a3c2e-...          │
     │                                           │
     │←────────────────────────── 200 OK ────── │  (no re-execute)
     │   same cached response
```

Key design details:

- **Key generation**: client-side UUIDv4 is the standard. The key must
  survive retries, so it must live outside the request body — the `Idempotency-Key`
  header is the convention.
- **Storage**: a durable store with a unique constraint on the key.
  Redis with TTL is fast; a Postgres table `idempotency_keys (key, response, expires_at)`
  with `UNIQUE(key)` is durable.
- **Concurrency**: two racing requests with the same key must not both
  execute. Use `INSERT ... ON CONFLICT DO NOTHING` to acquire a unique
  row lock, then execute under the lock, then `UPDATE` the row with the
  response. The losing request waits, then reads the stored response.
- **Payload mismatch**: a different payload with the same key should be
  rejected with `422 Unprocessable Entity` (or `409 Conflict`) — the
  client is misusing the key.
- **Error caching**: cache error responses too. A first attempt that
  returned `402 Payment Required` should not be retried into a successful
  charge on the second attempt.
- **Window**: keys expire after a TTL (Stripe uses 24 hours; AWS uses
  up to 24 hours; SQS uses 5 minutes for deduplication). After the TTL,
  the same key is a different operation.

## The Dedup Table

A durable implementation uses a SQL table:

```sql
CREATE TABLE idempotency_keys (
    key            TEXT PRIMARY KEY,        -- or (account_id, key)
    request_hash   TEXT NOT NULL,           -- hash of the body, for mismatch detection
    status         TEXT NOT NULL,           -- 'in_progress' | 'completed' | 'failed'
    response_code  INT,
    response_body  BYTEA,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at     TIMESTAMPTZ NOT NULL,
    owner          TEXT,                    -- which worker is executing
    CONSTRAINT key_request_uniq UNIQUE (key, request_hash)
);

CREATE INDEX ON idempotency_keys (expires_at);
```

The execution flow uses the table as both a lock and a result store:

```python
import hashlib, json, uuid

def idempotent_handler(request, business_logic):
    key = request.headers["Idempotency-Key"]
    request_hash = hashlib.sha256(request.body).hexdigest()

    # Try to claim the key atomically
    rows = db.execute("""
        INSERT INTO idempotency_keys (key, request_hash, status, expires_at, owner)
        VALUES (%s, %s, 'in_progress', now() + INTERVAL '24 hours', %s)
        ON CONFLICT (key) DO NOTHING
        RETURNING key
    """, (key, request_hash, worker_id))

    if rows:  # we claimed it — execute
        try:
            response = business_logic(request)
            db.execute("""
                UPDATE idempotency_keys
                SET status='completed', response_code=%s, response_body=%s
                WHERE key=%s
            """, (response.status_code, response.body, key))
            return response
        except Exception as e:
            db.execute("""
                UPDATE idempotency_keys
                SET status='failed', response_code=500
                WHERE key=%s
            """, (key,))
            raise

    # we didn't claim — someone else has it. Check payload + status.
    existing = db.execute("""
        SELECT request_hash, status, response_code, response_body
        FROM idempotency_keys WHERE key=%s
    """, (key,))

    if existing.request_hash != request_hash:
        return Response(422, "Idempotency key reused with different payload")

    if existing.status == "completed":
        return Response(existing.response_code, body=existing.response_body)

    if existing.status == "in_progress":
        # race — another worker is executing. Wait briefly, then read.
        sleep(backoff())
        return idempotent_handler(request, business_logic)

    if existing.status == "failed":
        # prior attempt failed; allow a clean retry by clearing the key
        db.execute("DELETE FROM idempotency_keys WHERE key=%s", (key,))
        return idempotent_handler(request, business_logic)
```

The `ON CONFLICT DO NOTHING` plus the `INSERT ... RETURNING` is a single
SQL statement that atomically acquires the lock — Postgres guarantees
only one inserter wins. This is the recommended pattern at the
[*AWS Builders' Library: Making retries safe with idempotent APIs*](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/).

## The Idempotency Window

Keys must expire. Without a TTL:

- The idempotency store grows unboundedly.
- Clients can never reuse a key — and clients *do* reuse keys in
  practice (test environments, generated UUID collisions, scripted flows).

A 24-hour window is the typical choice — long enough that no honest retry
will fall outside, short enough that the store stays bounded. AWS API
Gateway and many AWS service actions (e.g., `CreateChangeSet`,
`StartExecution`) use up to 24 hours. SQS uses a much shorter
**5-minute** deduplication window for FIFO queues
([*Amazon SQS FIFO deduplication*](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/using-messagededuplicationid-property.html))
because message-level dedup has different freshness needs.

After the window expires, the server must garbage-collect old entries.
The simplest cleanup pattern is a periodic `DELETE FROM idempotency_keys WHERE expires_at < now()`.

## Replay-Safe Design

An idempotency key protects against **client retries of the same logical
operation**. It does *not* protect against:

1. **Server-side replays of the underlying business operation.** If the
   server's charge endpoint calls a downstream payments gateway and the
   gateway times out, the server doesn't know if the charge was made. The
   server should retry the gateway call (which itself should be
   idempotent) and converge.
2. **At-least-once delivery of upstream events.** If a queue delivers the
   same "create order" message twice, two different idempotency keys may
   be generated — unless the consumer derives the key deterministically
   from the message ID (e.g., `Idempotency-Key: msg-${message_id}`).
3. **Concurrent operations with different keys but same effect.** Two
   different idempotency keys for "buy product X" produce two orders,
   unless the server enforces a uniqueness constraint on
   `(user_id, product_id, order_intent)` that's stronger than the key.

A replay-safe design pairs the idempotency key with **database uniqueness
constraints** that encode the actual business invariants:

```sql
-- payments: one charge per (order_id, attempt_within_window)
ALTER TABLE charges
    ADD CONSTRAINT charges_order_attempt_uniq
    UNIQUE (order_id);

-- or, if multiple attempts are allowed per order, derive the key
-- deterministically from the order:
def make_idempotency_key(order):
    return f"charge-{order.id}-{order.attempt_number}"
```

Combined with the transactional outbox pattern (write the charge + the
outbox event in one DB transaction), the system is replay-safe: every
replay of the same logical operation converges to the same final state.

## At-Least-Once Delivery vs Exactly-Once Processing

A common confusion: "we have exactly-once delivery" — you almost
certainly don't. The honest framing:

- **At-least-once delivery**: the message system may deliver the same
  message more than once. This is the default for Kafka, SQS, RabbitMQ
  (without FIFO), SNS. Networks don't guarantee exactly-once; they
  guarantee at-least-once with retries.
- **At-most-once delivery**: messages may be lost; never duplicated.
  Fire-and-forget UDP, or "acknowledge before processing" semantics
  (risky).
- **Exactly-once processing**: the *effect* of processing the message is
  applied exactly once, even if the message was delivered more than once.
  This is achieved via **idempotent consumers**, not via the transport.

The pattern: **at-least-once delivery + idempotent consumers ≈ exactly-once
processing**. Kafka's "exactly-once semantics" (EOS) feature
(`enable.idempotence=true`, transactional producers and consumers)
implements exactly this combination: the producer is idempotent (duplicate
acks from the broker don't duplicate the message in the log), and the
consumer-side transactional read-process-write is atomic.

AWS SQS FIFO implements the same combination:
[MessageDeduplicationId](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/using-messagededuplicationid-property.html)
is hashed and the SQS deduplication layer discards duplicates within a
5-minute window. The consumer still must be idempotent in case the
dedup misses.

The takeaway: never design a consumer that assumes exactly-once delivery.
Always assume the message will arrive more than once and design the
processing to converge.

## AWS API Gateway's Idempotency

AWS API Gateway's
[*idempotent APIs*](https://docs.aws.amazon.com/apigateway/latest/developerguide/idempotency-support.html)
feature lets you mark an API method as idempotent. The gateway stores
the response keyed by the `Idempotency-Key` header for the configured TTL
(1-3600 seconds), deduplicating retries at the edge before they reach
your origin. This is the cloud-platform implementation of the pattern,
and the AWS Builders' Library article is the canonical reference for
the deeper pattern.

## Implementation Patterns

### Redis-based Idempotency

```python
import redis, json, uuid, time

r = redis.Redis()

def idempotent_post(handler):
    def wrapper(request):
        key = request.headers.get("Idempotency-Key") or str(uuid.uuid4())
        lock_key = f"idem:lock:{key}"
        resp_key = f"idem:resp:{key}"

        # claim the lock with a short TTL
        if not r.set(lock_key, "1", nx=True, ex=30):
            # someone else is executing; wait, then read stored response
            for _ in range(30):
                cached = r.get(resp_key)
                if cached:
                    return json.loads(cached)
                time.sleep(0.1)
            return Response(409, "in-progress timeout")

        try:
            response = handler(request)
            r.setex(resp_key, 86400, json.dumps({
                "status": response.status_code,
                "body": response.body.decode("utf-8", "replace"),
            }))
            return response
        finally:
            r.delete(lock_key)  # release lock

    return wrapper
```

Redis is fast and easy, but note: data is volatile across Redis restarts.
For payment-grade idempotency, prefer the durable Postgres dedup table.
Hybrid (Redis for hot path, Postgres for durable records) is common.

### Convergence via Database Uniqueness

```python
# order creation: derive the idempotency key from the business identifier
# so that retries of the same intent always hit the same constraint
def create_order(user_id, cart_id):
    idem_key = f"order-{user_id}-{cart_id}"
    try:
        order = db.execute("""
            INSERT INTO orders (user_id, cart_id, status)
            VALUES (%s, %s, 'pending')
            ON CONFLICT (cart_id) DO NOTHING
            RETURNING id
        """, (user_id, cart_id))
        return order
    except ConflictOnUnique:
        return db.execute("SELECT id FROM orders WHERE cart_id=%s", (cart_id,))
```

The `ON CONFLICT (cart_id) DO NOTHING` makes the second insert a no-op,
and the follow-up `SELECT` returns the already-created order's id. No
duplicates, no client-side idempotency key needed.

## Common Pitfalls

1. **Relying on POST being idempotent** — the canonical interview trap;
   POST is not idempotent by spec.
2. **Idempotency keys in memory only** — lost on restart; the client
   retries and gets a double-execute.
3. **No concurrency protection on the key lookup** — two parallel retries
   both see "miss" and both execute. Use `INSERT ... ON CONFLICT DO
   NOTHING` or `SETNX` to claim atomically.
4. **Reusing keys across different operations** — should return `422`,
   not silently replay a different side effect.
5. **Not caching error responses** — a first attempt that returned `402`
   gets retried (within the window) into a successful second charge.
6. **Reusing the idempotency key as a database primary key** — the key
   is per-operation, not per-resource; mapping it directly to a row PK
   conflates two different concepts.
7. **Short TTLs that miss slow retries** — if the client's retry policy
   is "retry for 1 hour" and your TTL is 5 minutes, the 6th retry executes
   the operation again.
8. **Storing the response body as a string with size limits** — Stripe
   stores up to 1 MiB; if your response is bigger, store a pointer to S3
   instead.

## Interview Questions

### Q: How would you make a payment API safe against double charges?

Issue an `Idempotency-Key` per checkout; the payment endpoint looks it up
in a store with a unique constraint. First hit executes and stores the
key→result; retries (same key) return the stored result. Additionally
enforce a unique `order_id` in the DB so even a concurrent duplicate
insert cannot double-charge, and use the transactional outbox pattern to
make the charge + order state change atomic. The idempotency key is the
defense against client retries; the unique constraint is the defense
against server-side concurrency.

### Q: What's the difference between idempotency and exactly-once?

Idempotency means "same input → same effect, no matter how many times
applied" — it's a property of the operation. Exactly-once is a
*processing guarantee* — that an operation's effect is applied exactly
once. Systems achieve exactly-once processing by combining
at-least-once delivery (networks are unreliable) with idempotent
consumers (dedup keys, unique constraints). True exactly-once *delivery*
is essentially impossible in the presence of network partitions;
exactly-once *processing* is achievable.

### Q: GET is idempotent — is it also safe?

Yes: a GET is *safe* (no side effects) and therefore idempotent. Safe
methods should not cause observable state changes; clients may freely
retry them. (Logging, cache warmup, and observability side effects are
acceptable because they're not observable to the client.)

### Q: How does Stripe's idempotency work at scale?

Per the Stripe docs: the key is hashed and stored in a sharded data
store keyed by `(customer, key)`; first write wins via a unique index;
TTL expires keys; the stored response — including error responses — is
replayed for retries within the 24-hour window. The dedup layer is
separate from the business-logic storage so the store can be tuned
independently (high write throughput, fast lookups).

### Q: What's wrong with using `PUT` for "create if not exists"?

`PUT /users/42` is idempotent and is the right verb for create-or-replace.
But `PUT /users` (no id in URL, asking the server to assign) violates
PUT semantics (the URL must identify the resource being PUT). For
client-supplied IDs, PUT is correct; for server-assigned IDs, use POST
plus an idempotency key.

### Q: At-least-once delivery — how do you make a consumer safe?

Assume every message will arrive more than once. Make the consumer
idempotent: derive the idempotency key from the message ID
(`Idempotency-Key: msg-${message_id}`), store processed message IDs in
a dedup table, skip duplicates on read. Or use state-based convergence:
the consumer computes from current state so re-applying converges (like
PUT). Or use the transactional outbox: write the effect and the dedup
marker in one DB transaction.

## Cross-References

- [Idempotency (patterns)](../patterns/idempotency.md) — short form of this page
- [REST](./rest.md) — HTTP method semantics (PUT idempotent, POST not)
- [Retries and Backoff](../patterns/retry-timeout.md) — why clients retry
- [Event-Driven](../patterns/event-driven.md) — at-least-once consumers
- [Exactly-Once](../patterns/exactly-once.md) — Kafka EOS, transactional consumers
- [Event Sourcing](../patterns/event-sourcing.md) — replaying the event log idempotently
- [Payment System Design](../../interview/system-design/payment.md) — real-world application
- [Kafka](../messaging/kafka.md) — producer idempotence (`enable.idempotence=true`)
- [Distributed Transactions](../patterns/distributed-transactions.md) — atomicity across services

## References

- Stripe — *Making requests idempotent* — <https://docs.stripe.com/api/idempotent_requests>
- AWS Builders' Library — *Making retries safe with idempotent APIs* — <https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/>
- AWS API Gateway — *Use idempotent APIs in API Gateway* — <https://docs.aws.amazon.com/apigateway/latest/developerguide/idempotency-support.html>
- AWS SQS — *MessageDeduplicationId property* (FIFO dedup, 5-minute window) — <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/using-messagededuplicationid-property.html>
- RFC 7231 — *Hypertext Transfer Protocol (HTTP/1.1): Semantics and Content*, §4.2.1 (Safe Methods), §4.2.2 (Idempotent Methods) — <https://www.rfc-editor.org/rfc/rfc7231>
- Apache Kafka — *Exactly-Once Semantics* (producer idempotence, EOS) — <https://kafka.apache.org/documentation/#semantics>
- brandur.org — *Idempotency keys for the modern developer* (Brandur Leach, Stripe alumnus) — <https://brandur.org/idempotency-keys>
