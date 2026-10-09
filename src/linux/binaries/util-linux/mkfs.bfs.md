# mkfs.bfs — create SCO BFS boot filesystems

## Overview

`mkfs.bfs` builds a BFS (Boot File System) — a minimal filesystem originally from SCO OpenServer, adopted by Linux in the late 1990s for its boot-floppy images. It is one of the smallest filesystem builders in util-linux: a few hundred lines implementing a fixed-layout, contiguous-allocation filesystem whose entire selling point was predictable, simple reads by a boot loader. Today it is a museum piece that still ships because the kernel driver (`fs/bfs`) is still there and because it is a perfect teaching artifact.

It ships in the `util-linux` package at `/usr/sbin/mkfs.bfs`. It is often confused with the other built-in family members `mkfs.minix` and `mkfs.cramfs` (all three: tiny, legacy, util-linux-native), and — famously — with *any other mkfs helper's option conventions*, because BFS's `-V` and `-F` mean volume-name and filesystem-name, not version and force.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/mkfs.bfs |
| First appeared | late 1990s (SCO BFS lineage; Linux boot-disk tooling) |
| Standards | None — legacy/teaching filesystem |

## Synopsis

```
mkfs.bfs [options] <device> [blocks]
```

Common one-line forms:

```
mkfs.bfs /dev/fd0             # classic boot floppy
mkfs.bfs -N 48 image.img      # fixed inode count
mkfs.bfs -V BOOT -F image.img # volume name BOOT, fs name "image"
```

## How It Works

### The on-disk idea

BFS assumes a single purpose: hold a handful of boot files that a loader reads linearly. Everything follows from that:

- fixed **512-byte blocks**;
- the superblock (block 1) carries magic `0x1BADFACE`, the block/inode counts, and two short name fields (volume name, filesystem name);
- **inodes are allocated from the start of the device, data from the end** — each file's blocks are contiguous, appended as files are written;
- directories are tiny fixed-size entries; filenames are short;
- there is **no free-block bitmap and no reuse**: space is handed out monotonically.

```
block: 1            2..k          k+1 ......... N
     ┌──────────┬────────────┬─────────────────────┐
     │ super    │ inodes     │ data (allocated     │
     │ 0x1BADFACE│ (fixed     │ contiguously,       │
     │ + names  │  count)    │ from the end)       │
     └──────────┴────────────┴─────────────────────┘
```

That layout is why the builder is trivial: compute the inode zone, stamp the superblock, and exit. It is also why the filesystem cannot evolve — every property is baked into the fixed geometry.

### Superblock anatomy, byte for byte

The superblock occupies block 1 (absolute offset 512); every field after the magic is a 32-bit little-endian word, which makes the format trivially inspectable with `xxd`:

```
offset  size  field       meaning
512     4     s_magic     0x1BADFACE (little-endian bytes: CE FA AD 1B)
516     4     s_start     first block of the free/data area
520     4     s_end       last block of the data area
524     4     s_from      start of last backup range (dump bookkeeping)
528     4     s_to        end of last backup range
532     4     s_bfrom     block-ordered backup start
536     4     s_bto       block-ordered backup end
540     6     s_fsname    filesystem name  (-F, 6 bytes, not NUL-terminated)
546     6     s_volume    volume name      (-V, 6 bytes, not NUL-terminated)
552     ...   padding to end of block
```

The two name fields explain the `-V`/`-F` collision completely: they are SCO-compatible fixed 6-byte slots, so `-V BOOT` and `-F ROOT` are literal byte writes, and anything longer is rejected. Inodes are fixed-size records holding the run encoding of each file — start block, end block, end offset — which is how the format avoids an extent tree entirely: a file IS one contiguous run. Directory entries are likewise fixed 16-byte records: a 2-byte inode number plus a 14-byte name field, so filenames cannot exceed 14 characters. The root directory is always inode 2.

### Capacity math and the size operand

The optional trailing `blocks` operand caps the filesystem size in 512-byte blocks; without it, mkfs.bfs sizes from the device. The geometry keeps the filesystem in the low hundreds of MiB at most — boot floppies and boot partitions were the target, and the format has no mechanism for anything larger.

### Deletion is a leak

Because freed space is never reclaimed (no bitmap, no allocator state to update), deleting a file on BFS does not make its blocks available again. Writes continue from the high-water mark. For a boot image written once at install time that was acceptable; for anything else it is disqualifying — and it is the standard "why did this design die" interview answer.

### Where you would actually use it

Realistically: OS courses reproducing boot-disk layouts, archaeology on 1990s installation media, kernel-driver experiments (`fs/bfs` is a compact read), and image-format trivia. For real boot media, modern systems use FAT (EFI) or ext-family images — nothing current consumes BFS.

### What creation actually does, step by step

`mkfs.bfs` is a few hundred lines because "formatting" degenerates to three writes:

1. compute the fixed geometry from the device size (or the `blocks` operand) and the `-N` inode count — inode area size follows from the record size, data area is whatever remains;
2. write the inode area: all records zeroed except inode 2, the root directory, pre-created empty;
3. write the superblock: magic, both name fields, and the block-range fields delimiting the data area.

No bitmap exists to initialize, no journal to create, no free-list to seed — the allocator state *is* the two high-water marks in the superblock. That is the entire feature set; `mkfs.ext4`'s hundred of groups, descriptor tables, and feature flags are all absent by construction, and `-v` exists only to narrate these steps.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-N, --inodes <num>` | Number of inodes to reserve (fixed at creation — the fs cannot grow it) |
| `-V, --vname <name>` | Set the **volume name** stored in the superblock (short field) |
| `-F, --fname <name>` | Set the **filesystem name** stored in the superblock (short field) |
| `-v, --verbose` | Explain what is being done |
| `-h, --help` / `-V...` | Help; note the naming collision described below |

The famous trap: on every other util-linux tool `-V` is `--version` and `-F` is `--force`. Here `-V` is *volume name* and `-F` is *filesystem name* — SCO BFS compatibility won over convention. Name fields are tiny; long values are rejected/truncated, so keep them to a few characters.

## Usage Patterns

```bash
# The classic: format a 1.44M floppy image as BFS
dd if=/dev/zero of=bfs.img bs=1024 count=1440
mkfs.bfs bfs.img
```

```bash
# Reserve a specific number of inodes up front
mkfs.bfs -N 32 bfs.img
```

```bash
# Stamp identifying names into the superblock (short values!)
mkfs.bfs -V BOOT -F ROOT bfs.img
```

```bash
# Verify the magic number landed where expected
xxd -s 512 -l 16 bfs.img    # ...1BADFACE...
```

```bash
# Verbose build shows the computed geometry
mkfs.bfs -v bfs.img
```

```bash
# Explicit size in 512-byte blocks instead of full device
mkfs.bfs -N 16 bfs.img 2048
```

```bash
# Layout is deterministic: block 1 superblock, then inode area, then data
dd if=bfs.img bs=512 skip=2 count=2 status=none | xxd | head -8   # inode area
```

```bash
# Format a loop device instead of a file
losetup /dev/loop7 bfs.img && mkfs.bfs /dev/loop7
```

```bash
# Boot-image build order: mkfs first, then populate once, in final order,
# because every write appends and nothing is ever moved
mkfs.bfs -N 32 -V BOOT -F ROOT boot.img
# mount -o loop boot.img /mnt/b && cp -a kernel initrd /mnt/b/ && umount /mnt/b
```

```bash
# Never trust it with real data — demonstrate the delete-does-not-reclaim leak
mkfs.bfs bfs.img 2048
# (mount, write until full, delete, write again -> no space returned)
```

```bash
# Through the generic dispatcher
mkfs -t bfs bfs.img
```

```bash
# Inspect the stamped fields with byte offsets from the table above
xxd -s 512 -l 4 bfs.img      # magic: CE FA AD 1B  (0x1BADFACE little-endian)
xxd -s 540 -l 12 bfs.img     # the two 6-byte name fields (-F value, then -V)

# Confirm the kernel can actually mount BFS before building images
grep CONFIG_BFS_FS "/boot/config-$(uname -r)"    # =y builtin, =m module, absent = no
```

```bash
# Archaeology: verify an old BFS floppy image without mounting it
xxd -s 512 -l 4 ancient.img     # expect bytes CE FA AD 1B (magic, little-endian)
xxd -s 540 -l 12 ancient.img    # the -F name, then the -V name, 6 bytes each
```

## Nuances and Gotchas

- **`-V` and `-F` do not mean version/force here.** This is the headline gotcha: scripts generated by analogy with other mkfs helpers will silently set a volume name to "force" or fail on odd version strings. Check this page, not muscle memory.
- **The option family is tiny — no dry run, no label flag beyond `-V`.** Compared with every modern mkfs helper there is no `-n` preview, no UUID (the format has none), no alignment or discard handling. Anything you expect from mke2fs is simply absent; the correct expectation is "three writes and out".
- **The `blocks` operand can shrink the fs below the device, never grow it.** If you omit it the full device is consumed; there is no resize afterwards in either direction, so size once, correctly, at image-build time.
- **Names in the superblock are tiny.** Volume/filesystem names are short fixed fields; long strings are refused. Don't try to smuggle labels through them.
- **No space reclamation, ever.** Deletions leak blocks until rebuild. Anything long-lived on BFS fills up monotonically — by design.
- **Fixed inode count at creation.** Too few inodes = ENOSPC-style failures despite free blocks; too many = wasted fixed zone. `-N` is your only control and cannot be changed afterwards.
- **512-byte block geometry.** All size math (including the `blocks` operand) is in 512-byte units, unlike the 1 KiB convention of the minix family — a small but classic off-by-factor trap.
- **It is not a modern filesystem.** No journaling, no permissions richness worth mentioning, tiny name limits, small capacity ceilings. Use it to study, not to serve.
- **Busybox does not ship it.** It is util-linux-specific (and in the built-in family, not a split package).
- **There is no fsck.bfs.** No checker ships for BFS — the util-linux built-ins cover minix (mkfs+fsck), cramfs (mkfs+fsck), and BFS (mkfs only). Corruption on BFS is unrepairable by tooling; the recovery story is "rebuild the image", consistent with its write-once design.
- **Mounting needs CONFIG_BFS_FS.** Nothing else uses BFS, so many distro kernels still build it (it is tiny) but some minimal/embedded kernels omit it; a mount then fails with "unknown filesystem type". Check the kernel config before assigning BFS to a real boot path.
- **File placement is creation order.** Because data is appended contiguously from the high-water mark, the order files are written defines the physical layout. Boot-loaders that assumed linear reads got exactly that — and anything that rewrites a file in place (editors) breaks the contiguity assumption on the next write.
- **Filenames cap at 14 characters — enforced at mount time, not by mkfs.** `mkfs.bfs` stamps geometry only; the 14-byte name field in each directory entry is a kernel-driver limit (`fs/bfs`). Names you pack into an image must respect it regardless of what the builder accepted.
- **There is nothing to mount it with in many minimal kernels.** BFS support is a build-time option and worth checking (`grep CONFIG_BFS_FS /boot/config-$(uname -r)`) before committing to the format; a container or trimmed appliance kernel frequently lacks it, and mkfs.bfs happily produces images nothing on that host can read.

## Exit Status

- `0` — filesystem created.
- `8` — operational error (I/O failure, unwritable device, geometry problem).
- `16` — usage error (bad option, invalid name or block count).

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`mkfs`](./mkfs.md) — the dispatcher that finds `mkfs.bfs` for `mkfs -t bfs`.
- [`mkfs.minix`](./mkfs.minix.md) — fellow tiny util-linux builder (writable, checkable).
- [`mkfs.cramfs`](./mkfs.cramfs.md) — fellow read-oriented builder for boot images.

## Interview Questions

### Q: Why does BFS allocate data from the end of the device and inodes from the start?

To keep allocation trivially contiguous: appending a file never needs a search for free extents — the next write goes to the current high-water mark, and the loader reads files as straight runs. It trades all flexibility (reclamation, compaction) for predictable linear layout, which is exactly what boot-time code wanted.

### Q: What are the option-name collisions in mkfs.bfs and why do they matter?

`-V` means volume name and `-F` means filesystem name — not version and force as in the rest of util-linux. Scripts written by analogy set nonsense names or fail; the lesson is that even within one family, option semantics are per-binary and must be verified. It is a memorable example of interface inconsistency in Unix tooling.

### Q: What happens when you delete a file on a BFS filesystem, and why?

The blocks are leaked permanently: BFS has no free-block bitmap and its allocator only advances. Deletion clears the inode/directory entry but nobody tracks the freed region. The design assumed write-once boot images; the same property is why the format died the moment anything dynamic was attempted.

### Q: Where does the magic 0x1BADFACE live and what is it for?

In the superblock at block 1 (offset 512 into the device). Magic numbers let the kernel driver (`fs/bfs`) confirm it is looking at the right structure before trusting counts and offsets — the same validation pattern every filesystem uses, visible here in a format small enough to memorize.

### Q: Why would a course teach filesystems with mkfs.bfs instead of mkfs.ext4?

Because the whole format fits in a page: fixed 512-byte blocks, one superblock with magic and names, a fixed inode zone, contiguous data allocation from the end, no bitmap. Students can implement, inspect with xxd, and break it meaningfully. ext4's journal, extents, and checksums bury the same concepts under orders of magnitude more machinery.

### Q: You must serve a boot image to a loader that reads files linearly. Compare mkfs.bfs, mkfs.cramfs, and a plain FAT image for that job.

BFS guarantees contiguity by construction — each file is one run — but leaks deleted space and has no checker, so it only suits write-once images. cramfs is compressed and read-only, ideal when image size matters, and is checked by fsck.cramfs, but random-access reads decompress per page. FAT is the only one a modern firmware (EFI) actually consumes, at the cost of a FAT driver's complexity and cluster-chain reads. The senior answer notes the deciding variable is the *consumer*: SCO-era loaders (BFS), kernel initramfs-style read-only use (cramfs), firmware (FAT).

### Q: Inodes from the start, data from the end — what breaks if a BFS image is filled close to capacity?

The two zones grow toward each other with no reservation between them: once the inode area and the data high-water mark meet, the filesystem is full in both directions at once. With `-N` you choose the split point — too few inodes fails on file count, too many steals data capacity permanently, and nothing can rebalance afterwards. It is the same fixed-provisioning trade as Minix, made harsher by the absence of any free-space accounting between the fronts.

### Q: Why does BFS need no allocator search, and what single data structure encodes a file's location?

Each inode stores three numbers — start block, end block, and end byte offset — so a file's location is one contiguous run known before any lookup; the allocator never searches, it just advances the superblock's high-water mark. That one structure replaces free lists, extent trees, and fragmentation accounting, at the price of never being able to insert blocks into the middle of a file or reuse freed space. It is the cleanest possible illustration that allocation strategy, not capacity, is what makes filesystem code large.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/mkfs.bfs.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
