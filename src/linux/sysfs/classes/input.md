# /sys/class/input

| Field | Value |
|---|---|
| Subsystem | Input core, drivers/input/input.c (class `input_class`, devices input`<N>`); event nodes from drivers/input/evdev.c (devices event`<N>`) |
| Config gate | CONFIG_INPUT, "Generic input layer (needed for keyboard, mouse, ...)", default y (drivers/input/Kconfig) |
| ABI documentation | none found for the class core: the stable/, testing/ and obsolete/ ABI directories contain only driver-specific entries (sysfs-driver-input-axp-pek, sysfs-driver-input-cros-ec-keyb, sysfs-driver-input-exc3000); core attributes below are traced to drivers/input/input.c |
| Since | not stated by the sources checked (no ABI What: dates exist for the class core) |
| Live (5.10.134 host) | 2 entries observed; the /dev/input directory is absent in the container (devnode view separate from the class view) |
| Ledger ID | SYSC-input |

## What it represents

One device per input_dev registered with the input core, plus one event device per opened event queue. The class directory is the only sysfs view; the user API is the /dev/input/eventN char devices described by Documentation/input/input_uapi.rst, and udev's input_id builtin derives seat properties from the id/ and capabilities/ files below (systemd udev-builtin-input_id.c, cached during task 2-e).

## Relationship to the device model

Every input`<N>` is created by input_register_device() with dev->dev.class = input_class and name input%lu (input.c). evdev attaches event%d devices of the same class as children (evdev.c dev_set_name, evdev->dev.class = &input_class). Driver-specific attributes appear under input(x)/device/ per the driver ABI entries.

## Attributes (representative; source: drivers/input/input.c attribute groups)

| Attribute | R/W | Meaning |
|---|---|---|
| `name` | RO | Device name string |
| `phys`, `uniq` | RO | Physical topology string; unique identifier |
| `modalias` | RO | Input modalias for module autoloading |
| `properties` | RO | Input property bitmap (for example Pointer, ButtonPad) |
| `inhibited` | 0644 | Inhibit flag; writing 1 or 0 inhibits or uninhibits event delivery |
| `id/bustype`, `id/vendor`, `id/product`, `id/version` | RO | ID fields, each formatted "%04x" |
| `capabilities/ev`, `key`, `rel`, `abs`, `msc`, `led`, `snd`, `ff`, `sw` | RO | Capability bitmaps per event type |
| driver-specific, e.g. `device/startup`, `device/shutdown` | RO/WO | axp-pek power-button attrs per ABI testing/sysfs-driver-input-axp-pek |

## Safety and writes

`inhibited` is the only documented write path in the core groups; it pauses event processing. Driver-specific files may be write-only (axp-pek shutdown). All attribute claims on this page trace to input.c, evdev.c or the named ABI files.

## References

- Documentation/input/input_uapi.rst (uapi side, source-cache)
- drivers/input/input.c, drivers/input/evdev.c (fetched from torvalds/linux master into source-cache)
- Documentation/ABI/testing/sysfs-driver-input-{axp-pek,cros-ec-keyb,exc3000}
- [sysfs overview](../overview.md), [ledger](../ledger.md), [udev](../../admin/udev.md)
