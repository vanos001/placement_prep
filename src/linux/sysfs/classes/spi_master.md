# /sys/class/spi_master

| Field | Value |
|---|---|
| Subsystem | SPI core (serial peripheral interface bus class); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-spi-master` (2 What entries) plus device files in `sysfs-class-spi-eeprom` (3 entries) |
| Since | `new_device`/`delete_device` July 2026, KernelVersion 7.3 (newer than the live kernel); eeprom device files 5.14 (`fram`, `sernum`) and 6.19 (`jedec_id`) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/spi_master |
| Ledger ID | SYSC-spi_master |

## What it represents

One directory per SPI bus controller, named `spiB` for bus number B, with one child directory `spiB.D` per device on that bus (D = chip select). The class documents two hot-plug control files - `new_device` and `delete_device` for instantiating and removing SPI devices from userspace, analogous to the i2c-dev interface - and the ABI corpus also documents driver-specific files that appear inside device subdirectories (the at25 EEPROM/FRAM driver's identity files).

## Relationship to the device model

`spiB` directories are class views of SPI controller devices; `spiB.D` are the probed (or user-instantiated) SPI devices. Per the ABI, only devices created through `new_device` can be removed with `delete_device` - platform and device-tree devices are not affected by the removal path. The eeprom files (`fram`, `sernum`, `jedec_id`) are driver attributes of the at25-style device driver, not class-wide attributes.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `spiB/new_device` | WO | `<modalias> <chip_select> [<max_speed_hz> [<mode>]]`, instantiates a device | controller | ABI `sysfs-class-spi-master`, 7.3 |
| `spiB/delete_device` | WO | chip select number; removes a `new_device`-created device | controller | ABI `sysfs-class-spi-master`, 7.3 |
| `spiB.D/fram` | RO | FRAM binary content (at25-style, bus-speed writes) | eeprom/FRAM device | ABI `sysfs-class-spi-eeprom`, 5.14 |
| `spiB.D/sernum` | RO | 8-byte hex serial number of Cypress FRAM (FM25VN) | eeprom/FRAM device | ABI `sysfs-class-spi-eeprom`, 5.14 |
| `spiB.D/jedec_id` | RO | hex JEDEC ID from the RDID (0x9f) command, big-endian | device implementing RDID | ABI `sysfs-class-spi-eeprom`, 6.19 |

## Safety and writes

`new_device` wires a new SPI device onto the live bus with a chosen chip select, speed and mode; a wrong modalias binds the wrong driver, and a wrong chip select can disturb other bus users. `delete_device` only undoes devices it created. The two control files postdate the live host kernel (KernelVersion 7.3 in the ABI file), so on 5.10.134 neither exists - the honest live statement is that the class itself is absent here. The eeprom files are reads of hardware identity/memory; writing is not documented for them in the cached tree.

## References

- `Documentation/ABI/testing/sysfs-class-spi-master` (cached copy; 2 What entries, KernelVersion 7.3)
- `Documentation/ABI/testing/sysfs-class-spi-eeprom` (cached copy; 3 What entries)
- Implementation: not in cached tree
- Sibling pages: [i2c-adapter](./i2c-adapter.md) (the i2c new_device analog); coverage: [ledger](../ledger.md)
- Live check: /sys/class/spi_master absent (kernel 5.10.134, read-only enumeration)
