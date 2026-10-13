# `wcscmp` / `wcsncmp` / `wcscasecmp` / `wcsncasecmp` / `wcsnlen` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | C99 / POSIX.1-2001 (`wcscmp`, `wcsncmp`); POSIX.1-2008 (`wcscasecmp`, `wcsncasecmp`, `wcsnlen`) |
| Exported | `wcscmp@@GLIBC_2.2.5`, `wcsncmp@@GLIBC_2.2.5`, `wcsnlen@@GLIBC_2.2.5` (ifunc symbols), `wcscasecmp@@GLIBC_2.2.5`, `wcsncasecmp@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | `wcscmp`, `wcsncmp`, `wcsnlen`: MT-Safe; `wcscasecmp`, `wcsncasecmp`: MT-Safe locale (man ATTRIBUTES) |
| Ledger ID | GLIBC-wcscmp, GLIBC-wcsncmp, GLIBC-wcscasecmp, GLIBC-wcsncasecmp, GLIBC-wcsnlen |

## Declaration and gates

```c
#include <wchar.h>

int wcscmp(const wchar_t *s1, const wchar_t *s2);
int wcsncmp(const wchar_t *s1, const wchar_t *s2, size_t n);

int wcscasecmp(const wchar_t *s1, const wchar_t *s2);
int wcsncasecmp(const wchar_t *s1, const wchar_t *s2, size_t n);
size_t wcsnlen(const wchar_t *s, size_t maxlen);
```

`wcscmp`/`wcsncmp` are unconditional (`/usr/include/wchar.h` lines
130-134); the case-insensitive pair sits under `__USE_XOPEN2K8` at lines
136-145, and `wcsnlen` under its own `__USE_XOPEN2K8` block at lines
263-266. Man pages record `_POSIX_C_SOURCE >= 200809L` since glibc 2.10,
`_GNU_SOURCE` before, for the three later additions.

## Semantics

`wcscmp` compares two wide strings and returns negative/zero/positive as
`s1` orders before/equal/after `s2` at the first differing position
(`wcscmp(3)`); `wcsncmp` bounds the comparison to `n` wide characters
and stops at the first L'\0' in either string (`wcsncmp(3)`).
`wcscasecmp`/`wcsncasecmp` fold case with `towupper`/`towlower` before
comparing (`wcscasecmp(3)`). `wcsnlen` returns `wcslen(s)` capped at
`maxlen`, never examining `s+maxlen` or beyond - `maxlen` counts wide
characters, not bytes (`wcsnlen(3)`).

## Gotchas and portability

- Case folding is locale-dependent: both case-insensitive man pages
  carry a NOTES that behavior depends on the `LC_CTYPE` category, and
  their ATTRIBUTES say `MT-Safe locale`. Only the sign of the result is
  meaningful; magnitude is unspecified, as for the narrow family.
- `wcsnlen` parameter confusion is the classic wide-string bug: a
  `sizeof(buf)` byte count over-scopes by `sizeof(wchar_t)` (4 on
  x86-64).
- The plain length function `wcslen` is already documented in
  [strlen-sizeof.md](strlen-sizeof.md) alongside `strlen`/`strnlen`;
  this page covers the rest of the comparison family.
- Locale-taking twins `wcscasecmp_l`/`wcsncasecmp_l` share the
  `__USE_XOPEN2K8` block (wchar.h lines 146-152).
- musl 1.2.5 ships all five, plus the `_l` variants
  (`musl include/wchar.h` lines 166-174).

## References

- glibc manual: `string.texi`, node *String/Array Comparison* (wide
  comparisons inline)
- man3: `wcscmp(3)` (covers `wcsncmp`), `wcscasecmp(3)` (covers
  `wcsncasecmp`), `wcsnlen(3)`
- header: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
