# mknod — create special files (device nodes and FIFOs)

## Overview

`mknod` creates *special files*: block device nodes (`b`), character device nodes (`c` or `u`), and FIFOs (`p`). A device node is not a driver or hardware — it is a tiny filesystem entry holding a device **type** plus **major:minor** numbers that the kernel uses to route I/O to the right driver. Creating one is how `/dev/null`, `/dev/sda`, and their kin come into existence in the first place. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/mknod`.

In the devtmpfs/udev era you will almost never type `mknod` interactively: the kernel populates `/dev` automatically (devtmpfs) and udev manages ownership, permissions, and symlinks. The command survives in initramfs and rescue shells, chroot and minimal-container setups, embedded builds without udev, and interviews about the device layer. Creating device nodes requires `CAP_MKNOD`; unprivileged attempts on `b`/`c` fail with `Operation not permitted` (verified on this system), while `p` (FIFO) is allowed for regular users.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/mknod |
| First appeared | Early AT&T UNIX (Version 1 era); Linux `mknod(2)` since the beginning |
| Standards | Not in the POSIX shell-utility set (the `mknod(2)` syscall interface exists separately) |

## Synopsis

```
mknod [OPTION]... NAME TYPE [MAJOR MINOR]
```

Common one-line forms:

```
mknod /dev/null2 c 1 3      # char device: same minor as /dev/null
mknod loop0 b 7 0           # block device: first loop device
mknod /tmp/pipe p           # FIFO — no major/minor; same as mkfifo
mknod -m 666 myfifo p       # explicit mode like chmod
```

## How It Works

### The three types

Per `--help`, verified verbatim:

```
  b      create a block (buffered) special file
  c, u   create a character (unbuffered) special file
  p      create a FIFO
```

`MAJOR MINOR` are required for `b`, `c`, and `u`, and must be omitted for `p` (a FIFO has no driver behind it). The `u` alias for character devices survives from old System V convention ("unbuffered" vs "buffered").

### What major:minor actually does

The kernel keys its device table on `(type, major, minor)`. The major number selects the driver; the minor number is driver-internal (which disk, which partition, which tty). `ls -l` shows both in the size column for special files — verified on this system:

```bash
$ ls -l /dev/null
crw-rw-rw- 1 root root 1, 3 Oct  9 07:51 /dev/null
```

That `1, 3` is the contract: any node you create with `c 1 3` becomes a null-sink, regardless of its name. Number parsing is documented and worth memorizing: `0x`/`0X` prefixes mean hexadecimal, a leading `0` means **octal**, everything else decimal — so `mknod x c 010 0` attaches to major **8**, not 10.

```
              open("/dev/null2")          # a node you made: c 1 3
                      │
                      ▼
        kernel: char device, major 1 ────▶ mem driver
                      │                     (minor 3 = null sink,
                      ▼                      minor 5 = zero, ...)
                 read()/write() routed to the driver — the node's
                 name, permissions, and location are irrelevant
```

Block vs character is a data-path question: block devices go through the page cache and can be seeked (`b`: disks, loop devices); character devices stream bytes straight to/from the driver (`c`: terminals, `/dev/null`, sound devices).

### Permissions and privileges

The node is created with mode `a=rw` masked by the umask (use `-m` for chmod-style exact modes — device nodes conventionally end up `0660` with a `root:`group owner, which is udev's job on a normal system). The privilege boundary is sharp:

```bash
$ mknod hd0 b 8 0
mknod: hd0: Operation not permitted
$ echo $?
1
```

Only `CAP_MKNOD` holders may create `b`/`c` nodes — root on a normal host, but frequently nobody at all in hardened contexts: Docker's default seccomp profile blocks `mknod` outright, and unprivileged user namespaces don't grant device creation (creating a node that maps real hardware from a sandbox would be a security hole). FIFO creation (`p`) needs no privilege, which is why `mkfifo` works for every user.

### Where the nodes come from today

On a modern Debian system, `/dev` is a devtmpfs mount the kernel populates at boot and on device hotplug; udev (systemd-udevd) then applies ownership, permissions, symlinks, and rename rules. Consequences for `mknod` users:

- Nodes you create by hand on a devtmpfs `/dev` vanish at reboot (tmpfs semantics) and may be overwritten or ignored by udev.
- The supported way to add persistent device policy is a udev rule, not a script full of `mknod` calls.
- `mknod` remains essential exactly where that machinery is absent: early userspace before udev starts, rescue chroots with an empty `/dev`, and embedded/static kernels.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m`, `--mode=MODE` | Set permission bits as in `chmod` — exact mode, not umask-masked — instead of the default `a=rw` minus umask |
| `-Z` | Set the SELinux security context to the default type |
| `--context[=CTX]` | Like `-Z`, or set an explicit SELinux/SMACK context |
| `TYPE` operand | `b` block, `c` or `u` character, `p` FIFO (with `p`, no MAJOR/MINOR) |

## Usage Patterns

```bash
# Repair a chroot's /dev from inside a rescue environment (as root)
mknod -m 666 /mnt/rootfs/dev/null c 1 3
mknod -m 666 /mnt/rootfs/dev/zero c 1 5
mknod -m 666 /mnt/rootfs/dev/random c 1 8
```

```bash
# Block device node for a loop/first-disk in an initramfs
mknod -m 660 /dev/sda b 8 0
```

```bash
# FIFO without mkfifo — same syscall, same result
mknod -m 600 /run/myapp-ctl p
```

```bash
# Hex minors, as driver documentation often prints them
mknod mydev c 10 0xa   # minor 10 decimal == 0xa
```

```bash
# Inspect what you created: type, mode, and major:minor in one line
stat -c '%F mode=%a dev=%t:%T name=%n' mydev
```

```bash
# Cross-check with ls -l: the size column holds major, minor
ls -l /dev/null /dev/sda 2>/dev/null | head -2
```

```bash
# Provisional nodes inside a container image build (if the builder allows it)
#   RUN mknod /dev/console c 5 1 && mknod /dev/tty c 5 0
```

```bash
# Remove a node: it is just an inode — rm does not touch the hardware
rm /dev/null2
```

## Nuances and Gotchas

- **Octal by default for major/minor.** A leading `0` switches to octal (`010` = 8). Driver tables are usually printed in decimal or hex; copy-pasted values with stray zeros silently target the wrong device.
- **`u` is `c`.** The `u` type creates a character device, nothing else — a relic of the buffered/unbuffered naming split.
- **`EEXIST` and reuse.** The path must not exist; `mknod` never overwrites. Error messages name the path: `mknod: hd0: Operation not permitted` (verified).
- **FIFO privilege asymmetry.** `p` works for any user (subject to directory permissions); `b`/`c` need `CAP_MKNOD`. Scripts that "worked on my machine" as root fail with exit 1 in containers — check capabilities and seccomp before blaming the command.
- **A node is an inode, not the device.** `rm` removes the name; `ls -l` on a node shows major:minor, not size; `cat /dev/sda` reads hardware if permissions allow. The filesystem layer merely points at the driver.
- **devtmpfs makes manual nodes ephemeral.** Anything you `mknod` into `/dev` on a modern desktop/server lasts until the next boot and can be re-owned by udev. Persistence lives in udev rules, not in the filesystem.
- **Portability.** Not a POSIX utility; BSD/macOS ship their own `mknod` with differing flag sets (and `/dev/MAKEDEV` scripts historically). BusyBox includes a minimal `mknod`. Treat type/flag syntax as per-platform.
- **`--help` even warns about shells.** Some historical shells (ksh family) provided a builtin `mknod`; bash does not, but check `type -a mknod` before debugging flag mismatches in exotic environments.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Every special file created |
| 1 | Any failure: missing privilege (`Operation not permitted`), existing path, invalid type, wrong major/minor arity, unwritable parent |

## Related Commands

- [`mkfifo`](./mkfifo.md) — the friendly, portable way to do `mknod NAME p`.
- [`mkdir`](./mkdir.md) — directories are the other special inode you create by hand.
- [`ls`](./ls.md) — `-l` reveals type and major:minor of every node.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [permissions](../../admin/permissions.md) — the mode bits and umask that shape every created node.
- [systemd](../../admin/systemd.md) — udev's rule engine owns device naming and permissions today.
- [internals](../../internals.md) — where the device layer sits between the VFS and drivers.
- [find](../../shell/find.md) — `-type b` / `-type c` / `-type p` locate special files.

## Interview Questions

### Q: What do the major and minor numbers of a device node mean, and where do you see them?

The pair `(type, major)` selects a kernel driver from the device table; the minor is an instance number inside that driver (which disk, which partition, which tty). `ls -l` displays them in the size column — `/dev/null` is `1, 3` on Linux — and `stat` exposes them via `st_rdev`. The node's name and path are pure convention; only the type and the numbers route I/O, which is why a hand-made `c 1 3` node behaves exactly like `/dev/null`.

### Q: Why does an unprivileged `mknod mydev b 8 0` fail with "Operation not permitted" while `mknod f p` succeeds?

Creating block/character nodes lets you point a filesystem entry at arbitrary kernel drivers — a direct path to hardware access — so the kernel requires `CAP_MKNOD`. FIFOs carry no driver binding (data flows through a kernel buffer), so creating one needs only write permission on the directory. Container runtimes go further: Docker's default seccomp profile denies `mknod` entirely, and user namespaces never grant `CAP_MKNOD` for real devices.

### Q: Block vs character device — what's the operational difference?

Block devices (`b`) are accessed through the page cache in fixed-size blocks and support seeking — disks, partitions, loop devices; tools like `mount` and `dd` work on them at block granularity. Character devices (`c`) are unbuffered byte streams to and from the driver — terminals, `/dev/null`, `/dev/random`; no caching layer, no seeking semantics. The type letter in the node (`b` vs `c`) is what the kernel dispatches on, not the driver behind it.

### Q: In the devtmpfs and udev era, when does anyone still run mknod?

Early userspace (initramfs) before udev starts, rescue chroots with an empty `/dev`, minimal containers and embedded systems without udev, and recovery situations where devtmpfs is not mounted. Everywhere else, the kernel + udev create and manage nodes (and udev rules define persistent ownership/permissions), and hand-created nodes vanish at reboot because `/dev` is tmpfs-backed. Also of note: `mknod`'s FIFO mode survives as the underlying spelling of `mkfifo`.

### Q: `mknod x c 010 0` — which driver does this target, and why is this a gotcha?

Major `010` is octal, i.e. decimal 8 — the `sd` driver's major on Linux, not major 10 (which is `misc`). The documented parsing rule is: `0x`/`0X` hex, leading `0` octal, otherwise decimal. Copying values from tables that print decimal (most do) with an accidental leading zero silently attaches your node to the wrong driver — the node is valid, the behavior is not what you intended.

### Q: How are mknod, mkfifo, and mkdir related at the syscall level?

All three wrap dedicated syscalls that create one inode with a specific type: `mkdir(2)` for directories, `mknod(2)` for `b`/`c`/`p` special files (the coreutils `mkfifo` is a front end for `mknod(2)` with `S_IFIFO`). None can create a directory via `mknod(2)` — Linux deliberately forbids it — and each is atomic with respect to concurrent creators of the same name, with `EEXIST` for the loser.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/mknod.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
