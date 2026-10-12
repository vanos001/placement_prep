# setresuid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 117 / 164 / 147 / 164 |
| Since (kernel) | 2.2 |
| Man page | man2/setresuid.2 (cached roff, dated 2021-03-22); setresgid documented on the same page; man VERSIONS says "available under Linux since Linux 2.1.44" |
| glibc wrapper | setresuid(3) and setresgid(3) both @@GLIBC_2.2.5 (nm -D, glibc 2.41); glibc has provided the prototypes since version 2.3.2 (setresuid.2, NOTES) |
| Aliases covered | setresgid (119 / 170 / 149 / 170, SC-setresgid); setresuid32 (i386/arm 208, SC-setresuid32); setresgid32 (i386/arm 210, SC-setresgid32) |
| Ledger ID | SC-setresuid |

## Purpose

setresuid() sets all three user IDs of the calling process -- real, effective, and saved set-user-ID -- in a single call, with explicit -1-means-unchanged semantics. It is the nonstandard (HP-UX/BSD-derived) call that removes the ambiguity of setuid()/setreuid() about which IDs move together.

## Synopsis

```c
#define _GNU_SOURCE
#include <unistd.h>
int setresuid(uid_t ruid, uid_t euid, uid_t suid);
int setresgid(gid_t rgid, gid_t egid, gid_t sgid);
```

## Arguments and behavior

Each of the three arguments sets the corresponding ID; -1 leaves that ID unchanged (setresuid.2, DESCRIPTION). An unprivileged process may change each of the three IDs only to one of: the current real UID, the current effective UID, or the current saved set-user-ID. A privileged process -- on Linux one holding CAP_SETUID -- may set them to arbitrary values. Regardless of what changes are made, the filesystem UID is always set to the same value as the (possibly new) effective UID. setresgid() behaves identically for the group IDs (with CAP_SETGID), also forcing the filesystem GID to follow the new effective GID. The 16-bit originals were joined by setresuid32()/setresgid32() in Linux 2.4; the *32 numbers exist only on i386 and arm32 (hub; setresuid.2, NOTES).

## Return value and errors

0 on success, -1 with errno on failure. Errors (setresuid.2, ERRORS): EAGAIN, temporary allocation failure, or (before Linux 3.1) ruid would push user ruid's process count over RLIMIT_NPROC; EINVAL, a target ID is invalid in this user namespace; EPERM, unprivileged and the requested values are not permitted (CAP_SETUID / CAP_SETGID required).

## Flags and constants

None. CAP_SETUID is 7 and CAP_SETGID is 6 in /usr/include/linux/capability.h.

## Security and notes

The man page repeats the family-wide warning: the call can fail even for a UID 0 caller, so the return value must be checked. The Since value in the field table is the hub's 2.2; the cached man page's VERSIONS section says 2.1.44 -- a hub/man divergence like the ones recorded in worklog 1-a. _GNU_SOURCE is required for the prototypes per the cached SYNOPSIS. Cross-reference: [setuid](setuid.md), [setreuid](setreuid.md), [setfsuid](setfsuid.md).

## References

- https://man7.org/linux/man-pages/man2/setresuid.2.html
- /usr/include/linux/capability.h (CAP_SETGID 6, CAP_SETUID 7)
- /usr/include/unistd.h (setresuid/setresgid prototypes)
- worklog Task 1-a (credential family facts)
