# `mbrtowc` / `mbrlen` / `mbsinit` / `mbsrtowcs` / `mbsnrtowcs` / `wcrtomb` / `wcsrtombs` / `wcsnrtombs` (3) - glibc

> Split from the chapter *glibc: Character Set Handling* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` (`mbsnrtowcs`, `wcsnrtombs` under `__USE_XOPEN2K8`) |
| Standards | ISO C99/C11 (`mbrtowc`, `mbrlen`, `mbsinit`, `mbsrtowcs`, `wcrtomb`, `wcsrtombs`); POSIX.1-2008 (`mbsnrtowcs`, `wcsnrtombs`) |
| Exported | `mbrtowc@@GLIBC_2.2.5`, `mbrlen@@GLIBC_2.2.5`, `mbsinit@@GLIBC_2.2.5`, `mbsrtowcs@@GLIBC_2.2.5`, `mbsnrtowcs@@GLIBC_2.2.5`, `wcrtomb@@GLIBC_2.2.5`, `wcsrtombs@@GLIBC_2.2.5`, `wcsnrtombs@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`mbsinit`); MT-Unsafe `race:<fn>/!ps` for the rest -- the `ps` argument must be non-NULL per thread (`mbrtowc(3)`, `mbsrtowcs(3)`, `wcrtomb(3)` etc. ATTRIBUTES) |
| Ledger ID | GLIBC-mbrtowc, GLIBC-mbrlen, GLIBC-mbsinit, GLIBC-mbsrtowcs, GLIBC-mbsnrtowcs, GLIBC-wcrtomb, GLIBC-wcsrtombs, GLIBC-wcsnrtombs |

## Declaration and gates

```c
#include <wchar.h>

int mbsinit(const mbstate_t *ps);                      /* line 317 */
size_t mbrtowc(wchar_t *restrict pwc, const char *restrict s,
               size_t n, mbstate_t *restrict ps);      /* lines 321-323 */
size_t wcrtomb(char *restrict s, wchar_t wc,
               mbstate_t *restrict ps);                /* lines 326-327 */
size_t mbrlen(const char *restrict s, size_t n,
              mbstate_t *restrict ps);                 /* lines 332-333 */
size_t mbsrtowcs(wchar_t *restrict dst, const char **restrict src,
                 size_t len, mbstate_t *restrict ps);  /* lines 362-364 */
size_t wcsrtombs(char *restrict dst, const wchar_t **restrict src,
                 size_t len, mbstate_t *restrict ps);  /* lines 368-370 */
#ifdef __USE_XOPEN2K8                                  /* line 373 */
size_t mbsnrtowcs(wchar_t *restrict dst, const char **restrict src,
                  size_t nms, size_t len, mbstate_t *restrict ps);
size_t wcsnrtombs(char *restrict dst, const wchar_t **restrict src,
                  size_t nwc, size_t len, mbstate_t *restrict ps);
#endif                                                 /* lines 376-385 */
```

## Semantics

These are the restartable conversions: all state lives in the caller's
`mbstate_t *ps`, never in library globals, so independent threads can
use their own states and a conversion can be suspended and resumed.
An initial state is a zeroed `mbstate_t`; `mbsinit` tests for it and
returns nonzero for NULL `ps` (`mbsinit(3)`). `mbrtowc` converts at
most `n` bytes to one wide character, returning bytes consumed, 0 for
the null wide character, `(size_t) -2` when the bytes end mid-character
(resume with more input), and `(size_t) -1` with `errno` `EILSEQ` for
invalid input; `mbrlen` is `mbrtowc` without storing the wide
character. `mbsrtowcs` converts a whole string, setting `*src` to NULL
and restoring the initial state on complete success; `mbsnrtowcs`
limits the input to `nms` bytes. `wcrtomb`, `wcsrtombs`, `wcsnrtombs`
are the mirror images toward multibyte (`mbrtowc(3)`, `mbsrtowcs(3)`).

## Gotchas and portability

- Passing a NULL `ps` is legal (a function-local anonymous state is
  used) but drops thread-safety -- that is exactly the `race:<fn>/!ps`
  annotation.
- `(size_t) -2` is not an error: keep the same `ps` and feed more bytes.
- `mbsrtowcs` with a NULL `dst` is the idiomatic "how many wide chars?"
  pre-pass; `*src` semantics differ between the NULL-dst and dst runs.
- musl 1.2.5 provides all eight (`musl src/multibyte/`).

## Errors

`EILSEQ` is the only errno the man pages spell out for this family --
invalid multibyte input (`mbrtowc(3)`, `mbsrtowcs(3)`, `wcrtomb(3)`,
`wcsrtombs(3)`).

## References

- glibc manual: `charset.texi`, nodes *Restartable multibyte
  conversion*, *Keeping the state*, *Converting Strings*
- man3: `mbrtowc(3)`, `mbsinit(3)`, `mbsrtowcs(3)`, `wcsrtombs(3)`,
  `mbsnrtowcs(3)`, `wcsnrtombs(3)`
- headers: `/usr/include/wchar.h`
- musl: `src/multibyte/`
