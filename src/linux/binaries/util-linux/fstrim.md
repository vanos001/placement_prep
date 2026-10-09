# fstrim — reclaim unused blocks on mounted flash/thin-provisioned filesystems

## Overview

`fstrim` tells a mounted filesystem to report its unused blocks down the stack so the storage below — SSD, NVMe, eMMC, thin LVM, sparse loop file — can retire them. On flash it prevents write-amplification and keeps steady-state performance; on thin-provisioned storage it actually returns space to the pool. The tool wraps one ioctl per filesystem (`FITRIM`) and is normally driven weekly by the distro's `fstrim.timer` rather than typed by hand.

It ships in the `util-linux` package at `/usr/sbin/fstrim`. Reach for it on SSD-class or thin storage that lacks the continuous `discard` mount option, to verify discard support with `-n -v`, or to trim a freshly created filesystem before filling it. It is often confused with the `discard` mount option (continuous trimming at write time — the other of the two strategies), with `blkdiscard` (whole-device discard, destructive), and with `fsfreeze` (quiescing, not reclaiming).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/fstrim |
| First appeared | FITRIM ioctl added to Linux 2.6.37 (2011); fstrim shipped with util-linux in the same era |
| Standards | None (Linux-specific ioctl) |

## Synopsis

```
fstrim [options] <-A|-a|mount point>
```

Common one-line forms:

```
fstrim -av                 # weekly-job style: all mounted, all fstab, verbose
fstrim -v /                # trim one mountpoint, report bytes
fstrim -n -v /             # dry run: what would be trimmed
fstrim -m 512M -v /data    # skip free runs smaller than 512 MiB
```

## How It Works

### The path of a discarded block

`fstrim` performs one `FITRIM` ioctl per filesystem. The kernel walks the filesystem's free-space structures, collects runs of free blocks inside the requested range, filters them by the minimum extent size, and issues discard commands to the block layer, which translates them per transport: ATA `TRIM`/`DATA SET MANAGEMENT`, NVMe `Dataset Management (DSM)`, SCSI `UNMAP`, or device-mapper passthrough.

```
 fstrim -v /data
    │ ioctl FITRIM {start, len, minlen}
    ▼
 filesystem (ext4/xfs/btrfs...): free-extent bitmap walk
    │ ranges of free blocks ≥ minlen
    ▼
 block layer / device-mapper (dm-crypt?, lvm-thin, md, loop)
    │ pass through if discard enabled
    ▼
 device: ATA TRIM | NVMe DSM | SCSI UNMAP
    └── pages marked invalid; GC reclaims later (flash) or pool space freed (thin)
```

### The ioctl call, concretely

`fstrim` opens the mountpoint and issues one ioctl per filesystem:

```c
struct fstrim_range range = {          /* <linux/fs.h>               */
    .start  = 0,                       /* byte offset on the device  */
    .len    = ULLONG_MAX,              /* length from that offset    */
    .minlen = 0,                       /* smallest run worth sending */
};
ioctl(fd, FITRIM, &range);             /* fd open on the mounted fs  */
```

The CLI's `-o/-l/-m` map one-to-one onto these fields — that is why they are byte-granular device concepts, not filesystem concepts. The kernel rounds `minlen` down to the filesystem's allocation unit, walks the free-space structures, and emits discard bios (`REQ_OP_DISCARD`); the block layer translates per transport (ATA DATA SET MANAGEMENT, NVMe DSM, SCSI UNMAP). Why `minlen` exists at all: each discard command has per-command overhead, and a nearly-full fragmented filesystem can present millions of tiny free runs whose discards cost more CPU and device time than they reclaim — the field caps the fan-out.

### Who implements FITRIM

The ioctl is a generic interface; each filesystem implements the free-space walk itself, and support and granularity differ:

```
filesystem    FITRIM          notes
ext4          Linux 2.6.38    walks free-extent structures (buddy/bitmap)
xfs           Linux 2.6.38    per-allocation-group walk; handles -m well
btrfs         Linux 2.6.38    block-group oriented; discard=async (5.14+) is the continuous alternative
f2fs          later           flash-native, segment-based
overlayfs     no              the fs holding the upper dir is what must be trimmed
tmpfs, squashfs, proc, ...    no device below to inform
```

Practical upshot: `fstrim -a` on a typical host trims ext4/xfs/btrfs/f2fs and skips or errors on everything else. The "everything else" bucket is large (squashfs loops, ISOs, tmpfs, pseudo-filesystems), which is exactly why `--quiet-unsupported` exists for cron-style sweeps.

### What `-v` reports

`-v` prints, per filesystem, the sum of the discarded ranges *as requested from the kernel*:

```bash
$ sudo fstrim -v /
/: 12.3 GiB (13208776704 bytes) trimmed on /dev/sda2
```

This number is an accounting of block ranges handed to the device — not a guarantee of how much NAND was erased (devices defer and coalesce) nor, on thin storage, a precise readout of pool delta. Treat it as "upper bound of reclaimable space found this run".

### The two trimming strategies

```
continuous:  mount option "discard"      → every delete issues discards live
periodic:    fstrim.timer → fstrim -A/a  → batch discards weekly
```

Continuous discard spreads latency into every delete/`fsync` path (small, frequent device commands) and was the early-SSD default; periodic trimming keeps the hot path clean and reclaims space within the timer period, which is why modern distros ship `fstrim.timer` (weekly, `fstrim -A -v`) and leave `discard` off for ext4/XFS. Either strategy suffices for SSD health as long as *something* runs; thin-provisioned backends prefer periodic batches for efficiency.

### Scope and selection

- `-a` trims all *mounted* filesystems on devices that support discard.
- `-A` trims only filesystems listed in `/etc/fstab` (the timer's choice; skips chroot/ephemeral mounts).
- `-I <files>` checks membership in an arbitrary fstab-like file list instead of fstab.
- A bare mountpoint operand trims that one filesystem; `-t <types>` filters by fs type.
- `-o <offset>`/`-l <length>` restrict the byte range on the device (rarely used; maps directly onto the `fstrim_range` struct fields).
- `-m <min>` drops free runs smaller than `<min>` from consideration, trading completeness for speed on heavily fragmented free space.

### What the packaged units actually run

The shipped timer and service encode the distro's production answers — worth reading verbatim at `/usr/lib/systemd/system/fstrim.{timer,service}`:

```
fstrim.timer:   OnCalendar=weekly, Persistent=true, AccuracySec=1h,
                RandomizedDelaySec=100min, ConditionVirtualization=!container
fstrim.service: Type=oneshot
  ExecStart=/sbin/fstrim --listed-in /etc/fstab:/proc/self/mountinfo
                         --verbose --quiet-unsupported
  hardening: PrivateNetwork=yes, SystemCallFilter=@file-system ...
```

Three deliberate choices. The service trims with `-I /etc/fstab:/proc/self/mountinfo` — the union of "configured in fstab" and "currently mounted" — rather than `-a`'s blanket sweep or `-A`'s fstab-only restriction. `Persistent=true` catches up a missed weekly run after downtime. And `ConditionVirtualization=!container` disables the timer inside containers entirely: trimming is the host's job there. Copy this shape before inventing your own cron entry.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a, --all` | Trim every mounted filesystem on discard-capable devices |
| `-A, --fstab` | Trim only filesystems listed in `/etc/fstab` |
| `-I, --listed-in <list>` | Restrict to filesystems listed in the given files (like `-A` with custom fstab) |
| `-o, --offset <num>` | Byte offset on the device to start from |
| `-l, --length <num>` | Number of bytes to trim from the offset |
| `-m, --minimum <num>` | Minimum contiguous free extent to discard (default 0 = all) |
| `-t, --types <list>` | Limit to filesystem types |
| `-v, --verbose` | Print the number of bytes discarded per filesystem |
| `-n, --dry-run` | Walk everything and report, issue no discards |
| `--quiet-unsupported` | Silently skip filesystems/devices without discard support |

Size arguments accept `KiB/MiB/GiB/...` suffixes (the `iB` is optional).

## Usage Patterns

```bash
# What your distro's weekly timer effectively does
sudo fstrim -Av

# Trim one filesystem and see the accounting
sudo fstrim -v /data

# Dry run: check discard support and estimate reclaim, change nothing
fstrim -n -v /
# /: 0 B (dry run) trimmed

# Quietly trim everything that supports it (cron-safe)
sudo fstrim -a --quiet-unsupported

# Skip tiny free runs on a fragmented, nearly-full SSD (faster pass)
sudo fstrim -m 512M -v /

# Verify a fresh qcow2/loop-backed rootfs releases space to the host
sudo fstrim -v /

# Confirm whether the device below supports discard at all
cat /sys/block/sda/queue/discard_max_bytes   # nonzero => yes

# Check the weekly unit is actually enabled
systemctl list-timers fstrim.timer

# Trim inside a container's overlay upper dir? Not applicable —
# fstrim acts on mounted filesystems, and overlayfs does not pass FITRIM down;
# trim the host's backing fs instead.
```

```bash
# Override the weekly schedule fleet-wide with a drop-in (Friday nights instead)
systemctl edit fstrim.timer   # [Timer] OnCalendar=Fri 23:00 (then daemon-reload)
```

```bash
# Guest-to-host reclaim in VMs: guest fstrim + virtio-scsi/blk discard=unmap
sudo fstrim -av               # watch the host's qcow2 file shrink with du
```

```bash
# Prove the timer is armed and see the next fire time
systemctl list-timers fstrim.timer --no-pager
```

```bash
# Scope a manual pass to real filesystems, skipping loop/tmpfs noise
sudo fstrim -a -t ext4,xfs,btrfs -v
```

## Nuances and Gotchas

- **dm-crypt eats discards by default.** `luksFormat`-era defaults had `allow-discards` off, so trimmed ranges never reached the SSD: your `fstrim` "succeeded" and reclaimed nothing. Enabling it (`crypttab` `discard` option) trades a privacy leak (observers can infer free-block patterns) for reclaim. Always verify with `fstrim -n -v` plus device counters, not by exit status.
- **Exit status is about the ioctl, not about reclaim.** A filesystem on a non-discard device can still return success from the fs layer while the device ignored everything. `--quiet-unsupported` suppresses *messages*; it does not make trimming work.
- **`-a` vs `-A` differ on purpose.** `-a` hits every mounted fs (including chroots, snap loops, bind targets), `-A` only fstab members. The distro timer uses `-A` to avoid trimming exotic/container mounts — replicate that choice in custom jobs.
- **The `-v` number is a request, not a receipt.** Devices may coalesce, defer, or ignore ranges (especially over RAID or vendor firmware). Don't alert on "bytes trimmed < expected"; alert on the thin-pool's actual usage or `discard_max_bytes == 0` conditions.
- **RAID and layered stacks need end-to-end support.** mdadm arrays pass discards only if all members do; some hardware RAID controllers historically didn't. The block stack (`lsblk -D` shows discard/granularity/maximum) tells you the truth per layer.
- **Read-only mounts.** Trimming requires the fs to be mounted; read-only mounts typically fail the operation — trim rw mounts.
- **Do not confuse with destructive whole-device tools.** `fstrim` never touches allocated data; `blkdiscard /dev/sdX` wipes the *whole device* instantly. Tab-completion accidents here are catastrophic.
- **Btrfs nuance.** Btrfs supports `discard=async` (kernel 5.14+) making the mount-option vs fstrim tradeoff fuzzier; `fstrim` remains the periodic fallback for all filesystems.
- **Zoned devices and some NVMe namespaces** reject or ignore range-restricted trims; keep custom `-o/-l` usage to experiments, let `-a/-A` do production work.
- **TRIM is a hint, not an erasure.** After a successful trim the device only *may* retire the blocks (reads of deallocated NVMe ranges return zeros, but flash can retain old data until garbage collection). For data sanitization use `blkdiscard -s` / ATA SANITIZE — never `fstrim`.
- **Redundant but harmless with `discard` mounts.** A filesystem mounted with the continuous option has little left to reclaim; the weekly pass costs I/O for near-zero benefit. Not an error — just noise in the `-v` numbers.
- **Containers skip the timer by design.** `ConditionVirtualization=!container` in the shipped unit means a container's filesystem is never trimmed by the host's timer; heavy container writes land on the host fs, whose own timer handles them.
- **First-trim surprise on long-lived systems.** A box that never trimmed accumulates years of free-but-unretired blocks; the first `fstrim -av` can run for minutes and move real I/O. Run it in a maintenance window, not at peak.

## Exit Status

- `0` — requested filesystems were processed (trimmed, or skipped-unsupported when suppressed).
- Nonzero — failure: no such mountpoint, filesystem doesn't support FITRIM, insufficient privileges (trimming needs root; the `-n` dry run does not), or a kernel I/O error during the discard pass.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`fsfreeze`](./fsfreeze.md) — the other mountpoint-and-ioctl maintenance tool (quiesce vs reclaim).
- [`mount`](./mount.md) — where the `discard` mount option and per-fs state live.
- [`lsblk`](./lsblk.md) — `lsblk -D` exposes discard support/granularity of the stack.
- [`blkid`](./blkid.md) — fstab identity resolution for `-A`-driven sweeps.
- [`systemd`](../../admin/systemd.md) — `fstrim.timer`/`fstrim.service` scheduling.
- [`internals`](../../internals.md) — block layer discard plumbing and SSD garbage collection.

## Interview Questions

### Q: Why do distros trim weekly via fstrim instead of mounting with the discard option?

Continuous `discard` pushes device commands into every delete and fsync path, adding latency jitter for workloads that delete constantly, and sends many small discards that devices handle inefficiently. A weekly `fstrim -A` batch reclaims the same space with a small number of large, efficient discards off the hot path. Either strategy keeps an SSD healthy; periodic is the low-friction default, and thin-provisioned pools much prefer batched ranges.

### Q: fstrim -v reports 40 GiB trimmed, but the thin pool's usage didn't drop. Debug it.

The report counts ranges the kernel *requested*; the drop happens only if every layer passes them. Check each layer: `lsblk -D` for discard support per device, dm-crypt's `allow-discards` flag (the classic silent blocker), LVM thin pool `issue_discards` setting, RAID member support, and finally the array/controller. `fstrim` succeeding is a statement about the filesystem ioctl, not about end-to-end reclaim.

### Q: What exactly do -a and -A select, and why does the packaged timer use -A?

`-a` trims all mounted filesystems on discard-capable devices; `-A` restricts to filesystems present in `/etc/fstab`. The timer uses `-A` so ephemeral, container, chroot, and loop mounts (which fstab does not list) are skipped — trimming those is at best noise and at worst slow I/O on the wrong layer. `-I` generalizes the membership test to custom fstab-like files.

### Q: What is the -m/--minimum flag's tradeoff?

It excludes free extents smaller than the threshold from the discard pass. On a nearly-full, fragmented filesystem, millions of tiny free runs produce enormous discard traffic and long runtimes; `-m 512M` (a common job-level choice) skips them, finishing quickly at the cost of leaving small holes unreclaimed. Default is 0 — trim every free run regardless of size.

### Q: A security reviewer objects to enabling allow-discards on LUKS. Who is right?

Both have a point: without it, fstrim is a no-op through the crypto layer and SSDs degrade; with it, observers of the ciphertext can correlate freed regions over time (a side channel about deletion patterns). The standard mitigations are accepting it on full-disk layouts where the threat model doesn't include a ciphertext observer, or keeping discards disabled and scheduling re-encryption/migration-style wipes for high-security media. It's a documented, deliberate tradeoff — not a bug.

### Q: Why does FITRIM take a minlen instead of discarding every free block?

Discard commands are not free: each has device-side setup overhead, and a nearly-full fragmented filesystem can present thousands of tiny free runs whose discards cost more than they reclaim. `minlen` (rounded down by the kernel to the allocation unit) lets the caller skip sub-threshold runs so a pass completes in bounded time; `-m 512M`-style job thresholds are the same idea pushed into the admin's hands. The cost is small holes left unretired until the next pass — usually irrelevant, since the filesystem reuses them internally anyway.

### Q: The shipped fstrim.service uses --listed-in /etc/fstab:/proc/self/mountinfo, not -Av. Why does the distinction matter?

`--listed-in` with two files is the union of "configured in fstab" and "currently mounted": fstab members are trimmed even under unexpected paths, and runtime-only mounts are still covered, while exotic targets absent from both stay untouched. Plain `-A` would miss legitimate non-fstab mounts; `-a` sweeps everything including ephemera. The packaged choice is the production calculus — explicit scoping plus `--quiet-unsupported`, sandboxed unit, container skip — and it is a reminder to read the unit before assuming the folk version (`-Av`).

### Q: How would you verify discard works end-to-end in a test you can automate?

Create a thin target (loop-backed dm-thin or qcow2 with a sparse host file), write a known amount, delete it, run `fstrim -v`, and compare the host file's sparseness (`du` vs `ls -ls`) before and after; assert the post-trim allocated size dropped. Scriptable, layer-agnostic, and it fails exactly when some layer eats discards — which is the failure mode that exit codes cannot see.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/fstrim.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
