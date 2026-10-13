# `strspn` / `strcspn` / `strpbrk` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` |
| Standards | ISO C, POSIX.1-2001/2008, SVr4, 4.3BSD |
| Exported | `strspn@@GLIBC_2.2.5`, `strcspn@@GLIBC_2.2.5`, `strpbrk@@GLIBC_2.2.5`, all ifunc-selected (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`strspn(3)`, `strpbrk(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strspn, GLIBC-strcspn, GLIBC-strpbrk |

## Declaration and gates

```c
#include <string.h>

size_t strspn(const char *s, const char *accept);
size_t strcspn(const char *s, const char *reject);
char  *strpbrk(const char *s, const char *accept);
```

No feature-test gates; all three are ISO C (`/usr/include/string.h` lines
291-325, all marked `__attribute_pure__`).

## Semantics

`strspn` returns the length in bytes of the initial segment of `s` made up
entirely of bytes from `accept`; `strcspn` the length of the initial segment
made up entirely of bytes *not* in `reject` (`strspn(3)`). `strpbrk`
returns a pointer to the first byte in `s` that appears in `accept`, or
`NULL` if none does (`strpbrk(3)`). The manual groups all three in the
*Search Functions* node of `string.texi`.

## Gotchas and portability

- `strcspn(s, "")` is the allocation-free `strlen(s)`; `strcspn(s, "\n")`
  strips a trailing newline index for line buffers. The empty-set edge works
  because the terminator counts as a member of every `reject` set.
- `strspn`/`strcspn` return lengths, not pointers; a common bug is testing
  them for truthiness instead of comparing against `strlen(s)` to decide
  "string consists solely of ...".
- `strpbrk` is `strchr` generalized to a set; when the set has one member it
  degenerates to `strchr`, and `strcspn(s, reject)` equals
  `strpbrk(s, reject) ? strpbrk(s, reject) - s : strlen(s)`.
- These functions scan `accept`/`reject` for every position of `s`, so cost
  is O(len(s) * len(set)); glibc's ifunc-selected implementations mitigate
  but do not change the bound (nm shows `i`/ifunc symbols).
- All three are `const`-correct and do not modify their inputs; they are
  safe building blocks for lexers, but they cannot express "not in set A and
  in set B" without composition.
- musl 1.2.5 ships equivalent implementations
  (`musl src/string/strspn.c`, `strcspn.c`, `strpbrk.c`).

## References

- glibc manual: `string.texi`, node *Search Functions*
- man3: `strspn(3)` (covers `strcspn` via `.so` alias `strcspn.3`),
  `strpbrk(3)`
- header: `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
