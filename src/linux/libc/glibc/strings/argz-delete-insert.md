# `argz_delete` / `argz_extract` / `argz_insert` / `argz_next` / `argz_replace` / `argz_stringify` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `argz.h` |
| Standards | GNU extension (`argz_add(3)` CONFORMING TO; manual `@standards{GNU, argz.h}`) |
| Exported | `argz_delete@@GLIBC_2.2.5` (strong), `argz_extract@@GLIBC_2.2.5`, `argz_insert@@GLIBC_2.2.5`, `argz_next@@GLIBC_2.2.5`, `argz_replace@@GLIBC_2.2.5`, `argz_stringify@@GLIBC_2.2.5` (rest weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe for the whole argz family (`argz_add(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-argz_delete, GLIBC-argz_extract, GLIBC-argz_insert, GLIBC-argz_next, GLIBC-argz_replace, GLIBC-argz_stringify |

## Declaration and gates

```c
#include <argz.h>

void   argz_delete(char **restrict argz, size_t *restrict argz_len,
                   char *restrict entry);
void   argz_extract(const char *restrict argz, size_t argz_len,
                    char **restrict argv);
error_t argz_insert(char **restrict argz, size_t *restrict argz_len,
                    char *restrict before, const char *restrict entry);
char  *argz_next(const char *restrict argz, size_t argz_len,
                 const char *restrict entry);
error_t argz_replace(char **restrict argz, size_t *restrict argz_len,
                     const char *restrict str, const char *restrict with,
                     unsigned int *restrict replace_count);
void   argz_stringify(char *argz, size_t len, int sep);
```

No feature-test gates: `argz.h` declares all of these unconditionally.
The declarations live at `/usr/include/argz.h` lines 61-67 (extract,
stringify), 88-90 (delete), 98-101 (insert), 106-110 (replace) and
126-151 (`__argz_next` plus an inline `argz_next` wrapper).

## Semantics

`argz_delete` removes the element that `entry` points at, reallocating
`*argz` as needed; `argz_insert` is its inverse, inserting `entry` just
before the element `before` (or at the end when `before` is NULL; passing
`*argz` as `before` inserts at the beginning, since the first element
*is* `*argz`). `argz_extract` is the opposite of `argz_create`: it fills
a caller-supplied `argv` array with pointers to the elements plus a NULL
terminator. `argz_next` walks the vector: NULL `entry` yields the first
element, and NULL is returned after the last. `argz_replace` substitutes
each occurrence of `str` with `with`, reallocating as necessary and
bumping `*replace_count` when non-NULL. `argz_stringify` flattens the
vector back into one string by replacing every null byte except the last
with `sep` (manual, *Argz Functions*; `argz_add(3)`).

## Gotchas and portability

- Destructive argz functions reallocate, so pointers into the vector
  (such as an `entry` being deleted) are invalidated by the call - the
  manual calls this out explicitly for `argz_delete`.
- `argz_extract` writes `argz_count(argz, argz_len) + 1` pointers; the
  pointers alias `argz` rather than copying it, so the vector must stay
  put while `argv` lives (manual, *Argz Functions*). This is the intended
  bridge to `exec`-style argv vectors.
- `argz_next` supports two loop shapes (while with NULL seed, or for over
  `entry = argz`); the for shape requires the empty-vector-is-NULL
  invariant that the argz creators maintain.
- musl 1.2.5 has no argz support (no header, no implementation) - see the
  argz creation page for the same note.

## References

- glibc manual: `string.texi`, nodes *Argz and Envz Vectors*,
  *Argz Functions*
- man3: `argz_add(3)` (single page covers all twelve argz functions)
- header: `/usr/include/argz.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
