# /sys/class/pps

| Field | Value |
|---|---|
| Subsystem | PPS (Pulse Per Second) core, `drivers/pps/` (`obj-$(CONFIG_PPS) := pps_core.o`, torvalds/linux master) |
| Config gate | `CONFIG_PPS` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-pps` (8 What entries; the file carries Date February 2008 but no KernelVersion lines) |
| Since | not stated: the ABI file has no KernelVersion field (entries dated February 2008) |
| Live (5.10.134 host) | class directory present, 0 devices (no PPS source registered in the container) |
| Ledger ID | SYSC-pps |

## What it represents

One directory per PPS source, `ppsX` -- a signal discipline interface built
on hardware pulse-per-second inputs (serial DCD lines, GPIO captures, PTP
hardware clock PPS outputs). The ABI calls it "a unified interface to the
PPS sources" of the system. The per-source files split in two groups:
identity (`name`, `path` -- empty when the source is not connected to a
device, `echo` -- whether the source supports an echo function, `mode` --
functioning mode in hexadecimal, pointing at `include/linux/pps.h` for the
bit definitions) and the event records: `assert` and `clear`, each
reporting the last timestamp and sequence number of its event kind in the
exact format `<secs>.<nsec>#<sequence>`, empty when no such event has been
captured. Consumers pair sysfs discovery with the character device:
`/dev/ppsN` (per `Documentation/driver-api/pps.rst`) and the `PPS_FETCH`
ioctl from the host header `/usr/include/linux/pps.h`.

## Relationship to the device model

`/sys/class/pps/ppsX` is a class view over a PPS source device under
`/sys/devices/...` (a tty line discipline, GPIO, or a PTP clock registered
as a PPS source -- the [ptp](./ptp.md) class's `pps_enable` attribute hands
PTP hardware PPS events to this subsystem per the sysfs-ptp ABI). No pps
bus exists; events flow through the char device, sysfs is introspection.
Time-adjacent siblings: [rtc](./rtc.md), [timecard](./timecard.md).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `ppsX/assert` | RO | last assert event: `<secs>.<nsec>#<sequence>`; empty if none | always (content conditional) | ABI testing `sysfs-pps` |
| `ppsX/clear` | RO | last clear event: same format; empty if none | always (content conditional) | ABI testing `sysfs-pps` |
| `ppsX/mode` | RO | functioning mode, hexadecimal; see include/linux/pps.h | always | ABI testing `sysfs-pps` |
| `ppsX/echo` | RO | whether the source supports an echo function | always | ABI testing `sysfs-pps` |
| `ppsX/name` | RO | name of the source | always | ABI testing `sysfs-pps` |
| `ppsX/path` | RO | path name of the connected device; empty if unconnected | always (content conditional) | ABI testing `sysfs-pps` |

## Safety and writes

The ABI documents all six per-source files as reports -- nothing is
described as writable, and no capability requirements or error conventions
appear in the file. Reading `assert`/`clear` is safe and non-destructive;
the low-latency capture loop belongs to the char device and `PPS_FETCH`.
Because `mode` is a hex bitfield defined in `include/linux/pps.h`, readers
need the header to decode it -- the ABI deliberately defers the semantics.

## References

- `Documentation/ABI/testing/sysfs-pps` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-pps)
- `Documentation/driver-api/pps.rst` (not in sparse cache; `/dev/ppsN` and ppstest usage cited from it)
- `/usr/include/linux/pps.h` (host header: `PPS_FETCH` ioctl, mode bits)
- `drivers/pps/Makefile` (torvalds/linux master; fetched obj line)
- Ledger row SYSC-pps; `/sys/class/pps` present with 0 devices per `source-cache/live-sys/class-list.txt`
- Sibling pages: [ptp](./ptp.md), [rtc](./rtc.md), [timecard](./timecard.md)
