# blockdev — call block device ioctls from the command line

## Overview

`blockdev` is a thin, ioctl-per-flag utility: each subcommand maps to one
kernel block-device ioctl, letting scripts query and tweak device-level
properties — size, sector sizes, read-ahead, read-only state, cache
flushing, partition-table rereads — without writing C. It ships in the
`util-linux` package at `/usr/sbin/blockdev`. Almost every
storage-provisioning script you will read uses it somewhere, most often as
`blockdev --getsz` or `--getsize64`.

You reach for it when you need kernel ground truth about a device rather
than a filesystem's opinion: how big is this LV really, is the device in
read-only mode, what is the optimal I/O size, why is `mkfs` complaining
about alignment. It is often confused with `lsblk` (bulk presentation of
the same sysfs data, no setters), with `hdparm` (ATA-specific tuning,
partially overlapping), and with `sysfs` files under
`/sys/block/<dev>/queue/` (many blockdev values are readable there too).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/blockdev |
| First appeared | util-linux lineage (1990s), around the Linux 1.x/2.x ioctl era |
| Standards | Linux block-layer ioctls (BLKGETSIZE64, BLKROSET, ...); not POSIX |

## Synopsis

```
blockdev [-v|-q] commands devices
blockdev --report [devices]
blockdev -h|-V
```

Main one-line forms:

```
blockdev --getsz /dev/sda          # one command, one device
blockdev --getss --getpbsz /dev/nvme0n1   # several queries in one call
blockdev --setra 4096 /dev/sdb     # setter form
blockdev --report                  # table of every disk and partition
```

## How It Works

### One flag, one ioctl

Each `--foo` option is a direct ioctl on the opened device:

```
$ blockdev --getsz /dev/vdb
209715200                       # BLKGETSIZE64 / 512  -> sectors
$ blockdev --getsize64 /dev/vdb
107374182400                    # 100 GiB in bytes
$ blockdev --getss --getpbsz /dev/nvme0n1
512                             # logical  sector size (BLKSSZGET)
512                             # physical sector size (BLKPBSZGET)
```

Multiple commands on one invocation run left to right, one open per
device, one ioctl per command. Setters need `CAP_SYS_ADMIN` (root) and, in
the container-without-devices case, fail with the expected errors:

```
$ blockdev --getsz /dev/vda
blockdev: cannot open /dev/vda: No such file or directory   # exit != 0
```

### The report view

`--report` walks `/proc/partitions`-style devices and prints the numbers
an operator tunes most:

```
$ blockdev --report
RO    RA   SSZ   BSZ        StartSec            Size   Device
rw   256   512  4096           0      107374182400   /dev/vdb
ro   128   512  4096        2048          1048576   /dev/vdb1
#    │    │    │    │              │                │      └─ device name
#    │    │    │    │              │                └─ size in bytes
#    │    │    │    │              └─ partition start sector (0 = whole disk)
#    │    │    │    └─ current blocksize (BLKBSZGET)
#    │    │    └─ logical sector size
#    │    └─ read-ahead in 512-byte units
#    └─ read-only flag as the kernel sees it (BLKROGET)
```

### What the numbers mean

```
SSZ  logical  sector size — the unit the kernel/device addresses in
PBSZ physical sector size — what the media actually handles (4Kn = 4096)
RA   read-ahead, in 512-byte units — prefetched pages on sequential reads
BSZ  blocksize of the open file descriptor (BLKBSZGET/SET), not the FS blocksize
sz   device size; --getsz reports /512, --getsize64 reports bytes
```

`--getsz` is *always* in 512-byte units even on 4Kn devices; converting to
bytes requires `--getsize64` or multiplying by 512, not by SSZ. This
single fact prevents most size-math bugs.

### Cache, readahead, partition reread

```
$ blockdev --flushbufs /dev/sdb       # BLKFLSBUF: drop cached pages of
                                      #   this device, invalidate buffers
$ blockdev --setra 8192 /dev/sdb      # BLKRASET: read-ahead = 8192 sectors
$ blockdev --getra /dev/sdb
8192
$ blockdev --rereadpt /dev/sdb        # BLKRRPART: re-read the partition
                                      #   table; EBUSY if partitions are open
```

`--rereadpt` is the legacy way to make the kernel notice a new partition
table; the modern, partial-failure-tolerant path is `partx -u` (BLKPG
ioctls), which is why the two tools sit in the same package.

## Options That Matter

| Option | Effect |
| --- | --- |
| `--getsz` | Size in 512-byte sectors (the workhorse query) |
| `--getsize64` | Size in bytes (avoids the sector-math trap) |
| `--getss` / `--getpbsz` | Logical / physical sector size |
| `--getiomin` / `--getioopt` | Minimum / optimal I/O size (queue limits) |
| `--getmaxsect` | Maximum sectors per request |
| `--getbsz` / `--setbsz <bytes>` | Blocksize of the open file descriptor |
| `--setro` / `--setrw` / `--getro` | Kernel-level read-only flag (BLKROSET/GET) |
| `--setra` / `--getra` | Read-ahead in 512-byte units (BLKRASET/GET) |
| `--setfra` / `--getfra` | Filesystem read-ahead |
| `--getalignoff` | Alignment offset in bytes |
| `--getdiscardzeroes` | Does discard leave zeros readable? (DA0 capability) |
| `--getzonesz` | Zone size on zoned devices |
| `--getdiskseq` | Disk sequence number (detect live device replacement) |
| `--flushbufs` | Flush and invalidate device buffers/page cache |
| `--rereadpt` | Re-read the partition table (BLKRRPART) |
| `--report` | Tabulate RO/RA/SSZ/BSZ/StartSec/Size for all (or given) devices |
| `-q` / `-v` | Quiet / verbose for setters |

## Usage Patterns

```bash
# Provisioning math: bytes free before carving an LVM volume
size=$(blockdev --getsize64 /dev/vdb)
echo "$((size / 1024 / 1024)) MiB available"
```

```bash
# Which sector sizes does this device expose? (4Kn detection)
blockdev --getss --getpbsz /dev/nvme0n1
```

```bash
# Make a device read-only at the kernel level (fails writes even if FS rw)
blockdev --setro /dev/sdb
blockdev --getro /dev/sdb        # -> 1
```

```bash
# Tune read-ahead for a streaming backup disk
blockdev --setra 16384 /dev/sdb   # 8 MiB read-ahead
```

```bash
# Alignment sanity check before creating a filesystem
blockdev --getiomin --getioopt --getalignoff /dev/vdb
```

```bash
# Drop all cached data of a test device before a benchmark rerun
blockdev --flushbufs /dev/loop0
```

```bash
# After dd-ing a new partition table onto a disk, make the kernel look
blockdev --rereadpt /dev/sdb || partx -u /dev/sdb
```

```bash
# Report of everything, filtered to read-only devices
blockdev --report | awk '$1 == "ro"'
```

```bash
# Verify a discarding device promises zeros-after-discard
blockdev --getdiscardzeroes /dev/sdb     # 1 = DA0 set
```

```bash
# Detect that a hot-swapped disk is not the same device as before
seq1=$(blockdev --getdiskseq /dev/sdb); blockdev --getdiskseq /dev/sdb
```

```bash
# Sector-level size check that matches lsblk output
test "$(blockdev --getsz /dev/vdb)" -eq "$(lsblk -bno SIZE /dev/vdb | head -1 | awk '{print int($1/512)}')"
```

## Nuances and Gotchas

- **--getsz is in 512-byte sectors, always.** On 4Kn devices, size-in-bytes
  = `--getsz * 512`, not `* SSZ`. Scripts that multiply by the logical
  sector size are wrong on every modern NVMe device that reports 512 LBA
  but 4096 physical.
- **--setro is not a write-protect switch.** It sets the kernel's
  BLKROSET flag for the device — new opens are read-only, and the block
  layer rejects writes — but already-open writers keep their descriptor
  behavior, and the flag is lost on reboot. It also has nothing to do with
  the hardware RO jumper or NVMe write-protect namespaces.
- **--flushbufs is destructive.** It invalidates the page cache and
  buffers of the device; on a mounted filesystem this is a data-loss
  recipe (unsynced writes discarded). It is for idle test devices.
- **--rereadpt fails with EBUSY when partitions are in use** (mounted,
  swap, LVM PV). Use `partx -u`/`addpart`-style BLKPG updates instead;
  `--rereadpt` only works cleanly on idle disks.
- **--setbsz affects only that file descriptor.** It does not change the
  device persistently nor any filesystem's block size — a frequent
  misreading of the man page.
- **Container/case trap:** in minimal environments device nodes may be
  absent; blockdev then fails with "cannot open" and exit 1 — distinguish
  that from a real ioctl failure by the error message.
- **--getsize (32-bit) is deprecated** for good reason: it overflows past
  1 TiB; always use `--getsz`/`--getsize64`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested ioctls succeeded |
| 1 | Usage error, device open failed, or an ioctl was rejected (`EBUSY`, `EPERM`, `ENOTTY`) |

## Related Commands

- [`blkid`](./blkid.md) — `blkid -i` reports the same queue-limit family from the probing side
- [`blkdiscard`](./blkdiscard.md) — `--getdiscardzeroes` tells you what a discard will leave behind
- [`blkzone`](./blkzone.md) — `--getzonesz` pairs with blkzone's zone commands
- [`addpart`](./addpart.md) — the BLKPG-based alternative to the blunt `--rereadpt`
- [`cfdisk`](./cfdisk.md) — writes the tables that `--rereadpt`/partx then teach the kernel
- [Linux internals](../../internals.md) — where the page cache and buffer layer this tool flushes live
- [util-linux overview](./overview.md) — the rest of the block-device toolset

## Interview Questions

### Q: What is the difference between --getsz, --getsize, and --getsize64?

`--getsize` is the legacy 32-bit sector count and overflows above 1 TiB,
which is why it is deprecated. `--getsz` is the modern sector count in
fixed 512-byte units. `--getsize64` reports bytes and needs no unit math.
All three are the same kernel values filtered differently; picking the
wrong one is how scripts silently misreport a 2 TiB disk.

### Q: blockdev --setro was run on a disk, but an already-running process still writes to it. Explain.

BLKROSET is enforced per open: existing file descriptors keep their
original mode, and the flag is advisory for new opens. Only unmounting and
reopening (or the filesystem being unable to remount) guarantees behavior
change. Also the flag is not persistent — it disappears at reboot or when
something explicitly `--setrw`s.

### Q: Why would a benchmark script call blockdev --flushbufs between runs?

To remove the page cache as a variable: without it, the second run may be
measuring cache hits rather than the device. It only works on an idle
device, and for mounted filesystems it is dangerous — the benchmark should
target a loop device or an unmounted volume, and ideally drop caches
system-wide too.

### Q: The kernel refuses to re-read a partition table with blockdev --rereadpt: EBUSY. What now?

BLKRRPART is all-or-nothing and fails when any partition is open. The
BLKPG ioctl family (exposed by `partx -u`, `addpart`, `delpart`) adjusts
entries incrementally and tolerates busy disks — add the new partition,
resize one that grew, leave mounted ones untouched. That is precisely why
util-linux ships both interfaces.

### Q: How do you programmatically detect that /dev/sdb was replaced by a different physical disk under the same name?

`blockdev --getdiskseq` returns the disk-sequence number, which the kernel
increments per instantiated gendisk; a changed value between two reads
means the name now refers to another device. Combined with `--getsize64`
and the device's WWN/sysfs identity, it closes the classic hot-swap race
in provisioning scripts.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/blockdev.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
