# /sys/class/leds

| Field | Value |
|---|---|
| Subsystem | LED class, `drivers/leds/led-class.c` (core attributes); triggers in `drivers/leds/trigger/` |
| Config gate | `CONFIG_LEDS_CLASS` (`obj-$(CONFIG_LEDS_CLASS) += led-class.o` in `drivers/leds/Makefile`, torvalds/linux master; flash and multicolor extensions gated by `CONFIG_LEDS_CLASS_FLASH` and `CONFIG_LEDS_CLASS_MULTICOLOR`) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-led` (core); `sysfs-class-led-flash`, `sysfs-class-led-multicolor`, `sysfs-class-led-trigger-*` for extensions |
| Since | 2.6.17 (`brightness`, `max_brightness`, `trigger`); 2.6.38 (`inverted`); 4.11 (`brightness_hw_changed`); 5.9 (`multi_intensity`, `multi_index`) |
| Live (5.10.134 host) | class absent: no LED device registered in the container |
| Ledger ID | SYSC-leds |

## What it represents

One directory per LED, named `devicename:color:function` per `Documentation/leds/leds-class.rst` (for example `input0::numlock`). Userspace sets brightness, or attaches a trigger so the kernel drives the LED from events (disk activity, heartbeat, network). Most LEDs have no hardware dimming: any non-zero value is simply on, which the ABI states for `brightness`.

## Relationship to the device model

`/sys/class/leds/<led>` is a class view of a device under `/sys/devices/...` (platform, i2c, USB, or virtual device). No bus of its own and no char/block node; an LED is not a `/dev` object. Trigger-specific parameter files appear inside the LED directory once a trigger is selected (ABI `trigger` entry).

## Attributes

The core ABI file `sysfs-class-led` carries 5 What: entries; counting every path spelled `/sys/class/leds/...` across the ABI tree (flash, multicolor, triggers, per-driver files) gives 96, the number recorded in the ledger. The table below is representative.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<led>/brightness` | RW | 0..`max_brightness`, decimal; 0 clears the active trigger | always | ABI What `brightness` (2.6.17) |
| `<led>/max_brightness` | RO | integer; default 255 (`LED_FULL`), 1 if no levels | always | ABI What `max_brightness` (2.6.17) |
| `<led>/trigger` | RW | trigger name list; `none` removes, `default` selects the default trigger | always | ABI What `trigger` (2.6.17) |
| `<led>/inverted` | RW | 0/1; gpio and backlight triggers only | trigger-dependent | ABI What `inverted` (2.6.38) |
| `<led>/brightness_hw_changed` | RO | last hardware-set level; supports `poll()`; `ENODATA` before first change | only if driver detects hardware changes | ABI What `brightness_hw_changed` (4.11) |
| `<led>/multi_intensity` | RW | array of per-color intensities | multicolor LEDs only | ABI `sysfs-class-led-multicolor` (5.9) |
| `<led>/multi_index` | RO | color order array matching `multi_intensity` | multicolor LEDs only | ABI `sysfs-class-led-multicolor` (5.9) |
| `<led>/flash_*`, `<led>/pattern`, `<led>` trigger params | RW | see per-family ABI files | driver/trigger-dependent | `sysfs-class-led-flash`, `sysfs-class-led-trigger-*` |

Everything beyond the first five rows is conditional on driver, trigger, or class extension; none of it appears on a plain on/off LED.

## Safety and writes

Reads are always safe. Writing `brightness` needs write access to the file (typically root on a pre-udev-rule system; udev often grants the `video` or `input` group). Writing a trigger or a multicolor intensity changes what the LED indicates; a wrong `heartbeat` or `panic` trigger assignment is cosmetic, but patterns on embedded boards can double as status signalling (for example modem or panic LEDs), so treat writes as device policy.

## References

- `Documentation/ABI/testing/sysfs-class-led` (cached copy: 89 lines, 5 What: entries)
- `drivers/leds/led-class.c`, `drivers/leds/Makefile` (torvalds/linux master)
- `Documentation/leds/leds-class.rst` (naming scheme, per worklog 2-b)
- Ledger row SYSC-leds; worklog Task 2-b
