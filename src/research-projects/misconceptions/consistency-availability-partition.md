# "A distributed system can always provide consistency and availability during a partition"

## Overview

CAP is the most cited and most misquoted theorem in distributed systems. The
misquote — "you must pick two of three" — is wrong twice over: it treats C,
A, and P as freely chovable features, and it implies that picking C and P
means abandoning correctness while partitions are absent. This page gives
the precise statement (Brewer's 2000 conjecture, Gilbert and Lynch's 2002
proof), defines what C, A, and P formally mean, states what the theorem does
*not* say, and works the bank-ATM scenario where the tradeoff is forced.

## The Claim, Stated Fairly

The strongest common form: "Well-engineered systems give you both: strong
consistency *and* high availability, even when the network misbehaves.
Modern databases have mostly solved this." Stated fairly, this is not
naivety — it is the sincere hope of every product requirement document that
says "always available, always correct". It is also exactly the conjunction
that Gilbert and Lynch proved impossible to guarantee.

## Verdict

**False.** Gilbert–Lynch (2002) proved that no distributed system can
simultaneously guarantee consistency (linearizability) and availability
(every request eventually responds without error) when a network partition
occurs; during a partition, every system picks which one to sacrifice.

## Why People Believe It

The kernel of truth is real on both flanks. CP systems do provide consistency
and *usually* availability — partitions are rare, so a CP system can run for
years, visibly consistent and visibly available, and the theorem looks
refuted by experience. AP systems do provide availability and *useful*
consistency — eventually consistent replicas converge, and most reads most
of the time return current-enough data. "Modern databases" hedge in
sophisticated ways (quorums, leader leases, STONITH), so single-node
failures, which are far more common than partitions, never force the choice.

What experience cannot show is the theorem's content: a *guarantee* covering
the partition case. The claim "always" is about the tail regime that
engineering intuition — built from the non-partitioned 99.99% of time —
never observes.

## The Correct Formulation

Brewer conjectured the tradeoff in his 2000 PODC keynote; Gilbert and Lynch
formalized and proved it in 2002:

- **C (Consistency):** linearizability — every operation appears to take
  effect atomically at some instant between its invocation and response, on
  a single "logical" copy of the data (the linearizability model of Herlihy
  and Wing).
- **A (Availability):** every request received by a *non-failing* node
  eventually terminates with a (non-error) response.
- **P (Partition Tolerance):** the system tolerates the network dropping or
  arbitrarily delaying messages between nodes.

The theorem: a system that must tolerate partitions (P) cannot simultaneously
guarantee C and A — during a partition, the replicas cannot both accept
writes and answer reads consistently, because the messages needed to
coordinate cannot flow. The proof is a two-node argument: a write accepted at
one partitioned node cannot be seen by a read served at the other; either the
read must return stale data (C broken) or refuse/error (A broken).

**What the theorem does NOT say** — each negation is its own popular
misconception:

| Misreading | Reality |
|---|---|
| "Partitioned systems lose all correctness" | AP sacrifices *linearizability*, not every property: eventual and causal consistency remain well-defined and often sufficient |
| "CAP means drop C, keep AP, always" | The choice applies *during* partitions; the rest of the time a CP system is fully available |
| "P is optional" | P is not chovable — any distributed system spanning unreliable networks must tolerate partitions; the real choice is C vs A when one occurs |
| "CAP forbids strong consistency in the same system as availability" | Different operations can be treated differently (e.g., quorum reads/writes on critical paths, stale-allowed reads elsewhere) |
| "CAP covers latency" | It does not; PACELC extends it: if Partition, choose A or C; Else, choose latency or consistency |

## Where It Breaks

**The ATM partition, with numbers.** A bank keeps account balances replicated
at datacenters DC1 and DC2; the account holds 500. A partition severs the
link. A customer withdraws 400 at DC1; minutes later, another withdraws 400
at DC2. The system must pick:

- **Choose availability (AP):** DC2 accepts the second withdrawal. The account
  is now −300 across the partition. Both requests "succeeded"; consistency
  (linearizability of the balance) was sacrificed. The bank's business rule
  absorbed the loss — that is the engineering price of A, paid *by design*
  or paid by surprise.
- **Choose consistency (CP):** DC2 refuses (error: cannot verify balance).
  Availability was sacrificed — the non-failing node returned an error, which
  is precisely the letter of the theorem's A definition.

No third option exists *during the partition*; any response from DC2 either
contradicts DC1's write or admits it cannot guarantee the current balance.
That is Gilbert–Lynch in one paragraph, and it is why the claim "always both"
is false rather than merely unproven.

**The misquote's collateral damage.** "CAP says we must pick two, so we
picked C and A and dropped P" — this reading quietly assumes the network
never partitions, which no honest operations team believes. Systems built on
that reading meet their first real partition as an outage (or, worse, as
silent divergence) because the failure mode was designed away on paper
rather than handled in code.

## Practical Implications

- Decide per subsystem, not per company: payments can pay CP's availability
  price; likes and view-counts cannot, and AP with conflict resolution
  serves them well.
- For AP paths, choose the weaker guarantee deliberately — causal
  consistency, read-your-writes, or CRDTs with commutative merges — so "not
  linearizable" does not degrade into "not defined".
- For CP paths, use quorum reads and writes (R + W > N), leader leases with
  bounded staleness, and explicit "unavailable during partition" semantics
  in the SLA.
- Exercise partitions in testing (jepsen-style fault injection): the theorem
  is about guarantees, and guarantees that were never tested under partition
  are hopes.
- When no partition exists, the tradeoff is latency vs consistency (PACELC):
  even the happy path forces choices (sync replication adds latency; async
  replication adds staleness).

## Interview Questions

### State CAP precisely. What do C, A, and P actually mean?

C is linearizability (single-system-image atomicity), A is every request to a
non-failing node eventually responding without error, P is tolerating network
partitions. The theorem (Gilbert–Lynch 2002): under P, C and A cannot both be
guaranteed during a partition.

### Why is "CAP means you can only have two of three" wrong?

P is not optional for any real distributed system — the choice is only which
of C or A to sacrifice *when* a partition occurs, not whether partitions
happen. And the theorem says nothing about behavior outside partitions, nor
about which operations must make the same choice.

### Your leader-based database becomes read-only during a partition minority. Which side of CAP did it choose, and what did it sacrifice?

It chose consistency (CP): quorum-isolated leaders reject writes rather than
risk divergence. It sacrificed availability — non-failing nodes return errors
— which is exactly the theorem's A. Read-only minority behavior is the
concrete shape of that choice.

## Key Takeaways

- The precise impossibility: under partition tolerance, linearizable
  consistency and per-request availability cannot both be guaranteed —
  Gilbert and Lynch, 2002.
- C and A are formal properties (linearizability; non-error response), not
  vibes; the theorem's power comes from their precision.
- AP does not mean "incorrect": eventual and causal consistency are
  well-defined weaker guarantees chosen on purpose.
- PACELC completes the picture: no partition → latency vs consistency;
  partition → availability vs consistency.
- The theorem is a design tool, not a scoreboard: the engineering question
  is *which operations* pay the CP price, not *which systems* are exempt.

## Cross-References

- [Assumptions Hunt: Network and Distributed](../assumptions-hunt/network-distributed.md)
  — the reliable-network assumption this theorem limits
- [Connection Atlas: Transactions and Concurrency Control](../connection-atlas/transactions-concurrency-control.md)
  — the single-node consistency machinery CAP extends
- [Distributed Systems Overview](../../distributed/overview.md) — the
  broader landscape around this theorem
- [Consensus](../../distributed/consensus/README.md) — the machinery behind
  the CP choice
- [Consistency Tradeoffs](../../interview/system-design/hld/consistency-tradeoffs.md)
  — the applied version of the same decision
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- S. Gilbert, N. Lynch. *Brewer's Conjecture and the Feasibility of
  Consistent, Available, Partition-Tolerant Web Services*. ACM SIGACT News
  33(2), 2002, pp. 51–59.
  <https://dl.acm.org/doi/10.1145/564585.564601>
- E. Brewer. *Towards Robust Distributed Systems* — PODC 2000 keynote (the
  conjecture the above paper proved).
- D. J. Abadi. *Consistency Tradeoffs in Modern Distributed Database System
  Design: CAP is Only Part of the Truth*. IEEE Computer 45(2), 2012 (PACELC).
- M. Herlihy, J. Wing. *Linearizability: A Correctness Condition for
  Concurrent Objects*. ACM TOPLAS 12(3), 1990 (the formal C).
