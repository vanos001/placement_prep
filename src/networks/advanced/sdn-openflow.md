# SDN and OpenFlow Deep Dive — Separating Control from Data Plane

## Overview

Software-Defined Networking (SDN) decouples the **control plane** (routing
decisions, policy) from the **data plane** (packet forwarding). In a
traditional switch, both live on the same box — the ASIC forwards packets
while a control CPU runs OSPF/BGP/STP. In SDN, the control plane moves to
a central **controller** that programs the data plane over a standardized
protocol — most commonly **OpenFlow**.

This chapter covers the architecture at interview depth: control/data
plane separation, the OpenFlow switch model (flow tables, match fields,
actions, counters), controllers (RYU/ONOS/OpenDaylight), the
FlowMod/PacketIn lifecycle, northbound/southbound APIs, traditional-vs-SDN
comparisons, and the P4 evolution. The companion page
[`../wireless/sdn.md`](../wireless/sdn.md) is a quicker survey; this one
goes deeper.

## Why Decouple Control From Data?

In a traditional network, each switch makes its own decisions. Adding a
feature (new encapsulation, new policy, new monitoring) means firmware
updates on every box. SDN's bet: if a central controller programs all
switches, you can update logic in one place, automate policies, and reason
about the network as a whole.

```
   +----------------------------------------------+
   |         Application Plane                    |
   |  (SDN apps: LB, firewall, monitoring, TE)    |
   +----------------------+-----------------------+
                          ^ Northbound API (REST, gRPC)
   +----------------------v-----------------------+
   |            SDN Controller                   |
   |   (Network state, topology, flow logic)    |
   +-------+---------------+---------------+----+
           | OpenFlow      | OpenFlow    | OpenFlow  (Southbound)
   +-------v---+    +------v---+    +----v------+
   | Switch 1  |    | Switch 2 |    | Switch 3  |
   |  (data)   |    |  (data)  |    |  (data)   |
   +-----------+    +----------+    +-----------+
```

## The OpenFlow Switch (Spec 1.5, ONF TS-024)

OpenFlow defines the wire protocol between controller and switch, and the
switch's forwarding model. A switch has one or more **flow tables**, each
containing **flow entries**. Each entry is a 6-tuple:

| Field | Purpose |
|-------|---------|
| **Match** | Header fields to match (12-tuple in OF 1.0, 40+ in OF 1.3+, full P4-style in OF 1.5) |
| **Priority** | 16-bit; higher wins among matching entries |
| **Counters** | Per-flow packet/byte counters, durations |
| **Instructions** | What to do: apply-actions, write-actions, goto-table, meter, group |
| **Timeouts** | Idle (no traffic) and hard (absolute) expiry in seconds |
| **Cookie** | Opaque 64-bit value the controller uses to identify related flows |

### Match Fields (OF 1.5)

OpenFlow's match starts with the Ingress port, then walks the L2/L3/L4
headers: Ethernet (src/dst MAC, Ethertype, VLAN ID, VLAN PCP), MPLS
(label, TC), ARP (src/dst IP/opcode), IPv4/IPv6 (src/dst, DSCP, ECN,
proto, frag), ICMP, TCP/UDP (src/dst port), SCTP, GRE. OF 1.5 adds
tunable match against tunnel metadata (VXLAN VNI, Geneve options).

### Actions

| Action | Effect |
|--------|--------|
| `OUTPUT:port` | Send packet out a port |
| `GROUP:id` | Apply a group (used for ECMP, multicast, failover) |
| `SET_FIELD` | Modify a header field (rewrite VLAN, decrement TTL, set IP DSCP) |
| `PUSH_VLAN` / `POP_VLAN` | Push/pop a 802.1Q tag |
| `PUSH_MPLS` / `POP_MPLS` | Push/pop an MPLS label |
| `OUTPUT:CONTROLLER` | Send packet to controller (triggers PacketIn) |
| `DROP` | (implicit; no match -> no action) |

### Pipeline

A packet ingresses table 0, matches the highest-priority entry, executes
its instructions, and may `goto-table N` where N > current table
(forward-only). Up to 255 tables in OF 1.5.

## The Controller <-> Switch Lifecycle

OpenFlow defines three classes of messages from the controller, three
from the switch:

```
   Controller                              Switch
   ----------                              ------
   Features Request  ------------------->  reply: ports, tables, capabilities
   FlowMod (ADD/MOD/DEL) ---------------->  install/modify/delete flow
   PacketOut (with buffer_id) ---------->  inject packet on a port
   MultipartRequest (stats)  ------------>  reply: counters, flow stats, table stats
   RoleRequest (MASTER/SLAVE/EQUAL) ---->  for HA controller clusters
   GroupMod / MeterMod  ----------------->  modify group/meter tables

   <-------------------------- PacketIn:   unmatched packet, sent up (table-miss)
   <-------------------------- FlowRemoved: flow expired (idle/hard timeout)
   <-------------------------- PortStatus:  link up/down, port added/removed
   <-------------------------- PacketIn:    "packet with action=CONTROLLER"
```

### The Reactive Pattern

The most common SDN idiom: the switch has a single "table-miss" entry
pointing to `OUTPUT:CONTROLLER`. Any packet that does not match a
more-specific flow is sent up; the controller inspects it (often the
first packet of a flow), computes the path, and installs the necessary
flow entries on all switches along the path. Subsequent packets hit the
installed flow and never reach the controller.

```python
# RYU controller -- handle first packet of a TCP flow
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.controller import app_manager
from ryu.lib import packet

class L2Switch(app_manager.RyuApp):
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # Build a flow: dst_mac=X -> OUTPUT:port=N
        match = ofp_parser.OFPMatch(eth_dst=msg.match.get('eth_src'))
        actions = [ofp_parser.OFPActionOutput(msg.match.get('in_port'))]
        # Install on the switch
        self._add_flow(datapath, priority=1, match=match, actions=actions)

        # Send the buffered packet back out
        out = ofp_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id,
            in_port=ofp.OFPP_CONTROLLER, actions=actions)
        datapath.send_msg(out)
```

This is the **reactive** pattern. The opposite is **proactive**: the
controller pre-installs flows for known traffic classes (e.g., per
destination prefix) without waiting for a packet. Production SDN usually
combines both: proactive for known topology, reactive for unknown.

## Controllers: RYU, ONOS, OpenDaylight

| Controller | Language | Architecture | Use Case |
|------------|----------|--------------|----------|
| **RYU** | Python | Single-process, event-driven | Research, prototyping |
| **Floodlight** | Java | Single-process | Open source OpenFlow reference |
| **OpenDaylight (ODL)** | Java | OSGi modules, multi-protocol (OF, NETCONF, PCEP) | Carrier-grade, vendor-rich |
| **ONOS** | Java | Distributed (Raft/Atomix cluster), HA-first | Carrier-grade, 5G/mobile |
| **P4Runtime controllers** | any | P4Runtime + Stratum | White-box, P4-programmable |

RYU is the lightest weight, easy to learn, but single-process. ONOS is
built for HA from day one — a cluster of ONOS instances shares state via
a distributed store (originally Atomix/Raft, now ONOS's own ONOS-Cloud)
and OpenFlow switches connect to multiple controllers with role-based
election (MASTER, SLAVE, EQUAL).

### Northbound API

The northbound API exposes the controller's network view to applications.
There is no single standard (a chronic SDN weakness):

- **ODL MD-SAL** — Yang-modeled data store, RPCs and notifications
- **ONOS REST/gRPC** — `/intents`, `/devices`, `/flows`, `/hosts`
  endpoints
- **Intent-based APIs** — abstract: "connect Host A to Host B with
  bandwidth X"

### Southbound API

Below the controller, the southbound protocols talk to devices:

- **OpenFlow** (1.0 -> 1.5)
- **NETCONF/YANG** (RFC 6241/6020) for traditional switches
- **P4Runtime** — gRPC-based, programs P4-defined pipelines
- **OVSDB** (RFC 7047) — manage OVS bridges/tunnels
- **SNMP** — for legacy device stats

## SDN vs Traditional Networking

| Dimension | Traditional | SDN |
|-----------|-------------|-----|
| Control plane | Distributed on each device | Centralized in controller |
| Configuration | Per-device CLI / SNMP | Centralized API |
| Provisioning | Manual, slow | Programmatic, fast |
| Vendor lock-in | High (proprietary CLIs) | Lower (white-box + OpenFlow) |
| Failure domain | Per-device | Controller cluster (HA required) |
| Path computation | Per-protocol (BGP, OSPF) | Centralized, arbitrary policy |
| Innovation | Vendor-driven, slow | Software-driven, fast |

The catch: SDN makes the controller a single point of failure. Production
designs use HA controller clusters with consensus (Raft/Paxos) and
switch-side fallback (fail-secure mode = keep last known flows;
fail-secure vs fail-standalone is a configuration choice).

## P4: Protocol-Independent Programmable Pipeline

OpenFlow's match/action set is fixed by the spec — to add a new header
you wait years for the ONF to ratify OF 1.6. **P4** (Programming
Protocol-Independent Packet Processors, P4-16 spec) flips this: you
write a *program* that defines the parser, the match-action pipeline, and
the deparser, and the compiler targets the underlying hardware (BMv2
software model, Tofino ASIC, Netronome SmartNIC, DPDK target).

```p4
// Match a custom "Kreutz" header (GTP-like) and rewrite
header kreutz_t {
    bit<8>  version;
    bit<16> session_id;
    bit<32> sequence;
}

parser parse_kreutz(packet_in pkt, out headers hdr) {
    state kreutz {
        pkt.extract(hdr.kreutz);
        transition accept;
    }
}

control ingress(inout headers hdr, inout metadata m,
                inout standard_metadata_t sm) {
    action forward(in bit<9> port) { sm.egress_spec = port; }
    action set_seq(in bit<32> s)  { hdr.kreutz.sequence = s; }

    table kreutz_forward {
        key = { hdr.kreutz.session_id : exact; }
        actions = { forward; set_seq; }
        default_action = forward(0);
    }
    apply { kreutz_forward.apply(); }
}
```

A P4 target compiled with this program exposes its tables via
**P4Runtime** — a gRPC protocol with auto-generated messages from the P4
program. The controller speaks the same OpenFlow-style abstraction, but
the match/action *schema* is per-program. The same controller (ONOS,
Stratum, OpenDaylight with the P4 plugin) can drive both OpenFlow and
P4Runtime targets.

The Kreutz et al. 2014 paper "Software-Defined Networking: A
Comprehensive Survey" frames the continuum: OpenFlow =
protocol-dependent but field-programmable; P4 = protocol-independent.
P4 was a natural evolution of OpenFlow, both standardized by the ONF.

## Interview Pitfalls

- **"SDN eliminates hardware."** It does not. The data plane still needs
  switches — just switches whose forwarding table is programmable. The
  ASIC still exists; what changes is who programs it.
- **Confusing SDN (an architecture) with OpenFlow (a protocol).**
  OpenFlow is one of several southbound protocols; SDN is the
  decoupled-control architecture.
- **Confusing SDN with NFV (Network Functions Virtualization).** SDN
  separates control/data plane; NFV replaces hardware middleboxes
  (firewall, LB) with VMs/containers. They are complementary.
- **Forgetting the controller is a SPOF.** A controller cluster with
  consensus is mandatory for production; switch-side fail-secure mode
  defines what happens when the cluster is unreachable.

## References

- OpenFlow Switch Specification 1.5.1 (ONF TS-024):
  <https://opennetworking.org/wp-content/uploads/2014/10/openflow-spec-v1.5.1.pdf>
- ONOS Documentation: <https://docs.onosproject.org>
- OpenDaylight Documentation: <https://docs.opendaylight.org>
- P4-16 Language Specification: <https://p4.org/p4-spec/docs/P4-16-spec.html>
- P4Runtime Specification: <https://p4.org/p4runtime>
- RYU Controller: <https://ryu.readthedocs.io>
- Stratum (P4 white-box switch OS): <https://stratumproject.org>
- Diego Kreutz, Fernando M. V. Ramos, Paulo E. Verissimo, et al.,
  "Software-Defined Networking: A Comprehensive Survey,"
  *Proc. IEEE* 103(1):14-76, 2015.
  <https://doi.org/10.1109/JPROC.2014.2371999>
