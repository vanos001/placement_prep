# /sys/class/fc

| Field | Value |
|---|---|
| Subsystem | Fibre Channel transport udev interface (single pseudo device `fc_udev_device`); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: the ABI entry names no Kconfig symbol and no FC transport Kconfig is cached (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-fc` |
| Since | not stated in the ABI entry (dated Aug 2021) |
| Live (5.10.134 host) | class absent: no `fc` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-fc |

## What it represents

Not a per-device class: `/sys/class/fc` holds a single pseudo device directory, `fc_udev_device`, which carries one attribute, `appid_store`. The attribute is the write-side control point for the FC application identifier feature introduced in Aug 2021: it lets an admin attach an application identifier -- typically a UUID associated with an application or logical entity such as a virtual machine or container group -- to the blkcg of a cgroup. FC adapter drivers may query the identifier and tag FC traffic with it, so FC host and fabric entities can identify traffic sources. The class is therefore an admin/udev policy hook, not a fabric topology view (that role belongs to fc_host and fc_remote_ports).

## Relationship to the device model

`fc_udev_device` is a kernel-synthesized singleton, not a hardware device; the ABI gives it no parent description. It interacts with the block cgroup (blkcg) layer by cgroup inode, and with the FC transport's per-host/per-remote-port attributes only indirectly (drivers read the stored identifiers). The name `fc_udev_device` reflects its intended consumer: udev rules and storage management tools.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `fc_udev_device/appid_store` | WO | string `<cgroupid>:<appid>`; cgroupid = inode of the cgroup in hexadecimal, appid = up to 128 chars | always | ABI testing `sysfs-class-fc` |

Writing `<cgroupid>:` (empty appid) removes the identifier for that cgroup. A store for an already-tagged cgroup overrides the previous value. The ABI documents no readable form of the data.

## Safety and writes

This is a write-only admin interface; a write mutates per-cgroup FC traffic tagging state that fabric-side accounting then uses. Requires root (sysfs write permission plus, in practice, CAP_SYS_ADMIN-class privilege for the intended workflow -- capability requirement not verified from the cached tree). Errors are possible on malformed input (non-hex cgroupid, appid over 128 chars) although the ABI text does not specify error codes. Since removal requires an explicit overwrite with an empty appid, a forgotten mapping persists.

## References

- `Documentation/ABI/testing/sysfs-class-fc` (cached copy; single What: entry)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-fc)
- Companion pages: [fc_host](./fc_host.md), [fc_remote_ports](./fc_remote_ports.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-fc
