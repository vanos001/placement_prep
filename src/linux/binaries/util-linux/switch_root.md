# switch_root — switch to a new root filesystem and exec init (initramfs only)

## Overview

`switch_root` performs the final act of an initramfs boot: it deletes
everything on the current root filesystem (which lives in RAM), moves
the prepared new root to `/`, and `exec`s the real init there. It exists
for exactly one scenario — running as PID 1 inside an initramfs whose
job is done — and refuses or misbehaves outside it. It ships with the
`util-linux` package (Debian bookworm) at `/usr/sbin/switch_root`.

`switch_root` is often confused with `pivot_root` (a syscall wrapper
that swaps roots *without deleting* the old one — the live-CD and
container mechanism), with `chroot` (changes the root for a child
process only, moves nothing), and with BusyBox's `switch_root` (the
common initramfs implementation, with an extra `-c` console option).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/switch_root |
| First appeared / lineage | Linux initramfs-era tool (early 2000s); also reimplemented in BusyBox and klibc |
| Standards | None — Linux boot-process specific |

## Synopsis

```
switch_root [options] <newrootdir> <init> [<argument>...]
```

Common one-line forms:

```
switch_root /newroot /sbin/init          # classic invocation
switch_root /newroot /bin/busybox sh     # debug: shell instead of init
```

Note the option surface: only `-h/--help` and `-V/--version`. The
utility's job is fixed; all configuration happens before it is called.

## How It Works

### The boot-time handover, step by step

An initramfs (`rootfs`) is a tmpfs the kernel unpacked into RAM. Every
file in it pins memory, so before handing over, `switch_root` frees it
and moves the new root into place:

1. **Verify the target.** `newroot` must be a mountpoint — the new root
   filesystem has usually been mounted at a directory like `/newroot`
   by the initramfs init script.
2. **Delete the old root's contents.** It recursively unlinks every
   file and directory on the *current* root filesystem, so the tmpfs
   pages can be returned to the kernel. This is the step that makes it
   safe to move mounts and the reason it must never run on a real
   system's root.
3. **Move the new root.** `mount --move`-style: the mount carrying
   `newroot` is relocated onto `/`.
4. **chroot and exec.** It chroots into `/` (now the new root) and
   `exec`s the given `init` — replacing the initramfs PID 1 image with
   the real init, which then owns PID 1 for the rest of the boot.

```
 initramfs (tmpfs, RAM)                prepared newroot (disk)
 ┌──────────────────────┐              ┌──────────────────────┐
 │ /init, busybox, /dev │              │ /sbin/init, /etc ... │
 └──────────────────────┘              └──────────────────────┘
        │ 1. delete all files on rootfs        ▲
        │ 2. mount --move newroot → /          │
        │ 3. chroot . && exec /sbin/init ──────┘
        ▼
 PID 1 = /sbin/init in the real root; initramfs memory freed
```

Because step 3 is an `exec` in the same process, the running
`switch_root` binary — whose own file was just deleted along with the
rootfs — stays alive only until the exec, after which its image is
released. That ordering (delete, move, exec last) is the whole trick.

### Typical initramfs context

Before calling it, a real initramfs script has usually already moved the
virtual filesystems into the new root so they survive the switch:

```bash
mount --move /dev  /newroot/dev
mount --move /proc /newroot/proc
mount --move /sys  /newroot/sys
exec switch_root /newroot /sbin/init
```

Failure at any step aborts with a message and exit status 1 — observed
on a running (non-initramfs) system:

```bash
$ switch_root /tmp /bin/true
switch_root: failed to mount moving /tmp to /: Operation not permitted
switch_root: failed. Sorry.
$ echo $?
1
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `<newrootdir>` | The mountpoint of the new root filesystem. |
| `<init>` | Program to exec as PID 1 in the new root (usually `/sbin/init` or a systemd binary). |
| `<argument>...` | Extra arguments passed to init (e.g. `/bin/sh` for a debug shell). |
| `-h, --help` / `-V, --version` | The only options. |

BusyBox's `switch_root` adds `-c <console>` to reopen a console device
in the new root; util-linux has no equivalent, so scripts must arrange
console/stdio before switching if needed.

## Usage Patterns

```bash
# The canonical end of an initramfs /init script (root, PID 1 context)
exec switch_root /newroot /sbin/init
```

```bash
# Debug a broken boot: land in a shell instead of init
exec switch_root /newroot /bin/sh
```

```bash
# Pass arguments to the new init
exec switch_root /newroot /sbin/init single
```

```bash
# Move virtual filesystems into the new root first (survives the switch)
mount --move /dev  /newroot/dev
mount --move /proc /newroot/proc
mount --move /sys  /newroot/sys
exec switch_root /newroot /sbin/init
```

```bash
# Check the precondition the tool enforces: newroot must be a mountpoint
findmnt /newroot
```

```bash
# A failed run on a live system aborts harmlessly but attempts the move
switch_root /tmp /bin/true   # do NOT do this outside an initramfs
```

## Nuances and Gotchas

- **It deletes the current root's contents.** Not "unmounts" — *deletes*.
  Running it from a normal system against a mounted directory is the
  documented hazard; the delete phase targets rootfs contents and the
  move phase can still wreak havoc. It is designed to be unreachable
  except from PID 1 in an initramfs.
- **newroot must be a mountpoint.** A plain directory (not a mount)
  fails the move step — this is the check that most "why did it refuse"
  questions answer.
- **The exec'd init becomes PID 1.** If you exec something that exits,
  the kernel panics ("Attempted to kill init") — there is no parent to
  return to. Debug invocations (`/bin/sh`) must therefore not exit.
- **Virtual filesystems must be moved or remounted by the caller.**
  switch_root moves only the new root mount itself; `/proc`, `/sys`,
  `/dev` belong to the old root unless relocated first — initramfs
  scripts conventionally move them.
- **util-linux vs BusyBox variants differ.** BusyBox supports
  `switch_root -c /dev/console ...`; util-linux does not. Cross-read
  initramfs scripts before assuming option parity.
- **No return path.** Success means the process image is replaced;
  there is no "come back later" and nothing after the exec line of the
  calling script ever runs.
- **klibc's `run-init`** is the same idea under another name (Debian
  early-userland); do not mix their option vocabularies.
- **Containers do not use it.** Container runtimes use `pivot_root`
  (or MS_MOVE + chroot) because they must keep the old root alive for
  clean teardown — switch_root's delete phase makes it boot-only by
  design.

## Exit Status

| Code | Meaning |
| --- | --- |
| (no return) | On success the process is replaced by init; it never exits. |
| 1 | Any failure: newroot not a mountpoint, move failed (permission), init missing/not executable. |

## Related Commands

- [`pivot_root`](./pivot_root.md) — the non-destructive root swap used by live systems and containers.
- [`mount`](./mount.md) — mounting the new root and `--move`-ing virtual filesystems beforehand.
- [`losetup`](./losetup.md) — how loopback-mounted images become the newroot in test setups.
- [Internals](../../internals.md) — where rootfs, initramfs and PID 1 fit in the boot flow.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: Why does switch_root delete the contents of the old root instead of just unmounting it?

The initramfs rootfs is a tmpfs in RAM — it cannot be unmounted, only
emptied. Every file in it pins memory the real system needs; deleting
the tree lets the kernel reclaim those pages. That is also why it is
initramfs-only: deleting a disk-backed root would be pure destruction.

### Q: What are the hard requirements for a successful switch_root?

Run as root (in practice as PID 1 in an initramfs); the new root must
already be mounted and be a mountpoint; the specified init must exist
and be executable inside the new root. Satisfy all three or the tool
aborts with exit 1 — commonly after "failed to mount moving ... to /".

### Q: switch_root vs pivot_root — when is each correct?

switch_root: boot-time handover where the old root is disposable RAM —
it deletes, moves, and execs init, with no way back. pivot_root: swaps
the root mount while keeping the old one mounted (typically at
/oldroot) — reversible, and therefore what live CDs and container
runtimes use, since they need the old root for teardown or rollback.

### Q: A machine panics with "Attempted to kill init" right after switch_root. What happened?

The exec'd init exited or failed to start: PID 1 has no parent, so the
kernel panics. Common causes: wrong init path, missing dynamic loader
in the new root, or a debug `/bin/sh` invocation that was exited. Boot
the initramfs with `switch_root /newroot /bin/sh` and inspect the new
root before pointing PID 1 at the real init again.

### Q: Why does the initramfs usually move /dev, /proc and /sys into the new root before calling switch_root?

switch_root only relocates the newroot mount onto `/`. The virtual
filesystems mounted in the initramfs would otherwise be torn down with
it — and the new init needs /proc, /sys and a working /dev immediately.
Moving them (`mount --move`) preserves them across the switch; they can
also be remounted afterwards, but moving is the standard, ordering-safe
pattern.

### Q: How does the running switch_root survive deleting the rootfs it lives on?

Deleting unlinks the files; the kernel keeps the in-use program image
mapped until the process replaces it. switch_root carefully execs last,
so the moment the new init's image replaces it, the last reference to
the deleted tmpfs binary is gone and its memory is reclaimed. Any tool
that tried to exec *before* deleting would be destroying its own
footing.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/switch_root.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
