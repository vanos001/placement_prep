# Hinted Handoff: The Write Path When a Replica Is Down

Every quorum-replicated write carries a quiet assumption: the preferred replicas are *up*. The moment one of them is not, the coordinator has three options — reject the write, degrade below the replication factor, or find a stand-in. Hinted handoff is the third option: the coordinator hands the mutation to a live neighbour together with metadata naming the *intended* recipient, and replays it once the intended replica returns. Done well, it shrinks the inconsistency window from "until the next repair" to "until recovery + delivery lag". Done carelessly, it silently weakens your durability guarantees and can bury a recovering node under a replay storm.

This page is the write-path view of replication failure. The read-path and reconciliation views live in [Quorum Systems](./quorum-systems.md), [Anti-Entropy Protocols](./anti-entropy.md), and [Merkle Tree Sync](./merkle-sync.md).

## The Gap Between W and N

Recall the Dynamo-style parameters: `N` natural replicas per key, `W` of them must acknowledge a write. With `RF = 3` and `W = 2`, one replica can fail with no client-visible impact — the write is still acknowledged by two. The interesting question is what the system does about the *third* copy:

```text
RF=3, W=2, replica R2 is down:

  coordinator
     | 1. compute natural replicas {R1, R2, R3} from the key hash
     | 2. send mutation to R1, R2, R3
     |          R1 ACKs        R2 unreachable       R3 ACKs
     |
     | 3. W=2 satisfied  ->  client gets success at t
     |
     +-- 4. remaining copy options:
            a) drop it            -> N effectively becomes 2 for this key
            b) queue locally      -> coordinator is the stand-in
            c) forward to a live
               non-natural node   -> "sloppy" replica holds the hint
```

Option (a) is what happens with hinted handoff disabled: the write succeeds, but the key now permanently (until a repair) lives on 2 of 3 replicas. Every subsequent quorum read of that key touches a stale candidate. Options (b) and (c) are hinted handoff, and the difference between them matters — see [Where the Hint Lives](#where-the-hint-lives).

## Write-Path Walkthrough

Using Cassandra's documented flow (the same shape appears in Dynamo and ScyllaDB, with different hint placement):

1. **Replica computation.** The coordinator maps the partition key to `N` natural replica nodes via consistent hashing.
2. **Dispatch.** Mutations are sent to all `N`. Replicas that apply the mutation respond with an ACK.
3. **Timeout branch.** Any replica that does not ACK within `write_request_timeout_in_ms` (default 2 s in Cassandra) is treated as down for this write — "down" here includes overloaded nodes that miss the deadline, not just crashed ones.
4. **Quorum check.** If the number of ACKs already meets `W` (e.g., 2 of 3 for `LOCAL_QUORUM`), the coordinator responds success *immediately*. The client's write is durable on `W` replicas and invisible on the rest.
5. **Hint creation.** For each silent natural replica, the coordinator stores a hint: enough information to replay *this specific mutation* to *that specific node* later.
6. **Recovery trigger.** When the down node returns (gossip/heartbeat re-entry), coordinators that hold hints for it begin replay. In Cassandra the coordinator "applies any pending hinted mutations against the replica"; the hint is deleted once the destination acknowledges.
7. **Suppression.** New hints are only stored while the destination's downtime is below `max_hint_window_in_ms` (default 3 h in Cassandra). After that, the coordinator assumes a longer outage and leaves convergence to anti-entropy repair.

```text
t0   client -> coordinator: put(key, v)
t0   coordinator -> R1,R2,R3: mutation
t1   R1 ACK, R3 ACK  (R2 timed out at t0+2s)
t1   client <- coordinator: SUCCESS (quorum met)
t1   coordinator stores hint {target=R2, mutation=put(key,v), created=t1}
...
tR   R2 rejoins ring (gossip)
tR+  coordinator -> R2: replayed mutation; R2 ACKs; hint deleted
```

The crucial property to internalise: **between t1 and tR+delivery, a quorum read can be served entirely from replicas that do not have the value.** With `W=2, R=2` and R2 down, both read quorum members can be R1 and R3 (stale), while the newest version sits in R1 plus a hint. Hinted handoff bounds *eventual* convergence; it provides no read-path consistency by itself.

## Anatomy of a Hint

A hint is a self-contained replay instruction. The minimal field set is the same everywhere:

| Field | Purpose | Notes |
|---|---|---|
| Target node ID | Which natural replica the mutation was meant for | Hints are addressed to a node, not a key range |
| Partition key + table/keyspace ID | Where the mutation applies | Enough to route the replay on the destination |
| Mutation payload | The serialized write itself | Column values, tombstone marker, timestamp |
| Coordinator-local timestamp | Ordering and suppression decisions | Drives `max_hint_window` checks on replay |
| Delivery state | Pending / sent / acked | Cleared on destination ACK |

Where the hint physically lives is the main design fork:

- **Dynamo (2007):** the *preference list* is walked past the failed node, so the next live node outside the natural `N` (a "sloppy" replica) stores the write as a temporary holder. Durability is preserved by an extra machine outside the natural set; the temporary copy is handed off when the natural owner returns.
- **Cassandra:** the *coordinator* stores the hint locally (historically a per-destination queue on local disk backed by the `system.hints` table). No non-replica node ever holds user data — at the cost of concentrating hint storage and replay load on coordinators.
- **ScyllaDB:** the hint is the pair "target replica ID + mutation data", stored by the coordinator, replayed when the node is up again, deleted after ACK — architecturally Cassandra-like but implemented on the shard-per-core engine, with per-shard hint queues.

## Sloppy Quorum Interplay

In Dynamo's design, hinted handoff and sloppy quorum are two halves of one mechanism. When a natural replica is down, `put`/`get` operations target the first `N` *reachable* nodes in the preference list — walking down the ring past the dead node. Two consequences:

1. **W stays honest about liveness, dishonest about durability.** A `W=2` ACK can come from `{natural, natural}` or from `{natural, sloppy}`. The write is available, but the sloppy copy is *temporary* — if the holder dies before handoff completes, that copy is gone, and you are effectively at `W` copies minus one.
2. **R can silently lose overlap with the freshest data.** Reads still prefer the natural list. If the newest version is only on a natural replica plus a sloppy holder, a two-replica read that lands on two other natural replicas returns stale data even though "quorum" was technically met on the write path. The vector-clock reconciliation in [Anti-Entropy Protocols](./anti-entropy.md) is what catches these stragglers, not the quorum arithmetic itself.

The quorum theory behind these trade-offs (intersection bounds under failures, probabilistic quorum guarantees) is developed in [Quorum Systems](./quorum-systems.md); the practical summary is that sloppy quorum buys availability during outages at the price of a widening window where the "quorum" is no longer a true sample of the natural replica set.

## Consistency Consequences

**The stale window is bounded twice, by different mechanisms.** Hint replay converges a key within `delivery lag` after recovery — typically seconds to minutes. But the bound only holds if a hint exists. Cassandra explicitly documents hints as best-effort: they "do not guarantee eventual consistency like anti-entropy repair does". The two bounds compose:

```text
consistency gap for one mutation, from client ACK to full RF:

  |-- normal replication lag --|             (all replicas up)
  |-- hint storage + recovery + replay lag --|  (short outage, hint exists)
  |-- outage + suppression remainder + AAE interval --|  (hint lost/expired)
```

**Tunable-consistency reads during an outage.** With `RF=3, W=2, R=2` and one natural replica down, reads still succeed — but the freshest version may be the one only hinted. Systems where the coordinator can also *read* from the hint holder (Dynamo-style, since the holder is a real replica serving traffic) narrow this window; coordinator-hint designs (Cassandra/ScyllaDB) do not expose hints to the read path at all.

**Tombstones and the resurrection hazard.** A hint is an old mutation replayed later. If the destination's copy was deleted by a tombstone in the meantime, replaying the hint resurrects the data — the classic "zombie row" bug class. Cassandra guards this by not delivering hints older than the destination's `gc_grace_seconds`, mirroring the same reasoning that governs tombstone GC. This is also one of the historical arguments against aggressive `gc_grace` tuning combined with long hint queues.

**The lost-write shape.** If a *coordinator* holding hints dies before delivery, the hints die with it (Cassandra stores them locally). The write was acknowledged at `W=2`, but after the second independent failure the durable copy count can drop to 1 — or to 0 for the hinted copy specifically. This is why hinted handoff is a *latency-of-convergence* optimisation, not a durability mechanism; only acknowledged replicas count for durability.

## Partnership With Anti-Entropy

Hinted handoff is the *fast, narrow* repair channel; anti-entropy is the *slow, wide* one. Riak's documentation makes the division explicit: since version 1.3, replica conflicts are healed by read repair and active anti-entropy (AAE) — continuous, hash-tree-based background comparison — while hinted handoff's role is confined to availability during node failure. The production pattern across all Dynamo descendants:

| Mechanism | Trigger | Convergence bound | Catches what? |
|---|---|---|---|
| Hinted handoff | Write to down replica | Recovery + delivery lag | Only mutations that occurred while the replica was down and hinted |
| Read repair | Client read observes divergence | Immediate at read time | Only keys that are read |
| Merkle-tree AAE | Periodic/background sync | Minutes to hours | Everything, including cold keys and lost hints |

The three channels are complementary, not redundant: hints miss data (expiry, coordinator loss), read repair misses cold data, and AAE is too slow to be the only protection for hot keys. [Merkle Tree Sync](./merkle-sync.md) covers the hash-comparison machinery that makes the third channel affordable; [Anti-Entropy Protocols](./anti-entropy.md) covers all three in a single frame.

## Why Modern Systems Moved Away From HH-Centric Design

- **Riak demoted it.** Riak retains hinted handoff as a failure-availability technique (its glossary still describes neighbours temporarily taking over a failed node's storage), but the documented *conflict-resolution* story since 1.3 is read repair plus AAE. AAE closed the gap that HH could not: cold data, expired hints, and hints lost with a crashed coordinator.
- **DynamoDB never built on it.** The 2022 ATC paper describes DynamoDB's replication as per-partition **Multi-Paxos** groups with a steady-state leader — write availability comes from the leader protocol and synchronous log shipping, not from sloppy replicas holding hints. The evolution from the 2007 Dynamo design (eventual consistency, sloppy quorum, hints) to DynamoDB (leader-based, strongly consistent by default, bounded staleness) is the clearest data point that hint-based eventual replication was a cost/availability compromise of its era, not an endpoint.
- **Cassandra kept it but re-engineered it.** Hints remain part of Cassandra's model (the current docs' three-channel story: hints, read repair, anti-entropy repair), with a rewritten hints service in the 4.x line replacing the legacy per-node hint queues.
- **ScyllaDB kept the Cassandra contract** on its thread-per-core engine, keeping hint storage per-shard and replay bounded by the same configuration knobs (`max_hint_window_in_ms`, `hinted_handoff_enabled`).

The pattern: hinted handoff survives where tunable eventual consistency survives, and shrinks wherever the replication protocol itself was reworked around a leader and consensus.

## Failure Modes in Production

- **Hint queue overflow.** A node down for hours while the cluster takes heavy writes accumulates one hint per (mutation, destination) pair. In coordinator-hint designs, hot coordinators can accumulate gigabytes of hints; Cassandra's `max_hint_window_in_ms` exists precisely to cap this growth. Disk pressure from hints is an alertable condition, not a theoretical one.
- **Replay storms.** When a node that was down for two hours rejoins, coordinators drain hours of queued mutations into it at once, competing with live traffic for its compaction and memtable bandwidth. Delivery throttling (`max_hints_delivery_threads` in Cassandra, per-destination drain rates in ScyllaDB) spreads the replay, and nodes commonly rejoin with hints replayed at reduced concurrency first.
- **Deadline-vs-down ambiguity.** A node that times out but is actually alive receives both the live mutation (it was slow, not dead) and a replayed hint. Replay must be idempotent — mutations carry timestamps, so the replayed copy loses to any newer local version, but the wasted I/O is real.
- **Hint GC.** Three exits exist for a hint: delivered-and-acked (normal), expired by `max_hint_window` (superseded by AAE), or too old relative to `gc_grace_seconds` (unsafe to replay — potential resurrection). Confusing the second and third cases has historically produced both leaked hint storage and zombie-data reports.
- **Monitoring blindness.** "Writes succeeding" hides hint backlog. The operational signal is per-destination hint depth and oldest-pending-hint age, which is exactly the same shape as replica-lag monitoring in leader-based systems.

## Demo: Staleness Windows Under a Replica-Failure Trace

The simulation below builds an 8-node consistent-hash ring (100 vnodes per node), `RF=3`, `CL=TWO`, and replays a seeded 9-hour failure trace at one write per minute: node `n5` down 40→150 min (short outage, fully hint-covered), node `n3` down 0→500 min (long outage; after 180 min the coordinator stops storing new hints, mirroring `max_hint_window_in_ms`). It measures, per write, the window from client ACK until the last natural replica actually holds the mutation — via hint replay, or via a background Merkle anti-entropy sweep at t=530 for writes that ran out of hint coverage.

```python
"""Hinted-handoff staleness simulation (stdlib only, seeded -> deterministic).

8-node consistent-hash ring (100 vnodes/node), RF=3, CL=TWO, 1 write/tick,
1 tick = 1 minute, 9 h horizon. n5 down during [40,150) (short outage);
n3 down during [0,500); after 180 min (Cassandra default
max_hint_window_in_ms) no NEW hints are stored for n3.
Staleness window of a write = ACK time -> last natural replica updated
(by hint replay, or by the end-of-run Merkle anti-entropy sweep at t=530).
"""
import bisect, hashlib, random

NODES, VN, HORIZON = [f"n{i}" for i in range(8)], 100, 540
WINDOW, AE_END, DRAIN = 180, 530, 25
OUTAGES = {"n5": (40, 150), "n3": (0, 500)}

_h = lambda s: int.from_bytes(hashlib.md5(s.encode()).digest()[:8], "big")
RING = sorted((_h(f"v-{n}-{k}"), n) for n in NODES for k in range(VN))
TOKS = [t for t, _ in RING]

def replicas(key, n=3):
    i = bisect.bisect_left(TOKS, _h("K" + key)) % len(TOKS)
    out = []
    for j in range(len(TOKS)):
        node = RING[(i + j) % len(TOKS)][1]
        if node not in out:
            out.append(node)
            if len(out) == n:
                return out

def down(node, t):
    a, b = OUTAGES.get(node, (1, 0))
    return a <= t < b

def simulate(with_hints):
    random.seed(42)
    keys = [f"k{random.randrange(400):03d}" for _ in range(HORIZON)]
    queue, writes, log = [], [], []
    created = delivered = suppressed = 0
    seen = set()
    for t in range(HORIZON):
        key = keys[t]
        missing = {r for r in replicas(key) if down(r, t)}
        rec = {"key": key, "ack": t, "missing": set(missing), "done": None}
        if missing and with_hints:
            for dest in sorted(missing):
                if t - OUTAGES[dest][0] >= WINDOW:
                    suppressed += 1                 # window blown, no hint
                else:
                    queue.append((t, key, dest)); created += 1
                    if len(log) < 4:
                        log.append(f"  t={t:3d}min key={key} dest={dest} down"
                                   f" -> hint stored on coordinator")
        writes.append(rec)
        still = []
        for created_t, k2, dest in queue:
            if down(dest, t):
                still.append((created_t, k2, dest)); continue
            delivered += 1
            for r in writes:
                if r["key"] == k2:
                    r["missing"].discard(dest)
            if dest not in seen and len(log) < 8:
                seen.add(dest)
                log.append(f"  t={t:3d}min {dest} recovered -> replaying hints")
        queue = still
        for r in writes:
            if r["done"] is None and not r["missing"]:
                r["done"] = t
    for r in writes:                                    # Merkle AAE sweep
        if r["done"] is None:
            r["done"] = AE_END
    deg = [r for r in writes if r["ack"] < r["done"]]
    wins = sorted(r["done"] - r["ack"] for r in deg)
    aae = sum(1 for r in deg if r["done"] >= AE_END)
    return created, delivered, suppressed, deg, wins, aae, log

def stats(xs):
    if not xs: return "n=0"
    return (f"n={len(xs):3d} min={xs[0]:5.0f} mean={sum(xs)/len(xs):5.0f}"
            f" p95={xs[int(0.95*(len(xs)-1))]:5.0f} max={xs[-1]:5.0f}")

for flag, name in ((True, "WITH hinted handoff"), (False, "NO hints (AAE only)")):
    created, delivered, suppressed, deg, wins, aae, _ = simulate(flag)
    print(f"=== {name} ===")
    if flag:
        print(f"hints created={created} delivered={delivered} "
              f"suppressed(window blown)={suppressed}")
    print(f"degraded writes (replica missing at ACK): {len(deg)}")
    print(f"staleness window (minutes): {stats(wins)}")
    print(f"degraded writes left to the AAE sweep: {aae}")
    print()
print("--- event log (first 8 hint events) ---")
print("\n".join(simulate(True)[6]))
```

```text
=== WITH hinted handoff ===
hints created=103 delivered=103 suppressed(window blown)=104
degraded writes (replica missing at ACK): 193
staleness window (minutes): n=193 min=    8 mean=  233 p95=  467 max=  498
degraded writes left to the AAE sweep: 65

=== NO hints (AAE only) ===
degraded writes (replica missing at ACK): 193
staleness window (minutes): n=193 min=   37 mean=  304 p95=  497 max=  528
degraded writes left to the AAE sweep: 193

--- event log (first 8 hint events) ---
  t=  2min key=k012 dest=n3 down -> hint stored on coordinator
  t=  4min key=k140 dest=n3 down -> hint stored on coordinator
  t=  6min key=k114 dest=n3 down -> hint stored on coordinator
  t=  8min key=k377 dest=n3 down -> hint stored on coordinator
  t=150min n5 recovered -> replaying hints
  t=500min n3 recovered -> replaying hints
```

Reading the output the way an SRE would: hinted handoff cut the mean staleness window from 304 to 233 minutes and closed 128 of the 193 degraded writes *without* any background repair job — but 104 writes to `n3` were created after its downtime passed the 3 h window and got no hint at all, so 65 degraded writes still waited for the Merkle sweep (the other 40 were covered by hints created within the window and delivered at recovery). That 65-write residue is exactly the "hints are best-effort, not a repair guarantee" clause from the Cassandra docs, made numeric: hinted handoff accelerates convergence for *recoverable* outages; it does not remove the need for anti-entropy.

## Cross-System Comparison

| System | Hint stored on | Natural-replica data on hint holder? | Window / TTL knob | Repair partner | Status (2026) |
|---|---|---|---|---|---|
| Dynamo (2007 design) | Next live node outside natural N (sloppy replica) | Yes — serves traffic | No explicit window; coordinator-driven demotion of hints | Read repair + Merkle sync | Historical; descendant designs differ |
| Cassandra | Coordinator (local hint store, per-destination queues) | No | `max_hint_window_in_ms` (3 h default); `gc_grace` gate on replay | Read repair + incremental/full repair | Active, hints service reworked in 4.x |
| ScyllaDB | Coordinator, per-shard | No | `max_hint_window_in_ms`, `hinted_handoff_enabled` | Row-level repair (Merkle-based) | Active |
| Riak | Fallback vnodes on neighbouring nodes | Temporarily, in fallback vnode | Handoff-driven; no documented hint TTL | Read repair + AAE (primary since 1.3) | Active, but demoted in favour of AAE |
| DynamoDB | — no hints; Multi-Paxos log shipping per partition | — | — | Paxos catch-up from leader log | Active, design diverged |

## Interview Angle

- *Walk me through a write when one replica is down in a Cassandra-style system.* Replicas from the hash → dispatch → quorum met on live ACKs → hint stored per silent replica → replay on gossip re-entry → hint deleted on ACK → suppression after `max_hint_window`.
- *Why can a quorum read still be stale if W and R intersect?* Because the freshest copy may be the hinted one, and hints are not on the read path; sloppy quorum widens this by letting W land outside the natural set.
- *Why is hinted handoff not a durability mechanism?* The ACK guarantee covers only the replicas that acknowledged; hints die with their holder, expire, and are explicitly best-effort. Durability arguments must count acknowledged copies only.
- *Your hinted-handoff queue is growing during an outage. What do you do?* Check oldest-hint age against `max_hint_window` and `gc_grace`, ensure delivery throttling is sane, and plan a post-recovery incremental repair — the queue will drain but the tail belongs to anti-entropy.

## References

- DeCandia et al., [Dynamo: Amazon's Highly Available Key-value Store](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) (SOSP 2007), DOI [10.1145/1294261.1294281](https://doi.org/10.1145/1294261.1294281) — preference lists, sloppy quorum, hinted handoff as temporary replication.
- Apache Cassandra, [Hints](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/hints.html) — `max_hint_window_in_ms` (3 h default), `write_request_timeout_in_ms` (2 s default), best-effort status, replay-on-recovery flow.
- ScyllaDB, [Hinted Handoff](https://docs.scylladb.com/manual/stable/architecture/anti-entropy/hinted-handoff.html) — hint = target replica ID + mutation, storage conditions, replay and deletion on ACK.
- Riak KV, [Managing Active Anti-Entropy](https://docs.riak.com/riak/kv/latest/using/cluster-operations/active-anti-entropy/index.html) and the [Riak KV Glossary, "Hinted Handoff"](https://docs.riak.com/riak/kv/latest/learn/glossary/index.html) — AAE (since 1.3) as the conflict-resolution channel; HH as failure-time availability.
- Elhemali et al., [Amazon DynamoDB: A Scalable, Predictably Performant, and Fully Managed NoSQL Database Service](https://www.usenix.org/system/files/atc22-elhemali.pdf) (USENIX ATC 2022) — per-partition Multi-Paxos replication; the hint-free leader-based successor to the Dynamo design.
