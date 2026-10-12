# `wcsftime` (3) - glibc

> Split from the chapter *glibc: Formatting Calendar Time* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` (also reachable via `time.h` includes; `_l` twin under `__USE_GNU`) |
| Standards | ISO C99, POSIX.1-2001/2008 |
| Exported | `wcsftime@@GLIBC_2.2.5`, `wcsftime_l@@GLIBC_2.3` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `env locale` (manual `@mtsenv @mtslocale` safety comment, `time.texi`; no man page exists for it) |
| Ledger ID | GLIBC-wcsftime, GLIBC-wcsftime_l |

## Declaration and gates

```c
#include <wchar.h>

size_t wcsftime(wchar_t *restrict s, size_t maxsize,
                const wchar_t *restrict format,
                const struct tm *restrict tp);      /* lines 1043-1046 */

#ifdef __USE_GNU                                    /* lines 1048-1052 */
size_t wcsftime_l(wchar_t *restrict s, size_t maxsize,
                  const wchar_t *restrict format,
                  const struct tm *restrict tp, locale_t locale);
#endif
```

Both prototypes are unconditional in `/usr/include/wchar.h` (lines
1043-1046); `wcsftime_l` needs `_GNU_SOURCE` (header lines 1048+
) and is a GNU/POSIX-2008 locale twin.

## Semantics

`wcsftime` is `strftime` for wide strings: it formats the
broken-down time `*tp` into the wide buffer `s` (at most `maxsize`
wide characters, NUL-terminated on success) according to the wide
`format`. The manual states it supports the same flags, modifiers and
conversion specifiers as `strftime` -- including the GNU extensions
-- and returns the number of wide characters placed in the array,
excluding the terminating L'\0' (`time.texi`, `wcsftime` entry).
Returning 0 signals that the output would have exceeded `maxsize`
(and the buffer content is then unspecified), so a zero return must
be distinguished from "empty result" by the caller.

## Gotchas and portability

- The format string is wide (`L"%Y-%m-%d"`), not narrow -- a plain
  `"%Y"` literal is a type error caught at compile time, the usual
  first-contact bug.
- Zero return means "would not fit", matching `strftime`; there is no
  `errno` contract on this path.
- Locale-dependent output: results change with `LC_TIME` (and the
  manual's `@mtslocale` annotation); use `wcsftime_l` to pin a locale
  object.
- No `wcsftime(3)` man page exists in the man-pages tree on this
  host; semantics here follow the glibc manual and the header.
- musl 1.2.5 implements `wcsftime` (`src/time/wcsftime.c`); the
  `_l` twin is glibc-side only.

## References

- glibc manual: `time.texi`, node *Formatting Calendar Time*
  (`wcsftime`, `wcsftime_l` entries)
- headers: `/usr/include/wchar.h` (lines 1036-1052)
- symbols: `nm -D libc.so.6`
- musl: `src/time/wcsftime.c`
