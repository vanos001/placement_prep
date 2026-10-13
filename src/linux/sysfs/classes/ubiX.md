# /sys/class/ubiX

| Field | Value |
|---|---|
| Subsystem | UBI subsystem - per-device view (ubi0, ubi1, ...) inside the [ubi](./ubi.md) class; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/stable/sysfs-class-ubi`, entries `/sys/class/ubiX/` and `/sys/class/ubi/ubiX/*` |
| Since | 2.6.22 (July 2006); `mtd_num` 2.6.25; `ro_mode` 4.7 |
| Live (5.10.134 host) | class absent: no /sys/class/ubi on the host, hence no ubiX entries |
| Ledger ID | SYSC-ubiX |

## What it represents

The UBI device directories themselves: `/sys/class/ubi0`, `/sys/class/ubi1`, etc. describe UBI device 0, 1 and so on - one per attached MTD device. The ABI describes them both as `/sys/class/ubiX/` and, in the full class layout, as `/sys/class/ubi/ubiX/`; they are the per-device member directories of the ubi class (class page: [ubi](./ubi.md)), separated out here because the ledger tracks the device-dir layout as its own row. Geometry, media health and background-thread state are all exposed here, which makes a ubiX directory the one-stop troubleshooting view for an attached UBI device.

## Relationship to the device model

Each ubiX directory is the class view of one UBI device: it names the underlying MTD device (`mtd_num`), exposes geometry and health counters, and contains the `ubiX_Y` volume subdirectories. The `dev` file gives the major:minor of `/dev/ubiX`, the character device that performs attach/detach and volume management via ioctls. Volume directories and their attributes are documented on the [ubi](./ubi.md) class page.

## Attributes

All paths below are read-only; source is `Documentation/ABI/stable/sysfs-class-ubi` throughout.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `ubiX/avail_eraseblocks` | RO | logical eraseblocks available for volume creation | always | ABI, 2.6.22 |
| `ubiX/bad_peb_count` | RO | bad physical eraseblocks on the MTD device | always | ABI, 2.6.22 |
| `ubiX/bgt_enabled` | RO | ASCII 0/1 background thread state | always | ABI, 2.6.22 |
| `ubiX/dev` | RO | major:minor of /dev/ubiX | always | ABI, 2.6.22 |
| `ubiX/eraseblock_size` | RO | max logical eraseblock size (bytes) | always | ABI, 2.6.22 |
| `ubiX/max_ec` | RO | maximum erase counter value | always | ABI, 2.6.22 |
| `ubiX/max_vol_count` | RO | maximum number of volumes | always | ABI, 2.6.22 |
| `ubiX/min_io_size` | RO | minimum I/O unit size (bytes) | always | ABI, 2.6.22 |
| `ubiX/mtd_num` | RO | underlying MTD device number | always | ABI, 2.6.25 |
| `ubiX/reserved_for_bad` | RO | PEBs reserved for bad-block handling | always | ABI, 2.6.22 |
| `ubiX/ro_mode` | RO | ASCII 1 when the device switched to read-only after media errors | always | ABI, 4.7 |
| `ubiX/total_eraseblocks` | RO | count of good physical eraseblocks | always | ABI, 2.6.22 |
| `ubiX/volumes_count` | RO | volumes on this device | always | ABI, 2.6.22 |
| `ubiX/ubiX_Y/` | -- | one subdirectory per volume (attributes on the ubi class page) | volume exists | ABI, 2.6.22 |

## Safety and writes

Nothing writable: the whole ubiX attribute set is a status and geometry snapshot. The dangerous operations on UBI devices (detach, volume removal, update) are ioctls on the character device named by `dev`. For troubleshooting, `ro_mode`, `bad_peb_count` and `max_ec` are the media-health indicators the ABI itself describes.

## References

- `Documentation/ABI/stable/sysfs-class-ubi` (cached copy; ubiX entries)
- Class page: [ubi](./ubi.md); MTD layer: [mtd](./mtd.md); coverage: [ledger](../ledger.md)
- Implementation: not in cached tree
- Live check: /sys/class/ubi absent (kernel 5.10.134, read-only enumeration)
