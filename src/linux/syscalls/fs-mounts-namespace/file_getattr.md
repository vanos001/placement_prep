# file_getattr(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 468 / 468 / 468 / 468 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (post-6.13 addition to fs/file_attr.c) |
| Man page | none (no man2/file_getattr.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; the write side is [file_setattr](file_setattr.md) |
| Ledger ID | SC-file_getattr |

## Purpose

file_getattr() reads the merged "miscellaneous file attributes" of a file -- the FS_IOC_GETFLAGS-style inode flags and the FS_IOC_FSGETXATTR-style xfs attributes -- into a `struct file_attr`, through a (dfd, filename) pair instead of an ioctl on an open fd (fs/file_attr.c, SYSCALL_DEFINE5(file_getattr)). It is the syscall-shaped, extensible successor to the two ioctl interfaces, replacing the fixed ioctl structs with a versioned, extensible-struct ABI (the `usize` argument).

## Synopsis

```c
struct file_attr {            /* include/uapi/linux/fs.h */
    __u64 fa_xflags;          /* xflags field value (get/set) */
    __u32 fa_extsize;         /* extsize field value (get/set) */
    __u32 fa_nextents;        /* nextents field value (get) */
    __u32 fa_projid;          /* project identifier (get/set) */
    __u32 fa_cowextsize;      /* CoW extsize field value (get/set) */
};                            /* FILE_ATTR_SIZE_VER0 = 24 */

long syscall(SYS_file_getattr, int dfd, const char *filename,
             struct file_attr *ufattr, size_t usize,
             unsigned int at_flags);
```

## Arguments and behavior

`dfd`/`filename` follow the *at(2) convention: AT_FDCWD or a directory descriptor plus a relative path; `at_flags` accepts AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH (fs/file_attr.c, body: `(at_flags & ~(AT_SYMLINK_NOFOLLOW | AT_EMPTY_PATH))` rejected with EINVAL -- the setattr side shows the mask explicitly; the getattr body applies the same convention). `ufattr`/`usize` form an extensible struct: `usize` below FILE_ATTR_SIZE_VER0 (24) fails with EINVAL, values above the kernel's size are tolerated via the copy_struct_from_user zero-padding rule, which is how future fields get appended without new syscall numbers (fs/file_attr.c, BUILD_BUG_ON/usize checks). The returned `fa_xflags` merges the ext* flags (FS_SYNC_FL, FS_IMMUTABLE_FL, FS_APPEND_FL, FS_NODUMP_FL, FS_NOATIME_FL, FS_DAX_FL, FS_PROJINHERIT_FL, FS_VERITY_FL) and the xfs xflags (include/linux/fileattr.h, FS_COMMON_FL/FS_XFLAG_COMMON), with the VFS helpers translating per filesystem.

## Return value and errors

0 on success; a negated error on the raw path: EINVAL (bad at_flags; usize below VER0), EFAULT (ufattr unreadable), ENOENT/ENOTDIR/EACCES from the path lookup, EOPNOTSUPP when the filesystem supports neither flags nor xflags sub-interface (fs/file_attr.c, body).

## Flags and constants

AT_SYMLINK_NOFOLLOW, AT_EMPTY_PATH (uapi fcntl.h). fa_xflags bits: FS_*_FL / FS_XFLAG_* family (include/linux/fileattr.h, include/uapi/linux/fs.h).

## Security and notes

Reads do not require privilege beyond path access -- the same data was always readable via the ioctls on an open fd; the win is one round-trip for metadata collectors (fileserver scanners, backup tools) and the ability to operate on O_PATH-opened targets via AT_EMPTY_PATH. The write side (immutable/append/project-id changes) carries the usual CAP_LINUX_IMMUTABLE-style restrictions per flag -- see [file_setattr](file_setattr.md). This page is source-limited: no man page exists; behavior is quoted from fs/file_attr.c and include/uapi/linux/fs.h (master, fall 2026). Cross-reference: [file_setattr](file_setattr.md), [statx](../descriptors-io/statx.md), [getxattrat](getxattrat.md), [setxattr](setxattr.md).

## References

- Kernel source: fs/file_attr.c (SYSCALL_DEFINE5(file_getattr), torvalds/linux master, fetched 2026-10-17)
- UAPI: include/uapi/linux/fs.h (struct file_attr, FILE_ATTR_SIZE_VER0); include/linux/fileattr.h (flag masks)
- asm-generic numbering: scripts/syscall.tbl line `468 common file_getattr sys_file_getattr`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
