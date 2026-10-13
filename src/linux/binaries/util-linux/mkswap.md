# mkswap — set up a Linux swap area

## Overview

`mkswap` writes the swap-area header onto a partition or file so the kernel can use it as swap: a version-1 area description with a UUID and optional label, terminated by the magic string `SWAPSPACE2`. It initializes nothing else — no formatting, no data placement — and is the mandatory step between "I have a partition/file" and `swapon`. Every swap area on a running system got its signature from this tool (or a compatible one).

It ships in the `util-linux` package at `/usr/sbin/mkswap`. It is often confused with `swapon`/`swapoff` (which activate/deactivate areas — different tool, different `-p` meaning!), with `fallocate`/`dd` (which only create the *file* the swap area lives in), and with `blkid` (which later reports the UUID/label mkswap wrote).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/mkswap |
| First appeared | earliest Linux userspace (0.9x era) |
| Standards | None — Linux swap format |

## Synopsis

```
mkswap [options] <device> [size]
```

Common one-line forms:

```
mkswap /dev/sdb2                  # initialize a swap partition
mkswap /swapfile                  # initialize a swap file (after chmod 600)
mkswap -L swap1 -U <uuid> /dev/sdb2
chmod 0600 /swapfile && mkswap /swapfile && swapon /swapfile
```

## How It Works

### What gets written: the version-1 header

The first page of the area carries the header: the first 1 KiB stays free (boot-sector/partition-table territory), followed by the swap description — version, page count, UUID, label — with the 10-byte magic `SWAPSPACE2` placed at the *end of the first page*. `swapon` validates exactly that: header version and the magic in the expected place. Real run on a 4 MiB file (verified):

```
$ dd if=/dev/zero of=/tmp/sw.img bs=1M count=4
$ mkswap /tmp/sw.img
mkswap: /tmp/sw.img: insecure permissions 0664, fix with: chmod 0600 /tmp/sw.img
Setting up swapspace version 1, size = 4 MiB (4190208 bytes)
no label, UUID=1f6bf338-e42c-4598-9418-7a18238b1cde
```

```
first page: [ boot bits ][ swap header: ver, npages, UUID, label ][SWAPSPACE2]
                                                          ▲
                                        magic = last 10 bytes of page 0
```

The size it prints is the usable area (device size minus the page holding the header — note `4190208` = 4 MiB minus one 4 KiB page). UUID and label are how `/etc/fstab` and `swapon` identify the area; `blkid` reads them back (verified): `TYPE="swap"`, `VERSION="1"`, `LABEL=`, `UUID=`.

### Partition vs file

The workflow is identical except for preparation: partitions come from fdisk with type `82` (cosmetic, but conventional); swap files need a filesystem that can give the kernel stable block mapping — ext4/xfs are fine, btrfs requires NOCOW handling (and kernel support for btrfs swapfiles), and the file must be created so its blocks are actually allocated (`dd` or `fallocate` on supporting filesystems):

```
# classic swap-file recipe (ext4)
fallocate -l 4G /swapfile
chmod 0600 /swapfile
mkswap /swapfile
swapon /swapfile
```

### Identity and reproducibility

Each plain run generates a fresh random UUID; re-running mkswap on the same area *changes* its identity, silently breaking fstab-by-UUID entries. `-U` pins a specific UUID (the argument can also be the keywords `clear`, `random` or `time`) and `-L` sets the label. `-p` sets the page size — it must match the running kernel's page size, which is why it is almost always left alone.

### Priority is not mkswap's job

A recurring mix-up: `swapon -p 10` sets priority; `mkswap -p` sets page size. Nothing mkswap does influences scheduling between multiple swap areas — that lives entirely in swapon/fstab.

### The header, byte for byte (verified on a 4 MiB image)

```
offset 0    : 1024 bytes reserved (boot sector / disk-label territory)
offset 1024 : __u32 version      = 1
offset 1028 : __u32 last_page    = highest usable page index
offset 1032 : __u32 nr_badpages  = 0
offset 1036 : __u8  uuid[16]
offset 1052 : char  volume_name[16]
offset 4086 : "SWAPSPACE2" — 10 bytes, ending exactly at 4096
```

`last_page` is why the printed size is 4190208 on a 4 MiB file: 1024 pages total minus the header page, 1023 × 4096. The magic's *position* is the compatibility contract — `swapon(2)` reads the first page and checks bytes 4086-4095, rejecting anything else (v0 swap, stray filesystem signatures) with EINVAL. The reserved first 1024 bytes are also why a swap area can coexist with a boot sector or GPT protective area at the start of a disk.

### What swapon builds from it

`swapon(2)` validates the header, then constructs the kernel's in-memory bookkeeping: per-page usage counters for the area, the extents/cluster allocator state, and the area's priority (from `swapon -p` or fstab `pri=`). Nothing further is written to the device at activation — all runtime swap structures live in RAM and are rebuilt from the header at every swapon. That is why mkswap is a one-time step: the header is identity + size + bad-page list, and nothing else.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-L, --label <label>` | Store a label in the header (visible to blkid/lsblk) |
| `-U, --uuid <uuid>` | Set a specific UUID (or `clear`, `random`, `time`) |
| `-p, --pagesize <size>` | Page size in bytes; must match the kernel (default: detected) |
| `-c, --check` | Read the whole area first, checking for bad blocks (floppy-era practice) |
| `-f, --force` | Proceed even when the requested area is larger than the device |
| `-q, --quiet` | Suppress the informational output and warnings |
| `-v, --swapversion <num>` | Swap format version — only 1 is supported; option kept for compatibility |

Recent upstream releases add swap-file creation conveniences (direct file mode, offset/size overrides); Debian bookworm's mkswap predates them, so the chmod+mkswap+swapon recipe above remains the portable path.

## Usage Patterns

```bash
# Initialize a freshly created swap partition
mkswap /dev/sdb2
```

```bash
# Standard swap-file recipe on ext4
fallocate -l 4G /swapfile && chmod 0600 /swapfile && mkswap /swapfile
```

```bash
# Activate it (and check)
swapon /swapfile && swapon --show
```

```bash
# Persistent across reboots, by UUID
mkswap /dev/sdb2; blkid /dev/sdb2   # copy UUID into /etc/fstab: 'UUID=... none swap sw 0 0'
```

```bash
# Reproducible identity for automation (idempotent re-runs)
mkswap -U deadbeef-dead-beef-dead-beefdeadbeef -L swap1 /dev/sdb2
```

```bash
# Verify what mkswap wrote, via blkid (real output fields)
blkid -p /tmp/sw.img
```

```bash
# Silence the permission warning after fixing modes
chmod 0600 /swapfile && mkswap -q /swapfile
```

```bash
# Re-initialize an area while keeping its fstab identity
OLD=$(blkid -s UUID -o value /dev/sdb2); mkswap -U "$OLD" /dev/sdb2
```

```bash
# Hibernation-ready swap partition with a stable label
mkswap -L hibernate /dev/sdb3
```

```bash
# Show the page-size/header reality: usable size < device size
mkswap /tmp/sw.img | grep size
```

```bash
# Read the raw header back: version, last_page, and (later) the magic
od -A d -t x1 -j 1024 -N 16 /tmp/sw.img
# 0001024 01 00 00 00 ff 03 00 00 00 00 00 00 b9 8b 4b 03

# Legacy path where fallocate is unwanted (or holes are unsafe)
dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
chmod 0600 /swapfile && mkswap /swapfile && swapon /swapfile

# Relabel a live area: deactivate, re-sign, reactivate
swapoff /dev/sdb2 && mkswap -L swap0 /dev/sdb2 && swapon -a

# The kernel's view after activation: name, type, size, priority
swapon --show=NAME,TYPE,SIZE,PRIO
```

```bash
# Keep the fstab identity across a re-init (the idempotent-automation pattern)
UUID=$(blkid -s UUID -o value /dev/sdb2)
mkswap -U "$UUID" -L swap1 /dev/sdb2 && swapon -a

# Prove the two identities: header UUID vs what blkid reports now
blkid -s UUID -o value /dev/sdb2
```

## Nuances and Gotchas

- **The permissions warning is a secret-leak warning.** Swap pages hold decrypted memory (keys, passwords); a world-readable swapfile is a data leak. mkswap warns at 0664; `chmod 0600` before activation is not optional hygiene.
- **Re-running mkswap changes the UUID.** fstab entries by UUID, systemd units, and hibernation resume configuration all break silently. Pin with `-U` when idempotency matters (the "re-init but keep UUID" pattern above).
- **Signature sits at the end of the first page — writes to the file can destroy it.** Anything that later rewrites or relocates the file's blocks (filesystem defrag, btrfs CoW, snapshot restore) invalidates the area; `swapon` then fails with EINVAL or, worse, the kernel scrambles. On btrfs, swapfiles need NOCOW, no compression, no snapshots.
- **`mkswap -p` vs `swapon -p`.** Page size versus priority — same letter, unrelated meanings, guaranteed interview question. The page size must match the kernel's PAGE_SIZE; the priority only orders multiple swap areas.
- **mkswap wipes prior signatures.** Formatting over an ext4 partition prints a "wiping old ... signature" warning and destroys the filesystem. There is no undo; the only protection is the warning itself and backups.
- **Hibernation constraints.** Resume-from-disk needs a swap area holding the suspended image with a *stable identity* (`resume=` kernel parameter or initramfs hook). Re-formatting swap after hibernating destroys the saved image and the resume pointer.
- **Bad-block checking (`-c`) is vestigial.** It reads the whole area once; on SSDs/VMs it proves nothing. Kept for compatibility and period-correct scripts.
- **Size operand is legacy.** The trailing `size` (1 KiB blocks) predates reliable device geometry and is best omitted; mkswap sizes from the device, minus the header page.
- **The label field is 16 bytes — plan for short labels.** `volume_name` is a fixed-width field in the header; long labels do not fit. Keep labels short, DNS-ish, and unique per host.
- **Swap areas are not portable across kernels with different PAGE_SIZE.** A header formatted for a 16 KiB-page ARM64 kernel misreads on a 4 KiB x86_64 host and vice versa — `swapon` rejects it or the geometry is nonsense. Re-run mkswap on the target kernel when reusing media across architectures.
- **The wiping notice is your last forensic hint.** `mkswap: wiping old ext2fs signature ...` lists every stale signature (old filesystems, LUKS, LVM) it clobbered. mkswap itself writes only the first page; it does not scrub the rest of the device — data beyond page 0 survives until the kernel overwrites it with swapped pages.
- **systemd activates swap from fstab or .swap units.** A freshly mkswap'ed area with a new UUID needs the fstab entry updated *before* the next `daemon-reload`/`swapon -a`, or the boot fails that unit. `systemctl daemon-reload && swapon -a` is the completion step of any re-init.
- **Swap identity has a second consumer: suspend image validation.** The resume path matches the hibernated image against the swap header (UUID/label/size); re-formatting while hibernated — or changing size between suspend and resume — is not an error, it is data loss of the suspended state.

## Exit Status

- `0` — area initialized.
- `1` — failure: unreadable device, size smaller than one page, permission problem, or usage error.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`mkfs`](./mkfs.md) — the sibling front end for filesystem builders; same "initialize on-disk structure" pattern.
- [`blkid`](./blkid.md) — reads back the UUID/label/type mkswap wrote.
- [`fdisk`](./fdisk.md) — creates the swap partition (type 82) that mkswap initializes.

## Interview Questions

### Q: What exactly does mkswap write, and what does the kernel check at swapon?

A version-1 swap header in the first page: format version, page count, UUID, label — with the 10-byte magic `SWAPSPACE2` at the end of that page. `swapon` validates the header and magic (refusing with EINVAL when absent), then starts using the area. No data structures beyond the header exist; swap allocation happens at runtime.

### Q: Why does mkswap insist on chmod 0600 for swap files?

Swap contains decrypted process memory — credentials, keys, documents. A swap file with permissive modes exposes all of it to anyone who can read the file. The tool warns when it sees 0664-style permissions; the fix (and the exam answer) is 0600 *before* `swapon`. For partitions the device-node permissions play the same role.

### Q: You re-ran mkswap on an existing swap partition and the machine's fstab mounting "broke". Why?

Each mkswap run without `-U` generates a fresh random UUID. fstab (and hibernation resume configuration) usually reference the old UUID, which no longer exists. Fix by pinning the identity: either restore the old UUID (`mkswap -U <old>`) as a one-time repair, or always re-init with an explicit `-U` in automation.

### Q: Explain the difference between mkswap -p and swapon -p.

Same flag letter, different tools, unrelated meanings: mkswap's `-p` sets the *page size* of the area (must equal the kernel's PAGE_SIZE — effectively never touched), while swapon's `-p` sets the *priority* used to order multiple active swap areas. Confusing them is the classic swap-tooling trap.

### Q: Why is swap on btrfs or on a snapshotted filesystem problematic?

The kernel needs the swapfile's blocks to be stable and directly addressable. Copy-on-write relocation, compression, and snapshots move or alias blocks behind the kernel's mapping table, corrupting the area mid-swap. btrfs swapfile support (modern kernels) requires NOCOW, no compression, no snapshots on the file; ext4/xfs avoid the problem by construction. The lesson: swap needs raw, stable, contiguous block identity — a filesystem guarantee, not a default.

### Q: What does the kernel build in RAM at swapon time, and why does that matter operationally?

Per-page usage counters for the whole area, the extents/cluster allocator state, and the area's priority — all derived from the header at activation, none of it stored on disk. Consequences: swap "geometry" is decided at activation, not formatting; the area carries no runtime structures to fragment; and re-activating rebuilds everything, which is why mkswap being one-time is by design. It also means `swapoff` of a full area forces every swapped page back into RAM — the OOM risk in `swapoff` has nothing to do with mkswap.

### Q: Why is mkswap + swapon on btrfs a minefield while ext4 just works?

ext4/xfs give the file a block map that never moves; the kernel's swap code takes block-level mappings at swapon and assumes they hold forever. btrfs's CoW relocates blocks (compression, snapshots, balance) and can share them — any of which silently invalidates the kernel's view. Hence the kernel's btrfs requirements: NOCOW attribute, no compression, no snapshots covering the file. The generalizable lesson: swap wants raw, stable block identity, and any layer that shuffles blocks must be excluded.

### Q: An alert fires: "swap usage 90%". Where does mkswap fit in triaging it?

Nowhere directly — and that is the point: mkswap wrote identity and size; usage, priority, and behavior live in swapon/kernel state. Triage reads `swapon --show` (how many areas, which priorities), `/proc/swaps`, and `vm.swappiness`. Two areas where the high-priority one is full and the fallback idle tells a different story from a single priority -2 area. Knowing which layer owns which knob — mkswap: header identity; swapon: activation and priority; sysctl: behavior — is the interview-grade answer.

### Q: mkswap ran on a whole-disk device that used to hold a filesystem. What did you actually lose, and what survives?

You lost the filesystem's *signature* (mkswap wiped it and said so) and the kernel will now treat the device as swap once activated — but only the first page was overwritten by mkswap itself. Everything else on the old filesystem (inodes, data blocks) remains on the medium until swap traffic overwrites it, which is why "accidentally mkswap'ed the wrong disk" is a data-recovery scenario, not an instant zeroing. Practical lesson: confirm the target device twice, keep the wiping notice in your logs, and remember page 0 is the only thing mkswap destroys outright.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/mkswap.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
