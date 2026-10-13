# /sys/class/gpio

| Field | Value |
|---|---|
| Subsystem | GPIO sysfs (legacy), `drivers/gpio/gpiolib-sysfs.c` |
| Config gate | `CONFIG_GPIO_SYSFS` (`obj-$(CONFIG_GPIO_SYSFS) += gpiolib-sysfs.o` in `drivers/gpio/Makefile`, torvalds/linux master) |
| ABI documentation | `Documentation/ABI/obsolete/sysfs-gpio` (obsolete tree); replacement: `Documentation/ABI/testing/gpio-cdev` |
| Since | 2.6.27; the ABI file states it is "obsoleted by Documentation/ABI/testing/gpio-cdev and will be removed after 2020" |
| Live (5.10.134 host) | class absent: no gpiochip exported through the legacy interface in the container |
| Ledger ID | SYSC-gpio |

## What it represents

The legacy userspace GPIO interface. A flat `/sys/class/gpio` directory holds `export`/`unexport` control files, one `gpioN` directory per exported GPIO line, and one `gpiochipN` (or newer `chipX`) directory per controller. GPIOs are kernel-global integers; nothing is visible until a line is explicitly exported. The documented replacement is the `/dev/gpiochipN` ioctl character device (KernelVersion 4.4 per `gpio-cdev`, used via libgpiod).

## Relationship to the device model

`gpiochipN` directories are views over controller devices under `/sys/devices/...`; exported `gpioN` directories are synthesized children, not real devices, and persist only while exported. The modern interface maps the same controllers to `/dev/gpiochipN` char nodes (listed in `/sys/dev/char` when present). No GPIO bus exists; the class is the only sysfs view.

## Attributes

The obsolete ABI file documents the full layout as a tree (single What: entry for `/sys/class/gpio/`); the ledger's 1 documented attr reflects that. Every row below comes from that tree.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `export` | WO | GPIO integer number; exports a line for userspace use | always | ABI obsolete `sysfs-gpio` tree |
| `unexport` | WO | GPIO integer number; returns the line to the kernel | always | ABI obsolete tree |
| `gpioN/value` | RO/RW | 0/1; "always readable, writes fail for input GPIOs" | exported lines | ABI obsolete tree |
| `gpioN/direction` | RW | `in`, `out` (default low); writes accept `high`, `low` | exported lines | ABI obsolete tree |
| `gpioN/edge` | RW | `none`, `falling`, `rising`, `both` (interrupt source selection) | exported lines | ABI obsolete tree |
| `gpioN/active_low` | RW | 0/1 polarity inversion | exported lines | ABI obsolete tree |
| `gpiochipN/base` | RO | first GPIO number of the chip (same as N) | gpiochips | ABI obsolete tree |
| `gpiochipN/label` | RO | descriptive chip name | gpiochips | ABI obsolete tree |
| `gpiochipN/ngpio` | RO | line count; chip spans N..N+ngpio-1 | gpiochips | ABI obsolete tree |
| `chipX/{export,unexport,label,ngpio}` | mixed | hardware-offset based variant of the above | newer kernel form | ABI obsolete tree |

The `chipX` form addresses lines by hardware offset instead of the global base+number scheme.

## Safety and writes

All reads are safe. Writes are the danger zone: `export` takes a line from whatever kernel driver claimed it (the ABI allows export only for unclaimed lines, and kernel code may also export), and a userspace writer then toggles hardware with no knowledge of board context. `value` writes on an input line fail. `userspace-api/gpio/sysfs.rst` documents these hazards (worklog 2-b). The interface is deprecated: new code must use `/dev/gpiochipN` ioctls (`GPIO_GET_LINEHANDLE_IOCTL` and friends) or libgpiod; distros compile `CONFIG_GPIO_SYSFS` mostly for legacy scripts.

## References

- `Documentation/ABI/obsolete/sysfs-gpio`, `Documentation/ABI/testing/gpio-cdev` (cached copies)
- `drivers/gpio/gpiolib-sysfs.c`, `drivers/gpio/Makefile` (torvalds/linux master)
- `Documentation/userspace-api/gpio/sysfs.rst`, `Documentation/userspace-api/gpio/chardev.rst`
- Ledger row SYSC-gpio (Source column notes the obsolete-tree location); worklog Task 2-b
