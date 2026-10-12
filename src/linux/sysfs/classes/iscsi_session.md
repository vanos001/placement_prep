# /sys/class/iscsi_session

| Field | Value |
|---|---|
| Subsystem | iSCSI transport, drivers/scsi/scsi_transport_iscsi.c (transport class iscsi_session_class via DECLARE_TRANSPORT_CLASS, name "iscsi_session") |
| Config gate | CONFIG_SCSI_ISCSI_ATTRS (see iscsi_transport.md) |
| ABI documentation | none found - checked the stable/, testing/ and obsolete/ ABI listings and grep for iscsi; attributes below are named by drivers/scsi/scsi_transport_iscsi.c (iscsi_session_attrs[]) |
| Since | not stated by the sources checked |
| Live (5.10.134 host) | class present with 0 entries |
| Ledger ID | SYSC-iscsi_session |

## What it represents

One device per iSCSI session to a target. The device carries the negotiated login parameters, the target identity, and the private recovery state the transport uses to resynchronize after connection loss.

## Relationship to the device model

Sessions hang off the iSCSI SCSI host and are the parents of connection devices (iscsi_connection.md). The SCSI devices that reach LUNs appear in the SCSI/block trees once the session is bound; `target_id` names the transport-assigned id.

## Attributes (representative; source: scsi_transport_iscsi.c iscsi_session_attrs[])

| Attribute | R/W | Meaning |
|---|---|---|
| `targetname` | RO | iSCSI target node name |
| `targetalias` | RO | Target alias string |
| `tpgt` | RO | Target portal group tag |
| `ifacename`, `initiatorname` | RO | Bound iface name; initiator node name |
| `initial_r2t`, `immediate_data`, `first_burst_len`, `max_burst_len`, `max_outstanding_r2t`, `data_pdu_in_order`, `data_seq_in_order`, `erl` | RO | Negotiated login parameters |
| `fast_abort`, `abort_tmo`, `lu_reset_tmo`, `tgt_reset_tmo`, `def_taskmgmt_tmo` | RO | Abort and reset timeout configuration |
| `recovery_tmo` | 0644 | Reconnection grace period, default 120 s; writing "off" sets -1 and marks the override (iscsi_priv_session_rw_attr, store path sets recovery_tmo_sysfs_override) |
| `state`, `target_state` | RO | Private session state strings (show_priv_session_state et al.) |
| `creator`, `target_id`, `isid`, `tsid`, `discovery_session`, `portal_type`, `chap_auth`, `bidi_chap` | RO | Session bookkeeping and auth state |

Passwords and usernames in the attribute list (sess_password, sess_username and the _in variants) are param-backed entries whose visibility also follows transport attr_is_visible.

## Safety and writes

`recovery_tmo` is the only writable attribute in the list (S_IRUGO | S_IWUSR); the store helper rejects writes with -EBUSY while the session is FREE or FAILED. Empty on the container host.

## References

- drivers/scsi/scsi_transport_iscsi.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [iSCSI storage page](../../storage/iscsi.md), [iscsi_connection](./iscsi_connection.md), [iscsi_iface](./iscsi_iface.md)
