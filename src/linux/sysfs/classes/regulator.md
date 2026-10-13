# /sys/class/regulator

| Field | Value |
|---|---|
| Subsystem | regulator core, `drivers/regulator/core.c` (`regulator_class`) |
| Config gate | `CONFIG_REGULATOR` (`obj-$(CONFIG_REGULATOR) += core.o ...` in `drivers/regulator/Makefile`, torvalds/linux master) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-regulator` |
| Since | 2.6.26 (most entries); 2.6.28 (`name`); 3.7 (`bypass`); 5.18 (fault and warning flags) |
| Live (5.10.134 host) | class absent: no regulator registered in the container |
| Ledger ID | SYSC-regulator |

## What it represents

One directory per voltage or current regulator registered with the regulator framework (PMIC rails, LDOs, DC-DC converters, fixed supplies). The interface is deliberately a read-only status and constraint report: consumers control regulators through the kernel API (`regulator_enable()`, constraints from machine description), and sysfs shows what was configured. The ABI spells directories as `/sys/class/regulator/.../`; each holds the attributes its hardware can report.

## Relationship to the device model

Each regulator entry is a class view of a device under `/sys/devices/...` (usually an i2c/spi PMIC or a fixed-voltage platform device). The `parent` attribute is a symlink to the supplying regulator, expressing the supply tree. No regulator bus and no char/block node exist; the `num_users` count reflects in-kernel consumers that called `regulator_enable()`.

## Attributes

33 What: entries are documented in `Documentation/ABI/testing/sysfs-class-regulator`; the table below is representative.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `name` | RO | display string; empty if driver provides none | always (2.6.28) | ABI What `name` |
| `state` | RO | `enabled`, `disabled`, `unknown` | reporting regulators | ABI What `state` (2.6.26) |
| `status` | RO | `off`, `on`, `error`, `fast`, `normal`, `idle`, `standby` | reporting regulators | ABI What `status` |
| `type` | RO | `voltage`, `current`, `unknown` | always | ABI What `type` (2.6.26) |
| `microvolts` | RO | configured output voltage, E-6 volts | voltage regulators | ABI What `microvolts` |
| `microamps` | RO | configured current limit, E-6 amps | current regulators | ABI What `microamps` |
| `opmode` | RO | `fast`, `normal`, `idle`, `standby`, `unknown` | reporting regulators | ABI What `opmode` |
| `min_microvolts` / `max_microvolts` | RO | constraint values; `constraint not defined` if unset | constrained supplies | ABI What entries |
| `num_users` | RO | consumers that called `regulator_enable()` | always | ABI What `num_users` |
| `requested_microamps` | RO | summed load request, microamps | current reporting | ABI What `requested_microamps` |
| `parent` | RO | symlink to supplying regulator | if a supply exists | ABI What `parent` |
| `bypass` | RO | `enabled`/`disabled`/`unknown` | bypass-capable regulators | ABI What `bypass` (3.7) |
| `under_voltage`, `over_current`, `over_temp`, `fail`, ... `_warn` variants | RO | 0/1 fault and warning flags | fault-reporting regulators | ABI What entries (5.18) |
| `suspend_mem_microvolts`, `suspend_disk_state`, and siblings | RO | per-sleep-state configuration | suspend constraints | ABI What entries (2.6.26, May 2008) |

The ABI notes `microvolts`/`microamps`/`opmode` report the configuration regardless of enable state; use `state`/`status` for the actual output condition.

## Safety and writes

Everything is a read; the ABI documents no write semantics, and the class exists so userspace can observe regulator state, not drive it. Reads are safe and cheap. Changing rails belongs to kernel consumers with machine-level constraints; ad-hoc sysfs writes are not part of this interface.

## References

- `Documentation/ABI/testing/sysfs-class-regulator` (cached copy: 453 lines, 33 What: entries)
- `drivers/regulator/core.c`, `drivers/regulator/Makefile`, `include/linux/regulator/consumer.h` (torvalds/linux master)
- Ledger row SYSC-regulator; worklog Task 2-b (read-only interface characterization)
