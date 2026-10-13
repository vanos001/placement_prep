# /sys/class/mtd

| Field | Value |
|---|---|
| Subsystem | MTD core, drivers/mtd/mtdcore.c (class `mtd_class`, devices mtd%d) |
| Config gate | CONFIG_MTD, "Memory Technology Device (MTD) support" (drivers/mtd/Kconfig) |
| ABI documentation | Documentation/ABI/testing/sysfs-class-mtd (22 What: entries) |
| Since | Class and base attrs 2.6.29 (April 2009); ecc_strength and bitflip_threshold 3.4; ecc_step_size 3.10; ecc_failures, corrected_bits, bad_blocks, bbt_blocks 3.17; offset 4.1; oobavail 4.16 (all from the ABI file) |
| Live (5.10.134 host) | none observed (no flash device in the container) |
| Ledger ID | SYSC-mtd |

## What it represents

One directory per MTD device or partition, corresponding to each /dev/mtdX character device, plus a read-only twin directory mtdXro for the read-only device node (minor odd; the read-write node has an even minor). Entries may be physical or simulated flash, partitions, or concatenated devices.

## Relationship to the device model

The class device is registered by mtdcore.c with dev_set_name "mtd%d". The `name` attribute matches the entry in /proc/mtd, the historical procfs twin, so the two views can be reconciled. IOCTLS on the char device (MEMGETREGIONCOUNT, MEMGETREGIONINFO) complement the sysfs geometry attributes.

## Attributes (representative; source: ABI testing/sysfs-class-mtd)

| Attribute | R/W | Meaning |
|---|---|---|
| `type` | RO | absent, ram, rom, nor, nand, mlc-nand, dataflash, ubi, unknown |
| `flags` | RO | Hex flags: 0x0400 MTD_WRITEABLE, 0x0800 MTD_BIT_WRITEABLE, 0x1000 MTD_NO_ERASE, 0x2000 MTD_POWERUP_LOCK |
| `size` | RO | Total size of device or partition in bytes |
| `erasesize` | RO | Major erase size; when numeraseregions is 0 this is the whole-device eraseblock size |
| `writesize` | RO | Minimal writable unit: 1 for NOR, a page (or fraction) for NAND |
| `oobsize`, `oobavail` | RO | OOB bytes per page; bytes a client may use |
| `numeraseregions` | RO | Number of variable erase regions, 0 if uniform |
| `name` | RO | ASCII name matching /proc/mtd |
| `dev` | RO | <major>:<minor> of the char device |
| `ecc_strength`, `ecc_step_size` | RO | Correctable bit errors per ECC step; step size in bytes (0 without ECC) |
| `bitflip_threshold` | 0644 | Threshold for returning -EUCLEAN from reads; default ecc_strength; users are discouraged from changing it |
| `ecc_failures`, `corrected_bits` | RO | ECC failure and correction counters |
| `bad_blocks`, `bbt_blocks` | RO | Marked-bad and reserved (BBT) block counts in this partition |
| `offset` | RO | Partition offset from parent start; absent on full devices, so it distinguishes partitions |

## Safety and writes

The only write path is `bitflip_threshold`, which changes how reads report degradation; the ABI text warns against adjusting it without intimate device knowledge. Erasing and writing happen through the char device, not sysfs. None observed on the container host.

## References

- Documentation/ABI/testing/sysfs-class-mtd
- drivers/mtd/mtdcore.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [char devices](../../kernel/drivers/char-devices.md)
