# /sys/class/iscsi_iface

| Field | Value |
|---|---|
| Subsystem | iSCSI transport, drivers/scsi/scsi_transport_iscsi.c (struct class iscsi_iface_class, name "iscsi_iface") |
| Config gate | CONFIG_SCSI_ISCSI_ATTRS (see iscsi_transport.md) |
| ABI documentation | none found - checked the stable/, testing/ and obsolete/ ABI listings and grep for iscsi; attributes below are named by drivers/scsi/scsi_transport_iscsi.c (iscsi_iface_attrs[]) |
| Since | not stated by the sources checked |
| Live (5.10.134 host) | class present with 0 entries |
| Ledger ID | SYSC-iscsi_iface |

## What it represents

One device per iSCSI interface object. Ifaces model the network personality an initiator session uses (address, VLAN, TCP tuning, login parameters). Devices are named ipv4-iface-<host_no>-<iface_num> or ipv6-iface-<host_no>-<iface_num> depending on iface_type (iscsi_create_iface, scsi_transport_iscsi.c).

## Relationship to the device model

Each iface device is parented by its SCSI host device (iface->dev.parent = shost_gendev). Sessions carry their iface assignment through the `ifacename` session attribute (see iscsi_session.md); iscsiadm creates and binds ifaces through netlink, sysfs exposes the resulting state.

## Attributes (representative; source: scsi_transport_iscsi.c iscsi_iface_attrs[])

| Attribute | R/W | Meaning |
|---|---|---|
| `enabled` | RO | Whether the iface is enabled (visibility depends on transport support) |
| `vlan_id`, `vlan_priority`, `vlan_enabled` | RO | VLAN configuration |
| `mtu`, `port`, `ipaddress_state`, `cache_id`, `redirect_en` | RO | Network parameters via transport get_iface_param |
| `ipv4_iface_ipaddress`, `ipv4_iface_gateway`, `ipv4_iface_subnet`, `ipv4_iface_bootproto` | RO | IPv4 settings (visible on ipv4 ifaces) |
| `ipv6_iface_ipaddress`, `ipv6_iface_link_local_addr`, `ipv6_iface_router_addr` | RO | IPv6 settings (visible on ipv6 ifaces) |
| `header_digest`, `data_digest`, `immediate_data`, `initial_r2t`, `first_burst_len`, `max_burst_len`, `erl` | RO | Login parameter defaults |
| `initiator_name`, `def_taskmgmt_tmo`, `tcp_wsf`, `tcp_timer_scale`, `tcp_timestamp_en`, `delayed_ack_en`, `tcp_nagle_disable` | RO | TCP and login tuning |

The is_visible callback filters by iface_type (ISCSI_IFACE_TYPE_IPV4 vs IPV6) and by transport get_iface_param support, so live devices expose a subset.

## Safety and writes

Attributes are read-only; iface creation, address changes and binding are netlink operations. Empty on the container host.

## References

- drivers/scsi/scsi_transport_iscsi.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [iSCSI storage page](../../storage/iscsi.md), [iscsi_session](./iscsi_session.md), [iscsi_host](./iscsi_host.md)
