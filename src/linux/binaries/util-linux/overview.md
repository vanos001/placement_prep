# util-linux — Collection Overview

util-linux is the grab-bag kernel-adjacent userland package: everything
that talks to block devices, terminal lines, process attributes, system
clocks, and login sessions but is not part of coreutils or the C library.
`mount`, `fdisk`, `lsblk`, `dmesg`, `cfdisk`, `taskset`, `unshare`,
`hwclock` — the tools you reach for at the storage layer, the scheduler
layer, and the boot layer all come from here. This collection gives each
binary its own page; this overview carries the package-level picture, the
inventory, and the shared concepts.

## Package Shape and Lineage

util-linux grew out of the 1993 merge of assorted Linux utilities that had
no other home, absorbed the 4BSD-derived tools (`col`, `hexdump`, `look`,
`ul`, `write`, `wall` lineage) over the 2010s, and is today maintained
upstream on GitHub. Debian then re-splits it into binary packages by
operational role: `util-linux` (the core), `util-linux-extra` (newer or
niche tools such as `fincore`, `lsirq`, `hwclock` docs), `mount` (the
mount/umount/losetup/swapon/swapoff set), `fdisk` (the three partitioning
tools), `uuid-runtime` (`uuidgen`, `uuidparse`, `uuidd`), `eject`, and
`bsdextrautils` (the absorbed BSD terminal tools). A minimal container can
have one slice without the others — that fact alone answers a family of
interview questions about thin images.

The package is one of the most conservative in Linux: the mount/fdisk
option grammar of 20 years ago still works, and each release adds a
handful of new tools (`setpriv`, `uclampset`, `hardlink`) rather than
changing old ones. Modern releases moved aggressively toward libmount-based
table output (`findmnt`-style JSON), which is why so many pages here show
`--json` options.

Two tools that upstream once shipped are gone: `raw(8)` was removed in
util-linux 2.37 (deprecated block raw devices — bind mounts and O_DIRECT
replaced the use case), and `pg(1)` left Debian packaging years ago. They
appear here only as history notes because interviews occasionally mention
them.

## The Inventory

### Storage: identify, inspect, freeze (10)

| Binary | One-liner | Page |
|---|---|---|
| `blkid` | Locate/print block device attributes | [blkid](./blkid.md) |
| `blkdiscard` | Discard sectors on an SSD | [blkdiscard](./blkdiscard.md) |
| `blkzone` | Report/send zoned-block-device commands | [blkzone](./blkzone.md) |
| `blockdev` | ioctls for block devices | [blockdev](./blockdev.md) |
| `findfs` | Find a filesystem by label/UUID | [findfs](./findfs.md) |
| `findmnt` | Find/list mounted filesystems | [findmnt](./findmnt.md) |
| `lsblk` | List block devices as a tree | [lsblk](./lsblk.md) |
| `fincore` | Which pages are in page cache | [fincore](./fincore.md) |
| `fsfreeze` | Freeze/thaw a filesystem | [fsfreeze](./fsfreeze.md) |
| `wdctl` | Watchdog status | [wdctl](./wdctl.md) |

### Storage: partition and wipe (8)

| Binary | One-liner | Page |
|---|---|---|
| `fdisk` | Interactive MBR/GPT partitioning | [fdisk](./fdisk.md) |
| `sfdisk` | Scriptable partitioning | [sfdisk](./sfdisk.md) |
| `cfdisk` | curses partitioning UI | [cfdisk](./cfdisk.md) |
| `partx` | Tell kernel about partition table | [partx](./partx.md) |
| `resizepart` | Resize a partition in-kernel | [resizepart](./resizepart.md) |
| `addpart` | Register a partition manually | [addpart](./addpart.md) |
| `delpart` | Unregister a partition | [delpart](./delpart.md) |
| `wipefs` | Wipe filesystem/RAID signatures | [wipefs](./wipefs.md) |

### Storage: filesystems, loop, swap (13)

| Binary | One-liner | Page |
|---|---|---|
| `mount` | Attach filesystems | [mount](./mount.md) |
| `umount` | Detach filesystems | [umount](./umount.md) |
| `fsck` | Filesystem check dispatcher | [fsck](./fsck.md) |
| `fsck.cramfs` | Check cramfs images | [fsck.cramfs](./fsck.cramfs.md) |
| `fsck.minix` | Check minix images | [fsck.minix](./fsck.minix.md) |
| `mkfs` | Build filesystems (dispatcher) | [mkfs](./mkfs.md) |
| `mkfs.bfs` | Build BFS images | [mkfs.bfs](./mkfs.bfs.md) |
| `mkfs.cramfs` | Build cramfs images | [mkfs.cramfs](./mkfs.cramfs.md) |
| `mkfs.minix` | Build minix images | [mkfs.minix](./mkfs.minix.md) |
| `mkswap` | Set up swap area | [mkswap](./mkswap.md) |
| `swapon` | Enable swap | [swapon](./swapon.md) |
| `swapoff` | Disable swap | [swapoff](./swapoff.md) |
| `swaplabel` | Change swap label/UUID | [swaplabel](./swaplabel.md) |
| `losetup` | Set up loop devices | [losetup](./losetup.md) |
| `fstrim` | TRIM mounted filesystems | [fstrim](./fstrim.md) |
| `zramctl` | Control zram devices | [zramctl](./zramctl.md) |
| `isosize` | ISO image size | [isosize](./isosize.md) |

### Scheduling, privileges, namespaces (15)

| Binary | One-liner | Page |
|---|---|---|
| `taskset` | Set CPU affinity | [taskset](./taskset.md) |
| `uclampset` | Set utilization clamping | [uclampset](./uclampset.md) |
| `chrt` | Real-time scheduling policy | [chrt](./chrt.md) |
| `choom` | Adjust OOM score | [choom](./choom.md) |
| `ionice` | I/O scheduling class/priority | [ionice](./ionice.md) |
| `nice` (coreutils) | CPU niceness | sibling collection |
| `setpriv` | Run with modified privileges | [setpriv](./setpriv.md) |
| `setsid` | Run in a new session | [setsid](./setsid.md) |
| `setarch` | Personality wrappers (linux32…) | [setarch](./setarch.md) |
| `prlimit` | Get/set resource limits | [prlimit](./prlimit.md) |
| `nsenter` | Enter namespaces of a process | [nsenter](./nsenter.md) |
| `unshare` | Run with new namespaces | [unshare](./unshare.md) |
| `flock` | Advisory file locks | [flock](./flock.md) |
| `kill` | Signal by PID | [kill](./kill.md) |
| `runuser` | Run as another user (no PAM session) | [runuser](./runuser.md) |
| `su` | Switch user | [su](./su.md) |

### Terminals and sessions (17)

| Binary | One-liner | Page |
|---|---|---|
| `agetty` | TTY login prompt (getty) | [agetty](./agetty.md) |
| `mesg` | Control write access to your TTY | [mesg](./mesg.md) |
| `setterm` | Terminal attributes | [setterm](./setterm.md) |
| `more` | Pager | [more](./more.md) |
| `col` | Reverse-line-feed filter | [col](./col.md) |
| `colcrt` | Filter nroff for CRTs | [colcrt](./colcrt.md) |
| `colrm` | Remove columns | [colrm](./colrm.md) |
| `column` | Columnate input | [column](./column.md) |
| `hexdump` | ASCII/decimal/hex dump | [hexdump](./hexdump.md) |
| `look` | Dictionary/lines lookup | [look](./look.md) |
| `ul` | Underline filter for terminals | [ul](./ul.md) |
| `rev` | Reverse characters per line | [rev](./rev.md) |
| `namei` | Follow a pathname element-wise | [namei](./namei.md) |
| `mountpoint` | Is this a mountpoint? | [mountpoint](./mountpoint.md) |
| `whereis` | Locate binary/source/man | [whereis](./whereis.md) |
| `utmpdump` | Dump utmp/wtmp records | [utmpdump](./utmpdump.md) |
| `mcookie` | Generate magic cookies (xauth) | [mcookie](./mcookie.md) |

### System, clock, hardware (18)

| Binary | One-liner | Page |
|---|---|---|
| `dmesg` | Kernel ring buffer | [dmesg](./dmesg.md) |
| `hwclock` | Hardware clock sync | [hwclock](./hwclock.md) |
| `rtcwake` | Suspend until RTC time | [rtcwake](./rtcwake.md) |
| `chcpu` | Enable/disable CPUs | [chcpu](./chcpu.md) |
| `chmem` | Online/offline memory | [chmem](./chmem.md) |
| `lsmem` | List memory blocks | [lsmem](./lsmem.md) |
| `lscpu` | CPU topology display | [lscpu](./lscpu.md) |
| `readprofile` | Read kernel profiling | [readprofile](./readprofile.md) |
| `ctrlaltdel` | Set Ctrl-Alt-Del handling | [ctrlaltdel](./ctrlaltdel.md) |
| `eject` | Eject removable media | [eject](./eject.md) |
| `fallocate` | Preallocate file space | [fallocate](./fallocate.md) |
| `getopt` | Parse options in scripts | [getopt](./getopt.md) |
| `hardlink` | Consolidate duplicate files | [hardlink](./hardlink.md) |
| `rename` | Rename multiple files | [rename](./rename.md) |
| `ldattach` | Line discipline attach | [ldattach](./ldattach.md) |
| `last` | Login history from wtmp (lastb) | [last](./last.md) |
| `pivot_root` | Change root mount | [pivot_root](./pivot_root.md) |
| `switch_root` | Switch to a new rootfs (initramfs) | [switch_root](./switch_root.md) |
| `cal` | Calendar (FreeBSD ncal heritage) | [cal](./cal.md) |
| `uuidgen` | Generate UUIDs (uuidd) | [uuidgen](./uuidgen.md) |
| `uuidparse` | Parse UUIDs | [uuidparse](./uuidparse.md) |

## Shared Concepts

- **libmount table output**: `findmnt`, `lsblk`, `lscpu`, `lsipc`, `lsns`
  share the `--json`/`--list`/export output machinery — scripts should pick
  one stable format and stick to it.
- **Namespace pair**: `unshare` creates new namespaces and runs a command;
  `nsenter` enters another process's namespaces. Container debugging is
  mostly these two plus `setpriv` — see
  [Process Management](../../admin/process-management.md) and
  [Linux Internals](../../internals.md) for kernel context.
- **Partition kernel-vs-disk state**: `partx`/`resizepart`/`addpart`/
  `delpart` manipulate the kernel's view without rewriting the table; the
  fdisk family rewrites it. Knowing which side a tool operates on is the
  classic partitioning interview trap.
- **The su family**: `su` (PAM session), `runuser` (no PAM session), and
  the login-collection's [sulogin](../login/sulogin.md) differ in session
  setup and audit trail — the [su](./su.md) page holds the comparison.
- **Boot path**: initramfs hands off through `switch_root`; chroot-era
  tooling used `pivot_root`; both pages trace the handoff.
- **Debian package splits** listed above — a tool's absence from a minimal
  image is a packaging question, not an upstream one.

## Reading Order For Interview Prep

1. Storage core: [mount](./mount.md), [umount](./umount.md),
   [lsblk](./lsblk.md), [findmnt](./findmnt.md), [fdisk](./fdisk.md),
   [wipefs](./wipefs.md).
2. Process/namespace core: [taskset](./taskset.md), [chrt](./chrt.md),
   [nsenter](./nsenter.md), [unshare](./unshare.md), [setpriv](./setpriv.md),
   [flock](./flock.md).
3. Boot/repair: [dmesg](./dmesg.md), [hwclock](./hwclock.md),
   [switch_root](./switch_root.md), [fsck](./fsck.md),
   [agetty](./agetty.md).
4. Breadth: the tables above; the BSD-terminal tools (`col`, `ul`,
   `colcrt`) are low-yield trivia except at old-school shops.

## Interview Questions

### Q: Why does `lsblk` show a partition the kernel does not actually have?

`lsblk` reads sysfs; after you rewrite a partition table on a disk that is
in use, the kernel's view may be stale until you run `partx -u` (or
`partprobe` from a different package). The fdisk family warns "re-reading
the partition table failed" for exactly this reason. Kernel view vs
on-disk table vs userspace display are three different states — the
partitioning pages cover the reconciliation commands.

### Q: What is the difference between `unshare` and `nsenter`?

`unshare` starts a command in NEW namespaces (creation); `nsenter`
attaches to EXISTING namespaces referenced by `/proc/<pid>/ns/*` (entry).
Debugging inside a container without a shell is the canonical `nsenter`
use; building a test isolation sandbox is the canonical `unshare` use.
Both need matching capabilities, and neither mounts a rootfs by itself —
that is `pivot_root`/`switch_root` territory.

### Q: Which util-linux tools would you use to prove a disk is the bottleneck?

`blkid`/`lsblk` to identify topology, `blockdev --getra` and
`--setra` for readahead, `fsfreeze` to take a consistent snapshot point,
`fstrim` maintenance on SSDs, and `dmesg` to catch device errors. The
expected follow-up is iostat — procps and sysstat territory — so this
page set deliberately hands off to
[procps](../procps/overview.md).

### Q: Why does `flock` exist when `fcntl` locks exist?

`flock(2)` locks are per open-file-description, advisory, and simple to
use from shell pipelines (`flock /tmp/lock cmd`); `fcntl`/`lockf` record
locks are byte-range, survive across fork differently, and are what NFS
historically supported. The [flock](./flock.md) page walks the failure
modes; the one-line cron-mutex idiom is the interview favorite.

## References

- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/)
