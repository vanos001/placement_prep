# Modern Network Architecture: TSN, Segment Routing, Telemetry, and Verification

## Deterministic Networking and TSN

### The Need for Determinism

Best-effort Ethernet provides no timing guarantees. For industrial automation, autonomous vehicles, and professional audio, this is unacceptable — a control loop that misses its deadline by 1ms can cause a robot arm to crash or a missed brake signal. **Deterministic networking** guarantees bounded latency and jitter.

### TSN (Time-Sensitive Networking)

TSN is a set of IEEE 802.1 standards that adds deterministic scheduling to standard Ethernet. It is the evolution of AVB (Audio Video Bridging):

| Standard | Function |
|----------|----------|
 **802.1AS-Rev** | Precision Time Protocol (PTP) — sub-microsecond clock synchronization |
 **802.1Qbv** | Time-Aware Shaper (TAS) — schedule-based traffic transmission |
 **802.1Qci** | Per-Stream Filtering and Policing — admission control |
 **802.1Qbu/802.3br** | Frame Preemption — interrupt a low-priority frame for high-priority |
 **802.1CB** | Frame Replication and Elimination for Reliability (FRER) |
 **802.1Qcc** | Stream Reservation Protocol (SRP) for configuration |

### Time-Aware Shaper (802.1Qbv)

The TAS divides time into **gates** — each gate opens for a specific traffic class at a precisely scheduled time:

```
Time →
|--- Control ---|-- AVB ---|--- Best Effort ---|-- Control ---|-- AVB --|
^                 ^                              ^               ^
t0               t1                             t2              t3

The switch transmits each class only during its gate window.
Gate schedule is computed offline and distributed to all switches.
```

The schedule is a cyclic table: every cycle (e.g., 1ms), the same gate sequence repeats. Traffic class A (control) gets guaranteed slots; class B (AVB/streaming) gets residual bandwidth; class C (best effort) fills what's left. This provides hard latency bounds for class A traffic.

> **Interview Angle**: "How do you compute a TSN schedule?" — It's a constraint satisfaction / optimization problem. Each flow has a deadline and maximum hop count. The scheduler must assign each flow a time slot on each link such that: (1) no two flows overlap on the same link, (2) each flow arrives at its destination before its deadline, (3) the total schedule fits in the cycle time. This is NP-hard in general; heuristics (SMT solvers, list scheduling) are used in practice.

## Segment Routing

### Concept

Segment Routing (SR) encodes the packet's path as an **ordered list of segments** in the packet header. Each segment is an instruction ("go to node X" or "apply policy Y"). The source router encodes the entire path; intermediate routers simply follow the top segment.

### SR-MPLS

In SR-MPLS, segments are encoded as an MPLS label stack:

```
Packet: [Outer Label: Node 3] [Label: Node 7] [Label: Service A] [Payload]
         ↓                    ↓                ↓
     Forward to 3        At node 3,         Apply
                         pop label,         Service A
                         forward to 7
```

The ingress router pushes the full label stack. Each transit router pops the top label and forwards to the next. This is called **source routing** — the ingress determines the full path.

**Advantages over LDP/RSVP-TE**:
- **No per-flow state in the network**: Transit routers only do label lookup (O(1)). No LSP state to maintain.
- **Scalable**: Adding a new path doesn't require signaling to intermediate routers.
- **Fast reroute**: TI-LFA (Topology-Independent Loop-Free Alternate) computes backup paths using segment routing — <50ms recovery.

### SRv6

SRv6 encodes segments as **IPv6 extension headers** (Segment Routing Header, SRH):

```
IPv6 Header (DA = first segment)
SRH:
  [Next Header] [Hdr Ext Len] [Routing Type] [Segments Left: 3]
  [Segment List[0]: 2001:db8::3]  ← active segment (DA of IPv6)
  [Segment List[1]: 2001:db8::7]
  [Segment List[2]: 2001:db8::A]  ← final segment
  [Payload]
```

Each node updates the IPv6 Destination Address to the next segment and decrements Segments Left. SRv6 segments can be IPv6 addresses of nodes (topological) or function addresses (behavior, e.g., "decrypt and forward" or "apply firewall policy").

SRv6 is used in 5G core networks (3GPP Release 16+), where segments represent UPF (User Plane Function) processing steps. The flexibility of IPv6 addressing makes SRv6 more expressive than SR-MPLS but with a larger header overhead (each segment = 16 bytes vs. 4 bytes for MPLS labels).

## Programmable Telemetry and INT

### The Observability Gap

SNMP, sFlow, and NetFlow provide **aggregated** statistics (counters per interface/flow). They cannot answer: "What exactly happened to packet #12345?" or "What is the microsecond-level queue depth at switch port 3 right now?" **In-band Network Telemetry (INT)** fills this gap.

### INT (In-band Network Telemetry)

INT inserts **per-packet telemetry metadata** directly into packets as they traverse the network:

```
Original:  [Ethernet][IP][TCP][Payload]

With INT: [Ethernet][IP][TCP][INT Metadata Header]
           [Switch 1 metadata: ingress/egress port, queue depth, latency]
           [Switch 2 metadata: ingress/egress port, queue depth, latency]
           [Switch 3 metadata: ingress/egress port, queue depth, latency]
           [INT Metadata Trailer]
           [Payload]
```

Each switch along the path appends a metadata entry: ingress/egress port, queue occupancy, egress queue depth, and hop latency (calculated from timestamps). The receiver (or a dedicated telemetry collector) extracts this data.

Implemented on P4-programmable switches (Tofino) and supported by VMware, Arista, and Intel. INT provides **microsecond-granularity** visibility but adds per-packet overhead (~30–60 bytes per hop) and requires programmable hardware.

### Network Tomography

When INT is not available, **network tomography** infers internal network characteristics from end-to-end measurements:

- **Loss tomography**: Send probe packets from multiple sources to multiple receivers. Use the matrix of observed loss rates and maximum likelihood estimation to infer per-link loss probabilities.
- **Delay tomography**: Measure end-to-end delays and use multivariate regression or tomographic reconstruction to estimate per-link delays.
- **Traffic matrix estimation**: Use SNMP link counts and the relationship Σ(source × destination traffic on link) = link count. Solve the underdetermined system using gravity models or compressed sensing.

## Traffic Classification

Network operators need to identify what traffic is flowing (video, P2P, malware, specific applications) for QoS, security, and billing. Approaches:

| Method | How It Works | Limitation |
|--------|-------------|------------|
 **Port-based** | Match on well-known ports (80=HTTP, 443=HTTPS) | Encrypted traffic uses random ports |
 **DPI (Deep Packet Inspection)** | Match on payload patterns | Cannot inspect encrypted traffic |
 **Statistical/ML** | Classify based on flow statistics (packet sizes, inter-arrival times) | Training data dependency, adversarial |
 **Encrypted traffic analysis** | Use TLS SNI (unencrypted), JA3/JA4 fingerprinting | ESNI/ECH encrypts SNI |

The rise of encrypted traffic (90%+ of web traffic is HTTPS) has made traditional DPI largely ineffective. Modern approaches use **metadata** (TLS ClientHello SNI, QUIC handshake, flow statistics) for classification.

## Traffic Engineering

Traffic engineering (TE) optimizes the utilization of network paths. In a datacenter, TE ensures traffic is spread across multiple paths to avoid hotspots.

### ECMP and Its Limitations

ECMP (Equal-Cost Multi-Path) spreads flows across equal-cost paths using a hash of the 5-tuple. Problem: **elephant flows** (large, long-lived) may hash to the same path, creating a hotspot. Also, ECMP doesn't consider real-time link utilization.

### Weighted ECMP and WCMP

WCMP assigns weights to paths, splitting traffic proportionally. A path with weight 3 gets 3× the traffic of a path with weight 1. Implemented via a hash-to-weight mapping.

### Centralized TE

Google's B4 and Facebook's Fabric use centralized traffic engineering: a global controller computes the optimal assignment of flows to paths every few seconds, considering current link utilizations and traffic demands. This is solved as a linear program (minimize max link utilization) or via heuristics.

## SDN and OpenFlow

### SDN Architecture

Software-Defined Networking separates the **control plane** (routing decisions) from the **data plane** (packet forwarding):

```
SDN Controller (e.g., ONOS, OpenDaylight)
  ↕ Southbound API (OpenFlow, P4Runtime)
Switches (data plane)
  ↕ Northbound API (REST, gRPC)
Applications (TE, firewall, LB)
```

### OpenFlow

OpenFlow (ONF) was the first standardized southbound API. It defines a fixed pipeline of flow tables with match-action entries:

- **Match fields**: Ingress port, Ethernet src/dst, IP src/dst, TCP/UDP ports, etc.
- **Actions**: Forward (to port/group), modify (set field), enqueue (to queue), drop.
- **Tables**: Sequential pipeline — packets flow through table 0 → table 1 → ... → egress.

OpenFlow 1.3+ supports multiple tables, meters, and group tables. However, OpenFlow's fixed pipeline and limited header space made it insufficient for modern needs — leading to P4 and P4Runtime.

### P4Runtime

P4Runtime is the **southbound API for P4 switches**. It separates concerns:

- **P4 program** defines the pipeline (what the switch can do).
- **P4Runtime** configures the pipeline at runtime (which entries are in the tables).

P4Runtime uses gRPC for the control channel, supports streaming telemetry (for INT), and provides transactional updates (set multiple table entries atomically). It is the successor to OpenFlow for programmable data planes.

## Network Verification

### The Problem

Network configurations are complex (thousands of ACLs, BGP policies, VLAN configs). A single misconfiguration can cause an outage. Network verification tools **prove** properties about a network before deployment.

### Batfish

Batfish (Microsoft Research, now open source) analyzes network configurations (Cisco, Juniper, Arista) and answers queries: "Can host A reach host B?", "Which flows match ACL X?", "Is there a routing loop?" It builds a vendor-independent model from the configurations and performs symbolic execution of the forwarding logic.

### Header Space Analysis (HSA)

HSA (Kazemian et al., 2012) models the network as a function mapping the **entire header space** (all possible packet headers) to output ports. It uses symbolic representation of header fields (bitvectors) and tracks how the set of possible packets transforms at each hop. It can prove properties like "no packet with source 10.0.0.0/8 can reach 192.168.0.0/16."

### Minesweeper

Minesweeper (University of Washington) converts network configurations into a **SAT/SMT formula** and uses a constraint solver (Z3) to check if invariants hold. It can verify BGP route propagation, ACL reachability, and firewall consistency. The advantage: it handles complex interactions between protocols (e.g., route maps interacting with prefix lists).

### Symbolic Execution in Networking

All three tools share a common approach:

1. **Model**: Abstract the network devices as forwarding functions (f: packet → action).
2. **Symbolize**: Represent sets of packets as symbolic expressions (e.g., `src_ip ∈ 10.0.0.0/8 ∧ dst_port ∈ [80, 443]`).
3. **Compose**: Chain device functions: `f_total = f_n ∘ ... ∘ f_2 ∘ f_1`.
4. **Verify**: Check that the composed function satisfies the desired invariant.

> **Interview Angle**: "How would you verify that a firewall change won't break connectivity?" — Use Batfish or a similar tool: (1) snapshot the current network configs, (2) apply the proposed firewall change, (3) query: "for each critical service pair (A, B), is B still reachable from A?" If any pair breaks, the change is unsafe. This can be automated in CI/CD as a pre-deployment check.

### Comparison: Verification Tools

| Tool | Approach | Input | Strength |
|------|----------|-------|----------|
 **Batfish** | Vendor-specific config parsing + symbolic eval | Config files (CLI) | Real-world configs, ACL analysis |
 **HSA** | Header space as universe, set operations | Abstract model | Mathematical completeness |
 **Minesweeper** | SAT/SMT encoding + Z3 | Config files | Complex protocol interactions |
 **SecGuru** | Data-plane invariants | Config files | Security policy verification |
 **NetKAT** | Algebraic (Kleene algebra) | P4-like programs | Formal proof, equational reasoning |