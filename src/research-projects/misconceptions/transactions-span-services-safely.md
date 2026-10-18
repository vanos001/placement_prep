# "The transaction spans the services, so it all commits or rolls back together"

## Overview

This page audits the sentence that turns up in design reviews the moment
someone draws a sequence diagram that touches two systems: wrap the database
write and the downstream call in one transaction, and the whole operation
commits or rolls back as a unit. The claim feels supported by the tooling —
the `@Transactional` annotation sits right there on the method, the code that
writes the row and the code that calls the payment service live inside the
same brace-delimited block, and the word "transaction" carries fifty years of
atomicity connotation. What the sentence deletes is the definition of the
boundary: a database transaction is a contract between a client and one
resource manager, enforced by that resource manager's write-ahead log, and it
ends at that resource's commit point. An HTTP call to another service and a
publish to a message broker are side effects issued to other systems with
their own logs, their own commit protocols, and no participation in the
rollback. This page states the claim fairly, gives the one configuration
where a version of it is true, and works the dual-write counterexample end to
end.

## The Claim, Stated Fairly

The strongest common form is: "The order row and the `OrderCreated` event are
written inside one `@Transactional` method, so they are atomic — if the
publish fails, the row rolls back, and if the commit fails, the publish never
happened. The transaction spans the whole flow, including the call to the
payments service." Stated this way, the claim is not a strawman. It appears
in real pull requests where the annotation visibly encloses every step, in
architecture documents that draw one dashed box around five systems labeled
"ACID", and in the honest reasoning of engineers whose framework advertises
"declarative distributed transactions".

The kernel is real. Database transactions genuinely deliver atomicity —
within their boundary. Java's JTA and the XA protocol genuinely can enroll
two resource managers, such as a relational database and a JMS broker, into
one coordinated two-phase commit. PostgreSQL even ships the `PREPARE
TRANSACTION` statement that implements the second phase. The question is
whether "a transaction exists on my method" honestly compresses to "the
operation is atomic across the services it touches".

## Verdict

**False.** The claim is contradicted outright in the default configuration
of every mainstream stack: the transaction covers statements executed on the
connections enlisted in it, and nothing else. The HTTP call and the broker
publish are not statements on any enlisted connection; they are network
operations that commit the instant the remote system processes them and that
no rollback protocol can retract. There is a real protocol (XA) that spans
two *enlisted resource managers*, but services in the microservice sense —
HTTP peers, Kafka, SaaS APIs — do not enlist, and even where XA applies, its
failure modes (in-doubt transactions, coordinator blocking, heuristic
outcomes) defeat the "safely" in this page's filename. Cross-service
atomicity is a design problem solved with outbox patterns, sagas, and
idempotent consumers, not with a wider transaction.

## Why People Believe It

Four forces keep the claim alive. First, the annotation is *adjacent*: the
code that fails and the code that "should have rolled back" sit in the same
method, and syntactic proximity is the most persuasive argument in
programming. Nobody checks whether the broker connection was enlisted;
visually, everything is inside the transaction.

Second, the word "transaction" is imported from its native habitat without
its definition. In database theory, a transaction is bounded by the resource
manager that logs it; in design documents, it floats free as a synonym for
"reliable thing". Once the word floats, the guarantee floats with it.

Third, the failure that would refute the claim is rare in development and
silent in production. The dual-write inconsistency requires a commit to fail
*after* the remote call succeeded — a deadlock victim, a connection reset
during commit, a unique-constraint violation on a concurrent insert. Test
suites almost never inject these; production hits them weekly at any real
scale, and the resulting anomaly (an event without a row, a row without an
event) shows up days later as a data inconsistency nobody can trace to the
deploy.

Fourth, the honest alternatives are work. The outbox pattern adds a table, a
relay, and idempotent consumers; a saga replaces atomicity with a sequence of
compensations that must be designed per operation. Against that cost, the
sentence "the transaction already covers it" is cheap, plausible, and
reviewable — which is exactly why it survives review.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "One transaction covers the flow" | A transaction is a contract with one resource manager; it ends at that manager's commit point and covers nothing the manager does not log |
| "The HTTP call rolls back" | A completed HTTP call cannot be un-issued; the only rollback is a compensating call, which is a different mechanism with different failure modes |
| "The publish rolls back with the commit" | The broker persists and acknowledges the message on receipt; it never learns whether the database committed |
| "XA/JTA makes it true" | XA coordinates resource managers that enlist with a transaction manager (DB + JMS); Kafka, HTTP services, and most SaaS APIs have no XA resource, and XA adds blocking and in-doubt states of its own |
| "If the commit fails, the side effect never happened" | Ordering is unspecified: the side effect may precede the failed commit, and the failure may occur after the side effect was acknowledged |
| "Holding the transaction open is harmless" | The transaction holds locks and a connection while the remote call runs; a 30-second timeout converts remote slowness into local lock queues |

The correct sentence: "The transaction boundary ends at the resource manager
that logs it. Everything the method touches beyond that — service calls,
broker publishes, emails — commits on its own schedule, and stitching those
effects into one all-or-nothing outcome is a workflow-design problem, solved
with a transactional outbox or a saga, not with a wider annotation."

## Where It Breaks

**The dual-write counterexample, worked end to end.** The method opens a
transaction, inserts the order row (uncommitted, invisible to other
sessions), then publishes `OrderCreated` to Kafka. The broker appends the
record to its log and acknowledges — that append is the broker's commit, and
it is permanent. Two milliseconds later the database `COMMIT` fails: the
session was chosen as a deadlock victim, or the connection dropped during
the final handshake, or a deferred constraint was violated. The outcome is
exactly the one the claim excluded: the event exists for an order that does
not. Consumers have already shipped confirmation emails. The reverse
interleaving is just as real — the commit succeeds, then the publish throws,
and the row exists with no event, so downstream projections never learn the
order happened. Of the four outcomes of {commit, fail} x {publish, fail},
two are inconsistent states, and no amount of test coverage on the happy
path exposes them.

**XA is real, and it is still not what the claim means.** The honest defender
says: "JTA does this — database and JMS broker in one two-phase commit."
True, for resources that implement XA and enlist with a transaction manager.
Count what that buys and costs. The prepare phase holds row locks across an
extra network round trip; if the coordinator dies between prepare and
commit, every enlisted database holds its locks with the transaction
in-doubt until an operator resolves it, which is why PostgreSQL ships with
prepared transactions disabled by default (`max_prepared_transactions = 0`)
— a deliberate statement that the feature is a loaded tool, not a default.
And the protocol's reach stops at the enlistment boundary: Kafka has no XA
resource, no HTTP service is an XA resource, and the payments call in the
claim's own example is outside the protocol no matter how the annotation is
configured. "Transactions span services safely" survives, at most, as
"two-phase commit spans two cooperating brokers, with new failure modes of
its own".

**Holding the transaction across a remote call is its own failure.** Even
before any commit fails, the configuration the claim produces is pathological:
the database transaction stays open for the duration of the HTTP call, holding
row locks and a pooled connection. At 100 orders per second and a payments
endpoint degraded to 30-second timeouts, 3,000 transactions queue behind held
locks within half a minute; connection pools exhaust; the failure of one
remote dependency becomes a full outage of the order service. The lock
behavior is documented, predictable, and the reason "no remote calls inside a
transaction" is a standing rule in every store that has run this to ground.

**The outbox is the fix that manufactures what the annotation promised.**
Write the order row and the `OrderCreated` record in one local transaction —
two inserts, one resource manager, genuinely atomic. A relay (a poller or a
change-data-capture stream over the outbox table) publishes the event
afterward. The publish is now at-least-once, so consumers deduplicate by
event ID, and visibility of the event is eventual rather than simultaneous —
those are the honest prices. What is gained is the property the original
claim asserted falsely: no event without a committed row, and no committed
row without an eventual event, regardless of failure order.

**Sagas change the semantics, honestly.** Where the flow spans services —
reserve inventory, charge the card, ship — the correct structure is a saga:
a sequence of local transactions, each atomic within its own resource, plus
a compensating transaction for each step that must be undone. The
compensation is real work with its own failure modes; a charge that must be
refunded after a shipping failure is not "rolled back", it is refunded
through a second payment-network round trip that can itself fail and be
retried. The claim's appeal is precisely that it hides this entire
discipline behind one keyword.

## Practical Implications

- Treat `@Transactional` (and its equivalents) as a scope marker for
  statements on enlisted connections — and treat every remote call inside
  that scope as a defect: it neither rolls back nor keeps the transaction's
  locks local.
- Refuse dual writes: any feature that writes a row and publishes a fact
  gets an outbox, a CDC relay, and idempotent consumers, or an explicitly
  acknowledged inconsistency and a reconciliation job.
- Audit XA deployments as legacy risk: enumerate in-doubt transaction
  procedures, verify coordinator failover, and check whether every enlisted
  resource actually supports it — the protocol's availability is not the
  annotation's availability.
- In interviews and design reviews, answer "can we just put it in one
  transaction?" by naming the resource manager that logs the commit — that
  one question dissolves most versions of this claim on the whiteboard.

## Interview Questions

### A service inserts a row in PostgreSQL and publishes to Kafka inside one `@Transactional` method. The commit fails after the publish was acknowledged. What is the state of the world?

The event exists in the Kafka log; the row does not exist in the database.
The broker committed on acknowledgment — its log append is its commit — and
the database's failed commit left no row. The transaction never spanned the
broker, so no rollback reached it. A strong answer then proposes the outbox:
both writes in the local transaction, a relay publishing afterward, and
idempotent consumers to absorb redelivery.

### Why is two-phase commit not the general answer to atomicity across services?

Because it only coordinates resource managers that enlist in the protocol:
a Kafka broker, an HTTP API, or a SaaS endpoint is not an XA resource. Even
for cooperating resources, 2PC holds locks across a prepare round trip and
blocks them if the coordinator dies between phases, leaving in-doubt
transactions that need operator resolution. It trades availability for
atomicity at exactly the moment (a crash) when availability matters.

### What does the outbox pattern guarantee that the annotation does not, and what does it give up?

It guarantees the pairing: an event is published if and only if the row
committed, because both are one local transaction, and the relay publishes
from the durable outbox. It gives up simultaneity — consumers see the event
after a relay delay — and delivers at-least-once, so consumers must
deduplicate by event identifier. Those are bounded, designable costs;
the dual-write alternative has unbounded inconsistency.

### You must keep a database write and a payments call from producing "charged but no order". The payments API cannot roll back. What do you design?

A saga with compensations, not a transaction. Persist the order intent and
the charge authorization in local transactions, invoke the capture, and on
failure run the designed compensation (a refund or void) with retries and
an operations queue for compensation failures. The pivot matters: before
the irreversible step, retriable failures dominate; after it, the design
shifts to compensating. The answer that says "one transaction" has already
failed the question.

## Key Takeaways

- A transaction's boundary is the resource manager that logs it; annotations
  mark a scope, they do not extend a protocol.
- HTTP calls and broker publishes commit when the remote system commits; no
  local rollback reaches them, in either failure order.
- XA/2PC is real for enlisted resources and still fails the claim: no XA in
  Kafka or HTTP services, plus in-doubt transactions and coordinator
  blocking of its own.
- Holding a transaction across a remote call converts remote latency into
  local lock queues — 100 TPS behind a 30-second dependency is 3,000 queued
  transactions.
- Atomicity across services is manufactured, not declared: outbox for
  write-plus-event pairing, sagas with compensations for multi-service
  flows, idempotency everywhere downstream.

## Cross-References

- [Follow-up Tree: ACID Transactions](../followup-tree/acid-transactions.md)
  — the interview escalation from "define ACID" to exactly the boundary
  question this page audits.
- [Connection Atlas: Transactions & Concurrency Control](../connection-atlas/transactions-concurrency-control.md)
  — how isolation and locking behave inside the boundary the claim assumed
  was wider.
- [Assumptions Hunt: Database Isolation](../assumptions-hunt/database-isolation.md)
  — the hidden assumptions inside "the database keeps me safe", the local
  cousin of this claim.
- [Misconception: "We can always roll back the deploy"](./rollback-means-undo.md)
  — the deployment-shaped twin: both claims borrow the word "rollback" for
  effects that no rollback protocol reaches.
- [Backend Patterns: Transactional Outbox & CDC](../../backend/patterns/cdc-outbox.md)
  — the engineered substitute for the atomicity the annotation promised.
- [DBMS: Two-Phase Commit](../../dbms/transactions/two-phase-commit.md) —
  the real spanning protocol, with the prepare, lock, and in-doubt
  mechanics the claim skips.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- C. Richardson. *Saga pattern* — microservices.io, the canonical
  formulation of local transactions plus compensations across services.
  <https://microservices.io/patterns/data/saga.html>
- PostgreSQL Global Development Group. *PostgreSQL Documentation:
  Transactions* — the client-resource contract and commit semantics that
  define where the boundary actually sits.
  <https://www.postgresql.org/docs/current/tutorial-transactions.html>
- G. Hohpe. *Your Coffee Shop Doesn't Use Two-Phase Commit*, 2005 — cited by
  title; the standing analogy for why asynchronous compensation, not
  blocking commit protocols, is how independent businesses coordinate.
