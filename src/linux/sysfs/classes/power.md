# /sys/class/power

| Field | Value |
|---|---|
| Subsystem | legacy `power` class directory; only known in-tree references are ds2760 battery monitor entries inside the power-supply ABI file; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files) |
| ABI documentation | two What entries inside `Documentation/ABI/testing/sysfs-class-power` (`/sys/class/power/ds2760-battery.*/charge_now`, `charge_full`); no sysfs-class-power ABI file of its own |
| Since | May 2010, KernelVersion 2.6.35 (both entries) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/power |
| Ledger ID | SYSC-power |

## What it represents

A distinct sysfs class name `power` - not to be confused with any of its three namesakes. The only in-tree documentation is device-specific: the ds2760 battery monitor driver's charge counter files, whose What entries spell the path `/sys/class/power/ds2760-battery.*/` and which live, oddly, inside the power-supply ABI file rather than a class file of their own. The cached tree contains no driver or core sources, so nothing more about the class layout or registration can be verified here.

## Relationship to the device model

Cannot be documented from the cached sources beyond the two attribute paths. Disambiguation of the three different things called "power":

- `/sys/class/power/` - this class (ds2760 battery entries, 2.6.35-era).
- `/sys/class/power_supply/` - the power supply class: batteries, AC, USB; see [power_supply](./power_supply.md).
- `/sys/power/` - a top-level sysfs directory (not a class) for system sleep control, documented in `Documentation/ABI/testing/sysfs-power` (`state`, `mem_sleep`, `disk`).
- `/sys/devices/.../power/` - per-device runtime-PM and wakeup attributes, documented in `Documentation/ABI/testing/sysfs-devices-power`.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `ds2760-battery.*/charge_now` | RW | current coulomb counter value of the battery monitor chip | ds2760 hardware | ABI `sysfs-class-power`, May 2010, 2.6.35 |
| `ds2760-battery.*/charge_full` | RW | assumed battery full level, adjustable as batteries age | ds2760 hardware | ABI `sysfs-class-power`, May 2010, 2.6.35 |

Both files are explicitly described as writeable in the ABI text; they tune the gauge's fuel bookkeeping rather than report measurements.

## Safety and writes

Writing `charge_full` or `charge_now` corrupts the battery gauge's idea of its capacity if done wrongly (the ABI describes adjusting full level as batteries age), so these are calibration writes with permanent effects on remaining-capacity reporting. The class does not exist on the live 5.10.134 host; ds2760 is embedded (iPAQ-era) hardware and the entries document legacy interfaces. Beyond the two files above, nothing about this class is verifiable from the cached sources - the page is deliberately source-limited.

## References

- `Documentation/ABI/testing/sysfs-class-power` (cached copy; ds2760 entries at lines 683-704)
- `Documentation/ABI/testing/sysfs-power`, `Documentation/ABI/testing/sysfs-devices-power` (for the disambiguation)
- [power_supply](./power_supply.md) sibling page; coverage: [ledger](../ledger.md)
- Live check: /sys/class/power absent (kernel 5.10.134, read-only enumeration)
