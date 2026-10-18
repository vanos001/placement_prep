# Follow-up Tree: Rate Limiter Design

## Overview

"Design a rate limiter" is the canonical system-design opener precisely because its follow-ups ladder cleanly: requirements, algorithm choice, distributed correctness, failure posture, and scale — each answer creating the next question. The repo's full worked design lives in [Rate Limiter (System Design)](../../interview/system-design/rate-limiter.md); this page is the *escalation* companion: what each follow-up tests, how to reason through it, and where the standard answers break. The sibling pages [Backpressure](../connection-atlas/backpressure.md) (load shedding as the system-level frame) and [Caching and Distribution](../why-not-handbook/caching-distributed.md) (the distributed-consistency toolkit this design borrows) supply the surrounding theory.

## The Opening Question

**"Design a rate limiter for an API."**

The expected core answer: a component that decides, per request, whether the caller has exceeded an agreed quota — evaluated against a rule (who is limited, on what dimension, at what rate), enforced at a layer (client, gateway, or service), and backed by a decision algorithm. Before any algorithm: state the clarifying questions, because *the requirements are the design* — hard limit vs soft quota; per-user, per-IP, per-API-key, or global; what "exceeded" triggers (429 with `Retry-After`, queueing, silent drop, degraded response); and whether the limit must be exact or merely smooth.

Why this answer is correct: interviewers use the rate limiter to test whether you *scope before building*. A candidate who jumps to token buckets without asking "distributed or per-node?" and "what happens when the limiter itself fails?" has answered the easiest rung and failed the one above it — and the interviewer marks the missed questions as the real signal.

## Follow-up 1: Which Algorithm, and What Does Each Smooth or Distort?

**What it tests:** whether you know the algorithm zoo as a set of *distortion profiles*, not names — the rung where "token bucket" as a reflex gets exposed.

**How to reason:** every limiter answers two questions: what counts as "one request," and over what time shape the quota is enforced. Compare candidates on boundary behavior, burst tolerance, memory, and per-check cost.

**Answer.** **Fixed window**: count requests in each aligned interval (e.g., per minute); cheapest (one counter + timestamp) but has the *boundary burst* — 100 requests at 00:59 and 100 at 01:01 are both "in limit" while being 200 in two seconds, doubling the effective rate at window edges. **Sliding log**: store a timestamp per recent request (reject if the last window holds ≥ N); exact and smooth, but memory is O(N) per client and per-check cost grows with rate — a Redis ZSET of timestamps is the standard implementation ([Redis data structures](../../redis/data-structures.md)). **Sliding window counter**: interpolate between the previous and current fixed windows (weight by elapsed fraction) — smooths the boundary at O(1) memory, at the price of approximation; this is the popularized middle ground (Cloudflare, "How we built rate limiting capable of scaling to millions of domains," 2017). **Token bucket**: a bucket of B tokens refilling at r/s; each request takes one — enforces an *average* rate r while permitting bursts up to B, single-state, trivially atomic; the default choice when "some burst is fine" (Guava's RateLimiter, most API quota systems). **Leaky bucket**: requests queue (or are dropped) and are *served* at a constant rate — shapes output rather than capping input; nginx's `limit_req` is the canonical implementation. The senior sentence: token bucket controls *rate with bursts*, leaky bucket controls *pacing*, sliding log controls *history*; the choice is which distortion your callers can tolerate. For probabilistic memory savings on huge client populations, see [Probabilistic Data Structures](../../interview/system-design/probabilistic-data-structures.md).

## Follow-up 2: Now Make It Distributed — Where Do the Races Come From?

**What it tests:** distributed correctness — whether you can find the read-modify-write race without being led to it.

**How to reason:** one node, one counter, no problem. Two nodes, each keeping its own count, means 2× the limit. Centralize the counter in Redis — and now every check is a *network read followed by a conditional write*. Ask what happens between those two steps.

**Answer.** The naive flow — GET counter, compare to limit, INCR — is a race: two gateway nodes both GET the same count just below the limit, both pass, both INCR, limit exceeded. The fixes in order of adoption: (1) do the whole check *atomically in Redis* — a Lua script ([EVAL](https://redis.io/commands/eval/)) that reads, decides, and writes as one step; Redis executes each script serially, so no interleaving; (2) use single-command atomic primitives where the algorithm allows — [INCR](https://redis.io/commands/incr/) is atomic, so "INCR then compare then maybe reject" works for a fixed window, provided the TTL is set atomically too (`SET key 0 EX 60 NX` to create with expiry in one command — creating the key and setting TTL in two separate commands is the classic bug: crash between them leaves an immortal counter); (3) GETSET-style reset patterns for window rollover. Additional distributed edge cases to volunteer: **clock skew** — window boundaries must come from the Redis server's clock (the Lua `TIME` command), not each gateway's; **the check is not free** — every request now pays a network round trip (~0.5–1 ms in-datacenter) and Redis becomes both a latency floor and a single point of contention; **partition behavior** — if a gateway can't reach Redis, Follow-up 4 decides what happens. The design doc in [Rate Limiter (System Design)](../../interview/system-design/rate-limiter.md) walks the deployment shape; here, naming *where atomicity lives* is the rung's pass condition.

## Follow-up 3: The Redis Node Goes Down. Fail-Open or Fail-Closed?

**What it tests:** failure posture — the rung that separates candidates who designed a feature from candidates who designed a system.

**How to reason:** the limiter is now on the request path. When its dependency fails, enforcement stops — so ask what the limiter *protects*, because that determines which failure is acceptable.

**Answer.** **Fail-open** (allow on limiter failure) preserves availability of the API but removes the protection — correct when the limiter is a *courtesy quota* (public API fairness) and the backend can absorb a traffic surge. **Fail-closed** (reject on limiter failure) preserves the protection but turns a limiter outage into a full API outage — correct when the limiter is a *safety control* (protecting an expensive or fragile backend, enforcing paid tiers, security-sensitive endpoints) and unbounded traffic is the worse outcome. A useful refinement to volunteer: differentiate by blast radius — fail-open for user-facing reads, fail-closed for write paths or expensive jobs; and keep a *local fallback*: per-node counters with a stale global sync give degraded-but-working enforcement during a Redis outage, trading accuracy for liveness. State the trade as a decision the business owns: "the limiter's SLO is part of the API's SLO" — if enforcement failure means the *backend* falls over, fail-closed with a cache of recent decisions is the defensible posture; if it merely means some users exceed their quota briefly, fail-open. The general principle — decide which failure you prefer *before* the failure — is the same one behind load shedding and bulkheads ([Bulkheads](../../sre/bulkheads.md), [Backpressure](../../interview/system-design/backpressure.md)).

## Follow-up 4: Scale It — Hot Keys, Sync Costs, and Two-Level Limiting

**What it tests:** whether the design survives its own success — the follow-up that flips the design's assumptions one by one.

**How to reason:** the centralized counter assumed (a) one Redis key per client is one hot spot at most, (b) per-request sync is affordable, (c) client population is diffuse. Attack each assumption.

**Answer.** **Hot keys**: a celebrity account or a poisoned credential can hammer one key — Redis serializes per-key work, so that key becomes a throughput ceiling and a fairness problem. Standard mitigations: shard the counter (split the client's quota across N keys on different nodes; each check decrements a random shard, or sample-and-sync) at the cost of burst fuzziness; or make the limit higher-level (per-tenant rather than per-user) so hot users share a cheaper, less contended bucket. **Sync costs**: per-request Redis RTT is fine at modest QPS; at high QPS, batch (check every K requests or T milliseconds against a local allowance), or go two-level: each gateway holds a *local pre-allocation* (e.g., lease 100 units from Redis, enforce locally, renew when drained) — latency drops to zero on the hot path, accuracy degrades to the lease size, and Redis load drops by the lease factor. **Diffuse-client assumption**: at millions of clients you cannot keep precise state for all; keep exact state for the *active* set (LRU eviction of idle clients — the standard sliding-counter implementation detail) and approximate or aggregate the tail. If the interviewer pushes further ("multi-region?"), the honest answer is that a globally consistent limiter costs a WAN RTT per request — real systems either accept regional limits (per-region quota) or go asynchronous (near-real-time reconciliation, occasional overage) — a genuinely hard trade where naming both costs *is* the senior answer.

## Follow-up 5: "Now Make It X" — Handling the Twist

**What it tests:** the design-interview endgame: can you extend the design without rebuilding it, saying what each twist costs?

**How to reason:** each twist modifies one earlier decision. Locate which one, state the conflict it creates, and resolve it with the cheapest change.

**Answer sketch for the common twists.** *"Burst allowance for premium users"* — token bucket's B parameter per tier; state that sliding log handles this badly (history is uniform) while token bucket handles it natively. *"Fair sharing within a tenant"* — a quota per tenant hides a noisy-neighbor inside it; add per-user sub-limits or a weighted-fair-queue at the service ([Fair Queuing](../../networks/advanced/fair-queuing.md)). *"Rate limit by cost, not count"* — heavy queries cost more units; the counter decrements by cost instead of 1, token bucket becomes a credit system; note the atomicity requirement moves into the Lua script's arithmetic. *"Limiter for async jobs"* — same algorithms, but the rejection semantics change: jobs *retry with backoff* instead of erroring, so the limiter doubles as a scheduler input ([Task Scheduler patterns](../../interview/system-design/case-studies/distributed-task-scheduler.md)). *"Per-IP limiting"* — NAT makes IPs a poor identity proxy (thousands of users behind one IP); you are now designing *identity* (API keys, tokens, device fingerprints) more than limiting — say so explicitly, because recognizing that the twist left the domain is exactly the meta-skill being tested.

## How to Approach Unfamiliar Variations

1. **Every limiter question has three questions inside it: who, what shape, what on failure.** "Who" is identity and dimension; "what shape" is the algorithm's distortion profile (bursty? windowed? paced?); "what on failure" is fail-open/closed. Any unseen variant — websocket messages, cron jobs, LLM tokens per minute — is filled in by answering those three.
2. **Locate the atomicity before trusting any counter.** Read-modify-write across a network is the pattern to spot; the fix is always "make the decision inside one atomic step" — Lua in Redis, a DB transaction, a single INCR — never two commands with a decision between them.
3. **Price accuracy against latency explicitly.** Exact + centralized = an RTT per request and a hot spot; approximate + local = free checks and fuzzy edges. Saying "here is the knob and here is what it trades" beats picking either end.
4. **When the twist changes the *unit* (requests → tokens → cost → concurrency), re-derive, don't recall.** Concurrency limits (max in-flight per client) are the same math with "release" on completion; token-cost limits are the same math with a subtraction amount. The algorithm zoo survives; the decision logic adapts.

## Interview Questions

**Q: Why is a fixed-window counter in Redis prone to a subtle TTL bug?**
A: If the key is created with INCR and the TTL is set by a separate command, a failure between them (process crash, network error) leaves a counter with no expiry — the window never rolls over and the client is locked out indefinitely. Fix: create atomically with the TTL (`SET key 0 EX 60 NX` before INCR, or INCR with TTL-if-new semantics in a Lua script), or set the TTL unconditionally on each hit.

**Q: Your gateway fleet enforces a global 1,000 req/s via one Redis key, and Redis CPU is pegged. Cheapest structural fix?**
A: Two-level limiting: each gateway leases a share (say 50 requests) from Redis via an atomic decrement, enforces locally with zero per-request RTT, and refills when drained — Redis load falls by ~50×, global accuracy degrades to the lease granularity. Alternatively shard the key across nodes with per-shard quota. The wrong answer is a faster Redis: the ceiling is *contention on one key*, not Redis throughput overall.

**Q: Should a rate limiter for an expensive ML inference endpoint fail open or closed when its store is down?**
A: Fail closed: the endpoint's cost per request makes unbounded traffic the catastrophic failure, while limiter downtime means rejecting (or shedding) rather than overspend — pair it with a stale-but-usable local decision cache so brief outages only cost accuracy, not availability. For a cheap public read API the same failure should fail open. The choice follows from what the limiter protects, not from ideology.

**Q: Sliding log gives exact enforcement but your client population is 50M. What do you actually deploy?**
A: Sliding window counters (O(1) memory) or token buckets keyed in an LRU cache of active clients, with approximate enforcement for the long tail; exact logs only for high-value or flagged identities. 50M precise histories is a memory bill no correct answer pays; the design question is where the approximation is cheapest.

## Key Takeaways

- The rate limiter is a ladder about *scoping*: requirements (who, what shape, what on failure) are rung one because every later decision — algorithm, store, failure posture — hangs off them.
- The algorithm zoo is a set of distortion profiles: fixed window's edge burst, sliding log's exactness cost, sliding counter's approximation, token bucket's burst-with-average, leaky bucket's pacing. Choose by which distortion callers tolerate.
- Distributed enforcement moves atomicity into one atomic step per decision; the classic bugs (read-then-write races, orphaned TTLs, client clocks) all violate that rule.
- Fail-open vs fail-closed is a business decision about what the limiter protects; a local fallback turns a binary posture into a graceful degradation curve.
- Scale twists attack the design's assumptions one at a time — hot keys, per-request sync cost, diffuse clients — and two-level limiting (leases + local enforcement) is the standard resolution pattern.

## Cross-References

- [Rate Limiter (System Design)](../../interview/system-design/rate-limiter.md) — the full worked design this chain escalates from.
- [Redis Data Structures](../../redis/data-structures.md) — the counter/ZSET primitives behind Follow-up 2.
- [Redis Patterns and Internals](../../redis/patterns-and-internals.md) — atomicity, scripting, and single-threaded execution model.
- [Backpressure (System Design)](../../interview/system-design/backpressure.md) and [Bulkheads](../../sre/bulkheads.md) — load-shedding siblings of the fail-open/closed decision.
- [Probabilistic Data Structures](../../interview/system-design/probabilistic-data-structures.md) — approximate counting for huge client populations.
- [Fair Queuing](../../networks/advanced/fair-queuing.md) — the sharing discipline inside Follow-up 5's fair-share twist.
- [Caching and Distribution](../why-not-handbook/caching-distributed.md) — sibling handbook page for the cache/consistency toolkit this design borrows.
- [Backpressure Connection](../connection-atlas/backpressure.md) — sibling atlas page placing the limiter in the load-control family.
- [Latency Numbers](../../interview/system-design/latency-numbers.md) — the cost model behind "one RTT per request" arguments.
- [System Design Hub](../../interview/system-design/README.md) and [Interview Overview](../../interview/overview.md) — parent hubs.
