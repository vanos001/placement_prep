# `fgets` / `getline` / `getdelim` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-getline (group) |
| Header | `stdio.h` |
| Provenance | ISO C (`fgets`); POSIX.1-2008 (`getline`, `getdelim`); GNU (`fgets_unlocked`) |
| Status | documented |

**Signature** -- `char *fgets(char *s, int count, FILE *stream);`
`ssize_t getline(char **lineptr, size_t *n, FILE *stream);` `ssize_t
getdelim(char **lineptr, size_t *n, int delim, FILE *stream);`

**Semantics** -- `fgets` reads up to `count - 1` bytes, always stopping
after (and including) a newline, and NUL-terminates; returns `s`, or
`NULL` on EOF-with-nothing-read or error. It cannot detect embedded NUL
bytes, which is why the manual recommends `getline` for untrusted or
user-edited input (manual, *Line-Oriented Input*). `getline` reads an
entire line into a *malloc-managed* buffer: on entry `*lineptr` may be a
`malloc`'d buffer of `*n` bytes or `NULL` with `*n == 0`; the call
`realloc`s as needed and stores the new pointer and size back. It
returns the byte count including the newline (so embedded NULs are
measurable), or `-1` on EOF/error. `getdelim` generalizes the delimiter;
`getline` is `getdelim` with `'\n'` (manual shows the one-line
implementation).

**Allocation rules** -- the buffer stays owned by the caller and stays
allocated even when the first call fails; glibc NUL-terminates a buffer
it allocated itself so `-1` returns are still printable (manual). POSIX
leaves `*lineptr` undefined on `-1`; free the buffer exactly once when
done regardless.

**Return and errors** -- `-1` with `errno` from the underlying read
(`EAGAIN`, `EINTR`, `EIO`, ...).

**References** -- `man3/getline.3`; glibc manual *Line-Oriented Input*.
