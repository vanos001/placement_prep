# /sys/class/uacce

| Field | Value |
|---|---|
| Subsystem | UACCE (Unified/User-space Access to Accelerators) framework; ABI contact linux-accelerators@lists.ozlabs.org; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached); the ABI references kernel header uacce.h for UACCE_DEV_xxx flags (not cached; no uacce.h in host /usr/include/linux) |
| ABI documentation | `Documentation/ABI/testing/sysfs-driver-uacce` (8 What: entries, file named sysfs-driver-uacce but paths are class paths) |
| Since | 5.7 (Feb 2020: api, flags, available_instances, algorithms, region_mmio_size, region_dus_size); isolate_strategy, isolate 6.1 (Nov 2022) |
| Live (5.10.134 host) | class absent: /sys/class/uacce does not exist in this container |
| Ledger ID | SYSC-uacce |

## What it represents

The sysfs view of queue-capable hardware accelerators registered with the
UACCE framework. One directory per device (dev_name) describes the device
for application matching: the api string identifies the driver family an
application should bind to, algorithms lists what the hardware can do, and
the region sizes describe the queue file mmap areas. Isolation attributes
(6.1) expose a hardware error threshold policy. The framework pairs with
per-device queue character devices; the ABI sysfs file documents only the
class side.

## Relationship to the device model

The class attributes are uniform across UACCE devices; driver specifics
stay behind the api/algorithms free-form strings ("Can be any string and up
to userspace to parse"). available_instances returns -ENODEV if the driver
does not provide the uacce_ops get_available_instances callback -- the only
driver-callback behavior the ABI names. Queue files and their mmio/dus
regions (the region_mmio_size/region_dus_size byte counts) are the mmap
interface; their layout is not documented in the cached tree.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| api | RO | driver-matching string, free-form | always | ABI testing sysfs-driver-uacce, 5.7 |
| flags | RO | device attributes, UACCE_DEV_xxx flags defined in uacce.h | always | ABI, 5.7 |
| available_instances | RO | instances left; -ENODEV if uacce_ops get_available_instances not provided | always | ABI, 5.7 |
| algorithms | RO | supported algorithms, one per line, free-form | always | ABI, 5.7 |
| region_mmio_size | RO | size (bytes) of the mmio region of the queue file | always | ABI, 5.7 |
| region_dus_size | RO | size (bytes) of the dus (device user space) region of the queue file | always | ABI, 5.7 |
| isolate_strategy | RW | error threshold per hour for hardware isolation; integer 0 (never isolate, default) to 65535 | 6.1 and later | ABI, 6.1 |
| isolate | RO | 1 device isolated/unavailable, 0 available | 6.1 and later | ABI, 6.1 |

## Safety and writes

Reads are safe. The only writable file is isolate_strategy, a policy knob:
it decides how many hardware errors within one hour trigger isolation, i.e.
taking the accelerator away from userspace. Writing larger values makes the
kernel tolerate more errors before isolating; 0 disables isolation. The
class is absent on the 5.10.134 host, so no live read was possible.

## References

- `Documentation/ABI/testing/sysfs-driver-uacce` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-driver-uacce
- sysfs-attrs.json entry `uacce` (8 paths, exactly the eight ABI entries)
- Host header check: /usr/include/linux/uacce.h absent (read-only ls)
- Live enumeration: class absent, kernel 5.10.134; coverage: [ledger](../ledger.md)
