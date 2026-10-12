# /sys/class/thermal

| Field | Value |
|---|---|
| Subsystem | thermal core, `drivers/thermal/thermal_sysfs.c` (zone, cooling-device, stats attrs); class registered in `drivers/thermal/thermal_core.c` |
| Config gate | `CONFIG_THERMAL` (`obj-$(CONFIG_THERMAL) += thermal_sys.o` in `drivers/thermal/Makefile`, torvalds/linux master) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-thermal` |
| Since | not stated: the ABI file carries no `Date:` or `KernelVersion:` lines |
| Live (5.10.134 host) | class directory present, 0 thermal zones and 0 cooling devices (container) |
| Ledger ID | SYSC-thermal |

## What it represents

One `thermal_zoneX` directory per temperature sensor managed by the thermal framework, and one `cooling_deviceX` per controllable consumer of thermal state (fans, cpufreq cooling, devfreq cooling). A governor per zone reads the temperature, compares it with trip points, and throttles bound cooling devices. There is no separate `thermal_cooling` class in mainline: v5.10 and master `thermal_core.c` register a single class named `thermal`, so cooling devices live in this directory too.

## Relationship to the device model

`thermal_zoneX` and `cooling_deviceX` are class views over `/sys/devices/...` nodes created by zone drivers (ACPI, OF thermal, x86_pkg_temp, int340x, and so on). Each zone carries `cdevY` symlinks pointing at the cooling devices bound to it. No bus of its own and no `/sys/dev` char/block entry.

## Attributes

27 attribute paths are documented in `Documentation/ABI/testing/sysfs-class-thermal`. The table below is representative.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `thermal_zoneX/type` | RO | short lowercase string (for example `acpitz`) | no (required) | ABI What `thermal_zoneX/type` |
| `thermal_zoneX/temp` | RO | millidegree Celsius | no (required) | ABI What `thermal_zoneX/temp` |
| `thermal_zoneX/mode` | RW | `enabled`/`disabled` | optional | ABI What `thermal_zoneX/mode` |
| `thermal_zoneX/policy` | RW | governor name | required | ABI What `thermal_zoneX/policy` |
| `thermal_zoneX/available_policies` | RO | governor list | required | ABI What `available_policies` |
| `thermal_zoneX/trip_point_Y_temp` | RO | millidegree Celsius | per trip point | ABI What `trip_point_Y_temp` |
| `thermal_zoneX/trip_point_Y_type` | RO | `critical`, `hot`, `passive`, `active[0-*]` | per trip point | ABI What `trip_point_Y_type` |
| `thermal_zoneX/trip_point_Y_hyst` | RW | degrees Celsius (integer) | per trip point | ABI What `trip_point_Y_hyst` |
| `thermal_zoneX/cdevY` | RO | symlink to cooling device | per bound cdev | ABI What `thermal_zoneX/cdevY` |
| `thermal_zoneX/cdevY_weight` | RW | relative influence value | per bound cdev | ABI What `cdevY_weight` |
| `thermal_zoneX/emul_temp` | WO | millidegree Celsius; 0 disables emulation | debugging hook | ABI What `emul_temp` |
| `thermal_zoneX/sustainable_power` | RW | milliwatts (power allocator governor) | power allocator zones | ABI What `sustainable_power` |
| `cooling_deviceX/type` | RO | string (for example `Processor`, `Fan`) | no (required) | ABI What `cooling_deviceX/type` |
| `cooling_deviceX/cur_state` | RW | integer 0..`max_state` | no (required) | ABI What `cur_state` |
| `cooling_deviceX/max_state` | RO | integer | no (required) | ABI What `max_state` |
| `cooling_deviceX/stats/*` | RO/WO | `time_in_state_ms`, `trans_table`, `total_trans`, `reset` | stats support | ABI What `stats/*` entries |

The `k_pu`, `k_i`, `k_d`, `integral_cutoff`, `slope`, and `offset` attributes belong to power-allocator and hotspot-model zones and are optional.

## Safety and writes

`temp`, `type`, and trip points are safe to read. `cur_state` writes manually throttle hardware (set 0 for no cooling); on a CPU cooling device this is effectively a cpufreq clamp. `emul_temp` carries an explicit ABI warning: flooding it with low values disables kernel thermal policy, which can overheat a production system. `stats/reset` wipes cooling statistics. All writes need root.

## References

- `Documentation/ABI/testing/sysfs-class-thermal` (cached copy: 259 lines)
- `drivers/thermal/thermal_sysfs.c`, `drivers/thermal/thermal_core.c`, `drivers/thermal/Makefile` (v5.10 cross-check per worklog 2-b; master)
- `Documentation/driver-api/thermal/power_allocator.rst`
- Ledger row SYSC-thermal; worklog Task 2-b (no mainline `thermal_cooling` class)
