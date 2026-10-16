# listxattrat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 465 / 465 / 465 / 465 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (6.13-era xattrat batch in fs/xattr.c) |
| Man page | none (no man2/listxattrat.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; family: [getxattrat](getxattrat.md), [setxattrat](setxattrat.md), [removexattrat](removexattrat.md); base calls on [setxattr](setxattr.md) |
| Ledger ID | SC-listxattrat |

## Purpose

listxattrat() lists the extended attribute names of a file selected by (dfd, pathname) -- the *at(2) form of listxattr(3)/flistxattr(3) (fs/xattr.c, SYSCALL_DEFINE5(listxattrat)). Like the base call, it fills a caller buffer with NUL-separated attribute names and returns the total list length, enabling the size-probe-then-fill two-phase pattern.

## Synopsis

```c
long syscall(SYS_listxattrat, int dfd, const char *pathname,
             unsigned int at_flags, char *list, size_t size);
```

## Arguments and behavior

`dfd`/`pathname` follow the *at convention; `at_flags` carries AT_SYMLINK_NOFOLLOW -- the shared path translates it as `(at_flags & AT_SYMLINK_NOFOLLOW) ? 0 : LOOKUP_FOLLOW` (fs/xattr.c, filename_listxattr path). `list`/`size` are the output buffer and its capacity; a size-0 probe returns the required length (the listxattr(3) convention). Names come back in the `namespace.attr` form, including the special `system.posix_acl_access` / `system.posix_acl_default` synthesized entries (fs/xattr.c, vfs_listxattr machinery shared with the base calls).

## Return value and errors

On success, the total size of the attribute-name list (bytes, including NUL separators); ERANGE-style truncation semantics as the base call when the buffer is too small; a negated error on the raw path: EFAULT (bad list pointer), ENOENT/ENOTDIR/EACCES from the lookup, EOPNOTSUPP on filesystems without xattr support (fs/xattr.c, body).

## Flags and constants

AT_SYMLINK_NOFOLLOW (AT_FDCWD from fcntl.h).

## Security and notes

Listing obeys the same visibility rules as the base listxattr: security.* names are shown only to readers with ptrace-style access, and the operation itself requires no capability -- the caller just needs the path access. For interviews: the *at family's value here is atomicity plus O_PATH workflows (list attributes of a file you can open but not read), and the syscall preserves the exact listxattr(3) buffer contract so libc can layer it transparently later. This page is source-limited: fs/xattr.c (master, fall 2026) is the only reachable source. Cross-reference: [getxattrat](getxattrat.md), [setxattrat](setxattrat.md), [removexattrat](removexattrat.md), [setxattr](setxattr.md), [statx](../descriptors-io/statx.md).

## References

- Kernel source: fs/xattr.c (SYSCALL_DEFINE5(listxattrat), torvalds/linux master, fetched 2026-10-17)
- asm-generic numbering: scripts/syscall.tbl line `465 common listxattrat sys_listxattrat`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
