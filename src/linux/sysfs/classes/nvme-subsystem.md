# /sys/class/nvme-subsystem

| Field | Value |
|---|---|
| Subsystem | NVMe host driver; sibling of [nvme](./nvme.md) (nvme.md cites drivers/nvme/host/core.c from master; implementation file not in cached tree) |
| Config gate | CONFIG_NVME_MULTIPATH stated in ABI for iopolicy; class-level gate not stated in cached tree |
| ABI documentation | `Documentation/ABI/stable/sysfs-nvme` (six class-level What: entries at /sys/class/nvme-subsystem/) |
| Since | 4.15 (model, serial, firmware_rev, subsysnqn); iopolicy 5.1; subsystype 5.16 |
| Live (5.10.134 host) | class directory present, 0 devices (empty); no live value reads possible |
| Ledger ID | SYSC-nvme-subsystem |

## What it represents

One directory per NVMe subsystem (nvme-subsysX) rather than per controller.
A subsystem is the NVMe-level object that controllers connect to; with
multipath fabrics several controllers can serve the same subsystem, so the
identity attributes (model, serial, firmware_rev, subsysnqn) live here once,
while per-controller state stays in [nvme](./nvme.md). Per-namespace files
remain on the block devices covered by [block](./block.md).

## Relationship to the device model

sysfs-nvme documents this class in the same file as /sys/class/nvme/nvmeX/
and /sys/block/nvmeXnY/, i.e. one ABI surface over three sysfs views. The
class appears when the NVMe core has subsystems to expose; on this container
the directory is present with zero entries. The iopolicy entry states the
only Kconfig dependency in the cached text: it exists "Only available when
CONFIG_NVME_MULTIPATH is enabled".

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| model, serial, firmware_rev, subsysnqn | RO | identify strings and subsystem NQN of the NVMe subsystem | always | ABI stable sysfs-nvme, 4.15 |
| iopolicy | RW | multipath I/O path selection: "numa", "round-robin", "queue-depth"; changing it clears all current path selections | CONFIG_NVME_MULTIPATH | ABI stable sysfs-nvme, 5.1 |
| subsystype | RO | subsystem type: "discovery", "nvm", "reserved" | always | ABI stable sysfs-nvme, 5.16 |

The sysfs-attrs.json cache lists exactly these six paths for the class.

## Safety and writes

Reads are safe. The one writable file is iopolicy: it changes path selection
for live multipath I/O and, per the ABI, clearing current path selections
affects in-flight I/O on storage a mounted filesystem may be using. On the
5.10.134 host there is nothing to read or write (0 subsystems); permission
bits and value examples are unknown here and are not reported.

## References

- `Documentation/ABI/stable/sysfs-nvme` lines 425-453 (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/stable/sysfs-nvme
- sysfs-attrs.json entry `nvme-subsystem` (6 paths)
- Live enumeration: /sys/class/nvme-subsystem (empty, read-only, kernel 5.10.134)
- Sibling pages: [nvme](./nvme.md), [nvme-generic](./nvme-generic.md), [block](./block.md); coverage: [ledger](../ledger.md)
