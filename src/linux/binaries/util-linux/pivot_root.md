# pivot_root — replace the root mount of a mount namespace

## Overview

`pivot_root` moves the root mount of the *current mount namespace* to `put_old` and makes `new_root` the new root — an atomic root swap for the whole namespace, not just for one process. It ships in the `util-linux` package at `/usr/sbin/pivot_root` and is a thin command-line wrapper over the `pivot_root(2)` syscall, which dates to kernel 2.3.41 (2000).

You reach for it in exactly the places where a "first root" must become a "real root": initramfs handing over to the disk root at boot, container runtimes (runc et al.) setting up the image root, and chroot-style sandboxes that must *hide* the old filesystem rather than merely change one process's root. It is often confused with `chroot` (per-process root change; old mounts stay reachable), with `switch_root` (busybox/systemd composite: delete initramfs contents, move mounts or pivot, exec new init), and with `mount --move` (reparents one mount; pivot_root rewrites the namespace's root pointer itself).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/pivot_root |
| First appeared | kernel 2.3.41 (2000); util-linux wrapper of the same era |
| Standards | Linux-specific syscall wrapper; not POSIX |

## Synopsis

```
pivot_root [options] <new_root> <put_old>
```

Main one-line forms:

```
pivot_root /mnt/newroot /mnt/newroot/old      # canonical boot-time form
cd /mnt/newroot && pivot_root . old-root      # initramfs idiom (see below)
pivot_root . old-root && exec chroot . sh -c 'umount /old-root; exec /sbin/init'
```

## How It Works

### What the syscall does

```
before:                             after pivot_root(new_root, put_old):

  /  (old root mount)                 /  (was new_root)
  ├── bin  etc  usr                   ├── old/  (was the old root mount)
  ├── mnt                             │    ├── bin  etc  usr
  │   └── newroot (new root mount)    │    └── mnt
  └── ...                             └── bin  etc  usr  (new root's content)
```

The namespace's root pointer flips to `new_root`; the entire old root mount (with everything hanging under it) reattaches under `put_old`, which itself lives inside `new_root`. Every process in the namespace is affected: their `/` now resolves into the new tree. The old root is *still mounted* — pivot does not unmount anything — so the final step of every handover is unmounting `put_old` (frequently `umount -l` because the old init or shells keep a cwd there).

### The alternatives, and when each applies

```
tool / mechanism      scope            old root                typical use
chroot(2)             one process      untouched, reachable    app sandboxing
mount --move          one mount        stays as root           re-parenting a fs
pivot_root(2)         whole namespace  parked at put_old       initramfs, containers
switch_root(8)        composite        deleted (rm -rf) +      busybox/systemd boot
                                       move or pivot + exec
unshare -m + pivot    new namespace    isolated from host      testing root images
```

The design question each answers is "who must never see the old filesystem again?". Only pivot_root (and its composite wrappers) unmake the old root's visibility for the *entire namespace* while making it unmountable — which is why security-sensitive and memory-reclaiming paths (containers, initramfs) converge on it.

### The kernel's rules

From `pivot_root(2)` — all checked at syscall time:

- `new_root` must be a **mount point** (mount the new root first; a bare directory is not enough) and must not be `/`.
- `put_old` must be **at or underneath** `new_root`.
- The current root must be a mount point.
- The propagation type of `new_root` (and its parent mount) must **not be shared** — shared subtrees would propagate the swap sideways; `mount --make-rprivate` or `make-rslave` first. Violations surface as `EINVAL`, the classic mystery error here.
- When the current root is the initramfs `rootfs` (kernel-built-in tmpfs), `new_root` must be a *different* filesystem — the reason the initramfs idiom below `cd`s into `new_root` and pivots with `.`.

### Why `exec chroot .` — the caller-root caveat

The `pivot_root(8)` man page is explicit that the wrapper "simply calls pivot_root(2)" and that, depending on kernel implementation, the caller's root and working directory **may or may not** change as a side effect of the syscall. Every script therefore ends with `exec chroot .` — a form that behaves identically whether or not the root already flipped (it re-anchors on the cwd), and `exec` (replacing the shell) so no process remains holding the old root as its root or cwd. This is also the moment to detach stdio from the old tree: `sh <dev/console >dev/console 2>&1` — the man page's own example — because file descriptors pointing into the old root keep it busy for the final umount.

### Who keeps the old root busy

After the swap, `put_old` is still a mounted filesystem and `umount /old-root` fails with `EBUSY` for each live reference: a process whose cwd or root is inside the old tree, an open file descriptor, a memory-mapped file, or (subtly) inherited stdio to a device on it. The boot path handles this by design: `exec` replaces initramfs processes rather than forking children, `chroot` re-roots the replacement, stdio is redirected as above, and only then does the new init `umount -l /old-root` release the ramfs memory. In containers the same checklist applies to the runtime's shim processes.

### The initramfs idiom

```
mount /dev/sda2 /mnt/newroot          # new root must be a mount point
cd /mnt/newroot
pivot_root . old-root                 # "." trick: pivot relative to cwd
exec chroot . sh -c 'umount /old-root; exec /sbin/init'
```

Why `.`? The kernel applies the swap to the caller's root; pivoting on the cwd sidesteps the "current root is rootfs" constraint and leaves the initramfs parked at `/old-root`, unmountable once the new init no longer holds references into it. `switch_root` from busybox and systemd's `systemd-switch-root` automate this same sequence (including deleting the initramfs contents to free the ramfs memory).

### Containers

runc-style setups do the equivalent with stronger hygiene: `mount --rprivate /` (propagation off, satisfying the not-shared rule), mount proc/sys/dev into the new root, `pivot_root . old_root` (or `mount --move` + chroot on older paths), then `umount -l /old_root`. The effect an interviewer cares about: after pivot, the old root is *unreachable* — unlike chroot, where a process can still see the host tree below its own root, and escape if it holds an fd outside.

## Options That Matter

`pivot_root` has no behavioral flags — only:

| Option | Effect |
| --- | --- |
| `-h`, `--help` | Usage |
| `-V`, `--version` | Version |

All semantics live in the two positional arguments and the kernel's rule set.

## Usage Patterns

```bash
# Boot handover: initramfs -> disk root (script fragment)
mount -o ro /dev/vda2 /mnt/newroot
mount --make-rprivate /mnt/newroot    # no shared propagation into the swap
cd /mnt/newroot
pivot_root . old-root
exec chroot . sh -c 'umount -l /old-root; exec /sbin/init'
```

```bash
# Test a new root image in a throwaway mount namespace (no risk to the host)
unshare -m sh -c '
  mount --make-rprivate /
  mount -o loop,ro rootfs.img /mnt/newroot
  cd /mnt/newroot && pivot_root . old-root
  exec chroot . /bin/sh -c "umount -l /old-root; exec /bin/sh"
'
```

```bash
# Container-entry skeleton (what runc does, simplified)
mount --rbind /dev  newroot/dev
mount --rbind /proc newroot/proc
mount --rbind /sys  newroot/sys
mount --make-rslave newroot/dev newroot/proc newroot/sys
cd newroot && pivot_root . old-root
umount -l /old-root
```

```bash
# Verify the swap took (old root should be gone or parked)
findmnt -o TARGET,SOURCE
```

```bash
# Diagnose EINVAL: is anything shared? (must be private/slave)
findmnt -o TARGET,PROPAGATION | head
```

```bash
# put_old must exist inside new_root BEFORE pivoting (it is just a mountpoint slot)
mkdir -p /mnt/newroot/old-root
```

```bash
# Full boot-handover with stdio detached (the man page's interactive example)
mount /dev/sda2 /new-root
cd /new-root
pivot_root . old-root
exec chroot . sh <dev/console >dev/console 2>&1
umount /old-root
```

```bash
# Same job, composite tool: switch_root does delete-rf + move/pivot + exec for you
# (busybox switch_root /mnt/newroot /sbin/init) — read its source once; it
# automates exactly the sequence above, including freeing the initramfs memory
```

```bash
# Root-image smoke test, fully disposable: private namespace, loop root,
# pivot, inspect, exit — the host tree never knew
unshare -m sh -c '
  mount --make-rprivate /
  mount -o loop,ro rootfs.img /mnt/newroot
  cd /mnt/newroot && pivot_root . old-root
  exec chroot . /bin/sh -c "umount -l /old-root; ls /"
'
```

## Nuances and Gotchas

- **`EINVAL` almost always means propagation.** A `shared` mount under `new_root` (the default on systemd hosts is `shared` for `/`) makes pivot refuse. `mount --make-rprivate` (or `-rslave` when you still want host events) fixes it — this is the single most common pivot_root failure in scripts.
- **The old root must be unmounted by you.** pivot leaves it at `put_old`; forgetting that means the entire old filesystem stays live (memory pinned, devices held). `umount -l` is the pragmatic tool when something still holds a reference.
- **Processes with cwd/fds in the old tree survive — in a mangled view.** Their cwd now points under `put_old`; paths like `../..` from there behave surprisingly (the kernel forbids escaping the old root downward into the new tree, but the tree shape after the swap is genuinely confusing). This is why init sequences exec the new init with a clean cwd.
- **chroot is not pivot_root.** `chroot` changes the root for the calling process only; other processes, mounts, and even the caller's open fds keep the old view reachable. pivot_root rewrites the whole namespace. Containers that "chroot" without pivoting are trivially inspectable from inside.
- **Not usable across namespaces.** The swap affects the caller's mount namespace only; to pivot inside a container, enter its namespace first (`nsenter -t PID -m`).
- **`new_root` must be a mount point, not a directory on the current root.** Mount the image/disk first; bind-mounting a directory also satisfies the rule (that is how rootfs-overlay setups pivot).
- **Overmounting root (`pivot_root /newroot /old` style with rootfs) is the historical minefield.** The `cd newroot; pivot_root . old` idiom exists precisely because older kernels refused direct pivots off `rootfs`; modern kernels accept more shapes, but the idiom remains the portable one.
- **`put_old` must already exist.** It is an ordinary directory inside `new_root`; forgetting `mkdir old-root` fails with `ENOENT` after all the mount setup has already run — annoying to debug from inside a half-pivoted namespace.
- **`chroot` must be reachable from both sides.** The man page warns that `exec chroot .` needs the `chroot` binary under the old root (to launch it) and under the new root (to run it after the swap). A minimal initramfs that forgets the second copy dies exactly one step before handover.
- **Inherited stdio counts as a reference.** Even with every process re-rooted, a `</dev/console` or log file opened on the old root keeps `umount /old-root` at `EBUSY`; redirect explicitly in the `exec` line.
- **The syscall needs CAP_SYS_ADMIN over the mount namespace's owner.** Root in the container is not enough if the namespace is owned by a parent user namespace — runtimes delegate carefully here, and bare `sudo pivot_root` inside a foreign userns fails with EPERM even though everything else checks out.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Root swapped |
| 1 | Syscall failure: EINVAL (shared propagation, bad locations), EBUSY, ENOENT — the kernel rule list is the error map |

Reading the failure codes against the rule list above:

```
EINVAL   new_root == current root; put_old not under new_root; shared
         propagation on new_root or its parent; rootfs constraint violated
EPERM    missing CAP_SYS_ADMIN in the owning namespace (userns: must own it)
ENOENT   put_old directory does not exist / paths unresolved
EBUSY    (reported later, at umount time) something still references the old root
```

Note that EBUSY is *not* a pivot_root failure — the swap succeeded — it is the next step's failure, which is why scripts that ignore the umount's exit code ship broken root trees that only `findmnt` reveals.

## Related Commands

- [`mount`](./mount.md) — mount points, `--move`, `--make-*` propagation; the vocabulary pivot_root is written in.
- [`umount`](./umount.md) — the mandatory cleanup step for `put_old`.
- [`nsenter`](./nsenter.md) — enter the mount namespace you want to pivot.
- [`findmnt`](./findmnt.md) — verify propagation types and the resulting tree.
- [`internals`](../../internals.md) — mount namespaces and the VFS root pointer.
- [`overview`](./overview.md) — hub page of the util-linux collection.
- [`unshare`](./unshare.md) — create the disposable mount namespace a test pivot needs.

## Interview Questions

### Q: Why do container runtimes and initramfs use pivot_root instead of chroot?

Because pivot_root changes the root of the entire mount namespace: the old filesystem becomes unmountable and invisible, which is both the security boundary (no fd/cwd escape back into the host tree below the new root) and the operational requirement (old root's memory and devices must be releasable). chroot only bends path resolution for one process, leaves the host tree mounted and reachable through pre-existing fds, and does nothing about the initramfs holding RAM.

### Q: What are the kernel's prerequisites for pivot_root, and which one bites most often in practice?

`new_root` must be a mount point not equal to `/`; `put_old` under `new_root`; current root a mount point; propagation of `new_root` and its parent not shared. In practice the shared-propagation check is the usual failure — systemd hosts default to `shared` on `/`, so scripts must `mount --make-rprivate` (or `rslave`) first or they see `EINVAL` with no further explanation.

### Q: Walk through the initramfs handover and explain the `cd /mnt/newroot; pivot_root . old-root` idiom.

Mount the real root at `/mnt/newroot`, drop propagation, `cd` into it, pivot with relative paths so the namespace root becomes the cwd mount and the initramfs lands at `/old-root`, then `exec chroot .` a shell that unmounts `/old-root` and execs `/sbin/init`. The `.`-form is required because when the current root is the kernel's built-in `rootfs`, pivoting must be expressed relative to a directory inside the new filesystem; it also keeps the initramfs mounted (reclaimable via the later `umount -l`) rather than deleted.

### Q: After a successful pivot_root, what state is left that must be cleaned up, and what can go wrong if you skip it?

The old root mount sits at `put_old`, fully mounted. Skipping the `umount` keeps every file of the old tree alive: pages pinned, block devices held open, RAM (for initramfs) never freed, and container image layers unremovable. It also leaves a live second root in the namespace — a shock for anyone auditing the tree with `findmnt`. The standard cleanup is `umount -l /old-root` once no process holds cwd or fds there.

### Q: Why does every pivot_root recipe use `exec chroot .` when pivot_root already changes the root?

Because the syscall's effect on the *caller's* root and cwd has varied across kernel implementations — the man page says plainly it "may or may not" change them. `exec chroot .` is the form that is correct in every case: it re-anchors the root at the cwd (which is inside the new tree by construction, since you `cd`-ed before pivoting) and `exec` replaces the shell so no leftover process keeps the old root alive. The `.`-relative form also works whether or not the root already flipped, which absolute paths would not.

### Q: A container runtime reports EINVAL on pivot_root on one host but not another. Give a complete debugging sequence.

First check propagation: `findmnt -o TARGET,PROPAGATION` — a `shared` entry on `/` or the new root's parent is the usual culprit (systemd default), fixed by `mount --make-rprivate` inside the namespace before pivoting. Then verify the mechanical rules: `new_root` is a mount point (a bind-mount counts), `put_old` exists underneath it, current root is a mount point, and everything happens in the *same* mount namespace (nsenter first). If all that holds, check for a kernel older than the shared-subtree checks — behavior differences across kernel versions are real, which is why runtimes set up their own propagation unconditionally rather than trusting host defaults.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/pivot_root.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
