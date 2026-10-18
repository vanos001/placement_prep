# Follow-up Tree: Replication Lag

## Overview

"How does primary–replica replication work?" gets the rehearsed answer: the primary logs writes and ships them to replicas, which apply and serve reads. The interview actually starts at the next sentence: *the replica is behind* — and everything interesting lives in that gap. Replication lag is the distributed-systems ladder that never ends in buzzwords: it forces the candidate through async versus sync trade-offs, the measurement problem (lag of *what*, measured *where*), the user-visible anomalies (your own write vanishing, the counter running backwards), and the failover scenario where lag turns into data loss. Infrastructure and database teams use this chain because it tests whether a candidate models replicas as *eventually consistent caches of the truth* or as reliable backups with a pleasant UI. This page walks the ladder rung by rung — what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates. The mode comparison itself (sync, async, semi-sync, and what each sacrifices) is the companion page [Replication Modes](../why-not-handbook/replication-modes.md); the misconception this ladder dismantles in passing — that adding replicas buys consistency — is documented as [More Replicas ≠ More Consistency](../misconceptions/more-replicas-more-consistency.md). Book-level companions: [Primary–Backup](../../distributed/replication/primary-backup.md), [Quorum Replication](../../distributed/replication/quorum.md), and [Anti-Entropy](../../distributed/advanced/anti-entropy.md).

## The Opening Question

**"How does primary–replica replication work, and what does 'the replica is behind' actually mean?"**

The expected core answer: writes go to the primary, which records them durably (a write-ahead or commit log — the WAL connection is developed in [ACID Transactions](./acid-transactions.md)) and propagates changes to replicas; replicas apply changes in order and serve reads. "Behind" means the replica has applied *fewer* log entries than the primary has committed: there is a window in which a read served from the replica returns data that predates accepted writes.

A weak answer says "the replica copies data from the master, sometimes slowly" — it cannot say *what unit* the lag is measured in or *what breaks* because of it. The strong answer names the log position arithmetic: lag is a difference in applied log positions (bytes or events), every read from a lagging replica is a read of an older database state, and the anomalies that follow are specific and enumerable — stale reads, non-monotonic reads, lost-write illusions. The follow-up that escalates: **"Why not just make replication synchronous?"** — the trade-off rung.

## Level 2: Sync, Async, and Semi-Sync — What Each Latency Buys

**What it tests:** whether the candidate can *price* consistency: what synchronous replication costs in latency and availability, and why virtually every large deployment chooses some form of asynchrony.

**Weak answer:** "Sync is safer, async is faster" — true, and empty: no failure scenario, no latency arithmetic, no semi-sync middle ground.

**Strong answer:** derives the cost from the failure scenario — sync means every commit waits for a remote round trip and a replication *failure becomes a write outage*; async means the primary never blocks but accepts that acknowledged writes may be lost on failover; semi-sync bounds the loss window while keeping the primary available.

**Escalation trigger:** "Your primary commits at 5 ms locally. What does full synchronous replication to a cross-AZ replica do to write latency — and to availability when that replica dies?"

**Answer.** The arithmetic first: cross-AZ round trips are on the order of 1–2 ms inside a region, so sync adds a remote RTT *on the commit path* — 5 ms becomes roughly 6–7 ms, tolerable. The availability cost is the real price: with fully synchronous replication, a write succeeds only if the replica acknowledges, so a dead or partitioned replica does not degrade the system, it *stops writes* — CAP's honest form, discussed in [CAP](../../distributed/fundamentals/cap.md). Asynchronous replication inverts everything: the primary acknowledges on local commit alone, writes never wait, and the price is the loss window — everything acknowledged but not yet shipped is lost if the primary dies, which is exactly the "failover pain" rung below. Semi-sync (the PostgreSQL/MySQL middle ground) blocks the commit until *one* replica confirms receipt — receipt, not apply — bounding the loss window to roughly one RTT while surviving the loss of any single replica, with the failure mode that a missing acknowledgment must degrade to async (or stall writes) after a timeout — the same fail-open/fail-closed decision as the rate-limiter ladder ([Rate Limiter Design](./rate-limiter-design.md)). The senior framing: this is a latency–durability dial, not a binary; the question "sync or async?" is always really "how many milliseconds of loss window do you accept, and what happens to writes when the acker is gone?" The full mode taxonomy lives in [Replication Modes](../why-not-handbook/replication-modes.md).

## Level 3: Measuring Lag — of Bytes, Events, and Seconds

**What it tests:** operational maturity — whether the candidate knows lag is not one number, that measurement points disagree, and that the wrong metric hides the incidents.

**Weak answer:** "Check `SHOW SLAVE STATUS` and read Seconds_Behind_Master" — one tool, and no understanding of why that number lies.

**Strong answer:** distinguishes log-position lag (bytes or events the replica has not applied), *time-based* lag (how old is the newest data the replica would return — a heartbeat timestamp comparison), and visibility lag from the reader's side; knows the measurement failures (zero lag while disconnected, lag that is really apply-side stalls like a single-threaded applier or a long transaction).

**Escalation trigger:** "Your monitoring says lag is zero, but users on the replica see stale data. How?"

**Answer.** Lag is measured *somewhere*, and every vantage point has a blind spot. Position lag (primary binlog position minus replica-applied position) is precise but says nothing about *freshness in seconds*; the classic MySQL `Seconds_Behind_Master` is computed from timestamps in the log and reports zero when the replica is *disconnected* or when the replication threads are stopped — the number goes to zero exactly when replication is broken, which has caused many incidents. Time-based lag inverts the anchor: the replica heartbeats a timestamp, and lag is *now minus the newest heartbeat applied* — the metric a read-your-writes system actually needs, because it answers "how old is the data this replica will return" rather than "how many bytes are queued." The apply-side stalls complete the rung: a replica can receive bytes instantly and still lag because it applies single-threaded what the primary wrote in parallel (the reason MySQL added multi-threaded appliers), because one huge transaction blocks the log (everything after it waits), or because the replica's disk cannot keep up with write amplification — the storage-side mechanics are the chain in [Database Indexes](./database-indexes.md). The senior habit: alert on heartbeat age measured at the *replica*, chart it against network and apply phases, and treat "zero lag" with the suspicion any too-perfect metric deserves.

## Level 4: Session Guarantees — Read-Your-Writes and Monotonic Reads

**What it tests:** whether the candidate can translate lag into the specific user-visible anomalies it causes, and name the countermeasures as *session* properties rather than database-wide consistency upgrades.

**Weak answer:** "Users might see slightly old data for a few seconds" — treats staleness as uniformly harmless, missing the anomalies that feel like bugs: your own write disappearing, state going backwards.

**Strong answer:** names the two canonical anomalies — a user writes, then reads a replica that has not caught up (the read-your-writes violation that looks like data loss) and a user served by replica A, then replica B, seeing an *older* state (the monotonicity violation that looks like a time machine) — and designs the session-level fixes.

**Escalation trigger:** "A user saves their profile, the success page shows the old email, support says 'eventual consistency, wait a minute.' What do you change?"

**Answer.** The anomaly is precise: the *user's own writes* are the ones they cannot tolerate missing, and nobody else's — which is why the fix is session-scoped, not a fleet-wide consistency upgrade. The standard ladders, in increasing invasiveness: (1) read-your-writes routing — after a write, pin that session's reads to the primary (or a replica confirmed caught-up to the write's log position) for a TTL or until the position is applied; the token version (a "causal consistency token" carrying the write's position, checked by the storage layer) is the scalable form. (2) Monotonic reads — sticky per-session replica selection so a session cannot hop from a fresh replica to a stale one; this is cheap (affinity, the Level 4 analysis of [Load Balancing](./load-balancing.md)) and fixes the time-machine complaints. (3) Quorum reads — R + W > N makes overlapping read/write sets structural (the arithmetic in [Quorum Replication](../../distributed/replication/quorum.md)), buying the property for everyone at a latency price. The trap worth naming explicitly: none of these are purchased by *adding replicas* — more replicas multiply the places a stale read can come from, the documented claim in [More Replicas ≠ More Consistency](../misconceptions/more-replicas-more-consistency.md). The senior sentence: "eventual consistency is a fleet property; read-your-writes is a session property, and sessions are where you can afford to enforce it."

## Level 5: Failover, Conflicts, and the Judgment Rung

**What it tests:** the boundary rung — what lag does to failover (loss, split-brain, write races), how multi-primary systems resolve conflicts, and whether the candidate can choose a replication topology under constraints.

**Weak answer:** "If the primary dies, we promote a replica" — no loss window, no split-brain model, no promotion criteria.

**Strong answer:** knows promotion is choosing the most-caught-up replica and *accepting the loss of the tail* (the async loss window from Level 2, realized), names split-brain and fencing, and can compare conflict-resolution strategies — last-writer-wins and its clock dependence, per-key CRDTs, application-level merge — plus the judgment call between primary–backup, semi-sync, and multi-primary topologies.

**Escalation trigger:** "Primary dies. Your most advanced replica is 800 ms behind. Walk through promotion exactly."

**Answer.** Promotion is a bounded-loss procedure: elect the replica with the highest applied position (choosing a *less* caught-up one silently loses more), fence the old primary so a partitioned zombie cannot accept writes (split-brain is two primaries diverging two logs — unreconcilable without manual merge; fencing tokens and leases are the machinery in [Leases](../../distributed/advanced/leases.md) and [Fencing Tokens](../../distributed/fundamentals/fencing-tokens.md)), truncate or archive the un-applied tail, and redirect clients. What the 800 ms means concretely: every write acknowledged in that window is gone unless the old primary returns and is reconciled — this is the honest price of async, and semi-sync exists to shrink it (Level 2's dial). The failover *duration* is dominated not by copying data but by detection and quiescence — which is why leader-election systems formalize the whole procedure: [Consensus: Raft](./consensus-raft.md) is this rung's mechanism with the loss window closed by protocol instead of procedure. For multi-primary (active–active), lag becomes *conflict*: two primaries accept divergent writes for the same key and reconciliation must run continuously — last-writer-wins with wall clocks silently drops writes depending on clock skew (the clock machinery in [Clocks and Time](../assumptions-hunt/clocks-and-time.md)), while per-key CRDTs or application-level merge make convergence explicit (the catalog in [Multi-Primary](../../distributed/replication/multi-primary.md) and [CRDTs](../../distributed/fundamentals/crdts.md)). The judgment synthesis: pick topology from the write model — single-region write-heavy systems want primary–backup or semi-sync; globally distributed write-anywhere systems want multi-primary *plus* an explicit, tested conflict policy, because conflict resolution is a product decision, not a database setting.

## How to Approach Unfamiliar Variations

The template for replication-lag variations — "lag after a bulk load," "replicas for analytics," "lag in a queue-based system," "lag in CDN caches":

1. **Identify the log and the apply model.** Every lag discussion reduces to: what is the ordered record of changes (WAL, binlog, oplog, Kafka topic), and how does the follower apply it — in parallel, single-threaded, transactionally? Apply-model asymmetry between primary and replica is where surprise lag lives.
2. **Convert lag units to user-facing staleness.** Bytes and positions mean nothing to a user; heartbeat age does. When a variation hands you a lag number, ask what it means in "how old is the data a read returns" terms.
3. **Separate fleet properties from session properties.** Staleness, convergence, and conflict resolution are fleet-wide; read-your-writes and monotonic reads are per-session. Variations that mix them ("make everything strongly consistent") are invitations to restate the dial and its price.
4. **For failover questions, run the promotion script aloud.** Most-caught-up replica, fence the old primary, bound the tail loss, redirect — then name what the topology does to that script. Semi-sync shortens the tail; consensus closes it; multi-primary moves the pain to reconciliation.

## Interview Questions

**Q: Your read replicas lag 30 s every night during the batch window. The batch is 40 minutes of heavy writes. Why does lag spike and what are two structural fixes?**
A: The batch's write rate exceeds the replicas' apply throughput — lag is the queue formed when production rate exceeds apply rate, and it drains only after the batch ends. Structural fixes: throttle or chunk the batch to cap the write rate (queueing control, the pool-sizing arithmetic in [Connection Pooling](./connection-pooling.md)); or increase apply parallelism (multi-threaded applier, partitioned apply by key) so the replica's drain rate rises. A third lever: route batch-affected reads to the primary for the window, accepting primary load.

**Q: A product team demands "strong consistency" because of one checkout race. What do you actually offer them?**
A: The narrowest sufficient guarantee: their race is almost certainly read-your-writes plus a linearizable read of one or two keys. Offer position-based read routing or a quorum read on the specific key, not a database-wide consistency upgrade — and price the alternatives honestly (sync replication or consensus writes cost an RTT and availability on the write path). Most "strong consistency" requests dissolve into three session guarantees applied to one flow.

**Q: Seconds_Behind_Master reads 0, but you can prove the replica returns stale data. Give two mechanisms for the contradiction.**
A: (1) The metric is computed from log timestamps and reports zero when replication threads are stopped or disconnected — broken replication looks like perfect replication. (2) The lag is *before* the measurement point: the replica is current with the log it received, but the primary has not yet written the user's transaction (long-running transaction, commit ordering), so nothing is wrong with replication and the read is still stale. Fix the monitoring to heartbeat age measured on the replica's applied state, not replica-side thread bookkeeping.

**Q: You inherit a multi-primary database where last-writer-wins resolves conflicts using server clocks. What is the concrete risk and the cheapest mitigation?**
A: Silent lost updates: two primaries accept writes to the same key, and clock skew — or merely ordering — decides which survives, with no error surfaced. Skew between servers (and NTP steps) makes the "winner" arbitrary. Cheapest mitigation: scope LWW to keys where last-write-wins is semantically true (profile fields, presence) and move genuinely accumulating state (counters, balances) to commutative merges or application-level resolution; the catalog is in [Multi-Primary](../../distributed/replication/multi-primary.md) and [CRDTs](../../distributed/fundamentals/crdts.md).

## Key Takeaways

- Replication lag is a difference in applied log positions; every read from a replica returns some older state of the database, and the anomalies that follow are specific and enumerable.
- Sync replication spends a remote RTT and availability (a dead acker stops writes) to shrink the loss window; async spends the loss window to never block; semi-sync is the dial between them.
- Lag metrics lie by vantage point: thread-derived counters report zero when replication is broken; heartbeat age measured on applied state is the metric that answers freshness questions.
- Read-your-writes and monotonic reads are session properties, bought with position-based routing or replica stickiness; they are not purchased by adding replicas.
- Failover with async replication is bounded data loss plus a fencing problem; consensus turns the procedure into a protocol, and multi-primary turns lag into a conflict-resolution policy.
- The topology decision follows the write model: one write region wants primary–backup or semi-sync; write-anywhere wants multi-primary plus a tested, explicit merge policy.

## Cross-References

- [ACID Transactions](./acid-transactions.md) — the WAL/commit-log machinery replication ships, and the durability letter this ladder leans on.
- [Consensus: Raft](./consensus-raft.md) — the protocol that replaces the failover script with election and log matching, closing the loss window.
- [Message Queues](./message-queues.md) — the log as replication substrate: consumer lag is this chain's lag in a different costume.
- [Connection Pooling](./connection-pooling.md) — the queueing arithmetic behind "lag is a queue drained at apply rate."
- [Load Balancing](./load-balancing.md) — session affinity as the cheap monotonic-reads implementation.
- [Replication Modes](../why-not-handbook/replication-modes.md) — the companion comparison of sync/async/semi-sync and what each sacrifices.
- [More Replicas ≠ More Consistency](../misconceptions/more-replicas-more-consistency.md) — the documented misconception this ladder's Level 4 dismantles.
- [Primary–Backup](../../distributed/replication/primary-backup.md) and [Multi-Primary](../../distributed/replication/multi-primary.md) — the topology catalog behind the judgment rung.
- [Quorum Replication](../../distributed/replication/quorum.md) — the R + W arithmetic that makes overlap structural.
- [Anti-Entropy](../../distributed/advanced/anti-entropy.md) and [Hinted Handoff](../../distributed/advanced/hinted-handoff.md) — how eventually consistent systems catch replicas up after gaps.
- [Leases](../../distributed/advanced/leases.md) and [Fencing Tokens](../../distributed/fundamentals/fencing-tokens.md) — the split-brain countermeasures the promotion script depends on.
- [Clocks and Time](../assumptions-hunt/clocks-and-time.md) — why last-writer-wins on wall clocks is a gamble.
- [PostgreSQL Logical Replication](https://www.postgresql.org/docs/current/logical-replication.html) — a production replication pipeline to map this ladder's terms onto.
