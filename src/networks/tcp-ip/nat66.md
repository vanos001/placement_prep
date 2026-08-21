# NAT66 and NPTv6 — IPv6-to-IPv6 Translation

> *"IPv6 was meant to kill NAT. NAT did not die. What did die is the illusion that NAT was the only way to translate addresses."*

## 1. Why IPv6 Still Has Translation

The IPv6 design brief was explicit: enough addresses for every device, so that end-to-end connectivity (RFC 2775, RFC 4924) could be restored — no address overloading, no inbound-connection pinholes, no ALGs for FTP/SIP/H.323. RFC 6296 §1 opens with that exact disclaimer, then proceeds to specify a translation mechanism anyway. Why?

Three operational realities force translation back into IPv6:

1. **Multi-homing without BGP gymnastics.** A small site has two ISPs, each delegating a different IPv6 prefix. Announcing both prefixes from both ISPs requires BGP and PI (provider-independent) space — expensive and out of reach for a small enterprise. NAT-ing one prefix to another at the egress avoids needing any of that.
2. **Site renumbering.** A business changes ISPs and gets a new /48. Renumbering every server, every ACL, every DNS AAAA, every firewall rule is genuinely hard. Translation lets the internal network keep its old ULA numbering while a border device translates to the new public prefix at the edge.
3. **Residential CPE behaviour.** Consumer routers ship from a world where NAT44 is universal; vendors reflexively implemented an IPv6 equivalent, and a substantial fraction of CPE firmware still does Network-Side Prefix Translation by default. RFC 7755 acknowledges this and documents how to make it less harmful.

So the IETF produced two specifications: **NPTv6 (RFC 6296)** — stateless prefix translation, deliberately constrained to 1:1 mapping; and an informal family of stateful "NAT66" mechanisms (RFC 7605 §5) that have been **rejected** for standardisation. The choice of stateless is intentional: stateless preserves the end-to-end principle as much as possible.

## 2. NAT66 vs NPTv6 — Terminology

The naming is genuinely confusing. Clarifying it once and for all:

| Term | Defined where | Stateful? | Maps what | Standardised? |
|------|---------------|-----------|-----------|----------------|
| NAT44 | RFC 1631, RFC 3022 | Yes (PAT) | IPv4 addr + port | Yes |
| NAT64 | RFC 6146 | Yes | IPv6 ↔ IPv4 addr + port | Yes |
| SIIT  | RFC 7915 | No (stateless) | IPv6 ↔ IPv4 addr | Yes |
| NPTv6 | RFC 6296 | No | IPv6 prefix ↔ IPv6 prefix | Yes |
| NAT66 / NAPT66 | RFC 7605 §5 | Yes | IPv6 addr + port | NOT standardised |
| MAP-T/MAP-E | RFC 7597, RFC 7599 | No | IPv4-in-IPv6 mapping | Yes |

When operators say "NAT66", they usually mean *some* IPv6-to-IPv6 stateful translation — and there's no single RFC that defines it. The IETF's position (RFC 7605) is "we don't recommend stateful NAT66; use NPTv6 if you must translate."

## 3. The NPTv6 Algorithm — Stateless, Checksum-Neutral

NPTv6 translates between two /48 prefixes (or any two equal-length prefixes). The interface identifier (low 64 bits) is **preserved** through translation, so the mapping is 1:1 and reciprocal. No state, no port, no session table.

The naive version — substitute prefix A for prefix B — breaks L4 checksums, because the UDP/TCP/ICMPv6 pseudo-header includes both IP addresses. NPTv6 fixes this with a clever trick: it adjusts the translated prefix so that the one's-complement sum of the address is unchanged.

### The algorithm (RFC 6296 §3)

Given internal prefix `P_int` (48 bits) and external prefix `P_ext` (48 bits), and a packet whose source address is `P_int :: <IID>`:

1. Compute `d = ones_complement(P_ext) - ones_complement(P_int)`.
   - i.e. take the difference of the two prefixes' 16-bit one's-complement sums.
2. Substitute `P_ext` into the address, getting `P_ext :: <IID>`.
3. Adjust one octet of the IID (typically a byte of the IID chosen so that the original host-portion's checksum-neutral point is preserved) by adding `d`. The result is that `ones_complement(P_ext :: <IID>') = ones_complement(P_int :: <IID>)`.
4. The L4 checksum (which covers the pseudo-header) is therefore *unchanged* — the translator passes the packet through without recomputing it.

Concretely, the difference `d` is computed on the 48-bit prefix in three 16-bit chunks. If `P_int = 2001:0db8:0001::/48` and `P_ext = 2001:0db9:0002::/48`:

```
   16-bit chunks of P_int:  0x2001, 0x0db8, 0x0001   sum = 0x2EBA
   16-bit chunks of P_ext:  0x2001, 0x0db9, 0x0002   sum = 0x2EBC

   difference d = 0x2EBC - 0x2EBA = 0x0002

   For internal address 2001:0db8:0001:0abcd:1234:5678:9abc:def0,
   NPTv6 picks one of the IID's 16-bit groups (RFC 6296 suggests the 5th group
   counting from the left, but leaves it implementation-defined) and adds d to it.
   Let's pick group 5: 0x5678 + 0x0002 = 0x567A.

   External address = 2001:0db9:0002:0abcd:1234:567A:9abc:def0
                      ^^^^^^^^^^^^^^^^                  ^^
                      prefix substituted               IID-adjusted byte
```

The translator stores nothing. The same arithmetic applied in reverse recovers the original address.

### NPTv6 packet flow

```
                  Inside (ULA)                          Outside (GUA)
   Host 2001:db8:1111::5                         Public 2001:db8:2222::5
        |                                                 ^
        | packet src=2001:db8:1111::5, dst=remote          |
        v                                                 |
   +-----------+                                          |
   |  NPTv6    |  rewrite src prefix; adjust IID byte      |
   |  border  |-------------------------------------------+
   +-----------+
        |                                                 ^
        v                                                 |
   Internet sees src=2001:db8:2222::5 (adj)              |
                                                         |
        inbound packet src=remote, dst=2001:db8:2222::5  |
   +-----------+                                          |
   |  NPTv6    |  rewrite dst prefix; adjust IID byte back|
   |  border  |<------------------------------------------+
   +-----------+
        |
        v
   Host receives dst=2001:db8:1111::5
```

The key invariants of NPTv6:

1. **1:1 mapping** — each internal address maps to exactly one external address, and vice versa. No port overloading.
2. **Stateless** — translation is a pure function. The border device can reboot without dropping any flow.
3. **Checksum-neutral** — L4 checksum is preserved, so the translator need not even touch the L4 segment.
4. **Bi-directional** — inbound connections to the external address are translated to the corresponding internal address with no session table.

The first three are what let NPTv6 escape the "NAT breaks everything" critique that levelled NAT44. The fourth means an internal host can be reached from the outside by simply translating the public address — exactly what IPv6 wanted to enable.

### What NPTv6 does NOT do

- It does **not** hide internal topology. Each external address uniquely maps to one internal address — an observer that can correlate prefix-translation events can recover internal addresses.
- It does **not** multiplex many internal hosts onto one external address. There is no address conservation; the external prefix is the same size as the internal prefix.
- It does **not** translate ports. There is no PAT-style mapping, so a `connect()` from `internal:port1` and one from `internal:port2` to the same external endpoint have *different* translated source addresses, not different ports on the same address.
- It does **not** handle applications that embed IP addresses in the payload (SIP, FTP active mode, some legacy games) — but unlike NAT44, NPTv6 doesn't have to, because the external-to-internal mapping is one-to-one and the application sees the address it sent from.

## 4. Stateful NAT66 (NAPT66) — What the IETF Refused to Standardise

Stateful NAT66 — translating IPv6 addresses *and* ports (so multiple internal addresses map to one external address with port multiplexing) — is the obvious IPv6 analogue of NAT44. RFC 7605 §5 catalogues the proposals and explains why none was standardised.

The IETF's argument boils down to four points:

### 4.1 It solves a problem IPv6 doesn't have

NAT44 PAT exists because IPv4 has 2³² addresses. IPv6 has 2¹²⁸ addresses, of which 2⁶⁴ is the host portion of a single /64 — every link can have 18 quintillion addresses. Multiplexing many hosts onto one address is solving a problem that does not exist in IPv6.

### 4.2 It reintroduces every NAT44 failure mode

NAPT66 would have:
- A per-session state table (the border device can crash, dropping all flows).
- Port-overloading (a single external address has 65535 source ports — heavy contention on long-running networks).
- ALG requirements for any protocol that embeds addresses (SIP, FTP active, RTSP).
- Inbound connection pinholes (the " NAT as firewall" myth that breaks P2P).

The IETF reasoned: if NAT44 has known operational pathologies for 25 years (RFC 2993, RFC 3027), there's no point designing its IPv6 twin to inherit them.

### 4.3 It breaks end-to-end transparency permanently

The end-to-end principle (Saltzer, Reed, Clark, 1984) — the canonical argument that network-layer functions should be as dumb as possible — is the philosophical bedrock of the IPv6 design. RFC 6296 §1 makes this explicit: "the IETF does not recommend the use of IPv6-to-IPv6 Network Address Translation."

The IETF's compromise was NPTv6: it does the only legitimate things IPv6-to-IPv6 translation can do (multi-homing, renumbering, mismatched-prefix routing) without the pathologies.

### 4.4 It still ships, in violation of the standards

A substantial fraction of consumer-grade CPE ships a "NAT66" feature, often mislabelled "IPv6 NAT" or "IP Passthrough" in vendor marketing. It is variously:
- NPTv6 (stateless, RFC-compliant) — common in OpenWRT's `odhcpd` `ip6prefix` translation.
- A stateful PAT-style translator, sometimes borrowed from the same code path as NAT44.
- A "1:1" mapping per host (like static NAT44), which is NPTv6 minus the checksum-neutral trick and so does need L4 checksum rewrites.

Operators should explicitly disable the latter two wherever they encounter them, and use NPTv6 instead — the only IPv6-to-IPv6 translation with a standard reference.

## 5. NAT44 vs NPTv6 — A Real Comparison

| Property                       | NAT44 (PAT)                 | NPTv6 (RFC 6296)             |
|--------------------------------|-----------------------------|------------------------------|
| Maps                          | many internal → one external + port | one internal → one external |
| State                         | Stateful (per-flow table)   | Stateless (pure function)   |
| Address conservation           | Yes                          | No                           |
| L4 checksum recompute          | Yes (mandatory)              | No (checksum-neutral design) |
| Allows inbound connections    | Only via pinhole/port-forward | Yes — any internal host     |
| Breaks end-to-end              | Yes                          | Only on prefix — IID preserved |
| Hides internal topology        | Yes                          | No (1:1 mapping)             |
| Supports PMTUD                 | Buggy (RFC 3027)            | Yes (just passes ICMPv6 PTB) |
| ALG requirements               | Yes (FTP, SIP, etc.)        | No                            |
| Failure modes on border reboot | All flows die               | None — no state to lose     |
| Replaces what IPv6 mechanism   | (was IPv4 conservation hack) | Multi-homing edge translation |

A useful way to think about NPTv6: it's a *renumbering function applied at the boundary*, not a *translation function applied per-packet*. The packet that emerges from the border device is what the source host would have sent had it been told to use the external prefix in the first place.

## 6. When Translation Still Makes Sense

### 6.1 Multi-homing small sites

```
                  +---------+                  +---------+
                  |  ISP 1  |                  |  ISP 2  |
                  | prefix:|                  | prefix:|
                  | 2001:db8:aaaa::/48 |       | 2001:db8:bbbb::/48 |
                  +----+----+                  +----+----+
                       |                            |
                       v                            v
                  +----+-----+----------------+-----+----+
                  |    Border device (NPTv6 border)     |
                  | Internal prefix: fd00:cafe::/48    |
                  | ISP1 path: fd00:cafe <-> 2001:db8:aaaa
                  | ISP2 path: fd00:cafe <-> 2001:db8:bbbb
                  +----------------+-------------------+
                                   |
                                   v
                            Internal network
                            fd00:cafe::/48 (ULA)
```

The internal network runs a stable ULA prefix (`fd00:cafe::/48`), but on each egress the border device translates to the ISP's GUA. Outbound traffic picks one path (or load-balances); inbound to `2001:db8:aaaa::5` is translated back to `fd00:cafe::5`. Internal renumbering is *never required* — change ISPs in 5 minutes by changing one prefix on the border.

The catch: an internal host can be reached from the Internet via two different external addresses. If it accepts an inbound TCP connection from `2001:db8:aaaa::5`, the returning packets must egress via ISP 1, not ISP 2 — and source-prefix policies or BCP 38 must enforce this, or the traffic comes back via ISP 2 with a `2001:db8:bbbb::5` source address the original client doesn't expect.

### 6.2 Site renumbering

When an enterprise moves ISPs, its old prefix is being returned to the previous ISP. Renumbering every server and ACL can take months; NPTv6 lets the site keep its old ULA internally and translate to the new prefix immediately. Once the internal renumbering is finished piecemeal, NPTv6 can be removed.

### 6.3 Connecting to a partner's non-routable space

Two companies merge; one uses `fd00:1::/32` internally and the other uses `fd00:2::/32`. They want to merge networks without renumbering. NPTv6 at the interconnect translates each side's prefix to a globally-unique agreed range so neither side's addresses clash on the other side.

### 6.4 Cloud-edge deployments

Some cloud providers assign a public GUA per VM, but enterprises want their VMs to use internal ULAs that match their corporate IPAM. NPTv6 at the cloud edge translates between the two — VMs send from `fd00:corp::vm1`, the cloud border translates to the assigned GUA, the Internet sees the cloud's GUA, and inbound traffic to that GUA is translated back.

## 7. Why NPTv6 Has Not Conquered the World

Despite the elegance, NPTv6 deployment is rare outside enthusiast OpenWRT setups and a few niche enterprise sites. The reasons:

1. **Multi-homing sites that can afford IPv6 PI space get it.** A /48 PI prefix is a few hundred euros per year from a regional registry; this avoids any translation and the provider-egress policies.
2. **Cloud providers don't support customer-side NPTv6** — they assign GUAs and let the customer ULA internally without translation, then bridge.
3. **DNS aligns better with real GUA assignment.** AAAA records in the IPAM point to actual GUAs; NPTv6 would require translating DNS responses, which is fragile.
4. **Stateful middleboxes have feature gravity.** Operators used to NAT44 expect the same workflow (port forwarding, session logging) and demand stateful NAT66 from vendors, even though no RFC specifies it.

So NPTv6 is a niche answer to a niche problem. RFC 7605 is candid about this: stateless translation should be used where it fits, and IPv6 multi-homing should be solved by BGP/PI where multi-homing is the real need.

## 8. The End-to-End Principle (RFC 2775, RFC 4924, RFC 7269)

The IETF's reluctance to standardise stateful NAT66 is grounded in the end-to-end principle, articulated for IPv6 specifically in:

- **RFC 2775** — "Internet Transparency" (Carpenter, 2000). Argues that address translation is corrosive to the Internet's design.
- **RFC 4924** — "Reflections on Internet Transparency" (2007). Updates 2775 to consider NAT44's victory and explicitly warns against an IPv6 NAT that repeats the IPv4 story.
- **RFC 7269** — "NAT Behaviour in the IPv6 Era" (2014). Catalogues what NAT66 would have to do to be acceptable, and concludes stateful NAT66 should be avoided.
- **RFC 7021** — "Assessing the Impact of Carrier-Grade NAT on Network Applications". Documents NAT44's operational pathology, the case study for "don't do this in IPv6".
- **RFC 7421** — "Analysis of the IETF's Effect on the End-to-End Principle." Synthesises the policy.

The end-to-end principle says: only put intelligence in the network where it's necessary for the network's own function; trust the endpoints to handle everything else. NAT44 violated this to mitigate IPv4 exhaustion; the IETF's stance on IPv6 is that exhaustion isn't a problem here, so the violation isn't justified. NPTv6 is the narrow carve-out for the multi-homing case that genuinely needs translation, designed to leak as little state as possible.

## 9. Common Misconceptions

1. **"NPTv6 is NAT for IPv6."** — No, it's prefix translation without port or state. NAT44 PAT and NPTv6 share the word "translation" but little else.
2. **"NPTv6 hides internal addresses."** — No, it's 1:1. Each internal address maps to exactly one external, so traffic correlation recovers internal topology.
3. **"NPTv6 doesn't break checksums because IPv6 has no checksum."** — Half-true. IPv6 has no *header* checksum, but the L4 (UDP/TCP/ICMPv6) pseudo-header *does* include the addresses, so a naive prefix swap breaks L4. NPTv6's checksum-neutral design avoids this.
4. **"We need NAT66 for security."** — NAT44's "security" is obscurity, not access control. For IPv6 use a stateful firewall (RFC 6092 for residential edge filtering); do not introduce translation for security.
5. **"NPTv6 works with any prefix length."** — No, RFC 6296 requires the two prefixes be the same length, and the algorithm assumes a /48 (the spec allows /64 or other lengths but most deployments use /48).

## 10. Summary

- IPv6 was designed to eliminate NAT; it largely has, but multi-homing and site renumbering create residual demand.
- **NPTv6 (RFC 6296)** is the standards-track answer: a stateless, 1:1, checksum-neutral prefix translation. It preserves the IID and the L4 checksum.
- **Stateful NAT66 / NAPT66** has *not* been standardised and the IETF recommends against it (RFC 7605, RFC 7269). It ships anyway in some CPE, which is a bug rather than a feature.
- NPTv6 is a *renumbering function at the edge* — not the stateful, port-overloading, ALG-ridden NAT44 we know. It should be deployed only when BGP+PI is unavailable and multi-homing is a real requirement.

## 11. References

- RFC 6296 — IPv6-to-IPv6 Network Prefix Translation (NPTv6). https://www.rfc-editor.org/rfc/rfc6296
- RFC 7755 — IPv6-to-IPv6 Network Address Translation (a stateless NAT66 spec was not adopted; this RFC documents the failure of stateful approaches). https://www.rfc-editor.org/rfc/rfc7755
- RFC 7605 — IPv6-to-IPv6 Network Address Translation Considerations. https://www.rfc-editor.org/rfc/rfc7605
- RFC 7269 — NAT Behaviour in the IPv6 Era. https://www.rfc-editor.org/rfc/rfc7269
- RFC 2775 — Internet Transparency. https://www.rfc-editor.org/rfc/rfc2775
- RFC 4924 — Reflections on Internet Transparency. https://www.rfc-editor.org/rfc/rfc4924
- RFC 7021 — Assessing the Impact of Carrier-Grade NAT. https://www.rfc-editor.org/rfc/rfc7021
- RFC 7421 — Analysis of the Effect of the End-to-End Principle on IPv6. https://www.rfc-editor.org/rfc/rfc7421
- RFC 6092 — Recommended Simple Security Capabilities in Residential Customer Premises Equipment. https://www.rfc-editor.org/rfc/rfc6092
- RFC 7915 — Stateless IP/ICMP Translation (for IPv6-to-IPv4, included for context on the broader translation family). https://www.rfc-editor.org/rfc/rfc7915

## Cross-References

- [IPv6 Internals](ipv6-internals.md) — header, extension headers, addressing
- [NAT](nat.md) — IPv4 NAT, the original
- [IPv6 (overview)](ipv6.md) — high-level concepts
- [SLAAC & DHCPv6](slaac-dhcpv6.md) — how hosts get their addresses before translation
- [ICMPv6 & NDP](icmpv6-ndp.md) — control plane that translation must pass through
