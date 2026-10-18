# Backpressure: Demand Must Travel Upstream

## Overview

Every overload death in software is the same death: work flows downstream faster than the downstream can absorb it, and the *refusal* signal never makes it back upstream. The bounded queue whose `put()` blocks, TCP's receive window, and Reactive Streams' `subscription.request(n)` are three implementations of one mechanism — propagate demand (or refusal) upstream at least as fast as work flows downstream. Where the signal is missing or broken, systems choose, usually by accident, between bufferbloat (unbounded queues, latency and memory explode) and collapse (retry storms, cascade). This page builds the mechanism set, uses Little's Law as the quantitative glue that makes queue growth *computable*, and marks the three places the clean story breaks: fan-out topologies, the single slow consumer, and retries that impersonate new demand.

## The Concepts, Independently

**Bounded queues.** A producer-consumer queue with capacity B (see [../../concurrency/producer-consumer.md](../../concurrency/producer-consumer.md)) is the minimal backpressure device: when full, `put()` blocks, so the producer's throughput is physically coupled to the consumer's. An unbounded queue is a *deferred failure*: it converts overload into memory growth and latency, then an OOM — the failure arrives later, somewhere unrelated, with no diagnostic trail. Blocking-put, dropping-put, and caller-runs are the three honest alternatives to unboundedness; "unbounded, we'll monitor it" is the dishonest fourth.

**TCP flow control and congestion control.** The receiver advertises `rwnd` — bytes it is willing to accept; the sender may have at most `min(rwnd, cwnd)` bytes in flight. That is a **credit scheme**: downstream grants finite credits, upstream cannot exceed them, demand literally travels in every ACK. Congestion control (`cwnd`) adds a second credit source modeling the *network's* capacity — see [../../networks/tcp/flow-control.md](../../networks/tcp/flow-control.md). Note the shape: TCP never lets the sender "queue into the receiver" beyond granted credit; the OS socket buffer is bounded by policy.

**Pull vs push (Kafka).** A Kafka consumer *pulls*: it issues `poll()` with a fetch budget and processes at its own pace; the broker never pushes. Consequences that fall out of the mechanism: a slow consumer only accumulates its own **lag** (a visible, measurable queue depth — the monitoring gift of pull), the broker is never saturated by the slowest subscriber, and throughput is consumer-controlled via fetch size. Push systems (webhooks, MQTT broadcasts) invert this: the sender chooses the pace, so *someone* must implement credits or per-subscriber queues or the slowest consumer sets the system's pace.

**Reactive Streams semantics.** The spec (Reactive Streams / Java 9 `Flow`) defines `Publisher`, `Subscriber`, and the demand signal: a subscriber receives elements only up to the total it has requested via `subscription.request(n)`. That is TCP's rwnd with a method name: bounded prefetch, demand-driven, no queue growth beyond the granted credit. It exists precisely because unbounded asynchronous prefetch (an eager `flatMap` over an infinite stream) is the reactive world's unbounded queue.

**Shedding, queueing, rate limiting.** Three ways to reconcile λ_in > capacity: *queue* the excess (correct when the spike is shorter than the queue's drain time and latency budget allows), *shed* it (fail fast with 503/`Retry-After`; correct when latency matters more than completeness — better an explicit 1% rejection than a 30 s p99 for everyone), or *rate limit* at ingress (cap λ_in to capacity; correct for protecting steady state from a specific caller class). Queueing theory (see [./scheduling-queueing.md](./scheduling-queueing.md)) prices the first option; the other two are the "refusal propagates upstream" family.

## The Shared Principle

**Flow stability requires demand or refusal to propagate upstream as fast as work flows downstream; Little's Law is the quantitative glue.** With L = λW ([../../queueing-theory/mm1-queue.md](../../queueing-theory/mm1-queue.md)), three cap computations follow immediately: maximum throughput of a stage is L_max/W (workers × 1/W, or window/RTT); if λ_in exceeds that and L cannot grow (bounded queue, credit window), *shedding is forced*; if L *can* grow (unbounded queue), then queue growth rate is λ_in − λ_out and waiting time grows as L/λ_in. Every credit mechanism — blocking `put()`, rwnd, `request(n)` — is an implementation of "L cannot grow without downstream consent."

## Where the Analogy HOLDS and BREAKS

| Mechanism | HOLDS (same mechanism) | BREAKS (where the clean story fails) |
|---|---|---|
| Credit windows | TCP rwnd ≈ Reactive Streams `request(n)` ≈ bounded-queue blocking put: finite in-flight grants from downstream | TCP has one receiver and one number; application fan-out has many downstreams and demand must be *aggregated* up a tree — the aggregation step exists in no off-the-shelf primitive |
| Fail-fast over bufferbloat | CoDel drops to keep sojourn time low ≈ load shedding keeps p99 bounded ≈ bounded queue + drop | AQMs drop *probabilistically per packet*; API shedding must be *coherent per request* and needs client-visible semantics (Retry-After, partial results) — network drops are free, API drops are product decisions |
| Pull pacing | Kafka consumer pull ≈ subscriber-driven demand ≈ caller-runs pool: the slowest party slows only itself | Push-broadcast has no such isolation: one slow subscriber of a fan-out stall governs everyone unless the fan-out adds per-subscriber queues — the very machinery pull gives you for free |
| Overload feedback | TCP couples its sending rate to loss (cwnd shrink); retry budgets couple app retries to system state | Retries *violate* the demand-propagation premise: a failed unit of work re-enters as a fresh arrival; without a budget the system converts partial failure into multiplied load (see [../failure-casebook/github-october-2018.md](../failure-casebook/github-october-2018.md)) |

## A Concrete Worked Example

**Unbounded queue vs bounded, with numbers.** A service has 8 worker threads; each request needs one downstream call of W = 50 ms. Little's Law caps throughput at L/W = 8/0.05 = **160 req/s**. Traffic arrives at 300 req/s with an unbounded queue. Queue growth: 300 − 160 = 140 req/s; after 60 s the queue holds 8,400 requests; the wait a *new* request experiences is L/λ = 8,400/300 = **28 s**; memory held ≈ 8,400 × 50 KB of request context ≈ 420 MB and climbing. The service looks "alive" while delivering 28-second responses — classic bufferbloat. Fix with a bounded queue of 100: the queue fills in 100/140 ≈ 0.7 s, after which ~140 req/s must be shed (~47%); served traffic keeps p99 ≈ queue/W ≈ 100/160 ≈ 0.6 s worst case, and clients get explicit, fast failures instead of 28 s timeouts. Fix with scale-out: to pass 300 req/s at W = 50 ms you need L = λW = 15 requests in flight — 15 workers *or* batch downstream calls (5 requests per call ⇒ W_effective ≈ 50 ms at 60 calls/s ⇒ 8 workers suffice). The three fixes — bound+shed, add L, cut W — are the whole decision space; Little's Law sizes each.

**TCP's credit cap, with numbers.** Receiver advertises rwnd = 64 KB on a 40 ms RTT path. Maximum throughput = window/RTT = 64 KB / 0.04 s = **1.6 MB/s no matter how fast the sender is**. A sender upgrading its NIC sees nothing; only the receiver's advertised window (or cwnd growth) moves the cap. This is the cleanest demonstration that downstream demand, not upstream capacity, sets flow — the same arithmetic that sizes Reactive Streams prefetch (request 64 elements per credit cycle at 1 ms processing each ⇒ 64-element bursts, ~15 credit exchanges/s at 1,000 elements/s).

**Kafka lag arithmetic.** Partition in-rate 2,000 msg/s, one consumer processing 1,000 msg/s ⇒ lag grows 1,000 msg/s (L = λ_in − λ_out). Current lag 50,000 messages: with consumers scaled to out-rate 4,000 msg/s, drain time = 50,000/(4,000 − 2,000) = 25 s. Parallelism ceiling = partition count (12 partitions ⇒ at most 12 effective consumers) — so if 12 consumers can't reach 2,000 msg/s, the *partition count* is the backpressure bottleneck, not consumer count. Pull makes all four numbers directly measurable; push makes you instrument them yourself.

## When This Connection Is Useful

- **Problem-solving heuristics.** For any pipeline, compute the four numbers — λ_in, λ_out, L, W — at each stage; the stage where λ_in > L_max/W is your failure point, and the options are always {bound and shed, add L (scale out), cut W (batch/cache/parallelize)}. Choose queue vs shed by comparing spike duration to drain time (drain = L_current/(λ_out − λ_in)). Choose pull vs push by asking who should own the pacing and whether lag visibility matters.
- **Interview answers.** "Your service OOMs during traffic spikes — design a fix": lead with Little's Law sizing, then bounded queue + shedding + client backoff, and mention that unbounded queues move the failure from "fast, visible" to "slow, mysterious." "Why does Kafka scale better than push brokers for slow consumers?" — pull isolates consumer pace; lag is the queue made observable. "What does backpressure mean in async/reactive code?" — `request(n)` credit semantics, and why unbounded `flatMap` prefetch is the same bug as an unbounded queue.
- **Engineering decisions.** Give every queue an explicit capacity and every full-queue behavior (block/drop/caller-runs) an owner; expose lag/queue depth as first-class metrics (they are L); ship retry budgets and circuit breakers with every retry path; prefer protocols with native credit (rwnd, `request(n)`) at boundaries you don't control.

## Interview Questions

1. A pool of 12 workers serves requests needing 40 ms of downstream work. What is the maximum sustainable request rate, and what happens at 400 req/s with (a) an unbounded queue and (b) a bounded queue of 50? Give numbers for queue growth and added latency in both cases.
2. Explain how TCP's rwnd and Reactive Streams' `request(n)` are the same mechanism. Which overload problem does each *not* solve, and what additional mechanism covers the gap?
3. Why is "just make the queue unbounded and alert on depth" the worst of both worlds? Use bufferbloat arithmetic (growth rate, added latency, memory) to make the case.
4. One of 30 downstream calls in a fan-out is slow. Compare the behavior of naive async fan-out, per-downstream bounded concurrency, and hedged requests — which propagates demand upstream, and what couples the slow leaf to the other leaves?
5. During a dependency outage, your service's outbound retries triple its normal call volume. Explain the amplification with Little's Law, then design the retry budget and circuit-breaker policy that caps total offered load at, say, 120% of normal.

## Key Takeaways

- Backpressure is one mechanism in many uniforms: blocking bounded queues, TCP rwnd, Reactive Streams credits, Kafka pull — all make L grow only with downstream consent.
- Little's Law is the quantitative glue: throughput cap = L/W; queue growth = λ_in − λ_out; added latency ≈ L/λ_in. Compute, don't guess.
- Unbounded queues convert overload into bufferbloat — latency and memory explode while the system looks alive; bounded queue + shedding converts it into explicit, fast failure with bounded damage.
- The clean story breaks at fan-out (demand aggregation is unimplemented in most stacks), at push-broadcast (slowest subscriber governs), and at retries (failed work re-enters as fresh demand — budget it or be amplified).
- Pull architectures (Kafka) buy isolation and observable lag for free; push architectures must re-implement credits and per-subscriber queues or inherit the slowest consumer's pace.

## Cross-References

- [../../interview/system-design/backpressure.md](../../interview/system-design/backpressure.md) — Backpressure (System Design) — the design-interview framing of the same problem.
- [../../concurrency/producer-consumer.md](../../concurrency/producer-consumer.md) — Producer-Consumer — bounded queues and blocking semantics at the thread level.
- [../../concurrency/concurrent-queues.md](../../concurrency/concurrent-queues.md) — Concurrent Queues — the data-structure machinery underneath.
- [../../networks/tcp/flow-control.md](../../networks/tcp/flow-control.md) — TCP Flow Control — the credit window in its native form.
- [../../distributed/messaging/kafka.md](../../distributed/messaging/kafka.md) — Apache Kafka — consumer groups, fetch sizing, lag as an observable queue.
- [../../queueing-theory/mm1-queue.md](../../queueing-theory/mm1-queue.md) — The M/M/1 Queue and Little's Law — the derivations this page applies.
- [./scheduling-queueing.md](./scheduling-queueing.md) — OS Scheduling and Queueing Theory — utilization cliffs and discipline choice.
- [./virtual-memory-caching.md](./virtual-memory-caching.md) — Virtual Memory and Caching — thrashing as the memory-side twin of queue overload.
- [../followup-tree/rate-limiter-design.md](../followup-tree/rate-limiter-design.md) — Rate Limiter Design — ingress rate limiting algorithms and escalation chains.
- [../../interview/system-design/rate-limiter.md](../../interview/system-design/rate-limiter.md) — Rate Limiter (System Design) — token buckets in design interviews.
- [../failure-casebook/github-october-2018.md](../failure-casebook/github-october-2018.md) — GitHub October 2018 — retry/queue amplification as a named incident.
- Kafka consumer docs: <https://kafka.apache.org/documentation/>; Reactive Streams specification: <https://github.com/reactive-streams/reactive-streams-jvm>.
