# getdomainname(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | getdomainname - / - / - / -; setdomainname 171 / 121 / 162 / 121 (hub; the getdomainname slot exists only on SPARC/SPARC64, plus Alpha as osf_getdomainname -- syscalls(2) table) |
| Since (kernel) | getdomainname 2.2 (syscalls(2) row "2.2: SPARC, SPARC64; available as osf_getdomainname(2) on Alpha since Linux 2.0"); setdomainname 1.0 (ledger row) |
| Man page | man2/getdomainname.2 (cached, dated 2021-03-22; canonical page covering setdomainname) |
| glibc wrapper | yes for both; on architectures without the syscall (including x86) glibc implements getdomainname as a library function returning the domainname field of uname(2) (getdomainname.2 NOTES) |
| Aliases covered | setdomainname (SC-setdomainname, grouped per ledger) |
| Ledger ID | SC-getdomainname (ledger status: researched brief; SC-setdomainname also brief) |

## Purpose

getdomainname()/setdomainname() access the NIS domain name of the
calling process's UTS namespace. setdomainname() sets it from
`name`/`len` (CAP_SYS_ADMIN in the governing user namespace required);
getdomainname() returns the null-terminated domain name, truncated to
`len` bytes by glibc on overflow (libc variants instead error)
(getdomainname.2). Nothing in the modern kernel uses the NIS domain
name; the calls persist for compatibility.

## Synopsis

```c
#include <unistd.h>
int getdomainname(char *name, size_t len);
int setdomainname(const char *name, size_t len);
```

## Arguments and behavior

`len` is the byte size of `name`; no terminating null is required for
setdomainname. The domain-name limit including the null byte is 64
bytes since Linux 1.0 (8 before). getdomainname under libc errors with
EINVAL when name is NULL or the name is longer than len; the glibc
wrapper truncates instead (getdomainname.2). setdomainname fails with
EPERM without CAP_SYS_ADMIN, EINVAL for negative/oversized len,
EFAULT for a bad pointer.

## Return value and errors

0 on success; -1 with `errno`: `EFAULT`, `EINVAL`, `EPERM`
(setdomainname).

## Flags and constants

None. Feature-test since glibc 2.21: _DEFAULT_SOURCE for both
(getdomainname.2).

## Security and notes

- Architecture honesty (syscalls(2) quoted verbatim): getdomainname row
  is "SPARC, SPARC64; available as osf_getdomainname(2) on Alpha since
  Linux 2.0" -- no x64/i386/arm64-generic/arm32 slot; worklog 1-g
  flagged the ledger row as misleading without this arch note.
- POSIX does not specify either call (getdomainname.2 CONFORMING TO).
- UTS namespace scope as for [gethostname](gethostname.md);
  setdomainname has direct slots everywhere (170/74/161/74 per hub).

## References

- Cached man page: source-cache/man-pages-sparse/man2/getdomainname.2;
  arch note quoted from source-cache/man-pages-sparse/man2/syscalls.2.
- Numbers/Since: hub [overview](overview.md); ledger
  SC-getdomainname, SC-setdomainname.
