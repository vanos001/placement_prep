# Quorum Systems — Advanced Topics

> **Reference papers**: Malkhi et al. (2001) "Byzantine Quorum Systems"; Gifford (1979) "Weighted Voting"; Naor & Wool (1998)

## Quorum System Fundamentals

A **quorum system** over a universe of `n` processes is a collection of subsets (quorums) such that every pair of quorums intersects. This intersection property is the core mechanism that prevents conflicting decisions.

```
Universe U = {1, 2, 3, 4, 5}
Quorums Q = {{1,2,3}, {1,4,5}, {2,3,4}, {1,2,5}, {3,4,5}}

  {1,2,3} ∩ {1,4,5} = {1}  ✓  (non-empty)
  {2,3,4} ∩ {1,4,5} = {4}  ✓
  Every pair intersects → no two disjoint quorums
```

> **Interview Angle**: "Why do quorums need to intersect?" The intersection guarantees that any two operations that both achieve quorum share at least one common node. That common node acts as a "witness" — it has seen the latest state from the first operation and will report it to the second, ensuring the second operation sees at least as recent a state. This is the fundamental reason quorum reads see the latest write.

## Weighted Quorums (Gifford, 1979)

In many systems, not all replicas are equal. Some nodes may be faster, have more storage, or be more reliable. **Weighted voting** (Gifford's scheme) assigns votes to nodes and defines read and write quorums based on total vote counts.

### Formal Definition

- Each node `i` is assigned a weight `w_i` (number of votes)
- Total votes: `W = Σ w_i`
- A **write quorum** `Q_w` must satisfy: `Σ_{i ∈ Q_w} w_i > W/2`
- A **read quorum** `Q_r` must satisfy: `Σ_{i ∈ Q_r} w_i + Σ_{i ∈ Q_w} w_i > W`
- This ensures: `Q_r ∩ Q_w ≠ ∅` (intersection property)

### Example: Tiered Storage

```
Nodes:     A(5)  B(3)  C(2)  D(2)  E(1)   Total W = 13

Write quorum: must have > 6.5 votes  → at least 7
Read quorum:  must have + write > 13  → if write=7, read ≥ 7

  Write {A,B} = 8 votes  ✓   (fast: just the two strong nodes)
  Read  {A,C,D,E} = 10 votes ✓
  Intersection: {A}  ✓
```

This is used in practice by systems that place replicas across tiers (e.g., hot/warm/cold storage). Dynamo-style systems use a simplified version where all nodes have weight 1, but the concept extends naturally.

## Read/Write Quorum Tradeoffs

The classic tradeoff between read and write quorum sizes in a system with `N` replicas (all weight 1):

| Strategy | `W` (write) | `R` (read) | Intersection | Consistency | Availability | Latency |
|----------|-------------|------------|---------------|-------------|-------------|----------|
| W + R > N | W | R | Guaranteed | Strong (linearizable if single-leader) | High (flexible) | Tunable |
| W = N, R = 1 | N | 1 | All writes | Strongest | Write-sensitive | Fast reads, slow writes |
| W = 1, R = N | 1 | N | All reads | Weak (stale reads OK) | Read-sensitive | Fast writes, slow reads |
| W = ⌈N/2⌉+1, R = ⌈N/2⌉ | Majority | Majority | 1 node minimum | Strong | Balanced | Balanced |

### Dynamo's Tunable Consistency

Amazon Dynamo uses `(N, R, W)` where `N` is the replication factor, `R` is the minimum successful read responses, and `W` is the minimum successful write acknowledgments. When `R + W > N`, you get strong consistency; otherwise, you trade consistency for latency.

```python
# Dynamo-style quorum check
N = 3  # replication factor
R = 2  # read quorum
W = 2  # write quorum  → R + W = 4 > 3 ✓ strong consistency

def write(key, value):
    responses = asyncio.gather(*[
        send_to_replica(i, PUT, key, value) for i in preferred_nodes(key)
    ])
    successful = sum(1 for r in responses if r.ok)
    return successful >= W  # return to client

def read(key):
    responses = asyncio.gather(*[
        send_to_replica(i, GET, key) for i in preferred_nodes(key)
    ])
    successful = [r for r in responses if r.ok]
    if len(successful) < R:
        raise UnavailableError()
    # Resolve conflicts among successful responses
    return resolve(successful)  # version vector merge, LWW, etc.
```

## Quorum Intersection Properties

### Dissemination Quorum Systems

A quorum system has the **dissemination property** if every process belongs to at least one quorum. This ensures that every process's state is potentially included in decisions. This is trivially satisfied by majority quorums but must be explicitly verified for non-majority systems.

### Resilience

The **resilience** of a quorum system is the maximum number of failures `f` such that at least one quorum remains entirely available. For majority quorums on `n` nodes: `f = ⌊(n-1)/2⌋`.

### Load & Capacity

- **Load**: the maximum access probability of any single node (lower is better)
- **Capacity**: 1/load (higher is better — how many total operations the system can handle)
- Majority quorums on `n` nodes have load `1/⌈(n+1)/2⌉`, which is near-optimal
- Grid quorums (choosing a full row and full column in an `m × m` grid) can achieve lower load but are more complex

### Grid Quorum Example

```
  4×4 Grid (16 nodes)
  ┌───┬───┬───┬───┐
  │ a │ b │ c │ d │  Row 0
  ├───┼───┼───┼───┤
  │ e │ f │ g │ h │  Row 1
  ├───┼───┼───┼───┤
  │ i │ j │ k │ l │  Row 2
  ├───┼───┼───┼───┤
  │ m │ n │ o │ p │  Row 3
  └───┴───┴───┴───┘

Quorum = one full row + one full column
  e.g., Row 0 ∪ Col 2 = {a,b,c,d, c,g,k,o}
  Size = 7, but any two such quorums intersect
  (a row and a column always share exactly one cell)
  Resilience: up to 3 failures can still form a quorum
```

## Witness Replicas and Asymmetric Quorum Configurations

Everything above assumes replicas are symmetric: every voting node stores data and can serve reads. Production systems break this symmetry in both directions, and the two broken shapes are exact inverses of each other:

- A **witness** (voting, data-less) participates in consensus but stores no user data.
- A **read-only replica** (non-voting, full data) stores everything but never votes.

Each exists because disaster tolerance and read capacity are different problems: failover needs *votes*, serving queries needs *bytes*, and you don't always need both from the same machine.

### What a witness is, precisely

The Megastore paper (CIDR 2011, §4.4.3) gives the canonical definition: *"Witnesses vote in Paxos rounds and store the write-ahead log, but do not apply the log and do not store entity data or indexes, so they have lower storage costs. They are effectively tie breakers and are used when there are not enough full replicas to form a quorum."* Note what a witness does hold: enough state to agree on *ordering* — the Paxos participant state and the log — but not the materialized data. Voting is cheap in bytes because a tie-breaker must only agree on which writes committed, not answer questions about them. The paper adds an operational bonus: because witnesses have no read coordinator, they never add a round-trip when they fail to acknowledge a write.

### Where witnesses exist

- **Megastore** ([deep dive](../fundamentals/megastore.md)): witnesses are "used when there are not enough full replicas to form a quorum" — the paper's architecture figure shows an instance with two full replicas and one witness, the minimal witness-assisted majority.
- **Spanner**: replication is configured from a menu of named options that includes witness placements — the OSDI'12 paper's example is *"North America, replicated 5 ways with 1 witness"*.
- **SQL Server**: a Windows Server Failover Cluster's quorum can include a witness — disk witness, file-share witness, or a **cloud witness** (a small Azure Blob Storage blob giving both datacenters an odd vote that lives in neither). Dynamic quorum then adjusts votes to the live node set. In **distributed availability groups**, each underlying cluster keeps its *own* quorum and witness — two independent majorities, coordinated at a layer above.
- **Kafka (KRaft)**: the same separation at cluster scale — the 3-or-5 **controller** nodes form a metadata quorum ("A majority of the controllers must be alive in order to maintain availability", per the Kafka docs) running Kafka's Raft implementation, while data brokers serve partitions and hold no votes on the metadata log. Voters hold metadata; brokers hold user data.
- **MongoDB**: an **arbiter** is "part of a replica set but do[es] not hold data" and exists purely "to vote in elections" — the documented cheap fix for a primary-secondary pair where a third full secondary is unaffordable.

### The asymmetric quorum math

Witnesses make the configuration **asymmetric**: they are full members of write and election quorums, but they can never appear in a read quorum, because a witness cannot serve reads. The intersection guarantee still holds — with witnesses counted in `N`, `R + W > N` still forces `R ∩ W ≠ ∅` — but the intersection can now be *a node with no data*, and that changes what a read recovers:

```
Members: A (full), B (full), C (witness)      N = 3, majority = 2
Write:   A + C acknowledge  →  committed (B will catch up)
Read:    R = {A, B}  (data replicas only — C can't serve reads)
         R ∩ {A, C} = {A}  ✓
```

Two properties worth stating explicitly in an interview:

1. **Safety is unchanged; read availability is not consensus availability.** If the read quorum's intersection with the write quorum is the witness, the reader learns the latest committed *position* and must obtain the *content* elsewhere — in Megastore's design, by catching a lagging full replica up from the witness's write-ahead log. The witness makes the *decision* survive a failure; it does not make the *data access* survive. That is why read quorums exclude witnesses even when the math would allow them.
2. **The failure envelope is thinner than three full replicas.** With (full, full, witness) you tolerate any *single* failure: lose one full replica and the survivor + witness still form a majority. But lose a full replica **and** the witness simultaneously — a realistic correlation when the witness runs in the cheapest, least-staffed third location — and one vote remains: no majority, no leader, writes stall — the same majority rule that governs [Raft leader elections](../consensus/raft.md) — and recovery is a *manual* failover or forced quorum, exactly the human intervention the witness was bought to avoid. Witness loss alone is benign (two full replicas are still a majority), which is precisely what Windows Server's dynamic quorum formalizes by shrinking the live majority instead of counting the dead witness's vote.

### When a witness saves you vs. hurts you

**Saves you:** two datacenters and a budget for one small machine in a third location. Without it, a two-node cluster partitions 1-against-1: neither side holds a majority, so safe writes stop ([leader failover and its hazards](../../dbms/distributed/replication.md)) and unsafe writes split the brain. A witness in a third fault domain turns every partition into a 2-to-1 decision, resolved automatically. Azure's cloud witness is the packaged version of this trick (a tie-breaking vote in a cloud region, for the cost of a storage blob), and Amazon RDS Multi-AZ answers the same tie-breaking problem differently: the writer plus a standby that "provides failover support, but doesn't serve read traffic", with the *RDS control plane* detecting failures and driving the promotion — arbitration as a managed service rather than an in-quorum voter.

**Hurts you:** the stall scenario above, plus a subtle operational trap — because the witness is small and "just a vote", it lands on whatever machine is free, shares a fault domain with a data replica, or lapses in maintenance, and nobody notices until the day both it and a replica fail together. Rule of thumb: a witness must live in a **third failure domain** (separate site, separate availability zone, or a managed cloud witness) or it is decoration, not protection.

### Read-only replicas: the inverse symmetry

Megastore again, in one sentence: *"Read-only replicas are the inverse of witnesses: they are non-voting replicas that contain full snapshots of the data."* They exist to serve stale-tolerant reads across geographies without touching write latency — and, critically, they contribute **nothing to fault tolerance**. Because they hold no vote, they can neither break a tie nor complete a majority: adding read-only replicas to a two-node cluster changes read capacity, not election math, and cannot prevent split brain. (Raft's *learners* — log-catch-up members excluded from voting — are the same shape, and Raft membership changes are how you promote one when you need its vote; see [Raft Membership Changes](../consensus/raft-membership-changes.md).) The design takeaway is the symmetry itself: when you need fault tolerance for free-ish, add a **witness**; when you need read capacity for free-ish, add a **read-only replica** — and never confuse which one fixes a split-brain review finding.

> **Interview Angle**: "You have two datacenters and budget for one more small VM. Where do you put it, and what do you get?" Put the witness/arbiter in a third failure domain (or a managed cloud witness). You get automatic failover for a 2-of-3 majority at near-zero storage cost — and you accept the quantified risk that losing one full replica *and* the witness at once (2-of-3 down to 1 vote) degrades you to manual failover. A fourth read-only replica in either datacenter would add read capacity but change nothing about quorum math.

## Byzantine Quorum Systems

When nodes may be **Byzantine** (arbitrarily faulty), standard quorums are insufficient because a faulty node in the intersection can lie about what it witnessed. Byzantine quorum systems (Malkhi & Reiter, 1997) add additional requirements.

### Requirements

1. **Intersection**: any two quorums share at least `2f + 1` nodes (not just 1)
2. **Correctness threshold**: with `n` total nodes and at most `f` Byzantine faults, we need `n ≥ 3f + 1`
3. The intersection must contain enough correct nodes (`f + 1`) to outvote the `f` Byzantine ones

### Why `2f + 1` Intersection?

With `f` Byzantine nodes, an intersection of size `2f + 1` guarantees at least `f + 1` correct nodes. This majority of correct nodes in the intersection can outvote the Byzantine minority and determine the true value.

### Masking Quorum System

A **masking quorum system** provides both *safety* and *availability* despite Byzantine faults:

- **Every quorum has ≥ 2f + 1 nodes** (enough to mask `f` Byzantine)
- **Any two quorums intersect in ≥ 2f + 1 nodes** (enough correct nodes in intersection)
- Minimum size: `n ≥ 4f + 1` (for both properties simultaneously)
- For just safety (non-masking): `n ≥ 3f + 1` suffices

### Comparison: Crash vs Byzantine Quorums

| Property | Crash Quorums | Byzantine Quorums |
|----------|--------------|-------------------|
| Min intersection size | 1 | `2f + 1` |
| Min total nodes for `f` faults | `2f + 1` | `3f + 1` (safety) / `4f + 1` (masking) |
| Intersection purpose | Witness latest state | Outvote Byzantine nodes |
| Example protocol | Paxos, Raft | PBFT, HotStuff |
| Overhead | 1 round trip | 2-3 round trips |

## Quorum Systems in Practice

### Cassandra's Quorum

Cassandra uses `LOCAL_QUORUM` (quorum within a single datacenter) vs. `QUORUM` (quorum across all datacenters). This is a **colocated quorum system** where quorums are constrained to subsets of the full node set.

### CockroachDB's Raft Quorums

Each range (64MB data shard) in CockroachDB has its own Raft group with 3 or 5 replicas. Quorums are standard majority. The replication layer automatically moves ranges between nodes for load balancing.

### Spanner's Paxos Quorums

Google Spanner uses Paxos groups (one per data shard) with 3-5 replicas. Read quorums can be avoided entirely when reading from the leader (which serves stale reads by default) or when using `read-only transactions` that acquire a timestamp and read from any replica.

> **Interview Angle**: "Design a quorum system for a globally distributed key-value store with datacenters in US, EU, and Asia. Each DC has 5 nodes." Use a hierarchical quorum: each DC runs a local quorum (majority of 5 = 3), and writes must achieve quorum in at least 2 out of 3 DCs. This gives `W ≥ 2 DCs × 3 nodes = 6 nodes minimum`. Reads need quorum from any 1 DC (3 nodes). Total: 15 nodes, tolerates 1 full DC failure + 1 node failure in each remaining DC. Cross-reference: see [consistency models](../fundamentals/consistency.md) for consistency guarantees.

## References

- Baker et al., "Megastore: Providing Scalable, Highly Available Storage for Interactive Services", CIDR 2011 — §4.4.3 witness and read-only replica definitions — https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/36971.pdf
- Corbett et al., "Spanner: Google's Globally-Distributed Database", OSDI 2012 — replication configurations with witnesses — https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi2012.pdf
- Microsoft Azure: *Deploy a Cloud Witness for a Failover Cluster* — https://learn.microsoft.com/en-us/windows-server/failover-clustering/deploy-cloud-witness
- Microsoft SQL Server: *WSFC Quorum Modes and Voting Configuration* — https://learn.microsoft.com/en-us/sql/sql-server/failover-clusters/windows/wsfc-quorum-modes-and-voting-configuration-sql-server
- Microsoft SQL Server: *Distributed Availability Groups* — https://learn.microsoft.com/en-us/sql/database-engine/availability-groups/windows/distributed-availability-groups
- Apache Kafka documentation: *KRaft* (controller metadata quorum) — https://kafka.apache.org/43/operations/kraft/
- MongoDB Manual: *Add an Arbiter to a Self-Managed Replica Set* — https://www.mongodb.com/docs/manual/tutorial/add-replica-set-arbiter/
- AWS: *Multi-AZ deployments for Amazon RDS* — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html
