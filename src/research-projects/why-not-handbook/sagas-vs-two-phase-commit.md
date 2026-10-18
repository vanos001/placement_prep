# Sagas vs Two-Phase Commit: Where Does Uncertainty Live While a Transaction Crosses Services?

## Overview

Inside one database, atomicity is a solved problem: the WAL, the lock table, and the commit record conspire so that a transaction either happened or did not, and no one can observe the middle. The moment a "transaction" spans two services with separate databases, that machinery stops existing — and the design question becomes: **who holds the pieces of an unfinished cross-service transaction, for how long, and what does the rest of the system see while it is unfinished?** Two-phase commit answers with a protocol: a coordinator freezes the outcome space, participants promise, then everyone commits together — and between promise and outcome, locks are held and the system is blocked. Sagas answer with application structure: a chain of local transactions, each with a compensating inverse, intermediate states visible to everyone, and no protocol-level blocking at all.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **two-phase commit places uncertainty in the protocol — an in-doubt window where locks wait on a coordinator's recovery — while sagas place uncertainty in the application, where every reader between saga step two and step five must decide what a half-completed workflow means.** Neither removes the cost of distributed atomicity; they relocate it, and the choice is which bill the system pays — the honest answer is frequently "two-phase commit inside one service's walls, sagas across them."

## Step 1: The Problem and Its Constraints

The abstract shape: a business action (book flight + book hotel + charge card) must be all-or-nothing across autonomous participants. Constraints that decide the coordination mechanism:

- **Can every step be compensated?** Refunding a charge, releasing a reservation, canceling a booking — natural inverses. Sending an irreversible email or calling a non-refundable external API — not compensable. A saga with a non-compensable step is not a saga; that step's placement (early, behind reservations, or last) is the design constraint.
- **Isolation requirement.** Can other transactions and readers observe the intermediate states (order "pending payment", seat "reserved") without harm, or does correctness require that no one ever sees a partial transaction? Strict isolation is two-phase commit territory.
- **Blocking tolerance.** What happens if coordination itself fails? A system that may not stall (payments during a traffic spike) points toward non-blocking designs; a system that may not diverge (a ledger versus its derived index) can accept a blocking window.
- **Latency and throughput.** Two extra synchronous round trips plus the lock-hold window, versus N local transactions pipelined with asynchronous compensation.
- **Trust boundary topology.** Same organization, same network, shared DBA? Or separate teams, deployments, and databases that would never grant an external coordinator lock authority over their resources?
- **Recovery tooling.** Two-phase commit's failure mode is operational (resolving in-doubt transactions); sagas' is application-level (compensation that itself fails). Which on-call owns the 3 a.m. case?

## Step 2: The Mechanisms

### Two-phase commit: promise, then commit

The [two-phase commit protocol](../../dbms/transactions/two-phase-commit.md) gives a coordinator a two-round exchange with every participant. **Prepare:** each participant writes its intention to its own durable log, acquires the locks its part of the transaction needs, and answers "yes" — a promise that it can commit *even if it crashes now*, because the decision can be recovered from its log. **Commit:** when all yes-votes arrive, the coordinator records the global decision and the second round applies it everywhere. The mechanisms that matter:

- **The prepare promise is bought with locks.** From prepare until the global decision arrives, the participant holds its locks and cannot unilaterally proceed. This makes the protocol atomic — and blocking: if the coordinator dies between the rounds, every participant is **in doubt**, holding locks, unable to commit or abort, waiting for coordinator recovery (or a human heuristic that risks divergence).
- **The cost profile is two log forces and a lock window.** Every transaction pays the extra round trips plus lock hold across the coordination — tolerable on a fast LAN inside one system, punishing across a WAN or a slow participant.
- **Three-phase commit tries to remove the block.** The [3PC](../../dbms/transactions/three-phase-commit.md) variant adds a pre-commit round so an uncertain participant has an escape — at the price of network partitions enabling two coordinators, which is why real systems stay with 2PC and solve coordinator death with replicated coordinators.
- **Databases expose it as prepared transactions.** Postgres's [PREPARE TRANSACTION](https://www.postgresql.org/docs/current/sql-prepare-transaction.html) is the mechanism made visible — and its operators' warnings (in-doubt transactions are inspected manually; the feature is disabled by default) reflect exactly the operational weight the protocol carries.

### Sagas: local transactions plus compensations

A [saga](https://microservices.io/patterns/data/saga.html) breaks the distributed transaction into a sequence of local transactions, each committing independently, with a **compensating transaction** defined for each step that must be able to semantically undo it (the [original formulation](https://www.cs.cornell.edu/andru/cs711/2002fa/reading/sagas.pdf) formalized this for long-lived transactions). The mechanisms that matter:

- **No locks cross service boundaries.** Each local transaction locks only its own database, briefly. Concurrency is restored; atomicity is rebuilt from compensation — roll forward through the chain, running compensations in reverse for completed steps. Compensation must be idempotent (it may be retried) and safe against concurrent operations (a refund racing a dispute).
- **Isolation is gone, and something must replace it.** Between "seat reserved" and "payment captured," any reader can see and act on the intermediate state. Countermeasures are application-level: **semantic locks** (a status column making "reserved" visibly non-final), commutative update designs, reread-verify patterns — each a place where the application pays, in code, what 2PC paid in locks.
- **Coordination has two shapes.** Orchestration centralizes the state machine in one persistent coordinator process (explicit steps, easy observability and debugging); choreography publishes step-completion events and lets each service react (no central component, but the workflow's shape exists only implicitly across codebases). Either way, the orchestrator/choreography state must be updated *atomically with each step's effects* — the same [outbox discipline](./app-events-vs-cdc.md) that guards event publication.
- **Failure handling is a designed state, not an error path.** A compensation that fails (the refund API is down) is retried until it succeeds; the saga state machine carries "compensating" and "compensation failed" as first-class states an operator can act on.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Two-phase commit | Sagas |
|----------|------------------|-------|
| Atomicity | Strict — all commit or all abort | Eventual — steps commit locally; compensation repairs |
| Isolation during the transaction | Strict — locks hide intermediates | None by default — intermediates are visible |
| Blocking | Yes: in-doubt window waits on coordinator recovery | No protocol-level blocking anywhere |
| Latency per transaction | Two extra synchronous rounds + lock window | N local transactions, compensation only on failure |
| Throughput ceiling | Locks held across coordination bound it | Bounded by individual services, not coordination |
| Compensation logic required | None | Every step needs a correct inverse |
| Coordinator failure | In-doubt participants stall until recovery | Orchestrator state is rebuildable; steps never stall |
| Readers' contract | Never see partial state | Must understand pending/compensating states |
| Ops surface | In-doubt transaction tooling, coordinator HA | Saga state dashboards, compensation retry alarms |
| Characteristic failure | Coordinator crash freezing locks fleet-wide | Compensation racing concurrent business activity |
| Trust model | Coordinator is granted lock authority by all | Each service keeps authority over its own data |

The **uncertainty window** deserves the arrow drawn. Two-phase commit's in-doubt state is a protocol-level admission: between the votes and the decision, the truth exists nowhere in its entirety, and locks enforce that no one acts on partial truth — a dead coordinator converts that uncertainty into a fleet-wide stall. Sagas never concentrate uncertainty; they *broadcast* it — every intermediate state is uncertain by definition, and every reader must be programmed to handle what "pending" means. The 2PC bill is paid by the on-call operator during coordinator failures; the saga bill is paid by every developer who touches the workflow, in compensation and state-handling code.

## Step 4: When Each Wins

| Condition | Choice | Why |
|-----------|--------|-----|
| Participants share infrastructure and trust one coordinator | Two-phase commit | Strict atomicity and isolation without application compensation code |
| Short transactions, fast network, availability solvable for the coordinator | Two-phase commit | Blocking window is brief and rare; reasoning stays simple |
| Every step has a natural, implementable inverse | Sagas | Compensation is the mechanism; it is only honest when inverses exist |
| Cross-team/cross-org boundaries; no shared coordinator authority | Sagas | Each service keeps lock and schema authority over its own data |
| Long-running workflows (hours, days, human steps) | Sagas | Locks across human timescales are untenable; compensation is designed for it |
| Availability trumps momentary atomicity (checkout during spikes) | Sagas | No in-doubt stall; local commits keep flowing |
| The partial state would be a correctness event (ledger vs its index) | Two-phase commit | No reader may ever observe the middle |

**Two-phase commit wins** inside trust boundaries: a service coordinating its own database and cache invalidation, an XA transaction across two schemas of one cluster, anything where strict isolation matters more than availability and participants are few, fast, cooperative. **Sagas win** across boundaries: order workflows spanning inventory, payment, and fulfillment; workflows with human steps; topologies where a central coordinator would be a political single point of authority. **The honest hybrid** is the industry's settled answer: 2PC-equivalent atomicity inside each service's walls (one local transaction touching its own data plus its [outbox](./app-events-vs-cdc.md)), and a saga across services — strict atomicity at the scale where it is cheap, compensated workflows at the scale where it is not.

## Step 5: Edge Cases and Counterexamples

- **The coordinator crash that froze the ledger.** A 2PC coordinator dies after collecting prepare votes from a payment database and a ledger database; both now hold row locks in-doubt. Every transaction touching those rows stalls; dashboards show lock waits with no blocker. Recovery means waiting for coordinator restoration, or heuristic commit/abort per participant — and a wrong heuristic produces exactly the divergence the protocol exists to prevent. Atomicity preserved at the price of a system that can freeze.
- **The compensation that raced a shipment.** The saga reaches "payment failed" and starts compensating: release the reserved inventory — but the fulfillment worker already read "reserved" and shipped. Compensation and concurrent business activity are racing — "release stock" collides with "already shipped." Defenses: semantic locks (the "reserved" status fulfillment must refuse to act on), idempotent compensations, and explicit "compensating — do not act" states in consumer logic. The saga's bill, itemized.
- **The step that cannot be compensated, placed where it hurts.** A saga sends the confirmation email at step two and charges the card at step five; the charge fails; compensation runs — but the email is already out. Irreversible effects belong after every fallible, compensable step — "reserve everything, then execute the irreversible piece" — and the review question is always "where is the point of no return, and is everything before it reversible?"
- **The choreography that ping-ponged.** Two services each listening to the other's compensation events re-trigger each other in a loop — order service compensates, inventory service compensates its compensation, and the event log becomes an unrepeatable cycle. Choreography has no single place where the whole flow is written, so cycles and missing handlers are discovered in production; the orchestrator's explicit state machine is the debuggability answer, at the price of a component that must itself be durable and highly available.
- **The saga state that did not commit with the step.** The fulfillment service executes its local transaction, then writes "step done" to the orchestrator — two writes, one crash window. If the crash lands between them, the step re-executes (duplicate effect) or never records (workflow stalls). The fix is the outbox rule: step effect and step record in one local transaction — the saga inherits the disciplines of the systems it spans.

## Step 6: Decision Framework

1. **Do all participants sit inside one trust boundary with a viable coordinator?** Yes → two-phase commit (coordinator co-located with consensus for availability). No → sagas.
2. **Does every step have a correct, implementable compensation?** No → restructure the workflow (reservations before irreversible effects, compensation-free last steps) before choosing the mechanism; a saga with uncompensable steps is not atomic at any level.
3. **Can readers and concurrent workflows tolerate visible intermediate states?** Yes → sagas. No (the middle must be unobservable) → 2PC, or redesign so no one needs to observe the middle.
4. **What is the transaction's duration class?** Milliseconds on a fast LAN → 2PC's overhead is tolerable. Seconds-to-days, with human steps → sagas; locks cannot span human timescales.
5. **What is the failure budget for coordination itself?** "Never stall" → sagas (no in-doubt window exists). "Never diverge" → 2PC (the protocol's promise), accepting the stall risk.
6. **Default in doubt:** local ACID transactions plus outbox inside each service; a persistent orchestrator with per-step compensations, semantic-lock status columns, and idempotent compensation across services; reserve genuine 2PC for the short, few-participant, same-trust-domain cases where its isolation is actually required.

## Interview Questions

1. **"2PC is atomic, sagas are not — so 2PC is more correct." Critique the claim.** Both are correct relative to their contracts: 2PC offers strict atomicity with a blocking window whose cost is availability; sagas offer eventual atomicity with visible intermediates whose cost is application complexity. Saying one is "more correct" without naming the isolation-availability trade it accepts is the slogan this analysis exists to replace.
2. **A coordinator dies mid-2PC and 50 transactions are in doubt. What are the options, and what does each risk?** Restore the coordinator and let it resolve from its log (safe, slow); heuristic commit or abort per participant (fast, risks divergence — one side commits while its partner aborts). The design lesson: coordinator availability is not optional; production 2PC co-locates it with consensus.
3. **Design the saga boundary for "charge card, send confirmation email, provision account."** Order the steps so every fallible, compensable action precedes irreversible ones: provision (compensable: deactivate), charge (compensable: refund), email last (uncompensable but now only sent after success). Add semantic-lock statuses consumers respect, idempotent compensations, and the outbox so step effects and saga state commit together.
4. **Why does saga compensation need idempotency even though sagas "don't retry the happy path"?** Compensation runs on failure paths, failure paths correlate with retries (crashes, timeouts, operator replays), and an at-least-once orchestration means a compensation may fire more than once. A non-idempotent refund (credit issued twice) turns failure recovery into a money-losing bug — the same idempotency tax at-least-once messaging charges, collected on the compensation path.
5. **When is choreography better than orchestration for a saga?** When the workflow is short, stable, and owned by few teams — the event-driven decoupling avoids a central component and its HA burden. As steps, teams, or branches grow, the implicit workflow becomes undebuggable (cycles, missing handlers), and the persistent orchestrator's explicit state machine pays for itself in observability and change safety.

## Key Takeaways

- The fork is **where uncertainty lives**: 2PC concentrates it in an in-doubt window enforced by locks (stall on coordinator death); sagas distribute it across visible intermediate states that every reader must be programmed to interpret.
- 2PC's prepare promise is bought with locks — atomicity and blocking are the same mechanism viewed from two sides; coordinator availability is part of the design, not an afterthought.
- Sagas replace locks with compensation: every step needs a correct, idempotent inverse, semantic locks approximate isolation, and irreversible effects must be sequenced after every fallible step.
- Orchestration versus choreography decides where the workflow's truth lives — a debuggable state machine versus an implicit event graph — and both inherit the outbox discipline for state-that-commits-with-effects.
- The production default is a hybrid: strict atomicity inside each service (local transactions plus outbox), compensated sagas across services, and genuine 2PC reserved for short, few-participant, same-trust cases that justify its operational weight.

## Cross-References

- [ACID Transactions: Follow-up Tree](../followup-tree/acid-transactions.md) — the transaction ladder from local ACID to cross-service coordination.
- [Event Sourcing and WAL: Connection Atlas](../connection-atlas/event-sourcing-wal.md) — the log kinship behind outbox-based saga state and step records.
- [App Events vs CDC: Why-Not Handbook](./app-events-vs-cdc.md) — the dual-write hole and outbox bridge the saga state discipline relies on.
- [Two-Phase Commit](../../dbms/transactions/two-phase-commit.md) and [Saga](../../dbms/transactions/saga.md) — the book's mechanism chapters for each side.
- [Three-Phase Commit](../../dbms/transactions/three-phase-commit.md) — the attempted non-blocking revision and its partition trade.
- [Distributed Transactions](../../distributed/advanced/distributed-transactions.md) — the wider catalog of coordination designs beyond this pair.
- [Percolator](../../distributed/fundamentals/percolator.md) — 2PC rebuilt at planetary scale with client-driven coordination.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
