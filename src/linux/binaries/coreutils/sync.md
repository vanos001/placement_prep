# sync — flush cached writes to persistent storage

## Overview

`sync` forces the kernel to write buffered file data out of RAM and onto the storage device. It is the shell front end to the kernel's synchronization syscalls — `sync(2)`, `fsync(2)`, `fdatasync(2)`, and `syncfs(2)` — and the standard answer to "is my data really on disk?" Modern kernels make `sync` seem redundant: the page cache absorbs writes, and background writeback flushes dirty pages asynchronously seconds later. But the moment durability matters — before unplugging media, before a scripted reboot, after staging a backup — `sync` is the tool. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/sync`.

`sync` is often mistaken for a durability *guarantee*. It is not, by itself. Without operands it synchronizes all mounted filesystems and says nothing about the ordering or completion of any single file's writes. With FILE operands (a GNU extension added in coreutils 8.24, 2015) it calls `fsync(2)` per file, which is the per-file durable pattern applications are supposed to use; `-d` and `-f` switch to the weaker `fdatasync` and the filesystem-wide `syncfs` scopes. Everything else — the caches, the writeback threads, the write barriers — is kernel territory that `sync` merely pokes.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/sync |
| First appeared | Version 3 AT&T UNIX (1973) |
| Standards | POSIX.1-2018 (`sync`); FILE operands and `-d`/`-f` are GNU extensions |

## Synopsis

```
sync [OPTION] [FILE]...
```

One line per mode:

```
sync                      # sync(2): flush dirty data on ALL filesystems
sync FILE...              # fsync(2) each FILE (data + metadata)
sync -d FILE...           # fdatasync(2) each FILE (data, minimal metadata)
sync -f FILE...           # syncfs(2) the filesystem containing each FILE
```

## How It Works

### The write path

To understand `sync`, follow a `write()` through the kernel:

```
 application
     │ write(2)
     ▼
┌─────────────────────────────┐
│ page cache (RAM)            │  write() returns HERE — data is "done"
│  dirty pages accumulate     │  but the disk knows nothing yet
└──────────┬──────────────────┘
           │ background writeback              ┌──────────────┐
           │ (kernel flush threads,            │   sync(1)    │
           │  vm.dirty_* tunables)             │  forces this │
           ▼                                   └──────┬───────┘
┌─────────────────────────────┐                       │
│ block layer / disk cache    │ ◄─────────────────────┘
└──────────┬──────────────────┘
           ▼
     platters / flash
```

The kernel defers device writes because RAM is orders of magnitude faster than any medium. The cost is a window in which a crash or power loss loses data that the application believes was written — or worse, on older filesystems, corrupts the filesystem itself. `sync` closes that window on demand.

### Scope selection

With no operands, `sync` issues a single `sync(2)`: flush modified superblocks, modified inodes, and delayed reads and writes across *every* mounted filesystem. The program itself does nothing clever — as the GNU manual puts it, "the `sync` program does nothing but exercise the `sync`, `syncfs`, `fsync`, and `fdatasync` system calls."

With one or more FILE operands, `sync` opens each file and issues the syscall its options select:

| Invocation | Syscall | Scope | Flushes |
| --- | --- | --- | --- |
| `sync` | `sync(2)` | all filesystems | data + metadata |
| `sync FILE` | `fsync(2)` | that one file | data + metadata |
| `sync -d FILE` | `fdatasync(2)` | that one file | data + metadata needed to retrieve it |
| `sync -f FILE` | `syncfs(2)` | whole filesystem containing FILE | everything on that fs |

Two subtleties from that table are worth internalizing:

- **`fdatasync` is not "no metadata".** It skips metadata that only affects timestamps (atime/mtime), but it *must* flush inode changes that affect data retrieval — notably file size. Extending a file and calling `fdatasync` still writes the inode, because a size entry in RAM with the data on disk would be unrecoverable nonsense after a crash.
- **`-f` with a device node is a trap.** `sync -f /dev/sda` synchronizes the filesystem *containing the device node* (usually the root filesystem) — not the filesystem on `/dev/sda`. The GNU manual calls this out explicitly. If you want the device's filesystem, pass a file or mount point on it: `sync -f /mnt/disk`.

One more scope rule: historically POSIX allowed `sync(2)` to merely *schedule* writeback and return before it completes. Linux has actually waited since kernel 1.3.20 (1996), and GNU `sync` waits — but portable scripts should not assume every Unix does.

### Crash-consistency folklore

The incantation `sync; sync; sync` survives from an era when `sync(2)` genuinely ran writeback in the background and returned immediately. Admins typed it multiple times to give the disk time to catch up — "the third one is for luck", as the joke went. On Linux today, one `sync` waits for the job to finish, and typing it three times is harmless theater.

The folklore matters less on modern filesystems, too. A journaling filesystem (ext4, XFS, btrfs) guarantees *filesystem* consistency across a crash — it will mount cleanly — but it does not guarantee your last writes survived. Crash-consistency of application data still requires the application (or you, from a shell) to force the relevant writes out with `fsync`/`sync`. This is exactly the difference between "the machine rebooted and the filesystem is fine" and "the machine rebooted and half of yesterday's upload is gone."

### The durability ladder

Different calls buy different points on the cost/assurance curve:

```
nothing                write() returned; data lives only in the page cache
   │
   ├── fdatasync(fd)   data + size/indirection metadata of ONE file
   │                   (skips atime/mtime updates)      sync -d FILE
   ├── fsync(fd)       data + all metadata of ONE file   sync FILE
   ├── syncfs(fd)      everything on ONE filesystem      sync -f FILE
   └── sync()          everything on ALL filesystems     sync

cheaper ──────────────────────────────────────────────── more durable scope
```

Applications that implement crash-safe protocols (databases, journals, `apt`) sit at the `fdatasync`/`fsync` rungs and call them constantly. `sync` at the top rung is a blunt administrative instrument: correct, but it stops the world for everyone.

### What sync does not cover

A completed `sync` proves the kernel pushed the data to the device — not that the device committed it. Disks and arrays with volatile write caches can lose recently "completed" writes on power failure; the kernel's answer is write barriers (`blkdev` flush/FUA requests) issued by journaling filesystems during their own commits and by `fsync`. `sync` rides the same machinery, but a broken barrier configuration or a lying USB-bridge chipset silently weakens it. Relatedly, ext4's delayed allocation can reorder block allocation around your writes; `fsync` remains the only contract that closes that window for one file.

## Options That Matter

| Option | Effect |
| --- | --- |
| (none) | `sync(2)` — all filesystems, data and metadata |
| `-d`, `--data` | `fdatasync(2)` each FILE: data only, plus metadata required for retrieval |
| `-f`, `--file-system` | `syncfs(2)` on the filesystem containing each FILE |
| `--help`, `--version` | standard GNU options |

Note that `-d` and `-f` are only meaningful when FILE operands are given; the no-operand POSIX form takes no options at all.

## Usage Patterns

```bash
# Flush everything before a scripted shutdown or poweroff in a rescue shell
sync
```

```bash
# Make one copied file durable before declaring the backup "done"
cp data.tar.gz /mnt/backup/ && sync /mnt/backup/data.tar.gz && echo backup-stable
```

```bash
# Flush all pending I/O on the filesystem holding the mount point (syncfs)
sync -f /mnt/usb
```

```bash
# Sync a large VM image's data without the metadata churn of a full fsync
sync -d /var/lib/vms/disk.raw
```

```bash
# Belt and braces before unplugging: flush, then release the mount
sync -f /mnt/usb && umount /mnt/usb
```

```bash
# The old reboot ritual — still correct in emergency shells
sync; reboot -f
```

```bash
# Verify that a "completed" copy to flash really landed, byte for byte
cp image.bin /media/sd/ && sync -f /media/sd/ && cmp image.bin /media/sd/image.bin
```

```bash
# dd can do its own durability; conv=fsync is preferable to a post hoc sync
dd if=fw.img of=/dev/sdb bs=4M conv=fsync status=progress
```

```bash
# Flush one file tree's data cheaply, file by file (fsync semantics per file)
find /var/lib/app/state -type f -exec sync {} +
```

```bash
# Snapshot-style workflow: quiesce data, then let the snapshot tool proceed
sync -f /srv/db && lvcreate -s -n db-snap /dev/vg0/lv-db
```

```bash
# Embed a flush gate in a provisioning script so failures stop here, not at reboot
sync -f /target || { echo "writeback failed" >&2; exit 1; }
```

```bash
# Age check: force out pending writes, then read the honest free-space number
sync -f /var && df -h /var
```

```bash
# Watch writeback pressure while a job runs (Dirty should drain after sync)
watch -n1 'grep -E "Dirty|Writeback" /proc/meminfo'
```

## Nuances and Gotchas

- **`sync` is not an application durability API.** `sync` with no arguments flushes everything eventually but promises no ordering; only per-file `fsync` (or `sync FILE`) gives the per-file write barriers that crash-consistency reasoning needs. Programs that care issue `fsync(2)` themselves; `dd` exposes it as `conv=fsync`.
- **A no-operand `sync` can take a long time.** It serializes writeback for every filesystem on the machine. On a busy server with terabytes of dirty pages, it simply blocks. There is no way to narrow it except passing files, or `-f` on a specific mount.
- **`sync -f /dev/sdX` syncs the wrong thing.** As above: the filesystem containing the node, not the disk. This is an easy way to *think* you synced a drive while flushing `/` instead.
- **`fdatasync` still writes size-changing metadata.** "Data only" is approximate; inode fields needed to find and size the data are mandatory flush targets. Timestamps are what gets skipped.
- **Exit status only reports the syscall, not the platter.** A zero exit means the kernel accepted the flush; it cannot rule out drive-level write-cache loss. Enterprise arrays and disks with volatile caches are the reason write barriers and `O_FSYNC`-style flags exist.
- **Portability.** POSIX specifies only the no-operand form; `sync FILE`, `-d`, and `-f` are GNU extensions. macOS and the BSDs ship a no-operand `sync`, and BusyBox's option support varies by build — check `busybox sync --help` on embedded targets before scripting flags.
- **Background writeback limits how much you lose, not whether you lose.** Tuneables like `vm.dirty_ratio` and `vm.dirty_expire_centisecs` control how long dirty pages may linger. Long expire times make benchmarks look great and unplugged USB sticks look tragic.
- **`umount` flushes its own filesystem.** After a clean `umount`/`eject`, an extra `sync` is redundant. `sync` before `umount` is habit, not necessity — but harmless, and cheap insurance on filesystems with known quirks.
- **Reading `/proc/meminfo` shows the stakes.** `Dirty` is data waiting to be written, `Writeback` is data being written right now. `sync` drives both to (near) zero.
- **`O_SYNC`/`O_DSYNC` are the open-time equivalents.** A file opened with `O_DSYNC` behaves as if every write were followed by `fdatasync`; `O_SYNC` adds metadata. Those flags cost throughput per write; `sync`/`fsync` cost one syscall when *you* choose. The shell exposure is `dd oflag=dsync`.
- **Error reporting has improved recently.** Older kernels discarded writeback errors after the fact; modern kernels (and correspondingly recent coreutils) surface pending writeback errors to `syncfs`/`fsync` callers, so a failing disk can finally make `sync` exit nonzero instead of failing silently.
- **`sync` on read-only or nearly-idle filesystems is instant.** Cheap does not mean broken: if `Dirty` was already zero, there was simply nothing to do. A suspiciously fast `sync` after a big copy usually means the copy is still buffered in *userspace* (tar, cp with small writes are fine; streaming tools may not be).

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested flushes completed (or nothing needed flushing) |
| nonzero (1) | A syscall failed: missing FILE, permission denied, I/O error on the target |

A nonzero exit from `sync FILE` is genuinely alarming — it usually means the writeout of that file hit a real error, which is exactly what you wanted to know.

## Related Commands

- [`touch`](./touch.md) — writes metadata (timestamps); the other common inode-mutating idiom.
- [`truncate`](./truncate.md) — changes file size in place; pairs with `sync` when shrinking live files.
- [`dd`](./dd.md) — `conv=fsync` / `conv=fdatasync` / `oflag=direct` give durability inside the copy itself.
- [`shred`](./shred.md) — overwrites in place, relying on the same cache-flush machinery to be meaningful.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [Linux internals](../../internals.md) — page cache, dirty page writeback, and journaling behind the scenes.

## Interview Questions

### Q: You must ship logs to a central server, and after a crash some of the day's lines are missing while the filesystem mounts cleanly. Explain the mechanism and two remedies.

The filesystem journal protected metadata, so the fs mounts fine — but the log lines were only in the page cache when the power died; nobody ever issued a flush for them. Remedy one: have the writer `fdatasync` on interval or on importance (syslog implementations and databases do this). Remedy two: reduce the exposure window — smaller `vm.dirty_expire_centisecs`, or ship incrementally (`rsync`/streaming) so the authoritative copy exists elsewhere before the local cache ages out. `sync` from cron narrows the window but is still a polling approach, not a guarantee per line.

### Q: What is the difference between `sync`, `fsync`, `fdatasync`, and `syncfs`?

`sync(2)` flushes dirty data and metadata for all filesystems. `fsync(fd)` flushes one file's data and all its metadata. `fdatasync(fd)` flushes one file's data plus only the metadata needed to retrieve it (e.g., size), skipping pure timestamp updates — so it is usually cheaper. `syncfs(fd)` flushes the entire filesystem containing `fd`. From a shell: `sync` = all filesystems, `sync FILE` = fsync, `sync -d FILE` = fdatasync, `sync -f FILE` = syncfs. Choosing well is a performance question: `fdatasync` on a hot log file avoids needless inode timestamp writes, while `syncfs` is the sledgehammer before detaching a whole device.

### Q: Why did admins traditionally run `sync; sync; sync` before shutting down, and what do we do today?

Early Unix `sync(2)` scheduled writeback and returned before it finished (and some shells ran it in the background), so admins repeated the command to give the disk time — three was ritual. On Linux since 1.3.20, `sync` waits until the flush completes, so one call is enough; the triple-typing is folklore. Today the equivalent rigor is: `sync` in scripts before reboot, `umount`/`eject` for removable media (which flush their own filesystem), and — for data that must survive crashes — per-file `fsync` from the application rather than a global sync.

### Q: A script copies a backup to a USB stick, `cp` exits 0, the stick is unplugged, and the file is short or zero bytes. What happened, and name two fixes.

`cp` returned when its `write()` calls hit the page cache, not the stick; the data was still in RAM when the device vanished. Fix one: flush before release — `sync /mnt/usb/backup.tar` (fsync that file) or `sync -f /mnt/usb` (syncfs the filesystem), then `umount`. Fix two: make the writer durable by construction — `dd ... conv=fsync`, or have the application `fsync` before reporting success. The diagnostic habit: after any flash-medium copy you don't trust, `sync` and then `cmp` source and destination.

### Q: Does `sync` guarantee my file is on disk when it returns?

Mostly yes on Linux, but not by specification. POSIX historically permits `sync(2)` to merely schedule the writeback; Linux has waited since 1.3.20 and GNU `sync` blocks until the kernel reports completion. But even a returned `sync` proves kernel-level writeout, not media-level survival: drive write caches, controller caches, and lossy power can still undo it, which is why filesystems issue cache-flush barriers. And if you need *one file's* ordering guarantees (e.g., database WAL), only `fsync`/`fdatasync` on that file gives the contract you want.

### Q: What does `sync -f /dev/sdb` do, and why is it usually a mistake?

`-f` asks for `syncfs(2)` on the filesystem containing the argument. The device node `/dev/sdb` lives in `/dev`, i.e., on the root (or devtmpfs) filesystem — so the command flushes `/dev`'s filesystem, not whatever is mounted from `/dev/sdb`. To sync the mounted filesystem, pass something inside it: `sync -f /mnt/usb`. The general rule: `-f` takes a path *within* the filesystem of interest, while plain `sync FILE` takes the file itself.

### Q: You see `Dirty: 3.2 GB` in `/proc/meminfo` climbing steadily during a bulk import. What does it mean and when does it matter?

Dirty pages are written-but-not-yet-flushed file data sitting in the page cache; the kernel's writeback threads will push them out based on `vm.dirty_background_ratio`/`vm.dirty_bytes` and age thresholds. It matters when the window becomes a cliff: if writes arrive faster than the device can absorb them, dirty pages hit the hard limit and writers stall while a giant flush happens (the classic "everything freezes for 30 seconds" bulk-load symptom). Periodic `sync` from the importer, smaller `dirty_bytes`, or O_DIRECT/`fdatasync`-per-chunk smooths it out.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sync.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — sync](https://pubs.opengroup.org/onlinepubs/9699919799/)
