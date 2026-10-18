# "You must leave SQL to scale"

## Overview

This page examines the claim that scaling a system past a certain size
requires abandoning relational databases — the "SQL doesn't scale" meme
that drove a decade of architecture decisions. The reality is that the
relational model never was the bottleneck: the *deployment shape* was.
Read replicas, partitioning, and sharding scale classic SQL engines, and a
generation of distributed SQL systems (Vitess, CockroachDB, Spanner) scales
the relational model itself across nodes. What actually forces a move is
write throughput beyond one primary or a dataset beyond one box — and even
then the switch is about operational cost, not capability. This page
states the claim fairly, does the scaling arithmetic, and locates the real
trade.

## The Claim, Stated Fairly

The strongest common form of the claim is: "Relational databases scale
vertically only; past a modest size you must move to NoSQL (or equivalent)
horizontally scalable stores, because joins, ACID transactions, and the
SQL layer itself cannot be distributed." Stated this way, the claim is not
a caricature; it is the operating assumption behind many 2008–2015-era
migrations, and it is still repeated in design reviews as "we'll outgrow
Postgres, so let's start on a document store."

The claim deserves its fairness because it has a documented origin story.
A single-node database does have hard ceilings, and in the late 2000s the
pragmatic path around them was memcached, denormalization, and then
Dynamo-style stores — because the tools for scaling *SQL* horizontally were
research projects or in-house systems. The meme is a fossil of a true
observation about the *tools available at the time*.

## Verdict

**False.** "Must leave SQL" is a universal necessity claim, and the
counterexamples are planetary in scale: YouTube runs SQL at massive scale
through Vitess, Google built Spanner as a globally distributed SQL system,
and CockroachDB delivers serializable SQL across nodes. What is true is
narrower: single-node deployments have ceilings, and scaling *out* carries
an operational cost. Necessity became capability confusion.

## Why People Believe It

The kernel of truth is threefold. First, the single-node ceilings are real:
one primary takes one write path — bounded by WAL flush throughput, lock
contention, and the write set the buffer pool can hold — and one disk
array holds one dataset. Second, the historical moment was real: in the
era when the meme formed, horizontally scalable SQL required in-house
engineering (YouTube's sharding layer, Google's internals), while off-the-
shelf NoSQL offered horizontal scale by download. Third, some workloads
genuinely fit key-value access better, and those migrations succeeded
visibly, in public.

What disappears in compression is the distinction between the *model* and
the *deployment*. The relational model — tables, constraints, SQL — says
nothing about how many machines hold the tables. Ceilings attach to
specific single-node engines under specific workloads, not to SQL.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "SQL can't scale out" | Read replicas scale reads; partitioning/sharding scales datasets; distributed SQL (Vitess, CockroachDB, Spanner) scales the relational model itself |
| "Joins force NoSQL" | Joins get routed, colocated, or denormalized by design; the planner's work, not the model, is the constraint |
| "NoSQL scales, SQL doesn't" | Both scale when sharded; the real axes are write throughput, dataset size, and consistency requirements |
| "The move is free" | Sharding costs operational complexity (cross-shard transactions, resharding, scatter-gather); distributed SQL costs a consensus latency floor and a new ops envelope |
| "Vertical is dead" | Scale up first: a bigger box is often the cheapest order of magnitude you will ever buy |

The correct sentence: "A *single-node* database has hard ceilings. You
relieve them with replicas (reads), partitioning (datasets), and sharding
or distributed SQL (writes), and you choose among those by workload — the
relational model travels through every option."

## Where It Breaks

**Read scaling: replicas do the arithmetic.** One primary serving 10,000
reads/s with headroom can feed N replicas over a single WAL stream; eight
read replicas raise read capacity to roughly 80–90k reads/s (reasoning
arithmetic: fan-out is near-linear until replication lag or client fan-in
bites). That is an order of magnitude of read scaling without leaving SQL,
without changing the schema, and with a single operational primitive —
and it is why most "we outgrew SQL" incidents are, on inspection, read
capacity incidents.

**Write scaling: the actual ceiling, and what breaks it.** The honest
bottleneck is the single write path. Reasoning arithmetic (flagged, not a
benchmark): a well-tuned primary with group commit can push on the order
of 10–20k small durable writes/s; beyond that, the WAL flush budget and
single-writer apply are the walls. Sharding multiplies the wall by the
shard count: 16 shards is 16 independent write paths — a 16× ceiling — and
the data still speaks SQL, with a routing layer (Vitess-style) or an
engine that shards internally (CockroachDB ranges, Spanner tablets) doing
the bookkeeping. Dataset math behaves the same way: a 30 TB dataset that
outgrows the largest practical node becomes 8 shards of ~3.75 TB — a
capacity decision, orthogonal to the query language.

**The existence proofs end the argument.** Vitess began as YouTube's
MySQL sharding middleware and now runs database tiers at YouTube and,
publicly documented, at GitHub; it serves MySQL wire-compatible SQL across
hundreds of shards. Spanner (Corbett et al., OSDI 2012) provides a
relational, SQL-queryable database with external consistency across the
planet. CockroachDB replicates ranges by consensus and defaults to
serializable isolation. "SQL doesn't scale" is contradicted by systems
named after the scale at which they run.

**The real cost is operational — price it honestly.** Hand-sharded SQL
buys write ceiling and pays in cross-shard transactions, scatter-gather
queries, resharding migrations, hot-shard management, and per-shard
secondary indexes. Distributed SQL pays a different bill: every write
crosses a consensus round, so a multi-region commit has a latency floor of
roughly one WAN round trip between the nearest quorum members — call it
tens of milliseconds each way (light-in-fiber arithmetic, e.g., ~4,000 km
at ~200,000 km/s in fiber is ~20 ms one way before equipment), and reads
that must respect consensus ordering pay similar floors. None of this is
"SQL can't scale"; all of it is "distributed systems charge for
distribution," a bill NoSQL pays too.

## Practical Implications

- Order the ladder by cost: scale up, add read replicas, partition within
  the engine, shard across engines or adopt distributed SQL — and
  actually hit each rung before buying the next.
- Name the ceiling before migrating: write throughput per primary, dataset
  size per box, or read fan-out. "We might get big" is not a ceiling.
- If you shard, choose the shard key for the dominant access pattern and
  design for resharding on day one; the key is the decision, not the
  engine swap.
- Distributed SQL changes latency budgets, not just capacity: put quorum
  members' geography on the whiteboard before committing to multi-region
  writes.
- Analytics at scale is a different workload — columnar warehouses, which
  are also SQL — not a reason to migrate the OLTP store.
- In interviews, replace "SQL doesn't scale" with "single nodes have
  ceilings; here is the ladder" — then answer the follow-up about shard
  keys, which is the question that was actually being asked.

## Interview Questions

### "We're at 5 TB and worried about scale — should we start on Cassandra instead of Postgres?"

Start with the workload: read-to-write ratio, working-set size, access
patterns, consistency needs. Reads scale with replicas; 5 TB fits a large
node or partitions cleanly; Cassandra is justified by write-heavy,
key-value-shaped access and multi-datacenter needs, not by raw size.
A strong answer walks the ladder (scale up, replicas, partitioning,
sharding) and prices each rung before recommending a jump off the
relational model.

### Where is the actual scaling ceiling of a single relational primary?

The write path: WAL flush throughput, single-writer apply, lock/commit
contention, and buffer-pool fit for the hot set — reasoning arithmetic puts
well-tuned small-write throughput in the 10–20k durable writes/s range on
solid hardware. Reads extend via replication; capacity extends via
partitioning; only sustained write throughput past one primary's budget
forces distribution. Ceiling first, migration second.

### What do you give up when you adopt distributed SQL like CockroachDB or Vitess?

Distribution costs, not model costs: consensus latency floors on writes
(one WAN round trip minimum per multi-region commit), cross-shard
transaction coordination, resharding operations, and a new operational
envelope (cluster management, replica placement, recovery drills).
Hand-sharding (Vitess) adds routing and schema-migration complexity in the
application tier; engine-native sharding (CockroachDB) hides routing but
fixes more of the architecture. The honest trade is operational, and it
exists in NoSQL too.

## Key Takeaways

- The ceiling belongs to single-node *deployments*, not to the relational
  model; replicas, partitioning, and sharding all keep SQL intact.
- Distributed SQL (Vitess at YouTube/GitHub scale, Spanner, CockroachDB)
  is the standing counterexample to "SQL can't scale out".
- Only two things truly force distribution: write throughput beyond one
  primary and datasets beyond one box. Everything else is a ladder rung.
- The migration's price is operational — shard keys, cross-shard
  transactions, resharding, consensus latency floors — and NoSQL pays the
  same class of bill.
- Correct the sentence, keep the caution: "single nodes have ceilings;
  plan the ladder" scales better than the meme ever did.

## Cross-References

- [Why-Not Handbook: Scaling Up vs Out](../why-not-handbook/scaling-up-vs-out.md)
  — the vertical/horizontal decision this claim collapses
- [Why-Not Handbook: Database Choices](../why-not-handbook/database-choices.md)
  — the full engine-family decision framework
- [More replicas, more consistent?](./more-replicas-more-consistency.md)
  — the consistency price of the read-scaling rung
- [Sharding](../../dbms/distributed/sharding.md) — the mechanics behind
  the write-scaling rung
- [Replication](../../dbms/distributed/replication.md) — primary/replica
  fundamentals the ladder assumes
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- J. C. Corbett et al. *Spanner: Google's Globally-Distributed Database*.
  OSDI 2012 — globally distributed, SQL-queryable, externally consistent.
- R. Taft et al. *CockroachDB: The Resilient Geo-Distributed SQL Database*.
  Proceedings of the VLDB Endowment, 2020 — consensus-backed ranges and
  serializable-by-default SQL, cited by title.
- Vitess documentation — MySQL-compatible sharding middleware.
  <https://vitess.io/docs/>
- CockroachDB documentation.
  <https://www.cockroachlabs.com/docs/stable>
- GitHub Engineering. Public write-ups of GitHub's adoption of Vitess for
  core MySQL workloads, cited by title (github.blog).
