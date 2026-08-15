# IoT Protocols

## Overview

The Internet of Things demands protocols optimized for constrained environments: low power, limited memory, unreliable networks, and battery-powered devices. This chapter covers the protocol stack from physical/link layers (Zigbee, Thread, BLE, LoRaWAN) through application-layer messaging (MQTT, CoAP) and the emerging smart-home standards (Matter).

## MQTT Internals

**MQTT (Message Queuing Telemetry Transport)** is a pub/sub protocol designed for constrained devices and unreliable networks. It operates over TCP/TLS and is the dominant IoT messaging protocol.

### Architecture

```
┌──────────┐    PUBLISH     ┌───────────────┐    PUBLISH     ┌──────────┐
│Publisher │ ──────────────▶│  MQTT Broker  │──────────────▶ │Subscriber│
└──────────┘                └───────────────┘                └──────────┘
                                   │
                            ┌──────┴──────┐
                            │Topic Hierarchy│
                            │  /home/temp  │
                            │  /car/gps    │
                            └─────────────┘
```

### QoS Levels

| Level | Name | Behavior | Use Case |
|-------|------|----------|----------|
| 0 | At most once | Fire and forget, no ACK | Frequent sensor telemetry where data is transient |
| 1 | At least once | ACK required, may duplicate | Configuration commands, alarms |
| 2 | Exactly once | Four-part handshake (PUBREC/PUBREL/PUBCOMP) | Financial transactions, firmware delivery |

### Key Features

- **Retained messages**: broker stores the last message for a topic; new subscribers receive it immediately
- **Last Will and Testament (LWT)**: broker publishes a designated message when a client disconnects unexpectedly
- **Session state**: persistent sessions allow broker to queue messages for offline clients
- **Shared subscriptions**: multiple subscribers load-balance messages from a topic group (`$share/group/topic`)

### Broker Implementations

- **EMQX**: Erlang-based, supports millions of concurrent connections, clustering, and rule engines
- **Mosquitto**: lightweight C implementation, ideal for edge deployments
- **HiveMQ**: enterprise features (security, bridging, data hub)
- **VerneMQ**: distributed Erlang broker with auto-clustering

## CoAP

**Constrained Application Protocol (CoAP)** is a RESTful protocol for constrained devices, operating over UDP (with optional DTLS for security). Designed by the IETF (RFC 7252), it mirrors HTTP semantics:

- **Methods**: GET, POST, PUT, DELETE
- **Response codes**: 2.xx (success), 4.xx (client error), 5.xx (server error)
- **Content types**: CBOR, JSON, SenML (RFC 8428) for sensor measurements

### Reliable Delivery

CoAP provides reliability over UDP using a simple stop-and-wait mechanism:

- **Confirmable (CON) messages**: require an ACK; retransmitted with exponential backoff
- **Non-confirmable (NON) messages**: no ACK required; used for periodic telemetry
- **Observe pattern**: clients register interest in a resource; server pushes notifications on state change

### Block Transfer

For payloads larger than MTU, CoAP supports block-wise transfers (RFC 7959), enabling firmware updates and large data retrieval from memory-constrained devices.

## Thread & Matter

### Thread

Thread is an IPv6-based mesh networking protocol for smart-home and building automation (Thread Group, IEEE 802.15.4). Key properties:

- **IP-native**: each Thread device has an IPv6 address; no application-layer gateway needed
- **Mesh routing**: self-healing mesh with no single point of failure
- **Low power**: supports battery-powered sleepy end devices that poll routers periodically
- **Security**: all traffic encrypted with AES-128-CCM; commissioning uses a network master key

Thread handles network transport only; application-layer protocols ride on top.

### Matter

**Matter** (formerly Project CHIP) is a unified application-layer standard backed by Apple, Google, Amazon, Samsung, and the Connectivity Standards Alliance. It runs over Thread, Wi-Fi, and Ethernet:

- **Unified data model**: devices expose clusters (attributes, commands, events) independent of transport
- **Multi-admin**: multiple ecosystems (Apple Home, Google Home, Alexa) control the same device
- **Secure commissioning**: QR code or BLE-based pairing with certificate-based authentication
- **Interoperability**: a Matter light bulb works with any Matter-certified controller

Matter solves the fragmentation problem of the smart-home ecosystem by providing a single standard that all major platforms support.

## Zigbee

Zigbee (IEEE 802.15.4 based) is a mesh networking protocol widely deployed in smart lighting, building automation, and industrial sensing. While older than Thread, it has a massive installed base:

- **Zigbee 3.0**: unified application library with standardized device profiles
- **Zigbee Green Power**: energy-harvesting devices (switches, sensors) with no battery
- **Limitation**: not IP-native; requires a gateway/bridge to integrate with IP networks

Zigbee and Thread share the same PHY (802.15.4) but differ at the network and application layers.

## LoRaWAN

**LoRaWAN** (Long Range Wide Area Network) enables low-power, wide-area connectivity for remote sensors. It trades data rate for range:

- **Range**: 2–15 km in urban, up to 50 km rural (line of sight)
- **Data rate**: 0.3–50 kbps (adaptive data rate based on link quality)
- **Topology**: star-of-stars; end devices communicate with gateways, which forward to a network server

| Parameter | LoRaWAN | Zigbee/Thread | BLE |
|-----------|---------|---------------|-----|
| Range | km-scale | 10–100 m | 10–50 m |
| Data Rate | Very low | Medium | Medium |
| Power | Years on battery | Years (sleepy) | Days–weeks |
| Topology | Star-of-stars | Mesh | Star/mesh |
| Use Case | Agriculture, utilities | Smart home, buildings | Wearables, beacons |

## BLE Mesh

**Bluetooth Low Energy (BLE) Mesh** (Bluetooth 5.0+) provides mesh networking for commercial lighting, sensor networks, and building automation:

- **Managed flooding**: messages are relayed by all nodes within range; TTL prevents infinite loops
- **Friendship**: low-power nodes (LPN) have a "friend" node that caches messages for them
- **Provisioning**: out-of-band pairing (QR, NFC) with application keys for access control

## Industrial IoT (IIoT)

Industrial environments demand determinism, reliability, and interoperability with legacy systems:

- **OPC UA**: unified architecture for industrial communication (information modeling, security, discovery)
- **Modbus/TCP**: legacy serial protocol over TCP; still widely deployed in PLCs and SCADA
- **PROFINET/EtherNet/IP**: real-time Ethernet for industrial automation
- **ISA-95/IEC 62264**: integration between enterprise (ERP) and control systems (MES, SCADA)

### Real-Time IoT

For control loops with strict timing requirements (< 1 ms), industrial IoT uses:

- **TSN (Time-Sensitive Networking)**: IEEE 802.1 standards for deterministic Ethernet—time synchronization (802.1AS), traffic scheduling (802.1Qbv), frame preemption (802.1Qbu)
- **Hard real-time PLCs**: dedicated industrial controllers with microsecond response times
- **5G URLLC**: 1 ms radio latency for wireless industrial control, replacing wired fieldbuses

## Interview Angle

> **"Compare MQTT and CoAP for an IoT deployment. When would you choose each?"**

MQTT uses TCP (reliable transport, stateful broker), excels for pub/sub patterns with retained state. CoAP uses UDP (lower overhead, RESTful), better for request/response and resource-constrained devices. Choose MQTT for continuous telemetry with offline queuing; CoAP for infrequent polling and constrained devices that need RESTful semantics.

> **"Why does Matter matter for the IoT industry?"**

Discuss fragmentation: before Matter, buying a smart device meant checking compatibility with each ecosystem. Matter provides a universal layer—devices work with any controller, reducing vendor lock-in, simplifying development, and improving consumer trust. Mention the commissioning flow (QR → BLE → Thread/Wi-Fi) as an interview-ready design detail.

## Key References

- MQTT v5.0 specification (OASIS)
- RFC 7252 — The Constrained Application Protocol (CoAP)
- Matter specification (CSA)
- Thread 1.3 specification (Thread Group)
- LoRaWAN 1.0.4 specification (LoRa Alliance)
