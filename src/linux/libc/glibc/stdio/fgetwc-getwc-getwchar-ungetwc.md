# `fgetwc` / `getwc` / `getwchar` / `ungetwc` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` (`stdio.h` in the man page synopsis too; unlocked forms: `wchar.h` under `__USE_GNU`) |
| Standards | C99 / POSIX.1-2001 (`fgetwc`, `getwc`, `getwchar`, `ungetwc`); GNU (`*_unlocked`) |
| Exported | `fgetwc@@GLIBC_2.2.5` (weak, same slot as `getwc`), `getwc@@GLIBC_2.2.5`, `getwchar@@GLIBC_2.2.5`, `ungetwc@@GLIBC_2.2.5`, `fgetwc_unlocked@@GLIBC_2.2.5`, `getwc_unlocked@@GLIBC_2.2.5`, `getwchar_unlocked@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`fgetwc(3)`, `getwchar(3)`, `ungetwc(3)` ATTRIBUTES; `_unlocked` forms skip the stream lock) |
| Ledger ID | GLIBC-fgetwc, GLIBC-fgetwc_unlocked, GLIBC-getwc, GLIBC-getwc_unlocked, GLIBC-getwchar, GLIBC-getwchar_unlocked, GLIBC-ungetwc |

## Declaration and gates

```c
#include <wchar.h>

wint_t fgetwc(FILE *stream);
wint_t getwc(FILE *stream);
wint_t getwchar(void);
wint_t ungetwc(wint_t wc, FILE *stream);

wint_t getwc_unlocked(FILE *stream);      /* __USE_GNU */
wint_t getwchar_unlocked(void);           /* __USE_GNU */
wint_t fgetwc_unlocked(FILE *stream);     /* __USE_GNU */
```

The plain functions sit in the wide-character I/O block of `wchar.h`
with no extra feature-test gate beyond including the header
(`/usr/include/wchar.h` lines 935-979). The `_unlocked` forms are in the
`__USE_GNU` block right below (lines 982-1037), where the header notes
they are cancellation points too but lock nothing.

## Semantics

`fgetwc` is the wide-character equivalent of `fgetc`: it reads the next
wide character from `stream` and returns it, `WEOF` at end of stream or
if `ferror(stream)` becomes true, with `errno = EILSEQ` when the input
does not form a valid character (`fgetwc(3)`). `getwc` is identical but
may be a macro that evaluates `stream` more than once. `getwchar` is
`getwc(stdin)`. `ungetwc` pushes one wide character back so later reads
see it again: it decrements the file-position indicator, clears the
end-of-file indicator, leaves the backing storage untouched, and accepts
any valid `wc`, not just the last one read; only one level of pushback
is guaranteed (`ungetwc(3)`).

## Gotchas and portability

- Behavior follows `LC_CTYPE`: absent a `,ccs=` `fopen` mode, glibc reads
  a multibyte sequence and converts it to `wchar_t` (`fgetwc(3)` NOTES).
- Mixing these with narrow operations on an oriented stream is undefined
  and undiagnosed; set orientation first with `fwide` (`fwide(3)`).
- `WEOF` conflates end-of-file with error; check `ferror`/`feof` and
  `errno == EILSEQ` to tell them apart.
- musl 1.2.5: all present; the `_unlocked` forms need `_GNU_SOURCE`
  (`musl include/wchar.h` lines 145-153, `src/stdio/`).

## References

- glibc manual: `stdio.texi`, nodes *Streams and I18N*, *Simple Output*
- man3: `fgetwc(3)`, `getwchar(3)`, `ungetwc(3)`, `unlocked_stdio(3)`
  (covers the `_unlocked` forms)
- headers: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
