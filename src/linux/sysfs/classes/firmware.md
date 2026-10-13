# /sys/class/firmware

| Field | Value |
|---|---|
| Subsystem | Driver core firmware loader; drivers/base/firmware_loader/sysfs.c (class, device attrs), fallback.c (device lifecycle) |
| Config gate | CONFIG_FW_LOADER; the class-level `timeout` attr and FIRMWARE/TIMEOUT/ASYNC uevent vars require CONFIG_FW_LOADER_USER_HELPER; `cancel`/`status`/`error`/`remaining_size` require CONFIG_FW_UPLOAD (drivers/base/firmware_loader/Kconfig) |
| ABI documentation | Documentation/ABI/testing/sysfs-class-firmware (7 What: entries) |
| Since | All ABI entries dated July 2022, KernelVersion 5.19; the class predates the doc but no earlier date is stated by the sources checked |
| Live (5.10.134 host) | none observed (class absent from the cached 46-class enumeration) |
| Ledger ID | SYSC-firmware |

## What it represents

Transient devices representing in-progress firmware requests. The class serves two flows: the sysfs fallback mechanism (user space supplies an image the driver could not find on disk) and firmware upload (user space pushes an update to a device that opted in). Each device is named after the firmware image (`dev_set_name(f_dev, "%s", fw_name)`, drivers/base/firmware_loader/sysfs.c) and carries the uevent variables FIRMWARE, TIMEOUT and ASYNC (sysfs.c firmware_uevent).

## Relationship to the device model

Devices are children of the requesting device (`f_dev->parent`, sysfs.c fw_create_instance). The class is not the `/sys/firmware` tree (dmi, efi, memmap), which is a non-class firmware-nodes view and is tracked separately in the sysfs ledger.

## Attributes (representative; source per row)

| Attribute | R/W | Meaning (source: ABI testing/sysfs-class-firmware) |
|---|---|---|
| `loading` | 0644 | Echo 1 before writing `data`, 0 when complete (triggers transfer for uploads), -1 to abort |
| `data` | 0644 bin | Firmware image carrier for fallback and uploads |
| `timeout` | 0644 | Fallback timeout, seconds; class-level attr (0 means wait forever; sysfs.c timeout_store) |
| `status` | RO | One of idle, receiving, preparing, transferring, programming |
| `error` | RO | Failed upload as `<STATUS>:<ERROR>`; error tokens include hw-error, timeout, user-abort, device-busy, invalid-file-size, read-write-error, flash-wearout |
| `remaining_size` | RO | Bytes left to transfer, format "%u" |
| `cancel` | WO | Request cancel of an upload; rejected EBUSY (FLASH write in progress) or ENODEV (no update) |

## Safety and writes

The loading/data/cancel sequence drives kernel device state; reading `error` during a transfer fails with EBUSY. All attributes exist only while a request is being serviced by the fallback or upload path (fallback.c fw_run_sysfs_fallback, fw_create_instance). No live observation on the read-only container host.

## References

- Documentation/ABI/testing/sysfs-class-firmware
- drivers/base/firmware_loader/sysfs.c and fallback.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [udev](../../admin/udev.md)
