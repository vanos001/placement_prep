# getresuid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 118 / 165 / 148 / 165 |
| Since (kernel) | 2.2 (2.1.44 development series; man-pages 6.19 HISTORY) |
| Man page | man2/getresuid.2 (man-pages 6.19 HTML set, fetched 2026-10-17); man2/getresgid.2 is a one-line .so alias to getresuid.2 |
| glibc wrapper | getresuid(3) and getresgid(3) both @@GLIBC_2.2.5 (nm -D, glibc 2.41); wrappers transparently handle the 16/32-bit kernel entries (getresuid.2, HISTORY) |
| Aliases covered | getresgid (120 / 171 / 150 / 171, SC-getresgid); getresuid32 (i386 209, SC-getresuid32) |
| Ledger ID | SC-getresuid |

## Purpose

getresuid() returns the real, effective, and saved set-user-IDs of the calling process in the three arguments `ruid`, `euid`, and `suid`; getresgid() performs the analogous task for the group IDs (getresuid.2, DESCRIPTION). It is the read-side counterpart of [setresuid](setresuid.md): where setresuid(2) sets all three IDs at once, getresuid() reads all three at once, which a sequence of getuid(2)/geteuid(2)/getresuid-style calls could not do atomically against concurrent credential changes.

## Synopsis

```c
#define _GNU_SOURCE
#include <unistd.h>
int getresuid(uid_t *ruid, uid_t *euid, uid_t *suid);
int getresgid(gid_t *rgid, gid_t *egid, gid_t *sgid);
```

## Arguments and behavior

Three `uid_t *` (or `gid_t *`) out-parameters; the call stores one ID in each (getresuid.2, DESCRIPTION). The prototypes require `_GNU_SOURCE` (getresuid.2, SYNOPSIS). The original Linux system calls supported only 16-bit user and group IDs; Linux 2.4 added getresuid32()/getresgid32() supporting 32-bit IDs, and the glibc wrappers transparently deal with the variation across kernel versions (getresuid.2, HISTORY) -- on i386 the 32-bit twins are syscalls 209 (getresuid32) and 211 (getresgid32), see [getresgid](getresgid.md). At the kernel level credentials are per-thread attributes, but POSIX requires process-wide credentials, so the NPTL wrappers keep all threads consistent (see [setgid](setgid.md) for the same story on the group side).

## Return value and errors

0 on success; -1 on error with errno set (getresuid.2, RETURN VALUE). Errors: EFAULT, one of the three arguments specified an address outside the calling program's address space (getresuid.2, ERRORS). That is the only documented error: unlike [setresuid](setresuid.md) there is no permission check on reading credentials.

## Flags and constants

None.

## Security and notes

The call leaks the caller's own credential triple only -- there is no pid argument and no way to inspect another process, unlike the procps route via /proc/[pid]/status. The saved set-user-ID it exposes is what makes the setuid exec model reversible (see [setuid](setuid.md)); POSIX.1-2024 XSI standardized getresuid()/getresgid() (getresuid.2, STANDARDS), a 2024 addition worth citing in interviews when discussing credential APIs. Historical note: man-pages 6.19 HISTORY records "Linux 2.1.44, glibc 2.3.2, POSIX.1-2024 XSI". Cross-reference: [getuid](getuid.md), [getgid](getgid.md), [setresuid](setresuid.md), [capget](capget.md).

## References

- https://man7.org/linux/man-pages/man2/getresuid.2.html
- https://man7.org/linux/man-pages/man2/getresgid.2.html
- /usr/include/unistd.h (getresuid/getresgid prototypes, _GNU_SOURCE guard)
- worklog: glibc wrapper symbols verified with nm -D against glibc 2.41 (2026-10-17)
