# fsfreeze — suspend and resume write access to a mounted filesystem

## Overview

`fsfreeze` quiesces a mounted filesystem: `--freeze` flushes all dirty data to the device and blocks all further write operations, producing a stable, crash-consistent point on the block device — exactly what you want immediately before taking an LVM snapshot, a storage-array snapshot, or a cloud-disk snapshot. `--unfreeze` releases it. It is a two-flag tool wrapping two kernel ioctls (`FIFREEZE`/`FITHAW`) on the mountpoint.

It ships in the `util-linux` package at `/usr/sbin/fsfreeze` (the functionality descends from XFS's `xfs_freeze`, generalized to any filesystem implementing the freeze operations). Reach for it around snapshot-based backups of active filesystems; do not confuse it with `remount,ro` (which fails when files are open for writing and changes the visible mount), with `sync` (which flushes but does not stop new writes), or with database-level quiescing (which is a different, higher consistency level).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/fsfreeze |
| First appeared | Generic FIFREEZE ioctl added to Linux ~2009 (previously XFS-only via xfs_freeze) |
| Standards | None (Linux-specific ioctls) |

## Synopsis

```
fsfreeze [options] <mountpoint>
```

Common one-line forms:

```
fsfreeze -f /data        # freeze: flush + block all writes
snapshot_the_block_device
fsfreeze -u /data        # unfreeze: writers resume
```

## How It Works

### What freezing actually does

`FIFREEZE` is issued on the mountpoint's filesystem. The kernel: (1) syncs the filesystem — all dirty pages and metadata reach the device; (2) puts the filesystem into a quiesced state where every subsequent write path blocks; (3) reports the device quiescent to userspace. Reads continue to work from the page cache and device; writers (a logging app, an INSERT, a log writer) simply block inside the kernel until thaw. The resulting device state is equivalent to "clean power-off at this instant" — fs-metadata consistent, no torn writes.

```
  time ───────────────────────────────────────────────────────────►
  app writes:  ████████ │││││││││││││││││││ (blocked, D state) ████
  fs state:             ^FIFREEZE                       ^FITHAW
  device:      dirty…   clean, static, snapshot-safe…   resumes
                        └── take LVM/EC2/array snapshot ─┘
```

### The freeze window

Between `--freeze` and `--unfreeze`, the filesystem is frozen, not locked: existing processes continue running (their syscalls on write paths block in uninterruptible sleep, showing state `D` in `ps`), reads succeed, and the block device below is still. That window is where you take the snapshot. The window should be seconds; every second of freeze accumulates blocked writers, database lock queues, and monitoring alarms.

```bash
# Canonical LVM snapshot backup with a minimal freeze window
fsfreeze -f /data
lvcreate --snapshot --size 5G --name data-snap /dev/vg0/data
fsfreeze -u /data
mount /dev/vg0/data-snap /mnt/snap   # mount the snapshot at leisure, back it up
```

### Consistency level: crash-consistent, not application-consistent

Freeze gives filesystem-level consistency — like pulling power at a clean moment. An application with in-memory state (uncommitted transactions still in its buffers, but no data on disk yet) is captured as it would be after a crash: its journal/WAL must recover on next mount. Databases that need tighter guarantees should flush/checkpoint (`CHECKPOINT`, `pg_backup_start`, `FLUSH TABLES WITH READ LOCK`, ...) before the freeze; freeze then guarantees those flushed structures hit the device atomically.

### Requirements and failure modes

- The argument is a **mountpoint**, not a device.
- Requires root (`CAP_SYS_ADMIN`).
- The filesystem must implement freeze/thaw: ext4, XFS, Btrfs, F2FS and most local filesystems do; pseudo-filesystems (proc, sysfs, tmpfs) and network filesystems generally cannot be frozen and fail with `EOPNOTSUPP`/`EINVAL`.
- Freezing an already-frozen filesystem fails with `EBUSY`; unfreezing a non-frozen one likewise errors.
- Files held open for write do *not* prevent freezing (unlike `mount -o remount,ro`, which returns `EBUSY` in that situation) — freeze is the non-disruptive variant.

### The ioctl, precisely

`fsfreeze -f <mnt>` opens the mountpoint directory and issues `ioctl(fd, FIFREEZE)`. Inside the kernel this walks the superblock freeze sequence in stages — each stage blocks one class of writers, waits for stragglers, and syncs:

```
SB_FREEZE_WRITE      block new write(2)/create/unlink;   wait + sync
SB_FREEZE_PAGEFAULT  block writable mmap page faults;    wait + sync
SB_FREEZE_FS         quiesce fs-internal work (journal); final sync
```

Only then does the ioctl return. `FITHAW` unwinds the stages in reverse and releases everyone parked on the barriers. The freeze is refcounted per superblock in the kernel, and the ioctl path rejects a re-freeze with `EBUSY` — which is exactly the command-level behavior you see.

Two scope rules worth burning in: freeze is **per-superblock**, not per-mount — every bind mount of the same filesystem freezes together — and it requires `CAP_SYS_ADMIN` over the mount's owning user namespace.

### Blocked-writer anatomy

A writer that arrives during the window parks inside the kernel write path — visible as uninterruptible `D` state with a recognizable wait channel:

```bash
# During a freeze window, from another terminal:
$ ps axo pid,stat,wchan:24,cmd | awk '$2 ~ /^D/'
  8712 D    submit_bio_wait          dd if=/dev/zero of=/data/big
  8815 D    wait_on_page_bit         python3 loader.py
```

Blocked tasks keep holding their buffers, connection-pool slots, and application locks — which is why the freeze window, not the snapshot itself, is the risk budget of this operation.

### Freeze and the storage stack

`fsfreeze` operates above the block layer: it stops the *filesystem's* write paths but does not quiesce the device — reads and device-level housekeeping continue, and the device content is simply static because nothing writes it. `dmsetup suspend` (what LVM snapshot creation does internally) drains and holds *all* I/O at the device-mapper target; by itself it makes no statement about filesystem consistency. They compose: freeze first (filesystem-consistent), then the device-level operation sees a quiet, consistent device. That layering is why "fsfreeze + lvcreate snapshot" works and why neither half alone is sufficient.

### What the snapshot actually contains

The frozen device holds all synced data and metadata — but it is *not* a "cleanly unmounted" filesystem. The journal can still contain committed-but-not-checkpointed transactions, and the free-block bitmaps may disagree with a naive read of the state at the instant of the last sync. That is by design: mounting the snapshot (or the original after restore) replays the journal and reaches a consistent state — the same path a power-cycle takes. Crash-consistent, not clean; the distinction matters when a backup validator rejects "unclean" images instead of mounting them properly.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f, --freeze` | Flush and suspend all write access to the filesystem |
| `-u, --unfreeze` | Resume write access |
| `-h, --help` | Usage |
| `-V, --version` | Version |

Exactly one of `-f`/`-u` is required; the mountpoint is the sole operand. There is no timeout, no dry-run, and no list mode — orchestration lives in your script.

## Usage Patterns

```bash
# Cloud disk snapshot with consistent state (EC2/Azure/OpenStack volumes)
fsfreeze -f /data
snapshot_tool --volume vol-0123
fsfreeze -u /data

# Snapshot a thin-provisioned LVM pool backing a busy database
fsfreeze -f /var/lib/postgresql
lvcreate -s -L 10G -n pg-snap /dev/vg/pg
fsfreeze -u /var/lib/postgresql

# Freeze both volumes of an application (sequential, per-fs freeze)
fsfreeze -f /data && fsfreeze -f /wal
create_array_snapshot
fsfreeze -u /wal && fsfreeze -u /data

# Verify freeze behavior in a test loop (writers block, then resume)
(while :; do date >> /data/t.log; sleep 0.1; done) &
fsfreeze -f /data; sleep 5; fsfreeze -u /data

# Check whether a filesystem even supports freezing (expect failure on tmpfs)
fsfreeze -f /dev/shm && fsfreeze -u /dev/shm

# Defensive script: always unfreeze on error paths
fsfreeze -f /data && { snapshot_tool || true; fsfreeze -u /data; }

# Consistent raw device image without LVM: freeze, dd the block device, thaw
fsfreeze -f /data
dd if=/dev/vdb1 of=/backup/vdb1.img bs=4M status=progress
fsfreeze -u /data

# Canary: this write must hang while frozen; timeout proves the freeze took
fsfreeze -f /data
timeout 2 sh -c 'echo tick >> /data/canary.log' || echo "write blocked (frozen)"
fsfreeze -u /data

# Pre-flight: does this filesystem implement freeze at all?
fsfreeze -f /var/lib/containers 2>&1   # overlayfs: "Operation not supported"

# Emergency thaw when your own unfreeze step is unavailable (kernel.sysrq enabled)
echo j > /proc/sysrq-trigger           # SysRq "Just thaw it": thaws ALL frozen filesystems

# Time and log the window for SLO reporting
T0=$(date +%s.%N)
fsfreeze -f /data; snapshot_tool --volume vol-0123; fsfreeze -u /data
logger -t snap "freeze window: $(echo "$(date +%s.%N) - $T0" | bc)s"

# Pre-freeze census: who has the filesystem open, and as what?
fuser -vm /data          # access/types column shows F=fifo o=rdonly c=cwd e=exe f=open r=root m=mmap
```

## Nuances and Gotchas

- **Blocked writers are invisible but expensive.** Every writer parks in `D` state; connection pools fill; watchdogs fire. Keep the freeze window minimal and alert on it — a forgotten freeze is an outage discovered by an outage.
- **Never freeze `/` (or the fs containing your recovery tooling).** It works, but if anything needs to exec or write during the window, you can deadlock yourself out of unfreezing. Freeze dedicated data filesystems only.
- **`-f` twice is an error (EBUSY).** Scripts that retry freezes without checking state crash; track frozen state in your orchestration, or probe first (a second freeze attempt returning EBUSY is your probe).
- **It is per-filesystem, not per-volume-set.** Two filesystems on striped volumes cannot be frozen atomically — freeze them back-to-back and accept the tiny skew, or have the storage layer provide a group-consistent snapshot.
- **tmpfs and pseudo-filesystems refuse.** `fsfreeze -f /run` fails with an ioctl error; only filesystems with real backing devices implement freeze/thaw.
- **Freeze ≠ flush-only.** `sync` returns while apps keep writing; `fsfreeze -f` both flushes *and* stops the world. Doing sync → snapshot without freeze gives you a snapshot of a moving target.
- **Databases: pre-quiesce.** For strict application-level consistency, run the engine's own quiesce/checkpoint before freezing; freeze then ensures those quiesced bytes are what the snapshot contains. For most workloads, crash-consistent + WAL replay is perfectly adequate — say which one you have in your runbook.
- **`remount,ro` is the poor cousin.** It also quiesces but fails with EBUSY when files are open for write, and it changes the mount until remounted rw. Freeze fails nothing and leaves the mount untouched — that is its entire reason to exist.
- **Nested/container environments.** Freeze requires the mount to be visible in your namespace and CAP_SYS_ADMIN over it; inside containers without privileges the ioctl fails with EPERM even for a bind-mounted volume.
- **Freeze is per-superblock, not per-mountpoint.** Every bind mount of the same filesystem freezes together, and freezing a second mountpoint of an already-frozen fs fails with EBUSY. "I only froze the mirror path — why is the writer on the primary stuck?" Same superblock.
- **The emergency thaw exists: SysRq-j.** `echo j > /proc/sysrq-trigger` (requires `kernel.sysrq` enabled) thaws every frozen filesystem on the host — the escape hatch when your unfreeze tooling lives on the frozen filesystem itself. Know it before you need it.
- **mmap'ed writers block at fault time, not at freeze time.** A process with a writable mmap keeps running until it touches a page; the fault then blocks. Applications with large mmap'ed stores can amass far more blocked writers than the write(2) path alone shows.
- **Freeze state does not survive reboot.** There is no on-disk frozen marker; a host rebooting mid-window comes back with the filesystem mounted and writable. Orchestrators should treat "rebooted during freeze" as "snapshot invalid, redo it", not "thawed normally".
- **overlayfs and FUSE sit outside the club.** Container overlay filesystems do not implement freeze (`EOPNOTSUPP`); FUSE depends entirely on the userspace daemon honoring the request. Freeze the *backing* filesystem, not the overlay view.

## Exit Status

- `0` — freeze or unfreeze succeeded.
- Nonzero — failure: `EBUSY` (already frozen/not frozen), `EOPNOTSUPP`/`EINVAL` (filesystem cannot be frozen), `EPERM` (not root / lacking capabilities), or a plain I/O error. There are no partial-success codes: the ioctl either quiesced the fs or did not.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`fsck`](./fsck.md) — the other "make filesystem state predictable" tool, for the repair case.
- [`fstrim`](./fstrim.md) — the other mountpoint-oriented maintenance ioctl tool.
- [`mount`](./mount.md) — owns the remount,ro alternative and the mount table you freeze against.
- [`losetup`](./losetup.md) — loop devices over snapshot files use the same quiesce logic.
- [`lsblk`](./lsblk.md) — identify the block device your snapshot tool will target.
- [`systemd`](../../admin/systemd.md) — service stop/snapshot/start orchestration around freeze windows.
- [`internals`](../../internals.md) — page cache flushing and the VFS freeze/thaw barrier.

## Interview Questions

### Q: What problem does fsfreeze solve that `sync` doesn't, and `remount,ro` does clumsily?

`sync` flushes current dirty data but does not stop subsequent writes — a snapshot taken right after captures a moving target. `remount,ro` does quiesce, but fails with EBUSY when files are open for write and visibly changes the mount. `fsfreeze -f` flushes *and* blocks new writes without failing on open files or altering the mount, giving a clean, crash-consistent instant for block-level snapshots.

### Q: You froze /data to snapshot it, but the snapshot tool hung and unfreeze never ran. What do you expect to observe?

All processes writing to /data accumulate in uninterruptible `D` state; anything that needs to allocate journal space or write logs on that fs hangs; monitoring shows rising load with no I/O. Recovery is simply `fsfreeze -u /data` (or reboot) — blocked writers resume where they stopped, and because the fs was frozen after a flush, no corruption results. The operational lesson: freeze windows need watchdogs.

### Q: Is a fsfreeze + LVM snapshot backup "application-consistent"?

It is crash-consistent: the fs on the snapshot is exactly as after a clean power-off — metadata and all *flushed* data coherent. Application state living only in the process (uncommitted transactions, unwritten logs) is absent, and the application must replay its journal on restore. For stricter guarantees, quiesce or checkpoint the application first, then freeze; freeze then guarantees those structures reached the device.

### Q: Which filesystems can't you freeze, and why?

Filesystems without real backing storage or without freeze operations: proc, sysfs, tmpfs, cgroupfs and similar pseudo-filesystems, and (typically) network filesystems, whose client-side freeze cannot make the server-side device quiescent. The ioctl fails with EOPNOTSUPP/EINVAL. Local disk filesystems — ext4, XFS, Btrfs, F2FS — implement FIFREEZE/FITHAW.

### Q: How would you snapshot a two-filesystem application (data + WAL on separate volumes) as consistently as possible?

Freeze both, back to back: `fsfreeze -f /wal; fsfreeze -f /data; snapshot both volumes; fsfreeze -u /data; fsfreeze -u /wal`. Freezing WAL last and thawing it first minimizes the window where the two devices are in different quiesce states. True atomicity across devices requires storage-layer group snapshots (dm/LVM or array support); sequential fsfreeze is the pragmatic approximation and is what most backup tooling does.

### Q: A teammate proposes fsfreeze as a "poor man's database lock". Critique it.

Freeze blocks all write syscalls on the fs — including reads that touch metadata under some paths — for every process, not just the database; it cannot express "readers allowed"; it has no timeout, no queueing, and no per-table granularity; and a bug in the unfreeze path stalls the whole filesystem. It is a snapshot primitive, not a concurrency control. The right tools are the DB's own backup API or MVCC snapshots.

### Q: Walk through what the kernel does between FIFREEZE and FITHAW.

freeze_super() walks staged barriers: first new write syscalls are blocked (SB_FREEZE_WRITE) while in-flight writes drain and a sync runs; then writable mmap faults are blocked (SB_FREEZE_PAGEFAULT) and synced; finally filesystem-internal work such as journal commits is quiesced (SB_FREEZE_FS) with a last sync. The ioctl then returns, leaving writers parked on the barriers; FITHAW unwinds the stages in reverse. The sequence is generic VFS code (fs/super.c) — filesystems only hook the journal quiesce.

### Q: What is the difference between freezing a filesystem and suspending the device (dmsetup suspend)?

Layers. fsfreeze blocks the filesystem's write paths above the block layer and produces filesystem consistency; the device-level queue is untouched. dmsetup suspend drains and holds all I/O at the dm target — a quiet device, but no consistency statement about the filesystem. LVM snapshot creation does both in effect (it suspends the origin briefly), which is why freeze-then-lvcreate gives fs consistency plus a quiet device. For array/cloud snapshots, freeze is your fs-consistency lever and the array handles its own quiesce.

### Q: Why is "freeze, snapshot, thaw" preferred over "stop the service, snapshot, start"?

Stopping the service extends the outage to reads and queries and pays shutdown/startup cost — often minutes for databases. Freeze blocks only write syscalls for the snapshot window, keeps reads working, and yields the same crash-consistent device state; its cost is O(dirty pages), typically sub-second after the first sync. Where the service exposes a real quiesce API (database backup start/stop), layer it under the freeze — freeze then guarantees those quiesced bytes are what the snapshot contains.

### Q: What guardrails do you deploy around freeze windows in production?

A timeout around the whole window with an unconditional `fsfreeze -u` in the error path; an alert on window duration (seconds, not minutes); a documented emergency thaw (SysRq-j); and a pre-flight check that the filesystem supports freeze at all (tmpfs, overlay, FUSE do not). Never freeze `/` from a script that lives on `/`, and never let a hung snapshot tool be the only thing between frozen writers and an outage — monitoring must see the window, not just the snapshot result.

### Q: A restored snapshot mounts with "journal recovery" messages. Is the freeze broken?

No — that is the expected crash-consistent path. At freeze time the journal holds committed transactions that had not yet been checkpointed into their final locations; the snapshot faithfully contains them, and the mount replays them exactly as after a clean power loss. The freeze guarantees the *journal state itself* is consistent and complete, which is what makes replay deterministic. Only an image taken without freeze can replay into corruption.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/fsfreeze.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
