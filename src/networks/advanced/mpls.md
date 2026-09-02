# MPLS (Multiprotocol Label Switching)

MPLS is a packet-switched networking technology, standardized in RFC 3031 (2001) and widely used by service providers (ISPs, telcos) for their backbone networks. MPLS adds a 4-byte "label" to packets, allowing routers to forward based on labels rather than IP addresses — enabling traffic engineering, VPNs, and QoS. This page covers the architecture, the LDP protocol, the traffic engineering extensions, and the production use cases.

## The Architecture

Traditional IP routing: each router makes an independent forwarding decision based on the destination IP.

MPLS: a packet carries a "label" (a 20-bit identifier); routers forward based on the label. The label is added at the network's edge (Label Edge Router, LER) and removed at the egress LER.

```text
Ingress LER → Label Switch Router (LSR) → LSR → LSR → Egress LER
   (pushes label)  (swaps label)        (swaps) (pops label)
```

The path through the LSRs is called a Label Switched Path (LSP). The LSP can be:
- **Hop-by-hop**: each LSR picks the next hop based on the label's destination IP.
- **Explicit (Traffic Engineered)**: the LSP follows a pre-computed path (specified by the ingress LER).

## The Label Header

MPLS adds a "shim header" between the link-layer header and the network-layer header:

```text
Ethernet frame:
  [Dest MAC][Src MAC][EtherType=0x8847][MPLS label][IP packet]

MPLS label (4 bytes):
  Label (20 bits)
  Traffic Class (3 bits, formerly Exp)
  Bottom-of-Stack (1 bit)
  TTL (8 bits)
```

Multiple MPLS labels can be stacked (the "Bottom-of-Stack" bit indicates the last one). This is used for hierarchical LSPs.

## Label Distribution

LSRs need to know which labels correspond to which Forwarding Equivalence Classes (FECs). The Label Distribution Protocol (LDP, RFC 5036) handles this:

```text
1. LSR-A has a route to 10.0.0.0/8 (via IGP, e.g., OSPF).
2. LSR-A allocates label 100 for FEC 10.0.0.0/8.
3. LSR-A sends LDP message to LSR-B: "label 100 → 10.0.0.0/8".
4. LSR-B records: from LSR-A, label 100 → 10.0.0.0/8.
5. LSR-B allocates label 200 for the same FEC; sends to LSR-C.
6. LSR-B records: to LSR-A, label 100; to LSR-C, label 200.
7. When LSR-B receives a packet with label 200, it swaps to label 100 and forwards to LSR-A.
```

LDP runs on top of TCP (port 646); LSRs form LDP sessions and exchange labels.

## Traffic Engineering (RSVP-TE)

For traffic-engineered LSPs, the labels are distributed via RSVP-TE (Resource Reservation Protocol with Traffic Engineering extensions). RSVP-TE allows the ingress LER to specify the path:

```text
Ingress LER: "I want an LSP to 10.0.0.0/8 via LSR-X, LSR-Y, LSR-Z."
RSVP-TE: sends PATH message along the specified path.
Each LSR allocates a label; sends RESV back.
LSP is established with the explicit path.
```

This lets the operator route traffic along non-shortest paths (e.g., to avoid a congested link, or to use a lower-cost link).

## MPLS VPNs

MPLS supports layer-3 VPNs (RFC 4364):

```text
Customer A's sites → Provider Edge (PE) routers → MPLS backbone → PE → Customer A's site
Customer B's sites → PE routers → MPLS backbone → PE → Customer B's site
```

The PE routers maintain per-customer routing tables (VRFs — Virtual Routing and Forwarding). Each customer's traffic is isolated; the MPLS backbone carries the packets between PEs.

The PE adds two labels:
- **VPN label**: identifies the customer's VRF (used by the egress PE).
- **Transport label**: identifies the path to the egress PE (used by intermediate LSRs).

This is the standard way telcos provide MPLS VPN services to enterprise customers.

## QoS with MPLS

MPLS's 3-bit Traffic Class field provides 8 QoS levels:

```text
Traffic Class 0-1: Best effort.
Traffic Class 2-3: Low drop probability.
Traffic Class 4-5: Medium drop probability.
Traffic Class 6-7: High drop probability (control traffic).
```

LSRs can queue packets per Traffic Class, ensuring that high-priority traffic (e.g., VoIP) gets through congested links.

## Production Use Cases

### Service Provider Backbones

MPLS is the standard for ISP backbones. The label-based forwarding allows:
- Traffic engineering (avoid congestion).
- Fast reroute (FRR) — sub-50 ms failover on link failure.
- VPN services to enterprises.

### Enterprise WANs

Large enterprises use MPLS VPNs to connect their sites:
```text
Branch office → Service Provider's MPLS VPN → HQ
```

The service provider handles the routing; the enterprise sees a private network.

### Data Center Networks

Some modern data centers use MPLS in the fabric:
- Avoid the complexity of BGP at scale.
- Traffic engineering for east-west traffic.

But MPLS in the data center is rare; most use BGP (with EVPN) or simpler overlays (VXLAN, Geneve).

## Production Performance

MPLS forwarding performance:
- Per-packet lookup: O(1) (label is a direct index).
- Hardware support: most routers and switches have MPLS in ASICs.
- Throughput: limited by the router's hardware, not the MPLS protocol itself.

For comparison, IP forwarding requires a longest-prefix match (slightly more expensive per packet).

## MPLS vs. Segment Routing

Segment Routing (SR, RFC 8402, 2018) is the modern replacement for MPLS:
- SR uses source routing (the ingress node specifies the path).
- SR can run over MPLS (using MPLS labels) or IPv6 (using SRH extension header).
- SR is simpler (no LDP, no RSVP-TE).

```text
MPLS: LDP distributes labels; routers swap labels along the path.
SR: Source node adds a list of segments (labels); each router pops the next segment.
```

Major service providers are migrating from MPLS to SR for simplicity.

## Common Pitfalls

1. **Forgetting that MPLS doesn't replace IP; it's an overlay.** Packets still have IP headers (hidden behind the MPLS shim). The IP is used for routing at the egress LER.

2. **Forgetting that MPLS requires all routers in the path to support it.** A non-MPLS router in the middle breaks the LSP.

3. **Forgetting that LDP and IGP must be in sync.** LDP distributes labels for IGP routes. If the IGP and LDP diverge (e.g., IGP knows about a route but LDP doesn't), traffic can blackhole.

4. **Forgetting that RSVP-TE has scalability limits.** RSVP-TE maintains per-LSP state; large networks (10K+ LSPs) strain the LSRs. Segment Routing avoids this.

5. **Forgetting that MPLS VPNs require careful VRF configuration.** Misconfigured VRFs leak traffic between customers.

6. **Forgetting that MPLS doesn't encrypt.** For confidentiality, use IPSec or WireGuard on top of MPLS.

## Comparison to Other Networking Technologies

| Aspect | MPLS | Segment Routing | VXLAN/Geneve | IPSec |
|--------|------|------------------|---------------|-------|
| Layer | 2.5 (between L2 and L3) | L3 (IPv6) or L2.5 (MPLS) | L2 overlay | L3 encrypt |
| Use case | Service provider backbone | Modern backbone | Data center overlay | VPN encryption |
| Standard | RFC 3031 | RFC 8402 | RFC 7348/8926 | RFC 4301 |
| Best for | Telcos, enterprise WANs | Next-gen telcos | Data centers | Encrypted tunnels |

MPLS remains the dominant protocol in service provider backbones; SR is the modern replacement. VXLAN/Geneve are for data center overlays.

## References

- [RFC 3031: MPLS Architecture](https://datatracker.ietf.org/doc/html/rfc3031)
- [RFC 5036: LDP](https://datatracker.ietf.org/doc/html/rfc5036)
- [RFC 3209: RSVP-TE](https://datatracker.ietf.org/doc/html/rfc3209)
- [RFC 4364: BGP/MPLS IP VPNs](https://datatracker.ietf.org/doc/html/rfc4364)
- [RFC 8402: Segment Routing](https://datatracker.ietf.org/doc/html/rfc8402)
- [MPLS: A Tutorial (Juniper)](https://www.juniper.net/documentation/us/en/software/junos/mpls/topics/topic-map/mpls-overview.html)
- [LWN: MPLS overview (2020)](https://lwn.net/Articles/820133/)
