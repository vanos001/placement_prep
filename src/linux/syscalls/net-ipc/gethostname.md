# gethostname(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | gethostname - / - / - / -; sethostname 170 / 74 / 161 / 74 (hub; the gethostname slot exists only on Alpha, and on SPARC up to 2.6.26 -- syscalls(2) table) |
| Since (kernel) | 2.0 (hub/syscalls(2): gethostname "2.0 Alpha, was available on SPARC up to Linux 2.6.26"; sethostname 170/74/161/74 since 2.0) |
| Man page | man2/gethostname.2 (cached, dated 2021-03-22; canonical page covering sethostname) |
| glibc wrapper | yes for both; gethostname is a pure library function that calls uname(2) and copies the nodename field -- glibc does not employ the gethostname syscall (gethostname.2 "C library/kernel differences") |
| Aliases covered | sethostname (SC-sethostname, grouped per ledger) |
| Ledger ID | SC-gethostname (ledger status: researched brief; SC-sethostname also brief) |

## Purpose

gethostname()/sethostname() access the hostname of the calling
process's UTS namespace. sethostname() sets it from `name`/`len`
(needs CAP_SYS_ADMIN in the governing user namespace); gethostname()
returns the null-terminated name, truncating to `len` without error at
the syscall level (gethostname.2). Because glibc implements
gethostname via uname(2), the truncation case becomes ENAMETOOLONG in
the library (see below).

## Synopsis

```c
#include <unistd.h>
int gethostname(char *name, size_t len);
int sethostname(const char *name, size_t len);
```

## Arguments and behavior

`len` is a byte count, not a flags field; `name` need not be
null-terminated for sethostname. Linux HOST_NAME_MAX is 64 (since 1.0;
8 bytes in earlier kernels). glibc truncation behavior: it copies up to
len bytes, then if the nodename length >= len returns -1 with
ENAMETOOLONG and omits the terminating null; before glibc 2.2 nothing
was copied (gethostname.2).

## Return value and errors

0 on success; -1 with `errno`: `EFAULT`, `EINVAL`, `EPERM`
(sethostname), `ENAMETOOLONG` (glibc gethostname truncation; EINVAL
before glibc 2.1).

## Flags and constants

None. Feature-test: gethostname needs _XOPEN_SOURCE >= 500 or
_POSIX_C_SOURCE >= 200112L (or _BSD_SOURCE pre-2.19); sethostname
_DEFAULT_SOURCE since glibc 2.21 (gethostname.2).

## Security and notes

- Architecture honesty (syscalls(2) quoted verbatim): the gethostname
  syscall row exists on "Alpha, was available on SPARC up to Linux
  2.6.26" -- no x64/i386/arm64-generic/arm32 slot; worklog 1-g flagged
  the bare "Since 2.0" ledger row as misleading without this note.
- UTS namespace scope: hostname changes inside a container's UTS
  namespace do not leak outside it (gethostname.2, uts_namespaces(7)).
- sethostname is not specified by POSIX (only gethostname is).

## References

- Cached man page: source-cache/man-pages-sparse/man2/gethostname.2;
  arch note quoted from source-cache/man-pages-sparse/man2/syscalls.2.
- Numbers: hub [overview](overview.md); ledger SC-gethostname,
  SC-sethostname.
