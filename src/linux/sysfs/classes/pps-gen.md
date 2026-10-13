# /sys/class/pps-gen

| Field | Value |
|---|---|
| Subsystem | PPS (pulse per second) generator subsystem, Contact Rodolfo Giometti in the ABI file; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-pps-gen` (5 What entries) and `sysfs-pps-gen-tio` (1 entry) |
| Since | 6.13 (class, February 2025); TIO enable addition 6.15 (April 2025) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt; the 5.10 kernel predates the interface (6.13) |
| Ledger ID | SYSC-pps-gen |

## What it represents

The PPS generator class: devices that emit a pulse-per-second (or similar period) signal for calibrating remote clocks, the transmit-side counterpart of PPS capture. `/sys/class/pps-gen/` contains one `pps-genX` directory per generator with files to enable signal generation, report whether timing comes from the system clock, and read the generator's current time. The two classes are complementary: `/sys/class/pps` (consumer side) documents capture devices; this class documents sources.

## Relationship to the device model

One class device per registered generator, indexed X. The `system` file distinguishes generators driven from the kernel's own timekeeping (returns 1) from peripheral hardware clock generators (returns 0) - a property read from the device, not a setting. The TIO (time IO) addition documents the `enable` file specifically for the Intel pps_tio generator under a lowercase `pps-genx` spelling in the ABI file.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `pps-genX/enable` | WO | enable or disable PPS signal generation | generator | ABI `sysfs-pps-gen`, 6.13 |
| `pps-genX/system` | RO | 1 system clock source, 0 peripheral clock | generator | ABI `sysfs-pps-gen`, 6.13 |
| `pps-genX/time` | RO | two integers: current generator clock seconds and nanoseconds | generator | ABI `sysfs-pps-gen`, 6.13 |
| `pps-genx/enable` | WO | enable/disable PPS TIO generator output (Intel TIO) | TIO generator | ABI `sysfs-pps-gen-tio`, 6.15 |

## Safety and writes

The only write is `enable`, and its effect is emitting a physical timing signal; on a wrongly configured generator this injects wrong time references into equipment listening on the wire. The ABI states no permission bits; treat it as root-only time infrastructure. Reads (`system`, `time`) are safe. The consumer side keeps its own interface: PPS capture devices use `/dev/ppsN` with the `PPS_FETCH` ioctl (declared in `/usr/include/linux/pps.h`, present on the host) and the `/sys/class/pps` attributes documented in `sysfs-pps`.

## References

- `Documentation/ABI/testing/sysfs-pps-gen` (cached copy; 5 What entries)
- `Documentation/ABI/testing/sysfs-pps-gen-tio` (cached copy; 1 entry)
- `Documentation/ABI/testing/sysfs-pps` (consumer-side class, cached copy, listed for contrast)
- `/usr/include/linux/pps.h` (host header, PPS_FETCH ioctl)
- Coverage: [ledger](../ledger.md)
- Live check: /sys/class/pps-gen absent (kernel 5.10.134, read-only enumeration)
