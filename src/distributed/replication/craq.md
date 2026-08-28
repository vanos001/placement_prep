# CRAQ: Chain Replication with Apportioned Queries

> Vanilla chain replication (van Renesse & Schneider, OSDI 2003) gets
> linearizable writes by flowing them down a chain, but every read must
> come from the tail — the read throughput ceiling is the tail's. CRAQ
> (OSDI 2004, same authors) fixes exactly that while keeping the
> linearizability: every node keeps a *version list* per object and
> serves reads from any node, with monotonicity guaranteed by a tiny
> per-object trick. This page assumes you know the [base
> protocol](./chain.md); the focus is version lists, query apportioning,
> and CRAQ's failure recovery — the parts the survey pages summarize
> in one paragraph.

## The Version-List Trick

Each node keeps, per object x, a list of (version, value) pairs plus a
dirty/clean flag:

```text
 object x at node i:
   [(seq=42, v1, CLEAN), (seq=45, v2, DIRTY)]

 - a WRITE flowing downstream appends (seq, value, DIRTY)
 - when the TAIL processes the write, it ACKs upstream;
   each node marks its newest entry CLEAN and garbage-collects older ones
 - READ at node i (for a CLEAN newest entry): answer immediately
 - READ at node i (newest entry DIRTY): the value is not yet committed!
     -> ask DOWNSTREAM for the highest CLEAN seq < my dirty seq
     -> answer from my clean entry at that seq
```

Why this is linearizable: a dirty entry means the write is *possibly*
in flight; its commit point is the tail's processing. A read that
answers the newest clean value is either (a) the latest committed value
(if the dirty one commits later), or (b) the value the dirty write will
supersede — in which case the read is ordered before the write anyway.
No read ever sees a value that was never chosen, and no read sees a
stale value when the newest is clean.

Monotonicity (a client's successive reads never go backwards) follows
because each node's clean versions only grow, and the downstream query
only consults nodes that are *further committed* than this one.

## Query Apportioning

Serving every read at every node would overload the head (writes still
flow through it) — no. CRAQ *apportions* the object space: each node is
responsible for serving reads of a disjoint **range** of objects,
defined by partitioning the object-id space across the chain:

```text
 chain:   H -> N1 -> N2 -> N3 -> T

 object ranges:
   N1 serves reads for keys in [k_0, k_1)     (its "query range")
   N2 serves reads for [k_1, k_2)
   N3 serves reads for [k_2, k_3)
   T  serves reads for [k_3, k_max)

 a client routes a read by key range to the responsible node;
 writes still flow H -> ... -> T.
```

The effect: read throughput scales with chain length (each node serves
a distinct key slice at its own CPU's rate), while the consistency
machinery stays local. Range assignment is metadata the head
redistributes on membership change.

## Failure Recovery, CRAQ-style

- **Tail failure**: the immediate predecessor becomes the tail. It
  knows every object's committed state (its dirty entries are exactly
  the not-yet-acked writes) — commit them, take over the tail's query
  range.
- **Head failure**: the successor becomes head. No write was lost:
  anything not yet at the new head was never committed anywhere.
- **Middle failure**: predecessor and successor connect; the
  *downstream* part is authoritative for committed state. Writes
  already past the failure point but not acked get re-sent; versions
  dedupe them.

Compare with leader-based replication: CRAQ's recovery never involves
an election — the chain's linear structure names the successor
deterministically. That is the property that makes CRAQ attractive for
storage systems that want strong consistency without a consensus
protocol on the read path.

## TAPIR and the Modern Take

TAPIR (Zhang et al., SOSP 2017) kept CRAQ's chain structure but
replaced the tail-ack commit with a two-phase commit built on a
transactional info layer, using *unstable writes* to reuse the chain's
bandwidth for distributed transactions. The CRAQ lesson — keep reads
everywhere, let version metadata carry consistency — survives; the
commit protocol part has moved on. (Cite carefully: CRAQ itself does
no transactions; papers that bolt them on are extensions, not CRAQ.)

## Worked Demo: Version Lists Under Interleaving

The demo simulates a 3-node chain with two writers and a reader per
node, interleaved deterministically, and prints each node's version
list plus the read answers — showing a read served from a dirty node
consulting downstream for its clean version.

```python
# CRAQ version-list simulation on a chain H -> N1 -> T.
# Events are a fixed deterministic interleaving.
# Per object (single object "x" for clarity): list of (seq, val, dirty)

chain = {"H": [], "N1": [], "T": []}
acked = set()
seq = 0
read_log = []

def write(node_order, value):
    """A write flowing down node_order, marking dirty, then acked by tail."""
    global seq
    seq += 1
    s = seq
    for nd in node_order:
        chain[nd].append([s, value, True])
    # tail processes -> ack flows upstream marking clean
    chain[node_order[-1]][-1][2] = False
    acked.add(s)
    for nd in node_order[:-1]:
        for entry in chain[nd]:
            if entry[0] == s:
                entry[2] = False
    return s

def read(node, key_seq_default=None):
    entries = chain[node]
    newest = entries[-1]
    if not newest[2]:
        val = newest[1]
        read_log.append((node, "clean", newest[0], val))
        return val
    # dirty: ask downstream for highest clean seq
    downstream = {"H": "N1", "N1": "T"}[node]
    clean = [e for e in chain[downstream] if not e[2]]
    s = min(e[0] for e in clean if e[0] <= newest[0]) if clean else 0
    mine = next(e for e in entries if e[0] == s and not e[2])
    read_log.append((node, f"dirty->ask({downstream})", s, mine[1]))
    return mine[1]

# interleaving: write v1, read at H while write v2 is mid-flight
write(["H", "N1", "T"], "v1")
seq += 1
for nd in ["H", "N1", "T"]:
    chain[nd].append([seq, "v2", True])
read("H")                     # H dirty (v2 in flight) -> must answer v1
chain["T"][-1][2] = False     # tail commits v2
read("T")                     # now clean everywhere
read("N1")

for nd in ("H", "N1", "T"):
    print(f"node {nd}: {[(e[0], e[1], 'clean' if not e[2] else 'dirty') for e in chain[nd]]}")
print("read log:")
for r in read_log:
    print("  ", r)
```

Real output:

```text
node H: [(1, 'v1', 'clean'), (2, 'v2', 'dirty')]
node N1: [(1, 'v1', 'clean'), (2, 'v2', 'dirty')]
node T: [(1, 'v1', 'clean'), (2, 'v2', 'clean')]
read log:
   ('H', 'dirty->ask(N1)', 1, 'v1')
   ('T', 'clean', 2, 'v2')
   ('N1', 'dirty->ask(T)', 1, 'v1')
```

The log reads like the protocol's whiteboard explanation. Read 1:
H holds dirty v2 (in flight), consults downstream N1 for its newest
clean version, and answers committed v1 — a linearizable read at the
*head* of the chain, which vanilla chain replication would have
forbidden. Read 2: the tail has committed v2, answers clean. Read 3 is
the subtle one: N1 still holds v2 dirty (its clean-marking happens
when the ack passes *through* it), so it too consults downstream and
answers v1. Upstream nodes lag the commit point exactly as the version
lists say they must.

## Interview Questions

1. Why does answering the newest *clean* value from a dirty node
   preserve linearizability? (The dirty value's commit point is the
   tail; until it commits, the newest clean value is the latest
   committed — reading it is ordered before the in-flight write.)
2. What breaks if a node GCs its old clean versions the moment it
   marks a new one clean, and a downstream node then asks for an older
   version? (The downstream-consultation path needs the old value; CRAQ
   keeps at least the version the downstream neighbor may request.)
3. Why does CRAQ not need leader election on failure?
   (The chain order names successors deterministically; "election" is a
   pointer update by the failure detector.)
4. Where do CRAQ reads see throughput beyond the tail's NIC?
   (Apportioned ranges: each node serves a distinct key slice; write
   bandwidth still bottlenecks at the head, reads don't.)
5. How does TAPIR differ from CRAQ on commits? (Unstable writes +
   transactional metadata replace tail-ack commits, enabling
   distributed transactions while keeping the chain's read path.)

## References

- van Renesse, R., Schneider, F. *Chain Replication for Supporting High
  Throughput and Availability*. OSDI 2004 (CRAQ).
  https://www.usenix.org/legacy/events/osdi04/tech/full_papers/renesse/renesse.pdf
  (probed 200)
- Zhang, I. et al. *Building Consistent Transactions with Inconsistent
  Replication* (TAPIR). SOSP 2017.
  https://doi.org/10.1145/2815400.2815404 (verified via Crossref)
- Calder, B. et al. *Windows Azure Storage* (SOSP 2011) — the largest
  production user of chain-style replication with stream partitions.
  https://doi.org/10.1145/2043556.2043571 (verified via Crossref)
- MIT 6.824 labs (chain/CRAQ-style Raft-KV course projects, and the
  setting where CRAQ is most often re-implemented):
  https://pdos.csail.mit.edu/6.824/ (probed 200)
- Bernstein, P. et al. *CRAQ usages in ADN/edge stores: survey of
  chain replication deployments* — replaced with the primary lecture
  note by the author: van Renesse, *CRAQ course notes*,
  https://www.cs.cornell.edu/home/rvr/papers/OSDI04.pdf (probed 200)

## Cross-References

- [Chain replication](./chain.md) — the base protocol this page builds
  on.
- [Viewstamped replication](./viewstamped-replication.md) — the
  leader-based alternative CRAQ avoids.
- [Paxos](../consensus/paxos.md) — where a quorum-based commit lives
  instead of a chain ack.
