# `lsearch` / `lfind` (3) - glibc

> Split from the chapter *glibc: Searching and Sorting* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `search.h` |
| Standards | SVr4, 4.3BSD, POSIX.1-2001/2008 |
| Exported | `lsearch@@GLIBC_2.2.5`, `lfind@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe both (`lsearch(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-lsearch, GLIBC-lfind |

## Declaration and gates

```c
#include <search.h>

void *lfind(const void *key, const void *base, size_t *nmemb,
            size_t size, int (*compar)(const void *, const void *));
void *lsearch(const void *key, void *base, size_t *nmemb,
              size_t size, int (*compar)(const void *, const void *));
```

`/usr/include/search.h` lines 171-179, inside the
`#if defined __USE_MISC || defined __USE_XOPEN_EXTENDED` block that
opens at line 29 -- the same exposure gate as the rest of the search
family, so strict ISO C dialects need `_DEFAULT_SOURCE`-grade feature
selection (glibc's default does it).

## Semantics

Both functions run a linear scan over an array at `base` of
`*nmemb` elements, each `size` bytes, calling `compar(key, member)` per
element; zero means a match. `lfind` is the read-only probe: it returns
a pointer to the matching element, or NULL when there is none.
`lsearch` adds insert-if-missing: on a miss it copies `key` into the
slot immediately after the last element and increments `*nmemb`
(`lsearch(3)`). The return value is then a pointer to the freshly added
member.

## Gotchas and portability

- `lsearch` writes past `*nmemb` elements on insertion -- the caller
  must guarantee the buffer really has room for `*nmemb + 1` elements,
  or the write corrupts memory. There is no overflow report.
- O(n) probes: fine for tiny tables, wrong for anything searched
  repeatedly; `bsearch` (sorted arrays), `hsearch` and `tsearch` live
  on the same `search.h` shelf for a reason.
- The man page's BUGS entry says it plainly: "The naming is
  unfortunate" (`lsearch(3)`).
- Since `*nmemb` is in/out, the same array cannot be shared by threads
  doing concurrent inserts without external locking.
- musl 1.2.5 provides both (`musl src/search/lsearch.c`).

## References

- glibc manual: `search.texi`, node *Array Search Function*
- man3: `lsearch(3)` (covers `lfind`)
- headers: `/usr/include/search.h`
- musl: `include/search.h`, `src/search/lsearch.c`
