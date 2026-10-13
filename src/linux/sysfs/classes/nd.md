# /sys/class/nd

| Field | Value |
|---|---|
| Subsystem | libnvdimm; drivers/nvdimm/bus.c (nd_class, nvdimm_bus_create_ndctl) |
| Config gate | CONFIG_LIBNVDIMM (drivers/nvdimm/Makefile: obj-$(CONFIG_LIBNVDIMM) += libnvdimm.o, libnvdimm-y += bus.o) |
| ABI documentation | None for the class itself (Documentation/ABI documents the dax/pmem device trees it feeds: sysfs-bus-dax has 18 What: entries; nothing under /sys/class/nd) |
| Since | Source-established; nd class devices are the ndctl%d char devices created per nvdimm bus |
| Live (5.10.134 host) | 1 entry: ndctl0, dev 253:0 (char) |
| Ledger ID | SYSC-nd |

## What it represents

The control surface of libnvdimm: for every nvdimm bus the core creates one
ndctl%d character device in this class, the node the ndctl utility's ioctl
interface (ND_CMD_* commands: ars_cap, ars_start, clear_error, and the
family of bus commands) is issued against. The ndbus%d, region%d, dimm
devices and their attributes live in the bus tree (/sys/bus/nd/devices/)
and under their parents, not in this class. On the live host a pmem
namespace (pmem0, block major 259) is rooted at ndbus0/region0/namespace0.0,
while the class holds the single ndctl0 device.

## Relationship to the device model

nd_class is a bare class (no attributes, no devnode). nvdimm_bus_create_ndctl()
sets dev->class = &nd_class, parents it under the nvdimm_bus device, names it
"ndctl%d" from the bus id, and assigns devt MKDEV(nvdimm_bus_major, bus->id)
where the major comes from register_chrdev(0, "ndctl") at core init, so it
is dynamic. Live: the ndctl char major landed on 253, which coincides with
zram0's dynamic block major 253: the two live side by side because char and
block majors are separate namespaces (/sys/dev/char/253:0 -> ndctl0,
/sys/dev/block/253:0 -> zram0, both verified live).

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| ndctl0/dev | RO | 253:0 (char) | live check (5.10.134); bus.c devt assignment |
| ndctl0/uevent | RO/RW | standard uevent file | device core |
| (no class or device attrs) | - | the ioctl interface is the ndctl device's fops | bus.c nvdimm_bus_fops |

The class core defines no DEVICE_ATTR entries; all nd-bus attributes the
kernel exports belong to the bus/device tree (bus nd, dimm, region, dax
devices), which the ledger tracks under non-class prefixes and the dax ABI
file, not here.

## Safety and writes

Nothing under /sys/class/nd is writable: the ndctl device is the functional
interface, and its ioctls issue ARS (address range scrub), error-clear and
config commands against the platform's NVDIMM hardware, so any privilege
discussion belongs to /dev/ndctl<n> and the ndctl(1) tooling, not to sysfs.
Removing the region or namespace devices (echoing into their own tree, e.g.
under /sys/bus/nd or the pmem block device) is how namespaces get torn down;
doing so through the wrong node is a common confusion that this page cannot
instruct about because the nd class itself exposes no such files.

## References

- drivers/nvdimm/bus.c, fetched from raw.githubusercontent.com/torvalds/linux/master
- Documentation/ABI/testing/sysfs-bus-dax (adjacent dax tree, 18 What: entries; cached at source-cache/linux-sparse)
- Live enumeration /sys/class/nd, /sys/dev/char/253:0, /sys/dev/block/253:0 (read-only, kernel 5.10.134)
- Sibling pages: [block](./block.md), [devlink](./devlink.md); coverage: [ledger](../ledger.md)
