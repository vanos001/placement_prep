# fnmatch(3) - glibc

> Shell wildcard matching against a single string (manual chapter *Pattern Matching*, section *Wildcard Matching*). For filename expansion see [glob-globfree](./glob-globfree.md); for full shell word expansion see [wordexp](./wordexp.md).

| Field | Value |
|---|---|
| Header | `fnmatch.h` |
| Standards | POSIX.2 (`FNM_PATHNAME`, `FNM_PERIOD`, `FNM_NOESCAPE`); `FNM_FILE_NAME`, `FNM_LEADING_DIR`, `FNM_EXTMATCH` GNU; `FNM_CASEFOLD` GNU origin, standardized in POSIX.1-2024 |
| Exported | `fnmatch` `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe env locale (man3 ATTRIBUTES; manual safety annotation) |
| Ledger ID | `GLIBC-fnmatch` (Grouped FULL, glob+fnmatch entry) |

## Declaration and gates

```text
int fnmatch(const char *pattern, const char *string, int flags);
```

## Semantics

Tests whether `string` matches `pattern` (shell-style: `*`, `?`, `[...]`); returns `0` on match and the nonzero `FNM_NOMATCH` otherwise (manual). Flags:

| Flag | Effect |
|---|---|
| `FNM_PATHNAME` (alias `FNM_FILE_NAME`) | `/` must match `/` exactly; wildcards never span it |
| `FNM_PERIOD` | a leading `.` cannot be matched by wildcards; with `FNM_PATHNAME` also after each `/` |
| `FNM_NOESCAPE` | `\` is an ordinary character, no quoting |
| `FNM_LEADING_DIR` (GNU) | match succeeds if a leading directory component matches, ignoring the rest |
| `FNM_CASEFOLD` | case-insensitive comparison |
| `FNM_EXTMATCH` (GNU) | ksh-style extended patterns `?(list)`, `*(list)`, `+(list)`, `@(list)`, `!(list)` |

The manual notes one glibc quirk: "fnmatch might sometimes report errors by returning nonzero values that are not equal to FNM_NOMATCH", so test equality with `FNM_NOMATCH` rather than truthiness. `glob` implements its `GLOB_NOESCAPE`/`GLOB_PERIOD` handling by forwarding `FNM_NOESCAPE`/`FNM_PERIOD` to `fnmatch` (manual, *Flags for Globbing*).

## Gotchas and portability

- Flags are not uniform across systems: `FNM_CASEFOLD` and `FNM_LEADING_DIR` were long GNU-only (now POSIX.1-2024 for casefold); guard them with `#ifdef`.
- musl contrast: musl implements `fnmatch` in `src/regex/fnmatch.c` and honors `FNM_CASEFOLD` and `FNM_LEADING_DIR`; both headers reserve `FNM_NOSYS` (-1) for systems that cannot implement the function - glibc defines it but never returns it.

## References

- glibc manual section *Wildcard Matching*; man3 `fnmatch.3`; header `fnmatch.h`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 sources as cited.
