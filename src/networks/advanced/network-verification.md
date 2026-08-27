# Network Verification: Why Configs Lie and How to Catch Them

Every major cloud has had an outage caused not by hardware but by a router
configuration that every device accepted without complaint. Microsoft traced
one Azure outage to a misconfigured network device back in 2012 -- that
incident is still the canonical motivating citation in the verification
literature (it is in the Minesweeper paper's reference list). The uncomfortable
truth: a config is a distributed program written in five vendor dialects,
executed by routers whose behavior is only partially documented, and deployed
with no unit tests. Network verification replaces "lab it and pray" with a
tool that loads your configs, builds a model of what the network would do,
and answers questions about it -- before deployment.

[Modern Network Architecture](./modern-network-arch.md) carries a short survey
of these tools; this page is the deep dive: the models, the papers, the
failure classes, and a runnable micro-verifier.

## Where Configuration Bugs Come From

Verification papers converge on three bug classes, and the difference matters
because each needs a different checker:

1. **Propagation bugs.** A route-map, prefix-list, or export policy does
   something other than its author assumed, so a prefix silently fails to
   spread. The config on R4 is "fine"; the missing route appears three hops
   away. Control-plane verifiers exist precisely for this class.
2. **Interaction bugs.** Two features are individually correct and jointly
   broken: an ACL contradicts a NAT rule, redistribution re-advertises a
   summary into a region that already has specifics, a TE steering policy
   pins traffic onto a path routing cannot keep alive. This is the argument
   for whole-network models over per-device linting.
3. **Drift.** Hundreds of same-role devices were configured by different
   humans in different years. They were equivalent on the day they shipped
   and are not equivalent now. "Local equivalence" checks find this
   mechanically.

## The Pipeline: Configs -> Model -> Queries

```text
   vendor CLI configs               verification queries
   (IOS, IOS-XR, Junos, FRR)     "can A reach B on port 443?"
          |                                |
          v                                v
   +-------------+   +-----------------+   +---------------+
   | parse and   |-->| unified network |-->| search engine |
   | normalize   |   | model: nodes,   |   | (fixpoint or  |
   | per-vendor  |   | links, route    |   | SMT solver)   |
   | syntax      |   | maps, ACLs, RIBs|   |               |
   +-------------+   +-----------------+   +---------------+
          |                   |                      |
          v                   v                      v
    git config repo    simulated protocol      counterexample +
    (the snapshot)     execution -> RIBs       human explanation
                       -> FIBs -> FECs         of the violating path
```

Two vocabulary items carry most of the field:

- **Forwarding Equivalence Class (FEC).** The set of packets a device treats
  identically. Instead of reasoning packet by packet (impossible), verifiers
  reason per class: every packet in a class crosses the same rule sequence
  and lands in the same place. One check per class covers astronomically many
  packets.
- **Control plane vs data plane.** The control plane is the protocol machinery
  (OSPF, BGP, IS-IS) that computes RIBs from configs; the data plane is the
  FIB/TCAM state those RIBs installed. You can verify either, and the tools
  split cleanly along this line:

```text
 control-plane verifier                data-plane verifier
 (Batfish, Minesweeper)                (HSA, VeriFlow)

 configs -> simulate protocol      snapshot of FIB / TCAM rules
 exchanges -> RIBs -> FIBs         -> partition traffic into FECs
 -> check intended properties      -> check each class against
 before anything is deployed          live or frozen state

 finds: route never learned,        finds: loop after update,
 export policy contradicts          shadowed TCAM entry,
 intent, BGP session dead           black hole in current tables
```

Control-plane verification is *proactive*: it runs on candidate configs in a
git branch and catches errors before deployment. Data-plane verification is
*reactive or inline*: it analyzes what devices have actually installed, which
makes it the natural tool for validating live network updates.

## The Tool Lineage, 2012-2017

**Header space analysis (NSDI 2012).** Kazemian, Varghese, and Attie's insight
was representational: a packet header is one point in a `2^W`-dimensional
space (W = header width), and each forwarding rule is a region of that space.
Forwarding becomes a function from header space to header space, and analysis
becomes set algebra -- union, intersection, complement, difference over
wildcard expressions. Loop detection and shadowed-rule detection reduce to set
operations that run in real time. HSA founded the data-plane verification
line; later tools kept the representation and refined the computation.

**VeriFlow (NSDI 2013).** Khurshid et al. asked the scaling question:
verification is useless if it takes minutes when the network changes every
second. VeriFlow partitions forwarding state into equivalence classes once,
then processes each update incrementally -- recomputing only the classes the
update touches and checking each against invariants (no loops, no black
holes, policy-consistent reachability). The per-update cost is small enough
to run inline with SDN controller updates; the idea -- check the diff, not
the world -- is what makes verification usable in CI pipelines.

**Batfish (NSDI 2015).** "A General Approach to Network Configuration
Analysis" (Fogel, Fung, Pedrosa, Walraed-Sullivan, Govindan, Johari,
Millstein) made the control-plane side rigorous. It defines a formal model of
how routers exchange routes, encodes it in a Datalog variant (LogiQL on the
LogicBlox engine), and derives the data plane by computing the fixpoint of
that program. Properties are first-order-logic formulas over the resulting
relations, and because the derivation is declarative, the tool can produce
the concrete packets that violate a property. The authors analyzed two large
university networks; operators confirmed the majority of findings as real
misconfigurations. Batfish later became the open-source project at
[batfish.org](https://www.batfish.org) -- it is the tool most "how do you
test network changes?" interview answers are really about.

**Minesweeper (SIGCOMM 2017).** Minesweeper (Beckett, Gupta, Mahajan, Walker
-- Microsoft Research and Princeton; paper "A General Approach to Network
Configuration Verification") took the opposite point in the design space:
instead of simulating one environment at a time, encode *all* stable states
of the network as an SMT formula and let the solver decide whether any state
violates the property. Unsatisfiable means the property holds in every stable
state (all BGP message orders, all link failures); a satisfying assignment
*is* the counterexample. It checks reachability, isolation, waypointing,
black holes, bounded path length, load balancing, and router-role equivalence
-- graph properties path-based tools cannot express. Minesweeper also ships
inside Batfish as the `smt-` query family, so both strategies coexist in one
tool ([batfish.org/minesweeper](https://batfish.org/minesweeper)). For solver
mechanics see [SAT and SMT Solvers](../../formal-methods/sat-smt-solvers.md)
and [Symbolic Execution](../../formal-methods/symbolic-execution.md).

## What Operators Actually Ask

- **Reachability and black holes.** Can host A reach service B's port? Does
  any prefix die at a device with no route?
- **Loops.** Does any packet revisit a device under the candidate configs?
- **Shadowed rules.** Is any ACL/route-map entry unreachable because an
  earlier entry covers it? A shadowed *permit* is missing reachability; a
  shadowed *deny* is a security hole.
- **Load-balancing consistency.** With multiple equal-cost paths, every path
  must deliver the packet and per-flow choice should be deterministic
  ("multipath consistency" in Minesweeper's property set).
- **BGP checks** -- the highest-value category in practice: eBGP/iBGP sessions
  can actually establish (ASN, authentication, update-source, and TTL
  contracts modeled, not assumed); route-reflector client wiring is equivalent
  to the full-mesh design it replaced; export policies do not leak
  transit-learned routes toward providers; same-role routers (two border PEs,
  two route reflectors) treat the same route identically -- the drift
  detector from the taxonomy above.

None of that is observable from SNMP, and all of it is checkable from a
config snapshot in a CI job.

## The Cloud Deployment Story

The Minesweeper evaluation is the most concrete published account of
verification against production configs, and the numbers get cited constantly:

- It ran against **152 real networks from a large cloud provider** -- 2 to 25
  routers each, 1,000 to 23,000 config lines, running OSPF, eBGP, iBGP,
  static routes, ACLs, and route redistribution.
- The networks had been operational for years, so easy bugs were assumed
  gone. Minesweeper still reported **120 property violations**, some described
  as potentially serious security vulnerabilities -- found without knowing
  operator intent, purely from structural invariants like "management
  interfaces reachable from every node" and "same-role routers behave
  equivalently."
- On synthetic benchmarks it verified rich properties for networks of
  **hundreds of routers in under five minutes**, with model-slicing and
  hoisting optimizations cutting runtime by **over 460x** on large networks.

The paper says "large cloud provider"; the Microsoft Research affiliation and
the Azure-outage motivation reference are why people call this the Azure
verification story.

## Choosing a Search Strategy

| Strategy | Mechanism | Counterexamples | Best at |
|----------|-----------|-----------------|---------|
| Concrete fixpoint (Batfish) | Simulate protocol exchanges over sampled environments until stable | Yes -- concrete traces | Scale and fidelity on full vendor configs; daily CI |
| Symbolic header sets (HSA) | Set algebra over `2^W` header-space regions | Yes -- violating region | Data-plane invariants, TCAM-scale rule sets, real time |
| Incremental FEC checks (VeriFlow) | Re-verify only the classes an update touches | Yes -- failing class + invariant | Inline validation of live updates and SDN controllers |
| SMT over all stable states (Minesweeper) | One formula per property over the whole state space | Yes -- satisfying assignment | "Always holds" guarantees, failure environments, graph properties |

The honest trade-off: concrete simulation scales furthest but only checks
environments you thought to enumerate; SMT checks all environments but leans
on solver time that can explode on huge networks -- hence Minesweeper's
slicing and hoisting optimizations, and hence Batfish integrating both
strategies instead of choosing one.

## A Micro-Verifier in 70 Lines

The pipeline -- propagation model, forwarding trace, rule shadow analysis --
fits in a short Python program. The shadow check is exact: each rule's match
region is a 3-D interval box, and interval subtraction (the rectangle algebra
HSA-style tools use) decides coverage.

```python
"""Micro verifier: propagation fixpoint, forwarding trace, ACL shadows."""
P, R = "203.0.113.0/24", ["R1", "R2", "R3", "R4"]
LINKS = [("R4","R2"),("R2","R4"),("R4","R3"),("R3","R4"),
         ("R2","R1"),("R1","R2"),("R3","R1"),("R1","R3")]
EXP = {("R4","R2"): 1, ("R2","R4"): 1, ("R3","R4"): 1, ("R4","R3"): 0,  # BUG
       ("R2","R1"): 1, ("R1","R2"): 1, ("R3","R1"): 1, ("R1","R3"): 0}

def reach(fix):
    """Flood routes to a fixpoint (R4->R3 carries a stale prefix-list)."""
    ok = dict(EXP); ok[("R4","R3")] |= fix
    have = {n: n == "R4" for n in R}
    for _ in R:
        new = [(a,b) for (a,b) in LINKS if ok[(a,b)] and have[a] and not have[b]]
        if not new: break
        for (a,b) in new: have[b] = True
    return have

PIN = {"R1": "R3"}                   # TE steering / policy routing on R1

def trace(have):
    path, cur = ["R1"], "R1"
    for _ in range(2 * len(R)):      # hop budget; doubles as loop guard
        if cur == "R4":
            return path, "delivered"
        nxt = PIN.get(cur) or next((b for (a,b) in LINKS
                                    if a == cur and have[b]), None)
        if not nxt or not have[nxt]:
            return path + ["DROP(no route)"], "BLACK HOLE"
        path.append(nxt); cur = nxt
    return path + ["LOOP"], "FORWARDING LOOP"

# ACL: (id, action, (src), (dst), (ports)). Toy 8-bit address space: the
# server /24 is dst [0,63]; guest block src [128,255]; ops subset [128,159].
ACL = [(10,"deny",(128,255),(0,255),(0,65535)),  (20,"permit",(128,159),(0,63),(22,22)),
       (30,"permit",(0,127),(0,63),(22,22)),     (40,"deny",(0,255),(0,255),(0,65535))]

def minus(box, cut):
    """Box minus box -> disjoint pieces tiling the difference."""
    if any(box[d][1] < cut[d][0] or box[d][0] > cut[d][1] for d in range(3)):
        return [box]
    out = []
    for d in range(3):
        (lo,hi),(c0,c1) = box[d], cut[d]
        if lo < c0: out.append(box[:d] + ((lo,c0-1),) + box[d+1:])
        if hi > c1: out.append(box[:d] + ((c1+1,hi),) + box[d+1:])
    return out

def shadow(rules, i):
    """First earlier rule covering all of rule i's region, or None."""
    parts = [rules[i][2:]]
    for j in range(i):
        parts = [p for b in parts for p in minus(b, rules[j][2:])]
        if not parts: return j
    return None

for label, fix in (("A. as committed", 0), ("B. export typo fixed", 1)):
    have = reach(fix)
    path, verdict = trace(have)
    print(f"=== {label} ===")
    print("route to", P + ":",
          " ".join(f"{n}={'yes' if have[n] else 'no'}" for n in R))
    print(f"data plane: {' -> '.join(path)}")
    print(f"verdict   : {verdict}\n")

print("=== ACL shadow analysis on R1 ingress ===")
for i, (rid, act, s, d, p) in enumerate(ACL):
    j = shadow(ACL, i)
    det = (f"SHADOWED by rule {ACL[j][0]} ({ACL[j][1]} first, {act} dead)"
           if j is not None else "consulted")
    print(f"rule {rid} {act:<6} src {s[0]}-{s[1]:<3} dst {d[0]}-{d[1]:<3} "
          f"port {p[0]}-{p[1]:<5} -> {det}")

print("\n=== verifier report ===")
n = 1
if trace(reach(0))[1] == "BLACK HOLE":
    print(f"{n}. black hole: R1 steers {P} to R3, which never learned it"); n += 1
for i, (rid, act, *_ ) in enumerate(ACL):
    j = shadow(ACL, i)
    if j is not None and ACL[j][1] != act:
        print(f"{n}. shadowed rule {rid}: '{act}' dead under rule "
              f"{ACL[j][0]} '{ACL[j][1]}'"); n += 1
```

Output (real run):

```text
=== A. as committed ===
route to 203.0.113.0/24: R1=yes R2=yes R3=no R4=yes
data plane: R1 -> R3 -> DROP(no route)
verdict   : BLACK HOLE

=== B. export typo fixed ===
route to 203.0.113.0/24: R1=yes R2=yes R3=yes R4=yes
data plane: R1 -> R3 -> R4
verdict   : delivered

=== ACL shadow analysis on R1 ingress ===
rule 10 deny   src 128-255 dst 0-255 port 0-65535 -> consulted
rule 20 permit src 128-159 dst 0-63  port 22-22    -> SHADOWED by rule 10 (deny first, permit dead)
rule 30 permit src 0-127 dst 0-63  port 22-22    -> consulted
rule 40 deny   src 0-255 dst 0-255 port 0-65535 -> consulted

=== verifier report ===
1. black hole: R1 steers 203.0.113.0/24 to R3, which never learned it
2. shadowed rule 20: 'permit' dead under rule 10 'deny'
```

Finding 1 is the whole discipline in two lines: the control plane says R1 can
reach P (a route exists via R2), but a forwarding pin steers to R3, and no
control-plane-only lint would ever combine those two facts. Real verifiers do
exactly this combination with vendor-accurate protocol models instead of a
boolean flood.

## Limits Worth Knowing

- **Model fidelity is the bottleneck.** Verifiers are sound with respect to
  their model, and platform quirks (TCAM programming limits, vendor defaults,
  timer-dependent races) stay perpetually partial. A clean report is not a
  theorem about your silicon.
- **Intent is still yours.** Tools catch violations of properties you state;
  structural invariants catch a lot by accident, but someone writes the spec.
- **Convergence is harder than stability.** Minesweeper checks stable states;
  transient states need the update-consistency line (VeriFlow's incremental
  model, SDN update verification -- see [SDN and OpenFlow](./sdn-openflow.md)).
  The same rigor is starting to apply to source-routed designs -- see
  [SRv6](./srv6.md) for what verifiers would need to model there.

## References

- [Batfish -- open source network configuration analysis](https://www.batfish.org/)
- [Fogel et al., A General Approach to Network Configuration Analysis, NSDI 2015](https://www.usenix.org/conference/nsdi15/technical-sessions/presentation/fogel)
- [Kazemian et al., Header Space Analysis: Static Checking for Networks, NSDI 2012](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/kazemian)
- [Khurshid et al., VeriFlow: Verifying Network-Wide Invariants in Real Time, NSDI 2013](https://www.usenix.org/conference/nsdi13/technical-sessions/presentation/khurshid)
- [Beckett et al., A General Approach to Network Configuration Verification (Minesweeper), SIGCOMM 2017](https://dl.acm.org/doi/10.1145/3098822.3098834)
