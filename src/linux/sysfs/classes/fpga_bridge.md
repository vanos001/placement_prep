# /sys/class/fpga_bridge

| Field | Value |
|---|---|
| Subsystem | FPGA Bridge core, drivers/fpga/fpga-bridge.c (class `fpga_bridge_class`, device name br%d) |
| Config gate | CONFIG_FPGA_BRIDGE, "FPGA Bridge Framework" (drivers/fpga/Kconfig) |
| ABI documentation | Documentation/ABI/testing/sysfs-class-fpga-bridge (2 What: entries) |
| Since | January 2016, KernelVersion 4.5 (both entries) |
| Live (5.10.134 host) | none observed (class absent from the cached 46-class enumeration) |
| Ledger ID | SYSC-fpga_bridge |

## What it represents

One device per FPGA bridge driver registered with fpga_bridge_register(). A bridge is the switchable fabric segment between an FPGA and the rest of the system (buses, memory paths); it is disabled while the FPGA is reprogrammed and re-enabled afterwards so that live traffic does not cross a partially configured fabric.

## Relationship to the device model

Bridge devices hang off the hardware device their driver binds to. The FPGA region core (fpga_region.md) locates bridges by device-tree node and by device via class lookups (`class_find_device_by_of_node`, drivers/fpga/fpga-bridge.c), then enables or disables them around manager programming operations.

## Attributes (representative; source per row)

| Attribute | R/W | Meaning (source: ABI testing/sysfs-class-fpga-bridge; class code fpga-bridge.c) |
|---|---|---|
| `name` | RO | Name of the low level FPGA bridge driver |
| `state` | RO | Bridge state shown as "enabled" or "disabled" |

## Safety and writes

Both attributes are read-only. Enabling and disabling bridges happens inside the region programming flow through the fpga_bridge API; there is no sysfs write path, so no user action can leave a bridge open across a reconfiguration. None observed on the read-only container host.

## References

- Documentation/ABI/testing/sysfs-class-fpga-bridge
- drivers/fpga/fpga-bridge.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [fpga_manager](./fpga_manager.md), [fpga_region](./fpga_region.md)
