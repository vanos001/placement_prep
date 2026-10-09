# Spanner Internals: TrueTime Math, Paxos Groups, and Commit-Wait

## Overview

Spanner is Google's globally distributed SQL database; the [fundamentals page](../fundamentals/spanner.md) covers its architecture at survey level. This page goes into the internals interviewers actually probe: the TrueTime uncertainty budget and the commit-wait equation with its proof sketch, the Paxos-group machinery under each tablet, directory-based placement and how clients route around stale mappings, served vs safe time on replicas, the F1 client that sat above the original system, and what changed after the 2017 "Becoming a SQL System" paper (the file-backed storage redesign, the Postgres dialect). External consistency — the strongest behavior any production database advertises — is not a slogan here; it is two inequalities and a wait, and this page writes them down.

## TrueTime: The API and the Uncertainty Budget

TrueTime exposes time as an interval. `TT.now()` returns `[earliest, latest]` with `ε = latest − earliest` the local uncertainty; `TT.after(t)` and `TT.before(t)` answer "definitely past/future" by comparing against interval endpoints. The 2012 paper reports `ε` between 1 and 7 ms in production, averaging ~4 ms, sustained by two redundant time-master populations per datacenter — GPS receivers and cesium atomic clocks (they fail differently: GPS loses sky, clocks drift) — and by machines polling masters every 30 s. Uncertainty is a *budget* consumed by drift since the last poll: a machine that cannot reach any master widens its interval and eventually removes itself from service; a corrupted master is voted out by the daemon cross-checking masters against each other.

The engineering claim to remember: TrueTime is not a fancy clock, it is a *bounded-error contract* with an escape hatch (the interval only ever widens, and code must treat every timestamp as uncertain). Everything else on this page consumes that contract. The generic treatment — API, hardware, critiques — is in [TrueTime](../fundamentals/truetime.md); here we only carry the two facts the math needs: uncertainty is bounded, and `TT.after(s)` is a waitable event.

## Paxos Groups per Shard

Spanner shards data into **tablets** — contiguous key ranges — each owned by a **Paxos group** of replicas spread across sites (the paper's example universe: 5 replicas across 3 datacenters). One replica is the group leader, elected by Paxos and holding a **leader lease** (default 10 s) that lets it act without re-confirming election on every operation. Writes are proposed by the leader and recorded through Paxos; the leader **pipelines** Paxos writes (advancing proposal numbers per log slot without waiting for prior commits), which is what makes the group keep up with thousands of writes per second rather than one Paxos round per write.

Every replica maintains three pieces of state the rest of the protocol reads: the Paxos log and applied state, the **lock table** (a map from key ranges to lock holders for 2PC participants), and the **timestamp cache** (per-key-range last-read timestamps, so a leader cannot assign a write a timestamp below a read that already happened on its watch). Participant tablets in a transaction record their prepare in the Paxos log itself — lock acquisition is replicated, which is what makes the coordinator crash-recovery safe: any surviving replica knows the lock state.

The directory/placement layer (next section) decides *where* replicas live, but group membership changes run through Paxos as data: adding a replica, moving one, or re-electing are log entries, so the group remains a single total order of everything that happens to its tablet.

## Directories and Placement

Spanner's unit of data movement is the **directory**: a contiguous set of keys sharing an assignment (in practice, all rows of one customer or tenant). Directories are colocated with their tablet but can **move** — the background placement service migrates a hot or mislocated directory to another tablet (group) to balance load or honor geo-policy ("this tenant's data must live in the EU"). A move is a background copy that flips a pointer in tablet metadata; clients that cached the old mapping are corrected by an "assignment is stale" signal, forcing a metadata re-read — the same directory-cache-correction pattern CockroachDB's DistSender uses (see [CockroachDB architecture](./cockroachdb-architecture.md)).

The paper's placement knobs are: replication **configuration** per directory (which sites hold replicas — trading read latency against write latency), and **geo-locality** of the directory itself. Read latency at a site depends on whether a replica (ideally the leader) is local; write latency depends on how far apart the group's replicas are. This is the honest trade table of geo-distributed SQL: every choice optimizes some region's reads against some transaction's cross-site Paxos RTT, and the directory is the lever. Cloud Spanner's `INTERLEAVE IN PARENT` is the modern, schema-level version of the same colocation idea.

## The Commit Protocol and the Commit-Wait Equation

A read-write transaction touching multiple groups runs 2PC *over* Paxos: each participant leader locks the rows (via a replicated prepare in its Paxos log), the coordinator group's leader picks the commit timestamp and records the commit, participants apply and release locks. The whole correctness story is in how `s` is chosen and when it is acknowledged. Write:

\\[
s \;=\; \max\Big(\;TT.now().latest,\; \text{prepare-timestamps of all participants}\Big)
\\]

where each participant's prepare timestamp is itself ≥ the latest commit timestamp that group has assigned (enforced by the timestamp cache and Paxos ordering). The coordinator then **commits** the client's transaction only after:

\\[
TT.after(s) \;\text{holds} \qquad\Longleftrightarrow\qquad s \;<\; TT.now().earliest
\\]

i.e., it waits until `s` is *certainly in the past* before releasing locks and replying. With average uncertainty `ε̄ ≈ 4 ms` (paper measurement; interval up to 7 ms), the expected wait is on the order of `ε` — the paper reports ~8 ms mean for the full write path including Paxos, dominated by this wait and the quorum round trip.

### Why That Wait Buys External Consistency

External consistency (strict serializability across the globe) means: if transaction `T1` committed before `T2` *began* in real time, then `s_1 < s_2`. The proof sketch is three lines:

1. `T1` acknowledged only after `TT.after(s_1)`, so at acknowledgement time every correct machine's `TT.now().earliest > s_1`.
2. `T2` started after that acknowledgement, so when `T2`'s coordinator picks `s_2 = max(TT.now().latest, …)`, its TrueTime interval lies strictly after `s_1` — hence `s_2 ≥ TT.now().latest > s_1`.
3. Paxos ordering per group plus the timestamp cache guarantee no group assigns timestamps out of order, so the inequality survives to visibility.

The wait is the price of buying step 1 without a global clock: uncertainty cannot hurt you if you simply refuse to confirm anything until the uncertainty window has passed. This is the exact opposite trade from CockroachDB (no wait; instead, uncertainty restarts on conflict — see the comparison in [clocks & ordering](../advanced/clocks-ordering.md)).

## Served vs Safe Time

Replicas other than the leader can serve reads, but only up to a timestamp they can *prove* is complete. Define a replica's **safe time** `Ts.safe` as the highest `t` such that every Paxos write with timestamp ≤ `t` has been applied locally — in the paper's construction, the minimum of "all Paxos entries up to the last accepted prepare have arrived" and "the local state machine has applied them." A read at timestamp `ts ≤ Ts.safe` is a consistent snapshot read that requires no communication with the leader; a read above safe time must wait (at the leader) or fail over to another replica.

The leader tracks each replica's safe time (replicas report the timestamps they can serve) and routes reads accordingly; Cloud Spanner exposes the same mechanism as *staleness-bounded* or *exact-staleness* read-only transactions. **Served time** is simply what a given read actually observed — the snapshot timestamp handed back — and the two notions together are the API of "read at a historical point": safe time bounds what *can* be served, served time is what *was*. This is also the mechanism behind CockroachDB/TiKV follower reads; the Spanner paper is the original citation.

## F1: The Client Above Spanner

Spanner's first large consumer was not an application but **F1**, the AdWords SQL stack (a descendant of the shaded-MySQL fleet Megastore was built for — see [Megastore](../fundamentals/megastore.md)). F1 is a layer of stateless servers near Spanner that owns: query planning and execution against Spanner's KV API, pessimistic transactions with deadlock-aware locking via Spanner's lock API, and a globally replicated schema with **lease-based schema changes** — the F1 paper's celebrated result (VLDB 2013): a schema change commits a new schema version with a lease; all servers serve both old and new versions during the overlap; a change is complete when no server can still serve the old version. That protocol delivers asynchronous, non-blocking online schema changes without a maintenance window, and it is the ancestor of every "online schema change with version leases" design since (including the patterns in [online schema change](../../dbms/advanced/online-schema-change.md)).

The F1/Spanner split is a lesson in layering: Spanner provides replicated, timestamped KV with transactions and global consistency; F1 provides SQL, caching (with explicit invalidation via Spanner's read timestamps), and schema evolution. Interviews rarely need more than that division plus the lease-schema trick.

## What Changed After 2017

The [2017 paper](https://research.google/pubs/pub47702/) ("Spanner: Becoming a SQL System") marked the shift from "globally consistent KV with a transactional API" to a full SQL system, and the changes since cluster into three groups:

- **Query processing**: automatic, history-driven query optimization; range partitioning of distributed plans; resumable and vectorized execution — the machinery summarized in the fundamentals page's SQL section.
- **File-backed storage redesign** (post-2017 engineering, described in Google's 2022–2024 papers/talks): Spanner originally treated the Paxos log as the source of truth with disk writes on the commit path; the file-backed redesign moves durable state into Colossus-backed files, decoupling commit latency from local-disk flush behavior — commits wait on Paxos quorum and TrueTime, not on local fsyncs, which materially lowered tail write latency and eased storage evolution. The architectural invariant (log-ordered, timestamped writes) survived; the physical substrate changed.
- **Surface area**: the **Postgres dialect** (2021–2022) let PostgreSQL applications and ORMs adopt Spanner with minimal rewrites — a compatibility statement, not a semantics change (internals, isolation, and TrueTime behavior are identical); plus graph queries, enhanced change streams, and continued availability work (e.g., dual-region/quorum configurations documented in the Cloud Spanner docs).

The interview-worthy summary: the *core protocol* (TrueTime + Paxos + commit-wait + directories) has been stable since 2012; everything since 2017 has been about making it a mainstream SQL product — query planning, storage efficiency, and compatibility.

## Interview Questions

1. **State the commit-wait rule and prove external consistency from it.** The rule: a read-write transaction with commit timestamp `s = max(TT.now().latest, participant prepare timestamps)` is acknowledged only after `TT.after(s)`. If `T1` commits before `T2` starts, then every machine's `earliest` exceeds `s_1` at that moment, so `T2`'s coordinator — choosing `s_2` from a strictly later TrueTime interval — must pick `s_2 > s_1`. Per-group Paxos ordering and the timestamp cache preserve the ordering through to visibility. The wait converts a bounded-uncertainty clock into a total order consistent with real time.
2. **Why is commit-wait on the critical path, and what would you do if the product demanded lower write latency?** The wait cannot overlap the Paxos write: the transaction may only be acknowledged once `s` is certainly past, which by definition happens after the uncertainty interval begun when `s` was chosen has elapsed (mean ~4 ms, up to 7). Lower-latency options: shrink `ε` (better time infrastructure), use read-only transactions (no wait, safe-time reads), relax to bounded staleness reads, or re-architect as CockroachDB does — replace the wait with uncertainty-interval restarts that only pay on actual skew conflicts. Each is a real product decision with a documented precedent.
3. **What exactly can a follower replica serve, and what bounds it?** A follower serves reads at any `ts ≤ Ts.safe`, its safe time — every Paxos write with timestamp ≤ `ts` is applied locally. Safe time is bounded by raft/Paxos apply lag and the flow of timestamps from the leader; the leader tracks replicas' safe times to route reads. This is the mechanism behind Spanner's exact- and bounded-staleness read-only transactions and the template for follower reads in CockroachDB and TiKV.
4. **What is the role of the directory, and what happens to a client whose directory cache is stale?** Directories are the unit of placement: contiguous key sets moved between tablets to balance load or honor geo-policy. A client that routes by a stale cached mapping reaches a replica that no longer owns the range; Spanner answers with a "stale assignment" signal, the client refreshes its metadata and retries — one extra round trip, no correctness issue. The same pattern exists in every sharded system with client-side routing caches (CRDB's DistSender, Bigtable tablets).
5. **Describe F1's lease-based online schema changes in one paragraph.** F1 stores, alongside the data, a distributed "schema with version leases": a change introduces a new schema version that all F1 servers begin serving while the old version remains valid until their leases expire. Schemas are staged so every intermediate pair (old, new) is mutually consistent — e.g., add index as "absent → delete-only → write-only → backfill → public." Because any two concurrently-served versions are compatible, changes require no maintenance window and never block traffic; completion is when no lease on the old version survives. This protocol is the ancestor of modern online-DDL designs.
6. **What actually changed in Spanner after 2017 — internals or packaging?** Both, at different depths: query processing became a full optimizer with distributed plans and resumable vectorized execution (2017 paper); the storage layer was re-architected to a file-backed design on Colossus, decoupling commit latency from local disk flushes; and the surface gained the Postgres dialect and richer change streams/availability configurations. The core protocol — TrueTime, Paxos groups, commit-wait, directories — is unchanged since 2012, which is the strongest evidence that the original design got the hard parts right.

## Key Takeaways

- TrueTime is a bounded-uncertainty contract (`ε ≈ 1–7 ms`, mean ~4 ms), maintained by redundant GPS/atomic time masters and widened by drift — the entire correctness argument consumes only the bound.
- `s = max(TT.now().latest, prepare timestamps)`; acknowledge only after `TT.after(s)` — two inequalities plus a wait deliver external consistency; expected wait ~ε.
- Each tablet is a Paxos group with a leased leader, pipelined Paxos writes, a replicated lock table for 2PC, and a timestamp cache protecting read-before-write ordering.
- Directories are the placement unit: moves rebalance load and honor geo-policy; stale client caches are corrected by a one-round-trip signal.
- Safe time bounds what replicas may serve (`ts ≤ Ts.safe` for complete snapshot reads); served time is what a read observed — the basis of all staleness-bounded reads.
- F1 added SQL, caching, and lease-based online schema changes above Spanner; post-2017 Spanner became a mainstream SQL system (optimizer, file-backed storage, Postgres dialect) without changing the core protocol.

## References

- Corbett et al., ["Spanner: Google's Globally-Distributed Database"](https://research.google/pubs/pub39966/) (OSDI 2012) — TrueTime, commit-wait, directories, F1
- Bacon et al., ["Spanner: Becoming a SQL System"](https://research.google/pubs/pub47702/) (SIGMOD 2017) — optimizer, range partitioning, RSM redesign
- [Cloud Spanner documentation](https://cloud.google.com/spanner/docs/) — TrueTime ordering, read-only transactions, dialects
- [Cloud Spanner: TrueTime and external consistency](https://cloud.google.com/spanner/docs/true-time-ordering) — the customer-facing statement of the commit-wait rule
- Das et al., "Online, Asynchronous Schema Changes in F1" (VLDB 2013) — cited by title; no stable public PDF linked here
- Ongaro & Ousterhout, [In Search of an Understandable Consensus Algorithm](https://raft.github.io/raft.pdf) (USENIX ATC 2014) — ReadIndex/lease reads, the open-source analogue of Spanner's lease-read reasoning
- Lamport, ["Paxos Made Simple"](https://www.microsoft.com/en-us/research/publication/paxos-made-simple/) — the group-communication substrate

## Cross-References

- [Spanner (overview)](../fundamentals/spanner.md) — the survey-level treatment: tablets, SQL layer, schema, pitfalls.
- [TrueTime](../fundamentals/truetime.md) — the API, hardware, and the standard critiques.
- [Megastore](../fundamentals/megastore.md) — the system Spanner replaced and its entity-group consistency model.
- [CockroachDB architecture](./cockroachdb-architecture.md) — the open-source analogue: HLC + uncertainty restarts instead of commit-wait.
- [Clocks & ordering](../advanced/clocks-ordering.md) — the theory behind bounded-uncertainty reasoning.
- [Percolator](../fundamentals/percolator.md) — the Google transaction design that avoided TrueTime by centralizing timestamps.
- [Calvin & determinism](./calvin-and-deterministic.md) — the ordering-by-log alternative to ordering-by-time.
