# `getdate` / `getdate_r` (3) - glibc

> Split from the chapter *glibc: Calendar Time* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `time.h` (`getdate` under `__USE_XOPEN_EXTENDED`, `getdate_r` under `__USE_GNU`) |
| Standards | POSIX.1-2001/2008 (XSI) (`getdate`); GNU extension (`getdate_r`) |
| Exported | `getdate@@GLIBC_2.2.5`, `getdate_r@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:getdate env locale` (`getdate`); MT-Safe `env locale` (`getdate_r`) (`getdate(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getdate, GLIBC-getdate_r, GLIBC-getdate_err |

## Declaration and gates

```c
#include <time.h>

extern int getdate_err;    /* /usr/include/time.h line 425 */

struct tm *getdate(const char *string);   /* __USE_XOPEN_EXTENDED,
                                             lines 413-435 */
int getdate_r(const char *restrict string,
              struct tm *restrict res);   /* __USE_GNU, lines 437-449 */
```

Gates per the man page: `getdate` wants `_XOPEN_SOURCE >= 500`;
`getdate_r` wants `_GNU_SOURCE` (`getdate(3)`). The header's own gate
is `__USE_XOPEN_EXTENDED` (`/usr/include/time.h` line 413).

## Semantics

`getdate` converts a date-plus-time string to a broken-down
`struct tm` using the *template file* named by the `DATEMSK` environment
variable: the first line that matches the input (case-insensitively,
whitespace ignored) supplies the `strptime(3)`-style format, plus one
XSI extra, `%Z`. Missing fields are filled from defaults -- today's
date, current time, or forward-looking rules for bare weekday/month
inputs (`getdate(3)`). Success returns a pointer to a *static* `tm`;
failure returns NULL and stores a reason code 1-8 in the global
`getdate_err` (1: DATEMSK unset; 2: cannot open; 3: stat failed; 4:
not a regular file; 5: read error; 6: out of memory; 7: no template
line matches; 8: invalid input, e.g. February 31). `getdate_r` is the
reentrant GNU twin: results go into the caller's `res` buffer and the
error code becomes the return value (`getdate(3)`, manual *Parsing
Date and Time*).

## Gotchas and portability

- Static buffer + global error variable: glibc's manual flatly warns
  that `getdate` "should never be used" from multithreaded programs;
  use `getdate_r` (manual, `getdate` page).
- `%Z` is documented as not implemented in glibc (`getdate(3)`).
- `errno` changes across `getdate` are unspecified -- only
  `getdate_err` counts.
- musl 1.2.5 provides `getdate` (`src/time/getdate.c`); `getdate_r`
  is glibc-only.

## References

- glibc manual: `time.texi`, nodes *Parsing Date and Time*,
  `getdate_err` definition list
- man3: `getdate(3)`, `getdate_r(3)`, `getdate_err(3)`
- headers: `/usr/include/time.h` (error-code comment, lines 414-424)
- musl: `include/time.h`, `src/time/getdate.c`
