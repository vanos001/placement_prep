# `getdomainname` / `setdomainname` - glibc

> Split from the chapter *glibc: System Management* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` lines 928-934, both under `__USE_MISC` |
| Standards | POSIX does not specify these calls (getdomainname.2 CONFORMING TO); SVr4/4.4BSD lineage |
| Exported | `getdomainname@@GLIBC_2.2.5` (T), `setdomainname@@GLIBC_2.2.5` (T) (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES table in getdomainname.2; uname-copy wrapper / thin syscall |
| Ledger ID | GLIBC-getdomainname, GLIBC-setdomainname |

## Declaration and gates

```c
#include <unistd.h>

/* unistd.h:928 gate: __USE_MISC */
int getdomainname(char *name, size_t len);        /* unistd.h:930 */
int setdomainname(const char *name, size_t len);  /* unistd.h:933 */
```

getdomainname.2's gate history: `_DEFAULT_SOURCE` since glibc 2.21;
`_BSD_SOURCE || (_XOPEN_SOURCE && _XOPEN_SOURCE < 500)` before that --
matching the header's `__USE_MISC` block today.

## Semantics

These get or set the *NIS (YP) domain name* of the host -- more precisely,
of the calling process's UTS namespace (getdomainname.2). This is the
yellow-pages/NIS domain, **not** the DNS domain part of the FQDN; the
manual is emphatic that people confuse the two (sysinfo.texi, *Host
Identification*). `setdomainname` writes the `len` bytes at `name` into
the kernel's domainname field and needs `CAP_SYS_ADMIN`; the 64-byte
limit (with NUL) has held since Linux 1.0 (getdomainname.2 NOTES).
`getdomainname` copies out the NUL-terminated name, failing with
`ENAMETOOLONG` when it needs more than `len` bytes. On most
architectures -- x86 included -- **there is no `getdomainname` syscall**:
glibc implements it as a library function returning a copy of the
`domainname` field of `uname(2)` (getdomainname.2 NOTES; sysinfo.texi
line 298 says the same); `setdomainname` is a real syscall wrapper
([uname](../../../syscalls/process/uname.md) covers the same kernel
storage).

## Gotchas and portability

- With NIS dead on modern systems the field is usually the empty string;
  treat it as "whatever the admin wrote", not as DNS identity.
- The name lives in the same kernel slots that `uname`'s `domainname`
  member reports, and glibc's `struct utsname` exposes that member only
  under `__USE_GNU` (`__domainname` otherwise, sys/utsname.h lines 64-70).
- `setdomainname` succeeds even when NIS is not in use -- it is just
  kernel string storage.
- musl 1.2.5: both present (`include/unistd.h` lines 171-172).

## Errors

`EFAULT` (bad `name`), `EINVAL` (negative `len`; `setdomainname` over the
64-byte limit), `ENAMETOOLONG` (glibc `getdomainname` truncation), `EPERM`
(`setdomainname` without `CAP_SYS_ADMIN`) (getdomainname.2 ERRORS, same
shape as gethostname.2).

## References

- man2: `getdomainname.2` (covers `setdomainname`), `setdomainname.2` (`.so` link)
- glibc manual: `sysinfo.texi`, node *Host Identification*
- headers: `/usr/include/unistd.h` (lines 928-934)
- symbols: `nm -D --with-symbol-versions libc.so.6`
