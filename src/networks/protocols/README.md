# Network Protocols: Transport, Fabric, and Trust

## Overview

This directory holds protocols that sit *beside* the classic TCP/IP canon — the ones that
show up when the interview moves past "explain the three-way handshake": **SCTP** as the
third transport, **EVPN-VXLAN** as the modern data center's L2/L3 control plane, and
**RPKI/BGP security** as the interdomain trust layer. Each page is protocol-first: wire
format, handshake or control-plane machinery, failure behavior, and the deployment
economics that explain why the protocol is where it is today. All three topics reward the
same interview instinct — compare against the familiar sibling (TCP, VLAN, BGP) and say
*why the newer design exists*, not just what it does.

## Pages in this directory

| Page | One-line summary | Anchor RFCs | Interview frequency |
|---|---|---|---|
| [SCTP](./sctp.md) | Message-oriented transport: multi-streaming kills cross-stream HOL, multi-homing fails over paths, cookie handshake resists SYN floods, PR-SCTP makes reliability a per-message dial; WebRTC data channels ride it over DTLS. | 9260, 3758, 8831, 8261 | Telecom/infra roles; high in 5G & signaling contexts |
| [EVPN-VXLAN](./evpn-vxlan.md) | VXLAN moves L2 over UDP 4789 with a 24-bit VNI; BGP EVPN route types 1–5 replace flood-and-learn with a real control plane, enabling all-active multihoming (ESI), ARP suppression, and distributed anycast L3 gateways. | 7348, 7432, 8365, 9135, 9136 | Data center / cloud infra; near-universal in DC interviews |
| [BGP Security (RPKI)](./rpki-bgp-security.md) | Hijack anatomy and famous incidents; RPKI ROAs and the signing-to-validation chain; ROV's valid/invalid/not-found states; ASPA for leaks, BGPsec's failure, and the max-prefix/filtering hygiene that still catches most incidents. | 6480, 6811, 8210, 9234, 8205 | Network engineering roles; rising with routing-security adoption |

## Which protocol when

### Transport: SCTP vs TCP vs UDP vs QUIC

| You need... | Use | Why |
|---|---|---|
| Ordered byte stream, maximum ecosystem | TCP | Every middlebox, proxy, and stack speaks it |
| Minimal overhead, app-defined reliability | UDP | DNS, media, games — control belongs to the app |
| Web-native streams with per-stream control | QUIC | HOL-free streams + TLS 1.3 built in; the web's chosen path |
| Messages, independent streams, path failover, per-message reliability dial | SCTP | Signaling/telecom (SS7, Diameter, 5G), WebRTC data channels |

Details and the full comparison table: [SCTP](./sctp.md). TCP handshake mechanics:
[TCP three-way handshake](../tcp/three-way.md); QUIC internals: [QUIC](../http/quic.md).

### L2/L3 fabric: VLAN vs EVPN-VXLAN vs Geneve

| You need... | Use | Why |
|---|---|---|
| Campus switching, simple segmentation | VLANs | Zero encapsulation, universal hardware |
| Multi-rack L2 + L3 tenant fabric on switch hardware | EVPN-VXLAN | Standard control plane, ASIC-friendly fixed header |
| Software overlay with per-flow metadata (OVN/OVS) | Geneve | Variable TLV options carry policy metadata |

The underlay story (leaf-spine, ECMP): [Data Center Fabrics](../advanced/datacenter-fabrics.md).
The encapsulation details and packet walk: [EVPN-VXLAN](./evpn-vxlan.md);
[Geneve](../advanced/geneve.md) and [VLAN & STP](../advanced/vlan-stp.md) carry the
respective comparisons from their own angles.

### Interdomain trust: ROV vs OTC vs ASPA vs BGPsec

| You need... | Use | Status |
|---|---|---|
| Prove the origin AS owns the prefix | RPKI ROV (RFC 6811) | Deployed; ~half of IPv4 announcements covered |
| Stop route leaks between neighbors | OTC (RFC 9234) | Standardized, deploying |
| Verify customer-cone path structure | ASPA (sidrops draft) | Pilot phase |
| Cryptographic proof of the entire path | BGPsec (RFC 8205) | Complete, ≈0 deployment |

Filtering/max-prefix hygiene still stops more incidents than any crypto layer —
[BGP Security](./rpki-bgp-security.md) works through the full stack.

## How the three topics connect

They are one story at three layers of the stack. The data center fabric page (EVPN-VXLAN)
runs BGP as its control plane — the same protocol whose security posture is the RPKI page's
subject; a fabric edge that announces reachability into the world needs exactly the
filtering/ROV hygiene described there. SCTP appears on both sides too: carrier networks
built on SCTP signaling are the ones deploying RPKI hardest, and WebRTC — SCTP-over-DTLS —
is the end-host transport that must traverse fabrics and the public internet alike. When
an interviewer jumps topics ("VXLAN now, then how would you secure the eBGP to your
provider?"), they are testing whether you see the layers as one design.

## Suggested reading order

1. [SCTP](./sctp.md) — smallest scope; sharpens the transport comparison skills the
   TCP/UDP pages started ([TCP vs UDP](../udp/tcp-vs-udp.md)).
2. [EVPN-VXLAN](./evpn-vxlan.md) — read after [BGP Deep Dive](../routing/bgp-deep.md);
   EVPN is applied BGP with new route types.
3. [BGP Security](./rpki-bgp-security.md) — the deepest page; assumes BGP fluency and
   extends the security section of the deep-dive page.

## Lab tooling that makes the topics concrete

| Tool | What it teaches | Where |
|---|---|---|
| FRRouting | EVPN-VXLAN and RPKI in a lab: real `evpn` address family, RPKI-RTR config | [docs.frrouting.org](https://docs.frrouting.org/) |
| GoBGP | BGP internals, EVPN NLRI generation, scripted route injection | [github.com/osrg/gobgp](https://github.com/osrg/gobgp) |
| ExaBGP | Route injection/anomaly monitoring from Python — hijack detection practice | [github.com/Exa-Networks/exabgp](https://github.com/Exa-Networks/exabgp) |
| Routinator | RPKI validation: ROA fetching, VRP dumps, RTR serving | [routinator.docs.nlnetlabs.nl](https://routinator.docs.nlnetlabs.nl/) |
| Linux SCTP (`sctp_test`, kernel sockets) | Multi-stream/multi-homing behavior on loopback or veth pairs | [kernel networking docs](https://docs.kernel.org/networking/) |
| RouteViews / RIPE RIS | Real-world BGP data to spot hijacks and leaks in MRT archives | [routeviews.org](https://www.routeviews.org/routeviews/) |
| OVN / OVS | Geneve overlays and logical flows as the software-side contrast | [docs.ovn.org](https://docs.ovn.org/) |

## Numbers worth having ready

Interviews reward precise recall. The short list for this directory:

| Number | Belongs to | Why it matters |
|---|---|---|
| 24-bit VNI ≈ 16.7M segments | VXLAN | vs 12-bit VLAN's 4094 — the headline scaling number |
| UDP 4789 | VXLAN | IANA-assigned port; 8472 is the legacy port trap |
| 50 bytes | VXLAN overhead | Outer Eth+IP+UDP+VXLAN; drives the 9100+ MTU decision |
| 10 bytes | ESI | Ethernet Segment Identifier on multihoming bonds |
| 4789 vs 6081 | VXLAN vs Geneve | Ports are the fastest "which overlay" tell in a capture |
| IP protocol 132 | SCTP | Not a TCP/UDP port — middleboxes drop what they don't know |
| CRC32c | SCTP checksum | vs TCP/UDP additive checksum |
| 4 messages | SCTP handshake | INIT, INIT-ACK+cookie, COOKIE-ECHO, COOKIE-ACK |
| 5 | SCTP `Path.Max.Retrans` | Failover is association-grade, not sub-second |
| 5 | EVPN route types in use | 1 A-D, 2 MAC/IP, 3 IMET, 4 ES, 5 Prefix — know each by name |
| ~50% | RPKI coverage of IPv4 announcements (2024–25) | NotFound is still most of the table — the deployment gap |
| /22 maxLength /24 | ROA footgun | Loose maxLength re-opens the sub-prefix hijack |
| 1.5–2× | max-prefix sizing rule | Over expected prefix count, warn at 80–90% |
| 2018 | ROV drop-invalid normalization & BGPsec RFC | One year: enforcement rose, path-signing died |

## Common confusions (and the one-line fix)

- **"VXLAN has a control plane."** It doesn't — VXLAN is only the tunnel; EVPN is the
  control plane. Interviewers split this deliberately: [EVPN-VXLAN](./evpn-vxlan.md).
- **"SCTP fixed head-of-line blocking."** It removed *delivery* HOL across streams; one
  congestion window still couples all streams' sending rate: [SCTP](./sctp.md).
- **"SYN cookies were SCTP's answer to TCP's problem."** Backwards — the cookie handshake
  is native to SCTP (RFC 9260); TCP retrofitted SYN cookies later:
  [SYN cookies](../tcp/syn-cookies.md).
- **"RPKI validates the AS_PATH."** ROV validates *origin only*; path protection is OTC's
  leak role and ASPA's draft territory: [BGP Security](./rpki-bgp-security.md).
- **"Invalid means forged signature."** ROV produces a state, not a signature verdict —
  BGP carries no signatures; Invalid = contradiction with a covering ROA.
- **"Geneve beat VXLAN."** Neither won overall: ASIC fabrics standardized on EVPN-VXLAN,
  OVN-style software overlays on Geneve: [Geneve](../advanced/geneve.md).

## Interview questions to connect the pages

1. **Why does WebRTC run SCTP over DTLS over UDP instead of just using TCP or raw UDP?**
   See [SCTP — WebRTC data channels](./sctp.md): per-channel reliability/ordering,
   message boundaries, no cross-channel HOL — and no TCP-in-DTLS layering problems.
2. **A leaf switch dies. How does an EVPN fabric recover faster than a MAC-aging timer
   would?**
   See [EVPN-VXLAN — multihoming](./evpn-vxlan.md): Type-1 per-ES mass withdraw, one
   BGP withdrawal for the whole attachment circuit.
3. **Your provider suddenly drops your prefixes. RPKI-related? What do you check first?**
   See [BGP Security](./rpki-bgp-security.md): ROA freshness, maxLength changes,
   max-prefix exhaustion, invalid state from a stale/overlapping announcement.
4. **What do VXLAN's outer-UDP-source-port hashing and ECMP entropy have to do with each
   other?**
   See [EVPN-VXLAN — encapsulation](./evpn-vxlan.md): per-flow entropy over a fixed
   VTEP address pair.
5. **SCTP and QUIC both killed head-of-line blocking — where do they differ?**
   See [SCTP vs TCP vs UDP](./sctp.md): SCTP removes delivery HOL across streams but
   shares one congestion window; QUIC carries independent loss recovery per stream.

## Key Takeaways

- Three pages, three layers: transport (SCTP), fabric control plane (EVPN-VXLAN),
  interdomain trust (RPKI/BGP security) — all three are "the newer design exists because
  the classic one hit a structural wall".
- SCTP's wall: TCP's single ordering domain, single address pair, and all-or-nothing
  reliability; its answers are streams, multi-homing, and PR-SCTP.
- EVPN-VXLAN's wall: VLAN flood-and-learn and 4094 segments; its answer is a 24-bit VNI
  plus BGP route types 1–5 that replace learning with advertisement.
- RPKI's wall: BGP's zero-authentication origin model; its answers are ROAs + ROV today,
  OTC/ASPA for leaks, and a historical lesson from BGPsec about partial-deployment design.
- Interview pattern across all three: name the wall, the mechanism, one number (VNI bits,
  retransmit threshold, ROA coverage), and the deployment caveat.

## Cross-References

- [BGP Deep Dive](../routing/bgp-deep.md) — required background for both the EVPN
  control plane and the RPKI security pages.
- [Data Center Fabrics](../advanced/datacenter-fabrics.md) — the routed underlay that
  VXLAN tunnels across.
- [Geneve](../advanced/geneve.md) — the extensible software-overlay sibling of VXLAN.
- [VLAN & Spanning Tree](../advanced/vlan-stp.md) — the classic L2 design being replaced.
- [TCP Three-Way Handshake](../tcp/three-way.md) — the connection setup SCTP's cookie
  handshake improves on.
- [TCP vs UDP](../udp/tcp-vs-udp.md) — the baseline transport trade-off SCTP enters
  between.
- [QUIC](../http/quic.md) — the mainstream transport that made HOL-free streams popular.
- [Reference Library: Networking](../../references/networking.md) — verified primary
  sources for every protocol in this directory.
