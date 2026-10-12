# setfsuid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 122 / 138 / 151 / 138 |
| Since (kernel) | 1.2 |
| Man page | man2/setfsuid.2 (cached roff, dated 2021-03-22); man2/setfsgid.2 (full page, same cache date) |
| glibc wrapper | setfsuid(3) and setfsgid(3) both @@GLIBC_2.2.5 (nm -D, glibc 2.41), declared in sys/fsuid.h; glibc <= 2.15 returned EINVAL without issuing the call when the argument would be truncated on an old kernel (setfsuid.2, C library/kernel differences) |
| Aliases covered | setfsgid (123 / 139 / 152 / 139, SC-setfsgid); setfsuid32 (i386/arm 215, SC-setfsuid32); setfsgid32 (i386/arm 216, SC-setfsgid32) |
| Ledger ID | SC-setfsuid |

## Purpose

setfsuid() sets the filesystem user ID -- the Linux-specific credential used for permissions checking when accessing filesystem objects, normally kept equal to the effective user ID. It exists so that a program such as the NFS server can change the ID used for file access without changing the real and effective UIDs.

## Synopsis

```c
#include <sys/fsuid.h>
int setfsuid(uid_t fsuid);
int setfsgid(gid_t fsgid);   /* man2/setfsgid.2 */
```

## Arguments and behavior

Whenever the effective user ID changes through any other call, the kernel also sets the filesystem user ID to the same value; only setfsuid() can make the two diverge (setfsuid.2, DESCRIPTION). The call succeeds only if the caller is the superuser or fsuid matches the caller's real, effective, saved set-user-ID, or current filesystem user ID; setfsgid.2 states the analogous rule for the group ID. The original 16-bit calls gained setfsuid32()/setfsgid32() in Linux 2.4 (setfsuid.2, NOTES).

## Return value and errors

Both on success and on failure the call returns the previous filesystem user ID (setfsuid.2, RETURN VALUE). No error indication of any kind is returned -- the BUGS section calls this out and says EPERM should at least be returned when the caller lacks CAP_SETUID. To detect whether a call took effect, the caller must issue a further setfsuid(-1) (which always fails) and compare return values.

## Flags and constants

None. CAP_SETUID is 7 in /usr/include/linux/capability.h.

## Security and notes

The filesystem UID was added because, when the call was introduced, a process could signal any process with the same effective UID; a privileged process changing its effective UID for file checks would have exposed itself to unwanted signals. Since Linux 2.0 the signal permission rules changed, so setfsuid()/setfsgid() are nowadays unneeded and should be avoided in new applications (setfsuid.2, NOTES). setfsuid() is Linux-specific (CONFORMING TO). Cross-reference: [setuid](setuid.md), [setresuid](setresuid.md), [getuid](getuid.md).

## References

- https://man7.org/linux/man-pages/man2/setfsuid.2.html
- https://man7.org/linux/man-pages/man2/setfsgid.2.html
- /usr/include/x86_64-linux-gnu/sys/fsuid.h (both prototypes)
- /usr/include/linux/capability.h (CAP_SETUID value 7)
- worklog Task 1-a (credential family facts)
