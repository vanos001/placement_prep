# Consensus, Leases, and Fencing: Agreeing on Who Holds the Lock

## Overview

Three mechanisms answer the question "who may act on this resource right now?" under failure: consensus (Paxos/Raft) agrees on a single value — often "client X holds the lock, epoch 33"; leases make that answer expire so a vanished holder cannot freeze the system forever; fencing tokens make stale holders *provably rejectable* at the resource itself. They are commonly treated as a menu (use Raft, or use a lock service, or use leases), but they are actually layers of one design: consensus provides a linearizable registry of who holds what; a lease bounds how long the registry's answer can be acted on; fencing closes the residual gap — the window in which a paused or slow client still believes an answer that is no longer true.

This page builds that stack bottom-up, walks the classic failure step by step — client 1 freezes, the lease expires, client 2 is granted the lock, client 1 wakes up and writes anyway — and shows precisely where fencing turns corruption into a rejected write. It also states the punchline most lock-library documentation omits: consensus gives you linearizable *registration*, not mutual *exclusion*; exclusion happens at the resource, or it does not happen.

## The Concepts, Independently

**Consensus (Paxos/Raft).** The agreement problem: n processes, some of which crash, must agree on one value — or, in the replicated-log form, on a sequence of values. Raft organizes this as leader election plus log replication: a leader is elected by a majority, appends commands to its log, replicates them, and commits an entry once a majority stores it; committed entries are applied in log order and are safe against any minority failure ([../../distributed/consensus/raft.md](../../distributed/consensus/raft.md), [../../distributed/consensus/paxos.md](../../distributed/consensus/paxos.md), [../../distributed/consensus/README.md](../../distributed/consensus/README.md)). Two properties matter here. *Safety* does not depend on timing: no assumption about clock drift or message delay can cause two leaders to commit conflicting values for the same term. *Liveness* does: in a fully asynchronous system with one crash failure, no deterministic algorithm guarantees termination (FLP impossibility — see [../../distributed/fundamentals/flp.md](../../distributed/fundamentals/flp.md)), so real protocols use timeouts and randomness purely to make progress. Consensus is what etcd, ZooKeeper, and Chubby sell underneath their friendlier APIs ([../../distributed/systems/etcd-internals.md](../../distributed/systems/etcd-internals.md), [../../distributed/systems/chubby-and-consul.md](../../distributed/systems/chubby-and-consul.md)).

**Distributed locks and leases.** A lock service serializes access to a shared resource across processes: acquire, hold, release. A **lease** is a lock with a time bound: the grant expires after T unless renewed, so a crashed or partitioned holder cannot hold the resource indefinitely ([../../distributed/fundamentals/distributed-locks.md](../../distributed/fundamentals/distributed-locks.md), [../../distributed/advanced/leases.md](../../distributed/advanced/leases.md)). The lease primitive (Gray & Cheriton, SOSP 1989) was introduced for file-cache consistency — the same time-bounded-grant idea now used for leader election, task ownership, and job scheduling. Leases are built *on* consensus: ZooKeeper grants come with session timeouts maintained by the Zab-ordered log; etcd leases are objects in the Raft-replicated state machine with TTLs.

**Fencing tokens.** A fencing token is a monotonically increasing number issued with each lock/lease grant — epoch 33, then epoch 34, and so on ([../../distributed/fundamentals/fencing-tokens.md](../../distributed/fundamentals/fencing-tokens.md)). The resource (the storage node, the database, the file store) records the highest token it has seen and rejects writes bearing lower tokens. The token converts the otherwise undetectable condition "I *believe* I hold the lock" into a checkable fact at the point where damage would occur. Note what the token requires: monotonic issuance must be linearizable (consensus again), and the *resource* must cooperate by checking tokens — fencing moves the correctness check to where the data lives.

## The Shared Principle

**Agreeing on a single holder under partial failure requires three separable mechanisms: a linearizable registry of grants (consensus), a time bound on acting on a grant (lease), and a monotonic check at the resource (fencing).** Each mechanism covers the failure the previous one cannot: consensus handles crashes and network splits for the *registry*; the lease handles a holder that dies or detaches; fencing handles a holder that is merely *slow or paused* — alive, believing, and wrong. The lease's expiry is, in turn, an application of bounded-time assumptions: safety holds only if a paused client's pause is shorter than the lease, which is a real-world probability, not a guarantee (see [../../distributed/fundamentals/time.md](../../distributed/fundamentals/time.md) on clocks and [./gc-memory-management.md](./gc-memory-management.md), where leases reappear as the distributed analog of liveness approximation).

The reason this stack is non-negotiable is that **the lock service and the resource are different machines.** Consensus makes the lock *service* correct: at most one client holds the grant at any instant, and every client can find out who. But no protocol run by the lock service can stop a client from *acting* on stale knowledge — the resource is where the write lands, so the resource must be where the final check happens.

## Where the Analogy HOLDS and BREAKS

| Property | HOLDS | BREAKS |
|---|---|---|
| Single holder, at most, at any instant | Consensus guarantees the *registry* never records two simultaneous grants (one leader per term, one lock owner per epoch) | Registration is not exclusion: a paused client can act on an expired grant, because the resource does not consult the registry per write |
| Leases terminate stuck holders | Crashed holders' grants expire in bounded time; progress resumes | The bound is a timing assumption: GC pauses, VM freezes, or clock skew longer than the lease violate it — and leases *do* fail under exactly the conditions consensus was built to survive |
| Fencing rejects stale writers | Monotonic token + resource-side check makes stale writes provably rejected | Requires cooperation: filesystems, databases, and APIs that ignore tokens leave fencing unenforceable; monotonic tokens need a linearizable issuer |
| One mechanism suffices | — | Never: consensus alone does not stop stale actors; leases alone are consensus-with-a-clock-assumption; fencing alone has nothing to fence without a grant protocol. The stack is the design |
| Locks ≈ transactions | Both serialize access | Locks give no rollback: a fenced write is rejected after partial work may have happened; holding locks across network calls adds deadlock and liveness hazards that transactions manage explicitly |

The break worth internalizing: **Raft's leader is a lease you did not have to design.** A Raft leader stays leader only while followers' election timeouts do not fire — roughly a lease of a few hundred milliseconds, renewed by heartbeats. Raft's safety does not depend on that timing (a deposed leader cannot commit), which is exactly the property a raw lease lacks. When someone says "we use leases, not consensus," the correct follow-up is: whose log issues your epoch numbers?

## A Concrete Worked Example

**The frozen client, step by step.** Setting: storage node S accepts writes and checks fencing tokens; lock service L is a Raft-backed key-value store; lease T = 5 s; two clients C1 and C2.

```text
t=0    C1 acquires lock on object X from L. Grant: token 33.
t=1    C1 starts a 10 s GC pause (large heap, full GC).
t=5    Lease expires. L (correctly) grants the lock to C2. Grant: token 34.
t=6    C2 reads X=old, computes, writes X=2 to S. S records max token seen = 34.
t=11   C1 wakes. Its in-memory state still says "I hold the lock on X."
       C1 writes X=1 (computed from the stale pre-C2 read) to S.
       - Without fencing: S accepts. X is now 1 — C2's committed update lost.
         Two clients "held the same lock"; the data is corrupted.
       - With fencing: C1's write carries token 33. S has seen 34; 33 < 34 →
         rejected. Corruption becomes a rejected request with a clear error.
```

Six steps, no exotic failure: a 10-second GC pause against a 5-second lease is a default-JVM-scale accident, not a black swan. The fencing fix works because it changes *who checks*: C1's belief is unfalsifiable from C1's side (its clock, its pause, its view of the lease are all its own), but the token is a fact at S, the machine that matters. Two design notes follow from the example. First, fencing moves the invariant to the storage layer — so storage must cooperate; if S is a third-party API with no token support, you must implement the check above it (e.g., compare-and-set on a version column). Second, token issuance must be monotonic *and linearizable* — two concurrently granted epoch-34s would re-create the bug one level up; that monotonic counter is itself consensus work.

**Choosing lease durations with numbers.** Make the lease longer than worst-case pause + clock skew + one renewal round-trip. Renewals at 50 ms RTT with 200 ms jitter, skew ±100 ms, and a platform that can pause 10 s (JVM full GC on an 8 GB heap) make a 5 s lease misconfigured by construction. Either bound the pause (heap tuning, GC choice, cgroup CPU guarantees) or accept token enforcement at the resource. Kubernetes leader-election defaults sit around a 15 s lease for exactly this reason: long enough to ride over routine pauses, short enough to fail over in seconds. Raft's own numbers — election timeouts of hundreds of milliseconds — are safe only because deposed leaders cannot commit; a lease inherits that safety only if, like Raft, the *resource* independently refuses stale grants.

## When This Connection Is Useful

- **Design reviews.** Any "we'll just use a distributed lock" plan should be interrogated in stack order: Who runs the linearizable registry? What expires, and what pause bound does that imply? Does the resource check anything monotonic? If the third answer is no, the design accepts silent corruption as a tail-risk.
- **Interview answers.** "How do you prevent two cron schedulers from double-running jobs?" and "how do you elect a leader?" have the same senior-shaped answer: lease via a consensus-backed store (etcd/ZooKeeper), renew well inside the TTL, and — if the job writes to shared state — fence at the sink (version or epoch column). The escalation question "what if the client GC-pauses past the lease?" is answered by the token walk above, step by step.
- **Engineering decisions.** Prefer leases over blocking locks for failover (no manual cleanup of crashed holders); prefer fencing tokens over lease-duration paranoia for correctness; treat lock libraries that promise safety from lease length alone as unsafe. Double-check that your storage can enforce a monotonic check before designing the token scheme; otherwise, prefer idempotent operations over exclusion.

## Interview Questions

1. Build the frozen-client corruption scenario in five steps: what does each of C1, C2, the lock service, and the storage node know at each step, and where exactly does the first lie appear?
2. Explain why consensus gives linearizable registration but not mutual exclusion. What would the lock service have to do — and what would it still fail to do — to enforce exclusion from its side?
3. Raft deposes a leader on timeout, like a lease expiring. Why is Raft's safety unaffected by the timing while a plain lease's is? Name the mechanism inside Raft that plays the fencing-token role.
4. Your lease is 5 s, renewals take 50 ms, and the client platform pauses up to 10 s. Give two sound designs — one that changes the lease system, one that changes the resource — and the assumption each depends on.
5. Why must fencing-token issuance be linearizable? Sketch the failure with two concurrently issued equal tokens, and name the component that fixes it.

## Key Takeaways

- Consensus, leases, and fencing are three layers of one design: linearizable registry → time-bounded grant → monotonic check at the resource; each covers the failure the previous cannot.
- Consensus guarantees the registry is right; only the resource can guarantee stale actors fail. Exclusion happens at the data, or not at all.
- A lease is consensus plus a timing assumption: it fails when pauses, clock skew, or network delay outlast the bound — exactly the events consensus was designed to shrug off.
- Fencing tokens turn "I believe I hold the lock" into a checkable fact at the sink; they require a linearizable token issuer and a resource that cooperates.
- The frozen-client scenario (pause > lease → grant to C2 → C1 writes stale data) is the canonical interview story; being able to walk it step by step, then fix it with a token, demonstrates the whole stack.

## Cross-References

- [./gc-memory-management.md](./gc-memory-management.md) — GC and Memory Management — leases as the distributed analog of liveness approximation.
- [./tcp-distributed-failure.md](./tcp-distributed-failure.md) — TCP and Distributed Failure — timeouts as statistical failure detectors, the lease's underlying primitive.
- [../why-not-handbook/caching-distributed.md](../why-not-handbook/caching-distributed.md) — Caching vs Distributed Coordination — when to buy coordination and what it costs.
- [../followup-tree/rate-limiter-design.md](../followup-tree/rate-limiter-design.md) — Rate Limiter Design — hot keys, leases, and atomic grants in the limiter context.
- [../../distributed/consensus/raft.md](../../distributed/consensus/raft.md) — Raft — leader election, log replication, and term numbers as implicit fencing.
- [../../distributed/consensus/paxos.md](../../distributed/consensus/paxos.md) — Paxos — ballots and promises, the original fencing discipline.
- [../../distributed/fundamentals/distributed-locks.md](../../distributed/fundamentals/distributed-locks.md) — Distributed Locks — lock-service designs and their failure modes.
- [../../distributed/fundamentals/fencing-tokens.md](../../distributed/fundamentals/fencing-tokens.md) — Fencing Tokens — token schemes and resource-side enforcement.
- [../../distributed/advanced/leases.md](../../distributed/advanced/leases.md) — Leases — lease math, renewal, and clock assumptions.
- Ongaro, D. & Ousterhout, J., "In Search of an Understandable Consensus Algorithm," OSDI 2014 — <https://raft.github.io/raft.pdf>.
- Lamport, L., "The Part-Time Parliament," ACM TOCS 1998; "Paxos Made Simple," ACM SIGACT News 2001.
- Gray, C. & Cheriton, D., "Leases: An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency," SOSP 1989.
- Kleppmann, M., "How to do distributed locking," <https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html>.
- Kleppmann, M., *Designing Data-Intensive Applications*, ch. 8 (O'Reilly, 2017) — the fencing-token treatment this page follows.
