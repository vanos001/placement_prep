# `strtok` / `strtok_r` / `strsep` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` |
| Standards | ISO C / POSIX.1-2001 (`strtok`); POSIX.1-2001 (`strtok_r`); 4.4BSD (`strsep`) |
| Exported | `strtok@@GLIBC_2.2.5`, `strtok_r@@GLIBC_2.2.5` (weak), `strsep@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | `strtok`: MT-Unsafe race:strtok; `strtok_r`, `strsep`: MT-Safe (`strtok(3)`, `strsep(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strtok, GLIBC-strtok_r, GLIBC-strsep |

## Declaration and gates

```c
#include <string.h>

char *strtok(char *restrict str, const char *restrict delim);
char *strtok_r(char *restrict str, const char *restrict delim,
               char **restrict saveptr);   /* gate: _POSIX_C_SOURCE */
char *strsep(char **restrict stringp, const char *restrict delim);
```

`strtok_r` is declared under `__USE_POSIX` in `string.h` (lines 365-369);
glibc also keeps a private `__strtok_r`. `strsep` is under `__USE_MISC`
(lines 471-473); `strsep(3)` records the macro history as `_DEFAULT_SOURCE`
since glibc 2.19, `_BSD_SOURCE` before.

## Semantics

`strtok` breaks `str` into nonempty tokens separated by bytes from `delim`:
the first call passes the string, later calls pass `NULL`; runs of
delimiters count as one, leading and trailing delimiters are ignored. Each
found delimiter is overwritten with a null byte, and a static save pointer
carries the scan position (`strtok(3)`). Returns the next token or `NULL`.
`strtok_r` is the reentrant variant whose context lives in the caller's
`*saveptr`; on the first call `*saveptr` is ignored (some implementations,
e.g. Tru64, require `NULL` there - `strtok(3)` NOTES). `strsep` takes the
cursor as `char **`: it returns the original `*stringp`, overwrites the
delimiter with `'\0'`, advances `*stringp` past the token, and sets
`*stringp` to `NULL` when no delimiter remains; `*stringp == NULL` returns
`NULL` (`strsep(3)`).

## Gotchas and portability

- `strtok` mutates its input (delimiters become `'\0'`), cannot tokenize
  constant strings, loses the identity of the delimiter, and holds its
  position in static storage: `strtok(3)` BUGS lists all four.
- The static state makes concurrent `strtok` sequences in one process
  impossible; `strtok(3)` ATTRIBUTES marks it `MT-Unsafe race:strtok`.
  Same-process reentrancy breaks nested parsing loops too.
- `strtok` cannot return empty fields: `"a,,b"` with delimiter `","` yields
  two tokens. `strsep` exists precisely because of that (`strsep(3)` NOTES)
  and is the usual choice for parsing `:`-separated files like
  `PATH`/`passwd` fields.
- `delim` may change between calls for both families.
- musl 1.2.5 implements all three with the same contracts
  (`musl src/string/strtok.c`, `strtok_r.c`, `strsep.c`).

## References

- glibc manual: `string.texi`, node *Finding Tokens in a String*
- man3: `strtok(3)` (covers `strtok_r` via `.so` alias `strtok_r.3`),
  `strsep(3)`
- header: `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
