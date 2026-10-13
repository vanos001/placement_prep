# /sys/class/ata_link

| Field | Value |
|---|---|
| Subsystem | libata ATA link class (ABI doc section "Files under /sys/class/ata_link"); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: no ATA Kconfig or Makefile is cached, and the ABI entry names no config symbol (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-ata`, section "Files under /sys/class/ata_link" |
| Since | 2.6.37 (all three attributes; entries dated May 2010) |
| Live (5.10.134 host) | class absent: no `ata_link` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-ata_link |

## What it represents

One directory per SATA link. Behind each ata port there is an ata_link; when a SATA Port Multiplier is in the topology, 15 ata_link objects are created. Naming is positional: a link directly behind a port is `linkX` (X = ata_port_id of the port); a link behind a PM port is `linkX.Y` (X = parent port id, Y = PM port). The three attributes report the SATA link speed negotiation state: what the hardware supports, what libata permits, and what was actually negotiated.

## Relationship to the device model

The link is the layer between port and device in the libata topology described by the ABI doc: `ata_port/ataX` -> `ata_link/linkX[.Y]` -> `ata_device/devX[.Y].Z`. Links are not bus devices and have no driver binding; they are kernel-created children of the port-side devices under `/sys/devices/...`, surfaced through this class for speed inspection. The `sata_spd` value complements the transfer-mode attributes on the device level (`pio_mode`, `dma_mode`, `xfer_mode` on ata_device).

## Attributes

All three documented attributes are read-only.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `linkX[.Y]/hw_sata_spd_limit` | RO | speed limit of the connected SATA device | always | ABI testing `sysfs-ata` |
| `linkX[.Y]/sata_spd_limit` | RO | maximum speed imposed by libata | always | ABI testing `sysfs-ata` |
| `linkX[.Y]/sata_spd` | RO | current link speed, e.g. "1.5, 3 Gbps etc." | always | ABI testing `sysfs-ata` |

## Safety and writes

All documented attributes are read-only; the ABI file defines no write interface for links. (Speed limiting through sysfs is not offered here; the ABI documents only the limit and current-speed views.) Reads are safe and do not touch the hardware beyond reporting cached libata state. On hosts with a PM, the 15 `linkX.Y` directories appear alongside the port's own `linkX`, which is expected layout, not duplication.

## References

- `Documentation/ABI/testing/sysfs-ata` (cached copy; one What: block covers all three attributes)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-ata)
- Companion pages: [ata_port](./ata_port.md), [ata_device](./ata_device.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-ata_link
