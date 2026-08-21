# IPv6 Internals — Protocol, Header, Extension Headers and Transition

> *"IPv6 is not just 'IPv4 with longer addresses' — it is a from-scratch redesign that removes broadcast, removes header checksums, removes in-router fragmentation and folds ARP, ICMP-Router-Discovery and ICMP-Redirect into a single ICMPv6-based control plane."*

## 1. Why IPv6 Exists

IPv4 addresses are 32 bits, yielding ≈ 4.3 × 10⁹ unique values. After subtracting reserved ranges (RFC 1112 multicast, RFC 1918 private, RFC 6598 shared CGNAT, loopback, etc.), only ~3.7 × 10⁹ addresses were globally routable. IANA's central pool was exhausted on 3 February 2011; the five Regional Internet Registries followed between 2011 and 2017. IPv6, standardised as RFC 8200 (which obsoletes RFC 2460), expands the address field to **128 bits** — roughly 3.4 × 10³⁸ addresses, or 5 × 10²⁸ per human alive today.

But address space was only one of the design goals. RFC 8200 also fixed four things IPv4 got wrong:

1. The IPv4 header was variable-length (20–60 bytes) and forced routers to parse options per-packet, killing hardware forwarding. IPv6 has a **fixed 40-byte header** and pushes everything optional into *extension headers* that only need parsing at the relevant node.
2. IPv4 routers fragmented packets in the forwarding path, requiring per-flow fragment-state and reassembly buffers. IPv6 forbids in-network fragmentation — only the source may fragment, using PMTU discovery (RFC 8201).
3. The IPv4 header checksum was redundant with the link-layer FCS and L4 checksums, costing one 16-bit one's-complement pass per hop. IPv6 **removed the header checksum entirely**.
4. IPv4 broadcast (255.255.255.255 / directed broadcast) woke every host on the link and was a denial-of-service vector. IPv6 has **no broadcast** — it uses scoped multicast instead.

## 2. The 128-bit Address and Its Scopes

An IPv6 address is written as 8 colon-separated 16-bit groups of 4 hex digits, with two compression rules: leading zeros within a group may be dropped, and one run of all-zero groups may be replaced with `::`.

```
Uncompressed:  2001:0db8:0000:0000:0000:0000:0000:0001
Compressed:    2001:db8::1                          (canonical RFC 5952 form)
Embedded IPv4: 2001:db8::192.0.2.1                   (last 32 bits in IPv4 notation)
URL:           http://[2001:db8::1]:8080/            (brackets mandatory in URLs)
```

RFC 4291 partitions the address into a **network prefix** (high bits) and an **interface identifier** (low bits). For all currently allocated global unicast prefixes, the split is /64 — 64 bits of prefix, 64 bits of interface ID. The 64-bit interface ID is large enough to support stateless autoconfiguration via EUI-64 (RFC 4291 Appendix A) or cryptographically opaque values (RFC 7217, RFC 4941).

### Address types

| Type         | Prefix (typical)    | Scope        | Comment                                                  |
|--------------|---------------------|--------------|----------------------------------------------------------|
| Global Unicast (GUA) | 2000::/3   | Global        | Allocated by IANA/RIRs to operators.                    |
| Unique Local (ULA)   | fc00::/7   | Site-local    | RFC 4193; not globally routable. fd00::/8 is in use.   |
| Link-Local (LL)      | fe80::/10  | Single link   | Auto-generated per interface; mandatory for NDP.       |
| Multicast            | ff00::/8   | Per scope field| Scope bits 3..0 give ff01 (iface), ff02 (link), ff05 (site), ff0e (global). |
| Anycast              | (any prefix, flagged) |—       | Same address shared by multiple nodes; routed to "nearest" by IGP metric. |
| Loopback             | ::1/128    | Node          | IPv4's 127.0.0.1 equivalent.                            |
| Unspecified          | ::/0       | —             | Used as source during DAD and before DHCP.              |

Note that anycast is *not* a separate prefix range — it is an address *assigned to more than one node* with no flag in the packet itself. Operators signal anycast by injecting the same prefix from multiple BGP speakers (e.g., 8.8.8.8 for DNS) — IPv6 anycast follows the same operational model.

### Solicited-node multicast (why NDP doesn't broadcast)

Every unicast address `X` automatically maps to a *solicited-node multicast* address `ff02::1:ffXX:XXXX`, where the last 24 bits of `X` are appended. A host resolving a neighbor joins *only* the solicited-node group for that neighbor and listens on the matching ICMPv6 type. This means a neighbor lookup wakes up at most one host on the LAN — three orders of magnitude more efficient than ARP broadcast, which interrupts every interface.

```
Target unicast:           2001:db8:0:1::abcd:1234
Solicited-node multicast: ff02::1:ffcd:1234   (low 24 bits = cd:1234)
Ethernet dst MAC:         33:33:ff:cd:12:34    (RFC 2464 mapping)
```

## 3. The Fixed 40-byte IPv6 Header

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version|   Traffic Class   |           Flow Label              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Payload Length         |  Next Header  |   Hop Limit   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                      Source Address (128 bits)                +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                   Destination Address (128 bits)              +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

Field-by-field:

| Field            | Bits | Meaning |
|------------------|------|---------|
| Version           | 4   | 6 for IPv6. |
| Traffic Class    | 8   | DSCP (6 bits) + ECN (2 bits) — identical semantics to the IPv4 TOS byte. |
| Flow Label       | 20  | A non-zero value identifies a flow that the source wants all routers on the path to treat specially (e.g., QoS class, ECMP hash input). Defined in RFC 6437; previously (RFC 3697) routers were forbidden from changing it. |
| Payload Length   | 16  | Bytes after the 40-byte base header. A *jumbogram* (length > 65535) sets this field to 0 and carries the real length in a Hop-by-Hop Options header (RFC 2675). |
| Next Header      | 8   | Same numbering as IPv4 Protocol field (e.g., 6 = TCP, 17 = UDP, 58 = ICMPv6). When extension headers follow, it points to the first EH. |
| Hop Limit        | 8   | Same as IPv4 TTL — decremented per hop, dropped at 0. Renamed because nobody talks about "seconds to live" any more. |
| Source Address   | 128 | Source GUA/LL/ULA/::. |
| Destination Address | 128 | Final destination. Routing headers can change the value in flight. |

Notable absences vs. IPv4: no IHL (length is fixed), no Identification/Flags/Fragment-Offset (moved into the Fragment Extension Header), no header checksum, no options field.

### Why no header checksum?

Per RFC 8200 §8.2, the header checksum was removed because (a) the Ethernet FCS catches bit errors at L2, (b) the L4 checksum (TCP/UDP/ICMPv6) is mandatory and covers a pseudo-header containing both IP addresses, and (c) every IPv4 hop had to recompute the header checksum after decrementing TTL — pure wasted cycles in the fast path. Removing it lets routers touch only three fields per packet (Hop Limit, possibly Traffic Class), enabling wire-speed hardware forwarding.

A subtle consequence: UDP over IPv4 made its L4 checksum optional (it could be 0). UDP over IPv6 makes it **mandatory** (RFC 8200 §8.1), because there's no IP-level checksum to fall back on.

## 4. Extension Headers

When the sender needs IPv4-style options, it inserts them as a chained list of *extension headers* between the base header and the upper-layer payload. Each EH has its own `Next Header` field, forming a linked list.

```
+---------+   +----------------+   +-----------+   +-----------------+   +-------------+
| IPv6    |-->| Hop-by-Hop     |-->| Routing   |-->| Destination    |-->| Fragment    |--> TCP/UDP
| (NH=0)  |   | Options (NH=43)|   | (NH=43)   |   | Options (NH=60)|   | (NH=44)     |
+---------+   +----------------+   +-----------+   +-----------------+   +-------------+
```

| EH (Next Header value) | Processed by       | Purpose |
|------------------------|--------------------|---------|
| Hop-by-Hop Options (0) | Every router on the path | Router Alerts for RSVP, MLD, Jumbograms. MUST be first if present. |
| Routing (43)           | Specified intermediate nodes | Source routing. RFC 8200 deprecated RH0 (which allowed arbitrary source routing and became a reflector for amplification attacks); RH2 is used by Mobile IPv6 (RFC 6275). |
| Fragment (44)          | Destination host only | Holds original packet's fragment-offset and identification. Only present if the source actually fragmented (after PMTU discovery). |
| Destination Options (60) | Destination host (per-hop options may be placed before Routing) | Padding, MH type 2 for Mobile IPv6 home-address option. |
| AH (51) / ESP (50)    | Endpoint or VPN endpoints | IPsec; same AH/ESP as IPv4 (RFC 4302, RFC 4303). |
| Mobility (135)         | Home agent | Mobile IPv6 binding updates. |

### Recommended ordering (RFC 8200 §4.1)

Per the RFC, the canonical order is:

1. IPv6 base header
2. Hop-by-Hop Options (only if present, must be first)
3. Destination Options (with per-hop options)
4. Routing Header
5. Fragment Header
6. Authentication Header (IPsec AH)
7. Encapsulating Security Payload (IPsec ESP)
8. Destination Options (with per-destination options)
9. Upper-layer header (TCP/UDP/ICMPv6)

### Why ordering matters in practice

Routers are *not* required to look beyond the Hop-by-Hop Options header — indeed RFC 8200 §4.3 explicitly says routers SHOULD process Hop-by-Hop Options but MAY ignore them and forward the packet. Anything after Hop-by-Hop is processed only by the destination (or a node named by Routing). This is why the Fragment header is processed at the destination, not in the network — routers never fragment, they just drop packets exceeding MTU and send back an ICMPv6 Packet Too Big.

This is also why real-world operators struggle: middleboxes (stateful firewalls, load balancers) historically did not parse the full EH chain. RFC 7112 limits the total size of the EH chain that a destination must accept to one IPv6 minimum MTU (1280 bytes), and RFC 7872 documents that some 30–40% of middleboxes drop packets with extension headers. Avoid them unless you have a real reason.

## 5. Worked example: tracing a packet with extension headers

Suppose host A at `2001:db8:1::a` sends a 1500-byte TCP SYN to host B at `2001:db8:2::b`, but the path MTU is 1300. The on-wire layout changes as follows:

```
Without fragmentation (1500 > PMTU 1300 → fails, ICMPv6 Packet Too Big returned):

   [IPv6 hdr 40B | TCP SYN 60B ]                                  ← 100B, fits
   [IPv6 hdr 40B | 1400B payload ]                                ← 1440B, fails

After source-side fragmentation (RFC 8200 §4.5):

   +----+-----------+--------------+-----------+
   | v6 | Frag EH   | Payload 1    |   1280B   |  ← offset=0, M=1
   +----+-----------+--------------+-----------+
   | v6 | Frag EH   | Payload 2    |   160B    |  ← offset=1280, M=0
   +----+-----------+--------------+-----------+

   Fragment EH (8 bytes, RFC 8200 §4.5):
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |  Next Header  |   Reserved    |   Fragment Offset (13b) |Res|2b|M|
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                  Identification (32 bits)                   |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

   Source picks a 32-bit Identification per original packet; the destination
   reassembles using (Source, Dest, Identification) as the flow key.
```

Because the Identification field is 32 bits wide (vs. IPv4's 16 bits), the wraparound problem that plagued IPv4 reassembly at high speeds is essentially eliminated.

## 6. Comparison to IPv4

| Property                | IPv4                          | IPv6                          |
|-------------------------|-------------------------------|-------------------------------|
| Address length          | 32 bits                       | 128 bits                      |
| Header length           | 20–60 bytes (variable)        | 40 bytes (fixed)              |
| Header checksum         | Yes (recomputed per hop)      | None (L2/L4 cover it)         |
| Fragmentation           | Routers may fragment in path  | Source only, via Fragment EH  |
| Options                 | In variable header             | In chained Extension Headers  |
| Broadcast               | Yes (limited + directed)      | None (multicast replaces)     |
| ARP                     | Broadcast-based ARP           | Multicast NDP via ICMPv6      |
| IGMP                    | IPv4 IGMPv2/v3                | IPv6 MLDv1/v2 (ICMPv6)        |
| Address auto-config     | DHCP only                      | SLAAC + DHCPv6                |
| IPSec                   | Optional add-on                | Spec-referenced (EH types)   |
| PMTU discovery          | RFC 1191                       | RFC 8201 (uses ICMPv6 PTB)    |
| Minimum MTU             | 576 bytes                      | 1280 bytes                    |

## 7. Transition Mechanisms

Operators cannot flag-day the Internet to IPv6; transition is a permanent state. The mechanisms fall into three families.

### 7.1 Dual-Stack (RFC 4213)

The simplest and most common: run both IPv4 and IPv6 on every interface, with the upper-layer protocol picking the address via DNS (AAAA preferred when both exist, modulated by Happy Eyeballs RFC 8305). The cost is operational duplication (two routing protocols, two address plans, two firewall rule-sets, two monitoring stacks). The benefit is no translation, no encapsulation, no single point of failure.

### 7.2 Tunnels — IPv6 in IPv4 (and vice versa)

```
   +---------+                                    +---------+
   | IPv6    |                                    | IPv6    |
   |  host  |                                    |  host   |
   +----+----+                                    +----+----+
        |                                              |
        | IPv6 packet encapsulated in IPv4 proto 41    |
        v                                              v
   +----+----+          IPv4 cloud           +-------+----+
   | 6to4   |  <=========================>   |  6to4    |
   | router |                              |  router  |
   +---------+                              +----------+
```

- **6to4 (RFC 3056)** — Encapsulates IPv6 in IPv4 proto 41. The IPv6 prefix is derived from the IPv4 public address: `2002:VVVV:VVVV::/48` where `VVVV:VVVV` is the IPv4 address. A single anycast relay at `192.88.99.1` (and `2002:c058:6301::`) routed packets back to native IPv6. 6to4 is **deprecated** — RFC 7526 specifically retired the anycast relay because of persistent operational failures and asymmetry.
- **6rd (RFC 5969)** — The carrier-grade evolution of 6to4. Uses the ISP's own IPv6 prefix (not the 2002::/16 space) and the ISP's own 6rd border relays inside its network. Widely deployed by French operator Free in 2007 and later by others.
- **Teredo (RFC 4380)** — Tunnels IPv6 in UDP so it can traverse NATs. Effectively deprecated in favour of native v6 and 464XLAT.
- **DS-Lite (RFC 6333)** — IPv4-in-IPv6-tunnel from CPE to a CGNAT; lets operators run IPv6-only access while still offering IPv4.

### 7.3 Translation — NAT64 and DNS64

```
   IPv6-only                +------------+              IPv4-only
   client   -- (AAAA req) ->|   DNS64    |-- A query -->  DNS server
                           | synthesises|<- A reply ---
                           |  AAAA rec  |
                           +------------+
                                |
                                v (synthesised AAAA -> NAT64 prefix)
   IPv6-only                 +------------+
   client  -- IPv6 packet ->|   NAT64    |--> IPv4 packet --> IPv4 server
                           |  translator|
                           +------------+
```

- **NAT64 (RFC 6146)** — Stateful IPv6-to-IPv4 translation. The IPv6-only client sends to a synthesised address in the well-known prefix `64:ff9b::/96` (RFC 6052), embedding the IPv4 destination's last 32 bits. The translator maps the IPv6 5-tuple onto an IPv4 5-tuple using the IPv4 address pool on the translator.
- **DNS64 (RFC 6147)** — When an IPv6-only client asks for AAAA of an IPv4-only server and only A records exist, DNS64 synthesises a AAAA record whose address is `64:ff9b::<IPv4 addr>`, routing the request into the NAT64.
- **464XLAT (RFC 6877)** — The wirelessly-deployed combination: client-side *CLAT* (stateless IPv4→IPv6 translation on the device) talks IPv4-in-IPv6 to a carrier-side *PLAT* (the NAT64 translator). Lets IPv4-only apps on IPv6-only mobile networks reach IPv4 services. This is what T-Mobile US, and most cellular operators today, ship.
- **NAT64 prefix discovery (RFC 7050)** — A client learns the NAT64 prefix by looking up `ipv4only.arpa.` over DNS; the returned AAAA records contain the operator's NAT64 prefix. This lets a device that has both CLAT and an IPv6-only transport auto-discover the right translation point.

### 7.4 Why dual-stack is the long-term reality

Each transition mechanism has a measurable failure mode: 6to4 has asymmetric routing; DS-Lite still needs IPv4 addresses on the translator; NAT64 breaks literal-IP and DNS-config-less apps (anything that does `socket("203.0.113.1")` and expects to succeed); 464XLAT needs a CLAT daemon. Operators therefore run dual-stack in the access layer for as long as any IPv4 is left, and use translation only where IPv4 has genuinely run out (mobile networks, new entrant operators).

## 8. Common Implementation Pitfalls

1. **Assuming `::` is empty** — `::` is the *unspecified* address; you cannot route to it. `::1` is loopback. `::ffff:0:0/96` is the IPv4-mapped address space used inside AF_INET6 sockets.
2. **Using ULA (`fd00::/8`) for global traffic** — ULAs are not in the global routing table; they will be black-holed if leaked.
3. **Forgetting link-local** — every IPv6 interface always has at least one `fe80::/10` address, regardless of GUA assignment. Tools that `getaddrinfo()` and only return GUAs miss the address used by NDP and many routing protocols.
4. **Disabling ICMPv6** — unlike IPv4 where ICMP is sometimes filtered, blocking ICMPv6 (notably Packet Too Big and NDP) **breaks the protocol**. RFC 4890 gives the precise list of what may and may not be filtered.
5. **Hardcoding `/64` assumptions in apps** — the GUA prefix length is `/64` for SLAAC; manually-configured prefixes may use longer, but `getaddrinfo` is always preferred over `inet_pton` parsing.

## 9. Summary

- IPv6 fixes IPv4's three biggest sins: address exhaustion, broadcast, and header-checksum per-hop cost.
- The fixed 40-byte header plus extension-header chain enables wire-speed forwarding and optional source routing / IPsec / fragmentation without bloating the fast path.
- Three address families (GUA, ULA, LL) plus multicast replace IPv4's unicast + broadcast + IGMP model with a cleaner scoped-multicast + MLD model.
- Transition is permanent: dual-stack where you can, tunnels where you must, translation where IPv4 has truly run out.

## 10. References

- RFC 8200 — Internet Protocol, Version 6 (IPv6) Specification. https://www.rfc-editor.org/rfc/rfc8200
- RFC 4291 — IPv6 Addressing Architecture. https://www.rfc-editor.org/rfc/rfc4291
- RFC 4861 — Neighbor Discovery for IP version 6 (IPv6). https://www.rfc-editor.org/rfc/rfc4861
- RFC 7050 — Discovery of the IPv6 Prefix Used for IPv6 Address Synthesis. https://www.rfc-editor.org/rfc/rfc7050
- RFC 6437 — IPv6 Flow Label Specification. https://www.rfc-editor.org/rfc/rfc6437
- RFC 8201 — Path MTU Discovery. https://www.rfc-editor.org/rfc/rfc8201
- RFC 3056 — Connection of IPv6 Domains via IPv4 Clouds (6to4). https://www.rfc-editor.org/rfc/rfc3056
- RFC 5969 — IPv6 Rapid Deployment on IPv4 Infrastructures (6rd). https://www.rfc-editor.org/rfc/rfc5969
- RFC 6146 — Stateful NAT64. https://www.rfc-editor.org/rfc/rfc6146
- RFC 6147 — DNS64. https://www.rfc-editor.org/rfc/rfc6147
- RFC 6877 — 464XLAT. https://www.rfc-editor.org/rfc/rfc6877
- RFC 7872 — Observations on the Dropping of Packets with IPv6 Extension Headers. https://www.rfc-editor.org/rfc/rfc7872
- RFC 7112 — Implications of Oversized IPv6 Header Chains. https://www.rfc-editor.org/rfc/rfc7112

## Cross-References

- [IPv6 (overview)](ipv6.md) — high-level concepts and address types
- [ICMPv6 & NDP](icmpv6-ndp.md) — the control-plane protocol that replaces ARP
- [SLAAC & DHCPv6](slaac-dhcpv6.md) — how a host gets its addresses
- [NAT66](nat66.md) — when and why translation still happens in IPv6
- [NAT](nat.md) — IPv4 NAT, for comparison
