# EPaxos

EPaxos (Egalitarian Paxos) is a leaderless consensus protocol introduced by Iulian Moraru, David Turnbull, and others at Carnegie Mellon in 2013, with the full SOSP 2013 paper "There Is More Consensus in Egalitarian Parliaments." It eliminates the leader bottleneck of Multi-Paxos and Raft by allowing any replica to directly drive a command through consensus, provided the command conflicts with only a small set of other in-flight commands. This page covers the conflict graph, the slow path vs. fast path, and the practical limitations that prevented EPaxos from achieving production adoption despite its theoretical elegance.

## Why EPaxos Exists

Multi-Paxos (and Raft) elect a stable leader through which every command flows. The leader's bandwidth becomes the cluster's throughput ceiling, and a leader on a slow network node drags the whole cluster's latency. EPaxos asks: can we let any replica act as the leader for any individual command, while still achieving serializability?

The answer is yes, *if* commands are commutative. Two `PUT(x, 1)` and `PUT(y, 2)` commands can be agreed on independently because they commute. The conflict only arises when commands target the same key with non-commutative operations (e.g., `INCR(x)` twice).

EPaxos uses a **dependency graph**: each command's dependencies are the set of conflicting commands that were concurrently in-flight when it was proposed. The cluster agrees on both the command and its dependency set; the application executes commands in dependency order (using a topological sort).

## The Conflict Detection Model

Each command is annotated with a key set: `{keys touched by this command}`. Two commands conflict if their key sets intersect and at least one is non-commutative on the intersecting keys (e.g., a `PUT` and a `PUT` on the same key conflict; a `GET` and a `PUT` on the same key conflict; two `PUT`s on different keys do not).

```text
CMD: INCR(x)              conflicts with: {INCR(x), GET(x), PUT(x, ...)}
CMD: PUT(x, 5)            conflicts with: {GET(x), PUT(x, ...)}
CMD: PUT(y, 6)            conflicts with: {GET(y), PUT(y, ...)} — disjoint from x
CMD: INCR(z)              conflicts with: {INCR(z), GET(z), PUT(z, ...)}
```

A `PUT(x, 5)` and `PUT(y, 6)` are completely independent and can be agreed on in parallel without any coordination beyond the basic Paxos phase.

## Fast Path vs. Slow Path

The crucial innovation is detecting whether the fast path is safe. EPaxos runs a Paxos phase-1-like "Prepare" round only when needed.

### Fast Path (no conflicts)

A client sends a command to any replica R. R sends a `PreAccept` message to all other replicas, including the command and its (initially empty) dependency set. Each replica replies with the set of commands it knows about that conflict. If **all** replicas reply with the same dependency set (i.e., the conflict graph is "stable" — no new conflicting commands were concurrently proposed), R proceeds directly to `Accept` with the agreed dependencies and then `Commit`. Total: 1 RTT (client→R) + 1 RTT (R→all, PreAccept) + 1 RTT (Accept) = 3 RTTs.

### Slow Path (conflicts detected)

If replicas report different dependency sets (because a concurrent conflicting proposal was in flight), R must run a full Prepare phase to reconcile. This is essentially Multi-Paxos's view-change: R asks each replica for its current view, picks the union or intersection (depending on the protocol details), and proceeds. Total: 4 RTTs.

### The Quorum Math

The fast path requires `⌈(3/4) · N⌉` replicas to agree on the dependency set. For N=3f+1, that's `⌈(9f+3)/4⌉ = 2f+1 + ⌈(f+2)/4⌉` — i.e., more than a simple majority but less than N. The math guarantees that any two fast-path quorums intersect in at least f+1 honest replicas, which prevents conflicting commitments.

If the fast-path quorum is not met (because replicas are slow or report conflicting deps), EPaxos falls back to the slow path, which requires a simple 2f+1 quorum like classical Paxos.

## The Dependency Graph and Execution

Each command is committed with its dependency set. The application maintains a graph:

```text
committed commands: A, B, C, D
dependencies:
  A -> {B, C}
  B -> {C}
  C -> {}
  D -> {}

Topological sort: C, B, A, D  (or D, C, B, A; multiple valid orders)
```

Execution must be deterministic: any replica that processes the same committed commands in the same topological order produces the same state. EPaxos uses an SC-PR (Strong Consistency Partial Replication) execution model: each command is executed on the replicas that store its keys, and these replicas agree on the topological order via the dependency sets.

## Cost Analysis

For N replicas and a workload with conflict rate α (fraction of commands that conflict with at least one in-flight command):

- **α = 0 (no conflicts)**: All commands use the fast path. Cost = 3 RTT per command, throughput limited by N (every replica can drive commands). Compare with Multi-Paxos: 2 RTT per command (leader drive), throughput limited by 1 replica.
- **α = 1 (every command conflicts)**: All commands use the slow path. Cost = 4 RTT per command, throughput limited by N. Compare with Multi-Paxos: 2 RTT per command, throughput limited by 1 replica.

EPaxos wins when α is low and N is large. For low-N (3 or 5 replicas) and high-conflict workloads, Multi-Paxos with a fast leader is faster.

## Why EPaxos Didn't Take Off in Production

EPaxos is beautiful on paper. In production, it has been largely bypassed by Multi-Raft (CockroachDB, TiKV) and Spanner-style sharded Multi-Paxos. The reasons:

1. **Implementation complexity.** Multi-Paxos and Raft have well-tested libraries (`etcd-raft`, `braft`, hashicorp-raft). EPaxos has only academic prototypes (Spindle, 2015) and a few research clones. The dependency graph and topological execution add significantly to the runtime complexity.

2. **Network topology matters more than leader throughput.** In real deployments, leaders are pinned to the lowest-latency replica, and the leader's bandwidth is rarely the bottleneck — the network bandwidth across the cluster is. EPaxos's N-way load balancing doesn't help when all N replicas share a single network egress.

3. **Conflict rate in real workloads is higher than the model assumes.** The SOSP paper measured α ≈ 0.1 on a TPC-C workload, but production key-value workloads on a single hot key (e.g., a counter, a top-N list, a session) can have α ≈ 0.5 or higher. EPaxos degenerates to slow-path performance.

4. **Recovery is harder.** When a replica fails and rejoins, it must catch up on the dependency graph, not just the log. The "stable leader" of Multi-Paxos makes this trivial; EPaxos requires a complex synchronization phase.

5. **The fast-path quorum is `⌈(3/4)·N⌉`, which for N=3f+1 means f+1 failures are tolerated but the fast path is fragile under even one failure.** A single slow replica forces a slow-path Prepare.

## Modern Descendants

EPaxos's central insight — that conflict-aware consensus can run faster than conflict-blind consensus — has influenced:

- **Multi-Raft with batched conflict-aware dispatch** (CockroachDB's `ParallelCommit`): an extension to Raft that detects non-conflicting commands and commits them in parallel. Not as aggressive as EPaxos but production-grade.
- **Atlas (USENIX ATC 2020)**: a leaderless protocol that simplifies EPaxos's fast-path math while keeping the dependency-graph model.
- **MELD (SOSP 2023)**: combines CRDT semantics with EPaxos-style conflict detection for geo-distributed state.

## Comparison Table

| Protocol | Leader | Phases (best/worst) | Conflict required | Production users |
|----------|--------|---------------------|-------------------|------------------|
| Multi-Paxos | Stable | 2 / 2 | None | Spanner, Cassandra (Lightweight Tx) |
| Multi-Raft | Stable | 2 / 2 | None | CockroachDB, TiKV |
| EPaxos | None (rotating) | 3 / 4 | Yes (graph) | (none in production) |
| Atlas | None (rotating) | 2 / 3 | Yes (simplified) | (research only) |
| Flexible Paxos | Stable | 2 / 2 | None | (research) |

## Pitfalls

1. **Assuming EPaxos is "just as good" as Multi-Paxos.** EPaxos's fast path requires the *strongest* quorum of any modern consensus protocol (3/4·N). Under any sustained contention, it falls back to the slow path.
2. **Forgetting the dependency graph after recovery.** A recovered replica must reconstruct the full dependency graph from the log, not just replay commands in log order. Doing the latter breaks serializability under concurrent commits.
3. **Stable leaders in disguise.** A naive EPaxos implementation that always picks the same replica to drive commands is just Multi-Paxos with extra overhead. The leader-rotation must be per-command to be EPaxos.
4. **Treating all conflicts as equivalent.** A workload with 1000 reads/sec on key X and 100 writes/sec on key Y is bottlenecked by the writes on Y, not by the reads. EPaxos's conflict detection treats them identically.

## References

- Iulian Moraru, David Turnbull, et al., "[There Is More Consensus in Egalitarian Parliaments](https://www.cs.cmu.edu/~dga/papers/epaxos-sosp13.pdf)" (SOSP 2013)
- [Spindle: EPaxos evaluation repository](https://github.com/epaxos/spindle)
- [LWN: "Egalitarian Paxos and the limits of leaderless consensus" (2014)](https://lwn.net/Articles/619438/)
- Aapo Kojola, "EPaxos revisited" (blog series, 2022)
- [Pompeii: Modern EPaxos implementation in Rust](https://github.com/keir/pompeii)
- Moraru, Andersen & Kaminsky, "[There Is More Consensus in Egalitarian Parliaments](https://doi.org/10.1145/2517349.2517350)" (SOSP 2013, doi 10.1145/2517349.2517350 — the original EPaxos paper; the old talk PDF link is dead)
