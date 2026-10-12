# sysfs Class Encyclopedia

This section documents the `/sys/class/*` tree one class per page. The set of
classes is **not fixed**: it depends on kernel version, configuration, loaded
drivers, and hardware. Pages therefore distinguish three things that must
never be blurred:

1. **What the kernel guarantees** — attributes documented in
   `Documentation/ABI/` (`What:` lines) or created unconditionally by a
   subsystem core file.
2. **What the driver may add** — per-driver attributes, version- and
   config-dependent, documented only where a source names them.
3. **What a live host shows** — read-only enumeration results, stamped with
   the host kernel (5.10.134 container) and flagged wherever visibility
   differs from bare metal.

## Inventory

The [coverage ledger](./ledger.md) tracks 120 classes: 46 observed live on the
cached host, 94 with ABI documentation (overlapping sets), plus non-class
prefixes (`/sys/devices`, `/sys/bus`, `/sys/module`, `/sys/kernel`, `/sys/fs`,
`/sys/dev`) recorded separately so they are never misfiled as classes. Statuses
after the wave-2 pass: 42 documented, 77 researched, 1 source-limited.

## Pages

Per-class pages live under `classes/<class>.md` and follow the same nine-point
template: class name and `/sys/class/` path; owning kernel subsystem; the
class ↔ `/sys/devices/` ↔ `/sys/bus/` ↔ `/sys/dev/` relationship; typical
attributes and symlinks (with R/W, units, format, conditional presence);
configuration/hardware/capability/version dependencies; safe inspection
commands and write warnings; and primary references (ABI doc, subsystem
source, kernel doc — named per claim).

## Adjacent trees — classified, not conflated

- `/sys/devices/` — the actual device hierarchy; class dirs are views over it.
- `/sys/bus/<bus>/` — bus-specific device/driver binding views.
- `/sys/dev/char` and `/sys/dev/block` — major:minor lookup views.
- `/sys/module/<mod>/parameters` — module params (not class attributes).
- `/sys/kernel/`, `/sys/fs/` — kernel-internal and filesystem mounts.
- device-tree nodes (`/proc/device-tree`, sysfs fwnode links) — firmware
  views, cross-referenced but never listed as classes.
- `/proc/*` and `/dev/*` nodes — procfs interfaces and device nodes,
  systematically separated from sysfs attributes in every page.
