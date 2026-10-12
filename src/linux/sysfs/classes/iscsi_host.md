# /sys/class/iscsi_host

| Field | Value |
|---|---|
| Subsystem | iSCSI transport, drivers/scsi/scsi_transport_iscsi.c (transport class iscsi_host_class via DECLARE_TRANSPORT_CLASS, name "iscsi_host") |
| Config gate | CONFIG_SCSI_ISCSI_ATTRS (see iscsi_transport.md) |
| ABI documentation | none found - checked the stable/, testing/ and obsolete/ ABI listings and grep for iscsi; attributes below are named by drivers/scsi/scsi_transport_iscsi.c (iscsi_host_attrs[]) |
| Since | not stated by the sources checked |
| Live (5.10.134 host) | class present with 0 entries |
| Ledger ID | SYSC-iscsi_host |

## What it represents

One device per iSCSI-enabled SCSI host. iscsi_setup_host() runs when a transport host comes up and, if the transport supports it, creates a bsg request queue named iscsi_host<N> (see bsg.md); iscsi_remove_host() tears it down.

## Relationship to the device model

The transport container attaches a device to each /sys/class/scsi_host host that belongs to an iSCSI transport (transport_class_to_shost). Sessions (iscsi_session.md) and ifaces (iscsi_iface.md) reference the host; endpoint devices (iscsi_endpoint.md) are used for offload connection setup.

## Attributes (source: drivers/scsi/scsi_transport_iscsi.c iscsi_host_attrs[])

| Attribute | R/W | Meaning |
|---|---|---|
| `netdev` | RO | Network device name backing the host (ISCSI_HOST_PARAM_NETDEV_NAME) |
| `hwaddress` | RO | Hardware address (ISCSI_HOST_PARAM_HWADDRESS) |
| `ipaddress` | RO | IP address (ISCSI_HOST_PARAM_IPADDRESS) |
| `initiatorname` | RO | iSCSI initiator node name |
| `port_state` | RO | "LINK UP" or "LINK DOWN" (iscsi_get_port_state_name) |
| `port_speed` | RO | One of Unknown, 10 Mbps, 100 Mbps, 1 Gbps, 10 Gbps, 25 Gbps, 40 Gbps (iscsi_get_port_speed_name) |

Each attribute is only visible when the transport reports support via attr_is_visible(ISCSI_HOST_PARAM, ...) (iscsi_host_attr_is_visible).

## Safety and writes

All six attributes are read-only; host configuration goes through netlink and the iface class, not sysfs. Empty on the container host.

## References

- drivers/scsi/scsi_transport_iscsi.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [iSCSI storage page](../../storage/iscsi.md), [iscsi_transport](./iscsi_transport.md), [bsg](./bsg.md)
