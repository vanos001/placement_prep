# `bcopy` / `bzero` / `index` / `rindex` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `strings.h` |
| Standards | 4.3BSD origin; marked LEGACY in POSIX.1-2001; **removed** in POSIX.1-2008 |
| Exported | `bcopy@@GLIBC_2.2.5`, `bzero@@GLIBC_2.2.5` (weak), `index@@GLIBC_2.2.5`, `rindex@@GLIBC_2.2.5` (nm, host glibc 2.41; `index`/`strchr` and `rindex`/`strrchr` share addresses - alias evidence) |
| Thread-safety | MT-Safe (`bcopy(3)`, `index(3)`, `bzero(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-bcopy, GLIBC-bzero, GLIBC-index, GLIBC-rindex |

## Declaration and gates

```c
#include <strings.h>

void bcopy(const void *src, void *dest, size_t n);  /* args NOT like memcpy */
void bzero(void *s, size_t n);
char *index(const char *s, int c);                  /* == strchr */
char *rindex(const char *s, int c);                 /* == strrchr */
```

Declared in `strings.h` under `__USE_MISC || !__USE_XOPEN2K8`
(`/usr/include/strings.h` lines 32-99): visible in default builds,
suppressed by strict POSIX macro sets. `strings.h` also declares `bcmp`
under the same gate.

## Semantics

`bcopy` copies `n` bytes from `src` to `dest` and handles overlapping
areas like `memmove`; it returns nothing (`bcopy(3)`). `bzero` zeroes
`n` bytes at `s` (`bzero(3)`). `index`/`rindex` are `strchr`/`strrchr`
under their BSD names, terminator included (`index(3)`). All return no
value (the two search functions return `char *`).

## Gotchas and portability

- Argument-order trap: `bcopy(src, dest, n)` reverses the memcpy operand
  order; `bcopy(3)` CONFORMING TO explicitly warns "the first two
  arguments are interchanged for memcpy(3) and memmove(3)". Translated
  code is the primary source of `bcopy`-induced corruption.
- Obsolescence is documented, not folkloric: POSIX.1-2001 marked all four
  LEGACY and POSIX.1-2008 removed their specifications, directing users
  to `memcpy`/`memmove`/`memset`/`strchr`/`strrchr`
  (`bcopy(3)`, `bzero(3)`, `index(3)` CONFORMING TO).
- `bzero` is `memset(s, 0, n)`; but for secrets prefer `explicit_bzero`,
  which the compiler may not elide (`bzero(3)` page covers both).
- Header hygiene: in strict `_POSIX_C_SOURCE >= 200809L` builds glibc
  hides these declarations, so legacy code needs `_DEFAULT_SOURCE` (or
  its pre-2.19 `_BSD_SOURCE`) to compile (`strings.h` gate).
- nm alias evidence on this host: `index` shares the address of `strchr`
  (0x...a8080) and `rindex` of `strrchr` (0x...aa2a0), i.e. the BSD names
  are literal aliases, so there is no behavioral difference left.
- musl 1.2.5 keeps all four for compatibility
  (`musl src/string/{bcopy,bzero,index,rindex}.c`).

## References

- glibc manual: `string.texi` (legacy BSD names appear in the copy and
  search nodes only as contrasts)
- man3: `bcopy(3)`, `bzero(3)` (covers `explicit_bzero`), `index(3)`
  (covers `rindex`)
- header: `/usr/include/strings.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
