# `fgetc` / `getc` / `getchar` / `ungetc` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-fgetc (group) |
| Header | `stdio.h` |
| Provenance | ISO C (`fgetc`, `getc`, `getchar`, `ungetc`); POSIX `_unlocked`; SVID legacy (`getw`) |
| Status | documented |

**Signature** -- `int fgetc(FILE *stream);` `int getc(FILE *stream);`
`int getchar(void);` `int ungetc(int c, FILE *stream);` plus
`fgetc_unlocked`, `getc_unlocked`, `getchar_unlocked` and the SVID word
reader `getw`.

**Semantics** -- read one byte as `unsigned char`, returned as `int`;
`EOF` on end-of-file or error. The manual's rule: store the result in an
`int`, never a `char`, or `EOF` becomes indistinguishable from the valid
byte `(char)-1` (manual, *Character Input*). `getc`/`getchar` may be
macros that evaluate the stream argument more than once -- never pass a
side-effecting expression. `ungetc` pushes one byte back: the next read
returns it first. glibc supports pushing back several characters (read
in reverse push order), pushing a byte that differs from the one read,
and pushing without any prior read; `ungetc(EOF, ...)` is a no-op
returning `EOF`; a successful pushback on a stream at EOF clears the EOF
indicator; any positioning call discards pushed-back bytes (manual,
*Unreading*). `getw` reads one `int` and cannot report `-1` values --
legacy, use `fread`.

**Thread safety** -- locked variants MT-Safe; `_unlocked` variants need
external `flockfile`.
