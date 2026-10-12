# /sys/class/misc

| Field | Value |
|---|---|
| Subsystem | Character device core; drivers/char/misc.c (misc_class, misc_register) |
| Config gate | misc.o is obj-y in drivers/char/Makefile (no Kconfig gate for the class itself; each member driver has its own) |
| ABI documentation | Documentation/ABI/testing/sysfs-driver-xdata only (2 What: entries: dw-xdata-pcie.<device>/read, /write, KernelVersion 5.13) |
| Since | Source-established for the class (MISC_MAJOR 10); per-device attrs date from their drivers |
| Live (5.10.134 host) | 75 entries: cpu_dma_latency, dbom_virtio_tool, device-mapper, fuse, hw_random, ioasid_user, loop-control, tun, uinput, virtfuse0-63, vsock, vvu |
| Ledger ID | SYSC-misc |

## What it represents

The misc catch-all class for character drivers that do not warrant a major
number of their own: each driver calls misc_register() with a struct
miscdevice and gets a directory named after misc->name, under MISC_MAJOR 10
with either a fixed minor or MISC_DYNAMIC_MINOR. The class core creates no
attributes; device_create_with_groups() attaches whatever attribute group the
registering driver supplied. What a directory contains therefore varies
wildly: fuse and tun have empty dev dirs here, while driver-specific files
like the dw-xdata-pcie traffic-generator controls (the only two entries
documented in Documentation/ABI) appear on hardware that has that driver.

## Relationship to the device model

misc_class carries a devnode callback (misc_devnode) so devtmpfs can apply
per-driver node modes. The /proc/misc file is the procfs twin listing
registered minors and names. Member devices parent under their real device
when misc->parent is set. The live population shows how kernel config drives
the class: all 75 entries are built into this host's kernel (the 64
virtfuseN instances are an Alibaba kangaroo in-tree-style driver family,
live-verified here but not part of mainline ABI documentation).

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| cpu_dma_latency/dev | RO | 10:60 | live check (5.10.134) |
| device-mapper/dev | RO | 10:236 | live check |
| fuse/dev | RO | 10:229 | live check |
| hw_random/dev | RO | 10:183 | live check |
| loop-control/dev | RO | 10:237 | live check |
| tun/dev | RO | 10:200 | live check |
| uinput/dev | RO | 10:223 | live check |
| vsock/dev | RO | 10:61 | live check |
| vvu/dev | RO | 10:63 | live check |
| dbom_virtio_tool/dev | RO | 10:62 | live check (host-specific driver) |
| dw-xdata-pcie.<device>/read, /write | WO | trigger PCIe traffic generator in read or write direction | ABI sysfs-driver-xdata, 5.13; driver-specific, absent on this host |

Fixed minors for the named devices come from their drivers' miscdevice
declarations; the class assigns dynamic minors where MISC_DYNAMIC_MINOR is
used, so numbers can differ across kernels and module load order.

## Safety and writes

The class directory itself exposes only dev/uevent style files: nothing to
write. Every real interface belongs to the member driver and lives in its
/dev node or its driver-provided sysfs files (the ABI-documented dw-xdata
files are write-only triggers). Do not infer behavior from the class: tun,
fuse, uinput and loop-control are ioctl-driven, and cpu_dma_latency is a
PM QoS parameter file documented outside ABI. Treat unexplained entries
(here virtfuseN, dbom_virtio_tool) as vendor drivers: identify them via
/proc/misc and uevent MODALIAS, not by ABI docs that do not exist.

## References

- drivers/char/misc.c, include/uapi/linux/major.h (MISC_MAJOR 10), fetched from raw.githubusercontent.com/torvalds/linux/master
- Documentation/ABI/testing/sysfs-driver-xdata (cached at source-cache/linux-sparse)
- Live enumeration /sys/class/misc with per-entry dev reads (read-only, kernel 5.10.134)
- Sibling pages: [mem](./mem.md), [cpuid](./cpuid.md); coverage: [ledger](../ledger.md)
