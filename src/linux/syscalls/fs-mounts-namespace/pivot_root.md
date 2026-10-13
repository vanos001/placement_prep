# pivot_root(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 155 / i386 217 / arm64-generic 41 / arm32 218 |
| Since (kernel) | 2.3.41 (man VERSIONS: "pivot_root() was introduced in Linux 2.3.41"; ledger/worklog 1-d note that the ledger's Since column says 2.4 -- the man page value 2.3.41 is quoted here) |
| Man page | man2/pivot_root.2 (local cache, dated 2021-03-22) |
| glibc wrapper | None; call as `syscall(SYS_pivot_root, new_root, put_old)` (man page) |
| Aliases covered | none |
| Ledger ID | SC-pivot_root |

## Purpose

`pivot_root()` changes the root mount in the calling process's mount namespace:
it moves the current root mount to `put_old` and makes `new_root` the new root
mount. This is the standard way to switch from an initrd / temporary root to
the real root during boot, and the modern way to install a container's root
filesystem, because it leaves the old root mounted at a known place where it
can be unmounted ([umount2.md](umount2.md)). It also changes the root directory
and current working directory of every process or thread in the same mount
namespace whose root or cwd points at the old root, which keeps kernel threads
from pinning the old mount busy.

## Synopsis

    #include <sys/syscall.h>    /* SYS_* constants */
    #include <unistd.h>
    int syscall(SYS_pivot_root, const char *new_root, const char *put_old);

## Arguments and behavior

| Argument | Meaning |
|---|---|
| `new_root` | Path to the new root mount; must be a mount point and must not be `/` (a non-mount-point path can be turned into one by bind-mounting it onto itself) |
| `put_old` | Directory at or underneath `new_root` that receives the old root mount |

Restrictions from the man page: both paths must be directories; neither may be
on the same mount as the current root; `put_old` must be at or underneath
`new_root`; the propagation type of the parent mount of `new_root` (and of the
current root's parent, and of `put_old` if it is a mount point) must not be
`MS_SHARED`, so pivot operations never propagate to other namespaces; the
current root must be a mount point. The caller's own cwd is not changed unless
it was on the old root, so the sequence should be followed by `chdir("/")`
([chdir.md](chdir.md)). The `rootfs` (initial ramfs) mount cannot be
pivot_root-ed; the documented alternative is to delete its contents,
overmount it, and exec the new init (`switch_root(8)`).

## Return value and errors

Returns 0 on success, -1 on error with `errno` set. Errors per the man page:
`EBUSY` (`new_root` or `put_old` on the current root mount), `EINVAL`
(`new_root` not a mount point; `put_old` not at/under `new_root`; current root
not a mount point, e.g. after an earlier `chroot(2)`; current root on the
rootfs; `MS_SHARED` propagation on the involved mounts), `ENOTDIR`, `EPERM`
(missing capability), plus the general errors of `stat(2)`.

## Security and notes

Requires `CAP_SYS_ADMIN` in the user namespace that owns the caller's mount
namespace (man page). The man page documents the no-temporary-directory idiom
`chdir(new_root); pivot_root(".", "."); umount2(".", MNT_DETACH)`, which works
because the old root is stacked on top of the new root at `/`. `move_mount(2)`
with `MOVE_MOUNT_BENEATH` ([move_mount.md](move_mount.md)) explicitly cannot
mount beneath the filesystem root configured by `chroot(2)` or `pivot_root(2)`;
pivot_root remains the tool for that case.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/pivot_root.2`
- Online: https://man7.org/linux/man-pages/man2/pivot_root.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (155),
  `syscall_32.tbl` (217), `syscall_generic.tbl` (41)
- Worklog task 1-d: ledger Since discrepancy note (2.3.41 vs 2.4)
