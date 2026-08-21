# Multi-Paxos

Multi-Paxos is the canonical multi-decision consensus protocol, descended from Leslie Lamport's 1998 paper "The Part-Time Parliament" and its 2001 revision. It is the protocol underlying Google's Spanner, Apache Cassandra's lightweight transactions, and many database storage engines. This page covers the core-state vs. instance-state distinction, the leader election protocol, the stable-leader optimization that makes Multi-Paxos practical, and the relationship to Raft.

## From Paxos to Multi-Paxos

Classic Paxos (Single-Decree Paxos) decides **one** value. To decide a sequence of values — a log of operations — you can either:

1. Run independent Paxos instances for each log entry. Cost: 2 RTTs per entry, because every entry requires a fresh Prepare/Accept round.
2. Run Multi-Paxos: elect a stable leader that runs Prepare once and Accept for every subsequent decision.

Multi-Paxos is option 2. The leader runs a single Prepare phase to establish a *view* (a term, an epoch, a ballot — different literatures use different terms). For every subsequent log entry, only the Accept phase is needed: 1 RTT.

## The Two-Dimensional State

Multi-Paxos state has two dimensions:

- **Per-instance state**: For each log entry i, the protocol tracks `ballot[i]`, `accepted_value[i]`, `accepted_ballot[i]`, and `decided[i]`.
- **Per-replica state**: The current view number, the current leader, the first undecided instance, and the highest ballot seen.

```text
                 Log entries
                ┌───┬───┬───┬───┬───┬───┬───┐
  Replica A:    │ 1 │ 2 │ 3 │ 4 │ 5 │ . │ . │   <- decided up to 4
                └───┴───┴───┴───┴───┴───┴───┘
                              ↓
  Replica B:    │ 1 │ 2 │ 3 │ 4 │ X │ . │ . │   <- entry 5 is in-flight
                              ↓
  Replica C:    │ 1 │ 2 │ X │ . │ . │ . │ . │   <- behind on entry 3
```

The Multi-Paxos protocol must keep this state consistent across replicas under leader changes. The protocol's central invariant: once an entry is decided by a quorum, no future leader can overwrite it.

## The Stable Leader Optimization

Without a stable leader, Multi-Paxos degenerates to plain Paxos (2 RTTs per entry). The key insight that makes Multi-Paxos practical:

> A replica that has been chosen as leader for view v can issue Accept messages for *all* undecided entries in view v without re-running Prepare.

The leader election (Prepare phase) establishes:

1. The new view number.
2. The promise from a quorum of replicas that they will not accept any message from an older view.
3. The "highest ballot" and "accepted value" for each undecided entry, so the new leader can re-propose the value if any replica had accepted it.

After Prepare, the leader simply broadcasts `⟨Accept, v, i, value⟩` for each entry i. Replicas verify `v` matches their last promised view and accept.

## The Prepare Phase (Leader Election)

```text
Candidate Leader L (entering view v):
  send ⟨PREPARE, v, L, last_entry_index⟩ to all replicas

  Replica R (receiving PREPARE):
    if v > R.promised_view:
      R.promised_view = v
      reply with ⟨PREPARE_OK, v,
                  highest_accepted_ballot_per_undecided_entry,
                  accepted_value_per_undecided_entry⟩
    else:
      reply with NACK

L collects 2f+1 PREPARE_OK:
  for each undecided entry i:
    pick the value with the highest ballot among replicas' replies
    (or a new value if no replica accepted anything for entry i)
  now L is the leader; can issue Accept for any entry.
```

The Prepare phase costs 1 RTT. Crucially, it happens **once per view**, not per entry.

## The Accept Phase (Per-Entry Decision)

```text
Leader L (proposing entry i with value w):
  send ⟨ACCEPT, v, i, w⟩ to all replicas

Replica R:
  if v == R.promised_view:
    R.accepted_ballot[i] = v
    R.accepted_value[i] = w
    reply ACCEPT_OK
  else:
    reply NACK

L collects 2f+1 ACCEPT_OK:
  entry i is decided with value w
  broadcast DECIDED to all replicas (can be piggybacked on next ACCEPT)
```

The Accept phase is 1 RTT. Under a stable leader, every entry is decided in 1 RTT — that's the practical performance of Multi-Paxos.

## The Multi-Paxos Pipeline: Batched Accepts

A real implementation pipelines Accept messages:

```text
L broadcasts ACCEPT(v, i,   w_i)
L broadcasts ACCEPT(v, i+1, w_{i+1})
L broadcasts ACCEPT(v, i+2, w_{i+2})
...
```

Each replica accepts entries as they arrive. The leader collects ACCEPT_OKs in parallel. When 2f+1 ACCEPT_OKs arrive for entry i, it's decided. The leader can piggyback the DECIDED notification on the next ACCEPT, reducing message count.

This is the "Multi-Paxos fast path" that production systems use. Spanner's Paxos groups achieve ~10 µs per decision per group on a 5-replica cluster, limited by the network round-trip, not the protocol.

## Leader Failure and View Change

When a leader fails (or is suspected of failing), the protocol must:

1. **Detect the failure.** Timeouts: each replica waits for an ACCEPT within a configurable period. If none arrives, the replica suspects the leader and starts a new view.

2. **Run Prepare with the new view.** A new candidate picks `v+1` (or higher) and broadcasts PREPARE. The 2f+1 replies include the per-entry state of every undecided entry.

3. **Continue from the latest state.** The new leader re-proposes any entry that has an `accepted_value` from the previous view — even if the value was decided in the old view. (Note: an entry that was decided by a quorum in view v cannot be overwritten in view v+1, because the new leader will see the accepted value in at least one of its 2f+1 PREPARE_OK replies.)

This last point is the key safety invariant: **decided entries are stable across leader changes**.

## The Gap Problem and State Transfer

A subtle issue: replicas may have decided entries that other replicas don't yet know about. The leader's DECIDED broadcast is best-effort; a slow replica may have an entry's accepted value but not its decision status. When this replica recovers (or catches up), it needs to know which entries are decided.

Multi-Paxos implementations solve this with **state transfer**: a lagging replica asks the leader "what entries 0..N are decided?" and the leader sends the missing decisions. This is not part of the original paper but is universally implemented.

Spanner's implementation tracks per-replica log lengths and triggers state transfer when a replica falls more than a configurable number of entries behind.

## Comparison to Raft

Raft (Ongaro-Oki, 2014) was designed to be "understandable" while preserving Multi-Paxos's safety and liveness. The key differences:

| Aspect | Multi-Paxos | Raft |
|--------|-------------|------|
| Leader election | Implicit (Prepare) | Explicit (RequestVote RPC) |
| Log structure | Per-instance state | Per-term log with prevLogIndex/prevLogTerm checks |
| Membership change | α-approach (Lamport 2001) | Joint consensus (Ongaro-Oki 2014) |
| Log inconsistency handling | State transfer (out of paper) | Forced rollback of conflicting entries |
| Snapshotting | Not specified | `InstallSnapshot` RPC |
| Vote counting | Promise (one ballot per view) | Vote (one term per election) |

Both achieve 1 RTT per decision under a stable leader. Raft is more rigid — the log structure is fully specified, including how to recover from divergent logs. Multi-Paxos leaves more freedom, which is why Spanner's Paxos variant is significantly different from the textbook.

## Spanner's Paxos Variant

Google Spanner (2012) uses Multi-Paxos with three modifications:

1. **Per-group leader colocation.** Each Paxos group's leader is placed on a different physical machine, so load is spread. A schema maps groups to leaders at configuration time.

2. **Long-lived leaders.** Spanner leaders hold their position for ~10 seconds, far longer than the typical round. The cost of leader election is amortized over thousands of decisions.

3. **Paxos-leader-lease-based freshness.** Each replica grants the leader a lease on its "freshness" — a guarantee that no other replica can become leader until the lease expires. This lets Spanner serve reads from replicas without going through the leader, using the lease as proof that the leader hasn't changed.

## Common Pitfalls

1. **Forgetting that "Multi-Paxos" is a family, not a spec.** The original paper leaves many details unspecified — log recovery, snapshotting, state transfer, membership change. Real implementations pick from the literature, often inconsistently. A naive Multi-Paxos implementation will not interoperate with another naive one.

2. **Treating Prepare as a one-time event.** A leader that never re-runs Prepare risks accepting entries that conflict with values accepted by a quorum in a newer view. A leader must re-run Prepare if it ever loses contact with a quorum for longer than the lease timeout.

3. **Underestimating the cost of recovery.** A leader crash during a pipeline of in-flight Accepts leaves entries in a half-accepted state. The new leader must re-propose them with the values they had — a phase not adequately described in the original paper.

4. **Confusing "value decided" with "value applied."** Decided entries are not yet applied to the state machine. The apply step is the leader's responsibility (in classic Multi-Paxos) or each replica's (in some variants). Either way, application order must match log order.

5. **Accepting without checking the ballot.** A replica that forgets to verify `v == R.promised_view` before accepting will accept old-view values, violating safety. This bug is common in textbook implementations and is what made Paxos originally considered "hard to implement correctly."

## References

- Leslie Lamport, "[The Part-Time Parliament](https://lamport.org/pubs/pubs.html#lamport-paxos)" (ACM TOCS 1998)
- Leslie Lamport, "[Paxos Made Simple](https://lamport.org/pubs/pubs.html#paxos-simple)" (2001)
- Leslie Lamport, "[Multi-Paxos: How to Make a Stable Leader](https://lamport.org/pubs/pubs.html#multi-paxos)" (technical report)
- Diego Ongaro, "[Consensus: Bridging Theory and Practice](https://github.com/ongardio/dissertation)" (PhD thesis, 2014, includes Multi-Paxos analysis)
- James Myers, "[Paxos Made Moderately Complex](https://www.cs.rutgers.edu/~pxk/416/notes/paxos.html)" (2012, pedagogical)
- [Spanner: Google's Globally-Distributed Database](https://research.google/pubs/pub39966/) (OSDI 2012)
- [etcd-raft: production Raft implementation](https://github.com/etcd-io/raft) — Multi-Paxos-equivalent production reference
