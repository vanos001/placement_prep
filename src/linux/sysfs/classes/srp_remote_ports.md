# /sys/class/srp_remote_ports

| Field | Value |
|---|---|
| Subsystem | SCSI RDMA Protocol transport, remote-port side; the SRP transport attributes are selected as `SCSI_SRP_ATTRS` (fetched `srp-Kconfig`: `INFINIBAND_SRP` "select SCSI_SRP_ATTRS"); implementation file not in cached tree |
| Config gate | `CONFIG_SCSI_SRP_ATTRS` -- verified indirectly via the fetched drivers/infiniband/ulp/srp Kconfig, where `config INFINIBAND_SRP` (depends on SCSI && INFINIBAND_ADDR_TRANS) selects it |
| ABI documentation | `Documentation/ABI/stable/sysfs-transport-srp` |
| Since | 2.6.24 (`port_id`, `roles`); 3.7 (`delete`); 3.13 (`dev_loss_tmo`, `fast_io_fail_tmo`, `reconnect_delay`, `state`) |
| Live (5.10.134 host) | class absent: no `srp_remote_ports` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-srp_remote_ports |

## What it represents

One directory `port-<h>:<n>` per remote SRP target port that an SRP initiator (ib_srp) has encountered. The class holds the transport-layer view of that remote port: identity (`port_id`, `roles`), connection health (`state`), and the error-recovery timers that decide how fast I/O fails and how fast the target is reconnected or dropped. This is the SRP analogue of the FC remote-port class; the initiator-side control (login) lives in `/sys/class/infiniband_srp` instead.

## Relationship to the device model

Remote ports sit between the ib_srp initiator (`srp-<hca>-<port>` devices under `infiniband_srp`) and the SCSI hosts they create: each port-<h>:<n> drives SCSI hosts whose connection parameters (`dgid`, `ioc_guid`, `req_lim`, ...) are exposed under `/sys/class/scsi_host` and documented in the same stable ABI file. LUNs imported through the port appear in the usual SCSI/block trees; `delete` is the documented way to tear that whole import down.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `port-<h>:<n>/port_id` | RO | 16-byte local SRP port identifier in hexadecimal, colon-separated | always | ABI stable `sysfs-transport-srp` |
| `port-<h>:<n>/roles` | RO | "SRP Initiator" or "SRP Target" | always | ABI stable `sysfs-transport-srp` |
| `port-<h>:<n>/state` | RO | running, blocked, fail-fast, or lost | always | ABI stable `sysfs-transport-srp` |
| `port-<h>:<n>/delete` | WO | write instructs disconnect and removal of all imported LUNs | always | ABI stable `sysfs-transport-srp` |
| `port-<h>:<n>/dev_loss_tmo` | W | seconds before target removal after transport error; 0 = immediate; "off" disables | always | ABI stable `sysfs-transport-srp` |
| `port-<h>:<n>/fast_io_fail_tmo` | W | seconds before I/O is failed after transport error; 0 = immediate; "off" disables | always | ABI stable `sysfs-transport-srp` |
| `port-<h>:<n>/reconnect_delay` | W | seconds between reconnect attempts; "off" disables time-based reconnecting | always | ABI stable `sysfs-transport-srp` |

## Safety and writes

Reads are safe. The three timers are multipath-critical: `dev_loss_tmo` and `fast_io_fail_tmo` shape SCSI error handling, and the `state` machine (blocked -> fail-fast -> lost) is exactly what multipath tools watch. `delete` is the destructive one -- it disconnects from the target and removes every LUN imported from it, so writing it on an in-use path will take file systems down. The ABI text describes writes to the timers but does not state their readability (not verified).

## References

- `Documentation/ABI/stable/sysfs-transport-srp` (cached copy; seven What: entries)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/stable/sysfs-transport-srp)
- Fetched `srp-Kconfig` (drivers/infiniband/ulp/srp Kconfig, `select SCSI_SRP_ATTRS`)
- Companion pages: [infiniband_srp](./infiniband_srp.md), [scsi_host](./scsi_host.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-srp_remote_ports
