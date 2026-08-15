# Programmable Networks: P4, SmartNICs, DPDK, XDP, and eBPF Networking Advanced

## P4 (Programming Protocol-Independent Packet Processors)

### What P4 Is

P4 is a **domain-specific language** for defining how network switches process packets. Unlike OpenFlow, which configures a fixed pipeline (match-action tables with predefined headers), P4 lets you define the pipeline itself — the headers to parse, the match-action tables, and the control flow between them.

A P4 program defines:
1. **Headers**: The packet header formats to parse (Ethernet, IPv4, IPv6, custom headers).
2. **Parsers**: State machines that extract header fields from the byte stream.
3. **Match-Action Tables**: Tables with keys (header fields), actions (modify/count/forward), and control logic.
4. **Deparsers**: Reconstruct the packet from modified headers and payload.

```p4
// Simplified P4 parser
parser MyParser(packet_in b, out headers h) {
    state start {
        b.extract(h.ethernet);
        transition select(h.ethernet.etherType) {
            0x0800: parse_ipv4;
            default: accept;
        }
    }
    state parse_ipv4 {
        b.extract(h.ipv4);
        transition accept;
    }
}
```

### P4 Targets and Switch ASICs

P4 code must be compiled for a specific **target architecture** — the hardware capabilities of the switch:

| Target | Vendor | Key Feature |
--------|--------|-------------|
 **Tofino** (Tofino 1/2/3) | Intel/Barefoot | First merchant P4-programmable ASIC. 12.8 Tbps. Reconfigurable match-action pipeline. |
 **Tofino2** | Intel | 65.5 Tbps. Added IPv6 header support, register arrays, multicast enhancements. |
 **Marvell Prestera** | Marvell | P4-capable programmable pipeline. |
 **Cisco Silicon One** | Cisco | Proprietary programmable architecture with P4-like capabilities. |
 **NetFPGA** | Academic | FPGA-based P4 target for research. |
 **P4 software switch (bmv2)** | Open source | Software reference implementation. Slow but correct. Used for P4 development and testing. |

Tofino's architecture uses a **reconfigurable match-action table (RMT)**: a fixed pipeline of ingress/egress stages, each containing an ALU, SRAM for match tables, and TCAM for exact/wildcard matches. The P4 compiler maps the P4 program onto these stages, allocating table entries to SRAM/TCAM and scheduling ALU operations.

> **Interview Angle**: "Why not just use OpenFlow?" — OpenFlow configures a fixed pipeline (you can only add/remove flow entries). If you need a new header field (e.g., for a custom protocol or telemetry), you can't — the ASIC doesn't know how to parse it. P4 reprograms the pipeline itself. At scale (Google's datacenters), custom load balancing, congestion signals, and telemetry require header fields and actions that no fixed-pipeline ASIC provides.

### SmartNICs

A SmartNIC is a network interface card with an **embedded processor** (ARM cores, FPGA, or programmable ASIC) that can run custom network functions offloaded from the host CPU:

```
Traditional NIC:          SmartNIC:
┌──────────┐              ┌──────────┐
│   Host   │              │   Host   │
│   CPU    │              │   CPU    │
├──────────┤              ├──────────┤
│  PCIe    │              │  PCIe    │
├──────────┤              ├──────────┤
│  NIC     │              │ NIC +    │
│ (dumb    │              │ embedded │
│  DMA)    │              │ CPU/FPGA │
└──────────┘              └──────────┘
```

SmartNIC use cases:
- **OVS offloading**: Run Open vSwitch datapath on the NIC, freeing host CPU. NVIDIA BlueField-2 DPU (Data Processing Unit) runs a full Linux kernel with OVS, storage, and security functions.
- **TLS termination**: Decrypt/encrypt TLS at line rate on the NIC (Marvell LiquidIO, Intel QAT on IPU).
- **Stateful firewall/NAT**: Maintain connection tracking tables on the NIC.
- **RDMA/NVMe-oF acceleration**: Hardware protocol processing.
- **Key-value caching**: Buffer small cache lookups on the NIC (MC-NIC, EMA).

The trade-off: SmartNICs cost more ($500–2000 vs. $50–200 for a dumb NIC) and add complexity. They pay for themselves when the host CPU savings from offloading justify the cost — typically in cloud hyperscalers running millions of VMs/containers.

## DPDK Networking

The **Data Plane Development Kit** (DPDK) enables user-space packet processing by bypassing the Linux kernel networking stack entirely. See [../../os/advanced/fast-io.md](../../os/advanced/fast-io.md) for DPDK fundamentals. Here we cover advanced DPDK patterns relevant to programmable networking:

### DPDK Architecture Recap

- **PMD (Poll Mode Driver)**: Bypasses kernel interrupts; the application polls for packets in a tight loop. Achieves 10–100M packets/second (vs. ~1M with kernel).
- **Hugepages + mbuf pool**: Pre-allocated memory from hugepages, with a free-list of mbuf structs for zero-allocation packet processing.
- **rte_ring**: Lock-free SPSC/MPSC ring buffers for passing packets between cores.

### Advanced DPDK: Flow Classification and ACL

DPDK's `rte_flow` API (based on the switchdev model) allows programming NIC hardware to classify and steer packets:

```c
struct rte_flow_attr attr = { .ingress = 1 };
struct rte_flow_item pattern[] = {
    { RTE_FLOW_ITEM_TYPE_ETH, &eth_spec },
    { RTE_FLOW_ITEM_TYPE_IPV4, &ipv4_spec },
    { RTE_FLOW_ITEM_TYPE_TCP, &tcp_spec },
    { RTE_FLOW_ITEM_TYPE_END }
};
struct rte_flow_action actions[] = {
    { .type = RTE_FLOW_ACTION_TYPE_QUEUE, .conf = &queue_config },
    { .type = RTE_FLOW_ACTION_TYPE_END }
};
struct rte_flow *flow = rte_flow_create(port_id, &attr, pattern, actions, &error);
```

This programs the NIC's embedded switch/flow director to steer matching packets to a specific RX queue — enabling RSS-like distribution but with arbitrary match criteria. The ACL (Access Control List) library provides software classification for patterns that don't fit in hardware.

## XDP (eXpress Data Path)

### Hook Point

XDP attaches an eBPF program to the **earliest possible point** in the receive path — directly on the NIC driver's RX ring processing, before the kernel allocates an `sk_buff`:

```
NIC → [DMA to memory] → XDP program → XDP_PASS → skb_alloc → netif_receive_skb → ... → socket
                            ↓
                       XDP_DROP (free, no alloc)
                       XDP_TX   (bounce back out same interface)
                       XDP_REDIRECT (forward to another iface/CPUMAP)
                       XDP_ABORTED (drop + trace)
```

### XDP vs. DPDK

| Feature | XDP | DPDK |
---------|-----|------|
 **Hook point** | Kernel (driver-level) | User space (bypasses kernel) |
 **Memory** | Page-per-frame (kernel allocator) | Pre-allocated mbuf pool (hugepages) |
 **Packet modification** | Limited (no allocation in XDP) | Full |
 **NIC compatibility** | Native: few drivers; Generic: slower fallback | Requires DPDK PMD drivers |
 **CPU overhead** | Very low (no syscall, no skb) | Very low (polling) |
 **Deployment** | Loads with `ip link set dev eth0 xdp obj prog.o` | Custom application, dedicated cores |
 **Best for** | DDoS mitigation, firewall, L3/L4 LB | NFV, software routers, DPI |

XDP's key advantage is **deployment ease** — it works within the existing kernel networking model, doesn't require dedicated CPU cores or special memory setup, and can coexist with normal kernel networking.

### AF_XDP

AF_XDP (`socket(AF_XDP, SOCK_RAW)`) provides an XDP-to-user-space fast path. The user-space program allocates a UMEM (user memory region) and sets up four rings (fill, RX, TX, completion) for zero-copy packet exchange:

```
┌─────────────────────────────────────────┐
│                 UMEM                     │
│  [frame0][frame1][frame2]...[frameN]     │
└─────────────────────────────────────────┘
   ↑ fill ring     ↓ rx ring
   (app→kernel)   (kernel→app)
   ↑ tx ring      ↓ completion ring
   (app→kernel)   (kernel→app)
```

AF_XDP gives near-DPDK performance with standard kernel tooling. It is the basis for high-performance load balancers and firewalls in cloud environments.

## eBPF Networking Advanced

Beyond basic packet filtering (see [../ebpf-networking.md](../ebpf-networking.md)), eBPF enables advanced network functions:

### TC-BPF (Traffic Control)

BPF programs can attach to the `clsact` qdisc at the ingress or egress of any network interface. Unlike XDP (ingress-only, pre-alloc), TC-BPF can:
- Modify packets in both directions
- Access socket metadata (via `bpf_sk_assign`)
- Steer packets to specific sockets (sk_lookup program)
- Implement NAT, tunneling, and policy routing

### Cilium: eBPF-Based Networking

Cilium (used at Google, AWS, DigitalOcean) replaces kube-proxy's iptables with eBPF programs for Kubernetes networking:

- **Service load balancing**: TC-BPF on the node's network interface performs DNAT in the data plane, bypassing iptables' O(n) rule traversal. For a service with 100 backends, iptables evaluates 100 rules per packet; Cilium's BPF uses a BPF map lookup (O(1)).
- **Network policies**: XDP and TC-BPF enforce L3/L4/L7 policies at line rate.
- **Transparent encryption**: WireGuard via BPF, encrypting pod-to-pod traffic without sidecars.
- **Observability**: BPF tracepoints record packet drops, latency, and flow metadata.

## SR-IOV (Single Root I/O Virtualization)

SR-IOV allows a **single physical PCIe function** to present multiple **virtual functions (VFs)** to the OS or hypervisor, each with its own MAC address and DMA queues:

```
Physical Function (PF):  Full-featured NIC, managed by admin
├── VF 0: Lightweight NIC, assigned to VM 0
├── VF 1: Lightweight NIC, assigned to VM 1
├── VF 2: Lightweight NIC, assigned to VM 2
└── VF 3: Lightweight NIC, assigned to VM 3
```

Each VF appears as a separate PCIe device but shares the physical NIC's hardware. The PF (Physical Function) manages the VFs — enabling, disabling, configuring MAC addresses, VLAN stripping, etc. Key benefits:

- **Near bare-metal performance**: VF traffic goes directly to/from the VM via DMA, bypassing the hypervisor. No virtual switch overhead.
- **No software switch needed**: The physical switch on the NIC handles VF-to-VF traffic internally.
- **Isolation**: VFs cannot access each other's queues or the PF's configuration.

In Kubernetes with SR-IOV, the **SR-IOV CNI** plugin allocates VFs to pods, giving them direct NIC access for high-performance workloads (RDMA, DPDK).

> **Interview Angle**: "SR-IOV vs. virtio-net for VM networking?" — SR-IOV gives ~3–5× higher throughput and lower latency (bypasses hypervisor). But SR-IOV VFs are harder to live-migrate (need hardware support), harder to manage (limited VF count per NIC, fixed at boot), and lack the flexibility of virtio (which supports any feature via software). Cloud providers use a mix: SR-IOV for high-performance VMs, virtio for general purpose.
