# BGP Deep Dive — Path Vectors, AS Relationships, and Internet Routing

## Overview

BGP-4 (Border Gateway Protocol, version 4) is the protocol that holds the
Internet together. Defined in RFC 4271, it exchanges reachability information
between **Autonomous Systems** (ASes) — administrative domains under a single
routing policy. Unlike OSPF/IS-IS, BGP is a **path-vector** protocol: it does
not compute shortest paths by metric, it picks among alternate AS-level paths
using a multi-attribute, policy-driven decision process.

This chapter covers the protocol at the level needed for senior
network-engineering interviews: the AS_PATH attribute, eBGP vs iBGP
semantics, the Loc-RIB pipeline, the 13-step decision process, route
reflectors and the iBGP full-mesh problem, RPKI/BGPsec security, and a
head-to-head with OSPF. The companion page [`bgp.md`](bgp.md) is a
quicker survey; this one goes deeper.

## Autonomous Systems and Path-Vector Routing

An AS is a 32-bit number (2-byte form pre-2007, 4-byte form RFC 6793)
identifying a single routing domain. The Internet has roughly 75,000
advertised ASes (2024). BGP routers exchange **Network Layer Reachability
Information** (NLRI) — IPv4/IPv6 prefixes — tagged with a path of ASes.

The path-vector idea is simple: each BGP UPDATE carries the AS_PATH, the
ordered list of ASes the route has traversed. Loops are prevented not by TTL
(as in IP) or split-horizon (as in RIP), but by **AS_PATH loop detection** —
if your own AS number appears in the AS_PATH, you reject the route.

```
   AS 100 ── AS 200 ── AS 300 ── AS 400
     │         │         │         │
     │  advertises 198.51.100.0/24 with AS_PATH = [400, 300, 200]
     └────────────────────────────────────────────────────────────►
```

When the UPDATE arrives at AS 100 from AS 200, the AS_PATH is
`200 300 400`. AS 100 prepends its own AS only when re-advertising to an
eBGP peer (giving `100 200 300 400`). iBGP peers do **not** prepend — the
same AS — which is why iBGP needs the full-mesh workaround.

## eBGP vs iBGP

| Aspect | eBGP | iBGP |
|--------|------|------|
| Peer AS | Different | Same |
| AS_PATH prepended | Yes | No |
| TTL default (Cisco) | 1 (eBGP-multihop raises it) | 255 |
| NEXT_HOP behavior | Set to self on advertise | Preserved from eBGP route |
| AS_PATH loop check | Active (reject if own AS seen) | Inactive (no AS in path) |
| Route propagation | Advertises learned routes | Does NOT re-advertise iBGP-learned routes |
| Default AD | 20 | 200 |

The iBGP "do not re-advertise" rule is the source of the **full-mesh
problem**: with N routers in an AS you need N(N-1)/2 iBGP sessions. For N=100
that is 4,950 sessions.

## Path Attributes (RFC 4271 §4.3)

BGP attributes are TLV-encoded. They split into four categories:

| Category | Meaning | Examples |
|----------|---------|----------|
| Well-known mandatory | Must be present, every BGP must understand | ORIGIN, AS_PATH, NEXT_HOP |
| Well-known discretionary | Every BGP must understand, optional to send | LOCAL_PREF, ATOMIC_AGGREGATE |
| Optional transitive | May not be understood, must be passed on | AGGREGATOR, COMMUNITY |
| Optional non-transitive | May not be understood, dropped at AS border | MED, ORF |

### AS_PATH

The ordered list of ASes. Two segment types: `AS_SEQUENCE` (ordered, the
normal case) and `AS_SET` (unordered, used when aggregating to preserve path
information). AS_PATH prepending (e.g. `100 100 100 200 300`) inflates the
path length to make a route less attractive inbound.

```
   AS_PATH: 100 100 100 200 300     <-- prepended 3x by AS 100
            ^^^^^^^^^^^^^^^            to discourage inbound traffic
```

### LOCAL_PREF

A 32-bit integer propagated inside the AS only. Higher = preferred. Set on
inbound route-maps to bias **outbound** traffic toward a particular upstream.

### MED (Multi-Exit Discriminator)

A 32-bit integer (optional non-transitive) used to tell a neighboring AS
which of multiple links to prefer for **inbound** traffic. Lower =
preferred. Cisco's `always-compare-med` enables cross-AS comparison;
otherwise MED is compared only between routes from the same neighboring AS.

### NEXT_HOP

The IP to forward to. For eBGP-learned routes, NEXT_HOP is the peer's IP.
When that route is re-advertised into iBGP, NEXT_HOP is **preserved** (not
modified) — meaning iBGP receivers need an IGP route to the original eBGP
peer's IP, or `next-hop-self` must be set.

### COMMUNITIES

A 32-bit value, conventionally written `AS:NN` (e.g. `2914:140` is NTT's
blackhole community). Well-known communities:

- `NO_EXPORT` (0xFFFFFF01) — do not advertise to eBGP peers
- `NO_ADVERTISE` (0xFFFFFF02) — do not advertise to any peer
- `LOCAL_AS` / `NO_EXPORT_SUBCONFED` (0xFFFFFF03) — do not export outside the
  confederation

Large communities (RFC 8097) use 96 bits (`LC:<global>:<local>:<local>`) to
escape the 16-bit local-part limit.

## The Loc-RIB Pipeline: Adj-RIB-In → Loc-RIB → Adj-RIB-Out → FIB

A BGP speaker maintains three logical tables per peer:

```
   UPDATE   +---------------+   +--------------+   +--------------+   UPDATE
   -------> |  Adj-RIB-In   |-->|   Loc-RIB    |-->| Adj-RIB-Out  | ------>
            | (per-peer,    |   | (best paths, |   | (per-peer,   |
            |  all routes)  |   |  policy-appl)|   |  advertised) |
            +---------------+   +--------------+   +--------------+
                                          |
                                          v
                                   +--------------+
                                   |     FIB      |  <-- forwarding plane
                                   | (kernel/ASIC)|
                                   +--------------+
```

1. **Adj-RIB-In**: every route received from the peer, kept unmodified.
2. **Loc-RIB**: the *best* route per destination after running the decision
   process and applying import policy.
3. **Adj-RIB-Out**: routes selected for advertisement to a peer, after
   applying export policy.
4. **FIB**: Loc-RIB winners pushed to the kernel/forwarding ASIC.

When a new UPDATE arrives that wins the decision process for a prefix, the
old best route is replaced in Loc-RIB and a new UPDATE is computed and queued
to affected peers. The same prefix can produce many UPDATE churns —
controlled by **Route Flap Damping** (RFC 2439, now discouraged) and **BGP
AddPath** (RFC 7911), which lets peers receive multiple paths per prefix.

## The 13-Step Decision Process

Cisco's documented algorithm (iOS/XR ordering) evaluates routes to the same
prefix sequentially. The first step that breaks the tie wins:

| # | Step | Notes |
|---|------|-------|
| 1 | Highest WEIGHT (local to router, Cisco-proprietary) | Default 0; not in RFC 4271 |
| 2 | Highest LOCAL_PREF | 100 by default; only comparable within AS |
| 3 | Locally originated (network/aggregate command) preferred | "I made this route" |
| 4 | Shortest AS_PATH | AS_SET counts as 1 hop |
| 5 | Lowest ORIGIN code | IGP < EGP < Incomplete |
| 6 | Lowest MED | Only compared from same neighboring AS by default |
| 7 | eBGP-learned preferred over iBGP | eBGP = more "trustworthy" |
| 8 | Lowest IGP metric to NEXT_HOP | Tie-break after BGP-attributes |
| 9 | Oldest route (stability) | eBGP only |
| 10 | Lowest ROUTER_ID | BGP identifier of origin |
| 11 | Lowest CLUSTER_LIST length | Only with route reflectors |
| 12 | Lowest ORIGINATOR_ID | Only with route reflectors |
| 13 | Lowest PEER ADDRESS | Final deterministic tiebreak |

Steps 1-8 are pure attribute comparisons; steps 9 onward are deterministic
tiebreakers introduced to avoid oscillation. RFC 4271 §9.1.1 specifies a
similar (but vendor-neutral) order without WEIGHT.

## Route Reflectors and the Full-Mesh Problem

Because iBGP does not re-advertise learned routes, a 100-router AS needs
4,950 sessions. **Route Reflectors** (RFC 4456) solve this by allowing a
designated RR to "reflect" iBGP-learned routes to other iBGP peers.

```
                  +----------------+
                  |  Route         |
        +-------->|  Reflector     |--------+
        |         |  (RR)          |        |
        |         +----------------+        |
        |                  ^                |
        |                  | reflect         |
        |                  |                 |
   +----+----+       +----+----+       +----+----+
   | Client  |       | Client  |       | Client  |
   |   R1    |       |   R2    |       |   R3    |
   +---------+       +---------+       +---------+
```

The RR tags reflected routes with two attributes:

- **ORIGINATOR_ID**: the BGP ID of the route's originator (so the originator
  does not accept its own route back).
- **CLUSTER_LIST**: the list of cluster IDs the route has passed through
  (loop prevention — the iBGP equivalent of AS_PATH).

Clients peer only with RRs (or with each other). RRs peer with other RRs in
a hierarchy. A typical design has two RRs per PoP for redundancy.
Confederations (RFC 5065) are an alternative: sub-ASes inside an AS, where
eBGP-like semantics apply between sub-ASes (AS_PATH prepended with the
sub-AS IDs, full-mesh reduced within each sub-AS).

## BGP Security — RPKI and BGPsec

BGP was designed in 1989 with **no authentication of origin**: any AS can
advertise any prefix. The two classic attacks:

- **Prefix hijacking**: AS X advertises a prefix it does not own. The 2008
  Pakistan Telecom hijack of YouTube (AS 17557 advertised
  208.65.153.0/24 more specifically than YouTube's /22) took YouTube offline
  globally for ~2 hours.
- **Route leak**: a customer advertises routes learned from one transit
  provider to another, becoming an unintended transit AS. The 2015 Telekom
  Malaysia leak redirected traffic from Australia to the US through
  Malaysia for hours.

### RPKI (RFC 6480)

Resource Public Key Infrastructure: each RIR (ARIN, RIPE, APNIC…)
runs a CA. AS holders cryptographically sign **Route Origin
Authorizations** (ROAs) binding a prefix to an origin AS.

```
   ROA:  {prefix: 198.51.100.0/24, origin AS: 64500,
          maxLength: 24, validity: 2024-01-01..2025-01-01}
   signed by: ARIN's CA over the AS holder's resource cert
```

Validating routers fetch the ROA set (via rsync or the RRDP protocol), build
a validity cache, and tag each BGP route as **Valid**, **Invalid**, or
**NotFound**. Operators can then reject Invalids
(`bgp bestpath reject-invalid` in Cisco syntax). MANRS and NIST track ~40%
of the Internet's prefixes as RPKI-valid (2024).

### BGPsec (RFC 8205)

BGPsec extends RPKI to the *path*: each AS in the AS_PATH signs a segment
over the previous signature, producing a chain of cryptographic signatures
that proves the path was actually traversed. The 64-byte signatures are
massive per-UPDATE overhead; BGPsec has had almost no production deployment
as of 2024. ASPA (Autonomous System Provider Authorization,
draft-ietf-sidrops-aspa-profile) is the lighter alternative being
standardized — it only validates the *first* AS hop in the path against a
customer's signed provider list.

## BGP vs OSPF

| Dimension | BGP | OSPF |
|-----------|-----|------|
| Scope | Inter-AS (EGP) | Intra-AS (IGP) |
| Algorithm | Path vector | Link state + Dijkstra |
| Metric | Many attributes; policy-driven | Single cost (bandwidth) |
| Convergence | Minutes (conservative) | Seconds |
| Loop prevention | AS_PATH | LSDB + SPF tree |
| Scaling unit | ASes (~75k) | Areas |
| Topology | Policy-driven (not shortest path) | Shortest path |
| Default timers | Hold 90s, Keepalive 30s | Hello 10s, Dead 40s |
| Transport | TCP 179 | IP protocol 89 (its own) |

OSPF carries infrastructure inside an AS; BGP carries policy between ASes.
A common production design: OSPF/IS-IS underlay + iBGP carrying customer
prefixes + eBGP peering with upstreams. BGP is "slower but smarter"; OSPF
is "faster but dumber".

## Interview Pitfalls

- **"BGP uses bandwidth-based metrics."** It doesn't. The metric is the
  whole attribute set, with AS_PATH length as the primary lever. A 10-hop
  route can beat a 1-hop route if LOCAL_PREF or WEIGHT says so.
- **Treating MED as a global tiebreaker.** By default MED is only compared
  between routes whose neighboring AS is the same. Cross-AS MED comparison
  requires `always-compare-med` and is non-deterministic without it.
- **Forgetting NEXT_HOP preservation in iBGP.** The single most common
  cause of "BGP route in Loc-RIB but unreachable in FIB" — the IGP has no
  route to the eBGP peer's IP. Fix with `next-hop-self` or run the IGP to
  the peering link.
- **Saying iBGP has AS_PATH loop prevention.** It does not — same AS, no
  prepending, no AS_PATH entries to loop on. This is exactly why the
  full-mesh rule exists.

## References

- RFC 4271 — BGP-4: <https://www.rfc-editor.org/rfc/rfc4271>
- RFC 4456 — BGP Route Reflection: <https://www.rfc-editor.org/rfc/rfc4456>
- RFC 6480 — Resource Public Key Infrastructure (RPKI): <https://www.rfc-editor.org/rfc/rfc6480>
- RFC 8205 — BGPsec Protocol Specification: <https://www.rfc-editor.org/rfc/rfc8205>
- RFC 6793 — BGP Support for 4-octet AS Numbers: <https://www.rfc-editor.org/rfc/rfc6793>
- RFC 8097 — BGP Large Communities: <https://www.rfc-editor.org/rfc/rfc8097>
- MANRS — Mutually Agreed Norms for Routing Security: <https://www.manrs.org>
- Iljitsch van Beijnum, *BGP: Building Reliable Networks with the Border
  Gateway Protocol*, O'Reilly, 2002.
