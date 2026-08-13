# Chunk F Audit — Networks

**Scope:** src/networks/* (skipping already-fixed: tls-deep-dive, ospf, flow-control, timers, states, four-way, bbr)
**Files audited:** 89
**Files clean:** 71
**Total findings:** 18

**Severity breakdown:** HIGH: 6, MEDIUM: 11, LOW: 2 (Note: two findings appear in two severity sections because they include both HIGH and MEDIUM aspects; counted by unique issue.)

## Findings

### HIGH severity

#### src/networks/tcp/header.md:53-62
- **Wrong text:** The TCP flags table lists bit numbers as CWR=8, ECE=7, URG=6, ACK=5, PSH=4, RST=3, SYN=2, FIN=1, and the visual ASCII diagram shows a 9th column labeled "INN" (after FIN).
- **Correct text:** Per RFC 9293 (formerly RFC 3168/3540), the 9 flag bits are NS=8, CWR=7, ECE=6, URG=5, ACK=4, PSH=3, RST=2, SYN=1, FIN=0. The visual diagram's "INN" column should be NS (ECN Nonce, RFC 3540), and NS should appear as the leftmost column, not the rightmost.
- **Verification:** RFC 9293 §3.1 (TCP Header Format); RFC 3540 §2 (NS flag). Verified with Python: standard bit positions are NS=8 down to FIN=0.
- **Justification:** Teaches wrong bit positions and invents a non-existent flag — would cause wrong answers in any interview asking about TCP flag bit layout.

#### src/networks/tcp/options.md:84
- **Wrong text:** `Window scale: 4-14 (shift count)`
- **Correct text:** `Window scale: 0-14 (shift count)`
- **Verification:** RFC 7323 §2.2: "The shift count is sent in the body of the option... A shift count of 0 indicates no scaling." Maximum is 14 (per §2.3). The sibling file `tcp/header.md` correctly states "Shifts window field left by 0-14 bits".
- **Justification:** Excludes the most common value (0 = no scaling) and misleads readers about the valid range of a negotiated TCP option.

#### src/networks/tcp/cubic.md:22
- **Wrong text:** `K = time at which the window would reach W_max (computed as ∛(W_max × β / C))`
- **Correct text:** `K = time at which the window would reach W_max (computed as ∛(W_max × (1 - β) / C))`
- **Verification:** RFC 8312 §4.1 (CUBIC Window Growth Function): `K = cbrt(W_max * (1 - beta) / C)`. The pseudocode at line 138-141 of the same file correctly uses `(1 - BETA)`, but the prose formula is wrong. Python verification: K_correct = 4.217, K_wrong = 5.593 for W_max=100, β=0.7, C=0.4.
- **Justification:** The K formula is central to CUBIC; the wrong formula gives a different inflection point, and the file contradicts itself between prose and pseudocode.

#### src/networks/security/ssl.md:22
- **Wrong text:** `E --> F[TLS 3.1<br>2018]`
- **Correct text:** `E --> F[TLS 1.3<br>2018]`
- **Verification:** There is no "TLS 3.1" version. The 2018 release is TLS 1.3 (RFC 8446). The rest of the same file (and the sibling tls.md) correctly states "TLS 1.3 (RFC 8446, 2018)".
- **Justification:** Typo invents a non-existent TLS version; readers may believe TLS 3.1 exists.

#### src/networks/routing/README.md:62
- **Wrong text:** `| RIP | 200 |`
- **Correct text:** `| RIP | 120 |`
- **Verification:** Cisco/administrative-distance references: RIP AD = 120 (also correctly stated in `routing/rip.md` line 10: "AD: 120"). The value 200 is iBGP's AD (correctly listed separately at line 64 of the same table). The table has RIP and iBGP sharing the same value 200, which is wrong.
- **Justification:** Teaches the wrong AD for RIP, which would lead to wrong path-selection answers in interviews (a lower-AD OSPF route at 110 vs RIP at 200 vs RIP at 120 changes which protocol wins).

#### src/networks/http/http3.md:258-267
- **Wrong text:** The QUIC long-header ASCII diagram lists the first byte fields as: `Header Form (1)`, `Long (1)`, `Fixed (1)`, `Type (2)`, `Reserved (2)`, `PN Length (2)` — a 9-bit total.
- **Correct text:** Per RFC 9000 §17, the first byte of a QUIC long header is 8 bits: `Header Form (1)`, `Fixed Bit (1)`, `Long Packet Type (2)`, `Reserved Bits (2)`, `Packet Number Length (2)`. There is no separate "Long" bit — the Header Form bit IS the long/short indicator.
- **Verification:** RFC 9000 §17 "Long Header Packets": `Header Form (1) = 1, Fixed Bit (1) = 1, Long Packet Type (2), Reserved Bits (2), Packet Number Length (2)`. The sibling file `http/quic.md` (lines 59-63) describes the same header correctly without the phantom "Long" bit.
- **Justification:** A 9-bit first byte doesn't fit in one byte; teaches a packet format that doesn't exist on the wire.

### MEDIUM severity

#### src/networks/http/http1.md:163-166
- **Wrong text:** The first chunked-encoding example uses chunk size `1a` (hex = 26 decimal) for the data `<h1>Hello, World!</h1>`.
- **Correct text:** Chunk size should be `16` (hex) = 22 decimal (the actual length of `<h1>Hello, World!</h1>`).
- **Verification:** `len("<h1>Hello, World!</h1>") == 22 == 0x16`. Verified with Python.
- **Justification:** Wrong chunk size in a wire-format example would confuse anyone debugging real chunked responses.

#### src/networks/http/http1.md:345-348
- **Wrong text:** The second chunked-encoding example uses chunk sizes `19` (25) and `1a` (26) for two SSE chunks `event: message\ndata: Hello\n\n` and `event: message\ndata: World\n\n`.
- **Correct text:** Both chunks are 28 bytes long → chunk size should be `1c` (hex) for both. The two chunks have the same payload length (Hello and World are both 5 chars), so they must have the same chunk-size prefix.
- **Verification:** `len("event: message\\ndata: Hello\\n\\n") == 28 == 0x1c`. Verified with Python.
- **Justification:** Inconsistent chunk sizes for identical-length payloads; both numbers are also wrong.

#### src/networks/http/http1.md:377
- **Wrong text:** `Most browsers use **6 parallel connections per domain** (defined by HTTP/1.1 specification guidance).`
- **Correct text:** Browsers use 6 parallel connections per domain (their own implementation choice). The HTTP/1.1 specification (RFC 9112 §9.7) actually recommends a single-user client SHOULD NOT maintain more than 2 connections per server; the 6-connection limit is a browser convention that ignores the RFC.
- **Verification:** RFC 9112 §9.7: "a single-user client SHOULD NOT maintain more than 2 connections with any server..." Browser choice of 6 is documented in Chrome/Firefox source; RFC does not say 6.
- **Justification:** Mis-attributes the 6-connection number to the spec; the spec actually says 2.

#### src/networks/tcp/nagle.md:296-308
- **Wrong text:** The "Nagle's Algorithm Statistics" section header says "small messages (100-byte messages)" but the calculations use 41-byte packets (40-byte header + 1-byte payload), then claim "With Nagle: 200 segments/sec × 240 bytes = 48 KB/sec" and "Header overhead: 16 KB/sec (33.3%)".
- **Correct text:** Pick one message size consistently. If messages are 1 byte (matching the 41-byte packet): with 5 messages per ACK, segments are 45 bytes (5 + 40), giving 200 × 45 = 9 KB/sec, 8 KB/sec header (88.9%). If messages are 100 bytes: packets are 140 bytes, and the numbers change completely. The current "240 bytes/segment" and "33.3%" don't match either assumption.
- **Verification:** Python: 200 × 45 = 9000 (not 48000); 200 × 540 = 108000 (not 48000). The "240 bytes" figure has no consistent derivation.
- **Justification:** Internally inconsistent statistics — the "100-byte messages" header contradicts the 41-byte-packet math, and the final figures don't derive from either.

#### src/networks/tcp/reno.md:276
- **Wrong text:** `Reno increases cwnd by 1 MSS per RTT (1460 bytes per 100ms), so it takes ~8500 RTTs (14 minutes!) to fully utilize the link after a loss event.`
- **Correct text:** For a 3-dupACK loss (Reno's fast-recovery case), cwnd drops to cwnd/2 (≈4281 MSS), so recovery to BDP (≈8562 MSS) takes ~4281 RTTs (~7.1 minutes). The 8500-RTT / 14-minute figure is only correct for a timeout that resets cwnd to 1 MSS, which Reno's fast-recovery feature is designed to avoid. The phrase "after a loss event" without specifying timeout is misleading for Reno's main case.
- **Verification:** BDP = 1 Gbps × 100 ms = 12.5 MB = 8562 MSS. After 3-dupACK: cwnd = 4281 MSS. Linear recovery = 4281 RTTs × 100 ms = 428 s = 7.1 min. After timeout: 8562 RTTs × 100 ms = 856 s = 14.3 min (matches the doc). Verified with Python.
- **Justification:** Reno's whole point is fast recovery (cwnd/2 not 1); quoting the timeout-recovery number for "after a loss event" overstates Reno's weakness by 2x.

#### src/networks/osi/physical.md:91-92
- **Wrong text:** `Manchester Encoding ... Low-to-High transition = bit 0, High-to-Low transition = bit 1` (also restated in Q3 at line 175).
- **Correct text:** Per IEEE 802.3 (the Ethernet standard, which the doc says this is for — 10BASE-T), Low-to-High transition = bit 1, High-to-Low transition = bit 0. The doc is using the G.E. Thomas convention, which is the opposite of IEEE 802.3.
- **Verification:** IEEE 802.3 Clause 3 (specifically 3.2.2 for 10BASE-T): a logic 0 is sent as a High-to-Low transition at mid-bit, a logic 1 as Low-to-High. Wikipedia "Manchester code" documents both conventions and notes IEEE 802.3 uses the opposite of G.E. Thomas.
- **Justification:** The doc explicitly claims 10BASE-T (IEEE 802.3) but uses the opposite convention; would teach wrong encoding for Ethernet interview questions.

#### src/networks/udp/header.md:281,288
- **Wrong text:** The example claims "DNS Query (24 bytes)" and "Total UDP payload: 24 bytes" for a query of `example.com A`.
- **Correct text:** A DNS query for `example.com A` (class IN) is 29 bytes: 12-byte header + 13-byte QNAME (`\x07example\x03com\x00`) + 2-byte QTYPE + 2-byte QCLASS. Total UDP datagram would then be 8 + 29 = 37 bytes, and IP Total Length 20 + 37 = 57 bytes (not 52).
- **Verification:** DNS wire format (RFC 1035 §4.1). Python: 12 + 13 + 2 + 2 = 29 bytes. The IP Total Length in the doc is 52, which implies 24-byte payload — but 24 bytes only fits a 2-character SLD like "ab.com".
- **Justification:** The example uses "example.com" (7-char SLD) but the math only works for a 2-char SLD; readers will compute the wrong sizes.

#### src/networks/http/qpack.md:104-107
- **Wrong text:** The "Encoder Instructions" table lists prefixes as `00` for Insert with Name Ref and `01` for Insert Literal, which conflict with the same-row `001` (Set Dynamic Table Capacity) and `000` (Duplicate) — `00` and `01` are prefixes of `001` and `000`, so the table is ambiguous.
- **Correct text:** Per RFC 9204 §4.3.2: `1T` (1-bit prefix) for Insert with Name Reference, `01H` (3-bit prefix) for Insert with Literal Name, `001` for Set Dynamic Table Capacity, `000` for Duplicate.
- **Verification:** RFC 9204 §4.3.2 (Encoder Instructions). The prefixes must be uniquely decodable, which the doc's table is not.
- **Justification:** The encoder-instruction prefixes can't be told apart as written; readers will think `00` and `000` (or `01` and `001`) are different encodings of the same first bits.

#### src/networks/http/quic.md:127-133
- **Wrong text:** The stream-ID example shows `Stream 0 (control stream, unidirectional)`, `Stream 1 (control stream, unidirectional)`, `Stream 2 (encoder stream)`, `Stream 3 (decoder stream)`, then later `Stream 4 (request/response, bidirectional)` for HTTP requests.
- **Correct text:** Per RFC 9000 §2.1 and RFC 9114 §6, stream IDs encode type in their low 2 bits: 0b00 = client bidi (streams 0, 4, 8...), 0b01 = server bidi (1, 5, 9...), 0b10 = client uni (2, 6, 10...), 0b11 = server uni (3, 7, 11...). For HTTP/3: stream 0 is the first client-bidi HTTP request stream; the client control stream is stream 2; server control stream is stream 3; QPACK encoder streams are 6/7; QPACK decoder streams are 10/11.
- **Verification:** RFC 9114 §6.1 (Bidirectional Streams) and §6.2 (Unidirectional Streams); RFC 9204 §3.2 (QPACK encoder/decoder streams). The doc's bit-pattern description on lines 135-143 is actually correct, which makes the diagram at 127-133 self-contradictory.
- **Justification:** Teaches wrong stream assignments; stream 0 is NOT a control stream, it's the first HTTP request stream.

#### src/networks/http/quic.md:208-212
- **Wrong text:** `Example: ACK for packets 1,2,3,5,6,7,10 / Largest Acknowledged: 10 / First ACK Range: 0 (10-0 = 10, then...) / Ranges: {10-8}, gap, {6-4}, gap, {2-0}`. The ranges `{10-8}`, `{6-4}`, `{2-0}` include packet numbers (8, 9, 4, 0) that are NOT in the ACK set.
- **Correct text:** For ACK of packets 1,2,3,5,6,7,10: Largest Acknowledged = 10; First ACK Range = 0 (just packet 10); gap of 2 (packets 8,9 missing); ACK range = 2 (packets 5,6,7); gap of 1 (packet 4 missing); ACK range = 2 (packets 1,2,3). Or more clearly: ranges {10}, gap, {5-7}, gap, {1-3}.
- **Verification:** RFC 9000 §19.3 (ACK Frames): ranges are contiguous blocks of acknowledged packets separated by gaps of unacknowledged packets. Packets 8, 9, 4, 0 are explicitly NOT in the ACK set, so they can't appear in ranges.
- **Justification:** The range notation `{10-8}` includes packet 8 (which was never received); teaches wrong ACK frame construction.

#### src/networks/tcp-ip/arp.md:152
- **Wrong text:** `participant A as Attacker<br/>192.168.1.666`
- **Correct text:** `participant A as Attacker<br/>192.168.1.166` (or any other valid IP — each octet must be 0-255; 666 is invalid).
- **Verification:** IPv4 dotted-decimal notation requires each octet to be 0-255 (RFC 791). 666 > 255, so it's not a valid IPv4 address.
- **Justification:** An invalid IP in a diagram is a noticeable error that undermines the example's credibility.

#### src/networks/load-balancing/README.md:49
- **Wrong text:** `NOTE_FIX["Note: LB picks server based on IP:port only"]`
- **Correct text:** Remove the line entirely, or replace with a proper Mermaid note like `Note over LB: Picks server based on IP:port only`.
- **Verification:** Mermaid `graph LR` syntax: an unconnected node statement like `NOTE_FIX[...]` renders as a floating node with the label "NOTE_FIX". The variable-style name `NOTE_FIX` (all caps, underscore) suggests it's a leftover placeholder from editing.
- **Justification:** Editing artifact / leftover placeholder text in a published diagram.

### LOW severity

#### src/networks/tools/curl.md:108
- **Wrong text:** `curl -vv https://api.example.com/users` is presented as a "Very verbose (TLS details)" option distinct from `-v`.
- **Correct text:** curl's `-v` flag is binary (on/off) — repeating it as `-vv` does not increase verbosity. For TLS details, use `--trace` or `--trace-ascii` (as the doc itself mentions at line 126). Multiple `-v` flags have no additional effect in curl.
- **Verification:** curl man page: `-v, --verbose` — single flag. No `-vv` documented. The author may be confusing this with ssh or other tools where -vv increases verbosity.
- **Justification:** Minor — readers may type `-vv` expecting more output and be confused.

#### src/networks/sockets/tcp.md:213
- **Wrong text:** `the endpoint that sent the final ACK waits 2×MSL (typically 60s)`
- **Correct text:** RFC 793 specifies MSL = 2 minutes, so 2×MSL = 4 minutes (240 seconds). The 60-second figure is Linux's default `tcp_fin_timeout` (a different setting) — Linux TIME_WAIT is actually 60 seconds by default but the RFC-mandated value is 4 minutes.
- **Verification:** RFC 793 §3.5: "MSL is specified to be 2 minutes". Linux default TIME_WAIT is 60s (configurable via `net.ipv4.tcp_fin_timeout` is for FIN_WAIT_2, TIME_WAIT is fixed at 60s in modern Linux).
- **Justification:** The 60s is a Linux-specific default; stating it as the general "2×MSL" value misrepresents the RFC.

## Files confirmed clean

The following audited files had no significant errors (technical or stylistic):

- src/networks/overview.md
- src/networks/tcp-ip/README.md
- src/networks/tcp-ip/ipv4.md
- src/networks/tcp-ip/ipv6.md
- src/networks/tcp-ip/cidr.md
- src/networks/tcp-ip/subnetting.md
- src/networks/tcp-ip/nat.md
- src/networks/tcp-ip/dhcp.md
- src/networks/tcp-ip/rarp.md
- src/networks/tcp-ip/icmp.md
- src/networks/tcp-ip/ip.md
- src/networks/tcp/README.md
- src/networks/tcp/three-way.md
- src/networks/tcp/slow-start.md
- src/networks/tcp/congestion-control.md
- src/networks/tcp/congestion-avoidance.md
- src/networks/tcp/fast-retransmit.md
- src/networks/tcp/fast-recovery.md
- src/networks/tcp/keepalive.md
- src/networks/http/README.md
- src/networks/http/http2.md
- src/networks/http/https.md
- src/networks/http/grpc.md
- src/networks/http/rest.md
- src/networks/http/websocket.md
- src/networks/osi/README.md
- src/networks/osi/data-link.md
- src/networks/osi/network.md
- src/networks/osi/transport.md
- src/networks/osi/session.md
- src/networks/osi/presentation.md
- src/networks/osi/application.md
- src/networks/dns/README.md
- src/networks/dns/record-types.md
- src/networks/dns/resolution.md
- src/networks/dns/caching.md
- src/networks/dns/security.md
- src/networks/udp/README.md
- src/networks/udp/tcp-vs-udp.md
- src/networks/udp/header.md (only the example has the MEDIUM issue noted above; technical content is correct)
- src/networks/sockets/README.md
- src/networks/sockets/udp.md
- src/networks/sockets/tcp.md (only the TIME_WAIT LOW issue noted above)
- src/networks/sockets/unix.md
- src/networks/sockets/nonblocking.md
- src/networks/sockets/io-multiplexing.md
- src/networks/security/README.md
- src/networks/security/tls.md
- src/networks/security/ssl.md (only the TLS 3.1 HIGH typo noted above)
- src/networks/security/ipsec.md
- src/networks/security/firewalls.md
- src/networks/security/vpn.md
- src/networks/routing/rip.md
- src/networks/routing/bgp.md
- src/networks/routing/isis.md
- src/networks/routing/static-vs-dynamic.md
- src/networks/load-balancing/README.md (only the NOTE_FIX MEDIUM issue noted above)
- src/networks/load-balancing/algorithms.md
- src/networks/load-balancing/l4-vs-l7.md
- src/networks/load-balancing/reverse-proxy.md
- src/networks/cdn/README.md
- src/networks/cdn/edge.md
- src/networks/cdn/how-it-works.md
- src/networks/tools/README.md
- src/networks/tools/ping-traceroute.md
- src/networks/tools/curl.md (only the -vv LOW issue noted above)
- src/networks/tools/tcpdump.md
- src/networks/tools/wireshark.md
- src/networks/tools/netstat.md
- src/networks/wireless/README.md
- src/networks/wireless/wifi.md
- src/networks/wireless/bluetooth.md
- src/networks/wireless/5g.md
- src/networks/wireless/sdn.md
- src/networks/wireless/nfv.md
- src/networks/ebpf-networking.md

## Methodology

- All files were read in full (89 markdown files, ~140k words across TCP/IP, TCP, HTTP, OSI, DNS, UDP, sockets, security, routing, load-balancing, CDN, tools, wireless, eBPF).
- Arithmetic claims (subnet math, CIDR block sizes, RTT/throughput, chunk sizes, DNS payload sizes, Manchester encoding, BDP calculations, TCP flag bit numbering, CUBIC K formula) were verified with Python (`python3 -c` scripts).
- Protocol details were cross-checked against RFCs (RFC 793/9293 TCP, RFC 7323 Window Scale, RFC 6928 IW, RFC 8312 CUBIC, RFC 9000 QUIC, RFC 9114 HTTP/3, RFC 9204 QPACK, RFC 7540/9113 HTTP/2, RFC 7541 HPACK, RFC 6455 WebSocket, RFC 1035 DNS, RFC 791 IPv4, RFC 768 UDP, RFC 9112 HTTP/1.1, RFC 8446 TLS 1.3, RFC 4271 BGP, RFC 1058/2453 RIP, IEEE 802.3 Manchester, IEEE 802.11 Wi-Fi).
- Sample of citations verified against authoritative sources (Cisco AD table, IETF RFCs, IEEE standards).
- AI artifacts searched for: "Wait,", "Hmm,", "Actually,", "Let me re-", "Let me try", "Ah, I see", "Great, so", "Oh wait", "But wait" — none found.
- Placeholder/stub code: the only stub found is `bluetooth.md` which is intentionally a short stub; the `NOTE_FIX` placeholder in `load-balancing/README.md` is flagged above.
- Mermaid diagrams: scanned for undeclared participants and malformed syntax; the `NOTE_FIX` issue is the only structurally malformed diagram.

## Top 5 most egregious issues (with quotes)

1. **`routing/README.md:62` — wrong RIP AD value**: `| RIP | 200 |` should be `120`. RIP's actual administrative distance is 120 (verified in `routing/rip.md:10` and Cisco's documentation). 200 is iBGP's AD — the table accidentally duplicates iBGP's value for RIP.

2. **`security/ssl.md:22` — non-existent TLS version**: `E --> F[TLS 3.1<br>2018]` — there is no TLS 3.1. The 2018 release is TLS 1.3. Pure typo that invents a version.

3. **`tcp/header.md:53-62` — TCP flag bit numbering off by one and phantom "INN" flag**: The table lists CWR=8, ECE=7, ..., FIN=1 (off by one — should be CWR=7, ..., FIN=0) and omits the NS bit (which is bit 8 per RFC 9293); the ASCII diagram adds a non-existent 9th flag labeled "INN".

4. **`tcp/cubic.md:22` — wrong CUBIC K formula in prose**: `K = ∛(W_max × β / C)` should be `K = ∛(W_max × (1 - β) / C)` per RFC 8312 §4.1. The pseudocode at line 138-141 of the same file correctly uses `(1 - BETA)`, so the file contradicts itself.

5. **`http/http3.md:258-267` — 9-bit QUIC first byte**: The QUIC long-header diagram adds a phantom "Long (1)" bit on top of the "Header Form (1)" bit, making the first byte 9 bits instead of 8. RFC 9000 §17 specifies 8 bits only — the Header Form bit IS the long/short indicator.
