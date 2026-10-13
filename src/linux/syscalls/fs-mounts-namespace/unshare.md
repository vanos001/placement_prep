# unshare(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 272 / i386 310 / arm64-generic 97 / arm32 337 |
| Since (kernel) | 2.6.16 (man VERSIONS; hub 2.6.16) |
| Man page | man2/unshare.2 (cached, 2021-08-27) |
| glibc wrapper | Yes; `<sched.h>`, needs `_GNU_SOURCE` |
| Aliases covered | none |
| Ledger ID | SC-unshare |

## Purpose

`unshare()` disassociates parts of the calling process's execution context
that are shared with other processes or threads: file descriptor table,
filesystem attributes (root, cwd, umask), System V semadj list, or any of
the namespaces. Where fork/clone share or clone context at creation time,
unshare detaches it afterwards -- the syscall behind the `unshare(1)`
command and the "clone-then-detach" container bootstrap pattern.

## Synopsis

    #define _GNU_SOURCE
    #include <sched.h>
    int unshare(int flags);

## Arguments and behavior

`flags` is an OR of zero or more of the table below. `flags == 0` is a
no-op. `CLONE_FILES` and `CLONE_FS` reverse the matching clone flags;
`CLONE_SYSVSEM` (2.6.26) detaches the semadj list, applying pending
adjustments when this is the last reference. The `CLONE_NEW*` flags create
a fresh namespace and move (or, for PID and time namespaces, enroll future
children into) it. Composition rules from the man page: `CLONE_NEWIPC`
implies `CLONE_SYSVSEM`; `CLONE_NEWNS` implies `CLONE_FS`; `CLONE_NEWPID`
implies `CLONE_THREAD`; `CLONE_NEWUSER` requires a non-threaded caller and
implies `CLONE_THREAD` and, since 3.9, `CLONE_FS`. `CLONE_THREAD`,
`CLONE_SIGHAND` and `CLONE_VM` are accepted (with no effect) only for a
single-threaded caller and fail with `EINVAL` otherwise. `CLONE_NEWUSER`
additionally requires that the caller's euid/egid have a mapping in the
current user namespace and, since 3.9, fails in a chroot environment whose
root differs from the mount namespace root; success grants a full
capability set in the new user namespace.

## Return value and errors

Returns 0 on success, -1 on error: `EINVAL` (invalid bit; multithreaded
`CLONE_THREAD`/`SIGHAND`/`VM`; kernel built without the matching
`CONFIG_*_NS` option; repeated `CLONE_NEWPID` unshare), `ENOMEM`,
`ENOSPC` (PID-namespace nesting depth since 3.7; user-namespace nesting
and `/proc/sys/user` limits since 4.9, reported `EUSERS` from 3.11 to
4.8), `EPERM` (missing `CAP_SYS_ADMIN`; unmapped euid/egid for
`CLONE_NEWUSER`; chroot restriction since 3.9).

## Flags and constants

| Flag | Effect | Since |
|---|---|---|
| `CLONE_FILES` | Private file descriptor table | header (clone flag) |
| `CLONE_FS` | Private root/cwd/umask | header |
| `CLONE_SYSVSEM` | Private semadj list | 2.6.26 |
| `CLONE_NEWNS` | New mount namespace (`CAP_SYS_ADMIN`) | header (clone flag) |
| `CLONE_NEWIPC` | New IPC namespace (`CAP_SYS_ADMIN`) | 2.6.19 |
| `CLONE_NEWUTS` | New UTS namespace (`CAP_SYS_ADMIN`) | 2.6.19 |
| `CLONE_NEWNET` | New network namespace (`CAP_SYS_ADMIN`) | 2.6.24 |
| `CLONE_NEWPID` | New PID namespace for children (`CAP_SYS_ADMIN`) | 3.8 |
| `CLONE_NEWUSER` | New user namespace, full capabilities there | 3.8 |
| `CLONE_NEWCGROUP` | New cgroup namespace (`CAP_SYS_ADMIN`) | 4.6 |
| `CLONE_NEWTIME` | New time namespace for children (`CAP_SYS_ADMIN`) | 5.6 |

## Security and notes

Unprivileged `CLONE_NEWUSER` is the gateway to user-namespace container
features and, correspondingly, to a long tail of kernel CVEs -- many
distributions gate it via `/proc/sys/kernel/unprivileged_userns_clone`-style
sysctls (distribution patches, not mainline). Not every clone-shareable
attribute can be unshared: as of the cached page there are no flags to
reverse already-shared `CLONE_SIGHAND`, `CLONE_THREAD` or `CLONE_VM` for a
multithreaded caller (man NOTES). Joining existing namespaces is setns
([setns.md](setns.md)); mount namespaces pair with
[mount.md](mount.md) and [pivot_root.md](pivot_root.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/unshare.2`
- Online: https://man7.org/linux/man-pages/man2/unshare.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (272)
- Constants: `/usr/include/linux/sched.h` (CLONE_NEW*), `<bits/sched.h>`
