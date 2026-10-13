# `argz_add` / `argz_add_sep` / `argz_append` / `argz_count` / `argz_create` / `argz_create_sep` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `argz.h` |
| Standards | GNU extension (`argz_add(3)` CONFORMING TO; manual `@standards{GNU, argz.h}`) |
| Exported | `argz_add@@GLIBC_2.2.5`, `argz_add_sep@@GLIBC_2.2.5`, `argz_append@@GLIBC_2.2.5`, `argz_count@@GLIBC_2.2.5`, `argz_create@@GLIBC_2.2.5`, `argz_create_sep@@GLIBC_2.2.5`, all weak (nm, host glibc 2.41) |
| Thread-safety | MT-Safe for the whole argz family (`argz_add(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-argz_add, GLIBC-argz_add_sep, GLIBC-argz_append, GLIBC-argz_count, GLIBC-argz_create, GLIBC-argz_create_sep |

## Declaration and gates

```c
#include <argz.h>

error_t argz_add(char **restrict argz, size_t *restrict argz_len,
                 const char *restrict str);
error_t argz_add_sep(char **restrict argz, size_t *restrict argz_len,
                     const char *restrict str, int delim);
error_t argz_append(char **restrict argz, size_t *restrict argz_len,
                    const char *restrict buf, size_t buf_len);
size_t  argz_count(const char *argz, size_t argz_len);
error_t argz_create(char *const argv[], char **restrict argz,
                    size_t *restrict argz_len);
error_t argz_create_sep(const char *restrict str, int sep,
                        char **restrict argz, size_t *restrict argz_len);
```

`argz.h` declares all of these unconditionally - there is no feature-test
gate; the file is itself a GNU-only header. It defines `error_t` as `int`
unless `__error_t_defined` is already set (`/usr/include/argz.h` lines
30-32); the allocation functions sit at lines 40-55 (create/count) and
70-84 (append/add/add_sep).

## Semantics

An argz vector is `(pointer, length)` describing a block holding
null-terminated strings back to back; the last byte must be null when the
length is nonzero, and `(NULL, 0)` is the empty vector (`argz_add(3)`
DESCRIPTION). `argz_create` converts a NULL-terminated `argv` array into
an argz vector; `argz_create_sep` builds one by splitting `str` at every
occurrence of byte `sep`. `argz_count` returns the number of elements
(the number of null bytes). `argz_add` appends one string to the end of
`*argz`, updating `*argz` and `*argz_len`; `argz_add_sep` does the same
after splitting `str` at `delim` (the classic use is a `:`-separated
search path). `argz_append` appends a raw `(buf, buf_len)` argz block and
grows `*argz_len` by exactly `buf_len` (`argz_add(3)`, manual *Argz
Functions*).

## Gotchas and portability

- All allocating forms return `error_t`: `0` on success, `ENOMEM` only on
  allocation failure - there is no `errno` contract to consult
  (`argz_add(3)` RETURN VALUE, manual *Argz Functions*).
- Storage is `malloc`/`realloc`-owned: any vector grown by these functions
  must have been obtained from `malloc` and may be released with `free`
  (manual, *Argz Functions*). Passing a stack or static buffer to a
  growing function is undefined.
- `argz_count` counts null bytes, so a malformed vector with an interior
  embedded empty string silently inflates the count; vectors without the
  terminating null can segfault the walkers (`argz_add(3)` BUGS).
- musl 1.2.5 has no argz support at all: neither `argz.h`/`envz.h` in
  `musl include/` nor any `argz_*` source under `src/` - GNU-only code
  needs a bundled copy on musl.

## References

- glibc manual: `string.texi`, nodes *Argz and Envz Vectors*,
  *Argz Functions*
- man3: `argz_add(3)` (single page covers all twelve argz functions)
- header: `/usr/include/argz.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
