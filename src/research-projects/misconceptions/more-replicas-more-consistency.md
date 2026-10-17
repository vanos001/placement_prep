# "More replicas = more reliable and more consistent"

## Overview

This page examines the claim that adding replicas is a free win on both
reliability and consistency. The two halves have opposite signs. Replicas
do improve durability and read availability. Under asynchronous replication
— the default at scale — each additional replica *widens* the stale-read
window, so the consistency half runs backwards.
And the quorum arithmetic people reach for, R+W>N, is necessary but nowhere
near sufficient for linearizability.

## The Claim, Stated Fairly

The strongest common form of the claim is: "Every replica we add makes the
system more reliable *and* more consistent: more copies of the data means
more machines agree on the answer, so reads get safer too." Stated this
way, the claim is not a caricature; it is the reasoning in many capacity
reviews ("add a replica, that fixes both the load and the correctness
complaints").

The first conjunct is real and the second is true in one regime: with
*synchronous* replicas and quorum reads, more in-sync copies do strengthen
durability and read consistency. The question is whether that regime
honestly compresses to "more replicas".

## Verdict

**False.** The claim is a conjunction, and its second conjunct inverts under
async replication: replicas added for capacity lag the primary, the
stale-read window widens with every copy, and observed consistency
*degrades* from the always-fresh single-node baseline. The quorum formula
R+W>N does not rescue it without version ordering, durable state, and
failure handling that "just add replicas" never includes.

## Why People Believe It

The kernel of truth is threefold. Durability genuinely improves: three
copies on independent hardware survive failures that two do not, and read
availability widens with each healthy replica. The mental model comes from
synchronous mirroring — RAID-1, a hot standby — where the replica is
always current, so "more copies" and "more agreement" arrived together.
And in quorum-configured systems, replicas *within one synchronous group*
can allow stricter read sets.

What disappears in compression is the word *synchronous*. Scale-out systems
add replicas specifically so they can absorb reads without participating in
every write commit — the definition of asynchronous replication. The new
replica's value is purchased with exactly the currency the claim says it
improves.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "More replicas = more reliable" | True for durability and read availability: more independent copies survive more failures |
| "More replicas = more consistent" | Inverted under async replication: each lagging replica is another source of stale reads |
| "Quorums fix it: R+W>N" | Intersection guarantees a read quorum overlaps a *completed* write quorum — necessary, not sufficient |
| "Consensus is optional" | Linearizable reads require ordered writes (consensus or equivalent); quorum overlap alone does not order concurrent writes |

The correct sentence: "More replicas buy durability and read capacity at
the price of wider staleness windows under async replication; strong
consistency is a property of the *replication protocol* (synchronous
quorums with ordered writes, or consensus), not of the replica count."

## Where It Breaks

**The lag arithmetic.** A primary takes 10,000 writes/s. A replica whose
replication stream runs 200 ms behind is missing 2,000 recent writes at any
moment; any read it serves can contradict an acknowledged write. Five
async replicas at lags of 50–500 ms create a system-wide stale-read window
equal to the *union* of their lags, and load-balanced reads sample that
lottery on every request. Against the always-fresh single-node baseline,
observed consistency dropped. Geography makes it structural: light in
fiber covers ~4,000 km in ~20 ms, so a cross-region replica's lag has a
floor near one WAN round trip (reasoning arithmetic, not a measurement).

**Quorum intersection is not linearizability — counterexample one: ordering.**
Setup: N=3 replicas A, B, C; W=2, R=2 (2+2>3 holds). Versions are the local
wall-clock stamp of the first replica that applies each write — the
no-single-leader case quorum configs allow. Replica A's clock is correct;
B and C run 6 s behind (common real-world drift). Write
w1 completes on {A,B} at real time t=100; A stamps it 100. Write w2
completes on {B,C} at real time t=102; B stamps it 96. A read at t=104
touches {A,B} and takes the max version: 100 beats 96, so it returns w1 —
a value superseded, before the read began, by a completed write. Every
ingredient of the folk theorem held: R+W>N, read quorums, max-version
reads. What was missing is a *total order on writes that respects real
time* — which is why Spanner couples quorums with TrueTime bounds and
CockroachDB uses hybrid logical clocks with uncertainty windows.

**Counterexample two: durability of the quorum itself.** Write v1 is
acknowledged on {A,B}. Replica A crashes and reverts to its pre-write state
(a flush that never reached platters, or a failover that promoted a lagging
standby). Replica C never received v1. A read quorum {A,C} now returns v0 —
an *acknowledged write has vanished*, with every quorum formula satisfied.
R+W>N is a statement about set overlap, not about whether the overlapping
copies still hold the data.

**Counterexample three: quorums that move.** Sloppy quorums with hinted
handoff — Dynamo's mechanism for keeping W satisfied during partitions —
abandon the fixed-set intersection on purpose: the read quorum may
intersect *the set that would have been written*, not the set that
actually was. The paper frames the result as eventual consistency; an
honest design choice, and the opposite of the claim.

**The missing ingredient for concurrency.** Concurrent writes need
coordination even beyond ordering of completed writes: the classical
quorum register (Attiya, Bar-Noy, and Dolev, 1995) is linearizable because
its read *writes back* the highest version observed — plain "read R copies,
return the max" does not carry the guarantee. Read-repair is load-bearing,
not hygiene.

## Practical Implications

- Separate the two goals in capacity planning: replicas buy durability and
  read fan-out; the replication *protocol* buys consistency.
- Match mode to guarantee: synchronous quorum writes (or consensus) where
  reads must be linearizable; async with session guarantees (sticky
  routing, version checks) where UX needs per-user coherence.
- Treat replication lag as an SLO: monitor per-replica lag, alert on the
  tail, and cap replica count by the staleness budget the product can
  tolerate.
- For quorum deployments, verify the full recipe: R+W>N *plus* real-time
  ordered versions *plus* durable writes *plus* read-repair — miss any one
  and the formula is decorative.
- Multi-region: the WAN round trip is the write-latency floor, and far
  replicas widen both the lag floor and the blast radius.

## Interview Questions

### Does adding read replicas make a system more consistent?

No — under async replication it makes observed answers *less* consistent:
each replica adds its own lag window (a primary at 10k writes/s with a
replica 200 ms behind is missing 2,000 recent writes), and load-balanced
reads sample every replica's lottery. Replicas improve durability and read
availability; consistency is set by the replication protocol, not the copy
count.

### We use N=3, W=2, R=2. Why can a client still read a stale value after a completed write?

Because intersection guarantees overlap with a completed write's *quorum
set*, not correctness of what the overlap returns. Three concrete failure
modes: versions stamped by skewed clocks can order writes backwards (max
returns the older write); a quorum member that reverts after a crash can
resurrect pre-write state; and sloppy quorums break fixed-set intersection
by design. Linearizability needs ordered versions, durable state, and
read-repair — or consensus.

### Users complain "my change disappeared" at 1% rates on a sharded, replicated store. Where do you look first?

Async staleness first: which read path served the read, did the write
complete, and is the user's next read routed to a different replica
(missing session guarantees like read-your-writes)? Then the durability
cases: quorum writes without durable flushes, failover promoting a lagging
standby. Fixes follow the diagnosis — session guarantees, lag-aware
routing, durable quorum writes — not "more replicas".

## Key Takeaways

- Replicas improve durability and read availability; under async
  replication each copy widens the stale-read window, so the consistency
  conjunct inverts.
- R+W>N is a set-intersection condition, necessary and far from
  sufficient: ordering (clock skew), durability (the reverted quorum), and
  fixed sets (sloppy quorums) each break it alone.
- A linearizable read requires an ordered write history and read-repair —
  the quorum-register result (ABD 1995) — protocol machinery, not replica
  arithmetic.
- Lag windows grow with replica count and geography; light-in-fiber floors
  make multi-region staleness structural.
- The honest sentence: "more copies, more durability; the protocol decides
  consistency" — systems that conflate the two buy capacity and call it
  correctness.

## Cross-References

- [Why-Not Handbook: Replication Modes](../why-not-handbook/replication-modes.md)
  — sync vs async vs semi-sync as a decision
- [Connection Atlas: Consensus & Leases](../connection-atlas/consensus-leases.md)
  — the protocol machinery that orders writes
- [Consistency and Availability under Partition](./consistency-availability-partition.md)
  — the CAP backbone beneath this arithmetic
- [Quorum Replication](../../distributed/replication/quorum.md) — R+W>N
  mechanics
- [Primary-Backup Replication](../../distributed/replication/primary-backup.md)
  — the async pipeline this page prices
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- D. K. Gifford. *Weighted Voting for Replicated Data*. SOSP 1979 — the
  origin of quorum intersection conditions.
- H. Attiya, A. Bar-Noy, and D. Dolev. *Sharing Memory Robustly in
  Message-Passing Systems*. Journal of the ACM, 1995 — the quorum
  read/write register whose read-write-back step carries linearizability.
- G. DeCandia et al. *Dynamo: Amazon's Highly Available Key-value Store*.
  SOSP 2007 — sloppy quorums, hinted handoff, eventual consistency.
- L. Lamport. *Time, Clocks, and the Ordering of Events in a Distributed
  System*. Communications of the ACM, 1978 — why clocks do not order
  writes without additional machinery, cited by title.
