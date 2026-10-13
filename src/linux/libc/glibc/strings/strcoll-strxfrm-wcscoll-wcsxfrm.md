# `strcoll` / `strxfrm` / `wcscoll` / `wcsxfrm` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` (`strcoll`, `strxfrm`); `wchar.h` (`wcscoll`, `wcsxfrm`) |
| Standards | ISO C / POSIX.1-2001 (`strcoll`, `strxfrm` - C89/C99 per `strcoll(3)`); POSIX / XPG (`wcscoll`, `wcsxfrm`; no cached man page, manual documents them inline) |
| Exported | `strcoll@@GLIBC_2.2.5`, `strxfrm@@GLIBC_2.2.5` (strong), `wcscoll@@GLIBC_2.2.5`, `wcsxfrm@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe locale (`strcoll(3)`, `strxfrm(3)` ATTRIBUTES; manual `@mtslocale` notes for the wide pair) |
| Ledger ID | GLIBC-strcoll, GLIBC-strxfrm, GLIBC-wcscoll, GLIBC-wcsxfrm |

## Declaration and gates

```c
#include <string.h>
int    strcoll(const char *s1, const char *s2);
size_t strxfrm(char *restrict dest, const char *restrict src, size_t n);

#include <wchar.h>
int    wcscoll(const wchar_t *s1, const wchar_t *s2);
size_t wcsxfrm(wchar_t *restrict dest, const wchar_t *restrict src,
               size_t n);
```

`strcoll`/`strxfrm` are unconditional in `/usr/include/string.h` (lines
163-168); `wcscoll`/`wcsxfrm` unconditional in `/usr/include/wchar.h`
(lines 155-160). Locale-taking twins `strcoll_l`/`strxfrm_l` and
`wcscoll_l`/`wcsxfrm_l` sit under `__USE_XOPEN2K8` (string.h lines
171-181, wchar.h lines 162-175).

## Semantics

Both pairs compare strings using the `LC_COLLATE` ordering of the
current locale instead of raw code-point order - Spanish accents
collating with their base letters and Czech `ch` sorting between `h`
and `i` are the manual's examples (*Collation Functions*). `strcoll`/
`wcscoll` apply the collation mapping implicitly for one comparison;
`strxfrm`/`wcsxfrm` apply it explicitly, writing up to `n` units of the
transformed form so that `strcmp`/`wcscmp` on transformed strings equals
`strcoll`/`wcscoll` on the originals. They return the full length the
transformed string needs (excluding the terminator); if that is `n` or
more, the contents of `dest` are indeterminate (`strxfrm(3)`). In the C
locale all four degenerate to `strcmp`/`wcscmp` (`strcoll(3)` NOTES,
manual).

## Gotchas and portability

- Two-call sizing idiom: `strxfrm(NULL, src, 0)` to measure, allocate,
  transform once - then compare with `strcmp`. The manual recommends
  transforming once for repeated comparisons (sort keys) as the
  efficient path.
- Results are locale-bound: after `setlocale(LC_COLLATE, ...)` changes,
  previously transformed keys are stale; comparisons made with the
  narrow family (`strcmp`) are not interchangeable with collated ones.
- The magnitude of nonzero returns is unspecified, as everywhere in the
  compare family.
- musl 1.2.5 ships all four (`musl include/wchar.h` lines 61-62 for the
  wide pair; locale support limited to C/UTF-8).

## References

- glibc manual: `string.texi`, node *Collation Functions* (all four,
  qsort example)
- man3: `strcoll(3)`, `strxfrm(3)`; no cached `wcscoll(3)`/`wcsxfrm(3)`
  man pages (manual is the wide-pair authority)
- headers: `/usr/include/string.h`, `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
