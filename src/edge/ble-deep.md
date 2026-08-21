# Bluetooth Low Energy Deep Dive

## Overview

Bluetooth Low Energy (BLE, also marketed as Bluetooth Smart and now simply as the LE portion of the Bluetooth Core Specification) is the radio protocol that powers the entire wearable and beacon ecosystem. Since Bluetooth 4.0 (2010), LE has been a separate stack from Classic Bluetooth (BR/EDR) sharing only the 2.4 GHz band — and from version 5.0 onwards LE has its own high-throughput, long-range, and mesh extensions. This chapter unpacks the advertising channels, the connection-event model, GAP roles, GATT services, the ATT protocol, and the LE Secure Connections pairing model.

## The BLE Radio

### Frequency Plan

BLE operates in the 2.4 GHz ISM band (2400–2483.5 MHz), divided into **40 channels** spaced 2 MHz apart (RF channel indexes 0–39):

```
RF channel:   0    1    2    3 ...  36   37   38   39
              │    │    │    │       │    │    │    │
              └──────── low/mid/high data channels ────┘
                                      ↑    ↑    ↑
                              Advertising channels (3)
```

- **Channels 37, 38, 39** are *advertising* channels, at 2402, 2426, and 2480 MHz. They sit at the band edges and middle to avoid the WiFi channels 1, 6, 11 patterns as much as possible (WiFi uses 20 MHz-wide channels; BLE channels are 2 MHz, so most BLE channels fit in the WiFi gaps).
- **Channels 0–36** are *data channels* used during a connection, hop pseudorandomly (frequency hopping spread spectrum, FHSS) at every connection event.

### Modulation and Throughput

- **GFSK** (Gaussian Frequency Shift Keying), ±185 kHz deviation, 1 Msym/s raw rate, 1 Mbps bit rate (Bluetooth 4.0–4.2).
- **2M PHY** (Bluetooth 5.0): 2 Mbps raw rate at half the symbol time, lower energy per bit but more susceptible to interference — used when the link is short and strong.
- **Coded PHY** (Bluetooth 5.0): two coding schemes — S=2 (500 kbps effective, range ×2) and S=8 (125 kbps effective, range ×4). Coding uses a convolutional encoder (rate 1/2 or 1/8) plus a pattern mapper; the receiver does Viterbi decoding.
- **LE Long Range** is the combination of Coded PHY + higher TX power (up to +20 dBm).

### Frequency Hopping

Connection events hop across the 37 data channels using an algorithm derived from `(channel map, hop interval, access address)`. The hop increment is 5–16, computed at connection time. *Channel map* allows the master to mark some channels as "unused" (e.g. because they coincide with WiFi 1/6/11) — adaptive frequency hopping (AFH).

## Advertising Channels (37/38/39)

### Why Three Advertising Channels?

Three channels maximise the chance a scanner catches an advertisement even when the spectrum is congested. The advertiser transmits the same packet on **37, then 38, then 39** in sequence (the *advertising interval* is `T_advEvent = advInterval + 0–10 ms randomisation`; the randomisation prevents perpetual synchronisation between two devices that happen to use the same interval).

```
   ch37    ch38    ch39        ch37    ch38    ch39
    │       │       │           │       │       │
    ▼       ▼       ▼           ▼       ▼       ▼
   [P]     [P]     [P]         [P]     [P]     [P]
                      \__________advInterval (20 ms–10.24 s)
   ─────────────────────────────────────────────────────►
```

A **scanner** listens on one channel at a time (default 150 ms per channel, rotating 37→38→39). To receive an advert reliably, the scanner must be on the same channel as the advertiser during the ~150 µs the packet is on air.

### Advertising Packet Format

```
Preamble (1 byte, alternates 0xAA / 0x55)
Access Address (4 bytes; advertising AA = 0x8E89BED6, a fixed value)
PDU (2–255 bytes)
CRC (3 bytes)
```

The PDU for legacy advertisements is:

```
| Header (2 bytes) | MAC Address (6 or 0 bytes) | Payload (up to 31 bytes) |
```

Payload subfields (each is `length | type | data`):
- **Flags** (0x01): discoverability mode (limited, general, BR/EDR not supported).
- **Complete/Incomplete 16-bit UUID list** (0x02/0x03): service UUIDs advertised.
- **Complete/Incomplete Local Name** (0x08/0x09): device name (or shortened).
- **TX Power Level** (0x0A): used by receivers to estimate proximity (`RSSI = -X at distance d`).
- **Manufacturer Specific Data** (0xFF): vendor blob, often a beacon payload (iBeacon = Apple, Eddystone = Google, AltBeacon = open).

Bluetooth 5.0 added **Extended Advertising** — secondary advertising channels among the 0–36 set that can carry payloads up to 254 bytes and chain PDUs together (up to 1650 bytes total). The primary channel carries a tiny "ADV_EXT_IND" header pointing to the secondary channel; the scanner tunes there to receive the longer payload. This decoupling lets primary-channel on-air time stay tiny (~22 µs) so a sensor can advertise frequently without burning battery.

## Connection Events

When a scanner receives a `CONNECT_IND` advertisement response (from a *central* wanting to connect), the two devices enter a *connection*. The connection is divided into **connection events**, each anchored on a specific channel and time. Both devices wake at the anchor point, exchange a few PDUs, and sleep until the next anchor.

```
Anchor 1 ─┬─[P1: master→slave]─[P2: slave→master]─[P3: master→slave]─┬─
Anchor 2 ─┼─[P1: master→slave]─[P2: slave→master]─[P3: master→slave]─┼─
Anchor 3 ─┴─[P1: master→slave]─[P2: slave→master]────────────────────┴─
                ▲                                              ▲
                | (channel hops each connection event)        Slave can sleep
```

### Connection Parameters

- **Connection Interval** (CI): 7.5 ms to 4.0 s. Determines how often master and slave wake. A shorter CI means lower latency at the cost of more wake-ups (higher power).
- **Slave Latency** (SL): 0 to 499 connection events the slave can skip. Allows the slave to sleep through connection events it doesn't expect data — but if it misses a window it didn't know was coming, the master still caches data.
- **Supervision Timeout** (ST): 100 ms to 32 s. If no packet is received for this duration, the link is considered lost.

```
Effective interval = (1 + SL) * CI
Energy with SL=4, CI=100 ms:  slave wakes only every 500 ms
Latency for unsolicited master→slave:  up to (1 + SL) * CI ms (if master has data, slave won't see it until next anchor)
```

This tension between latency and battery is the heart of BLE power engineering. Nordic's "Bluetooth Low Energy power profiler" toolchain exists precisely to visualise this.

## GAP Roles

**Generic Access Profile (GAP)** defines four roles:

| Role | Description | Common Example |
|------|-------------|----------------|
| **Broadcaster** | Sends advertisements only — no connection. | Beacon (iBeacon, Eddystone) |
| **Observer** | Listens for advertisements only — no connection. | Beacon scanner, indoor-positioning receiver |
| **Peripheral** | Advertises and accepts connections; slave once connected. | Heart-rate sensor, smart bulb (during commissioning) |
| **Central** | Scans and initiates connections; master once connected. | Smartphone, BLE dongle on a PC |

A device can hold multiple roles concurrently (e.g. be a Peripheral to its phone and a Broadcaster for nearby beacons). Multi-role firmware is increasingly common in modern SoCs (Nordic nRF52/nRF53, Texas Instruments CC2640R2).

### Connection vs Broadcast Models

- **Broadcast** is one-way, low latency, low security — anyone in range can hear. Beacons use this; their "payload" is one advertisement (e.g. URL + TX power).
- **Connection** is bi-directional, secure (once paired), and reliable. Most device-to-phone interactions use connections — the phone is the central, the device is the peripheral.

## GATT Profile

The **Generic Attribute Profile (GATT)** defines the data model after a connection is established. GATT is hierarchical:

```
Profile  (e.g. Heart Rate Profile — collection of services defining a use case)
  └── Service       (UUID: e.g. Heart Rate 0x180D)
        ├── Characteristic (UUID: Heart Rate Measurement 0x2A37)
        │     ├── Value: byte stream (e.g. HR 78 bpm, sensor contact OK)
        │     └── Descriptors
        │            ├── CCCD 0x2902 (Client Characteristic Configuration)
        │            │   bit 0: notifications (default 0x0000 = off)
        │            │   bit 1: indications
        │            └── Characteristic User Description 0x2901 ("HR")
        ├── Characteristic (Body Sensor Location 0x2A38)
        └── Characteristic (Heart Rate Control Point 0x2A39 — write-only)
```

### UUIDs

BLE uses three UUID lengths:
- **16-bit**: assigned by Bluetooth SIG for standardized services/characteristics (e.g. 0x180D = Heart Rate). On the wire they're transmitted as 16-bit values.
- **32-bit**: vendor-assigned, in the 32-bit UUID space. Transmitted as 32-bit.
- **128-bit**: fully random/assigned, e.g. `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` (Nordic UART Service). Stored as 128-bit but in ATTR protocol compressed via a "base" + offset.

The 128-bit UUID base used by the SIG is `0000xxxx-0000-1000-8000-00805F9B34FB` — replacing `xxxx` with the 16-bit assigned number reproduces the 128-bit form.

### Characteristic Properties

Each characteristic has a *properties* byte (8-bit flags):

```
| Broadcast | Read | Write Without Response | Write | Notify | Indicate | Authenticated Signed Writes | Extended Properties |
```

These properties determine which ATT operations are valid on the characteristic. Notify and Indicate are *server-initiated* (the peripheral pushes data); the others are *client-initiated* (the central reads/writes).

## ATT (Attribute Protocol)

GATT is built on **ATT**, a simple client-server protocol where the server (peripheral) holds a table of **attributes**. Each attribute is:

```
| Handle (2 bytes) | Type (16/128-bit UUID) | Value (variable, up to MTU-1) | Permissions |
```

- **Handle** — 16-bit; usually allocated densely starting at 0x0001.
- **Type** — a UUID that names the attribute.
- **Value** — the attribute data, addressed as `value[offset:length]` (read supports partial).
- **Permissions** — read/write/encrypt/authenticated flags.

### ATT Operations

| Method | Opcode | Direction | Purpose |
|--------|--------|-----------|---------|
| **Request** | 0x04 | C→S | Read attribute value at handle |
| **Response** | 0x05 | S→C | Return value |
| **Write Request** | 0x12 | C→S | Write value with response |
| **Write Command** | 0x52 | C→S | Write without response (fire-and-forget) |
| **Handle Value Notification** | 0x1B | S→C | Server-pushed, no ACK |
| **Handle Value Indication** | 0x1D | S→C | Server-pushed, requires ATT Confirmation (0x1E) |
| **Find By Type Value** | 0x06 | C→S | Discover services by UUID |
| **Read By Type** | 0x08 | C→S | Discover characteristics by UUID |
| **Read Blob** | 0x0C | C→S | Read continuation (offset > 0) |
| **Exchange MTU Request** | 0x02 | C→S | Negotiate larger ATT_MTU |

### ATT_MTU Negotiation

The default ATT_MTU is **23 bytes** (so attribute values are limited to 20 bytes after ATT header). After connecting, both sides can negotiate up to a max supported MTU (typically 247 bytes for Nordic chips, 517 for some). Larger MTUs mean fewer round-trips for big payloads (e.g. firmware updates over OTA use 244-byte packets).

```
Master → Slave:  Exchange MTU Request (Client RX MTU = 247)
Slave → Master:  Exchange MTU Response (Server RX MTU = 247)
Effective MTU = min(247, 247) = 247. From now on, all ATT PDUs can carry up to 244-byte attribute values.
```

### Notifications vs Indications

- **Notification** — packet type 0x1B, no acknowledgement, fire-and-forget. Higher throughput (back-to-back notifications possible). Lossy.
- **Indication** — packet type 0x1D, must be followed by an **ATT Confirmation** (0x1E). Reliable but each cycle costs 2× round-trip time.

The Client Characteristic Configuration Descriptor (CCCD, 0x2902) is a 2-byte attribute that the central writes to enable either mode:

```
Master writes 0x0001 to handle of CCCD → notifications ON
Master writes 0x0002 to handle of CCCD → indications ON
Master writes 0x0000 to handle of CCCD → both OFF
```

## Pairing: Legacy vs LE Secure Connections

### Legacy Pairing (BT 4.0–4.1)

Three "association models": **Just Works** (no MITM protection — used when no input/output possible), **Passkey Entry** (one side displays 6-digit passkey, other side types it), **Out of Band** (OOB — exchange via NFC, QR).

Legacy pairing uses **Temporary Key (TK)** derived from the passkey (or 0 in Just Works), then computes **Short-Term Key (STK)** via `s1` AES-CMAC function. STK encrypts the link temporarily; the Long-Term Key (LTK) is generated *after* pairing is complete and stored in NVRAM. The weakness: TK for Just Works is 0, so an active eavesdropper can recover STK and forge future links. Also, the 6-digit passkey space is only `10^6` — vulnerable to brute force.

### LE Secure Connections (BT 4.2+)

LE Secure Connections replaces TK/STK with **ECDH P-256 key agreement**. The protocol:

```
1. Pairing Feature Exchange
   Initiator sends: IO Capabilities, Authentication Req, Max Key Size, Initiator Key Distribution
   Responder sends: same

2. Public Key Exchange
   Each side generates an ECDH keypair (private d, public Q) and sends its Q to the other side.

3. Authentication Stage (depending on association model):
   a. Just Works: no MITM — but ECDH still protects confidentiality.
   b. Passkey Entry: 20 rounds of bit-by-bit commitment exchange
      (NaCl-style: each bit is committed with a random nonce,
       the responder reveals in the next round after the initiator).
   c. Numeric Comparison: both sides compute f4(Qi, Qr, Na, Nb, Cb) → 6-digit display.
      User confirms equality on both screens.

4. DHKey Check
   Both sides compute the ECDH shared secret DHKey = d1 * Q2 (mod p).
   Confirm using f6 (with DHKey, Na, Nb, IO Capabilities, public keys).

5. LTK Generation
   LTK = dHK extract over salt, derived from DHKey + Na + Nb.
```

The win: even if an attacker captures the entire exchange, they cannot compute DHKey without solving ECDLP. **Numeric Comparison** (the 6-digit "Y/N?" screen on both phones) replaces **Passkey Entry** as the new MITM-resistant default when both devices have a display. **Passkey Entry** is still supported for asymmetric IO (e.g. one device has a display, other has a keyboard).

### Encryption Key Hierarchy

- **LTK** — Long-Term Key, persistent, used to re-encrypt reconnections (LE Link Re-establishment, BT 4.1+).
- **STK** — Short-Term Key, used only during legacy pairing.
- **IRK** — Identity Resolving Key; resolves a bonded device's *random* MAC (rotated every 15 min on devices with privacy) to its known identity.
- **CSRK** — Connection Signature Resolving Key; used for data signing over an unencrypted link (rare; mostly legacy).

### Resolvable Private Addresses

To protect against long-term MAC tracking, devices with **privacy** enabled rotate their MAC into a `Resolvable Private Address` (RPA): `hash = ah(IRK, prand)` where `prand` is the 24-bit prefix. A bonded central stores the IRK; on receiving an RPA, it tries each IRK until `ah(IRK, prand)` matches the hash — at which point the device is recognised without revealing its identity on the wire.

## BLE vs Classic Bluetooth (BR/EDR)

| Property            | BLE                                | Classic Bluetooth (BR/EDR)      |
|---------------------|------------------------------------|----------------------------------|
| First spec          | BT 4.0 (2010)                     | BT 1.0 (1999)                    |
| Modulation          | GFSK (1 Mbps), 2M PHY, Coded PHY   | GFSK (1 Mbps), π/4-DQPSK (2 Mbps), 8DPSK (3 Mbps) |
| Spectrum            | 40 channels × 2 MHz (37 data + 3 advert) | 79 channels × 1 MHz, FHSS    |
| Discovery           | Advertising (3 channels)           | Inquiry (32 wake + 1 paging)    |
| Pairing             | SSP, then LE Secure Connections (4.2)| SSP (ECDH P-192)                |
| Network             | Master/slave (≤ 7 active slaves per master); BLE Mesh (5.0+) | Piconet/scatternet (7 active slaves) |
| Data rate (peak)    | 1–2 Mbps (uncoded), 0.5/0.125 Mbps coded | 2–3 Mbps                       |
| Latency             | 3 ms (advert-to-connect)           | 100+ ms (inquiry + page)        |
| Range               | ~50 m typical, ~200 m (Coded PHY, +20 dBm) | ~10–30 m                       |
| Power (always-on)   | ~1% duty cycle typical              | ~5–10% with continuous page scan |
| Typical apps         | Wearables, beacons, sensors, smart-home | Audio (A2DP), HID, file transfer |

The two stacks can coexist on a single chip ("dual-mode") — phones are almost always dual-mode. BLE-only chips ("single-mode") are what smartwatches, beacons, and Thread/Matter devices ship.

## Interview Angle

> **"Why does BLE have three advertising channels (37/38/39)?"**

Three is a trade-off between discovery latency and power. With three channels the scanner can rotate through them (default 150 ms on each → 450 ms scan window), and the advertiser transmits its packet on each channel in turn — so a scanner listening on any channel has ~3 chances per `T_advEvent` of catching the advertisement. One channel would be too fragile (a single WiFi burst kills it); more than three would burn power. The chosen frequencies 2402/2426/2480 MHz are deliberately at the band edges and middle to avoid WiFi channels 1 (2412), 6 (2437), and 11 (2462) — adaptive frequency hopping means data channels that overlap with active WiFi get pruned at runtime.

> **"What's the difference between notifications and indications?"**

Both are server-pushed GATT operations, but notifications don't require a confirmation while indications do (an ATT Confirmation PDU). Notifications give higher throughput (the server can fire many back-to-back) at the cost of reliability — if the client is busy or the link drops, notifications are lost without the server knowing. Indications give reliability (server doesn't send the next until it gets the confirmation) at the cost of throughput. Use notifications for high-frequency sensor data (accelerometer at 100 Hz); use indications for control commands where each message must be acknowledged.

## Key References

- Bluetooth Core Specification v5.4 (2023) — https://www.bluetooth.com/specifications/specs/core-specification-5-4/
- Bluetooth Developer Portal — "GATT Overview" — https://developer.bluetooth.com/core/Specifications/GATT
- Nordic Semiconductor — "BLE and Bluetooth" Infocenter — https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/bluetooth.html
- Nordic Semiconductor — "Bluetooth LE Adaptive Frequency Hopping" — https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/bluetooth/le/afh.html
- Bluetooth SIG — "Bluetooth Low Energy — Get Started" — https://www.bluetooth.com/learn-about-bluetooth/tech-overview/le-2/
- Bluetooth SIG — "Mesh Profile Specification" (BLE Mesh) — https://www.bluetooth.com/specifications/specs/mesh-profile-specification-v1-0-1/
- "Bluetooth Low Energy: The Developer's Handbook" (Heydon, 2013)
- Apple — "Core Bluetooth Programming Guide" — https://developer.apple.com/library/archive/documentation/NetworkingInternetWeb/Conceptual/CoreBluetooth_concepts/AboutCoreBluetooth/AboutCoreBluetooth.html
