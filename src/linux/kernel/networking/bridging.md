# Linux Bridge

## Introduction

A Linux bridge is a software switch that forwards Ethernet frames between connected network interfaces based on MAC addresses. It operates at Layer 2 (Data Link) of the OSI model, learning which MAC addresses are behind each port and forwarding frames only to the appropriate destination port — just like a physical Ethernet switch.

Linux bridging is fundamental to modern virtualization and containerization. KVM/QEMU virtual machines connect to the host network through bridges. Docker and Kubernetes use bridges (docker0, cbr0) for container networking. Linux bridges also support STP (Spanning Tree Protocol), VLAN filtering, and various offload capabilities, making them suitable for production use.

## Bridge Architecture

```mermaid
graph TD
    subgraph "Linux Bridge"
        B[br0 - Software Switch]
    end
    subgraph "Connected Ports"
        E0[eth0 - Physical NIC]
        E1[eth1 - Physical NIC]
        V0[vnet0 - VM Interface]
        V1[vnet1 - VM Interface]
        T[tap0 - TAP Device]
    end
    
    E0 --> B
    E1 --> B
    V0 --> B
    V1 --> B
    T --> B
    B --> NET[Network / Internet]
```

## Creating and Managing Bridges

### Using iproute2 (Preferred)

```bash
# Create a bridge
ip link add name br0 type bridge

# Set bridge parameters
ip link set br0 type bridge ageing_time 30000
ip link set br0 type bridge stp_state 1
ip link set br0 type bridge vlan_filtering 1

# Add interfaces to the bridge
ip link set eth0 master br0
ip link set eth1 master br0
ip link set tap0 master br0

# Assign IP address to the bridge
ip addr add 192.168.1.100/24 dev br0

# Bring everything up
ip link set eth0 up
ip link set eth1 up
ip link set br0 up

# Remove interface from bridge
ip link set eth0 nomaster

# Delete bridge
ip link del br0
```

### Using bridge Command

The `bridge` utility (part of iproute2) provides bridge-specific management:

```bash
# Show bridge details
bridge link show
# 3: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 master br0 state forwarding priority 32 cost 100
# 4: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 master br0 state forwarding priority 32 cost 100
# 5: tap0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 master br0 state forwarding priority 32 cost 100

# Show FDB (forwarding database / MAC table)
bridge fdb show
# 00:11:22:33:44:55 dev eth0 master br0
# 66:77:88:99:aa:bb dev eth1 master br0
# ff:ff:ff:ff:ff:ff dev eth0 master br0 permanent

# Add static FDB entry
bridge fdb add de:ad:be:ef:00:01 dev eth0 master br0

# Delete FDB entry
bridge fdb del de:ad:be:ef:00:01 dev eth0 master br0

# Show MAC table count
bridge fdb show | wc -l

# Show bridge VLAN info
bridge vlan show
# port    vlan ids
# eth0     1 PVID Egress Untagged
# eth1     1 PVID Egress Untagged
# tap0     1 PVID Egress Untagged

# Add VLAN to port
bridge vlan add dev eth0 vid 100
bridge vlan add dev eth0 vid 100 pvid untagged

# Remove VLAN from port
bridge vlan del dev eth0 vid 100
```

### Using brctl (Legacy)

The `brctl` command is the legacy bridge management tool. It still works but is deprecated:

```bash
# Create bridge
brctl addbr br0

# Add interfaces
brctl addif br0 eth0
brctl addif br0 eth1

# Show bridge status
brctl show
# bridge name    bridge id           STP enabled    interfaces
# br0            8000.001122334455   yes            eth0
#                                                   eth1

# Show MAC table
brctl showmacs br0
# port no    mac addr                is local?   ageing timer
#  1         00:11:22:33:44:55       yes          0.00
#  2         66:77:88:99:aa:bb       no           3.12

# Enable/disable STP
brctl stp br0 on
brctl stp br0 off

# Set bridge parameters
brctl setageing br0 30
brctl setfd br0 15

# Remove interface
brctl delif br0 eth0

# Delete bridge
brctl delbr br0
```

## STP (Spanning Tree Protocol)

STP prevents loops in networks with redundant bridges/switches. When multiple paths
exist between two points, STP blocks redundant paths to prevent broadcast storms.
The Linux bridge implements STP/RSTP in-kernel, with the protocol state machine
running as part of the bridge code (`net/bridge/stp_*`).

### How STP Works

```mermaid
graph LR
    subgraph "Before STP"
        A1[Bridge A] --- B1[Bridge B]
        A1 --- C1[Bridge C]
        B1 --- C1
        B1 --- D1[Host D]
    end
    subgraph "After STP"
        A2["Bridge A<br>Root"] --- B2[Bridge B]
        A2 --- C2[Bridge C]
        B2 -.->|Blocked| C2
        B2 --- D2[Host D]
    end
```

### STP Port States

From the [kernel bridge documentation](https://docs.kernel.org/networking/bridge.html),
each bridge port has an STP state that controls its behavior:

| State | Value | Description |
|-------|-------|-------------|
| Disabled | 0 | Port completely inactive (BPDU filter). Traffic forwarding stopped. |
| Listening | 1 | Listens for STP BPDUs, drops all other traffic. |
| Learning | 2 | Accepts traffic only for MAC address table updates. |
| Forwarding | 3 | Fully active — forwards traffic. |
| Blocking | 4 | Processes only STP BPDUs (used during election). |

### STP Bridge Netlink Attributes

The bridge exposes STP configuration through netlink attributes:

| Attribute | Description | Default |
|-----------|-------------|---------|
| `IFLA_BR_STP_STATE` | Enable/disable STP (0=off, >0=on) | 0 (disabled) |
| `IFLA_BR_PRIORITY` | Bridge STP priority (0–65535) | 32768 |
| `IFLA_BR_FORWARD_DELAY` | Time in LISTENING+LEARNING states (2–30s × USER_HZ) | 15s |
| `IFLA_BR_HELLO_TIME` | Interval between hello packets (1–10s × USER_HZ) | 2s |
| `IFLA_BR_MAX_AGE` | Hello packet timeout before assuming bridge is dead (6–40s × USER_HZ) | 20s |
| `IFLA_BR_STP_MODE` | STP mode (userspace vs kernel) | — |

### STP Configuration

```bash
# Enable STP
ip link set br0 type bridge stp_state 1

# Or via brctl
brctl stp br0 on

# Set bridge priority (lower = more likely root bridge, default 32768)
ip link set br0 type bridge priority 4096

# Set port priority (lower = preferred, default 128)
ip link set eth0 type bridge_slave priority 10
ip link set eth1 type bridge_slave priority 20

# Set path cost (lower = preferred path)
ip link set eth0 type bridge_slave cost 100
ip link set eth1 type bridge_slave cost 200

# Forward delay (time in listening/learning state, in 1/100 seconds)
ip link set br0 type bridge forward_delay 1500

# Hello time (STP BPDU interval)
ip link set br0 type bridge hello_time 200

# Max age (BPDU validity period)
ip link set br0 type bridge max_age 2000

# View STP status
bridge link show
# port states: disabled, listening, learning, forwarding, blocking

cat /sys/class/net/br0/bridge/stp_state
# 1
```

### RSTP (Rapid STP — IEEE 802.1w)

RSTP provides faster convergence than classic STP (802.1D). The Linux bridge
implements RSTP natively — when STP is enabled on modern kernels, RSTP is
used automatically. RSTP achieves sub-second convergence by:

- Using proposal/agreement handshake instead of timer-based transitions
- Introducing **alternate** and **backup** port roles for rapid failover
- Eliminating the 30-second listening→learning delay for edge ports
- Allowing ports to transition to forwarding without waiting for BPDU timeout

```bash
# RSTP is enabled by default when STP is on in modern kernels
ip link set br0 type bridge stp_state 1

# View STP protocol in use
bridge -d link show | grep -i "state"

# The bridge STP mode can be set via IFLA_BR_STP_MODE:
# 0 = use kernel STP (default, RSTP)
# 1 = use userspace STP daemon (e.g., xSTPd)
```

### STP Timers

The kernel tracks several STP timers per bridge, readable via netlink:

| Timer | Description |
|-------|-------------|
| `IFLA_BR_HELLO_TIMER` | Time until next hello BPDU is sent |
| `IFLA_BR_TCN_TIMER` | Topology Change Notification timer |
| `IFLA_BR_TOPOLOGY_CHANGE_TIMER` | Topology change detection timer |
| `IFLA_BR_GC_TIMER` | Garbage collection timer for stale entries |

Read-only status attributes include `IFLA_BR_ROOT_ID`, `IFLA_BR_BRIDGE_ID`,
`IFLA_BR_ROOT_PORT`, `IFLA_BR_ROOT_PATH_COST`, `IFLA_BR_TOPOLOGY_CHANGE`,
and `IFLA_BR_TOPOLOGY_CHANGE_DETECTED`.

## VLAN Filtering

Linux bridges support IEEE 802.1Q VLAN filtering, allowing the bridge to act as a VLAN-aware switch:

```bash
# Enable VLAN filtering
ip link set br0 type bridge vlan_filtering 1

# View current VLAN configuration
bridge vlan show
# port    vlan ids
# eth0     1 PVID Egress Untagged
# eth1     1 PVID Egress Untagged
# br0      1 PVID Egress Untagged

# Add VLAN 100 to eth0, tagged
bridge vlan add dev eth0 vid 100

# Add VLAN 100 to eth0, untagged (access port)
bridge vlan add dev eth0 vid 100 pvid untagged

# Remove default VLAN 1 from port
bridge vlan del dev eth0 vid 1

# Add multiple VLANs (trunk port)
bridge vlan add dev eth1 vid 100
bridge vlan add dev eth1 vid 200
bridge vlan add dev eth1 vid 300

# Show VLAN details
bridge -d vlan show
# port    vlan ids
# eth0     100 PVID Egress Untagged
# eth1     100
#          200
#          300

# Self port (bridge itself as VLAN member)
bridge vlan add dev br0 vid 100 self
```

### VLAN-Aware Bridge Example

```bash
# Create VLAN-aware bridge
ip link add name br0 type bridge vlan_filtering 1

# eth0: trunk port carrying VLANs 100, 200
ip link set eth0 master br0
bridge vlan add dev eth0 vid 100
bridge vlan add dev eth0 vid 200
bridge vlan del dev eth0 vid 1  # remove default VLAN

# tap0 (VM): access port on VLAN 100
ip link set tap0 master br0
bridge vlan add dev tap0 vid 100 pvid untagged
bridge vlan del dev tap0 vid 1

# tap1 (VM): access port on VLAN 200
ip link set tap1 master br0
bridge vlan add dev tap1 vid 200 pvid untagged
bridge vlan del dev tap1 vid 1
```

## Bridge in Virtualization

### KVM/QEMU with Bridged Networking

```bash
# 1. Create bridge
ip link add name br0 type bridge
ip link set br0 up

# 2. Move host IP to bridge
ip addr del 192.168.1.100/24 dev eth0
ip addr add 192.168.1.100/24 dev br0
ip link set eth0 master br0
ip route add default via 192.168.1.1 dev br0

# 3. Launch VM with bridge
qemu-system-x86_64 \
    -m 2048 \
    -netdev bridge,id=net0,br=br0 \
    -device virtio-net-pci,netdev=net0 \
    disk.qcow2

# Or with tap device manually
ip tuntap add dev tap0 mode tap
ip link set tap0 master br0
ip link set tap0 up
qemu-system-x86_64 \
    -netdev tap,id=net0,ifname=tap0,script=no,downscript=no \
    -device virtio-net-pci,netdev=net0 \
    disk.qcow2
```

### Docker Bridge Networking

```bash
# Docker creates docker0 bridge by default
ip link show docker0
# docker0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500

bridge link show | grep docker
# veth1234@if5: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 master docker0 state forwarding

# Custom bridge network
docker network create --driver bridge \
    --subnet 172.20.0.0/16 \
    --gateway 172.20.0.1 \
    mybridge

# Run container on custom bridge
docker run --network mybridge --ip 172.20.0.10 -it ubuntu
```

### Libvirt Bridged Network

```xml
<!-- /etc/libvirt/qemu/networks/br0.xml -->
<network>
  <name>br0</name>
  <forward mode="bridge"/>
  <bridge name="br0"/>
</network>
```

```bash
virsh net-define br0.xml
virsh net-start br0
virsh net-autostart br0
```

## Bridge Offloading

Modern NICs support bridge offloading, where the hardware performs switching functions:

```bash
# Check if hardware offloading is available
ethtool -k eth0 | grep -i switch
# switchdev: on

# Enable bridge hardware offloading (for supported NICs)
ip link set eth0 type bridge_slave hwmode on
# or for switchdev mode
devlink dev eswitch set pci/0000:03:00.0 mode switchdev

# View offload status
bridge -d link show | grep -i offload
# eth0: <...> master br0 ... offload yes
```

## Bridge Monitoring

```bash
# Show bridge status
ip -d link show br0
# br0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ...
#     bridge forward_delay 1500 hello_time 200 max_age 2000
#     vlan_filtering 1 vlan_protocol 802.1Q

# Show MAC address table
bridge fdb show dev br0

# Count learned MACs
bridge fdb show | grep -v permanent | wc -l

# Monitor FDB changes
bridge monitor fdb

# Monitor link state changes
bridge monitor

# Bridge statistics
ip -s link show br0

# Show bridge port states
bridge -d link show
```

## Per-VLAN Spanning Tree (PVST)

```bash
# Linux bridge supports per-VLAN STP (PVST)
# With VLAN filtering enabled, STP runs per VLAN

# Set per-VLAN STP state
bridge vlan dev eth0 vid 100 state 3  # 0=disabled, 1=listening, 2=learning, 3=forwarding
```

## Bridge Internals

The Linux bridge is implemented in `net/bridge/` and uses:

- **Hash table** for FDB (MAC learning table)
- **Port state machine** for STP (listening → learning → forwarding)
- **VLAN database** per port for VLAN filtering
- **Netfilter hooks** for ebtables integration
- **Switchdev API** for hardware offloading

```bash
# View bridge internals via debugfs
ls /sys/kernel/debug/br0/
#  br0/hash_size
#  br0/group_fwd_mask

# View bridge FDB hash table details
cat /sys/class/net/br0/bridge/hash_max
# 4096
```

## References

- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Kernel Bridge Documentation](https://docs.kernel.org/networking/bridge.html)
- [Linux Foundation: Bridge](https://wiki.linuxfoundation.org/networking/bridge)
- [man-pages: bridge(8)](https://man7.org/linux/man-pages/man8/bridge.8.html)
- [IEEE 802.1D — Spanning Tree](https://standards.ieee.org/standard/802_1D-2004.html)
- [IEEE 802.1Q — VLANs](https://standards.ieee.org/standard/802_1Q-2018.html)
- [Red Hat: Configuring Network Bridging](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_managing_networking/configuring-a-network-bridge_configuring-and-managing-networking)

## Bridge Internals (Kernel Implementation)

### Data Structures

The Linux bridge is implemented in `net/bridge/` with these key structures:

```c
/* Bridge instance */
struct net_bridge {
    struct net_device   *dev;           /* Bridge netdev */
    struct list_head    port_list;      /* List of ports */
    spinlock_t          lock;
    struct net_bridge_fdb_hash *fdb_hash;  /* MAC learning table */
    unsigned long       ageing_time;    /* FDB entry timeout */
    stp_state;                          /* STP state */
    vlan_enabled;                       /* VLAN filtering */
    struct net_bridge_vlan_group *vlans; /* VLAN database */
};

/* Bridge port (attached interface) */
struct net_bridge_port {
    struct net_bridge   *br;            /* Parent bridge */
    struct net_device   *dev;           /* Port netdev */
    struct list_head    list;           /* Link in port_list */
    u8                  priority;       /* STP port priority */
    u16                 path_cost;      /* STP path cost */
    u8                  state;          /* STP port state */
    struct net_bridge_vlan_group *vlans; /* Per-port VLANs */
};
```

### FDB (Forwarding Database)

The FDB is a hash table mapping MAC addresses to ports:

```c
/* FDB entry */
struct net_bridge_fdb_entry {
    struct hlist_node   hlist;          /* Hash chain */
    struct net_bridge_port *dst;        /* Destination port */
    mac_addr;                           /* MAC address */
    unsigned long       updated;        /* Last seen timestamp */
    unsigned long       used;           /* Last used timestamp */
    u16                 vlan_id;        /* VLAN tag */
    u8                  is_local;       /* Local (bridge) entry */
    u8                  is_static;      /* Static entry */
};

/* Hash function */
static inline int br_mac_hash(const unsigned char *mac) {
    return jhash(mac, ETH_ALEN, 0) % FDB_HASH_SIZE;
}
```

### Frame Forwarding Path

```mermaid
flowchart TD
    RX[Frame received on port] --> LEARN[Source MAC learning]
    LEARN --> FDB_LOOKUP[FDB lookup: destination MAC]
    FDB_LOOKUP --> FOUND{Entry found?}
    FOUND -->|Yes| PORT{Same port?}
    PORT -->|Yes| DROP["Drop, hairpin"]
    PORT -->|No| FWD[Forward to destination port]
    FOUND -->|No| FLOOD[Flood to all ports
(except source)]
    FWD --> VLAN_CHECK{VLAN filtering
enabled?}
    FLOOD --> VLAN_CHECK
    VLAN_CHECK -->|Yes| VLAN_FWD[Check VLAN tags
and port membership]
    VLAN_CHECK -->|No| SEND[Send frame]
    VLAN_FWD --> SEND
```

## Bridge with iptables/nftables

The bridge integrates with Netfilter for packet filtering:

```bash
# Enable bridge Netfilter
modprobe br_netfilter

# Filter bridged traffic with iptables
iptables -I FORWARD -m physdev --physdev-in eth0 -j DROP

# Or with nftables
nft add chain bridge filter forward '{ type filter hook forward priority 0; }'
nft add rule bridge filter forward iifname "eth0" drop

# Enable bridge_nf_call_iptables (bridge → iptables)
echo 1 > /proc/sys/net/bridge/bridge-nf-call-iptables

# Arptables for ARP filtering on bridge
arptables -A INPUT -i eth0 -j DROP
```

## Bridge Port Isolation

Port isolation prevents communication between ports on the same bridge:

```bash
# Enable port isolation (Linux 3.18+)
ip link set eth0 type bridge_slave isolated on
ip link set eth1 type bridge_slave isolated on

# Isolated ports can still communicate with non-isolated ports
# Useful for hosting providers: VMs can't see each other
```

## Multicast Snooping

The bridge supports IGMP/MLD snooping for efficient multicast:

```bash
# Enable multicast snooping
echo 1 > /sys/class/net/br0/bridge/multicast_snooping

# Set multicast querier
echo 1 > /sys/class/net/br0/bridge/multicast_querier

# Set multicast router
echo 1 > /sys/class/net/br0/bridge/multicast_router

# View multicast group membership
bridge mdb show
# dev br0 port eth0 grp 239.1.1.1 permanent
# dev br0 port eth1 grp 239.1.1.1 temp
```

## Common Bridge Scenarios

### Transparent Bridge (Bridging Firewall)

```bash
# Bridge two interfaces transparently
ip link add name br0 type bridge
ip link set eth0 master br0
ip link set eth1 master br0
ip link set br0 up
ip link set eth0 up
ip link set eth1 up

# No IP on bridge — purely Layer 2
# Filter with ebtables or bridge nftables
```

### Bridge with Multiple VLANs

```bash
# Trunk port (eth0) carries VLANs 100, 200
# Access ports: tap0 → VLAN 100, tap1 → VLAN 200

ip link add name br0 type bridge vlan_filtering 1
ip link set eth0 master br0
ip link set tap0 master br0
ip link set tap1 master br0

bridge vlan add dev eth0 vid 100
bridge vlan add dev eth0 vid 200
bridge vlan del dev eth0 vid 1

bridge vlan add dev tap0 vid 100 pvid untagged
bridge vlan del dev tap0 vid 1

bridge vlan add dev tap1 vid 200 pvid untagged
bridge vlan del dev tap1 vid 1

ip link set br0 up
```

## Bridge Performance Tuning

### FDB Hash Table Sizing

```bash
# Default hash size: 4096 entries
# Increase for large networks
echo 65536 > /sys/class/net/br0/bridge/hash_max

# Set ageing time (seconds)
# Default: 300s (5 minutes)
echo 600 > /sys/class/net/br0/bridge/ageing_time

# View FDB statistics
cat /sys/class/net/br0/bridge/hash_max
# 4096
```

### Bridge Port Settings

```bash
# Set port priority (lower = preferred for STP)
ip link set eth0 type bridge_slave priority 10

# Set path cost (lower = preferred path)
ip link set eth0 type bridge_slave cost 100

# Enable hairpin mode (for VM-to-VM on same port)
ip link set tap0 type bridge_slave hairpin on

# Set multicast fast leave
ip link set eth0 type bridge_slave mcast_fast_leave on
```

### Monitoring Bridge Performance

```bash
# Bridge statistics
ip -s link show br0
# RX: bytes packets errors dropped overrun mcast
# TX: bytes packets errors dropped carrier collsns

# Per-port statistics
bridge -s link show
# Port 1: eth0
#   RX: 12345678 bytes, 12345 packets
#   TX: 98765432 bytes, 98765 packets

# Monitor FDB changes in real-time
bridge monitor fdb

# Count active FDB entries
bridge fdb show | grep -v permanent | wc -l
```

## Common Bridge Issues

### Broadcast Storms

Without STP, redundant bridge paths cause broadcast storms:

```bash
# Enable STP to prevent loops
ip link set br0 type bridge stp_state 1

# Or use bridge priority to control root bridge election
ip link set br0 type bridge priority 4096
```

### MTU Mismatch

```bash
# Ensure all bridge ports have same MTU
ip link set eth0 mtu 1500
ip link set eth1 mtu 1500
ip link set br0 mtu 1500

# For jumbo frames
ip link set br0 mtu 9000
ip link set eth0 mtu 9000
ip link set eth1 mtu 9000
```

### DHCP Issues with Bridging

```bash
# Ensure bridge forwards DHCP
echo 1 > /proc/sys/net/bridge/bridge-nf-call-iptables

# Or use bridge-specific ebtables
ebtables -A FORWARD -p IPv4 --ip-protocol UDP \
    --ip-destination-port 67:68 -j ACCEPT
```

## Related Topics

- [Network Bonding](./bonding.md) — Link aggregation
- [VLANs](./vlans.md) — 802.1Q VLAN interfaces
- [Network Namespaces](./namespaces.md) — Isolated network stacks
- [Traffic Control](./tc.md) — QoS on bridge ports
- [Netlink](./netlink.md) — Programmatic bridge management
- Netfilter — Packet filtering framework
- [Virtualization](../../virtualization/overview.md) — VM networking with bridges
