# /sys/class/wakeup

| Field | Value |
|---|---|
| Subsystem | PM wakeup sources statistics class (wakeup_source tracking), Contact Tri Vo in the ABI file; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-wakeup` (11 What entries) |
| Since | June 2019 (all entries; no KernelVersion lines stated in the file) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/wakeup |
| Ledger ID | SYSC-wakeup |

## What it represents

Pointers to all wakeup sources in the kernel at a given moment. A wakeup source is any entity that can prevent autosleep or abort a suspend; every wakeup event in the system is accounted here. The class is the aggregated statistics view - counts and durations - while the decision surface for whether a given device may wake the system lives elsewhere, in the per-device `power/wakeup` file documented in `sysfs-devices-power`.

## Relationship to the device model

Each directory under the class corresponds to one `struct wakeup_source`. Wakeup sources are registered both by the device core (for devices that can signal wakeup events) and by kernel subsystems for software sources, so the directories are not a one-to-one view of physical devices: they are the set of active accounting objects. All attributes are read-only counters and timestamps; nothing here enables or disables anything.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `.../name` | RO | wakeup source name | wakeup source | ABI, June 2019 |
| `.../active_count` | RO | times the wakeup source was activated | wakeup source | ABI, June 2019 |
| `.../event_count` | RO | number of signaled wakeup events | wakeup source | ABI, June 2019 |
| `.../wakeup_count` | RO | number of times the source might abort suspend | wakeup source | ABI, June 2019 |
| `.../expire_count` | RO | number of times the source's timeout expired | wakeup source | ABI, June 2019 |
| `.../active_time_ms` | RO | ms continuously active; 0 if inactive | wakeup source | ABI, June 2019 |
| `.../total_time_ms` | RO | ms total time active | wakeup source | ABI, June 2019 |
| `.../max_time_ms` | RO | ms longest continuous active period | wakeup source | ABI, June 2019 |
| `.../last_change_ms` | RO | monotonic ms time of last touch | wakeup source | ABI, June 2019 |
| `.../prevent_suspend_time_ms` | RO | ms spent preventing autosleep | wakeup source | ABI, June 2019 |

## Safety and writes

Purely observational: every documented attribute is read-only, so there is no write path, no capability requirement and no risk of changing power behavior through this class. It answers "who woke the machine and for how long" - the data behind wakeup debugging on Android-derived systems (the ABI contact is from the Android team). To change wakeup behavior, use the per-device `/sys/devices/.../power/wakeup` `enabled`/`disabled` control (ABI `sysfs-devices-power`, January 2009) instead; that file exists only for devices capable of generating system wakeup events.

## References

- `Documentation/ABI/testing/sysfs-class-wakeup` (cached copy; 11 What entries)
- `Documentation/ABI/testing/sysfs-devices-power` (per-device wakeup control, cached copy)
- Implementation: not in cached tree
- Coverage: [ledger](../ledger.md)
- Live check: /sys/class/wakeup absent (kernel 5.10.134, read-only enumeration)
