# truncate — shrink or extend a file's size in place

## Overview

`truncate` sets a file's size to an exact byte count — shrinking it (permanently discarding the tail) or extending it (filling the added space with a hole that reads as zeros). It is the command-line face of `ftruncate(2)` and the fastest way to do the two jobs sysadmins meet daily: emptying a growing log file without deleting it, and materializing large sparse files — VM disk images, loop-device payloads, size-fixed test fixtures — in microseconds. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/truncate`.

It is often confused with its neighbors in the size business. `dd of=... seek=N count=0` predates it as the sparse-extension trick and still matters for byte-precise surgery; `fallocate`(1) (util-linux) looks similar but does the *opposite* thing — it reserves real blocks so the file is NOT sparse; and plain `rm` throws away the inode, permissions, and every open file descriptor's view, while `truncate -s 0` keeps the file alive for everyone already holding it. Unlike `touch`, `truncate` is destructive in one direction: a shrink is unrecoverable, with no prompt and no backup.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/truncate |
| First appeared | FreeBSD 4.2 (2000); GNU coreutils 7.1 (2009) |
| Standards | none — GNU/BSD extension, not in POSIX |

## Synopsis

```
truncate OPTION... FILE...
```

One line per mode:

```
truncate -s SIZE FILE...      # set absolute size (creates FILE if missing)
truncate -s +SIZE FILE...     # extend by SIZE
truncate -s -SIZE FILE...     # shrink by SIZE
truncate -s 0 FILE...         # empty the file (the log-rotation idiom)
truncate -c -s SIZE FILE...   # ...but never create (no-create)
truncate -r RFILE FILE...     # take the size from RFILE instead
```

## How It Works

### What ftruncate(2) actually does

`truncate` opens each operand (`O_CREAT` unless `-c`) and issues `ftruncate(2)` with the target size. Two asymmetric things can happen:

```
SHRINK (size < current)
  before: [bbbb][bbbb][bbbb][bbbb]        (4 blocks of data)
  after:  [bbbb]
          └─ blocks beyond the new EOF are freed to the filesystem
          └─ data is GONE: no trash can, no undo

EXTEND (size > current)
  before: [bbbb]
  after:  [bbbb]..........................  (hole to the new EOF)
          └─ NO blocks are allocated for the hole (sparse!)
          └─ reads from the hole return zeros; writes allocate blocks
```

Both paths update mtime and ctime immediately — the size metadata itself is the change. Extension is non-destructive by construction: the file grows logically, and the hole is zero-filled on demand. Shrinking frees real blocks back to the filesystem *at once* — which is why `truncate -s 0` is the instant "df goes down" move on a bloated log, and why it is also the instant "data goes away" move on a mistyped path.

### The SIZE grammar

The `-s` operand is an integer with optional unit and optional adjusting prefix:

| Form | Meaning | Verified result (from 100 bytes) |
| --- | --- | --- |
| `150` | set to 150 bytes | 150 |
| `+50` | extend by 50 | 150 |
| `-20` | shrink by 20 | 130 |
| `%100` | round UP to a multiple of 100 | 200 |
| `/512` | round DOWN to a multiple of 512 | 0 |
| `<32K` | at most 32 KiB (shrink only if larger) | 16384 (unchanged) |
| `>1K` | at least 1 KiB (extend only if smaller) | 1024 (from 100); 5000 stays 5000 |

Unit suffixes follow GNU coreutils' dual convention — this trips people constantly:

```
K=1024   M=1024²   G=1024³ ...        (binary, the default expectation)
KB=1000  MB=1000²  GB=1000³ ...       (decimal, SI)
KiB=K    MiB=M     GiB=G ...          (explicit binary)
```

Verified: `truncate -s 1K` yields 1024 bytes, `truncate -s 1KB` yields 1000, `truncate -s 1M` yields 1048576, `truncate -s 1MB` yields 1000000. The adjusting prefixes combine with suffixes (`-s %+4K` is valid), and `-o`/`--io-blocks` interprets the number in the file's I/O block size instead of bytes — verified: `truncate -o -s 4` on a 4096-byte-block fs produces 16384 bytes.

One documented surprise: reducing below zero does not error. `truncate -s -1M` on a 5000-byte file *empties it* and exits 0 — verified. People expect underflow to fail; instead `-N` clamps at zero, so an oversized `-` operand is a silent full truncate.

### Sparse files, seen from outside

```
$ truncate -s 2M sparse.img
$ stat -c 'size=%s blocks=%b' sparse.img
size=2097152 blocks=0
$ du -h sparse.img
0       sparse.img
$ du -h --apparent-size sparse.img
2.0M    sparse.img
```

`ls -l`/`%s`/`du --apparent-size` report the *apparent* size the OS presents; `du` (default) and `stat %b` report *allocated* blocks. Zero blocks for a 2M file is the sparse fingerprint. Two consequences follow everywhere: backups and copies may inflate the hole into real zeros (`tar` without `-S`, `scp`), and filesystems with different block sizes give different `du` numbers for the "same" sparse file.

### truncate vs the alternatives

| Goal | Tool | Why |
| --- | --- | --- |
| Exact size, sparse extension | `truncate -s N` | one syscall; no data movement |
| Exact size, REAL blocks reserved | `fallocate -l N f` | preallocates; no holes; predictable I/O later |
| Byte surgery at an offset | `dd of=f bs=1 seek=N conv=notrunc` | positioning + partial overwrite |
| Delete the file entirely | `rm f` | inode gone; open FDs keep writing to a ghost |
| Empty but keep the inode | `truncate -s 0 f` (or `> f`) | open FDs see EOF; log idiom |

`> file` from the shell is equivalent to `truncate -s 0` for regular files (the shell opens with `O_TRUNC`), but `truncate` works when the shell's redirection would be clumsy — multiple operands, `-c` guard rails, adjusting prefixes, and no dependence on shell quoting.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-s`, `--size=SIZE` | Set/adjust the size (required unless `-r`) |
| `-c`, `--no-create` | Never create missing operands; silently skip them |
| `-r`, `--reference=RFILE` | Use RFILE's size as the target for each operand |
| `-o`, `--io-blocks` | Interpret SIZE as a count of the file's I/O blocks, not bytes |
| `--help`, `--version` | Standard GNU options |

`-r` combines with the adjusting prefixes: `truncate -r base.bin -s +1M out.bin` sizes `out.bin` one MiB beyond `base.bin`.

## Usage Patterns

```bash
# Empty a growing log without deleting it — open writers keep working
sudo truncate -s 0 /var/log/app/access.log
```

```bash
# Batch-empt a set of rotated logs (inodes, owners, permissions preserved)
sudo truncate -s 0 /var/log/app/*.old
```

```bash
# 10 GiB sparse disk image for a VM, instantly, zero blocks used
truncate -s 10G vm-disk.img
```

```bash
# Pad a fixture to exactly 1 MiB
truncate -s 1M fixture.bin
```

```bash
# Grow a file by 4 KiB without touching the bytes already there
truncate -s +4096 data.raw
```

```bash
# Block-align a file: round down to 4K, or up to 4K
truncate -s /4K video.raw
truncate -s %4K video.raw
```

```bash
# Make this file exactly as large as that one
truncate -r template.bin out.bin
```

```bash
# Cap a cache file at 256 MiB — shrink only if it grew past the cap
truncate -s '<256M' cache.dat
```

```bash
# Resize only files that exist; never leave a stray empty file behind
truncate -c -s 0 orphan.lock
```

```bash
# Salvage the first 512 bytes of a damaged dump, discard the corrupt tail
truncate -s 512 broken.dump
```

```bash
# Before writing a fixed-size structure at EOF, reserve space for it
truncate -s +512 header.dat
```

```bash
# Prove the sparse behavior of an image before shipping it
stat -c '%n: apparent=%s allocated=%b*512' vm-disk.img
```

```bash
# Guarantee a header file is never smaller than one sector (extend-only)
truncate -s '>512' sector.img
```

```bash
# Pre-size a raw loopback payload, then check it mounts cleanly
truncate -s 512M loop.img && sudo losetup -fP --show loop.img
```

## Nuances and Gotchas

- **Shrink is irreversible.** There is no `-i`, no trash, no recovery tool short of forensic carving. The `<`/`>` "at most / at least" modifiers exist precisely because blind absolute sizing is dangerous: `'<32K'` cannot grow a small file, `'>1M'` cannot shrink a big one.
- **`-N` underflow empties instead of failing.** `truncate -s -1M small.bin` zeroes the file and returns 0 (verified). If the current size can be smaller than your delta, compute first or use `<`/`>` semantics.
- **Unit suffixes are binary; `KB` is decimal.** `M` = 1 MiB, `MB` = 1 MB. A `-s 5MB` disk image is 5,000,000 bytes, not 5 MiB — the source of subtle "image too small for the installer" bugs. When in doubt, spell it `MiB`/`GB` explicitly.
- **Sparse ≠ free lunch on every layer.** The hole costs no blocks, but backups, `scp`/`sftp` transfers, and non-sparse-aware copy tools materialize it as real zeros. `cp` (default `--sparse=auto`), `rsync -S`, and `tar -S` preserve holes; `dd` needs `conv=sparse`.
- **Write permission is required even to shrink.** `ftruncate` semantics: the file is opened for writing. Read-only access to an overgrown file you own is not enough without the write bit (or root).
- **Directories and most special files refuse.** `truncate -s 0 /some/dir` fails (EISDIR); device nodes and FIFOs generally fail too — resizing a block device is the `blockdev`/LVM domain, not this tool's.
- **Shrinking a file under an active writer is a contract change.** Processes holding an open descriptor see the new EOF immediately; a writer using explicit offsets may produce a file with a hole back-filled later, while `O_APPEND` writers continue safely at the (new) end. Database folks truncate WAL only when the database itself agrees.
- **`-c` quietly changes failure modes.** Without it, missing operands are created (and a nonexistent parent directory is an error, exit 1). With `-c`, missing operands are skipped and still not an error — mirror of `touch -c`.
- **mtime/ctime change, birth time doesn't.** After truncation the file is "modified"; for content-dedup pipelines that key on mtime, a truncate looks like an edit — because it is one.
- **Not POSIX.** Scripts targeting busybox/BSD should check availability; FreeBSD's `truncate` shares the `-s` grammar but has no `-o`/adjusting-prefix parity guarantees. The old portable idiom is `dd of=f bs=1 seek=SIZE count=0` or `> f` for zeroing.
- **The `<`/`>` prefixes need shell quoting.** Unquoted, the shell consumes them as redirection: `truncate -s >256M qf` actually runs `truncate -s qf` with stdout into a new file `256M` — verified result: exit 1 (`Invalid number: 'qf'`) plus a stray empty `256M` file. Quote them: `truncate -s '>256M' qf`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All operands resized (or skipped under `-c`) |
| 1 | Any failure: bad `-s` grammar, missing `-s`, unwritable path, nonexistent parent, wrong file type |

Verified: `truncate -s 1 /no/such/dir/x` exits 1; `truncate -s -1M tinyfile` (underflow) exits 0 with the file emptied.

## Related Commands

- [`touch`](./touch.md) — updates timestamps instead of size; the other in-place inode editor.
- [`sync`](./sync.md) — force writeback after resizing; `ftruncate`'s freed/extended blocks are cache-managed too.
- [`dd`](./dd.md) — `seek=N count=0` sparse-extension idiom and `conv=notrunc` byte surgery.
- [`rm`](./rm.md) — removes the inode entirely; `truncate -s 0` is the "keep the file, drop the content" alternative.
- [`shred`](./shred.md) — overwrite-in-place before shrinking when the freed blocks matter forensically.
- [`stat`](./stat.md) — `%s` vs `%b` is how you verify sparseness afterwards.
- [`ls`](./ls.md) — `ls -l` shows apparent size; `ls -s` shows allocated blocks.
- [Linux internals](../../internals.md) — sparse files, extents, and block allocation behind holes.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.

## Interview Questions

### Q: What does `truncate -s 2G newfile` do to disk usage, and how do you prove it?

It creates a sparse file: logical size 2097152 bytes with (typically) zero allocated blocks — extension past EOF becomes a hole, and `ftruncate` allocates nothing for it. Proof: `stat -c '%s %b'` shows `2097152 0`, `du -h` reports 0 while `du -h --apparent-size` reports 2.0M, and `df` before/after shows no change. Reads from the hole return zeros without I/O; the first write into any hole region triggers real allocation. This is the mechanism behind instant VM disk images and pre-sized database files.

### Q: Compare `truncate -s 1G`, `fallocate -l 1G`, and `dd if=/dev/zero of=f bs=1M count=1024`.

`truncate` sets the size with a hole: instant, zero blocks, reads-as-zeros, first write pays the allocation cost. `fallocate` reserves real blocks immediately: the file takes 1 GiB on disk now (no holes), later writes skip the allocator — the right choice when predictable latency matters more than space. `dd` from `/dev/zero` writes actual zero bytes: slowest, uses 1 GiB, but produces a *non-sparse-looking* file (unless the filesystem detects zeros, which is a fs-level optimization, not a guarantee). Same apparent size, three completely different storage and performance profiles.

### Q: Why is `truncate -s 0 /var/log/app.log` usually safer than `rm /var/log/app.log` for an active log?

`rm` unlinks the name; processes holding the file open keep writing to the now-anonymous inode, so `df` shows the space consumed until every descriptor closes — the classic "deleted the log but the disk stayed full" mystery. `truncate -s 0` keeps the inode, path, permissions, and all open descriptors valid; writers simply continue at offset 0 (with `O_APPEND`, exactly where they should). The residual subtlety: non-append writers keep their file offset and may create a hole — which is why real log rotation copies then truncates (`copytruncate`) or signals the daemon to reopen.

### Q: What do `+N`, `-N`, `%N`, `/N`, `<N`, `>N` do in `-s`, and which combination prevents accidental damage?

`+N` extends by N bytes; `-N` shrinks by N (clamping at zero, silently); `%N` rounds the size up to a multiple of N; `/N` rounds down; `<N` shrinks only if the file is larger; `>N` extends only if smaller. The non-destructive pair is `<`/`>` — they enforce a bound instead of imposing a size, so `truncate -s '<256M' cache.dat` can only ever shrink an oversized cache and `>1M'` can only ever pad an undersized one. Absolute sizes and `-N` are the destructive forms.

### Q: `ls -l` says 2M for a file, `du` says 0. Name three mechanisms that can explain a disagreement like this, and which one applies here.

(1) Sparse files: holes mean apparent size exceeds allocated blocks — this is the case here (created by `truncate`). (2) Filesystem overhead: every file rounds up to at least one block, so many small files make `du` exceed apparent bytes — the opposite direction. (3) Compression/deduplication (btrfs, zfs, overlayfs layers) can make allocated usage smaller than the logical bytes. The diagnostic is `stat -c '%s %b'` plus `df -T`: size vs blocks vs filesystem type usually settles it in one line.

### Q: You need the last 100 MiB gone from a 1 GiB capture file, keeping the first 924 MiB intact. Give the command and two things to verify afterwards.

`truncate -s 924M capture.raw` — but only after checking the suffix semantics: `924M` here means 924×1024×1024. Verify with (1) `stat -c '%s'` for the exact new size, and (2) a checksum of the retained prefix (`head -c 968884224 capture.raw | sha256sum` compared against the original) — `truncate` cannot corrupt bytes below the new EOF, and demonstrating that with a hash is the professional way to close the change ticket. If the capture might be referenced elsewhere, also confirm no other hard links exist (`stat -c %h`): truncation is visible through every name of the inode.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/truncate.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
