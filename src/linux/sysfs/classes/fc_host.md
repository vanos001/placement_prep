# /sys/class/fc_host

| Field | Value |
|---|---|
| Subsystem | Fibre Channel SCSI transport class, host side (FPIN statistics view); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: the ABI entries name no Kconfig symbol and no FC transport Kconfig is cached (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-fc_host` |
| Since | not stated in the ABI entries (dated July 2020) |
| Live (5.10.134 host) | class absent: no `fc_host` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-fc_host |

## What it represents

One directory `hostX` per Fibre Channel-capable SCSI host, created by the FC transport layer that sits between the SCSI midlayer and FC adapter drivers (LLDDs). The cached ABI documentation covers only the FPIN statistics subset added in July 2020 by a Marvell contact: counters for fabric performance impact notification (FPIN) events recorded by the F_Port -- congestion notifications, link integrity errors, and delivery-related errors. The entries use the `fpin_cn_yyy` / `fpin_li_yyy` / `fpin_dn_yyy` spelling with the `yyy` suffix as printed in the doc. The much larger set of per-host FC attributes (port names, speeds, states) is not represented in the cached ABI tree and is therefore not listed here.

## Relationship to the device model

`fc_host` is a transport-class view over SCSI hosts: the same `hostX` numbering used by `/sys/class/scsi_host`, with FC-specific attributes layered on by the transport. Remote ports seen by each host get their own class (`fc_remote_ports`, directories `rport-X:Y-Z` with a mirrored `statistics/` group). Writes to the singleton `/sys/class/fc/fc_udev_device` (application id store) associate traffic tags with cgroups that FC hosts then carry into the fabric.

## Attributes

All documented attributes are read-only counters, one file per event type.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `hostX/statistics/fpin_cn_yyy` | RO | count of congestion notification FPIN events recorded by the F_Port | FPIN-capable drivers | ABI testing `sysfs-class-fc_host` |
| `hostX/statistics/fpin_li_yyy` | RO | count of link integrity error FPIN events | FPIN-capable drivers | ABI testing `sysfs-class-fc_host` |
| `hostX/statistics/fpin_dn_yyy` | RO | count of delivery-related error FPIN events | FPIN-capable drivers | ABI testing `sysfs-class-fc_host` |

## Safety and writes

Reads are safe. No write path exists in the cached documentation. The counters are congestion/error telemetry: rising `fpin_li` values indicate physical link problems, `fpin_cn` fabric congestion -- the intended consumers are fabric monitoring tools reacting to FPIN notifications. Whether an individual driver implements the statistics group depends on the LLDD (the ABI names no Users: field, so no consumer list is available in the cached tree).

## References

- `Documentation/ABI/testing/sysfs-class-fc_host` (cached copy; three What: entries)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-fc_host)
- Companion pages: [fc_remote_ports](./fc_remote_ports.md), [fc](./fc.md), [scsi_host](./scsi_host.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-fc_host
