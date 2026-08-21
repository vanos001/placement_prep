# Geneve Overlay Network

Geneve (Generic Network Virtualization Encapsulation) is a network overlay protocol, standardized in RFC 8926 (2020). It generalizes VXLAN by using a flexible Type-Length-Value (TLV) header, allowing network devices to encode any metadata. Geneve is the standard overlay for modern SDN (Software-Defined Networking) solutions: OVN, Open Virtual Network (OVN-Kubernetes), Anthos, and Cilium's BGP-aware mode. This page covers the packet format, the VXLAN-to-Geneve migration, and the production use cases.

## The VXLAN Limitations

VXLAN (RFC 7348, 2014) is the older overlay protocol. Its 8-byte header is fixed:

```text
VXLAN header (8 bytes):
  Flags (1 byte) + Reserved (3 bytes) + VXLAN Network ID (3 bytes) + Reserved (1 byte)
```

The 24-bit VNI (VXLAN Network ID) gives 16M virtual networks — enough for most deployments. But the fixed header doesn't allow:
- Per-flow metadata (e.g., the source application).
- Quality-of-Service tagging.
- Encryption metadata.

Geneve addresses this with a TLV-based header.

## The Geneve Packet

```text
Outer UDP header (8 bytes):
  Source port: hash of inner packet (for ECMP load balancing)
  Destination port: 6081 (Geneve's IANA-assigned port)
  Length: outer UDP + Geneve + inner packet lengths
  Checksum: 0 (typically)

Geneve header (variable, 8+ bytes):
  Version (2 bits): 0
  Option Length (6 bits): length of options in 4-byte words
  O (1 bit): OAM (Operations, Administration, Maintenance)
  C (1 bit): critical options present
  Reserved (6 bits)
  Protocol Type (2 bytes): inner Ethernet = 0x6559
  VNI (3 bytes) + Reserved (1 byte)
  Options (variable, 4 to 256 bytes):
    TLV format: Type (2 bytes) + Length (1 byte) + Reserved (3 bits) + Value

Inner packet (Ethernet + IP + TCP/UDP/...)
```

The TLV options can encode:
- `Type 0x01`: Geneve policy (firewall metadata).
- `Type 0x02`: Custom (vendor-specific).
- `Type 0x03`: Network policy (e.g., Cilium's identity).
- `Type 0x06`: Intra-cluster routing.
- `Type 0x09`: Generic destination routing.

## The Overlay Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Underlay network (physical): e.g., 10.0.0.0/16            │
│  Standard IP routing, no overlay awareness                 │
└─────────────────────────────────────────────────────────────┘
       ↑                                       ↑
       │                                       │
┌──────┴────────┐                     ┌──────┴────────┐
│  Host 1        │                     │  Host 2        │
│  VTEP/PE       │                     │  VTEP/PE       │
│  geneve0 iface │                     │  geneve0 iface │
│  VNI: 100      │ ←──────────────────→│  VNI: 100      │
│  (10.0.0.1)    │   UDP/6081 packet   │  (10.0.0.2)    │
└────────────────┘                     └────────────────┘
       ↑                                       ↑
       │                                       │
┌──────┴────────┐                     ┌──────┴────────┐
│  Pod A         │                     │  Pod B         │
│  192.168.1.10 │                     │  192.168.1.11  │
└────────────────┘                     └────────────────┘
```

The hosts' VTEPs (Virtual Tunnel Endpoints) encapsulate inner packets (Pod A → Pod B traffic) in UDP/6081 outer packets. The underlay network sees only outer IP/UDP; the overlay network sees the original inner packet.

## The MTU Problem

Overlay encapsulation adds 50-100 bytes to each packet (Geneve header + outer UDP + outer IP + outer Ethernet). If the underlay network has a 1500-byte MTU (standard Ethernet), the overlay must use a 1450-byte MTU to avoid fragmentation.

```text
Underlay MTU: 1500 bytes
Overlay MTU: 1500 - 20 (outer IP) - 8 (outer UDP) - 8 (Geneve min header) = 1464 bytes
```

The pod interface's MTU must be set to 1450 (or lower) to account for the overlay overhead. If not, large packets get fragmented, causing significant performance issues.

Many Kubernetes CNIs handle MTU automatically:
- Cilium: auto-detects underlay MTU and sets pod MTU to underlay - 50.
- Calico: same, configurable via `mtu` setting.
- Flannel (VXLAN): same.

## Production Use Cases

### Kubernetes CNIs

- **Cilium**: uses Geneve in its "BGP-aware" mode. Default mode uses VXLAN; Geneve is opt-in.
- **OVN-Kubernetes**: uses Geneve as the default overlay.
- **Calico**: uses VXLAN or IPIP, not Geneve (by default).
- **Antrea**: uses Geneve or VXLAN.

### Anthos (Google Cloud)

Anthos uses Geneve as its overlay for multi-cluster Kubernetes networking. Each cluster's pods can communicate with pods in other clusters via Geneve tunnels.

### OVN (Open Virtual Network)

OVN is a widely-used SDN controller (used by OpenStack, OVN-Kubernetes, and others). It uses Geneve as its overlay, with TLV options to encode routing metadata.

## ECMP and Load Balancing

The outer UDP source port is hashed from the inner packet's 5-tuple (src IP, src port, dst IP, dst port, protocol). This allows the underlay to use ECMP (Equal-Cost Multi-Path) routing to spread flows across multiple paths:

```text
Inner packet (TCP 5-tuple: A:1234 → B:80, TCP)
   │
   ▼
Outer UDP source port: hash(5-tuple) = 12345
   │
   ▼
Underlay router sees UDP packet with src=12345, picks ECMP path based on src port
```

Different inner flows (with different 5-tuples) hash to different outer UDP source ports, spreading across the underlay's paths.

## The Geneve TLV in Practice

```c
// Cilium's Geneve TLV for source identity (Type 0xC0):
struct geneve_opt_cilium {
    __be16 opt_class;       // Cilium's class: 0x0102 (assigned by IANA)
    __u8 type;              // 0x80 (Cilium identity)
    __u8 length: 5;        // 4 bytes of value
    __u8 rsvd: 3;
    __be32 identity;       // Cilium security identity
};
```

This TLV tells the receiving VTEP "this packet came from Cilium identity 42" — useful for enforcing network policy without re-evaluating the source's identity.

## Comparison to VXLAN

| Aspect | VXLAN | Geneve |
|--------|-------|--------|
| Header size | 8 bytes (fixed) | 8+ bytes (TLV) |
| Metadata | VNI only | VNI + arbitrary TLVs |
| Destination port | 4789 | 6081 |
| Standard | RFC 7348 (2014) | RFC 8926 (2020) |
| Production users | Most CNIs (default) | OVN, Anthos, Cilium BGP mode |
| Hardware support | Mature (most switches) | Mature (newer switches) |

For greenfield deployments in 2024+, Geneve is preferred (more flexible). For compatibility with older hardware, VXLAN remains common.

## Common Pitfalls

1. **Forgetting the MTU overhead.** Overlay encapsulation adds 50-100 bytes. Set the pod MTU to underlay - 50 to avoid fragmentation.

2. **Forgetting that Geneve uses UDP port 6081.** Firewalls must allow this port for the overlay to work.

3. **Forgetting that the TLV options are optional.** A device that doesn't understand a TLV option must skip it (the `Option Length` field gives the size). Don't assume all VTEPs understand all TLVs.

4. **Forgetting that Geneve is just an overlay, not a security boundary.** The overlay doesn't encrypt; for security, use IPSec or WireGuard on top.

5. **Forgetting that ECMP depends on the source port hash.** If the source port is set to a fixed value (some implementations), ECMP doesn't work — all flows use the same path.

6. **Forgetting that the VNI is global per underlay.** Two hosts with VNI=100 are in the same overlay network, regardless of physical location. Use distinct VNIs for distinct networks.

## References

- [RFC 8926: Geneve](https://datatracker.ietf.org/doc/html/rfc8926)
- [RFC 7348: VXLAN](https://datatracker.ietf.org/doc/html/rfc7348)
- [OVN-Kubernetes architecture](https://github.com/ovn-org/ovn-kubernetes/blob/master/docs/architecture.md)
- [Cilium: BGP-aware overlay mode](https://docs.cilium.io/en/stable/network/bgp-control-plane/)
- [Anthos networking](https://cloud.google.com/anthos/clusters/docs/security/networking)
- [Geneve in Open vSwitch (OVS)](https://docs.openvswitch.org/en/latest/topics/)
- [LWN: Geneve vs VXLAN (2021)](https://lwn.net/Articles/850489/)
- [Geneve vs VXLAN comparison (NVIDIA)](https://docs.nvidia.com/networking-ethernet-software/knowledge-base.html)
