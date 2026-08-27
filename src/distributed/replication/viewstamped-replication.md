# Viewstamped Replication (VR)

In 1988, Brian Oki and Barbara Liskov published Viewstamped Replication, a replication
protocol that keeps a service running - correctly - through crash failures and through
membership changes, on an asynchronous network, using the same quorum machinery Paxos
uses. The name comes from its central trick: every message carries a "view stamp", a
view number naming which replica set the sender believes is active and which replica is
currently the primary. Paxos solved bare agreement (Lamport's write-up famously took
until 1998 to appear in print), but VR solved agreement and group reconfiguration as one
problem - and Raft, which arrived in 2014 looking suspiciously similar, cites VR as
prior art. This page follows the protocol as redesigned in Liskov and Cowling's
"Viewstamped Replication Revisited" (2012), which is the version worth knowing: cleaner
message flow, an explicit recovery protocol, and built-in reconfiguration.

It is the missing middle child between [Primary-backup](primary-backup.md)
(easy, but safety depends on how you handle failover) and [Quorum](quorum.md)
(no leader, but two rounds per operation). For the other leader-based protocol in this
family, see [Multi-Paxos](../consensus/multi-paxos.md) and [Raft](../consensus/raft.md).

## The Framing: Replication and Membership Are One Problem

VR replicates a deterministic state machine. A service starts with a fixed ordered list
of `n = 2f + 1` replicas and tolerates `f` crash faults. Replicas move through numbered
**views**; view `v` fixes the primary as replica `v mod n` in the list. A "view" is thus
both an epoch number and a membership decision, and it is stamped on every message.

Two properties do all the work:

- **Quorum intersection.** Any two sets of `f + 1` replicas (out of `2f + 1`) share at
  least one replica. Information recorded at `f + 1` replicas can therefore always be
  recovered from any later `f + 1` quorum.
- **Order by one leader.** Only the current primary assigns positions in the log, so no
  two operations ever claim the same slot with different content.

Compare this with [chain replication](chain.md), which also linearizes writes through a
single point but detects failures through a separate master and re-splices a chain; VR
uses timeouts plus a quorum exchange and needs no external coordinator.

## Normal-Case Operation

```text
   client                primary (view v)             backups (view v)
      |                        |                           |
      |--REQUEST(cid, req#, op)|                           |
      |                        |--PREPARE(v, m, op#)------>|   to all backups
      |                        |<----------PREPAREOK-------|   from f of them
      |                        |   (f OKs => committed)    |
      |<--REPLY(v, req#, res)--|                           |
      |                        |--COMMIT(v, commit#)------>|   backups apply up to commit#
```

Roles of the four numbers that make the protocol precise:

| Number | Set by | Meaning | Failure it prevents |
| --- | --- | --- | --- |
| view | protocol | which replica set and primary | two primaries acting at once |
| op number | primary | position of an operation in the log | holes and divergent orders |
| request number | client | per-client monotonic sequence | replays and out-of-order retries |
| commit number | primary | highest op known to be committed | backups applying uncommitted ops |

Mechanics, step by step:

1. The client sends REQUEST to the primary with its client id and a monotonically
   increasing request number. Replicas keep a client table (client -> last request
   number and last reply, replicated as part of state); a stale or duplicate request
   number gets the cached reply resent, never re-executed. This is how VR gives clients
   exactly-once semantics.
2. The primary picks the next op number, appends the operation to its log, and sends
   PREPARE to all backups.
3. A backup checks the view and op number for consistency with its own log, appends,
   and replies PREPAREOK. It must not apply the operation yet.
4. When the primary has `f` PREPAREOKs - itself makes `f + 1` - the operation is
   committed. The primary applies it and replies to the client.
5. COMMIT messages (or piggybacked commit numbers on later messages) tell backups how
   far it is safe to apply. A replica with a hole in its log cannot apply past it and
   must fetch the missing entries (state transfer from another replica).

A request sent to a non-primary is forwarded or answered with current view information,
so clients converge on the real primary in one round trip.

## Why 2f + 1: the Intersection Argument in One Paragraph

Suppose operation `X` commits in view `v`: `f + 1` replicas recorded it (the primary plus
`f` PREPAREOKs). Later, view `v'` installs a new primary from some quorum of `f + 1`
replies. Those two sets intersect in at least one replica that held `X` at the end of
view `v` and reports its log (view-change responses include each replica's op and commit
numbers), so the new primary's log contains `X`. No committed operation can be lost by a
view change - the same argument that makes Paxos majorities and
[quorum systems](../advanced/quorum-systems.md) safe. With `n = 3` you survive 1 failure;
with `n = 5`, 2; and nothing about the argument needs synchronized clocks.

## View Changes

Any backup that stops hearing from the primary - no PREPARE, no COMMIT, no other
primary-known traffic - starts a view change for view `v + 1` after a timeout. VR never
trusts the primary to declare its own death; it also never lets a replica participate
with state it cannot vouch for.

```text
  replicas suspect primary of view v          backup i (timeout)          replica j
        |                                            |  DOVIEW(v+1, last-normal-view,
        |                                            |    op#, commit#)   |
        |                                            |<-------------------|  (f+1 total,
        |                                            |   including own)   |   with logs)
        |  new primary = (v+1) mod n                 |                    |
        |  picks log so it covers every committed op |                    |
        |                                            |--STARTVIEW(v+1, log, op#, commit#)
        |                                            |   to every other replica
```

- The new primary is the next replica in order - rotation, not election. There is no
  randomized election and no candidate campaigning; the failure detector just decides
  when the rotation happens.
- The quorum of DOVIEW responses tells the new primary the highest view any witness saw
  (aborting if a higher view is already running) and lets it reconstruct a log that
  covers everything the intersection argument guarantees.
- STARTVIEW distributes that log and current numbers; lagging replicas catch up by
  state transfer, and a replica that was itself recovering stays out of quorums until
  its state is valid again.

The subtlety worth remembering: the new primary may itself have been lagging. Raft
solves this the opposite way - a candidate must be fully up to date before it can win an
election (voters compare (lastTerm, lastIndex) and refuse stale candidates), while VR
installs the designated successor first and lets it pull missing operations from the
quorum during the view change. Different mechanism, same guarantee.

## Recovery

A crashed replica that comes back knows nothing: not the view, not the log, not the
commit number. VR's recovery protocol has it query a quorum, adopt the latest committed
state those replicas agree on, and only then rejoin normal operation. The recovering
replica marks its state invalid and refuses to take part in view changes or prepares
until recovery completes - otherwise its stale numbers could poison a quorum.

The primary's recovery matters most: a recovered replica must not resume as primary with
a log missing committed operations. VR Revisited makes the recovering primary run the
same quorum exchange and re-prove its log before accepting writes. This is the case
chain replication punts to its master, and the case that makes naive "restart the leader
and replay the local log" designs quietly unsafe.

## Reconfiguration: the Part Paxos Left Out

VR treats "the set of replicas is changing" as a normal concern of the protocol rather
than an afterthought. Reconfiguration runs in epochs: the current group processes a
reconfiguration request like any other operation, but the operation names the next
membership. The old replicas must hand over enough state (snapshots plus log suffixes)
for the new group to take over without a quorum gap, and the change must preserve
intersection across the epoch boundary. Practical consequence: a group running with
replicas that are merely slow - not crashed - should replace them early, because every
additional failure shrinks the fault tolerance you bought with `2f + 1` machines. Raft's
joint consensus (2014) and single-server changes are the modern restatement of this
problem; VR had it in scope from the start.

## VR vs Raft vs Multi-Paxos

| Aspect | VR (1988/2012) | Raft (2014) | Multi-Paxos (1988/1998) |
| --- | --- | --- | --- |
| Leader | fixed rotation: view v -> replica v mod n | election among candidates | any replica with the highest ballot |
| Leader completeness | quorum pull during view change | vote restriction: candidate must have newest (term, index) | prepare phase with higher ballot |
| Heartbeat | COMMIT / Prepare traffic | AppendEntries | implementation-defined |
| Client dedup | client table: request numbers | session state on leader | rarely specified |
| Membership change | built in: reconfiguration ops and epochs | joint consensus or single-server | outside the original paper |
| Failure model | crashes, async network | crashes, async network | crashes, async network |

Lineage notes: Raft's paper explicitly positions itself as more understandable than
Paxos while acknowledging VR and ZAB ([ZAB](../consensus/zab.md) is ZooKeeper's
broadcast protocol, likewise leader-based with epoch numbers). TAPIR (SOSP 2015) built
transactional storage directly on VR, showing the protocol is still a viable substrate
thirty years on - VR's client table and op numbers are exactly what TAPIR needed for
exactly-once application of transaction writes.

## Interview Sharp Edges

- "Why f PREPAREOKs and not f + 1?" The primary counts itself; `f` acknowledgments make
  `f + 1` replicas holding the operation, which is the quorum every later argument uses.
- "Can a view change lose committed data?" No - that is the intersection argument. What
  it can lose is uncommitted operations: entries prepared but not yet acknowledged at
  `f + 1` replicas may vanish, and clients retry them in the new view (request numbers
  make the retry safe).
- "Why do backups wait for COMMIT before applying?" Between PREPAREOK and COMMIT the
  primary may fail; replicas must not expose state that might be rolled back, so apply
  trails the commit number.
- "What actually distinguishes VR from Raft?" Less than you would guess: rotation plus
  quorum-pulled logs versus elections plus vote restrictions; client tables versus
  leader sessions; epoch-based reconfiguration versus joint consensus. The guarantees
  are the same shape: linearizable log, `f` of `2f + 1`, crash faults.
- "Does VR need stable storage?" The Revisited design assumes replicas keep state in
  volatile memory and recover it from quorums, precisely because rebuilding from `f + 1`
  peers is cheap - a deliberate contrast with protocols that persist every log append.

## References

- Viewstamped Replication - Oki and Liskov (PODC 1988): https://doi.org/10.1145/62546.62549
- Viewstamped Replication Revisited - Liskov and Cowling (2012): https://arxiv.org/abs/1303.5450
- TAPIR: Building Consistent Transactions with Inconsistent Replication (SOSP 2015): https://doi.org/10.1145/2815400.2815415
- Raft homepage and paper (Ongaro and Ousterhout, USENIX ATC 2014): https://raft.github.io/raft.pdf
