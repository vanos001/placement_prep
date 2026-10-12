# `qsort` / `qsort_r` / `bsearch` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` |
| Standards | ISO C89 / POSIX.1-2001 (`qsort`, `bsearch`); GNU (`qsort_r`) |
| Exported | `qsort@@GLIBC_2.2.5`, `qsort_r@@GLIBC_2.8` (weak), `bsearch@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`qsort(3)`, `bsearch(3)` ATTRIBUTES), modulo a thread-unsafe comparator |
| Ledger ID | GLIBC-qsort, GLIBC-qsort_r, GLIBC-bsearch |

## Declaration and gates

```c
#include <stdlib.h>

typedef int (*__compar_fn_t)(const void *, const void *);

void   qsort(void *base, size_t nmemb, size_t size, __compar_fn_t compar);
void  *bsearch(const void *key, const void *base, size_t nmemb,
               size_t size, __compar_fn_t compar);

/* GNU: comparator takes a caller context pointer */
typedef int (*__compar_d_fn_t)(const void *, const void *, void *);
void qsort_r(void *base, size_t nmemb, size_t size,
             __compar_d_fn_t compar, void *arg);
```

`qsort_r` is under `__USE_GNU` in the installed header
(`/usr/include/stdlib.h` lines 947-993); `qsort(3)` records `_GNU_SOURCE`
and "added to glibc in version 2.8".

## Semantics

`qsort` sorts `nmemb` elements of `size` bytes at `base` into ascending
order per `compar`, which receives two element pointers and must return
negative / zero / positive as the first element orders before / equal /
after the second (`qsort(3)`). Returns nothing. `bsearch` finds an element
matching `key` in an array already sorted ascending under the *same*
`compar` (with `key` passed as the first argument) and returns a pointer to
it, or `NULL` (`bsearch(3)`).

## Gotchas and portability

- `qsort` is **not stable**: "If two members compare as equal, their order
  in the sorted array is undefined" (`qsort(3)`). Sorting by a secondary
  key requires folding it into the comparator.
- The comparator contract is total ordering: inconsistent comparators
  (e.g. returning "equal" for distinct elements that then compare
  differently through other paths) corrupt both `qsort` and `bsearch`
  results; `bsearch` additionally requires the *exact* ordering used for
  sorting, with `key` as first argument (`bsearch(3)` DESCRIPTION).
- Duplicate matches: when several elements compare equal to `key`, which
  one `bsearch` returns is unspecified (`bsearch(3)` RETURN VALUE).
- `qsort_r` exists precisely to avoid globals in comparators and is the
  reentrant form (`qsort(3)` DESCRIPTION); its signature (extra `arg`
  last) is GNU-specific and differs from some BSDs.
- Size zero and `nmemb <= 1`: glibc 2.39 NEWS lists the early-return fix
  for `nmemb <= 1` (bug 19305); glibc 2.42 NEWS fixes a `qsort` memory
  leak when a C++ exception is thrown from the comparison function
  (bug 32058).
- musl 1.2.5 implements its own in-place algorithm
  (`musl src/stdlib/qsort.c`, Valentin Ochs) with the same contract.

## References

- glibc manual: `search.texi` (Searching and Sorting chapter)
- man3: `qsort(3)` (covers `qsort_r`), `bsearch(3)`
- header: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
