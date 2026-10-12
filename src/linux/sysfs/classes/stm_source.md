# /sys/class/stm_source

| Field | Value |
|---|---|
| Subsystem | System Trace Module core (kernel-side trace sources), `drivers/hwtracing/stm/` (same core object as the stm class: `obj-$(CONFIG_STM) += stm_core.o`, torvalds/linux master) |
| Config gate | `CONFIG_STM` (obj line verified against torvalds/linux master 2026; no separate stm_source Kconfig symbol found) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-stm_source` (1 What entry) |
| Since | 4.3 (the single documented entry, dated June 2015) |
| Live (5.10.134 host) | class absent: no `/sys/class/stm_source` directory |
| Ledger ID | SYSC-stm_source |

## What it represents

One directory per stm_source device -- the kernel-internal producers of
System Trace Protocol data (kernel drivers that want to emit trace data
through an STM device). A stm_source is created by kernel code, not by
userspace; its sysfs directory carries exactly one meaningful attribute,
`stm_source_link`, which is the wiring between producer and sink. Reading
it returns the name of the currently connected stm device, or the literal
string "<none>" if unconnected. Writing an existing (registered) stm
device's name connects that device; per the ABI text, if a device is
already connected to this stm_source, the write first disconnects it.
The ledger records exactly 1 documented path, matching the ABI file.

## Relationship to the device model

`/sys/class/stm_source/<stm_source>` is a class view over kernel-created
devices under `/sys/devices/...`. The pairing is by name, not by pointer:
the class here and the [stm](./stm.md) class there are joined by writing
the sink's name into `stm_source_link`. This is the reverse of the usual
class pattern -- the source devices represent software entities rather
than hardware, so their directory exists to hold the single link attribute
and nothing else. No bus, no char node, no policy objects are documented
on this side.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<stm_source>/stm_source_link` | RW | name of an existing registered stm device; reads return the connection or "<none>" | always | ABI testing `sysfs-class-stm_source` (4.3) |

## Safety and writes

A write retargets where this kernel producer's trace data goes; the ABI
documents the disconnect-first semantics on overwrite. Writing an unknown
device name is the obvious failure case, but the ABI text does not state
the error code, so none is claimed. No capability requirements are
documented. Reads are safe. With one attribute and no stated errors, the
safety story is short by construction -- the class has no other surface.

## References

- `Documentation/ABI/testing/sysfs-class-stm_source` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-stm_source)
- `drivers/hwtracing/stm/Makefile` (torvalds/linux master; fetched obj line)
- Ledger row SYSC-stm_source; `/sys/class/stm_source` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [stm](./stm.md)
