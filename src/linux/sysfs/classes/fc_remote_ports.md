# /sys/class/fc_remote_ports

| Field | Value |
|---|---|
| Subsystem | Fibre Channel SCSI transport class, remote-port side (FPIN statistics view); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: the ABI entries name no Kconfig symbol and no FC transport Kconfig is cached (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-fc_remote_ports` |
| Since | not stated in the ABI entries (dated July 2020) |
| Live (5.10.134 host) | class absent: no `fc_remote_ports` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-fc_remote_ports |

## What it represents

One directory `rport-X:Y-Z` per remote Fibre Channel port discovered by an FC host: the SCSI transport's representation of target-side FC ports (and, in general, remote FC entities the LLDD reports). The cached ABI documentation covers only the FPIN statistics group added in July 2020: three counters per remote port for fabric performance impact notification (FPIN) events -- congestion notification, link integrity errors, and delivery-related errors -- recorded by the F_Port/Nx_Port. The `X:Y-Z` name components (scsi host, channel, target id) follow the SCSI remote-port naming used across transport classes. The full per-rport attribute set of the FC transport is not in the cached tree and is not listed here.

## Relationship to the device model

Remote ports belong to an fc_host (`hostX` under `/sys/class/fc_host`, same `hostX` namespace as `/sys/class/scsi_host`); SCSI targets and LUNs hang off them in the SCSI device tree. The statistics group mirrors the per-host one in `sysfs-class-fc_host`, so host-side and port-side FPIN counters can be compared. Traffic tagging for these ports is administered via the `fc` class singleton (`fc_udev_device/appid_store`).

## Attributes

All documented attributes are read-only counters.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `rport-X:Y-Z/statistics/fpin_cn_yyy` | RO | count of congestion notification FPIN events | FPIN-capable drivers | ABI testing `sysfs-class-fc_remote_ports` |
| `rport-X:Y-Z/statistics/fpin_li_yyy` | RO | count of link integrity error FPIN events | FPIN-capable drivers | ABI testing `sysfs-class-fc_remote_ports` |
| `rport-X:Y-Z/statistics/fpin_dn_yyy` | RO | count of delivery-related error FPIN events | FPIN-capable drivers | ABI testing `sysfs-class-fc_remote_ports` |

## Safety and writes

Reads are safe; no writes are documented. Port-level FPIN counters localize a fabric problem to one target path: `fpin_li` spikes point at the physical path to that port, `fpin_cn` at congestion the fabric reports for it. Per the ABI description block, events are "reported using fabric performance impact notification (FPIN) event", so presence of the files depends on driver/fabric FPIN support; absence on older or non-FPIN LLDDs is expected.

## References

- `Documentation/ABI/testing/sysfs-class-fc_remote_ports` (cached copy; three What: entries)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-fc_remote_ports)
- Companion pages: [fc_host](./fc_host.md), [fc](./fc.md), [srp_remote_ports](./srp_remote_ports.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-fc_remote_ports
