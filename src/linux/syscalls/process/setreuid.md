# setreuid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 113 / 70 / 145 / 70 |
| Since (kernel) | 1.0 |
| Man page | man2/setreuid.2 (cached roff, dated 2021-03-22); setregid documented on the same page |
| glibc wrapper | setreuid(3) and setregid(3) both @@GLIBC_2.2.5 (nm -D, glibc 2.41); declared in unistd.h under __USE_MISC or __USE_XOPEN_EXTENDED; wrappers handle the 16/32-bit kernel split |
| Aliases covered | setregid (114 / 71 / 143 / 71, SC-setregid); setreuid32 (i386/arm 203, SC-setreuid32); setregid32 (i386/arm 204, SC-setregid32) |
| Ledger ID | SC-setreuid |

## Purpose

setreuid() sets the real and/or effective user ID of the calling process in one call; setregid() does the same for group IDs. It is the 4.2BSD-origin call for swapping the two IDs without touching the saved set-user-ID.

## Synopsis

```c
#include <unistd.h>
int setreuid(uid_t ruid, uid_t euid);
int setregid(gid_t rgid, gid_t egid);
```

## Arguments and behavior

A value of -1 for either argument leaves that ID unchanged (setreuid.2, DESCRIPTION). Unprivileged processes may set the effective user ID to the real user ID, the effective user ID, or the saved set-user-ID, and the real user ID only to the real or effective user ID. If the real user ID is changed, or the effective user ID is set to a value different from the previous real user ID, the saved set-user-ID is set to the new effective user ID. setregid() mirrors all of this with "group". Setting the effective ID to the saved ID has been possible since Linux 1.1.37 (setregid 1.1.38; setreuid.2, NOTES). The 16-bit originals gained 32-bit twins setreuid32/setregid32 in Linux 2.4; the *32 rows exist only on i386 and arm32 (hub; setreuid.2, NOTES).

## Return value and errors

0 on success, -1 with errno on failure. Errors (setreuid.2, ERRORS): EAGAIN, temporary allocation failure, or (before Linux 3.1) ruid would push user ruid's process count over RLIMIT_NPROC; EINVAL, a target ID is invalid in this user namespace; EPERM, unprivileged and the change is none of (i) swapping effective with real, (ii) setting one to the value of the other, or (iii) setting the effective ID to the saved ID -- the required capability is CAP_SETUID for setreuid() and CAP_SETGID for setregid().

## Flags and constants

None. CAP_SETUID is 7 and CAP_SETGID is 6 in /usr/include/linux/capability.h.

## Security and notes

POSIX.1 does not specify all the ID changes Linux allows an unprivileged process here, nor the effect on the saved IDs (setreuid.2, NOTES); details vary across implementations. As with the whole set*uid family, kernel-level IDs are per-thread and the NPTL wrappers broadcast changes to all threads (setreuid.2, C library/kernel differences). glibc's seteuid() built on this call before 2.1 (see [setuid](setuid.md)). Cross-reference: [setuid](setuid.md), [setresuid](setresuid.md), [getuid](getuid.md).

## References

- https://man7.org/linux/man-pages/man2/setreuid.2.html
- /usr/include/linux/capability.h (CAP_SETGID 6, CAP_SETUID 7)
- /usr/include/unistd.h (setreuid/setregid under __USE_MISC || __USE_XOPEN_EXTENDED)
- worklog Task 1-a (credential family facts)
