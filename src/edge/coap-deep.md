# CoAP Deep Dive: Constrained REST Over UDP

CoAP (RFC 7252) is what you get when you take REST apart, keep the nouns and verbs, and discard everything that costs bytes or batteries: TCP handshakes, text headers, per-request connections. What remains is a 4-byte binary header, UDP datagrams, and a reliability layer that can be switched off per message. This page is the mechanics companion to the surveys [IoT Protocols](iot-protocols.md) and [IoT Protocol Deep Dive](iot-protocols-deep.md) (which owns the AMQP model and the LwM2M object tree); the pub/sub alternative lives in [MQTT Protocol Internals](mqtt-internals.md) and is not repeated here. Every constant below was checked against the RFC text.

## The Wire: Header, Options, and Why Delta Encoding

A CoAP message is a 4-byte fixed header, a token of 0-8 bytes, a sequence of TLV options, and optionally the payload marker `0xFF` plus payload:

```text
byte 0     Ver(2) T(2) TKL(4)   version, type, token length
byte 1     Code(8)              class.detail: 0.01 = GET, 2.05 = Content
bytes 2-3  Message ID(16)       duplicate detection + ACK matching
bytes 4..  Token (TKL bytes)    client-local request identity
then       Options (TLV), then 0xFF + payload if a payload exists
```

Options are the clever part. Each option byte packs a 4-bit **option delta** (this option number minus the previous option number) and a 4-bit **option length**. Values 0-12 fit the nibble; 13 means "one extra byte holds value minus 13"; 14 means "two extra bytes hold value minus 269"; 15 is reserved. Because options must appear in ascending numeric order, delta encoding makes the common case (`Uri-Path` segments, `Content-Format`) a single byte per option, and a zero-length uint value encodes the number 0 -- an Observe registration costs exactly one byte (`0x60`).

The following program builds a real CON GET for `coap://host/temperature-sensor-array/reading` with an Observe registration, then decodes its own bytes:

```python
import struct

OPTION_NAMES = {6: "Observe", 11: "Uri-Path", 12: "Content-Format", 14: "Size2"}

def encode_get(mid, token, segments, observe=None):
    msg = struct.pack("!BBH", 0x40 | len(token), 0x01, mid) + token
    last, opts = 0, ([(6, b"")] if observe is not None else []) + \
                    [(11, s.encode("ascii")) for s in segments]
    for num, val in opts:                      # options sorted by number
        delta, length = num - last, len(val)
        d = (delta, b"") if delta < 13 else (13, bytes([delta - 13]))
        l = (length, b"") if length < 13 else (13, bytes([length - 13]))
        msg += bytes([(d[0] << 4) | l[0]]) + d[1] + l[1] + val
        last = num
    return msg                                 # GET carries no payload

def ext(buf, nib, i):                          # nibble 13 -> +1 byte, 14 -> +2
    if nib < 13: return nib, i
    if nib == 13: return 13 + buf[i], i + 1
    return 269 + int.from_bytes(buf[i:i + 2], "big"), i + 2

def decode(msg):
    vtt, code, mid = struct.unpack("!BBH", msg[:4])
    t, tkl = vtt >> 4 & 3, vtt & 0x0F
    token, i, last, opts = msg[4:4 + tkl], 4 + tkl, 0, []
    while i < len(msg) and msg[i] != 0xFF:
        b, i = msg[i], i + 1
        d, i = ext(msg, b >> 4, i)
        l, i = ext(msg, b & 15, i)
        opts.append((last + d, msg[i:i + l])); last += d; i += l
    return t, tkl, code, mid, token, opts

m = encode_get(mid=0xBC90, token=bytes.fromhex("715A"),
               segments=["temperature-sensor-array", "reading"], observe=0)
for r in range(0, len(m), 8):                  # hex dump, 8 bytes per row
    print(" ".join("%02x" % b for b in m[r:r + 8]).ljust(23),
          "".join(chr(b) if 32 <= b < 127 else "." for b in m[r:r + 8]))
t, tkl, code, mid, token, opts = decode(m)
print("type=%d (0=CON)  TKL=%d  code=%d.%02d (GET)  MID=0x%04x  token=%s"
      % (t, tkl, code >> 5, code & 31, mid, token.hex()))
for num, val in opts:
    print("option %-2d %-10s len=%d value=%r" % (num, OPTION_NAMES.get(num, "?"),
          len(val), val.decode("ascii") if num == 11 else int.from_bytes(val, "big")))
print("header+options=%d bytes; Ver=%d, T=%d" % (len(m), m[0] >> 6, m[0] >> 4 & 3))
```

```text
42 01 bc 90 71 5a 60 5d B...qZ`]
0b 74 65 6d 70 65 72 61 .tempera
74 75 72 65 2d 73 65 6e ture-sen
73 6f 72 2d 61 72 72 61 sor-arra
79 07 72 65 61 64 69 6e y.readin
67                      g
type=0 (0=CON)  TKL=2  code=0.01 (GET)  MID=0xbc90  token=715a
option 6  Observe    len=0 value=0
option 11 Uri-Path   len=24 value='temperature-sensor-array'
option 11 Uri-Path   len=7 value='reading'
header+options=41 bytes; Ver=1, T=0
```

The first option byte `0x60` is delta 6 / length 0 (an Observe registration); `0x5D 0x0B` is delta 5 (option 11 = `Uri-Path`) with extended length 13+11=24, so the long segment name costs only two length bytes. Total: 41 bytes for a full request against a deep resource path -- compare a typical HTTP/1.1 GET at 150+ bytes of text.

## CON, NON, ACK, RST: The Reliability State Machine

The 2-bit type field selects one of four message types:

- **CON (Confirmable, 0)**: the receiver MUST either ACK it or reject it with RST. The only type with retransmission.
- **NON (Non-confirmable, 1)**: fire-and-forget, but still carries a Message ID so the receiver can suppress duplicates (Section 4.5 of RFC 7252).
- **ACK (2)**: echoes the Message ID of the CON it acknowledges, and either carries the response (piggybacked) or is Empty.
- **RST (3)**: "I have no context for this message" -- always Empty; a client's RST is how an Observe subscription is cancelled.

An **Empty message** (Code 0.00, token length 0) is a fourth thing entirely: an empty ACK stops a sender's retransmissions, and a CON Empty message is a **ping** -- the standard CoAP liveness probe, answered with RST.

The retransmission state machine (Section 4.2 of RFC 7252) works like this: sample the initial timeout **once per exchange** uniformly in `[ACK_TIMEOUT, ACK_TIMEOUT * ACK_RANDOM_FACTOR]` (defaults 2 s and 1.5, so 2.0-3.0 s); on each timeout, retransmit the identical bytes (same MID, same token), increment the counter, and double the timeout; when the counter reaches `MAX_RETRANSMIT` (default 4) on a timeout -- after 5 total transmissions -- cancel and report failure to the application.

```text
 sender                                        receiver
   | CON [MID=0xbc90] GET /temp (Token 0x715a)   |
   |-------------------------------------------->|  first transmission, lost
   |       w = U(2.0 s, 3.0 s), sampled once     |
   | retransmit: same MID, same token, same body |
   |-------------------------------------------->|  attempt 2
   |<--------------------------------------------|  ACK [MID=0xbc90]
   | 2.05 Content (Token 0x715a) "22.5 C"        |  piggybacked response
```

If the server cannot respond immediately, it sends an **Empty ACK** (stopping the backoff machine) and later sends the response as a separate CON message, which the client must in turn ACK -- the "separate response" of Section 5.2.2. Derived constants bound every exchange (Section 4.8.2 and Appendix A of RFC 7252, using the defaults):

| Constant | Formula | Default value |
|---|---|---|
| MAX_TRANSMIT_SPAN | ACK_TIMEOUT * (2^MAX_RETRANSMIT - 1) * ACK_RANDOM_FACTOR | 45 s |
| MAX_TRANSMIT_WAIT | ACK_TIMEOUT * (2^(MAX_RETRANSMIT+1) - 1) * ACK_RANDOM_FACTOR | 93 s |
| MAX_LATENCY / PROCESSING_DELAY | arbitrarily fixed 100 s / set equal to ACK_TIMEOUT | 100 s / 2 s |
| EXCHANGE_LIFETIME | MAX_TRANSMIT_SPAN + 2*MAX_LATENCY + PROCESSING_DELAY | 247 s |

EXCHANGE_LIFETIME is the dedup window: a receiver must remember the MIDs it has seen for that long, because a retransmission can outlive the round trip itself (NON messages stay deduplicated for NON_LIFETIME = span + MAX_LATENCY = 145 s). Note 45 s is the worst-case time of the **last** transmission; the sender waits one more doubled window before giving up entirely. The model below reproduces the ladder with seeded jitter:

```python
import random

ACK_TIMEOUT, ACK_RANDOM_FACTOR, MAX_RETRANSMIT = 2.0, 1.5, 4

def exchange(seed, ack_abs=None):
    """RFC 7252 4.2: sample the initial timeout ONCE, double per retransmit."""
    rng = random.Random(seed)
    w = rng.uniform(ACK_TIMEOUT, ACK_TIMEOUT * ACK_RANDOM_FACTOR)
    now, txs = 0.0, []
    for _ in range(MAX_RETRANSMIT + 1):        # initial + MAX_RETRANSMIT retries
        txs.append(now)
        if ack_abs is not None and ack_abs <= now + w:
            return txs, "ACK received: exchange closes", ack_abs
        now += w
        w *= 2                                 # exponential backoff
    return txs, "give up, inform application of failure", now  # after 5th window

def report(title, seed, ack_abs):
    txs, verdict, close = exchange(seed, ack_abs)
    print(title)
    for k, t in enumerate(txs, 1):
        print("  tx#%d at t=%6.2f s" % (k, t))
    print("  %s at t=%.2f s\n" % (verdict, close))

report("Scenario A: lossy link, no ACK ever (seed=7)", 7, None)
report("Scenario B: silent server until t=4.10 s, then empty ACK (seed=7)", 7, 4.10)
span = ACK_TIMEOUT * (2 ** MAX_RETRANSMIT - 1) * ACK_RANDOM_FACTOR
wait = ACK_TIMEOUT * (2 ** (MAX_RETRANSMIT + 1) - 1) * ACK_RANDOM_FACTOR
print("derived: MAX_TRANSMIT_SPAN=%g s  (first transmission -> last transmission)" % span)
print("derived: MAX_TRANSMIT_WAIT=%g s  (first transmission -> give up)" % wait)
print("derived: EXCHANGE_LIFETIME=%g s = span + 2*MAX_LATENCY(100) + PROCESSING_DELAY(=ACK_TIMEOUT)"
      % (span + 2 * 100 + ACK_TIMEOUT))
```

```text
Scenario A: lossy link, no ACK ever (seed=7)
  tx#1 at t=  0.00 s
  tx#2 at t=  2.32 s
  tx#3 at t=  6.97 s
  tx#4 at t= 16.27 s
  tx#5 at t= 34.86 s
  give up, inform application of failure at t=72.04 s

Scenario B: silent server until t=4.10 s, then empty ACK (seed=7)
  tx#1 at t=  0.00 s
  tx#2 at t=  2.32 s
  ACK received: exchange closes at t=4.10 s

derived: MAX_TRANSMIT_SPAN=45 s  (first transmission -> last transmission)
derived: MAX_TRANSMIT_WAIT=93 s  (first transmission -> give up)
derived: EXCHANGE_LIFETIME=247 s = span + 2*MAX_LATENCY(100) + PROCESSING_DELAY(=ACK_TIMEOUT)
```

The sampled jitter (2.32 s here) is deliberate: simultaneous retransmissions from many devices would otherwise synchronize on every lost datagram, so RFC 7252 bakes in per-exchange randomization the way Ethernet does for backoff slots. With the minimum sample of 2.0 s the give-up time is 62 s; the worst case of 3.0 s reaches the 93 s MAX_TRANSMIT_WAIT bound. Also note `NSTART = 1` by default: one outstanding CON exchange per peer, so a lossy link serializes interactions badly and every retransmission blocks the queue behind it.

## Token vs Message-ID: Two Namespaces With Different Jobs

| Property | Message ID (16 bits) | Token (0-8 bytes) |
|---|---|---|
| Layer | message layer, per datagram | application layer, per request |
| Chosen by | sender of the CON/NON | client, "could have been called a request ID" (RFC 7252 Sec. 5.3.1) |
| Echoed by | ACK and RST | every response; server MUST echo it unmodified |
| Purpose | duplicate suppression + ACK matching | matching responses to requests across piggyback/separate/proxy paths |
| Security note | trivially guessable, fine | SHOULD carry 32+ bits of randomness without DTLS, to stop response spoofing |

Confusing the two is the classic CoAP interview trap. In an Observe relationship the token does the heavy lifting permanently: every future notification repeats the registering GET's token, so the client routes notifications among concurrent subscriptions without any per-notification request. The Message ID, by contrast, is recycled per datagram and dies at EXCHANGE_LIFETIME.

## Observe (RFC 7641): Server Push Without a Broker

A GET carrying `Observe = 0` (option number 6) **registers** the client; the server replies normally and then sends unsolicited 2.05 notifications, each carrying a strictly increasing 24-bit sequence number. `Observe = 1` on a GET **deregisters**; a client RST on a notification cancels from the server side.

```text
 client                              server
   |  CON GET /temp (Observe=0)  -->  |  register; token binds the subscription
   |  <-- 2.05 (Observe=12) 22.5 C    |  notification, piggybacked on the ACK
   |  <-- 2.05 (Observe=60) 21.9 C    |  separate CON notification; client ACKs
```

- **Ordering** is 24-bit serial-number arithmetic (RFC 1982): a notification is fresher if `(V1 < V2 and V2 - V1 < 2^23)` or `(V1 > V2 and V1 - V2 > 2^23)`, or if more than 128 seconds have elapsed since the freshest one -- the 128 s number sits just above MAX_LATENCY so the comparison stays meaningful across wraps.
- **No delivery guarantee per state**: the server MAY skip notifications for intermediate states when the network cannot keep up (RFC 7641 Sec. 3.3.1). Observe delivers the *latest* state, not every state; if you need every sample, publish each one or use a broker.
- **Freshness has a timer**: notifications age out like cached HTTP responses via Max-Age; a client that stops receiving them MUST stop trusting the last value and re-register, waiting a random 5-15 s to avoid re-registration storms.

## Blockwise Transfer (RFC 7959): Big Payloads, Small Datagrams

A CoAP message should fit the link (a 6LoWPAN frame leaves roughly 60-80 bytes after headers). RFC 7959 adds two options -- **Block1** (27) for request bodies, **Block2** (23) for response bodies -- plus `Size1` (60) and `Size2` (28) hints. The option value packs `NUM | M | SZX`: a block number, a 1-bit "more" flag, and a 3-bit size exponent giving 2^(SZX+4) bytes, i.e. 16 B at SZX=0 up to the 1024 B maximum at SZX=6 (SZX=7 is reserved).

The server stays stateless across blocks: each GET with a Block2 option is answered from scratch, so a crashed client resumes by asking for the next NUM, and a proxy can cache individual blocks. With Observe, RFC 7959 Sec. 2.6 defines the interaction: observations cover the whole resource (you cannot observe a single block), the server pushes only the **first block** of each notification, and the client fetches the remaining blocks itself with ordinary Block2 GETs -- and if the resource changed mid-transfer, the client must detect the mismatch and restart.

## Resource Discovery: /.well-known/core

Section 7.1 of RFC 7252 reserves the `/.well-known/core` path (RFC 5785's well-known scheme) and RFC 6690 defines the payload: a CoRE Link Format document listing `<URI>` entries with attributes such as `rt` (resource type), `if` (interface), `ct` (content-format code), and `obs` (observable). `GET /.well-known/core?rt=temperature` is the constrained-device analogue of a service registry query -- one datagram, a few dozen bytes, no lookup service. The Resource Directory (RFC 9176) scales this pattern: devices register their link set with a directory entity instead of answering every discovery query themselves, which matters when the querier is meters away over a battery radio.

## Security: DTLS, OSCORE, and the Transports Question

- **DTLS 1.2** (RFC 6347) is the default: TLS minus TCP, with handshakes re-engineered to survive datagram loss. Section 9 of RFC 7252 defines three credential modes -- Pre-Shared Key, Raw Public Key, certificates. RFC 7925 profiles this for IoT, makes `TLS_PSK_WITH_AES_128_CCM_8` the mandatory-to-implement ciphersuite (8-byte MAC, AES-CCM, one pass over the data), and mandates session resumption in constrained clients because full handshakes are expensive on radio time.
- **OSCORE** (RFC 8613) moves protection inside the message: option 9 carries the encrypted object, "Class E" options (URI path, payload...) move into the COSE ciphertext, and sequence numbers give end-to-end replay protection. Because the transport sees only opaque bytes, OSCORE survives proxies, caches, and gateway translation -- the pieces DTLS cannot cover.
- **Transports**: RFC 8323 defines CoAP over TCP, TLS, and WebSockets, dropping the Ver/Type/MID fields entirely (TCP already provides retransmission and deduplication) and adding a variable-length field instead. It exists for enterprise firewalls and NAT traversal -- TCP bindings mean 386 minutes average idle timeout vs 160 seconds for UDP -- but the RFC is explicit that CoAP over UDP remains the recommended transport for constrained networks. A related tightening, RFC 9175 (Echo, Request-Tag, Token Processing), updates RFC 7252 itself against replay and cross-protocol attacks.

## CoAP vs MQTT vs HTTP on a Constrained Device

Mechanics-level comparison (the feature-level table lives in [IoT Protocol Deep Dive](iot-protocols-deep.md); MQTT delivery semantics in [MQTT Protocol Internals](mqtt-internals.md)):

| Property | CoAP (RFC 7252) | MQTT 5 | HTTP/1.1 |
|---|---|---|---|
| Transport | UDP + DTLS (TCP per RFC 8323) | TCP + TLS | TCP + TLS |
| Model | REST + observe push | brokered pub/sub | request/response |
| Smallest request | 4 B header + options | 2 B fixed header | hundreds of bytes of text |
| Reliability | per-message CON backoff, NSTART=1 | broker-side QoS 0/1/2 | TCP only |
| Push | observe (server-initiated) | subscriptions | none native |
| Idle cost | zero state between exchanges | persistent session | connection or reconnect |
| Multicast | NON + group communication | no | no |

The design tension to articulate in an interview: CoAP keeps **zero connection state** (ideal for sleeping devices that wake, ask once, and return to sleep) but pays with stop-and-wait reliability and a 16-bit MID; MQTT pays a persistent TCP session and broker infrastructure to get session resumption and durable queues for the same sleeping device.

## LwM2M: The Flagship CoAP Deployment

OMA LightweightM2M is a full device-management stack built on CoAP, and it is where most production CoAP traffic lives: bootstrap, registration, and firmware update on CoAP/UDP+DTLS. The object model (`/3/0/0` = Device/Manufacturer and friends) is walked through in [IoT Protocol Deep Dive](iot-protocols-deep.md); the deployment facts: releases are tracked on OMA's public listing -- LwM2M 1.0 (2013), 1.1 (approved 2018-07-10, adding TCP/TLS and OSCORE transports), 1.2 (2020-11-10), 1.2.1 (2022-12-09), and 1.2.2 (2024-06-13), the version OMA's smart-water-utility work builds on. The open-source reference stack is Eclipse's: the Leshan server and bootstrap server, the Wakaama client library for MCUs, and the Californium Java CoAP framework that Leshan builds on. Thread devices also speak CoAP internally for commissioning and application payloads (see [Thread and Matter Deep Dive](thread-matter.md)), and CoAP's multicast NON messaging is the substrate for group commands in mesh-like deployments.

## Failure Modes and Interview Gotchas

- **MID wraparound**: 16 bits cycles every 65536 messages; duplicate suppression is bounded by EXCHANGE_LIFETIME, so a chatty sender that wraps within 247 s can alias an old exchange on a lossy path.
- **NSTART=1 serialization**: one outstanding CON per peer means each retransmission cycle (up to 93 s) stalls everything behind it; batch telemetry should use NON.
- **Observe is not a queue**: skipped intermediate states are by design; Max-Age, not the network, tells you when the last notification is too old to trust. Comparing sequence numbers without the 2^23 serial-arithmetic rule silently drops notifications after 16,777,216 updates.
- **Blockwise state poisoning**: changing a resource between blocks can mix two versions into one reassembled body unless the client validates (ETag/Size2) and restarts.
- **DTLS handshake cost**: full PSK handshakes cost multiple round trips; RFC 7925's session resumption is not optional for battery devices -- and probing liveness with an empty CON can be ambiguous behind firewalls that drop RSTs.

## References

1. [RFC 7252: The Constrained Application Protocol (CoAP)](https://www.rfc-editor.org/rfc/rfc7252) -- header format, message types, transmission parameters (Table 2, Section 4.8), deduplication (4.5), tokens (5.3.1), discovery (7.1), security (9).
2. [RFC 7641: Observing Resources in CoAP](https://www.rfc-editor.org/rfc/rfc7641) -- Observe option 6, register/deregister, 24-bit ordering arithmetic, freshness model.
3. [RFC 7959: Block-Wise Transfers in CoAP](https://www.rfc-editor.org/rfc/rfc7959) -- Block1/Block2/Size options, SZX sizes, Observe interaction (2.6).
4. [RFC 6690: CoRE Link Format](https://www.rfc-editor.org/rfc/rfc6690) -- /.well-known/core payloads and attributes.
5. [RFC 8323: CoAP over TCP, TLS, and WebSockets](https://www.rfc-editor.org/rfc/rfc8323) -- elided fields, length framing, transport trade-offs.
6. [RFC 8613: OSCORE](https://www.rfc-editor.org/rfc/rfc8613) -- option 9, Class E options, end-to-end object security.
7. [RFC 7925: TLS/DTLS Profiles for IoT](https://www.rfc-editor.org/rfc/rfc7925) -- PSK ciphersuite mandate, session resumption requirement.
8. [RFC 9176: CoRE Resource Directory](https://www.rfc-editor.org/rfc/rfc9176) -- directory-based discovery at scale.
9. [OMA LwM2M release listing](https://openmobilealliance.org/release/LightweightM2M/) -- version history 1.0 through 1.2.2; [OMA SpecWorks LwM2M overview](https://omaspecworks.org/what-is-oma-specworks/iot/lightweight-m2m-lwm2m/) and conformance tooling.
10. [Eclipse Leshan](https://eclipse.dev/leshan/) (LwM2M server), [Californium](https://eclipse.dev/californium/) (Java CoAP framework), [Wakaama](https://eclipse.dev/wakaama/) (C client library).
