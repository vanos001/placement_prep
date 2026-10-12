# /sys/class/power_supply

| Field | Value |
|---|---|
| Subsystem | power supply class, `drivers/power/supply/power_supply_sysfs.c` (attribute table, uevent properties); core in `power_supply_core.c` |
| Config gate | `CONFIG_POWER_SUPPLY` (`obj-$(CONFIG_POWER_SUPPLY) += power_supply.o` in `drivers/power/supply/Makefile`, torvalds/linux master) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-power` |
| Since | per-entry `Date:` lines start May 2007; 13 entries carry `KernelVersion:` lines (earliest 2.6.35) |
| Live (5.10.134 host) | class directory present, 0 devices (container without battery/AC entries) |
| Ledger ID | SYSC-power_supply |

## What it represents

One directory per power supply object: batteries, AC adapters, USB and wireless chargers, fuel gauges. Each device exposes a flat set of property files whose availability mirrors the `POWER_SUPPLY_*` properties the driver reports. The same properties are exported in the device `uevent` as `POWER_SUPPLY_*` variables (worklog 2-b: `add_uevent_var` in `power_supply_sysfs.c`), which is what udev and desktop power daemons consume.

## Relationship to the device model

`/sys/class/power_supply/<supply>` is a class symlink view of a device under `/sys/devices/...` (ACPI battery, platform charger, USB port device). There is no power_supply bus and no char/block device node. The `type` and `scope` files let userspace classify the supply without probing drivers.

## Attributes

59 What: entries live in `Documentation/ABI/testing/sysfs-class-power`; counting every path spelled `/sys/class/power_supply/...` across the ABI tree (including driver-specific files such as `sysfs-class-power-max1720x`) gives 82, the number the ledger records. The table below is representative.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `type` | RO | `Battery`, `UPS`, `Mains`, `USB`, `Wireless` | always | ABI What `<supply_name>/type` |
| `manufacturer`, `model_name` | RO | string | driver-dependent | ABI What entries, May 2007 |
| `serial_number` | RO | string | driver-dependent | ABI What entry, January 2008 |
| `temp` | RO | 1/10 degrees Celsius | battery or charger reporting | ABI What `temp` |
| `voltage_now` | RO (RW on programmable USB) | microvolts | always for batteries | ABI What `voltage_now` |
| `current_now` | RO (RW on programmable USB) | microamps; negative while discharging | battery or charger reporting | ABI What `current_now` |
| `capacity` | RO | 0-100 percent | batteries | ABI What `capacity` |
| `health` | RO | enum string | batteries | ABI What `health` |
| `status` | RO | enum (`Charging`, `Discharging`, `Full`, ...) | driver-dependent | ABI What `status` (enum text from `POWER_SUPPLY_STATUS_TEXT`) |
| `cycle_count` | RO | integer | batteries with gauge | ABI What `cycle_count` |
| `uevent` | RO | `POWER_SUPPLY_*` key list | always | `power_supply_sysfs.c` (worklog 2-b) |

Which files exist is decided by each driver: a mains adapter may expose only `online` and `type`, a smart battery dozens of charge/discharge and capacity-level files. Driver-specific extensions are documented in their own ABI files (`sysfs-class-power-*`).

## Safety and writes

Reading is safe; this is the data source of `upower`, `acpi`, and desktop battery indicators. Writes are rare and driver-gated: the ABI marks `current_now`/`voltage_now` writable only when the supply's `online` state is programmable (USB VBUS/IBUS control). Charge-control attributes (for example charge behaviour and current limits in driver-specific files) need root and can stop or alter charging; treat them as hardware policy.

## References

- `Documentation/ABI/testing/sysfs-class-power` (cached copy; 59 What: entries)
- `drivers/power/supply/power_supply_sysfs.c`, `drivers/power/supply/Makefile` (torvalds/linux master; key blocks summarized in worklog 2-b)
- Ledger row SYSC-power_supply (`src/linux/sysfs/ledger.md`); worklog Task 2-b
