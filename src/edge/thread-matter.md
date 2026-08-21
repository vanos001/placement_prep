# Thread and Matter Deep Dive

## Overview

Thread and Matter are the two protocols that have reshaped the consumer smart home. **Thread** is the IPv6 mesh *transport* that ships on a low-power radio; **Matter** is the *application layer* that defines a common data model so that an Apple Home, a Google Home, an Alexa, and a Samsung SmartThings can all control the same light bulb. This chapter unpacks the Thread mesh (802.15.4 PHY, 6LoWPAN compression, router/leader election), the Matter interaction model (Node/Endpoint/Cluster/Attribute/Command/Event), the commissioning flow (PASE→CASE→fabric), and the comparison with Zigbee, Z-Wave, and BLE Mesh.

## Thread

### Physical Layer: IEEE 802.15.4

Thread rides on the **IEEE 802.15.4** physical and MAC layers — the same PHY as Zigbee. The radio specifications:

- **Frequency**: 2400–2480 MHz ISM (a European 868 MHz variant exists but is rarely used for Thread).
- **Channels**: 16 channels, 5 MHz apart, numbered 11–26. Thread defaults to channel 11 (2405 MHz) but the channel is configurable per network.
- **Modulation**: **O-QPSK** (offset quadrature phase shift keying) with half-sine pulse shaping → effectively MSK. Bit rate 250 kbps, symbol rate 62.5 ksym/s (4 bits/symbol).
- **MAC**: CSMA/CA with random back-off; ACKs at the MAC layer; inter-frame spacing 192 µs.
- **Range**: 10–30 m indoor, ~100 m line of sight per hop. Mesh extends this.

A single 802.15.4 frame is up to 127 bytes at the MAC layer; with MHR (MAC header) + security headers, ~80 bytes are usable for upper layers. Thread compresses IPv6 down via 6LoWPAN so a typical application packet fits in one MAC frame.

### 6LoWPAN and IPv6

Every Thread device has an **IPv6 address** — typically a ULA (Unique Local Address, `fd00::/8`) plus the link-local `fe80::` derived from the EUI-64. 6LoWPAN (RFC 6282) compresses the 40-byte IPv6 header down to 2 bytes for typical link-local traffic, by eliding fields that can be derived from the link layer (e.g. source address derived from PAN ID). This is the **key advantage of Thread over Zigbee/Z-Wave** — applications speak IP, not a vendor protocol.

```
Application on Thread device
   │   UDP socket
   ▼
IPv6 (40 B → 2 B after 6LoWPAN)  ◀── mesh forwarding at Layer 3
   ▼
6LoWPAN adaptation
   ▼
802.15.4 MAC (25 B header)
   ▼
802.15.4 PHY (O-QPSK, 250 kbps, 2.4 GHz)
```

### Mesh Topology and Roles

```
                ┌─────────────────┐
                │ Border Router   │ ◀──── IPv6 to Wi-Fi/Ethernet
                └────────┬────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
     ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
     │ Router  │───┤ Router  │───┤ Router  │
     │ (RX on) │   │ (RX on) │   │ (RX on) │
     └────┬────┘   └────┬────┘   └─────────┘
          │              │
     ┌────┴────┐    ┌────┴────┐
     │SED      │    │SED      │
     │(polling)│    │(polling)│
     └─────────┘    └─────────┘
```

| Role | Description | Power |
|------|-------------|-------|
| **Leader** | Elected router that owns the partition's network data (the authoritative set of routes, prefixes, services). | Mains |
| **Router** | Participates in mesh forwarding, maintains child devices. | Mains |
| **Router-Eligible End Device (REED)** | End device that can become a router if more routers are needed. | Mains |
| **End Device (ED)** | Leaf node with one parent (a router). No mesh-forwarding duty. | Mains or battery |
| **Sleepy End Device (SED)** | An ED that polls its parent for queued data. | Battery (years) |
| **Sleepy Synchronized SED** | Time-synchronised with parent; wakes at predictable times (low-jitter). | Coin cell |

Router-Router links use **Mesh Link Establishment (MLE)** to discover neighbours, exchange link-quality metrics, advertise the partition ID, and form the routing graph. Routers run a distance-vector protocol over MLE; the *Network Data* (set of border routers, on-mesh prefixes, services) is signed by the Leader and flooded to all routers.

### Partitioning and Healing

If a router fails or a link drops, the network fragments into **partitions**. Each partition elects its own Leader. When two partitions re-contact each other, the one with the higher `(partition_id, leader_router_id)` wins; the losing partition merges into it. This is **self-healing**: there is no central controller and no single point of failure.

### Router Election (Router ID Table)

Each router has a Router ID (1–62, allocated by the Leader). When a REED wants to become a router, it asks the Leader for an ID; the Leader advertises the new ID in the Network Data. Routers maintain a `(Router ID → Link-Local Address)` table. A *router upgrade* is triggered when a router has too many children or when a partition's router count drops below a threshold.

### Security

All Thread traffic is encrypted with **AES-128-CCM** at the 802.15.4 MAC layer. Two keys:

- **Network Master Key** — used to derive per-traffic keys; rotates periodically.
- **KEK (Key Encryption Key)** — used during commissioning.

Commissioning introduces a new device with credentials — typically the Network Master Key, the PAN ID, the channel, and an Extended PAN ID — over an out-of-band channel (Bluetooth Low Energy or a QR code). Once the device joins, it has its security credentials and can speak encrypted Thread.

## Matter

Matter (formerly Project CHIP — Connected Home over IP) is the **unified application layer** for the smart home, hosted by the Connectivity Standards Alliance (CSA). The first spec was released in October 2022 (v1.0); the current major release is 1.3 as of 2024.

### Transports: Thread + Wi-Fi + Ethernet

Matter is *transport-agnostic* — the same cluster model runs over Thread, Wi-Fi, or Ethernet (and BLE is used only for commissioning). In practice:

- **Thread** is used for battery-powered or low-bandwidth devices (sensors, light switches, smart locks).
- **Wi-Fi** is used for high-bandwidth devices (cameras, video doorbells).
- **Ethernet** is used for mains-powered hubs (Apple TV, Nest Hub).

A single Matter *fabric* (controller's domain of devices) can span all three transports simultaneously — a Thread light bulb, a Wi-Fi camera, and an Ethernet-connected TV are all in the same fabric and addressable by the same controller.

### Node / Endpoint / Cluster / Attribute / Command / Event

Matter's data model is hierarchical:

```
Node  (a single physical device, has a Node ID, on a fabric)
  └── Endpoint 0  (root endpoint, mandatory — carries Basic Information, etc.)
  └── Endpoint 1  (e.g. a light bulb)
        ├── On/Off cluster (cluster ID 0x0006)
        │     ├── Attribute: OnOff          (boolean, read/write/subscribe)
        │     ├── Attribute: StartUpOnOff   (enum, read/write)
        │     ├── Command:   Off            (invoke)
        │     ├── Command:   On             (invoke)
        │     ├── Command:   Toggle        (invoke)
        │     └── Event:     StartUp        (subscribe)
        ├── Level Control cluster (0x0008)
        │     └── Attribute: CurrentLevel   (0..254, read/subscribe)
        └── Color Control cluster (0x0300)
              └── Attribute: CurrentHue / CurrentSaturation
```

- **Node** = one Matter entity (e.g. one smart bulb).
- **Endpoint** = a *logical device* inside a node. A combo switch + dimmer might expose Endpoint 1 (switch) and Endpoint 2 (dimmer).
- **Cluster** = a unit of functionality, identified by a 32-bit ID. Clusters have attributes (state), commands (verbs), and events (logs of asynchronous change). The cluster library is the CSA spec — the On/Off cluster, Level Control cluster, etc. work uniformly across every Matter device.
- **Fabric** = the set of devices under one controller's authority (e.g. "my Apple Home"). A device can be in **multiple fabrics** simultaneously (multi-admin) — e.g. my Apple, Google, and Alexa fabrics each see the same bulb.

### Interactions

Matter defines four **interaction types** over the secure channel:

1. **Read** — controller reads an attribute/event at a node; supports wildcards (e.g. read attribute `OnOff` on every endpoint of every node).
2. **Write** — controller writes an attribute (e.g. set `OnOff = true`).
3. **Subscribe** — controller subscribes to attribute/event changes; the node reports min/max periodically and on change (similar to LwM2M Observe).
4. **Invoke** — controller invokes a command (e.g. `Toggle`).

These interactions carry an **Interaction Profile ID**, **Invoke ID**, **Attribute Path** (a list of `EndpointID / ClusterID / AttributeID` triples, with wildcards), and optional *data filters* (`MinIntervalFloor`, `MaxIntervalCeiling` for subscriptions).

### Commissioning: PASE → CASE → Fabric Joining

The Matter commissioning flow is intentionally painful because trust is the foundation:

```
Commissioner (e.g. iPhone)             Commissionee (e.g. smart bulb, BLE advertising)
  │
  │ 1. Scan QR code → Manual Pairing Code (11 or 21 digit) → passcode
  │ 2. BLE connection → exchange device info
  │
  │ 3. PASE (Password Authenticated Session Establishment)
  │    SPAKE2+ PAKE over passcode → secure channel keys
  ├── (encrypted from here on)
  │
  │ 4. Commissioner sends operational credentials + root cert
  │ 5. Device generates Node Operational Cert (signed by vendor CA)
  │ 6. Commissioner → Device: AddTrustedRootCert, AddNOC (Node Operational Cert)
  │
  │ 7. Device now has: OperationalCert, RootCACert, fabric ID, Node ID
  │
  │ 8. Device switches to CASE (Certificate Authenticated Session Establishment)
  │    for all subsequent operational traffic on Thread/Wi-Fi
  │
  │ 9. Discover on operational network (mDNS "_matter._tcp")
  │10. Operational session established → device is now on fabric
```

- **PASE** uses SPAKE2+ (a PAKE protocol) to negotiate a session key from a short passcode. The passcode is encoded in a QR code (with anti-replay by a discriminating PIN).
- **CASE** uses X.509 certificates signed by the vendor's Product Attestation Authority (PAA) and per-fabric Root CAs. After PASE, the commissioner gives the device an operational certificate; subsequent sessions are CASE-authenticated, with ECDH (P-256) and signatures.

The **Fabric** is identified by a `FabricID` (64-bit) and is anchored by a `Root Public Key` + the fabric's `Root Cert`. A device added to a second fabric gets a *second* operational certificate (with a different `NodeID` per fabric) — that's the multi-admin story.

### Data Model Wire Format

Matter messages are encoded in **TLV (Tag-Length-Value)** — not CBOR, not protobuf. TLV carries typed values: integers, strings, octet strings, nested structures, arrays. Every attribute, command, and event payload is encoded as a TLV structure. The wire framing is:

```
Message Frame:
  [ Header (varlen, includes session ID, message counter) ]
  [ Security tag (encrypted: header + payload + MIC) ]
  [ Payload: Interaction PDU (TLV-encoded) ]

Interaction PDU example (SubscribeRequest):
  InteractionID        = 0x0a (subscribe)
  InvokeID             = 0x1234
  AttributeRequests    = [ {Endpoint=1, Cluster=0x0006, Attribute=0x0000}, ... ]
  MinIntervalFloor     = 0  (s)
  MaxIntervalCeiling    = 30 (s)
```

Message framing and reliability (acknowledgements, retries, windowed delivery) come from the **Matter Reliable Messaging** protocol over IPv6, with the **Message Counter** providing replay protection.

### Comparison to Zigbee, Z-Wave, BLE Mesh

| Property          | Thread + Matter                  | Zigbee 3.0                       | Z-Wave (800/900)              | BLE Mesh (5.0+)            |
|-------------------|----------------------------------|-----------------------------------|-------------------------------|-----------------------------|
| PHY/MAC           | IEEE 802.15.4 (2.4 GHz)           | IEEE 802.15.4 (2.4 GHz)           | ITU-T G.9959 (sub-GHz 868/908) | BLE (2.4 GHz, GFSK)         |
| Network layer     | IPv6 + 6LoWPAN                   | Zigbee NWK (proprietary routing)  | Z-Wave NWK (source routing)   | Mesh proxy + LPN           |
| Application model | Matter cluster library (CSA)     | Zigbee Cluster Library (ZCL)     | Z-Wave Command Class          | BLE Mesh Model (Generic On/Off, etc.) |
| IP-native          | Yes                               | No (needs a coordinator/gateway)  | No                            | No (proxy node bridges IP)   |
| Mesh routing      | Distributed, distance-vector      | Tree + AODV-like                  | Source-routed                  | Managed flooding (TTL + relay) |
| Pairing           | BLE + QR + SPAKE2+ → CASE         | Touchlink / install code (link key) | S2 security with DSK         | OOB + application keys      |
| Multi-admin       | Yes (multiple fabrics)            | No                                | No                            | No                          |
| Stack sizes       | ~150 KB flash, ~50 KB RAM (Thread)| ~128 KB / 8 KB                    | ~64 KB / 4 KB                 | ~64 KB / 8 KB                |
| Latency (typical) | 30–100 ms (on-mesh)               | 100–300 ms                        | 30–200 ms                      | 50–200 ms                   |
| Operator/owner    | CSA (Thread Group)                | CSA (formerly Zigbee Alliance)    | Silicon Labs                   | Bluetooth SIG              |

### Why Thread + Matter Won

Zigbee shipped first, but it was *not IP-native* — every ecosystem needed its own cloud or hub to translate Zigbee Cluster Library commands to application semantics, and Zigbee networks could not bridge to other Zigbee networks cleanly. Apple's HomeKit needed HomePod or Apple TV to bridge. Google's Nest Hub had its own Zigbee/Weave translation. The result was a decade of fragmented "works with" badging.

Thread solved the *transport* problem — every device speaks IPv6, so a Thread device is directly reachable from any Thread border router that has IP connectivity. Matter solved the *application* problem — every device speaks the same cluster library. Combine them, and a bulb certified for Matter runs on the same Thread radio for any controller that pays the CSA membership dues. Apple, Google, Amazon, Samsung — the *Matter* spec guarantees multi-admin by design.

## Interview Angle

> **"Why does Matter support multiple fabrics (multi-admin)?"**

A fabric is the cryptographic and namespace boundary of one controller's ecosystem. A device in multiple fabrics has multiple NodeIDs, one per fabric, each backed by a different operational certificate signed by that fabric's Root CA. This is Matter's killer feature: a consumer can buy a Matter bulb, commission it into Apple Home, and later add it to Google Home without resetting the bulb — both controllers control it simultaneously, with their own ACLs (Access Control Lists). The cluster model is identical, so the bulb behaves consistently regardless of which ecosystem addressed it.

> **"What's the difference between Thread and Matter?"**

Thread is the *transport* — IPv6 mesh over 802.15.4, just the network layer. Matter is the *application* — the cluster model and the interaction protocol. Matter can run over Thread, Wi-Fi, or Ethernet; Thread can carry Matter or any other IPv6 application (e.g. CoAP). When you see "Thread-certified" on a smart-lock box, that's the network stack; "Matter over Thread" is the consumer-facing statement that the device uses Matter's data model on Thread's transport.

## Key References

- Thread 1.3 Specification (Thread Group) — https://www.threadgroup.org/thread-specificationv1-3
- Thread Group "Thread Primer" — https://www.threadgroup.org/what-is-thread
- Matter 1.3 Specification (CSA) — https://csa-iot.org/all-solutions/matter/
- Matter SDK (ConnectedHomeIP) on GitHub — https://github.com/project-chip/connectedhomeip
- Matter Specification — Data Model and Interactions — https://github.com/CHIP-Specifications/connectedhomeip-spec/blob/master/spec/07-Matter-Data-Model.adoc
- Apple "Why Matter" developer docs — https://developer.apple.com/videos/play/tech-talks/110382/ (Matter and Thread overview)
- Google Home Developer — "Matter" — https://developers.home.google.com/matter
- IEEE 802.15.4-2020 standard — https://standards.ieee.org/ieee/802.15.4/7029/
- 6LoWPAN (RFC 6282) — https://www.rfc-editor.org/rfc/rfc6282
