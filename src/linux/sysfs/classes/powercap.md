# /sys/class/powercap

| Field | Value |
|---|---|
| Subsystem | power capping subsystem (`Documentation/power/powercap/powercap.rst` named by the ABI file); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-powercap` (18 What entries) |
| Since | September 2013, KernelVersion 3.13 (all entries) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/powercap; `/usr/include/linux/powercap.h` not present on the host either |
| Ledger ID | SYSC-powercap |

## What it represents

The power cap class: control types, power zones and constraints. A control type (for example `intel-rapl`) determines how power is controlled and contains power zones - single devices or device collections that can be monitored and limited. Zones nest: a package zone may contain core and uncore child zones (ABI example path `intel-rapl:0:1:1`). Each zone exposes an energy counter, an optional power value, and numbered constraints with limits and time windows.

## Relationship to the device model

The tree is three levels deep by construction: `/sys/class/powercap/<control type>/<power zone>/<child power zone>`. Zone names qualified by control type (`intel-rapl:0:1:1`) identify position in the hierarchy. `enabled` exists at both control-type level (affects every zone using that type) and zone level (applies to the zone and its children), so enabling is hierarchical.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<control type>/enabled` | RW | 0/1 power capping enable for the type | control type | ABI, 3.13 |
| `<power zone>/name` | RO | zone name | zone | ABI, 3.13 |
| `<power zone>/energy_uj` | RW | micro-joules counter; write 0 resets; RO if not resettable | zone | ABI, 3.13 |
| `<power zone>/max_energy_range_uj` | RO | range of the energy counter, micro-joules | zone | ABI, 3.13 |
| `<power zone>/power_uw` | RO | current power, micro-watts | zone supporting power | ABI, 3.13 |
| `<power zone>/max_power_range_uw` | RO | range of the power value, micro-watts | zone supporting power | ABI, 3.13 |
| `<power zone>/enabled` | RW | 0/1; applies to zone and children | zone | ABI, 3.13 |
| `<zone>/constraint_X_name` | RO | optional constraint name, X = 0..max integer | constraint present | ABI, 3.13 |
| `<zone>/constraint_X_power_limit_uw` | RW | power limit in micro-watts over the X time window | constraint present | ABI, 3.13 |
| `<zone>/constraint_X_time_window_us` | RW | time window in micro-seconds | constraint present | ABI, 3.13 |
| `<control type>/.../constraint_X_max_power_uw` | RO | maximum allowed power, micro-watts | constraint present | ABI, 3.13 |
| `<control type>/.../constraint_X_min_power_uw` | RO | minimum allowed power, micro-watts | constraint present | ABI, 3.13 |
| `<zone>/constraint_X_max_time_window_us` | RO | maximum allowed time window | constraint present | ABI, 3.13 |
| `<zone>/constraint_X_min_time_window_us` | RO | minimum allowed time window | constraint present | ABI, 3.13 |

## Safety and writes

Reads are safe; energy_uj is the data source for power meters such as turbostat-style tools. Writes are the enforcement path: constraint power limits and time windows throttle real hardware immediately, and enabled toggles switch capping on or off for whole zones. energy_uj accepts the write 0 to reset the counter, but only where the hardware allows reset. Values are bounded by the min/max constraint files; out-of-range writes fail. This is power-plant-level policy - a wrong limit can slow every workload on the machine.

## References

- `Documentation/ABI/testing/sysfs-class-powercap` (cached copy; 18 What entries)
- `Documentation/power/powercap/powercap.rst` named by the ABI file; not in cached tree
- Host check: `/usr/include/linux/powercap.h` absent (verified), so no local uapi citation
- Sibling page: [power](./power.md); coverage: [ledger](../ledger.md)
- Live check: /sys/class/powercap absent (kernel 5.10.134, read-only enumeration)
