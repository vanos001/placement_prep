# /sys/class/scsi_generic

| Field | Value |
|---|---|
| Subsystem | SCSI generic (sg) character-device class; implementation file not in cached tree; userspace interface documented by the glibc header `/usr/include/scsi/sg.h` |
| Config gate | not verifiable from the cached tree: no SCSI Kconfig is cached and no cached file names the sg config symbol (not verified) |
| ABI documentation | none found in tree -- `rg -i scsi_generic` over Documentation/ABI/stable, testing, obsolete, removed returns no files |
| Since | not stated by any cached source; `/usr/include/scsi/sg.h` says "New interface introduced in the 3.x SG drivers follows" (sg driver version 3 interface) |
| Live (5.10.134 host) | class present with 0 entries: `/sys/class/scsi_generic` exists but is empty (no SCSI device exposed via sg in the container) |
| Ledger ID | SYSC-scsi_generic |

## What it represents

The class view of the SCSI generic driver's character devices: nodes that user processes open to send arbitrary SCSI commands (pass-through) to a device, instead of using the block or tape interfaces on top. The authoritative cached material for the interface is the host's `/usr/include/scsi/sg.h` (glibc, 11663 bytes), which documents the sg 3.x programming interface: `struct sg_io_hdr` with fields for the SCSI command (`cmdp`), data direction (`dxfer_direction`, values `SG_DXFER_NONE`/`SG_DXFER_TO_DEV`/`SG_DXFER_FROM_DEV`), sense buffer (`sbp`), and status; plus the ioctl set including `SG_IO` (0x2285, "synchronous SCSI command ioctl ... similar effect as write() followed by read()"). The sysfs class itself is the enumeration handle; the interface is the char device each entry represents.

## Relationship to the device model

Each class entry corresponds to one SCSI device (logical unit) that the sg driver has attached, the same LUNs that appear as scsi_device entries; sg adds a command-pass-through char device on top. On the empty host the correspondence cannot be inspected, only inferred from the sg.h model of "fd's bus, chan, dev, lun + type" (SG_GET_SCSI_ID). The resulting device nodes are character devices created by the sg driver, not block devices.

## Attributes

No sysfs attribute of this class is documented in any cached source, so none is listed. The functional interface is ioctl-based, per `/usr/include/scsi/sg.h`: `SG_IO` (sync command), `SG_SCSI_RESET` (reset device/bus/host), `SG_GET_VERSION_NUM`, `SG_EMULATED_HOST` ("true for emulated host adapter (ATAPI)"), `SG_SET_RESERVED_SIZE`/`SG_GET_RESERVED_SIZE`, `SG_GET_SCSI_ID`, `SG_GET_NUM_WAITING`, `SG_MAX_QUEUE 16` queued commands.

## Safety and writes

There are no sysfs writes to document; the safety story belongs to the char device. Raw SCSI commands bypass the block layer's protections: a `write()`/`SG_IO` can issue destructive opcodes (format, mode changes) to whatever LUN is opened, and `SG_SCSI_RESET` resets device, bus, or host. `SG_IO` on a device opened read-only restricts data direction -- that restriction is kernel behavior, not stated in the cached header (not verified). On this host the class is empty, so nothing is exposed.

## References

- `/usr/include/scsi/sg.h` (glibc header on this host; SG_IO and ioctl set, sg_io_hdr struct)
- `source-cache/live-sys/class-list.txt`, row `scsi_generic	0`
- Direct read-only inspection: `/sys/class/scsi_generic` exists and is empty
- ABI search for `scsi_generic`: 0 matches (negative evidence)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [SCSI storage page](../../storage/scsi-nvme.md)
- Ledger row SYSC-scsi_generic
