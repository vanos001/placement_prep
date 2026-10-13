# /sys/class/ptp

| Field | Value |
|---|---|
| Subsystem | PTP (Precision Time Protocol) hardware clock core, `drivers/ptp/` (`obj-$(CONFIG_PTP_1588_CLOCK) += ptp.o`, torvalds/linux master) |
| Config gate | `CONFIG_PTP_1588_CLOCK` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-ptp` (16 What entries; the file carries dates from September 2010 but no KernelVersion lines) |
| Since | not stated as versions: entries dated September 2010 (core), March 2014 (`n_pins`, `pins`), May 2021 (`n_vclocks`, `max_vclocks`) |
| Live (5.10.134 host) | class present with 1 device: `ptp0` = "KVM virtual PTP" (values read live on the host; see Attributes) |
| Ledger ID | SYSC-ptp |

## What it represents

One directory per PTP hardware clock (PHC), `ptpN` -- NIC PHY/MAC clocks,
SoC timers, virtual clocks. Sysfs advertises the clock's capabilities:
`clock_name` (human-readable "friendly name" to distinguish PHY-based from
MAC-based devices, explicitly not required to be unique), `max_adjustment`
(maximum frequency adjustment in parts per billion), and the channel
counts `n_alarms`, `n_external_timestamps`, `n_periodic_outputs`,
`n_programmable_pins`/`n_pins`. The timestamping and pin-routing control
plane lives on `/dev/ptpN` ioctls (host header
`/usr/include/linux/ptp_clock.h`: `PTP_CLOCK_GETCAPS`, `PTP_PF_*` function
values that the sysfs `pins` documentation points to). The 2021 additions
manage virtual clocks: writing `n_vclocks` creates that many vclocks and
makes the physical clock free-running; `max_vclocks` caps the pool.

## Relationship to the device model

`/sys/class/ptp/ptpN` is a class view over the clock's parent device under
`/sys/devices/...`. The live host instance is a virtual one:
`ptp0 -> ../../devices/virtual/ptp/ptp0`, `dev` = 249:0, registered by the
KVM ptp_kvm driver. PHCs feed PPS events into the PPS subsystem when
enabled via `pps_enable` (per sysfs-ptp), and large multi-function
appliances expose their own class beside this one:
[timecard](./timecard.md) links back to its PHC via its `ptp` symlink.
Time-adjacent siblings: [pps](./pps.md), [rtc](./rtc.md).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `ptpN/clock_name` | RO | human-readable clock name string | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/max_adjustment` | RO | positive integer, parts per billion | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/n_alarms` | RO | number of periodic or one-shot alarms | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/n_external_timestamps` | RO | number of external timestamp channels | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/n_periodic_outputs` | RO | number of programmable periodic output channels | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/n_pins` | RO | number of programmable pins | conditional: absent on host ptp0 (0 pins) | ABI testing `sysfs-ptp` (Mar 2014) |
| `ptpN/pins/<name>` | RW | two integers: assigned function (PTP_PF_*, linux/ptp_clock.h) and channel | per pin | ABI testing `sysfs-ptp` (Mar 2014) |
| `ptpN/pps_available` | RO | 1 if the clock can deliver PPS to the host CPU, else 0 | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/extts_enable` | WO | "<channel index> 1" to enable, "... 0" to disable external timestamps | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/fifo` | RO | external event timestamps: channel index, seconds, nanoseconds | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/period` | WO | five integers: channel, start sec/nsec, period sec/nsec; zeros disable | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/pps_enable` | WO | 1/0: deliver PPS events to the Linux PPS subsystem | always | ABI testing `sysfs-ptp` (Sep 2010) |
| `ptpN/n_vclocks` | RW | virtual clocks in use; 0 = physical clock adjustable | always (ABI entry dated May 2021) | ABI testing `sysfs-ptp` (May 2021) |
| `ptpN/max_vclocks` | RW | maximum number of ptp vclocks; write to reconfigure | always (ABI entry dated May 2021) | ABI testing `sysfs-ptp` (May 2021) |

Live cross-check on host ptp0 (5.10.134): `clock_name` = "KVM virtual PTP",
`max_adjustment`/`n_alarms`/`n_external_timestamps`/`n_periodic_outputs`/
`n_programmable_pins`/`pps_available` all read 0, `dev` = 249:0 -- the
zero-pin clock omits `n_pins`/`pins`, exactly the conditional behavior the
ABI describes.

## Safety and writes

The write-only controls (`extts_enable`, `period`, `pps_enable`) program
hardware event plumbing; `pins` and the vclock pair reconfigure
clock routing and clock topology (creating vclocks makes the physical
clock free-running, which changes what time synchronization daemons see).
The ABI states no capability requirements; in practice writes need root.
Reads are safe.

## References

- `Documentation/ABI/testing/sysfs-ptp` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-ptp)
- `/usr/include/linux/ptp_clock.h` (host header: `PTP_CLOCK_GETCAPS`, `PTP_PF_*`)
- `drivers/ptp/Makefile` (torvalds/linux master; fetched obj line)
- Live values: `/sys/class/ptp/ptp0/*` read directly on the 5.10.134 host
- Ledger row SYSC-ptp; live enumeration per `source-cache/live-sys/class-list.txt`
- Sibling pages: [pps](./pps.md), [rtc](./rtc.md), [timecard](./timecard.md)
