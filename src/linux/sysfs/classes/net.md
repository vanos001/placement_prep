# /sys/class/net

| Field | Value |
|---|---|
| Subsystem | Networking core; net/core/net-sysfs.c (net_class, net_class_attrs[]) |
| Config gate | CONFIG_NET; net-sysfs.o is obj-y in net/core/Makefile |
| ABI documentation | Documentation/ABI/testing/sysfs-class-net (31 What: entries) + sysfs-class-net-queues (14) + sysfs-class-net-statistics (24) |
| Since | KernelVersion 2.6.12 (type, tx_queue_len, April 2005) through 5.12 (threaded, January 2021) |
| Live (5.10.134 host) | 3 interfaces: eth0, lo, dummy0; eth0 operstate=up mtu=1450 speed=-1 ifindex=3; lo speed read fails with EINVAL |
| Ledger ID | SYSC-net |

## What it represents

One directory per network interface (struct net_device), regardless of driver
or kind: physical NICs, loopback, dummies, bridges, tunnels. The base files
expose identity (address, broadcast, addr_len, ifindex, iflink, type,
dev_id, dev_port), RFC 2863 state (operstate, carrier, dormant, duplex,
speed, link_mode), tunables (mtu, tx_queue_len, netdev_group, ifalias) and
link-event counters. The name is the interface name, so entries appear and
disappear as links are created and renamed; uevent carries INTERFACE and
IFINDEX.

## Relationship to the device model

Interface devices live under their driver parent (live: eth0/device ->
virtio1) with class = &net_class; net_class_attrs[] from net-sysfs.c is
attached as dev_groups so every interface gets the same base set. Two
subdirectories are populated per feature: queues/ holds one rx-N and one
tx-N kobject per RX/TX queue (rx: rps_cpus, rps_flow_cnt; tx: xps_cpus,
xps_rxqs, tx_timeout, tx_maxrate, byte_queue_limits/), and statistics/
holds the 24 rtnl_link_stats64 counters. A wireless/ subtree appears only on
wireless drivers and phydev is a symlink when a PHY is attached.

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| ifindex, iflink | RO | interface numbers | ABI, 2.6.12 era |
| type | RO | ARP protocol type, e.g. 1 for Ethernet (ARPHRD_ETHER) | ABI, 2.6.12; include/uapi/linux/if_arp.h |
| address, broadcast | RW | MAC, colon separated; live eth0 addr_len 6 | ABI; address RW per net-sysfs.c |
| mtu | RW | bytes; live eth0 = 1450 (overlay-style veth/underlay MTU) | ABI, 2.6.12 |
| operstate | RO | unknown/notpresent/down/lowerlayerdown/testing/dormant/up; live eth0 = up | ABI, 2.6.17 |
| carrier, dormant, testing | RO | 0 or 1 | ABI |
| speed | RO | Mbit/s; live eth0 = -1 (SPEED_UNKNOWN); reading lo returns EINVAL | ABI, 2.6.33: only valid with ethtool get_link_ksettings |
| duplex | RO | half, full, unknown | ABI |
| tx_queue_len | RW | packets; default 1000 for Ethernet | ABI, 2.6.12 |
| ifalias | RW | free-form interface alias string | ABI |
| netdev_group | RW | netdev cgroup group id | ABI |
| flags | RO | device flags as hex | ABI |
| carrier_changes / carrier_up_count / carrier_down_count | RO | u32 event counters | ABI, 3.15 / 4.16 |
| name_assign_type, addr_assign_type | RO | how name/address was chosen | ABI |
| gro_flush_timeout, napi_defer_hard_irqs | RW | deferral tuning, live on eth0 but not in the ABI file | net-sysfs.c net_class_attrs[]; live check (5.10.134) |
| proto_down | RW | protocol-initiated down state, live on eth0, not in the ABI file | net-sysfs.c; live check (5.10.134) |
| threaded | RW | NAPI threading switch; added 5.12, absent on this 5.10 host | ABI, January 2021 |
| queues/rx-0/rps_cpus, queues/tx-0/xps_cpus | RW | CPU masks; live single rx-0/tx-0 | ABI sysfs-class-net-queues |
| queues/tx-0/traffic_class | RO | present live, not in the ABI file | live check (5.10.134) |
| statistics/rx_bytes, tx_packets, ... (24 files) | RO | u64 counters matching rtnl_link_stats64 names | ABI sysfs-class-net-statistics |

## Safety and writes

Reads are safe. Writes change live behavior for all traffic: mtu (live 1450
on eth0 shows a non-default value set by the host network stack), address,
ifalias, tx_queue_len, netdev_group, the RPS/XPS CPU masks and the NAPI
deferral knobs. speed and duplex are read-only reports of the ethtool link
settings; on interfaces without that method (lo) the read returns EINVAL
rather than 0, which is a quirk worth knowing in scripts. Counters reset on
driver reload, and 32-bit counters can wrap.

## References

- Documentation/ABI/testing/sysfs-class-net, -queues, -statistics (cached at source-cache/linux-sparse)
- net/core/net-sysfs.c, fetched from raw.githubusercontent.com/torvalds/linux/master
- Live enumeration /sys/class/net/eth0 (+ queues/, statistics/), lo, dummy0 (read-only, kernel 5.10.134)
- Sibling pages: [tty](./tty.md), [devlink](./devlink.md); coverage: [ledger](../ledger.md)
