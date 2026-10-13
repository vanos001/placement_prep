# /sys/class/i2c-adapter

| Field | Value |
|---|---|
| Subsystem | I2C core, `drivers/i2c/i2c-core-base.c` |
| Config gate | `CONFIG_I2C` (`obj-$(CONFIG_I2C) += i2c-core.o` in `drivers/i2c/Makefile`); `/dev/i2c-N` needs `CONFIG_I2C_CHARDEV` (`obj-$(CONFIG_I2C_CHARDEV) += i2c-dev.o`) |
| ABI documentation | none: no `Documentation/ABI/` file spells `/sys/class/i2c-adapter/` (ledger documents 0 ABI attrs) |
| Since | not stated in any ABI file; v5.10 `i2c-core-base.c` registers it as a compat class (`class_compat_register("i2c-adapter")`), master registers bus devices only |
| Live (5.10.134 host) | class directory present, 0 devices (no I2C adapters in the container) |
| Ledger ID | SYSC-i2c-adapter |

## What it represents

A compat symlink view of the I2C adapters that live under `/sys/bus/i2c/devices/i2c-N` (N is the logical bus number, possibly a MUX channel). On kernels with the compat class (verified in v5.10 source, worklog 2-b) each adapter also appears as `/sys/class/i2c-adapter/i2c-N`. Current master creates no such class; userspace is directed at the bus view, which `Documentation/i2c/i2c-sysfs.rst` walks through in detail.

## Relationship to the device model

The real object is the `i2c_adapter` device on the I2C bus; `/sys/class/i2c-adapter/i2c-N` is a compatibility link to it, and `/dev/i2c-N` (major 89, `Documentation/i2c/dev-interface.rst`, per worklog 2-b) is its userspace transfer interface. Adapter directories contain standard device attributes (`uevent`, `device`, `of_node`, `subsystem`, `power`) plus the `i2c-dev` symlink to the char device. Child slave devices appear in the bus directory as `N-00XX` entries, not in the class view.

## Attributes

3 adapter-specific attributes are documented outside the ABI tree, in `Documentation/i2c/i2c-sysfs.rst` and `Documentation/i2c/instantiating-devices.rst` (directory listings in the doc show `name`, `new_device`, `delete_device` alongside standard attrs); worklog 2-b traces them to the adapter attribute block in `drivers/i2c/i2c-core-base.c`.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `name` | RO | adapter/driver name string | always | `i2c-core-base.c` attr block; `i2c-sysfs.rst` listings |
| `new_device` | WO | two tokens: driver name and 7-bit address in hex (for example `echo lm75 0x48`); instantiates a device | always on adapters | `i2c-core-base.c`; `instantiating-devices.rst` |
| `delete_device` | WO | address previously instantiated via `new_device`; destroys it | always on adapters | `i2c-core-base.c`; `instantiating-devices.rst` |
| `uevent`, `device`, `of_node`, `subsystem`, `power`, `i2c-dev` | RO/links | standard device-model attributes and char-device symlink | standard | `i2c-sysfs.rst` directory listings |

No `What:` lines exist for these files in `Documentation/ABI/`; treat the i2c documentation as the contract, exactly as the ledger notes.

## Safety and writes

Reading `name` is safe. `new_device` and `delete_device` are root-only and potent: `new_device` tells the kernel a chip exists at an address and binds a driver to it, so a wrong address or driver makes the kernel probe and possibly corrupt other hardware on that bus; `delete_device` unbinds and removes it. They exist for chips that cannot be auto-detected (no class-based instantiation) and for board bring-up. Normal userspace talks to adapters through `/dev/i2c-N` with `i2c-tools` instead.

## References

- `Documentation/i2c/i2c-sysfs.rst`, `Documentation/i2c/instantiating-devices.rst`, `Documentation/i2c/dev-interface.rst` (torvalds/linux master)
- `drivers/i2c/i2c-core-base.c`, `drivers/i2c/Makefile` (v5.10 compat-class cross-check per worklog 2-b; master)
- Ledger row SYSC-i2c-adapter (0 ABI attrs is correct); worklog Task 2-b
