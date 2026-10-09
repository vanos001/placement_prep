# wipefs — wipe filesystem, RAID, or partition-table signatures

## Overview

`wipefs` erases **signature magic strings** — the filesystem superblocks, RAID superblocks, and partition-table headers that libblkid recognizes — from a block device, so the kernel and probing tools stop seeing an old filesystem there. It does **not** erase the data: blocks outside the magic strings are untouched, and wipefs is explicitly *not* a secure eraser. Without arguments it merely *lists* the signatures it can see on a device, with their types and offsets. It ships in the Debian `util-linux` package at `/usr/sbin/wipefs`.

You reach for it when reusing disks: a leftover GPT from a previous life makes the disk "unusable" for a new partitioner, an old mdadm superblock makes a disk join a phantom RAID array at boot, or a stale ext4 signature confuses `mount`/`blkid` after you built a new layout with `dd`. It is often confused with `dd if=/dev/zero` (brute-force overwriting — slower, unnecessary, and destructive to data you may want to recover), `blkid` (the read-only signature prober it shares code with), and `mkfs` (which *writes* a fresh signature rather than removing one).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/wipefs |
| First appeared | early-2010s util-linux (built on libblkid) |
| Standards | none; libblkid signature database |

## Synopsis

```
wipefs [options] <device>...                # list signatures (no -a/-o given)
wipefs [--backup] -o <offset> <device>...   # erase one signature by offset
wipefs [--backup] -a <device>...            # erase all recognized signatures
```

Main one-line forms:

```
wipefs /dev/sdb                       # list: what signatures exist
wipefs -a /dev/sdb                    # wipe all signatures on the disk
wipefs -a /dev/sdb1 /dev/sdb2 /dev/sdb  # partitions first, then the table
wipefs -o 0x438 /dev/sdb              # erase the signature at one offset
wipefs -n -a /dev/sdb                 # dry run: what *would* be wiped
```

## How It Works

### Signature anatomy

Why offsets dominate the tool's semantics — where the common signatures live:

```
signature        location                    notes
---------------  --------------------------  ------------------------------
GPT primary      LBA 0-33 (0x0 + table)      protective MBR + header + entries
GPT backup       last 33 LBAs of the disk    survives "dd first MiB" cleanups
MBR (msdos)      LBA 0 (0x0), 512 bytes      partition entries inside sector 0
ext2/3/4 sb      offset 0x438 (1024+56)      the classic "superblock at 1 KiB"
XFS sb           offset 0                    whole-device superblock
md/RAID sb       0.9/1.0/1.1/1.2 layouts     1.2 = 4 KiB into the device
swap (swsusp)    page-aligned header         blocks mkswap reuse confusion
```

The ext4 case motivates `-o 0x438`: one wiped superblock copy makes blkid stop reporting the FS even though backup superblocks (and all data) remain — convenient for repurposing, misleading if you believed the FS is "gone". The GPT backup header is why the partition-first recipe matters.

### wipefs in provisioning workflows

Cloud-init/kickstart/Ansible disk roles standardize on the pattern:

```bash
# idempotent disk reset (Ansible-ish shell)
if blkid -o value -s TYPE /dev/vdb | grep -q .; then
    wipefs -a /dev/vdb* 2>/dev/null; wipefs -a /dev/vdb
fi
```

Wipe-then-partition is also what `sgdisk --zap-all` emulates, and what a failed `parted mklabel` hints at when it complains about existing signatures. In recovery contexts the `-b` backup plus the parsable output (`-p`/`-J`) gives auditable before/after state — a property dd-based wiping never had.

### Probing, listing, erasing

`wipefs` reuses libblkid's probing database: it reads the device, matches magic strings at known offsets, and reports them. The erasing step overwrites exactly those signature bytes (typically a few hundred bytes at fixed offsets) and notifies the kernel:

```
$ wipefs /dev/sdb
DEVICE  OFFSET      TYPE    UUID      LABEL
sdb     0x0         gpt
sdb     0x200       gpt     (primary header)
sdb     0x1dffffe00 gpt     (backup header)
```

GPT is the canonical example of why offsets matter: the table lives at the *start* and the *end* of the disk, so a naive `dd` of the first MiB leaves the backup header — and tools will happily "recover" the old partition table from it. `wipefs -a` clears all of them.

After erasing a partition-table signature, wipefs calls the `BLKRRPART` ioctl as its last step so the kernel re-reads partition devices (`/dev/sdb1`... disappear without a reboot) — which is why the recommended whole-disk cleanup erases the partitions first and the disk last:

```bash
wipefs -a /dev/sdb1 /dev/sdb2 /dev/sdb
```

### Guards and safety rails

- Wiping a *mounted* device fails (EBUSY via the default exclusive device lock; `--lock=nonblock|no` exists for special cases).
- `--force` is required to erase nested signatures on non-whole-disk devices (e.g. a leftover FS signature *inside* a partition device) — by default wipefs refuses to touch nested tables.
- `--backup[=dir]` writes each signature to `wipefs-<devname>-<offset>.bak` (in `$HOME` or the given dir) *before* removing it, making the operation reversible:

```
erase flow:  probe ──> backup signature(s) ──> overwrite magic bytes
                     (wipefs-<dev>-<off>.bak)  ──> BLKRRPART (if table wiped)
```

Restoring is the same tool in reverse: `dd if=bak of=/dev/sdb seek=<offset> conv=notrunc` re-creates the old signature (offsets printed by the backup file naming).

### What it does not do

It zeroes *only* the magic strings. All file data, and even most metadata, remains on disk and is trivially recoverable with carving tools. For disposal you need `blkdiscard` (SSD/TRIM), `shred`/`dd`/crypto-erase, or `nvme format`. wipefs answers "make the device look blank to the kernel", not "make the data unreadable".

## Options That Matter

| Option | Effect |
| --- | --- |
| (none) | List detected signatures: type, offset, UUID, label. |
| `-a, --all` | Wipe all recognized signatures on the device. |
| `-o, --offset <num>` | Erase only the signature at this offset (suffixes KiB/MiB... accepted). |
| `-t, --types <list>` | Restrict to filesystem/RAID/partition-table types (e.g. wipe only `raid`). |
| `-b, --backup[=<dir>]` | Back up each signature before erasing (`wipefs-<dev>-<offset>.bak`). |
| `-n, --no-act` | Do everything except the actual write — the safe dry run. |
| `-f, --force` | Allow erasing nested signatures on partition devices / proceed aggressively. |
| `--lock[=<mode>]` | Exclusive device lock: `yes` (default), `nonblock`, `no`. |
| `-J, --json` / `-p, --parsable` | JSON or machine-parsable listing output. |
| `-O, --output <list>` | Columns for listings: `UUID`, `LABEL`, `LENGTH`, `TYPE`, `OFFSET`, `USAGE`, `DEVICE`. |
| `-q, --quiet` | Suppress the per-wipe messages. |

## Usage Patterns

```bash
# What signatures does this disk carry?
wipefs /dev/sdb
```

```bash
# Reuse a disk: clear the old GPT (both headers) — the standard recipe
wipefs -a /dev/sdb1 /dev/sdb2 /dev/sdb
```

```bash
# Preview exactly what would be erased
wipefs -n -a /dev/sdb
```

```bash
# Kill only a stale mdadm superblock so the disk stops auto-assembling
wipefs -a -t raid /dev/sdb
```

```bash
# Wipe one signature by its offset from the listing
wipefs -o 0x1dffffe00 /dev/sdb
```

```bash
# Wipe with a safety net: signatures backed up to ~/wipefs-*.bak
wipefs -b -a /dev/sdc
```

```bash
# Machine-readable listing for provisioning scripts
wipefs -J -O PATH,TYPE,UUID /dev/nvme0n1
```

```bash
# Clean a loop device built from an image file
losetup -fP disk.img && wipefs -a /dev/loop0
```

```bash
# Reversal: restore a backed-up signature at its offset
dd if=~/wipefs-sdb-0x00000200.bak of=/dev/sdb bs=1 seek=$((0x200)) conv=notrunc
```

```bash
# Confirm the device is signature-free before mkfs
wipefs /dev/sdb && mkfs.ext4 /dev/sdb
```

```bash
# Ansible/cloud-init style idempotent reset of a data disk
blkid /dev/vdb >/dev/null 2>&1 && wipefs -a /dev/vdb1 /dev/vdb2 /dev/vdb
```

```bash
# Audit an unknown image file before mounting it
wipefs -J disk.img | jq -r '.signatures[] | .type + " @" + .offset'
```

```bash
# Wipe only filesystem signatures, keep partition table intact
wipefs -a -t ext4,xfs,btrfs /dev/sdb1 /dev/sdb2
```

```bash
# Get a parsable single line per signature for logging
wipefs -p /dev/sdb | tee /var/log/disk-reset.log
```

## Nuances and Gotchas

- **Not a data shredder.** The `-a` flag's "BE CAREFUL!" is about killing signatures, not about privacy; data remains. Confusing wipefs with secure erase is a classic (and dangerous) interview misconception.
- **Wipe partitions before the disk.** The whole-disk recipe (`-a` on partitions, then the disk) exists because BLKRRPART and nested-signature rules interact; wiping only the disk's GPT while partition signatures remain leaves a half-probed state.
- **`--force` exists because nested signatures are refused by default.** A filesystem signature inside a partition device, or a leftover table inside an image, needs `-f` — the default protects you from wiping something the kernel currently presents as a partition.
- **Mounted or in-use devices fail.** The exclusive lock (and EBUSY) refuses wiping active devices; if you *must* work around it (`--lock=no`), you are corrupting a live view — don't.
- **Loop devices and images.** wipefs works on regular files too (via loop or directly), which makes it the clean way to reset image files between test runs — much cheaper than zeroing.
- **Stale RAID superblocks boot-loop systems.** A disk with an old md superblock gets pulled into an array by auto-assembly at boot; wiping `-t raid` before repurposing is preventive medicine. Conversely, wiping a member of a *live* array destroys it — verify array state (`/proc/mdstat`) first.
- **Backup restore needs the exact offset.** The `.bak` filename encodes it; restoring at the wrong offset re-corrupts. Note the restore is `dd`, not a wipefs flag.
- **Partition devices disappear on table wipe.** After BLKRRPART, `/dev/sdb1` nodes vanish; scripts iterating over partitions after a table wipe must re-scan (`partprobe`/`lsblk`).
- **The lock is per-invocation.** Two concurrent wipefs runs can still race (lock is not a global queue) — serialize disk-reset steps in your orchestrator instead of relying on `--lock` alone.
- **Wiping is visible to multipath/RAID layers.** A device that is a multipath path or a live md member may refuse or, worse, propagate the wipe to shared storage. Always confirm the device is not claimed by `dmsetup ls`/`/proc/mdstat` before `-a`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Listing succeeded; with `-a`/`-o`, all requested signatures wiped (or would be, with `-n`). |
| 1 | Probe failure, busy/locked device, permission denied, or a requested signature could not be erased. |

## Related Commands

- [`blkid`](./blkid.md) — the read-only signature prober; run before and after wipefs.
- [`findfs`](./findfs.md) — locates devices by the very signatures wipefs removes.
- [`mkfs`](./mkfs.md) — writes a fresh filesystem signature where an old one was wiped.
- [`losetup`](./losetup.md) — loop-device plumbing for practicing on image files.
- [`blkdiscard`](./blkdiscard.md) — the actual data-erasing counterpart for SSD sectors (TRIM/erase).
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What exactly does `wipefs -a /dev/sdb` destroy, and what does it leave intact?

It overwrites the magic strings of every signature libblkid recognizes — filesystem superblocks, RAID superblocks, GPT/MBR headers at all offsets — and re-reads the partition table into the kernel. File contents and all other blocks are untouched, so the data is still recoverable; the device just stops *presenting* an old filesystem to mount/blkid.

### Q: Why is the canonical reuse recipe `wipefs -a /dev/sdb1 /dev/sdb2 /dev/sdb` rather than just the disk?

Because signatures exist at multiple levels: partition-table structures at the disk level (GPT backup header at the *end* of the device!) and filesystem signatures inside each partition device. Erasing the table alone leaves FS signatures that blkid still reports; erasing only partitions leaves the table. Doing partitions first then the disk also plays correctly with the BLKRRPART re-read wipefs issues after a table wipe.

### Q: A server boots and a disk "joins" a nonexistent RAID array. What happened and how do you fix it?

The disk carries a stale mdadm superblock, and md auto-assembly assembles any disks whose superblocks match an array UUID. Fix: confirm the array is truly retired, stop it (`mdadm --stop`), then `wipefs -a -t raid /dev/sdX` on each member to remove only RAID signatures. This is the textbook targeted-wipe use of the `-t` filter.

### Q: How would you make a wipefs operation reversible, and what are the limits?

Use `--backup[=dir]`: each erased signature is saved as `wipefs-<dev>-<offset>.bak` before removal, and you restore with `dd` to the exact encoded offset. Limits: only the signature bytes are backed up — the rest of the old filesystem is unchanged anyway, but a restore at the wrong offset corrupts the device, and the restore step is manual dd, not a wipefs flag.

### Q: Why does wipefs refuse to wipe nested signatures without `--force`?

Because on a non-whole-disk device, a detected signature is usually *content* (a filesystem living inside a partition) rather than container metadata you intend to remove. Requiring `--force` for nested erasure protects against wiping live data structures through a partition view; the flag documents that you understood the layering.

### Q: Compare `wipefs -a`, `blkdiscard`, and `dd if=/dev/zero` for preparing a disk.

wipefs removes recognized signatures only — instant, non-destructive to data, ideal before repartitioning/reusing. blkdiscard de-allocates entire sector ranges on SSDs via TRIM/discard — fast, data-destroying on such devices, but a no-op on devices without discard support. dd zeroing overwrites everything — slow, unnecessary for reuse, and the only one of the three that is also (single-pass) data sanitization. Picking by intent — re-probe, erase, or sanitize — is the answer interviewers want.

### Q: After `wipefs -a /dev/sdb`, `lsblk` still shows no partitions but `blkid /dev/sdb` now prints nothing, yet your backup superblocks exist. Is the filesystem recoverable?

Yes — wipefs only removed the primary superblock magic; ext4 backup superblocks and all data blocks are intact. Recovery is either re-writing the signature bytes from a `-b` backup at the recorded offset, or running `mke2fs -S`/fsck-style salvage against a backup superblock (`e2fsck -b 32768 ...`). The scenario exists to test whether candidates confuse "signature wiped" (probe-level invisibility) with "filesystem destroyed" (block-level loss) — wipefs does the former by definition.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/wipefs.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
