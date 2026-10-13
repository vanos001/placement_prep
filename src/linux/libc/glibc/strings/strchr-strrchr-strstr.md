# `strchr` / `strrchr` / `strchrnul` / `strstr` / `memmem` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` (`strchrnul`, `memmem`, `strcasestr`: GNU) |
| Standards | ISO C / POSIX.1-2001 (`strchr`, `strrchr`, `strstr`); GNU extensions (`strchrnul`, `memmem`, `strcasestr`) |
| Exported | `strchr@@GLIBC_2.2.5`, `strrchr@@GLIBC_2.2.5`, `strchrnul@@GLIBC_2.2.5`, `strstr@@GLIBC_2.2.5`, `memmem@@GLIBC_2.2.5` (weak), all ifunc-selected (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`strcasestr`: MT-Safe locale) per `strchr(3)`, `strstr(3)`, `memmem(3)` ATTRIBUTES |
| Ledger ID | GLIBC-strchr, GLIBC-strrchr, GLIBC-strchrnul, GLIBC-strstr, GLIBC-memmem |

## Declaration and gates

```c
#include <string.h>

char *strchr(const char *s, int c);
char *strrchr(const char *s, int c);
char *strstr(const char *haystack, const char *needle);

#define _GNU_SOURCE          /* strchrnul, memmem, strcasestr */
#include <string.h>
char *strchrnul(const char *s, int c);          /* __USE_MISC in string.h */
void *memmem(const void *h, size_t hl, const void *n, size_t nl);
char *strcasestr(const char *haystack, const char *needle);
```

Gates in `/usr/include/string.h`: `strchrnul` under `__USE_MISC` (lines
277-289), `memmem`/`strcasestr` under `__USE_MISC` (lines 371-393);
`memmem(3)` and `strstr(3)` document the `_GNU_SOURCE` spelling.

## Semantics

`strchr` returns a pointer to the first occurrence of byte `c` in `s`,
`strrchr` to the last; the terminating null is part of the string, so `c` of
`'\0'` returns a pointer to the terminator (`strchr(3)`). `strchrnul` is
`strchr` that returns `s + strlen(s)` instead of `NULL` on miss
(`strchr(3)`, manual *Search Functions*). `strstr` finds the first occurrence
of `needle` in `haystack`; an empty `needle` returns `haystack` itself
(`strstr(3)`). `memmem` is the binary (length-bounded) analogue over
`haystacklen`/`needlelen` bytes (`memmem(3)`).

## Gotchas and portability

- `strchr` NULL misses lose the position of the terminator; when you need
  "found or end-of-string" in one call, the manual recommends `strchrnul`
  over searching twice (manual *Search Functions*, `strchr` entry).
- `strchr(s, 0)` as a strlen replacement is legal but obscure; both manual
  and man page call out the terminator-is-part-of-the-string rule.
- `strchrnul` first appeared in glibc 2.1.1 (`strchr(3)` VERSIONS) and is a
  GNU extension: unportable outside glibc/BSD-derived libc.
- `memmem` had an argument-order bug through libc 5.0.9 and returned the
  last byte of `haystack` for an empty `needle` in glibc 2.0, fixed in 2.1
  (`memmem(3)` BUGS).
- `strcasestr` is MT-Safe *locale* because case folding consults
  `LC_CTYPE` (`strstr(3)` ATTRIBUTES).
- Bytes only: "character" here means byte; none of these work on multibyte
  or wide characters (`strchr(3)`).
- musl 1.2.5 implements all of these including the GNU extras
  (`musl src/string/strchrnul.c`, `src/string/memmem.c`).

## References

- glibc manual: `string.texi`, node *Search Functions*
- man3: `strchr(3)` (covers `strrchr`, `strchrnul`), `strstr(3)`, `memmem(3)`
- header: `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
