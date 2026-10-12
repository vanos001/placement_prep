# /sys/class/mei

| Field | Value |
|---|---|
| Subsystem | Intel Management Engine Interface (Intel MEI) Linux driver; name from /usr/include/linux/mei.h; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached); UAPI headers /usr/include/linux/mei.h and mei_uuid.h present on host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-mei` (10 What: entries) |
| Since | 3.17 (class, meiN); fw_status 3.19; hbm_ver/hbm_ver_drv 4.9; tx_queue_limit 4.16; fw_ver 4.18; dev_state 5.1; trc 5.5; kind 5.8 |
| Live (5.10.134 host) | class absent: /sys/class/mei does not exist in this container |
| Ledger ID | SYSC-mei |

## What it represents

The mei device class: one meiN directory per probed MEI device. The ME
(Management Engine) firmware writes health and status information into
registers that the class surfaces read-only (fw_status, trc), plus the
negotiated HBM protocol versions, the firmware version, the device state
machine, and one tunable. The ABI states the fw_status register "contains
running state, power management state, error codes, and others", decoded per
PCH/SoC generation, with 1 to 6 registers depending on generation.

## Relationship to the device model

The class sub-directory "belongs to mei device class" (ABI). Each meiN is
created "for each probed mei device"; the cached tree documents the class
view only. The char-device side of the UAPI is visible on this host through
/usr/include/linux/mei.h: IOCTL_MEI_CONNECT_CLIENT associates a file
descriptor with a firmware client identified by UUID, after which reads and
writes talk to that client. The class sysfs view is the health/identity
surface; the cached ABI tree has no /dev/mei entry (rg: 0 matches), so this
page claims nothing about chardev attributes.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| fw_status | RO | contents of 1-6 fw status registers; decoding per PCH/SoC generation | always | ABI testing sysfs-class-mei, 3.19 |
| hbm_ver | RO | HBM protocol version negotiated between driver and device | always | ABI, 4.9 |
| hbm_ver_drv | RO | HBM protocol version supported by the driver | always | ABI, 4.9 |
| tx_queue_limit | RW | maximal number of pending writes per opened session | always | ABI, 4.16 |
| fw_ver | RO | `<platform>:<major>.<minor>.<milestone>.<build_no>`, up to three blocks for different FW components | always | ABI, 4.18 |
| dev_state | RO | INITIALIZING, INIT_CLIENTS, ENABLED, RESETTING, DISABLED, POWER_DOWN, POWER_UP | always | ABI, 5.1 |
| trc | RO | Glitch Detection HW (TRC) status register content | always | ABI, 5.5 |
| kind | RO | "mei" for generic devices; special-purpose devices have their own names ("itouch" for ipts) | always | ABI, 5.8 |

## Safety and writes

All read-only files are safe. The only writable file in the ABI is
tx_queue_limit, which changes flow-control depth for sessions opened
afterwards. No MEI device exists in this container, so no live values,
permission bits, or behavior could be verified; nothing on this page comes
from a live read.

## References

- `Documentation/ABI/testing/sysfs-class-mei` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-mei
- Host headers /usr/include/linux/mei.h, /usr/include/linux/mei_uuid.h (read-only check)
- sysfs-attrs.json entry `mei` (10 paths); live enumeration: class absent, kernel 5.10.134
- Coverage: [ledger](../ledger.md)
