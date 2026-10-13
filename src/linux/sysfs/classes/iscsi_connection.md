# /sys/class/iscsi_connection

| Field | Value |
|---|---|
| Subsystem | iSCSI transport, drivers/scsi/scsi_transport_iscsi.c (transport class iscsi_connection_class via DECLARE_TRANSPORT_CLASS, name "iscsi_connection") |
| Config gate | CONFIG_SCSI_ISCSI_ATTRS (see iscsi_transport.md) |
| ABI documentation | none found - checked the stable/, testing/ and obsolete/ ABI listings and grep for iscsi; attributes below are named by drivers/scsi/scsi_transport_iscsi.c (iscsi_conn_attrs[]) |
| Since | not stated by the sources checked |
| Live (5.10.134 host) | class present with 0 entries |
| Ledger ID | SYSC-iscsi_connection |

## What it represents

One device per TCP/IP connection inside an iSCSI session. A single-connection session has one; multiconnection sessions (MC/S) have several. The device carries the live login/transport parameters and the peer address state.

## Relationship to the device model

Connection devices are children of their session device: the show helpers resolve the session with iscsi_dev_to_session(dev->parent) (scsi_transport_iscsi.c), so the /sys/devices hierarchy nests connections under sessions under hosts. Which of the attributes below appear is decided per transport by attr_is_visible.

## Attributes (representative; source: scsi_transport_iscsi.c iscsi_conn_attrs[])

| Attribute | R/W | Meaning |
|---|---|---|
| `address`, `port` | RO | Peer (target) IP address and port |
| `persistent_address`, `persistent_port` | RO | Address and port recorded in the persisted configuration |
| `local_ipaddr`, `local_port` | RO | Local address and port of the connection |
| `exp_statsn`, `statsn` | RO | Expected and current status/command sequence numbers |
| `max_recv_dlength`, `max_xmit_dlength` | RO | Negotiated PDU length limits |
| `header_digest`, `data_digest` | RO | Digest negotiation state |
| `ping_tmo`, `recv_tmo`, `keepalive_tmo` | RO | Timeout parameters (ISCSI_PARAM_PING_TMO et al.) |
| `tcp_wsf`, `tcp_xmit_wsf`, `tcp_recv_wsf`, `tcp_timer_scale`, `tcp_timestamp_enable`, `tcp_nagle_disable` | RO | TCP tuning state |
| `state` | RO | Connection state string (show_conn_state) |
| `ipv4_tos`, `ipv6_traffic_class`, `ipv6_flow_label`, `is_fw_assigned_ipv6`, `fragment_disable`, `ifmarker`, `ofmarker` | RO | Address-family specific and marker state |

## Safety and writes

All connection attributes are read-only. Peer and persistent address/port pairs are the values tools print when diagnosing a hung session. Empty on the container host.

## References

- drivers/scsi/scsi_transport_iscsi.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [iSCSI storage page](../../storage/iscsi.md), [iscsi_session](./iscsi_session.md), [iscsi_endpoint](./iscsi_endpoint.md)
