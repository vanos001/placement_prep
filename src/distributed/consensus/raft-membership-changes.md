# Raft Membership Changes

Raft's log carries two kinds of state: application commands and the cluster
configuration itself. Reconfiguration is therefore not an administrative
afterthought bolted onto the side — it is a consensus problem of its own, and
the configuration entry is just another log entry replicated under the same
commit rules as everything else. The Raft line of work published two concrete
designs with different trade-offs: **joint consensus** (two-phase,
`C_old,new` transition) and **single-server changes** (one add or one remove
per entry). This page works through both, the safety arguments behind them,
the rules they impose on leaders mid-transition, and the uncomfortable
reality that nearly every production Raft ships only the second one.

## The failure mode any design must rule out

Suppose a leader switches its configuration atomically from
`C_old = {A, B, C}` to `C_new = {D, E, F}` the moment it decides to. The
third server `C` was in both configs, but nothing forces new and old
quorums to touch:

```text
        C_old = {A, B, C}                 C_new = {D, E, F}
        quorum {A, B}                     quorum {E, F}
        elects leader L1 (term 5)         elects leader L2 (term 6)

   A ---\                                 /--- D
   B ----+-- L1: has log thru idx 10     E ----+-- L2: has log thru idx 9
   C ----/                               F ----/
        (C never learned of C_new)       (D,E,F never saw A,B,C votes)
```

`{A, B}` is a majority of `C_old`; `{E, F}` is a majority of `C_new`. The two
sets are disjoint, so the classic election restriction ("a candidate must
have all committed entries") breaks: each quorum can elect a different
leader with a different view of the log, and two commits can diverge
irreversibly. Every safe reconfiguration mechanism — Raft's two, VR's
reconfiguration, Viewstamped Reconfiguration, Vertical Paxos — is an answer
to this single question: *how do you guarantee that any two quorums that can
simultaneously believe they are in charge overlap?* See
[consensus-advanced.md](../advanced/consensus-advanced.md) for the Paxos-side
treatment and [viewstamped-replication.md](../replication/viewstamped-replication.md)
for the ancestor protocol this problem was first solved in.

## Design 1: single-server changes (the delta log entry)

The approach the Raft paper presents as the practical alternative and the
Ongaro dissertation analyzes in depth (§4.4): each configuration entry
describes a **delta** — add one server, or remove one server — relative to
the previous entry. The effective configuration at log position `i` is the
accumulated result of applying every delta up to `i`. There is no joint
state and no second phase.

### Mechanics

1. **Adding a server.** The leader first brings the joiner's log up to date
   (an out-of-band catch-up / snapshot transfer) so the new node does not
   drag election availability down. Only then does it append the
   `add S_n` entry. A new server cannot vote before it appears in the
   configuration, so it cannot accidentally double-vote.
2. **Commit as usual.** The delta entry commits when replicated to a
   majority of the *current* (old) configuration — nothing about the commit
   rule changes, which is the whole elegance of the design.
3. **Removing a server.** The leader appends `remove S_k`. Once that entry
   is committed, `S_k` is no longer a voter: it neither receives
   ReplicateEntries traffic nor counts toward quorums.
4. **Candidates count votes against the latest configuration in their own
   log.** The `RequestVote` response carries the responder's latest
   configuration, so a candidate running with a stale config upgrades
   itself as soon as it hears from a fresher node and restarts election
   under the newer rules.

### The inductive safety argument

Why can one-server deltas never open the disjoint-quorum hole? Consecutive
configurations always share a majority:

- **Add one node `x`**: any majority of the new config contains a majority
  of the old one minus `x` — concretely, a majority of `n+1` servers has at
  least `(n+1)/2` members and at most one of them is `x`, so it still holds
  more than half of the old `n`. Two majorities of overlapping configs
  therefore intersect in at least one *old* server.
- **Remove one node**: by symmetry, a majority of the old config either
  already excludes the removed node or intersects the new config's
  majorities in a survivor.

Because the property "every quorum of config `i` intersects every quorum of
config `i+1`" holds per step, it holds transitively along the whole chain of
deltas — that is the induction the joint-consensus design was originally
built to achieve in one hop. The quorum-audit demo below checks this
exhaustively for a 3 → 4 → 5 chain.

### The special rules that make it work

The base protocol needs three amendments, and interviews love probing them:

| Rule | Statement | What breaks without it |
|------|-----------|------------------------|
| Leader in own config | A leader that is no longer in the latest configuration in its log steps down once that entry commits | A removed leader keeps replicating to a config that ignores it |
| Leader may add itself | When the next delta is an add and the leader is not a voter, the entry adds the leader | A non-member cannot commit its own reconfiguration |
| Resign on removal | A leader being removed keeps serving until the remove entry commits, then steps down and does not vote again | Removed leader and its replacement double-serve one command |
| Vote freshness | RequestVote/AppendEntries responses piggyback the sender's latest config | A candidate stuck on config `i` can win under rules config `i+1` has superseded |

One subtlety from the dissertation: a single-server change is only safe if
the leader's view of the configuration is not stale — the leader must not
append a delta on top of a configuration entry it has not actually seen
committed. The fix implemented in practice is the same staleness defense the
rest of Raft uses: entries only propagate from leaders, and leaders only
exist under configurations their log has caught up to.

### The availability cost

Safety per-step says nothing about availability across a chain of removals.
Dropping from 5 servers to 3 one at a time is safe, but if two of the five
are already dead you can strand yourself: removing a dead node shrinks the
live quorum set, and the chain of deltas may pass through configurations
where the survivors no longer form a majority. The standard mitigations are
**leader transfer** before removals, replacing instead of removing
(add-then-remove), and operators running `etcdctl member list` sanity checks
before each step. This is an operational discipline problem, not a protocol
bug — and it is a real production incident generator.

## Design 2: joint consensus (the two-phase transition)

The paper's first, fully general mechanism. Any configuration `C_old` can
move to any `C_new` in two committed steps, with no availability dip and no
per-step inductive argument required:

```text
 log:  ...  [cmds]   [C_old,new]      [cmds]   [C_new]
                    -------- committed --------> committed
                       ^                          ^
                       | phase 1                  | phase 2
 quorum rule:          maj(C_old) AND maj(C_new)   maj(C_new) only
 leader:               old leader keeps serving    old leader may step down
```

- **Phase 1.** The leader writes the `C_old,new` entry. Decisions under the
  joint configuration need a majority of `C_old` *and* a majority of
  `C_new` — both must sign off on every entry after the joint one.
- **Phase 2.** Once `C_old,new` commits, the leader writes `C_new` alone.
  Once `C_new` commits, `C_old` is retired, servers not in `C_new` step
  down, and the transition is final.

Why the two phases close the hole: while `C_old,new` is uncommitted, any
`C_old` quorum (from a leader that has not heard of the transition) still
intersects any joint quorum, because a joint quorum *contains* a `C_old`
majority. After the joint entry commits, no leader can be elected on
`C_old` alone — a candidate would need a `C_old`-majority plus a
`C_new`-majority for the joint section of its log, and that quorum still
intersects every joint quorum. The demo below enumerates this exactly: for
the disjoint 3+3 case, `maj(C_old) × maj(C_new)` overlap is 0, but
`C_old × joint`, `joint × joint`, and `joint × C_new` overlaps are all ≥ 1.

Costs and benefits versus deltas:

| Dimension | Joint consensus | Single-server changes |
|-----------|-----------------|-----------------------|
| Steps for arbitrary change | One transition, any size | Chain of single add + remove deltas |
| Quorum cost during transition | Both configs (slowest of the two) | Current config only |
| Availability during change | No dip by design | Can dip across removal chains |
| Complexity | Two-phase state machine, joint quorum checks | Tiny; config is a running delta |
| Leader resignation | Old leader steps down after `C_new` commits | Steps down when own removal commits |

## What production actually ships

Here is the part interviewers rarely expect candidates to know: joint
consensus is the *paper's* flagship mechanism, yet it is nearly absent from
deployed systems. The reference implementation of joint consensus is
Ongaro's own LogCabin. The systems most engineers touch — etcd, Consul
(hashicorp/raft), TiKV, CockroachDB — implement single-server changes. The
dissertation itself flags the asymmetry, and the etcd runtime-reconfiguration
guide exposes exactly the delta operations (`member add`, `member remove`,
`member update`), one member at a time.

The reasons are pragmatic: single-server changes need no second quorum
during the transition, they reuse the ordinary commit path verbatim, and the
joint state machine is genuinely hard to test (two active configs means two
sets of live quorums, double failure-handling, and a leader whose
resignation timing is phase-dependent). The honest engineering summary:
joint consensus is the completeness result that proves arbitrary
reconfiguration is safe in one bound; single-server changes are what
operations actually pays for.

## Recovery from a lost quorum

No reconfiguration protocol can help once a majority is permanently gone —
by design. If it could, a partitioned minority could also "help" itself,
which is exactly the safety property you paid consensus to get. With 2 of 3
nodes dead, the surviving node cannot remove them: a quorum of the current
config is required to commit the remove deltas. The documented paths are:

1. **etcd**: restore from a snapshot into a new cluster
   (`etcdctl snapshot restore` with an explicit `--initial-cluster`), then
   point clients at the new cluster. The old cluster is abandoned, not
   repaired — its log is dead weight once its quorum is lost.
2. **Consul / hashicorp/raft**: the same shape — a `-raft-recovery` style
   peer-cleanup run from an operator-supplied configuration file built from
   the last snapshot and any live peer's data.
3. **Prevention**: an odd, evenly-spread voter count (3 or 5, one per
   failure domain), never an even one, and alerting on `member health`
   before any member surgery.

The one legitimate in-protocol trick for *imminent* (not already-lost)
quorum: if two of three are failing but the cluster still has quorum, use
normal single-server deltas to shrink to the surviving member — deliberately
operating with a one-node quorum — then rebuild outward. That window is
exactly why operators rehearse `member remove` before the second disk dies.

## Common failure modes to be able to name

- **Removing a member with no replacement** in a 3-node cluster and losing
  the delta commit mid-way: the config entry is half-replicated; recovery
  proceeds from the last committed config, not from the operator's
  intention.
- **Even-sized clusters** (`member add` "temporarily" making it 4): the
  quorum grows to 3, so availability drops until the next remove —
  opposite of the operator's instinct.
- **New node added without catch-up**: joiner starts voting while its log
  is far behind, election timeouts spike cluster-wide as Raft re-elects
  around the laggard.
- **Testing only the happy add**: Jepsen-style reconfiguration tests
  ([jepsen.md](../testing/jepsen.md)) interleave adds, removes, partitions,
  and crashes; the interesting bugs live in leader resignation windows.

## Quorum-intersection audit (runnable check)

The script enumerates every majority quorum in each phase of a transition
and reports the minimum overlap between every pair of quorum families. A
zero anywhere means two disjoint quorum families can both elect leaders —
the split-brain signature from the first diagram.

```python
"""Quorum-intersection audit across a Raft membership transition.

Experiments:
  1. UNSAFE one-shot switch C_old={A,B,C} -> C_new={D,E,F}: a C_old majority
     and a C_new majority may be disjoint -> two leaders possible.
  2. Joint consensus: a quorum must be a majority of C_old AND of C_new;
     check intersection against every other phase's quorum.
  3. Single-server chain C0={A,B,C} -> C1={A,B,C,D} -> C2={A,B,C,D,E}:
     inductively check every consecutive pair of configs.
"""
from itertools import combinations

def majorities(cfg):
    """All majority subsets (voter sets granting a leader its votes)."""
    n = len(cfg)
    k = n // 2 + 1
    return {frozenset(c) for c in combinations(sorted(cfg), k)}

def min_overlap(qs1, qs2):
    return min(len(q1 & q2) for q1 in qs1 for q2 in qs2)

C_old, C_new = frozenset("ABC"), frozenset("DEF")
m_old, m_new = majorities(C_old), majorities(C_new)
joint = {qo | qn for qo in m_old for qn in m_new}   # need votes from BOTH

print("EXP 1: one-shot switch, C_old={A,B,C} -> C_new={D,E,F}")
print("  C_old majorities:", len(m_old), " C_new majorities:", len(m_new))
print("  min overlap maj(C_old) x maj(C_new):",
      min_overlap(m_old, m_new),
      "-> 0 means two disjoint quorums can elect two leaders: UNSAFE")

print("EXP 2: joint consensus quorum = maj(C_old) AND maj(C_new)")
print("  joint quorums:", len(joint), " smallest size:", min(map(len, joint)))
phases = [("C_old", m_old), ("joint", joint), ("C_new", m_new)]
for n1, p1 in phases:
    for n2, p2 in phases:
        print("  %-6s x %-6s min overlap: %d" % (n1, n2, min_overlap(p1, p2)))

print("EXP 3: single-server chain {A,B,C} -> {A,B,C,D} -> {A,B,C,D,E}")
chain = [frozenset("ABC"), frozenset("ABCD"), frozenset("ABCDE")]
for a, b in zip(chain, chain[1:]):
    ov = min_overlap(majorities(a), majorities(b))
    print("  maj(%s) x maj(%s): min overlap %d -> safe" %
          (",".join(sorted(a)), ",".join(sorted(b)), ov))
```

Read the output against the theory: the single zero in EXP 2 is exactly the
`C_old × C_new` cell — the phase pair that never coexists once joint
consensus is in force. EXP 3's minimum overlap of 1 per step is the
inductive base for single-server safety.

```text
EXP 1: one-shot switch, C_old={A,B,C} -> C_new={D,E,F}
  C_old majorities: 3  C_new majorities: 3
  min overlap maj(C_old) x maj(C_new): 0 -> 0 means two disjoint quorums can elect two leaders: UNSAFE
EXP 2: joint consensus quorum = maj(C_old) AND maj(C_new)
  joint quorums: 9  smallest size: 4
  C_old  x C_old  min overlap: 1
  C_old  x joint  min overlap: 1
  C_old  x C_new  min overlap: 0
  joint  x C_old  min overlap: 1
  joint  x joint  min overlap: 2
  joint  x C_new  min overlap: 1
  C_new  x C_old  min overlap: 0
  C_new  x joint  min overlap: 1
  C_new  x C_new  min overlap: 1
EXP 3: single-server chain {A,B,C} -> {A,B,C,D} -> {A,B,C,D,E}
  maj(A,B,C) x maj(A,B,C,D): min overlap 1 -> safe
  maj(A,B,C,D) x maj(A,B,C,D,E): min overlap 1 -> safe
```

## Interview drills

1. *Why can't a leader append `C_new` while `C_old,new` is still
   uncommitted?* Because a future leader could be elected under `C_old`
   without the joint entry and fork history before the joint config ever
   took effect — the joint entry must gate the final one.
2. *A 5-node cluster must drop 2 dead members; you're down to 3 alive. Walk
   the safe operational sequence and say where it can go wrong.*
3. *Your team's Raft fork commits config entries against "majority of
   current config" but lets a removed leader keep voting until it notices.
   Name the interleaving that breaks it.*
4. *Why does etcd refuse `member add` when the cluster has lost quorum?*
   Because committing the add delta itself requires a quorum — the protocol
   cannot bootstrap out of a lost majority (see recovery above).

## References

- Ongaro & Ousterhout, "In Search of an Understandable Consensus Algorithm
  (Extended Version)" — membership changes in the section on cluster
  membership changes. <https://raft.github.io/raft.pdf>
- Ongaro, *Consensus: Bridging Theory and Practice* (PhD dissertation,
  Stanford, 2014) — §4.4 single-server changes, LogCabin implementation.
  <https://github.com/ongardie/dissertation>
- etcd operations guide, "Runtime reconfiguration" — member add/remove/
  update procedure and the one-member-at-a-time rule.
  <https://etcd.io/docs/v3.5/op-guide/runtime-configuration/>
- etcd operations guide, "Disaster recovery" — snapshot restore for lost
  quorum. <https://etcd.io/docs/v3.5/op-guide/recovery/>
- hashicorp/raft — production single-server change API (`AddVoter`,
  `RemoveServer`). <https://github.com/hashicorp/raft>
