# pidfd_getfd(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 438 / 438 / 438 / 438 |
| Since (kernel) | 5.6 (pidfd_getfd.2 VERSIONS) |
| Man page | man2/pidfd_getfd.2 (cached roff, dated 2021-03-22); no aliases |
| glibc wrapper | pidfd_getfd(3), symbol version GLIBC_2.36 (nm -D on installed glibc 2.41; the cached man page still carries the older "glibc provides no wrapper" note) |
| Aliases covered | none |
| Ledger ID | SC-pidfd_getfd |

## Purpose

pidfd_getfd() duplicates a file descriptor held by another process into the caller, given a pidfd for that process. It is the no-cooperation sibling of SCM_RIGHTS fd passing over unix sockets: no socket connection and no consent from the target are needed, only a ptrace-level permission check (pidfd_getfd.2, NOTES). Typical uses: debuggers, service managers, and sandbox monitors inspecting or inheriting foreign descriptors.

## Synopsis

```c
#include <sys/syscall.h>
int syscall(SYS_pidfd_getfd, int pidfd, int targetfd, unsigned int flags);
```

## Arguments and behavior

pidfd is a PID file descriptor (from pidfd_open(2) or clone3(2) with CLONE_PIDFD) referring to the target process. targetfd is the descriptor number in the target's file table. flags is reserved and must be 0. The new descriptor refers to the same open file description as the target's, so file status flags and offset are shared and operations (for example bind(2) on a socket) work identically (pidfd_getfd.2, DESCRIPTION). The descriptor returned to the caller has close-on-exec set. Permission is governed by a PTRACE_MODE_ATTACH_REALCREDS ptrace access-mode check against the target (see ptrace.2).

## Return value and errors

Success: a nonnegative file descriptor in the caller. Failure: -1 with errno (pidfd_getfd.2):

| Error | Meaning |
|---|---|
| EBADF | pidfd is not a valid pidfd; or targetfd is not an open descriptor in the target |
| EINVAL | flags is not 0 |
| EMFILE / ENFILE | per-process / system-wide open-file limit reached |
| EPERM | Caller lacks PTRACE_MODE_ATTACH_REALCREDS permission over the target |
| ESRCH | Target process has terminated and been waited on |

## Flags and constants

None accepted: flags must be 0 (pidfd_getfd.2). Related: PIDFD_NONBLOCK on the pidfd itself (see [pidfd_open](pidfd_open.md)).

## Security and notes

The PTRACE_MODE_ATTACH_REALCREDS check means same-UID targets, Yama policy (PR_SET_PTRACER), or CAP_SYS_PTRACE determine success, mirroring ptrace(2) attach rules; the ability to grab fds without target cooperation is exactly why the check is attach-level rather than read-level (pidfd_getfd.2, NOTES; ptrace.2, access-mode checking). SCM_RIGHTS differs additionally in requiring an established socket connection and active cooperation of the sender. Cross-reference: [pidfd_open](pidfd_open.md), [clone](clone.md), [ptrace](ptrace.md).

## References

- https://man7.org/linux/man-pages/man2/pidfd_getfd.2.html
- kernel/pid.c (source files named in worklog 1-a for the pidfd family)
- /usr/include/linux/pidfd.h
