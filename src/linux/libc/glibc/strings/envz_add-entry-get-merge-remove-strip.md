# `envz_add` / `envz_entry` / `envz_get` / `envz_merge` / `envz_remove` / `envz_strip` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `envz.h` (which includes `argz.h`) |
| Standards | GNU extension (`envz_add(3)` CONFORMING TO; manual `@standards{GNU, envz.h}`) |
| Exported | `envz_add@@GLIBC_2.2.5`, `envz_entry@@GLIBC_2.2.5`, `envz_get@@GLIBC_2.2.5`, `envz_merge@@GLIBC_2.2.5`, `envz_remove@@GLIBC_2.2.5`, `envz_strip@@GLIBC_2.2.5`, all strong T symbols (nm, host glibc 2.41) |
| Thread-safety | MT-Safe for all six (`envz_add(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-envz_add, GLIBC-envz_entry, GLIBC-envz_get, GLIBC-envz_merge, GLIBC-envz_remove, GLIBC-envz_strip |

## Declaration and gates

```c
#include <envz.h>

char   *envz_entry(const char *restrict envz, size_t envz_len,
                   const char *restrict name);
char   *envz_get(const char *restrict envz, size_t envz_len,
                 const char *restrict name);
error_t envz_add(char **restrict envz, size_t *restrict envz_len,
                 const char *restrict name, const char *restrict value);
error_t envz_merge(char **restrict envz, size_t *restrict envz_len,
                   const char *restrict envz2, size_t envz2_len,
                   int override);
void    envz_remove(char **restrict envz, size_t *restrict envz_len,
                    const char *restrict name);
void    envz_strip(char **restrict envz, size_t *restrict envz_len);
```

No feature-test gates; `envz.h` is a GNU-only header that includes
`argz.h` (and `errno.h` for `error_t`). Declarations sit at
`/usr/include/envz.h` lines 33-41 (entry/get) and 49-70 (add, merge,
remove, strip).

## Semantics

An envz vector is an argz vector whose elements have the form
`name=value`; everything after the first `=` is the value. An element
with no `=` is a *null* entry - distinct from an entry with an empty
value (manual, *Envz Functions*). `envz_entry` returns a pointer to the
whole entry for `name`, `envz_get` returns a pointer to the value
portion. `envz_add` inserts `name=value` (or just `name` when `value` is
NULL, creating a null entry), removing any same-name entry first.
`envz_merge` adds every entry of `envz2` as if by `envz_add`, with
`envz2` values superseding existing ones only when `override` is true.
`envz_remove` deletes one entry; `envz_strip` drops all null entries
(`envz_add(3)`, manual).

## Gotchas and portability

- The NULL/empty distinction is the trap: `envz_get` returns `0` both for
  "no such name" and for a null entry, so a NULL result is ambiguous
  unless `envz_entry` confirms presence; a trailing `=` yields the empty
  string `""`, not NULL (`envz_add(3)` DESCRIPTION, manual).
- Allocating forms (`envz_add`, `envz_merge`) return `0` or `ENOMEM`,
  same `error_t` contract as argz; the vector is `malloc`-owned.
- In `envz_merge`, a null entry in the destination counts as present:
  with `override` false it blocks the same-named `envz2` entry from being
  added (manual, *Envz Functions*).
- musl 1.2.5 has no envz support (no `envz.h`, no implementation), like
  argz.

## References

- glibc manual: `string.texi`, nodes *Argz and Envz Vectors*,
  *Envz Functions*
- man3: `envz_add(3)` (single page covers all six envz functions)
- header: `/usr/include/envz.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
