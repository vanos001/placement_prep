# fallocate — preallocate or deallocate file space

## Overview

`fallocate` manipulates the disk space backing a file directly through the
`fallocate(2)` syscall family: it reserves space for a file *without writing
data*, and it can punch holes, zero ranges, collapse or insert ranges, or
re-scan a file and turn runs of zeros into holes. The canonical use is
preallocation — "make this 20 GiB file exist, with real blocks reserved, in
milliseconds and without ENOSPC surprises mid-write."

Debian bookworm ships it in the `util-linux` package at `/usr/bin/fallocate`
(man section 1). It is the command-line face of the syscall and requires a
filesystem that implements it (ext4, xfs, btrfs, tmpfs and friends do; many
network filesystems and FAT historically do not).

Confusions worth pre-empting: with `truncate -s` (which grows a file *sparse*
— size without blocks), with `dd if=/dev/zero` (preallocation by brute-force
writing), and with `dd conv=sparse` / `cp --sparse` (the copy-side equivalents
of hole handling).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Section (man) | 1 |
| Path | /usr/bin/fallocate |
| Lineage | util-linux original; built on fallocate(2) (Linux 2.6.23) |
| Standards | None — Linux syscall interface (posix_fallocate is the POSIX fallback) |

## Synopsis

```
fallocate [options] <filename>
```

The main operation forms (length is required for range operations):

```
fallocate -l 10G disk.img             # allocate 10 GiB, extend file
fallocate -d big.log                  # dig holes: zeros → space returned
fallocate -p -o 1M -l 4M file         # punch a 4 MiB hole at offset 1M
fallocate -z -o 0 -l 1M -n file       # zero+allocate 1 MiB, keep apparent size
```

## How It Works

### Allocation without writing

Plain `fallocate -l N file` reserves `N` bytes of blocks for the file and
extends `st_size` to cover the range if needed. On ext4/xfs the reserved range
becomes an **unwritten extent**: blocks are charged to the file (visible in
`du`), reads return zeros, but no data was actually written. The kernel
guarantees that subsequent writes into that range will not fail with ENOSPC —
the entire point of preallocation for VM images, download targets, and
database files.

Verified on this system:

```bash
$ fallocate -l 100M fa.bin
$ ls -l fa.bin; du -h fa.bin
-rw-rw-r-- 1 z z 104857600 ...   fa.bin     # apparent size 100M
100M    fa.bin                              # and 100M of real blocks
```

Compare with sparse creation, where size and blocks diverge:

```bash
$ truncate -s 100M sp.bin            # coreutils; NOT fallocate's job
$ ls -l sp.bin; du -h sp.bin
-rw-rw-r-- 1 z z 104857600 ...   sp.bin
0       sp.bin                       # size 100M, blocks: zero
```

### The two size notions

Every operation here is really about the pair `(st_size, allocated blocks)`:

| Operation | st_size | blocks (du) |
| --- | --- | --- |
| `fallocate -l N` (default) | grows to cover range | grows by N |
| `fallocate -p` (punch hole) | unchanged | shrinks |
| `fallocate -z` (zero range) | unchanged | grows (ensures allocation) |
| `fallocate -z -n` (keep size) | unchanged | may grow beyond EOF view |
| `fallocate -c` (collapse) | shrinks by length | shrinks |
| `fallocate -d` (dig holes) | unchanged | shrinks where zeros found |

`-n` (`--keep-size`) is the modifier that freezes `st_size` — combined with
`-p` it is implied, because punching a hole must not change what the file
*looks* like.

### Punch, zero, collapse, insert

```
file: [AAAA][BBBB][CCCC]
punch  -o 4k -l 4k →  [AAAA][hole][CCCC]   blocks freed; reads give zeros
zero   -o 4k -l 4k →  [AAAA][0000][CCCC]   blocks (re)allocated as zeros
collapse -o 4k -l 4k →[AAAA][CCCC]         range removed; file shrinks
insert -o 4k -l 4k →  [AAAA][hole][BBBB][CCCC]  hole spliced in
```

`-d` (`--dig-holes`) is punch-hole with a search: it scans the file for runs
of actual zeros and converts them into holes. This is the space reclamation
tool for already-written data — it shrinks a log full of zero padding back to
its real content, and it is what makes `zerofree`-style cleanup possible per
file. Verified:

```bash
$ dd if=/dev/zero of=dig.bin bs=1M count=10 status=none
$ fallocate -d dig.bin
$ du -h dig.bin; ls -l dig.bin
0       dig.bin
-rw-rw-r-- 1 z z 10485760 ...  dig.bin    # 10 MiB file, zero blocks
```

### Filesystem support and the -x fallback

`fallocate(2)` is a filesystem op: ext4/xfs/btrfs/tmpfs support it well; some
filesystems support only some modes (punch-hole support arrived per-filesystem
over the years); NFS and FAT-family filesystems often support nothing. `-x`
(`--posix`) switches to `posix_fallocate(3)`, which is implemented in libc for
any filesystem by *writing zeros* — slow and data-touching, but universally
available and POSIX-portable. Scripts should probe or be prepared to fall back:

```bash
$ fallocate -l 1M /mnt/fat/test.img
fallocate: /mnt/fat/test.img: fallocate failed: Operation not supported
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-l, --length <num>` | Length of the range operation (required; suffixes KiB…YiB, `iB` optional) |
| `-o, --offset <num>` | Start of the range (default 0) |
| `-p, --punch-hole` | Replace range with a hole; frees blocks; implies `-n` |
| `-z, --zero-range` | Zero the range and *ensure* it is allocated |
| `-n, --keep-size` | Do not change the file's apparent size |
| `-c, --collapse-range` | Remove the range entirely, shifting data down; file shrinks |
| `-i, --insert-range` | Insert a hole of that length at the offset, shifting data up |
| `-d, --dig-holes` | Detect zero runs and turn them into holes |
| `-x, --posix` | Use `posix_fallocate(3)` — portable, writes zeros |
| `-v, --verbose` | Verbose operation |

## Usage Patterns

```bash
# Preallocate a VM disk image so later writes never hit ENOSPC
fallocate -l 20G vm-root.img
```

```bash
# Fast "create the log file at its rotation cap" so df is honest from day one
fallocate -l 500M app.log
```

```bash
# Sparse-friendly backup: reclaim space from zero-filled regions
fallocate -d daily-snapshot.img
```

```bash
# Punch out a known-dead range of a sparse database file
fallocate -p -o $((64*1024*1024)) -l $((16*1024*1024)) data.db
```

```bash
# Zero+allocate a header region, without extending the file
fallocate -z -o 0 -l 1M -n image.raw
```

```bash
# Remove the first 4 KiB of a file without rewriting it
fallocate -c -o 0 -l 4096 capture.pcap
```

```bash
# Splice in space for a header that will be written later
fallocate -i -o 0 -l 4096 image.raw
```

```bash
# Portable preallocation on a filesystem without fallocate support
fallocate -x -l 1G /mnt/nfs-share/blob.bin
```

```bash
# Check allocation state: apparent size vs blocks actually reserved
stat -c '%s bytes apparent, %b blocks of %B bytes' img.bin
```

```bash
# Create a swap file by reservation, not by writing zeros (then format it)
fallocate -l 4G scratch.swap && mkswap scratch.swap
```

## Nuances and Gotchas

- **fallocate ≠ truncate.** `truncate -s` makes a *sparse* file: size grows,
  blocks do not; a later full write still needs real space and can fail with
  ENOSPC. Preallocation claims blocks up front. Interviewers probe exactly this
  distinction.
- **`du` vs `ls` reading.** After preallocation both show the full size; after
  punching, `ls` shows the old size and `du` the reduced blocks. Tools that
  assume `du == ls` misreport sparse/unwritten files.
- **Filesystem support is uneven.** Failure is `EOPNOTSUPP`, not silence. Notably
  `fallocate -x` exists as the escape hatch but *writes* zeros — its cost
  profile is dd-like, not syscall-like.
- **Collapse/insert are the exotic ones.** Many filesystems implement punch and
  zero but not collapse/insert; test on the target FS, don't assume.
- **Punched holes read as zeros but are not "zeros".** Backups and sync tools
  handle holes differently (`rsync -S`, `cp --sparse=always|never`); moving a
  sparse/unwritten file to a filesystem without hole support materializes the
  space.
- **Size suffixes are binary.** `-l 10G` means 10 GiB (the help says suffixes
  are KiB…YiB with optional `iB`); a 10 GB expectation versus 10 GiB allocation
  is a subtle support issue in size-sensitive workflows.
- **Not a security wipe.** Zeroing (`-z`) is about allocation guarantees, not
  data sanitization; deleted-block remnants elsewhere on the device are out of
  scope. Use `shred`/`blkdiscard`-class tools for that intent.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Failure — unsupported operation on the filesystem, ENOSPC, bad arguments, or permission denied |

## Related Commands

- [`overview`](./overview.md) — index of all util-linux collection pages
- [internals](../../internals.md) — extents, unwritten state and the page cache behind fallocate's behavior

## Interview Questions

### Q: How does fallocate -l differ from truncate -s 100M?

`fallocate` reserves actual blocks (an unwritten extent on ext4/xfs), so `du`
immediately reports the space and subsequent writes cannot fail with ENOSPC.
`truncate` only raises `st_size`, creating a sparse file with zero blocks —
cheap, but the space is promised to no one. Preallocation = capacity
reservation; sparse = apparent size only.

### Q: What is an unwritten extent and what does a read of fallocated space return?

The filesystem marks the reserved range as allocated but unwritten; reads are
satisfied as zeros without materializing data, and the first real write into
each block converts the state to written. This is why preallocation is fast
(no I/O) yet safe (space is charged). POSIX itself guarantees only the
ENOSPC-prevention and, via posix_fallocate, the zeros — kernel-side unwritten
extents are the ext4/xfs mechanism that makes it cheap.

### Q: When would you use fallocate -d, and what does it cost?

`-d` (dig-holes) reclaims space from files that contain long runs of zeros —
snapshots, images, overwritten logs — by punching holes where it finds them.
The cost is a full read scan of the file plus metadata churn per hole; on
busy files or slow media it can be expensive, and it changes the file's
physical layout, which affects sparse-aware copy tools.

### Q: A script runs fallocate on an NFS mount and fails with "Operation not supported". Options?

The server/filesystem does not implement fallocate(2). Use `-x` to fall back to
`posix_fallocate(3)`, which works everywhere but writes zeros (slow), or design
around it (write the file then truncate, accept sparseness). The failure is
per-filesystem, so probe once and cache the capability rather than retrying.

### Q: Why is fallocate the wrong tool for securely deleting data?

Its contract is space management, not sanitization: zero-range/punch-hole make
no promises about erasing remnants of previously written data elsewhere on the
device, and filesystem journaling/COW (xfs, btrfs, ext4) can leave old copies
outside the file entirely. Secure deletion needs overwrite-aware tooling or
device-level erase (blkdiscard/shred with the right caveats).

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/fallocate.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
