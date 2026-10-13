# getgroups(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 115 / 80 / 158 / 80 |
| Since (kernel) | 1.0 |
| Man page | man2/getgroups.2 (cached roff, dated 2021-03-22; setgroups documented on the same page); man2/setgroups.2 is a one-line .so alias to getgroups.2 |
| glibc wrapper | getgroups(3) (@@GLIBC_2.2.5) declared in unistd.h; setgroups(3) (@@GLIBC_2.2.5) declared in grp.h under _DEFAULT_SOURCE (since glibc 2.19) or _BSD_SOURCE before that (getgroups.2, SYNOPSIS); both handle the 16/32-bit kernel split |
| Aliases covered | setgroups (116 / 81 / 159 / 81, SC-setgroups); getgroups32 (i386 205, SC-getgroups32); setgroups32 (i386 206, SC-setgroups32) |
| Ledger ID | SC-getgroups |

## Purpose

getgroups() returns the calling process's supplementary group IDs; setgroups() replaces them. Supplementary groups are the third group credential besides real and effective GID: the kernel checks all of them against a file's group bits.

## Synopsis

```c
#include <unistd.h>
int getgroups(int size, gid_t list[]);
#include <grp.h>
int setgroups(size_t size, const gid_t *list);
```

## Arguments and behavior

getgroups(size, list): size is the capacity of list; if the process belongs to more than size supplementary groups the call fails. It is unspecified whether the effective GID appears in the returned list, so an application should consult getegid(2) as well (getgroups.2, DESCRIPTION). With size 0, list is not touched and the number of supplementary groups is returned -- the usual sizing idiom. setgroups(size, list) replaces the whole set; setgroups(0, NULL) drops all supplementary groups. A process may hold up to NGROUPS_MAX supplementary IDs besides the effective GID; the man page records 32 before Linux 2.6.4 and 65536 since, and the kernel UAPI header on this host agrees (/usr/include/linux/limits.h: 65536; glibc's bits/posix1_lim.h still carries a fallback NGROUPS_MAX 8). Since 2.6.4 the maximum is also exposed read-only at /proc/sys/kernel/ngroups_max (getgroups.2, NOTES). The 16-bit originals gained getgroups32()/setgroups32() in Linux 2.4.

## Return value and errors

getgroups() returns the number of supplementary group IDs, setgroups() returns 0; on error -1 with errno (getgroups.2, RETURN VALUE). Errors: EFAULT, invalid list address; EINVAL (getgroups), size smaller than the number of groups but not zero; EINVAL (setgroups), size exceeds NGROUPS_MAX; ENOMEM (setgroups); EPERM (setgroups), caller lacks CAP_SETGID in its user namespace, or since Linux 3.19 setgroups() is denied in this user namespace via /proc/[pid]/setgroups (getgroups.2, ERRORS).

## Flags and constants

NGROUPS_MAX: 65536 (/usr/include/linux/limits.h); CAP_SETGID is 6 (/usr/include/linux/capability.h).

## Security and notes

The set is inherited from the parent and preserved across execve(2) (getgroups.2, NOTES). At the kernel level the IDs are per-thread; NPTL wrappers broadcast changes to all threads (getgroups.2, C library/kernel differences). setgroups() requires privilege and is therefore not covered by POSIX.1 (CONFORMING TO). The companion library function initgroups(3) (cached man3/initgroups.3) populates the supplementary list from the user database. Cross-reference: [getgid](getgid.md), [setreuid](setreuid.md), [execve](execve.md).

## References

- https://man7.org/linux/man-pages/man2/getgroups.2.html
- /usr/include/linux/limits.h (NGROUPS_MAX 65536)
- /usr/include/x86_64-linux-gnu/bits/posix1_lim.h (NGROUPS_MAX 8 fallback)
- /usr/include/linux/capability.h (CAP_SETGID value 6)
- man3/initgroups.3 (cached)
