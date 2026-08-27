# MQTT Protocol Internals: QoS Machines, Sessions, and Brokers

MQTT's design center is a smoke detector with a coin cell talking to a broker over a flaky cellular link. Every protocol decision follows from that: a two-byte minimum header, one persistent TCP connection per client instead of request/response churn, and a broker that owns fan-out, queuing, and presence so the endpoints stay dumb. The existing [IoT protocol deep dive](./iot-protocols-deep.md) surveys MQTT alongside CoAP, AMQP, and LwM2M; this page goes one level down into the state machines, the flow-control rules, the matching costs inside brokers, and a measured comparison of what QoS 1 versus QoS 2 actually costs on a lossy link.

## Wire economics

Every packet starts with a 1-byte fixed header (type + flags) followed by the Remaining Length field, a variable-length integer of 1-4 bytes at 7 bits per byte. That encoding reaches 268,435,455 bytes, so a minimal QoS 0 PUBLISH is genuinely two bytes of protocol before the topic even starts. Do the arithmetic for a 16-byte sensor reading published to topic `t/1`, four times a minute:

| Approach | Per-reading protocol bytes (arithmetic, not measurement) | Notes |
|----------|----------------------------------------------------------|-------|
| MQTT QoS 0 PUBLISH | 2 (fixed header) + 2 (topic length) + 3 (topic) = 7 | Connection already established; zero handshakes |
| MQTT QoS 1 PUBLISH | same + 2 (packet ID) = 9, + PUBACK (2) = 11 on the wire | Stop-and-wait per packet ID |
| HTTP/1.1 POST | ~150-200 request headers + ~120 response headers | Plus a TCP handshake (and TLS, 1-2 RTTs) unless reused |

Over a month, the MQTT QoS 0 path moves roughly 40 KB of protocol overhead where the per-request HTTP path moves megabytes - and on NB-IoT-style links where every radio wakeup costs joules, the handshake elimination matters more than the header size. The catch is that MQTT's economy depends on the connection staying up, which is why the session machinery below exists.

## The connection state machine

CONNECT is the only packet a client may send first; the broker answers CONNACK carrying a session-present flag and a reason code. The CONNECT payload binds the Client ID, credentials, and the Last Will. Three pieces of this state machine interview well:

Because CONNECT is the session's foundation, it is worth reading the actual bytes. A minimal MQTT 5 CONNECT (client id "dev", keepalive 30 s, Clean Start, Session Expiry 300 s) decodes as:

```text
 10 15                                          <- fixed header: CONNECT, rem.len = 21
 00 04 4D 51 54 54          "MQTT"              <- protocol name (2-byte len + 4 chars)
 05                                             <- protocol version (5)
 02                                             <- connect flags: 0x02 = Clean Start
 00 1E                                          <- keepalive = 30 s
 05                                             <- property length = 5 bytes follow
 11 00 00 01 2C                                 <- property 0x11 = Session Expiry = 300 s
 00 03 64 65 76             "dev"               <- payload: client id (2-byte len + 3 chars)
```

Walking one real handshake by hand is the fastest way to internalize that everything in MQTT is (type, flags, remaining length) plus a property list - and it makes encoder bugs (wrong flag bit, properties out of order) obvious in a hex dump.

**Keepalive and half-open detection.** The client advertises a keepalive interval in seconds and must show liveness (any packet counts) within it. The spec is blunt about enforcement: if the server does not receive an MQTT Control Packet from the client within one and a half times the Keep Alive time period, it MUST close the Network Connection as if the network had failed. That 1.5x grace absorbs one lost PINGREQ. The half-open problem is symmetric and nastier: when a client's radio drops the path without RST, the broker waits out the keepalive, but the client may sit on a dead socket for minutes because TCP will only tell it after retransmission timeouts. Clients that care detect this by timing out PINGRESP themselves rather than trusting TCP.

**Last Will and Testament.** CONNECT registers a will topic, payload, and QoS; the broker publishes it when the connection dies without a clean DISCONNECT - keepalive timeout, transport error, protocol error. MQTT 5 adds a Will Delay Interval so a brief reconnect (phone entering an elevator) does not flap the will. The classic gotcha: a second client connecting with the same Client ID takes over the session, and the old connection's will is still published - fleet deployments that recycle client IDs get phantom "device offline" events this way.

**Sessions.** In v3.1.1, `cleanSession=0` asks the broker to remember subscriptions and queue QoS 1/2 messages across disconnects; the CONNACK session-present flag tells the client whether it is resuming or starting cold. MQTT 5 splits the concept into Clean Start (this connection) plus a Session Expiry Interval property (3.1.2.11.2) in seconds that survives the connection - set it to 0xFFFFFFFF for never-expiring sessions. The queued-message window is unbounded by spec, so a subscriber offline for a week against a chatty topic is a broker memory problem you signed up for.

## QoS as two stop-and-wait machines

The three levels are three different contracts, not three speeds:

| Level | Handshake | Delivery guarantee | Receiver dedup state |
|-------|-----------|--------------------|----------------------|
| 0 | none | fire and forget | none |
| 1 | PUBLISH -> PUBACK | at least once | none - retransmission means re-delivery, by design |
| 2 | PUBLISH -> PUBREC -> PUBREL -> PUBCOMP | exactly once | packet-ID state on both sides |

QoS 1's duplicate behavior is not a bug: the receiver keeps no dedup state, so a lost PUBACK forces a retransmission that the broker correctly treats as a fresh message. QoS 2 spends two more packets to close exactly that hole, and the spec pins both machines down: the sender must treat PUBLISH as unacknowledged until PUBREC, must not re-send the PUBLISH once it has sent the corresponding PUBREL, and may reuse the packet identifier only after PUBCOMP; the receiver accepts ownership of the message when it answers PUBREC, must re-acknowledge any retransmitted PUBLISH with the same packet ID using PUBREC, and must not cause duplicate delivery.

That is why both sides need the packet identifier: on the sender it names the in-flight machine (which state am I retransmitting?), on the receiver it names the dedup entry (have I taken ownership of this id yet?). One identifier, two state machines, four packets:

```text
  QoS 2 with retransmission branches (one hop: client -> broker)

  Client                              Broker (receiver)
    |                                    |
    | PUBLISH(id=n, DUP=0) ------------> | state[id]=owned, send PUBREC
    | PUBLISH(id=n, DUP=1) --(timeout)-> | already owned: re-send PUBREC ONLY
    |<---------------------------------- | PUBREC(id=n)          (lost -> branch)
    |                                    |
    | PUBREL(id=n) ---------------------> | release: forward exactly once,
    | PUBREL(id=n) --(PUBCOMP lost)----> |   then forget id (PUBCOMP either way)
    |<---------------------------------- | PUBCOMP(id=n)
    |                                    |
    free id n; never re-send PUBLISH after PUBREL (spec: MQTT-4.3.3-6)
```

Note what the PUBREL half buys: once the sender has PUBREC, it stops re-sending PUBLISH, so the receiver's dedup entry is safe to retire at PUBCOMP. Per-hop this is exactly-once; end-to-end MQTT composes two such hops (publisher -> broker -> subscriber), and QoS is negotiated per subscription, so a QoS 2 publish degrades to QoS 0 on any subscriber whose subscription asked for QoS 0.

## Flow control, fan-out, and MQTT 5 conveniences

The naive QoS design has a resource hole: an unbounded number of unacknowledged in-flight messages per client. MQTT 5 closes it with Receive Maximum (CONNECT property 3.1.2.11.3, rules in section 4.9 Flow Control): a quota of QoS 1/2 messages the peer may have outstanding without acknowledgment, restored per acknowledgment.

```text
  sender window under Receive Maximum = 3 (stop sending when quota exhausted)

  in-flight:  [ PUBLISH id=7 ->][ PUBLISH id=8 ->][ PUBLISH id=9 ->]   quota 3/3 used
  acked:      [ id=6 PUBACK ]                                           +1 back
  next:       id=10 must WAIT until one of 7/8/9 is acknowledged

  broker -> client direction has its own, independent quota
```

This turns each client's in-flight window into an explicit backpressure knob - set it to 1 and every hop is stop-and-wait; raise it and the broker can pipeline. A slow consumer therefore slows its own delivery queue rather than the broker's memory. Two more 5.0 additions matter in production:

- **Topic aliases** (PUBLISH property, 3.3.2.3.4): send `alias=4, topic="factory/line3/oven2/temperature"` once, then publish with just `alias=4`. On radio links the topic string can dwarf the payload; aliases cap per-message bytes without changing the topic semantics.
- **Shared subscriptions**: the filter `$share/{ShareName}/{filter}` (4.8.2) turns fan-out into load-balancing - one worker per group receives each message, which is how people build MQTT-based work queues.

Retained messages deserve a sentence of caution here: they are a one-slot-per-topic last-value cache, not a database. A retained topic answers "what is the current state" instantly on subscribe, but there is no history, no per-client retention, and a zero-byte payload is the delete key.

One ordering rule rounds out the delivery contract (section 4.6): a single client's messages on a single topic at a given QoS level arrive in publish order, but MQTT promises nothing across topics, across clients, or across QoS levels - and a retransmission after reconnect (4.4) may surface an old message late. Application code that assumes global ordering is writing to the spec's blank spaces.

## Inside the broker: topic trees and the wildcard-explosion problem

Brokers index subscriptions as a tree keyed on topic levels, with `+` (single level) and `#` (multi-level suffix) as branch wildcards. A publish walks the tree, so matching cost is proportional to the topic's levels and the number of matching branches - not the subscriber count. The pathology is subscription shape, not size:

1. **Wildcard fan-out**: one publish to `sensors/site1/line7/temp` must be matched against every `sensors/#` and `sensors/+/line7/#` filter; a fleet of broad wildcard subscribers turns each publish into a scan of their filters.
2. **Overlapping subscriptions**: a client subscribed to both `sensors/#` and `sensors/site1/#` matches one publish twice; brokers may deliver one copy per matching subscription or collapse to the highest negotiated QoS - either is spec-legal, so behavior differs across brokers and your client may see duplicates.
3. **$-topics**: `$SYS/` and `$share/` are invisible to wildcard roots (`#` does not match `$SYS/...`), a rule that exists precisely to keep wildcards from matching broker internals.

Mosquitto, EMQX, and HiveMQ all implement this matching model with different scaling strategies (Mosquitto as a deliberately lightweight single-process broker; EMQX and HiveMQ as horizontally clustered brokers), but the matching semantics are fixed by the spec, which is why wildcard hygiene is portable advice: prefer explicit levels, keep `#` subscribers few and slow-consuming.

## Constrained variants: MQTT-SN and bridging

MQTT-SN (Sensor Networks) targets devices that cannot afford TCP: it runs over UDP (or ZigBee/802.15.4), replaces topic strings with 2-byte topic IDs negotiated via REGISTER, adds gateway discovery by broadcast (ADVERTISE/SEARCHGW), and supports sleeping clients whose messages the gateway queues until they wake. Topology-wise it comes in a transparent gateway (one MQTT connection per SN client) or an aggregating gateway (one connection total), and it is standardized in the OASIS MQTT TC's SN track rather than in MQTT 5 itself.

Bridging is the deployment complement: a Mosquitto-style bridge connects two brokers with configured topic maps (in/out/both directions, optional remote/local prefixes), which is how you splice a factory's local broker onto a cloud broker without putting every sensor on the internet. The classic failure is loop topologies - two bridges forwarding overlapping wildcards back and forth - mitigated with careful topic direction and bridge-protocol loop detection.

## Measuring the cost: QoS 1 vs QoS 2 on a lossy link

The two machines above can be simulated exactly on a link that drops each packet independently with probability p. QoS 1 retransmits PUBLISH until a PUBACK lands; every PUBACK lost in flight becomes a duplicate application delivery. QoS 2 runs the two-phase machine and delivers exactly once regardless:

```python
import random

class Link:
    """One-way lossy link: each packet is dropped with probability p."""
    def __init__(self, p, rng):
        self.p, self.rng = p, rng
    def send(self, pkt):
        return self.rng.random() >= self.p

def qos1_transfer(link, log):
    """PUBLISH -> PUBACK, retransmit on loss. Receiver keeps NO dedup state,
    so a lost PUBACK makes the broker deliver the message a second time."""
    while True:
        log["c2s"] += 1
        if link.send("PUBLISH"):
            log["app"] += 1                    # broker hands message to app
            log["s2c"] += 1
            if link.send("PUBACK"):
                return
        log["retx"] += 1                       # timeout -> retransmit PUBLISH

def qos2_transfer(p, rng, log):
    """PUBLISH -> PUBREC -> PUBREL -> PUBCOMP with per-state retransmission.
    Broker delivers to app only on PUBREL, keyed by packet id => exactly once."""
    link, pid, state = Link(p, rng), "msg", {}
    while pid not in state:                    # phase 1: get PUBLISH stored
        log["c2s"] += 1
        if link.send("PUBLISH"):
            if pid not in state:
                state[pid] = "stored"          # first arrival only
            log["s2c"] += 1
            if link.send("PUBREC"):
                break
        log["retx"] += 1
    while True:                                # phase 2: release the message
        log["c2s"] += 1
        if link.send("PUBREL"):
            if state.get(pid) == "stored":     # deliver exactly once, on PUBREL
                log["app"] += 1
                del state[pid]                 # forget id -> safe to reuse
            log["s2c"] += 1
            if link.send("PUBCOMP"):
                return
        log["retx"] += 1                       # PUBREL/PUBCOMP lost -> resend

def run(n_msgs, p, seed=42):
    rng = random.Random(seed)
    q1 = {"c2s": 0, "s2c": 0, "retx": 0, "app": 0}
    for _ in range(n_msgs):
        qos1_transfer(Link(p, rng), q1)
    q2 = {"c2s": 0, "s2c": 0, "retx": 0, "app": 0}
    for _ in range(n_msgs):
        qos2_transfer(p, rng, q2)
    return q1, q2

n = 200
print(f"{'loss':>5} {'msgs':>5} | {'QoS1 wire':>9} {'retx':>5} {'app':>4} {'dups':>4} | "
      f"{'QoS2 wire':>9} {'retx':>5} {'app':>4} {'dups':>4} | {'overhead':>8}")
for p in (0.05, 0.20, 0.40):
    q1, q2 = run(n, p)
    d1, d2 = q1["app"] - n, q2["app"] - n
    w1, w2 = q1["c2s"] + q1["s2c"], q2["c2s"] + q2["s2c"]
    print(f"{p:>4.0%} {n:>5} | {w1:>9} {q1['retx']:>5} {q1['app']:>4} {d1:>4} | "
          f"{w2:>9} {q2['retx']:>5} {q2['app']:>4} {d2:>4} | {w2 / w1:>7.2f}x")
```

Real output (Python 3.12, seed 42):

```text
 loss  msgs | QoS1 wire  retx  app dups | QoS2 wire  retx  app dups | overhead
  5%   200 |       430    19  211   11 |       834    36  200    0 |    1.94x
 20%   200 |       548   103  245   45 |       980   184  200    0 |    1.79x
 40%   200 |       829   320  309  109 |      1367   522  200    0 |    1.65x
```

Three things fall out of the numbers:

- **QoS 2 delivers exactly 200 - always.** Every loss is absorbed as a retransmission, never a duplicate; QoS 1's duplicate rate climbs steeply with loss (11 -> 45 -> 109 duplicates per 200 messages), because every PUBACK lost in flight converts into a re-delivery later.
- **The relative overhead shrinks as the link gets worse** (1.94x at 5% loss -> 1.65x at 40%): QoS 1's retransmission count includes its own duplicate deliveries and re-acks, so both machines degrade; QoS 2 just degrades more gracefully per delivered message.
- **The absolute overhead is brutal on bad links**: at 40% loss each QoS 2 message costs ~6.8 wire packets versus the ideal 4, which is why constrained-device profiles push QoS 1 + idempotent consumers before QoS 2.

## References

1. [MQTT Version 5.0 OASIS Standard (connect properties 3.1.2.11, QoS 2 in 4.3.3, flow control 4.9, shared subscriptions 4.8.2)](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html)
2. [MQTT.org - protocol overview and version history](https://mqtt.org/)
3. [HiveMQ MQTT Essentials - practitioner-level series on sessions, QoS, and LWT](https://www.hivemq.com/mqtt-essentials/)
4. [Eclipse Mosquitto: mqtt(7) man page - protocol description and packet types](https://mosquitto.org/man/mqtt-7.html)
5. [OASIS MQTT-SN Technical Committee - MQTT for Sensor Networks standardization](https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=mqtt-sn)
