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
