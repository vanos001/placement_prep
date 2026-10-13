# `gethostname` / `sethostname` - glibc

> Split from the chapter *glibc: System Management* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` (`gethostname` line 911 gated on `__USE_XOPEN_EXTENDED` or `__USE_XOPEN2K`; `sethostname` line 919 under `__USE_MISC`) |
| Standards | POSIX.1-2001/2008 (`gethostname`); SVr4, 4.4BSD (`sethostname` is *not* POSIX) |
| Exported | `gethostname@@GLIBC_2.2.5` (W), `sethostname@@GLIBC_2.2.5` (T) (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES table in gethostname.2; the glibc wrapper is a uname-based copy with no shared state |
| Ledger ID | GLIBC-gethostname, GLIBC-sethostname |

## Declaration and gates

```c
#include <unistd.h>

int gethostname(char *name, size_t len);        /* unistd.h:911 */
int sethostname(const char *name, size_t len);  /* unistd.h:919, __USE_MISC */
```

Per gethostname.2, `gethostname` needs `_XOPEN_SOURCE >= 500` or
`_POSIX_C_SOURCE >= 200112L`; `sethostname` needs `_DEFAULT_SOURCE`
(glibc >= 2.21).

## Semantics

Both operate on the hostname of the calling process's UTS namespace
(gethostname.2). `sethostname` sets it to the `len` bytes at `name` (no
NUL needed) and is restricted to privileged callers (`CAP_SYS_ADMIN`).
`gethostname` fills `name` with the NUL-terminated hostname, truncating
silently if it does not fit `len`. **The glibc wrapper does not issue the
`gethostname` syscall**: it calls `uname(2)` and copies `nodename`, then
returns -1 with `ENAMETOOLONG` if the name did not fit -- in which case
the buffer is not NUL-terminated (gethostname.2, "C library/kernel
differences"; the raw syscall page is
[uname](../../../syscalls/process/uname.md)). Linux limits hostnames to
`HOST_NAME_MAX` = 64 bytes (SUSv2 says 255) (gethostname.2 NOTES).

## Gotchas and portability

- Truncation is the classic bug: POSIX says it is unspecified whether a
  truncated buffer keeps its NUL; glibc answers by failing with
  `ENAMETOOLONG` instead -- but only on the truncating path.
- `sethostname` is typically a boot-time, init-only call (manual,
  *Host Identification*); in containers it fails without `CAP_SYS_ADMIN`
  in the owning user namespace.
- The value is settable per UTS namespace, so threads in different
  namespaces see different hostnames.
- musl 1.2.5: both present (`include/unistd.h` lines 124, 170).

## Errors

`EFAULT` (bad `name`), `EINVAL` (negative `len`; for `sethostname`, too
long), `ENAMETOOLONG` (glibc `gethostname` truncation), `EPERM`
(`sethostname` without privilege) (gethostname.2 ERRORS).

## References

- man2: `gethostname.2` (covers `sethostname`), `sethostname.2` (`.so` link)
- glibc manual: `sysinfo.texi`, node *Host Identification*
- headers: `/usr/include/unistd.h` (lines 905-920)
- symbols: `nm -D --with-symbol-versions libc.so.6`
