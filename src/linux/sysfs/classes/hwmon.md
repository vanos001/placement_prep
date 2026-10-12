# /sys/class/hwmon

| Field | Value |
|---|---|
| Subsystem | hardware monitoring (hwmon) core, `drivers/hwmon/hwmon.c` |
| Config gate | `CONFIG_HWMON` (`obj-$(CONFIG_HWMON) += hwmon.o` in `drivers/hwmon/Makefile`, torvalds/linux master) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-hwmon` |
| Since | not stated: the ABI file carries no `KernelVersion:` lines (What: entries only) |
| Live (5.10.134 host) | class directory present, 0 devices (no sensor chip driver bound in the container) |
| Ledger ID | SYSC-hwmon |

## What it represents

One directory per hardware monitoring chip registered with the hwmon core: voltage, temperature, fan, current, power, energy, and humidity sensors plus fan-speed (PWM) controls. Chip drivers register a `hwmon` device; the core creates `hwmonX` entries and forwards attribute names to the driver. This is the interface `sensors` (lm-sensors) and `fancontrol` read.

## Relationship to the device model

`/sys/class/hwmon/hwmonX` is a class view of a device that also lives under `/sys/devices/...` (the `device` link inside `hwmonX` points at the parent, typically an i2c or platform device). There is no bus of its own and no `/sys/dev` entry: hwmon devices carry no major:minor. The legacy per-driver sysfs layout is described in `Documentation/hwmon/sysfs-interface.rst`, which the class ABI mirrors.

## Attributes

120 attribute paths spell `/sys/class/hwmon/...` in What: lines across the ABI tree (119 of them in `sysfs-class-hwmon` itself, 1 in a driver ABI file); the sysfs-attrs.json cross-check and the ledger both record 120. The table below is representative.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `hwmonX/name` | RO | short lowercase chip name; only mandatory attribute | no | ABI What `hwmonX/name` |
| `hwmonX/label` | RO | free-form text | driver-dependent | ABI What `hwmonX/label` |
| `hwmonX/update_interval` | RW | milliseconds | driver-dependent | ABI What `hwmonX/update_interval` |
| `hwmonX/tempY_input` | RO | millidegree Celsius | per channel Y | ABI What `tempY_input` |
| `hwmonX/tempY_max` | RW | millidegree Celsius | per channel | ABI What `tempY_max` |
| `hwmonX/tempY_max_alarm` | RO | 0/1 flag | per channel | ABI What `tempY_max_alarm` |
| `hwmonX/fanY_input` | RO | revolution/min (RPM) | per channel | ABI What `fanY_input` |
| `hwmonX/fanY_fault` | RO | 0/1 flag | per channel | ABI What `fanY_fault` |
| `hwmonX/pwmY` | RW | 0-255 (255 = 100%) | fan-control chips | ABI What `pwmY` |
| `hwmonX/pwmY_enable` | RW | 0 none, 1 manual, 2+ automatic | fan-control chips | ABI What `pwmY_enable` |
| `hwmonX/inY_input` | RO | millivolt (board scaling not applied) | per channel | ABI What `inY_input` |
| `hwmonX/currY_input` | RO | milliampere | per channel | ABI What `currY_input` |
| `hwmonX/powerY_input` | RO | microWatt; `energyY_input` is microJoule | per channel | ABI What `powerY_input`, `energyY_input` |
| `hwmonX/humidityY_input` | RO | milli-percent (per cent mille) | per channel | ABI What `humidityY_input` |
| `hwmonX/intrusionY_alarm` | RW | 0/1; sticks until cleared by writing 0 | chassis intrusion support | ABI What `intrusionY_alarm` |

Channel numbering (`Y`) and the subset present are driver-specific; limits, alarms, `_enable`, `_label`, and rated/history variants follow the same per-family naming. Live values were not sampled: the host has no hwmon device.

## Safety and writes

All readings are safe to read as any user. Writes (limits, `pwmY`, `*_enable`, history resets) affect sensor policy or fan control and need root; writing a wrong `pwmY_enable` mode can force fans to full speed or hand control to the chip. Alarm flags other than `intrusionY_alarm` clear on read; the intrusion flag persists until explicitly cleared. `powerY_cap` and friends state that the system reacts when limits are crossed, so treat them as safety-critical configuration, not telemetry.

## References

- `Documentation/ABI/testing/sysfs-class-hwmon` (cached copy: 1089 lines, What: inventory)
- `drivers/hwmon/hwmon.c`, `drivers/hwmon/Makefile` (torvalds/linux master)
- `Documentation/hwmon/sysfs-interface.rst`
- Ledger row SYSC-hwmon (`src/linux/sysfs/ledger.md`); prior research: worklog Task 2-b
