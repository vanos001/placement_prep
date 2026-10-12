# /sys/class/stm

| Field | Value |
|---|---|
| Subsystem | System Trace Module core (hardware tracing), `drivers/hwtracing/stm/` (`obj-$(CONFIG_STM) += stm_core.o`, torvalds/linux master) |
| Config gate | `CONFIG_STM` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-stm` (3 What entries) |
| Since | 4.3 (`masters`, `channels`); 4.7 (`hw_override`) |
| Live (5.10.134 host) | class absent: no `/sys/class/stm` directory, no STM device registered |
| Ledger ID | SYSC-stm |

## What it represents

One directory per STM (System Trace Module) device -- tracing hardware that
emits System Trace Protocol (STP) streams. The class exposes the device's
master/channel namespace geometry as three read-only facts: `masters` shows the
first and last master numbers available to software on the device,
`channels` shows how many channels each master gets, and `hw_override`
tells whether the hardware silently rewrites software-assigned master
numbers in the produced STP stream (1) or leaves them as assigned (0).
That is the whole documented surface: the class is the discovery metadata
for the STP stream layout, while trace data itself flows through char
policy devices (`/dev/stm*`, policy via `configfs-stp-policy*`, not in this
class and not documented in the cached ABI for this class).

## Relationship to the device model

`/sys/class/stm/<stm>` is a class view over STM hardware devices under
`/sys/devices/...` (e.g. Intel TH / Coresight STM hardware). Writers of
trace data reach the device through the STM policy/char-device layer; this
class directory is read-only metadata consumed by tools that need to lay
out master/channel assignments before writing. The sibling class
[stm_source](./stm_source.md) covers the kernel-side producers that link
into an STM device by name. No STM bus exists in sysfs terms.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<stm>/masters` | RO | first and last available-to-software master numbers on this device | always | ABI testing `sysfs-class-stm` (4.3) |
| `<stm>/channels` | RO | number of channels per master | always | ABI testing `sysfs-class-stm` (4.3) |
| `<stm>/hw_override` | RO | 0: software master numbers appear in the STP stream; 1: hardware overrides them | always | ABI testing `sysfs-class-stm` (4.7) |

The ledger records exactly these 3 paths; no other STM class attribute is
documented in the tree.

## Safety and writes

All three documented attributes are read-only and safe. The ABI defines no
writable attribute, no error conventions, and no capability requirements
for the class; all configuration happens through the policy layer outside
this class, which the cached sources do not cover.

## References

- `Documentation/ABI/testing/sysfs-class-stm` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-stm)
- `drivers/hwtracing/stm/Makefile` (torvalds/linux master; fetched obj line)
- `Documentation/ABI/testing/configfs-stp-policy`, `configfs-stp-policy-p_sys-t` (cached; related configfs policy interfaces)
- Ledger row SYSC-stm; `/sys/class/stm` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [stm_source](./stm_source.md)
