# `isalpha_l` and the `*_l` locale variants (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `ctype.h` (classifiers); `string.h`/`strings.h` (`strcasecmp_l`, `strcoll_l`, `strxfrm_l`); `stdlib.h` (`strtol_l`, `strtod_l`) |
| Standards | POSIX.1-2008 extended locale API; ISO C23 adopts `*_l` for some functions; `isascii_l` GNU only |
| Exported | `isalpha_l@@GLIBC_2.3` (weak), `isdigit_l@@GLIBC_2.3` (weak), `tolower_l@@GLIBC_2.3`, `isalnum_l@@GLIBC_2.3`, `strtol_l@@GLIBC_2.3`, `strtoul_l@@GLIBC_2.3` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe; the locale object, not the global locale, is consulted |
| Ledger ID | GLIBC-isalpha_l, GLIBC-isdigit_l, GLIBC-tolower_l, GLIBC-strtol_l rows |

## Declaration and gates

```c
#define _GNU_SOURCE /* or _XOPEN_SOURCE >= 700 */
#include <ctype.h>
#include <locale.h>

int isalpha_l(int c, locale_t locale);
int isdigit_l(int c, locale_t locale);
int isblank_l(int c, locale_t locale);
int tolower_l(int c, locale_t locale);
int toupper_l(int c, locale_t locale);
/* one *_l twin for every is* classifier; isascii_l/toascii_l GNU only */

#include <string.h>
int   strcasecmp_l(const char *s1, const char *s2, locale_t loc);
size_t strxfrm_l(char *dest, const char *src, size_t n, locale_t loc);

#include <stdlib.h>
long strtol_l(const char *nptr, char **endptr, int base, locale_t loc);
```

Declared in glibc under `__USE_XOPEN2K8` for the classifier and string
twins (`ctype.h` lines 235-323, `string.h` lines 170-182) and under
`__USE_GNU` for the `strtol_l` family (`stdlib.h` lines 340-356).
Gate history per `isalpha(3)`: `_XOPEN_SOURCE
>= 700` since glibc 2.10, `_GNU_SOURCE` before. `locale_t` itself comes
from `bits/types/locale_t.h`, pulled in by those headers.

## Semantics

Every `*_l` function behaves like its base function except that it uses the
locale object `locale` (created with `newlocale(3)`, duplicated with
`duplocale(3)`, installed per-thread with `uselocale(3)`) instead of the
current global or thread locale. Behavior is undefined if `locale` is
`LC_GLOBAL_LOCALE` or an invalid handle (`isalpha(3)` DESCRIPTION for the
classifiers; same wording in `strerror(3)` for `strerror_l`).

## Gotchas and portability

- These are the POSIX.1-2008 extended-locale API: the only way to run
  case folding, collation or numeric parsing against a locale that is not
  the ambient one, e.g. parsing a fixed-format data file while the process
  runs under the user's locale.
- C locale object vs global locale: creating a `locale_t` does not touch
  `setlocale`; an `_l` call never invalidates strings cached from the
  global locale.
- Versioning: the `_l` classifier symbols carry `GLIBC_2.3` (nm), older
  than their POSIX standardization; man pages therefore split the gate
  history at glibc 2.10.
- `isascii_l`/`toascii_l` are GNU-only and, like `isascii`, locale-free by
  definition - they exist purely for API symmetry (`ctype.h` lines
  299-321; `isalpha(3)` CONFORMING TO).
- musl 1.2.5 declares the `*_l` functions but ignores the locale argument:
  `__isalpha_l(int c, locale_t l)` just returns `isalpha(c)`
  (`musl src/ctype/isalpha.c`), because musl's only real locales are "C"
  and "C.UTF-8" (`src/locale/setlocale.c`). Portable code must not assume
  `_l` actually changes behavior under musl.

## References

- glibc manual: `locale.texi` (locale objects context), `ctype.texi`
- man3: `isalpha(3)` (`*_l` group), `newlocale(3)`, `duplocale(3)`,
  `uselocale(3)`, `strerror(3)` (`strerror_l`)
- headers: `/usr/include/ctype.h`, `/usr/include/strings.h`,
  `/usr/include/bits/types/locale_t.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
