# dd — block-level copy and convert

## Overview

`dd` copies data block by block, with configurable block sizes, offsets, and byte-level conversions. It reads from an input file (by default stdin) and writes to an output file (by default stdout), making it the standard tool for raw-device work: disk and partition images, MBR backups, wiping media, benchmarking throughput, and surgically patching bytes at fixed offsets. It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at `/usr/bin/dd` on modern Debian/Ubuntu systems.

The name famously echoes the **DD (data definition) statement of IBM JCL** — `dd`'s operand syntax (`if=`, `of=`, `bs=`) is a deliberate nod to JCL rather than normal Unix option style. That syntax is also its biggest footgun: operands use `key=value` with no leading dash, and `dd -if` is an error. Where `cp` thinks in files and inodes, `dd` thinks in blocks and byte offsets — you reach for it when the position of bytes matters more than the identity of files.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/dd |
| First appeared | Version 5-era AT&T UNIX (1974); named for IBM JCL's DD statement |
| Standards | POSIX.1-2018 (`dd`) |

## Synopsis

```
dd [OPERAND]...
dd OPTION
```

Typical one-line forms:

```
dd if=IN of=OUT bs=1M              # plain block copy with 1 MiB blocks
dd if=/dev/sda of=mbr.img bs=512 count=1   # fixed-size extraction
dd if=IN of=OUT conv=fsync status=progress # durable, monitored copy
dd of=FILE bs=1 seek=OFFSET        # byte surgery at an offset
```

## How It Works

### Operand grammar

Every argument is `key=value`; there are no dashes. Order is irrelevant. Numeric values take multiplicative suffixes — and GNU offers *both* families:

```
c=1, w=2, b=512            byte, word, block
kB=1000  K=1024  KiB=1024  the "K vs kB" distinction is real
MB=1000² M=1024² MiB=1024² likewise for M, G, T, ...
N ending in 'B' counts BYTES not blocks (recent coreutils)
```

`bs=BYTES` sets both read and write size and overrides `ibs`/`obs`. `count=N` copies at most N input *blocks* (independent of byte size), `skip=N` skips N `ibs`-sized input blocks, `seek=N` seeks N `obs`-sized output blocks forward. Mixing `bs=4M` with `count=10` copies 40 MiB — not 10 bytes.

### Positioning: skip, seek, and offsets

`skip` and `seek` turn `dd` into a byte-addressable editor:

```
input:   [ blk0 ][ blk1 ][ blk2 ][ blk3 ][ blk4 ]
                skip=2 ────┐        count=2 ────┐
                           ▼                      ▼
output:  [ blk0 ][ blk1 ][ seek=2 → blk2 ][ blk3 ]   (conv=notrunc!)
```

Because positioning is in blocks, `skip=1 seek=1 bs=512` and `skip=1 seek=1 bs=4M` address wildly different offsets. When you need byte addressing, the standard trick is a one-byte block size plus a byte-valued count, or — cheaper — a large aligned `bs` whose multiples land where you need. On devices, `seek` past the current end of the output *extends* it (with a hole, on regular files), which is the instant-sparse-file idiom: `dd of=vol.img bs=1M seek=1024 count=0`.

### Block size and syscall arithmetic

The default 512-byte block size is a historical artifact (the disk sector size of the era). Every read and write is a syscall, so a 1 GiB copy at `bs=512` costs ~2 million syscalls; at `bs=1M` it costs ~1 thousand. For large transfers, sizes from 1M to 16M typically saturate; beyond that, gains flatten. Two caveats:

- `iflag=direct`/`oflag=direct` require the buffer size to be aligned to the device's logical block size, or the kernel returns EINVAL.
- Tapes and some record-oriented devices still care about `obs` as the record length — the reason `ibs`/`obs` survive at all.

### The data path

```
   stdin / if=FILE
        │  read up to ibs bytes (short reads possible!)
        ▼
 ┌──────────────┐   conv= list applied
 │ input buffer │   (swab, lcase, block/unblock, sync ...)
 └──────┬───────┘
        ▼
 ┌──────────────┐   iflag= / oflag= modifiers
 │ output buffer│   (direct, dsync, fullblock, nonblock ...)
 └──────┬───────┘
        ▼
   write obs bytes to of=FILE / stdout
   (seek/skip decide WHERE; conv=notrunc decides if truncation happens)
```

Two behaviors distinguish `dd` from `cp` here:

- **Short reads are normal.** A read may return fewer than `ibs` bytes (pipes, tapes, flaky media). Without `iflag=fullblock`, that short read is written as one short output block — the reason patched-together reads from a pipe can desynchronize byte offsets.
- **The output is truncated on open** unless `conv=notrunc`. This is the classic `dd` data-loss story: `dd if=small of=big.img` leaves `big.img` *exactly* `small`'s size — everything after is gone.

### Reading the status line

```
$ dd if=/dev/zero of=zeros.img bs=1M count=5
5+0 records in
5+0 records out
5242880 bytes (5.2 MB, 5.0 MiB) copied, 0.00270917 s, 1.9 GB/s
```

`5+0` means 5 full blocks plus 0 partial blocks. The byte count is shown in both decimal (MB) and binary (MiB) units — useful sanity checks when a vendor quotes "4.7 GB" media. `status=progress` prints a continuously updating line on stderr; `status=none` silences everything but errors; `status=noxfer` drops the final stats. On a running `dd`, sending `USR1` (GNU; SIGINFO on BSD/macOS) prints statistics and continues — the traditional progress hack in scripts.

### conv= conversions

| Symbol | Effect |
| --- | --- |
| `notrunc` | Do not truncate the output file on open |
| `noerror` | Continue after read errors (pairs with `sync`) |
| `sync` | Pad each input block with NULs (spaces with block/unblock) to ibs size |
| `sparse` | Seek instead of writing all-NUL output blocks |
| `swab` | Swap every pair of input bytes |
| `lcase` / `ucase` | Lowercase / uppercase conversion |
| `block` / `unblock` | Fixed-length cbs records with newline padding/trimming (line printer & EBCDIC era) |
| `ascii`, `ebcdic`, `ibm` | Character-set conversion tables |
| `excl` / `nocreat` | Fail if output exists / never create the output |
| `fsync`, `fdatasync` | Physically write data (and metadata) before exiting |

`conv=noerror,sync` is the canonical damaged-media invocation: continue past read errors and pad the failed block with NULs so the *offsets* of subsequent data stay aligned. Dropping `sync` silently compresses the image around the bad spots and misaligns everything — a classic recovery mistake.

### iflag= / oflag= modifiers

`direct` (O_DIRECT — bypass the page cache), `dsync`/`sync` (synchronized I/O), `nonblock`, `nofollow`, `noatime`, `nocache` (drop caches around the transfer), `directory` (fail unless the input is a directory), `append` (output), and `fullblock` (input only: accumulate full ibs blocks before writing — mandatory when `ibs` exceeds what a pipe delivers per read). Flags are comma-separated: `iflag=direct,fullblock`.

## Options That Matter

| Operand | Effect |
| --- | --- |
| `if=FILE` / `of=FILE` | Input/output path (default stdin/stdout) |
| `bs=BYTES` | Block size for both directions (default 512) |
| `ibs=` / `obs=` | Independent read/write block sizes |
| `count=N` | Copy at most N input blocks (`NB` suffix = N bytes, recent coreutils) |
| `skip=N` / `seek=N` | Skip N input blocks / N output blocks before copying |
| `conv=LIST` | Comma-separated conversions (see table above) |
| `status=LEVEL` | `none`, `noxfer`, or `progress` |
| `iflag=` / `oflag=` | Comma-separated I/O flags |
| `cbs=BYTES` | Conversion record size for block/unblock |

`--help` and `--version` are the only dash-style options; everything else is an operand.

## Usage Patterns

```bash
# Back up the first 512 bytes of a disk — partition table + bootloader
sudo dd if=/dev/sda of=/root/sda.mbr bs=512 count=1

# Full image of a USB stick for duplication or reverse engineering
sudo dd if=/dev/sdb of=/var/img/usb.img bs=4M status=progress conv=fsync
```

```bash
# Write an ISO to a USB drive, forcing data to hit the planks before unplug
sudo dd if=debian-12.iso of=/dev/sdb bs=4M status=progress oflag=direct
```

```bash
# Wipe a disk with zeros (or random data for pre-destruction sanitizing)
sudo dd if=/dev/zero of=/dev/sdz bs=1M status=progress
sudo dd if=/dev/urandom of=/dev/sdz bs=1M status=progress
```

```bash
# Extract bytes 1MiB..2MiB of a file (skip is in ibs-sized blocks)
dd if=coredump.img of=chunk.bin bs=1M skip=1 count=1

# Patch 4 bytes at offset 0x1F8 of a boot sector without touching anything else
printf '\x55\xaa' | dd of=boot.bin bs=1 seek=504 conv=notrunc
```

```bash
# Force a file to zero length without deleting it (truncate via write)
dd of=large.log bs=1 count=0

# Create a 1 GiB sparse file instantly
dd of=volume.img bs=1M seek=1024 count=0
```

```bash
# Rough sequential read benchmark, cache-bypassed
dd if=/dev/nvme0n1 of=/dev/null bs=1M count=4096 iflag=direct status=progress

# Measure write durability, not cache performance
dd if=/dev/zero of=test.bin bs=1M count=1024 conv=fdatasync status=progress
```

```bash
# Rescue data from scratched media: keep going, keep offsets aligned
dd if=/dev/cdrom of=rescue.iso bs=2048 conv=noerror,sync status=progress

# Zero-copy-ish swap of two byte pairs (endianness fixups on old formats)
dd if=oldfile of=swapped conv=swab
```

```bash
# Generate a fixed-size key file without leaking through a shell variable
dd if=/dev/urandom of=/etc/crypt.key bs=64 count=1

# Copy a partition preserving sparseness in the image
dd if=/dev/sda1 of=root.img bs=4M conv=sparse status=progress
```

```bash
# Copy with a progress pipeline the old way: status=progress is easier,
# but this works on any dd (BSD, busybox) that prints stats on USR1
sudo dd if=/dev/sda of=/dev/sdb bs=4M &
sleep 5; while kill -USR1 "$!" 2>/dev/null; do sleep 30; done
```

```bash
# Discard device-backed data (TRIM-like) on supporting drives, block cache aside
sudo dd if=/dev/zero of=/dev/sdz bs=1M count=1024 iflag=nocache oflag=direct

# Compare cold-cache read speed of two disks in one script
for d in /dev/sda /dev/sdb; do
  dd if="$d" of=/dev/null bs=1M count=2048 iflag=direct status=none && echo "$d done"
done
```

```bash
# Classic fixed-record conversion: pad short lines to 80 columns with spaces
# (line-printer heritage; still seen in mainframe interchange formats)
dd if=report.txt of=report.fx bs=80 cbs=80 conv=block

# The reverse: strip the padding back to newline-terminated text
dd if=report.fx of=report.txt bs=80 cbs=80 conv=unblock
```

## Nuances and Gotchas

- **`of=` truncates by default.** Writing a smaller file onto a bigger one destroys the tail unless you pass `conv=notrunc`. The mirror error: writing to a *device* image file without `notrunc` when you intended an in-place patch.
- **`skip=`/`seek=`/`count=` are in blocks, not bytes.** With `bs=4M`, `skip=3` skips 12 MiB. Switching to `bs=1` for byte-granular work is correct but slow; recent GNU coreutils allow a `B` suffix on counts to mean bytes (`count=1024B`).
- **`bs` too small is a performance cliff.** The default 512-byte blocks turn a 1 GiB copy into two million syscalls. For plain throughput use `bs=1M` or larger; for offsets, use big `bs` with matching `skip`/`seek` or a single `bs=1` byte-surgery command.
- **Progress and durability are separate concerns.** `status=progress` only reports; `oflag=direct` skips the cache; `conv=fsync` forces flush at the end. A "completed" `dd` without fsync can still be sitting in RAM — yank the USB stick early and the image is short.
- **`conv=noerror` without `sync` corrupts alignment.** Bad blocks are *omitted*, and everything after shifts down. Always pair them when offsets matter.
- **Signals differ by implementation.** GNU `dd` accepts `USR1` (and in newer releases `USR2` too) for mid-run stats; BSD/macOS uses `SIGINFO` (`Ctrl-T`). BusyBox `dd` is a much smaller dialect: no `iflag=`/`oflag=`, fewer `conv=` symbols.
- **`dd if=/dev/zero of=/dev/sda` is a blind eraser.** It overwrites in order and stops at no boundary but `count`; a typo in `of=` is unrecoverable. It also verifies nothing: `sha256sum` both sides (or `cmp`) afterwards is the cheap correctness check.
- **`excl` as a safety rail.** `of=/dev/sdb conv=excl` fails if the target is already something unexpected; `conv=nocreat` refuses to create a file, so a typo'd output path aborts instead of silently writing a new file.
- **POSIX vs GNU.** POSIX defines the core operands (`if`, `of`, `bs`, `count`, `seek`, `skip`, basic `conv=` set) but not `status=progress`, the flags, or the sparse handling. GNU's decimal/binary suffix matrix (`MB` vs `M`) is deliberate and documented in `--help`.
- **`dd` is not a disk-image format tool.** It copies bytes; partition tables, filesystem metadata and everything else are just payload. A "disk image" made from a mounted, live filesystem is internally inconsistent — image a quiesced device or a snapshot, then run filesystem checks on the copy.
- **Verify with hashes, not with the status line.** The record counts prove blocks moved, not that the bytes match; `sha256sum` both source and copy, or a plain `cmp`, is the cheap correctness check.
- **`oflag=direct` alignment.** O_DIRECT demands aligned buffers and sizes on many devices; a stray `bs=3M` fails where `bs=1M` works. When you see `Invalid argument` out of nowhere, suspect alignment.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Transfer completed (tolerated `noerror` reads included) |
| nonzero (1) | Any write failure, invalid operand, or un-tolerated read error |

## Related Commands

- [`cp`](./cp.md) — file-semantics copy with attribute preservation; the everyday alternative.
- [`mktemp`](./mktemp.md) — safe scratch files that `dd` output or input can point at.
- [`mknod`](./mknod.md) — create the device nodes `dd` so often reads and writes.
- [`install`](./install.md) — copy with attribute enforcement, the file-level counterpart.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [Linux internals](../../internals.md) — page cache, direct I/O, and block device layers behind `oflag=direct`.
- [Process management](../../admin/process-management.md) — sending USR1 to a running `dd` and inspecting it with strace/iotop.

## Interview Questions

### Q: Why is it called `dd`, and what does that heritage explain about its syntax?

The name and operand style (`if=`, `of=`, `bs=`) come from the DD (data definition) statement of IBM System/360 JCL — a nod by its Bell Labs authors. The heritage explains the syntax's oddity: no dashes, `key=value` operands, conversions as lists. It also explains why `dd` feels like a miniature ETL language (block/unblock, EBCDIC tables) rather than a normal Unix filter.

### Q: What is the difference between `bs=1M` and `ibs=1M obs=1M`?

For plain copies, little — `bs` sets both. The difference surfaces at the edges: `skip=` counts `ibs` blocks and `seek=` counts `obs` blocks, so with independent sizes those offsets diverge; and `fullblock` accumulation only exists on the input side. Also, with `bs=` set, a single short read still produces a short write, whereas splitting sizes makes the asymmetry explicit. In practice: use `bs` for throughput, `ibs`/`obs` only when offsets or device-specific record sizes demand it.

### Q: You need to overwrite bytes 1024–1031 of a 4 GB image. Give the command and the flag people forget.

`printf '8 bytes' | dd of=image.img bs=1 seek=1024 count=8 conv=notrunc`. The forgotten flag is `conv=notrunc` — without it, `dd` truncates the 4 GB file at the point where writing stops, silently destroying everything after the patch. Using `bs=1 count=8` bounds the write; `seek=1024` positions it.

### Q: What does `conv=noerror,sync` do and why is `sync` the part people drop?

`noerror` keeps copying after read errors (a scratched CD, failing sector); `sync` pads each short/failed block to the full input block size with NULs so byte offsets stay aligned with the original medium. People drop `sync` and get a "recovered" image that is smaller than the source with every subsequent byte shifted — the image looks plausible and decompresses, but its internal offsets are wrong. The pair belongs together whenever the image will be mounted or parsed.

### Q: How do you monitor a long-running `dd` started from a provisioning script?

Modern: start it with `status=progress`. Legacy/already-running: `kill -USR1 <pid>` (GNU) makes `dd` print its statistics to stderr and continue — scripts historically looped this. BSD/macOS uses `SIGINFO` via `Ctrl-T`. Alternatively attach `strace -p` or watch `/proc/<pid>/io` for read/write bytes. Knowing the signal trick is the expected interview answer.

### Q: Why does `dd if=/dev/zero of=test bs=1M count=100` report a much higher throughput than the disk is capable of?

The writes land in the page cache and are flushed asynchronously after `dd` exits. To measure real write throughput, force durability: `conv=fdatasync` (flush data before finishing), `conv=fsync` (data plus metadata), or `oflag=dsync`/`oflag=direct` (synchronized/bypassed I/O during the run). Reading the disk the same way needs `iflag=direct` to avoid serving from cache — the same reason a second identical run of a read benchmark is suspiciously fast.

### Q: When would you choose `dd` over `cp`, and when is that choice wrong?

Choose `dd` when byte position, fixed block counts, or raw devices are the point: images of unmounted disks/partitions, boot-sector surgery, fixed-size extractions, benchmarks with cache control. It's the wrong choice for file trees — `dd if=dir` is an error; it has no notion of recursion, metadata, or attributes. It is also the wrong tool for copying a *mounted, changing* filesystem: you get a torn image, and `dd` will happily write garbage to the wrong device if `of=` is mistyped. That last failure mode is why careful operators write to a file first, verify, then image the device.

### Q: What are `ibs`, `obs` and `cbs` for, given that `bs` seems to cover everything?

`ibs`/`obs` split the read and write record sizes — historically the physical record sizes of tapes and line printers, still relevant for `skip`/`seek` accounting (they count `ibs`/`obs` blocks respectively) and for devices with asymmetric block constraints. `cbs` is the conversion buffer for the record conversions `block`/`unblock` and the character-set conversions (`ascii`, `ebcdic`): padding or trimming fixed-length records. If you are not doing record-oriented conversion, `bs` is all you need — which is exactly why it is the flag everyone remembers.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/dd.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — dd](https://pubs.opengroup.org/onlinepubs/9699919799/)
