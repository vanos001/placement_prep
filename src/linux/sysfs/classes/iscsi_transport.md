# /sys/class/iscsi_transport

| Field | Value |
|---|---|
| Subsystem | iSCSI transport class, drivers/scsi/scsi_transport_iscsi.c (struct class iscsi_transport_class, name "iscsi_transport") |
| Config gate | CONFIG_SCSI_ISCSI_ATTRS, tristate, depends on SCSI and NET, selects BLK_DEV_BSGLIB (drivers/scsi/Kconfig); transport modules such as iscsi_tcp depend on it |
| ABI documentation | none found - checked the stable/, testing/ and obsolete/ ABI listings and grep for iscsi; attributes below are named by drivers/scsi/scsi_transport_iscsi.c |
| Since | not stated by the sources checked (no ABI What: entries exist) |
| Live (5.10.134 host) | class present with 0 entries (no iSCSI transport loaded) |
| Ledger ID | SYSC-iscsi_transport |

## What it represents

One device per registered iSCSI transport implementation (the software transport iscsi_tcp and offload drivers register with iscsi_register_transport()). These devices are the transport bookkeeping layer; the classes iscsi_host.md, iscsi_iface.md, iscsi_endpoint.md, iscsi_session.md and iscsi_connection.md carry the per-object state.

## Relationship to the device model

The transport device exposes the capability set of the implementation to user space (netlink discovers it via the `handle` value). All session, connection, iface and endpoint objects reference their transport through the same iscsi_internal structure (scsi_transport_iscsi.c).

## Attributes (source: drivers/scsi/scsi_transport_iscsi.c iscsi_transport_attrs[])

| Attribute | R/W | Meaning |
|---|---|---|
| `handle` | RO | 64-bit transport handle (sysfs_emit "%llu"); read requires CAP_SYS_ADMIN, otherwise -EACCES |
| `caps` | RO | Transport capability bitmask, format "0x%x" |

## Safety and writes

Both attributes are read-only. The handle is deliberately privileged: user space needs it to address the transport through the iSCSI netlink interface (iscsi_uevent, same file), so exposing it unprivileged would leak a kernel-addressing token. Empty on the container host.

## References

- drivers/scsi/scsi_transport_iscsi.c (fetched from torvalds/linux master into source-cache)
- drivers/scsi/iscsi_tcp.c (software transport that registers a transport)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [iSCSI storage page](../../storage/iscsi.md), [iscsi_host](./iscsi_host.md), [iscsi_session](./iscsi_session.md)
