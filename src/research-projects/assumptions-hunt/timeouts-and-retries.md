# Timeout and Retry Assumptions: What "Add a Timeout and Retry" Silently Promises

## Overview

Setting a timeout and retrying with backoff is the most commonly prescribed reliability fix, and it embeds four assumptions that fail in production with arithmetic precision: that the timeout is longer than real completion times at every layer it stacks through, that retries only help, that the retried operation is safe to repeat, and that backoff prevents the retry traffic from amplifying an outage into a catastrophe. Each assumption is examinable with numbers, and the numbers are unforgiving — retries multiply load exactly when the system can least afford load, and timeouts multiply user-facing latency exactly when latency is already at its worst.

This chapter audits the family with the collection's five-step pattern. The retry-amplification and latency-stacking arithmetic below was computed directly and is reproducible; the design responses (retry budgets, hedged requests, circuit breakers) follow the Google SRE book's cascading-failure chapter and Dean and Barroso's "The Tail at Scale". Where an assumption failure has a dedicated incident page, the chapter links to the casebook rather than retelling it.

## Assumption 1: "A Timeout Prevents Hanging"

### The taught rule

Set a timeout on every network call so a stalled dependency cannot hang the caller forever.

### The hidden assumptions

- A timeout only prevents *hanging*; it does not prevent *waiting*. If the timeout is set generously (or copied from a default), the caller still waits for its full duration before failing.
- Timeouts are per-hop, but user latency is the *sum* of hops. Three sequential service calls, each with a 5-second timeout, give a 15-second worst case before any layer decides the request failed — nobody set "15 seconds" anywhere; it emerged.
- Retries stack inside the same window: a 5-second timeout with 3 attempts per layer turns 15 seconds into 45. Deadlines do not propagate unless the caller explicitly sends a remaining-budget header or context value; most systems do not.
- The timeout fires on the *client*, but the *server* keeps working. A timed-out request that eventually completes consumes resources and may commit side effects — the client's retry then runs concurrently with the zombie work.

### Counterexample

A checkout page calls the order service, which calls the inventory service, which calls the pricing service. Each hop sets a 5-second timeout — individually reasonable, none synchronized. Pricing stalls during a GC pause. The user's worst-case experience: pricing times out at 5 s, inventory retries twice more (5 + 5 + 5 = 15 s per attempt chain), then order service's own timeout budget adds its layer. With 3 attempts at each of the 3 layers the theoretical worst case is 45 seconds of a user staring at a spinner — verified arithmetic (3 layers × 5 s × 3 attempts), and it requires nobody to have configured anything except "5 seconds" in three places. The corrected budget works the other direction: if the page's SLO is 300 ms, the platform allocates a total deadline of, say, 500 ms, and every hop receives the *remaining* time rather than its own fresh budget — the deepest layer inherits what is left, not what it wishes for.

### What changes when the assumption is removed

Corrected statement: *a timeout bounds the caller's wait, not the failure; only deadline propagation turns per-hop timeouts into a system-wide latency contract.* Derive per-layer budgets from the SLO (allocate the end-to-end budget across hops with margin), propagate deadlines explicitly (context deadline, gRPC deadline, HTTP `Deadline` header conventions), and remember that a timed-out call is not a canceled one — idempotency and cancellation are separate problems.

### Consequences

The interview probe "user says the site hangs for 15 seconds; where do you look?" is this assumption: the answer starts at per-layer timeout configuration and ends at deadline propagation. The SRE book's cascading-failures chapter makes the same point from the overload side: without deadline discipline, slow dependencies convert free capacity into wasted work.

## Assumption 2: "Retry With Backoff Fixes Flakiness"

### The taught rule

Transient failures happen; retrying the request after a short backoff converts most of them into successes. Higher retry counts, more reliability.

### The hidden assumptions

- Retries multiply load precisely when success is least likely. Every failed call becomes two or more calls to the failing dependency; the traffic surge arrives during the outage, not before it.
- The multiplication is multiplicative *across layers*: if A retries 3 attempts against B, and B retries 3 attempts against C, then one A request generates up to 9 C calls while C is failing completely. Three layers: 27.
- Retries also reshape latency: a request that fails at the 99th percentile and retries consumes twice its timeout budget, so the retry policy that fixes the error rate extends the tail.
- None of this is safe unless the operation is idempotent (Assumption 3) — but the two assumptions are usually configured in the same code path and inherited together.

### Counterexample

Verified arithmetic, two regimes. *Partial outage:* C serves 90% of requests successfully; B retries up to 3 attempts. Expected C-calls per B-request: 1 (first attempt) + 0.1 (10% fail once) + 0.01 (1% fail twice) = 1.11. If C's healthy load is 1,000 rps at exactly capacity, retries alone push demand to 1,110 rps — an 11% overload generated by the recovery mechanism, pushing C's success rate lower, which raises the expected call count further: a feedback loop with a documented name (retry storm) and a dedicated mechanism in the SRE book's cascading-failure chapter. *Total outage:* every attempt fails, so each layer retries the full count: one A-request becomes 3 B-calls, each becomes 3 C-calls — 9× amplification through two layers, 27× through three. This is the shape of the connection storm that degraded GitHub's failover in October 2018 (the casebook chapter has the timeline and primary sources): the clients and internal callers behaving *correctly per their retry configuration* were the load that kept the recovery from converging.

### What changes when the assumption is removed

Corrected statement: *retries are a load-multiplying trade — they buy end-to-end success probability (independent 2%-failure attempts retried three times drop the failure rate to 0.0008%) with traffic amplification during exactly the windows you cannot afford it.* The standard defenses are retry budgets (cap total retries as a fraction of normal traffic — with a 2% baseline error rate, a 10% budget permits every failure several retries on average while refusing to multiply load beyond 10%), circuit breakers (stop calling a dependency that has gone unhealthy, fail fast, probe with a trickle), and latency-budget-aware retrying (never retry a request whose deadline is already spent).

### Consequences

In system-design interviews, "what happens to your retry policy during a partial outage?" is the escalation that separates template answers from reasoning ones; the expected-C-calls-per-request arithmetic above is a complete answer in three lines. The backpressure atlas chapter develops the feedback-signal side; the SLO error-budget page supplies the budget arithmetic framework.

## Assumption 3: "Retries Are Idempotent"

### The taught rule

Retry any failed request — a failure means nothing happened, so repeating it is safe.

### The hidden assumptions

- A failed *call* is not a failed *operation*. The response can be lost after the server committed the work (payment captured, row inserted, email sent); from the server's side the operation succeeded, from the client's side it timed out.
- HTTP method semantics are advisory: RFC 9110 (HTTP Semantics, section 9.2.2) defines GET, PUT, DELETE, and others as idempotent — repeating them leaves the same server state — while POST carries no such guarantee. Client retry libraries do not enforce the distinction; the code that calls `client.post(...)` inside a retry loop does.
- Even PUT/DELETE idempotency is a property of *state after completion*, not of side effects: a PUT that triggers a notification each time has a non-idempotent shadow effect.

### Counterexample

The double charge, in five steps: client POSTs a payment request; the payment service debits the card and commits; the network drops the response; the client's 200 ms timeout fires; the retry library resends the POST; the service debits the card a second time. Every component behaved as configured — the retry fixed a failed call by repeating a *succeeded* operation. The standard fix is idempotency keys: the client generates a unique key per logical operation and sends it with every attempt; the server records the first attempt's outcome and replays it for duplicates. Stripe's API documents exactly this mechanism (including that keys are retained for 24 hours and that only the first request's result is stored and returned for replays), and it exists because the underlying operation — a charge — is precisely the kind POST that must not be repeated. The failure mode that remains is the *expired* key plus a very late retry, and the race between two concurrent first attempts, both of which the server-side key logic must handle.

### What changes when the assumption is removed

Corrected statement: *retry safety is a property of the operation's semantics, not the transport's error; make it explicit per endpoint — idempotent by method semantics, idempotent by key, or not safe to retry and therefore configured to never retry.* Classify every write path in the API surface, put the key generation in the client's logical-operation scope (not the retry loop's scope — a new key per attempt defeats the mechanism), and decide the duplicate-handling behavior (return the original result; reject with a specific error; return "already in progress") as part of the contract.

### Consequences

This assumption is the intersection of two interview favorites: "what makes POST dangerous to retry?" and "how do payment systems avoid double charges?" — and the honest answer includes the boundary cases (key expiry, concurrent duplicates, non-idempotent shadow effects like emails) rather than just the happy-path key store. The API contracts chapter treats idempotency keys as part of the service's explicit contract.

## Assumption 4: "Backoff Prevents Amplification" (Jitter, Budgets, Hedging)

### The taught rule

Exponential backoff — wait 1 s, then 2, then 4 — spreads retries out and prevents storms.

### The hidden assumptions

- Backoff spreads each client's retries in *time*, but says nothing about alignment *between* clients. A shared trigger — a failover completing, a cache expiring, a deploy finishing, a cron starting 10,000 jobs — wakes every client simultaneously, and identical backoff schedules keep them synchronized: waves of retries at 1 s, 2 s, 4 s.
- Backoff's stabilization is per-client memory; retry *budgets* are the mechanism that bounds the fleet-wide multiplication (Assumption 2), and they are a separate mechanism most teams never configure.
- Hedged requests — the tail-latency technique from "The Tail at Scale" where the client fires a second copy of a request after the first exceeds the p95 — are *deliberate, bounded* amplification (typically a few percent of requests) and must be budgeted like retries, not added on top of them.
- Circuit breakers invert the policy when a dependency is failing: without one, the retry configuration's steady-state behavior during an outage is exactly the amplification profile of Assumption 2.

### Counterexample

A shared database finishes failing over at t = 0. Ten thousand application instances each have 2 queued requests and an exponential backoff of 1 s, 2 s, 4 s. Because they all observed the failure at the same instant, all 20,000 retries arrive at t ≈ 1 s — synchronized exactly at the moment the recovering database is accepting its first connections. The recovery converges only after the system survives several of these waves; the fix documented in the AWS Architecture Blog post "Exponential Backoff and Jitter" is to randomize the delay ("full jitter": sleep uniformly in [0, base × 2^attempt]), which spreads the same retries across the whole window instead of stacking them at the boundaries. The same post's arithmetic shows full jitter reducing total completion time of a fleet-wide retry wave by an order of magnitude relative to equal-spacing backoff — the pattern is the point: *randomize, then bound with a budget, then break the circuit when the budget is gone.*

### What changes when the assumption is removed

Corrected statement: *backoff alone decorrelates a single client's attempts; fleet-scale stability needs jitter (break alignment), retry budgets (bound multiplication), circuit breakers (change policy under failure), and explicit exclusion of non-idempotent paths.* Order the mechanisms: jitter is free and always-on; budgets cap the aggregate; breakers stop the bleeding; hedging is an opt-in tool for tail latency with its own small budget. The lease-based failure-detection pattern in the connection atlas chapter shows the same timeout-jitter interplay at the coordination layer.

### Consequences

"Your service just failed over; 10,000 clients retry at once; walk me through the first 30 seconds" is a complete system-design interview in miniature: it touches jitter, budgets, breakers, warmup, and idempotency — every mechanism in this chapter — from one trigger event. Teams meeting this in production usually meet it as "the recovery made it worse", which is the signature of retries configured without this assumption set being examined.

## Interview Questions

1. **Three service layers each set 5-second timeouts. What is the user's worst-case wait, and how do you fix the configuration?** 15 seconds before any retry, up to 45 with 3 attempts per layer. Fix: derive one end-to-end deadline from the SLO and propagate the remaining budget to each hop (gRPC deadlines, context deadlines), so no layer can outlive its caller.
2. **C serves 90% success; every caller retries 3 attempts. What load does C actually see?** Expected 1.11 calls per request (1 + 0.1 + 0.01): an 11% self-inflicted overload at exactly capacity. During a total outage the multiplication is the full retry count per layer — 9× through two layers, 27× through three.
3. **Why is retrying a failed POST dangerous, and what is the production fix?** The response can be lost after the server committed the work, so the retry repeats a completed operation (double charge). Fix: idempotency keys generated per logical operation, with server-side storage of the first result and defined duplicate behavior — Stripe's documented 24-hour key retention is a concrete reference design.
4. **What does exponential backoff not fix, and what completes it?** It does not decorrelate clients sharing a trigger, and it does not bound fleet-wide multiplication. Add full jitter (randomize each delay), retry budgets (cap retries as a fraction of traffic), and circuit breakers to stop calling unhealthy dependencies.
5. **Retries turned a 1% error rate into an outage. Reconstruct the mechanism.** Retry amplification at scale: the retry traffic multiplied load during degradation, pushing the dependency deeper into overload (the 1.11× → higher-load → lower-success loop), coordinated waves re-synchronized by shared triggers; the recovery mechanism carried the outage. Budgets and breakers exist to make this loop impossible.

## Key Takeaways

- A timeout bounds waiting, not failure; only deadline propagation turns per-hop timeouts into an end-to-end latency contract, and untimed zombie work keeps running after the client gives up.
- Retries multiply load in the worst windows: 1.11× at 90% success with 3 attempts, up to retry-count-per-layer squared through stacked layers at total failure.
- Retry safety is the operation's semantics, not the transport's: POST is non-idempotent per RFC 9110, and the fix is idempotency keys with defined duplicate and expiry behavior.
- Backoff needs jitter to break cross-client alignment, budgets to bound amplification, and circuit breakers to change policy under failure — each is a separate mechanism.
- Hedged requests are bounded amplification for tail latency, budgeted like retries, not stacked on top of them.
- The signature of unexamined retry assumptions in production is "the recovery mechanism caused the outage" — a class of incident with a named case study in this repo's casebook.

## Cross-References

- [Network and distributed assumptions](network-distributed.md) — the "safe retries" assumption among the Eight Fallacies.
- [GitHub October 2018](../failure-casebook/github-october-2018.md) — failover connection storm with the retry-amplification shape.
- [Backpressure](../connection-atlas/backpressure.md) — the load-shedding counterpart to client-side retry policy.
- [Consensus and leases](../connection-atlas/consensus-leases.md) — timeout-based failure detection and its own assumption set.
- [SLO error budgets](../../sre/slo-error-budget.md) — the budget arithmetic framework retries should live inside.
- [Bulkheads](../../sre/bulkheads.md) — containing the amplification a retry storm generates.
- [Availability (HLD)](../../interview/system-design/hld/availability.md) — where these mechanisms land in a designed system.
- [Google SRE book: Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) — retry/cancel behavior and overload coupling, from the source.
