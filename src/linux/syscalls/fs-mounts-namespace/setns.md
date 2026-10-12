# setns(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 308 / i386 346 / arm64-generic 268 / arm32 375 |
| Since (kernel) | 3.0 (man VERSIONS; hub 3.0) |
| Man page | man2/setns.2 (cached, 2021-08-27) |
| glibc wrapper | Yes; `<sched.h>`, needs `_GNU_SOURCE` |
| Aliases covered | none |
| Ledger ID | SC-setns |

## Purpose

`setns()` moves the calling thread into an existing namespace. The classic
form takes a file descriptor referring to a `/proc/[pid]/ns/` symlink (or a
bind mount of one) and reassociates one namespace membership; since 5.8 the
fd may instead be a pidfd, in which case the caller joins several of the
target thread's namespaces atomically. It is the join-side complement of
[unshare.md](unshare.md) and the mechanism `nsenter(1)` is built on.

## Synopsis

    #define _GNU_SOURCE
    #include <sched.h>
    int setns(int fd, int nstype);

## Arguments and behavior

With an `/proc/[pid]/ns/` fd, `nstype` is 0 (any type) or one of the
`CLONE_NEW*` constants, used to verify the fd's namespace type (table
below). A nonzero `nstype` matters when the fd was passed from another
process and its type is unknown. With a pidfd (5.8), `nstype` is instead
an OR of the constants naming which of the target's namespaces to join
(for example `CLONE_NEWUSER`, `CLONE_NEWNET`, `CLONE_NEWUTS`); 0 is
invalid here. Type-specific capability rules are folded into the table;
extra user-namespace rules: joining grants a full capability set in the
target, a multithreaded process cannot change user namespace, rejoining
the current one is forbidden, and `CLONE_FS` sharing blocks the join.

## Return value and errors

Returns 0 on success, -1 on error: `EBADF`, `EINVAL` (type mismatch between
`fd` and `nstype`; joining an ancestor PID namespace; rejoining the current
user namespace; multithreaded or `CLONE_FS`-sharing caller; invalid pidfd
`nstype`), `ENOMEM`, `EPERM` (missing capability), `ESRCH` (pidfd target
already reaped).

## Flags and constants

"both-userns" below means `CAP_SYS_ADMIN` in the caller's own user namespace
and in the user namespace owning the target (man setns.2):

| Constant | Namespace | setns use since | Rules |
|---|---|---|---|
| `CLONE_NEWIPC` | SysV IPC / POSIX message queues | 3.0 | both-userns |
| `CLONE_NEWNET` | Network devices, stacks, ports | 3.0 | both-userns |
| `CLONE_NEWNS` | Mount namespace | 3.8 | both-userns plus `CAP_SYS_CHROOT`; `CLONE_FS` sharing forbidden |
| `CLONE_NEWPID` | PID numbering | 3.8 | both-userns; descendants only; moves only future children |
| `CLONE_NEWUSER` | User/UID mappings | 3.8 | `CAP_SYS_ADMIN` in target (descendants only); grants full caps there |
| `CLONE_NEWUTS` | Hostname, NIS domain | 3.0 | both-userns |
| `CLONE_NEWCGROUP` | cgroup membership view | 4.6 | both-userns; cgroup memberships unchanged |
| `CLONE_NEWTIME` | CLOCK_MONOTONIC/BOOTTIME offsets | 5.8 | both-userns |

## Security and notes

Namespace fd usage and `NS_GET_*` ioctls are described in
`namespace.h`-adjacent man pages not cached here; the capability rules above
are quoted from the cached page. Unlike fork-time namespace creation via
clone flags ([unshare.md](unshare.md), [clone.md](../process/clone.md)),
setns moves only the calling thread, so a multithreaded process can join
everything except a user namespace. Container runtimes combine setns with
[pivot_root.md](pivot_root.md) to build a fresh root.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/setns.2`
- Online: https://man7.org/linux/man-pages/man2/setns.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (308)
- Constants: `/usr/include/linux/sched.h` (CLONE_NEW*), `<bits/sched.h>`
