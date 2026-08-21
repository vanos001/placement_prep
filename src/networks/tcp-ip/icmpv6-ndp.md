# ICMPv6 and the Neighbor Discovery Protocol

> *"In IPv4, ICMP was the polite protocol that reported errors and was often firewalled. In IPv6, ICMPv6 is the protocol that runs the network — block it and your interface cannot even learn a MAC address."*

## 1. What ICMPv6 Replaces

In IPv4, the network layer has *three* separate control-plane mechanisms:

1. **ICMP** (RFC 792) for error reporting and diagnostics.
2. **ARP** (RFC 826) for mapping an IPv4 address to a Layer-2 MAC on a multi-access link.
3. **IGMP** (RFC 3376) for hosts to tell a multicast router they want a group's traffic.

In IPv6, all three collapse into **ICMPv6** (RFC 4443), extended by **NDP** (RFC 4861) for the on-link control plane and **MLD** (RFC 3810) for multicast group management. There is no separate ARP and no separate IGMP — both are ICMPv6 message types. This means an IPv6 firewall that drops all ICMPv6 *will break basic reachability* — Neighbor Solicitation will fail, address configuration will hang, and PMTU discovery will collapse into black-holes. RFC 4890 spells out precisely what may and may not be filtered.

## 2. ICMPv6 Message Format

Every ICMPv6 message has the same 4-byte fixed header followed by a message-body whose layout depends on the type.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    Type (8)   |    Code (8)   |          Checksum (16)        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          Message Body                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

The checksum is computed the same way as for ICMPv4, except that the *pseudo-header* includes source IP, destination IP, upper-layer length, and a "next header = 58" identifier (RFC 4443 §2.2). This is mandatory — there is no IPv4-style fallback where the IP-layer checksum catches errors.

### The error message family (Type < 127) and the informational family (Type ≥ 128)

Per RFC 4443 §3.1, the high bit of Type partitions the namespace:

- `Type < 128` → error messages; destination host emits them in response to a packet it cannot deliver or cannot parse. Source must NOT generate a new error in response to an error message (to avoid storms).
- `Type ≥ 128` → informational messages, used by NDP, MLD, Echo, and the multicast-routing control plane.

### The canonical ICMPv6 error messages

| Type | Code range | Message | What triggers it |
|------|------------|---------|------------------|
| 1    | 0–6        | Destination Unreachable            | No route, admin-prohibited, address-unreachable, port-unreachable, source-address-failed-policy, reject-route-to-dest. |
| 2    | 0          | Packet Too Big                    | A router's outgoing MTU < packet size. RFC 8201 PMTUD. Contains the offending MTU in the body. |
| 3    | 0–1        | Time Exceeded                     | Hop Limit reached 0 (code 0) or reassembly timeout (code 1). Used by traceroute. |
| 4    | 0–3        | Parameter Problem                | Erroneous header field (code 0), unrecognised Next-Header (code 1), unrecognised option (code 2), impossible to process extension headers (code 3, RFC 7112). |
| 100, 101, 200, 201 | —     | Experimental / reserved | Per RFC 4443 §10. |
| 127  | —          | Reserved extension error messages | Future use; no current code. |
| 255  | —          | Reserved extension info messages  | Future use; no current code. |

### The informational messages (Type ≥ 128)

| Type | Code | Message | Used by |
|------|------|---------|---------|
| 128  | 0    | Echo Request              | `ping6` |
| 129  | 0    | Echo Reply                | `ping6` |
| 130  | 0    | Multicast Listener Query  | MLDv1 (RFC 2710) |
| 131  | 0    | Multicast Listener Report | MLDv1 |
| 132  | 0    | Multicast Listener Done   | MLDv1 |
| 133  | 0    | Router Solicitation (RS)  | NDP |
| 134  | 0    | Router Advertisement (RA) | NDP |
| 135  | 0    | Neighbor Solicitation (NS)| NDP (replaces ARP request) |
| 136  | 0    | Neighbor Advertisement (NA)| NDP (replaces ARP reply) |
| 137  | 0    | Redirect                  | NDP |
| 143  | 0    | MLDv2 Report              | MLDv2 (RFC 3810) — like IGMPv3 |

A subtlety: every ICMPv6 Echo Request that a router sees is itself an upper-layer payload, so the router forwards it like any other packet. ICMPv6 errors, by contrast, are emitted by routers and endpoints, never by middleboxes that simply forward — a NAT box that returns "destination unreachable" for a packet it cannot translate is exercising behaviour beyond RFC 4443 (and most NAT64 boxes deliberately suppress unreachable for translated flows).

## 3. The Neighbor Discovery Protocol (NDP)

NDP is defined in RFC 4861 (and used by RFC 4862 for SLAAC). It runs entirely over ICMPv6 and replaces ARP, IPv4 ICMP Router Discovery (RFC 1256), and IPv4 ICMP Redirect. Five message types do all the work:

| Message | Type | Sent to | Purpose |
|---------|------|---------|---------|
| Router Solicitation    | 133 | ff02::2 (all routers)  | "I just came up, please send an RA now" |
| Router Advertisement  | 134 | ff02::1 (all nodes) or unicast | Periodically or in response to RS — carries prefixes, MTU, hop limit, routes, lifetime |
| Neighbor Solicitation | 135 | Solicited-node multicast of target | "What is your L2 address?" OR "Are you using this address?" (DAD) |
| Neighbor Advertisement| 136 | unicast to NS sender   | "Here is my MAC" OR "yes, that address is mine" |
| Redirect              | 137 | unicast to originator  | "Use this better next-hop for that destination" |

### 3.1 Neighbor Solicitation — the multicast ARP replacement

In IPv4, ARP broadcasts "who has 192.168.1.5?" to *every* host on the LAN. In IPv6, NS uses solicited-node multicast so only the target host gets the interrupt:

```
   Host A wants to send to 2001:db8::5
   -------------------------------------------------
   Step 1: compute solicited-node multicast:
      target unicast = 2001:db8:0000:0000:0000:0000:0000:0005
      low 24 bits   = 00:00:05
      solicited-node = ff02::1:ff00:5
   Step 2: Ethernet dst = 33:33:ff:00:00:05 (RFC 2464)
   Step 3: send NS (ICMPv6 type 135)
            src  = A's link-local (fe80::a)
            dst  = ff02::1:ff00:5
            body = Target Address = 2001:db8::5
            option = Source Link-Layer Address = A's MAC
   Step 4: target replies with NA (type 136) unicast to A
            body = Target Address = 2001:db8::5
            option = Target Link-Layer Address = B's MAC
            flags = S=1 (solicited), O=1 (override)
   Step 5: A caches the (IP, MAC) entry in its neighbor cache
```

Three things to note vs. ARP:

- **No broadcast** — only the solicited-node multicast group is hit, which on a modern switch is snooped (via MLD snooping, RFC 4541) so packets go to exactly one port.
- **Source-link-layer option in NS** — the request itself carries A's MAC, saving an extra round-trip. ARP required a separate request/response.
- **No gratuitous ARP** — DAD uses NS to the solicited-node multicast of the address being tested; if anyone replies NA, the address is in use.

### 3.2 Neighbor Unreachability Detection (NUD)

ARP entries time out blindly (typically 4 hours). IPv6's neighbor cache does active reachability confirmation via NUD (RFC 4861 §7.3). A host in REACHABLE state transitions through STALE → DELAY → PROBE → REACHABLE/UNREACHABLE:

```
                     no traffic for 30s
   REACHABLE  ------------------------>  STALE
       ^                                   |
       |                                   | traffic sent
       |                                   v
       |                               DELAY (5s)
       |                                   | no confirmation
       |                                   v
       +-------NA confirms------       PROBE (3 unicast NS, 1s apart)
                                          |
                                          | no reply
                                          v
                                      UNREACHABLE
```

NUD avoids the "stale ARP entry keeps sending to a dead MAC" problem because the cache actively probes before declaring a neighbor gone — a much cleaner failure mode than ARP's silent timeout.

### 3.3 Router Discovery and the RA message

When a host boots, it sends 3 RS messages (RFC 4861 §6.3.7) spaced 4 seconds apart. Routers on the link answer with RA. An RA contains:

- Cur Hop Limit (default 64) — every host's hop-limit starts here.
- M/O/A flags: **M**anaged (use DHCPv6 for address), **O**ther-config (DHCPv6 for non-address config), **A**utonomous (use SLAAC for the included prefix).
- Default Router Lifetime (default 1800 s) — used as the lifetime for the default route.
- Reachable Time and Retrans Timer for NUD.
- Prefix Information options (one per advertised prefix) carrying the prefix, valid-lifetime, preferred-lifetime, and on-link/L/A flags.
- Optionally, MTU (so a mixed-MTU link agrees on a value), RDNSS (RFC 8106 recursive DNS server list), and routes (RFC 4191 for default-router preferences).

Routers also emit unsolicited RAs periodically (default interval = 200 s, jittered ±100 ms) so hosts that missed the RS response still learn the prefixes.

### 3.4 Redirect

When a host forwards a packet to a router that turns out to be on the same link as a *better* next-hop, the router sends an ICMPv6 Redirect to tell the host to use the better next-hop directly. This is identical in spirit to IPv4 ICMP Redirect (RFC 792) but happens via ICMPv6 type 137, and carries both the target next-hop's L2 address (so no follow-up NS is needed) and the destination prefix that should be redirected.

## 4. Duplicate Address Detection (DAD)

DAD is the SLAAC equivalent of IPv4's gratuitous ARP — a host must verify that nobody else is using an address it intends to use. DAD is defined in RFC 4862 §5.4 and is implemented as a single NS:

```
   Host H wants to claim 2001:db8::1
   -------------------------------------------------
   1. H sends NS:
        src  = ::        (unspecified — H doesn't have an address yet)
        dst  = ff02::1:ff00:1  (solicited-node for ::1 ... wait, for ::2001:db8::1)
        body = Target Address = 2001:db8::1
   2. If no host on the link is using 2001:db8::1:
        nobody replies within RetransTimer (default 1 s)
        H declares the address TENTATIVE → PREFERRED
   3. If another host K is already using 2001:db8::1:
        K sees the NS (joined to that solicited-node group)
        K replies NA:
            src  = 2001:db8::1
            dst  = ff02::1 (or unicast to H)
            body = Target Address = 2001:db8::1
        H sees the NA, declares a DUPLICATE, gives up the address
```

DAD is mandatory for *every* IPv6 address assignment, including link-local `fe80::/10`. A failure of DAD is a real outage mode on links with broken multicast (e.g., certain Wi-Fi APs that mishandle multicast).

### Optimistic DAD and DAD extensions

- **Optimistic DAD (RFC 4429)** — A host may use the address *during* DAD for established sessions, treating it as OPTIMISTIC rather than TENTATIVE, which avoids the multi-second delay that hurts short-lived TCP connections. The cost: if a duplicate is detected, the host has already emitted traffic from a duplicate address, and must reset its connections.
- **CGA and SEND (RFC 3971)** — Cryptographically Generated Addresses bind the interface ID to a public key, preventing a malicious neighbour from claiming an address via DAD. SEND is largely undeployed; operators use RA-Guard (RFC 6105) and RA nonce options instead.

## 5. MLD — Multicast Listener Discovery

MLD is IPv6's replacement for IGMP. Three versions, mirroring IGMP:

| MLD version | RFC | Equivalent IGMP | What it adds |
|-------------|-----|-----------------|--------------|
| MLDv1 | 2710 | IGMPv2 | Basic join/leave with `Done` (type 132) |
| MLDv2 | 3810 | IGMPv3 | Source-specific join (SSM) — `ff3x::/32` groups, "include" / "exclude" source lists |
| MLD Querier | 3590 (All-Routers) | — | Defines which router queries on a link |

MLD messages are themselves *multicast ICMPv6*. A host joining a group sends an MLDv2 Report to `ff02::16` (all-MLDv2-listeners), with a body listing every (group, source-list) it wants. Switches that snoop MLD (RFC 4541 / RFC 6636) prune multicast to ports that have actually joined — without snooping, IPv6 multicast floods every port, which can drown a wireless link with NS messages.

## 6. ICMPv6 vs ICMPv4 — operational differences

| Behaviour                       | ICMPv4                         | ICMPv6 |
|---------------------------------|--------------------------------|---------|
| Echo Request/Reply              | Yes, types 8/0                 | Yes, types 128/129 |
| Destination Unreachable for MTU | "Fragmentation Needed" (3, 4) | "Packet Too Big" (type 2, single code 0) — must carry the offending MTU |
| Traceroute mechanism            | TTL=0 → Time Exceeded          | Hop Limit=0 → Time Exceeded (code 0) |
| In-flight checksum              | Has IPv4 header checksum       | Only L4 + pseudo-header — mandatory |
| Filtering                       | Often blocked by routers; harmless | Must not be blocked, would break PMTUD, NDP, MLD |
| Multicast control plane         | IGMP (separate protocol, proto 2) | MLD (ICMPv6 types 130/131/132/143) |
| ARP                             | Separate protocol (Ethernet 0x0806) | NDP (ICMPv6 types 135/136/137) |

The single most-violated rule in IPv6 firewalls is **"ICMPv6 is unfilterable"**. RFC 4890 §4.4.1 explicitly says PTB, Destination Unreachable code 0, Time Exceeded, and Parameter Problem *must* be allowed inbound; all of NS, NA, RS, RA, and Redirect *must* be allowed on ingress to a link on which hosts autoconfigure. Many enterprises drop ICMPv6 anyway — and then wonder why their IPv6 traffic suffers periodic stalls (because PTB is being silently dropped and TCP can never discover the path MTU).

## 7. Worked Example: a host joins a link

Trace the actual ICMPv6 exchange when a laptop boots on a SLAAC-configured Ethernet:

```
t=0.000 s  Host up; assigns tentative fe80::1a2b:3cff:fe45:5678 (EUI-64)
t=0.000 s  Host sends DAD NS:  src=::, dst=ff02::1:ff45:5678, target=fe80::1a2b:3cff:fe45:5678
t=1.000 s  No NA reply → DAD succeeds → link-local becomes PREFERRED
t=1.001 s  Host sends 3× RS:     src=fe80::1a2b.../64, dst=ff02::2, every 4 s until RA arrives
t=1.250 s  Router sends RA:      src=fe80::abcd::1, dst=ff02::1
              Prefix=2001:db8:0:1::/64, valid=86400s, preferred=14400s, A=1, L=1
              MTU=1500, hop-limit=64, default-router-lifetime=1800s
              RDNSS=2001:db8:0:1::53 (RFC 8106)
t=1.251 s  Host assigns tentative 2001:db8:0:1:1a2b:3cff:fe45:5678
t=1.251 s  Host DADs that GUA via solicited-node NS — same flow as before
t=2.251 s  GUA becomes PREFERRED → host can send packets
t=2.300 s  Host has DNS, default route, source address → can fetch https://example.com/
              getaddrinfo() returns 2001:db8:0:1:1a2b:... (RFC 6724 source-address selection)
              ARP-equivalent NS/NA happens only when actually sending the SYN
t=2.305 s  Host NSs for the gateway MAC at solicited-node for fe80::abcd::1
t=2.310 s  Router NAs with its MAC → host caches it → TCP SYN goes out
```

The complete on-link control plane is roughly 6 packets — three for DAD on the link-local, three for SLAAC + gateway MAC resolution. Compare with IPv4 DHCP DORA + ARP request/reply + ICMP-Router-Discovery (if enabled): roughly the same, but with three protocols instead of one.

## 8. Operational Pitfalls

1. **Filtering ICMPv6 Packet Too Big** silently breaks TCP performance — connections stall after their first window-size burst because they cannot shrink their segment size. Always allow ICMPv6 type 2 code 0 inbound.
2. **Disabling RAs on a link** to "force DHCPv6" — Android does not implement DHCPv6 address assignment, so an Android device on an RA-less link will end up with only a link-local and no reachability. Use the M-flag and SLAAC coexistence instead.
3. **Not joining solicited-node multicast on a router** — a router that forwards traffic destined to itself must join the solicited-node group for each of its addresses, otherwise NDP fails and packets to it cannot resolve.
4. **Treating NUD STALE as dead** — STALE means "we haven't confirmed recently", not "unreachable". Killing the cache entry on entering STALE breaks long-idle TCP connections.

## 9. Summary

- ICMPv6 collapses ICMP, ARP and IGMP into one protocol with one checksum model.
- NDP (RS/RA/NS/NA/Redirect) is the on-link control plane; MLD is the multicast control plane; both are ICMPv6.
- DAD is a one-packet-per-address safety check; failures of DAD reliably indicate broken multicast L2.
- Filtering ICMPv6 *will* break your IPv6 network — the protocol was designed assuming ICMPv6 travels unmodified end-to-end.

## 10. References

- RFC 4443 — Specification of the Internet Control Message Protocol (ICMPv6). https://www.rfc-editor.org/rfc/rfc4443
- RFC 4861 — Neighbor Discovery for IP version 6 (IPv6). https://www.rfc-editor.org/rfc/rfc4861
- RFC 4862 — IPv6 Stateless Address Autoconfiguration. https://www.rfc-editor.org/rfc/rfc4862
- RFC 4890 — Recommendations for Filtering ICMPv6 Messages in Firewalls. https://www.rfc-editor.org/rfc/rfc4890
- RFC 2710 — Multicast Listener Discovery (MLD) for IPv6. https://www.rfc-editor.org/rfc/rfc2710
- RFC 3810 — Multicast Listener Discovery Version 2 (MLDv2) for IPv6. https://www.rfc-editor.org/rfc/rfc3810
- RFC 4429 — Optimistic Duplicate Address Detection (DAD) for IPv6. https://www.rfc-editor.org/rfc/rfc4429
- RFC 3971 — SEcure Neighbor Discovery (SEND). https://www.rfc-editor.org/rfc/rfc3971
- RFC 7559 — Making DHCPv6-Only Networks Reliable. https://www.rfc-editor.org/rfc/rfc7559
- RFC 8106 — IPv6 Router Advertisement Options for DNS Configuration. https://www.rfc-editor.org/rfc/rfc8106
- RFC 4191 — Default Router Preferences and More-Specific Routes. https://www.rfc-editor.org/rfc/rfc4191

## Cross-References

- [IPv6 Internals](ipv6-internals.md) — header, extension headers, addressing
- [SLAAC & DHCPv6](slaac-dhcpv6.md) — what the host does with the RA it just received
- [IPv6 (overview)](ipv6.md) — high-level concepts
- [ICMP](icmp.md) — IPv4 ICMP, for comparison
- [ARP](arp.md) — what NDP replaced
