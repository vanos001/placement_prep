# losetup — set up and control loop devices

## Overview

`losetup` associates a regular file (or, on some setups, another block device) with a **loop device** — a pseudo block device (`/dev/loop0`, `/dev/loop1`, …) whose contents are the file's contents. Once attached, the file behaves exactly like a block device: it can be partitioned, formatted with `mkfs`, mounted, used as swap, or read with `dd`. This is the mechanism underneath `mount -o loop disk.img /mnt`, live ISOs, SquashFS images, encrypted containers, and "disk in a file" lab setups. Ships in the `mount` package (Debian bookworm) at `/usr/sbin/losetup`.

Reach for it when you need explicit control that `mount -o loop` hides: attaching with an offset (a partition inside a whole-disk image), a size limit, read-only mode, or partition scanning. It is often confused with `mount -o loop` (the one-shot convenience that calls losetup internally), with `mknod` folklore (loop devices are created by the kernel/udev, not by hand), and with `losetup -a`'s cousin `mount | grep loop` (which only shows mounted loops, not attached-but-unmounted ones).

| Field | Value |
| --- | --- |
| Package | mount (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/losetup |
| First appeared | Linux mid-1990s; util-linux tooling since then |
| Standards | None (Linux-specific loop device API) |

## Synopsis

```
losetup [options] [<loopdev>]
losetup [options] -f | <loopdev> <file>
```

Common one-line forms:

```
losetup -f --show image.img        # find a free loopdev, attach, print its name
losetup -a                         # list all attached loop devices
losetup -j image.img               # which loopdevs use this file?
losetup -d /dev/loop0              # detach
```

## How It Works

### The loop stack

```
  mount /dev/loop0 /mnt          mkfs/mkswap/dd ... /dev/loop0
        ▲                              ▲
        │                              │
  ┌──────────────────────────────────────────────┐
  │ /dev/loop0  (loop block device, kernel loop.ko) │
  └──────────────────────────────────────────────┘
                        │  maps block I/O onto file ranges
                        ▼
             /srv/images/disk.img  (regular file)
```

Every read/write on the loop device is translated by the kernel's loop driver into file I/O on the backing file at the configured offset/size. The loop device presents standard block semantics (partition table parsing, block caches, filesystem journaling), which a plain file cannot. The attachment pins the backing *inode* — the device follows renames of the backing file, but not replacement of its contents.

### The ioctl API underneath

`losetup` is a thin client over the loop driver's ioctl interface, and knowing the calls explains every option:

```
/dev/loop-control + LOOP_CTL_GET_FREE  → allocate a free loop number (kernel 3.1+)
LOOP_CONFIGURE    one call: attach fd + full config    (kernel 5.8+, race-free)
LOOP_SET_FD / LOOP_CLR_FD              → old two-step attach / detach
LOOP_SET_STATUS64 / LOOP_GET_STATUS64  → struct loop_info64: offset, sizelimit, flags
LOOP_SET_CAPACITY                      → re-read backing file size (losetup -c)
```

`struct loop_info64` carries `lo_offset`, `lo_sizelimit`, `lo_flags` (`LO_FLAGS_READ_ONLY`, `LO_FLAGS_AUTOCLEAR`, `LO_FLAGS_PARTSCAN`, `LO_FLAGS_DIRECT_IO`) and the backing-file identity — the columns `losetup -l` prints map onto these fields directly. Historically attach was `LOOP_SET_FD` followed by a separate `LOOP_SET_STATUS64`; the gap between the two calls was a real race window (another process could observe or use a misconfigured device), which is exactly what `LOOP_CONFIGURE`'s single atomic call closed — and why modern libmount-driven setups prefer it.

### Attach, use, detach

```bash
$ dd if=/dev/zero of=/srv/disk.img bs=1M count=64 status=none
$ losetup -f --show /srv/disk.img
/dev/loop0
$ mkfs.ext4 /dev/loop0 && mount /dev/loop0 /mnt
... use /mnt ...
$ umount /mnt && losetup -d /dev/loop0
```

`-f` asks the kernel for the first unused loop device; `--show` prints the chosen name — always combine them in scripts, because hardcoding `/dev/loop0` races with other users of the machine.

### Listing and association

```bash
$ losetup -a
/dev/loop1: [2049:123456] (/srv/data/container.img)
$ losetup -j /srv/disk.img
/dev/loop0: [2049:123457] (/srv/disk.img)
```

`-a` shows every attachment with its backing file's inode (`major:minor`); `-l` adds the column view (size limit, offset, autoclear, read-only, direct-io); `-j <file>` answers "is this file attached, and where".

### Offsets, partition scanning, autoclear

- **`-o, --offset <bytes>`** — start the device at a byte offset into the file. This is how you expose *one partition* of a whole-disk image: read the partition's start sector from `fdisk -l disk.img` (multiply by sector size) and attach there.
- **`--sizelimit <bytes>`** — cap the device size; combined with `-o` it carves arbitrary sub-ranges.
- **`-P, --partscan`** — ask the kernel to scan the attached device for a partition table and create `/dev/loop0p1`, `p2`, …; otherwise loop devices pretend to be partitionless.
- **Autoclear** — attachments made via `mount -o loop` (and `-L`/autoclear-flagged ones) are detached automatically when the last user (the mount) goes away. `losetup -d` exists for the explicit lifecycle.
- **`-c, --set-capacity`** — after growing the backing file (e.g. `truncate -s +1G disk.img`), make the attached loop device notice the new size without a detach cycle.

### Listing, JSON, and --direct-io

`losetup -l` renders the loop_info64 state as columns (NAME, SIZELIMIT, OFFSET, AUTOCLEAR, RO, BACK-FILE, DIO); `-O`/`--output-all` select columns explicitly and `-J` emits JSON for scripts — prefer those over parsing `-a`'s colon format, which is fine for eyes but brittle for code. One flag worth singling out: `--direct-io=on` opens the backing file with `O_DIRECT`, bypassing its page cache. That stops the same blocks being cached twice (once for the loop device view, once for the file view) and gives steadier benchmark numbers, at the price of per-I/O latency on small reads.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f, --find` | Find the first unused loop device |
| `--show` | With `-f`: print the device name after attaching |
| `-a, --all` | List all used loop devices with backing files |
| `-l, --list` | Column listing (offset, sizelimit, autoclear, RO, back-file, DIO) |
| `-j, --associated <file>` | List loop devices backed by `<file>` |
| `-d, --detach <dev>...` | Detach one or more loop devices |
| `-D, --detach-all` | Detach every loop device |
| `-o, --offset <num>` | Device starts at byte `<num>` into the file |
| `--sizelimit <num>` | Device is limited to `<num>` bytes |
| `-P, --partscan` | Scan the attached image for partitions (`loop0p1`…) |
| `-r, --read-only` | Attach read-only (also auto for read-only backing files) |
| `-c, --set-capacity <dev>` | Re-read the backing file size after it grew |
| `-L, --nooverlap` | Refuse to share the same backing-file range twice |
| `-b, --sector-size <num>` | Set the logical sector size of the loop device |

## Usage Patterns

```bash
# Attach an ISO read-only and mount it (classic)
LOOP=$(losetup -f --show -r debian.iso) && mount -o ro "$LOOP" /mnt/iso

# Expose the first partition of a whole-disk image (offset = start_sector * 512)
fdisk -l disk.img                       # note start sector, e.g. 2048
losetup -f --show -o $((2048*512)) disk.img
mount /dev/loop0 /mnt/root

# Or let the kernel do partition scanning
losetup -f --show -P disk.img
mount /dev/loop0p2 /mnt/root

# Build a filesystem in a file end-to-end
truncate -s 100M fs.img
LOOP=$(losetup -f --show fs.img)
mkfs.ext4 "$LOOP"

# Prepare a swap file via loop (see also mkswap's own workflow)
dd if=/dev/zero of=/swapfile bs=1M count=512 status=none
chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile

# Which loops are attached right now, and to what?
losetup -a
losetup -l

# Find what device is holding a given image
losetup -j /srv/disk.img

# Grew the backing file? Resize the live loop device
truncate -s +1G /srv/disk.img && losetup -c /dev/loop0

# Clean up everything a lab session attached
sudo losetup -D
```

```bash
# Script-safe listing: JSON in, jq out (no fragile colon-format parsing)
losetup -J | jq -r '.loopdevices[] | select(.back-file != null) | .name'
```

```bash
# Explicit column pick for monitoring dashboards
losetup -l -O NAME,BACK-FILE,OFFSET,SIZELIMIT,AUTOCLEAR,RO
```

```bash
# Attach with O_DIRECT for consistent benchmarking (no double page caching)
losetup -f --show --direct-io=on bench.img
```

```bash
# Grow-and-notify cycle: enlarge file, tell the loop device, grow the fs
truncate -s +2G data.img && losetup -c /dev/loop1 && resize2fs /dev/loop1
```

```bash
# Carve a swap-sized sub-range out of a bigger image (offset + sizelimit)
losetup -f --show -o $((64*1024*1024)) --sizelimit $((2*1024*1024*1024)) big.img
```

## Nuances and Gotchas

- **Requires privileges.** Attaching/detaching needs `CAP_SYS_ADMIN`; unprivileged users hit "Permission denied", and many containers/sandboxes lack loop support entirely (`/dev/loop-control` absent → "failed to set up loop device: No such file or directory"). Test loop workflows inside the target environment, not just on your laptop.
- **`-o`/`--sizelimit` are in bytes, not sectors.** The universal bug: `fdisk` shows sector 2048, `losetup` wants `1048576`. Multiply, do not paste.
- **Hardcoded `/dev/loop0` is a race.** Two concurrent scripts can grab the same device; always `losetup -f --show` and capture the output.
- **Autoclear vs explicit detach.** `mount -o loop` attachments vanish with the umount; hand-attached ones persist until `-d`. Leftover attached-but-unmounted loops (check with `losetup -a`) block their backing file from being moved or truncated (EBUSY on the file is not always obvious — the device holds it).
- **Moving/truncating a backing file under a live loop** corrupts the view: the loop device holds the *inode*, so `mv` keeps it working (same inode), but `cp`-over, `truncate`, or editing in place changes data out from under the block device.
- **Backing files on NFS/network storage** are fragile (page-cache/DIO semantics, server reboots); keep loop backends on local filesystems unless you enjoy corruption hunts.
- **Partition scanning needs `-P`** (or `partprobe /dev/loop0`); without it `mount /dev/loop0p1` fails with "no such file" and people blame the image, not the flag.
- **Read-only is inferred, not promised.** A read-only *file* gives a read-only loop device; a writable file lets `mkfs`/writes through even if you "only meant to look" — pass `-r` deliberately.
- **`mount -o loop` is the shortcut** — fine for ISOs; reach for `losetup` when you need offset/size/partscan/sizelimit control or want the device to outlive the mount.
- **Loop devices are allocated dynamically now.** With `/dev/loop-control` (kernel 3.1+) the driver hands out numbers on demand, so scripts should never assume only `loop0..7` exist — always `-f`. Pre-3.1 kernels depend on pre-created nodes and the `max_loop` module parameter; sandboxes that stub `/dev` may have neither.
- **`-D` reports EBUSY on busy attachments.** Detach-all does not force: mounted or otherwise open-backed loops refuse with EBUSY. Clean mounts first, or script a `losetup -a`-driven loop of `-d` calls that reports what refused and why.
- **Partition nodes appear asynchronously after `-P`.** The ioctl returns before udev processes the uevent, so `mkfs /dev/loop0p1` on the very next line can race node creation — `udevadm settle` (or a retry loop) closes the gap.

## Exit Status

- `0` — the operation succeeded (attach, detach, list, capacity update).
- `1` — failure: no free loop device, unreadable backing file, permissions/capability missing, invalid offset/size, or the device was not attached. `losetup -f` with no free devices also fails.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`mount`](./mount.md) — the higher-level consumer; `mount -o loop` drives losetup for you.
- [`mkswap`](./mkswap.md) — formats a file/device as swap; the other common in-file-formatting step.
- [`lsblk`](./lsblk.md) — shows loop devices in the block tree alongside real disks.
- [`blkid`](./blkid.md) — probe the filesystem/UUID that ended up on the loop device.
- [`fdisk`](./fdisk.md) — read partition tables inside whole-disk images to compute `-o` offsets.
- [`internals`](../../internals.md) — the loop driver, block device layer, and page-cache interactions.

## Interview Questions

### Q: What is a loop device and why does mounting an image file need one?

The kernel's filesystem layer speaks the block I/O interface; a regular file does not. A loop device is a pseudo block device whose block reads/writes the loop driver translates into file I/O on the backing file — giving the file standard block semantics (partitions, mkfs, mount, swap). `losetup` performs the file↔device association that `mount -o loop` does implicitly.

### Q: How do you mount the second partition of a raw disk image?

Either read the partition start sector from `fdisk -l disk.img` and attach at the byte offset (`losetup -f --show -o $((start*512)) disk.img`), or attach with `-P` and let the kernel create `loopXp1..N` (`losetup -f --show -P disk.img; mount /dev/loop0p2 /mnt`). The byte-vs-sector multiplication is the classic off-by-512×N bug here.

### Q: A script does `mount -o loop` and later the image cannot be truncated — why, and what do you check?

The mount's loop attachment holds the backing inode open; if umount failed or something else attached the file (check `losetup -a` / `losetup -j <file>` / `fuser -vm`), `truncate`/`rm` get EBUSY or silently diverge. Clean in order: umount filesystems on loopXp*, detach with `losetup -d`, then touch the file. Also confirm no autoclear-less attachment lingers from a crashed run.

### Q: Explain autoclear and when an attachment survives umount.

Attachments carry the LO_FLAGS_AUTOCLEAR flag when created through `mount -o loop`: when the mount goes away, the kernel detaches. Attachments made directly with `losetup` lack the flag and persist until an explicit `losetup -d` (or reboot, or `losetup -D`). This is why "I unmounted it" does not always free the loop device — check with `losetup -l`'s AUTOCLEAR column.

### Q: The image file grew but the loop device still shows the old size. What now?

The loop device caches the backing file size at attach time. Either resize in place with `losetup -c /dev/loop0` (set-capacity re-reads the file size), or detach and re-attach. After the device grows, grow the filesystem itself (`resize2fs` on ext4, for example). Doing it in the other order — resizing the FS first — is the usual mistake.

### Q: Why do loop operations fail inside many containers, and what are the alternatives?

Attaching requires CAP_SYS_ADMIN plus the loop module and `/dev/loop-control`, which container runtimes typically deny or do not expose. Alternatives: run the loop workflow on the host (bind-mount the result in), use a privileged/debug container, or restructure around filesystem-level tools (`e2cp`, `debugfs`, `libguestfs`/`guestfish`, or mounting via `fuse2fs`) that operate on image files without the block layer.

### Q: What problem does LOOP_CONFIGURE solve compared with the old LOOP_SET_FD + LOOP_SET_STATUS64 sequence?

Atomicity under concurrency. The old sequence attached the file first — device live with default configuration — and configured it second, so between the two ioctls other processes (udev, LVM scans, another losetup) could observe or even act on a device with the wrong offset or flags. LOOP_CONFIGURE (kernel 5.8+) takes the fd and the full configuration in one call, so the device appears fully configured or not at all; it also bundles block-size setup, trimming syscalls from hot paths that attach many images (containers, VM orchestration).

### Q: How would you give an unprivileged user loop-based image mounting on a shared host?

You cannot hand out the raw capability safely: attach/detach needs CAP_SYS_ADMIN, and loop devices are host-global kernel state, not per-user resources. The standard answers: FUSE-based filesystem drivers for specific image types (e.g. `fuse2fs` for ext images), a polkit/sudo-whitelisted wrapper that owns the full lifecycle (`losetup -f --show` → mount → umount → detach), or per-user namespaces with unprivileged mounts where the distro enables them. Each trades something — performance (FUSE), audit surface (wrappers), attack surface (userns) — and the interview point is recognizing that global kernel state needs a control process, not permission bits.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/mount/losetup.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
