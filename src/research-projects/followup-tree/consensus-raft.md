# Follow-up Tree: Consensus — Raft

## Overview

"How does Raft work?" is the consensus question interviewers reach for because Raft was *designed* to be explainable — leader election, log replication, safety properties, each with a name — which makes the follow-ups unusually precise: the candidate either knows why the election restriction guarantees safety or they do not, and there is no fog to hide in. The ladder this page walks runs from the three subproblems (election, replication, safety) through the properties that make a Raft log correct, into the rung that separates practitioners from readers — *what Raft does not give you* (client dedup, linearizable reads without care, anything about your application's side effects) — and lands on the judgment rung: the single-leader design point, what Raft costs, and when a lease or a quorum read is the right tool instead. The full algorithm is deliberately not re-derived here — [Raft](../../distributed/consensus/raft.md) and the original paper (Ongaro & Ousterhout, "In Search of an Understandable Consensus Algorithm," 2014; companion site [raft.github.io](https://raft.github.io/)) own that — this page builds the escalation structure interviews demand. The sibling connections are explicit: transaction machinery in [ACID Transactions](./acid-transactions.md), lease-based alternatives in [Consensus and Leases](../connection-atlas/consensus-leases.md), and replication posture compared in [Replication Modes](../why-not-handbook/replication-modes.md). Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"How does Raft work?"**

The expected core answer: Raft is consensus for a replicated log, decomposed into three subproblems. **Leader election**: servers are followers, candidates, or leaders; time is divided into monotonically increasing *terms*, a candidate requests votes for its term, and a majority wins — so there is at most one leader per term. **Log replication**: the leader accepts client commands, appends them to its log, and replicates entries to followers in `AppendEntries` RPCs; an entry is **committed** once stored on a majority, and the leader applies committed entries to its state machine, advancing the **commit index**. **Safety**: elections are restricted so a candidate can win only if its log is at least as up-to-date as a majority — which is what prevents a leader from ever overwriting committed entries.

A weak answer stops at "it elects a leader and replicates a log" with no terms, no majorities, and no commit semantics. The strong answer names the term clock as the system's *logical time* (all decisions are stamped and compared in terms), states the majority quorum as the mechanism behind both election and commit, and volunteers the design intent: Raft trades a little decentralization for understandability compared to Paxos (see [Paxos](../../distributed/consensus/paxos.md)). The follow-up that escalates: **"Why can't two leaders ever commit conflicting entries?"** — which dives into the safety properties.

## Level 2: Terms, Split Votes, and the Election Restriction

**What it tests:** whether the safety argument is something you can *run* — given a scenario, can you show which property blocks the bad outcome?

**Weak answer:** "The majority prevents split brain" — said as a slogan, unable to trace a two-leader or stale-leader scenario to the property that stops it.

**Strong answer:** can execute the scenarios: a stale leader (older term) stepping aside on seeing a higher term; the election restriction (up-to-date-log check via last-log-index/term comparison) filtering stale candidates; split votes resolved by randomized election timeouts; and log matching making replication prefix-consistent.

**Escalation trigger:** "A partitioned minority leader keeps appending entries — what happens when the partition heals?"

**Answer.** Walk the scenario: the old leader in term 5 keeps accepting (uncommitted) appends from its minority side; on healing, any majority-side exchange with a term-6 or higher leader makes the old leader *step down immediately* — seeing a higher term in any RPC reverts a server to follower, so terms function as an logical clock that deposes stale leaders without any explicit "you're fired" message. Its uncommitted minority-only entries are then *overwritten* by the leader's log — which is safe precisely because they were never committed, i.e., never acknowledged to a client on a majority. The safety invariant underneath: a leader in term T has its log up-to-date by majority vote, and a majority of term-T voters intersect any majority that committed an earlier entry, so the new leader *must* already contain every committed entry — the **election restriction** in action ([Raft](../../distributed/consensus/raft.md) derives this; [Quorum Systems](../../distributed/replication/quorum.md) owns the intersection math).

The remaining mechanisms complete the picture: **split votes** (three candidates each with a minority) resolve via *randomized election timeouts* — some candidate retries first and gathers the majority before the next split; **log matching** (if two logs share an entry at an index and term, everything before it is identical) lets the leader's `AppendEntries` act as the consistency check — a follower truncates conflicting suffixes and accepts the leader's; and the leader forces its own log onto followers rather than reconciling, the design point that makes "leader's log is the truth" load-bearing. The deployment sting to volunteer: a leader whose disk is slow can stall commits for the whole cluster (it must fsync before answering), and pre-vote / check-quorum extensions exist precisely to stop a partitioned old leader from disrupting term numbers and elections — the difference between the algorithm on paper and the tuned protocol in [etcd internals](../../distributed/systems/etcd-internals.md).

## Level 3: What Raft Does NOT Give You

**What it tests:** the practitioner's rung — whether you know the boundary between the replicated-log abstraction and everything a real system still has to build around it.

**Weak answer:** "Raft is linearizable" — full stop, with no scope, no client-dedup discussion, and no awareness of read-path subtleties.

**Strong answer:** enumerates the gaps: Raft guarantees a *consistent log*, not (a) exactly-once execution for clients that retry across leader changes, (b) linearizable reads without extra work (majority quorum reads, ReadIndex, or leader leases), (c) any behavior for *your* state machine's side effects, or (d) snapshots, reconfiguration, and persistence hygiene — each is a documented layer on top.

**Escalation trigger:** "The client retried after a network timeout — how does the new leader know the command already ran?"

**Answer.** The dedup gap first: Raft executes each *log entry* once, but a client retry after a timeout becomes a *new* entry, and if the first attempt had actually committed and applied, the command runs twice. Real systems solve it above the log: client session IDs plus per-session sequence numbers and a dedup table in the state machine (the etcd/TiKV approach — see [etcd Internals](../../distributed/systems/etcd-internals.md)) or idempotency keys from the application. The read gap next: answering a read *from the leader's local state* can be stale — that leader may have been deposed without knowing it — so linearizable reads need either a majority round-trip (the read is logged, or a heartbeat quorum confirms leadership), the **ReadIndex** optimization (confirm leadership with a heartbeat quorum, then read local state), or **lease reads** (time-based leadership assumption, trading clock assumptions for speed) — the trade is exactly the one mapped in [Consensus and Leases](../connection-atlas/consensus-leases.md) and [Leases](../../distributed/advanced/leases.md).

The remaining gaps are operational: **membership changes** (replacing servers without downtime) require their own protocol — joint consensus or single-server steps — where a naive change can produce two disjoint majorities (see [Raft Membership Changes](../../distributed/consensus/raft-membership-changes.md)); **snapshots** (log compaction) are necessary because the log cannot grow forever, and snapshot-install is how a lagging follower catches up; and **fsync discipline** — Raft's correctness assumes a persisted log, so misconfigured disks (write caches without flush) silently void the guarantees. The senior framing sentence: "Raft gives you a replicated state machine *kernel*; sessions, linearizable reads, compaction, and configuration are the rest of the system" — the framing that separates having read the paper from having run the software. ZooKeeper's Zab makes the same point from a different lineage ([ZooKeeper Internals](../../distributed/systems/zookeeper-internals.md)), and TiKV's multi-Raft (thousands of Raft groups sharding a keyspace) shows the kernel composed at scale ([TiDB Architecture](../../distributed/systems/tidb-architecture.md), [Multi-Raft](../../distributed/consensus/multi-raft.md)).

## Level 4: The Single-Leader Design Point — Costs, Alternatives, and When Not to Use It

**What it tests:** judgment at the top rung — can you defend Raft's design point, compare it against its alternatives, and say when the answer is *not* consensus at all?

**Weak answer:** "Raft is the standard, so we use it" — no costs named, no alternatives compared, no failure domain thought through.

**Strong answer:** names what single-leader buys (one serialization point, trivial read of the ordering, simple invariants) and what it costs (every write pays a leader round trip plus majority fsync — 1 WAN RTT floor, no multi-master write availability), places Raft against 2PC (who coordinates failure) and multi-primary (who resolves conflicts), and knows the escape hatches: leases for reads, local quorums for region-local writes, or abandoning consensus when the workload is mergeable.

**Escalation trigger:** "Your cluster spans three regions. What does a write cost, and what would you change?"

**Answer.** The cost accounting: every write is client → leader → majority of followers → apply → respond, so the floor is roughly two RTTs (client-leader, leader-follower-majority — partially overlappable) *plus* the fsync on a majority of disks; put the leader in one region and write latency is hostage to the worst RTT in its majority — availability, likewise, is majority-bound: lose the leader's region plus one node and the cluster halts until a new leader is elected ([FLP](../../distributed/fundamentals/flp.md) reminds us termination in async networks is probabilistic — timeouts, not certainty). The alternatives map cleanly: **2PC** coordinates an existing transaction across resources but blocks when its coordinator dies ([Two-Phase Commit](../../dbms/transactions/two-phase-commit.md)) — Raft replaces the coordinator's fragility with an elected one; **multi-primary replication** keeps writing during partitions and pays for it in conflict resolution ([Multi-Primary](../../distributed/replication/multi-primary.md)); **primary-backup without consensus** is faster but cannot distinguish a slow leader from a dead one ([Primary-Backup](../../distributed/replication/primary-backup.md)) — the comparison table is the territory of [Replication Modes](../why-not-handbook/replication-modes.md).

The judgment coda — when *not* to reach for Raft: single-writer workloads that only need durable replication, read-mostly configuration data served fine from leases and gossip, highly-contended counters where CRDTs merge instead of ordering ([CRDTs](../../distributed/fundamentals/crdts.md)), and anything where the majority-quorum WAN tax cannot be afforded — geo-distributed systems then shard their consensus (region-local Raft groups with async cross-region replication, the CockroachDB/TiKV pattern) or use leader leases to serve local reads between elections. The interview closing line that lands: "consensus is how you *pay* for a strongly-ordered replicated log; the design question is whether your workload needs the ordering strongly enough, everywhere, to pay it on every write" — and whether reads can ride cheaper mechanisms ([CAP](../../distributed/fundamentals/cap.md)) without lying about staleness.

## How to Approach Unfamiliar Variations

The template for consensus variations — "multi-Raft," "witness replicas," "why not Paxos":

1. **Locate the term clock and the quorum.** Every Raft-family protocol has a leader-selection epoch and a majority intersection; the variation is usually a change to *which* quorum decides what (flexible quorums, witnesses that vote but do not store logs).
2. **For every "it guarantees X," ask: as of which round trip?** Linearizable reads, exactly-once execution, and durability all have round-trip and fsync boundaries — the guarantee is real only inside its scope.
3. **Trace the partition scenario before answering.** Two leaders, stale leader, minority leader appending — run the scenario against terms and the election restriction; the safety property either fires visibly or your model has a hole.
4. **Price the design before defending it.** Leader RTT + majority fsync + election stall on failure — versus the alternatives' costs (2PC blocking, multi-primary conflicts). A design defended without its price sounds like advocacy, not engineering.

## Interview Questions

**Q: Why do randomized election timeouts matter, and what breaks without them?**
A: Split votes: multiple candidates time out simultaneously, each collects a minority, nobody wins, and the term churns — livelock. Randomization makes one candidate's retry statistically likely to finish before the next timeout, breaking symmetry without coordination. Without it (fixed timeouts), candidates keep colliding in lockstep; with too-aggressive randomization ranges, elections slow down and failover latency rises — the tuning is a real production knob.

**Q: A client sends a write, gets a timeout, and retries. The first attempt had committed. Does Raft run it twice?**
A: The retry is a *new* log entry, so yes — Raft's exactly-once is per log entry, not per client command. Systems fix it with client sessions: session ID plus sequence number recorded in the state machine, so the dedup table turns the duplicate into a cached response. This is why "Raft gives exactly-once" is a wrong sentence without the word "state machine's" in front of it.

**Q: etcd is often called the control plane's database. Why Raft there, and why multi-Raft in TiKV?**
A: etcd needs a small, strongly consistent, linearizable key-value store for cluster state — a single Raft group is exactly that kernel, and its read path (ReadIndex, leases) is tuned for it. TiKV needs per-region consistency over terabytes: thousands of Raft groups, each ordering one keyspace region, scale the same kernel horizontally — the difference is scope: one log for the world versus one log per shard ([Multi-Raft](../../distributed/consensus/multi-raft.md)).

**Q: Your read-heavy service needs consistent reads but cannot afford a majority round trip per read. Options?**
A: Lease reads — the leader assumes validity for a lease duration shorter than the election timeout, so followers will not start an election during the window, and reads serve locally; the cost is a clock-drift assumption. ReadIndex is the middle option (one heartbeat quorum per read, no clock assumption). Both are standard etcd options; the choice is literally "do you trust bounded clock skew" — the same trade [Consensus and Leases](../connection-atlas/consensus-leases.md) develops.

## Key Takeaways

- Raft decomposes consensus into leader election, log replication, and safety; terms are the logical clock, majorities the decision rule, and the commit index the point where an entry becomes real.
- Safety rests on the election restriction plus quorum intersection: a new leader must already hold every committed entry — walk the partition scenario, don't recite it.
- Split votes die by randomized timeouts; log matching lets the leader truncate and converge followers; stale leaders are deposed by any higher-term message.
- Raft gives a replicated log — not exactly-once client execution, not linearizable reads for free, not compaction or reconfiguration: sessions/dedup tables, ReadIndex/lease reads, snapshots, and membership changes are extra layers.
- Single-leader buys simplicity at a price: leader-region RTT and majority fsync on every write, majority-bound availability; 2PC, multi-primary, and CRDT alternatives pay different costs.
- When writes don't need global strong ordering, shard the consensus (multi-Raft) or replace it with leases, quorum reads, or mergeable state — paying for consistency only where the workload needs it.

## Cross-References

- [Raft](../../distributed/consensus/raft.md) — the full algorithm: elections, log replication, and the safety proofs.
- [Multi-Raft](../../distributed/consensus/multi-raft.md) — sharding one protocol across thousands of groups.
- [Raft Membership Changes](../../distributed/consensus/raft-membership-changes.md) — joint consensus and single-server reconfiguration.
- [Paxos](../../distributed/consensus/paxos.md) — the ancestor protocol and the understandability contrast.
- [etcd Internals](../../distributed/systems/etcd-internals.md) — Raft in production: sessions, MVCC, and read paths.
- [ZooKeeper Internals](../../distributed/systems/zookeeper-internals.md) — Zab: the other production consensus lineage.
- [TiDB Architecture](../../distributed/systems/tidb-architecture.md) — multi-Raft as the storage engine of a distributed SQL database.
- [Consensus and Leases](../connection-atlas/consensus-leases.md) — the lease/consensus trade space for reads and leadership.
- [Replication Modes](../why-not-handbook/replication-modes.md) — the comparison table: sync, semi-sync, multi-primary, consensus.
- [Primary-Backup](../../distributed/replication/primary-backup.md) — replication without consensus and its failure ambiguity.
- [Quorum Systems](../../distributed/replication/quorum.md) — the intersection math behind majorities.
- [FLP Impossibility](../../distributed/fundamentals/flp.md) — why timeouts, not certainty, power elections.
- [Two-Phase Commit](../../dbms/transactions/two-phase-commit.md) — coordination without election, and the blocking cost.
- [ACID Transactions](./acid-transactions.md) — the transaction ladder whose durability rung consensus underwrites.
- [Message Queues](./message-queues.md) — the log abstraction in a different role: ordering without consensus per record.
- [Leases](../../distributed/advanced/leases.md) — the time-based mechanism behind lease reads.
- [raft.github.io](https://raft.github.io/) — the paper, visualizations, and reference implementations.
