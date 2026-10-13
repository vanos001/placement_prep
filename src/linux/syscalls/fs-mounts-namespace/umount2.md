# umount2(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 166 / i386 52 / arm64-generic 39 / arm32 52 |
| Since (kernel) | 2.1.116 (man umount.2 DESCRIPTION; ledger row SC-umount2 says 2.2) |
| Man page | man2/umount2.2 exists only as a roff `.so` alias -> man2/umount.2 (cached) |
| glibc wrapper | Yes; `umount2()` in `<sys/mount.h>` (installed glibc 2.41); `MNT_DETACH` / `MNT_EXPIRE` in glibc since 2.11 |
| Aliases covered | `umount` (SC-umount; oldumount: i386 22 / arm32 OABI 22 only, no x64 or arm64-generic number) |
| Ledger ID | SC-umount2 |

## Purpose

`umount2()` removes the attachment of the (topmost) filesystem mounted on `target`
and allows flags that control the operation. It was added in Linux 2.1.116; the
x86_64 and asm-generic ABIs expose only this flags-taking variant. The man page
records a naming wrinkle: "umount2 is the glibc name for what the kernel now calls
umount, and umount is the glibc name for oldumount". Plain `umount(target)` (the
glibc wrapper of oldumount, i386 syscall 22) has no flags and no number on x64 /
arm64-generic; the hub [overview.md](overview.md) routes `umount` and `umount2`
to a shared `umount.md` family page, while this page documents the flag set.

## Synopsis

    #include <sys/mount.h>
    int umount2(const char *target, int flags);

## Arguments and behavior

| Argument | Meaning |
|---|---|
| `target` | Mount point to detach; must name a mount point in the caller's mount namespace |
| `flags` | Bit mask of `MNT_*` constants (table below); 0 gives plain umount semantics |

Appropriate privilege (`CAP_SYS_ADMIN`) is required. Historical note from the man
page: before 2.3.99-pre7 `umount(device)` existed; only `umount(dir)` remains
because devices can be mounted in several places.

## Flags and constants

| Constant | Value | Meaning | Since |
|---|---|---|---|
| `MNT_FORCE` | 1 | Ask the filesystem to abort pending requests before unmounting; may complete without an inaccessible server but can lose data; still fails if processes hold references | 2.1.116 |
| `MNT_DETACH` | 2 | Lazy unmount: hide from new lookups, disconnect the subtree, really unmount when no longer busy | 2.4.11 |
| `MNT_EXPIRE` | 4 | Mark as expired; first call fails with `EAGAIN` and marks it, a second call unmounts if untouched in between; invalid with `MNT_FORCE` or `MNT_DETACH` | 2.6.8 |
| `UMOUNT_NOFOLLOW` | 8 | Do not dereference `target` if it is a symbolic link (set-user-ID-root safety) | 2.6.34 |

`MNT_FORCE` filesystem support "as at Linux 4.12" per the man page: NFS (2.1.116),
cifs (2.6.12), 9p (2.6.16), fuse (2.6.16), ceph (2.6.34), lustre (3.11).
Lock flags: the kernel-internal `MNT_LOCK_*` bits (not in UAPI headers) mark mounts
whose flags are pinned by namespace propagation; unmounting a locked mount fails
with `EINVAL`, see [mount.md](mount.md) and `mount_namespaces(7)`.

## Return value and errors

Returns 0 on success, -1 on error with `errno` set. Errors: `EAGAIN` (`MNT_EXPIRE`
marked an unbusy filesystem), `EBUSY` (target busy), `EFAULT`, `EINVAL` (not a
mount point; locked mount; `MNT_EXPIRE` combined with `MNT_FORCE`/`MNT_DETACH`;
invalid flag since 2.6.34), `ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `EPERM`.

## Security and notes

Requires `CAP_SYS_ADMIN` in the owning user namespace of the mount namespace.
Shared mounts propagate unmounts to every peer and its slaves; the man page warns
that `MNT_DETACH` of a recursive bind of `/` can lazily unmount everything and
recommends `mount(..., MS_REC | MS_PRIVATE, ...)` first. `UMOUNT_NOFOLLOW` exists
to harden set-user-ID programs that let unprivileged users unmount filesystems.
Detached mount objects from the fd API (fsmount / open_tree with
`OPEN_TREE_CLONE`) are implicitly lazily unmounted on close, "akin to umount2
with MNT_DETACH" (fetched fsmount.2 / open_tree.2).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/umount.2`, `.so` alias `umount2.2`
- Online: https://man7.org/linux/man-pages/man2/umount2.2.html
- Constants: `/usr/include/x86_64-linux-gnu/sys/mount.h` (enum `MNT_FORCE` .. `UMOUNT_NOFOLLOW`)
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (166), `syscall_32.tbl` (22, 52)
