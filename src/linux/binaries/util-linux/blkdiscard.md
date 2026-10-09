# blkdiscard — discard (TRIM) sectors on a block device

## Overview

`blkdiscard` issues a discard request — the block layer's `TRIM`/`UNMAP`
operation — against a range of a block device, telling the storage: "the
contents of these sectors are garbage; you may forget them." On SSDs and
thin-provisioned storage this releases physical cells or pool space, which
is why the tool exists. It ships in the `util-linux` package at
`/usr/sbin/blkdiscard` and is the block-device-level sibling of
`fstrim`, which does the same thing filesystem-aware and per-mount.

You reach for it when wiping a device you are about to return to a pool
(cheap and fast compared to `dd`), when reclaiming space on
thin-provisioned LVM or SAN volumes, when zeroing/erasing flash before
reprovisioning, or when testing whether a device honors discards at all.
It is often confused with `fstrim` (filesystem level, periodic, refuses
whole mounted disks), with `wipefs` (removes signatures, not cell data),
and with plain `dd if=/dev/zero` (slow, writes actual bytes, and on SSDs
causes wear instead of relieving it).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/blkdiscard |
| First appeared | util-linux 2.23 (2012) |
| Standards | Linux block-layer discard / WRITE ZEROES ioctls |

## Synopsis

```
blkdiscard [options] <device>
```

Main one-line forms:

```
blkdiscard /dev/sdb                  # discard the whole device
blkdiscard -s /dev/sdb               # secure discard (erase cells)
blkdiscard -z /dev/vdb               # write zeroes instead of discarding
blkdiscard -o 1M -l 100M /dev/nvme0n1
```

The device must be given; there is no "all devices" mode — by design, since
the operation is destructive.

## How It Works

### What a discard actually is

A discard is a *hint*, not a write. The block layer converts
`blkdiscard`'s request into an opcode on the wire:

```
device family        what blkdiscard triggers
-----------------    --------------------------------------------
SATA/SCSI SSD        ATA TRIM / SCSI UNMAP — ranges marked invalid
NVMe SSD             NVMe Deallocate — ranges marked invalid
thin LV / SAN        UNMAP to the backing pool — space is returned
loop device          punch-hole (fallocate) into the backing file
zoned (SMR/ZNS)      zone reset via the same request path
```

Afterwards a read of the range returns *something* — zeros on most SSDs,
unspecified on some — but the device is free to remap the cells, which is
what makes the operation fast and wear-friendly. That is also why "discard"
is not an erase standard: controllers may keep data in over-provisioned
areas. `-s` (secure) asks the device to make the data unrecoverable, but
support is optional and frequently missing.

### Alignment and the length math

The device advertises discard granularity and alignment in sysfs:

```
$ cat /sys/block/sdb/queue/discard_granularity
4194304                      # 4 MiB — discard requests should align to this
$ cat /sys/block/sdb/queue/discard_max_bytes
1073741824                   # 1 GiB cap per request
```

`-o` (offset) and `-l` (length) are **bytes**, and the kernel rounds them
to the device's discard alignment. `-v` prints the aligned values the tool
actually used:

```
$ blkdiscard -v -o 100M -l 10M /dev/sdb
blkdiscard: /dev/sdb: offset aligned to 104857600, length aligned to 12582912
#        (100M start was unaligned; kernel rounded up to the 4 MiB grid)
```

Without `-l`, the whole device from `-o` is discarded. `-p <size>` walks
the range in steps — useful because some devices and drivers choke on very
large single requests.

### Discard vs zeroout

```
$ blkdiscard -z /dev/sdb      # WRITE ZEROES path: reads after return are zeros
$ blkdiscard    /dev/sdb      # UNMAP path:      reads are "don't care"
```

`-z` uses the `BLKZEROOUT`/write-zeroes machinery: it is deterministic
(verified zeros) and still cheaper than `dd` on storage that offloads it,
but it does not necessarily release cells. A safe wipe-then-reuse recipe on
modem SSDs is `-z`; a space-reclamation recipe on thin storage is plain
discard; an at-rest-eradication attempt is `-s`, if the device supports it
at all.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-o, --offset <num>` | Start offset in bytes (suffixes KiB/MiB/GiB accepted) |
| `-l, --length <num>` | Range length in bytes; default: to end of device |
| `-p, --step <num>` | Issue the request in chunks of this many bytes |
| `-s, --secure` | Request *secure* erase (device must support it) |
| `-z, --zeroout` | Zero-fill the range instead of unmapping it |
| `-f, --force` | Skip the "device looks in use" safety check |
| `-v, --verbose` | Print the aligned offset/length actually used |
| `-q, --quiet` | Suppress the warning messages |

Size arguments accept binary suffixes with or without the trailing `iB`
(`1M` = 1 MiB), unlike `blkzone` where all values are 512-byte sectors —
a recurring trap when switching between the two tools.

## Usage Patterns

```bash
# Retire a disk: fastest possible wipe before resale/reprovision
blkdiscard /dev/sdb
```

```bash
# Securely erase an SSD that advertises secure discard support
blkdiscard -f -s /dev/nvme0n1
#   (fails with EOPNOTSUPP on devices without secure trim)
```

```bash
# Wipe only the partition you are reusing, not the whole disk
blkdiscard -o 1G -l 20G /dev/sda3
```

```bash
# Reclaim space of a removed VM disk image on thin-provisioned storage
lvremove vg/oldvm
blkdiscard /dev/vg/thinpoolmeta-check  # pool handles UNMAPs automatically;
                                       # blkdiscard used on the LV *before* lvremove
```

```bash
# Deterministic zeroing of a fresh volume before LUKS (measurable, fast)
blkdiscard -z /dev/vdb
cryptsetup luksFormat /dev/vdb
```

```bash
# Device hangs on big discards? Step in 512 MiB chunks
blkdiscard -p 512M /dev/sdb
```

```bash
# Does this device honor discards at all?
cat /sys/block/sdb/queue/discard_granularity   # nonzero => supported
blkdiscard -v -o 0 -l 4M /dev/sdb
```

```bash
# Loop devices: punch holes in the backing file, watch df shrink
truncate -s 1G sparse.img && losetup /dev/loop0 sparse.img
blkdiscard /dev/loop0
ls -lh sparse.img      # back to ~0 bytes actually allocated
```

```bash
# Script guard: never discard anything mounted
mountpoint -q /mnt && echo "refusing: mounted" || blkdiscard /dev/sdb2
```

## Nuances and Gotchas

- **No undo, no confirmation.** One keystroke destroys the filesystem on
  the target. `blkdiscard` warns and asks for `-f` only when the device
  appears in use; an unmounted-but-important device is erased silently.
  Double-check the device node: `sdb` vs `sdb1` differ by one character.
- **Discard ≠ erase.** Plain discard is a performance/space hint; data may
  survive in over-provisioned flash. `-s` is the erase flavor but is often
  unsupported, and standards-based verification of secure erase is weak.
  For compliance-grade wiping, use vendor tools or cryptographic erasure.
- **Bytes here, sectors in blkzone.** `-o`/`-l` are bytes (with suffixes);
  in `blkzone` the same-named options count 512-byte sectors. Mixing them
  up is a classic off-by-8x or off-by-512x error.
- **Read-after-discard is undefined.** Some devices return zeros, some
  return stale data. Code that depends on reading zeros after a discard
  should use `-z` (zeroout) or `--getdiscardzeroes` in `blockdev` to check
  the DA0 capability first.
- **Alignment is silently fixed.** Unaligned offset/length are rounded to
  the device's discard alignment; `blkdiscard -v` is the only way to see
  what was actually requested. Rarely matters for whole-device wipes,
  matters a lot for surgical `-o/-l` use.
- **Swap and mounted devices.** Discarding a mounted filesystem's device
  corrupts it — the kernel may allow it with `-f`, but nothing will save
  the data. Swapoff before discarding the swap partition.
- **fstrim does this better for filesystems.** For periodic maintenance on
  mounted SSDs, `fstrim.timer` is the intended mechanism; `blkdiscard` is
  for device-level work.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All discard requests succeeded |
| 1 | Usage error, device open failed, unsupported operation (e.g. secure discard not implemented), or I/O error |

## Related Commands

- [`blockdev`](./blockdev.md) — `--getdiscardzeroes`, `--getsz`, and other block-device queries
- [`blkzone`](./blkzone.md) — zone reset/management for zoned devices; also sector-unit based
- [`blkid`](./blkid.md) — verify the device really has no filesystem before you discard it
- [util-linux overview](./overview.md) — the rest of the block-device toolset
- [Linux internals](../../internals.md) — how discards flow through the block layer

## Interview Questions

### Q: What is the difference between blkdiscard, fstrim, and wipefs?

`blkdiscard` operates on a block device range at the block layer and is
destructive to whatever filesystem was there. `fstrim` walks a *mounted*
filesystem, asks it which extents are free, and discards exactly those —
it never destroys live data. `wipefs` only erases filesystem/RAID
signature bytes (magic strings) from the device, releasing it from
auto-detection, without unmapping cells or erasing content.

### Q: Why might blkdiscard succeed but a later read return garbage instead of zeros?

Because a discard is an unmapping hint. The controller promises to forget
the mapping, not to write zeros; read behavior after unmap is
implementation-defined. If a workflow needs deterministic zeros, it should
use `blkdiscard -z` (write zeroes) and optionally verify that the device
advertises a write-zeroes or discard-zeroes-data capability.

### Q: How do you check whether a device supports discards and secure discard before relying on them?

Discard support: nonzero `/sys/block/<dev>/queue/discard_granularity` and
`discard_max_bytes`. Secure-discard support is not exposed there reliably —
the practical test is running `blkdiscard -s` on a scratch device and
looking for `EOPNOTSUPP`, or checking the transport capabilities
(`hdparm -I`, NVMe identify data). Interviewers like the point that
`blockdev --getdiscardzeroes` tells you whether the device promises
read-as-zero after discard.

### Q: Why is blkdiscard preferred over dd if=/dev/zero when wiping an SSD?

`dd` writes every byte, saturating the device for the full capacity and
burning P/E cycles; on thin storage it also *allocates* all backing space —
the opposite of what you wanted. `blkdiscard` sends one ioctl per range,
completes in seconds regardless of device size, relieves rather than adds
flash wear, and can be made deterministic with `-z` when zeros are required.

### Q: What does the -f (force) flag actually check?

It disables blkdiscard's own safety heuristic that refuses (or warns on)
devices that appear to be in use — partitioned devices, devices with
holders in /sys (LVM, md), or mounted filesystems. It does not and cannot
protect you from wiping a disk the kernel considers idle but your workload
needs; `-f` is a way to say "I checked" to the tool, not a safety net.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/blkdiscard.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
