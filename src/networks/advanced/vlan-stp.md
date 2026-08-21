# VLANs and Spanning Tree Protocol — 802.1Q, STP, RSTP, MSTP

## Overview

Two technologies dominate Layer 2 networking: **802.1Q** virtual LANs
(VLANs), which let one switch fabric carry multiple isolated broadcast
domains, and **802.1D** Spanning Tree Protocol (STP), which prevents the
loops that VLAN trunks would otherwise create. Their interplay, evolutions
(RSTP, MSTP), and security pitfalls are foundational Layer-2 interview
material.

## 802.1Q Frame Format

A standard Ethernet frame carries a 2-byte EtherType. With 802.1Q, a
4-byte shim is inserted after the source MAC: the Tag Protocol Identifier
(TPID = 0x8100), then a Tag Control Information (TCI) field with three
pieces:

```
   6    6   2    2    2    2         variable      4
   +----+----+----+---------+--------+-------------+----+
   |DMAC|SMAC|TPID|  TCI    | EtherT | payload     | FCS|
   +----+----+----+---------+--------+-------------+----+
                     |
                     v
              +--------------------------------+
              | PCP(3) | DEI(1) | VID(12 bits) |
              +--------------------------------+
                3 bits   1 bit    12 bits  -> 0..4095
```

- **PCP** (Priority Code Point, 3 bits): 802.1p priority (0=BE … 7=NC),
  eight QoS levels.
- **DEI** (Drop Eligible Indicator, 1 bit): formerly CFI; marks the frame
  as eligible for early drop under congestion.
- **VID** (VLAN ID, 12 bits): 0-4095. VLAN 0 is priority-tagged (no real
  VLAN), VLAN 4095 is reserved, VLAN 1 is the default, VLANs 1002-1005
  are reserved for legacy FDDI/Token Ring.

This 4094-VID limit is the central scaling pressure that drives VXLAN
(24-bit VNID = 16M).

## Trunk, Access, and Native VLAN

A switch port operates in one of three modes:

| Mode | Egress | Ingress |
|------|--------|---------|
| **Access** | Untagged, in the access VLAN | Untagged -> access VLAN |
| **Trunk** (802.1Q) | Tagged, in the VLAN of the frame | Tagged -> use the tag |
| **Hybrid** | Per-VLAN tagged or untagged | Mixed |

```
   PC ---(access VLAN 10)---- SW1 ---(trunk: VLANs 10,20,30, native=99)---- SW2 ---(access VLAN 10)---- PC
```

**Native VLAN**: on a trunk, frames in the native VLAN are sent *untagged*.
The default is VLAN 1 but every production network changes this to a
deliberately unused VLAN (e.g. 999). Why? Untagged traffic on a trunk is
implicitly placed in the native VLAN — if your trunk's native VLAN is 1,
any packet leaking from one side lands in VLAN 1, the management VLAN.

```
   ! Cisco IOS
   interface GigabitEthernet0/1
     switchport mode trunk
     switchport trunk allowed vlan 10,20,30
     switchport trunk native vlan 999        ! never use VLAN 1
   !
   interface GigabitEthernet0/2
     switchport mode access
     switchport access vlan 10
     spanning-tree portfast                  ! access-port optimization
```

## Spanning Tree Protocol (802.1D-1998)

A switching loop is a broadcast storm: any broadcast frame circulates
forever, doubling at each cycle. STP builds a loop-free tree by electing
a single root bridge and selecting, on every segment, exactly one port
that forwards toward the root. All other ports block.

### Bridge Protocol Data Unit (BPDU)

STP switches speak using Configuration BPDUs (multicast
01:80:C2:00:00:00, LLC SNAP). Key fields:

```
   Protocol Identifier:           0x0000
   Protocol Version:              0x00 (STP), 0x02 (RSTP), 0x03 (MSTP)
   BPDU Type:                     0x00 (Config), 0x80 (RST), 0x02 (TCN)
   Flags:                         TC | TCA | Agreement | Forwarding |
                                  Learning | PortRole(2) | Proposal
   Root Identifier:               8 bytes -- priority(4 bits) + sys-id-ext(12)
                                            + MAC(48 bits)
   Root Path Cost:                4 bytes -- cumulative cost from this
                                            bridge to root
   Bridge Identifier:             8 bytes -- same encoding as Root ID
   Port Identifier:              2 bytes -- priority(4) + port number(8)
   Message Age:                  2 bytes -- seconds since root
   Max Age:                      2 seconds -- when to discard (default 20)
   Hello Time:                   2 seconds -- BPDU periodic (default 2)
   Forward Delay:                2 seconds -- Listening->Learning,
                                            Learning->Forwarding
                                            (default 15)
```

### Root Bridge Election

1. Every bridge starts by advertising itself as root (Root ID = own
   Bridge ID).
2. The lowest Bridge ID wins. Bridge ID =
   `priority.sysid_ext.MAC` compared as a 64-bit unsigned integer; with
   default priority 32768, MAC becomes the tiebreaker.
3. Once a bridge hears a superior Root ID, it stops advertising itself
   and relays the superior BPDU (adding its path cost).

The administrator biases election by lowering priority on the intended
root: `spanning-tree vlan 10 priority 4096`. The sysid-ext field allows
per-VLAN STP (PVST+) on Cisco gear — same priority but a different sysid
per VLAN.

### Port Roles and States

Once the root is elected:

- **Root Port**: on every non-root bridge, the port with lowest Root
  Path Cost.
- **Designated Port**: on every segment, the port with the lowest Root
  Path Cost (root bridge's ports are all designated).
- **Blocking Port**: the other port on a segment with two
  non-designated ends.

| State | Receives BPDUs? | Learns MACs? | Forwards data? | Duration |
|-------|------------------|--------------|------------------|----------|
| **Blocking** | Yes | No | No | Up to Max Age (20s) |
| **Listening** | Yes | No | No | Forward Delay (15s) |
| **Learning** | Yes | Yes | No | Forward Delay (15s) |
| **Forwarding** | Yes | Yes | Yes | Steady-state |
| **Disabled** | No | No | No | Administratively down |

A typical STP convergence from a topology change: 20 (max-age) + 15
(listening) + 15 (learning) = **50 seconds**. This is the painful
802.1D-1998 convergence that motivated RSTP.

## RSTP (802.1w-2001)

Rapid Spanning Tree Protocol collapses four blocking-derived states into
three: **Discarding** (= Blocking + Listening), **Learning**,
**Forwarding**. More importantly, RSTP adds:

- **Alternate Port** — a backup for the root port (immediately promoted
  if root fails)
- **Backup Port** — a backup for a designated port on the same segment
- **Proposal/Agreement** handshake — fast transition to forwarding on
  point-to-point links
- BPDUs sent every Hello (no longer relies on the root relaying) — a
  switch considers its neighbor gone after 3 missed BPDUs (3 * Hello =
  ~6s, vs 20s MaxAge)
- Edge ports (`portfast`) skip listening/learning

```
                     +----- Root Bridge -----+
                     |                       |
                  RP |                    RP  |
              +------v---+             +-----v---+
              |Bridge A  |             |Bridge B |
              +--+-------+             +---------+
                 | AP (alternate)              ^
                 +-------- link ---------------+
                                 DP
            (B's port becomes Designated; A's port is Alternate, blocks)
```

RSTP convergence on a link failure: typically sub-second. The handshake:
Bridge A sends a Proposal flag on a newly-up port; the downstream Bridge
B replies with an Agreement flag; A transitions to Forwarding
immediately. RSTP is backward-compatible — STP BPDUs are interpreted and
RSTP ports fall back to 802.1D behavior.

## MSTP (802.1s-2002 / 802.1Q-2018)

Multiple Spanning Tree Protocol runs *one* instance of RSTP per VLAN
*group* rather than one per VLAN (PVST+) or one for all VLANs (CST). A
network with 1000 VLANs does not need 1000 STP trees — it needs as many
trees as there are topologically distinct paths.

MSTP introduces **MST Regions**: groups of switches with identical
VLAN-to-instance mappings. Inside a region, the protocol computes an MST
instance per group; between regions, the CIST (Common and Internal
Spanning Tree) is one big RSTP.

```
   Region 1                              Region 2
   +---------------------------+         +---------------------------+
   |  IST0 (instance 0)        |  CIST   | IST0                      |
   |  MSTI 1 (VLANs 10-50)     | ------> | MSTI 1 (VLANs 10-50)      |
   |  MSTI 2 (VLANs 60-99)     |         | MSTI 2 (VLANs 60-99)      |
   +---------------------------+         +---------------------------+
```

The MST Configuration Digest (a hash of the VLAN-to-instance table,
RFC-defined) ensures two switches that *claim* to be in the same region
actually agree on the mappings.

```
   ! Cisco IOS MST config
   spanning-tree mode mst
   spanning-tree mst configuration
     name REGION1
     revision 1
     instance 1 vlan 10-50
     instance 2 vlan 60-99
```

## The VLAN Hopping Attack

VLANs are a security boundary only if the trunk configuration is
correct. Two classic attacks:

### 1. Switch Spoofing (DTP attack)

If a trunk port negotiates via Dynamic Trunking Protocol (DTP), an
attacker sends DTP "desirable" frames and the port transitions to trunk
mode. The attacker now receives traffic for all VLANs on the trunk.

**Mitigation**: configure trunk ports as `switchport nonegotiate` and
`switchport mode trunk` (not `dynamic desirable`); configure access
ports as `switchport mode access` and `switchport nonegotiate`.

### 2. Double-Tagging (802.1Q double-encapsulation)

If the native VLAN is the access VLAN of an attacker (say VLAN 1, the
default), the attacker sends:

```
   Outer tag: VLAN 1 (the native VLAN -- stripped at ingress)
   Inner tag: VLAN 10 (the target -- survives the inner egress)
   Payload:  Ethernet frame destined for victim on VLAN 10
```

The ingress access port tags the frame with VLAN 1 (the attacker's
access VLAN). On egress across the trunk, the *outer* VLAN-1 tag is
stripped because VLAN 1 is native (untagged). The remaining inner
VLAN-10 tag is then processed by the receiving switch as if it were a
legitimate VLAN-10 frame.

This attack is **one-way** (the attacker can send into VLAN 10 but
cannot receive replies) and only works when the native VLAN of the
trunk matches the attacker's access VLAN.

**Mitigation**: never use the default VLAN as the native VLAN; tag the
native VLAN explicitly (`vlan dot1q tag native` on Cisco).

## Comparison to VXLAN

VXLAN (RFC 7348) is the datacenter-scale answer to the 4094-VLAN ceiling.
It encapsulates a Layer-2 frame inside UDP/IP with a 24-bit VNID, giving
16M isolated segments. Where 802.1Q tags sit in the Ethernet header,
VXLAN adds a 50-byte shim:

```
   Outer UDP/IP (28 bytes) | Outer Eth (14) | VXLAN shim (8) | Inner Eth | Inner Payload
                            +------ 50 bytes of overhead -----+
```

| Dimension | 802.1Q | VXLAN |
|-----------|--------|-------|
| Segment ID | 12-bit VID (4K) | 24-bit VNID (16M) |
| Header cost | 4 bytes | 50 bytes |
| Transport | L2 switches | IP underlay (UDP 4789) |
| Loop prevention | STP/RSTP | None native (relies on IP routing) |
| Multicast | Not used | Underlay MC for BUM flooding (or EVPN HER) |
| STP exposure | Full (every L2 loop) | None (IP underlay has no STP) |
| Used in | Campus, access | Datacenter leaf-spine with EVPN |

Modern datacenters use VXLAN with EVPN (RFC 8365, RFC 9161) to replace
STP flooding with MP-BGP control-plane learning — the IP underlay's
routing protocol (OSPF/BGP) replaces spanning tree.

## Interview Pitfalls

- **"VLANs are security boundaries."** They are not by default; the two
  hopping attacks above defeat naive configurations.
- **Forgetting the native VLAN is untagged.** That single fact drives
  both the double-tag attack and most misconfigurations on trunks.
- **Confusing STP port states with RSTP.** RSTP merged Blocking +
  Listening into Discarding; calling it "Blocking" is technically
  wrong in RSTP.
- **Saying "STP converges in 50 seconds, RSTP in 1 second."** RSTP's
  actual numbers depend on topology; sub-second convergence requires
  point-to-point links and the proposal/agreement handshake.
- **Missing MSTP regions.** Two switches claiming to be in the same
  MST region but with different VLAN-to-instance tables are silently
  treated as separate regions, leading to CIST-only load balancing that
  defeats the design.

## References

- IEEE 802.1Q-2018 (Bridges and Bridged Networks):
  <https://standards.ieee.org/standard/802_1Q-2018.html>
- IEEE 802.1D-2004 (STP, superseded):
  <https://standards.ieee.org/standard/802_1D-2004.html>
- IEEE 802.1w (RSTP, merged into 802.1Q-2018):
  <https://en.wikipedia.org/wiki/Rapid_Spanning_Tree_Protocol>
- IEEE 802.1s (MSTP, merged into 802.1Q-2018):
  <https://en.wikipedia.org/wiki/Multiple_Spanning_Tree_Protocol>
- RFC 7348 — VXLAN: <https://www.rfc-editor.org/rfc/rfc7348>
- RFC 8365 — EVPN-VXLAN Network Reference Model:
  <https://www.rfc-editor.org/rfc/rfc8365>
- Cisco Spanning Tree Configuration Guide:
  <https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24062-146.html>
