# Raft

## Overview

Raft is a consensus algorithm designed to be **understandable** while being equivalent to Paxos in correctness and performance. Created by Diego Ongaro and John Ousterhout in 2014, Raft has become the dominant consensus algorithm in modern distributed systems, used by etcd (Kubernetes), CockroachDB, TiKV, Consul, and many others.

## Detailed Explanation

### Why Raft?

```mermaid
flowchart LR
    A[Paxos] -->|Hard to understand<br/>Hard to implement| B[Raft]
    B -->|Designed for<br/>understandability| C[Widely Adopted]

    style A fill:#ffcdd2
    style B fill:#c8e6c9
    style C fill:#c8e6c9
```

Raft decomposes consensus into three independent subproblems:
1. **Leader Election** — Choosing a leader
2. **Log Replication** — Replicating log entries
3. **Safety** — Ensuring consistency

### Raft Roles

```mermaid
flowchart TD
    A[Node States] --> B[Follower<br/>Passive, responds to leader]
    A --> C[Candidate<br/>Requests votes to become leader]
    A --> D[Leader<br/>Handles all client requests]

    B -->|Election timeout| C
    C -->|Wins election| D
    C -->|Discovers higher term| B
    D -->|Discovers higher term| B
    D -->|Heartbeat timeout| B

    style D fill:#c8e6c9
    style B fill:#e1f5fe
    style C fill:#fff3e0
```

| Role | Behavior |
|------|----------|
| **Follower** | Passive; responds to leader heartbeats and candidate votes |
| **Candidate** | Actively requests votes to become leader |
| **Leader** | Handles client requests, replicates log to followers |

### Term (Election Epoch)

Raft divides time into **terms**, each beginning with an election:

```
Term 1: Leader A (elected)
Term 2: Leader B (A failed, B elected)
Term 3: Split vote, no leader elected
Term 4: Leader C (elected after retry)
```

**Term serves as a logical clock:**
- Each node tracks the current term
- Higher term = more recent
- Stale leaders are detected by term comparison

### Leader Election

```mermaid
sequenceDiagram
    participant F1 as Follower 1
    participant F2 as Follower 2
    participant F3 as Follower 3

    Note over F1,F3: Leader fails, heartbeats stop

    F1->>F1: Election timeout (150-300ms)
    F1->>F1: Become candidate, term=2
    F1->>F2: RequestVote(term=2, lastLogIndex, lastLogTerm)
    F1->>F3: RequestVote(term=2, lastLogIndex, lastLogTerm)
    F2-->>F1: VoteGranted(term=2)
    F3-->>F1: VoteGranted(term=2)
    Note over F1: Got majority (2/3), become leader
    F1->>F2: AppendEntries (heartbeat)
    F1->>F3: AppendEntries (heartbeat)
```

**Election rules:**
1. Follower becomes candidate if no heartbeat received within **election timeout**
2. Candidate increments term and votes for itself
3. Candidate sends RequestVote to all other nodes
4. A node votes for the candidate if:
   - Candidate's term ≥ node's current term
   - Node hasn't voted in this term yet
   - Candidate's log is at least as up-to-date as node's log
5. If majority votes received → become leader
6. If another leader discovered (higher term) → become follower

**Split vote handling:**
```
If no candidate gets majority:
  - Election timeout expires
  - New term begins
  - Random timeout prevents repeated split votes

Random timeout: 150-300ms (each node picks random value)
Probability of repeated split votes: very low
```

### Log Replication

```mermaid
sequenceDiagram
    participant C as Client
    participant L as Leader
    participant F1 as Follower 1
    participant F2 as Follower 2

    C->>L: SET x = 5
    L->>L: Append to log: [term=1, index=1, cmd: SET x=5]
    L->>F1: AppendEntries(term=1, prevLogIndex=0, prevLogTerm=0, entries=[SET x=5])
    L->>F2: AppendEntries(term=1, prevLogIndex=0, prevLogTerm=0, entries=[SET x=5])
    F1-->>L: Success(term=1, matchIndex=1)
    F2-->>L: Success(term=1, matchIndex=1)
    Note over L: Majority (2/3) acknowledged → committed
    L->>L: Apply to state machine
    L-->>C: OK
    L->>F1: Heartbeat (commitIndex=1)
    L->>F2: Heartbeat (commitIndex=1)
```

**Log entry structure:**
```
┌───────┬───────┬───────────────────┐
│ Term  │ Index │ Command           │
├───────┼───────┼───────────────────┤
│   1   │   1   │ SET x = 5         │
│   1   │   2   │ SET y = 10        │
│   2   │   3   │ SET x = 7         │
│   3   │   4   │ SET z = 15        │
└───────┴───────┴───────────────────┘
```

**Log matching property:**
- If two entries at the same index have the same term, all preceding entries are identical
- This ensures consistency across replicas

### AppendEntries RPC

```python
# Leader → Follower
AppendEntries(
    term,              # Leader's current term
    leaderId,          # So follower can redirect clients
    prevLogIndex,      # Index of entry before new ones
    prevLogTerm,       # Term of entry at prevLogIndex
    entries[],         # Log entries to append (empty for heartbeat)
    leaderCommit       # Leader's commit index
)

# Follower → Leader response
Response(
    term,              # Follower's current term (for leader to update)
    success,           # True if entry was appended
    matchIndex         # Follower's last log index
)
```

**Consistency check:**
```
If follower doesn't have entry at prevLogIndex:
  → Return false
  → Leader decrements nextIndex and retries
  → Eventually finds matching point
  → Overwrites follower's divergent entries
```

### Safety Guarantees

Raft ensures these safety properties:

| Property | Description |
|----------|-------------|
| **Election Safety** | At most one leader per term |
| **Leader Append-Only** | Leader never overwrites its own log |
| **Log Matching** | If two logs have entry with same index and term, all preceding entries match |
| **Leader Completeness** | If entry committed in term T, all future leaders have that entry |
| **State Machine Safety** | If node applies entry at index, no other node applies different entry at same index |

### Log Compaction (Snapshotting)

Over time, the log grows unboundedly. Raft uses **snapshots** to compact:

```mermaid
flowchart LR
    A[Log: 1-1000] --> B[Snapshot<br/>at index 1000]
    B --> C[Log: 1001-2000]
    C --> D[Snapshot<br/>at index 2000]
    D --> E[Log: 2001-...]

    style B fill:#c8e6c9
    style D fill:#c8e6c9
```

```
Snapshot:
  - Contains state machine state at a point in time
  - Includes last included index and term
  - Old log entries before snapshot are discarded

InstallSnapshot RPC:
  - Leader sends snapshot to lagging follower
  - Follower replaces its state with snapshot
```

### Membership Changes

Changing the cluster membership (adding/removing nodes) requires care:

```mermaid
flowchart TD
    A["Old Config: {A, B, C}"] --> B["Joint Consensus:<br/>{A,B,C} and {A,B,C,D}"]
    B --> C["New Config: {A, B, C, D}"]

    style B fill:#fff3e0
```

**Joint consensus (Raft's approach):**
1. Leader creates log entry with **joint configuration** (old + new)
2. Decisions require majority from BOTH old and new configs
3. Once joint config is committed, create log entry with new config only
4. Once new config is committed, old nodes can be removed

### Raft in Practice

**etcd (Kubernetes' key-value store):**
```
3 or 5 node cluster
Leader handles all writes
Followers replicate log
Used for: configuration, service discovery, leader election
```

**CockroachDB:**
```
Each range (shard) has its own Raft group
Leader handles reads and writes for the range
Multi-range transactions use 2PC across Raft groups
```

**TiKV (TiDB's storage layer):**
```
Region = Raft group (default 96MB)
Leader handles reads/writes
Replicas on different machines
Auto-rebalancing when nodes added/removed
```

## Interview Questions

### Q1: How does Raft ensure only one leader is elected per term?
**Answer:** Raft's election rule requires a candidate to receive votes from a majority of nodes. Each node votes at most once per term. Since any two majorities overlap by at least one node, it's impossible for two candidates to both get a majority in the same term. If a candidate discovers a higher term, it steps down to follower.

### Q2: What happens when a Raft leader fails?
**Answer:**
1. Followers stop receiving heartbeats
2. A follower's election timeout expires (150-300ms, randomized)
3. The follower becomes a candidate, increments term, requests votes
4. If it gets a majority, it becomes the new leader
5. The new leader accepts client requests and replicates the log

During the election (~200ms), the cluster is unavailable for writes. Reads may be served by followers (stale) or rejected (linearizable reads).

### Q3: How does Raft handle network partitions?
**Answer:** In a partition:
- The partition with the majority of nodes elects a new leader and continues operating
- The minority partition's leader (if any) discovers the higher term and steps down
- When the partition heals, the stale nodes catch up via log replication

Example: 5 nodes, partition into {A,B} and {C,D,E}:
- {C,D,E} elects a new leader (3 nodes = majority)
- {A,B} can't elect a leader (2 nodes < majority)
- When healed, A and B replicate from the leader

### Q4: What is the "election timeout" and how is it chosen?
**Answer:** The election timeout is the time a follower waits before becoming a candidate. It must be:
- **Long enough** to avoid unnecessary elections (heartbeat interval << election timeout)
- **Short enough** to detect failures quickly
- **Randomized** to prevent split votes

Typical values:
- Heartbeat interval: 50-100ms
- Election timeout: 150-300ms (random per node)
- Rule: broadcastTime << electionTimeout << MTBF (mean time between failures)

### Q5: How does Raft differ from Paxos?
**Answer:**
- **Leader**: Raft has a strong leader; Paxos can have competing proposers
- **Log ordering**: Raft has strictly sequential logs; Paxos can have gaps
- **Understandability**: Raft is designed for understandability; Paxos is notoriously complex
- **Specification**: Raft is fully specified; Paxos leaves many details to the implementer
- **Membership changes**: Raft has joint consensus; Paxos requires external mechanisms

Raft is equivalent to Multi-Paxos in power but much easier to implement correctly.

## Deep Dive: Leader Election Algorithm

### Election Timeout Mechanism

```
Election timeout = random value in [T, 2T]
  Typical T = 150ms
  So timeout = 150-300ms (random per node)

Why random?
  - Prevents all nodes from starting election simultaneously
  - One node will timeout first, request votes, become leader
  - Probability of repeated split votes: very low

Timing constraints:
  broadcastTime << electionTimeout << MTBF
  
  broadcastTime: time for a message to reach all nodes (~1-10ms on LAN)
  electionTimeout: 150-300ms
  MTBF: mean time between failures (months/years)
```

### Detailed Election Walkthrough

```
Initial state: Node A is leader (term=1), B and C are followers

1. Leader A crashes

2. B's election timeout fires (after 200ms):
   B transitions: FOLLOWER → CANDIDATE
   B.currentTerm = 2
   B.votedFor = B (votes for itself)
   B sends RequestVote to A and C:
     RequestVote {
       term: 2,
       candidateId: B,
       lastLogIndex: 5,
       lastLogTerm: 1
     }

3. C receives RequestVote from B:
   Check: B.term (2) >= C.term (1) → OK
   Check: C hasn't voted in term 2 → OK
   Check: B's log is at least as up-to-date → OK
   C votes for B: VoteGranted { term: 2, voteGranted: true }
   C resets its election timeout

4. A is down, no response

5. B receives VoteGranted from C:
   B has 2 votes (self + C) = majority of 3
   B becomes LEADER for term 2
   B sends heartbeats to A and C

6. A comes back online:
   A receives heartbeat from B with term=2
   A.term (1) < B.term (2)
   A steps down: LEADER → FOLLOWER
   A updates A.term = 2
```

### Log Up-to-Date Check

When a follower receives a RequestVote, it checks if the candidate's log is at least as up-to-date:

```
Compare:
  1. lastLogTerm: candidate's term of last log entry
     - Higher term = more up-to-date
  2. lastLogIndex: candidate's index of last log entry
     - If terms are equal, higher index = more up-to-date

Rule: Vote YES if:
  (candidate.lastLogTerm > my.lastLogTerm) OR
  (candidate.lastLogTerm == my.lastLogTerm AND
   candidate.lastLogIndex >= my.lastLogIndex)

Why this matters:
  Prevents a node with an incomplete log from becoming leader.
  If candidate is missing committed entries, it would lose data.
```

## Deep Dive: Log Replication

### Log Entry Structure

```
Each log entry contains:
  ┌──────────────────────────────────────────────┐
  │ Term │ Index │ Command │ Committed? │
  ├──────────────────────────────────────────────┤
  │  1   │   1   │ SET x=5 │     ✓      │
  │  1   │   2   │ SET y=10│     ✓      │
  │  2   │   3   │ SET x=7 │     ✓      │
  │  3   │   4   │ SET z=15│     ✗      │
  └──────────────────────────────────────────────┘

Term: when the entry was created
Index: position in the log (monotonically increasing)
Command: the state machine operation
```

### Commit Rules

```
An entry is committed when:
  1. It has been replicated to a MAJORITY of nodes
  2. The leader that created the entry is still the current leader

Rule 2 is critical:
  If leader for term T replicates entry to majority, then crashes,
  A new leader for term T+1 might NOT have that entry.
  But the entry IS committed (majority had it).
  The new leader WILL have it (because log up-to-date check).

Scenario that demonstrates the rule:
  Term 1: Leader S1 replicates entry at index 2 to S1, S2 (not S3)
  S1 crashes
  Term 2: S3 wins election (gets votes from S3, S4, S5)
  S3 doesn't have entry at index 2!
  S3 replicates its own entry at index 2 (term 2)
  S3 crashes before committing
  Term 3: S1 wins election again
  S1 has entry [term=1, index=2]
  S3 has entry [term=2, index=2]
  S1 replicates [term=1, index=2] to S3 → overwrites S3's entry

  This is SAFE because S3's entry was never committed.
```

### AppendEntries Consistency Check

```
The AppendEntries RPC includes:
  prevLogIndex: index of entry immediately before new entries
  prevLogTerm: term of entry at prevLogIndex

Follower checks:
  1. Does follower have an entry at prevLogIndex?
  2. If yes, does its term match prevLogTerm?

If either check fails:
  → Return false
  → Leader decrements nextIndex[follower]
  → Retry AppendEntries
  → Eventually finds matching point
  → Overwrites follower's divergent entries

Example:
  Leader log: [T1] [T1] [T2] [T3] [T3]
  Follower log: [T1] [T1] [T2] [T4]  ← diverges at index 4

  Leader sends AppendEntries(prevLogIndex=4, prevLogTerm=T3)
  Follower: entry at index 4 has term T4 ≠ T3 → REJECT
  Leader decrements nextIndex to 3
  Leader sends AppendEntries(prevLogIndex=3, prevLogTerm=T2)
  Follower: entry at index 3 has term T2 = T2 → MATCH
  Leader overwrites follower's entry at index 4 with [T3]
  Leader sends entry at index 5 [T3]
```

## Deep Dive: Safety Guarantees

### Election Safety Proof

```
Theorem: At most one leader per term.

Proof:
  - Each node votes at most once per term
  - A candidate needs majority of votes to become leader
  - Any two majorities overlap by at least one node
  - That node can't vote for two different candidates in the same term
  - Therefore, at most one candidate can get majority in any term
  - ∎
```

### Leader Completeness Proof

```
Theorem: If entry e is committed in term T, all leaders for terms > T have e.

Proof:
  - Entry e committed in term T means it was replicated to majority M1
  - Leader for term T+1 was elected by majority M2
  - M1 ∩ M2 ≠ ∅ (majorities overlap)
  - At least one node in M2 has entry e
  - Leader election requires candidate's log to be at least as up-to-date
  - Therefore the new leader must have entry e
  - By induction, all future leaders have e
  - ∎
```

### State Machine Safety

```
Theorem: If a node applies entry e at index i, no other node applies a different entry at index i.

Proof:
  - An entry is applied only after it's committed
  - Committed entries are present in all future leaders (Leader Completeness)
  - Leaders never overwrite committed entries (they only append)
  - Therefore all nodes apply the same entry at each index
  - ∎
```

## Raft vs Paxos vs ZAB

```
Aspect          │ Raft              │ Multi-Paxos        │ ZAB
────────────────┼───────────────────┼────────────────────┼─────────────────────
Leader          │ Strong leader     │ No fixed leader    │ Strong leader
Log ordering    │ Strictly ordered  │ Gaps possible      │ Strictly ordered
Understandability│ High             │ Low (notoriously)  │ Medium
Specification   │ Complete          │ Incomplete         │ Complete
Membership      │ Joint consensus   │ External           │ Atomic broadcast
Used by         │ etcd, CockroachDB │ Spanner, Chubby    │ ZooKeeper
```

## Common Mistakes

- ❌ **Not randomizing election timeouts** — Causes repeated split votes
- ❌ **Setting election timeout too short** — Causes unnecessary elections during normal operation
- ❌ **Not handling the old leader** — Old leader may still think it's leader (stale term)
- ❌ **Ignoring log compaction** — Log grows unboundedly without snapshots
- ❌ **Confusing commit with apply** — Entry is committed when majority acknowledges; applied when state machine executes it
- ❌ **Not understanding the commit rule** — Leader can't commit entries from previous terms directly; it must commit a new entry from its own term first
- ❌ **Assuming Raft is always available** — Raft requires majority; minority partition is unavailable

## Summary

| Aspect | Details |
|--------|---------|
| **Purpose** | Understandable consensus algorithm |
| **Subproblems** | Leader election, log replication, safety |
| **Leader** | Required, handles all writes |
| **Terms** | Logical clock for detecting stale leaders |
| **Log** | Replicated, strictly ordered, snapshotted |
| **Used by** | etcd, CockroachDB, TiKV, Consul |

Raft has become the standard consensus algorithm for modern distributed systems, replacing Paxos in most new implementations due to its clarity and well-defined specification.

## Cross-References

- [Paxos](./paxos.md) — the classic consensus algorithm
- [Consensus](./consensus.md) — the consensus problem
- [Replication](./replication.md) — Raft enables strong replication
- [Consistency Models](./consistency.md) — what Raft provides
- [WAL](../internals/wal.md) — write-ahead log (Raft log is similar)


## Cross References

- [Paxos](paxos.md)
- [Raft (Distributed)](../../distributed/consensus/raft.md)
- [Consensus](consensus.md)
