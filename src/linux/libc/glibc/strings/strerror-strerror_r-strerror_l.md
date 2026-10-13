# `strerror` / `strerror_r` / `strerror_l` / `strerrorname_np` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` |
| Standards | ISO C / POSIX.1-2001 (`strerror`); POSIX.1-2001 (`strerror_r` XSI); POSIX.1-2008 (`strerror_l`); GNU (`strerror_r` GNU form, `strerrorname_np`, `strerrordesc_np`) |
| Exported | `strerror@@GLIBC_2.2.5`, `strerror_r@@GLIBC_2.2.5` (weak), `strerror_l@@GLIBC_2.6` (weak), `strerrorname_np@@GLIBC_2.32`, `strerrordesc_np@@GLIBC_2.32` (nm, host glibc 2.41) |
| Thread-safety | `strerror`: MT-Unsafe race:strerror; `strerror_r`, `strerror_l`, `strerrorname_np`, `strerrordesc_np`: MT-Safe (`strerror(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strerror, GLIBC-strerror_r, GLIBC-strerror_l, GLIBC-strerrorname_np, GLIBC-strerrordesc_np |

## Declaration and gates

```c
#include <string.h>

char *strerror(int errnum);

/* strerror_r: two incompatible prototypes, chosen at compile time */
int   strerror_r(int errnum, char *buf, size_t buflen);  /* XSI form */
char *strerror_r(int errnum, char *buf, size_t buflen);  /* GNU form  */

char *strerror_l(int errnum, locale_t locale);           /* __USE_XOPEN2K8 */
const char *strerrorname_np(int err);                    /* __USE_GNU, 2.32 */
const char *strerrordesc_np(int err);                    /* __USE_GNU, 2.32 */
```

The XSI form is selected only when `_POSIX_C_SOURCE >= 200112L` (or
`__USE_XOPEN2K`) *and* `_GNU_SOURCE` is undefined; glibc implements it as a
redirect to `__xpg_strerror_r` (`/usr/include/string.h` lines 420-446).
`strerrorname_np`/`strerrordesc_np` sit under `__USE_GNU` (lines 448-453).

## Semantics

`strerror` maps `errnum` to a translated message string (LC_MESSAGES);
the string must not be modified and is invalidated by later `strerror` or
`strerror_l` calls, or by thread exit; the function preserves `errno` and
cannot fail (manual `errno.texi` *Error Messages*). Both `strerror_r`
flavors target a caller buffer of `buflen` bytes: XSI returns `0` on
success or the error number (glibc 2.13+; earlier glibc returned `-1` with
`errno` set); GNU returns a pointer that may point into `buf` or to an
immutable static string (`strerror(3)`). `strerror_l` translates per
`locale`; `strerrorname_np` returns the symbolic name ("EPERM") and
`strerrordesc_np` the untranslated description, both `NULL` for invalid
numbers (`strerror(3)`).

## Gotchas and portability

- GNU vs XSI `strerror_r` is a classic portability trap: the same source
  line compiles to an `int` or a `char *` depending on feature macros. With
  no explicit macros the XSI form wins by default since glibc 2.4
  (`strerror(3)` SYNOPSIS).
- `strerror` itself is MT-Unsafe: glibc keeps one buffer of 1024 characters
  per address space for it (`strerror(3)` NOTES). Library code should use
  `strerror_r`, `%m`, or the `_np` functions instead (manual *Error
  Messages*).
- Unknown error numbers: glibc returns "Unknown error nnn" and keeps
  `errno`; some other systems return `NULL` or set `EINVAL` (`strerror(3)`
  CONFORMING TO/NOTES).
- `strerrorname_np`/`strerrordesc_np` (glibc 2.32, per NEWS under
  *Version 2.32*) are MT-Safe and async-signal-safe, unlike `strerror`
  (`strerror(3)` NOTES).
- musl 1.2.5 declares only `int strerror_r(...)` and aliases
  `__xpg_strerror_r` to it, so the GNU return-the-pointer form does not
  exist there (`musl include/string.h` line 66, `src/string/strerror_r.c`);
  its message table is not locale-translated (`src/errno/strerror.c`).

## References

- glibc manual: `errno.texi`, node *Error Messages*
- man3: `strerror(3)` (covers `strerror_r`, `strerror_l`,
  `strerrorname_np`, `strerrordesc_np`)
- header: `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
