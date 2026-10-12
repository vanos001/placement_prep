# /sys/class/pwm

| Field | Value |
|---|---|
| Subsystem | generic PWM framework, `drivers/pwm/core.c` (sysfs code lives here; master also registers a chardev via `cdev_device_add` with the ioctl ABI in `include/uapi/linux/pwm.h`) |
| Config gate | `CONFIG_PWM` (`obj-$(CONFIG_PWM) += core.o` in `drivers/pwm/Makefile`, torvalds/linux master) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-pwm` |
| Since | 3.11 (class, chips, channels); 4.8 (`capture`) |
| Live (5.10.134 host) | class absent: no PWM controller registered in the container |
| Ledger ID | SYSC-pwm |

## What it represents

One `pwmchipN` directory per probed PWM controller and, under it, one `pwmX` directory per channel exported for sysfs control. Period and duty cycle are expressed in nanoseconds, polarity as a string. This is the direct sysfs route for driving servos, backlight rails, and buzzers on SBCs; `Documentation/driver-api/pwm.rst` describes the same interface from the driver side.

## Relationship to the device model

`pwmchipN` is a class view of a controller device under `/sys/devices/...` (platform or SoC device). Exporting a channel with `export` materializes a `pwmX` child directory. There is no PWM bus and no `/sys/dev` entry for the sysfs interface; on current master the same devices additionally expose `/dev/pwmchipN` character devices (chardev ABI per worklog 2-b). Do not confuse this class with hwmon's `pwmY` files: those are 0-255 fan-duty controls inside hwmon chips, not this nanosecond-based channel API.

## Attributes

11 What: entries are documented in `Documentation/ABI/testing/sysfs-class-pwm`: three describe the directory structure (`/sys/class/pwm/`, `pwmchipN/`, `pwmX/`) and eight name attributes; the table covers the attributes.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `pwmchipN/npwm` | RO | number of channels the chip supports | always | ABI What `npwm` (3.11) |
| `pwmchipN/export` | WO | channel number 0..npwm-1; creates `pwmX` | always | ABI What `export` (3.11) |
| `pwmchipN/unexport` | WO | channel number; removes `pwmX` | always | ABI What `unexport` (3.11) |
| `pwmchipN/pwmX/period` | RW | nanoseconds | exported channels | ABI What `pwmX/period` (3.11) |
| `pwmchipN/pwmX/duty_cycle` | RW | nanoseconds, must be <= `period` | exported channels | ABI What `pwmX/duty_cycle` (3.11) |
| `pwmchipN/pwmX/polarity` | RW | `normal` or `inversed` | exported channels | ABI What `pwmX/polarity` (3.11) |
| `pwmchipN/pwmX/enable` | RW | 0 disabled, 1 enabled | exported channels | ABI What `pwmX/enable` (3.11) |
| `pwmchipN/pwmX/capture` | RO | pair of unsigned integers: period and duty cycle, space separated | input-capable channels | ABI What `pwmX/capture` (4.8) |

The sysfs ABI file is still under `Documentation/ABI/testing/`, and the exported-channel model (explicit export/unexport) parallels the legacy GPIO sysfs design.

## Safety and writes

Reads are safe. Every write (`export`, `period`, `duty_cycle`, `polarity`, `enable`) needs root and directly drives hardware pins: enabling a channel with a bad period can command motors, heaters, or backlight drivers beyond their ratings. Exporting a channel also takes it from any in-kernel consumer. On 5.10-era kernels the sysfs interface is the only generic one; on master prefer the character device ABI, which is the direction the PWM subsystem documents.

## References

- `Documentation/ABI/testing/sysfs-class-pwm` (cached copy: 11 What: entries)
- `drivers/pwm/core.c`, `drivers/pwm/Makefile`, `include/uapi/linux/pwm.h` (torvalds/linux master, per worklog 2-b)
- `Documentation/driver-api/pwm.rst` (sysfs section)
- Ledger row SYSC-pwm; worklog Task 2-b (hwmon `pwmX` disambiguation)
