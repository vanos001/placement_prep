# "A cache always improves performance"

## Overview

Caching is the most recommended optimization in systems design, and the
recommendation is earned — most well-placed caches transform latency. This
page maps the boundary of that truth: caches are a bet on reuse, paid for on
every miss and every write, with failure modes (stampede, staleness,
pollution) that can leave the system *worse* than uncached. The verdict is
"incomplete": the claim captures a real average-case benefit and deletes the
preconditions — locality, sufficient hit rate, staleness tolerance — that
decide whether the bet pays.

## The Claim, Stated Fairly

The strongest common form: "Reading from the database on every request is
obviously wasteful; put a cache in front and requests get served from memory.
Caching is the single highest-leverage performance move in system design, so
add it early." This is fair as stated — it is what most design documents say,
it is often the right call, and in the regime the speaker works in (hot keys,
read-heavy traffic, tolerable staleness) it is true.

## Verdict

**Incomplete.** Caching improves performance only under locality, reuse, a
hit rate high enough to amortize the miss penalty, and tolerance for
staleness; outside that regime it adds latency, memory, and failure modes
with no return.

## Why People Believe It

The kernel of truth is arithmetic that really works in most workloads. With
a 1 ms cache hit, a 50 ms uncached read, and a 90% hit rate, mean latency is
0.9 × 1 + 0.1 × 50 = 5.9 ms — a ~8.5× improvement, and at 99% it is
~1.5 ms. Real caches deliver this daily; CPU caches, page caches, CDNs, and
Redis deployments all exist because the reuse bet pays. Design-interview
culture reinforces it: "add a cache" is a stock answer because hot keys and
read skew are genuinely common.

What the belief deletes: the same formula *inverts* when the hit rate is low
or the miss path is expensive, and the inversion is not hypothetical — it is
a standing production incident class (stampede), a correctness class (stale
reads), and a cost class (memory for the un-hit tail).

## The Correct Formulation

Caching pays when four preconditions hold: (1) **reuse** — the same data is
requested more than once within its validity window; (2) **sufficient hit
rate** — the hit-rate-weighted latency beats the uncached path including
overhead; (3) **staleness tolerance** — consumers accept answers that may be
older than the source of truth; (4) **capacity for the working set** — the
hot keys fit in memory, so the hit rate is real rather than theoretical.

The break-even is easy to compute. Let a hit cost 1 ms and a miss cost 51 ms
(the 50 ms read plus 1 ms of cache overhead), against a 50 ms uncached read.
The cached mean is below 50 ms only when h·1 + (1 − h)·51 < 50, which solves
to h > 2%. So with these numbers, a cache under 2% hit rate is pure loss —
every request pays the extra overhead, and none gets the benefit. Change the
miss penalty to a 500 ms upstream and the break-even drops to ~0.2%; change
the overhead to 5 ms (serialized object materialization, network to Redis)
and the break-even rises to ~8%. The regime boundary moves with the
parameters — which is exactly why "always" is wrong and "measure your hit
rate" is right.

| Claim says | Reality |
|---|---|
| "Serving from memory is faster" | Faster *on hits*; the miss path is the uncached path *plus* cache overhead |
| "Caching is free capacity" | Memory and serialization cost; caching the un-hit tail buys nothing |
| "TTL keeps things fresh" | TTL trades staleness window against load; it never makes data fresh |
| "More cache is safer" | Each cold or expired key can stampede; bigger caches change, not remove, that risk |

## Where It Breaks

**Single-shot access.** A job reads each of 10,000,000 user records exactly
once (an offline migration). Hit rate: 0%. Every record pays the extra
overhead on top of the full read: the cache is a strict tax. This is the
cleanest counterexample — no locality, no reuse, nothing to amortize.

**The stampede.** A hot key expires at t = 0. At that moment 1,000 requests
per second arrive and all miss. All 1,000 run the 50 ms upstream query
against a database sized for 10 such queries per second — the database
saturates, timeouts cascade, and the recovery (retry storms) extends the
incident. Mitigations exist and are workload-standard: request coalescing
(single-flight, so one loader fetches while 999 wait), probabilistic early
expiration (refresh before TTL with probability proportional to remaining
value lifetime), per-key locks, and jittered TTLs so keys do not expire in
lockstep. The uncached system had none of these failure modes.

**Write-heavy workloads.** A counter updated 10,000 times per second and read
once per hour: caching the read saves nothing while the write path either
invalidates constantly (cache-aside churn) or coalesces writes (write-behind)
and risks losing them. The reuse precondition fails on the write side.

**Stale reads with teeth.** A permissions cache with a 60-second TTL grants a
revoked user 60 seconds of access. The "performance improvement" is a
security regression: staleness tolerance is a precondition the workload does
not have. The fix (shorter TTL, explicit invalidation on revocation) costs
the hit rate the cache was justified by.

**Cache pollution.** One bulk scan of the key space evicts the genuine hot
set (LRU is vulnerable to sequential scans). After the scan, hit rates
collapse and the database pays for the cache's existence — "we added a cache
and the database got slower" is a real report with this mechanism.

## Practical Implications

- Measure hit rate and miss penalty *before* justifying a cache with them;
  the break-even formula h·t_hit + (1−h)·t_miss < t_uncached is the audit.
- Design the miss path for concurrency from day one: single-flight/coalescing
  and jittered TTLs are not optional extras, they are the difference between
  a cache and a stampede generator.
- Make staleness a product decision: every cache has an implicit freshness
  SLA; for security-adjacent data, invalidation on event beats TTL hoping.
- Protect the working set: size caches to the hot keys, and use scan
  resistant policies where bulk reads are expected.
- Instrument hit/miss ratios and evictions; a cache without hit-rate metrics
  is an unfalsifiable belief.

## Interview Questions

### When does adding a cache make a system slower rather than faster?

When reuse fails: single-shot reads (0% hits, pure overhead), write-heavy
data (invalidation churn), or a miss path expensive enough that even the hit
rate cannot amortize it — plus systemic cases like a stampede that the
uncached system never had. The break-even is
h·t_hit + (1−h)·t_miss < t_uncached.

### What is a cache stampede and name two mitigations.

A hot key's expiry causes many concurrent misses to run the expensive
recomputation or upstream read simultaneously, saturating the backing store.
Mitigations: request coalescing/single-flight (one loader, followers wait),
jittered or probabilistically early TTL refresh, and per-key locks.

### Your cache has a 70% hit rate but p99 got worse after deploying it. What are your top hypotheses?

The miss path added latency and skew (misses are now slower than uncached
reads, concentrating in the tail), stampedes on expiry of hot keys, and
stale-answer retries (clients re-request after detecting staleness). Check
miss latency distribution, expiry-aligned spikes, and upstream load.

## Key Takeaways

- A cache is a bet on reuse: the payout formula
  h·t_hit + (1−h)·t_miss improves latency only when the hit rate clears the
  break-even that the miss penalty and overhead set.
- The miss path is the uncached path *plus* overhead — with low locality the
  cache is a strict tax.
- Stampede, staleness, pollution, and memory cost are not edge cases; they
  are the cache's second invoice.
- "Caching helps" is a conditional theorem; the conditions (locality, reuse,
  staleness tolerance, working-set fit) are the actual engineering content.

## Cross-References

- [Assumptions Hunt: Caching](../assumptions-hunt/caching.md) — the locality
  and reuse assumptions made explicit
- [Why-Not Handbook: Caching and Distributed](../why-not-handbook/caching-distributed.md)
  — when not to cache, as a decision framework
- [Cache Patterns](../../sre/cache-patterns.md) — cache-aside,
  write-through, and the invalidation machinery
- [Caching Strategy](../../interview/system-design/hld/caching-strategy.md)
  — the design-interview version of the same tradeoffs
- [Indexes Always Faster](./indexes-always-faster.md) — the database-side
  cache (buffer pool) displacement argument
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- The break-even and stampede material above is reasoning from the standard
  caching model (hit-rate-weighted mean latency) rather than citation of a
  specific measurement; the arithmetic is shown inline and reproducible.
- M. Kleppmann. *Designing Data-Intensive Applications*. O'Reilly, 2017 —
  Chapter 1's caching discussion and the read-through/write-through pattern
  taxonomy.
