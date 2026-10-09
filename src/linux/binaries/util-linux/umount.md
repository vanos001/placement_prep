# umount — detach filesystems from the directory tree

## Overview

`umount` is the inverse of [`mount`](./mount.md): it detaches a mounted filesystem from the file hierarchy, making its contents unreachable at that path and flushing cached state so the device can be removed or re-mounted elsewhere. It ships in the Debian `mount` package (upstream util-linux) at `/usr/bin/umount`, installed **setuid root** (4755) for the same fstab-delegation reasons as `mount` — the syscall underneath requires `CAP_SYS_ADMIN`.

You reach for `umount` when ejecting media, repartitioning a disk, draining a server, or cleaning up test mounts. The command's real complexity is not the syscall but the **busy problem**: the kernel refuses to detach a filesystem with open files, resident processes, or active submounts — and diagnosing "target is busy" is a daily sysadmin task. This page focuses on detach-side semantics; mount-side details (option grammar, fstab, propagation) live in the [`mount`](./mount.md) page.

| Field | Value |
| --- | --- |
| Package | mount (Debian bookworm) |
| Man section | 8 |
| Path | /usr/bin/umount (setuid root, 4755) |
| First appeared | AT&T UNIX, Version 1 (1971) |
| Standards | Not POSIX; Linux `umount(2)`/`umount2(2)` semantics, LSB historical |

## Synopsis

```
umount [-hV]
umount -a [-dflnrv] [-t fstypes] [-O options]
umount [-dflnrv] <directory> | <device>
```

Main one-line forms:

```
umount /mnt/data              # detach by mountpoint (preferred)
umount /dev/sdb1              # detach by device (obsolete-ish; fails when multi-mounted)
umount -a -t nfs4             # unmount all nfs4 filesystems
umount -l /mnt/hang           # lazy detach when the server is unreachable
umount -R /srv/chroot         # recursively unmount a stack of mounts
```

## How It Works

### One syscall underneath

```
umount(target)              # classic call
umount2(target, flags)      # flags: MNT_FORCE, MNT_DETACH, MNT_EXPIRE, UMOUNT_NOFOLLOW
  MNT_FORCE   -> -f  invalidate in-flight I/O (NFS servers gone)
  MNT_DETACH  -> -l  lazy: detach from tree now, free references later
```

libmount resolves your operand against `/proc/self/mountinfo`, checks permission (setuid + fstab user entries for non-root), optionally calls a `/sbin/umount.<type>` helper (NFS historically), then invokes the syscall and updates `/etc/mtab` bookkeeping (a symlink to `/proc/mounts` on modern systems, so "updating mtab" is mostly vestigial).

### Why "target is busy" happens

The kernel refuses `umount(2)` when the filesystem still has live references. A reference is any of:

```
open file or directory FD          cat /mnt/data/log > /dev/null &
process cwd or root inside         cd /mnt/data (even a shell sitting there)
executable mmapped from it         running binary on the FS
active submount underneath         /mnt/data/docker/overlay2 mounted
swap file or swap device on it     swapon /mnt/data/swapfile
kernel-internal reference          exported NFS root, loop-backed file
```

Diagnosis pattern:

```bash
$ umount /mnt/data
umount: /mnt/data: target is busy.
$ fuser -vm /mnt/data            # which PIDs have files/cwd there
$ lsof +f -- /mnt/data           # per-FD view
$ findmnt -R /mnt/data           # any child mounts stacked below?
```

Note the man page's favorite gotcha: the offending process can be `umount` itself (libc/locale files it opens) or your shell sitting in the directory.

### User mounts: the setuid gate

Like `mount`, `/usr/bin/umount` is setuid root, and libmount inside it grants a non-root user the detach operation **only** for filesystems that an `/etc/fstab` line delegates with `user`, `users`, `owner`, or `group`. Any other attempt fails with *must be superuser*. Remember the pairing: `users` lets any user detach another user's delegated mount; `user` restricts unmounting to the user who mounted. Desktop reality (udisks2, FUSE) routes around this via privileged services instead, which is why removable media unmounts fine without fstab entries on modern desktops.

### Hung servers and the D-state trap

The nastiest busy case is network filesystems: when the server disappears mid-RPC, processes touching the mount sleep in uninterruptible sleep (`D` state), and even `umount` itself can hang in path resolution before reaching the syscall. Mitigations in order:

```bash
umount -f -l /mnt/dead-nfs     # force + lazy: the classic pair
# use absolute paths (no symlink stat) and -c to skip canonicalization
```

The man page's warning deserves quoting in interviews: `-f` does not guarantee `umount` won't hang — it interrupts in-flight I/O but path lookups through dead servers still block. Prevention (hard/soft/intr mount options, shorter timeouts) beats cure.

### Lazy unmount lifecycle

`-l` (`MNT_DETACH`) unlinks the mount from the tree immediately; existing references keep working until they die:

```
before umount -l:        after umount -l:            after last reference dies:
  /mnt  ──> fsA            /mnt ──> (underlying)        fsA fully freed;
  /proc/x/fd: fsA          holder's FDs still see fsA   device deletable
```

The path itself becomes usable again (shows underlying directory content for new lookups), but holders of FDs, mmapped files, or their own root inside the old mount keep a private copy alive. The man page warns: expect a reboot in the near future if you lazy-unmount network or locally-submounted filesystems — the leftovers can be hard to enumerate afterwards.

### Recursive and all-targets unmounting

Stacked mounts (chroots, container roots, nested binds) fail a plain `umount` with EBUSY because of the child mounts. `-R` walks `/proc/self/mountinfo` and unmounts children first (stopping at the first failure); `-A` unmounts *every* mountpoint of the given device in the current namespace; combining them drains a device completely:

```bash
$ umount -RA /dev/nvme1n1p1     # every instance, plus nested mounts, deepest-first
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a` | Unmount everything in `/proc/self/mountinfo` (except pseudo-FS), restricted by `-t`/`-O`. |
| `-A, --all-targets` | Unmount all mountpoints of the named filesystem in this namespace. |
| `-R, --recursive` | Unmount a target plus everything stacked below it. |
| `-l, --lazy` | `MNT_DETACH`: detach now, reap when the last reference dies. |
| `-f, --force` | `MNT_FORCE`: for unreachable NFS; does not guarantee no hang. |
| `-r, --read-only` | On failure, remount read-only (last-ditch data-integrity fallback). |
| `-d, --detach-loop` | Also free the loop device (auto-clear makes this default for `mount -o loop`). |
| `-t` / `-O` | Filter `-a` by filesystem type / by fstab option set. |
| `-N, --namespace` | Perform the umount inside another mount namespace (by PID or nsfd). |
| `-q, --quiet` | Suppress "not mounted" errors (idempotent scripts). |
| `-i` | Skip `/sbin/umount.<type>` helpers. |
| `--fake` | Do everything except the syscall (mtab bookkeeping tests). |

## Usage Patterns

```bash
# Eject a USB disk cleanly
umount /media/user/USBDRIVE
```

```bash
# Unmount everything mounted from one device, including nested binds
umount -RA /dev/sdb1
```

```bash
# Server gone: don't hang the shutdown, detach lazily
umount -l /mnt/nfs-archive
```

```bash
# Idempotent teardown script: quiet when already gone
umount -q /mnt/test || true
```

```bash
# Unmount all filesystems of one type (e.g. before fencing a cluster node)
umount -a -t ocfs2
```

```bash
# Remount read-only instead of failing, if writes must stop now
umount -r /srv/data
```

```bash
# Tear down a chroot: unmount the stack in reverse order
umount -R /srv/chroot
```

```bash
# Perform the umount in a container's mount namespace from the host
umount -N 4217 /mnt/cache
```

```bash
# Find the busy culprits before the real umount
fuser -vm /mnt/data && umount /mnt/data
```

```bash
# Unmount by fstab option set: everything marked _netdev
umount -a -O _netdev
```

```bash
# Loop image cleanup when the loop device wasn't autocleared
umount -d /mnt/iso
```

```bash
# Dry-run the bookkeeping of a scripted unmount
umount --fake /mnt/test
```

```bash
# Unmount everything under a point for another user's session (root)
umount -A /dev/mapper/vg0-home
```

```bash
# Shutdown script: drain network filesystems first, lazily, then local
umount -a -t nfs,cifs -l
umount -a -t ext4,xfs -r
```

```bash
# Verify detachability of a candidate mount in CI before tests run
mountpoint -q /mnt/scratch && umount -q /mnt/scratch
```

## Nuances and Gotchas

- **Order matters.** Unmount deepest-first; a parent FS with an active child mount is always busy. `umount -R` automates the order but stops on the first failure, leaving a partial stack.
- **`-l` hides problems instead of solving them.** Lazy unmount succeeds instantly, so monitoring sees "unmounted" while disk space and references remain held until holders exit. In containers, `umount -l` on a busy root is a common way to *not* actually free anything.
- **By-device unmount is legacy.** `umount /dev/sdb1` fails when the device is mounted at several points (`A, --all-targets` exists for that); scripts should pass mountpoints.
- **NFS `-f` is a band-aid.** Force unmounts interrupt in-flight RPCs but the man page explicitly says the command can still hang; avoid symlinked paths so no `stat`/`readlink` touches the dead server first (`-c` no-canonicalize helps).
- **umount vs systemd.** Under systemd, manually unmounted filesystems may be re-mounted by automount units, and `systemctl stop` of a `.mount` unit is the cleaner interface; also `x-systemd.requires` dependencies can keep a mount "busy" at unit level.
- **Busy can be you.** A shell whose cwd is under the target (or a `less` still holding a file) is enough. `fuser -vm` prints the answer; skipping diagnosis and reaching for `-l` leaves zombies of state behind.
- **`--fake` only fakes the syscall.** It still updates mtab-era bookkeeping — useful to remove stale entries on ancient systems, misleading as a modern dry run.
- **Helpers are legacy but alive.** `/sbin/umount.nfs` still exists in some stacks; `-i` bypasses them, and mismatched helpers are a classic source of "works as root, fails in script" bugs.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success (all requested filesystems unmounted). |
| 1 | Incorrect invocation or permissions; also kernel rejection such as `target is busy` / `not mounted`. |
| 2 | System error (out of memory, cannot fork, no more loop devices). |
| 4 | Internal mount bug or missing support in util-linux. |
| 8 | User interrupt. |
| 16 | Problems writing or locking `/etc/mtab`-bookkeeping. |
| 32 | Unmount failure of some or all targets with `-a`. |
| 64 | Some unmounts succeeded, some failed (`umount -a` aggregate result). |

`umount -a` returns 0 (all succeeded), 32 (all failed) or 64 (partial). Recent util-linux also documents 126 for failure to execute an external helper.

## Related Commands

- [`mount`](./mount.md) — the other half of the pair; option grammar, fstab and propagation live there.
- [`findmnt`](./findmnt.md) — query the mount table; the tool to run before and after `umount -R`.
- [`mountpoint`](./mountpoint.md) — test whether a path is a mountpoint (script-friendly exit codes).
- [`losetup`](./losetup.md) — loop-device plumbing behind `umount -d`.
- [`fsfreeze`](./fsfreeze.md) — quiesce a filesystem before snapshotting; the safe prelude to detaching.
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: A filesystem refuses to unmount with "target is busy". Give a complete triage sequence.

Identify reference holders: `fuser -vm`/`lsof +f -- <dir>` for open FDs and cwds, `findmnt -R` for stacked child mounts, check for swapfiles (`/proc/swaps`), loop backing files, and NFS exports. Unmount children first or use `-R`, kill or `cd` processes out, then retry. If the FS must go now and holders are dying slowly, `umount -l` detaches from the tree while references drain — understanding that it defers rather than fixes is the key point.

### Q: Explain exactly what `umount -l` does and two risks of using it casually.

It performs `umount2(MNT_DETACH)`: the mount is removed from the namespace immediately, but the kernel keeps the superblock alive while any open FD, mmap, or process root references it. Risks: resources (space, device) stay held invisibly after "success", and for network or nested-stack filesystems the man page warns a reboot may be the practical cleanup — remounting over the lazy-detached path and later reaping leftovers gets messy.

### Q: Why is `umount` setuid root in Debian, and what actually protects the system?

`umount(2)` requires `CAP_SYS_ADMIN`, so the setuid bit lets non-root users detach filesystems — but libmount inside the binary only honors that for entries the fstab delegates to users (`user`/`users`/`owner`/`group`). Everything else fails with "must be superuser"; the setuid bit is a gate for fstab-delegated mounts, not a bypass.

### Q: What is the difference between `umount -R`, `umount -A`, and `umount -A -R`?

`-R` recursively unmounts one *mountpoint* and everything stacked beneath it (children first, stop on first failure). `-A` unmounts all mountpoints in the current namespace for a given *filesystem/device* at top level. `-A -R` drains the device everywhere it is mounted, including nested mounts under each instance — the nuclear option before pulling a disk.

### Q: When does `umount -f` help, and why is it not a general "force" button?

Its `MNT_FORCE` flag interrupts in-flight network I/O, which is meaningful for NFS where the server is unreachable — without it the process hangs in D-state on the RPC. For local filesystems the flag does nothing useful: EBUSY from open references is a reference-count problem, not an I/O wait, and no flag can revoke live FDs. The man page even warns `-f` cannot guarantee the command itself won't hang.

### Q: You scripted `umount /mnt/x && rm -rf /mnt/x` and the script erased data underneath a still-mounted FS once. What happened?

A lazy (`-l`) or failed-but-ignored umount left the filesystem mounted; `rm -rf` then wrote through into the mounted FS (or, with a quiet `-q`, "not mounted" was suppressed and `rm` hit real data). The fix: never treat umount as idempotent-by-default — check exit status or `mountpoint -q`, avoid `-q` in teardown scripts, and only clean the *directory* after verifying no mount exists there.

### Q: Why does `umount -a` deliberately skip proc, sysfs, devpts and friends?

Because detaching pseudo-filesystems that the kernel and userspace fundamentally depend on (procfs, sysfs, devtmpfs) would freeze the system mid-command — they are infrastructure, not data mounts. The exclusion list in the man page is a hard-coded safety net; everything else in the mount table is fair game, filtered further by `-t`/`-O`. It is also why `umount -a` is rarely what people want outside shutdown and switch-root contexts, where ordering and lazy flags matter more than breadth.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/mount/umount.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
