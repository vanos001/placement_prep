# OS Scheduling and Queueing Theory: The Same Waiting Line

## Overview

An operating-system scheduler and a load-balanced web service are the same mathematical object: jobs arrive, wait in a queue, receive service from one or more servers, and leave. The OS chapter teaches mechanisms (round robin, multilevel feedback, CFS vruntime); the queueing-theory chapter teaches laws (Kendall notation, Little's Law, the utilization cliff). Put side by side they answer each other's missing half — queueing theory predicts *what a scheduling discipline will cost before you deploy it*, and OS scheduling shows *which mechanisms implement each discipline*.

This page explains both sides independently, verifies the one law that binds them (Little's Law, L = λW) rather than reciting it, and is precise about where the queueing models stop predicting real systems — heavy tails and burstiness being the two biggest liars.

## The Two Sides, Independently

**OS schedulers.** FCFS runs jobs in arrival order — trivially fair in time-order, terrible for latency mix (see worked example below). Round Robin adds a quantum q, cycling through jobs so no job waits longer than (n−1)q for its first slice; q too small → context-switch overhead dominates, q too large → FCFS again. Priority scheduling risks starving low priorities, fixed by aging (priority rises with wait time). Multilevel feedback queues approximate SJF without foresight: new jobs start high, sink if they run long, so interactive jobs (short bursts) stay high — a *learned* discipline. Linux CFS keeps per-task virtual runtime scaled by weight (nice value) and always runs the task with the least vruntime — a work-conserving implementation of fair queueing. All of these are **queue disciplines**: policies for which waiting job to serve next.

**Queueing theory.** Kendall notation A/S/c describes a system by arrival process / service-time distribution / server count: M/M/1 = Poisson arrivals, exponential service, one server; M/G/1 = arbitrary ("general") service. The stability condition is λ < c·μ, i.e., utilization ρ = λ/(cμ) < 1. For M/M/1 with μ = 100 jobs/s the mean time in system is W = 1/(μ−λ):

| λ (jobs/s) | ρ = λ/μ | W = 1/(μ−λ) | vs 10 ms service time |
|---|---|---|---|
| 50 | 0.50 | 20 ms | 2× |
| 80 | 0.80 | 50 ms | 5× |
| 90 | 0.90 | 100 ms | 10× |
| 99 | 0.99 | 1,000 ms | 100× |

That table is the utilization cliff: **mean delay roughly doubles for every ~10% of utilization near saturation**, and it is not a modeling artifact — it is the arithmetic of sharing. Queue discipline interacts with variance: FCFS's mean wait equals that of any work-conserving discipline (M/G/1 with FCFS: W_q = λE[S²]/(2(1−ρ))), but SRPT (shortest remaining processing time) provably minimizes mean wait when it can see job sizes — which is exactly the information an OS MLFQ tries to infer.

**CoDel, where the two meet.** The CoDel AQM (RFC 8289) is queueing theory shipped in a router: it ignores queue *length* and tracks queue *sojourn time* — the quantity queueing theory says users feel. If the minimum sojourn time over an interval (100 ms window) exceeds the target (5 ms), packets are dropped/marked with increasing frequency until the standing queue drains. It is MLFQ's philosophy generalized to network buffers: control the delay, not the occupancy.

## The Shared Principle

**A scheduler is a queue discipline, and both fields study the same object: a service system whose delay is a function of utilization, service-time variance, and discipline.** Little's Law is the invariant that connects the two vocabularies — it needs no Poisson assumptions, which is why it transfers from OS run queues to web backends unchanged.

**Verifying L = λW rather than reciting it.** Claim: for any stable system, L = λW with L = average number in system, λ = average arrival rate, W = average time in system. Proof by area: measure over a long window T. Total area under the N(t) (number in system) curve is ∫N(t)dt = sum over jobs of their residence time (each job contributes 1 to the count for exactly its residence time W_i). So ∫N dt = Σ W_i. Divide both sides by T: left side = L (time-average of N). Right side: (Σ W_i)/T = (N_T · W̄)/T where N_T jobs arrived in T, N_T/T = λ and W̄ = W. Hence L = λW. (Little 1961 formalized the limits and conditions; the area argument is the intuition.) **Numeric check:** 90 req/s arrive, each spending 100 ms in the system → L = 9 × ... precisely 90 × 0.1 = 9 requests in system on average — matching the M/M/1 row above (ρ = 0.9, L = ρ/(1−ρ) = 9 — a match). Two independent derivations agree; the formula is verified, not assumed.

## Where the Analogy HOLDS and BREAKS

| Aspect | HOLDS | BREAKS |
|---|---|---|
| Little's Law L = λW | Universal — any stable system, any distribution: run queues, thread pools, HTTP queues, disk queues | Requires stability (λ bounded and < capacity) and long-run averages; transient bursts and p99 are outside its jurisdiction |
| Utilization → latency cliff | Any shared server with variance shows the same shape (M/G/1: W_q ∝ 1/(1−ρ)) | Real arrivals are bursty (C_v > 1) and correlated, moving the cliff *left*; the M/M/1 table is then optimistic, not pessimistic |
| FCFS vs priority/fair disciplines | OS aging ≈ fair queueing's guarantees; MLFQ ≈ SRPT approximation; CoDel ≈ delay-based admission | OS schedulers are work-conserving and never drop work; AQMs *drop*; application load-shedders *reject* — three different failure policies the "discipline" abstraction hides |
| Stability condition ρ < 1 | Same overload death everywhere: queue → ∞ | Distributed systems add correlated failure and cascade: one slow node redirects load, raising λ elsewhere — the model's independence assumption fails exactly when it matters |

The variance term deserves naming because it is the most interview-valuable piece: by Pollaczek–Khinchine (M/G/1), W_q = (ρ/(μ(1−ρ))) · (1+C_s²)/2, where C_s² is the squared coefficient of variation of service time. Deterministic service (C_s = 0) halves the wait versus exponential (C_s = 1); a heavy-tailed service (C_s² = 9) makes waits 5× worse *at the same mean utilization*. "Average load is fine, p99 exploded" is this formula speaking.

## A Concrete Worked Example

**Head-of-line blocking, with numbers.** One CPU (or one worker thread), FCFS. Jobs: 99% are 1 ms, 1% are 100 ms. Mean service E[S] = 0.99·1 + 0.01·100 = 1.99 ms. An arriving job's expected wait *for the in-service job alone* is the mean residual life E[S²]/(2E[S]) = (0.99·1 + 0.01·10,000)/(2·1.99) = 100.99/3.98 ≈ **25 ms** — thirteen times the *mean* service time, produced by the 1% of long jobs. This is why a single slow request on a connection or in a thread pool inflates everyone's tail, why HTTP/2 multiplexing over one TCP stream still suffers HOL at the TCP layer, and why MLFQ/SRPT (serve short jobs first) is worth its complexity: reordering cannot change utilization but can change the variance penalty dramatically.

**Sizing with Little's Law.** A worker pool does downstream calls of W = 50 ms. With 8 workers, maximum sustainable throughput is λ = L/W = 8/0.05 = 160 req/s — *not* "CPU-bound, so 8 cores ⇒ lots of headroom." If traffic is 300 req/s and the pool is the bottleneck, L must grow: to pass 300 req/s at 50 ms you need L = 15 in flight — either 15 workers or a queue, and a queue of depth d adds d·W... more precisely adds d/λ_extra seconds of delay: 300-deep queue at 300 req/s adds 1 s to every request. This same arithmetic sizes thread pools, DB connection pools, and consumer concurrency — one law, applied three times.

## When This Connection Is Useful

- **Problem-solving heuristics.** Any latency incident: measure λ, W, L, ρ. If ρ > 0.7–0.8 with C_s > 1, the cliff explains p99 before you profile anything. Then choose the fix in discipline terms: reduce λ (admission control), reduce W (faster/batched service), reduce variance (timeouts, jittered retries, breaking HOL), or change discipline (SRPT-ish, fair queueing across tenants). CoDel's insight generalizes: instrument *sojourn time*, not queue length.
- **Interview answers.** "Why does latency explode near 100% CPU?" — the 1/(1−ρ) curve plus the variance term, with the ρ→W table reproduced on the whiteboard. "Why does one slow request hurt everyone?" — mean residual life arithmetic. "How many workers does this service need?" — Little's Law, not vibes. Candidates who verify L = λW with the area argument instead of reciting it are instantly credible.
- **Engineering decisions.** Leave headroom (target ρ ≤ 0.7 for latency-critical services; the table shows why 0.9 is already 10×). Prefer many small queues over one shared FCFS queue when job sizes are bimodal (per-endpoint pools, bulkhead). Use queue *depth* alarms only as capacity proxies; alarm on sojourn time. Know that autoscaling by CPU lags the cliff — autoscale by λ or latency.

## Interview Questions

1. State Kendall notation and classify: Nginx with keep-alive connections, a disk array, a call center. What breaks in each classification?
2. Prove L = λW using the area argument, then apply it: a service holds 4,000 requests in flight at 2,000 req/s. What is the mean end-to-end time, and how much of it is queueing if the service itself needs 150 ms of work?
3. Explain head-of-line blocking with the residual-life formula, and say why HTTP/2's stream multiplexing moved the HOL problem rather than eliminating it.
4. Your service's p99 degrades at 70% CPU while p50 is flat. Give a complete queueing-theoretic explanation, including the role of C_s², and two concrete mitigations with their expected effects.
5. Compare CoDel's approach (drop based on sojourn time) with FCFS plus a huge buffer (bufferbloat). Why does "add memory to the queue" make latency worse without changing throughput?

## Key Takeaways

- OS scheduling and queueing theory study the same object; disciplines (FCFS, RR, MLFQ, CFS, CoDel, SRPT) are policy points on one map, and queueing theory prices each point.
- Little's Law L = λW is distribution-free and verified here by area argument; it sizes thread pools, connection pools, and consumer concurrency identically.
- The utilization cliff is arithmetic, not anecdote: at μ=100/s, W goes 20 ms → 100 ms → 1 s as ρ goes 0.5 → 0.9 → 0.99.
- Service-time variance (C_s²) enters through Pollaczek–Khinchine; heavy tails and HOL blocking are variance phenomena, curable by discipline choice (SRPT/MLFQ, per-class queues), not by faster hardware alone.
- Models break at burstiness, heavy tails, correlation, and closed-loop feedback — treat M/M/1 numbers as best-case until you have measured your arrival C_v.

## Cross-References

- [../../queueing-theory/fundamentals.md](../../queueing-theory/fundamentals.md) — Queueing Theory Fundamentals — Kendall notation, M/M/c, and model breakdowns in full.
- [../../queueing-theory/mm1-queue.md](../../queueing-theory/mm1-queue.md) — The M/M/1 Queue and Little's Law — derivations this page compresses.
- [../../queueing-theory/applied-systems.md](../../queueing-theory/applied-systems.md) — Applied Queueing Systems — call centers, Erlang models, capacity planning.
- [../../os/scheduling/linux-cfs.md](../../os/scheduling/linux-cfs.md) — Linux CFS — vruntime fair queueing implementation.
- [../../os/scheduling/multilevel-feedback.md](../../os/scheduling/multilevel-feedback.md) — Multilevel Feedback Queues — the SRPT-approximation discipline.
- [../../os/scheduling/fcfs.md](../../os/scheduling/fcfs.md) — FCFS Scheduling — the discipline whose HOL cost we computed.
- [../../distributed/fundamentals/tail-latency.md](../../distributed/fundamentals/tail-latency.md) — Tail Latency — what p99 means when servers are replicated.
- [../../cloud/noisy-neighbors.md](../../cloud/noisy-neighbors.md) — Noisy Neighbors — multi-tenant fair queueing and its violations.
- [./backpressure.md](./backpressure.md) — Backpressure — Little's Law as the load-management tool.
- CoDel: RFC 8289, <https://datatracker.ietf.org/doc/html/rfc8289> — the AQM specification (target 5 ms, interval 100 ms).
- Little, J. D. C., "A Proof for the Queuing Formula: L = λW," *Operations Research* 9(3), 1961 — the original statement and conditions.
