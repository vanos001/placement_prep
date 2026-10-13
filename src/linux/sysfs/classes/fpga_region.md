# /sys/class/fpga_region

| Field | Value |
|---|---|
| Subsystem | FPGA Region core, drivers/fpga/fpga-region.c (class `fpga_region_class`, device name region%d) |
| Config gate | CONFIG_FPGA_REGION, depends on CONFIG_FPGA_BRIDGE (drivers/fpga/Kconfig) |
| ABI documentation | Documentation/ABI/testing/sysfs-class-fpga-region (1 What: entry) |
| Since | June 2018, KernelVersion 4.19 |
| Live (5.10.134 host) | none observed (class absent from the cached 46-class enumeration) |
| Ledger ID | SYSC-fpga_region |

## What it represents

One device per reconfigurable region. A region ties together an FPGA manager (which programs the fabric) with the set of FPGA bridges that must be shut and reopened around programming. Region drivers register with fpga_region_register(); the region then owns the reconfiguration flow for its slice of the device tree.

## Relationship to the device model

Region devices are class children of the platform device that created them (fpga-region.c). The region core finds managers and bridges through their classes (`fpga_mgr_class`, `fpga_bridge_class`), so the three FPGA classes form a triangle: region drives manager plus bridges. See fpga_manager.md and fpga_bridge.md.

## Attributes (representative; source per row)

| Attribute | R/W | Meaning (source: ABI testing/sysfs-class-fpga-region; DEVICE_ATTR_RO in fpga-region.c) |
|---|---|---|
| `compat_id` | RO | Region id for compatibility check between reconfiguration hardware and image; defined or calculated by the layer creating the region; returns -ENOENT when the creator does not use compat_id |

## Safety and writes

The single attribute is read-only. Reconfiguration itself is not exposed through the region class; it is driven by the subsystem API (for example device-tree overlay application, per drivers/fpga/fpga-region.c), which guards the manager and bridge sequence. None observed on the read-only container host.

## References

- Documentation/ABI/testing/sysfs-class-fpga-region
- drivers/fpga/fpga-region.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [fpga_manager](./fpga_manager.md), [fpga_bridge](./fpga_bridge.md)
