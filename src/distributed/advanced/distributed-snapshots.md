# Distributed Snapshots & Coordination Primitives

> **Reference papers**: Chandy & Lamport (1985) "Distributed Snapshots"; Dijkstra (1965) mutual exclusion; Ricart & Agrawala (1981); Suzuki & Kasami (1985)

## Chandy-Lamport Distributed Snapshot Algorithm

The Chandy-Lamport algorithm records a **consistent global snapshot** of a distributed system — a set of local states that could have occurred simultaneously in some sequential execution consistent with the happened-before relation.

### System Model

- **Reliable FIFO channels** between processes (the algorithm's key assumption)
- Processes communicate only via message passing
- Channels may contain in-transit messages that must be captured

### Algorithm

1. **Initiator** records its own local state, then sends a **marker message** on each of its outgoing channels
2. When a process `p` **receives a marker** on channel `c` for the **first time**:
   - Record `p`'s local state
   - Record the state of channel `c` as the sequence of messages received on `c` **before** the marker
   - Send a marker on each of `p`'s other outgoing channels
3. When `p` receives a marker on channel `c` **subsequently** (already recorded its state):
   - Record the state of channel `c` as empty (all messages before the marker have been recorded, all after are part of the "after" state)
4. The algorithm terminates when all processes have recorded their state

### Pseudocode

```python
# On process p
def initiate_snapshot():
    my_state = record_local_state()
    for channel in outgoing_channels:
        send(channel, MARKER)

def receive(channel, message):
    if message == MARKER:
        if not snapshot_initiated:
            my_state = record_local_state()
            channel_states[channel] = []  # messages received so far
            for ch in outgoing_channels:
                if ch != channel:
                    send(ch, MARKER)
        else:
            channel_states[channel] = []  # no pre-marker messages remain
    else:
        if snapshot_initiated and not channel_state_finalized[channel]:
            channel_states[channel].append(message)
        deliver_to_application(message)
```

### Why FIFO is Required

```
Timeline of messages on channel A→B:

  m1   m2   MARKER   m3   m4   m5
  │    │      │       │    │    │
  ├────┼──────┼───────┼────┼────┤
  │    │      │       │    │    │
  ✓ in snapshot   ✗ post-snapshot

Without FIFO: MARKER could arrive before m1 or m2
  → channel state would miss messages that causally precede the snapshot
```

### Consistency Proof Sketch

The snapshot is consistent because: (1) if event `e1` is in the snapshot and `e1 → e2` (happened-before), then `e2` is also in the snapshot. This holds because the marker on each channel acts as a cut point — all messages sent before the marker are captured, and any message received before a marker must have been sent before the marker (FIFO guarantee).

> **Interview Angle**: "How is the Chandy-Lamport snapshot used in practice?" The most prominent use is **Flink's checkpointing** for distributed stream processing. Flink injects barrier markers into the data stream (analogous to Chandy-Lamport markers). When a barrier passes through an operator, the operator snapshots its state. Downstream operators wait for barriers from all inputs before snapshotting. This is Chandy-Lamport adapted for dataflow graphs rather than general message-passing.

## Checkpointing & Recovery

### Uncoordinated Checkpointing

Each process checkpoints independently at arbitrary times. On recovery, the system must find a **consistent set of checkpoints** (a "recovery line") using techniques like:
- **Domino effect detection**: checkpoint C of process P may depend on a later checkpoint of process Q, creating chains. If Q's later checkpoint is invalid, P's is too.
- **Rollback propagation**: cascading rollbacks to find a consistent global state

### Coordinated Checkpointing

All processes checkpoint simultaneously using Chandy-Lamport or a two-phase protocol. Simpler recovery (just restore the last global checkpoint) but requires coordination overhead.

### Comparison

| Aspect | Uncoordinated | Coordinated |
|--------|--------------|-------------|
| Normal operation overhead | Minimal | Marker propagation cost |
| Recovery complexity | Finding consistent recovery line | Restore last checkpoint |
| Blocking during checkpoint | None | Slight pause |
| Domino effect risk | Yes | No |
| Used by | Chandy-Lamport variants | Flink, Spark streaming |

## Termination Detection

### Dijkstra-Scholten Algorithm

A **tree-based** algorithm for detecting when a distributed computation has terminated. The initiator maintains a spanning tree of all active processes. When a process becomes idle and all its descendants are idle, it sends an acknowledgment up the tree. Termination is detected when the root becomes idle and has received acknowledgments from all children.

### Credit-Recovery Algorithm

Each process holds a "credit" token. When a process sends a message, it must have enough credit. The initiator starts with credit equal to the total number of messages in the system. When all credit returns to the initiator and no process is active, computation has terminated.

```
Initiator: credit = 1

send message → forward credit 1 (decrement local credit)
receive message → gain credit 1
become idle → return all credit to parent

Termination: root has credit = 1 AND is idle
```

> **Interview Angle**: "Why can't you just check if all processes are idle?" Because a process might be idle but have sent a message that hasn't been delivered yet. The receiver might become active upon receiving it. You need to account for in-flight messages. This is fundamentally the same challenge as the Chandy-Lamport channel state problem.

## Mutual Exclusion in Distributed Systems

### Ricart-Agrawala Algorithm (1981)

A fully distributed mutual exclusion algorithm that uses ** Lamport-style logical clocks** to totally order requests.

#### Protocol

```
To enter critical section:
1. Increment logical clock
2. Broadcast REQUEST(ts, pid) to all processes (including self)
3. Enter CS when:
   a. Own REQUEST has been acknowledged by all processes
   b. For every other REQUEST received with (ts', pid'):
      either (ts', pid') > (ts, pid) lexicographically
n      or a REPLY has been received for it

On receiving REQUEST(ts', pid'):
1. If currently not in CS and not interested:
   → reply REPLY immediately
2. If interested and (ts', pid') < (ts, pid):
   → reply REPLY (they have priority)
3. Otherwise:
   → defer REPLY until after leaving CS

On leaving CS:
1. Send deferred REPLYs to all waiting processes
```

#### Analysis

- **Messages per CS entry**: `2(n - 1)` — `n - 1` REQUESTs and `n - 1` REPLYs
- **Synchronization delay**: 1 message delay (one round trip)
- **Fault tolerance**: no single point of failure (unlike centralized algorithms)
- **Problem**: every node receives every request, creating `O(n)` messages per entry

### Lamport's Algorithm

A precursor to Ricart-Agrawala. Uses a similar REQUEST/REPLY mechanism but with a slightly different priority scheme. Ricart-Agrawala is a simplification that reduces the message count.

### Suzuki-Kasami Algorithm (1985)

Uses **tokens** to grant access to the critical section. A single token circulates among processes. Only the token holder can enter the CS.

#### Protocol

```
Data structures:
- Token: {queue: [pid, ...], LN: [0, 0, ..., 0]}  (last sequence numbers)
- Each process: RN[j] = highest sequence number of REQUEST
  received from process j

Requesting CS:
1. Increment RN[self]
2. Broadcast REQUEST(RN[self], self) to all processes
3. Wait until token arrives
4. Enter CS

On receiving REQUEST(seq, j):
1. RN[j] = max(RN[j], seq)
2. If I have the token and my RN[j] == token.LN[j] + 1:
   → send token to process j

On receiving token:
1. Enter CS
2. Update token.LN[j] = RN[j] for all j
3. Add processes j where RN[j] == token.LN[j] + 1 to token.queue
4. If token.queue is non-empty, send token to first process in queue
```

#### Analysis

| Metric | Ricart-Agrawala | Suzuki-Kasami |
|--------|---------------|---------------|
| Messages per entry | `2(n-1)` | `n` (worst case) |
| Synchronization delay | 1 RTT | Up to n-1 hops |
| Uses token | No | Yes |

### Token-Ring Algorithm

Processes are arranged in a logical ring. A single token circulates. A process can enter the CS only when it holds the token.

```
Process layout: P1 → P2 → P3 → P4 → P1
                    ↑                       ↓
                 Token circulates clockwise

P3 wants CS → waits for token → enters CS → releases token → token goes to P4
```

- **Messages per entry**: `n` on average (wait for token to circulate, 1/N chance per hop)
- **Advantage**: very simple implementation
- **Disadvantage**: unfair in the short term (a process might wait for the token to traverse the entire ring)
- **Used in**: IBM Token Ring (historical), some embedded systems

### Mutual Exclusion Comparison

| Algorithm | Messages/Entry | Delay | Fault Tolerance | Fairness | Best For |
|-----------|--------------|-------|-----------------|----------|----------|
| Centralized | 3 | 2 | Low (single coordinator) | FIFO | Low-contention, simple systems |
| Ricart-Agrawala | `2(n-1)` | 1 RTT | High (no SPOF) | By timestamp ordering | Moderate contention |
| Suzuki-Kasami | `0` to `n` | Variable | High | FIFO | Token-based systems |
| Token-Ring | `0` to `n` | Up to `n` hops | Low (token loss = deadlock) | Fair (circular) | Low contention, ring topologies |

> **Interview Angle**: "Would you use any of these in production?" Almost never directly. In practice, distributed mutual exclusion is handled by: (1) **distributed locks** built on consensus (etcd, ZooKeeper, Chubby), (2) **leases** with fencing tokens (Spanner), or (3) **database-level locks** (SELECT FOR UPDATE). These algorithms are important for understanding the theory but are too fragile for production use without additional crash-recovery and liveness mechanisms. Cross-reference: [distributed locks](../fundamentals/distributed-locks.md).