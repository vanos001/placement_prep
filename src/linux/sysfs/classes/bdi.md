# /sys/class/bdi

| Field | Value |
|---|---|
| Subsystem | Memory management writeback; mm/backing-dev.c (bdi_class, bdi_dev_attrs) |
| Config gate | None; backing-dev.o is obj-y in mm/Makefile, postcore_initcall(bdi_class_init) |
| ABI documentation | Documentation/ABI/testing/sysfs-class-bdi (10 What: entries) |
| Since | January 2008 (class, read_ahead_kb, min_ratio, max_ratio, stable_pages_required); October 2022 (min_bytes, max_bytes, strict_limit); November 2022 (min_ratio_fine, max_ratio_fine) |
| Live (5.10.134 host) | 9 entries: 0:41, 0:46, 0:51-0:54, 253:0, 254:0, 259:0; no "default" dir |
| Ledger ID | SYSC-bdi |

## What it represents

One directory per backing_dev_info object: the per-filesystem or per-block-device
writeback state that the VM uses to decide how much dirty page cache each
consumer may hold and how fast to clean it. The ABI file names three identifier
shapes: MAJOR:MINOR for block devices and for filesystems that register the
device they sit on, MAJOR:MINOR-fuseblk for fuseblk mounts, and "default" for
filesystems without their own BDI. mm/backing-dev.c itself takes the directory
name from the registrant: bdi_register_va() formats bdi->dev_name with the
caller's printf string and calls device_create(&bdi_class, NULL, MKDEV(0, 0),
bdi, bdi->dev_name). genhd.c registers every visible disk as "%u:%u"
(major:first_minor); the six 0:N directories on the live host are anonymous
(non-device-backed) BDIs whose owners are not discoverable from sysfs alone.

## Relationship to the device model

Every bdi class device is created with devt 0:0, so the class has no dev
attribute and creates no /dev nodes. The link from device to BDI goes the
other way: genhd.c creates a "bdi" symlink inside each disk directory
(/sys/devices/.../block/vda/bdi). Live: 253:0 matches zram0, 254:0 matches
vda, 259:0 matches pmem0. No device symlink exists inside the bdi dirs.

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| read_ahead_kb | RW | read-ahead window, KiB; live 253:0 = 128 | ABI, January 2008; bdi_dev_attrs[] |
| min_ratio | RW | minimum percent of writeback cache | ABI, January 2008 |
| min_ratio_fine | RW | minimum, parts per million | ABI, November 2022 |
| max_ratio | RW | maximum percent of writeback cache | ABI, January 2008 |
| max_ratio_fine | RW | maximum, parts per million | ABI, November 2022 |
| min_bytes | RW | minimum reserve in bytes | ABI, October 2022 |
| max_bytes | RW | maximum in bytes | ABI, October 2022 |
| strict_limit | RW | enforce per-BDI limit before global dirty limit; no effect at max_ratio 100 | ABI, October 2022 |
| stable_pages_required | RO | pages must stay stable during writeout | ABI, January 2008 |

All nine attributes exist on every BDI directory; the live 253:0 listing
matches this set exactly (plus the standard core files power/, subsystem,
uevent).

## Safety and writes

Reads are safe. ratio/bytes writes change global dirty-throttling behavior:
raising max_ratio or max_bytes lets one slow or untrusted device hold more
dirty page cache (the ABI file cites stuck NFS mounts and FUSE as the use
case); lowering min_ratio reserves QoS for a device. strict_limit has no
visible effect while max_ratio is 100. Wrong values are clamped or rejected
by the store handlers, but a careless cap on the root device's BDI throttles
the whole system. There is no "default" directory to tune on this host.

## References

- Documentation/ABI/testing/sysfs-class-bdi (cached at source-cache/linux-sparse)
- mm/backing-dev.c, block/genhd.c (bdi_register "%u:%u" + bdi symlink), fs/super.c (super_setup_bdi_name), fetched from raw.githubusercontent.com/torvalds/linux/master
- Live enumeration /sys/class/bdi and /sys/class/bdi/253:0 (read-only, kernel 5.10.134)
- Sibling pages: [block](./block.md); coverage: [ledger](../ledger.md)
