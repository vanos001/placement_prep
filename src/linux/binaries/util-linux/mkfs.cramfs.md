# mkfs.cramfs — create compressed ROM filesystem images

## Overview

`mkfs.cramfs` packs a directory tree into a cramfs image — a read-only, zlib-compressed filesystem that the kernel can mount directly and decompress on demand, one 4 KiB page at a time. It is the util-linux-native builder for the format that powered late-1990s/2000s initrds, embedded firmware `/rom` partitions, and Live-CD-style read-only roots: files stay compressed on disk, the page cache holds decompressed pages, and nothing on the image is ever writable.

It ships in the `util-linux` package at `/usr/sbin/mkfs.cramfs`, paired with the checker `fsck.cramfs`. It is often confused with `mkfs.minix` (writable legacy builder from the same family), with squashfs (`mksquashfs` — the successor with better compression and features), and with `gen_init_cpio`-style initramfs tooling (cpio archives, not a mountable filesystem).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/mkfs.cramfs |
| First appeared | late 1990s (kernel-era mkcramfs, absorbed into util-linux) |
| Standards | None — Linux kernel cramfs format |

## Synopsis

```
mkfs.cramfs [options] <directory> <file>
```

Common one-line forms:

```
mkfs.cramfs rootfs/ rootfs.cramfs     # pack a tree into an image
mkfs.cramfs -N reg rootfs/ r.cramfs   # encode file types for busybox-style use
mkfs.cramfs -b 4096 -v rootfs/ r.cramfs
```

## How It Works

### What the format stores

The first 1 KiB of the image is the cramfs superblock: magic, size, flags, the edition/revision numbers, and a single global timestamp. Directory entries and inodes follow, then compressed file data. Everything about the format is deliberately small:

```
offset 0                 ┌ superblock: magic, size, flags, edition,
                         │             revision, ONE global timestamp
                         ├ directory entries + inodes (uncompressed)
                         ├ file data: zlib-deflated 4 KiB pages
                         └ (padded out to a 4 KiB boundary)
```

- **Only file data is compressed** — metadata stays plain, so path lookups never decompress.
- Files are compressed as independent **4 KiB pages** (the `-b` block size), which is what lets the kernel page cache map and decompress on demand instead of inflating whole files.
- The format is strictly read-only: mounting it writable is not a kernel option; "updating" means rebuilding and remounting the image.

### The hard limits you inherit

The compact inode encoding trades away metadata fidelity, and these limits are interview favorites because they are structural, not configurable:

| Limit | Consequence |
| --- | --- |
| uid/gid stored in 8 bits each | owners above 255 wrap around — root-owned images are the safe pattern |
| file size in 24 bits | no single file above 16 MiB |
| page offset field | total image tops out around 256 MiB (4 KiB pages) |
| one global timestamp | per-file mtimes do not exist; the image build time is it |
| no hard links | the same content under two names is stored twice |

### Building the image

`mkfs.cramfs` walks the source directory, sorts entries, compresses each file's pages with zlib, writes the superblock, and pads the image to a 4 KiB multiple. `-N, --named-file-type` pads chunks and encodes the file type (dir/reg/chr/blk/fifo/sock) so type info survives in contexts that need it; `-i, --image` embeds an extra file (the classic initrd-inside-cramfs trick); `-e, --edition` and `-r, --revision` stamp the superblock counters. The resulting file is consumed verbatim: loop-mount it, dd it to an MTD partition, or hand it to a bootloader.

```
$ mkfs.cramfs rootfs/ rootfs.cramfs
$ mount -t cramfs -o loop rootfs.cramfs /mnt/rom
$ ls /mnt/rom          # decompress-on-demand through the page cache
```

### Why squashfs displaced it

Squashfs offers better compressors (xz/zstd/lzo), larger limits, real timestamps, uid/gid fidelity, and append mode — cramfs's only remaining virtues are that the kernel driver is tiny, ancient, and needs no userspace tools at mount time. Legacy firmware and exam questions keep it alive.

### The on-disk layout, from the kernel's own header

`linux/cramfs_fs.h` is the contract both the builder and the mount driver code against; the constants there explain every "hard limit" in this page:

```
super:  magic(0x28cd3d45) size flags future
        signature[16] = "Compressed ROMFS"
        fsid { crc, edition, blocks, files }
        name[16]                       (volume name)
        root inode
inode:  8 bytes, bit-packed: mode, uid, size, gid,
        namelen:6, offset:26
```

Details with teeth: `namelen` is 6 bits storing the name length divided by 4 — a single file name caps at 252 bytes, and the builder refuses longer ones. `offset` is 26 bits in 4-byte units, which is where the ~256 MiB image ceiling comes from. Device nodes carry their `major:minor` in the `size` bits, since special files have no data. Per-file data begins with a block-pointer table — one 4-byte entry per 4 KiB page whose top bits flag `UNCOMPRESSED` and `DIRECT_PTR` pages, so the mount driver skips inflate for incompressible chunks instead of growing them.

The inode has no timestamp field at all — the single global stamp in the superblock is all the format can express. Symlink targets are stored as the link's "data", compressed like file contents, and dangling symlinks survive fine because nothing is resolved at build time.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-b, --blocksize <size>` | Compression page size; must match the kernel page size expectations (default 4096) |
| `-e, --edition <num>` | Stamp the superblock edition number |
| `-r, --revision <num>` | Stamp the filesystem revision |
| `-N, --named-file-type <list>` | Encode file types (dir, reg, chr, blk, fifo, sock) and pad chunks accordingly |
| `-i, --image <file>` | Embed the named file as an initial image entry (e.g. a ramdisk) |
| `-v, --verbose` | Explain what is being done |

## Usage Patterns

```bash
# Pack a rootfs tree into a mountable read-only image
mkfs.cramfs rootfs/ rootfs.cramfs
```

```bash
# Loop-mount the image and inspect it
mount -t cramfs -o loop rootfs.cramfs /mnt/rom && ls /mnt/rom
```

```bash
# Show the image is really compressed: source vs image size
du -sh rootfs/ rootfs.cramfs
```

```bash
# Verify integrity with the sibling checker
fsck.cramfs -v rootfs.cramfs
```

```bash
# Stamp an edition number so the bootloader can reject stale images
mkfs.cramfs -e 7 rootfs/ rootfs-v7.cramfs
```

```bash
# Encode file types (devices/fifos visible without devtmpfs tricks)
mkfs.cramfs -N dir,reg,chr,blk,fifo,sock rootfs/ rootfs-typed.cramfs
```

```bash
# Embed a prebuilt ramdisk image
mkfs.cramfs -i initrd.gz rootfs/ boot.cramfs
```

```bash
# Explicit page size (must be a power of two, kernel-page-compatible)
mkfs.cramfs -b 4096 rootfs/ rootfs.cramfs
```

```bash
# Ship it to an MTD partition on embedded flash
dd if=rootfs.cramfs of=/dev/mtdblock4
```

```bash
# Confirm the superblock magic before flashing
xxd -l 16 rootfs.cramfs
```

```bash
# Inspect the header without xxd: magic then signature (od is everywhere)
od -A x -t x1z -N 32 rootfs.cramfs
# 000000 45 3d cd 28 00 10 00 00 02 00 00 00 00 00 00 00  >E=.(............<
# 000010 43 6f 6d 70 72 65 73 73 65 64 20 52 4f 4d 46 53  >Compressed ROMFS<
```

```bash
# Measure the real compression ratio of a build
SRC=$(du -sb rootfs/ | cut -f1); IMG=$(stat -c %s rootfs.cramfs)
echo "image is $((IMG * 100 / SRC))% of the source tree"

# Confirm the booted kernel can even mount it, before shipping
grep -w cramfs /proc/filesystems || modprobe cramfs 2>/dev/null

# Round-trip test on a loop device before flashing anything
mkdir -p /mnt/rom && mount -t cramfs -o loop,ro rootfs.cramfs /mnt/rom \
  && diff -r rootfs/ /mnt/rom && umount /mnt/rom

# Device nodes in the image: create them in the source tree (root), then -N
mknod rootfs/dev/console c 5 1
mkfs.cramfs -N dir,reg,chr,blk,fifo,sock rootfs/ rootfs-dev.cramfs

# Check what the image claims before flashing: files and block counts
fsck.cramfs -v rootfs-dev.cramfs | head -3
```

## Nuances and Gotchas

- **uid/gid wrap at 8 bits.** Build images as root (or with everything owned by uid ≤ 255), or a file owned by uid 1000 on the build host becomes uid 232 on the image. Silent truncation — nothing warns.
- **16 MiB per file, ~256 MiB per image.** The encoder fails (or the layout does) past these; big assets need splitting or a different format. There is no knob.
- **One timestamp for everything.** Per-file mtime does not exist in cramfs; build-time stamped globally. Tools that diff by mtime misbehave on cramfs mounts.
- **Hard links are not a thing.** Two names for one file means two stored copies — deduplication is your problem at build time.
- **`-b` must align with the kernel page size.** The whole on-demand decompression scheme assumes the image's page size matches what the kernel maps; a mismatched `-b` builds an image that mounts wrong or not at all.
- **Read-only is absolute.** No remount-rw, no overlay tricks inside the format; updates require rebuild + remount (or a writeable overlay stacked above it).
- **Mounting cramfs needs kernel support.** `CONFIG_CRAMFS` must be in; slim kernels and containers without it will refuse `-t cramfs` before your image is even read.
- **The 252-byte filename cap is per component.** `namelen` is 6 bits storing the length divided by 4; hashed/asset-style generated names can exceed it and the build fails. Keep names short at the source, not with a post-hoc rename pass.
- **Incompressible content still costs the pointer table.** Pages that zlib-grow are stored uncompressed (the `UNCOMPRESSED` block flag), but each file pays a 4-byte block-pointer entry per page — tiny files are net *larger* than their content, and already-compressed assets (`.gz`, `.png`) waste table space for no ratio gain.
- **fsck.cramfs is a checker, not a repairer.** It verifies CRCs and that every page inflates; "repair" means rebuild the image and reflash. Budget verification time into the build pipeline, not field service.
- **Metadata equality with the source is not guaranteed.** Only the global timestamp exists, special-file metadata is lossy, and permissions come from the build host — validate the *mounted* image (the loop round-trip above), not the source tree, in CI.
- **Builds are host-dependent in the small.** Directory iteration order is normalized (sorted dirs), but zlib versions differ in output bytes across build hosts — two "identical" builds can produce non-byte-identical images. Compare via fsck.cramfs and mounted diff, not `cmp`.

## Exit Status

- `0` — image written successfully.
- `1` — failure: unreadable source, file over format limits, bad options, or write error.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`mkfs`](./mkfs.md) — the dispatcher front end (`mkfs -t cramfs <dir> <img>`).
- [`fsck.cramfs`](./fsck.cramfs.md) — the sibling checker for these images.
- [`mkfs.minix`](./mkfs.minix.md) — the writable member of the built-in builder family.

## Interview Questions

### Q: How does cramfs provide "compressed filesystem" semantics without unpacking everything at boot?

Files are stored as independently compressed 4 KiB pages; the kernel's read path inflates just the requested page and caches it like any page-cache entry. Random access works (each page self-contained), boot needs no staging space, and RAM cost scales with what you actually touch — the same idea squashfs later refined.

### Q: Why are uid/gid values in a cramfs image only 8 bits, and what breaks?

The inode layout spent its bits on size and offset instead of metadata; uid/gid get one byte each. Anything owned by uid 256+ silently wraps, so images built for real deployments standardize on root ownership. It is the canonical example of a format trading fidelity for compactness — and of why "it worked on my build host" fails on the device.

### Q: Your embedded image must be updated in the field. Why is cramfs a poor choice, and what replaced it?

cramfs is strictly read-only with no append/update path: any change means building a whole new image and flashing/mounting it atomically, with all metadata limits (8-bit uid/gid, 16 MiB files, one timestamp) as permanent constraints. Squashfs adds real timestamps, uid fidelity, stronger compressors, and larger limits while staying read-only — which is why it displaced cramfs everywhere.

### Q: What does the -N --named-file-type option solve?

Plain cramfs inodes do not distinguish special-file types in a way some consumers rely on; `-N` pads chunks and encodes the type bits (dir/reg/chr/blk/fifo/sock) so device nodes and FIFOs are recognizable from the image itself. Embedded setups that create devices before devtmpfs exists depend on this.

### Q: Compare mkfs.cramfs and mkfs.minix as "tiny filesystem" tools.

cramfs optimizes footprint via compression and read-only rigidity (no writes possible, no checker repairs possible); minix is a small *writable* POSIX-ish filesystem with a genuine repair tool. Both are legacy teaching artifacts shipped by util-linux; choosing between them means choosing between "compressed read-only media" and "writable minimal fs", not between two versions of the same idea.

### Q: Walk through a read of one byte at offset 500000 of a 2 MiB file on a mounted cramfs.

The VFS request maps to page index ~122; the cramfs read path uses the file's block-pointer table to locate the compressed extent holding that page, inflates just it (or copies it raw when the `UNCOMPRESSED` flag is set) into a page-cache page, and returns the byte. Neighboring reads hit the page cache; nothing else in the file is decompressed. That page-at-a-time model — not whole-file inflate — is the format's defining trick.

### Q: Why does cramfs need no journal or boot-time fsck, and what actually corrupts it?

The kernel never writes to a mounted cramfs, so no unflushed state can exist and there is nothing to replay or repair — the "recovery" story is rebuild-and-reflash. Corruption comes from outside the write path: bad flash blocks, truncated transfers, or a broken builder. That is precisely what fsck.cramfs detects (CRC and inflate verification over the whole image) and precisely what it cannot fix.

### Q: When would you still pick cramfs over squashfs today?

Only under constraint: a tiny `CONFIG_CRAMFS` in a minimal or ancient kernel, bootloaders or toolchains that already speak the format, and certification-fixed firmware where changing filesystems is out of scope. Squashfs wins everywhere else — better compressors, real timestamps, uid fidelity, xattrs, far larger limits — so the honest answer names the constraint and documents an exit path, rather than defending cramfs on merit.

### Q: What do the superblock flags (holes, sorted dirs, extended block pointers) change at mount time?

The mount driver refuses images whose flags exceed `CRAMFS_SUPPORTED_FLAGS` — the format's forward-compatibility mechanism. `SORTED_DIRS` records that directories were written in sorted order (lookup shortcuts); `HOLES` marks sparse regions that read as zeros without stored pages; `EXT_BLOCK_POINTERS` switches the per-page pointer table to the extended encoding with the flag bits. All are set by the builder, interpreted by the kernel, and invisible to userspace — which is why a newer mkfs.cramfs output may simply refuse to mount on an ancient kernel.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/mkfs.cramfs.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
