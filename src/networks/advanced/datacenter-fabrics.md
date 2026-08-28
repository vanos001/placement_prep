# Datacenter Fabrics: Bisection Arithmetic, ECMP Failure Modes, and ML-Cluster Rails

The structural side of this topic -- Clos stages, expander graphs, optical circuit
switching -- lives in [Datacenter Network Topology](./datacenter-topology.md).
This page is the engineering layer on top of any Clos drawing: what the port
budget actually buys, why the routing protocol and the hash function decide
whether the hardware's bisection bandwidth reaches the workloads, and how the
design changes when the dominant workload is collective communication.

## The full-duplex bisection, derived from port budgets

A k-ary fat-tree is built entirely from k-port switches, and the port budget
fixes every other number: **pods** = k/2 (each holding k/2 edge + k/2 aggregation
switches); each edge switch splits k/2 server ports with k/2 uplinks; each
aggregation switch splits k/2 downlinks with k/2 core uplinks; the core tier has
(k/2)^2 switches.

Two derivations matter for interviews and capacity planning. First, the server
count: k/2 pods x (k/2 edge switches) x (k/2 server ports) = (k/2)^3 servers, and
the switch count is 3k^2/4 (k^2/4 per tier). A k=48 fat-tree therefore hosts
13,824 servers on 1,728 switches -- not 27,648 switches, a number that sometimes
circulates from confusing the k^3/4 host-capacity arithmetic with switch count.

Second, the bisection. Cut the pod set into two halves. Servers on the same side
of the cut never need the core tier, so the only links crossing the cut are the
aggregation-to-core links leaving one half:

```text
        left half (k/4 pods)              right half (k/4 pods)
        edge -> agg (internal)            edge -> agg (internal)
             \                             /
              agg == X == core == X == agg        <- the cut crosses here
             /                             \
        k^3/16 links leave the left half   k^3/16 links arrive on the right
```

Each pod contributes (k/2 aggregation switches) x (k/2 core uplinks) = k^2/4
links, and one half holds k/4 pods, so the cut carries **k^3/16 links**. With
full-duplex links this is the standard convention: a bisection of k^3/16 x C
means the N/2 = k^3/16 servers on one side can all transmit at line rate C to
the other side simultaneously. That is the precise meaning of "1:1
non-blocking": the worst-case all-to-all-across-the-cut demand equals the cut
capacity exactly, with zero margin. Real fabrics keep headroom or oversubscribe
deliberately -- which is a budget decision, not an accident (Section 2).

| k (port count) | Switches | Servers | Bisection links | Full-duplex bisection @ 100 G |
|---|---|---|---|---|
| 4 | 12 | 8 | 4 | 400 Gbps |
| 8 | 48 | 64 | 32 | 3.2 Tbps |
| 48 | 1,728 | 13,824 | 6,912 | 691.2 Tbps |
| 128 | 12,288 | 262,144 | 131,072 | 13,107.2 Tbps |

The k=128 row is the honest reason fabrics replaced chassis: a single 128-port
tier is unbuyable, but 12,288 commodity switches is a warehouse problem, and
cable failures become the dominant failure class.

## Oversubscription as an explicit design parameter

Oversubscription ratio = (downstream bandwidth offered at a tier) / (upstream
bandwidth leaving that tier). A leaf with 48 x 100 G server ports and 8 x 100 G
spine uplinks is 4,800/800 = 6:1; swapping the uplinks to 8 x 400 G makes it
1.25:1. Two properties trip people up:

- **Ratios multiply only along a path.** A 3-tier fabric with 4:1 at the
  aggregation layer and 2:1 at the core layer is 8:1 for traffic that must
  traverse both tiers -- but a 2:1 tier is 1:1 for east-west traffic that
  terminates below it. Always state the traffic matrix you are budgeting for.
- **East-west growth made high ratios untenable.** Once storage replicas,
  VM migration, and map-reduce shuffles became the majority flows, 8:1 fabrics
  turned a single shuffle into a congestion event (the incast mechanics are in
  [Data-Center TCP](./datacenter-tcp.md)).

The economics are asymmetric. Oversubscription buys cheaper upstream tiers; the
cost is tail latency under adversarial traffic. AI/ML training and tier-0 storage
fleets buy 1:1 or even 2:1 *under*-subscribed rails, while general-purpose
compute settles at 3:1-8:1. Neither choice is "correct"; the ratio is a
product decision about which workloads pay for the fabric.

## ECMP inside the fabric, and how it fails

The fabric has (k/2)^2 equal-cost paths between two servers in different pods.
Equal-cost multi-path (ECMP) picks one per **flow** by hashing a flow key --
the 5-tuple (src IP, dst IP, src port, dst port, protocol) in IPv4, the flow
label or the 3-tuple in IPv6. RFC 2992 analyzes the hash-threshold variant and
shows its flow-to-link assignment is stable as link sets change, which is why it
beat plain modulo-N hashing. The load balancer page covers the same hashing from the balancer's side:
[L4 Load Balancing Internals](./l4-load-balancing-internals.md).

Hashing flows, not bytes, is the root of every ECMP failure mode:

| Failure mode | Mechanism | Symptom | Mitigation |
|---|---|---|---|
| Hash polarization | Cascaded ECMP stages reuse the same hash on the same key, so correlated choices collapse path diversity | 3-stage fabric uses ~N end-to-end paths out of N x M; some core links idle while others queue | Re-key (salt) the hash per stage; vendor features exist precisely for this |
| Hash collision | Two elephant flows land on the same link; TCP/flow-level fair sharing does not apply to them | One link at 100%, its pair idle, no queue visible on other ports | Flowlet/dynamic load balancing, adaptive routing, bigger ECMP pools |
| Flow/byte imbalance | Flow counts balance; bytes do not (elephants) | Per-link utilization spread is wide at low flow counts | Measure bytes, not packets, when validating; use variable-length flowsets |
| Fragment/ICMP breakage | Non-first fragments and ICMP errors lack L4 fields the hash needs | A flow's fragments take a different path; reordering or misdelivered ICMP | Hash on IP-only for fragments; 5-tuple otherwise (RFC 2991) |
| ECMP rehash on failure | A member change rehashes flows that were not using the failed link | Disruption wider than the failure | Resilient hashing / consistent ECMP tables |

Polarization deserves the example because it is invisible per-stage: each layer
looks perfectly balanced while the end-to-end fabric uses a fraction of its
paths. The runnable model in Section 6 reproduces it: two cascaded 8-way ECMP
stages with a shared hash drive only 8 of 64 core links, and salting the hash
per stage restores all 64.

## Routing the underlay: why BGP replaced STP

A leaf-spine fabric is a layered L2/L3 topology only if you make it one.
Running it as a single L2 domain under Spanning Tree Protocol (STP) defeats the
design: STP blocks redundant links to break loops, so half the bisection you
paid for is administratively switched off, and reconvergence is timer-driven --
tens of seconds for classic 802.1D, seconds even for RSTP. The STP mechanics and
why EVPN displaced it as the L2 overlay are covered in
[VLAN & STP](./vlan-stp.md) and the EVPN control plane in
[Networking Advanced](../networking-advanced.md). Here the point is the
underlay: RFC 7938 documents the design Facebook (Meta) and most large operators
converged on -- **eBGP as the fabric protocol**:

- Every switch is its own autonomous system (private ASNs) or every pod shares
  one AS, with eBGP peering on every fabric link. No route reflectors, no IGP
  flooding domains, no spanning-tree state anywhere.
- BGP multipath gives ECMP its candidate set; BFD (or fast timers) detects
  neighbor death in milliseconds, so sub-second reconvergence is routine.
- Failure domains shrink to a link or a device: a spine failure withdraws its
  prefixes and every leaf still has a path through the remaining spines.

Jupiter Evolving (SIGCOMM 2022) is the production-scale datapoint: Google kept
BGP-style routing for years, then moved control toward a software-defined
centralized controller over optical circuit switches -- preserving the property
that matters here: any single failure shrinks capacity incrementally instead of
partitioning the fabric.

## Rail-optimized fabrics for ML clusters

Collective communication changed the traffic matrix. A ring all-reduce over G
GPUs sends every byte through G-1 hops of *rank-ordered* pairs: GPU i talks
mostly to GPU i+1 and GPU i-1, rarely to an arbitrary peer. A generic fat-tree
spreads those pairs over the whole fabric and pays ECMP hashing for the
privilege. A **rail-optimized** topology gives every rank its own switching
plane:

```text
   Rail-0 plane        Rail-1 plane        Rail-2 plane        Rail-3 plane
   (ToR0+spines)       (ToR1+spines)       (ToR2+spines)       (ToR3+spines)
        |                   |                   |                   |
   GPU0 of server A    GPU1 of server A    GPU2 of server A    GPU3 of server A
   GPU0 of server B    GPU1 of server B    GPU2 of server B    GPU3 of server B
   GPU0 of server C    GPU1 of server C    GPU2 of server C    GPU3 of server C

   same-rank traffic (GPU i of A <-> GPU i of B) crosses exactly one plane;
   cross-rank traffic would need to traverse planes laterally (the fabric's
   weak spot -- rail-aware collectives avoid it)
```

Server j's GPU i connects to rail i's leaf. NVIDIA's NCCL documentation states
the payoff directly: rail-optimized topology "maximizes all-reduce performance
while minimizing network interference between flows" ([NVIDIA Developer
blog](https://developer.nvidia.com/blog/doubling-all2all-performance-with-nvidia-collective-communication-library-2-12/))
-- a ring whose consecutive members share a rail never leaves its plane. Meta's
SIGCOMM 2024 production paper pairs rails with adaptive routing for RDMA
training traffic. The trade-offs:

- **Cabling and optics cost** scale with rails x planes; a 8-GPU server implies
  8 planes.
- **Cross-rank ("off-rail") traffic** still exists (all-gather, MoE
  all-to-all), and the rail fabric is deliberately bad at it -- hence adaptive
  routing and topology-aware collectives as compensations.
- **Failure handling** is plane-local: losing rail 2's spine degrades GPU-2
  bandwidth fleet-wide but never partitions; NCCL re-forms rings from topology
  discovery.

Rail design is the visible symptom of a deeper shift: when one application owns
the fabric, the fabric co-designs with the collective algorithm instead of
optimizing for arbitrary any-to-any flows.

## Failure blast radius: classic 3-tier vs Clos fabrics

| Failure event | 3-tier under STP | Leaf-spine under eBGP | Rail-optimized ML pod |
|---|---|---|---|
| ToR / leaf switch dies | its access block (1-2 racks) offline | rack offline | rack offline; NVLink inside racks unaffected |
| Spine / core switch dies | tree recompute; if it was on the active path, inter-block traffic stalls until convergence | capacity drops by 1/S; no partition (all leaves still reachable) | that rail's plane degraded; collectives re-route around it |
| Link flap | TCN flood re-floods CAM tables fabric-wide | single prefix withdraw + re-add; ECMP rehash may reset unrelated flows | plane-local ring shift |
| Uplink oversubscription failure mode | blocked standby links mean the "redundant" path was never load-tested | multipath absorbs it; watch for rehash storms on member loss | ring re-orders; bandwidth drops stepwise |
| Worst realistic blast radius | one forwarding domain = whole building | one device or link | one rail plane |

The structural win in columns 3 and 4 is not raw redundancy -- 3-tier fabrics
had redundancy too -- it is that Clos fabrics keep **all** links forwarding, so
every failure is a capacity arithmetic problem (N-1 of N paths) rather than a
topology re-election. Re-election is what makes STP outages unpredictable;
arithmetic is what makes Clos outages plannable.

## Worked model: bisection arithmetic and ECMP polarization

The model derives fat-tree capacity from the port budget, then hashes 20,000
synthetic 5-tuples through two cascaded ECMP stages -- leaf-to-spine and
spine-to-core -- once with a shared hash and once with per-stage salts.

```python
"""Fabric arithmetic + ECMP polarization in a two-stage routing chain.
Part A derives k-ary fat-tree capacity from the Al-Fares port budget;
Part B hashes 20,000 5-tuples through two cascaded ECMP stages
(leaf->spine, spine->core): 'same-seed' reuses one hash at both stages,
'salted' re-keys per stage. Sizes are seeded lognormal (elephants)."""
import hashlib
import random

def h(seed, key):
    return int.from_bytes(hashlib.md5(f"{seed}|{key}".encode()).digest()[:8], "big")

def fat_tree(k):                 # k-port switches, pod-split bisection
    pods = k // 2
    edge = agg = pods * (k // 2)
    core = (k // 2) ** 2
    hosts = pods * (k // 2) * (k // 2)                    # (k/2)^3
    return edge, agg, core, hosts, (pods // 2) * (k // 2) ** 2   # k^3/16

print("k-ary fat-tree, Al-Fares wiring (all switches k ports, 100G hosts):")
for k in (4, 8, 48, 128):
    edge, agg, core, hosts, bl = fat_tree(k)
    bw = bl * 100                                        # links * 100 Gbps
    txt = (f"{bw:.0f} Gbps" if bw < 1000 else
           (f"{bw/1000:.1f} Tbps" if bw < 10000 else f"{bw/1000:,.0f} Tbps"))
    print(f"  k={k:>3}: edge={edge:>5} agg={agg:>5} core={core:>6} "
          f"hosts={hosts:>7}  bisection={bl:>6} links = {txt} full-duplex")

print("\nleaf-spine oversubscription (host bandwidth / uplink bandwidth):")
for hp, hg, up, ug in ((48, 100, 6, 100), (48, 100, 8, 400), (32, 100, 8, 100)):
    down, ul = hp * hg, up * ug
    print(f"  {hp}x{hg}G down, {up}x{ug}G up: {down}G/{ul}G = {down/ul:g}:1")

rng = random.Random(20260801)                            # seeded, deterministic
FLOWS, SPINES, CORES = 20000, 8, 8
flows = [(f"10.{i//256%16}.{i%256}.{(i*7)%254}:5201->10.{(i*3)//256%16}.{(i*3)%256}.9:443 TCP",
          min(1.0e9, max(1.0e4, rng.lognormvariate(0.0, 2.0)))) for i in range(FLOWS)]
keys = [k_ for k_, _ in flows]
spine_same = [h("fabric", k_) % SPINES for k_ in keys]
spine_salt = [h("stage1", k_) % SPINES for k_ in keys]
core_same  = [h("fabric", k_) % CORES for k_ in keys]     # reused hash
core_salt  = [h("stage2", k_) % CORES for k_ in keys]     # per-stage salt

def report(name, spines, cores):
    pairs = list(zip(spines, cores))
    lb = [0.0] * (SPINES * CORES)
    for (s, c), (_, sz) in zip(pairs, flows):
        lb[s * CORES + c] += sz
    total = sum(lb)
    print(f"{name:26s} core links used: {len(set(pairs)):>2}/64   "
          f"byte share max/mean: {max(lb)/(total/len(lb)):4.2f}   "
          f"heaviest link: {100*max(lb)/total:4.1f}% of all bytes")

print(f"\ncascaded ECMP, {FLOWS} flows, {SPINES}x{CORES} spine-core links:")
report("same hash at both stages", spine_same, core_same)
report("salted hash per stage", spine_salt, core_salt)
```

Real output (Python 3.12):

```text
k-ary fat-tree, Al-Fares wiring (all switches k ports, 100G hosts):
  k=  4: edge=    4 agg=    4 core=     4 hosts=      8  bisection=     4 links = 400 Gbps full-duplex
  k=  8: edge=   16 agg=   16 core=    16 hosts=     64  bisection=    32 links = 3.2 Tbps full-duplex
  k= 48: edge=  576 agg=  576 core=   576 hosts=  13824  bisection=  6912 links = 691 Tbps full-duplex
  k=128: edge= 4096 agg= 4096 core=  4096 hosts= 262144  bisection=131072 links = 13,107 Tbps full-duplex

leaf-spine oversubscription (host bandwidth / uplink bandwidth):
  48x100G down, 6x100G up: 4800G/600G = 8:1
  48x100G down, 8x400G up: 4800G/3200G = 1.5:1
  32x100G down, 8x100G up: 3200G/800G = 4:1

cascaded ECMP, 20000 flows, 8x8 spine-core links:
same hash at both stages   core links used:  8/64   byte share max/mean: 8.19   heaviest link: 12.8% of all bytes
salted hash per stage      core links used: 64/64   byte share max/mean: 1.14   heaviest link:  1.8% of all bytes
```

Read the last two lines as one sentence: a fabric whose per-stage tables each
looked balanced was carrying its inter-stage traffic on 8 of 64 links, with one
link holding 12.8% of all bytes -- the salted variant puts that at 1.8%. And the
k=48 row's 691.2 Tbps bisection is the *ceiling*: the observed number is whatever
polarization, collisions, and the traffic matrix leave behind.

## Failure modes worth knowing

- Budgeting the bisection with the wrong convention: "bisection bandwidth" is
  full-duplex here; some papers count half-duplex (links x C / 2). Always ask
  which convention a vendor datasheet uses before comparing numbers.
- Treating 1:1 as a guarantee: it is an equality with no margin. Incast, a
  single hot rack, or a collectives burst saturates a "non-blocking" fabric
  exactly as fast as an oversubscribed one at the bottleneck tier.
- Assuming ECMP balances by bytes. It balances flow *counts* through a hash;
  validation must be on utilization counters, not on packet/flow tables.
- Salt asymmetry: re-keying per stage is not free -- inconsistent salting
  across a fleet re-creates polarization after a code push. Test with the
  production hash configuration, not lab defaults.

> **Interview angle**: "Why is a Clos fabric more fault-tolerant than a 3-tier
> network if both have redundant links?" -- A Clos fabric keeps every link
> forwarding (no blocked spanning-tree ports), so a failure is handled by
> arithmetic: the remaining (S-1)/S paths still exist, ECMP rehashes, BGP
> withdraws one prefix set. A 3-tier STP network must *re-elect* a tree before
> its redundancy returns. Capacity loss vs re-election is the whole answer.

## References

- [Al-Fares, Loukissas, Vahdat -- A Scalable, Commodity Data Center Network Architecture, SIGCOMM 2008](https://doi.org/10.1145/1402958.1402967)
- [RFC 7938 -- Use of BGP for Routing in Large-Scale Data Centers](https://www.rfc-editor.org/rfc/rfc7938.txt)
- [RFC 2991 -- Multipath Issues in Unicast and Multicast Next-Hop Selection](https://www.rfc-editor.org/rfc/rfc2991.txt)
- [RFC 2992 -- Analysis of an Equal-Cost Multi-Path Algorithm](https://www.rfc-editor.org/rfc/rfc2992.txt)
- [Poutievski et al. -- Jupiter Evolving: Transforming Google's Datacenter Network via Optical Circuit Switches and Software-Defined Networking, SIGCOMM 2022](https://doi.org/10.1145/3544216.3544265)
