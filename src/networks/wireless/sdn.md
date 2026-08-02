# SDN — Software-Defined Networking

## Overview

SDN is a network architecture that **separates the control plane** (routing decisions) **from the data plane** (packet forwarding). A centralized controller programs network devices, enabling dynamic, manageable, and cost-effective networks.

## Traditional vs SDN Architecture

```mermaid
graph TD
    subgraph "Traditional Networking"
        T1[Switch 1<br>Control + Data] --- T2[Switch 2<br>Control + Data]
        T2 --- T3[Switch 3<br>Control + Data]
        T3 --- T1
    end
    subgraph "SDN Architecture"
        C[SDN Controller<br>Control Plane]
        S1[Switch 1<br>Data Plane Only]
        S2[Switch 2<br>Data Plane Only]
        S3[Switch 3<br>Data Plane Only]
        C -->|OpenFlow| S1
        C -->|OpenFlow| S2
        C -->|OpenFlow| S3
    end
```

## SDN Layers

```mermaid
graph TD
    subgraph "Application Plane"
        A1[Network Monitoring]
        A2[Load Balancing]
        A3[Firewall Rules]
        A4[Traffic Engineering]
    end
    subgraph "Control Plane"
        C[SDN Controller<br>OpenDaylight, ONOS, Floodlight]
    end
    subgraph "Data Plane"
        D1[Switch 1]
        D2[Switch 2]
        D3[Switch 3]
    end
    A1 --> C
    A2 --> C
    A3 --> C
    A4 --> C
    C --> D1
    C --> D2
    C --> D3
```

| Layer | Function | Examples |
|-------|----------|----------|
| **Application** | Network services and policies | Load balancers, firewalls, monitoring |
| **Control** | Centralized network brain | OpenDaylight, ONOS, Floodlight |
| **Data** | Packet forwarding | OpenFlow switches, white-box switches |

## OpenFlow Protocol

OpenFlow is the standard SDN protocol between controller and switches:

### Flow Table Entry

| Field | Description |
|-------|-------------|
| **Match** | Header fields to match (IP, port, MAC, etc.) |
| **Actions** | What to do with matched packets (forward, drop, modify) |
| **Priority** | Rule precedence |
| **Counters** | Packet/byte counters |
| **Timeouts** | Idle/hard timeout for rule expiration |

### OpenFlow Messages

```mermaid
sequenceDiagram
    participant C as Controller
    participant S as Switch
    C->>S: FlowMod (add/modify/delete flow)
    S->>C: PacketIn (no matching flow)
    C->>S: PacketOut (send packet)
    S->>C: FlowRemoved (flow expired)
    S->>C: PortStatus (link up/down)
    C->>S: MultipartRequest (statistics)
    S->>C: MultipartReply
```

### Example Flow Rules

```
# Forward HTTP traffic to web server
Match: IP dst=10.0.0.1, TCP dst_port=80
Action: output:port3

# Drop SSH from external
Match: IP src=203.0.113.0/24, TCP dst_port=22
Action: drop

# Default rule (send to controller)
Match: *
Action: send_to_controller
```

## SDN Controllers

| Controller | Language | Features |
|-----------|----------|----------|
| **OpenDaylight** | Java | Modular, production-grade, multi-protocol |
| **ONOS** | Java | Distributed, carrier-grade, high availability |
| **Floodlight** | Java | Lightweight, OpenFlow-focused |
| **Ryu** | Python | Simple, good for learning |
| **P4Runtime** | - | P4-programmable data planes |

## SDN Benefits

| Benefit | Description |
|---------|-------------|
| **Centralized management** | Single point of control for entire network |
| **Programmability** | APIs for automation and custom applications |
| **Vendor independence** | White-box switches, open protocols |
| **Rapid innovation** | New features via software, not hardware |
| **Cost reduction** | Commodity hardware, centralized management |
| **Dynamic configuration** | Real-time policy changes |

## SDN Use Cases

```mermaid
graph TD
    A[SDN Use Cases] --> B[Data Center Networking]
    A --> C[Wide Area Networks]
    A --> D[Network Virtualization]
    A --> E[Security]
    A --> F[traffic Engineering]
    B --> G[Google B4 WAN]
    B --> H[VMware NSX]
    C --> I[SD-WAN]
    D --> J[Overlay networks]
    E --> K[Dynamic firewalling]
    F --> L[Load balancing]
```

## SD-WAN

SD-WAN applies SDN principles to WAN connections:

```mermaid
graph TD
    subgraph "Branch Office"
        SDWAN[SD-WAN Appliance]
    end
    subgraph "Transport Options"
        MPLS[MPLS Link]
        INET[Internet Link]
        LTE[LTE/5G Link]
    end
    subgraph "Cloud / HQ"
        GW[SD-WAN Gateway]
    end
    SDWAN --> MPLS --> GW
    SDWAN --> INET --> GW
    SDWAN --> LTE --> GW
```

**Benefits**: Application-aware routing, cost savings (use internet instead of MPLS), centralized management, automatic failover.

## Interview Questions

1. **Q: What is SDN and why is it important?**
   A: SDN separates the control plane (routing decisions) from the data plane (packet forwarding). A centralized controller programs network devices. Benefits: centralized management, programmability, vendor independence, and rapid innovation.

2. **Q: What is OpenFlow?**
   A: The standard SDN protocol between controller and switches. It defines how the controller installs flow rules (match + action) in switches. When a packet doesn't match any rule, it's sent to the controller (PacketIn).

3. **Q: What's the difference between traditional and SDN networking?**
   A: Traditional: each device has its own control plane (distributed). SDN: centralized control plane manages all devices. Traditional requires CLI/SNMP per device. SDN uses APIs for programmatic control.

4. **Q: What is SD-WAN?**
   A: SD-WAN applies SDN to WAN connections. It aggregates multiple transport links (MPLS, internet, LTE) and routes traffic based on application requirements. Benefits: cost savings, application-aware routing, centralized management.

5. **Q: What are the challenges of SDN?**
   A: 1) Single point of failure (controller), 2) Scalability (controller must handle all decisions), 3) Security (controller is a high-value target), 4) Latency (controller-switch communication), 5) Vendor lock-in (despite open standards).

## Common Mistakes

- Confusing SDN (architecture) with OpenFlow (protocol)
- Assuming SDN eliminates all hardware (data plane still needs switches)
- Not understanding that SDN controller is a single point of failure
- Forgetting that SDN requires well-defined APIs between layers
- Confusing SDN with NFV (complementary but different)

## Summary

SDN separates control and data planes, enabling centralized, programmable network management. OpenFlow is the standard protocol. SD-WAN applies SDN to WAN. Benefits include programmability, vendor independence, and dynamic configuration.

## Cross-References

- [Wireless Overview](README.md)
- [NFV](nfv.md) — Complementary technology
- [5G](5g.md) — 5G uses SDN principles
- [Load Balancing](../load-balancing/README.md) — SDN use case

## Cross References

- [NFV](nfv.md)
- [Load Balancing](../load-balancing/README.md)
- [Cloud Virtualization](../../cloud/virtualization/README.md)
