# IoT Protocol Deep Dive: MQTT, CoAP, AMQP, LwM2M

## Overview

The IoT application layer is dominated by four protocols with very different philosophies: **MQTT** (lightweight pub/sub over TCP), **CoAP** (RESTful request/response over UDP), **AMQP 1.0** (a fully-featured message queueing protocol with transactions and durable links), and **LwM2M** (a device-management profile layered on CoAP). This chapter goes inside the wire format, the QoS machinery, the queue/link models, and the object model so that you can pick the right protocol for a given deployment and reason about failure modes.

## MQTT Internals

### Packet Format

Every MQTT 5 packet starts with a fixed header: a single byte that combines the packet type (4 bits) and per-type flags (4 bits), followed by a variable-length *Remaining Length* field encoded with 7-bit groups (the high bit of each byte is a continuation flag, allowing up to 4 bytes for lengths up to 256 MB):

```
Byte 1: [ Pkt Type (4) | Flags (4) ]
Byte 2..5: Remaining Length (1-4 bytes, 7 bits each + continuation)
Body: Variable header + Payload
```

| Type | Value | Direction | Purpose |
|------|-------|-----------|---------|
| CONNECT | 1 | C→S | Open session, specify client ID, will, credentials |
| CONNACK | 2 | S→C | Session-present flag, reason code |
| PUBLISH | 3 | both | Carries a topic + payload |
| PUBACK / PUBREC / PUBREL / PUBCOMP | 4–7 | both | QoS 1 and QoS 2 handshakes |
| SUBSCRIBE / SUBACK | 8/9 | C→S, S→C | Topic filter + granted QoS |
| PINGREQ / PINGRESP | 12/13 | both | Keep-alive |
| DISCONNECT | 14 | both | Orderly teardown |

### Publish/Subscribe Model

A publisher emits a `PUBLISH` to a *topic* (a UTF-8 string with `/` separators, e.g. `factory/line3/oven2/temperature`). It never learns who consumes the data — that is the broker's job. Subscribers register *topic filters* containing wildcards: `+` (single level, `factory/+/oven2/temperature`) and `#` (multi-level suffix, `factory/line3/#`). The broker maintains a *subscription tree* (typically a trie) so that matching is O(filter length) rather than O(subscribers).

The decoupling has three dimensions:

- **Space decoupling** — publisher and subscriber don't know each other.
- **Time decoupling** — with *persistent sessions*, messages for offline clients are queued.
- **Synchronisation decoupling** — publisher doesn't block on subscribers.

### QoS Levels

| Level | Wire handshake | Deliveries | Overhead |
|-------|----------------|------------|----------|
| 0 (at-most-once) | Single PUBLISH | 0 or 1, no retry | lowest |
| 1 (at-least-once) | PUBLISH → PUBACK | ≥1, possible duplicates | +1 RTT |
| 2 (exactly-once) | PUBLISH → PUBREC → PUBREL → PUBCOMP | exactly 1 | +2 RTT, broker must dedupe by `PacketIdentifier` |

The 4-step QoS 2 flow looks like:

```
Publisher                  Broker                    Subscriber
   |--- PUBLISH(id=42) ----->|                            |
   |<-- PUBREC(id=42) -------|                            |
   |                          |--- PUBLISH(id=42) ------->|
   |                          |<-- PUBREC(id=42) ---------|
   |--- PUBREL(id=42) ------->|                            |
   |<-- PUBCOMP(id=42) -------|                            |
   |                          |--- PUBREL(id=42) -------->|
   |                          |<-- PUBCOMP(id=42) --------|
```

Both hops are independently QoS-2. The publisher stores the message until it sees PUBCOMP; the broker stores it until it sees PUBREL from the publisher (signalling "you may release it"). This avoids the famous *exactly-once* impossibility of two independent hops — each hop is itself exactly-once.

### Retained Messages

A `PUBLISH` with the `RETAIN` flag set instructs the broker to store the *latest* payload for that topic. Any future subscriber whose filter matches the topic immediately receives the retained message (with the `RETAIN` flag set in the delivery, so it can be distinguished from a live message). This is the canonical way to publish *state* (e.g. a switch position) rather than *events* (button presses). Publishing a zero-byte retained message clears the retained value.

### Session State, Will, and Shared Subscriptions

- **Clean Start / Session Expiry (MQTT 5)** — A session holds subscription state and queued QoS ≥1 messages. `Clean Start=true` discards state on disconnect; a non-zero `Session Expiry Interval` keeps it for that many seconds.
- **Last Will and Testament (LWT)** — A client specifies a topic + payload + QoS in CONNECT. If the broker detects an ungraceful disconnect (keep-alive timeout, transport RST), it publishes the will. Common pattern: clients publish `{"online": false}` as their will to a `status/<client-id>` topic; consumers watch `status/+/online`.
- **Shared Subscriptions** — A topic filter prefixed with `$share/<group-id>/` distributes messages among group members round-robin (or by broker policy). This is the load-balancing primitive — useful when many workers consume from one topic.

### A Minimal Subscribe + Publish (Python, paho-mqtt)

```python
import paho.mqtt.client as mqtt

def on_connect(c, *a):
    c.subscribe("sensors/+/temp", qos=1)

def on_message(c, _ctx, msg):
    print(msg.topic, msg.payload, msg.retain, msg.qos)

c = mqtt.Client(client_id="edge-gw-1", protocol=mqtt.MQTTv5)
c.will_set("status/edge-gw-1", payload=b'{"online":false}', qos=1, retain=True)
c.on_connect = on_connect
c.on_message = on_message
c.connect("broker.local", 1883, keepalive=30)
c.loop_forever()
```

## CoAP Internals

### Message Format

CoAP (RFC 7252) packs a request or response into a 4-byte fixed header followed by a token (0–8 bytes), a series of TLV *options*, and an optional payload marker (`0xFF`) + payload:

```
 0                   1                   2                   3
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Ver(2) | T(2) |   TKL(4)   |     Code(8)     |  Message ID(16) |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Token (0..8 bytes) ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Options (variable) ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| 0xFF | Payload (variable) ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `Ver` = 1 (current CoAP version).
- `T` = type: CON (0), NON (1), ACK (2), RST (3).
- `TKL` = token length.
- `Code` is split into a 3-bit class (0=request, 2=success, 4=client-error, 5=server-error) and a 5-bit detail: e.g. `0.01` = GET, `2.05` = Content, `4.04` = Not Found.
- `Message ID` is a 16-bit integer used for deduplication and ACK matching. The same MID + source endpoint identifies a retransmission.

### Confirmable / Non-Confirmable

- **CON** requires an ACK. If none arrives within `ACK_TIMEOUT` (default 2 s, randomized to ±`ACK_RANDOM_FACTOR` = 1.5), the sender retransmits with exponential back-off up to `MAX_RETRANSMIT` (default 4) times. This is a *stop-and-wait* reliability layer — only one outstanding CON per peer at a time.
- **NON** is fire-and-forget, but the recipient still uses the MID to deduplicate (a sensor that transmits the same reading twice on a flaky link won't be counted twice).
- **RST** (reset) is a sender's way of saying "I have no context for this — stop." A server receiving RST for an Observe registration treats it as cancellation.

### Block-wise Transfer (RFC 7959)

A single CoAP message must fit in an IP packet (and ideally in a single 802.15.4 frame after 6LoWPAN compression, ~80 bytes of payload). For firmware updates or large sensor dumps, CoAP chunks the body using the **Block1** (request) and **Block2** (response) options:

```
Block option value: NUM (variable bits) | M (1 bit "more") | SZX (3 bits)
SZX=0 → 16 bytes, SZX=1 → 32, ... SZX=6 → 1024 bytes

GET /fw/image.bin
Block2: NUM=0, M=0, SZX=6  → "send me block 0, 1024-byte chunks"

2.05 Content
Block2: NUM=0, M=1, SZX=6  → "here is block 0, there is more"
Payload: 1024 bytes

GET /fw/image.bin
Block2: NUM=1, M=0, SZX=6
... loop until M=0
```

The server is stateless across block requests — it re-derives the offset from the Block2 option each time — so a crashed client can resume from any block.

### Observe (RFC 7641)

A `GET` with the `Observe` option (option number 6) registers the client for future notifications. The server later sends 2.05 responses carrying a monotonically-increasing `Observe` value, so the client can order and deduplicate notifications. This turns the RESTful request/response model into a lightweight pub/sub — closer to MQTT than to HTTP SSE.

### DTLS and OSCORE

CoAP secures the transport with **DTLS** (typically AES-CCM over UDP, RFC 9200 series) or, more recently, **OSCORE** (RFC 8613), which provides end-to-end object security independent of the transport and survives proxying. OSCORE is preferred when intermediaries (CoAP caches, border routers) terminate the transport.

## AMQP 1.0

AMQP 1.0 (ISO/IEC 19464) is not just a wire protocol — it is a *connection* protocol for a typed, framed, multiplexed binary channel. Its model is *links* and *transfers*, not just topics.

### Frame Structure

Every AMQP 1.0 frame begins with an 8-byte header (size, DOFF, frame type, channel) followed by one or more *performatives* encoded with AMQP type encoding:

```
+0..3  Size (uint32)        — total frame length including this header
+4     DOFF (uint8)         — data offset in 4-byte words (default 2)
+5     Type (uint8)         — 0=AMQP, 1=SASL
+6..7  Channel (uint16)     — multiplexed logical channel
+8..   AMQP performative(s) + body bytes
```

There are 5 layers of performative:

1. **OPEN** — negotiate container-id, max-frame-size, idle-time-out.
2. **BEGIN/END** — open/close a *session* (a unidirectional flow-control boundary).
3. **ATTACH/DETACH** — establish a *link* (a directed edge with a *role*: sender or receiver, an *address*, a *source*/*target* filter, and *settlement mode*).
4. **TRANSFER/DISPOSITION** — move a *message* (with its AMQP-encoded application data) along a link, and settle the delivery (accept/reject/release/modify).
5. **FLOW** — link credit: how many more transfers the receiver will accept, and a window for outgoing bytes.

### Queue Model and Transactions

A *node* in AMQP 1.0 is anything addressable: a queue, a topic, a stream, a router. Links attach to nodes. A broker can be a *queue* (point-to-point, store-and-forward, competing consumers) or a *topic* (fan-out, ephemeral). The protocol itself does not mandate either; it gives the building blocks.

**Transactions** in AMQP 1.0 are carried by the `txn` class. A coordinator (the broker) issues a *txn-id*; subsequent TRANSFER frames carry that txn-id in their `transaction-id` field. A DISPOSITION with `settled=true` and a transactional outcome commits or rolls back all transfers under that txn-id atomically:

```
Coordinator → client: txn-id = "abc123"   (DECLARE txn)
Sender → coordinator: TRANSFER(msg1, txn-id=abc123)
Sender → coordinator: TRANSFER(msg2, txn-id=abc123)
Sender → coordinator: DISPOSITION( txn-id=abc123, accepted, settled )
Coordinator: commits BOTH msg1 and msg2 atomically; or ROLLBACK discards both.
```

This is *distributed XA-style* transactions, but framed inside AMQP. Apache Qpid, Solace, Azure Service Bus, and ActiveMQ Artemis all speak AMQP 1.0.

### Comparison to MQTT

AMQP's per-message overhead is larger (typed binary encoding, mandatory link negotiation). MQTT wins for raw throughput on telemetry. AMQP wins for **transactions, multi-recipient routing, and message format interoperability** (AMQP type system encodes maps, UUIDs, decimals, etc.).

## OMA LwM2M

**Lightweight Machine-to-Machine** (LwM2M, Open Mobile Alliance) is a *device management and telemetry profile* on top of CoAP/UDP (or SMS). Where MQTT is "just" pub/sub, LwM2M specifies the entire lifecycle of a constrained device: bootstrap, registration, observation, firmware update, connectivity monitoring, location.

### Object Model

Every resource on an LwM2M device is addressed through a uniform `/<ObjectID>/<InstanceID>/<ResourceID>` path, mirroring the CoAP URI scheme. Objects are *standardised* with a registry (e.g. Object 0 = LwM2M Security, Object 3 = Device, Object 5 = Firmware Update, Object 19 = BinaryAppDataContainer).

```
Object 3 (Device)
  └── Instance 0
        ├── Resource  0 : Manufacturer       (r, string)
        ├── Resource  1 : Model Number       (r, string)
        ├── Resource  9 : Battery Level      (r, 0..100)
        ├── Resource 10 : Memory Free        (r, integer bytes)
        └── Resource 13 : Current Time       (rw, Unix epoch)

URI:  coap://device/3/0/13   → "read Current Time of Device Object Instance 0"
```

Resources carry **operations** (R/W/E = read/write/execute), **data type** (integer, string, opaque, time, float, objlink), and **multiple-instance** flags. The model is rich enough to express *any* sensor/actuator — a temperature sensor is just `Object 3303 (Temperature) / Instance 0 / Resource 5700 (Sensor Value)`.

### Interfaces

LwM2M defines four client-side interfaces:

- **Bootstrap Interface** — the client contacts a bootstrap server to obtain the security objects (PSK credentials, server URIs) it will use for normal operation.
- **Client Registration Interface** — `POST /rd` to the LwM2M server; client registers its objects and an endpoint name. The server holds the registration for a TTL; the client refreshes periodically.
- **Device Management & Service Enablement Interface** — the server does CoAP `READ`, `WRITE`, `EXECUTE`, `WRITE-ATTRIBUTES` (configuring observation parameters like minimum/maximum period, threshold), `DISCOVER`, `CREATE`, `DELETE` on individual resources or object instances.
- **Information Reporting Interface** — the server sends a CoAP `GET` with the Observe option, then receives async `2.05 Content` notifications when the resource changes (periodically or on threshold).

### Firmware Update (Object 5)

A canonical LwM2M workflow that exercises the whole stack:

```
1. WRITE  /5/0/3  = "https://update.example.com/fw-v2.bin"   (package URI)
2. EXECUTE /5/0/2                                           (Download)
   → state 2 (Downloading), poll /5/0/3 (state) until 3 (Downloaded)
3. EXECUTE /5/0/5                                           (Update)
   → state 4 (Updating), device reboots, comes back as v2
4. WRITE  /5/0/5  = 0                                       (Update Result = 0 → success)
```

The same sequence works across every LwM2M 1.x device — no per-vendor protocol.

## Protocol Comparison Table

| Property            | MQTT 5               | CoAP (RFC 7252)         | AMQP 1.0                   | LwM2M 1.1              |
|---------------------|----------------------|-------------------------|----------------------------|------------------------|
| Transport           | TCP/TLS, WS          | UDP (DTLS)              | TCP/SASL/TLS               | UDP/DTLS (over CoAP)   |
| Messaging style    | Pub/sub (broker)     | Request/response + Observe | Queue, pub/sub, both     | Object-model RPC      |
| Reliability         | QoS 0/1/2 in protocol | CON/ACK + block-wise   | Transfers + transactions   | Inherits CoAP          |
| Header overhead     | 2+ bytes             | 4+ bytes                | 8+ bytes (per frame)       | 4+ (CoAP) + URI        |
| Multiplexing        | 1 topic tree         | 1 UDP socket            | Multiple channels/links    | Per-resource           |
| Transactions        | No (no atomic ack)   | No                      | Yes (txn class)            | No                     |
| Stateful model      | Session + retained   | Stateless               | Links + sessions           | Registered objects     |
| Typical MTU         | 256 MB (enc limit)   | ~1280 B, block-wise     | Configurable (max-frame)   | 1280 B, block-wise     |
| Best for            | Telemetry, pub/sub fanout | Constrained sensor reading | Mission-critical messaging | Device management, FOTA |

## Interview Angle

> **"Walk me through MQTT QoS 2. Why is it four packets instead of three?"**

A three-packet protocol that just ACKs the publisher would still let the broker deliver the message twice if the publisher's original PUBLISH was retransmitted (because the publisher didn't get the ACK) *and* the broker forwarded it again (because it didn't know the publisher had received the ACK). The four-step PUBREC→PUBREL→PUBCOMP dance splits the operation into two halves: PUBREC says "broker received and stored," PUBREL says "publisher agrees — release and stop holding," PUBCOMP confirms release. The broker only forwards after PUBREL and stops keeping the dedup entry after PUBCOMP — so the message is published exactly once on each hop.

> **"When would you pick LwM2M over MQTT for a fleet of 100k smart meters?"**

LwM2M gives you a *standardised* data model and a management surface: battery level, firmware update, connectivity monitoring, location — all out of the box. With MQTT you'd design your own JSON schema and lifecycle messages, and you'd need a side channel (HTTP, custom MQTT topics) for firmware update. LwM2M runs over UDP/CoAP, so devices can sleep without keeping a TCP connection alive — crucial for battery-powered meters. The trade-off: fewer off-the-shelf brokers (Leshan, Wakaama, Cumulocity) and a smaller ecosystem than MQTT.

## Key References

- MQTT 5.0 specification (OASIS Standard, 2019) — https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
- RFC 7252 — The Constrained Application Protocol (CoAP) — https://www.rfc-editor.org/rfc/rfc7252
- RFC 7959 — Block-Wise Transfers in CoAP — https://www.rfc-editor.org/rfc/rfc7959
- RFC 7641 — Observing Resources in CoAP — https://www.rfc-editor.org/rfc/rfc7641
- AMQP 1.0 specification (OASIS, ISO/IEC 19464) — https://docs.oasis-open.org/amqp/core/v1.0/amqp-core-complete-v1.0.pdf
- OMA LwM2M 1.1 specification — https://www.openmobilealliance.org/release/LightweightM2M/V1_1-20200910-L/OMA-ETS-LightweightM2M-V1_1-20200910-L.pdf
- Eclipse Leshan (reference LwM2M server) — https://eclipse.dev/leshan/
