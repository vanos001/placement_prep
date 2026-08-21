# QUIC Protocol Internals (RFC 9000)

> Prerequisites: skim [QUIC](./quic.md) for the high-level "why UDP" pitch.
> This page goes one layer deeper: packet formats, frame types, packet
> number encryption, the loss-detection state machine, and connection
> migration mechanics. Every byte diagram below is reproduced from the
> normative text of RFC 9000.

## 1. Where QUIC Lives in the Stack

QUIC is a *transport* protocol that ships itself inside UDP datagrams.
Everything TCP used to do in the kernel — reliable delivery, congestion
control, flow control, loss recovery, and now TLS termination — is
re-implemented in userspace. That is the whole point: the IETF can ship
new transport features (pacing, 0-RTT, per-stream loss recovery) without
waiting for every OS in the world to upgrade its TCP stack.

```
   application layer        HTTP/3 frames  (HEADERS, DATA, SETTINGS …)
   ┌──────────────────────────────────────────────────────────────┐
   │  HTTP/3                                                       │
   ├──────────────────────────────────────────────────────────────┤
   │  QPACK  (header compression — RFC 9204)                      │
   ├──────────────────────────────────────────────────────────────┤
   │  QUIC stream multiplexer   (frames: STREAM, ACK, CRYPTO …)   │
   ├──────────────────────────────────────────────────────────────┤
   │  QUIC packet protection   (header protection + AEAD packet   │
   │                            payload, integrated TLS 1.3)        │
   ├──────────────────────────────────────────────────────────────┤
   │  QUIC packet framing      (long/short header packets)        │
   ├──────────────────────────────────────────────────────────────┤
   │  UDP datagrams                                               │
   ├──────────────────────────────────────────────────────────────┤
   │  IP                                                          │
   └──────────────────────────────────────────────────────────────┘
```

The "packet protection" box is the trick: unlike TCP+TLS, where TLS just
runs over an opaque byte stream, QUIC *interleaves* its transport
handshake with the TLS handshake using a dedicated `CRYPTO` frame. The
TLS record layer is not used at all — QUIC replaces it. See RFC 9001
§1.

## 2. Long vs Short Header Packets

QUIC distinguishes two packet classes by the high bit of byte 0:

- **Long header packets** (high bit = 1) — used during handshake and
  0-RTT. They carry the version, the full source and destination
  connection IDs, and a variable-length length field.
- **Short header packets** (high bit = 0) — used after the handshake
  completes. The version, length, and source connection ID are elided
  (the peer already knows them).

### Long header format (Initial, 0-RTT, Handshake, Retry)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|1|1| Form Bits |   ← high bit=1 (long), next 2 bits = packet type
+-+-+-+-+-+-+-+-+
|                    Version (32 bits)                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| DCID Len (8)  |   Destination Connection ID (variable…)       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| SCID Len (8)  |   Source Connection ID (variable…)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|              Packet Number (variable-length int)             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Payload Length (variable-length int)                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Packet Payload  (AEAD-encrypted frames)                    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

The 2-bit `Form Bits` field distinguishes Initial (00), 0-RTT (01),
Handshake (10), Retry (11). Note `Retry` packets are *not* encrypted —
they carry a 16-byte integrity tag computed with AEAD_AES_128_GCM
using a hardcoded key derived from the string `"quic tls retry"` (RFC
9001 §5.8). This stops off-path attackers from injecting fake Retry
packets.

### Short header format (1-RTT)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|0|1|P|  K  |RR |
+-+-+-+-+-+-+-+-+
|   DCID (variable length, up to 20 bytes)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Packet Number (1, 2, or 4 bytes, truncated)                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Packet Payload (AEAD-encrypted frames)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `P` (1 bit) — spin bit, optional heartbeat for path measurement
  (RFC 9306).
- `K` (1 bit) — set when the key phase has flipped, signalling a
  key-update.
- `RR` (2 bits) — reserved, must be 0 unless the peer negotiated the
  use of those bits via `grease_quic_bit`.

The DCID is the *only* identifier that survives NAT rebinding, because
the SCID is not sent in short-header packets.

## 3. Connection IDs — More than an Address

TCP ties a connection to the 4-tuple `(src_ip, src_port, dst_ip,
dst_port)`. If any of those change — for example the laptop roams from
Wi-Fi to 5G — the connection dies. QUIC introduces **connection IDs
(CIDs)** that are *end-to-end meaningful* and decoupled from the IP
tuple.

Each side picks one or more CIDs for itself. The client puts its chosen
DCID in the Initial; the server replies with its own SCID. New CIDs are
issued with `NEW_CONNECTION_ID` frames, each tagged with a sequence
number and an optional 16-byte stateless reset token. The retired ones
go out with `RETIRE_CONNECTION_ID`. A connection can have up to 8
active CIDs on either side at once (RFC 9000 §5.1.1).

The clever bit is that CIDs are *routing keys*. A QUIC-aware load
balancer can read the DCID straight out of the cleartext long-header
(or out of the short header, which is also unencrypted for the CID
portion) and route the datagram to the right backend *without*
terminating TLS. This is the foundation of things like the *QUIC-LB*
draft, which encodes a backend identifier inside the CID layout.

```
            client                       LB                       backend
              │                          │                           │
   Initial:   │  DCID = LB-encoded ID    │                           │
              │ ─────────────────────────>│                           │
              │                          │   forward UDP unchanged   │
              │                          │ ─────────────────────────>│
              │                          │                           │
              │                          │            short header:  │
              │                          │<───────── DCID=client ────│
              │<─────────────────────────│                           │
```

Stateless reset tokens are a fallback: if a backend has lost all state
for a connection (e.g., it crashed and rebooted) but the client keeps
sending packets, the backend can reply with a *stateless reset* — a
short packet whose last 16 bytes are an HMAC of the connection's reset
token. The client recognizes its own token, aborts the connection
cleanly, and frees its state.

## 4. Packet Number Encryption (Header Protection)

Even the *packet number* is encrypted in QUIC. This is what prevents
passive observers from linking a 0-RTT packet to the corresponding
handshake — a property called **packet number confidentiality**.

The mechanism is **header protection**, borrowed from TLS 1.3's record
padding scheme. For every packet, the AEAD produces a 16-byte
authentication tag. The 5 bytes right before that tag are taken and run
through a mask function — either `AES-ECB` of a 5-byte sample, or
ChaCha20 keystream — and XORed into the high bits of the packet
number and the reserved bits. So the plaintext packet number lives in
the clear only after the receiver has decrypted the payload (because
the mask requires the AEAD output as input).

```
   ciphertext packet bytes:
   +----------+----------+----------+----------+----------+
   | hdr      | pn       | ... encrypted payload ... | tag(16)|
   +----------+----------+----------+----------+----------+
                                  sample = last 16 bytes of ciphertext payload
                                  mask   = header_protection(sample)
                                  pn[0..n] ^= mask[0..n]
```

Because packet numbers are truncated to the smallest width that
distinguishes them from recently-seen numbers (1, 2, or 4 bytes), the
mask only covers those low bytes. After decryption, the receiver
reconstructs the full 62-bit packet number by extrapolating from the
largest previously observed value (RFC 9000 §17.3 / Appendix A).

## 5. Frame Types

Inside an encrypted packet payload lives a sequence of frames. The
important ones:

| Type byte | Frame       | Notes                                                          |
|----------:|-------------|----------------------------------------------------------------|
| 0x00      | PADDING     | Pure zero bytes, only used to pad a datagram to MTU size.      |
| 0x01      | PING        | Triggers an immediate ACK; used for keepalive and anti-amplify. |
| 0x02-0x03 | ACK         | Carries ACK ranges; E bit (0x03) signals ECN echo counts.      |
| 0x04-0x06 | RESET_STREAM| One stream aborted, with final offset + error code.            |
| 0x07      | STOP_SENDING| Tell peer to stop sending on a stream.                          |
| 0x08      | CRYPTO      | Carries TLS handshake bytes; offset+length+data.               |
| 0x09-0x0f | NEW_TOKEN   | Server-issued token for address validation (future 0-RTT).     |
| 0x10-0x14 | STREAM      | Per-stream data, with FIN bit.                                 |
| 0x15-0x18 | MAX_DATA    | Bump connection-level flow-control window.                      |
| 0x19-0x1c | MAX_STREAMS| Bump the count of allowed bidir/unidir streams.                 |
| 0x1d-0x1e | BLOCKED    | Signal that we are blocked on flow control.                    |
| 0x1f-0x24 | STREAM_BLOCKED / STREAM_RESET | Per-stream flow-control signals.            |
| 0x25-0x26 | STOP_SENDING| (one variant)                                                  |
| 0x2c-0x2d | NEW_CONNECTION_ID | New CID + stateless reset token + retire-prior-to.       |
| 0x2e-0x2f | RETIRE_CONNECTION_ID | "You can drop CID with sequence N".                     |
| 0x30-0x31 | PATH_CHALLENGE / PATH_RESPONSE | 8-byte random, for path validation.            |
| 0x32-0x33 | CONNECTION_CLOSE | Transport-level or application-level close.                 |
| 0x34      | HANDSHAKE_DONE| Sent by server once the TLS Finished is verified.              |

Each STREAM frame (0x08-0x0f subtypes vary by flags) carries a stream
ID, an offset, a length, and (optionally) the FIN bit. Streams are
identified by a 62-bit integer whose low two bits encode
directionality:

- bit 0 = 0 → client-initiated; = 1 → server-initiated
- bit 1 = 0 → bidirectional; = 1 → unidirectional

So client bidirectional streams are 0, 4, 8, …; server unidirectional
streams are 3, 7, 11, …

## 6. The Handshake and 0-RTT

The handshake is the layer where TLS and QUIC stop being separable.
The TLS ClientHello is sent *inside* a CRYPTO frame in the client's
Initial packet. The whole of TLS — ServerHello, EncryptedExtensions,
Certificate, CertificateVerify, Finished — flows through CRYPTO frames
on Initial, Handshake, and 1-RTT packets.

A 1-RTT timeline:

```
   client                                           server
   Initial [ CRYPTO(ClientHello, TLS_1.3) ]  ────>
                                            <────  Initial  [ CRYPTO(ServerHello…) +
                                                            ACK ]
                                            <────  Handshake [ CRYPTO(EncryptedExt,
                                                                       Cert, CertVerify,
                                                                       Finished) ]
   Handshake [ CRYPTO(Finished) ]            ────>
   1-RTT     [ first app STREAM frames ]     ────>
                                            <────  1-RTT [ HANDSHAKE_DONE + app frames ]
```

The single round-trip for the full TLS 1.3 handshake is the 1-RTT
case. 0-RTT is the optimisation where the client, having cached the
server's transport parameters and a TLS session ticket from a previous
connection, sends a `0-RTT` packet *in the same datagram* as its
Initial. Inside that 0-RTT packet are application STREAM frames —
already encrypted under keys derived from the resumption master
secret.

The catch is replay. TLS 1.3's 0-RTT data is encrypted under a
forward-secure key, but a network attacker can capture the 0-RTT
packet and replay it to the server later. Servers must therefore (a)
only accept 0-RTT data whose transcript hash matches what they
issued, and (b) only let through idempotent operations in that
window. The defense-in-depth mechanism is a *strike register* — a
bounded bloom filter or single-use token table — that detects
duplicate 0-RTT packets within a replay window (RFC 8446 §8 + RFC
9001 §8).

## 7. Loss Detection (RFC 9002)

QUIC's loss detection is in some ways simpler and in some ways
smarter than TCP's. The spec is RFC 9002.

The big idea is **per-packet-number tracking plus a Probe Timeout
(PTO)**. There is no Reno-style retransmission timer tied to a single
"in flight" segment. Instead:

1. Every packet is acked individually via the ACK frame, which carries
   the largest acked PN plus a list of *ranges* of acked PNs.
2. *Ack-induced loss detection* — if a packet is sent and N packets
   with higher PNs are acked, the original is declared lost
   (RFC 9002 §6.1). The threshold `packet_threshold` defaults to 3.
3. *Time-threshold loss detection* — if a packet is unacked for longer
   than `RTT * (9/8)` it's declared lost. The `1/8` factor is a
   safety margin against reordering.
4. *Probe Timeout (PTO)* — if no ack is received for
   `smoothed_rtt + max(4*rttvar, kGranularity) + max_ack_delay`, send
   *probe* packets (a PING plus an ack-eliciting frame) in pairs to
   elicit an immediate ACK. PTO does not declare loss — it just
   keeps the loss-detection clock alive.

PTO is what makes QUIC robust to reordering-induced spurious timeouts:
the sender doesn't conclude that a packet was lost just because its
retransmission timer fired. It sends a probe, gets an ACK back,
updates RTT, and only then decides whether to declare loss.

```
   send PN=42  ────────────────────────────────────────────────
              t                                  t+PTO
              │                                   │
              │  no ack...                        │  send PING + PING probe pair
              │                                   │
   ack PN=43..50 arrives at t+RTT ─────>  declare PN=42 lost (k=3 packets acked above)
                                              └─> retransmit its frames in new packets
```

Note one subtlety: when a packet is "retransmitted", what gets
retransmitted are the *frames* inside it, not the packet itself. The
new packet has a fresh PN. This is the meaning of *"QUIC never
retransmits packets; it retransmits frames."* It's also why QUIC has
no retransmission ambiguity — the RTT estimate is never corrupted by
retransmissions because the new PN is unique.

## 8. Congestion Control

QUIC's congestion control is *pluggable*. The reference default in RFC
9002 is a NewReno-flavoured algorithm — slow start, congestion
avoidance, fast recovery — operating on packet numbers, with the
modification that loss recovery is *per-ack* rather than per-segment.
That makes QUIC able to react to small losses without going into
full fast-recovery for the entire window.

In practice most production QUIC stacks ship multiple controllers:

- **Cubic** (default in Chrome and Cloudflare quiche) —
  https://blog.cloudflare.com/cubic-and-bbr-in-quiche/
- **BBR v2** — Google's model-based controller, tuned for non-lossy
  congestion signals (delay, ECN, bandwidth estimation).
- **NewReno** — RFC 9002's reference, used in test suites.

The sender also has a hard **anti-amplification limit** (RFC 9000
§8.1): until the client proves it owns the source address, the server
may not send more than 3× the bytes it has received. This blocks
reflection-style amplification attacks. The limit is lifted once the
client sends a Handshake packet that completes the address-validation
step, or once the server has issued a NEW_TOKEN and the client echoes
it back.

## 9. Connection Migration

Connection migration is the single most visible feature of QUIC. The
flow is:

1. Client starts sending packets from a new 4-tuple (e.g., Wi-Fi →
   cellular handover). Because the DCID stays the same, the server
   still recognizes the connection.
2. The server replies to the new path, but it must *validate* that
   path before sending more than 3× the bytes received — i.e., the
   anti-amplification limit kicks in again for the new path.
3. Validation: server sends a `PATH_CHALLENGE` containing 8 random
   bytes. Client must echo them back in a `PATH_RESPONSE` on the
   same path. Only then is the path "validated".
4. Once validated, the server can use the new path freely, and the
   connection survives the migration.

There are also non-trivial gotchas:

- Path MTU can differ between paths. QUIC re-measures PMTU on the new
  path using DPLPMTUD (RFC 8899).
- RTT estimates for the new path start fresh; the congestion
  controller must not assume the old RTT.
- A client that's behind NAT can spontaneously migrate without ever
  noticing — the migration is transparent. Servers should treat
  migration as the rule, not the exception.

## 10. Comparison to TCP + TLS

| Concern              | TCP + TLS 1.3                                | QUIC                                                          |
|----------------------|----------------------------------------------|---------------------------------------------------------------|
| Handshake RTT        | 1 RTT TCP + 1 RTT TLS = 2 RTT (or 1 RTT with TLS resumption) | 1 RTT, 0 RTT with resumption                                  |
| HoL blocking         | Yes — single byte stream, all streams blocked on loss. | No — streams are independent.                                  |
| Loss recovery        | Reno/Cubic in kernel, retransmit-ambiguity prone. | Per-PN, no ambiguity, packet-number encryption hides reorder. |
| Connection identity  | 4-tuple. NAT rebinding kills it.             | Connection ID; survives migration.                            |
| Middlebox ossification| High — middleboxes expect specific TCP/TLS patterns. | Lower — UDP datagrams, opaque payload, easy to evolve.       |
| Encryption           | TLS is a layer on top; handshake bytes are unauthenticated by TCP. | Integrated; even packet numbers are encrypted.                |
| CPU cost             | Low — kernel TLS offload (kTLS) is mature.   | Higher — userspace crypto; few NICs accelerate QUIC yet.     |

The middlebox point is the most under-appreciated. TCP has ossified
so thoroughly that any new TCP option (MPTCP, TCP Fast Open, TCP INC)
is routinely stripped by NATs and firewalls. QUIC, by shipping inside
UDP and keeping the wire format free of any in-network semantics,
sidesteps that problem entirely — at the cost of re-implementing the
transport stack in userspace.

## 11. Common Pitfalls

1. **0-RTT for mutating requests.** Replays can do real damage. Limit
   0-RTT to GET; do an anti-replay strike check before processing any
   other method.
2. **Forgetting the anti-amplification limit.** A server that sends
   more than 3× received bytes before validation can be abused as an
   amplification reflector. Implementations must enforce the cap per
   path, not just per connection.
3. **Reusing a connection ID across migrations.** If the client
   intentionally changes the DCID while migrating, the server should
   *also* validate the new path with PATH_CHALLENGE; otherwise an
   on-path attacker can hijack the connection.
4. **Tiny initial congestion windows on resumption.** Some
   implementations reset cwnd to 10 MSS after migration. That kills
   throughput for large uploads — instead, the spec recommends
   cwnd = max(2 * MSS, cwnd_before / 2).
5. **Trusting the spin bit for path measurement.** The spin bit (P
   in the short header) is opt-in and observers can spoof it; it's a
   hint, not a source of truth.

## References

- RFC 9000 — *QUIC: A UDP-Based Multiplexed and Secure Transport*.
  https://www.rfc-editor.org/rfc/rfc9000.html
- RFC 9001 — *Using TLS to Secure QUIC*. https://www.rfc-editor.org/rfc/rfc9001.html
- RFC 9002 — *QUIC Loss Detection and Congestion Control*. https://www.rfc-editor.org/rfc/rfc9002.html
- RFC 9369 — *Version-Independent QUIC*. (Defines the fixed bits in
  long headers so that v1 and v2 packets are distinguishable.)
  https://www.rfc-editor.org/rfc/rfc9369.html
- RFC 9306 — *Datagram Packetization Layer (DPLPMTUD) for QUIC* and
  the spin bit. https://www.rfc-editor.org/rfc/rfc9306.html
- IETF QUIC WG — *WG wiki and drafts archive.*
  https://datatracker.ietf.org/wg/quic/about/
- Cloudflare — *"Cubic and BBR in quiche"*.
  https://blog.cloudflare.com/cubic-and-bbr-in-quiche/
- Cloudflare — *"The road to QUIC"* (engineering notes on building a
  production QUIC stack). https://blog.cloudflare.com/the-road-to-quic/
- chromium — *QUIC implementation docs.*
  https://www.chromium.org/quic/
- Litespeed — *lsquic README* (a widely-deployed open-source QUIC
  library, useful for reading real wire-format code).
  https://github.com/litespeedtech/lsquic

## Cross-References

- [QUIC overview](./quic.md) — high-level pitch and TCP comparison.
- [HTTP/3](./http3.md) — the application layer that sits on top.
- [HPACK](./hpack.md) and [QPACK](./qpack.md) — header compression
  for HTTP/2 vs HTTP/3.
- [TLS internals](./https.md) — what QUIC's CRYPTO frames transport.
