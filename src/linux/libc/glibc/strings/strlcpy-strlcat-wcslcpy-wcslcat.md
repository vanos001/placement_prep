# `strlcpy` / `strlcat` / `wcslcpy` / `wcslcat` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` (`strlcpy`, `strlcat` under `__USE_MISC`); `wchar.h` (`wcslcpy`, `wcslcat` under `__USE_MISC`) |
| Standards | POSIX.1-2024, originally OpenBSD 2.4 / BSD extension (manual `@standards{POSIX-1.2024, string.h}`); added to glibc in 2.38 |
| Exported | `strlcpy@@GLIBC_2.38`, `strlcat@@GLIBC_2.38`, `wcslcpy@@GLIBC_2.38`, `wcslcat@@GLIBC_2.38`, all weak (nm, host glibc 2.41) |
| Thread-safety | MT-Safe per manual safety notes (`@mtsafe`); no cached man pages for any of the four |
| Ledger ID | GLIBC-strlcpy, GLIBC-strlcat, GLIBC-wcslcpy, GLIBC-wcslcat |

## Declaration and gates

```c
#include <string.h>
size_t strlcpy(char *restrict dest, const char *restrict src, size_t n);
size_t strlcat(char *restrict dest, const char *restrict src, size_t n);

#include <wchar.h>
size_t wcslcpy(wchar_t *restrict dest, const wchar_t *restrict src,
               size_t n);
size_t wcslcat(wchar_t *restrict dest, const wchar_t *restrict src,
               size_t n);
```

The narrow pair sits in `/usr/include/string.h` lines 504-515 under
`__USE_MISC`; the wide pair in `/usr/include/wchar.h` lines 107-119
under the same gate, with the mirrored comments "Copy at most N - 1
characters" / "Append SRC to DEST, possibly with truncation to keep the
total size below N". Both are glibc 2.38 additions (nm version
`GLIBC_2.38`, the only non-2.2.5 versions in this batch).

## Semantics

`strlcpy` copies `src` into a destination of total size `n`: when the
string fits, it copies and null-terminates, leaving any remaining
destination bytes *unchanged* (unlike `strncpy`'s padding); when it does
not fit, it copies exactly `n-1` bytes plus a terminator. It returns
`strlen(src)`, so truncation happened iff the return value is `>= n`
(manual, *Truncating Strings*). `strlcat` appends at the existing
terminator under the same size cap and returns the sum of the original
`to` length and `strlen(src)`. The wide variants are identical with `n`
counting wide characters (`wcslcpy(3)` story per manual).

## Gotchas and portability

- The manual is blunt: these "are generally poor choices for processing"
  strings, and `strlcpy`'s cost is proportional to `strlen(src)` even
  when `n` is tiny - it always walks the source to size the return
  value.
- GLIBC_2.38 versioning means glibc < 2.38 links fail or need a local
  shim; the sibling page
  [strcpy-strncpy-stpcpy.md](strcpy-strncpy-stpcpy.md) records the
  2.38 NEWS note ("derived from OpenBSD, expected to be added to a
  future POSIX version") - that future is POSIX.1-2024 per the manual.
- musl 1.2.5 has the narrow pair unconditionally
  (`musl include/string.h` lines 86-87) but neither wide variant - no
  `wcslcpy.c`/`wcslcat.c`, no declaration in `musl include/wchar.h`.

## References

- glibc manual: `string.texi`, node *Truncating Strings*
  (strlcpy/strlcat/wcslcpy/wcslcat, POSIX.1-2024)
- man3: none cached for these four names in
  `source-cache/man-pages-sparse/man3/`
- headers: `/usr/include/string.h`, `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
