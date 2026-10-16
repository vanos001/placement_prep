# getxattrat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 464 / 464 / 464 / 464 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (6.13-era xattrat batch in fs/xattr.c) |
| Man page | none (no man2/getxattrat.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; family: [setxattrat](setxattrat.md), [listxattrat](listxattrat.md), [removexattrat](removexattrat.md); base calls on [setxattr](setxattr.md) |
| Ledger ID | SC-getxattrat |

## Purpose

getxattrat() reads one extended attribute of a file selected by (dfd, pathname) -- the *at(2)-style, extensible-struct version of getxattr(3)/fgetxattr(3) (fs/xattr.c, SYSCALL_DEFINE6(getxattrat)). The attribute value and buffer size are passed through a `struct xattr_args` rather than bare arguments, so the interface can grow without new numbers.

## Synopsis

```c
struct xattr_args {           /* include/uapi/linux/xattr.h */
    __aligned_u64 value;      /* user pointer to the attribute buffer */
    __u32 size;               /* buffer size (bytes) */
    __u32 flags;              /* must be 0 on getxattrat */
};                            /* XATTR_ARGS_SIZE_VER0 */

long syscall(SYS_getxattrat, int dfd, const char *pathname,
             unsigned int at_flags, const char *name,
             struct xattr_args *uargs, size_t usize);
```

## Arguments and behavior

`dfd`/`pathname` follow the *at convention (AT_FDCWD allowed); `at_flags` carries AT_SYMLINK_NOFOLLOW semantics -- the lookup flags are derived as `(at_flags & AT_SYMLINK_NOFOLLOW) ? 0 : LOOKUP_FOLLOW` in the shared filename_getxattr path (fs/xattr.c). `name` is the attribute name in the usual `namespace.attr` form (user., security., trusted., system.). `uargs`/`usize` form the extensible struct: usize below XATTR_ARGS_SIZE_VER0 fails with EINVAL, above PAGE_SIZE with E2BIG, and copy_struct_from_user absorbs trailing growth (fs/xattr.c, body). Inside xattr_args, `value` is the output buffer and `size` its length; `flags` must be 0 -- anything else fails with EINVAL (fs/xattr.c, body). A zero `value`/`size` pair queries the attribute size, mirroring getxattr(3)'s two-phase pattern.

## Return value and errors

On success, the number of bytes copied into the buffer (or the attribute size for the size-query form), matching getxattr(3)'s contract; a negated error on the raw path: EINVAL (usize below VER0; args.flags nonzero), E2BIG (usize above PAGE_SIZE), EFAULT (bad pointers), ENOATTR/ENODATA (attribute does not exist), EACCES/ENOENT/ENOTDIR from the lookup (fs/xattr.c, body).

## Flags and constants

AT_SYMLINK_NOFOLLOW (AT_FDCWD from fcntl.h); xattr_args.flags must be 0 for the get side.

## Security and notes

Access rules are those of the base xattr calls: security.* reads require ptrace-style access to the file (read permission or ownership), user.* obeys ordinary read permissions and the attribute-size quota against the inode. The interesting design point for interviews: pushing value/size into a struct is what lets the kernel later add flags (e.g. value-pinning, xattr-handle semantics) without a new syscall -- the same copy_struct_from_user pattern as [statx](../descriptors-io/statx.md) and clone3. This page is source-limited: fs/xattr.c and include/uapi/linux/xattr.h (master, fall 2026) are the only reachable sources. Cross-reference: [setxattrat](setxattrat.md), [listxattrat](listxattrat.md), [removexattrat](removexattrat.md), [setxattr](setxattr.md), [file_getattr](file_getattr.md).

## References

- Kernel source: fs/xattr.c (SYSCALL_DEFINE6(getxattrat), torvalds/linux master, fetched 2026-10-17)
- UAPI: include/uapi/linux/xattr.h (struct xattr_args)
- asm-generic numbering: scripts/syscall.tbl line `464 common getxattrat sys_getxattrat`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
