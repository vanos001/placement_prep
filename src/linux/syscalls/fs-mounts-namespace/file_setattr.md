# file_setattr(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 469 / 469 / 469 / 469 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (post-6.13 addition to fs/file_attr.c) |
| Man page | none (no man2/file_setattr.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; the read side is [file_getattr](file_getattr.md) |
| Ledger ID | SC-file_setattr |

## Purpose

file_setattr() writes the merged miscellaneous file attributes -- the ioctl FS_IOC_SETFLAGS and FS_IOC_FSSETXATTR surface -- through one versioned syscall, taking a `struct file_attr` from the caller and applying it to the file resolved from (dfd, filename) (fs/file_attr.c, SYSCALL_DEFINE5(file_setattr)). It exists so that attribute manipulation stops depending on an open file descriptor and fixed-size ioctl structs, and so new per-file attributes can be added behind the extensible-struct rule.

## Synopsis

```c
struct file_attr {            /* include/uapi/linux/fs.h */
    __u64 fa_xflags;          /* xflags field value (get/set) */
    __u32 fa_extsize;         /* extsize field value (get/set) */
    __u32 fa_nextents;        /* nextents field value (get) */
    __u32 fa_projid;          /* project identifier (get/set) */
    __u32 fa_cowextsize;      /* CoW extsize field value (get/set) */
};                            /* FILE_ATTR_SIZE_VER0 = 24 */

long syscall(SYS_file_setattr, int dfd, const char *filename,
             const struct file_attr *ufattr, size_t usize,
             unsigned int at_flags);
```

## Arguments and behavior

Same (dfd, filename, ufattr, usize, at_flags) shape as [file_getattr](file_getattr.md); `at_flags` accepts AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH -- anything else is rejected with EINVAL (`(at_flags & ~(AT_SYMLINK_NOFOLLOW | AT_EMPTY_PATH)) != 0` check, fs/file_attr.c, body). `usize` below FILE_ATTR_SIZE_VER0 fails with EINVAL; larger sizes go through copy_struct_from_user, so trailing unknown bytes must be zero (fs/file_attr.c, body). The kernel translates fa_xflags into the fileattr machinery (fileattr_fill_xflags / fileattr_fill_flags in include/linux/fileattr.h) and hands it to the filesystem, which enforces per-flag policy: the immutable and append flags require CAP_LINUX_IMMUTABLE (the same rule FS_IOC_SETFLAGS has always applied), project-ID changes require project-quota setup, and read-only inode flags (FS_XFLAG_PREALLOC, FS_XFLAG_HASATTR, FS_XFLAG_VERITY, FS_XFLAG_CASEFOLD, ...) are not settable through this interface (include/linux/fileattr.h, FS_XFLAG_RDONLY_MASK).

## Return value and errors

0 on success; a negated error on the raw path: EINVAL (bad at_flags; usize below VER0; flags the filesystem rejects), EPERM (CAP_LINUX_IMMUTABLE-gated flags on a non-privileged caller; project-ID rules), EFAULT (ufattr unreadable), EACCES/ENOENT/ENOTDIR from the path lookup, EOPNOTSUPP where the filesystem lacks the sub-interface (fs/file_attr.c, body).

## Flags and constants

AT_SYMLINK_NOFOLLOW, AT_EMPTY_PATH; fa_xflags FS_*_FL / FS_XFLAG_* family (include/uapi/linux/fs.h, include/linux/fileattr.h).

## Security and notes

The security-sensitive flags are the same ones interviews ask about: FS_IMMUTABLE_FL pins a file against modification and unlink (the classic ransomware-hardening and rootkit-hiding duality -- CAP_LINUX_IMMUTABLE decides which), FS_APPEND_FL enforces append-only logs, FS_PROJINHERIT_FL drives project quotas in containers. Because the call goes through a path rather than an fd, LSMs see the operation at path level (security hooks inside the fileattr machinery), matching ioctl behavior. This page is source-limited: fs/file_attr.c and include/linux/fileattr.h (master, fall 2026) are the only reachable sources. Cross-reference: [file_getattr](file_getattr.md), [setxattr](setxattr.md), [removexattrat](removexattrat.md), [statx](../descriptors-io/statx.md).

## References

- Kernel source: fs/file_attr.c (SYSCALL_DEFINE5(file_setattr), torvalds/linux master, fetched 2026-10-17)
- UAPI: include/uapi/linux/fs.h (struct file_attr, FILE_ATTR_SIZE_VER0); include/linux/fileattr.h (FS_XFLAG_RDONLY_MASK, fill helpers)
- asm-generic numbering: scripts/syscall.tbl line `469 common file_setattr sys_file_setattr`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
