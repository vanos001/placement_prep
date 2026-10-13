# getgid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 104 / 47 / 176 / 47 |
| Since (kernel) | 1.0 |
| Man page | man2/getgid.2 (cached roff, dated 2021-03-22); man2/getegid.2 is a one-line .so alias to getgid.2 |
| glibc wrapper | getgid(3) and getegid(3) both @@GLIBC_2.2.5 (nm -D, glibc 2.41); wrappers transparently handle the 16/32-bit kernel entries (getgid.2, NOTES) |
| Aliases covered | getegid (108 / 50 / 177 / 50, SC-getegid); getgid32 (i386 200, SC-getgid32); getegid32 (i386 202, SC-getegid32) |
| Ledger ID | SC-getgid |

## Purpose

getgid() returns the real group ID and getegid() the effective group ID of the calling process -- the group counterparts of getuid()/geteuid(). The effective GID is one of the credentials checked against a file's group permission bits.

## Synopsis

```c
#include <unistd.h>
gid_t getgid(void);
gid_t getegid(void);
```

## Arguments and behavior

No arguments. getgid() returns the real group ID; getegid() returns the effective group ID (getgid.2, DESCRIPTION). The original Linux system calls supported only 16-bit group IDs; Linux 2.4 added getgid32()/getegid32(), and the glibc wrappers deal with the variation across kernel versions (getgid.2, NOTES). On Alpha a single getxgid() call returns the pair of real and effective GIDs, with the glibc wrappers hiding this (getgid.2, NOTES).

## Return value and errors

The requested group ID. These functions are always successful and never modify errno (getgid.2, ERRORS).

## Flags and constants

None.

## Security and notes

The supplementary group list is a separate credential with its own calls -- see [getgroups](getgroups.md). Changing the real/effective GIDs is done by setgid(2)/setregid(2)/setresgid(2); setgid(2) and the *32 rows live on the hub's setgid.md page (file not yet written), setregid on [setreuid](setreuid.md). As with all credentials, kernel-level IDs are per-thread and libc wrappers enforce the POSIX process-wide view. Cross-reference: [getuid](getuid.md), [getgroups](getgroups.md), [setreuid](setreuid.md).

## References

- https://man7.org/linux/man-pages/man2/getgid.2.html
- https://man7.org/linux/man-pages/man2/getegid.2.html
- /usr/include/unistd.h (getgid/getegid prototypes)
- worklog Task 1-a (credential family facts)
