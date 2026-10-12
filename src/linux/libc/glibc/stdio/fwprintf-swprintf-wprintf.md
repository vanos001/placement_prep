# `fwprintf` / `swprintf` / `wprintf` / `vfwprintf` / `vswprintf` / `vwprintf` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` (ledger row `wprintf` names `stdio.h`; the declarations are in `wchar.h`) |
| Standards | C95 (Amendment 1) / C99 / POSIX.1-2001 |
| Exported | `fwprintf@@GLIBC_2.2.5`, `wprintf@@GLIBC_2.2.5`, `swprintf@@GLIBC_2.2.5`, `vfwprintf@@GLIBC_2.2.5`, `vswprintf@@GLIBC_2.2.5`, `vwprintf@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe locale all (`wprintf(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-fwprintf, GLIBC-swprintf, GLIBC-vfwprintf, GLIBC-vswprintf, GLIBC-vwprintf, GLIBC-wprintf |

## Declaration and gates

```c
#include <wchar.h>

int fwprintf(FILE *restrict stream, const wchar_t *restrict format, ...);
int wprintf(const wchar_t *restrict format, ...);
int swprintf(wchar_t *restrict ws, size_t n,
             const wchar_t *restrict format, ...);
int vfwprintf(FILE *restrict s, const wchar_t *restrict format,
              va_list ap);
int vwprintf(const wchar_t *restrict format, va_list ap);
int vswprintf(wchar_t *restrict s, size_t n,
              const wchar_t *restrict format, va_list ap);
```

All six sit in the `#if defined __USE_ISOC95 || defined __USE_UNIX98`
block of `wchar.h` (`/usr/include/wchar.h` lines 722, 732-766). The man
page's feature-test gate is `_XOPEN_SOURCE >= 500 || _ISOC99_SOURCE ||
_POSIX_C_SOURCE >= 200112L` (`wprintf(3)`).

## Semantics

These are the wide-character counterparts of the `printf` family: the
format string is `wchar_t *` and the return value counts *wide
characters* written (`wprintf(3)`, manual *Formatted Output
Functions*). `wprintf`/`vwprintf` write to `stdout`, which must not be
byte oriented. `swprintf`/`vswprintf` store into `ws` with a trailing
null wide character counted against the `n` limit -- they correspond to
`snprintf`, not `sprintf` (manual, *Formatted Output Functions*).

## Errors

On error the functions return `-1`. glibc sets `errno = E2BIG` when
`swprintf` output does not fit, a GNU extension (manual). A failing
`EILSEQ` conversion of argument or format characters is also possible
(manual, *Formatted Output* error table).

## Gotchas and portability

- The truncation contract differs from `snprintf`: `swprintf` returns a
  negative value instead of the would-be length, and glibc sets `E2BIG`
  (`wprintf(3)`, manual).
- Non-ASCII wide characters in the format string require the runtime
  `LC_CTYPE` to match the compile-time locale; glibc `wchar_t` values
  are Unicode code points, other platforms differ (`wprintf(3)` NOTES).
- musl 1.2.5: all six present (`musl src/stdio/fwprintf.c`,
  `vfwprintf.c`, `vswprintf.c`, `vwprintf.c`).

## References

- glibc manual: `stdio.texi`, nodes *Formatted Output Functions*,
  *Variable Arguments Output*, *Streams and I18N*
- man3: `wprintf(3)` (covers the family)
- headers: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
