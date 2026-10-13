# /sys/class/platform-profile

| Field | Value |
|---|---|
| Subsystem | platform profile class (firmware/EC performance modes), platform/x86 origin; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-platform-profile` (3 What entries); predecessor ACPI interface in `sysfs-platform_profile` |
| Since | March 2025, KernelVersion 6.14 (class entries); ACPI predecessor October 2020 |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/platform-profile |
| Ledger ID | SYSC-platform-profile |

## What it represents

One directory per platform-profile device, named `platform-profile-X`. A platform profile selects a platform-wide operating mode - low power, quiet, balanced, performance - implemented by firmware or an embedded controller. The class generalizes the older ACPI-only interface `/sys/firmware/acpi/platform_profile` (documented October 2020) so that multiple drivers, including non-ACPI ones, can register profile handlers.

## Relationship to the device model

Each `platform-profile-X` directory is a class device registered by a platform driver. The class is a aggregation point: when several drivers register, each gets its own directory, whereas the legacy ACPI interface exposed a single merged view under /sys/firmware/acpi. The profile names are standardized; the class file `choices` lists the subset the driver supports from that vocabulary.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `platform-profile-X/name` | RO | driver-given device name | always | ABI, 6.14 |
| `platform-profile-X/choices` | RO | space-separated standard profile names | always | ABI, 6.14 |
| `platform-profile-X/profile` | RW | one of the choices; pollable with POLLPRI on change | always | ABI, 6.14 |

The standard profile vocabulary (both ABI files): `low-power`, `cool`, `quiet`, `balanced`, `balanced-performance`, `performance`, plus in the class file `max-power` and `custom`. The class `profile` may also read back `custom` for a driver-defined mode.

## Safety and writes

Reading is safe. Writing `profile` changes the machine's performance/thermal/noise policy in firmware; the ABI allows polling the file for POLLPRI because profiles can also change asynchronously (hotkeys, EC decisions), so a writer should re-read rather than assume the written value stuck. On the legacy ACPI interface `custom` is read-only and only informational; the class file documents no such restriction. Root is the expected writer.

## References

- `Documentation/ABI/testing/sysfs-class-platform-profile` (cached copy)
- `Documentation/ABI/testing/sysfs-platform_profile` (ACPI predecessor, cached copy)
- Implementation: not in cached tree
- Sibling page: [power_supply](./power_supply.md); coverage: [ledger](../ledger.md)
- Live check: /sys/class/platform-profile absent (kernel 5.10.134, read-only enumeration)
