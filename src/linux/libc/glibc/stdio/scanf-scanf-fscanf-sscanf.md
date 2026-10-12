# `scanf` (scanf, fscanf, sscanf) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-scanf (group) |
| Header | `stdio.h` |
| Provenance | ISO C |
| Status | documented |

**Signature** -- `int scanf(const char *fmt, ...);` `int fscanf(FILE
*stream, const char *fmt, ...);` `int sscanf(const char *s, const char
*fmt, ...);` plus the ISO C99 `vscanf`/`vfscanf`/`vsscanf` `va_list`
forms.

**Conversions** (manual, *Table of Input Conversions*): `%d` signed
decimal; `%i` signed with C-constant prefix detection (`0x`, `0`); `%b`
binary (ISO C23); `%o`, `%u`, `%x` unsigned radix; `%e %f %g` float;
`%s` non-whitespace string; `%[` scanset string; `%c` raw characters
(width-bounded); `%p` pointer in `printf("%p")` format; `%n` stores
characters consumed so far, converts nothing; `%%` a literal percent.
Whitespace in the template matches any amount; ordinary characters must
match exactly.

**Return semantics** -- number of successful *assignments*; a matching
failure stops the scan and returns the count so far; `EOF` only when an
input failure (EOF or read error) happens *before* any conversion,
including whitespace and literal matching (`scanf(3)`, manual,
*Formatted Input Basics*). Distinguish all three states at the call
site.

**Security** -- `%s`, `%[`, `%c` without an explicit maximum field width
is a buffer overflow; always bound (`%63s`). Arguments must be pointers
of matching type; wrong types or missing arguments are undefined.
`%n`-bearing untrusted formats are dangerous as with `printf`.

**References** -- `man3/scanf.3`, `man3/fscanf.3`, `man3/sscanf.3`.
