# /sys/class/ubi

| Field | Value |
|---|---|
| Subsystem | UBI subsystem (Unsorted Block Images, wear-leveling layer over MTD); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); `/usr/include/linux/ubi-user.h` absent on the host (verified) |
| ABI documentation | `Documentation/ABI/stable/sysfs-class-ubi` (26 What entries: class, version, ubiX device dirs, ubiX_Y volume dirs) |
| Since | 2.6.22 (July 2006); `mtd_num` 2.6.25; `ro_mode` 4.7 |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/ubi (no MTD-backed UBI device in the container) |
| Ledger ID | SYSC-ubi |

## What it represents

The UBI control and device class. The class directory carries the on-media format `version` (currently 1) and one `ubiX` directory per UBI device (ubi0, ubi1, ...), each built over an MTD device. Each ubiX directory holds the device geometry and health files plus one `ubiX_Y` subdirectory per UBI volume, the dynamic/static partitions that user data lives in. Creation and deletion of devices and volumes is done through the `/dev/ubiN` and `/dev/ubiX_Y` character devices and their ioctls, not sysfs.

## Relationship to the device model

ubiX directories are class views of UBI devices; `dev` in each gives the major:minor of the matching character device. Each ubiX sits over an MTD device identified by `mtd_num`, so the UBI class is a consumer view of the MTD subsystem (see [mtd](./mtd.md)). Volume directories are nested under their device, not at class level - the volume's own `dev` file points at the volume character device. The sibling page [ubiX](./ubiX.md) documents the per-device layout in isolation.

## Attributes

Class level:

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `version` | RO | latest supported UBI on-media format version (currently 1) | always | ABI, 2.6.22 |

Per UBI device (`/sys/class/ubi/ubiX/`):

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `avail_eraseblocks` | RO | logical eraseblocks available for new volumes | always | ABI, 2.6.22 |
| `bad_peb_count` | RO | bad physical eraseblocks on the MTD device | always | ABI, 2.6.22 |
| `bgt_enabled` | RO | ASCII 0/1, background thread state | always | ABI, 2.6.22 |
| `dev` | RO | major:minor of the UBI character device | always | ABI, 2.6.22 |
| `eraseblock_size` | RO | max logical eraseblock size (bytes) | always | ABI, 2.6.22 |
| `max_ec` | RO | maximum erase counter value | always | ABI, 2.6.22 |
| `max_vol_count` | RO | maximum number of volumes | always | ABI, 2.6.22 |
| `min_io_size` | RO | minimum I/O unit size (bytes) | always | ABI, 2.6.22 |
| `mtd_num` | RO | underlying MTD device number | always | ABI, 2.6.25 |
| `reserved_for_bad` | RO | PEBs reserved for bad-block handling | always | ABI, 2.6.22 |
| `ro_mode` | RO | ASCII 1 when UBI switched to read-only after an unrecoverable error | always | ABI, 4.7 |
| `total_eraseblocks` | RO | good physical eraseblocks total | always | ABI, 2.6.22 |
| `volumes_count` | RO | volumes on this device | always | ABI, 2.6.22 |

Per volume (`/sys/class/ubi/ubiX/ubiX_Y/`): `alignment`, `corrupted` (0/1, e.g. interrupted update), `data_bytes` (meaningful for static volumes), `dev`, `name`, `reserved_ebs`, `type` (`dynamic`/`static`), `upd_marker` (1 = update in progress or interrupted), `usable_eb_size` - all RO, all from the same ABI file (2.6.22).

## Safety and writes

Every documented attribute is read-only; all UBI mutations (attach, detach, volume create/resize/remove, update start/end) are ioctl territory via the character devices. Two files deserve attention when troubleshooting: `ro_mode` = 1 means UBI gave up writing because of media errors, and `upd_marker` = 1 means an interrupted volume update (check `corrupted`). No sysfs write path exists in the ABI.

## References

- `Documentation/ABI/stable/sysfs-class-ubi` (cached copy; 26 What entries)
- `/usr/include/linux/ubi-user.h` absent on the host (verified) - the ioctl uapi could not be cited locally
- Implementation: not in cached tree
- Sibling pages: [ubiX](./ubiX.md), [mtd](./mtd.md); coverage: [ledger](../ledger.md)
- Live check: /sys/class/ubi absent (kernel 5.10.134, read-only enumeration)
