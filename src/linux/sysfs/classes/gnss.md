# /sys/class/gnss

| Field | Value |
|---|---|
| Subsystem | GNSS receiver core, `drivers/gnss/` (core object `gnss.o`: `obj-$(CONFIG_GNSS) += gnss.o` in `drivers/gnss/Makefile`, torvalds/linux master) |
| Config gate | `CONFIG_GNSS` (obj line verified against torvalds/linux master 2026; the sparse cache holds no driver tree) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-gnss` (a single What entry: the `type` attribute) |
| Since | 4.18 (KernelVersion of the only documented entry, dated May 2018) |
| Live (5.10.134 host) | class absent: no `/sys/class/gnss` directory, no receiver registered in the container |
| Ledger ID | SYSC-gnss |

## What it represents

One directory per GNSS receiver, named `gnss<N>`. The class abstracts the
receiver vendor behind a common kernel object so that userspace can consume
position data without caring which protocol the hardware speaks; the
documented `type` attribute reflects the protocol(s) the receiver supports:
"NMEA" (NMEA 0183), "SiRF" (SiRF Binary), or "UBX" (u-blox UBX). The ABI
notes that even non-"NMEA" receivers typically still accept a subset of
NMEA 0183 with vendor extensions, for example to switch into the vendor
binary protocol. The cached tree documents nothing else for this class; the
ledger likewise carries exactly 1 documented attribute.

## Relationship to the device model

`/sys/class/gnss/gnss<N>` is a class view over a device below
`/sys/devices/...` (serial/USB receivers attach through the corresponding
bus device). No GNSS-specific bus exists; the class is the only sysfs view,
and receiver I/O is expected to flow through the usual character-device
plumbing rather than through sysfs attributes. Because the class exposes no
control plane beyond `type`, the device-model story is the standard one:
subsystem symlink, `uevent`, device link, and whatever power attributes the
parent device carries.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `gnss<N>/type` | RO | `"NMEA"`, `"SiRF"`, `"UBX"` -- protocol(s) supported by the receiver | always | ABI testing `sysfs-class-gnss` (4.18) |

Only `type` is documented anywhere in the tree. Any other file seen in a
`gnss<N>` directory would be a generic class-device attribute (`uevent`,
`dev`, power), not part of a documented GNSS ABI.

## Safety and writes

Nothing in the documented ABI is writable and nothing has stated capability
requirements: `type` is a plain read. No warnings, deprecations, or error
conventions are recorded in the ABI entry. Given the single-attribute
surface, the practical safety story is that sysfs here is read-only
introspection; any receiver interaction (sending commands, changing baud
rates) happens outside this class and is not documented in the cached
sources.

## References

- `Documentation/ABI/testing/sysfs-class-gnss` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-gnss)
- `drivers/gnss/Makefile` (torvalds/linux master; fetched obj-$(CONFIG_GNSS) line)
- Ledger row SYSC-gnss; `/sys/class/gnss` absent on the 5.10.134 host per `source-cache/live-sys/class-list.txt`
- Sibling pages: [tty](./tty.md) (serial receivers), [input](./input.md)
