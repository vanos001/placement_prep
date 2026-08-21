# Bully Algorithm

The Bully Algorithm is a leader-election algorithm for distributed systems, published by Hector Garcia-Molina in 1982. It elects the node with the highest ID as the leader, using a tournament-style message exchange: when a node notices the leader has failed, it broadcasts an "election" message; the highest-ID respondent that wins the tournament becomes the new leader. This page covers the message protocol, the recovery model, and why the algorithm has been largely superseded by Raft-style leader election in modern systems.

## The Model

- N nodes, each with a unique, totally-ordered ID (often a numeric ID assigned at deployment).
- Synchronous communication: every message has a known maximum delay Δ.
- Crash-stop failures: a node fails by halting and may recover later.
- No Byzantine failures.

The "bullying" behavior: when a node X with ID i sees the leader fail, X starts an election. Nodes with higher IDs "bully" X out of the running by responding — X cannot win if any higher-ID node is alive. The election proceeds until no higher-ID node is alive, and the highest alive node wins.

## The Message Protocol

Three message types:

1. **ELECTION**: A node broadcasts "I am starting an election" to all higher-ID nodes.
2. **ANSWER**: A higher-ID node replies "I am alive and I'm taking over".
3. **COORDINATOR**: The new leader broadcasts "I am the leader now".

The algorithm:

```text
Node X (notices leader L is down):
  For each node Y with ID > X.id:
    send ELECTION(X) to Y
  Wait for ANSWER within time T (typically 2Δ, the worst-case round-trip)

  If X received ANSWER from any Y:
    Wait for COORDINATOR (within another timeout)
    If no COORDINATOR received within timeout, X starts another election
  Else (no ANSWER received — X is the highest-ID alive node):
    X is the new leader
    send COORDINATOR(X) to all nodes

Node Y (receives ELECTION from X with lower ID):
  send ANSWER(Y) to X
  Y starts its own election (forwards to nodes with ID > Y.id)
  Y eventually sends COORDINATOR if Y wins

Node Z (receives COORDINATOR from W):
  Set my_leader = W
  If W.id == Z.id, ignore (Z sent the message)
```

## Worked Example

Consider a 5-node cluster with IDs 1, 2, 3, 4, 5 (where 5 is the leader). Suppose node 5 fails. The remaining nodes (1, 2, 3, 4) detect this:

```text
Step 1: Node 3 notices leader (5) is unreachable.
Step 2: Node 3 sends ELECTION(3) to nodes 4 and 5.
Step 3: Node 4 receives ELECTION(3) and replies ANSWER(4). Node 5 is dead.
        Node 4 starts its own election — sends ELECTION(4) to node 5.
        Node 5 is unreachable, no ANSWER.
        Node 4 is the highest alive node, sends COORDINATOR(4) to all.
Step 4: Node 3 (still in its wait state) receives COORDINATOR(4).
        Node 3 sets my_leader = 4.
Step 5: Nodes 1, 2 also receive COORDINATOR(4) and update.
Step 6: Node 5 (when recovered) cannot be the leader — its ID is higher
        than 4, but only by starting another election can 5 take over.
        Node 5 sends ELECTION(5) to no one (no higher IDs).
        Node 5 sends COORDINATOR(5) to all and re-takes leadership.
```

The "bullying" pattern: node 3 starts the election but node 4 (with higher ID) takes over by virtue of being higher. Node 5, when recovered, takes over from node 4 because 5 > 4.

## Recovery Behavior

When a node recovers from a crash:

1. The node starts an election if it has a higher ID than the current leader.
2. If a lower-ID node, the node waits for the next COORDINATOR message and accepts the leader.

This is asymmetric: high-ID nodes always seek leadership on recovery, while low-ID nodes always accept existing leadership. The asymmetry is the source of the algorithm's name — high-ID nodes "bully" their way to leadership.

## Cost Analysis

The worst-case message complexity:

- Node 1 initiates an election in a 5-node cluster.
- Node 1 sends ELECTION to nodes 2, 3, 4, 5 (4 messages).
- Nodes 2, 3, 4 each receive ELECTION and start their own elections.
  - Node 2 sends ELECTION to 3, 4, 5 (3 messages).
  - Node 3 sends ELECTION to 4, 5 (2 messages).
  - Node 4 sends ELECTION to 5 (1 message).
- The total ELECTION messages: O(N²) (specifically, N(N-1)/2).
- Each node that loses sends ANSWER (1 per ELECTION received, except for the eventual winner).
- The winner sends COORDINATOR to all N-1 nodes.

Total: O(N²) messages, O(N²) bytes per election.

For N=100, that's 10,000 messages per leader change. This is the algorithm's biggest weakness — it scales poorly.

## Optimizations

Several variants reduce the message complexity:

1. **Bully with broadcast**: Instead of unicast to higher IDs, broadcast ELECTION to all. Nodes that see the broadcast compare their ID and the highest wins. O(N) messages but requires a broadcast primitive (e.g., IP multicast or pub/sub).

2. **Chang-Roberts**: A token-ring election where each node sends the ELECTION message to its successor; the highest ID in the message is the new leader. O(N²) worst case but O(N) average case on a ring topology. Used in Token Ring networks and some peer-to-peer systems.

3. **Invitation Algorithm**: Each node maintains a "view" of the cluster; nodes invite each other to form groups. The invitations converge to a single group containing all alive nodes, with the highest-ID node as leader. Used in JGroups and some Java EE clusters.

## Why Bully Has Been Largely Superseded

Modern distributed systems rarely use Bully directly. Reasons:

1. **O(N²) message complexity** is unacceptable at scale. Raft's leader election is O(N) messages per term, and the term advances only when the leader fails or steps down.

2. **No safety against split-brain under partition**. If a partition separates nodes 1-2 from nodes 3-4-5, both partitions will elect their own leader (node 2 in the smaller, node 5 in the larger). The Bully algorithm provides no mechanism to detect or resolve this — it's a single-cluster algorithm.

3. **No log replication**. Bully only elects a leader; it doesn't say what the leader does with state. Real systems need a consensus protocol (Paxos, Raft) that combines leader election with log replication.

4. **Failure detection is assumed synchronous**. The algorithm assumes a known timeout Δ for "leader is dead". In asynchronous networks (the real world), this can lead to false elections and leader oscillation. Modern systems use lease-based detection with heartbeat quorums (e.g., Raft's random election timeout).

## Where Bully Still Appears

The Bully algorithm is still used in:

- **Embedded and IoT clusters** with N ≤ 10, where the protocol's simplicity outweighs its scaling cost.
- **Database failover clusters** (Oracle RAC, PostgreSQL repmgr) — the "highest-priority replica takes over" pattern is Bully by another name.
- **Service discovery systems** like Consul's "leader election" using the Serf gossip protocol — Bully is wrapped in a more sophisticated liveness layer.

## Comparison to Other Leader-Election Algorithms

| Algorithm | Message complexity | Failure detection | Topology required | Modern use |
|-----------|--------------------|---------------------|-------------------|-------------|
| Bully (1982) | O(N²) | Synchronous timeout | None (broadcast) | Embedded, IoT |
| Chang-Roberts (1979) | O(N) avg, O(N²) worst | Synchronous timeout | Ring | Token Ring |
| Raft (2014) | O(N) per term | Random timeout + heartbeat | None | etcd, Consul, CockroachDB |
| Paxos (1998) | O(N²) Prepare, O(N) per decision | View change | None | Spanner, Cassandra LWT |
| SWIM (1987) | O(N) gossip | Probabilistic | Gossip overlay | HashiCorp Consul |

## Common Pitfalls

1. **The bully is determined by ID, not by capability.** A high-ID node that is on a slow or overloaded machine becomes the leader — the algorithm has no notion of capability. Production systems use a "priority" or "weight" that takes both ID and load into account.

2. **Synchronous timeout tuning is brittle.** Too short, and slow network pings trigger false elections. Too long, and a failed leader blocks the cluster. Production systems use adaptive timeouts based on observed RTT.

3. **Recovery is racy.** When a high-ID node recovers, it starts an election immediately. But its network state may not be ready — its ELECTION messages may be dropped, and it'll wait T then re-elect. The retry loop can produce oscillation.

4. **Coordinator messages may be lost.** If the COORDINATOR broadcast is lost (e.g., network partition during broadcast), some nodes will know the new leader and some won't. The algorithm assumes reliable broadcast; real implementations add a confirmation step.

## References

- H. Garcia-Molina, "[Elections in a Distributed Computing System](https://www.cs.cornell.edu/home/livelock/theory-dc-paper.pdf)" (IEEE TOC 1982)
- Chang-Roberts, "[An improved algorithm for decentralized extrema-finding in circular configurations of processes](https://www.cs.yale.edu/homes/aspnes/papers/chang-roberts.pdf)" (CACM 1979)
- [Wikipedia: Bully algorithm](https://en.wikipedia.org/wiki/Bully_algorithm)
- [Distributed Systems: Algorithms and Protocols (Mukesh Singhal)](https://www.amazon.com/Distributed-Computing-Principles-Algorithms-Applications/dp/0471516421)
- [Raft paper (use as modern comparison)](https://raft.github.io/raft.pdf)
