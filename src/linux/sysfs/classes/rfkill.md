# /sys/class/rfkill

| Field | Value |
|---|---|
| Subsystem | rfkill core, `net/rfkill/` (`obj-$(CONFIG_RFKILL) += rfkill.o`; RFKILL_INPUT input filter `rfkill-$(CONFIG_RFKILL_INPUT) += input.o`, torvalds/linux master) |
| Config gate | `CONFIG_RFKILL` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/stable/sysfs-class-rfkill` (7 What entries); the old `claim` knob is documented as removed in `Documentation/ABI/removed/sysfs-class-rfkill` |
| Since | 2.6.22 (class dir, `name`, `type`, `persistent`, `state`); 2.6.34 (`hard`, `soft`) |
| Live (5.10.134 host) | class absent: no `/sys/class/rfkill` directory, no radio transmitter registered |
| Ledger ID | SYSC-rfkill |

## What it represents

One directory per RF transmitter kill switch, `rfkill<N>`, each representing
a radio (wlan, bluetooth, wwan, ...) whose power state must be controllable
independently of its driver. Two block kinds are distinguished: *soft* block
(software asks the driver to turn the transmitter off) and *hard* block
(something outside the driver's control -- a hardware switch or firmware --
forces it off). The composite `state` file (0 soft-blocked, 1 unblocked,
2 hard-blocked) predates that split: the stable ABI itself says it was
scheduled for removal in 2014 but kept for its users, and recommends the
newer `hard`/`soft` pair because `state` cannot express "soft and hard
block" simultaneously. Types come from `include/linux/rfkill.h` (host
header present, also the uapi for the `/dev/rfkill` event interface with
`struct rfkill_event` / `rfkill_event_ext`).

## Relationship to the device model

`/sys/class/rfkill/rfkill[0-9]+` is a class view over a device under
`/sys/devices/...` (platform, USB, or PCI radio device). No rfkill bus
exists. The class is the only sysfs surface; the event/notification side
lives on the `/dev/rfkill` misc node, whose uapi is the same
`/usr/include/linux/rfkill.h` the `type` values point to. Sibling page:
[bluetooth](./bluetooth.md) (a bluetooth HCI device is one of the typical
rfkill-registered radios).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `rfkill[0-9]+/name` | RO | arbitrary string assigned by the driver | always | ABI stable `sysfs-class-rfkill` (2.6.22) |
| `rfkill[0-9]+/type` | RO | driver type string ("wlan", "bluetooth", etc; see include/linux/rfkill.h) | always | ABI stable `sysfs-class-rfkill` (2.6.22) |
| `rfkill[0-9]+/persistent` | RO | 0/1: soft-blocked state initialised from non-volatile storage at startup | always | ABI stable `sysfs-class-rfkill` (2.6.22) |
| `rfkill[0-9]+/state` | RO* | 0 soft-blocked, 1 unblocked, 2 hard-blocked; marked deprecated-in-place by its own ABI text | always | ABI stable `sysfs-class-rfkill` (2.6.22) |
| `rfkill[0-9]+/hard` | RO | 0/1 hard-block state | always | ABI stable `sysfs-class-rfkill` (2.6.34) |
| `rfkill[0-9]+/soft` | RW | 0/1 soft-block state | always | ABI stable `sysfs-class-rfkill` (2.6.34) |
| `rfkill[0-9]+/claim` | -- | deprecated claim knob; removed in 2016 | removed | ABI removed `sysfs-class-rfkill` |

The stable file does not mark `state` R/W explicitly beyond "Current state";
its own text steers writers to `soft`.

## Safety and writes

The only documented writable is `soft` (0/1): writing 1 software-blocks the
radio, an immediate effect on wireless connectivity. No capability
requirements are stated; distros gate the directory to root or plugdev-style
groups via udev. `hard` is read-only by definition -- a writer cannot clear
a block enforced outside the kernel. Reads are safe. The removed `claim`
file is a historical trap: old scripts writing it now get ENOENT.

## References

- `Documentation/ABI/stable/sysfs-class-rfkill`, `Documentation/ABI/removed/sysfs-class-rfkill` (cached copies; online: https://www.kernel.org/doc/Documentation/ABI/stable/sysfs-class-rfkill)
- `Documentation/driver-api/rfkill.rst` (referenced by both ABI files; not in sparse cache)
- `/usr/include/linux/rfkill.h` (host header: `rfkill_event`, `rfkill_event_ext`, `RFKILL_IOCTL_MAX_SIZE`)
- `net/rfkill/Makefile` (torvalds/linux master; fetched obj lines)
- Ledger row SYSC-rfkill; `/sys/class/rfkill` absent per `source-cache/live-sys/class-list.txt`
