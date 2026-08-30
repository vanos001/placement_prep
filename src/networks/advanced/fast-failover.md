# Sub-Second Failover: BFD, IP Fast Reroute, and the Anatomy of a Repair

Availability is quoted in nines, but the experience of an outage is governed
by a different quantity: how long the network keeps forwarding into a black
hole after a path dies. That interval is a detection time (noticing the
failure) plus a repair time (rewriting the forwarding plane). This page
walks that pipeline -- protocol timers, Bidirectional Forwarding Detection,
SPF reconvergence, and pre-computed backups (LFA, Remote LFA, TI-LFA) -- with
the real RFC criteria and a runnable coverage calculator. The verification
angle (proving a candidate repair behaves before the failure) is
[Network Verification](./network-verification.md).

## The Failure-Detection Ladder

Every protocol notices death on its own schedule, and they differ by orders
of magnitude:

| Mechanism | Detects | Typical interval | Basis |
|-----------|---------|------------------|-------|
| Carrier/link state | Physical failure | ~0 ms | Driver + PHY |
| BFD async session | Any bidirectional path failure | 3 x 300 ms default; tunable to tens of ms | RFC 5880 |
| OSPF dead timer | Silent neighbor | RouterDeadInterval (commonly 4x Hello = 40 s) | RFC 2328 |
| BGP hold timer | Silent peer | 90 s suggested default | RFC 4271 |
| BGP route aging | Stale routes | MRAI 30 s (eBGP), 5 s (iBGP) | RFC 4271 |

The pattern is painful: the fastest native mechanism inside OSPF or BGP is
seconds slow, because routing protocols were designed to be gentle on CPU.
BFD exists to break exactly that trade-off.

## BFD: Failure Detection as a Dedicated Protocol

Bidirectional Forwarding Detection (RFC 5880) is a lightweight hello
protocol that runs over the forwarding path of any link or encapsulation.
Two modes exist: asynchronous mode (both ends send periodic control
packets) and demand mode (periodic packets suppressed, echo packets do the
detection work).

The detection time is never transmitted -- it is derived locally. RFC 5880
section 6.8.4, verbatim: "In Asynchronous mode, the Detection Time
calculated in the local system is equal to the value of Detect Mult
received from the remote system, multiplied by the agreed transmit interval
of the remote system (the greater of bfd.RequiredMinRxInterval and the last
received Desired Min TX Interval)."

```text
     BFD async session, Detect Mult = 3, agreed tx = 50 ms

     R1  --------------------------------->  R2    control packets
         <---------------------------------        every 50 ms
     R1  --------------------------------->  R2
         <---------------------------------
     R1  ---X   link dies                    R2
         <---------------------------------  \
     R1  <---------------------------------   | 3 missed packets
     R1  <---------------------------------   | => DOWN after ~150 ms
                                              /
     detection = Detect Mult x max(RequiredMinRx, DesiredTx)
```

The FRR implementation documents the interaction concretely: with
`detect-multiplier 3`, local `transmit-interval 300`, and remote
`receive-interval 200`, "the remote system will detect failures only after
900 milliseconds without receiving packets." FRR defaults are 300 ms and
multiplier 3; hardware BFD offload pushes the same math into the ASIC at
tens of milliseconds with no route-processor cost.

The **echo function** buys aggressive timers safely: echo packets are looped
by the remote's forwarding plane back to the sender, so "the Echo function
has the advantage of truly testing only the forwarding path on the remote
system." Because the loop exercises silicon rather than the remote BFD
process, round-trip jitter drops, which "may reduce round-trip jitter and
thus allow more aggressive Detection Times, as well as potentially detecting
some classes of failure that might not otherwise be detected" (RFC 5880).
When echo carries detection, the control-packet rate can be kept low.

## After Detection: The Convergence Pipeline

Detection only starts the clock. For a link-state IGP the remaining steps
are LSP/LSA origination (pacing delays), flooding (grows with network
diameter), SPF recomputation (implementations throttle exponentially to
protect CPU under flapping), and finally RIB-to-FIB update -- usually the
largest single cost on big hardware, and the phase where update *ordering*
decides whether transient micro-loops form.

Micro-loops deserve the detail: between two routers' FIB updates, router A
may forward along the new path while B still forwards along the old -- a
transient cycle. RFC 6976 ("Framework for Loop-Free Convergence Using the
Ordered Forwarding Information Base (oFIB) Approach") formalizes the fix:
order FIB updates so routers farther from the failure rewrite first. Fast
reroute attacks the same window from the other side by never waiting for
reconvergence at all.

## IP Fast Reroute: LFA in One Inequality

Loop-Free Alternates (RFC 5286) pre-install a backup next hop during the
same SPF that found the primary. The whole criterion is one inequality --
for calculating router S, neighbor N, destination D, with Distance_opt(X,Y)
the shortest-path distance:

```text
    Distance_opt(N, D) < Distance_opt(N, S) + Distance_opt(S, D)

            Inequality 1: Loop-Free Criterion  (RFC 5286)
```

N is a usable backup if N's own best path to D does not come back through S;
if it did, traffic sent to N after the failure would u-turn. A stricter
subset, downstream paths, requires "Distance_opt(N, D) <
Distance_opt(S, D)" (Inequality 2) and survives more complex failures. The
catch is coverage: whether an LFA exists depends on topology and link
costs. RFC 6571 documents that real service-provider topologies leave a
meaningful fraction of (source, destination) pairs unprotected, especially
for node failures. This is not a corner case -- the calculator below leaves
11.9% of pairs without a plain LFA on a 7-node network.

## Remote LFA and TI-LFA: Repair Beyond One Hop

When no single neighbor qualifies, the repair node must be reached through a
tunnel. **Remote LFA** (RFC 7490) computes the intersection of P-space
(routers S can reach without traversing the failed link) and Q-space
(routers from which D is reachable without the failed link), then tunnels
packets to a node in that intersection -- historically via LDP targeted
sessions.

**TI-LFA** (RFC 9855, "Topology Independent Fast Reroute Using Segment
Routing") generalizes this with a segment-routing data plane. Its abstract:
the FRR "builds on proven IP FRR concepts being LFAs, Remote LFAs (RLFAs),
and Directed Loop-Free Alternates (DLFAs)" and steers traffic "over the
expected post-convergence paths from the Point of Local Repair." The
mechanics are a P-space/Q-space computation per protected resource, with the
repair encoded as a segment list (adjacency segments into the repair node,
then prefix segments along the post-convergence path). Because the repair IS
the post-convergence path, TI-LFA does not fight the reconverging network --
it converges into itself. Where the repair node is directly adjacent, a
plain next-hop swap suffices and no segment is needed. The SRv6 transport
for the same design is in [SRv6](./srv6.md) and
[Segment Routing](../../linux/kernel/networking/segment-routing.md).

## An LFA Coverage Calculator

The criterion, the coverage gap, and the TI-LFA repair search all fit in a
short pure-stdlib program: Dijkstra for distances, the RFC 5286 inequalities
per (source, destination) pair, and for uncovered pairs a P/Q-space
intersection producing either a next-hop swap or a segment list.

```python
"""LFA coverage + TI-LFA repair emulation (RFC 5286 criteria).

For every (S, D) pair: primary next hop, then any neighbor N satisfying
Inequality 1  D_opt(N, D) < D_opt(N, S) + D_opt(S, D)   -> LFA,
else the stricter Inequality 2 (downstream). Uncovered pairs get a
TI-LFA-style repair: X in P-space (reachable from S with the failed link
removed) intersected with Q-space (X reaches D with the failed link
removed); adjacent X => next-hop swap, else segment list through X.

Pure stdlib. Deterministic. Python 3.12."""

import itertools

EDGES = {  # undirected link costs; R2-R6 deliberately absent
    ("R1", "R2"): 10, ("R1", "R3"): 10, ("R2", "R3"): 4,
    ("R2", "R4"): 10, ("R3", "R5"): 4, ("R4", "R5"): 10,
    ("R4", "R6"): 10, ("R5", "R6"): 10, ("R5", "R7"): 10,
    ("R6", "R7"): 4,
}
NODES = sorted({n for e in EDGES for n in e})
ADJ = {n: {} for n in NODES}
for (a, b), c in EDGES.items():
    ADJ[a][b] = c
    ADJ[b][a] = c


def dijkstra(adj, src):
    dist = {src: 0}
    done = set()
    while len(done) < len(adj):
        u = min((n for n in adj if n not in done and n in dist),
                key=lambda n: dist[n], default=None)
        if u is None:
            break
        done.add(u)
        for v, w in adj[u].items():
            if v not in done and dist[u] + w < dist.get(v, 10**9):
                dist[v] = dist[u] + w
    return dist


DIST = {n: dijkstra(ADJ, n) for n in NODES}


def dijkstra_avoid(src, avoid_edge):
    adj = {n: {} for n in NODES}
    for (a, b), c in EDGES.items():
        if {a, b} != set(avoid_edge):
            adj[a][b] = c
            adj[b][a] = c
    return dijkstra(adj, src)


def primary_nh(s, d):
    if d not in DIST[s]:
        return None
    cands = [v for v, w in ADJ[s].items()
             if v in DIST[v] and DIST[s][v] + DIST[v].get(d, 10**9) == DIST[s][d]]
    return min(cands) if cands else None


def lfa(s, d, nh):
    """RFC 5286 Inequality 1 over S's neighbors."""
    for n in sorted(ADJ[s]):
        if n != nh and DIST[n].get(d, 10**9) < DIST[n][s] + DIST[s][d]:
            return n
    return None


def downstream(s, d, nh):
    """RFC 5286 Inequality 2 (stricter)."""
    for n in sorted(ADJ[s]):
        if n != nh and DIST[n].get(d, 10**9) < DIST[s][d]:
            return n
    return None


def ti_lfa(s, d, failed):
    """P-space (from S, failed link removed) intersect Q-space (to D)."""
    p = dijkstra_avoid(s, failed)
    q = dijkstra_avoid(d, failed)
    both = sorted({n for n in NODES if n in p and n != s}
                  & {n for n in NODES if n in q and n != d})
    if not both:
        return None
    x = min(both, key=lambda n: p[n] + q[n])  # cheapest repair node
    if x in ADJ[s]:
        return [f"next-hop swap to {x}"], p[x] + q[x]
    segs = [f"adj-seg to {x}"]
    if x != d:
        segs.append(f"SRGB prefix-seg {d}")
    return segs, p[x] + q[x]


covered, swaps, seglists, unprotected, rows = 0, 0, 0, 0, []
for s, d in itertools.permutations(NODES, 2):
    nh = primary_nh(s, d)
    if nh is None:
        continue
    failed = tuple(sorted((s, nh)))
    tag = ""
    alt = lfa(s, d, nh)
    if alt:
        covered += 1
        tag = f"LFA via {alt}"
    else:
        alt = downstream(s, d, nh)
        if alt:
            covered += 1
            tag = f"downstream via {alt}"
        else:
            rep = ti_lfa(s, d, failed)
            if rep:
                segs, cost = rep
                tag = f"TI-LFA: {', '.join(segs)}  (cost {cost})"
                if segs[0].startswith("next-hop"):
                    swaps += 1
                else:
                    seglists += 1
                rows.append(f"  {s} -> {d:<3} primary nh {nh:<3} {tag}")
            else:
                unprotected += 1
                rows.append(f"  {s} -> {d:<3} primary nh {nh:<3} UNPROTECTED")

total = covered + swaps + seglists + unprotected
print(f"topology: {len(NODES)} nodes, {len(EDGES)} links, "
      f"{total} (src, dst) pairs with a primary path")
print(f"plain LFA / downstream coverage : {covered}/{total} "
      f"= {100.0 * covered / total:.1f}%")
print(f"TI-LFA next-hop swap repairs    : {swaps}")
print(f"TI-LFA segment-list repairs     : {seglists}")
print(f"pairs with no repair found      : {unprotected}")
print("\npairs that plain LFA cannot protect:")
for r in rows:
    print(r)
```

Real output:

```text
topology: 7 nodes, 10 links, 42 (src, dst) pairs with a primary path
plain LFA / downstream coverage : 37/42 = 88.1%
TI-LFA next-hop swap repairs    : 4
TI-LFA segment-list repairs     : 1
pairs with no repair found      : 0

pairs that plain LFA cannot protect:
  R2 -> R4  primary nh R4  TI-LFA: next-hop swap to R3  (cost 18)
  R3 -> R5  primary nh R5  TI-LFA: next-hop swap to R2  (cost 24)
  R3 -> R6  primary nh R5  TI-LFA: next-hop swap to R2  (cost 24)
  R3 -> R7  primary nh R5  TI-LFA: next-hop swap to R2  (cost 28)
  R5 -> R3  primary nh R3  TI-LFA: adj-seg to R2, SRGB prefix-seg R3  (cost 24)
```

Read the last row against the mechanism: R5's primary path to R3 leaves via
R3 itself, so every other R5 neighbor violates Inequality 1 -- each one's
best route to R3 comes back through R5. No one-hop backup exists, but node
R2 sits in P-space and Q-space, so one adjacency segment steers the packet
there and normal prefix forwarding finishes the job. That is TI-LFA's value
proposition in one line.

## The BGP Side of Failover

IGP fast reroute fixes the IGP leg, but end-to-end availability also crosses
BGP, which reconverges differently: re-advertisement is rate-limited by the
Minimum Route Advertisement Interval -- RFC 4271 sets "the suggested default
value for the MinRouteAdvertisementIntervalTimer on EBGP connections is 30
seconds" (5 seconds for iBGP) -- and peer death was classically noticed via
the 90-second hold timer ("The suggested default value for the HoldTime is
90 seconds", same RFC). Two fixes are standard practice: BFD sessions bound
to BGP peers tear the session down in multiples of the BFD interval instead
of the hold time, and BGP PIC (Prefix Independent Convergence) pre-installs
the backup in the FIB so per-prefix best-path recomputation happens lazily
instead of rewriting hundreds of thousands of prefixes. The ECMP hashing
that picks a flow's path member -- and what a member death does to that flow
-- is treated in [Datacenter Fabrics](./datacenter-fabrics.md).

## Failure Modes and Trade-offs

- **Aggressive timers cost CPU at scale.** Each session emits on its own
  interval; thousands of sessions multiply into a route-processor load.
  Hardware offload or distributed BFD (both documented in the FRR
  implementation) is how large deployments run fast timers.
- **False positives under congestion.** A missed control packet is
  indistinguishable from a dead link; multiplier 3 exists to absorb jitter.
  Shrinking it to chase milliseconds converts queueing events into outages.
- **LFA coverage is not guaranteed.** Coverage is a property of link costs
  and router degree; 88.1% on a tiny graph is typical of sparse topologies,
  and RFC 6571 records the same on service-provider networks.
- **Protection is scoped to the modeled failure.** A link-protecting LFA can
  micro-loop if the node fails (RFC 5286 discusses exactly this); node and
  SRLG protection need stricter criteria and diversity data.
- **The repair is only as good as its model.** A backup that ignores what
  the rest of the network believes is a loop generator; oFIB ordering and
  post-convergence-path repairs (TI-LFA) are the systematic answers, and
  verifying candidate configs against these properties before deployment is
  the job of [Network Verification](./network-verification.md).

## References

1. [RFC 5880 - Bidirectional Forwarding Detection](https://www.rfc-editor.org/rfc/rfc5880.txt)
2. [RFC 5881 - BFD for IPv4/IPv6 (Single Hop)](https://www.rfc-editor.org/rfc/rfc5881.txt)
3. [RFC 5286 - Basic Specification for IP Fast Reroute: Loop-Free Alternates](https://www.rfc-editor.org/rfc/rfc5286.txt)
4. [RFC 6571 - LFA Applicability in Service Provider Networks](https://www.rfc-editor.org/rfc/rfc6571.txt)
5. [RFC 7490 - Remote Loop-Free Alternate (LFA) Fast Reroute](https://www.rfc-editor.org/rfc/rfc7490.txt)
6. [RFC 9855 - Topology Independent Fast Reroute Using Segment Routing (TI-LFA)](https://www.rfc-editor.org/rfc/rfc9855.txt)
7. [RFC 6976 - Framework for Loop-Free Convergence Using oFIB](https://www.rfc-editor.org/rfc/rfc6976.txt)
8. [RFC 4271 - A Border Gateway Protocol 4 (BGP-4)](https://www.rfc-editor.org/rfc/rfc4271.txt)
9. [FRRouting Documentation - BFD](https://docs.frrouting.org/en/latest/bfd.html)
