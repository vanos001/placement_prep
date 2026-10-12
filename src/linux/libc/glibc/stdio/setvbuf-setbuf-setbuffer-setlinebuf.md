# `setvbuf` / `setbuf` / `setbuffer` / `setlinebuf` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-setvbuf (group) |
| Header | `stdio.h` |
| Provenance | ISO C (`setvbuf`, `setbuf`); BSD (`setbuffer`, `setlinebuf`) |
| Status | documented |

**Signature** -- `int setvbuf(FILE *stream, char *buf, int mode, size_t
size);` `void setbuf(FILE *stream, char *buf);` `void setbuffer(FILE
*stream, char *buf, size_t size);` `void setlinebuf(FILE *stream);`

**Modes** -- `_IOFBF` full, `_IOLBF` line, `_IONBF` unbuffered. Call
after opening and before any other operation on the stream (manual,
*Controlling Buffering*). If `buf` is `NULL`, glibc `malloc`s the buffer
of `size` and frees it at `fclose`; a caller-provided buffer must stay
alive (static or heap, not a dead stack frame) for the stream's
lifetime and must not be read or written by the program while the stream
uses it.

**Equivalences** -- `setbuf(s, buf)` is `setvbuf(s, buf, buf ? _IOFBF :
_IONBF, BUFSIZ)`; `setbuffer` is the same with a caller-chosen size;
`setlinebuf` selects `_IOLBF` with an allocated buffer. `BUFSIZ` is the
historic default chunk; the truly optimal size is `st_blksize` from
`fstat` on the descriptor (manual). Nonzero return from `setvbuf`
signals an invalid mode or a refused request.
