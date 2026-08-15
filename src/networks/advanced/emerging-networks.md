# Emerging Networks: Satellite, 5G/6G, NFV, and Next-Gen Transports

## Satellite Networks and LEO Constellations

### GEO vs. MEO vs. LEO

| Orbit | Altitude | RTT | Coverage | Examples |
-------|----------|-----|----------|----------|
 **GEO** | 35,786 km | ~240 ms (one-way ~120 ms) | Fixed, 42% of Earth surface | Viasat, HughesNet |
 **MEO** | 2,000–35,786 km | 50–150 ms | Regional constellations | O3b (8,000 km) |
 **LEO** | 200–2,000 km | 1–7 ms | Global (thousands of satellites) | Starlink, Kuiper, OneWeb |

### LEO Constellation Architecture

Starlink (SpaceX) uses ~5,400 operational satellites (targeting ~12,000, licensed for 42,000) in a shell constellation at 550 km altitude. Each satellite communicates with its neighbors via **laser inter-satellite links (ISL)**, forming a mesh network in space:

```
         Laser ISL
  Sat A ←─────────→ Sat B
    ↕                    ↕
  User link           User link
    ↕                    ↕
 Ground           Ground
 Station          Station
    ↕                    ↕
  User            User
```

Laser ISLs operate at ~100 Gbps with ~1μs latency per hop. A packet from New York to Tokyo routes through ~4–6 satellite hops, achieving end-to-end latency comparable to or better than fiber (~70–100 ms vs. ~130 ms for the great-circle fiber route, because the satellite path is geometrically shorter).

### Challenges

- **Handoff**: Satellites move at ~7.5 km/s. A user's connection must hand off to the next satellite every ~5–10 minutes. This requires fast link-layer reassociation.
- **Routing**: The topology changes continuously. Distributed routing (distance-vector or link-state) must converge faster than the topology changes. Starlink uses a centralized path computation (ground stations compute routes periodically) rather than distributed routing.
- **Spectrum management**: Ka-band (26.5–40 GHz) and Ku-band (12–18 GHz) have limited bandwidth. Frequency reuse requires careful beam planning to avoid interference between adjacent satellite beams.
- **Regulation**: ITU coordination, spectrum licensing, and space debris mitigation (satellites must deorbit within 25 years).

## Edge Networks and Fog Computing

### Edge vs. Fog vs. Cloud

| Layer | Location | Latency | Compute | Examples |
-------|----------|---------|---------|----------|
 **Cloud** | Regional datacenter | 20–100 ms | Heavy (GPUs, clusters) | AWS us-east-1 |
 **Edge (MEC)** | Cell tower / local DC | 1–10 ms | Moderate (servers) | AWS Outposts, 5G MEC |
 **Fog** | On-premise / gateway | <1 ms | Light (IoT gateways) | Industrial PLC, router |
 **Device** | End device | 0 ms | Minimal | Smartphone, sensor |

### Mobile Edge Computing (MEC)

MEC (ETSI standard) places compute resources at the **base station** or aggregation point of the cellular network. Use cases:

- **Video analytics**: Process camera feeds locally for traffic monitoring, security.
- **AR/VR**: Render frames near the user to meet <20ms motion-to-photon latency.
- **vRAN**: Virtualize the radio access network function itself on edge servers.
- **CDN edge**: Serve cached content from the cell tower (Cloudflare, Akamai edge nodes).

## 5G Core and Network Slicing

### 5G Architecture

5G separates the **Access Network (RAN)** from the **Core Network (5GC)**, with a service-based architecture:

```
UE (phone) → gNodeB (base station) → UPF (User Plane Function) → Internet
                      ↓
                 AMF (Access and Mobility Mgmt)
                 SMF (Session Mgmt)
                 AUSF (Authentication)
                 UDM (Unified Data Mgmt)
                 PCF (Policy Control)
                 NRF (NF Repository - service discovery)
```

Key 5GC functions are implemented as **microservices** communicating via HTTP/2 APIs (service-based interface, SBI). This enables cloud-native deployment (Kubernetes).

### Network Slicing

5G slicing allows a single physical network to provide logically isolated networks with different characteristics:

| Slice Type | Use Case | Requirements |
-----------|----------|-------------|
 **eMBB** | Video streaming, VR | High bandwidth (1 Gbps), moderate latency |
 **URLLC** | Autonomous driving, remote surgery | Ultra-low latency (<1 ms), ultra-reliability (99.999%) |
 **mMTC** | IoT, smart meters | Massive device density (10^6/km²), low throughput |

Each slice gets its own UPF instance, QoS policies, and resource guarantees. The AMF routes UE sessions to the appropriate slice based on subscription and slice selection policy.

### 5G Slicing Implementation

In practice, slicing is implemented via:
- **RAN slicing**: Partition PRBs (Physical Resource Blocks) per slice. A scheduler gives URLLC flows strict priority, eMBB gets the rest.
- **Core slicing**: Dedicated UPF/SMF instances per slice with isolated network functions.
- **Transport slicing**: Segment Routing or MPLS VPNs for slice-isolated transport.
- **Orchestration**: OSM/ONAP (MANO frameworks) provision and manage slice lifecycle.

## 6G Vision

6G (expected commercialization ~2030) targets:

- **Terahertz (0.1–10 THz) spectrum**: Enables 100 Gbps–1 Tbps peak rates but with ~10m range (requires massive MIMO and RIS).
- **Reconfigurable Intelligent Surfaces (RIS)**: Programmable metasurfaces that reflect and focus wireless signals, extending coverage and enabling beam steering without active amplification.
- **AI-native**: Network AI for autonomous optimization (self-healing, predictive resource allocation).
- **Sensing as a service**: Using wireless signals for sensing (detecting objects, gestures, breathing) alongside communication.
- **Non-terrestrial networks (NTN)**: Integrated satellite-terrestrial operation.

## NFV and Service Function Chaining

### NFV (Network Functions Virtualization)

NFV replaces dedicated hardware appliances (firewalls, load balancers, WAN optimizers) with software running on commercial servers:

```
Before NFV:                After NFV:
┌──────────┐              ┌──────────────────────────┐
│ Physical │              │     x86/ARM Server       │
│ Firewall │              │ ┌────┐ ┌────┐ ┌────┐    │
│ Appliance│              │ │ VNF│ │ VNF│ │ VNF│    │
└──────────┘              │ │ FW │ │ LB │ │NAT │    │
┌──────────┐              │ └────┘ └────┘ └────┘    │
│ Physical │              │    Managed by MANO/VNFM  │
│ LB       │              └──────────────────────────┘
│ Appliance│
└──────────┘
```

VNFs (Virtual Network Functions) run as VMs or containers. The MANO (Management and Orchestration) framework automates VNF lifecycle (onboard, instantiate, scale, terminate).

### Service Function Chaining (SFC)

SFC steers traffic through an **ordered sequence** of network functions:

```
Ingress → [Firewall VNF] → [DPI VNF] → [WAN Optimizer VNF] → Egress
```

Implemented via:
- **NSH (Network Service Header)**: Encapsulates packets with a service path ID and service index. Each VNF decrements the index and forwards to the next.
- **SR (Segment Routing)**: Each function is a segment. The ingress encodes the chain in the packet header.
- **TC/eBPF steering**: Linux traffic control or eBPF programs redirect packets between VNFs.

## Container Networking

### CNI (Container Network Interface)

CNI is the Kubernetes-standard plugin interface for configuring pod networking. When a pod is created, the kubelet calls the CNI plugin's `ADD` operation with the pod's network namespace and configuration. The plugin creates a veth pair, assigns an IP, and adds routes.

### eBPF CNI

Cilium's CNI uses eBPF instead of traditional iptables/veth:

- **No iptables**: BPF programs on TC hooks handle NAT, forwarding, and policy enforcement. This avoids the O(n) iptables rule traversal.
- **Direct routing**: Pods can route directly to each other (node-to-node via BPF encapsulation or native routing) without an overlay.
- **Bandwidth management**: BPF programs implement EDT (Earliest Departure Time) rate limiting, providing accurate per-pod bandwidth guarantees.

### Network Service Mesh

Network Service Mesh extends the service mesh concept to **layer 2/3**: it provides virtual network interfaces that follow workloads across clusters and clouds. A pod's network endpoint moves with it, maintaining the same IP and MAC address. This enables seamless workload migration between on-premises and cloud.

## QUIC Internals

See [../http/quic.md](../http/quic.md) for the QUIC overview. Here we cover internals:

### QUIC Connection Establishment

QUIC combines transport and TLS 1.3 handshake into a single round trip:

```
Client → Server: ClientHello (CRYPTO frame with TLS ClientHello)
Server → Client: Initial + Handshake (ServerHello, Certificate, Finished)
Client → Server: Handshake (Finished) + 1-RTT data
```

With 0-RTT resumption (pre-shared key from a previous connection), the client sends application data in the first flight:

```
Client → Server: Initial (CRYPTO: ClientHello with PSK) + 0-RTT data
Server → Client: Initial + Handshake (ServerHello, Finished)
```

0-RTT data is vulnerable to replay attacks — the server may have processed this data already during a previous connection. Applications must ensure 0-RTT requests are idempotent.

### QUIC Loss Detection and Congestion Control

QUIC uses separate packet number spaces for Initial, Handshake, and 1-RTT packets (each starts at 0). This prevents ambiguity: an ACK for packet 0 in the Handshake space cannot be confused with an ACK for packet 0 in the 1-RTT space.

QUIC's loss detection is similar to TCP's but with improvements:
- **Packet number gap**: If packet N is acked but N-1 is not, N-1 is declared lost immediately (no need to wait for 3 duplicate ACKs, since QUIC has no inherent ordering).
- **Time threshold**: A packet is lost if it was sent more than `kPacketThreshold` packets or `kTimeThreshold × smoothed_rtt` ago.
- **No retransmission ambiguity**: Unlike TCP (where a retransmitted packet has the same sequence number), QUIC retransmissions get new packet numbers. The original's ACK still arrives, providing an accurate RTT sample.

### Multipath QUIC (MPQUIC)

MPQUIC (draft-ietf-quic-multipath) extends QUIC to use multiple paths simultaneously (e.g., WiFi + cellular, or multiple network interfaces). Each path has its own congestion controller and RTT estimator. The connection ID identifies the path. MPQUIC enables seamless handoff between networks without connection interruption — critical for mobile devices.

### MASQUE

MASQUE (Multiplexed Application Substrate over QUIC Encryption, RFC 9298) provides a framework for proxying arbitrary traffic over QUIC. It defines:

- **CONNECT-UDP**: Proxy UDP traffic over QUIC (replaces DNS-over-HTTPS for DNS, supports QUIC-aware proxies).
- **CONNECT-IP**: Proxy IP traffic (any IP protocol) over QUIC.
- **Extended CONNECT**: Proxy TCP traffic over QUIC.

MASQUE enables private relay services (like Apple's iCloud Private Relay or Cloudflare WARP) that proxy traffic through an intermediary without the intermediary seeing the content (QUIC encryption end-to-end).

## HTTP/3

See [../http/http3.md](../http/http3.md) for the HTTP/3 overview. Key internals:

HTTP/3 maps HTTP semantics onto QUIC streams. Each request-response pair uses a single bidirectional QUIC stream. HTTP/3 uses **QPACK** for header compression (similar to HPACK in HTTP/2, but designed for QUIC's non-head-of-line-blocking streams).

## Encrypted Transport

### DoH (DNS over HTTPS) and DoT (DNS over TLS)

DoH (RFC 8484) sends DNS queries as HTTPS requests (POST or GET to a well-known URI). DoT (RFC 7858) wraps DNS in a TLS connection on port 853. Both prevent on-path observers from seeing DNS queries (which reveal browsing intent).

| Feature | DoH | DoT |
---------|-----|-----|
 **Port** | 443 (standard HTTPS) | 853 (dedicated) |
 **Transport** | HTTP/2 (can multiplex queries) | TLS (one query per connection or pipelined) |
 **Firewall traversal** | Easy (looks like HTTPS) | May be blocked |
 **Overhead** | HTTP framing + TLS | TLS only |
 **Adoption** | Cloudflare 1.1.1.1, Google 8.8.8.8 | Most resolvers |

### Oblivious DNS over HTTPS (ODoH)

ODoH (RFC 9230) adds a proxy layer to DoH: the client encrypts the DNS query with the resolver's public key and sends it through a **relay proxy**. The relay cannot see the query content; the resolver cannot see the client's IP. This provides metadata privacy beyond DoH/DoT:

```
Client → Relay (encrypted query, Relay can't read) → Resolver (decrypts, resolves, encrypts response)
Resolver → Relay (encrypted response) → Client (decrypts)
```

Implemented by Cloudflare (ODoH relay + resolver) and Apple (as part of iCloud Private Relay).

> **Interview Angle**: "What's the difference between encrypted DNS and a VPN?" — Encrypted DNS (DoH/DoT/ODoH) only encrypts DNS queries, not the actual HTTP traffic. A VPN encrypts all traffic. DoH prevents DNS-based tracking (seeing which domains you visit) but the connection to the web server is still visible to on-path observers (IP, SNI in TLS ClientHello). Encrypted Client Hello (ECH) addresses the SNI leak, completing transport-layer privacy.
