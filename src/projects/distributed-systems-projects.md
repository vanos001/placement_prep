# Distributed Systems Project Implementation Guides

Hands-on projects that build distributed systems from scratch. Each project forces you to grapple with the core challenges: consensus, partitioning, fault tolerance, and network programming. These complement the ideas in [project-ideas.md](project-ideas.md) by providing deep implementation roadmaps.

---

## 1. Distributed Key-Value Store

### What to Build
A multi-node key-value store with linearizable reads and writes, automatic leader election, log replication, and client library with retry logic. This is essentially building a mini etcd or a simplified Redis Cluster.

### Why It Matters
This is the foundational distributed systems project. It teaches you that distributed state is fundamentally harder than in-memory state — network partitions, partial failures, and consistency trade-offs are real problems you'll encounter in production.

### Suggested Tech Stack
- **Language**: Go (goroutines + channels for concurrency, net package for networking)
- **RPC**: gRPC (protobuf)
- **Consensus**: Implement Raft yourself (see project #2)
- **Storage**: BoltDB or badger (embedded key-value) for persistent WAL and snapshots
- **Testing**: Docker Compose to spin up 5-node cluster

### Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Node 1   │     │  Node 2   │     │  Node 3   │
│ (Leader)  │◄───►│(Follower) │◄───►│(Follower) │
│           │     │           │     │           │
│ - State   │     │ - Log     │     │ - Log     │
│ Machine   │     │ - Apply   │     │ - Apply   │
└─────┬─────┘     └─────┬─────┘     └─────┬─────┘
      │                 │                 │
      └─────────────────┼─────────────────┘
                        │
                  Client Requests → Leader
                  Follower Redirect → Leader
```

### Implementation Roadmap
1. **Week 1**: Single-node key-value store with WAL (write-ahead log) and in-memory state machine
2. **Week 2**: Implement Raft leader election and log replication between 3 nodes
3. **Week 3**: Add client library with leader discovery, retry on redirect, linearizable reads (read index or lease read)
4. **Week 4**: Snapshots for log compaction, membership changes (add/remove nodes), multi-raft

### Key Challenges
- **Split brain prevention**: Raft's term + vote mechanism ensures at most one leader
- **Log consistency**: leader must not overwrite committed entries; followers must reject entries from old terms
- **Snapshot transfer**: large snapshots must be streamed, not sent in one RPC

### Interview Discussion Points
- "What happens when the leader and one follower are partitioned?" → majority quorum ensures safety
- "How do you handle slow followers?" → leader tracks `nextIndex` per follower, sends missing entries
- "Linearizable vs. eventually consistent reads" → read through leader or read index protocol

### Difficulty: Very Hard | Estimated Time: 4–6 weeks

---

## 2. Raft Consensus Implementation

### What to Build
A clean, standalone implementation of the Raft consensus algorithm following the original paper. This is the consensus layer that would plug into the KV store above, but built as a reusable library.

### Why It Matters
Raft is the most widely taught consensus algorithm and is used in etcd, Consul, and CockroachDB. Implementing it from the paper demonstrates deep understanding of distributed coordination.

### Suggested Tech Stack
- **Language**: Go or Rust
- **Testing**: The paper provides a deterministic testing framework — implement it
- **Visualization**: Simple web UI showing node states, log entries, and term changes

### Implementation Roadmap
1. **Election**: Implement RequestVote RPC, heartbeat timeout, vote granting rules
2. **Log Replication**: AppendEntries RPC, leader sends entries, followers apply
3. **Commit**: Leader advances commit index when majority have an entry
4. **Safety**: Leaders only commit entries from their own term (Figure 8 constraint)
5. **Log Compaction**: Snapshot + InstallSnapshot RPC
6. **Membership Change**: Joint consensus or single-node change

### Key Challenges
- **Getting elections right**: vote request response timing, split vote scenarios
- **Log matching property**: if two logs share an entry with same index and term, all prior entries must match
- **Figure 8 scenario**: a leader from a prior term must not commit entries using log from a different term

### Interview Discussion Points
- Walk through the state transitions: follower → candidate → leader → follower
- Explain why Raft is easier to understand than Paxos (decomposition into subproblems)
- "What is the committed index and how is it calculated?"
- "How does Raft handle network partitions?" → leader on minority partition cannot commit

### Difficulty: Very Hard | Estimated Time: 3–5 weeks

---

## 3. Distributed Cache with Consistent Hashing

### What to Build
A multi-node in-memory cache with consistent hashing for data distribution, virtual nodes for balance, replication for fault tolerance, and a client library with request routing.

### Why It Matters
Caches are everywhere — from CDN edge caches to application-level caches to database query caches. Building a distributed one teaches you about data partitioning, which is fundamental to scalability.

### Suggested Tech Stack
- **Language**: Go or Python
- **Protocol**: Custom TCP or HTTP (REST for simplicity)
- **Hashing**: Consistent hash ring with MD5 or MurmurHash
- **Eviction**: LRU or LFU with configurable max memory

### Architecture

```
┌────────┐     ┌──────────────────────────────┐
│ Client  │────►│      Consistent Hash Ring    │
└────────┘     │                              │
               │  Node A    Node C    Node B   │
               │    ◄─────────────────────►    │
               │   (virtual nodes ensure even   │
               │    distribution)               │
               └──────────────────────────────┘
```

### Implementation Roadmap
1. **Week 1**: Single-node cache with LRU eviction and TTL support
2. **Week 2**: Add consistent hash ring with virtual nodes; client routing logic
3. **Week 3**: Add replication (each key stored on N nodes), read repair
4. **Week 4**: Gossip protocol for cluster membership, node join/leave

### Key Data Structures
```python
class HashRing:
    def __init__(self, virtual_nodes: int = 150):
        self.ring = {}         # hash → node_id
        self.sorted_keys = []  # sorted hash values
        self.virtual_nodes = virtual_nodes

    def add_node(self, node_id: str):
        for i in range(self.virtual_nodes):
            key = f"{node_id}:vnode_{i}"
            hash_val = self._hash(key)
            self.ring[hash_val] = node_id
            self.sorted_keys.append(hash_val)
        self.sorted_keys.sort()

    def get_node(self, key: str) -> str:
        hash_val = self._hash(key)
        # Binary search for first node >= hash_val
        idx = bisect_left(self.sorted_keys, hash_val)
        if idx == len(self.sorted_keys):
            idx = 0  # wrap around
        return self.ring[self.sorted_keys[idx]]
```

### Interview Discussion Points
- "Why consistent hashing over modulo-based partitioning?" → minimal data movement on node changes
- "How many virtual nodes per physical node?" → typically 100-200; trade-off between balance and metadata size
- "What happens when a node fails?" → its keys are re-hashed to the next node; replication mitigates data loss

### Difficulty: Hard | Estimated Time: 3–4 weeks

---

## 4. Event Sourcing System

### What to Build
An event-sourced application (e.g., a bank account or order management system) where the state is derived from an immutable sequence of events. Includes an event store, event bus for publishing, projectors for building read models, and snapshots for performance.

### Why It Matters
Event sourcing is used in financial systems, audit-heavy applications, and CQRS architectures. It teaches you to think about state as a sequence of facts rather than a single mutable record.

### Suggested Tech Stack
- **Language**: Python (FastAPI) or Java (Spring)
- **Event Store**: PostgreSQL (append-only table) or Kafka
- **Projection**: Read model in PostgreSQL (denormalized views)
- **Snapshot Store**: PostgreSQL or Redis

### Architecture

```
Command → Command Handler → Event Store (append events)
                                  │
                              Event Bus
                                  │
                           ┌──────┼──────┐
                           ▼      ▼      ▼
                      Projector Projector Projector
                        │        │        │
                        ▼        ▼        ▼
                    Read Model Read Model Read Model
```

### Implementation Roadmap
1. **Week 1**: Event store (append-only PostgreSQL table), event serialization
2. **Week 2**: Aggregate root pattern (BankAccount), command validation, event generation
3. **Week 3**: Event bus (in-process pub/sub or Kafka), projectors for read models
4. **Week 4**: Snapshots (every N events, store full state to avoid replay), event replay

### Key Design Patterns
- **Aggregate Root**: enforces invariants, is the only entity that can produce events
- **Event Store**: immutable, append-only, ordered by sequence number
- **Projection**: subscribes to events, builds denormalized read model
- **Snapshot**: stores aggregate state at point-in-time, reduces replay cost

### Interview Discussion Points
- "Why event sourcing over traditional CRUD?" → full audit trail, temporal queries, replayability
- "How do you handle event schema evolution?" → versioned events, upcasting
- "What about eventual consistency in read models?" → accept delay, show staleness indicator
- "How do you handle command validation that requires reading state?" → validate against latest state snapshot

### Difficulty: Hard | Estimated Time: 3–4 weeks

---

## 5. Chat Server with Rooms

### What to Build
A TCP-based chat server supporting multiple rooms, user registration/nicknames, room creation/joining/leaving, message history per room, and private messaging. Extend to WebSocket for browser clients.

### Why It Matters
Chat servers are a classic network programming problem that teaches you about connection management, concurrency, message broadcasting, and stateful server design.

### Suggested Tech Stack
- **Language**: Go (net package for TCP, gorilla/websocket for WS) or Python (asyncio)
- **Protocol**: Custom text protocol or WebSocket frames
- **Storage**: In-memory (Redis for persistence if needed)

### Architecture

```
Client A ──► Server ──► Room "general" ──► Client B
Client C ──► Server ──► Room "random"  ──► Client D
                          │
                    Message History
                    (per room, bounded)
```

### Implementation Roadmap
1. **Week 1**: TCP server accepting connections, simple echo server
2. **Week 2**: Room management, nickname registration, public messaging with broadcast
3. **Week 3**: Private messaging, message history (bounded ring buffer per room)
4. **Week 4**: WebSocket support, presence (online/offline), typing indicators

### Key Challenges
- **Broadcasting to all room members**: maintain a map of room → connected clients; use channels for non-blocking fan-out
- **Connection cleanup**: detect disconnects (TCP RST, heartbeat/ping-pong)
- **Message ordering**: per-room ordering is sufficient (no global ordering needed)

### Interview Discussion Points
- "How do you detect disconnected clients?" → TCP keepalive, periodic ping, or read deadline
- "How do you scale beyond one server?" → Redis pub/sub for cross-server message routing
- "What's the difference between TCP and WebSocket for this use case?"
- "How do you handle message history storage at scale?" → bounded buffer, oldest-drop, or persistent storage with pagination

### Difficulty: Intermediate-Hard | Estimated Time: 2–3 weeks

---

## How to Choose Your Project

| Your Goal | Recommended Projects |
|---|---|
| Learn consensus and replication | #1 Distributed KV Store, #2 Raft Implementation |
| Understand data partitioning | #3 Distributed Cache |
| Learn event-driven architecture | #4 Event Sourcing System |
| Practice network programming | #5 Chat Server |
| Maximum learning (do all) | Start with #5 (easiest), then #3, then #1/#2 (hardest) |

## Reading Prerequisites

Before starting these projects, you should be comfortable with:
- **TCP/IP basics** (sockets, connections, ports)
- **Concurrency primitives** (threads, locks, channels)
- **Serialization** (JSON, protobuf)
- **Basic database operations** (SQL, indexing)
- **Distributed systems fundamentals** (CAP theorem, consistency models)
