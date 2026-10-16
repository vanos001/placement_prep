# fchroot(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 472 / 472 / 472 / 472 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (post-6.13 addition to fs/open.c) |
| Man page | none (no man2/fchroot.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; the path-based base call is [chroot](chroot.md) |
| Ledger ID | SC-fchroot |

## Purpose

fchroot() changes the calling process's root directory to the directory referenced by an open file descriptor, the fd-based analogue of [chroot](chroot.md) -- the same relationship [fchdir](chdir.md) has to chdir(2) (fs/open.c, SYSCALL_DEFINE2(fchroot, int, fd, unsigned int, flags)). Working through a descriptor removes the path-lookup race: the target directory can be opened under restrictive sharing (O_PATH, O_NOFOLLOW, inside an open_tree(2)-prepared bind) and then pinned, instead of trusting a pathname that another mount namespace could rewrite between check and use.

## Synopsis

```c
/* no glibc declaration; called directly */
long syscall(SYS_fchroot, int fd, unsigned int flags);
```

## Arguments and behavior

`fd` is a file descriptor referring to a directory; `flags` must be 0 -- any other value fails with EINVAL (fs/open.c, body). The kernel validates the descriptor (EBADF if empty), requires the target to be a directory (ENOTDIR), and applies the same permission gates as chroot(2): file_permission(MAY_EXEC | MAY_CHDIR) on the descriptor, then ns_capable(CAP_SYS_CHROOT) in the caller's user namespace -- unprivileged callers get EPERM (fs/open.c, body). A special reserved descriptor value, FD_FAILFS_ROOT, requests the failfs root instead of an arbitrary directory; the source guards it with extra checks: without CAP_SYS_CHROOT the caller must have no_new_privs set, must own its fs_struct exclusively (`fs->users == 1`, because a shared fs_struct would let a sibling exec setuid binaries past the check), and must not already be chrooted, since moving the root to failfs lifts the old root's ".." barrier (fs/open.c, body). LSM hooks run via security_path_chroot exactly as for chroot(2).

## Return value and errors

0 on success; a negated error on the raw path: EINVAL (flags nonzero; or the shared-fs_struct failfs condition), EPERM (missing CAP_SYS_CHROOT; failfs without no_new_privs; failfs while already chrooted), EBADF (bad descriptor), ENOTDIR (descriptor is not a directory), EACCES-equivalent failures from file_permission, plus LSM-denied results from security_path_chroot (fs/open.c, body).

## Flags and constants

None (`flags` reserved, must be 0). FD_FAILFS_ROOT is a kernel-private reserved descriptor value, not a uapi constant.

## Security and notes

The CAP_SYS_CHROOT gate matches chroot(2), and the man-page-era criticism applies unchanged: chroot alone is not a sandbox (classic chroot(2) escape via fchdir on an open descriptor outside the tree), which is why containers pair it with pivot_root(2) ([pivot_root](pivot_root.md)) and mount namespaces ([setns](setns.md)). The interesting new part is the failfs path's interplay with no_new_privs and fs_struct sharing -- read that as the kernel encoding "root change must not amplify privilege" as explicit checks rather than trusting capability bits alone. This page is source-limited: behavior above is quoted from fs/open.c (master, fall 2026); no man page exists yet to reconcile against. Cross-reference: [chroot](chroot.md), [chdir](chdir.md), [pivot_root](pivot_root.md), [setns](setns.md), [unshare](unshare.md).

## References

- Kernel source: fs/open.c (SYSCALL_DEFINE2(fchroot), torvalds/linux master, fetched 2026-10-17)
- asm-generic numbering: scripts/syscall.tbl line `472 common fchroot sys_fchroot`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
