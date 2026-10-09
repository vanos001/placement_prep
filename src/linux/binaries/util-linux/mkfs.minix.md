# mkfs.minix — create Minix filesystems

## Overview

`mkfs.minix` builds Minix filesystems — the tiny filesystem from Andy Tanenbaum's MINIX teaching OS that early Linux used for its own disks. It is one of util-linux's built-in builders (`/usr/sbin/mkfs.minix`), pairs with the checker/repairer `fsck.minix`, and survives because it is a complete, self-contained filesystem stack small enough to read end-to-end: ideal for OS courses, floppy/embedded images, and demonstrating what a superblock, bitmaps, and inode tables actually do.

It is often confused with `mkfs.ext2` (the "modern minimal" choice for real work — always prefer it there), with its sibling `fsck.minix` (which checks/repairs what this tool builds), and with the other legacy builders `mkfs.bfs` and `mkfs.cramfs`. Note also that "Minix filesystem" (this page) and "MINIX the OS" are different artifacts: the filesystem is just an on-disk format that Linux supported from the very beginning.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/mkfs.minix |
| First appeared | Minix fs 1987 (Tanenbaum); builder in Linux userspace since the early 1990s |
| Standards | None — legacy/teaching filesystem |

## Synopsis

```
mkfs.minix [options] <device> [size-in-blocks]
```

Common one-line forms:

```
mkfs.minix -3 image.img        # Minix v3 (60-char names, larger blocks)
mkfs.minix -1 minix.img        # classic v1, 14-char names
mkfs.minix -c -n 30 -i 48 img  # check for bad blocks, 30-char names, 48 inodes
```

## How It Works

### The textbook on-disk layout

A Minix filesystem is the minimal redundant-accounting design, and the builder's job is to stamp exactly these structures:

```
Block:  1             2                3               4..N          N+1..
      ┌─────────┬─────────────────┬────────────────┬─────────────┬──────────┐
      │ super   │ inode bitmap    │ zone bitmap    │ inode table │ data     │
      │ block   │                 │                │             │ zones    │
      └─────────┴─────────────────┴────────────────┴─────────────┴──────────┘
```

The superblock records the magic number (which also encodes the version/name-length variant), inode and zone counts, bitmap sizes, first data zone, and maximum file size. The two bitmaps say which inodes and data zones are in use; the inode table holds mode, uid, size, and the direct/indirect zone pointers. `mkfs.minix` computes counts from the requested size, writes zeroed bitmaps (root directory pre-created), and exits — no journaling, no extents, nothing else.

### Superblock and inode fields, concretely

```
v1/v2 superblock (block 2, offset 1024):     v3 adds:
s_ninodes        inode count                 32-bit counts throughout,
s_nzones         size in zones (16-bit v1!)  an explicit s_block_size field,
s_imap_blocks    inode bitmap size           and its own single magic value.
s_zmap_blocks    zone bitmap size
s_firstdatazone  first data zone
s_log_zone_size  zone/block ratio
s_max_size       max file size (32-bit)
s_magic          version + name-length selector
s_state          bit 0 = cleanly unmounted, bit 1 = errors seen
```

The magic values double as the version dial: `0x137F` (v1, 14-char names), `0x138F` (v1, 30-char names), `0x2468` (v2, 14-char), `0x2478` (v2, 30-char), `0x4D5A` (v3). Each inode carries seven direct zone pointers plus indirect chains — v1 inodes have two (single, double), v2/v3 inodes add a triple — which, with 1 KiB blocks, is how v1 computes its ~64 MiB maximum file size (7 + 256 + 256² KiB). The `s_state` word is the entire crash-consistency story: the kernel or fsck sets/clears it, and there is nothing else to replay.

One offset subtlety worth knowing before you hexdump: the superblock's first bytes are `s_ninodes`, not the magic. In v1/v2 the magic `u16` sits 16 bytes in (absolute offset 1040); in v3 it sits 24 bytes in (absolute 1048), followed by the 32-bit block size at 1052.

### The three versions

| Version | Names | Blocks | Scale | Magic variants |
| --- | --- | --- | --- | --- |
| v1 | 14 chars | 1 KiB | ~64 MiB ceiling | two magics encode 14 vs 30-char names |
| v2 | 30 chars | 1 KiB | GiB-range | two magics likewise |
| v3 | 60 chars | 1–4 KiB | larger (32-bit zone counts) | single magic |

Name length is not a free field: for v1/v2 it is baked into the superblock magic value (14- or 30-char directory entries), and v3 uses its own format. `-n` therefore only accepts values valid for the chosen version — mismatched combinations are refused rather than silently producing an unmountable image.

### Sizing and the blocks operand

Without the trailing `size-in-blocks` operand, the tool sizes from the device (a partition, loop device, or regular file — image files are first-class here). With it, the filesystem is capped at that many blocks regardless of device size. The inode count (`-i`) is bounded by the size: inodes cost bitmap bits and table space, and requesting more than the geometry allows is an error. `-c` reads every block of the target to find bad blocks before formatting (meaningful on floppies; pointless and slow on SSDs), and `-l` accepts a bad-block list from a file instead.

### The family workflow

```
dd if=/dev/zero of=minix.img bs=1M count=8
mkfs.minix -3 minix.img
mount -o loop minix.img /mnt/m     # use it
umount /mnt/m
fsck.minix minix.img               # check/repair (sibling page)
```

### What creation computes and writes

The builder is a size-and-stamp program. Given the target size it derives: the zone count, the inode count (`-i` or a default proportional to size), the number of bitmap blocks each count needs (`s_imap_blocks`, `s_zmap_blocks`), and the first data zone (after superblock + bitmaps + inode table). Then it writes: the superblock with the version's magic, two zeroed bitmaps with the root directory's inode and its zone pre-marked used, the inode table with only the root inode initialized, and nothing else. Everything a later `fsck.minix` pass relies on is created in those few writes — which is why an image can be verified byte-for-byte right after creation and why there is no "phase 2" like ext builders have.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-1` | Build a Minix **v1** filesystem (14-char names, 1 KiB blocks, ~64 MiB) |
| `-2, --minix2` | Build a Minix **v2** filesystem (30-char names) |
| `-3, --minix3` | Build a Minix **v3** filesystem (60-char names, bigger blocks) |
| `-n, --namelength <len>` | Max filename length; only values valid for the selected version (14/30; 60 for v3) |
| `-i, --inodes <num>` | Number of inodes to reserve (fixed for the life of the fs) |
| `-b, --blocksize <size>` | Block size (version-dependent values; v3 supports up to 4096) |
| `-c, --check` | Read the whole device first, abort/annotate on bad blocks |
| `-l, --badblocks <file>` | Take the bad-block list from a file instead of scanning |

Historical note: very old mkfs.minix versions used `-v` to request a v2 filesystem — a flag collision (with today's "verbose") that surprises anyone reviving 1990s scripts.

## Usage Patterns

```bash
# The classic lab: make a floppy image with a Minix v1 filesystem
dd if=/dev/zero of=minix.img bs=1024 count=1440
mkfs.minix -1 minix.img
```

```bash
# Modern-ish variant: v3 with long names, 4 KiB blocks
dd if=/dev/zero of=m3.img bs=1M count=32
mkfs.minix -3 -b 4096 m3.img
```

```bash
# Loop-mount and use it like any filesystem
mount -o loop minix.img /mnt/m && cp notes.txt /mnt/m/ && umount /mnt/m
```

```bash
# Cap the filesystem smaller than the container file
mkfs.minix -3 m3.img 8192
```

```bash
# Reserve a specific inode count for a known file population
mkfs.minix -3 -i 200 m3.img
```

```bash
# Scan for bad blocks first (floppy-era practice)
mkfs.minix -1 -c minix.img
```

```bash
# Use a pre-supplied bad-block list
mkfs.minix -1 -l badblocks.txt /dev/fd0
```

```bash
# Check the result with the sibling tool
fsck.minix -l minix.img
```

```bash
# Inspect the superblock magic variants by version
xxd -s 1024 -l 4 minix.img
```

```bash
# Through the generic dispatcher
mkfs -t minix minix.img
```

```bash
# Read the version dial straight out of the superblock (offsets above)
xxd -s 1040 -l 2 minix.img      # v1 14-char names: bytes 7f 13 (0x137F LE)
xxd -s 1040 -l 2 m3.img         # v3 magic lives 8 bytes further: -s 1048
```

```bash
# Provisioning math: inodes are the scarce resource, plan before -i
mkfs.minix -3 -i $(( expected_files * 2 )) m3.img   # headroom, fixed forever
```

```bash
# Bad-block list file format: one decimal block number per line
printf '17\n1023\n' > bad.txt
mkfs.minix -1 -l bad.txt /dev/fd0
```

```bash
# End-to-end lab loop with the sibling checker (build, use, unmount, check)
mkfs.minix -3 lab.img
mount -o loop lab.img /mnt/m && echo data > /mnt/m/f && umount /mnt/m
fsck.minix -l lab.img && echo "consistent, exit $?"
```

## Nuances and Gotchas

- **Name length is structural, not cosmetic.** v1's 14-char limit and the magic-encoded variants mean an image created with the wrong `-n` is not merely "inconvenient" — it is a different on-disk dialect. Match creator and consumer versions deliberately.
- **The inode count is forever.** Like BFS but unlike ext: no resizing, no inode growth. Under-provision and the fs refuses new files while data zones are still free — the classic Minix-filesystem ENOSPC surprise.
- **~64 MiB ceiling for v1.** Zone counters and max-size fields bound the format; trying to "just make a big v1 image" fails or produces something the driver rejects.
- **Unmounted only.** Same rule as every fs checker: `fsck.minix` on a mounted image races the kernel and manufactures corruption. Build, use, unmount, then check.
- **`-c` is a full-device read.** On a 1.4 MiB floppy it is instant; on multi-GiB containers it is a waste of time — bad-block scanning made sense on magnetic media, not on flash or virtual disks.
- **Small images may not be mountable if undersized.** Bitmaps and inode tables consume a fixed overhead; an image smaller than the minimum geometry is refused. Don't shrink below the tool's minimum.
- **No label support.** The Minix format has no volume-label field — scripts that look for `LABEL=` via blkid find nothing. Use UUIDs? There are none either; identification is by magic version and size.
- **Version 3 compatibility.** Linux supports all three versions, but some minimal/embedded kernels build only v1/v2. Images for such systems must use `-1`/`-2` even though `-3` is nicer.
- **The magic check trap when hexdumping.** `xxd -s 1024` reads the *inode and zone counts*, not the magic — the superblock opens with `s_ninodes`. v1/v2 magic is a 16-bit field 16 bytes in (offset 1040), v3's 24 bytes in (1048) with the 32-bit block size right after. Scripts asserting on the first superblock bytes misidentify every healthy image.
- **v1's 16-bit zone counter is the ceiling mechanism.** `s_nzones` cannot express more than 65535 zones (with 1 KiB zones, ~64 MiB before you even consider the max-file-size field); v2 widened it, v3 moved everything to 32-bit. This is why "just make a bigger v1 image" is not a matter of tooling — the format's counters run out.
- **`s_state` is the whole crash story.** One 16-bit word: cleanly-unmounted bit, errors-seen bit. `fsck.minix -a` re-stamps it after repair; a kernel that detects on-mount anomalies sets the error bit. No replay, no checksums — recovery means fsck's reconciliation or rebuild.
- **busybox ships its own mkfs.minix.** Embedded images often carry the busybox applet: fewer options (no `-b` block-size control on old builds), different defaults. Match the builder to the checker — a busybox-built image checked by util-linux fsck.minix is fine, but option availability differs.
- **The size operand's unit depends on nothing — it is always 1 KiB blocks in v1/v2, the configured block size in v3.** Mixing it up with mkfs.bfs's 512-byte convention or `dd`'s `bs=` is a recurring off-by-factor; compute expected byte sizes and compare with `lsblk -b` or `stat -c %s` before mounting.

## Exit Status

- `0` — filesystem created successfully.
- `8` — operational error (I/O failure, bad blocks found with `-c`, unusable device).
- `16` — usage error (invalid option combination, bad size or inode count).

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`mkfs`](./mkfs.md) — the dispatcher that routes `mkfs -t minix` here.
- [`fsck.minix`](./fsck.minix.md) — the checker/repairer for images this tool builds.
- [`mkfs.bfs`](./mkfs.bfs.md) — fellow tiny util-linux builder (boot-oriented, no repair tool).
- [`mkfs.cramfs`](./mkfs.cramfs.md) — fellow built-in builder (compressed, read-only).

## Interview Questions

### Q: Why is the Minix filesystem the standard vehicle for teaching filesystem internals?

Because it implements the complete minimal accounting model — superblock, inode bitmap, zone bitmap, inode table, data zones — with no journal, extents, or checksumming to obscure the concepts. Every question a real checker asks (orphan inodes, cross-linked zones, link counts, dot entries) appears at readable scale, and the tooling (`mkfs.minix`/`fsck.minix`) is a few thousand lines instead of hundreds of thousands.

### Q: Explain how the v1 14-char vs 30-char name variants are encoded.

Not in a superblock field — in the magic number. v1 and v2 each have two magic values, one for 14-character directory entries and one for 30; the driver reads the magic and derives the directory-entry size from it. That is why `-n` only accepts values valid for the selected version: the combination is structural, and a mismatch produces an image no driver will interpret correctly.

### Q: A Minix filesystem reports free data zones but refuses new files. What happened?

The inode table is exhausted: inodes are provisioned once at mkfs time (`-i`) and can never grow, so a filesystem with more files than reserved inodes hits ENOSPC while data zones remain free. This fixed-provisioning model is the key operational difference from ext-family filesystems, where inode counts are at least settable at build time to generous sizes.

### Q: Why does mkfs.minix offer -c bad-block checking at all, and when is it pointless?

It is a floppy-era feature: magnetic media shipped with factory flaws, so formatting meant scanning and annotating bad blocks. On modern flash, virtual disks, and SSDs there are no user-visible bad blocks (remapping is below the interface), so `-c` only costs a full read of the device. It survives for period-correct workflows and teaching.

### Q: What does mkfs.minix share with fsck.minix, and why ship both?

They implement the same on-disk knowledge from opposite directions: the builder stamps valid structures; the checker reconciles them after damage (and repairs with `-a`/`-r`). Both are in util-linux, self-contained, and version-aware (v1/v2/v3). Shipping both makes the pair a closed loop for courses and image archaeology — build, break, repair.

### Q: Where exactly is the Minix magic number stored, and why do the versions disagree?

The superblock starts at offset 1024 with `s_ninodes` — the magic is not first. v1/v2 place the 16-bit magic at superblock offset 16 (absolute 1040), which is also why two name-length variants per version had to be encoded *in the magic itself*: there was no spare field for a name-length byte, so 0x137F/0x138F and 0x2468/0x2478 each pair off by one bit of intent. v3, written later, reorganized the block with 32-bit counts, an explicit block-size field, and one magic (0x4D5A) at offset 24. Anyone writing detection code must handle all five values at two different offsets.

### Q: Your course lab asks students to "add a feature to the minix filesystem." Why is this format a good substrate for that, and what should they expect to touch?

Because the accounting model is closed: a feature like "one more indirect level" or "a free-zone counter" touches the superblock layout (a field), the inode (a pointer), and the two bitmaps — with no journal, checksums, or extents dragging in consistency machinery. The toolchain is similarly closed: mkfs.minix and fsck.minix are a few thousand lines each and know every byte of the format. The lesson students take away is how quickly the same change multiplies in ext4: descriptor tables, journal replay rules, feature flags, e2fsck passes.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/mkfs.minix.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
