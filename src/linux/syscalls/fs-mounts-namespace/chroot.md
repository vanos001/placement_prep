# chroot(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 161 / i386 61 / arm64-generic 51 / arm32 61 |
| Since (kernel) | 1.0 (hub) |
| Man page | man2/chroot.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Yes; `chroot()` in `<unistd.h>`; glibc gates (since 2.2.2): `_XOPEN_SOURCE && !(_POSIX_C_SOURCE >= 200112L)` or `_DEFAULT_SOURCE` (glibc >= 2.20) or `_BSD_SOURCE` (glibc <= 2.19) |
| Aliases covered | none (post-6.17-era `fchroot`, x64/generic 472, is a separate hub row, not covered here) |
| Ledger ID | SC-chroot |

## Purpose

`chroot()` changes the root directory of the calling process to `path`.
Pathnames beginning with `/` are then resolved from that directory, and the new
root is inherited by all children. The man page is explicit that this call
"changes an ingredient in the pathname resolution process and does nothing
else": it is not a security mechanism, not a sandbox, and does not restrict
filesystem system calls. For a real root swap, including switching the mount,
use [pivot_root.md](pivot_root.md).

## Synopsis

    #include <unistd.h>
    int chroot(const char *path);

## Arguments and behavior

| Argument | Meaning |
|---|---|
| `path` | Directory that becomes the new root for `/`-prefixed lookups |

The call does not change the current working directory, so after the call `.`
can lie outside the tree rooted at the new `/`; the man page gives the classic
escape `mkdir foo; chroot foo; cd ..`. It also does not close open file
descriptors, which keep working and may point outside the chroot tree. Another
documented escape: `chdir(2)` into a directory that is later moved out of the
chroot, then open a relative path such as `../../../etc/passwd`; the man page
warns that daemons accepting a "chroot directory" parameter must ensure
directories are never moved out of it.

## Return value and errors

Returns 0 on success, -1 on error with `errno` set. Errors per the man page:
`EACCES` (search permission denied on a path prefix component), `EFAULT`,
`EIO`, `ELOOP`, `ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `ENOTDIR`, and `EPERM`
(caller has insufficient privilege).

## Security and notes

Only a privileged process may call `chroot()`: Linux requires the
`CAP_SYS_CHROOT` capability in the caller's user namespace (man page; kernel
`fs/open.c` `SYSCALL_DEFINE1(chroot)` enforces
`ns_capable(current_user_ns(), CAP_SYS_CHROOT)` -- fetched master copy,
`source-cache/fetched/master-fs-open.c` line 607). Because unprivileged users
can create user namespaces, `CAP_SYS_CHROOT` in a non-initial user namespace is
attainable, which is why the man page's "not a sandbox" warning matters.
Children inherit the root via `fork(2)` and keep it across `execve(2)`. The
`/proc/[pid]/root` magic link exposes a process's root directory (proc(5)).
FreeBSD offers the stronger `jail()`. Related calls in this directory:
[chdir.md](chdir.md), [pivot_root.md](pivot_root.md), and the hub rows for
`fchroot` (472, post-6.17 era) in [overview.md](overview.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/chroot.2`
- Online: https://man7.org/linux/man-pages/man2/chroot.2.html
- Kernel source: `fs/open.c` (torvalds/linux master,
  `source-cache/fetched/master-fs-open.c`)
- Conformance per man page: SVr4, 4.4BSD, SUSv2 (marked LEGACY); not in POSIX.1-2001
