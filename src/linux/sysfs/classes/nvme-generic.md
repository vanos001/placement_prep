# /sys/class/nvme-generic

| Field | Value |
|---|---|
| Subsystem | NVMe host driver sibling class; implementation file not in cached tree |
| Config gate | not stated in cached sources (no drivers/Kconfig cached) |
| ABI documentation | none found in tree (no What: entry names /sys/class/nvme-generic in the cached Documentation) |
| Since | not stated in cached sources |
| Live (5.10.134 host) | class directory present, 0 devices (empty); nvme and nvme_core modules loaded |
| Ledger ID | SYSC-nvme-generic |

## What it represents

A sibling of [nvme](./nvme.md) for NVMe multipath views. The cached kernel
Documentation mentions the nvme-subsystem and nvme classes in
`Documentation/ABI/stable/sysfs-nvme` but never names nvme-generic, so this
page can only state what is verifiable: the class exists in the live kernel
enumeration, it is empty on this host (no NVMe devices in the container), and
the companion page [nvme](./nvme.md) records that sibling classes nvme-subsystem
and nvme-generic exist for multipath fabrics setups. What attribute files it
would carry per device cannot be cited from the cached tree.

## Relationship to the device model

The class directory `/sys/class/nvme-generic` exists on the 5.10.134 host but
contains no device directories and no attribute files to inspect. Unlike
nvme-subsystem, which has six documented attributes in sysfs-nvme
(model, serial, firmware_rev, subsysnqn, iopolicy, subsystype), nvme-generic
has no cached-tree documentation at all, so no device-model claims are made
here. The nvme and nvme_core modules are loaded on the host (seen in
/sys/module), which is consistent with the class directories being registered
even with zero devices.

## Attributes

No attribute is documented for this class in the cached sources; the table is
intentionally empty rather than filled from memory.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| (none citable) | -- | -- | -- | rg over cached linux-sparse tree: 0 matches for nvme-generic |

## Safety and writes

Nothing to read or write on this host: the class is empty. This page
deliberately reports no attribute semantics. For controller-level write
hazards (reset_controller, delete_controller and friends) see [nvme](./nvme.md);
per-namespace attributes belong to [block](./block.md). If a future host
exposes devices here, re-document from `Documentation/ABI/stable/sysfs-nvme`
or a newer ABI entry rather than from this page.

## References

- `Documentation/ABI/stable/sysfs-nvme` (cached; covers nvme and nvme-subsystem, not nvme-generic)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/stable/sysfs-nvme
- Live enumeration: /sys/class/nvme-generic (empty, read-only, kernel 5.10.134)
- Sibling pages: [nvme](./nvme.md), [block](./block.md); coverage: [ledger](../ledger.md)
