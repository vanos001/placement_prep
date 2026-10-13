# /sys/class/intel_pmt

| Field | Value |
|---|---|
| Subsystem | Intel Platform Monitoring Technology (PMT) devices, per the ABI text; contacts David E. Box, Alexander Duyck (Intel); implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-intel_pmt` (telem/crashlog entries) and `Documentation/ABI/testing/sysfs-class-intel_pmt-features` (features directories) |
| Since | 5.10 (October 2020, telem and crashlog); features-`<PCI BDF>` 6.16 (2025-04-24) |
| Live (5.10.134 host) | class absent: /sys/class/intel_pmt does not exist in this container (class-list.txt row intel_pmt: none; task brief's "live" claim was wrong) |
| Ledger ID | SYSC-intel_pmt |

## What it represents

Devices exposing Intel PMT hardware telemetry. Three sub-families live in
one class: telem`<x>` directories for telemetry regions, crashlog`<x>`
directories for crash-data recording, and (newer) features-`<PCI BDF>`
directories that group per-feature capabilities for a PCI device. The data
itself is read from binary files meant "to be mapped or read"; each region
ships a GUID that selects the XML register-layout description for the
parent PCI device, so decoding is a userspace concern driven by
device-id-plus-GUID lookup.

## Relationship to the device model

The features ABI ties the class to PCI devices explicitly: directories are
named features-`<PCI BDF>`, and the example uses BDF 0000:00:03.1, i.e. the
class device hangs off a PCI address. telem/crashlog entries reference
"the parent device" whose PCI id plus the GUID select the XML layout.
Feature directories contain per-feature subdirs (accelerator_telemetry,
crash_log, per_core_*_telemetry, per_rmid_*_telemetry, tpmi_control,
tracing, uncore_telemetry) with common caps and guids files and conditional
extras (max_command_size, max_stream_size for MCTP; min_watcher_period_ms
for the watcher API; num_rmids for RMID telemetry).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| telem`<x>`/telem | RO | telemetry data region; may be mapped or read | per telem device | ABI testing sysfs-class-intel_pmt, 5.10 |
| telem`<x>`/{guid,size,offset} | RO | GUID string; region size and offset in bytes | per telem device | ABI, 5.10 |
| crashlog`<x>`/crashlog | RO | crashlog buffer; may be mapped or read | per crashlog device | ABI, 5.10 |
| crashlog`<x>`/{guid,size,offset} | RO | GUID string; buffer length and offset in bytes | per crashlog device | ABI, 5.10 |
| crashlog`<x>`/enable | RW | boolean: crashlog recording enabled for this device | per crashlog device | ABI, 5.10 |
| crashlog`<x>`/trigger | RW | boolean: read reports whether crashlog triggered; write false clears, write triggers a new event if not set | per crashlog device | ABI, 5.10 |
| features-`<PCI BDF>`/`<feature>`/caps | RO | lists available capabilities for the feature | features ABI, 6.16 | ABI testing sysfs-class-intel_pmt-features, 6.16 |
| features-`<PCI BDF>`/`<feature>`/guids | RO | GUIDs associated with this feature | features ABI, 6.16 | ABI, 6.16 |
| features-`<PCI BDF>`/`<feature>`/{max_command_size,max_stream_size} | RO | MCTP out-of-band limits, bytes | MCTP-capable features only | ABI, 6.16 |
| features-`<PCI BDF>`/`<feature>`/min_watcher_period_ms | RO | minimum watcher sampling/reporting period, milliseconds | watcher-API features only | ABI, 6.16 |
| features-`<PCI BDF>`/`<feature>`/num_rmids | RO | maximum RMIDs tracked simultaneously | RMID telemetry features only | ABI, 6.16 |

## Safety and writes

Reads are safe; the binary telem/crashlog files are intended for mmap. The
writable files control crash recording on real hardware: enable switches
crashlog on/off and trigger arms or clears crash capture -- writing it on a
production machine alters the platform's crash-diagnosis behavior. The
class is absent on this host; nothing was read live.

## References

- `Documentation/ABI/testing/sysfs-class-intel_pmt`, `sysfs-class-intel_pmt-features` (cached copies)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-intel_pmt
- sysfs-attrs.json entry `intel_pmt` (14 paths); live enumeration: class absent, kernel 5.10.134
- Coverage: [ledger](../ledger.md)
