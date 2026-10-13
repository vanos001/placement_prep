# /sys/class/extcon

| Field | Value |
|---|---|
| Subsystem | extcon (external connector) framework, drivers/extcon; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-extcon` (6 What entries) |
| Since | February 2012 (main entries); `mutually_exclusive/` December 2011; no KernelVersion lines stated in the file |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/extcon |
| Ledger ID | SYSC-extcon |

## What it represents

One directory per extcon object - a single external connector port such as a dock, cradle or accessory jack. One port can carry several cables at once (the ABI example is a 30-pin board port with HDMI and charger attached, or audio, video and USB). The class reports which cable states are attached and lets privileged userspace set the whole cable-state bitmask for testing or platform control.

## Relationship to the device model

Each extcon directory is a class view of an `extcon_dev` registered by a driver (the name comes from `extcon_dev_register`). Cable identity is positional: cable numbers 0-31 map to per-cable `cable.X` directories, and the textual cable names appear in the aggregated `state` output. Mutually exclusive cable sets are declared by the driver in the `mutually_exclusive` array and mirrored as file names under the `mutually_exclusive/` subdirectory - the ABI stresses the file names carry the information, not the file contents.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `.../name` | RO | extcon object name; `show_name` callback can override | always | ABI, February 2012 |
| `.../state` | RW | read: `NAME=0/1` lines per cable; write: hex mask starting 0x setting the whole state | always | ABI, February 2012 |
| `.../cable.X/name` | RO | cable name, X in 0-31 | cable present | ABI, February 2012 |
| `.../cable.X/state` | RW | 0 detached, 1 attached | cable present | ABI, February 2012 |
| `.../mutually_exclusive/...` | RO | file per exclusive set, hex mask names (0x3, 0x5, ...) | driver declares exclusivity | ABI, December 2011 |

## Safety and writes

The aggregated `state` write is the powerful one: it updates every cable state at once and is the ABI-recommended way to change states atomically; the per-cable `cable.X/state` write cannot update multiple cables simultaneously. All writes must satisfy the mutually exclusive sets the driver declared, otherwise they are rejected. Writing connector state on real hardware emulates or forces attachment (charger detection, dock switches), so it can fool power and USB subsystems; it is test/setup functionality, not routine configuration.

## References

- `Documentation/ABI/testing/sysfs-class-extcon` (cached copy; 6 What entries)
- `drivers/extcon/` implementation: not in cached tree
- Sibling pages: [mux](./mux.md), [power_supply](./power_supply.md); coverage: [ledger](../ledger.md)
- Live check: /sys/class/extcon absent (kernel 5.10.134, read-only enumeration)
