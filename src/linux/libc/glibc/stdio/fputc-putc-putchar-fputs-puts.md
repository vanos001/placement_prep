# `fputc` / `putc` / `putchar` / `fputs` / `puts` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-fputc (group) |
| Header | `stdio.h` |
| Provenance | ISO C; POSIX `_unlocked`; GNU (`fputs_unlocked`); SVID (`putw`) |
| Status | documented |

**Signature** -- `int fputc(int c, FILE *stream);` `int putc(int c, FILE
*stream);` `int putchar(int c);` `int fputs(const char *s, FILE
*stream);` `int puts(const char *s);` plus `putw(int w, FILE *stream)`.

**Semantics** -- character output: `fputc` writes `c` cast to `unsigned
char`, returning the character, or `EOF` on write error. `putc` and
`putchar` are macro-able aliases (`putc` may evaluate `stream` twice);
`putchar` targets `stdout`. Line output: `fputs` writes the string
without the terminating NUL and without adding a newline; `puts` writes
to `stdout` and appends a newline (manual, *Simple Output*). All set the
stream error indicator and `errno` on failure. `putw` writes one `int`;
SVID legacy, prefer `fwrite`.

**Cancellation** -- `fputs`/`puts` are possible cancellation points
(headers). `_unlocked` variants (GNU: `fputs_unlocked`,
`fputc_unlocked`; POSIX: `putc_unlocked`, `putchar_unlocked`) skip the
implicit lock and are the hot-path choice under `flockfile`.
