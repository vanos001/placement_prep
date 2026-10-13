# /sys/class/mux

| Field | Value |
|---|---|
| Subsystem | Generic MUX (multiplexer controller) framework, drivers/mux; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-mux` (2 What entries) |
| Since | April 2017, KernelVersion 4.13 (both entries) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/mux |
| Ledger ID | SYSC-mux |

## What it represents

The sysfs presence of the Generic MUX Framework: mux controllers are hardware switches that route one of several inputs (MIPI DPI pins, I2C buses, PHY lanes) to a consumer. The class directory holds one `muxchip<N>` directory per probed mux chip, where N is a simple enumeration. It is an enumeration surface only.

## Relationship to the device model

`/sys/class/mux/muxchipN` is created for each mux chip registered by the mux core; consumer drivers (the devices that actually change the switch state) operate the chip through the kernel mux API, not through sysfs. The ABI file documents only the class directory and the per-chip directory - no per-chip attributes - so the entire userspace-visible layout in the cached sources is the two-level directory tree.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `muxchip<N>/` | -- | directory per probed mux chip, N simple enumeration | chip probed | ABI, 4.13 |

No attribute files under `/sys/class/mux/` are documented in the cached tree: the ABI file's two What entries cover only the class directory and the muxchipN directory. Control of a mux is done by its consumer driver in-kernel; any control file would be driver-specific and none is documented here.

## Safety and writes

Nothing documented to read or write: no attribute rows exist beyond the directory layout, so there is no documented read or write path, and no capability requirement can be stated from sources. The honest safety statement is that the framework deliberately keeps mux control in the kernel (consumers arbitrate switch ownership), and this class is for visibility, not control - as far as the cached documentation goes.

## References

- `Documentation/ABI/testing/sysfs-class-mux` (cached copy; 2 What entries, Contact Peter Rosin)
- `drivers/mux/` implementation: not in cached tree
- Sibling page: [extcon](./extcon.md); coverage: [ledger](../ledger.md)
- Live check: /sys/class/mux absent (kernel 5.10.134, read-only enumeration)
