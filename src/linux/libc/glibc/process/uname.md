# `uname` - glibc

> Split from the chapter *glibc: System Management* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/utsname.h` (struct at lines 48-70, `uname` declared at line 81 -- unconditional) |
| Standards | POSIX.1-2001/2008, SVr4 (uname.2 CONFORMING TO); no 4.3BSD equivalent |
| Exported | `uname@@GLIBC_2.2.5` (W) (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES table in uname.2; single syscall filling a caller buffer |
| Ledger ID | GLIBC-uname |

## Declaration and gates

```c
#include <sys/utsname.h>

int uname(struct utsname *buf);   /* sys/utsname.h:81 */

struct utsname {                  /* sys/utsname.h:48-70 */
    char sysname[_UTSNAME_SYSNAME_LENGTH];    /* e.g. "Linux" */
    char nodename[_UTSNAME_NODENAME_LENGTH];  /* hostname slot */
    char release[_UTSNAME_RELEASE_LENGTH];    /* e.g. "6.1.0" */
    char version[_UTSNAME_VERSION_LENGTH];
    char machine[_UTSNAME_MACHINE_LENGTH];    /* e.g. "x86_64" */
#ifdef __USE_GNU
    char domainname[_UTSNAME_DOMAIN_LENGTH];  /* NIS domain */
#else
    char __domainname[_UTSNAME_DOMAIN_LENGTH];
#endif
};
```

Array length: `_UTSNAME_LENGTH` is 65 on Linux (`__NEW_UTS_LEN` + 1);
the fields are NUL-terminated but POSIX leaves the array sizes
unspecified (uname.2 DESCRIPTION/NOTES).

## Semantics

`uname` returns kernel-identified facts in `buf` and 0; only the first
five members are POSIX. Four fields are meaningful (OS name, release,
version, machine); `nodename` is the name the kernel was told via
`sethostname(2)` -- "the name of the present machine in some undefined
network" -- and `domainname` is the `setdomainname(2)` slot, a GNU
extension that glibc exposes under `__USE_GNU` (uname.2 DESCRIPTION and
NOTES). On Linux the glibc wrapper passes through to the `uname` syscall
(raw page: [uname](../../../syscalls/process/uname.md)); the same kernel
strings back `gethostname`/`getdomainname`, which are library-level
copies out of `nodename`/`domainname`. The manual uses `uname` for
"Platform Type" detection -- `release` for kernel features, `machine`
for architecture dispatch (sysinfo.texi, *Platform Type*).

## Gotchas and portability

- `sysname`/`release`/`version` are kernel strings, not distro identity;
  parsing `release` for distro versioning is wrong -- use `/etc/os-release`
  data for that.
- `nodename` == hostname holds on Linux, but POSIX does not require it
  (uname.2 NOTES).
- Old syscall variants (`olduname`, `oldolduname`) survive in the man
  cache only as historical entries; glibc exposes just `uname`.
- `domainname` member visibility changes struct layout between
  `__USE_GNU` and strict builds -- do not binary-copy `struct utsname`
  across compilation modes.
- musl 1.2.5: present (`include/sys/utsname.h`), same struct shape.

## Errors

`EFAULT` (`buf` invalid) is the only documented error (uname.2 ERRORS).

## References

- man2: `uname.2` (see also `olduname.2`, `oldolduname.2` for history)
- glibc manual: `sysinfo.texi`, nodes *Platform Type*, *Host Identification*
- headers: `/usr/include/x86_64-linux-gnu/sys/utsname.h` (lines 31-81)
- symbols: `nm -D --with-symbol-versions libc.so.6`
