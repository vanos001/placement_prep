# `perror` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-perror |
| Header | `stdio.h` |
| Provenance | ISO C |
| Status | documented |

**Signature** -- `void perror(const char *message);`

**Semantics** -- prints to `stderr`: the message (or nothing if `NULL`
or empty), then `": "` and the `strerror(errno)` text, then newline
(manual, *Error Messages*). It does not change `stderr`'s orientation --
if the stream is not yet oriented, glibc writes through a dup of the
descriptor to avoid orienting it (manual safety note). Because it reads
the *current* `errno`, call it immediately after the failure, or save
`errno` first -- every intervening library call may overwrite it.

**When to prefer what** -- `perror` is portable ISO C; the manual's
critique is that the format is fixed: no program-name prefix, no
location, no custom text after the message. `error()` for GNU-style
output, `fprintf(stderr, "%s: %s\n", prog, strerror(errno))` when
needing both, and `strerror_r`/`snprintf("%m")` where the static
`strerror` buffer would be a race.
