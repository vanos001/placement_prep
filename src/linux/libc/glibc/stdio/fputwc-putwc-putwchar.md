# `fputwc` / `putwc` / `putwchar` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` (unlocked forms: `wchar.h` under `__USE_GNU`) |
| Standards | C99 / POSIX.1-2001 (`fputwc`, `putwc`, `putwchar`); GNU (`*_unlocked`) |
| Exported | `fputwc@@GLIBC_2.2.5`, `putwc@@GLIBC_2.2.5`, `putwchar@@GLIBC_2.2.5`, `fputwc_unlocked@@GLIBC_2.2.5`, `putwc_unlocked@@GLIBC_2.2.5`, `putwchar_unlocked@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`fputwc(3)`, `putwchar(3)` ATTRIBUTES; `_unlocked` forms skip the stream lock) |
| Ledger ID | GLIBC-fputwc, GLIBC-fputwc_unlocked, GLIBC-putwc, GLIBC-putwc_unlocked, GLIBC-putwchar, GLIBC-putwchar_unlocked |

## Declaration and gates

```c
#include <wchar.h>

wint_t fputwc(wchar_t wc, FILE *stream);
wint_t putwc(wchar_t wc, FILE *stream);
wint_t putwchar(wchar_t wc);

wint_t fputwc_unlocked(wchar_t wc, FILE *stream);  /* __USE_GNU */
wint_t putwc_unlocked(wchar_t wc, FILE *stream);   /* __USE_GNU */
wint_t putwchar_unlocked(wchar_t wc);              /* __USE_GNU */
```

The plain forms are in the wide-character I/O block of `wchar.h`
(`/usr/include/wchar.h` lines 949-956) with no additional
feature-test gate; the `_unlocked` forms are in the `__USE_GNU` block
(lines 982-1037), commented there as faster versions when locking is
not necessary.

## Semantics

`fputwc` is the wide-character equivalent of `fputc`: it writes `wc` to
`stream` and returns `wc`. If `ferror(stream)` becomes true, or the
conversion of `wc` to the stream's encoding fails, it returns `WEOF`
and in the conversion-failure case sets `errno` to `EILSEQ`
(`fputwc(3)`). `putwc` behaves identically but may be a macro that
evaluates its arguments more than once. `putwchar` is `putwc(wc,
stdout)` (`putwchar(3)`). What actually hits the descriptor is the
multibyte sequence corresponding to `wc` under the current locale, not
raw `wchar_t` bytes.

## Gotchas and portability

- Return `WEOF` is the only failure signal; `errno == EILSEQ` flags a
  conversion error, `ferror(stream)` flags a stream error.
- No newline handling: the function writes exactly one wide character;
  newline translation to the stream encoding still applies to the
  multibyte output under the locale.
- The stream must already be (or become) wide oriented; mixing with
  narrow operations is undefined and undiagnosed (`fwide(3)`).
- musl 1.2.5: all six present; `_unlocked` forms need `_GNU_SOURCE`
  (`musl include/wchar.h` lines 145-153, `src/stdio/`).

## References

- glibc manual: `stdio.texi`, nodes *Streams and I18N*, *Simple Output*
- man3: `fputwc(3)`, `putwchar(3)`, `unlocked_stdio(3)`
- headers: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
