# /sys/class/scsi_tape

| Field | Value |
|---|---|
| Subsystem | SCSI tape driver ("st" per the ABI text: "the number of I/Os currently in-flight between the st module and the SCSI mid-layer"); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: no SCSI Kconfig is cached and the ABI entry names no config symbol (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-scsi_tape` |
| Since | 4.2 (all entries dated Apr 2015, KernelVersion 4.2) |
| Live (5.10.134 host) | class absent: no `scsi_tape` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-scsi_tape |

## What it represents

I/O statistics for SCSI tape drives, one `stats/` group per tape device directory in the class. The counters cover the traffic between the st driver and the SCSI midlayer: read/write request and byte counts, wait times in nanoseconds, non-read/write SCSI commands (e.g. the rewind issued when a rewind tape device is closed), in-flight commands, and residuals. Byte counts are tracked in bytes because, as the ABI notes, tape drives support variable length block sizes.

## Relationship to the device model

The `stats/` group hangs off per-device directories under `/sys/class/scsi_tape`; the devices are the st driver's view of scsi_device LUNs that present as tape. The class is a statistics-only view: device control (position, mode select) is done through the tape char devices and ioctls, not sysfs. No relationship to block devices exists -- tapes do not appear in `/sys/block`.

## Attributes

All documented attributes are read-only counters under the `stats/` subdirectory.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `*/stats/in_flight` | RO | number of I/Os in-flight between st and the SCSI mid-layer | always | ABI testing `sysfs-class-scsi_tape` |
| `*/stats/read_cnt` / `write_cnt` | RO | number of read / write requests issued | always | ABI testing `sysfs-class-scsi_tape` |
| `*/stats/read_byte_cnt` / `write_byte_cnt` | RO | total bytes requested from / written to the drive (bytes, variable block sizes) | always | ABI testing `sysfs-class-scsi_tape` |
| `*/stats/read_ns` / `write_ns` | RO | nanoseconds waiting for read / write I/O completion | always | ABI testing `sysfs-class-scsi_tape` |
| `*/stats/io_ns` | RO | total nanoseconds waiting for all I/O incl. other commands (io_ns - read_ns - write_ns = other wait) | always | ABI testing `sysfs-class-scsi_tape` |
| `*/stats/other_cnt` | RO | number of I/O requests other than SCSI read/write (e.g. rewinds) | always | ABI testing `sysfs-class-scsi_tape` |
| `*/stats/resid_cnt` | RO | count of residual > 0 cases found when the midlayer indicated an error | always | ABI testing `sysfs-class-scsi_tape` |
| `*/stats/write_ms` | RO | ABI description says "total amount of time in nanoseconds" for writes -- name says ms, text says ns; discrepancy kept as documented | always | ABI testing `sysfs-class-scsi_tape` |

## Safety and writes

Read-only throughout; no write path exists in the ABI file. Reads are safe and cheap (accounting state, no hardware access). Note the `write_ms` naming inconsistency flagged above; the ABI entries also carry empty `Users:` fields -- no consumers are named in the cached tree.

## References

- `Documentation/ABI/testing/sysfs-class-scsi_tape` (cached copy; ten What: entries)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-scsi_tape)
- `source-cache/sysfs-attrs.json` scsi_tape entry (10 paths, matching)
- Companion pages: [scsi_device](./scsi_device.md), [scsi_generic](./scsi_generic.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-scsi_tape
