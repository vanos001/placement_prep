# /sys/class/lcd

| Field | Value |
|---|---|
| Subsystem | LCD class (framebuffer-adjacent display control), `drivers/video/backlight/` (core object `lcd.o`: `obj-$(CONFIG_LCD_CLASS_DEVICE) += lcd.o`, torvalds/linux master) |
| Config gate | `CONFIG_LCD_CLASS_DEVICE` (obj line verified against torvalds/linux master 2026; same Makefile as the backlight class) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-lcd` (3 What entries) |
| Since | 2.6.12 (all three documented entries, dated April 2005) |
| Live (5.10.134 host) | class absent: no `/sys/class/lcd` directory, no LCD device registered |
| Ledger ID | SYSC-lcd |

## What it represents

One directory per LCD panel device, exposing power and contrast control. It
is the panel-side sibling of the backlight class: both live in
`drivers/video/backlight/`, both were introduced by the same April 2005
ABI entries, and both express power state through the `FB_BLANK_*` values
from `fb.h` rather than a dedicated enum. Where backlight controls the
illumination behind a panel, the lcd class controls the panel device itself
(power) and its contrast register (0 to `max_contrast`). The ABI is
deliberately tiny: three files, unchanged since 2.6.12. The ledger's 3
documented attributes match the ABI file exactly.

## Relationship to the device model

`/sys/class/lcd/<lcd>` is a class view over a device under
`/sys/devices/...`; LCD devices are registered by display drivers (the
master Makefile shows platform-specific drivers such as `corgi_lcd.o`,
`jornada720_lcd.o`, and `platform_lcd.o` building on the core). There is no
LCD bus and no char/block node -- the control path is purely sysfs, which is
why the class exists at all. Individual drivers register `lcd_device`
objects that appear here, in the same pattern as backlight devices.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<lcd>/lcd_power` | RW | `FB_BLANK_*` from fb.h: 0 (`FB_BLANK_UNBLANK`, power on), 4 (`FB_BLANK_POWERDOWN`, off) | always | ABI testing `sysfs-class-lcd` (2.6.12) |
| `<lcd>/contrast` | RW | current contrast, between 0 and `<lcd>/max_contrast` | always | ABI testing `sysfs-class-lcd` (2.6.12) |
| `<lcd>/max_contrast` | RO | maximum contrast for this LCD device | always | ABI testing `sysfs-class-lcd` (2.6.12) |

The ABI does not mark read/write explicitly; `max_contrast` is described as
a maximum (read-only in nature) while `lcd_power` and `contrast` are
described as "control" attributes, i.e. writable.

## Safety and writes

Writing `lcd_power` with 4 powers the panel off and 0 turns it back on --
an immediate, physical effect on the display. `contrast` writes are bounded
by `max_contrast`. No capability requirements are stated in the ABI, but
these are device-level writes normally reserved for root or udev-granted
permissions. Nothing is deprecated; the interface has been frozen since
2.6.12. See the sibling [backlight](./backlight.md) page for the
illumination-side controls and their users (systemd-backlight and friends).

## References

- `Documentation/ABI/testing/sysfs-class-lcd` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-lcd)
- `drivers/video/backlight/Makefile` (torvalds/linux master; fetched obj lines)
- Ledger row SYSC-lcd; `/sys/class/lcd` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [backlight](./backlight.md), [graphics](./graphics.md)
