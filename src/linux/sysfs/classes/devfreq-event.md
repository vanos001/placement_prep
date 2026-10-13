# /sys/class/devfreq-event

| Field | Value |
|---|---|
| Subsystem | devfreq-event framework (event counters feeding devfreq governors), PM subsystem; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-devfreq-event` (3 What entries) |
| Since | January 2017 (all entries; no KernelVersion line stated in the file) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/devfreq-event |
| Ledger ID | SYSC-devfreq-event |

## What it represents

One directory per devfreq-event object, named `event<x>` with a unique number x. A devfreq-event device is a monitored resource - typically a set of hardware performance counters (DDRC load, bus utilization, PMU blocks) - that devfreq governors read to decide frequency changes. The class is the sysfs handle for enumerating those counters and their enable state.

## Relationship to the device model

Each `event<x>` directory is a class view of a devfreq-event device registered by a platform driver. The event objects are consumed by devfreq through the kernel API; sysfs only exposes the name and the enable reference count, so userspace can see which measurement blocks exist and whether any governor is currently using them. Unlike [devfreq](./devfreq.md) there is no control surface here: no file selects an event or configures it. The class can also exist independently of any devfreq consumer - the ABI describes the objects as a place for devfreq-event variables, with the enable count simply staying at zero when no governor has enabled the event.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `event<x>/` | -- | directory per devfreq-event object | always | ABI, January 2017 |
| `event<x>/name` | RO | name of the devfreq-event object | always | ABI, January 2017 |
| `event<x>/enable_count` | RO | integer reference count; > 0 means enabled | always | ABI, January 2017 |

## Safety and writes

All three documented paths are read-only; there is nothing to write and no permission hazard. The enable reference count is kernel-managed: it increases when a consumer (a devfreq governor) enables the event and decreases on disable, so a nonzero value only means "in use by the kernel right now". No ABI documentation exists for any write access to this class.

## References

- `Documentation/ABI/testing/sysfs-class-devfreq-event` (cached copy; 3 What entries)
- Sibling page: [devfreq](./devfreq.md); coverage: [ledger](../ledger.md)
- Live check: /sys/class/devfreq-event absent (kernel 5.10.134, read-only enumeration)
