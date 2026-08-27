# Megastore: Entity Groups with Paxos Replication

## The Problem It Solved

By the late 2000s Google had Bigtable — a horizontally scalable, replicated wide-column store — and the Ad Serving System (ADS), a fleet of hundreds of hand-sharded MySQL databases behind a per-record ODBC proxy — transactional, but operationally fragile and increasingly hard to scale. Bigtable gave scale and availability, but its replication was asynchronous and eventually consistent, there were no multi-row transactions, and interactive web applications kept reimplementing the same consistency scaffolding badly. ADS, meanwhile, proved that strong transactions at interactive latency were worth enormous engineering effort.

Megastore, published at CIDR 2011 and deployed behind "95+ production apps" at Google (including App Engine's Datastore, Blogger, and Google Apps), was the intermediate point: **relational-style schemas and synchronous replication, at Bigtable scale, by giving up one thing — transactions across partitions in the common case.** Its central move is the **entity group**: a partition of related records that is the unit of ACID transactions, the unit of Paxos replication, and the unit of data placement — all at once. Within an entity group you get fully serializable, synchronously replicated transactions across datacenters. Across entity groups, you get asynchronous messaging (Megastore queues) or an expensive, explicitly-avoided two-phase commit.

## Data Model: Entity Groups as the Universal Unit

Megastore's schema language looks object-like: entity types (ETs) with typed properties, where one entity type is declared a **entity group root** and other entities are its children. Children must reference a root (the "foreign key"), and together a root plus its descendants form one entity group. A photo-sharing app:

```text
User            <- entity group root (one per user)
 ├── Profile
 ├── Photo      (child entities: keyed by (user_id, photo_id))
 └── Album

FollowerGraph   <- a *separate* entity group (social edges are not
                   transactionally coupled to photo content)
```

Design consequences, all deliberate:

- **No joins.** Queries hit one entity type at a time. Anything a query needs is stored redundantly where it will be read — the paper is explicit that this is a Bigtable-style denormalization choice, not an oversight.
- **Indexes come in two flavors.** *Entity-group-local indexes* live inside the group's storage and are updated atomically with the group's transaction. *Global indexes* (e.g., "search photos by tag across all users") are updated **asynchronously** and may briefly miss recent commits — the price of indexing across transaction boundaries without distributed commits.
- **Partitioning is by application semantics, not by hash.** A Dynamo-style system hashes keys to spread load evenly; Megastore groups by *ownership* so that "update profile + insert photo + update album count" is one local transaction instead of a distributed one.

## Replication: One Paxos Log per Entity Group

Each entity group's writes form a totally ordered log, agreed by **Paxos** running across the replicas of that group. There is no global write order in the system — two different users' entity groups can commit in different orders at different replicas, and that is fine, because no transaction ever spans them. This is the load-bearing trick: Paxos is usually considered too slow for high-throughput writes, but per-partition Paxos with only local-lead writes is fast.

```text
Entity group "user 4711" replicated across three regions

   Region A (write)        Region B              Region C
  ┌────────────┐        ┌────────────┐        ┌────────────┐
  │ Paxos log  │        │ Paxos log  │        │ Paxos log  │
  │ pos 41: W3 │◀─agree─│ pos 41: W3 │◀─agree─│ pos 41: W3 │
  │ pos 42: W7 │◀─agree─│ pos 42: W7 │◀─agree─│ pos 42: W7 │
  └────────────┘        └────────────┘        └────────────┘
   leader for this EG is local in A; B and C are catch-up
   copies that apply the agreed log asynchronously
```

Structural details worth remembering:

- **Full replicas** store the data and participate in consensus. **Witness replicas** participate in the Paxos vote but store no data — they exist to guarantee a quorum survives a region loss without paying for full data copies.
- The **Paxos leader for a given entity group is placed near the client** that writes it. A user's writes go to "her" datacenter, which is the leader for her groups: the WAN consensus round-trip is paid once per write for the quorum, but the protocol's latency is dominated by one local-commit-plus-propagation path rather than a cross-ocean transaction coordinator.
- **Timestamps are per-log positions.** Every committed write gets the next timestamp in the group's log; all reads and writes within the group respect that order, and each write also records the *last* timestamp it observed (so a later write can detect a concurrent one — Megastore uses this for its commit protocol).

## Reads: The Coordinator Fast Path

Synchronous replication would be brutally slow for reads if every read paid a quorum round-trip. Megastore avoids that with **coordinators**: a per-datacenter service that tracks which entity groups the local replica has observed as up to date.

A **current (strong) read** takes the fast path when two conditions hold: the local coordinator says the group is up-to-date locally, and the local replica confirms it has applied the group's latest known log position. Then the read is served from local storage with no network round-trip — strong consistency at local-disk speed.

```python
# Read-path decision, distilled from the Megastore paper (Section 4.2).

def resolve_read(requested_consistency, coordinator_ok, local_caught_up):
    """Return the plan for satisfying a read on the local replica.

    requested_consistency: 'current' | 'snapshot' | 'inconsistent'
    coordinator_ok:        local coordinator believes this EG is current here
    local_caught_up:       local replica applied the EG's latest log position
    """
    if requested_consistency == "inconsistent":
        return "serve from local cache/index (may be stale)"

    if requested_consistency == "snapshot":
        return "serve from local replica at a recent log timestamp"

    # requested_consistency == "current"
    if coordinator_ok and local_caught_up:
        return "fast path: strong read served locally"
    if coordinator_ok and not local_caught_up:
        return "catch up: pull missing log positions, then serve locally"
    return "slow path: consult a majority quorum for latest position, " \
           "update coordinator, then serve"
```

When the fast path fails — the coordinator is unsure, or the local replica lags — the read falls back to consulting a majority of replicas to find the latest committed log position, catching up the local copy, and *then* serving. Correctness never depends on the coordinator being right; it depends on the coordinator being **conservative**. A coordinator that has any doubt (leader change, missed heartbeat, partial failure) immediately **invalidates** the entity group locally, forcing the slow path until the group is re-synced. The paper describes this fail-closed behavior explicitly: coordinators may hurt availability of the fast path, never correctness.

## Writes: Per-Group Paxos in Practice

A write to one entity group proceeds through the group's Paxos pipeline:

1. The client picks a leader replica (its local one if possible) and submits the mutation with its **last observed timestamp** (for conflict detection).
2. The leader runs Paxos for the next log position: acceptors across full/witness replicas agree on *the value for this position* (the "leader's value" rule resolves collisions — a competing proposer's value gets replayed into the log before ours).
3. Once committed in the log, the write is applied at each replica asynchronously, secondary indexes update, and the local coordinator is told this group is now current locally.

Two entity groups never synchronize here. If an application truly needs atomicity across groups, it has two tools:

- **Megastore queues** — asynchronous, at-least-once message queues between entity groups, with transactional delivery to the destination group (a queue enqueue can be atomic with the sender's group write; the receiving group processes messages as its own transactions). This covers the common cross-group workflow: "user 4711 posted a photo" → "enqueue update to each follower's feed entity group."
- **Two-phase commit** — supported but slow (the paper: "slow" enough that the schema guidance says design it away). The root of one group acts as coordinator; witnesses can block progress, so 2PC is a last resort.

## Availability: Full vs. Partial

Megastore distinguishes **full availability** (all replicas reachable: everything works locally everywhere) from **partial availability** (some replicas down: reads are served by whichever replicas are up, writes require a majority quorum and may fail if the group's quorum is unreachable). Witness replicas are the bridge: they let three full replicas + two witnesses still form a majority after losing one full replica, without the storage cost of five full copies.

The cost of the design is **cross-group isolation**: a read of one entity group cannot observe another group's uncommitted state, and there is no global snapshot. Applications that need "read your writes across groups" must route through queues or accept eventual consistency for those parts of the schema.

## Megastore vs. Its Neighbors

| Aspect | Bigtable | Megastore | Spanner |
|---|---|---|---|
| Replication | async, eventual | sync Paxos per entity group | sync Paxos per Paxos group |
| Transactions | none | per entity group (ACID) | multi-group via TrueTime + 2PC |
| Cross-partition ops | n/a | queues (async), 2PC (slow) | native, externally consistent |
| Global read ordering | no | no (per-group only) | yes (globally consistent timestamps) |
| Schema/indexes | denormalized | relational-ish, local + async global indexes | relational (F1 on top) |
| Load partitioning | hash/ordered | semantic (entity groups) | semantic (with movement) |

Megastore was the step that made Google comfortable with interactive, strongly-consistent-per-user storage; Spanner took the same per-group Paxos skeleton and added TrueTime so that *cross-group* transactions and consistent global snapshots became practical (see the Spanner and TrueTime pages in this section). App Engine's Datastore — the most direct Megastore descendant — still exposes the entity-group model (in XG mode: up to 25 groups per transaction) to this day.

## Interview Angles

- **Why is per-group Paxos fast when "consensus" is famous for being slow?** Because the leader is co-located with the writer, the value proposal collides only under contention *within one group*, and reads don't pay consensus at all on the fast path — the coordinator makes strong reads local.
- **What breaks if the coordinator lies (says current when it isn't)?** Strong reads could miss a committed write. Hence coordinators must be conservative: any uncertainty triggers invalidation and the quorum path. Availability of the fast path is negotiable; correctness is not.
- **Schema your chat app for Megastore.** One EG per conversation (root + messages + participants), one EG per user profile; fan-out via queues to recipient EGs; a global async index for search. Justify why message send must not be 2PC.
- **Why did Spanner supersede Megastore?** TrueTime turned "per-group serializable, cross-group async" into "globally ordered with bounded uncertainty," enabling multi-group transactions and consistent reads without coordinator gymnastics — at the price of waiting out clock uncertainty on writes.
- **Compare partitioning strategies:** hash partitioning (Dynamo) spreads load but destroys transaction locality; entity groups preserve locality but accept hot-group risk; explain witness replicas and selective replication as the mitigations.

## References

- [Baker et al., "Megastore: Providing Scalable, Highly Available Storage for Interactive Services", CIDR 2011](https://research.google/pubs/pub36971/)
- [Google Cloud Datastore (Megastore-descendant) concepts overview](https://cloud.google.com/datastore/docs/concepts/overview)
- [Corbett et al., "Spanner: Google's Globally-Distributed Database", OSDI 2012](https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi2012.pdf)
- [Chang et al., "Bigtable: A Distributed Storage System for Structured Data", OSDI 2006](https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf)
