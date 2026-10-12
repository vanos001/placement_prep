# /sys/class/vtconsole

| Field | Value |
|---|---|
| Subsystem | virtual terminal console class (vt/console layer, drivers/tty/vt); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); the class is present on the live host, so its gate (vt console support) is enabled there |
| ABI documentation | none found in tree - no ABI file, and no MAINTAINERS hit for vtconsole in the cached tree (checked `Documentation/ABI/` recursively and MAINTAINERS) |
| Since | not stated by any cached source |
| Live (5.10.134 host) | class present with 1 device: `vtcon0`, containing `bind` (0644, reads 1), `name` (0444, reads "(S) dummy device"), `uevent`, a `power/` directory and a `subsystem` symlink - verified live |
| Ledger ID | SYSC-vtconsole |

## What it represents

One directory per virtual console console-driver binding: the class represents the pairing between the virtual terminal layer and a console driver (for example vgacon, fbcon, or on virtualized hosts a dummy console). The live host's single `vtcon0` reports the name string "(S) dummy device" - read verbatim from `name`; the meaning of the "(S)" prefix is not documented in the cached tree, and the dummy device name reflects that this VM runs no real framebuffer console driver.

## Relationship to the device model

`vtconN` directories are class devices created by the vt layer for each registered console driver; they are not hardware devices and have no bus parent. The `subsystem` symlink points back at the class, and the standard per-device `power/` directory (per-device runtime PM attributes, documented under `Documentation/ABI/testing/sysfs-devices-power`) is present as on any struct device. `bind` is the switch that attaches/detaches a console driver to the vt layer.

## Attributes

Everything in this section is live-verified on the 5.10.134 host (read-only); no cached source documents these files, so R/W is inferred from observed permission bits only.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `vtconN/name` | RO (0444) | console driver name string; live: "(S) dummy device" | always | live check 5.10.134 |
| `vtconN/bind` | RW (0644) | 0/1; live value 1 | always | live check 5.10.134 |
| `vtconN/uevent` | RO | device uevent file, empty on read live | always | live check 5.10.134 |
| `vtconN/power/` | -- | standard per-device power directory | always | live check 5.10.134 |

No attribute for this class is documented in the cached Documentation tree; the two meaningful files (`name`, `bind`) above are recorded from the live host.

## Safety and writes

The documented-hazard candidate is `bind`: writing 0 detaches the console driver from the virtual terminals, which can leave the system with no visible console - on a machine where fbcon is the only console this blanks the display until something rebinds. That behavior is the evident purpose of a bind switch, but it is inferred from the file name and live value, not from any cached ABI text. Reads are safe. Everything is root-only by normal sysfs ownership.

## References

- Live enumeration: /sys/class/vtconsole/vtcon0 (kernel 5.10.134; name/bind/uevent/power read-only)
- `Documentation/ABI/` recursive search for vtconsole: no match (cached tree)
- MAINTAINERS search for vtconsole: no match (cached tree)
- Related ABI: `Documentation/ABI/testing/sysfs-tty` (tty class, a different layer); [tty](./tty.md) sibling page; coverage: [ledger](../ledger.md)
