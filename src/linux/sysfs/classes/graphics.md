# /sys/class/graphics

| Field | Value |
|---|---|
| Subsystem | Framebuffer core; drivers/video/fbdev/core/fbmem.c (fb_class, fbmem_init) + fbsysfs.c (fb_device_create) + fbcon.c (fbcon device, fb_console_init) |
| Config gate | CONFIG_FB (fbmem.o, fbsysfs.o in fb-y); the fbcon device comes from fb_console_init() called by fbmem_init |
| ABI documentation | None (no What: entries in Documentation/ABI for /sys/class/graphics) |
| Since | Source-established; the class is the fb subsystem's sysfs home (fb_class = class_create("graphics")) |
| Live (5.10.134 host) | 1 entry: fbcon (no dev attribute; rotate = 0, cursor_blink = -1, rotate_all write-only) |
| Ledger ID | SYSC-graphics |

## What it represents

The framebuffer subsystem's class. It holds two populations: fbN devices
created by fb_device_create() for every registered framebuffer
(device_create_with_groups(fb_class, ..., "fb%d", node) with devt
MKDEV(FB_MAJOR=29, node)), and the fbcon device that fbcon.c creates once at
boot with MKDEV(0, 0), so it has no dev attribute and no /dev node. The
fbcon entry exposes the only sysfs-tunable console controls the fb layer
offers: cursor blinking and console rotation. This container registers no
framebuffer hardware (no fb0), so the class shows exactly the single fbcon
entry.

## Relationship to the device model

fb_class is created in fbmem_init() (fbmem.c) and passed by pointer to
fbsysfs.c and fbcon.c. Real framebuffers parent under their hardware device
and get the fbsysfs attribute set (bits_per_pixel, blank, console, cursor,
mode, modes, pan, virtual_size, name, stride, rotate, state, all 0644 except
name and stride which are 0444). fbcon is a parentless class device created
with
fbcon_device_groups; its three attributes are plain device attrs in
fbcon_device_attrs[]. /sys/class/tty/... handles the terminal side of the
console; this class handles the drawing side. /dev/fbN nodes (major 29) come
from the same fbN devices via devtmpfs.

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| fbcon/rotate | RW | rotation int: 0 = normal; live value 0 | fbcon.c DEVICE_ATTR_RW(rotate); live check (5.10.134) |
| fbcon/cursor_blink | RW | boolean-ish int; live value -1 (unset) | fbcon.c DEVICE_ATTR_RW(cursor_blink); live check |
| fbcon/rotate_all | WO | write triggers console-wide rotation | fbcon.c DEVICE_ATTR_WO(rotate_all); live perms --w------- |
| fb`<N>`/dev | RO | 29:`<N>` when a framebuffer exists | fbsysfs.c fb_device_create (FB_MAJOR 29); absent live |
| fb`<N>`/bits_per_pixel, blank, console, cursor, mode, modes, pan, virtual_size, rotate, state | RW | fb_info state mirrors, 0644 | fbsysfs.c fb_device_attrs[]; not present without an fb device |
| fb`<N>`/name, stride | RO | 0444 identity fields | fbsysfs.c fb_device_attrs[]; not present without an fb device |

The three fbcon attributes are the whole class-observable control set on
this host; everything else appears only with registered framebuffer
hardware.

## Safety and writes

cursor_blink and rotate change the live text console's rendering: rotation
rewrites console geometry for all users on that vt, rotate_all propagates it
to every console, and cursor_blink toggles blinking. Values outside the
accepted set are rejected by the store handlers. Writing is harmless to
graphics state beyond the console (no modeset), but on headless servers
without an fb device there is nothing here to tune at all. fbN files, when
present, follow the fbdev ioctl semantics mirrored in sysfs and can trigger
modesets; treat them as display-state files, not diagnostics.

## References

- drivers/video/fbdev/core/fbmem.c, fbsysfs.c, fbcon.c, fetched from raw.githubusercontent.com/torvalds/linux/master
- include/uapi/linux/major.h (FB_MAJOR 29)
- Live enumeration /sys/class/graphics/fbcon (values and permission bits, read-only, kernel 5.10.134)
- Sibling pages: [drm](./drm.md), [tty](./tty.md); coverage: [ledger](../ledger.md)
