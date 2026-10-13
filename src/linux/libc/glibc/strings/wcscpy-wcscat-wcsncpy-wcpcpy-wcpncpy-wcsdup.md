# `wcscpy` / `wcscat` / `wcsncpy` / `wcsncat` / `wcpcpy` / `wcpncpy` / `wcsdup` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | C99 / POSIX.1-2001 (`wcscpy`, `wcsncpy`, `wcscat`, `wcsncat`); POSIX.1-2008 (`wcpcpy`, `wcpncpy`, `wcsdup`) |
| Exported | `wcscpy@@GLIBC_2.2.5`, `wcsncpy@@GLIBC_2.2.5`, `wcscat@@GLIBC_2.2.5`, `wcsncat@@GLIBC_2.2.5`, `wcpcpy@@GLIBC_2.2.5`, `wcpncpy@@GLIBC_2.2.5` (ifunc symbols), `wcsdup@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`wcscpy(3)`, `wcscat(3)`, `wcsncpy(3)`, `wcpcpy(3)`, `wcpncpy(3)`, `wcsdup(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-wcscpy, GLIBC-wcscat, GLIBC-wcsncpy, GLIBC-wcsncat, GLIBC-wcpcpy, GLIBC-wcpncpy, GLIBC-wcsdup |

## Declaration and gates

```c
#include <wchar.h>

wchar_t *wcscpy(wchar_t *restrict dest, const wchar_t *restrict src);
wchar_t *wcsncpy(wchar_t *restrict dest, const wchar_t *restrict src,
                 size_t n);
wchar_t *wcscat(wchar_t *restrict dest, const wchar_t *restrict src);
wchar_t *wcsncat(wchar_t *restrict dest, const wchar_t *restrict src,
                 size_t n);

wchar_t *wcpcpy(wchar_t *restrict dest, const wchar_t *restrict src);
wchar_t *wcpncpy(wchar_t *restrict dest, const wchar_t *restrict src,
                 size_t n);
wchar_t *wcsdup(const wchar_t *s);
```

`wcscpy`/`wcsncpy`/`wcscat`/`wcsncat` are unconditional
(`/usr/include/wchar.h` lines 98-127). The pointer-returning pair and
`wcsdup` sit under `__USE_XOPEN2K8`: `wcsdup` at lines 162-178, and
`wcpcpy`/`wcpncpy` at the tail of the header, lines 687-698. Man pages
record the same history: `_POSIX_C_SOURCE >= 200809L` since glibc 2.10,
`_GNU_SOURCE` before.

## Semantics

Wide twins of the narrow copy family, measured in `wchar_t` elements.
`wcscpy` copies including the terminating L'\0' and needs
`wcslen(src)+1` room; `wcscat` appends at `dest`'s L'\0' (needs
`wcslen(dest)+wcslen(src)+1`); neither tolerates overlap
(`wcscpy(3)`, `wcscat(3)`). `wcsncpy`/`wcsncat` are the bounded forms:
`wcsncpy` writes exactly `n` wide characters, padding with L'\0' or - if
`src` is at least `n` long - leaving the result unterminated
(`wcsncpy(3)`); `wcsncat` always terminates. `wcpcpy` returns a pointer
to the terminating null it wrote; `wcpncpy` returns a pointer to the
last wide character written, `dest + n - 1` per the cached man page.
`wcsdup` mallocs a duplicate (`wcsdup(3)`).

## Gotchas and portability

- The `wcsncpy` unterminated-result trap mirrors `strncpy` exactly;
  force termination manually or use `wcslcpy` (see
  [strlcpy-strlcat-wcslcpy-wcslcat.md](strlcpy-strlcat-wcslcpy-wcslcat.md)).
- `wcpncpy`'s return value is a documentation oddity: the man page says
  `dest + n - 1` while `wcpncpy(3)`'s NAME promises "a pointer to its
  end" and the header comment says "address of the last character
  written"; narrow `stpncpy` (documented in
  [strcpy-strncpy-stpcpy.md](strcpy-strncpy-stpcpy.md)) returns
  `dest + n` when unterminated. Recorded as printed; do not rely on the
  exact value across implementations.
- `wcsdup` sets `errno` to `ENOMEM` on failure - the only member of this
  batch with an errno contract (`wcsdup(3)` ERRORS).
- musl 1.2.5 ships all seven (`musl src/string/wcs*.c`, `wcpcpy.c`,
  `wcpncpy.c`; `wcsdup` in `include/wchar.h` line 165).

## References

- glibc manual: `string.texi`, nodes *Copying Strings and Arrays*,
  *Truncating Strings* (wide variants documented inline)
- man3: `wcscpy(3)`, `wcscat(3)`, `wcsncpy(3)`, `wcsncat(3)`,
  `wcpcpy(3)`, `wcpncpy(3)`, `wcsdup(3)`
- header: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
