# `btowc` / `wctob` / `mblen` / `mbtowc` / `mbstowcs` / `wctomb` / `wcstombs` (3) - glibc

> Split from the chapter *glibc: Character Set Handling* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` (`btowc`, `wctob`); `stdlib.h` (`mblen`, `mbtowc`, `wctomb`, `mbstowcs`, `wcstombs`) |
| Standards | ISO C89/C99, POSIX.1-2001/2008 |
| Exported | `btowc@@GLIBC_2.2.5`, `wctob@@GLIBC_2.2.5`, `mblen@@GLIBC_2.2.5`, `mbtowc@@GLIBC_2.2.5`, `mbstowcs@@GLIBC_2.2.5`, `wctomb@@GLIBC_2.2.5`, `wcstombs@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`btowc`, `wctob`, `mbstowcs`, `wcstombs`); MT-Unsafe `race` (`mblen`, `mbtowc`, `wctomb` -- hidden static state) (`btowc(3)`, `mbtowc(3)`, `wctomb(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-btowc, GLIBC-wctob, GLIBC-mblen, GLIBC-mbtowc, GLIBC-mbstowcs, GLIBC-wctomb, GLIBC-wcstombs |

## Declaration and gates

```c
#include <wchar.h>

wint_t btowc(int c);                                   /* line 309 */
int wctob(wint_t c);                                   /* line 313 */

#include <stdlib.h>

int mblen(const char *s, size_t n);                    /* line 1062 */
int mbtowc(wchar_t *restrict pwc, const char *restrict s,
           size_t n);                                  /* lines 1065-1066 */
int wctomb(char *s, wchar_t wchar);                    /* line 1069 */
size_t mbstowcs(wchar_t *restrict pwcs, const char *restrict src,
                size_t n);                             /* lines 1073-1074 */
size_t wcstombs(char *restrict s, const wchar_t *restrict pwcs,
                size_t n);                             /* lines 1077-1078 */
```

All seven are unconditional in their headers on this host
(`/usr/include/wchar.h`, `/usr/include/stdlib.h`).

## Semantics

This is the non-restartable half of the multibyte API: `mblen`,
`mbtowc` and `wctomb` keep their shift state in hidden static variables
(one per function). `mbtowc` converts one character, returning bytes
consumed, 0 for the null byte, -1 on invalid or incomplete input; the
same trio reset their state when called with a NULL string argument.
`mblen` is `mbtowc` minus the wide output. `wctomb` writes at most
`MB_CUR_MAX` bytes for one wide character, returning its length or -1.
`mbstowcs`/`wcstombs` convert whole strings without length-limit
restart state; they return the number of elements written, or
`(size_t) -1` on invalid input. `btowc` widens a single byte valid in
the initial state (else `WEOF`); `wctob` narrows back or returns `EOF`
(`btowc(3)`, `mbtowc(3)`, `mbstowcs(3)`).

## Gotchas and portability

- The man pages are blunt: "This function should never be used" for
  `btowc` and `wctob` -- they only work for encodings where the
  single-byte case is meaningful and break for stateful encodings;
  prefer `mbrtowc`/`wcrtomb` (`btowc(3)`, `wctob(3)` NOTES).
- The `race` annotations on `mblen`/`mbtowc`/`wctomb` are the static
  state again; the restartable page's `mbstate_t` versions are the fix.
- A length-limit stop in `mbstowcs`/`wcstombs` loses the shift state;
  only the restartable forms can resume.
- musl 1.2.5 provides all seven (`musl src/multibyte/`).

## References

- glibc manual: `charset.texi`, nodes *Non-reentrant Conversion*,
  *Non-reentrant String Conversion*, *Extended Char Intro*
- man3: `btowc(3)`, `wctob(3)`, `mblen(3)`, `mbtowc(3)`, `wctomb(3)`,
  `mbstowcs(3)`, `wcstombs(3)`
- headers: `/usr/include/wchar.h`, `/usr/include/stdlib.h`
- musl: `src/multibyte/`
