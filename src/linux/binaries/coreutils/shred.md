# shred — Overwrite file contents in place before deletion

## Overview

`shred` repeatedly overwrites a file's bytes with fresh patterns — random
data, then optionally zeros — so that the previous contents are hard to
recover even with laboratory equipment. It exists because plain deletion
does not erase anything: `rm` (see `./rm.md`) only unlinks a name, leaving
every data block intact on disk until reuse.

It ships in Debian package `coreutils` and lives at `/usr/bin/shred`. It
comes from the GNU fileutils/coreutils line of the 1990s, inspired by the
era's "secure deletion" research on magnetic media. It is not in POSIX and
is not part of every Unix: BSDs and macOS do not ship it by default.

`shred` is most useful — and most honest — when you understand the model it
assumes: **the filesystem writes your bytes in place at the same physical
location**. On modern systems that assumption frequently fails, and the
tool itself prints a CAUTION saying so. Knowing exactly when shred works
and when it is theater is the interview-worthy part.

| Field | Value |
|---|---|
| Package | coreutils (Debian bookworm) |
| Section (man) | 1 — User Commands |
| Path | /usr/bin/shred |
| First appeared / lineage | GNU fileutils era, 1990s; now maintained in GNU coreutils |
| Standards | not in POSIX 2018; GNU extension |

## Synopsis

```
shred [OPTION]... FILE...
```

```bash
shred -u secret.key            # overwrite (default 3 passes) then remove
shred -v -n1 -z disk.img       # one random pass, then a zero pass, verbose
shred -n0 -z /dev/sdb           # zero-fill a whole device in a single pass
shred --remove=wipesync -u -v file   # obfuscate the file name, sync each byte
```

## How It Works

For each regular file, `shred` opens it for writing and streams passes over
the full length: each pass seeks through the file writing a pattern block
by block, then `fsync`s so bytes actually reach storage before the next
pass starts. The default is **3 passes, all random**; `-z` appends one
final pass of zeros afterwards (so a file after `-z` looks like an ordinary
zeroed file rather than obviously-shredded random noise):

```bash
$ printf 'TOPSECRET' > s.txt
$ shred -v -n1 -z s.txt
shred: s.txt: pass 1/2 (random)...
shred: s.txt: pass 2/2 (000000)...
```

Two mechanical details surprise people:

- **Length rounding.** Shred rounds the file size up to the next full
  block (typically 4096 bytes) so nothing of the last partial block
  survives in a page-cache read-back. A 9-byte file comes out 4096 bytes
  long unless you pass `-x` (`--exact`), which is the default only for
  non-regular files such as device nodes.
- **Nothing is removed by default.** Shred assumes you may be operating on
  a device file (`/dev/sdb`), which must not be unlinked. Add `-u` or
  `--remove=HOW` to delete afterwards.

### The removal modes

`--remove=HOW` controls how the *name* is disposed of, because filenames
leak information too:

| HOW | Behavior |
|---|---|
| `unlink` | plain `unlink(2)`, same as `rm` |
| `wipe` | overwrite the name bytes (e.g. with 0xFF) before unlinking |
| `wipesync` | like `wipe`, but fsync after each renamed byte (default) |

`wipesync` is thorough and slow: it renames the file one byte at a time,
synchronizing each step so the old name never lingers in journal replay.

### Where the overwrite model holds — and where it breaks

```
 overwrite in place?              physical reality
 ┌──────────────┐
 │ shred writes │──► classic HDD + ext2/ext4 (data in place): mostly holds
 │  byte N      │
 └──────┬───────┘
        │
        ▼  translation layers rewrite your "in place" write elsewhere:
        ├─ COW filesystems (btrfs, ZFS, snapshots): old extent retained
        ├─ SSD FTL: write goes to fresh cells; old cells wear-leveled away
        ├─ journaling: data/metadata copies may sit in the journal
        ├─ compression/dedup FS (zstd on btrfs, ZFS dedup): no 1:1 mapping
        └─ snapshots/RAID mirrors: N stale copies, not 1
```

Being precise about each failure mode:

- **Copy-on-write filesystems.** btrfs and ZFS never overwrite a live
  extent; every write lands in a newly allocated extent and the old one is
  only freed (snapshots can pin it indefinitely). Shredding a btrfs file
  may even make things *worse* by multiplying data via CoW metadata churn.
- **SSDs and the flash translation layer.** The OS address of byte N is
  not a physical cell; the FTL writes the new data to fresh erased cells
  and marks the old ones stale. Garbage collection and wear leveling copy
  stale data around behind the OS's back. Overwrite-based wiping cannot
  address the stale copies; ATA/NVMe `sanitize` or `blkdiscard` is the
  correct mechanism, or full-disk encryption with key destruction.
- **Journaling filesystems.** ext4 with `data=ordered` (the default)
  journals metadata only, so file *data* is overwritten in place and shred
  mostly works; but `data=writeback` or other modes can leave data copies
  in the journal. Either way the *name* and metadata trail live in the
  journal — which is exactly what `--remove=wipesync` tries to clean.
- **Where it genuinely works.** Whole-device passes on raw block devices
  (`shred /dev/sdb`), files on non-COW, non-journaled-data filesystems on
  spinning media, and any target you will subsequently fill with zeros or
  re-encrypt anyway.

The modern best practice follows from these limits: encrypt volumes at
rest (LUKS/dm-crypt), and "delete" by destroying the key — the on-disk
ciphertext becomes uniformly unrecoverable without any overwrite pass.

## Options That Matter

| Option | Effect |
|---|---|
| `-n`, `--iterations=N` | number of overwrite passes (default 3); `-n0` means none (useful with `-z`) |
| `-z`, `--zero` | append a final all-zeros pass to hide the shredding |
| `-u` | remove the file after overwriting (default removal mode `wipesync`) |
| `--remove=HOW` | `unlink` / `wipe` / `wipesync` — how the name is disposed of |
| `-f`, `--force` | change permissions to allow writing if necessary |
| `-s`, `--size=N` | shred only the first N bytes (suffixes K/M/G accepted) |
| `-x`, `--exact` | do not round the size up to the next full block |
| `-v`, `--verbose` | print one progress line per pass |
| `--random-source=FILE` | use bytes from FILE instead of the internal PRNG |

## Usage Patterns

```bash
# Wipe and remove a key file: one random pass is enough for the threat model
shred -u -n1 -z secret.key
```

```bash
# Sanitize a decommissioned spinning disk overnight (3 random passes + zeros)
shred -v -n3 -z /dev/sdb
```

```bash
# Zero-fill a disk image so it compresses well before upload
shred -n0 -z -v disk.img
```

```bash
# Shred exactly the payload bytes of a fixed-format record file
shred -x -s 512 record.bin
```

```bash
# Shred files found by age, NUL-safe through xargs
find /tmp/scratch -type f -mtime +7 -print0 | xargs -0 shred -u
```

```bash
# Faster deterministic wipe for a USB stick that will be reformatted anyway
shred -n0 -z /dev/sdc
```

```bash
# Audit the passes on a small file without removing it
shred -v -n1 important.txt && file important.txt
```

```bash
# Feed shred's random stream to another tool via a FIFO name (use sparingly)
shred --random-source=/dev/urandom -n1 file.dat
```

## Nuances and Gotchas

- **Shredding a file does not shred its duplicates.** Snapshots, backups,
  copies, editor swap files, and journal/wal copies all keep the data
  alive. Scope the tool to the medium, not the name.
- **Sparse files are a trap.** Shred writes through the whole range,
  which *allocates* every hole: shredding a 10 GiB sparse file turns it
  into a real 10 GiB of blocks. Size targets on shared systems first.
- **`-u` default is `wipesync`, and it is slow.** Byte-by-byte renames
  with fsync on a directory of thousands of files takes orders of
  magnitude longer than the data pass itself; use `--remove=unlink` when
  the name does not matter.
- **Rounded sizes change `ls` output.** A 9-byte file becomes 4096 bytes
  after shredding; if a protocol depends on exact length, pass `-x`.
- **Permissions may block the write.** Read-only files fail to open for
  writing; `-f` chmods them for the pass (and leaves them writable —
  re-chmod afterwards if the mode matters).
- **Do not shred the wrong layer.** `shred` on a file inside a snapshot,
  an encrypted volume's plaintext view, or a thin-provisioned LV only
  churns one copy. Shred the backing device, or rely on crypto-erase.
- **Not present everywhere.** BSD/macOS do not ship GNU shred; busybox
  has a reduced version. Scripts relying on `-n`/`-z`/`--remove` should
  check availability first.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | all operands overwritten (and removed if requested) successfully |
| 1 | any failure: open/write/seek error, bad option, unsupported target |

Failures are reported per file; other operands continue to be processed.

## Related Commands

- [`rm`](./rm.md) — the unlink step shred performs afterwards; no overwriting
- [`truncate`](./truncate.md) — makes files sparse or zero-length, allocating nothing
- [`sync`](./sync.md) — the durability primitive shred uses between passes
- [Collection overview](./overview.md) — all pages in the GNU Coreutils collection

## Interview Questions

### Q: Why does shred's man page warn that it may not work on modern filesystems?

Because shred assumes a write to byte N lands on the same physical
location it read from. Copy-on-write filesystems (btrfs, ZFS) allocate a
new extent for every overwrite and keep the old one; SSD flash translation
layers remap every write to fresh cells and let wear leveling relocate
stale data; journals may hold data copies. In all three cases the "old"
bytes survive somewhere the overwrite cannot reach, so the correct modern
approach is full-disk encryption plus key destruction, or hardware
sanitize/blkdiscard commands.

### Q: What does `shred -u -n1 -z file` actually do, in order?

One random pass over the file with fsync, then one pass of zeros, then
removal of the directory entry — by default via `wipesync`, renaming the
file byte-by-byte with per-byte synchronization so the old name does not
survive in journal replay. Without `-z`, the file would end containing
random data; with it, the final content is indistinguishable from a
zeroed file, which leaks less information about the tool used.

### Q: Why is the file larger after shredding, and how do you prevent that?

Shred rounds the file length up to the next filesystem block (commonly
4096 bytes) so that no part of the final partial block survives; your
9-byte file becomes 4096 bytes. `--exact` (`-x`) disables the rounding
and is the default only for non-regular files such as block devices,
where rounding makes no sense.

### Q: A teammate proposes running shred inside a btrfs subvolume that has snapshots. What do you tell them?

It will not achieve the goal and may amplify storage churn. btrfs is
copy-on-write: the shred passes create new extents while the snapshots
pin the original data extents indefinitely; the sensitive bytes remain in
every snapshot taken before the shred. The right approach is to delete
the snapshots, rely on the volume being encrypted, or wipe the entire
device — not to overwrite one file and hope the CoW layer cooperates.

### Q: When is overwrite-based deletion actually reliable?

On block devices addressed directly (`shred /dev/sdX`), on classic
in-place filesystems on spinning disks (ext2/ext4 with `data=ordered`,
where only metadata is journaled), and as a pre-step to something else —
e.g. zero-filling before compression or before issuing TRIM/BLKDISCARD.
Even then it is a best-effort tool for magnetic media; for flash and COW
storage, cryptographic erasure is the only design that does not depend on
physical overwrite semantics.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/shred.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
