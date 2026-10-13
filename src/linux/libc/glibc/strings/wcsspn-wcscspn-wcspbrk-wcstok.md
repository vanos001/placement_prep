# `wcsspn` / `wcscspn` / `wcspbrk` / `wcstok` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | C99 / POSIX.1-2001 (all four; `wcstok(3)` CONFORMING TO) |
| Exported | `wcsspn@@GLIBC_2.2.5`, `wcscspn@@GLIBC_2.2.5`, `wcspbrk@@GLIBC_2.2.5` (strong), `wcstok@@GLIBC_2.2.5` (strong) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`wcsspn(3)`, `wcscspn(3)`, `wcspbrk(3)`, `wcstok(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-wcsspn, GLIBC-wcscspn, GLIBC-wcspbrk, GLIBC-wcstok |

## Declaration and gates

```c
#include <wchar.h>

size_t  wcsspn(const wchar_t *wcs, const wchar_t *accept);
size_t  wcscspn(const wchar_t *wcs, const wchar_t *reject);
wchar_t *wcspbrk(const wchar_t *wcs, const wchar_t *accept);
wchar_t *wcstok(wchar_t *restrict wcs, const wchar_t *restrict delim,
                wchar_t **restrict ptr);
```

All four are declared unconditionally in `/usr/include/wchar.h`:
`wcscspn` lines 212-213, `wcsspn` lines 216-217, `wcspbrk` lines
220-226, `wcstok` lines 242-244. No feature-test gates - unlike the
narrow `strtok`, `wcstok` has had its context pointer since C99.

## Semantics

`wcsspn` returns the length of the longest initial segment of `wcs`
made entirely of characters from `accept` (`wcsspn(3)`); `wcscspn` the
complement - the initial segment containing none of `reject` - i.e. the
offset of the first rejected character, or `wcslen(wcs)` if none
(`wcscspn(3)`). `wcspbrk` returns a pointer to the first occurrence of
any `accept` character, NULL if none (`wcspbrk(3)`). `wcstok` splits
`wcs` into tokens: it skips leading delimiters, terminates the token by
overwriting the next delimiter with L'\0', and keeps its place in the
caller's `*ptr`; NULL `wcs` continues from there, and NULL is returned
when no tokens remain (`wcstok(3)`).

## Gotchas and portability

- `wcstok` is *not* `strtok`-shaped: the third argument is mandatory and
  there is no context-free variant - code translated from `strtok` will
  not compile until the state pointer is threaded through, which is
  precisely what makes it MT-Safe where `strtok` is
  `MT-Unsafe race:strtok` (see
  [strtok-strtok_r-strsep.md](strtok-strtok_r-strsep.md)).
- Like `strtok`, `wcstok` destructively modifies the input - delimiters
  become L'\0' - so it cannot tokenize constant strings (`wcstok(3)`
  NOTES).
- The span functions return counts, `wcspbrk` returns a pointer:
  `wcschr(wcs, ...)` style NULL checks on the span results are a type
  error waiting to happen.
- musl 1.2.5 implements all four (`musl src/string/wcsspn.c`,
  `wcscspn.c`, `wcspbrk.c`, `wcstok.c`).

## References

- glibc manual: `string.texi`, nodes *Search Functions*,
  *Finding Tokens in a String*
- man3: `wcsspn(3)` (covers `wcscspn` context), `wcspbrk(3)`,
  `wcstok(3)`
- header: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
