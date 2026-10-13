# /sys/class/backlight

| Field | Value |
|---|---|
| Subsystem | backlight class, `drivers/video/backlight/backlight.c` (core DEVICE_ATTR block) |
| Config gate | `CONFIG_BACKLIGHT_CLASS_DEVICE` (`obj-$(CONFIG_BACKLIGHT_CLASS_DEVICE) += backlight.o` in `drivers/video/backlight/Makefile`, torvalds/linux master) |
| ABI documentation | `Documentation/ABI/stable/sysfs-class-backlight` (5 core entries) plus `Documentation/ABI/testing/sysfs-class-backlight` (`scale`, ADP-driver attributes) |
| Since | 2.6.12 (`bl_power`, `brightness`, `max_brightness`); 2.6.17 (`actual_brightness`); 2.6.37 (`type`); 5.4 (`scale`) |
| Live (5.10.134 host) | class directory present, 0 devices (headless container) |
| Ledger ID | SYSC-backlight |

## What it represents

One directory per panel backlight, exposing brightness control to userspace tools such as `brightnessctl` and `systemd-backlight`. Each entry carries a `type` describing the control interface so userspace can prefer firmware interfaces over raw register control when several exist (stable ABI `type` entry). The stable ABI file lists `Users: HAL`, a hint at its desktop-stack age.

## Relationship to the device model

`/sys/class/backlight/<backlight>` is a class view over `/sys/devices/...` (firmware, platform, or DRM-registered device). There is no backlight bus and no char/block node; the control path is purely sysfs. The class name inside `backlight.c` is the registration point; individual drivers register `backlight_device` objects that appear here.

## Attributes

The stable ABI file documents 5 core attributes and the testing file adds `scale` plus driver-specific ADP entries; 16 What: paths spelling `/sys/class/backlight/...` exist across the ABI tree (the ledger records 15 as the class-level count). The table below is representative.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `brightness` | RW | 0..`max_brightness`; reads back the stored level, which may differ from hardware | always | stable ABI What `brightness` (2.6.12) |
| `max_brightness` | RO | integer | always | stable ABI What `max_brightness` (2.6.12) |
| `actual_brightness` | RO | queried hardware level; may differ from `brightness` | always | stable ABI What `actual_brightness` (2.6.17) |
| `bl_power` | RW | `FB_BLANK_*` values: 0 unblank, 4 powerdown | always | stable ABI What `bl_power` (2.6.12) |
| `type` | RO | `firmware`, `platform`, or `raw` | always | stable ABI What `type` (2.6.37) |
| `scale` | RO | `unknown`, `linear`, `non-linear`; guides how UIs should map a slider | core attr, 5.4 | testing ABI What `scale` |
| `ambient_light_level`, `ambient_light_zone`, `<zone>_max`, `<zone>_dim` | RO/RW | ADP8860/ADP8870/ADP5520 ambient-light zones, 0..127 | driver-specific (Analog Devices ADP*) | testing ABI What entries (2.6.32/2.6.35) |

Only `brightness`, `max_brightness`, `actual_brightness`, `bl_power`, `type`, and `scale` come from the class core; anything else visible in a directory is driver-specific.

## Safety and writes

Reading is safe. Writing `brightness` (0..max) and `bl_power` needs root or appropriate udev permissions; these writes change panel illumination and, on some firmware interfaces, talk to the embedded controller. `bl_power` 4 blanks the panel entirely. Because `brightness` stores a value that may not match hardware, userspace is told to use `actual_brightness` only for display, not for decisions (stable ABI text).

## References

- `Documentation/ABI/stable/sysfs-class-backlight`, `Documentation/ABI/testing/sysfs-class-backlight` (cached copies)
- `drivers/video/backlight/backlight.c`, `drivers/video/backlight/Makefile` (torvalds/linux master; core attr block per worklog 2-b)
- Ledger row SYSC-backlight; worklog Task 2-b
