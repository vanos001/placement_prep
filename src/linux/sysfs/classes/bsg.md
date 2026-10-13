# /sys/class/bsg

| Field | Value |
|---|---|
| Subsystem | Block layer SCSI generic v4, block/bsg.c (class `bsg_class`) and block/bsg-lib.c (queue plumbing); uapi struct sg_io_v4 in include/uapi/linux/bsg.h |
| Config gate | CONFIG_BLK_DEV_BSG "/dev/bsg support (SG v4)", bool, depends on SCSI, default y; helper lib CONFIG_BLK_DEV_BSGLIB (block/Kconfig, drivers/scsi/Kconfig) |
| ABI documentation | none found - checked the stable/, testing/ and obsolete/ ABI listings and grep for bsg; attributes are traced to block/bsg.c instead |
| Since | not stated by the sources checked; the source carries only the driver version string "0.4" (BSG_VERSION, block/bsg.c) |
| Live (5.10.134 host) | class present with 0 entries (no bsg device on the container) |
| Ledger ID | SYSC-bsg |

## What it represents

Char devices (one per request queue registered via bsg_register_queue()) that speak the SG v4 protocol: requests described by struct sg_io_v4. iSCSI hosts create bsg nodes named iscsi_host`<N>` (drivers/scsi/scsi_transport_iscsi.c bsg_setup_queue) so iscsiadm can send transport-specific commands.

## Relationship to the device model

Each bsg device is created against a parent device and request queue (bsg.c); when the queue belongs to a disk, a "bsg" symlink is created from the disk's queue kobject to the bsg device (sysfs_create_link, bsg.c). The class has no attributes of its own; the interface is the char device, which the devnode callback places under /dev/bsg/.

## Attributes

None. The class `bsg_class` defines only .name and .devnode (block/bsg.c); there is no attribute group. All observable state is: the device name (set by the registering driver), the dynamically allocated major number ("bsg", alloc_chrdev_region) and the /dev/bsg/`<name>` node created by the devnode callback (kasprintf "bsg/%s").

## Safety and writes

Commands passed through the char device are SCSI commands issued against the hardware; the minor space is capped at BSG_MAX_DEVS devices ("too many bsg devices" error otherwise). No sysfs writes exist. The class is present but empty on the container host, which is expected on hosts without SCSI transports that register bsg queues.

## References

- block/bsg.c, block/bsg-lib.c, include/uapi/linux/bsg.h (fetched from torvalds/linux master into source-cache)
- drivers/scsi/scsi_transport_iscsi.c (iscsi_host bsg queue)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [block devices](../../kernel/block/devices.md), [SCSI storage page](../../storage/scsi-nvme.md), [iscsi_host](./iscsi_host.md)
