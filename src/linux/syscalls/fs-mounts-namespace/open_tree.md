# open_tree(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 428 / i386 428 / arm64-generic 428 / arm32 428 |
| Since (kernel) | 5.2 (man HISTORY; hub); `open_tree_attr` since 6.15 |
| Man page | not in local man2 cache; fetched from man7.org -> `source-cache/fetched/open_tree.2.html` / `.txt` (man-pages 6.19; the open_tree_attr section lives inside this page) |
| glibc wrapper | `open_tree()`: yes, since glibc 2.36; `open_tree_attr()`: no wrapper, use `syscall(2)` (man page) |
| Aliases covered | `open_tree_attr` documented here as a section; ledger also carries SC-open_tree_attr (467) with its own hub row |
| Ledger ID | SC-open_tree |

## Purpose

`open_tree()` either (a) returns an `openat(2)`-equivalent `O_PATH`-style
descriptor for `path` (no `OPEN_TREE_CLONE`), or (b) with `OPEN_TREE_CLONE`
creates a detached mount object that is a bind-mount of `path` -- like
`mount(2)` with `MS_BIND`, but tied to a file descriptor and not attached to
the tree. Detached objects can be passed to [move_mount(2)](move_mount.md) or
[mount_setattr(2)](mount_setattr.md); if never attached they are lazily
unmounted on close (akin to `umount2` with `MNT_DETACH`, per the man page).

## Synopsis

    #define _GNU_SOURCE
    #include <fcntl.h>    /* AT_* constants */
    #include <sys/mount.h>
    int open_tree(int dirfd, const char *path, unsigned int flags);

    /* open_tree_attr, via syscall(2): */
    int syscall(SYS_open_tree_attr, int dirfd, const char *path,
                unsigned int flags, struct mount_attr *attr, size_t size);

## Arguments and behavior

`dirfd` / `path` follow the `*at()` convention (absolute path ignores `dirfd`;
`AT_FDCWD`; empty path with `AT_EMPTY_PATH` operates on `dirfd` itself).
Unlike plain `open(2)` with `O_PATH`, automounts are triggered unless
`AT_NO_AUTOMOUNT` is given.

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `OPEN_TREE_CLONE` | 1 | Create detached bind-mount object (needs `CAP_SYS_ADMIN`) |
| `OPEN_TREE_CLOEXEC` | `O_CLOEXEC` | Set `FD_CLOEXEC` |
| `AT_EMPTY_PATH` | - | Empty path operates on `dirfd` (Linux-specific; `_GNU_SOURCE`) |
| `AT_NO_AUTOMOUNT` | - | Do not trigger automount on terminal component |
| `AT_SYMLINK_NOFOLLOW` | - | Do not dereference trailing symlink |
| `AT_RECURSIVE` | - | Recursive bind (like `MS_REC`); only with `OPEN_TREE_CLONE` |

Master UAPI adds `OPEN_TREE_NAMESPACE` 0x2; absent in the v6.18 tag, so the
shipping release is unverified here.

## open_tree_attr (since Linux 6.15)

`open_tree_attr()` performs the same operation and additionally applies the
`struct mount_attr` changes in `attr` (with `size` = `sizeof(struct
mount_attr)`) before returning the fd. Version pin 6.15 was verified by tag
probes in worklog task 1-d (absent in v6.14, present in v6.15) and by the
fetched page's HISTORY section ("open_tree_attr: Linux 6.15"). Semantics match
[mount_setattr(2)](mount_setattr.md) with two extensions: `MOUNT_ATTR_IDMAP`
can be set or cleared on a newly cloned detached mount (clearing disables
id-mapping), and `AT_RECURSIVE` applies attributes recursively on top of the
bind recursion (still requires `OPEN_TREE_CLONE`). Without
`OPEN_TREE_CLONE` it modifies the attributes of the mount attached at `path`
and fails if that is not a mount point. There is no glibc wrapper; ledger row
SC-open_tree_attr (numbers 467 on all four ABIs) tracks it separately in the
[hub](overview.md).

## Return value and errors

Returns a new file descriptor on success, -1 on error with `errno` set.
Errors include `EPERM` (`OPEN_TREE_CLONE` without `CAP_SYS_ADMIN`), `EBADF`,
`EFAULT`, `EINVAL` (invalid flag), `EACCES`, `ELOOP`, `ENAMETOOLONG`,
`ENOENT` (including empty path without `AT_EMPTY_PATH`), `ENOTDIR`, `EMFILE`,
`ENFILE`, `ENOMEM`, and `ENOSPC` (per-user mount namespace limit blocks the
"anonymous" namespace needed for a `OPEN_TREE_CLONE` object).

## Security and notes

Only `OPEN_TREE_CLONE` is privileged; the plain path-open mode behaves like
`openat(2)`. Detached bind objects are the container-runtime building block for
constructing mount trees before publication, together with
[fsmount.md](fsmount.md) and [fspick.md](fspick.md).

## References

- Fetched man page: `source-cache/fetched/open_tree.2.txt` (from
  https://man7.org/linux/man-pages/man2/open_tree.2.html, man-pages 6.19)
- Constants: kernel UAPI `include/uapi/linux/mount.h`
  (`source-cache/fetched/master-include-uapi-linux-mount.h`)
- Worklog task 1-d (version pins), [overview.md](overview.md)
