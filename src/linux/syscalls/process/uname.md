# uname(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 63 / 122 / 160 / 122 |
| Since (kernel) | 1.0 |
| Man page | man2/uname.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | uname(3) @@GLIBC_2.2.5 (nm -D, glibc 2.41); wrapper hides the oldolduname -> olduname -> newuname progression and always calls the newest version the kernel provides (uname.2, C library/kernel differences) |
| Aliases covered | none |
| Ledger ID | SC-uname |

## Purpose

uname() returns kernel and system identification -- sysname, nodename, release, version, machine, and the GNU domainname -- in a struct utsname; the kernel reads it from the calling process's UTS namespace.

## Synopsis

```c
#include <sys/utsname.h>
int uname(struct utsname *buf);
```

## Arguments and behavior

buf points to a struct utsname filled with NUL-terminated strings (uname.2, DESCRIPTION): the man page shows sysname, nodename, release, version, machine, plus domainname under _GNU_SOURCE. Field lengths are unspecified -- the page warns against constants like SYS_NMLN and says to use sizeof; glibc on this host uses _UTSNAME_LENGTH 65 for every member (bits/utsname.h), and the domainname member is named domainname only under __USE_GNU, otherwise __domainname (sys/utsname.h). Four fields are genuinely known to the kernel; nodename and domainname are not -- the kernel "has to be told what to answer", via sethostname(2) and setdomainname(2) (uname.2, NOTES). On Linux the nodename is the string set by sethostname(2) -- the page notes no standard forces that equality, but it holds on Linux. The domainname member is a GNU extension carrying the NIS/YP domain name, a legacy network-service concept POSIX does not define; it survives in the structure only for that purpose and likewise must be set with setdomainname(2). UTS namespace interaction: the data lives in the process's UTS namespace, so processes in different uts_namespaces(7) see different answers; clone(2)/unshare(2) create such namespaces (SEE ALSO). The same information is partly exposed at /proc/sys/kernel/{ostype,hostname,osrelease,version,domainname} (uname.2, NOTES).

## Return value and errors

0 on success, -1 with errno on failure (uname.2, RETURN VALUE). Errors: EFAULT, buf is not valid (uname.2, ERRORS).

## Flags and constants

None. _GNU_SOURCE gates the domainname member in glibc's header.

## Security and notes

Over time the struct grew: the three kernel-side versions used lengths 9, 65, and 65 plus domainname (uname.2, C library/kernel differences). There is no uname() in 4.3BSD (CONFORMING TO). The release/version fields are the supported way to gate kernel-version-dependent code. Cross-reference: none of the sibling pages document sethostname(2)/setdomainname(2) yet, so they remain plain-text references on this page.

## References

- https://man7.org/linux/man-pages/man2/uname.2.html
- /usr/include/x86_64-linux-gnu/sys/utsname.h (struct utsname, __USE_GNU domainname)
- /usr/include/x86_64-linux-gnu/bits/utsname.h (_UTSNAME_LENGTH 65)
- worklog Task 1-a (uname full entry)
