# getuid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 102 / 24 / 174 / 24 |
| Since (kernel) | 1.0 |
| Man page | man2/getuid.2 (cached roff, dated 2021-03-22); man2/geteuid.2 is a one-line .so alias to getuid.2 |
| glibc wrapper | getuid(3) and geteuid(3) both @@GLIBC_2.2.5 (nm -D, glibc 2.41); wrappers transparently handle the 16/32-bit kernel entries (getuid.2, NOTES) |
| Aliases covered | geteuid (107 / 49 / 175 / 49, SC-geteuid); getuid32 (i386 199, SC-getuid32); geteuid32 (i386 201, SC-geteuid32) |
| Ledger ID | SC-getuid |

## Purpose

getuid() returns the real user ID and geteuid() the effective user ID of the calling process. These are the read side of the setuid() family: the effective UID drives most permission checks, the real UID identifies who launched the process.

## Synopsis

```c
#include <unistd.h>
uid_t getuid(void);
uid_t geteuid(void);
```

## Arguments and behavior

No arguments. getuid() returns the real user ID; geteuid() returns the effective user ID (getuid.2, DESCRIPTION). The original Linux system calls supported only 16-bit user IDs; Linux 2.4 added getuid32()/geteuid32(), and the glibc wrappers deal with the variation across kernel versions (getuid.2, NOTES). On Alpha there is no pair of calls -- a single getxuid() returns the real and effective UIDs together, and the glibc wrappers hide that too (getuid.2, NOTES).

## Return value and errors

The requested user ID. These functions are always successful and never modify errno (getuid.2, ERRORS).

## Flags and constants

None.

## Security and notes

Historical note from getuid.2 (NOTES, History): in UNIX V6 getuid() returned (euid << 8) + uid packed into one value; UNIX V7 introduced the separate getuid()/geteuid() calls. On Linux the IDs are per-thread attributes at the kernel level, but POSIX requires process-wide credentials, so libc wrappers keep them consistent (see [setuid](setuid.md)). The companion group-ID calls are on [getgid](getgid.md); the three-at-once variant is getresuid(2) (see the hub row getresuid.md, page not yet written). Cross-reference: [setuid](setuid.md), [getgid](getgid.md).

## References

- https://man7.org/linux/man-pages/man2/getuid.2.html
- https://man7.org/linux/man-pages/man2/geteuid.2.html
- /usr/include/unistd.h (getuid/geteuid prototypes)
- worklog Task 1-a (credential family facts)
