# Distributed Lock Assumptions: What "Acquire a Lock and Proceed" Silently Promises

## Overview

A distributed lock is the most tempting primitive in system design: take the concept every programmer learned on threads, move it to Redis or ZooKeeper, and the mutual-exclusion problem looks solved. The gap between the single-machine and distributed versions is not implementation quality — it is physics. A local mutex never expires while its holder is alive; a distributed lock's lease can expire while its holder is alive and working. A local mutex cannot lie about identity; a distributed lock service can be partitioned so that two clients each hear "you hold it." And a local mutex is on the same failure domain as the code; a lock service is a separate system with its own availability, which means every use of it is a new dependency with a fail-open-or-closed decision attached.

This chapter audits the distributed-lock family with the collection's five-step pattern. The core argument — that an expiry-based lock without fencing tokens cannot guarantee exclusivity, worked through a GC-pause scenario — follows Martin Kleppmann's widely cited analysis, and the counter-position (Redlock's design rationale) is documented in Redis's own distributed-lock guide; both are linked so the disagreement can be read at the source. The lease mechanics reference Google's Chubby paper, whose distinction between locks for efficiency and locks for correctness is the most useful single sentence in this field. The GC-pause trigger comes from the concurrency chapter's assumption set, and the consensus machinery that underlies correct lock services belongs to the follow-up tree's Raft chain.

## Assumption 1: "An Acquired Lock Means Exclusivity"

### The taught rule

If `acquire()` returned success, no other client holds the lock, so the protected resource is exclusively mine.

### The hidden assumptions

- Exclusivity is only as fresh as the lock's expiry. If the lock is lease-based (all practical ones are, to bound crash-orphaned locks), the lease can expire while the holder is mid-operation — and the holder has usually already passed the "is it still mine?" check and is acting on the resource.
- The client's clock is not the lock service's clock: a client that computes remaining lease time locally can believe it holds a lock the server has already reassigned. Every implementation detail that touches two clocks widens this window.
- Exclusivity without fencing is a belief. A fencing token — a monotonically increasing number handed out at acquire time and checked by the resource itself (a conditional write, a version check, an ACL) — is the only mechanism that makes the resource itself reject a stale holder. Without it, the lock service's promise cannot reach the resource.
- The failure trigger is common, not exotic: a stop-the-world GC pause, a VM live migration, a network retry — any stall longer than the lease. The concurrency chapter treats "sleep durations and pauses are unpredictable" as its own assumption; the lock version is where that assumption costs data.

### Counterexample

The Kleppmann scenario, stated with numbers: client 1 acquires the lock with a 30-second lease and begins a write to storage that takes a granted-lease-plus-consideration path; at t = 30 s its runtime hits a 40-second GC pause; the lease expires and client 2 acquires the lock and begins its own write; client 1's pause ends at t = 40 s and, unaware anything happened, continues writing — both clients now write the same object, last writer wins, and one update is silently lost. The fix that survives this sequence is not a longer lease (pauses are unbounded) but a fencing token: the lock service increments a counter per grant, the storage layer rejects writes whose token is below the highest seen, so client 1's stale token fails its write even though the lock library believed everything was fine. Where the resource cannot check tokens (many cannot), the honest engineering statement is that the lock provides *efficiency* — avoiding duplicated work in the common case — not *correctness*, and the design must tolerate the overlap it claims to prevent.

### What changes when the assumption is removed

Corrected statement: *an acquired lock means "no one else held it as of my last check with the service"; exclusivity at the resource requires the resource to participate — via fencing tokens, conditional writes, or idempotent operations — and otherwise the lock is an efficiency optimization whose failure mode must be survivable.* Design responses in order: make the protected operation idempotent (then overlap costs nothing), add a token check at the resource (then stale holders fail loudly), and only then use the lock for scheduling convenience.

### Consequences

The interview probe "two clients both believe they hold the lock — how?" is the sharpest opening in distributed-systems interviews, and the strong answer runs the GC-pause timeline and lands on fencing. The Redlock debate (Kleppmann's critique versus Redis's documentation) is the follow-up escalation, and its resolution in practice is the efficiency-versus-correctness distinction from the Chubby paper rather than either side "winning."

## Assumption 2: "The Lock TTL Covers My Work"

### The taught rule

Set the lock's time-to-live comfortably above the job's expected duration and the lease will outlive the work.

### The hidden assumptions

- "Expected duration" is the wrong statistic: the lease must exceed the *maximum* duration, and the maximum of a long-tail operation is unbounded in exactly the environments (GC, hypervisor stalls, network partitions, oversized inputs) that make the lock necessary. Using p99 to size a TTL means one in a hundred runs outruns its own protection.
- Renewal exists precisely because fixed TTLs are wrong, but the renewal loop is itself a distributed component: it can be delayed by the same pauses, stopped by a paused runtime, or silently broken by an auth-token expiry — and a holder whose renewal fails but who never notices is the same bug as Assumption 1 with extra steps.
- Clock skew between client and server converts a correctly sized TTL into a shorter effective one, and lease arithmetic done in wall-clock time inherits every problem the clocks chapter catalogs (steps, slew, zone confusion is rare here but monotonicity assumptions are not).
- The recovery question is usually unasked: after a holder loses its lease (expired, revoked, renewal failed) and later *notices*, what may it still do? Chubby's lease semantics give the answer's shape — the holder must stop issuing new operations on the resource and revalidate before continuing; code that "finishes up" after lease loss is unprotected work.

### Counterexample

A migration runner takes a lock with a 10-minute TTL. The migration includes a backfill whose worst case is 25 minutes on a large shard (the team sized the TTL from the test environment's 4-minute run). At minute 10, the lease lapses; a cron-triggered second instance acquires the lock and starts the same migration on the same schema; at minute 12 the two runners execute conflicting DDL, one blocks on the other's table lock, and the migration ends in a half-applied state that needs manual repair during peak traffic. The fixes are layered: a renewal (watchdog) thread extending the lease while the work is alive and healthy; a progress heartbeat that distinguishes "slow but alive" from "stuck"; a hard work budget with abort-on-expiry (the job checks its own remaining lease at every step boundary and stops cleanly when it is gone); and lease-aware idempotency so a re-run from the new holder resumes rather than repeats. The zero-downtime-migrations chapter's expand-contract discipline is what makes "stop and resume" possible at all.

### What changes when the assumption is removed

Corrected statement: *no fixed TTL covers unbounded work; the lease must be renewed by a component that can fail, so the job must check lease health at operation boundaries, stop on loss, and be idempotent enough to resume under a new holder.* The design checklist: renewal with monitored failures, lease-aware step boundaries, an explicit post-loss behavior (abort, re-acquire, hand off), and work structured so the next holder can pick up where the last one verifiably stopped.

### Consequences

The interview probe "your job outlives the lock TTL — what actually happens?" is the practical version of Assumption 1, and the differentiating answer names the renewal watchdog's own failure modes rather than "we set a big TTL." The consensus-leases chapter develops the same lease arithmetic at infrastructure level, and the background-jobs ladder borrows these mechanics for job exclusivity.

## Assumption 3: "The Lock Service Is Always Reachable"

### The taught rule

The lock service (Redis, ZooKeeper, etcd) is highly available, so `acquire()` and `release()` will work when needed.

### The hidden assumptions

- "Highly available" means the service survives partitions internally; it does not mean *your client* can reach it. During the exact incident that makes locking important, the lock service may be unreachable — and the code path for "cannot acquire/release" is usually a barely tested exception handler.
- The fail-open-or-closed decision is forced and usually implicit: if you cannot reach the lock service, do you proceed without the lock (fail open: risk duplicate work at the worst time) or block (fail closed: convert a lock-service outage into a work stoppage)? Most codebases fail open by accident and fail closed by résumé.
- Release is the subtle casualty: a client that loses the service mid-critical-section cannot release, so the lock's fate depends on TTL expiry alone — which couples this assumption to the TTL arithmetic of Assumption 2 and delays everyone who queued behind a holder that is gone.
- Quorum-based services (etcd, ZooKeeper) refuse writes during their own leadership transitions; Redis-as-lock loses locks on failover where replication is asynchronous. The service's own consistency mode silently defines how often "acquired" was never exclusive — the consensus-raft chain explains why those transitions exist.

### Counterexample

A payment reconciliation job holds a lock from a ZooKeeper-based service. A network maintenance window partitions the job host from the ensemble for 90 seconds. The session expires (ZooKeeper's own lease, unrelated to the job's TTL), a second instance — running in another zone, reachable — acquires the lock and starts. When the partition heals, the first instance's session is gone, but its process is alive and its code's error path on "session expired" was `log.warning` and continue — the fail-open-by-accident default. Two reconcilers run for the remaining hour; duplicate payments are generated for 40 accounts and reversed manually over two days. The post-incident fix set: session-expiry is a *stop* signal wired to the same code path as lease loss (Assumption 2's boundary checks), the fail-open-or-closed decision is written per job with its blast radius, and the resource gains an idempotency key so a duplicate run is a no-op instead of an incident.

### What changes when the assumption is removed

Corrected statement: *the lock service's reachability is a probability, and every lock user must define behavior for each of acquire-fail, hold-loss, and release-fail; correctness-critical paths need the resource itself to reject duplicates rather than trusting the lock service's liveness.* Design responses: explicit fail-open/closed policy per use, session-loss wired to the stop path, idempotent operations as the belt to the lock's suspenders, and monitoring on lock-service reachability *from the clients' vantage point*, not the service's.

### Consequences

The interview probe "your lock service is down — what happens to the system?" has a three-part answer (fail open, fail closed, or stop-and-resume, each chosen per job) and a strong finish: the reason fencing and idempotency exist is precisely that the lock service's availability and the exclusivity guarantee are independent properties. The Chubby paper's efficiency-versus-correctness line is the design compass for the whole assumption.

## Interview Questions

1. **Two clients both believe they hold the lock. Walk me through the timeline.** Client 1 acquires with a lease; a GC pause or stall exceeds it; the service grants to client 2; client 1 resumes unaware. Fix: fencing tokens checked by the resource, or accept the lock as an efficiency tool and make overlap survivable.
2. **Why is sizing the lock TTL above the p99 job duration insufficient?** The tail is unbounded in the environments that make locking necessary; renewal (watchdog) with monitored failures, lease-aware step boundaries, and resume-capable idempotent work are the durable answer.
3. **Your client loses its lock-service session mid-job. What is the correct behavior?** Stop issuing new operations on the resource, revalidate before continuing (Chubby's lease discipline), and treat "finish up anyway" as unprotected work — most incidents in this family are a log-and-continue default.
4. **Fail open or fail closed when the lock service is unreachable?** It is a per-job decision with a blast radius: fail open risks duplicate work during incidents; fail closed couples your availability to the lock service. Either must be written down, and correctness-critical paths should not depend on the choice because the resource itself rejects duplicates.
5. **What does a fencing token add that the lock cannot?** A monotonically increasing grant number the *resource* checks, so a stale holder's operations fail at the storage layer regardless of what the lock library believes — it closes the gap between the lock service's view and the resource's.

## Key Takeaways

- A lease-based lock guarantees exclusivity only as of the last successful check; expiry during work plus a pause produces two holders, and fencing tokens at the resource are the only closure of that gap.
- No fixed TTL covers unbounded work: renewal loops, lease-aware step boundaries, and idempotent resumable work are the system, and the TTL is just its slowest component.
- The lock service's reachability is a separate property from its correctness; every user must explicitly choose fail-open or fail-closed and wire session loss to a stop path.
- Chubby's distinction is the design compass: locks for efficiency tolerate overlap because it is cheap; locks for correctness require the resource to participate via tokens or conditional writes.
- The detection artifact is overlap itself: log grant/renewal/expiry events per lock and alert on concurrent-holder detections, because a system that never observes its double-holds will keep producing silent lost updates.

## Cross-References

- [Concurrency and scheduling](concurrency-and-scheduling.md) — the pauses and scheduling surprises that trigger lease expiry during work.
- [Clocks and time](clocks-and-time.md) — the clock-skew assumptions lease arithmetic inherits.
- [Timeouts and retries](timeouts-and-retries.md) — the retry-and-expiry interplay at request timescale, sibling to lease timescale.
- [Consensus and leases](../connection-atlas/consensus-leases.md) — lease mechanics at infrastructure level, the atlas view of this chapter's core.
- [Consensus and Raft escalation chain](../followup-tree/consensus-raft.md) — why lock services have leadership transitions and quorum refusals.
- [Mutex to lock-free escalation chain](../followup-tree/mutex-to-lock-free.md) — the single-machine locking concepts the distributed versions borrow and betray.
- [Transactions and concurrency control](../connection-atlas/transactions-concurrency-control.md) — conditional writes and version checks, the resource-side machinery fencing tokens use.
- [Martin Kleppmann: How to do distributed locking](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html) — the fencing-token argument and the GC-pause scenario at full length.
- [Redis: Distributed locks with Redlock](https://redis.io/docs/latest/develop/use/patterns/distributed-locks/) — the implementation-side design rationale, the counter-position.
- [The Chubby lock service for loosely-coupled distributed systems](https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/) — the efficiency-versus-correctness distinction and lease semantics, from the source.
