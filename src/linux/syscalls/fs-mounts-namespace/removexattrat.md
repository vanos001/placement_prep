# removexattrat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 466 / 466 / 466 / 466 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (6.13-era xattrat batch in fs/xattr.c) |
| Man page | none (no man2/removexattrat.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; family: [getxattrat](getxattrat.md), [setxattrat](setxattrat.md), [listxattrat](listxattrat.md); base calls on [setxattr](setxattr.md) |
| Ledger ID | SC-removexattrat |

## Purpose

removexattrat() removes the extended attribute `name` from a file selected by (dfd, pathname) -- the *at(2) form of removexattr(3)/fremovexattr(3) (fs/xattr.c, SYSCALL_DEFINE4(removexattrat)). The base calls are literally implemented on top of its shared helper: `SYSCALL_DEFINE2(removexattr, ...) { return path_removexattrat(AT_FDCWD, pathname, 0, name); }` (fs/xattr.c), which makes this the canonical entry point in the current kernel.

## Synopsis

```c
long syscall(SYS_removexattrat, int dfd, const char *pathname,
             unsigned int at_flags, const char *name);
```

## Arguments and behavior

`dfd`/`pathname` follow the *at convention (AT_FDCWD allowed); `at_flags` carries AT_SYMLINK_NOFOLLOW, translated by the shared path as `(at_flags & AT_SYMLINK_NOFOLLOW) ? 0 : LOOKUP_FOLLOW` (fs/xattr.c, filename_removexattr path). `name` is the fully-qualified attribute name (user.data, security.selinux, ...). Removal obeys the per-namespace write rules: user.* requires ownership of the file, security.* requires capability or LSM-granted rights, trusted.* requires CAP_SYS_ADMIN (fs/xattr.c, xattr_permission machinery shared with the base calls).

## Return value and errors

0 on success; a negated error on the raw path: EFAULT (bad pointers), ENODATA (attribute does not exist), EPERM (write rules of the namespace violated), EACCES/ENOENT/ENOTDIR from the lookup, EOPNOTSUPP on filesystems without xattr support (fs/xattr.c, body).

## Flags and constants

AT_SYMLINK_NOFOLLOW (AT_FDCWD from fcntl.h).

## Security and notes

Removal is a write operation, so the interesting failures are permission ones -- interviews like the user.* ownership rule and the fact that removing security.* attributes can invalidate LSM state on the file. The *at form matters for the same reasons as the rest of the family: race-free operation against an already-resolved directory, and support for O_PATH-resolved targets. This page is source-limited: fs/xattr.c (master, fall 2026) is the only reachable source. Cross-reference: [setxattrat](setxattrat.md), [getxattrat](getxattrat.md), [listxattrat](listxattrat.md), [setxattr](setxattr.md), [file_setattr](file_setattr.md).

## References

- Kernel source: fs/xattr.c (SYSCALL_DEFINE4(removexattrat) and the base removexattr(2) built on path_removexattrat, torvalds/linux master, fetched 2026-10-17)
- asm-generic numbering: scripts/syscall.tbl line `466 common removexattrat sys_removexattrat`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
