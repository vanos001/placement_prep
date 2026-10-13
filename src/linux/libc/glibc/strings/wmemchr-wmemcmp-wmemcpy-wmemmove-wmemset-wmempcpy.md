# `wmemchr` / `wmemcmp` / `wmemcpy` / `wmemmove` / `wmemset` / `wmempcpy` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | C99 / POSIX.1-2001 (`wmemchr`, `wmemcmp`, `wmemcpy`, `wmemmove`, `wmemset`); GNU extension (`wmempcpy`) |
| Exported | `wmemchr@@GLIBC_2.2.5`, `wmemcmp@@GLIBC_2.2.5`, `wmemset@@GLIBC_2.2.5` (ifunc symbols), `wmemcpy@@GLIBC_2.2.5`, `wmemmove@@GLIBC_2.2.5`, `wmempcpy@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`wmemchr(3)`, `wmemcmp(3)`, `wmemcpy(3)`, `wmemmove(3)`, `wmemset(3)`, `wmempcpy(3)` via `mempcpy(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-wmemchr, GLIBC-wmemcmp, GLIBC-wmemcpy, GLIBC-wmemmove, GLIBC-wmemset, GLIBC-wmempcpy |

## Declaration and gates

```c
#include <wchar.h>

wchar_t *wmemchr(const wchar_t *s, wchar_t c, size_t n);
int      wmemcmp(const wchar_t *s1, const wchar_t *s2, size_t n);
wchar_t *wmemcpy(wchar_t *restrict dest, const wchar_t *restrict src,
                 size_t n);
wchar_t *wmemmove(wchar_t *dest, const wchar_t *src, size_t n);
wchar_t *wmemset(wchar_t *wcs, wchar_t wc, size_t n);

wchar_t *wmempcpy(wchar_t *restrict dest, const wchar_t *restrict src,
                  size_t n);            /* __USE_GNU */
```

The five ISO functions are unconditional in `/usr/include/wchar.h`
(wmemchr around lines 262-270, wmemcmp 272, wmemcpy 287-288, wmemmove
292, wmemset 296); `wmempcpy` sits under `__USE_GNU` at lines 298-303.
`wmempcpy(3)` documents `_GNU_SOURCE` plus `<wchar.h>` for the wide
spelling.

## Semantics

The `wmem` family works on wide-character *arrays* with an explicit
count - not null-terminated strings; the manual's *String/Array
Conventions* node reserves the `wmem` prefix exactly for this
(`wmemcpy` etc. take a size and may hold embedded L'\0').
`wmemcpy` copies `n` wide characters and requires non-overlapping
arrays; `wmemmove` handles overlap like `memmove`. `wmemset` fills `n`
slots with `wc`; `wmemchr` finds the first `c` among `n` characters,
returning NULL when absent; `wmemcmp` compares `n` wide characters and
returns the sign of the first difference. `wmempcpy` is `wmemcpy` plus
the `mempcpy` twist: it returns `dest + n`, so successive copies chain
without re-computing offsets (`mempcpy(3)`).

## Gotchas and portability

- Counted in wide characters, never bytes: passing a `sizeof`-style
  byte count multiplies the copy by `sizeof(wchar_t)` and runs off the
  buffer. The `wcsnlen(3)` man page notes the same confusion for
  lengths.
- Overlap: `wmemcpy` with overlapping arrays is undefined - switch to
  `wmemmove` (`wmemcpy(3)` DESCRIPTION).
- `wmempcpy` is GNU-only and musl 1.2.5 does not have it (no
  `wmempcpy.c`, no declaration in `musl include/wchar.h`); the other
  five are all present in musl (`musl src/string/wmem*.c`).

## References

- glibc manual: `string.texi`, nodes *String/Array Conventions*,
  *Copying Strings and Arrays* (wmem functions inline)
- man3: `wmemchr(3)`, `wmemcmp(3)`, `wmemcpy(3)`, `wmemmove(3)`,
  `wmemset(3)`, `mempcpy(3)` (covers `wmempcpy`)
- header: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
