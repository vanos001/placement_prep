# CRDT Internals — State, Operations, Deltas, and GC

> **Reference papers**: Shapiro, Preguiça, Baquero & Zawirski (2011) "Conflict-Free Replicated Data Types"; Almeida, Shoker & Baquero (2018) "Delta State CRDTs"; Kleppmann & Beresford (2017) on CRDT GC

## CRDT Foundations Recap

A CRDT is a data structure designed for distributed systems that guarantees **eventual consistency without coordination**. Formally, a state-based CRDT (CvRDT) is a join-semilattice `(S, ⊑, ⊔)` where `⊔` (merge) is: (1) commutative, (2) associative, (3) idempotent. These three properties guarantee convergence regardless of message order, duplication, or delay.

See [CRDT basics](../fundamentals/crdts.md) for introductory material on G-Counter, PN-Counter, G-Set, OR-Set, and LWW-Register.

## State-Based CRDTs (CvRDTs)

### Semilattice Structure

Every CvRDT defines a partial order `⊑` ("less or equal") on its state space `S`:

```
Merge: s3 = s1 ⊔ s2
  - s1 ⊑ s3  (merge includes all of s1)
  - s2 ⊑ s3  (merge includes all of s2)
  - s1 ⊔ s2 = s2 ⊔ s1  (commutative)
  - (s1 ⊔ s2) ⊔ s3 = s1 ⊔ (s2 ⊔ s3)  (associative)
  - s ⊔ s = s  (idempotent)
```

### Join Semilattice for G-Counter

```python
class GCounter:
    def __init__(self, node_id, n):
        self.node_id = node_id
        self.counts = [0] * n  # one slot per node
    
    def increment(self):
        self.counts[self.node_id] += 1
    
    def value(self):
        return sum(self.counts)
    
    def merge(self, other):
        # ⊔ = component-wise max
        result = GCounter(self.node_id, len(self.counts))
        result.counts = [max(a, b) for a, b in zip(self.counts, other.counts)]
        return result
    
    def __le__(self, other):
        # ⊑ = component-wise ≤
        return all(a <= b for a, b in zip(self.counts, other.counts))
```

### CvRDT Communication Model

State-based CRDTs exchange their **entire state** and merge on receipt. This is simple but expensive for large states. The payload is `O(|S|)` per sync.

```
Node A: state S_A ──────── send full state ──────→ Node B: S_B' = S_B ⊔ S_A
Node B: state S_B ──────── send full state ──────→ Node A: S_A' = S_A ⊔ S_B

Both converge to the same state (by properties of ⊔)
```

## Operation-Based CRDTs (CmRDTs)

Operation-based CRDTs (CmRDTs) transmit **operations** rather than full state. Operations are delivered through a **causal broadcast** channel that ensures:

1. **Causal delivery**: if `op1 → op2` (causally), then `op1` is delivered before `op2`
2. **No duplication**: each operation is delivered exactly once

### CmRDT vs CvRDT Tradeoffs

| Aspect | CvRDT (State-based) | CmRDT (Op-based) |
|--------|---------------------|-------------------|
| Message size | O(state size) | O(op size) — typically O(1) |
| Delivery requirement | Best-effort (idempotent) | Causal broadcast (exactly-once) |
| Duplicate handling | Merge is idempotent | Must deduplicate |
| Bandwidth | Higher (full state) | Lower (just ops) |
| Complexity | Simpler (no delivery tracking) | Needs causal broadcast, op buffers |

### Op-Based G-Counter

```python
class OpBasedGCounter:
    def __init__(self, node_id):
        self.node_id = node_id
        self.counts = {}  # node_id → count
    
    def increment(self):
        op = ('inc', self.node_id)  # operation to broadcast
        self.apply(op)
        broadcast(op)  # causal broadcast
    
    def apply(self, op):
        _, nid = op
        self.counts[nid] = self.counts.get(nid, 0) + 1
    
    def value(self):
        return sum(self.counts.values())
```

The causal broadcast channel can be implemented using vector clocks to track which operations a node has seen and only delivering operations whose causal dependencies are satisfied.

## Delta-State CRDTs

**Delta-state CRDTs** (Almeida, Shoker, Baquero, 2018) combine the best of both approaches: they send **deltas** (small patches to the state) rather than full state, while maintaining the simple best-effort delivery of CvRDTs.

### Core Idea

Instead of sending the full merged state `S ⊔ S'`, send only the **delta** `δ = S ⊔ S' \ S` (the incremental change). The delta itself is a valid CRDT state fragment that can be merged into any replica.

```
Standard CvRDT:  send(S_new)        → O(|S|) bandwidth
Delta CRDT:      send(δ = S_new ⊔ S_old - S_old)  → O(|δ|) bandwidth
```

### Delta G-Counter

```python
class DeltaGCounter:
    def __init__(self, node_id, n):
        self.node_id = node_id
        self.counts = [0] * n
    
    def increment(self):
        # Generate delta: only the changed component
        delta = [0] * len(self.counts)
        delta[self.node_id] = 1
        self.counts = merge(self.counts, delta)
        broadcast(delta)  # best-effort, can be lost/duplicated
    
    def merge_delta(self, delta):
        # Delta is just another state fragment; merge is component-wise max
        self.counts = [max(a, b) for a, b in zip(self.counts, delta)]
```

### Delta Mutability Rules

A delta `δ` can only be produced by a single **source** node (the one that generated the operation). This is crucial for correctness:

1. **Propagate**: a received delta can be forwarded to other nodes (it's just another CRDT fragment)
2. **Don't mutate**: once generated, a delta is immutable
3. **Merge semantics**: merging deltas follows the same `⊔` as full states

### Delta CRDT in Practice

- **Riak**: uses delta CRDTs internally since Riak 2.0 for improved bandwidth efficiency
- **Automerge**: a JavaScript CRDT library using delta-state for collaborative editing
- **Yjs**: uses a delta encoding approach for its YATA CRDT algorithm
- **Redis CRDT** (Redis Labs): supports delta-mode for OR-Set and other types

## CRDT Garbage Collection

A fundamental problem with CRDTs is that metadata grows **monotonically and forever**. Every node that ever incremented a G-Counter adds a permanent slot. Every element added to an OR-Set adds a permanent unique tag.

### Why GC is Hard

The CRDT merge function must be commutative, associative, and idempotent. If we remove metadata from the state, a late-arriving message containing that metadata might be incorrectly handled:

```
1. Node A adds element "X" with tag tag-5
2. GC removes tag-5 (it's been observed everywhere)
3. Node B (was partitioned) sends its state including tag-5
4. Without tag-5 in local metadata, the merge might:
   - Re-add "X" (wrong, it was deleted!)
   - Lose information about A's operation
```

### Stable Metadata

An element of CRDT metadata is **stable** when all replicas have incorporated it. Once stable, it can be safely removed.

### GC Approaches

#### 1. Global Stabilization with Vector Clocks

Maintain a vector clock of the minimum knowledge across all replicas. Any metadata older than this min-VC is stable and can be GC'd.

```python
# Simplified: track the minimum vector clock across all known replicas
class CRDTWithGC:
    def __init__(self, node_id, n):
        self.state = CRDTState()
        self.node_id = node_id
        self.n = n
        self.min_vc = [0] * n  # minimum VC across all replicas
    
    def on_sync(self, other_vc, other_state):
        # Update min_vc: the minimum of our min and the other's full VC
        for i in range(self.n):
            self.min_vc[i] = min(self.min_vc[i], other_vc[i])
        self.state.merge(other_state)
    
    def garbage_collect(self):
        # Remove any metadata that is dominated by min_vc
        self.state.prune_older_than(self.min_vc)
```

#### 2. Tombstone-Based GC with Epochs

Divide time into epochs. At the start of each epoch, all replicas agree (via consensus) on a stable frontier. Metadata from previous epochs can be garbage collected.

- Used by: **Riak** (with AAE — Active Anti-Entropy and Merkle tree sync)
- Requires: periodic coordination to agree on the frontier

#### 3. Entropy-Based GC (Kleppmann & Beresford, 2017)

Use a **dot-based encoding** where each piece of metadata is tagged with a unique dot `(node, counter)`. Dots are garbage collected when:
- The dot's node is known to have advanced past that counter
- This is determined through periodic anti-entropy

This avoids needing global consensus for GC while still providing safety.

#### 4. Compact Representation

Instead of storing individual entries, store a **run-length encoding** or **interval representation** of the causal history. This doesn't remove entries but dramatically reduces space.

```
Full:    {A:1, A:2, A:3, A:4, B:1, B:2}
Compact: {A:[1,4], B:[1,2]}
```

### GC Comparison

| Approach | Coordination Needed | GC Precision | Overhead | Use Case |
|----------|-------------------|--------------|----------|----------|
| Min VC | Periodic sync | Exact | O(n) VC per node | Small groups |
| Epoch/consensus | Per-epoch consensus | Exact | Consensus round | Systems with consensus anyway |
| Entropy/dot | Periodic anti-entropy | Best-effort | Anti-entropy cost | Large, dynamic groups |
| Compact repr | None | N/A (no removal) | Encoding/decoding | Any system with monotonic metadata |

## Advanced CRDT Types

### LWW-Element-Set

A set where each element has a timestamp, and deletion is modeled by adding a **tombstone** with a later timestamp. On merge, for each element, keep whichever entry (add or delete) has the latest timestamp. Requires synchronized or hybrid logical clocks for meaningful ordering.

### OR-Set with Observed-Remove

The Observed-Remove Set tracks each element's addition with a unique tag. When removing an element, only the tags that the remover has **observed** are removed. Tags the remover hasn't seen (from concurrent additions) survive. This prevents the "add-wins vs remove-wins" dilemma by making remove only affect what you've seen.

### PN-Counter (Positive-Negative Counter)

Combines two G-Counters: one for increments, one for decrements. The value is `sum(increments) - sum(decrements)`. Merging is component-wise max on both counters independently.

### Sequence CRDTs

For collaborative text editing (like Google Docs), sequence CRDTs maintain an ordered sequence that supports insertions and deletions at arbitrary positions:

- **RGA (Replicated Growable Array)**: each character is tagged with a unique ID and a reference to the character after which it was inserted. On merge, characters with the same insertion position are ordered by their unique ID.
- **LSEQ**: uses a logical addressing scheme based on a balanced n-ary tree to assign positions
- **YATA (Yjs)**: uses an item-based approach with left/right origin pointers

> **Interview Angle**: "Why doesn't everyone use CRDTs instead of consensus?" CRDTs trade off consistency for availability — they provide eventual but not linearizable consistency. Many workloads (banking, inventory, configuration) need linearizable semantics. Additionally, CRDT metadata grows unboundedly, and the data types are limited (you can't easily CRDT-encode arbitrary transactions). The best approach is often hybrid: use consensus for the critical path and CRDTs for lower-assurance data. Cross-reference: [consensus protocols](../consensus/raft.md) for the coordination side.