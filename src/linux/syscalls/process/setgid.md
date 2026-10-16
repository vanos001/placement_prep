# setgid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 106 / 46 / 144 / 46 |
| Since (kernel) | 1.0 |
| Man page | man2/setgid.2 (man-pages 6.19 HTML set, fetched 2026-10-17); man2/setgid32.2 is a one-line .so alias |
| glibc wrapper | setgid(3) W @@GLIBC_2.2.5 (nm -D, glibc 2.41); wrapper handles the 16/32-bit kernel entries (setgid.2, HISTORY) |
| Aliases covered | setgid32 (i386 214, SC-setgid32) |
| Ledger ID | SC-setgid |

## Purpose

setgid() sets the effective group ID of the calling process; if the caller is privileged -- precisely, holds CAP_SETGID in its user namespace -- the real GID and the saved set-group-ID are also set (setgid.2, DESCRIPTION). It is the group-side counterpart of [setuid](setuid.md) and, under Linux, implements the POSIX `_POSIX_SAVED_IDS` semantics: a set-group-ID program that is not set-user-ID-root can drop all of its group privileges, do unprivileged work, and then re-engage the original effective GID securely (setgid.2, DESCRIPTION).

## Synopsis

```c
#include <unistd.h>
int setgid(gid_t gid);
```

## Arguments and behavior

One argument, `gid`, the new group ID. Unprivileged callers may set the effective GID only to the real GID or the saved set-group-ID; privileged callers set all three (real, effective, saved) to `gid` (setgid.2, DESCRIPTION). The original Linux system call supported only 16-bit group IDs; Linux 2.4 added setgid32() (i386 214) for 32-bit IDs, with the glibc wrapper transparently dealing with the variation (setgid.2, HISTORY). Note the asymmetry with [setuid](setuid.md): an unprivileged setuid() can only drop privileges, while setgid() can switch between real and saved GID freely because group privileges carry no setgid-root special case.

## Return value and errors

0 on success; -1 on error with errno set (setgid.2, RETURN VALUE). Errors: EINVAL, the group ID specified in `gid` is not valid in this user namespace; EPERM, the calling process is unprivileged (no CAP_SETGID in its user namespace) and `gid` does not match the real GID or the saved set-group-ID (setgid.2, ERRORS).

## Flags and constants

None.

## Security and notes

At the kernel level group IDs are per-thread attributes, but POSIX requires process-wide credentials, so NPTL wrapper functions -- including setgid(3) -- use a signal-based technique to change credentials in every thread of the process (setgid.2, VERSIONS, C library/kernel differences; details in nptl(7)). Capability check: CAP_SETGID (value 6) scoped to the caller's user namespace (setgid.2, DESCRIPTION); background in [linux-capabilities](../../kernel/security/linux-capabilities.md). The per-thread-vs-process-wide gap is a classic interview trap: a concurrent setgid() from another thread is serialized by the wrappers, but raw syscall(2) invocation bypasses that and changes only the calling thread's kernel-side attribute. Standards: POSIX.1-2024 (setgid.2, STANDARDS). Cross-reference: [setuid](setuid.md), [getgid](getgid.md), [setfsuid](setfsuid.md), [setresuid](setresuid.md), [getresuid](getresuid.md).

## References

- https://man7.org/linux/man-pages/man2/setgid.2.html
- man-pages syscalls(2) version table (setgid32 in 2.4)
- worklog: wrapper symbol setgid W @@GLIBC_2.2.5 verified with nm -D against glibc 2.41 (2026-10-17)
