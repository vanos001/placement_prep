# `fgetws` / `fputws` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` (ledger rows `fgetws`/`fputws`; unlocked forms `wchar.h` under `__USE_GNU`) |
| Standards | C99 / POSIX.1-2001 (`fgetws`, `fputws`); GNU (`fgetws_unlocked`, `fputws_unlocked`) |
| Exported | `fgetws@@GLIBC_2.2.5`, `fputws@@GLIBC_2.2.5`, `fgetws_unlocked@@GLIBC_2.2.5`, `fputws_unlocked@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`fgetws(3)`, `fputws(3)` ATTRIBUTES; `_unlocked` forms skip the stream lock) |
| Ledger ID | GLIBC-fgetws, GLIBC-fgetws_unlocked, GLIBC-fputws, GLIBC-fputws_unlocked |

## Declaration and gates

```c
#include <wchar.h>

wchar_t *fgetws(wchar_t *restrict ws, int n, FILE *restrict stream);
int fputws(const wchar_t *restrict ws, FILE *restrict stream);

wchar_t *fgetws_unlocked(wchar_t *restrict ws, int n,      /* __USE_GNU */
                         FILE *restrict stream);
int fputws_unlocked(const wchar_t *restrict ws,            /* __USE_GNU */
                    FILE *restrict stream);
```

The plain forms are declared in the wide-character I/O block of
`wchar.h` without an extra gate (`/usr/include/wchar.h` lines 964-972);
the `_unlocked` forms are in the `__USE_GNU` block (lines 982-1037).

## Semantics

`fgetws` is the wide-character equivalent of `fgets`: it reads at most
`n-1` wide characters into `ws`, stops after storing a newline wide
character, at end of stream, or on error, and appends `L'\0'`; the
caller must provide room for at least `n` wide characters. It returns
`ws`, or `NULL` if end of stream was already reached or an error
occurred (`fgetws(3)`). `fputws` is the wide `fputs`: it writes the
wide-character string up to but not including the terminating `L'\0'`
and returns a nonnegative integer on success or `-1` on error; it does
not append a newline (`fputws(3)`). Like all wide stream operations,
both convert through `LC_CTYPE`, so the descriptor carries multibyte
bytes.

## Gotchas and portability

- `NULL`/`-1` conflate end-of-file with error; `feof`/`ferror` decide.
- Newline is *stored* by `fgetws` but *not added* by `fputws` -- the
  same asymmetry as the narrow `fgets`/`fputs` pair.
- The stream must be wide oriented before use; mixing orientations is
  undefined and undiagnosed (`fwide(3)`, manual node *Streams and I18N*).
- musl 1.2.5: all four present; `_unlocked` forms need `_GNU_SOURCE`
  (`musl include/wchar.h` lines 145-153, `src/stdio/fgetws.c`,
  `fputws.c`).

## References

- glibc manual: `stdio.texi`, nodes *Line-Oriented Input*,
  *Streams and I18N*
- man3: `fgetws(3)`, `fputws(3)`, `unlocked_stdio(3)`
- headers: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
