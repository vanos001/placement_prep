# TCP and Distributed Systems: Failure Detection in Miniature

## Overview

TCP is not a "reliable pipe" abstraction to be taken for granted — it is a small, single-pair distributed system that solves, with 1970s constraints, several problems distributed systems still struggle with: "Is the peer alive?" (timeouts as failure detectors), "Should I resend?" (retransmission as retry), "How long should I wait?" (exponential backoff), "What if the response was lost but the operation happened?" (sequence-number dedup as idempotency), and "Don't overwhelm the receiver" (flow control as backpressure). Reading TCP *as a distributed system* explains why application-level distributed protocols keep reinventing its mechanisms — and, more importantly, where those mechanisms stop transferring because TCP's world model (one peer, eventual connectivity, no adversary) is too kind.

## The Two Sides, Independently

**TCP's failure machinery.** TCP estimates path latency continuously (RFC 6298): on each acknowledged segment, SRTT ← (7/8)·SRTT + (1/8)·RTT and RTTVAR ← (3/4)·RTTVAR + (1/4)·|SRTT − RTT_sample|; the retransmission timeout is RTO = SRTT + 4·RTTVAR (minimum 1 s initially). A segment un-ACKed past the RTO is retransmitted and the RTO doubles each consecutive loss (exponential backoff; Karn's algorithm excludes retransmitted segments from RTT sampling so ambiguity doesn't poison the estimator). Loss can also be repaired *without* waiting: three duplicate ACKs trigger fast retransmit. At the receiver, sequence numbers plus cumulative ACKs provide **duplicate suppression**: a retransmitted segment that was actually received (its ACK got lost) is recognized by sequence range and discarded while the ACK is re-sent — the data appears exactly once to the application. Receiver flow control (rwnd) caps unacknowledged bytes in flight.

**Distributed systems' failure machinery.** In a group of machines, "is node X alive?" has no ground truth available to any single observer: a missing heartbeat can mean crash, GC pause, network partition, or congestion. Failure detectors (per [../../distributed/fundamentals/failure-detectors.md](../../distributed/fundamentals/failure-detectors.md)) are specified by *completeness* (eventually suspect every dead process) and *accuracy* (limit false suspicions), with the strong conclusion (the FLP result) that perfect detection is impossible in asynchronous systems — so practice uses timeouts tuned from heartbeat inter-arrival statistics (the φ-accrual detector computes φ = −log₁₀ P(elapsed-silence | normal operation) and acts on thresholds of φ, e.g., 12 ≈ one-in-a-trillion false positive under the fitted distribution). Retries at the application layer need **idempotency keys**: the client attaches a unique key to the operation; the server records the key with its response and replays the stored response on retry. Leases and fencing tokens guard against acting on stale suspicion. All of this is TCP's machinery re-built in a world with N peers and no shared clock.

## The Shared Principle

**Both systems construct a failure detector from latency statistics, and both make retries safe only by explicit duplicate suppression.** A timeout is a statistical estimate of unobservable state ("no ACK in SRTT + 4·RTTVAR ⇒ probably lost"); an idempotency key is the application-layer descendant of the sequence number ("this request was already executed; here is the recorded response"). The second principle is shared too: **both couple retry pressure to feedback** — TCP's RTO doubling and congestion window shrink when loss rises; sane application retry policies use exponential backoff with jitter and retry budgets. The mechanism transfer is real and precise, not metaphorical.

## Where the Analogy HOLDS and BREAKS

| Mechanism | HOLDS (TCP ↔ distributed) | BREAKS (why distributed systems need more) |
|---|---|---|
| Timeout as failure detector | Both estimate "probably lost" from latency statistics | TCP never has to *conclude* the peer is dead — it may retry indefinitely and costs nothing but a socket; a leader-election detector must act (promote a successor), so false positives cause split brain, and accuracy needs φ-accrual, not a single RTO formula |
| Retransmission ↔ retry with backoff | Identical curve: RTO doubling ≈ exponential backoff + jitter; both avoid amplifying overload | TCP couples loss to *its own* load (congestion control) within one protocol; application retries have no built-in coupling — retry storms need explicit budgets/circuit breakers (see [../failure-casebook/github-october-2018.md](../failure-casebook/github-october-2018.md)) |
| Duplicate suppression ↔ idempotency | Same shape: sender re-sends, receiver dedups by key and replays the answer | TCP's dedup state is per-connection, in-memory, and both peers know it atomically; idempotency stores must survive server crashes, failovers, and replica races — and responses can outlive the key's TTL, forcing "unknown result" semantics TCP never faces |
| Flow control ↔ backpressure | rwnd is a credit window; consumer-driven demand works at both scales | One TCP peer's window is one number; a service with 10⁴ clients has *aggregated* backpressure plus fan-out and slow-consumer pathologies (see [./backpressure.md](./backpressure.md)) |
| Trust model | TCP's only adversary is noise: a 16-bit checksum plus sequence numbers suffice | Distributed systems face buggy or malicious nodes (Byzantine-ish ambiguity): a node may *claim* liveness, so liveness claims need quorums and fencing — concepts TCP cannot even express |

The deepest break is **partial failure**. TCP has exactly two endpoints: either the connection delivers, or it visibly dies — there is no state where "the left half of the connection works." Distributed systems live permanently in between: node A hears node B fine, node C cannot hear B at all, and B may be *slow rather than dead* — a distinction no local observation can settle (the "crashed vs slow" ambiguity). TCP's world model ("eventual connectivity to one peer") makes its machinery simple; distributed systems pay for generality with impossibility results, quorums, and ambiguity-tolerant designs.

## A Concrete Worked Example

**Timeout arithmetic, and the classic bug.** A client talks to a service over a path with RTT samples centered at 40 ms, spread ±10 ms. Steady state: SRTT = 40 ms, RTTVAR ≈ 10 ms, so TCP's RTO ≈ 40 + 4·10 = 80 ms; after each RTO-triggered loss the backoff doubles: 80 → 160 → 320 → 640 → 1280 → 2560 ms — five consecutive losses cost ~4.9 s before the sixth attempt. Now the application bug this exposes: the same client sets a 100 ms request timeout "to be snappy." During a transient congestion episode (a real 300 ms delay spike), TCP would have recovered inside its RTO dynamics — but the app *aborts at 100 ms*, opens a retry, adds load, and the retry storm amplifies the episode. The rule the numbers teach: **application timeouts below the transport's own recovery timescale convert transport recovery into application-incited load.** The fix is layering discipline: app timeout ≥ path RTO under stress, plus jittered backoff and a retry budget (e.g., stop retrying when retries exceed 10% of live traffic).

**Idempotency by sequence number, made concrete.** Client POSTs "charge card #42, $100" with `Idempotency-Key: k-7f3a`. The response is lost after the server executed it. TCP's ancestor: the receiver that already got bytes re-ACKs and discards a retransmission. Application version: the server stored `(k-7f3a → response)`; the retry (same key) replays the stored response — the card is charged once. Without the key, the retry is a second $100 charge: at-least-once delivery without dedup is a money bug. Note the distributed-only wrinkle: if the server crashed after executing but before persisting `k-7f3a`, no amount of TCP-style machinery saves you — that is why idempotency storage is itself a durability design decision (persist before executing, or accept "unknown" and reconcile).

## When This Connection Is Useful

- **Problem-solving heuristics.** Any retry design question decomposes into TCP's five questions: what is my RTT estimate (so timeouts adapt), what is my backoff (doubling + jitter), what is my dedup key (idempotency or the operation must be naturally idempotent), what is my window (concurrency cap), and what feedback couples my retries to system load (retry budgets, circuit breakers). If any answer is "none," you have found the next outage.
- **Interview answers.** "How do you know a server is down?" — the strong answer is *you cannot, exactly*; you maintain a statistical detector and bound its false-positive cost with fencing/quorums, exactly as TCP bounds its false loss-detection with RTO + 4σ but without TCP's luxury of a single peer. "Why exponential backoff and why jitter?" — RTO doubling prevents synchronized retry waves; jitter desynchronizes colliding clients. Walking from TCP's mechanisms to their distributed descendants makes the answer feel derived rather than memorized.
- **Engineering decisions.** Never set application timeouts below the transport's recovery envelope; prefer idempotency keys over "retry-safe by design" when the operation has side effects; treat failure detection thresholds as *accuracy* parameters (φ-accrual or missed-heartbeat counts with measured loss rates) and pair every detection with a fencing mechanism, because a detector good enough to fail over is also good enough to double-promote.

## Interview Questions

1. Derive TCP's RTO from SRTT and RTTVAR and explain why retransmitted segments are excluded from RTT sampling (Karn's algorithm). What distributed-systems failure detector has the same estimation problem?
2. Explain how TCP's sequence numbers make retransmission safe, then design the application-layer equivalent for a payment API. Where does the equivalence stop — name two things the idempotency store must handle that the TCP receiver's buffer does not.
3. Why is "crashed vs slow" undecidable in an asynchronous distributed system but a non-issue inside a TCP connection? Frame your answer in terms of partial failure and who bears the cost of waiting.
4. A service calls a dependency with a 100 ms timeout over a 40 ms-RTT path. During congestion the dependency recovers in ~300 ms. Describe the failure loop that follows and quantify how backoff changes the offered load after five failed rounds.
5. Compare a fixed 3-missed-heartbeats failure detector with a φ-accrual detector. Under 1% independent heartbeat loss, what is the false-suspicion probability of the fixed detector, and why does that calculation fail under a partition?

## Key Takeaways

- TCP is a working distributed system for two nodes: statistical failure detection (RTO from SRTT/RTTVAR), safe retries (backoff + dedup), and credit-based flow control.
- The transferable principles: timeouts are latency statistics, retries are safe only with duplicate suppression, and retry pressure must be coupled to load feedback.
- The transfer stops at partial failure, crash-vs-slow ambiguity, multi-peer state (idempotency stores across failovers), and adversarial behavior — each requiring quorums, leases, or fencing that TCP cannot express.
- Application timeouts below transport recovery timescales convert congestion into retry storms; the GitHub October 2018 incident is the canonical case to study.
- A failure detector's accuracy is a *cost parameter*: tune it like TCP tunes RTO, and always pair detection with fencing.

## Cross-References

- [../../networks/tcp/timers.md](../../networks/tcp/timers.md) — TCP Timers — RTO estimation and backoff mechanics.
- [../../networks/tcp/fast-retransmit.md](../../networks/tcp/fast-retransmit.md) — Fast Retransmit — loss recovery without waiting for the RTO.
- [../../networks/tcp/flow-control.md](../../networks/tcp/flow-control.md) — TCP Flow Control — the credit-window mechanism.
- [../../networks/tcp/congestion-control.md](../../networks/tcp/congestion-control.md) — TCP Congestion Control — the load-feedback loop application retries lack.
- [../../distributed/fundamentals/failure-detectors.md](../../distributed/fundamentals/failure-detectors.md) — Failure Detectors — completeness/accuracy and φ-accrual.
- [../../distributed/fundamentals/system-models.md](../../distributed/fundamentals/system-models.md) — System Models — synchrony assumptions behind "crashed vs slow."
- [../assumptions-hunt/network-distributed.md](../assumptions-hunt/network-distributed.md) — Network/Distributed Assumptions Hunt — the assumption audit this page deepens.
- [../failure-casebook/github-october-2018.md](../failure-casebook/github-october-2018.md) — GitHub October 2018 — retry and connection-pool dynamics under failover (named incident, primary-source timeline).
- [./backpressure.md](./backpressure.md) — Backpressure — the flow-control connection explored in full.
- RFC 9293 (TCP, obsoletes 793): <https://datatracker.ietf.org/doc/html/rfc9293>; RFC 6298 (RTO computation): <https://datatracker.ietf.org/doc/html/rfc6298>.
