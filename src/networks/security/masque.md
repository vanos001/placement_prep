# MASQUE: Proxying IP over HTTP/3

Most tunnels invent a protocol and then fight the Internet to carry
it: IPsec needs ESP and IKE, WireGuard has its own UDP message format.
MASQUE takes the opposite bet: make the tunnel look like ordinary
HTTP/3 on UDP port 443, and let a standard reverse proxy -- the kind
already running at every CDN edge -- forward TCP connections, UDP
flows, or IP packets. This page covers the protocol family, the
CONNECT machinery, the unmerged draft that makes proxies QUIC-aware,
and an honest overhead comparison; tunneling fundamentals are in
[vpn.md](./vpn.md), the QUIC layer in
[../http/quic-internals.md](../http/quic-internals.md) and
[../http/http3.md](../http/http3.md).

## 1. A Protocol Family, Not a Protocol

"MASQUE" names an IETF working group (expanded on the datatracker as
*Multiplexed Application Substrate over QUIC Encryption*); its output
is a stack of documents:

| Document | Status | What it defines |
| ------------------------------------ | ------------------------------ | ---------------------------------------------- |
| RFC 9110 / 9114 | RFC | Plain `CONNECT`; usable over HTTP/3 |
| RFC 8441 / 9220 | RFC (2018 / 2022) | Extended CONNECT (`:protocol`) for HTTP/2 and HTTP/3 |
| RFC 9297 | RFC (Aug 2022) | HTTP Datagrams + the capsule protocol |
| RFC 9221 | RFC (Mar 2022) | QUIC DATAGRAM frame (types 0x30-0x31) |
| RFC 9298 | RFC (Aug 2022) | `CONNECT-UDP` -- proxy UDP over HTTP |
| RFC 9484 | RFC (Oct 2023) | `CONNECT-IP` -- proxy IP packets over HTTP |
| draft-ietf-masque-quic-proxy | Internet-Draft (-07, Oct 2025) | QUIC-aware proxying (CID reuse / FlowID) |
| draft-ietf-masque-connect-ip-dns, -connect-ethernet | Internet-Drafts | DNS/PREF64 config; Ethernet proxying |

Common misquote: RFC 9298 defines *CONNECT-UDP*, not "the MASQUE
protocol" -- citing 9298 alone as all of MASQUE is like calling
TLS 1.3 "HTTPS".

## 2. Why Tunnel Over QUIC At All

Four motivations, in the order the working group weighs them:
**standard infrastructure** -- a MASQUE proxy is an HTTP server behind
ordinary load balancers, CDN edges, certs, and web tooling, with no
exotic protocol for middleboxes to fear; **NAT reality** -- each inner
flow sent as its own UDP socket creates its own NAT binding (per-flow
state, CGNAT port exhaustion), while MASQUE multiplexes every proxied
flow over **one** outer UDP 4-tuple: one binding, one migration story;
**mobility** -- inner packets ride QUIC, so a WiFi-to-cellular IP
change survives via connection IDs, no IKE MOBIKE, no re-handshake;
and **congestion control for free** -- the tunnel inherits the QUIC
controller instead of appearing as opaque loss. Honest costs: all
inner flows share one congestion window; per-packet overhead is *not*
smaller than WireGuard or ESP (Section 6); and stream-based
forwarding of TCP re-creates TCP-in-TCP meltdown.

## 3. The Method Stack: Extended CONNECT, Capsules, Datagrams

Plain `CONNECT` (RFC 9110 Section 9.3.6) proxies TCP by authority and
works over HTTP/3 (RFC 9114); MASQUE starts where TCP ends.
**Extended CONNECT** (RFC 8441 for HTTP/2, RFC 9220 for HTTP/3) adds
a `:protocol` pseudo-header turning one stream into a negotiated
sub-protocol; CONNECT-UDP (RFC 9298) uses `:protocol: connect-udp`
against a URI template:

```text
CONNECT-UDP request (RFC 9298):
  :method   = CONNECT
  :protocol = connect-udp
  :scheme   = https
  :path     = /.well-known/masque/udp/192.0.2.6/443/
  :authority = proxy.example
  -> 2xx; stream becomes a capsule channel; per-packet traffic moves
     to HTTP Datagrams (RFC 9297)
```

An **HTTP datagram** (RFC 9297) is addressed by a *quarter stream ID*
(its CONNECT stream / 4) plus a *context ID* (0 = proxied payload;
non-zero = extension channels). When the QUIC connection negotiated
`max_datagram_frame_size` (RFC 9221) each HTTP datagram ships in one
QUIC DATAGRAM frame; otherwise it falls back to a capsule on the
CONNECT stream.

```text
   Inner UDP datagram (e.g. QUIC client -> origin, via proxy)
      |  inner UDP header + payload, untouched by the proxy
      v
   HTTP Datagram   [ quarter-stream-ID | context-ID=0 | payload ]
      v
   QUIC DATAGRAM frame  [ type 0x30/0x31 | length | ^ HTTP datagram ]
      v
   QUIC 1-RTT packet    [ flags | DCID | packet no. | AEAD-protected ]
      v
   UDP  +  IP           [ 8 + 20 outer bytes: the only plaintext routing ]
```

The proxy reads only the outer IP/UDP plus its own QUIC layer; inner
bytes are ciphertext to it -- but it *is* a man-in-the-middle by
design (Section 8).

## 4. CONNECT-IP: A VPN-Shaped Interface

RFC 9484 (October 2023, updates 9298) generalises the machinery from
UDP datagrams to IP packets: `:protocol: connect-ip`,
`/.well-known/masque/ip/{target}/{ipproto}/`, or `*/*` for "proxy my
whole IP stack". Two capsules negotiate topology: `ADDRESS_ASSIGN`
hands the client an address/prefix (the "you are now 100.64.x.x"
moment of a VPN session) and `ROUTE_ADVERTISEMENT` says which prefixes
the proxy will carry.

Two forwarding modes, and the choice matters: **datagram mode** (QUIC
DATAGRAM frames) is per-packet, unreliable, and head-of-line-blocking
free -- right for UDP inner flows and for TCP flows whose reliability
already belongs to the inner endpoints, i.e. the WireGuard-shaped
mode; **stream mode** puts inner packets on QUIC streams, where
TCP-in-TCP stacks loss recovery on loss recovery (meltdown) and
head-of-line blocking serialises flows. When would CONNECT-IP hurt?
Stream mode carrying TCP. Cloudflare's WARP MASQUE mode is
CONNECT-IP based (see the `usque` reimplementation).

## 5. QUIC-Aware Proxying and FlowID

A plain MASQUE proxy is QUIC-oblivious: inner QUIC connections are
just ciphertext on datagrams. draft-ietf-masque-quic-proxy
("QUIC-Aware Proxying Using HTTP") makes the proxy QUIC-literate: the
client tells the proxy the original destination's QUIC connection IDs,
and the proxy re-uses those IDs on its own outbound connection, so
inner packets need no extra per-packet framing -- the original CID
*is* the flow identifier (informally, FlowID). Cited benefits: lower
per-packet overhead than capsule framing, and many inner QUIC
connections coalesced onto one UDP 4-tuple with unambiguous demux --
less NAT state, smoother migration and path validation. Status
honesty: still an **Internet-Draft** (-07, October 2025), not an RFC,
as of this writing (Aug 2026); CONNECT-IP DNS/PREF64 and
CONNECT-ETHERNET are unmerged too.

## 6. Tunnel Overhead in Numbers

Per-packet overhead decides how much of a small packet (DNS, VoIP,
ACKs) is payload versus transport. The model sums per-tunnel
constants (see the breakdown column); RFC-derivable values are cited
in the text, "typ" marks deployment-typical choices:

- Outer IPv4 20 (RFC 791) + UDP 8 (RFC 768).
- QUIC short header 12 typ (1 flags + 8-byte DCID + 3-byte packet
  number; RFC 9000 allows DCID 0-20, PN 1-4) + 16-byte AEAD tag
  (RFC 9001 AES-128-GCM).
- DATAGRAM frame 5 (RFC 9221 type 0x30/0x31; RFC 9297
  quarter-stream-ID / context-ID / length).
- WireGuard data message 32 = 16-byte header + 16-byte Poly1305 tag:
  60 bytes over IPv4, 80 over IPv6, per its whitepaper.
- ESP AES-128-GCM (RFC 4106): SPI 4 + Seq 4 + IV 8 + ICV 16 + ~4
  trailer/pad + new outer IPv4 header in tunnel mode = 56.
- TLS-VPN: TCP 20 + TLS 1.3 record header 5 + tag 16 (implicit
  nonce). Static model -- a floor, not a benchmark.

```python
#!/usr/bin/env python3
"""Tunnel overhead model: MASQUE vs WireGuard vs IPsec vs TLS-VPN.
Static per-packet model; constants and citations in the text above.
"""

SIZES = [64, 200, 576, 1200, 1400, 1440]  # ACK/DNS, VoIP, min-MTU, QUIC, MSS

TUNNELS = [
    ("MASQUE (QUIC dgram)",   61, "ip20 + udp8 + quic12 + tag16 + dgframe5"),
    ("WireGuard (IPv4)",      60, "ip20 + udp8 + wg32 (hdr16 + tag16)"),
    ("IPsec ESP-GCM tunnel",  56, "ip20 + esp36 (spiseq8 + IV8 + ICV16 + pad4)"),
    ("TLS-VPN over TCP",      61, "ip20 + tcp20 + tlshdr5 + tag16"),
]

print("Per-packet overhead model (outer IPv4, no options, no extra padding)")
print("  name                      ohd  breakdown")
for name, ohd, note in TUNNELS:
    print("  %-24s%4d  %s" % (name, ohd, note))

print()
print("  efficiency% = inner / (inner + overhead), by inner packet size:")
print("  %-24s%s" % ("tunnel (ohd)", "".join("%8d" % s for s in SIZES)))
for name, ohd, _ in TUNNELS:
    cells = "".join("%8.1f" % (100.0 * s / (s + ohd)) for s in SIZES)
    print("  %-24s%s" % ("%s (%d)" % (name, ohd), cells))
```

Real output (run twice; byte-identical re-runs):

```text
Per-packet overhead model (outer IPv4, no options, no extra padding)
  name                      ohd  breakdown
  MASQUE (QUIC dgram)       61  ip20 + udp8 + quic12 + tag16 + dgframe5
  WireGuard (IPv4)          60  ip20 + udp8 + wg32 (hdr16 + tag16)
  IPsec ESP-GCM tunnel      56  ip20 + esp36 (spiseq8 + IV8 + ICV16 + pad4)
  TLS-VPN over TCP          61  ip20 + tcp20 + tlshdr5 + tag16

  efficiency% = inner / (inner + overhead), by inner packet size:
  tunnel (ohd)                  64     200     576    1200    1400    1440
  MASQUE (QUIC dgram) (61)    51.2    76.6    90.4    95.2    95.8    95.9
  WireGuard (IPv4) (60)       51.6    76.9    90.6    95.2    95.9    96.0
  IPsec ESP-GCM tunnel (56)    53.3    78.1    91.1    95.5    96.2    96.3
  TLS-VPN over TCP (61)       51.2    76.6    90.4    95.2    95.8    95.9
```

Reading: at MSS-sized packets all four tunnels land within ~1% of each
other (95.8-96.3%) -- MASQUE's per-packet overhead is *not* a selling
point. What changes is where the bytes go: MASQUE spends roughly one
compressed request/response pair (QPACK amortises the repeated
well-known template) per proxied *flow*, while WireGuard's overhead is
purely per-*packet*. At 64-byte inner packets every design wastes
about half the wire; every row leaves ~1440 clean inner bytes on a
1500-byte path MTU.

## 7. Proxying vs VPN: The Honest Comparison

| | MASQUE | WireGuard | IPsec (IKEv2/ESP) | TLS-VPN (OpenVPN-style) |
| --- | --- | --- | --- | --- |
| Outer transport | QUIC / UDP 443 | UDP (any port) | IP proto 50/51, UDP 4500 | TCP or UDP |
| Crypto | TLS 1.3 (via QUIC) | Noise IK, ChaCha20 | IKEv2 + ESP suites | TLS records |
| Congestion control | QUIC, shared window | built-in | n/a (IP layer) | TCP: yes; UDP: app |
| HoL blocking risk | no (datagram mode) | no | no | yes over TCP |
| NAT / middlebox story | looks like HTTP/3 | one UDP flow, fine | NAT-T needed | fine (TCP) |
| Mobility on IP change | QUIC connection IDs | roaming allowed | MOBIKE, clunky | reconnect |
| Config surface | HTTP proxy + cert | one keypair | policy + IKE identity | PKI + config |
| Std proxy semantics | yes (CONNECT family) | no | no | no |

The framing that survives cross-examination: MASQUE is a **proxy**
protocol wearing VPN clothes -- the proxy terminates its own TLS and
*can* inspect what you send, so privacy from the operator comes from
protocol design (two-hop relays, oblivious DNS), not the tunnel,
whereas WireGuard and IPsec protect you *from* the tunnel endpoint.
Pick MASQUE when deployment realities dominate (browser clients, CDN
relays, mobile migration); WireGuard for lean always-on site tunnels;
IPsec where policy frameworks exist. The TLS layer behind all of
these is in [tls-deep-dive.md](./tls-deep-dive.md).

## 8. Who Actually Runs This

- **Chrome -- IP Protection.** Chromium's IP Protection (Incognito and
  later phases) forwards third-party traffic through a two-hop
  CONNECT/CONNECT-UDP proxy chain (Google first hop, external CDN
  second); the Chromium tracker for generic QUIC-over-MASQUE support
  says it works "only for IP Protection" -- no general user-facing
  MASQUE proxy option as of Aug 2026.
- **Apple -- iCloud Private Relay.** Traffic rides two relays with
  ODoH for DNS; Cloudflare's operator documentation confirms MASQUE is
  the relay technology; Apple exposes the plumbing as "network relay"
  in its Network framework.
- **Cloudflare -- WARP.** Consumer WARP shipped MASQUE in 2023 (iOS
  beta first), Zero Trust WARP made it selectable in 2024, and by 2025
  WARP's MASQUE tunnel runs post-quantum hybrid key exchange; the
  MASQUE mode is CONNECT-IP (see the `usque` reimplementation).

## 9. Interview Questions

- **Why not just run a WireGuard-style VPN over QUIC?** You can, but
  MASQUE rides HTTP infrastructure (LBs, certs, CDN edges), gets
  per-flow HTTP semantics (auth, routing, telemetry), and survives NAT
  with one binding; WireGuard wins per-packet overhead and in-kernel
  simplicity.
- **Where do inner flows' congestion windows live?** One QUIC
  connection = one shared window in datagram mode; stream mode adds
  QUIC flow control per stream, and TCP-in-stream re-adds TCP-in-TCP
  coupling.
- **Is FlowID standardised?** No -- draft-ietf-masque-quic-proxy is
  still an Internet-Draft (-07, Oct 2025). Say so explicitly.
- **Why would a proxy re-use original connection IDs?** The outer
  packet's DCID identifies the inner flow: many inner QUIC connections
  share one UDP 4-tuple with unambiguous demux and no per-packet proxy
  header, while inner migration keeps working.

## References

1. RFC 9298, *Proxying UDP in HTTP* (CONNECT-UDP) -- <https://www.rfc-editor.org/rfc/rfc9298.html>
2. RFC 9484, *Proxying IP in HTTP* (CONNECT-IP; updates 9298) -- <https://www.rfc-editor.org/rfc/rfc9484.html>
3. RFC 9221, *An Unreliable Datagram Extension to QUIC* -- <https://www.rfc-editor.org/rfc/rfc9221.html>
4. RFC 9297, *HTTP Datagrams and the Capsule Protocol* -- <https://www.rfc-editor.org/rfc/rfc9297.html>
5. IETF MASQUE working group -- <https://datatracker.ietf.org/wg/masque/about/>
6. draft-ietf-masque-quic-proxy, *QUIC-Aware Proxying Using HTTP* (I-D) -- <https://datatracker.ietf.org/doc/draft-ietf-masque-quic-proxy/>
7. Cloudflare, *Donning a MASQUE: building a new protocol into WARP* (2023) -- <https://blog.cloudflare.com/masque-building-a-new-protocol-into-cloudflare-warp/>
8. Cloudflare, *Zero Trust WARP: tunneling with a MASQUE* (2024) -- <https://blog.cloudflare.com/zero-trust-warp-with-a-masque/>
9. Chromium issue 40252810, *Support QUIC over QUIC proxies* -- <https://issues.chromium.org/issues/40252810>
10. GoogleChrome/ip-protection explainer -- <https://github.com/GoogleChrome/ip-protection>
11. Kuhlewind, Carlander-Reuterfelt, Ihlar, Westerlund, *Evaluation of QUIC-based MASQUE proxying*, EPIQ@CoNEXT 2021, doi 10.1145/3488660.3493806 -- <https://dl.acm.org/doi/10.1145/3488660.3493806>
