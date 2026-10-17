# Network and Distributed-Systems Assumptions: The Lies We Tell the LAN

## Overview

Distributed code is written on one machine and run on many, and every step of that translation smuggles in assumptions that were true on the development laptop: the network is up, responses arrive quickly, in order, once; clocks agree; a timeout means the peer died; retrying is harmless. These are not careless mistakes — they are the default conclusions of any single-machine intuition, which is why Peter Deutsch's fallacies have outlived every technology generation that laughed at them.

This chapter audits the load-bearing assumptions with the collection's five-step pattern, and closes with the Eight Fallacies as the historical summary of exactly this list. Where an incident illustrates an assumption, the chapter links to the casebook rather than retelling it.

## Assumption 1: "The LAN Is Reliable and Fast — and Localhost Is Production"

### The taught rule

Service-to-service calls on the same network are effectively reliable local calls; the test suite passes on localhost.

### The hidden assumptions

- Packet loss, retransmissions, GC pauses, and router buffers do not exist in the test environment — so the code has no paths for them.
- Latency is uniform: localhost round trips are microseconds; even a clean cross-AZ call adds milliseconds, and a congested one adds tail latencies measured in hundreds of milliseconds (the [tail latency](../../distributed/fundamentals/tail-latency.md) chapter covers why the tail, not the mean, dominates user experience).
- Bandwidth and connection limits do not apply. Connection pools sized on localhost behavior meet production connection storms.
- Failure is binary. Real networks fail *partially*: some requests, some directions, some connections — which is harder to detect than total failure.

### Counterexample

A microservice calls a dependency twice per request; on localhost each call takes 0.3 ms and nobody measured. In production the dependency's p99 is 150 ms; with fan-out, a user-facing endpoint whose "logic" is trivial spends seconds at the tail. During a dependency brownout, TCP retransmission stalls turn "slow" into "hung" for some connections only — the health check passes while half the requests fail. The fix is not better hardware: timeouts, retries with backoff and jitter, circuit breakers ([bulkheads](../../sre/bulkheads.md)), and latency budgets per hop.

### What changes when the assumption is removed

Corrected statement: *every remote call has a latency distribution and a failure distribution; production engineering means specifying budgets for both (timeouts, deadlines, retry policy) and testing against degraded-network conditions, not against localhost.* Traffic-shaping tools (`tc`/netem, proxies like Toxiproxy) exist to make "the network is sometimes awful" a reproducible test input.

### Consequences

"Your service is slow but healthy — what do you check first?" is the standard incident interview; the strong answers start with tail latencies and fan-out arithmetic, not CPU.

## Assumption 2: "The Network Delivers in Order"

### The taught rule

Messages arrive in the order they were sent.

### The hidden assumptions

- TCP's ordering guarantee is per-connection and applies to the *byte stream it hands your application*: the protocol retransmits and resequences to hide network reordering. The network layer itself reorders routinely (route changes, link failover, multi-queue NICs); TCP pays to repair that, with retransmission latency when it happens.
- Multiple connections have no ordering relationship. A client sharding requests over eight parallel TCP connections (or an anycast setup landing on different servers) can have response 1 land after response 8 — each connection is ordered, the ensemble is not.
- UDP (RFC 768) provides no ordering and no retransmission at all; QUIC provides ordering per stream, with streams independent of each other.

### Counterexample

An event pipeline fans updates out over a pool of persistent connections to save connection-setup cost, and the consumer assumes "sent first, applied first". Two updates to the same record — delete, then create — traverse different connections; the consumer applies create, then delete, and the record vanishes. Every individual connection delivered its own bytes in order; the cross-connection ordering assumption failed. The fix is application-level sequencing (per-record version or sequence numbers, with reorder buffering or last-write-wins by version), not transport tuning.

### What changes when the assumption is removed

Corrected statement: *ordering is a per-connection (TCP) or per-stream (QUIC) transport property, and any system that shards traffic across connections, processes, or paths owns ordering explicitly — via sequence numbers, versions, or a single ordered channel per logical stream.*

### Consequences

Interview questions of the form "TCP guarantees delivery and order — why do I need sequence numbers in my protocol?" are exactly this distinction: the guarantee is scoped, and the scoping is the lesson.

## Assumption 3: "Remote Calls Are Basically Free" (Zero-Latency Thinking)

### The taught rule

Compose functionality by calling services; a call is like a function call with a network in between.

### The hidden assumptions

- A remote call holds resources while waiting: a thread, a connection, a slot in a pool. Synchronous fan-out multiplies the hold time.
- The N+1 pattern: one call per item turns a page of 50 items into 50 sequential round trips — latency adds, throughput divides.
- Chatty designs pay serialization, deserialization, and connection churn per call, invisible in a profiler that only sees your process.

### Counterexample

An endpoint that renders an order detail calls the customer service, then per line item calls the pricing service — 51 sequential calls at a 5 ms floor each is 255 ms before any logic runs. Batching the pricing call (one request with 50 keys) yields one 8 ms round trip. Same asymptotic work; two orders of magnitude from call granularity alone — the distributed version of the constants-vs-big-O lesson from [complexity claims](complexity-claims.md).

### What changes when the assumption is removed

Corrected statement: *remote calls are resource-holding operations with fixed per-call costs; design interfaces batch-first, parallelize independent calls with a shared deadline, and budget latency per hop so the caller's timeout is always the sum of its children's.*

### Consequences

"Optimize this endpoint that's slow in production" interviews are usually N+1 questions in costume; the [latency numbers](../../interview/system-design/latency-numbers.md) reference gives the per-call floors to do the arithmetic out loud.

## Assumption 4: "Clocks Are Synchronized"

### The taught rule

Timestamps order events; `time.now()` is "the" time.

### The hidden assumptions

- Physical clocks drift; NTP (RFC 5905) corrects them over the network — with its own uncertainty, and with different policies (slew small offsets, step large ones) that can make time visibly jump or run fast/slow.
- Leap seconds make civil time non-monotonic. During the 2016-2017 transition, Cloudflare's RRDNS hit a documented failure: the leap second made clocks step backward, a negative duration fed a signature TTL computation, and resolvers received negative TTLs — the engineering write-up ("How and why the leap second affected Cloudflare DNS") is the primary account, and it credits Go's subsequently introduced monotonic clock as the fix.
- Ordering by wall clock across machines is unsound in general: causality is a logical property (Lamport clocks, vector clocks — see the [Lamport clocks](../../distributed/fundamentals/lamport.md) and [vector clocks](../../distributed/fundamentals/vector-clocks.md) pages), and databases that promise external consistency need bounded-uncertainty APIs like TrueTime (the [TrueTime](../../distributed/fundamentals/truetime.md) page covers the design).

### Counterexample

Two data centers each process an order at nearly the same moment for the same customer with a per-region uniqueness rule implemented as "check the log timestamp, reject if one exists within a second". Clock A is 300 ms ahead (an NTP correction in progress); both orders look out-of-window locally and both commit. Wall-clock comparisons across machines produced a contradiction that logical clocks (or a transactional uniqueness constraint) would have prevented.

### What changes when the assumption is removed

Corrected statement: *treat wall clocks as inputs with error bars, not oracles: order events by causal/logical clocks, derive time-bound guarantees only from APIs that expose uncertainty (TrueTime-style commit waits), use monotonic clocks for measuring durations, and never compute a TTL or deadline as a difference of two machines' wall clocks.*

### Consequences

"Design an ordering guarantee for events from multiple regions" is a staple system-design prompt, and it exists because the wall-clock assumption fails at every scale from leap seconds to NTP corrections.

## Assumption 5: "Failure Detectors Are Accurate" (A Timeout Means "Down")

### The taught rule

If a node does not answer within the timeout, it failed; remove it and reassign its work.

### The hidden assumptions

- A timeout is *suspicion*, not fact: a slow node is indistinguishable from a dead one. Declaring it dead while it still acts is how you get two nodes believing they own the same work.
- In an asynchronous system, a *perfect* failure detector is impossible — this is the FLP impossibility result (the [FLP](../../distributed/fundamentals/flp.md) page covers the theorem); real systems use imperfect detectors with tunable accuracy/completeness (phi-accrual detectors, SWIM's suspicion mechanism — see [failure detectors](../../distributed/fundamentals/failure-detectors.md) and [SWIM](../../distributed/fundamentals/swim-membership.md)).
- Acting on suspicion needs safety rails: fencing tokens (monotonically increasing tickets that let storage reject stale owners) are the standard defense — the [fencing tokens](../../distributed/fundamentals/fencing-tokens.md) page details the pattern.

### Counterexample

A lease-based job scheduler times out worker W1 (GC pause of 20 seconds) and hands the shard to W2. W1 wakes up, believes it still holds the lease (its clock-based check passes), and writes to the shard. Two writers, no fault in either: the assumption "timeout implies stopped" manufactured a split brain. With fencing, W1's old ticket number is rejected by the storage layer at write time.

### What changes when the assumption is removed

Corrected statement: *treat timeouts as probabilistic suspicion that triggers *safe* action — reassignment *with* fencing, not just reassignment; distinguish "unresponsive" from "dead" in both code and runbooks, and size detection from the workload's actual latency distribution (GC pauses, not just network).*

### Consequences

Leader-lease and lock questions in interviews are fencing-token questions underneath; candidates who say "the lease expired so the old holder stops" get the GC-pause follow-up every time.

## Assumption 6: "Retrying Is Safe"

### The taught rule

The call timed out or errored — retry. Retrying improves availability and is harmless.

### The hidden assumptions

- The first attempt may have *succeeded*: a response lost after the server committed means a retry repeats a side effect — double charge, double send, double insert. Timeouts mean "unknown outcome" (see [concurrency and scheduling](concurrency-and-scheduling.md), Assumption 8).
- Retries multiply load precisely when the system is least able to bear it: an outage plus a 3x retry rate plus no backoff is a self-amplifying storm — the retry storm that turns degradation into collapse.
- Retried requests interleave with fresh ones: without jitter, synchronized retries arrive in waves (thundering herd in time), and without deduplication, at-least-once delivery surfaces as duplicates everywhere downstream.

### Counterexample

A payment endpoint experiences a 5-second network blip. Every in-flight client times out at 5 s and retries immediately; the retry wave doubles the request rate exactly as the dependency recovers, pushing it back down; the cycle repeats with increasing amplitude. Separately, the 2% of payment requests whose first attempt *did* commit before the blip are now charged twice — the two classic consequences of one missing design element: idempotency keys (client-generated tokens the server deduplicates) and retries with exponential backoff plus jitter.

### What changes when the assumption is removed

Corrected statement: *retrying is safe exactly when the operation is idempotent (or deduplicated by idempotency key) and the retry policy is capped, backed off, and jittered — otherwise retries convert partial failure into duplicated side effects and amplified outages.* Exactly-once *effects* are built from at-least-once attempts plus deduplication, never from wishing delivery semantics better.

### Consequences

"Make this payment API retry-safe" is one of the most common interview questions with a production basis, and the expected answer has two halves — idempotency for correctness, backoff/jitter for stability.

## The Eight Fallacies: The Historical Summary

Peter Deutsch's list — compiled at Sun in the 1990s, with the eighth added by James Gosling — is the ancestor of every section above, and it remains verifiable at [nighthacks.com/jag/res/Fallacies.html](https://nighthacks.com/jag/res/Fallacies.html):

1. The network is reliable. (Assumption 1)
2. Latency is zero. (Assumption 1, 3)
3. Bandwidth is infinite. (Assumption 3)
4. The network is secure. (beyond this chapter's scope — see the repo's security tracks)
5. Topology doesn't change. (Assumption 2's route changes)
6. There isn't an administrator. (operational reality of Assumption 1)
7. Transport cost is zero. (Assumption 3's per-call floors)
8. The network is homogeneous. (Assumption 2's mixed transports — TCP, UDP, QUIC)

The list has survived because each fallacy is the *default* assumption of code that works. The method of this chapter — name the assumption, break it, restate the corrected rule — is the systematic way to stop falling for them.

## Interview Questions

1. **TCP guarantees order and delivery. Why does your event consumer still need sequence numbers?** TCP's ordering is per-connection and applies to the byte stream it delivers; traffic sharded across multiple connections (or UDP/QUIC paths) has no cross-connection ordering. Application-level versions/sequences restore the cross-connection order the transport never promised.
2. **A client times out after 5 seconds and retries. What are the two failure modes, and what fixes them?** The first attempt may have committed (duplicate side effect — fixed by idempotency keys/deduplication), and synchronized retries amplify load (fixed by exponential backoff with jitter and retry caps). A timeout means unknown outcome, not failure.
3. **Why can't you order events by their timestamps across data centers?** Wall clocks drift and step (NTP corrections, leap seconds — Cloudflare's 2017 DNS incident is the documented example), so timestamp order is not causal order. Use logical/causal clocks for ordering, monotonic clocks for durations, and uncertainty-aware APIs when wall-clock guarantees are required.
4. **A worker's lease expired during a GC pause and it wakes up still holding state. What went wrong and what is the standard defense?** The timeout was treated as ground truth about the worker's state (assumption: failure detectors are accurate; FLP says they cannot be). The defense is fencing tokens: monotonically increasing leases checked by the storage layer, so the stale owner's writes are rejected.
5. **An endpoint makes 50 sequential microservice calls. Name the assumption and three fixes.** The assumption is zero-cost remote calls. Fixes: batch the calls (one call with all keys), parallelize independent calls under a shared deadline, and cache or denormalize to remove calls entirely; the underlying principle is that remote calls hold resources for their full latency.

## Key Takeaways

- Every remote call has a latency and failure *distribution*; localhost hides both, and production engineering is budgeting for both.
- Transport ordering is scoped (per-connection, per-stream); anything sharded across connections or paths owns ordering explicitly with sequence numbers or versions.
- Remote calls are resource-holding and floor-priced: batch first, fan out under deadlines, and do latency arithmetic per hop.
- Wall clocks are inputs with error bars; order by causality, measure with monotonic clocks, and quote leap-second history when someone proposes cross-machine timestamp comparisons.
- Timeouts are suspicion, not fact — pair reassignment with fencing, and retries with idempotency plus backoff and jitter.
- The Eight Fallacies are the compressed, thirty-year-old version of this chapter; they remain the fastest checklist for auditing any distributed design.

## Cross-References

- [TCP fundamentals](../../networks/tcp/README.md) and [TCP vs UDP](../../networks/udp/tcp-vs-udp.md) — the transport semantics behind Assumption 2.
- [Networking overview](../../networks/overview.md) and [distributed systems overview](../../distributed/overview.md) — the parent tracks.
- [Tail latency](../../distributed/fundamentals/tail-latency.md) — why the tail dominates fan-out designs.
- [Time in distributed systems](../../distributed/fundamentals/time.md), [TrueTime](../../distributed/fundamentals/truetime.md), [Lamport clocks](../../distributed/fundamentals/lamport.md) — the clock-assumption toolbox.
- [Failure detectors](../../distributed/fundamentals/failure-detectors.md), [FLP impossibility](../../distributed/fundamentals/flp.md), [fencing tokens](../../distributed/fundamentals/fencing-tokens.md) — the suspicion-and-safety toolkit for Assumption 5.
- [TCP and distributed failure atlas](../connection-atlas/tcp-distributed-failure.md) — how transport behavior maps to distributed failure modes.
- [Latency numbers reference](../../interview/system-design/latency-numbers.md) — the arithmetic for Assumption 3.
- [Cloudflare: how and why the leap second affected Cloudflare DNS](https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns) — primary account of the leap-second failure (verified).
- [The Eight Fallacies of Distributed Computing](https://nighthacks.com/jag/res/Fallacies.html) — Deutsch's list as hosted by Jon Callas (verified).
- [NTPv4, RFC 5905](https://www.rfc-editor.org/rfc/rfc5905.html) — primary source for clock synchronization behavior (verified).
- [UDP, RFC 768](https://www.rfc-editor.org/rfc/rfc768.txt) — primary source for UDP's connectionless, unordered semantics (verified).
