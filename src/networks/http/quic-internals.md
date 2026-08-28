# QUIC Protocol Internals (RFC 9000 / 9001 / 9002)

> Prerequisites: skim [QUIC](./quic.md) for the high-level "why UDP" pitch.
> This page goes one layer deeper: packet formats, frame types, packet
> number encryption and decoding, the loss-detection state machine, and
> connection migration mechanics. Frame-type values, byte diagrams, and
> cryptographic constants below are checked against the normative text
> of RFC 9000 and RFC 9001 (the working examples in §12 reproduce the
> test vectors printed in the RFCs themselves).

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
TLS record layer is not used at all — QUIC replaces it (RFC 9001 §1).
QUIC authenticates the entire header and encrypts almost everything
except what receivers physically need in the clear: the header form,
fixed bit, packet type, connection IDs, length, and the packet number
truncation width.

## 2. Long vs Short Header Packets

QUIC distinguishes two packet classes by the high bit of byte 0:

- **Long header packets** (high bit = 1) — used during handshake and
  0-RTT. They carry the version, the full source and destination
  connection IDs, and a length field.
- **Short header packets** (high bit = 0) — used after the handshake
  completes. The version, length, and source connection ID are elided
  (the peer already knows them).

### Long header format (RFC 9000 §17.2)

Byte 0 layout: `1` (header form) | `1` (fixed bit) | 2-bit long packet
type | 4 type-specific bits. The long packet type values are Initial =
`0x0`, 0-RTT = `0x1`, Handshake = `0x2`, Retry = `0x3`. After byte 0
follow the version and connection IDs; everything else is
type-specific. The single most commonly botched detail is the field
*order* — the length field comes **before** the packet number:

```
Initial Packet (RFC 9000 §17.2.2):
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|1|1|Type=0x0|RR|PP|   ← RR = reserved (2 bits), PP = PN length (2 bits)
+-+-+-+-+-+-+-+-+
|                    Version (32 bits)                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| DCID Len (8)  |   Destination Connection ID (0..160 bits)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| SCID Len (8)  |   Source Connection ID (0..160 bits)          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Token Length (varint)                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Token (…)                                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Length (varint) — covers PN + payload      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Packet Number (1-4 bytes, protected)       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Protected Payload (AEAD-encrypted frames)  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

0-RTT and Handshake packets are identical except they omit the Token
fields. Retry packets (§17.2.5) are the outlier: they carry **no
packet number, no length, and no payload at all** — just the header,
DCID, SCID, an opaque Retry Token, and a 128-bit Retry Integrity Tag.

### Retry integrity (RFC 9001 §5.8)

The Retry Integrity Tag is the output of AEAD_AES_128_GCM over an
empty plaintext, with fixed, RFC-assigned parameters:

- key K = `0xbe0c690b9f66575a1d766b54e368c84e` (128 bits)
- nonce N = `0x461599d35d632bf2239825bb` (96 bits)
- both derived by HKDF-Expand-Label from the secret
  `0xd9c9943e6101fd200021506bcc02814c73030f25c79d71ce876eca876e6fca8e`
  with labels `"quic key"` and `"quic iv"` respectively
- associated data = the *Retry Pseudo-Packet*: the Retry packet minus
  the integrity tag, **prepended** with the ODCID (the DCID of the
  Initial packet this Retry responds to)

Embedding the client's original DCID in the pseudo-packet is what
stops off-path attackers from injecting fake Retry packets: only an
endpoint that actually observed the client's Initial can compute a
valid tag.

### Short header format (RFC 9000 §17.3)

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+
|0|1|S|RR|K|PP|   ← S = spin, RR = reserved (2), K = key phase,
+-+-+-+-+-+-+-+-+     PP = packet number length (2)
|   DCID (0..20 bytes, as chosen by the peer)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Packet Number (1, 2, 3, or 4 bytes, truncated + protected)   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Protected Payload (AEAD-encrypted frames)                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `S` — the **latency spin bit** (RFC 9000 §17.4). The server reflects
  the value it received; the client flips it once per RTT, so an
  on-path observer can measure the interval between toggle events to
  estimate RTT. It is optional: endpoints must disable it for at least
  one in every 16 paths (or connection IDs) so spin-disabled
  connections are commonly observed, and administrators must be able
  to turn it off globally or per connection.
- `K` — the **key phase bit**, toggled to signal a key update
  (RFC 9001 §6).
- `RR` — reserved bits; a sender MAY set them to any value
  (in-packet greasing), and a receiver MUST ignore them.
- `PP` — packet number length minus 1: packet numbers are encoded in
  **1, 2, 3, or 4 bytes** (two of the four 2-bit encodings' full
  ranges are legal; 3-byte packet numbers do occur).

The fixed bit itself can be greased too: the `grease_quic_bit`
transport parameter (0x2ab2, RFC 9287) signals "I will accept packets
with the QUIC (fixed) bit cleared to 0", letting future versions
repurpose that bit without ossifying it. This is *the fixed bit*
(0x40), not the reserved bits — reserved-bit greasing needs no
negotiation at all.

The DCID is the *only* identifier that survives NAT rebinding in the
short header, because the SCID is not sent there.

## 3. Connection IDs — More than an Address

TCP ties a connection to the 4-tuple `(src_ip, src_port, dst_ip,
dst_port)`. If any of those change — for example the laptop roams from
Wi-Fi to 5G — the connection dies. QUIC introduces **connection IDs
(CIDs)** that are *end-to-end meaningful* and decoupled from the IP
tuple.

Each side issues CIDs for its peer to use as *destination* IDs. New
CIDs travel in `NEW_CONNECTION_ID` frames, each carrying a sequence
number, a `Retire Prior To` value, and a 16-byte stateless reset
token. The peer retires old ones with `RETIRE_CONNECTION_ID`. How many
CIDs each side must issue is bounded by the peer's
`active_connection_id_limit` transport parameter — the default is 2,
and values below 2 are invalid (RFC 9000 §18.2). There is no fixed
"8 active CIDs" constant in the spec; the cap is whatever the peer
advertised.

The clever bit is that CIDs are *routing keys*. A QUIC-aware load
balancer can read the DCID straight out of the cleartext header and
route the datagram to the right backend *without* terminating TLS.
This is the foundation of QUIC-LB — the IETF load-balancing design
(draft-ietf-quic-load-balancers) that encodes a backend identifier
inside the CID layout so that stateless routers can demultiplex
handshakes.

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

Stateless reset tokens are a fallback: if an endpoint loses all state
for a connection (e.g., it crashed and rebooted) but the peer keeps
sending packets, it can reply with a **stateless reset**
(RFC 9000 §10.3) — a minimal packet that begins with the fixed bits
`0b01` followed by unpredictable bytes, and whose **last 16 bytes are
the stateless reset token itself** (distributed earlier inside the
encrypted `NEW_CONNECTION_ID` frame). The peer recognises its token
and immediately terminates the connection. Nothing is HMACed on the
wire — the "authentication" is simply knowing a 16-byte value that was
never sent in the clear for this connection.

## 4. Packet Protection and Header Protection (RFC 9001 §5.4)

Even the *packet number* is encrypted in QUIC. This is what prevents
passive observers from linking a 0-RTT packet to the corresponding
handshake — a property called **packet number confidentiality**. Header
protection is a QUIC-specific design (RFC 9001 §5.4) — TLS 1.3 record
padding has nothing to do with it.

The mechanics:

1. The AEAD encrypts the payload (header protection is applied *after*
   packet protection).
2. A **16-byte sample of ciphertext** is taken starting at an offset of
   4 bytes after the *start* of the packet number field — i.e., the
   receiver that doesn't yet know the PN length just samples the first
   16 bytes after the longest possible 4-byte PN. This is the
   *beginning* of the protected payload, not the tail.
3. The sample is encrypted with a separate **header protection key**
   (derived with the `"quic hp"` label): AES-based suites compute
   `AES-ECB(hp_key, sample)`, ChaCha20 suites run ChaCha20 with the
   sample as plaintext. Either way the output is a **5-byte mask**.
4. The mask is XORed in: long headers unmask the low 4 bits of byte 0
   plus the PN bytes; short headers unmask the low 5 bits (which
   includes the key phase) plus the PN bytes. Leftover mask bytes are
   unused when the PN is shorter than 4 bytes.

```
   ciphertext packet bytes:
   +----------+----------+-----------------------------+----------+
   | hdr      | pn(1-4)  | protected payload ...       | tag (16) |
   +----------+----------+-----------------------------+----------+
                          ^
                          sample = 16 bytes starting right after the
                                   packet number field (as the receiver
                                   sees it: PN assumed 4 bytes long)
                          mask   = header_protection(hp_key, sample)
                          hdr/pn ^= mask (5 bytes, LSB-aligned)
```

Because only the low bits of the PN are hidden, packet numbers are
truncated to the smallest width that still decodes — a sender must
leave the top bits implicit, and the receiver reconstructs the full
62-bit number from `largest_pn + 1` (RFC 9000 §17.1 and Appendix A,
worked through in §12 below).

## 5. Frame Types (RFC 9000 §12.4 / §19)

Inside a protected packet payload lives a sequence of complete frames.
The complete list of v1 types (RFC 9000 Table 3):

| Type byte | Frame                 | Notes                                                            |
|-----------|-----------------------|------------------------------------------------------------------|
| 0x00      | PADDING               | Zero bytes; also consumes congestion window (§13.2.7).           |
| 0x01      | PING                  | Ack-eliciting keepalive; no fields.                              |
| 0x02-0x03 | ACK                   | ACK ranges; 0x03 carries ECN counts. Not ack-eliciting.          |
| 0x04      | RESET_STREAM          | Abruptly terminate one stream: error code + final size.          |
| 0x05      | STOP_SENDING          | Ask the peer to stop sending on a stream.                        |
| 0x06      | CRYPTO                | TLS handshake bytes, with offset for out-of-order delivery.      |
| 0x07      | NEW_TOKEN             | Server-issued token for future address validation (0-RTT).       |
| 0x08-0x0f | STREAM                | Data on a stream; bits 0x04 = OFFSET, 0x02 = LEN, 0x01 = FIN.    |
| 0x10      | MAX_DATA              | Raise connection-level flow-control limit.                       |
| 0x11      | MAX_STREAM_DATA       | Raise stream-level flow-control limit.                           |
| 0x12-0x13 | MAX_STREAMS           | Raise stream-count limit (0x12 bidi, 0x13 unidir).               |
| 0x14      | DATA_BLOCKED          | Connection-level flow control blocked.                           |
| 0x15      | STREAM_DATA_BLOCKED   | Stream-level flow control blocked.                               |
| 0x16-0x17 | STREAMS_BLOCKED       | Stream-count limit reached (0x16 bidi, 0x17 unidir).             |
| 0x18      | NEW_CONNECTION_ID     | New CID + sequence + Retire Prior To + stateless reset token.    |
| 0x19      | RETIRE_CONNECTION_ID  | Drop the CID with the given sequence number.                     |
| 0x1a      | PATH_CHALLENGE        | 8 unpredictable bytes, for path validation.                      |
| 0x1b      | PATH_RESPONSE         | Echo the 8 challenge bytes back on the same path.                |
| 0x1c-0x1d | CONNECTION_CLOSE      | 0x1c = transport error, 0x1d = application error.                |
| 0x1e      | HANDSHAKE_DONE        | Sent by the server once the handshake is confirmed.              |

A payload must contain at least one frame; receiving a packet with zero
frames is a PROTOCOL_VIOLATION. The 3-bit sub-encoding inside the
STREAM type byte is worth memorising: `0x08` bare, `+0x01` FIN,
`+0x02` length present, `+0x04` offset present — e.g. `0x0b` =
STREAM with offset + length + FIN.

Streams are identified by a 62-bit integer whose low two bits encode
directionality and initiator (RFC 9000 §2.1):

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

QUIC packets of different types may be coalesced into one UDP datagram
(RFC 9000 §12.2), so the client's first datagram can carry Initial
packets; once 1-RTT keys exist, everything switches to short header
packets.

0-RTT is the optimisation where the client, having cached the server's
transport parameters and a TLS session ticket from a previous
connection, sends application STREAM frames immediately in 0-RTT
packets (which may be coalesced with the Initial). The cryptographic
detail that matters: **0-RTT keys are derived from the resumption
secret and are *not* forward-secure** (RFC 8446 §2.2, RFC 9001 §4.2.1)
— anyone who later compromises the PSK can decrypt recorded 0-RTT
data. That is precisely why replay protection exists.

The replay story has two halves. First, single-use tickets: a server
that hands out each session ticket once can reject replays, which is
why TLS 1.3 defines the per-ticket `max_early_data_size` and a
recommended ticket age check with a tolerance window. Second,
application discipline: servers must only accept 0-RTT for operations
that are safe to replay (RFC 9001 §8); treating 0-RTT like 1-RTT for
mutating requests is the classic integration bug.

## 7. Loss Detection (RFC 9002)

QUIC's loss detection is in some ways simpler and in some ways
smarter than TCP's. The spec is RFC 9002.

The big idea is **per-packet-number tracking plus a Probe Timeout
(PTO)**. There is no Reno-style retransmission timer tied to a single
"in flight" segment. Instead:

1. Every packet is acked individually via the ACK frame, which carries
   the largest acked PN plus a list of *ranges* of acked PNs.
2. *Packet-threshold loss detection* — if a packet is sent and 3 or
   more packets with higher PNs are acked (`kPacketThreshold = 3`),
   the original is declared lost (RFC 9002 §6.1).
3. *Time-threshold loss detection* — if a packet is unacked for longer
   than `kTimeThreshold * smoothed_rtt` with `kTimeThreshold = 9/8`,
   it's declared lost. The 1/8 margin is a safety factor against
   reordering.
4. *Probe Timeout (PTO)* — if no ack is received for
   `smoothed_rtt + max(4*rttvar, kGranularity) + max_ack_delay`, send
   *probe* packets (ack-eliciting frames) to elicit an immediate ACK.
   PTO does not declare loss — it keeps the loss-detection clock alive
   by forcing the peer to acknowledge.

```
   send PN=42  ────────────────────────────────────────────────
              t                                  t+PTO
              │                                   │
              │  no ack...                        │  send probe (ack-eliciting)
              │                                   │
   ack PN=43..50 arrives ─────>  declare PN=42 lost (3 packets acked above)
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
reflection-style amplification attacks. Validation completes when the
server sees a HANDSHAKE_DONE-eligible path (or the client echoes a
NEW_TOKEN on the new path); the limit is enforced per path, not per
connection.

## 9. Connection Migration

Connection migration is the single most visible feature of QUIC. The
flow is:

1. Client starts sending packets from a new 4-tuple (e.g., Wi-Fi →
   cellular handover). Because the DCID stays the same, the server
   still recognizes the connection.
2. The server replies to the new path, but it must *validate* that
   path before sending more than 3× the bytes received — i.e., the
   anti-amplification limit kicks in again for the new path.
3. Validation: server sends a `PATH_CHALLENGE` containing 8
   unpredictable bytes. Client must echo them back in a
   `PATH_RESPONSE` on the same path. Only then is the path "validated".
4. Once validated, the server can use the new path freely, and the
   connection survives the migration.

What the spec actually requires of the congestion controller after
validation (RFC 9000 §9.4): the controller and RTT estimator **must be
reset to initial values** for the new path — *unless* the address
change is port-only (the classic NAT-rebinding case), where the
endpoint MAY retain its state. There is no "shrink cwnd to half"
recommendation; plain reset is the normative behaviour, and carrying
an old path's cwnd onto a wildly different path is explicitly warned
against.

Other gotchas:

- Path MTU can differ between paths. QUIC re-measures PMTU on the new
  path using DPLPMTUD (RFC 8899, integrated into QUIC at RFC 9000
  §14.3).
- A client behind NAT can spontaneously migrate without ever
  noticing — the migration is transparent. Servers should treat
  NAT rebindings as routine.
- Non-migrating connections also deserve care: an endpoint that
  changes the DCID it sends *without* migrating should expect the
  peer's LB tier to re-hash it (that is exactly what new CIDs are
  for — "intent to change path" vs "privacy rebinding" is signaled by
  `NEW_CONNECTION_ID` / `Retire Prior To`, not by IP changes alone).

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

1. **0-RTT for mutating requests.** Replays can do real damage, and
   0-RTT keys are not forward-secure. Limit 0-RTT to idempotent
   requests; check ticket age and single-use state before processing
   anything else.
2. **Forgetting the anti-amplification limit.** A server that sends
   more than 3× received bytes before validation can be abused as an
   amplification reflector. Implementations must enforce the cap per
   path, not just per connection.
3. **Reusing a connection ID across migrations.** If the client
   intentionally changes the DCID while migrating, the server should
   *also* validate the new path with PATH_CHALLENGE; otherwise an
   on-path attacker can hijack the connection.
4. **Carrying congestion state across paths.** RFC 9000 §9.4 requires
   resetting cwnd and the RTT estimator to initial values on a
   validated path change (port-only NAT rebinding excepted). Keeping
   the old cwnd makes the sender transmit too aggressively on the new
   path until the estimator adapts.
5. **Trusting the spin bit for path measurement.** The spin bit is
   opt-in, disabled for at least 1/16 of connections, and observers
   can see it but never forge meaningful toggles into the RTT estimate
   of a well-implemented endpoint; treat it as a hint, not a source of
   truth.
6. **Assuming packet numbers are 1, 2, or 4 bytes.** The 3-byte
   encoding is legal and real (a 2-bit length field with four
   values); a decoder that only handles 1/2/4 will desynchronise on
   long-lived connections where PN gaps land in the 3-byte range.

## 12. Packet Number Decoding — Worked Example (RFC 9000 Appendix A)

The receiver recovers a full 62-bit packet number from a truncated
field using the window centered on `expected_pn = largest_pn + 1`:

```python
# RFC 9000 Appendix A - packet number decoding (transcribed from Figure 47)
def decode_pn(largest_pn, truncated_pn, pn_nbits):
    expected_pn = largest_pn + 1
    pn_win = 1 << pn_nbits
    pn_hwin = pn_win // 2
    pn_mask = pn_win - 1
    candidate = (expected_pn & ~pn_mask) | truncated_pn
    if (candidate <= expected_pn - pn_hwin
            and candidate < (1 << 62) - pn_win):
        return candidate + pn_win
    if (candidate > expected_pn + pn_hwin
            and candidate >= pn_win):
        return candidate - pn_win
    return candidate

# Worked example from RFC 9000 Appendix A:
assert decode_pn(0xa82f30ea, 0x9b32, 16) == 0xa82f9b32

print(hex(decode_pn(0xa82f30ea, 0x9b32, 16)))
print(hex(decode_pn(0xa82f30ea, 0x01, 8)))
print(hex(decode_pn(0x00ffffff, 0xff, 8)))
print(hex(decode_pn(0x0100, 0x00, 8)))
```

Real output:

```
0xa82f9b32
0xa82f3101
0xffffff
0x100
```

The first line is the RFC's own worked example: with the largest
authenticated PN at `0xa82f30ea`, a 16-bit field containing `0x9b32`
decodes to `0xa82f9b32`. The second shows the window logic: truncated
`0x01` is inside the "came before expected" half of the 8-bit window,
so it is interpreted as `+256` relative to the naive reconstruction.
Lines 3-4 confirm behaviour at window boundaries: a truncation of
`0xff` just below `0x1000000` snaps back to `0xffffff`, not
`0x10000ff`, and a fresh packet right after a roll-over decodes
exactly.

## References

- RFC 9000 — *QUIC: A UDP-Based Multiplexed and Secure Transport*.
  https://www.rfc-editor.org/rfc/rfc9000.html
- RFC 9001 — *Using TLS to Secure QUIC*. https://www.rfc-editor.org/rfc/rfc9001.html
- RFC 9002 — *QUIC Loss Detection and Congestion Control*. https://www.rfc-editor.org/rfc/rfc9002.html
- RFC 9287 — *Greasing the QUIC Bit* (the `grease_quic_bit` transport
  parameter, 0x2ab2). https://www.rfc-editor.org/rfc/rfc9287.html
- RFC 9369 — *QUIC Version 2* (v2 header forms and type codes).
  https://www.rfc-editor.org/rfc/rfc9369.html
- RFC 8899 — *Datagram Packetization Layer Path MTU Discovery*
  (DPLPMTUD). https://www.rfc-editor.org/rfc/rfc8899.html
- QUIC-LB — *draft-ietf-quic-load-balancers* (CID-based routing).
  https://datatracker.ietf.org/doc/draft-ietf-quic-load-balancers/
- RFC 8446 — *The Transport Layer Security (TLS) Protocol Version 1.3*
  (0-RTT semantics and replay risks). https://www.rfc-editor.org/rfc/rfc8446.html
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
