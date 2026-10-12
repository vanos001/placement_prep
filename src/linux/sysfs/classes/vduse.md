# /sys/class/vduse

| Field | Value |
|---|---|
| Subsystem | VDUSE framework (virtio data path acceleration in userspace; UAPI in /usr/include/linux/vduse.h); contact Yongji Xie; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-vduse` (4 What: entries) |
| Since | 5.15 (Oct 2021, all entries) |
| Live (5.10.134 host) | class absent: /sys/class/vduse does not exist in this container |
| Ledger ID | SYSC-vduse |

## What it represents

The configuration surface of the VDUSE framework: "The vduse/ class
sub-directory belongs to the VDUSE framework and provides a sysfs interface
for configuring VDUSE devices" (ABI). The class holds the control device
entry and one directory per VDUSE device created through it. VDUSE devices
are software-defined virtio devices whose data path is implemented in
userspace; the sysfs side only carries lifecycle configuration (creation via
control, and the message timeout), while the real device API is the ioctl
interface in /usr/include/linux/vduse.h.

## Relationship to the device model

Three ABI entries are containers rather than attribute files: the class
itself, control/ ("created for the control device of VDUSE framework"), and
<device-name>/ ("created when a VDUSE device is created via the control
device"). The only file documented is <device-name>/msg_timeout. The UAPI
header on this host confirms the pairing: its ioctls are labeled "The
ioctls for control device (/dev/vduse/control)" and VDUSE_CREATE_DEV takes
struct vduse_dev_config with a NUL-terminated name, vendor_id, device_id,
virtio features, vq_num, vq_align, config_size and config buffer.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| control/ | -- | directory for the VDUSE control device (char dev /dev/vduse/control per host vduse.h) | always | ABI testing sysfs-class-vduse, 5.15; /usr/include/linux/vduse.h |
| <device-name>/ | -- | per-device directory, appears on VDUSE_CREATE_DEV via control | per created device | ABI, 5.15 |
| <device-name>/msg_timeout | RW | timeout in seconds waiting for a control-message response from userspace; default 30; write 0 disables the timeout | per created device | ABI, 5.15 |

## Safety and writes

The only sysfs write is msg_timeout. Lowering it makes the kernel give up
sooner on userspace control-message responses; writing 0 waits forever,
which can hang device teardown if the userspace daemon wedges. Device
creation and destruction happen through the control ioctl interface, not
sysfs. The class is absent on the 5.10.134 host (5.15 ABI), so no live read
was possible and no value examples are reported.

## References

- `Documentation/ABI/testing/sysfs-class-vduse` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-vduse
- Host header /usr/include/linux/vduse.h (read-only inspection: control ioctls, VDUSE_CREATE_DEV)
- sysfs-attrs.json entry `vduse` (4 paths); live enumeration: class absent, kernel 5.10.134
- Coverage: [ledger](../ledger.md)
