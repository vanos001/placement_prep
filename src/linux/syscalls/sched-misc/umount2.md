# oldumount(2) (file name: umount2.md)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (per-arch compat tables) |
| Since (kernel) | 2.4.116 per syscalls(2): "Name of the old umount(2)" -- the rename date, not the call's origin |
| Man page | none (no man2/oldumount.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction; umount(2)/umount2(2) live in the fs-mounts-namespace domain ([umount2](../fs-mounts-namespace/umount2.md)) |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; base calls umount(2)/umount2(2) at [umount2](../fs-mounts-namespace/umount2.md) |
| Ledger ID | SC-oldumount |

## Purpose

oldumount() is the old umount(2) entry -- same unmount-the-filesystem contract, no flags argument -- renamed in the per-arch tables when umount2 (with MNT_FORCE/MNT_DETACH/MNT_EXPIRE) arrived, so both numbers could coexist. The verified implementation still lives in fs/namespace.c: `SYSCALL_DEFINE1(oldumount, char __user *, name)` (torvalds/linux master fetched 2026-10-17), a thin wrapper over do_umount with zero flags.

## Synopsis

```c
/* compat variant */
long syscall(SYS_oldumount, const char *target);
```

## Arguments and behavior

One argument: the mount-point path (verified source signature). Behavior equals umount(2) with flags 0.

## Return value and errors

0 on success; -1 with the umount(2) error set (EINVAL/EPERM/EBUSY/ENOENT/EFAULT per man2/umount.2's contract).

## Flags and constants

None (the flags are precisely what this variant lacks).

## Security and notes

Source-limited: signature verified in the fetched source; no man page exists for the renamed slot. Note the ledger's file-name quirk -- the page for oldumount lives at sched-misc/umount2.md, while the modern umount2 lives in fs-mounts-namespace/; cross-links below keep the two apart. Cross-reference: [umount2](../fs-mounts-namespace/umount2.md), [mount](../fs-mounts-namespace/mount.md), [pivot_root](../fs-mounts-namespace/pivot_root.md).

## References

- Kernel source: fs/namespace.c (SYSCALL_DEFINE1(oldumount), torvalds/linux master, fetched 2026-10-17)
- man-pages syscalls(2) (oldumount(2), 2.4.116)

