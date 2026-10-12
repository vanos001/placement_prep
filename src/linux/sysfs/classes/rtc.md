# /sys/class/rtc

| Field | Value |
|---|---|
| Subsystem | RTC class core, `drivers/rtc/` (`obj-$(CONFIG_RTC_CLASS) += rtc-core.o`, torvalds/linux master) |
| Config gate | `CONFIG_RTC_CLASS` (obj line verified against torvalds/linux master 2026; `hctosys` additionally reports `CONFIG_RTC_HCTOSYS` per the ABI text) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-rtc` (11 What entries); one driver-specific file exists (`Documentation/ABI/testing/sysfs-class-rtc-rtc0-device-rtc_calibration`) |
| Since | 2.6.17 (class dir, `rtcX`, `date`, `name`, `since_epoch`, `time`); 2.6.20 (`wakealarm`); 2.6.24 (`max_user_freq`); 2.6.32 (`hctosys`); 4.6 (`offset`); 4.16 (`range`) |
| Live (5.10.134 host) | class absent: no `/sys/class/rtc` directory, no RTC device registered in the container |
| Ledger ID | SYSC-rtc |

## What it represents

One directory per real-time clock, `rtcX`, exposing the hardware clock that
keeps time across reboots. The read side answers "what does the RTC say":
`date` (YYYY-MM-DD), `time` (24-hour hh:mm:ss), `since_epoch` (seconds),
`name`, plus `hctosys` -- 1 if this RTC provided the system time at boot
via `CONFIG_RTC_HCTOSYS` -- and `range` (valid seconds-from-epoch interval,
[min, max], 4.16). The write side is the wakeup story: `wakealarm` takes an
epoch timestamp by default, a leading `+` for seconds-in-the-future, or
`+=` for seconds ahead of the current alarm; it is a one-shot wakeup, so it
must be reset after each wake for daily alarms. `max_user_freq` bounds the
interrupt rate an unprivileged user may request, and `offset` (ppb, 4.6)
reads/writes the firmware clock adjustment, visible only when the driver
supports offset adjustment.

## Relationship to the device model

`/sys/class/rtc/rtcX` is a class view over an RTC device under
`/sys/devices/...`; the attrs cache records a `rtc0/device/rtc_calibration`
path, showing driver-specific attributes appearing under the `device/`
link (the one driver-specific ABI file documents exactly such an
attribute). The RTC's char-device face (`/dev/rtcN` with its ioctl API) is
documented separately in `Documentation/ABI/testing/rtc-cdev` (cached).
Time-adjacent siblings in this encyclopedia: [ptp](./ptp.md) (hardware
timestamps, not wall time), [pps](./pps.md) (pulse discipline),
[timecard](./timecard.md) (GNSS-disciplined appliance clock).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `rtcX/date` | RO | YYYY-MM-DD | always | ABI testing `sysfs-class-rtc` (2.6.17) |
| `rtcX/time` | RO | hh:mm:ss, 24-hour | always | ABI testing `sysfs-class-rtc` (2.6.17) |
| `rtcX/since_epoch` | RO | seconds since the epoch | always | ABI testing `sysfs-class-rtc` (2.6.17) |
| `rtcX/name` | RO | name of this RTC | always | ABI testing `sysfs-class-rtc` (2.6.17) |
| `rtcX/hctosys` | RO | 1 if RTC set system time at boot (CONFIG_RTC_HCTOSYS), else 0 | always | ABI testing `sysfs-class-rtc` (2.6.32) |
| `rtcX/range` | RO | valid range as [min, max] seconds from epoch | always | ABI testing `sysfs-class-rtc` (4.16) |
| `rtcX/wakealarm` | RW | epoch seconds, or `+N` seconds ahead, or `+=N` ahead of current alarm; one-shot | always | ABI testing `sysfs-class-rtc` (2.6.20) |
| `rtcX/max_user_freq` | RW | maximum interrupt rate for unprivileged users (Hz) | always | ABI testing `sysfs-class-rtc` (2.6.24) |
| `rtcX/offset` | RW | parts per billion; positive makes a day pass more slowly | only if driver supports offset adjustment | ABI testing `sysfs-class-rtc` (4.6) |

## Safety and writes

`wakealarm` programs hardware that can wake the machine from power-off or
suspend -- a wrong write either fails or schedules an unwanted wakeup, and
by design the alarm is one-shot. `offset` and `max_user_freq` change clock
discipline and interrupt policy; `max_user_freq` exists precisely to cap
what unprivileged users may do with RTC interrupts. Reads are safe. No
capability requirements are stated in the ABI; in practice writes need
root or udev-granted permissions.

## References

- `Documentation/ABI/testing/sysfs-class-rtc`, `Documentation/ABI/testing/rtc-cdev`, `Documentation/ABI/testing/sysfs-class-rtc-rtc0-device-rtc_calibration` (cached copies; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-rtc)
- `drivers/rtc/Makefile` (torvalds/linux master; fetched obj line)
- `source-cache/sysfs-attrs.json` (11 rtc paths incl. the driver-specific `rtc0/device/rtc_calibration`)
- Ledger row SYSC-rtc; `/sys/class/rtc` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [ptp](./ptp.md), [pps](./pps.md), [timecard](./timecard.md)
