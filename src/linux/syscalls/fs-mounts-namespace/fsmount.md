# fsmount(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 432 / i386 432 / arm64-generic 432 / arm32 432 |
| Since (kernel) | 5.2 (man HISTORY; hub) |
| Man page | not in local man2 cache; fetched from man7.org -> `source-cache/fetched/fsmount.2.html` / `.txt` (man-pages 6.19) |
| glibc wrapper | Yes, since glibc 2.36 (man HISTORY; glibc NEWS); declared in `<sys/mount.h>` (installed glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-fsmount |

## Purpose

`fsmount()` takes a filesystem context fd that has just run
`FSCONFIG_CMD_CREATE` (the "awaiting-mount" state) and instantiates a detached
mount object for the root of the new filesystem instance, returning an fd bound
to it. Unlike [open_tree(2)](open_tree.md) with `OPEN_TREE_CLONE`, it can be
called only once per context. Afterwards the context is reset into
reconfiguration mode (as if returned by [fspick(2)](fspick.md)) and the context
fd can be closed safely.

## Synopsis

    #include <sys/mount.h>
    int fsmount(int fsfd, unsigned int flags, unsigned int attr_flags);

## Arguments and behavior

| Argument | Meaning |
|---|---|
| `fsfd` | Filesystem context fd from fsopen(2) in "awaiting-mount" state |
| `flags` | `FSMOUNT_CLOEXEC` or 0 |
| `attr_flags` | `MOUNT_ATTR_*` bits applied to the new mount, interpreted like `mount_setattr(2)` with `attr.attr_set` set to the same value |

The returned fd behaves like an `open(2)` `O_PATH` descriptor: it can be a
`dirfd` for `*at()` calls, passed to [move_mount(2)](move_mount.md) to attach
the mount, or to [mount_setattr(2)](mount_setattr.md). If never attached, the
mount is unmounted when the fd is closed; that unmount is lazy, "akin to
umount2(2) with MNT_DETACH" (open references keep working until the mount is
idle). `MOUNT_ATTR_*` values that need extra `mount_attr` fields, notably
`MOUNT_ATTR_IDMAP`, are not valid in `attr_flags`.

## Return value and errors

Returns a new file descriptor on success, -1 on error with `errno` set.
Errors per the man page: `EBUSY` (context in the wrong state; fsmount is
one-shot), `EINVAL` (invalid flag in `flags` or invalid `MOUNT_ATTR_*` in
`attr_flags`), `EMFILE` / `ENFILE` (fd limits), `ENOSPC` (the per-user mount
namespace limit blocks allocating the "anonymous" mount namespace that holds
the detached mount), `ENOMEM`, `EPERM` (missing `CAP_SYS_ADMIN`).

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `FSMOUNT_CLOEXEC` | 0x00000001 | Set `FD_CLOEXEC` on the new descriptor |

`attr_flags` accepts the `MOUNT_ATTR_*` set documented on
[mount_setattr.md](mount_setattr.md) (values from `include/uapi/linux/mount.h`).
Master UAPI adds `FSMOUNT_NAMESPACE` 0x00000002 ("create the mount in a new
mount namespace"); it is absent in the v6.18 tag, so the release that ships it
is unverified here. Installed glibc 2.41 `<sys/mount.h>` does not define it.

## Security and notes

Requires `CAP_SYS_ADMIN` (man page). The detached mount lives in a fresh
"anonymous" mount namespace tied to the caller; the per-user limit on mount
namespaces is surfaced as `ENOSPC`. Typical sequence (man page example):
fsopen -> fsconfig -> fsmount -> openat on the mount fd, then move_mount to
publish the tree. Unmount behavior on close links this page to
[umount2.md](umount2.md).

## References

- Fetched man page: `source-cache/fetched/fsmount.2.txt` (from
  https://man7.org/linux/man-pages/man2/fsmount.2.html, man-pages 6.19)
- Constants: kernel UAPI `include/uapi/linux/mount.h`
  (`source-cache/fetched/master-include-uapi-linux-mount.h`)
- glibc NEWS "Version 2.36" (`source-cache/glibc-sparse/NEWS`)
