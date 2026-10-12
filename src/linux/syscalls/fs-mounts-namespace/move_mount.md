# move_mount(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 429 / i386 429 / arm64-generic 429 / arm32 429 |
| Since (kernel) | 5.2 (man HISTORY; hub); `MOVE_MOUNT_SET_GROUP` since 5.15, `MOVE_MOUNT_BENEATH` since 6.5 |
| Man page | not in local man2 cache; fetched from man7.org -> `source-cache/fetched/move_mount.2.html` / `.txt` (man-pages 6.19) |
| glibc wrapper | Yes, since glibc 2.36 (man HISTORY; glibc NEWS); declared in `<sys/mount.h>` (installed glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-move_mount |

## Purpose

`move_mount()` moves the mount object identified by `from_dirfd` /
`from_path` to the location identified by `to_dirfd` / `to_path`. The source
can be an existing mount in the caller's namespace (equivalent to
`mount(2)` with `MS_MOVE`) or a detached mount object from
[fsmount(2)](fsmount.md) or [open_tree(2)](open_tree.md) with
`OPEN_TREE_CLONE` (equivalent to attaching a bind mount). A mount fd stays
bound to its mount object after the call, so it can be re-attached repeatedly.

## Synopsis

    #include <fcntl.h>   /* AT_* constants */
    #include <sys/mount.h>
    int move_mount(int from_dirfd, const char *from_path,
                   int to_dirfd, const char *to_path,
                   unsigned int flags);

## Arguments and behavior

Both (dirfd, path) pairs follow the `*at()` convention: absolute paths ignore
the dirfd, `AT_FDCWD` means the caller's working directory, relative paths
resolve against the dirfd, and an empty path with the matching
`MOVE_MOUNT_*_EMPTY_PATH` flag operates on the dirfd itself (any file type).
No permission is needed on the source or destination objects, but execute
(search) permission is required on every directory named in the two paths.

## Flags and constants

| Constant | Value | Meaning | Since |
|---|---|---|---|
| `MOVE_MOUNT_F_SYMLINKS` | 0x00000001 | Follow symlinks on from path (default: no) | 5.2 |
| `MOVE_MOUNT_F_AUTOMOUNTS` | 0x00000002 | Follow automounts on from path | 5.2 |
| `MOVE_MOUNT_F_EMPTY_PATH` | 0x00000004 | Empty from path permitted (standard way to attach a detached mount fd) | 5.2 |
| `MOVE_MOUNT_T_SYMLINKS` | 0x00000010 | Follow symlinks on to path | 5.2 |
| `MOVE_MOUNT_T_AUTOMOUNTS` | 0x00000020 | Follow automounts on to path | 5.2 |
| `MOVE_MOUNT_T_EMPTY_PATH` | 0x00000040 | Empty to path permitted | 5.2 |
| `MOVE_MOUNT_SET_GROUP` | 0x00000100 | Do not move anything; add the to-side attached private mount into the peer group of the from-side mount (argument order matters: the to-side is modified) | 5.15 |
| `MOVE_MOUNT_BENEATH` | 0x00000200 | Attach or move beneath the top mount of the target stack instead of over it | 6.5 |

`MOVE_MOUNT__MASK` is 0x00000377 in the UAPI header. `MOVE_MOUNT_BENEATH`
restrictions summarized from the man page: nothing beneath the filesystem root
(use `pivot_root(2)`, see [pivot_root.md](pivot_root.md)); target must not be a
detached mount; top mount and its parent must be in the caller's namespace;
caller must be privileged enough to unmount the top mount; no overmounts on the
source; propagation constraints on the parent mounts.

## Return value and errors

Returns 0 on success, -1 on error with `errno` set. Errors include `EPERM`
(missing `CAP_SYS_ADMIN`), `EBADF`, `EFAULT`, `EINVAL` (invalid flag; source is
not a mount object; incompatible mount types; source or target outside the
caller's namespace; shared parent mount of source; `BENEATH` restrictions
violated), `EACCES`, `ELOOP`, `ENAMETOOLONG`, `ENOENT` (including empty path
without the EMPTY_PATH flag), `ENOTDIR`, `ENOMEM`.

## Security and notes

Requires `CAP_SYS_ADMIN` (man page). `MOVE_MOUNT_SET_GROUP` enables building a
private mount tree first and configuring shared-subtree propagation afterwards
(`mount_namespaces(7)` peer groups). `MOVE_MOUNT_BENEATH` gives atomic
mount-tree replacement ("upgrade" by covering a tree and later unmounting the
cover, see [umount2.md](umount2.md)).

## References

- Fetched man page: `source-cache/fetched/move_mount.2.txt` (from
  https://man7.org/linux/man-pages/man2/move_mount.2.html, man-pages 6.19)
- Constants: kernel UAPI `include/uapi/linux/mount.h`
  (`source-cache/fetched/master-include-uapi-linux-mount.h`)
- Siblings: [fsmount.md](fsmount.md), [open_tree.md](open_tree.md),
  [mount_setattr.md](mount_setattr.md), [mount.md](mount.md)
