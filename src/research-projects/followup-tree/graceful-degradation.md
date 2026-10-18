# Follow-up Tree: Graceful Degradation

## Overview

"Your database is at 100 percent CPU and latency is climbing — what should the service do right now?" is the follow-up that converts a textbook answer ("add capacity") into a senior answer, because by the time the database is saturated, adding capacity is not one of the options the next five minutes contain. The ladder tests whether you have a pre-decided answer for overload: shed load early rather than degrade everything uniformly, contain the failure with bulkheads so one dependency cannot consume the process, serve a deliberately reduced product (degraded modes with a pre-argued shedding order), and lean on static or stale fallbacks where a fresh answer is impossible. Every rung ties to another chain: the queueing arithmetic is [Queueing Fundamentals](../../queueing-theory/fundamentals.md), rate-limit placement is [Rate Limiter Design](./rate-limiter-design.md), failure detection is [Circuit Breakers](./circuit-breakers.md), and the casebook's Fastly entry shows a system that failed *closed* with no degraded mode. This page owns the decision itself: what to reject, contain, dim, and in what order — the contract a service signs about how it will fail.

## The Opening Question

**"What should a service do when it is overloaded — and why is 'keep accepting requests' the wrong answer?"**

The expected core answer: an overloaded service must shed load — deliberately reject some requests early with an explicit status (429 or 503, ideally with a retry hint) — because accepting everything degrades *every* request: queues grow, latency explodes, timeouts fire downstream and multiply retries, and the service transitions from "slow for some" to "useless for all." The counterintuitive core is that rejection is *protective*: shedding 20 percent of traffic lets the remaining 80 percent succeed at normal latency, preserving more useful work than admitting 100 percent and serving none in time. Deciding *whom* to shed (new vs existing sessions, critical vs cosmetic, paying vs free) is the design content, and the mechanism — admission control at the edge, per-dependency limits inside — recurs at every level.

Why this answer is correct: it treats overload as a queueing problem with a control decision, not an outage to be endured. The next question is predictable — "how do you know you are overloaded, and what do you shed first?" — and deliberate-policy framing establishes the whole ladder's vocabulary.

## Level 2: Load Shedding — Reject Early, Reject Deliberately

**What it tests:** whether you understand admission control as a first-class mechanism — where it sits, what signal drives it, why unbounded queueing is the enemy — rather than a last-resort error path.

**Weak answer:** "We scale out when CPU is high" — autoscaling is a minutes-scale response to a seconds-scale problem and says nothing about the gap between overload and fleet growth.

**Strong answer:** the overloaded component protects itself by refusing work it cannot serve in time, at the earliest point the decision can be made correctly (the edge for global decisions, the service itself for dependency-specific ones), driven by a signal that *predicts* failure — queue depth, in-flight count, concurrency limits, latency trends — rather than one that reports it after the fact. Knows the amplification mechanics: retries and timeouts convert one slow request into several fresh ones, so a service that does not shed generates its own load storm; knows the postures for rejected requests (fail fast with 429/503 and Retry-After, or a bounded admission queue) and why "shed at the edge, queue briefly inside" is the common compromise.

**Escalation trigger:** "Under a 3x traffic spike, p99 goes from 200 ms to 30 s and success drops to 40 percent — yet CPU is only at 60 percent. What is happening and what do you change?"

**Answer.** The service is not compute-bound — it is *queue-bound*: requests are admitted faster than they can be processed, so they wait; utilization past the knee drives latency up hyperbolically, and the 30 s p99 is mostly waiting. The 60 percent CPU and 40 percent success are the signature: threads and connections parked on something downstream, timeouts firing at scale, client retries adding load when the system can least afford it — the amplification loop. The changes: admit consciously — enforce a concurrency or in-flight limit at the service boundary so excess requests get a fast 429/503 instead of a 30-second death; make timeouts and retries well-behaved (bounded attempts, jittered backoff) so amplification is cut even if shedding misses; and shed *by value* — protect checkout and auth, shed prefetch and personalization; the value ordering is the next rung's content. The queueing mechanics are [Queueing Fundamentals](../../queueing-theory/fundamentals.md); the stream-flow version of the same contract is [Backpressure](../connection-atlas/backpressure.md).

## Level 3: Bulkheads — Contain the Blast Radius Before You Need It

**What it tests:** whether "one dependency is down" means "the service is down" in your mental model, or whether resource isolation makes dependency failures *local* — and whether you know that timeouts alone do not provide containment.

**Weak answer:** "We set timeouts on downstream calls, so we're protected" — a timeout bounds one call's duration but does nothing about ten thousand calls parked in the same shared pool waiting on a dead dependency.

**Strong answer:** bulkheading partitions finite resources (worker threads, connection pools, memory, quotas) per dependency or per tenant, so saturation in one partition cannot consume another's: recommendation can hang without taking down checkout, because checkout's threads were never lent to recommendation work. Knows the two implementations — thread/semaphore-per-dependency (bounded parallelism per downstream) and pool-per-dependency (connections, memory) — and the failure signature of missing bulkheads: a slow dependency's calls accumulate in the shared pool until *every* endpoint touching it starves, the cascade timeouts were supposed to prevent but numerically cannot. Ties it to deployment-level isolation (instance pools, cells) as the same idea at coarser granularity.

**Escalation trigger:** "Your auth dependency slows from 20 ms to 8 s. With per-call timeouts of 5 s, why might the whole service still fall over — and what would have contained it?"

**Answer.** Walk the arithmetic: every request still *calls* auth (the timeout fires only after 5 s of waiting), so at 100 requests/second the service holds ~500 auth calls in flight, each holding a thread and a connection — the shared pool is exhausted by calls that are all *going to fail*, and endpoints that never touch auth starve behind it. The timeout bounded each call's duration, not the *aggregate* resource held by failing calls — aggregate containment is the bulkhead's job. What would have contained it: a semaphore or thread-pool bulkhead around the auth dependency (say, 50 concurrent max — the 51st fails immediately), so auth degradation costs at most 50 slots rather than the whole runtime; a circuit breaker (stop calling auth once failure rate crosses threshold — the [Circuit Breakers](./circuit-breakers.md) chain owns the state machine) to convert those 50 from "waiting 5 s" to "failing in microseconds"; and per-dependency pools so the datastore never competes with the auth client. The [bulkheads](../../sre/bulkheads.md) chapter develops the pattern; at the deployment tier the same idea becomes cells ([Cell Architecture](../../sre/cell-architecture.md)). The senior framing: timeouts, bulkheads, and breakers are three controls over one overload — duration, concurrency, and invocation — and real systems need all three because each addresses what the others leave exposed.

## Level 4: Degraded Modes and the Shedding Order — Dim the Lights on Purpose

**What it tests:** whether the candidate's system has a *pre-decided* partial service — a ranked list of features to disable, with stale and static fallbacks — or whether degradation will be improvised at 02:00 by whoever is on call.

**Weak answer:** "We show a maintenance page" — the binary last resort presented as a strategy; it discards every feature that could still work.

**Strong answer:** describes a degradation ladder agreed before the incident: features ranked by (business value, dependency cost), disabled from the top of the cost list down — personalization and recommendations first (expensive, cosmetic), then reviews and comments, then non-essential writes, leaving browse/search/cart/checkout on cache-backed read paths until last. Names the supporting mechanisms: feature flags to flip expensive features off without deploys ([Feature Flags](../../sre/feature-flags.md)), stale-while-revalidate and serve-on-error caching ([Redis Caching](./redis-caching.md) owns the cache-aside machinery), static fallback pages, and read-only mode — "keep shopping from your cart, you cannot check out" — which preserves product value while protecting write invariants.

**Escalation trigger:** "Design the degradation plan for an e-commerce site whose search backend dies two hours into a Black Friday peak."

**Answer.** The plan exists in the runbook, not in the incident: search dies, so step one is the flag that swaps the search box for category navigation and curated collections — zero revenue-critical loss, because browsing was never search-dependent in the plan. Step two protects capacity from the *retries and refreshes* the failed search generates (the breaker opens — fail fast; freed capacity re-admitted to browse and checkout). Step three is the customer-communication contract: "search is temporarily unavailable" on the degraded surface, because silent degradation reads as brokenness and drives support load. What makes this senior is what it *refuses*: it does not attempt degraded queries against the primary database — the improvised move that converts a search outage into a database outage mid-peak — and it does not treat the maintenance page as the plan, because discarding a working checkout to hide a dead search box is strictly worse. The shedding order is a *product* decision with an engineering cost model — made in planning season, exercised in game days ([Chaos Engineering](../../sre/chaos-engineering.md) owns the discipline), and encoded as flags. The Fastly incident in the [Failure Casebook](../failure-casebook/fastly-june-2021.md) is the cautionary mirror: one bad config took the whole edge down globally because fail-closed was the only mode — no degraded surface existed to fall back to.

## Level 5: Fairness, Testing, and the Judgment Rung — When Not to Shed

**What it tests:** the design-judgment boundary: shedding policy under heterogeneous clients, verifying degradation before it is needed, and the honest limits — invariants and writes that cannot be safely degraded.

**Weak answer:** applies shedding uniformly ("reject 30 percent of everything") and has never tested the degraded paths — both surface only in production, at the worst moment.

**Strong answer:** distinguishes fairness-aware shedding (per-client or per-tier admission so one noisy tenant cannot consume others' shed budget; priority classes where checkout outranks analytics — the per-client limit placement is [Rate Limiter Design](./rate-limiter-design.md) territory) from naive global shedding; insists degradation is *tested* (load tests crossing the shedding threshold, game days flipping the flags, fallback verification — an untested fallback is a second incident waiting inside the first); and states the honest limit: some work cannot degrade — writes protected by invariants (inventory decrement, payment capture) fail rather than approximate, and systems where consistency under partition is non-negotiable choose unavailability for that path deliberately ([Consistency vs Availability](../misconceptions/consistency-availability-partition.md) frames the choice).

**Escalation trigger:** "Your shedding works in staging. Black Friday: the shed activates, success improves — but one enterprise customer generates 60 percent of the failures, and your static fallback page starts returning yesterday's prices. What went wrong at each layer?"

**Answer.** Layer one is fairness: global shedding treats all traffic alike, so the enterprise customer's legitimate load got shed at the same rate as the abusive spike — under heterogeneous clients, shedding must be per-class (weighted by tier or value), otherwise your best customers absorb the outage proportionally to their usage. The fix is admission control keyed on client identity with per-class budgets — the per-client placement [Rate Limiter Design](./rate-limiter-design.md) analyzes — plus protection floors (a class may be degraded, not zeroed). Layer two is the fallback's own contract: a static fallback carrying *stale prices* is not degradation but a correctness incident — prices are transaction-adjacent, so the fallback must be explicitly labeled and cleared for staleness, or scoped to data that cannot hurt (category names, marketing copy). Both failures share a root cause: the degradation paths were exercised in staging but never re-validated against production semantics — who the clients are, and what the fallback data may claim. The fixes: class-aware shedding with floors, fallbacks audited field by field for staleness tolerance, and game days replaying the real traffic mix ([Load Testing Strategies](../../sre/load-testing-strategies.md) covers production-shaped load). The takeaway to volunteer: degradation is a product surface, not an infrastructure trick — every dimmed feature changes what users experience and what the business promises, so the ladder belongs to engineering and product jointly, written down in advance.

## How to Approach Unfamiliar Variations

1. **Locate the finite resource, then place the control.** Every overload variation — CPU, threads, connections, memory, downstream quota — is answered by finding the resource that runs out first and asking where the admission decision can be made correctly. Shedding, bulkheads, and breakers are that one decision at three scopes.
2. **Convert "slow" into "fast failure" and count what it frees.** When a variation describes dependency degradation, compute what bounded failure returns to the pool (threads, connections, latency budget) — the numbers decide whether timeouts suffice or bulkheads are mandatory.
3. **Rank features before the scenario asks.** For any "design the degradation" variant, produce the ladder explicitly: what dims first, what never dims, what is served stale, what is served static, what fails. The ranking with its cost/value reasoning *is* the answer.
4. **Separate what can be approximate from what cannot.** The invariant test — "if this degraded answer is wrong, what breaks?" — sorts every datum into sheddable, staled, static, and protected classes. Applying it explicitly separates a degradation plan from a refusal strategy.

## Interview Questions

**Q: Why is a 503 with a Retry-After header better for the system than queueing every request until it can be served?**
A: Two reasons: queueing converts overload into latency (admitted requests age, clients time out and retry, amplifying load when capacity is scarce), and bounded admission keeps intake proportional to real capacity. Retry-After shapes the client's retry timing (with jitter), turning an uncontrolled amplification loop into a controlled backoff — the client sheds load on your behalf, at the right layer.

**Q: You have timeouts on every downstream call. What overload scenario do timeouts still lose to?**
A: Aggregate saturation: many concurrent calls to one slow dependency each bound their duration but collectively exhaust the shared thread pool or connection pool, starving unrelated features. Timeouts bound per-call duration; bulkheads bound per-dependency concurrency. The fix is a semaphore or pool per dependency plus a breaker to stop invoking a dependency that is already failing at the bound.

**Q: The business insists checkout must never shed traffic. The checkout dependency saturates at 3x normal load. What do you actually build?**
A: Protect checkout by shedding everything else first: a priority admission policy where checkout gets a protected budget while analytics, recommendations, and prefetch are shed at progressively lower thresholds, and degrade the *content around* checkout (product pages from cache, search dimmed) so checkout's own load shrinks. Say honestly what this buys: it raises the overload point without repealing it — at some load even the protected path saturates.

**Q: A teammate adds serve-stale-on-error to the pricing service. Approve?**
A: Depends on the staleness contract per field, not the pattern: caching category pages stale is fine; serving *prices* stale silently can breach pricing promises and compliance. Approve with changes — staleness bounds per data class, explicit "may be outdated" surfacing, and an audit of which fields are transaction-adjacent. The pattern is sound; the invariant analysis decides scope.

## Key Takeaways

- Overload is a queueing event: past the utilization knee, admitting everything converts partial slowness into total failure, so deliberate rejection preserves more useful work than universal admission.
- Timeouts bound call duration, bulkheads bound concurrent resource consumption, breakers bound invocation — three controls over one overload, and production systems need all three.
- A degradation ladder is a ranked, pre-decided list of what dims first, supported by flags, stale caches, and static fallbacks — improvised degradation is how search outages become database outages.
- Shedding must be fairness-aware: per-class admission with protection floors, or your most valuable clients absorb the outage proportionally to their usage.
- Some things cannot degrade: invariant-protected writes fail rather than approximate, and static fallbacks must be audited for what their staleness is allowed to claim.

## Cross-References

- [Circuit Breakers](./circuit-breakers.md) — the sibling chain that owns failure detection and the stop-calling state machine that triggers these paths.
- [Rate Limiter Design](./rate-limiter-design.md) — admission control's cousin: per-client versus per-resource limits and the failure-posture decision they share.
- [Load Balancing](./load-balancing.md) — the health-check removal mechanics that interact with shedding signals at the edge.
- [Message Queues](./message-queues.md) — the alternative to shedding: absorb spikes as backlog, and when queueing beats rejecting.
- [Redis Caching](./redis-caching.md) — the stale-while-error machinery that keeps read paths alive when origins cannot answer.
- [API Gateway](./api-gateway.md) — where global shedding policy is usually enforced, and the config-blast-radius caveats that follow.
- [Backpressure](../connection-atlas/backpressure.md) — the streaming-systems formulation of the same capacity-propagation contract.
- [Consistency vs Availability](../misconceptions/consistency-availability-partition.md) — the underlying choice when a protected path must fail rather than approximate.
- [Fastly, June 2021](../failure-casebook/fastly-june-2021.md) — the fail-closed global outage: what a system without a degraded surface does with one bad config.
- [AWS S3, us-east-1, 2017](../failure-casebook/aws-s3-us-east-1-2017.md) — recovery traffic treated as uncontrolled load: why restarts need admission control too.
- [Bulkheads](../../sre/bulkheads.md) — the book chapter on per-dependency resource partitioning with concrete pool designs.
- [Cell Architecture](../../sre/cell-architecture.md) — bulkheads at deployment granularity: partitioned instance pools and tenant blast radius.
- [Feature Flags](../../sre/feature-flags.md) — the mechanism that makes the degradation ladder a config flip instead of a deploy.
- [Chaos Engineering](../../sre/chaos-engineering.md) — the game-day discipline that verifies degradation before the incident does.
- [Load Testing Strategies](../../sre/load-testing-strategies.md) — building production-shaped load that actually crosses the shedding threshold.
- [Handling Overload (Google SRE Book)](https://sre.google/sre-book/handling-overload/) — the canonical treatment of shedding signals and criticality-based admission (verified this session).
