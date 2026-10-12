# `fseeko` / `ftello` (fseek, ftell, rewind, fgetpos, fsetpos) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-fseeko (group) |
| Header | `stdio.h` |
| Provenance | ISO C (`fseek`, `ftell`, `rewind`, `fgetpos`, `fsetpos`); Unix98 XSI (`fseeko`, `ftello`); Unix98 LFS twins (`fseeko64`, `ftello64`, `fgetpos64`, `fsetpos64`) |
| Status | documented |

**Signature** -- `int fseeko(FILE *stream, off_t offset, int whence);`
`off_t ftello(FILE *stream);` `void rewind(FILE *stream);` `int
fgetpos(FILE *stream, fpos_t *pos);` `int fsetpos(FILE *stream, const
fpos_t *pos);`

**Semantics** -- `fseek`/`ftell` take `long int`; `fseeko`/`ftello` take
`off_t`, which is the type that actually matches the descriptor layer
(manual, *File Positioning*). `SEEK_SET`/`SEEK_CUR`/`SEEK_END` match
`lseek`. A successful seek flushes or repositions buffered output,
discards `ungetc` pushback, and clears the EOF indicator; `rewind` is
`fseek(stream, 0L, SEEK_SET)` that additionally resets the error
indicator and reports nothing. `fgetpos`/`fsetpos` traffic in the opaque
`fpos_t`, which on glibc also carries the wide-conversion state
(`mbstate_t`) -- the only fully portable pair, and required to preserve
multibyte state on wide streams (manual, *Portable Positioning*).

**64-bit interplay** -- with `_FILE_OFFSET_BITS == 64` the `o` names
become the `64` twins on 32-bit hosts; `ftell`'s `long int` can be too
narrow for large files even when `off_t` is not, one more reason to
prefer `ftello`. Failure convention: `fseek`/`fseeko` return nonzero and
set `errno`; `fgetpos`/`fsetpos` return nonzero and set `errno` to an
implementation-defined positive value.
