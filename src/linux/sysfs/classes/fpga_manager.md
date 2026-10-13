# /sys/class/fpga_manager

| Field | Value |
|---|---|
| Subsystem | FPGA Manager core, drivers/fpga/fpga-mgr.c (class `fpga_mgr_class`, device name fpga%d) |
| Config gate | CONFIG_FPGA (framework); individual low-level drivers under FPGA_MGR_* (drivers/fpga/Kconfig) |
| ABI documentation | Documentation/ABI/testing/sysfs-class-fpga-manager (3 What: entries) |
| Since | `name` and `state` August 2015, KernelVersion 4.3; `status` June 2018, KernelVersion 4.19 |
| Live (5.10.134 host) | none observed (class absent from the cached 46-class enumeration) |
| Ledger ID | SYSC-fpga_manager |

## What it represents

One device per FPGA programming backend registered with fpga_mgr_register(). The manager is the subsystem object that walks an FPGA through a programming sequence (power, reset, write init, write, post-programming steps) on behalf of a region.

## Relationship to the device model

Manager devices are class children of the underlying hardware device created by the low-level driver; the FPGA region pages reconfigure through a manager, and bridges gate the paths the reconfigured fabric exposes. See the sibling pages fpga_bridge.md and fpga_region.md.

## Attributes (representative; source per row)

| Attribute | R/W | Meaning (source: ABI testing/sysfs-class-fpga-manager; dev_groups in fpga-mgr.c) |
|---|---|---|
| `name` | RO | Name of the low level FPGA manager driver |
| `state` | RO | Manager state string: a superset across manufacturers (unknown, power off, power up, reset, firmware request, firmware request error, write init, write init error, write, write error, write complete, write complete error, operating) |
| `status` | RO | Programming error detail (4.19+): reconfig operation error, reconfig CRC error, reconfig incompatible image, reconfig IP protocol error, reconfig fifo overflow error |

## Safety and writes

All three attributes are read-only; the class exposes no write path. Programming is triggered by the region or by driver code requesting firmware, not by writing to the manager. The `state` list is deliberately a superset, so absent states mean the step was skipped, not a failure. None observed on the read-only container host.

## References

- Documentation/ABI/testing/sysfs-class-fpga-manager
- drivers/fpga/fpga-mgr.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [platform drivers](../../kernel/drivers/platform-drivers.md), [fpga_bridge](./fpga_bridge.md), [fpga_region](./fpga_region.md)
