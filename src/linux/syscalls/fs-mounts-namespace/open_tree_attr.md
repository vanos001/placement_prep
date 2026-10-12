# open_tree_attr(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 467 / i386 467 / arm64-generic 467 / arm32 467 (`common` in the x64 table, worklog 1-d) |
| Since (kernel) | 6.15 (open_tree.2 fetched HISTORY: "open_tree_attr() Linux 6.15"; worklog 1-d tag probe: present v6.15, absent v6.14; ledger date "--") |
| Man page | No standalone page: documented as the open_tree_attr() section of man7.org open_tree.2 (man-pages 6.19), cached at `source-cache/fetched/open_tree.2.txt`; kernel side read from `fs/namespace.c` (master, this session) |
| glibc wrapper | None -- the man page and `<bits/syscall.h>` (`SYS_open_tree_attr`) both require `syscall(2)` |
| Aliases covered | none (ledger row SC-open_tree_attr only) |
| Ledger ID | SC-open_tree_attr |

## Purpose

`open_tree_attr()` is `open_tree()` with a mount-attribute argument bolted
on: it clones or opens a detached mount object exactly as
[open_tree.md](open_tree.md) does, then applies a `struct mount_attr`
change to the result before the descriptor is returned. This saves the
open_tree -> mount_setattr two-step and, critically, allows configuring
`MOUNT_ATTR_IDMAP` on a freshly cloned mount in one call.

## Synopsis

    /* via syscall(2): glibc provides no wrapper */
    int syscall(SYS_open_tree_attr, int dirfd, const char *path,
                unsigned int flags, struct mount_attr *attr, size_t size);

## Arguments and behavior

`dirfd`/`path`/`flags` behave exactly as for `open_tree()`
(`OPEN_TREE_CLONE`, `AT_EMPTY_PATH`, `AT_SYMLINK_NOFOLLOW`,
`AT_NO_AUTOMOUNT`, `AT_RECURSIVE`; see the open_tree page for the table).
`attr` is the `struct mount_attr` described on
[mount_setattr.md](mount_setattr.md) (`attr_set`, `attr_clr`, `propagation`,
`userns_fd`); `size` must be `sizeof(struct mount_attr)` to allow future
extension. With `attr == NULL`, or all of `attr_set` / `attr_clr` /
`propagation` zero, the call degenerates to plain `open_tree()`. Semantics
are those of `mount_setattr(2)` with two extensions: (1) on an
`OPEN_TREE_CLONE` clone, `MOUNT_ATTR_IDMAP` may be added to `attr_clr` to
drop an ID mapping or to `attr_set` with `attr.userns_fd` to install a new
one -- changing or removing the mapping of an already existing mount is only
permitted here, on a new detached clone; (2) `AT_RECURSIVE` applies the
attributes recursively in addition to the open_tree meaning of
`AT_RECURSIVE`, and therefore requires `OPEN_TREE_CLONE`. Without
`OPEN_TREE_CLONE`, the call modifies the attributes of the mount attached at
`path`, and fails if that path is not a mount point.

## Return value and errors

Returns a new file descriptor on success, -1 on error: `EACCES`, `EBADF`,
`EFAULT`, `EINVAL` (bad flags/attr), `ELOOP`, `EMFILE`, `ENAMETOOLONG`,
`ENFILE`, `ENOENT`, `ENOSPC` (anonymous mount-namespace limit),
`ENOMEM`, `EPERM` (`OPEN_TREE_CLONE` without `CAP_SYS_ADMIN`). Kernel source
(fs/namespace.c, master): `SYSCALL_DEFINE5(open_tree_attr, dfd, filename,
flags, uattr, usize)` rejects `!uattr && usize` with `EINVAL`, opens the
tree via the shared `open_tree` path, then runs the shared
`mount_setattr` machinery; `MOUNT_KATTR_IDMAP_REPLACE` is set only when
`OPEN_TREE_CLONE`, and `MOUNT_KATTR_RECURSE` when `AT_RECURSIVE`.

## Flags and constants

Reuses the `OPEN_TREE_*` / `AT_*` flag set of open_tree and the
`MOUNT_ATTR_*` bits of mount_setattr verbatim (both tabled on their pages);
no constants are unique to this call.

## Security and notes

Marked per the worklog: this page is source-limited to the fetched
open_tree.2 section plus kernel source -- no dedicated man page exists in
our cached man2 tree (fchmodat2-era batch). The ID-mapping replace path is
the feature that motivated the syscall. Companions:
[open_tree.md](open_tree.md), [mount_setattr.md](mount_setattr.md),
[move_mount.md](move_mount.md).

## References

- Fetched man page section: `source-cache/fetched/open_tree.2.txt`
  (man-pages 6.19, "open_tree_attr()" subsection)
- Kernel implementation: `fs/namespace.c` on torvalds/linux master
  (`SYSCALL_DEFINE5(open_tree_attr, ...)`), fetched this session
- Version pin: worklog Task 1-d (unistd.h probes v6.14/v6.15);
  `SYS_open_tree_attr` in installed `<bits/syscall.h>`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (467, `common`)
