# OSPF Deep Dive — Link State, Areas, and the SPF Engine

## Overview

OSPF (Open Shortest Path First, RFC 2328 for IPv4 and RFC 5340 for IPv6) is
the dominant Interior Gateway Protocol in enterprise networks. It is a
**link-state** protocol: every router floods a description of its local
connections to all routers in its area, building an identical **Link State
Database** (LSDB), then runs Dijkstra's shortest-path-first (SPF) algorithm
against that database to compute its own routing table.

This chapter unpacks what interviews probe: the link-state model, the SPF
algorithm with a worked example, the area hierarchy and LSA types, the
DR/BDR election, OSPF vs IS-IS, and authentication. The companion page
[`ospf.md`](ospf.md) is a quicker survey; this one goes deeper.

## Link-State Fundamentals

Distance-vector protocols (RIP) propagate *the answer* (a route +
distance) and trust neighbors' answers — that is why RIP suffers from
count-to-infinity. Link-state protocols propagate *the inputs* (router X is
connected to networks Y, Z with costs a, b) and let each router recompute
the answer independently. This gives:

- **Loop-free** by construction (the SPF tree is a tree)
- **Fast convergence** (a single flooded LSA re-runs SPF in seconds)
- **Full topology knowledge** (each router sees the entire area's graph)

The cost is memory and CPU: each router stores the full LSDB and runs SPF
on every topology change. For very large networks OSPF uses **areas** to
bound LSDB size.

## Dijkstra's SPF Algorithm

The SPF algorithm (Edsger Dijkstra, 1959) computes shortest paths from a
source node to all other nodes in a weighted graph. OSPF's variant:

```python
import heapq

def dijkstra(adj, source):
    """adj[u] = list of (v, cost) directed edges."""
    dist = {source: 0}
    parent = {source: None}
    pq = [(0, source)]
    visited = set()

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        for v, cost in adj[u]:
            nd = d + cost
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(pq, (nd, v))

    return dist, parent
```

Two subtleties in OSPF's actual SPF:

1. **Incremental SPF (iSPF, RFC 8362)**: only recompute the affected
   subtree after a topology change, not the whole tree.
2. **Partial SPF**: changes to Type-1/Type-2 LSAs trigger full SPF;
   changes to Type-3 (Summary) LSAs only trigger a partial recalculation
   for those destinations.

### Worked Example

```
      2        3
   A -------- B -------- C
   |                    |
   |5                   |1
   |                    |
   D ---------- E ------+
       1          2
```

Adjacency: A->B(2), A->D(5), B->C(3), C->E(1), D->E(1), E->C(2).

Dijkstra from A:

1. Start: dist[A]=0, frontier={(0,A)}
2. Pop A (0). Relax: B=2, D=5. Frontier: {(2,B),(5,D)}
3. Pop B (2). Relax: C=2+3=5. Frontier: {(5,C),(5,D)}
4. Pop C (5). Relax: E=5+1=6. Frontier: {(5,D),(6,E)}
5. Pop D (5). Relax: E=5+1=6 (no improvement; E already 6). Frontier:
   {(6,E)}
6. Pop E (6). Done.

Resulting tree from A:

- A->B cost 2
- A->D cost 5
- A->B->C cost 5
- A->D->E cost 6 (note: A->B->C->E is also 6 — tie broken by Router ID)

OSPF stores both the next-hop and the full path in the RIB, which is why
ECMP (Equal-Cost Multi-Path) can split traffic across A->D->E and
A->B->C->E.

## Area Hierarchy

OSPF scales by partitioning the domain into **areas**. Every router in an
area has an identical LSDB for that area; routers on area borders (ABRs)
maintain separate LSDBs per attached area and summarize between them.

```
                       +----------------------------------+
                       |            Area 0 (Backbone)     |
                       |  ABR1 ----------------- ABR2      |
                       +------|---------------------|------+
                              |                     |
                       +------|-------+    +--------|-------+
                       |   Area 1    |    |   Area 2      |
                       |   R1   R2   |    |   R3   R4    |
                       +-------------+    +---------------+
```

Rules:

- All areas must connect to Area 0 (backbone).
- Area 0 itself is contiguous; if an area is physically separated, a
  **virtual link** (RFC 2328 §4.0.8) tunnels it through a transit area.
- Type-1 and Type-2 LSAs are area-scoped — never leave their area.
- Inter-area traffic must transit Area 0.

### Area Types

| Type | Receives Type-5 (external)? | Receives Type-3 (summary)? | Use |
|------|------------------------------|----------------------------|-----|
| Normal | Yes | Yes | Default |
| Stub | No | Yes | Leaf area, no externals |
| Totally stub (Cisco ext) | No | No (just default route) | Highly constrained leaf |
| NSSA | No (replaced by Type-7) | Yes | Leaf with local ASBR |
| Totally NSSA | No | No | NSSA + totally stub |

NSSA (Not-So-Stubby Area, RFC 3101) was invented for branch offices that
needed to inject a few external routes (e.g. a default route to the
internet) without carrying the full external LSDB of the core.

## LSA Types

Each LSA is a typed record flooded through the area/AS. The 7 OSPFv2 LSA
types:

| Type | Name | Originator | Scope | Purpose |
|------|------|------------|-------|---------|
| 1 | Router-LSA | Every router | Area | "I have these links with these costs" |
| 2 | Network-LSA | DR | Area | "This transit network has these attached routers" |
| 3 | Summary-LSA | ABR | Area -> Area | "Reach these prefixes in Area X" |
| 4 | ASBR-Summary | ABR | Area | "Reach ASBR Y via Area X" |
| 5 | AS-External-LSA | ASBR | AS-wide | "Reach this external prefix via me" |
| 7 | NSSA-External | ASBR in NSSA | NSSA | External route inside NSSA; converted to Type-5 by ABR |

### Type-1 LSA (Router-LSA) Layout

```
   LS Age: 1200      Options: (E) External Routing
   Type: 1 (Router)  Link State ID: 1.1.1.1 (Router ID)
   Advertising Router: 1.1.1.1
   Sequence: 0x80000012
   Length: 64 bytes
   Flags: B (border) E (external) V (virtual link) ...
   Number of Links: 3
     Link 1: Type=Point-to-Point, Link ID=2.2.2.2, Link Data=10.0.0.1, Metric=10
     Link 2: Type=Transit,        Link ID=10.0.0.4, Link Data=10.0.0.1, Metric=10
     Link 3: Type=Stub,           Link ID=192.168.1.0, Link Data=255.255.255.0, Metric=1
```

The "Transit" type means "this link has a DR — see the matching Type-2 LSA
for the full list of attached routers."

### OSPFv3 LSA Types (RFC 5340)

OSPFv3 reorganizes the LSA types to separate topology information
(Link-LSA, Intra-Area-Prefix-LSA) from addressing — this is what lets
OSPFv3 carry IPv6 *and* IPv4 (RFC 6850) using Address-Family extensions.
Two LSAs unique to OSPFv3:

- **Link-LSA (Type 8)**: scoped to a single link; carries link-local
  addresses and per-link prefixes.
- **Intra-Area-Prefix-LSA (Type 9)**: ties prefixes to routers/transit
  networks so a router-LSA only carries topology now.

## DR and BDR Election

On a multi-access segment (Ethernet, Frame Relay), N neighbors would form
N(N-1)/2 adjacencies if every router paired with every other. OSPF avoids
this by electing a **Designated Router** (DR) and **Backup DR** (BDR); all
other routers form full adjacencies only with DR/BDR, and exchange LSDB
sync via 224.0.0.6 (AllDRouters). DR floods LSAs to 224.0.0.5
(AllSPFRouters).

Election algorithm (RFC 2328 §9.4):

1. Collect Hello packets from neighbors on the segment.
2. Filter out routers with priority 0 (ineligible to be DR).
3. Among the eligible, choose the one with the highest priority (default
   1, range 0-255). Ties broken by highest Router ID.
4. A router already configured as DR (the "DR bit" in its Hello) wins even
   if a higher-priority router comes up later — DR/BDR election is
   **non-preemptive**.

```
                +------------------+
                | DR (priority 100)|
                +----+--------+-----+
            +--------+        +----------+
       +----|----+        +---|----+
       | R1 (P=1)|        | R2 (P=1)|
       +--------+        +--------+
                +---------+----+
                | BDR (P=99)   |
                +--------------+
```

This is also why OSPF network-type "broadcast" is the default on Ethernet
— the protocol assumes DR/BDR. On point-to-point links (no broadcast) the
DR/BDR step is skipped and full adjacency is formed directly.

## OSPF vs IS-IS

OSPF and IS-IS solve the same problem (link-state IGP) but differ in
details that matter at scale:

| Dimension | OSPF | IS-IS |
|-----------|------|-------|
| Spec | RFC 2328 (IETF) | ISO 10589 (OSI), RFC 1195 (IP) |
| Transport | IP protocol 89 | Layer 2 directly (no IP) |
| Areas | On interfaces (numbered) | On the router (Level 1/2) |
| Addressing | IPv4 Router-ID | NET (Network Entity Title) |
| LSA extensibility | LSA type-tagged (hard to add types) | TLV-encoded (easy to add TLVs) |
| IPv6 | Separate process (OSPFv3) | Single process, new TLVs |
| Multi-topology | Not in baseline | Native (RFC 5120) |
| Where used | Enterprise, campus | ISP backbones, large cloud |

IS-IS's TLV design is why it is preferred at scale: adding IPv6,
multi-topology, or traffic-engineering extensions was a matter of defining
new TLVs, not new LSA types. OSPFv3 made bigger changes (new LSA types,
new options field) for IPv6.

## Authentication

OSPFv2 supports two modes:

- **Null** — no authentication (default)
- **Simple password** — cleartext 8-byte password, useless against
  sniffing
- **MD5** — keyed HMAC-MD5 per RFC 5709

Modern OSPFv3 (per RFC 6506) added:

- **HMAC-SHA-1-96** and **HMAC-SHA-256-128** (RFC 5709 / RFC 7474)

OSPFv3 had no authentication in its original RFC 5340 because IPv6 was
assumed to use IPsec (AH/ESP) for all authentication. In practice
operators prefer HMAC-SHA per-protocol because IPsec key management is
heavier.

```
router ospf 1
  area 0 authentication message-digest
  !
  interface GigabitEthernet0/0
    ip ospf message-digest-key 1 md5 <secret>
    ip ospf hello-interval 10
    ip ospf dead-interval 40
    ip ospf priority 100
```

## Interview Pitfalls

- **Forgetting SPF is loop-free by construction** — interviewers love to
  ask why OSPF cannot loop. The SPF tree has no cycles, so routes follow
  a tree.
- **Confusing AD 110 (OSPF) with AD 20 (eBGP)** — when both advertise a
  prefix, eBGP wins, which is why a BGP-learned default beats an
  OSPF-injected one.
- **Saying DR/BDR is preemptive** — it is not. New higher-priority
  routers do not take over until the current DR fails.
- **Treating Type-7 and Type-5 LSAs as the same** — Type-7 lives inside
  the NSSA only and must be translated to Type-5 at the ABR before
  leaving.
- **Treating cost as a hop count** — cost is `reference_bandwidth /
  interface_bandwidth`; with the default 100 Mbps reference, both 1 GbE
  and 10 GbE come out as cost 1, which is why you should raise the
  reference bandwidth (`auto-cost reference-bandwidth 100000`) on modern
  networks.

## References

- RFC 2328 — OSPF Version 2: <https://www.rfc-editor.org/rfc/rfc2328>
- RFC 5340 — OSPF for IPv6 (OSPFv3): <https://www.rfc-editor.org/rfc/rfc5340>
- RFC 3101 — The OSPF NSSA Option: <https://www.rfc-editor.org/rfc/rfc3101>
- RFC 6850 — OSPFv3 AF Extension: <https://www.rfc-editor.org/rfc/rfc6850>
- RFC 5709 — OSPFv2 HMAC-SHA Cryptographic Authentication: <https://www.rfc-editor.org/rfc/rfc5709>
- RFC 7474 — Security Extension for OSPFv2 (SHA): <https://www.rfc-editor.org/rfc/rfc7474>
- John T. Moy, *OSPF: Anatomy of an Internet Routing Protocol*,
  Addison-Wesley, 1998.
