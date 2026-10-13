# /sys/class/iscsi_endpoint

| Field | Value |
|---|---|
| Subsystem | iSCSI transport, drivers/scsi/scsi_transport_iscsi.c (struct class iscsi_endpoint_class, name "iscsi_endpoint") |
| Config gate | CONFIG_SCSI_ISCSI_ATTRS (see iscsi_transport.md) |
| ABI documentation | none found - checked the stable/, testing/ and obsolete/ ABI listings and grep for iscsi; the single attribute below is named by drivers/scsi/scsi_transport_iscsi.c |
| Since | not stated by the sources checked |
| Live (5.10.134 host) | class present with 0 entries |
| Ledger ID | SYSC-iscsi_endpoint |

## What it represents

One device per transport connection endpoint, created by iscsi_create_endpoint() when an offload transport establishes the hardware side of a TCP/IP connection before the session exists. The endpoint is the handle user space and the kernel use to reference that half-open connection.

## Relationship to the device model

Endpoints are standalone class devices (no parent declared at creation, ep->dev.class = iscsi_endpoint_class); they are consumed when a connection (iscsi_connection.md) binds to them and are released with the endpoint id freed through the iscsi_ep_idr (iscsi_endpoint_release).

## Attributes (source: drivers/scsi/scsi_transport_iscsi.c iscsi_endpoint_attrs[])

| Attribute | R/W | Meaning |
|---|---|---|
| `handle` | RO | Endpoint id (sysfs_emit "%d"), the value passed over netlink when binding a connection |

## Safety and writes

The single attribute is read-only. Endpoint lifetimes are managed by the transport through netlink; there is no sysfs write path. Empty on the container host; in real deployments these devices appear only transiently during offload login.

## References

- drivers/scsi/scsi_transport_iscsi.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [iSCSI storage page](../../storage/iscsi.md), [iscsi_connection](./iscsi_connection.md), [iscsi_transport](./iscsi_transport.md)
