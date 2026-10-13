# /sys/class/ata_port

| Field | Value |
|---|---|
| Subsystem | libata ATA port class (ABI doc section "Files under /sys/class/ata_port"); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: no ATA Kconfig or Makefile is cached, and the ABI entry names no config symbol (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-ata`, section "Files under /sys/class/ata_port" |
| Since | 2.6.37 for `nr_pmp_links`/`idle_irq` (entries dated May 2010); 3.11 for `port_no` (May 2013) |
| Live (5.10.134 host) | class absent: no `ata_port` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-ata_port |

## What it represents

One directory `ataX` per ATA port, where X is the ata_port_id of the port. The ABI introduction for the `ata_*` classes says they "provide a place in sysfs for storing the ATA topology of the system", exposing information about ATA objects that libata created while registering a host controller. The device parent of each `ataX` entry is the ata host device. `port_no` exists specifically so udev can compose persistent links in `/dev/disk/by-path`, making this class part of stable disk naming.

## Relationship to the device model

`ata_port` sits in the middle of the libata topology chain documented by the same ABI file: a host controller device has ports (`/sys/class/ata_port/ataX`), each port has a link (`/sys/class/ata_link/linkX`, or `linkX.Y` behind a port multiplier), and each link has up to two devices (`/sys/class/ata_device/devX[.Y].Z`). No ATA bus exists in sysfs; the class directories are views over devices parented by the ata host device, not bus endpoints.

## Attributes

All three documented attributes are read-only.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `ataX/nr_pmp_links` | RO | integer; number of links behind a SATA Port Multiplier | only if a PM is connected | ABI testing `sysfs-ata` |
| `ataX/idle_irq` | RO | integer; IRQs received while idle | "some ata HBA only" per ABI | ABI testing `sysfs-ata` |
| `ataX/port_no` | RO | integer; host local port number, used by udev for /dev/disk/by-path | always | ABI testing `sysfs-ata` |

## Safety and writes

All documented attributes are read-only; the ABI file describes no write path for this class. Reading them is safe and side-effect free. The port-multiplier and idle-IRQ counters depend on hardware topology, so absence of a file is normal rather than an error. No udev/kernel warnings are attached to these files in the cached documentation.

## References

- `Documentation/ABI/testing/sysfs-ata` (cached copy; one What: block covers `nr_pmp_links`/`idle_irq`, a second covers `port_no`)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-ata)
- Companion pages: [ata_link](./ata_link.md), [ata_device](./ata_device.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-ata_port (9/3/3 attribute counts for the ata_device/ata_link/ata_port trio)
