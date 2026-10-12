# `strcat` / `strncat` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` |
| Standards | ISO C, POSIX.1-2001/2008, SVr4, 4.3BSD |
| Exported | `strcat@@GLIBC_2.2.5`, `strncat@@GLIBC_2.2.5`; fortified `__strcat_chk@@GLIBC_2.3.4`, `__strncat_chk@@GLIBC_2.3.4` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (ATTRIBUTES in `strcat(3)`) |
| Ledger ID | GLIBC-strcat, GLIBC-strncat |

## Declaration and gates

```c
#include <string.h>

char *strcat(char *restrict dest, const char *restrict src);
char *strncat(char *restrict dest, const char *restrict src, size_t n);
```

No feature-test gates: both are ISO C (`/usr/include/string.h` lines 148-153).

## Semantics

`strcat` appends `src` to `dest`, overwriting `dest`'s terminating null and
adding a new one; the strings may not overlap and `dest` must have room for
the result (`strcat(3)`). Both return `dest`. `strncat` uses at most `n` bytes
from `src` (which then need not be null-terminated) and always appends one
terminating null, so it writes `n + 1` bytes when `src` has `n` or more bytes;
`dest` must be at least `strlen(dest) + n + 1` bytes (`strcat(3)`; manual
*Truncating Strings* node). A compliant sketch from the manual is
`memcpy(to + len, from, strnlen(from, size)); to[len + strnlen(from, size)] = '\0';`.

## Gotchas and portability

- `dest` size arithmetic is the classic overflow source: `strcat(3)` states
  outright that if `dest` is not large enough "buffer overruns are a favorite
  avenue for attacking secure programs".
- `strncat` is the safer of the pair but is *not* a bounded `strcat` with the
  same argument order of risk: its `n` bounds the source, not the
  destination, and it still assumes `dest` already holds a valid string.
- Quadratic cost: both functions re-scan `dest` from its start to find the
  terminator, so repeated concatenation into one buffer is O(n^2);
  `strcat(3)` ships a benchmark program demonstrating this, and the manual's
  *Truncating Strings* node lists "significant performance issues" for both.
  For many appends, track the end pointer yourself or use `stpcpy`.
- Overlap is undefined (manual, *Truncating Strings*).
- BSD `strlcat`: added to glibc in 2.38 (glibc NEWS under *Version 2.38*);
  declared on this host under `__USE_MISC` in `string.h`. The cached
  `strcat(3)` page (2021) predates that and still says it is absent.
- musl 1.2.5 has both plus `strlcat` (`musl src/string/strcat.c`,
  `src/string/strlcat.c`).

## References

- glibc manual: `string.texi`, nodes *Concatenating Strings*,
  *Truncating Strings*
- man3: `strcat(3)` (covers `strncat` via `.so` alias `strncat.3`)
- header: `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
