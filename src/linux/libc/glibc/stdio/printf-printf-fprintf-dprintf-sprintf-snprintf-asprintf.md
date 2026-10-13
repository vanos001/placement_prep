# `printf` (printf, fprintf, dprintf, sprintf, snprintf, asprintf) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-printf (group) |
| Header | `stdio.h` |
| Provenance | ISO C (printf/fprintf/sprintf/snprintf); POSIX.1-2008 (`dprintf`); GNU (`asprintf`) |
| Status | documented |

**Signature** -- `int printf(const char *fmt, ...);` `int fprintf(FILE
*f, const char *fmt, ...);` `int dprintf(int fd, const char *fmt, ...);`
`int sprintf(char *s, const char *fmt, ...);` `int snprintf(char *s,
size_t size, const char *fmt, ...);` `int asprintf(char **ptr, const
char *fmt, ...);`

**Return semantics** -- the stream and string forms return the character
count written; `printf`/`fprintf`/`dprintf` return a *negative* value on
output error. `snprintf` (C99 semantics, glibc changed in 2.1) returns
the number of characters that *would* have been written, excluding the
NUL -- so `ret >= size` means truncation, and `size == 0` writes nothing
(not even the NUL) with `s` allowed to be `NULL`. `asprintf`
`malloc`s exactly the right buffer into `*ptr` and returns its length;
glibc writes `NULL` into `*ptr` on failure (manual, *Dynamic Output*).
`swprintf` differs from `snprintf`: overflow returns a negative value
with `errno` set to `E2BIG` (GNU extension, manual).

**Shared errors** -- `EOVERFLOW` (output would exceed `INT_MAX`),
`ENOMEM`, `EILSEQ` for input conversion failures; `dprintf` adds
whatever `write(2)` produces on that descriptor, and the number of
`write` calls it makes is unspecified -- partial output may occur even
on error (manual, *Formatted Output Functions*).

**Security notes** -- `%n` *writes* the count so far into an `int *`;
`printf(3)` documents that untrusted data used as a format string (for
example `printf(foo)`) is an exploitable hole via `%n`. Always use
format literals or `printf("%s", s)`. `sprintf` has no bound and is
unsalvageable for unbounded input; field widths are minimums, not
maximums. glibc's `%m` prints `strerror(errno)` (GNU extension).
GCC's `format(printf, ...)` attribute, used by glibc's own `error.h`,
checks format strings at compile time.
