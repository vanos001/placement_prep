# setuid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 105 / 23 / 146 / 23 |
| Since (kernel) | 1.0 |
| Man page | man2/setuid.2 (cached roff, dated 2021-03-22); man2/seteuid.2 (same cache date, full page) |
| glibc wrapper | setuid(3) and seteuid(3) both @@GLIBC_2.2.5 (nm -D, glibc 2.41); wrapper picks the 16-bit or 32-bit kernel entry transparently (setuid.2, NOTES) |
| Aliases covered | setuid32 (i386/arm 213, SC-setuid32); seteuid (libc-only, no syscall numbers -- no SC-seteuid ledger row; documented here per task brief from man2/seteuid.2) |
| Ledger ID | SC-setuid |

## Purpose

setuid() sets the user identity of the calling process: depending on privilege it changes only the effective UID or all three of real, effective, and saved set-user-ID. This page also covers seteuid(), which changes just the effective UID.

## Synopsis

```c
#include <unistd.h>
int setuid(uid_t uid);
int seteuid(uid_t euid);   /* _POSIX_C_SOURCE >= 200112L */
```

## Arguments and behavior

setuid(uid) (setuid.2, DESCRIPTION): a privileged caller -- more precisely, one holding CAP_SETUID in its user namespace -- sets the real UID, effective UID, and saved set-user-ID all to uid; afterward root privileges cannot be regained. Unprivileged, the call implements the POSIX _POSIX_SAVED_IDS behavior: only the effective UID changes, and only to the real UID or the saved set-user-ID (EPERM otherwise) -- which is why a set-user-ID-root program must use seteuid() to drop and regain root. seteuid(euid) (seteuid.2) changes only the effective UID; unprivileged callers may set it to the real, effective, or saved set-user-ID. seteuid.2 NOTES: glibc 2.0 implemented it as setreuid(-1, euid), which could move the saved ID; since glibc 2.1 it is setresuid(-1, euid, -1), which does not -- the same page's C library/kernel differences section instead calls both library functions over setreuid(2)/setregid(2), an internal conflict; rely on the saved-ID-preserving 2.1+ behavior.

## Return value and errors

0 on success, -1 with errno on failure. Errors (setuid.2, ERRORS): EAGAIN, temporary allocation failure, or (before Linux 3.1) pushing user uid's process count over RLIMIT_NPROC; EINVAL, uid invalid in this user namespace; EPERM, unprivileged and uid matches neither the real UID nor the saved set-user-ID. seteuid.2 adds EPERM when euid matches none of real/effective/saved without CAP_SETUID. Both man pages warn the call can fail even for UID 0, so the return value must be checked.

## Flags and constants

None. CAP_SETUID is capability number 7 (/usr/include/linux/capability.h).

## Security and notes

If uid differs from the old effective UID, core dumps are forbidden (setuid.2, NOTES), and under Linux setuid() also sets the filesystem UID (see [setfsuid](setfsuid.md)). The original syscall handled only 16-bit UIDs; Linux 2.4 added setuid32() (the cached arm32 table maps 23 to sys_setuid16 and 213 to sys_setuid), hidden by the glibc wrapper. At the kernel level UIDs are per-thread, but POSIX requires process-wide credentials; NPTL wrappers use a signal-based technique to change every thread (setuid.2, C library/kernel differences). Cross-reference: [setreuid](setreuid.md), [setresuid](setresuid.md), [setfsuid](setfsuid.md), [getuid](getuid.md), background in [process-control](../../sysprog/process-control.md).

## References

- https://man7.org/linux/man-pages/man2/setuid.2.html
- https://man7.org/linux/man-pages/man2/seteuid.2.html
- /usr/include/linux/capability.h (CAP_SETUID value 7)
- /usr/include/unistd.h (seteuid declared under __USE_XOPEN2K)
- /home/z/my-project/source-cache/kernel/syscall_arm.tbl (sys_setuid16 at 23, sys_setuid at 213)
- worklog Task 1-a (credential family facts)
