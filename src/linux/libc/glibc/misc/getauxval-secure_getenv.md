# `getauxval` / `secure_getenv` (3) - glibc

> Split from the chapter *glibc: Program Basics* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/auxv.h` (`getauxval`); `stdlib.h` under `__USE_GNU` (`secure_getenv`) |
| Standards | Nonstandard glibc extensions |
| Exported | `getauxval@@GLIBC_2.16`, `secure_getenv@@GLIBC_2.17` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe both (`getauxval(3)`, `getenv(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getauxval, GLIBC-secure_getenv |

## Declaration and gates

```c
#include <sys/auxv.h>      /* pulls in <elf.h> (line 22) */

unsigned long int getauxval(unsigned long int type);   /* lines 31-32 */

#include <stdlib.h>

char *secure_getenv(const char *name);   /* __USE_GNU, lines 776-779 */
```

`getauxval` lives in `/usr/include/x86_64-linux-gnu/sys/auxv.h` lines
28-32 with no feature-test gate; `secure_getenv` sits in the
`__USE_GNU` block of `/usr/include/stdlib.h` (`_GNU_SOURCE`,
`getenv(3)`). The `AT_*` type constants come from `/usr/include/elf.h`
(`AT_NULL` ... starting at line 1196).

## Semantics

`getauxval` reads the kernel's auxiliary vector -- the ELF loader's
key/value side-channel above argv/envp. Given an `AT_*` type it
returns the value: `AT_PAGESZ`, `AT_HWCAP` (CPU feature bits),
`AT_CLKTCK`, `AT_ENTRY`, `AT_EXECFN`, `AT_SYSINFO_EHDR` (vDSO) and
many more; not all types exist on all architectures (`getauxval(3)`).
`LD_SHOW_AUXV=1` dumps it, `/proc/[pid]/auxv` exposes it per process.
`secure_getenv` behaves like `getenv` but returns NULL whenever
"secure execution" is required -- effective IDs differ from real IDs
(set-user-ID / set-group-ID), the file carries an effective
capability bit, or the process has a nonempty permitted capability
set; Linux security modules can force it too. It exists so
general-purpose libraries do not trust environment variables in
privileged programs (`getenv(3)`).

## Gotchas and portability

- Before glibc 2.19, a missing `type` was indistinguishable from a
  value of 0; now `errno` is set to `ENOENT`, so check `errno`
  (`getauxval(3)` BUGS).
- Zero return with no `ENOENT` is a legitimate auxv value.
- `getauxval` is also a musl function (`src/misc/getauxval.c`) but
  with limited type support; `secure_getenv` exists in musl too
  (`src/env/secure_getenv.c`).

## Errors

`ENOENT` (glibc 2.19+): `type` not present in the auxiliary vector.

## References

- glibc manual: `startup.texi`, nodes *Auxiliary Vector*,
  *Environment Access*
- man3: `getauxval(3)`, `getenv(3)` (covers `secure_getenv`)
- headers: `/usr/include/x86_64-linux-gnu/sys/auxv.h`,
  `/usr/include/stdlib.h`, `/usr/include/elf.h`
- musl: `src/misc/getauxval.c`, `src/env/secure_getenv.c`
