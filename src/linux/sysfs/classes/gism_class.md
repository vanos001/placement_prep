# /sys/class/gism_class

| Field | Value |
|---|---|
| Subsystem | "gism" driver class (vendor/vendor-specific; the name is only attested by the live host); implementation file not in cached tree and not identifiable from any cached source |
| Config gate | not verifiable: no cached Kconfig, Makefile, ABI file, or documentation mentions gism in any form (not verified) |
| ABI documentation | none found in tree -- `rg -i gism` over Documentation/ABI/stable, testing, obsolete, removed returns no files, and the class is absent from upstream kernel documentation in the cached tree |
| Since | unknown; no source states it |
| Live (5.10.134 host) | class present with 1 device: `/sys/class/gism_class/gism` -> `../../devices/virtual/gism_class/gism` |
| Ledger ID | SYSC-gism_class |

## What it represents

A live-only, source-limited page: the host runs a kernel (5.10.134-013.15.kangaroo.al8.x86_64, an Alibaba/Yahoo7 style vendor build per the host naming in the cached enumeration) that ships a `gism` driver creating a virtual class `gism_class` with exactly one device named `gism`. The class name and device name are the only identifiers available; nothing in the cached kernel documentation, ABI tree, or fetched sources describes what the driver does or what its character device is for. This page therefore documents exactly what is observable on the host and nothing more.

## Relationship to the device model

The device is a virtual device: the class symlink resolves to `/sys/devices/virtual/gism_class/gism`, i.e. a device under the `/sys/devices/virtual` tree with no bus and no physical parent. Its `uevent` file declares a character device: `MAJOR=247`, `MINOR=0`, `DEVNAME=gism`. There is no `driver` symlink on the device and no modalias, consistent with a virtual device registered directly by its driver. The `subsystem` symlink points back to `/sys/class/gism_class`. No `/dev/gism` node exists in the container's `/dev` (checked; node creation may depend on udev on the real host).

## Attributes

All entries below are from read-only inspection of `/sys/class/gism_class/gism/` on the host (2026-10-12 snapshot of live-sys); the device carries only standard device-core attributes.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `dev` | RO | "247:0" (major:minor) | always | live listing of `/sys/class/gism_class/gism/` |
| `uevent` | RW (standard) | `MAJOR=247`, `MINOR=0`, `DEVNAME=gism` | always | live listing, file content read |
| `subsystem` | RO (symlink) | points to `../../../../class/gism_class` | always | live listing |
| `power/` | dir | standard runtime PM group: autosuspend_delay_ms, control, runtime_active_kids, runtime_active_time, runtime_enabled, runtime_status, runtime_suspended_time, runtime_usage | always | live listing of `power/` |

## Safety and writes

No driver-specific attributes exist to write; the only writable standard files are `uevent` and the `power/` runtime-PM knobs, whose semantics belong to the device core. Nothing in the cached sources suggests what the gism char device (247:0) does, so opening it should be treated as untrusted/unknown -- that caution is procedural, not source-based. Class marked source-limited: 0 documented attributes from upstream, 4 standard entries from the live listing.

## References

- `source-cache/live-sys/class-list.txt`, row `gism_class	1`
- Direct read-only inspection of `/sys/class/gism_class/` and `/sys/devices/virtual/gism_class/gism/` (dev, uevent, power/, subsystem symlink)
- `Documentation/ABI/` search for `gism`: 0 matches (negative evidence)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-gism_class (status: live@5.10.134, 0 documented attributes)
