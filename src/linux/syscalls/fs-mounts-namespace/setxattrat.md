# setxattrat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 463 / 463 / 463 / 463 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (6.13-era xattrat batch in fs/xattr.c) |
| Man page | none (no man2/setxattrat.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; family: [getxattrat](getxattrat.md), [listxattrat](listxattrat.md), [removexattrat](removexattrat.md); base calls on [setxattr](setxattr.md) |
| Ledger ID | SC-setxattrat |

## Purpose

setxattrat() creates or replaces the extended attribute `name` on a file selected by (dfd, pathname), taking the value through the extensible `struct xattr_args` -- the *at(2), versioned form of setxattr(3)/fsetxattr(3) (fs/xattr.c, SYSCALL_DEFINE6(setxattrat)). It is the lowest-numbered member (463) of the xattrat batch, which the kernel introduced so containers and LSM tooling could manage xattrs on path-resolved and O_PATH-resolved targets.

## Synopsis

```c
struct xattr_args {           /* include/uapi/linux/xattr.h */
    __aligned_u64 value;      /* user pointer to the attribute value */
    __u32 size;               /* value length (bytes) */
    __u32 flags;              /* XATTR_CREATE (1) / XATTR_REPLACE (2) */
};

long syscall(SYS_setxattrat, int dfd, const char *pathname,
             unsigned int at_flags, const char *name,
             const struct xattr_args *uargs, size_t usize);
```

## Arguments and behavior

`dfd`/`pathname` follow the *at convention; `at_flags` carries AT_SYMLINK_NOFOLLOW (fs/xattr.c, shared lookup path). `uargs`/`usize` are the extensible struct: usize below XATTR_ARGS_SIZE_VER0 fails with EINVAL, above PAGE_SIZE with E2BIG, copy_struct_from_user absorbs growth (fs/xattr.c, body). Inside the struct, `value`/`size` carry the attribute value, and `flags` carries the create/replace semantics the base setxattr(3) exposes: XATTR_CREATE fails if the attribute exists, XATTR_REPLACE fails if it does not; 0 creates-or-replaces (fs/xattr.c, setxattr machinery). Note the asymmetry with [getxattrat](getxattrat.md): the get side rejects nonzero `flags`, the set side consumes them (fs/xattr.c, bodies).

## Return value and errors

0 on success; a negated error on the raw path: EINVAL (usize below VER0; bad flags combination), E2BIG (usize above PAGE_SIZE; or value size beyond the filesystem/namespace limit), EFAULT (bad pointers), EEXIST (XATTR_CREATE on an existing attribute), ENODATA (XATTR_REPLACE on a missing attribute), ENOSPC/EOPNOTSUPP (quota or filesystem support), EPERM (namespace write rules), plus lookup errors (fs/xattr.c, body).

## Flags and constants

AT_SYMLINK_NOFOLLOW (AT_FDCWD); XATTR_CREATE (1), XATTR_REPLACE (2) inside xattr_args.flags.

## Security and notes

Write rules mirror the base calls per namespace: user.* needs file ownership, security.* is LSM-gated, trusted.* needs CAP_SYS_ADMIN, system.* is kernel-managed (fs/xattr.c, xattr_permission). Setting security.* on exec'd files interacts with LSM labeling -- a classic container-escape review topic. The design interview point: value-in-struct (rather than value-as-argument) is what lets the kernel add xattr features (timestamps, handles, transactional set) without new numbers, consistent with the copy_struct_from_user extensible-ABI discipline. This page is source-limited: fs/xattr.c and include/uapi/linux/xattr.h (master, fall 2026) are the only reachable sources. Cross-reference: [getxattrat](getxattrat.md), [listxattrat](listxattrat.md), [removexattrat](removexattrat.md), [setxattr](setxattr.md), [file_setattr](file_setattr.md).

## References

- Kernel source: fs/xattr.c (SYSCALL_DEFINE6(setxattrat), torvalds/linux master, fetched 2026-10-17)
- UAPI: include/uapi/linux/xattr.h (struct xattr_args)
- asm-generic numbering: scripts/syscall.tbl line `463 common setxattrat sys_setxattrat`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
