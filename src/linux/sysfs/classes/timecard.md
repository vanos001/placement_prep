# /sys/class/timecard

| Field | Value |
|---|---|
| Subsystem | OpenCompute TIME CARD driver (PTP clock appliance), `drivers/ptp/` (`obj-$(CONFIG_PTP_1588_CLOCK_OCP) += ptp_ocp.o`, torvalds/linux master) |
| Config gate | `CONFIG_PTP_1588_CLOCK_OCP` (obj line verified against torvalds/linux master 2026; depends on the PTP class core) |
| ABI documentation | `Documentation/ABI/testing/sysfs-timecard` (37 What entries) |
| Since | not stated as kernel versions: entries dated September 2021 (core), March 2022 (gen/freq/status group), August 2024 (`tty/` group) |
| Live (5.10.134 host) | class absent: no `/sys/class/timecard` directory, no timecard hardware in the container |
| Ledger ID | SYSC-timecard |

## What it represents

One directory per OpenCompute timecard, `ocpN` -- a PCIe time appliance
card pairing a PTP hardware clock with GNSS receivers, a miniature atomic
clock, IRIG-B/DCF timecode, SMA connectors, frequency counters and
generators. The class is the card's configuration panel:
`available_clock_sources` (NONE/PPS/TOD/IRIG/DCF) vs the writable
`clock_source` that picks one; `available_sma_inputs`/`available_sma_outputs`
(10Mhz, PPS1/2, TS1-4, IRIG, DCF, FREQ1-4, PHC, MAC, GNSS1/2, GEN1-4, GND,
VCC) vs the writable `sma1`..`sma4` connectors, whose format is a
space-separated signal list prefixed by `in:`/`out:` direction. Discipline
state: `clock_status_drift`/`clock_status_offset` (firmware's atomic-clock
disciplining), `gnss_sync`, `tod_correction` and `utc_tai_offset` (UTC/TAI
bookkeeping for NMEA and DCF/IRIG formats). Optional subgroups: `freqX/`
(measured `frequency`, measurement window `seconds` 0-255), `genX/`
(signal generator: `duty`, `period`, `phase`, `polarity`, `running`,
`start`, and the composite RW `signal` accepting
"period [duty [phase [polarity]]]" in nanoseconds/percent), `tty/`
(GNSS, GNSS2, MAC, NMEA serial port names), and the cross-class links
`ptp`, `pps`, `i2c`.

## Relationship to the device model

The card is a PCI device whose driver registers several kernel objects at
once; the ABI exposes them from the class directory as symlinks --
`ptp` "links to the associated PTP device" ([ptp](./ptp.md) class),
`pps` to the associated PPS device ([pps](./pps.md)), `i2c` to the
associated i2c device, and the `tty/` names point at serial ports for the
GNSS modules. `serialnum` identifies the physical card. There is no
timecard bus; the class is the appliance's single configuration surface.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `ocpN/available_clock_sources`, `available_sma_inputs`, `available_sma_outputs` | RO | fixed token sets (NONE/PPS/TOD/IRIG/DCF; 10Mhz/PPS1/2/TS1-4/...; 10Mhz/PHC/MAC/GNSS1/2/...) | always | ABI testing `sysfs-timecard` (2021) |
| `ocpN/clock_source` | RW | one value from available_clock_sources | always | ABI testing `sysfs-timecard` (2021) |
| `ocpN/sma1`..`sma4` | RW | space-separated signal list, optional `in:`/`out:` prefix; 10Mhz input valid on SMA1 only | always | ABI testing `sysfs-timecard` (2021) |
| `ocpN/clock_status_drift`, `clock_status_offset` | RO | firmware disciplining drift/offset values | always | ABI testing `sysfs-timecard` (Mar 2022) |
| `ocpN/gnss_sync` | RO | GNSS signal validity / loss indication | always | ABI testing `sysfs-timecard` (2021) |
| `ocpN/freqX/frequency`, `freqX/seconds` | RO / RW | measured frequency; measurement seconds 0-255, 0 disables | optional freq counters | ABI testing `sysfs-timecard` (Mar 2022) |
| `ocpN/genX/{duty,period,phase,polarity,running,start}`, `genX/signal` | RO, RW | percent 1-99; nsec; nsec; 0/1; 0/1; `<sec>.<nsec>`; composite `period [duty [phase [polarity]]]` | optional generators | ABI testing `sysfs-timecard` (Mar 2022) |
| `ocpN/irig_b_mode` | RW | integer 0-7, timecode format B00`<n>` | always | ABI testing `sysfs-timecard` (2021) |
| `ocpN/tod_correction`, `ocpN/utc_tai_offset` | RW | TAI correction for incoming GNSS/UTC time; offset seconds added to TAI for DCF/IRIG | always | ABI testing `sysfs-timecard` (2021) |
| `ocpN/ts_window_adjust` | RW | nsec subtracted from the post-read SYS timestamp for PTP SYS_OFFSET_EXTENDED midpoints | always | ABI testing `sysfs-timecard` (2021) |
| `ocpN/serialnum` | RO | card serial number | always | ABI testing `sysfs-timecard` (2021) |
| `ocpN/{ptp,pps,i2c}`, `ocpN/tty/{ttyGNSS,ttyGNSS2,ttyMAC,ttyNMEA}` | RO symlinks/names | associated class devices and serial ports | optional links | ABI testing `sysfs-timecard` (2021, Aug 2024) |

## Safety and writes

Writes reconfigure physical signal routing and timekeeping: `sma*` and
`clock_source` reroute hardware signals (the ABI itself warns "not all
input combinations may make sense" and restricts the 10Mhz input to SMA1);
`tod_correction`/`utc_tai_offset` shift the card's time base by seconds;
`genX/signal` starts/stops a signal generator (`echo 0 > signal` turns it
off). No capability requirements are stated; writes in practice need root.
Reads are safe.

## References

- `Documentation/ABI/testing/sysfs-timecard` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-timecard)
- `drivers/ptp/Makefile` (torvalds/linux master; fetched obj line)
- Ledger row SYSC-timecard (37 paths); `/sys/class/timecard` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [ptp](./ptp.md), [pps](./pps.md)
