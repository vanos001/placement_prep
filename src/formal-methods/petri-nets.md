# Petri Nets: Token Semantics for Concurrent Systems

An automaton has one program counter, so it can only ever be *in* one state. Concurrency
breaks that assumption: a producer and a consumer act in parallel, a bus controller serves
several requests, a workflow fork spawns tasks whose order nobody fixed in advance. Carl
Adam Petri's 1962 thesis proposed a different primitive: state lives *distributed across
places*, and computation moves *tokens* along arcs. Partial order, conflict, and
synchronization become first-class instead of being simulated by `2^n` interleaved
automaton states.

This page covers the formal core (places, transitions, the firing rule), the practical net
families, the analysis results (invariants, reachability, coverability, boundedness,
liveness), the decidability picture and its link to vector addition systems, a runnable
simulator, and the tools you would actually reach for. For the general model-checking
framing these nets plug into, see [Model Checking](./model-checking.md).

## Places, Transitions, Markings, and the Firing Rule

A **place/transition (P/T) net** is `N = (P, T, W)` with disjoint place set `P`, transition
set `T`, and arc weights `W : (P x T) union (T x P) -> N`. A **marking** `M : P -> N`
assigns a token count to every place -- the net's current state.

The firing rule is the whole semantics:

1. A transition `t` is **enabled** at `M` when every input place holds enough tokens:
   `M(p) >= W(p, t)` for all `p` in the pre-set of `t`.
2. **Firing** consumes the input tokens and produces the output tokens:
   `M'(p) = M(p) - W(p, t) + W(t, p)`.

Two transitions enabled simultaneously are **concurrent** if they compete for no tokens;
if they need the same token, they are in **conflict**, and the choice of which fires is
nondeterministic -- that is how choice and race conditions get modeled honestly.

```text
      1-token mutual exclusion, before and after firing

        (free)              (free)
          |                   |
          v                   v
   (p1)-->[enter]-->(cs)   (p1)  [enter disabled: no token in (free)]
   (p2)                    (p2)-->[enter]-->(cs)   <- after p2 fires

   Places: p1, p2 (processes waiting), cs (critical section), free (the mutex)
   One token in (free) means the critical section is available.
```

The name **token game** is standard: to check anything about a net you slide tokens
around. What makes nets more than a notation is that the *state* is the whole marking, so
interleaving is implicit and the reachable state space is exactly what a model checker
explores.

## The Net Family Tree

| Class | Tokens carry | Time | Typical use | Representative tools |
|---|---|---|---|---|
| Place/transition (P/T) | nothing (just count) | untimed | protocol + workflow structure | LoLA, TAPAAL |
| Colored (CPN) | typed data values | untimed | protocols with parameters, resource IDs | CPN Tools |
| Timed-arc | tokens with ages | real-valued ages | real-time schedulers, network protocols | TAPAAL |
| Stochastic (GSPN) | rates on transitions | exponential delays | manufacturing throughput, reliability | GreatSPN, TimeNET |
| Continuous / hybrid | real-valued markings | piecewise flows | chemical processes, batch plants | hybrid model checkers |
| Workflow nets (WF-net) | case data via color | untimed | business process soundness | ProM, CPN Tools |

Colored nets collapse combinatorial duplication (a token that is "packet #7 for flow 2"
instead of seven anonymous tokens); stochastic nets attach rates so the same structure
answers queueing questions; hybrid nets mix discrete transitions with continuous tank
levels. Structure is shared, so most P/T analysis carries over.

## Boundedness, Safeness, Liveness: Worked Mini-Nets

These are the behavior words both interviewers and papers mean:

| Property | Definition | Checked how |
|---|---|---|
| Safe (1-bounded) | every place holds at most 1 token in every reachable marking | reachability exhaustion |
| Bounded (k-bounded) | some k bounds every place across all reachable markings | reachability or coverability |
| Deadlock-free | every reachable marking enables some transition | reachability |
| Live | every transition can still fire eventually from any reachable marking | liveness analysis (siphons, coverability) |

```text
  (a) SAFE: producer with a 1-slot buffer        (b) DEADLOCK: a classic bug

  (ready)<--[produce]--(in)        [a]--(swap)-->[b]     swap enabled at (1,1):
  (free)<--[serve]----(out)        [b]--(swap)-->[a]     (1,1) -> (0,0): stuck
  1 slot => ready <= 1 => safe     swap enabled at (0,0) too, and it empties the net
```

Net (b) deserves a second look: both firings *decrease* the token count. No amount of
testing individual traces finds this reliably; exhaustive reachability finds it in
milliseconds. That gap between "looks fine" and "is live" is the net-checking value
proposition.

## Reachability Graphs, Coverability, and the Complexity Wall

For a **bounded** net the reachable markings are finite, so the semantics *is* a labeled
transition system: nodes are markings, edges are firings. Everything becomes ordinary
explicit-state model checking -- LTL properties, deadlocks, home states (see
[Temporal Logic](./temporal-logic.md)).

Unbounded nets break finiteness, so the **Karp-Miller coverability tree** (1968) replaces
exact counts with `omega` ("some unbounded number"): whenever a marking is reached that
covers an ancestor componentwise, the covered components become `omega`. The result is a
finite *over-approximation* that still answers coverability and boundedness questions,
though it can be exponentially larger than needed -- modern tools use efficient variants
(expand-and-shorten trees, interval or polyhedral encodings).

The complexity picture is the reason this field keeps mathematicians employed (reachability's
decidability was settled by Mayr in 1981 after a 20-year open problem; the bounds below are
the modern sharpenings):

| Problem | Decidable? | Known bounds |
|---|---|---|
| Reachability (can marking M occur?) | yes | non-elementary (Czerwinski et al. 2019); Ackermann-complete (Leroux-Schmitz 2019) |
| Boundedness / coverability | yes | EXPSPACE-complete (Rackoff 1978 upper, Lipton 1976 lower) |
| Liveness | yes | reduces to reachability-family results |
| Deadlock-freedom | yes | coverability-tier |

The exponential gap between the *finite* coverability structure and the *brutal* worst-case
bounds is why tool engineering matters: LoLA, TAPAAL, and colleagues win the annual Model
Checking Contest by symbolic reduction, partial-order methods, and over-approximation
tuning, not by implementing the textbook algorithms naively.

## Vector Addition Systems: Why P/T Nets Inherit Decidability Results

A **Vector Addition System with States (VASS)** is a finite automaton whose transitions add
integer vectors to a counter vector; a Petri net is a VASS whose "states" are the
transitions and whose counters are the places. The translation is mechanical in both
directions (Hack, MIT 1976 memo), so every decidability and complexity result proven for
one formalism transfers to the other -- and the two literatures jointly cover verification
of counter programs (see [Computability](../cs-theory/computability.md) for why these
decidability islands are remarkable: reachability for richer models is usually
undecidable).

Practical consequence: an analysis of "does this boot loop leak file descriptors?" -- a
counter system -- is answered by the same coverability machinery as a token-net question.
That is why coverability appears in both the Petri-net tooling and the program-analysis
literature.

## Structural Analysis: Invariants and the State Equation

The **incidence matrix** `A` of a net has one row per transition, one column per place, and
entries `A[t, p] = W(t, p) - W(p, t)`. Firing sequence `sigma` moves the marking by
`M = M0 + A^T . sigma` -- the **state equation**. It is a relaxation (it also admits
*spurious* solutions that no firing sequence realizes) but a powerful one.

A **P-invariant** (S-invariant in the stochastic-net tradition) is a nonzero `x >= 0` with
`A^T . x = 0`: a weighted token sum that *every* firing conserves. A **T-invariant** is
`A . y = 0`: a firing multiset that returns the net to its starting marking -- the
signature of reproducible behavior. For the 2-slot buffer used in the demo below
(`slots, ready, buf, idle_c, busy`):

```text
                slots  ready  buf  idle_c  busy
  produce         -1     +1     0     0      0
  append           0     -1    +1     0      0          A (rows = transitions)
  serve            0      0    -1    -1     +1
  finish          +1      0     0    +1     -1

  P-invariant x = (1, 1, 1, 0, 1): every firing conserves
  slots + ready + buf + busy.  At M0 the sum is 2, so it stays 2 forever --
  certified by linear algebra, without enumerating a single state.
```

Structural results turn behavior questions into linear algebra: nets covered by
P-invariants are bounded without any state exploration; siphons (place sets that, once
empty, stay empty) characterize deadlocks; T-invariants certify recurring behavior.
Murata's survey remains the standard map of this territory.

## Python Demo: Firing Simulator, Reachability, Bound Check

The bounded buffer net is explored exhaustively (9 markings, per-place bounds, verdict);
the unbounded net blows the exploration cap and is convicted with a **cover witness** --
a marking reached that covers an earlier one, which the token game then replays forever.
Pure stdlib, deterministic:

```python
from collections import deque

# transitions: name -> (pre-multiset, post-multiset)
NET1 = {
    "places": ["slots", "ready", "buf", "idle_c", "busy"],
    "m0": {"slots": 2, "ready": 0, "buf": 0, "idle_c": 1, "busy": 0},
    "transitions": {
        "produce": ({"slots": 1}, {"ready": 1}),
        "append":  ({"ready": 1}, {"buf": 1}),
        "serve":   ({"buf": 1, "idle_c": 1}, {"busy": 1}),
        "finish":  ({"busy": 1}, {"idle_c": 1, "slots": 1}),
    },
}
NET2 = {"places": ["A"], "m0": {"A": 1},
        "transitions": {"fork": ({"A": 1}, {"A": 2})}}      # A -> A + A

def enabled(pre, m):
    return all(m.get(p, 0) >= w for p, w in pre.items())

def fire(pre, post, m):
    r = dict(m)
    for p, w in pre.items():
        r[p] -= w
    for p, w in post.items():
        r[p] = r.get(p, 0) + w
    return r

def explore(net, cap):
    """BFS over reachable markings -> (states, place bounds, capped)."""
    places = net["places"]
    start = tuple(net["m0"].get(p, 0) for p in places)
    seen, bounds, q = {start}, dict(zip(places, start)), deque([start])
    while q:
        md = dict(zip(places, q.popleft()))
        for pre, post in net["transitions"].values():
            if enabled(pre, md):
                m2 = tuple(fire(pre, post, md).get(p, 0) for p in places)
                if m2 not in seen:
                    seen.add(m2)
                    for i, p in enumerate(places):
                        bounds[p] = max(bounds[p], m2[i])
                    if len(seen) > cap:
                        return seen, bounds, True        # state explosion: give up
                    q.append(m2)
    return seen, bounds, False

def cover_witness(net, steps=64):
    """Greedy firing; M' >= M over an earlier M on the path proves unboundedness."""
    places, hist = net["places"], []
    m = tuple(net["m0"].get(p, 0) for p in places)
    hist.append(m)
    for _ in range(steps):
        for pre, post in net["transitions"].values():
            md = dict(zip(places, m))
            if enabled(pre, md):
                m = tuple(fire(pre, post, md).get(p, 0) for p in places)
                hist.append(m)
                for old in hist[:-1]:
                    if all(b >= a for a, b in zip(old, m)) and m != old:
                        return old, m, len(hist) - 1
                break
    return None

states, bounds, capped = explore(NET1, cap=1_000_000)      # exhaustive: bounded net
print("Net 1 (producer-consumer, 2-slot buffer):")
print(f"  reachable markings: {len(states)}")
print("  place bounds:      ", dict(sorted(bounds.items())))
mb = max(bounds.values())
print("  verdict:", ("CAP HIT" if capped else
                    f"BOUNDED, {'SAFE' if mb == 1 else 'not safe (max bound %d)' % mb}"))

states2, _, capped2 = explore(NET2, cap=500)               # unbounded net: cap kicks in
print("\nNet 2 (token-doubling transition):")
print(f"  exploration hit the 500-marking cap: {'yes' if capped2 else 'no'} -> suspect UNBOUNDED")
old, m2, k = cover_witness(NET2)
print(f"  cover witness after {k} firings: {old} --fork*--> {m2}")
print(f"  {m2} >= {old} componentwise, strictly greater -> tokens grow without bound")
print("  verdict: UNBOUNDED")

m = dict(NET1["m0"])                                       # concrete firing trace
print("\nFiring trace (Net 1), place order (slots, ready, buf, idle_c, busy):")
print("  m0          ", tuple(m[p] for p in NET1["places"]))
for t in ["produce", "append", "produce", "append", "serve", "finish"]:
    pre, post = NET1["transitions"][t]
    assert enabled(pre, m), f"{t} not enabled"
    m = fire(pre, post, m)
    print(f"  fire {t:<7} -> {tuple(m[p] for p in NET1['places'])}")
```

```text
Net 1 (producer-consumer, 2-slot buffer):
  reachable markings: 9
  place bounds:       {'buf': 2, 'busy': 1, 'idle_c': 1, 'ready': 2, 'slots': 2}
  verdict: BOUNDED, not safe (max bound 2)

Net 2 (token-doubling transition):
  exploration hit the 500-marking cap: yes -> suspect UNBOUNDED
  cover witness after 1 firings: (1,) --fork*--> (2,)
  (2,) >= (1,) componentwise, strictly greater -> tokens grow without bound
  verdict: UNBOUNDED

Firing trace (Net 1), place order (slots, ready, buf, idle_c, busy):
  m0           (2, 0, 0, 1, 0)
  fire produce -> (1, 1, 0, 1, 0)
  fire append  -> (1, 0, 1, 1, 0)
  fire produce -> (0, 1, 1, 1, 0)
  fire append  -> (0, 0, 2, 1, 0)
  fire serve   -> (0, 0, 1, 0, 1)
  fire finish  -> (1, 0, 1, 1, 0)
```

Note what the demo quietly teaches: Net 1 is bounded *because* the `slots` place
implements the P-invariant; delete `produce`'s input arc from `slots` and you get Net 2's
behavior class.

## Where Petri Nets Model Real Systems

**Workflow management.** A WF-net has one source place, one sink place, and every task on
some path between them; **soundness** (safe completion of every case, no dead tasks) is
decidable by reduction to net analysis. Van der Aalst's workflow verification work made
this the theoretical backbone of BPM engines, and his
[workflow patterns](http://www.workflowpatterns.com/) catalog recasts every control-flow
idiom (XOR/AND splits and joins, cancellation, iteration) as net fragments -- a shared
vocabulary across BPMN, BPEL, and YAWL.

**Manufacturing.** Flexible cells (robots, buffers, machines) are the textbook GSPN
application: tokens are parts, stochastic transitions are machining times, and the same
net answers both liveness (can this sequence of operations ever jam?) and throughput
(after attaching rates).

**Protocol negotiation.** Handshakes and resource allocation are naturally nets: each
party's states are places, message sends are transitions shared across the boundary.
Deadlock-freedom of a two-party negotiation is a coverability question; colored nets
carry sequence numbers.

## Verification Tooling

| Tool | Origin | Focus | Notable capability |
|---|---|---|---|
| TAPAAL | Aalborg University | timed-arc nets plus integer/continuous P/T nets | query-language verification, Model Checking Contest medalist |
| GreatSPN | University of Torino | generalized stochastic nets (GSPN) | structural analysis (invariants, bounds) + simulation |
| LoLA 2 | U. Rostock (K. Wolf) | LTL/CTL model checking over P/T nets | stubborn sets, sweep-line, invariant exploitation |

All three consume or export PNML (the standard net interchange format), which is the
practical answer to "should I model this in TAPAAL or GreatSPN?" -- model once, verify
against several engines, and let each tool's reduction stack attack the state explosion
from a different side. For the spec-side languages (the LTL/CTL formulas you hand these
tools), see [Temporal Logic](./temporal-logic.md); for protocol specs written as
TLA+-style state machines instead of nets, see [TLA+](./tla-plus.md).

## Cross-Links

- [Model Checking](./model-checking.md) -- the general engine a bounded net's reachability
  graph feeds into
- [Temporal Logic](./temporal-logic.md) -- LTL/CTL properties to ask of a net
- [TLA+](./tla-plus.md) -- spec distributed protocols as state machines rather than nets
- [Computability](../cs-theory/computability.md) -- why decidable reachability here is an
  island in an undecidable sea

## References

1. T. Murata, "Petri Nets: Properties, Analysis and Applications," *Proceedings of the
   IEEE* 77(4), 1989. doi:10.1109/5.24143
2. W.M.P. van der Aalst, "Verification of Workflow Nets," *ICATPN 1997*, LNCS 1248.
   doi:10.1007/3-540-63139-9_48; pattern catalog: <http://www.workflowpatterns.com/>
3. TAPAAL -- modeling, simulation and verification of Petri nets:
   <https://www.tapaal.net/> (documentation: <https://www.tapaal.net/documentation/>)
4. GreatSPN -- GSPN modeling and analysis, Universita di Torino:
   <http://www.di.unito.it/~greatspn/index.html>
5. LoLA 2 tool entry, Hamburg Petri Net Tools database:
   <https://www.informatik.uni-hamburg.de/TGI/PetriNets/tools/db/lola.html>;
   K. Wolf, "Petri Net Model Checking with LoLA 2," *Petri Nets 2018*, LNCS 10877.
   doi:10.1007/978-3-319-91268-4_18
