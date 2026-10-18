# Replication Modes: Synchronous vs Semi-Synchronous vs Asynchronous

## Overview

Replication mode is the knob that decides which single question you can never fully have: when a commit returns OK, does that *guarantee* a second copy exists? Synchronous says yes and pays one network round trip per commit plus availability risk. Asynchronous says no and pays with a failover data-loss window you do not control. Semi-synchronous tries to buy the guarantee without always paying the round trip — and introduces the strangest failure mode of the three: a durability guarantee that silently downgrades to async *exactly while a failure is in progress*.

This page runs the [handbook framework](./index.md) over the three modes with the doc-level knobs named (PostgreSQL's `synchronous_commit` levels, MySQL's semi-sync wait points and timeouts), concrete magnitudes for ack waits and loss windows, and the incident that makes the async loss window visceral: GitHub's October 2018 failover ([case study](../failure-casebook/github-october-2018.md)). The quick-reference tables live in [trade-offs](../../trade-offs/README.md); here it is mechanisms all the way down.

## Step 1: The Problem and Its Constraints

A primary accepts writes; replicas follow. The caller of `COMMIT` needs to know what that acknowledgment *means*. Three constraints define the space:

- **The ack contract.** "Committed" locally is cheap; "committed and on a second machine" requires coordination. Every mode is a choice of what the OK promises: nothing about replicas (async), replica *received* the bytes (semi-sync variants), replica *durably flushed* or even *applied* (sync variants).
- **The latency budget.** A synchronous commit inherits the network round trip to the acking replica: ~0.2–1 ms within a rack, ~1–2 ms across availability zones, 30–150 ms across regions (typical magnitudes, not measurements — these are RTT orders, the physics all designs share). Commit latency *is* the RTT distribution's tail, not its mean.
- **The availability constraint.** If the OK requires *k* ackers and fewer than *k* are alive, either writes stall (choose consistency/availability-for-writes) or the requirement is waived (choose availability, lose the guarantee). There is no setting where both happen; this is the local application of the consistency–availability fork ([CAP, per-operation](./caching-distributed.md)).

## Step 2: The Mechanisms

### Asynchronous

The primary commits locally, acknowledges, and ships its log in the background. Replicas apply at their own pace; the gap — *replication lag* — is the data-loss window at failover. Mechanically, the primary's commit path never touches the network, so commit latency equals local fsync latency (amortized by group commit — see Step 5). The guarantee signed: **acknowledged transactions may be lost if the primary dies before its log ships.** MySQL's default replication and PostgreSQL's default streaming (with `synchronous_commit = off` or no sync standby configured) both live here ([PostgreSQL async commit](https://www.postgresql.org/docs/current/wal-async-commit.html)).

### Synchronous

The primary ships its log and waits for the replica to reach a named stage before acknowledging. PostgreSQL names the stages explicitly in `synchronous_commit` ([runtime-config replication](https://www.postgresql.org/docs/current/runtime-config-replication.html)):

| `synchronous_commit` | Waits for remote replica to… | Remote crash loses… |
|----------------------|------------------------------|---------------------|
| `remote_apply` | Replay (apply) the WAL — queries on the replica see the commit | Nothing — causal read-after-write across nodes |
| `on` (remote flush) | Flush (fsync) the WAL to disk | Nothing durable |
| `remote_write` | Write WAL to the OS (no fsync yet) | The transaction only if the replica's *machine* dies (OS cache lost) |
| `local` | Nothing — local flush only | The usual async window |
| `off` | Nothing — and even local flush is deferred | Configured subset of recent commits |

`synchronous_standby_names` selects which standbys must respond, with a quorum syntax (`ANY 1 (s1, s2)`) — semi-sync in PG is expressed as "one of these, chosen per commit". The strongest setting, `remote_apply`, additionally buys read-your-writes across nodes, which is why it exists despite being the slowest.

### Semi-synchronous (MySQL's named variants)

MySQL implements "wait for one replica" as a plugin with two wait points ([semisynchronous replication](https://dev.mysql.com/doc/refman/8.0/en/replication-semisync.html)):

- **`AFTER_COMMIT`** (the original): primary commits locally, *then* waits for the replica's ack. The client's OK implies the replica has the event — but the ordering leaves a hole: if the primary dies after local commit and before the replica received the binlog, the transaction was **committed on a node that then became a zombie**, and failover to the replica loses it. Acknowledged-and-lost, the worst outcome in the matrix below.
- **`AFTER_SYNC`** (MySQL 5.7.3+, "lossless semi-sync"): primary writes its binlog, waits for the replica to *sync* it, and only then commits locally and acks. A transaction that never reached the replica was never committed — failover cannot lose an acknowledged write. The price: the primary may hold a synced-but-uncommitted transaction that is simply abandoned at failover (benign — clients never saw OK).
- **`rpl_semi_sync_master_timeout`** (default 10,000 ms): if no replica acks within the timeout, the primary **degrades to asynchronous** and keeps committing. When a replica catches up, semi-sync re-engages. This timeout is the feature and the trap — see Step 5.

## Step 3: The Matrix — Guarantees, Latency, Availability

Magnitudes below are typical orders for planning, not benchmarks; they derive from RTT and fsync physics per Step 1.

| Mode | Extra commit latency | Failover data-loss window | Availability behavior when ackers die | Client-visible anomaly class |
|------|----------------------|---------------------------|----------------------------------------|------------------------------|
| Async | ~0 (local only) | = lag at failure moment: sub-second healthy, seconds under load, **unbounded** during partition | Writes continue regardless | Read-your-writes violations on replicas; acknowledged-write loss at failover |
| Semi-sync `AFTER_COMMIT` | +1 RTT to fastest acker (≈1–2 ms AZ, ≈30–150 ms region) | Loses transactions committed-but-unacked-by-replica at primary death (bounded by in-flight window) | Blocks up to timeout, then **silently async** | Acknowledged-write loss *possible* (the hole above) |
| Semi-sync `AFTER_SYNC` (lossless) | +1 RTT before local commit completes | **Zero acknowledged-write loss**; may abandon synced-but-uncommitted txns | Blocks up to timeout, then silently async | None in the loss class; commits delayed by replica health |
| Sync `remote_write` | +1 RTT | Zero for machine crash of primary; replica's OS crash can drop last writes | Writes **stall indefinitely** (PG has no timeout) | Stalls are operator-visible outages until topology changed |
| Sync `on`/`remote_apply` | +1 RTT (apply adds replica replay time) | Zero | Same stall behavior | `remote_apply` gives monotonic reads across replicas |

The three-way tension is explicit now: **async buys latency and write-availability and sells the loss window; sync buys the loss window to zero and sells write-availability (stalls); semi-sync sells a bounded, configurable version of both — with the downgrade trap.** More replicas do not by themselves improve consistency of what callers see — that misconception gets its own treatment in [more replicas, more consistency?](../misconceptions/more-replicas-more-consistency.md).

## Step 4: When Each Wins

| Workload | Appropriate mode | Why the others lose here |
|----------|------------------|--------------------------|
| Financial ledger, billing, orders-as-money | Sync within a region (AZ quorum, `on`/`remote_apply`); cross-region async + reconciliation | Async can lose money; cross-region *synchronous* makes every commit pay a 30–150 ms tail and turns a regional outage into a write outage |
| Social feeds, analytics ingest, telemetry | Async, often multi-primary | Sync latency buys nothing: data is re-derivable, loss is a re-run, and ingest rates make per-commit RTT prohibitive |
| Global user data (profiles, sessions) | Local sync (AZ-level), async across regions; per-user conflict resolution | Global sync = global write latency; async-only risks visible inconsistencies users actually notice (settings reverting) |
| Cache/KV tiers with a durable source of truth behind them | Async | The source of truth owns durability; the cache layer only needs eventual catch-up |

Note the pattern: mode follows *the cost of losing one acknowledged write*, not fashion. That cost, not the RTT, is what makes cross-region synchronous replication rare in practice — and it is why "just add replicas" never upgrades a durability contract (the mechanism is in [primary-backup replication](../../distributed/replication/primary-backup.md) and [quorum replication](../../distributed/replication/quorum.md)).

## Step 5: Edge Cases and Counterexamples

- **The acknowledged write that failed over into oblivion.** Async (or `AFTER_COMMIT` semi-sync) primary takes write W, acks it, dies before its log ships; failover promotes a replica that never saw W. The client *holds an OK for a write that no longer exists* — and application-level reconciliation is now mandatory: compare client-side records (receipts, event logs) against post-failover state and re-apply or compensate. GitHub's October 2018 incident is the canonical public case: a 43-second partition triggered failover while seconds of East-coast writes had never replicated; recovery chose fail-forward plus multi-terabyte restores, and one of the busiest clusters required manual reconciliation of 954 writes ([case study](../failure-casebook/github-october-2018.md)). The system-design residue: any async system needs a *reconciliation plan*, and "the client saw OK" is the only input that matters when deciding what to re-apply.
- **The semi-sync stall — PostgreSQL's version is the sharper one.** PG has **no timeout**: if your single sync standby dies, every commit that must wait stalls indefinitely, and the fix is an operator editing `synchronous_standby_names` (or per-transaction `SET LOCAL synchronous_commit = local` escape hatches built in advance). The durability setting has become an availability outage. MySQL's timeout converts the same event into the *other* failure: after 10 s, commits succeed with **no replica ack — the guarantee silently vanished during the failure it existed for**, and nothing in application behavior announces the downgrade. Both are the same mechanism (a wait with a policy hole), with opposite degradations: stall vs silent downgrade. Quorum syntax (`ANY 1 (s1, s2)`; multiple semi-sync sources) exists precisely to keep one failure from consuming the guarantee.
- **Group commit amortization — why sync is cheaper than it looks.** A synchronous commit costs "+1 RTT", but the fsync *and* the RTT are amortizable: MySQL's binlog group commit batches the log flush and replica-ack wait of all concurrent commits into one cycle, and PG's `commit_delay` lets commits pile up for one flush. Under concurrency, N sync commits cost roughly one RTT plus one fsync in aggregate, not N — which is why latency benchmarks at low concurrency overstate sync's cost for real concurrent workloads. The corollary edge: low-concurrency writers pay full price; a single-threaded financial batch sees every RTT.
- **`remote_write`'s hidden hole.** Waiting for the replica's OS write (not fsync) survives a replica *process* crash but not a replica *power* loss — the acknowledgement is stronger than async and weaker than it sounds. The doc-named stages exist because the durability boundary is per-level; interviews probe exactly whether you know which boundary your config sits on.
- **Semi-sync's ack is not a read guarantee.** `AFTER_SYNC`/`on` promise durability of the commit, not visibility: only `remote_apply` means a replica query will *see* the just-acked write. Applications that write-then-read-from-replica under semi-sync still serve stale reads — a different guarantee than the one they bought.

## Step 6: Decision Framework

1. **Price a lost acknowledged write.** Money/audit → sync-class guarantee (AFTER_SYNC or `on`/`remote_apply`) within a region; re-derivable data → async.
2. **Pick the acker topology before the mode.** Quorum of ackers in independent failure domains (`ANY 1 (s1, s2)`) so one dead replica never consumes the guarantee.
3. **Name the degradation policy explicitly.** PG: decide *now* what stalls mean and pre-build the `synchronous_commit=local` escape hatch / runbook. MySQL: treat the timeout as a durability *downgrade event* — alert on it, never set it to wait forever without a quorum.
4. **Read-after-write needed on replicas?** Only `remote_apply` (or sticky read routing after write) delivers it; semi-sync durability does not.
5. **Cross-region?** Default async + reconciliation tooling + client receipts; reserve cross-region sync for ledgers where the RTT and regional-outage trade-offs are consciously accepted.
6. **Always:** monitor lag (async's loss window is *observable* — alert before failover reveals it), and drill failover + reconciliation like GitHub's postmortem implies: the plan is not real until restored from backup and reconciled on prod-shaped data.

## Interview Questions

1. **A client received a successful commit; after failover, the row is gone. Name two configurations that allow this and one that forbids it.** Allowed: asynchronous replication (log not yet shipped), MySQL `AFTER_COMMIT` semi-sync (committed locally before the replica ack). Forbidden: `AFTER_SYNC` lossless semi-sync — the primary commits only after the replica has synced the log record, so anything acknowledged exists on the acker.
2. **Your single sync standby dies. What do PostgreSQL and MySQL respectively do, and why is each answer dangerous?** PG stalls commits indefinitely (no timeout) — a durability setting becomes a write outage until an operator edits `synchronous_standby_names`. MySQL blocks up to `rpl_semi_sync_master_timeout` (default 10 s) and then silently degrades to async — the guarantee vanishes exactly during the failure it exists for. Both are the stall/downgrade duality; the fix is a quorum of ackers plus an explicit policy.
3. **Why can `remote_write` lose a transaction that `on` cannot?** `remote_write` waits only for the standby's OS to accept the bytes; a standby power loss loses its OS cache. `on` waits for fsync on the standby, making the record durable against machine crash. The stages in `synchronous_commit` are exactly the durability boundaries.
4. **Under high concurrency, synchronous replication is often far cheaper than "+1 RTT per commit" suggests. Why?** Group commit: concurrent transactions share one log flush and one replica-ack wait (MySQL binlog group commit; PG `commit_delay`). The marginal cost of the k-th concurrent commit approaches zero, so sync mode's tax is a concurrency-shaped amortization, not a flat per-commit RTT.
5. **GitHub's October 2018 recovery did not "roll back" the lost writes — it reconciled them. Why is reconciliation the only honest endgame for async systems?** Because with async, primary and promoted replica can each hold writes the other lacks; there is no single ordered log to replay. Clients hold acknowledgments for writes that may not exist, so the application must compare client-side receipts against post-failover state and re-apply or compensate — a designed-in process, not an emergency improvisation ([case study](../failure-casebook/github-october-2018.md)).

## Key Takeaways

- The replication-mode question is "what does the commit OK promise?" — nothing about replicas (async), receipt at a named durability stage (semi-sync/sync), or visibility (remote_apply). Name the stage, or you have not configured anything.
- Semi-sync's wait point is the whole design: `AFTER_SYNC` closes the acknowledged-but-lost hole of `AFTER_COMMIT` for one reordering of two events.
- Every mode has a signature degradation: async — an unbounded loss window; MySQL semi-sync — silent downgrade after timeout; PostgreSQL sync — indefinite stall. Quorum ackers and pre-built escape hatches are the countermeasures.
- The loss window of async is observable (lag monitoring) and its endgame is application-level reconciliation of client-held acknowledgments; GitHub October 2018 is the public case study.
- Group commit amortizes both fsync and RTT under concurrency — evaluate sync modes at workload concurrency, not single-threaded benchmarks.

## Cross-References

- [ACID Transactions: Follow-up Tree](../followup-tree/acid-transactions.md) — escalation chain on durability and atomicity guarantees this page builds on.
- [GitHub October 2018: Failure Casebook](../failure-casebook/github-october-2018.md) — the named incident behind the async-failover edge case.
- [More Replicas, More Consistency: Misconceptions](../misconceptions/more-replicas-more-consistency.md) — why replica count does not upgrade the ack contract.
- [Primary-Backup Replication](../../distributed/replication/primary-backup.md) and [Quorum Replication](../../distributed/replication/quorum.md) — the topology layer beneath the modes.
- [Multi-Primary Replication](../../distributed/replication/multi-primary.md) — what happens when every site accepts writes.
- [DB Replication](../../dbms/distributed/replication.md) and [Replication Strategies](../../dbms/advanced/replication-strategies.md) — engine-level mechanics.
- [Crash Recovery](./crash-recovery.md) — sibling page: the local durability machinery (WAL, fsync) that replication ships.
- [Caching & Distributed](./caching-distributed.md) — sibling page: per-operation consistency/availability choices.
- [Consistency Fundamentals](../../distributed/fundamentals/consistency.md) — the read-your-writes and causal guarantees `remote_apply` provides.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
