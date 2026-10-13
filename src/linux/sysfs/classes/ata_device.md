# /sys/class/ata_device

| Field | Value |
|---|---|
| Subsystem | libata ATA device class (ABI doc section "Files under /sys/class/ata_device"); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: no ATA Kconfig or Makefile is cached, and the ABI entry names no config symbol (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-ata`, section "Files under /sys/class/ata_device" |
| Since | 2.6.37 for the main block (entries dated May 2010); 4.10 for `trim` (May 2015) |
| Live (5.10.134 host) | class absent: no `ata_device` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-ata_device |

## What it represents

One directory per ATA device at the bottom of the libata topology: behind each link up to two ata devices are created. Directory names are `devX[.Y].Z` where X is the ata_port_id of the port, Y the PM port if any, and Z the device id -- for PATA usually two devices (0 and 1), for SATA one. The attributes expose the cached identity and mode state of the device: device class, IDENTIFY data, transfer modes, error history and TRIM behavior. The ABI text repeatedly says "cached" -- these files report libata's cached results, not live hardware queries.

## Relationship to the device model

These are the leaf objects of the `ata_port` -> `ata_link` -> `ata_device` chain in one ABI doc. The class value (`class` attribute) distinguishes "ata" disk, "atapi" packet device, "pmp" port multiplier, or "none". The block devices a user actually mounts appear elsewhere (SCSI layer); this class is the libata-side view of the physical device.

## Attributes

All documented attributes are read-only.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `devX[.Y].Z/class` | RO | `ata` (disk), `atapi` (packet), `pmp` (PM), `none` | always | ABI testing `sysfs-ata` |
| `devX[.Y].Z/id` | RO | IDENTIFY result per ATA8 7.16/7.17 | only if device is not a PM | ABI testing `sysfs-ata` |
| `devX[.Y].Z/gscr` | RO | PM GSCR register dump (regs 0,1,2,32,33,64,96,130 valid) | only if device is a PM | ABI testing `sysfs-ata` |
| `devX[.Y].Z/ering` | RO | formatted error ring of the device | always | ABI testing `sysfs-ata` |
| `devX[.Y].Z/spdn_cnt` | RO | count of libata speed-down decisions due to errors | always | ABI testing `sysfs-ata` |
| `devX[.Y].Z/pio_mode` | RO | PIO transfer mode; mostly PATA | always | ABI testing `sysfs-ata` |
| `devX[.Y].Z/dma_mode` | RO | DMA transfer mode; mostly PATA | always | ABI testing `sysfs-ata` |
| `devX[.Y].Z/xfer_mode` | RO | current transfer mode; mostly PATA | always | ABI testing `sysfs-ata` |
| `devX[.Y].Z/trim` | RO | one of unsupported, unqueued, queued, forced_unqueued | since 4.10 | ABI testing `sysfs-ata` |

`forced_unqueued` means the drive's queued DSM support is known to be buggy so only unqueued TRIM commands are sent.

## Safety and writes

No write path is documented for this class; everything is a read-only report of cached libata state, so reads are safe. `spdn_cnt` and `ering` are the diagnostic pair for unstable links (compare with `sata_spd` on the link). `trim` is informational -- it shows which DSM TRIM mode the kernel decided to use, it does not issue a TRIM.

## References

- `Documentation/ABI/testing/sysfs-ata` (cached copy)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-ata)
- Companion pages: [ata_port](./ata_port.md), [ata_link](./ata_link.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-ata_device
