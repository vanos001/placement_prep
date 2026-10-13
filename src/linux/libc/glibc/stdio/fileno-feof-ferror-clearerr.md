# `fileno` / `feof` / `ferror` / `clearerr` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-fileno (group) |
| Header | `stdio.h` |
| Provenance | POSIX (`fileno`); ISO C (`feof`, `ferror`, `clearerr`); GNU `_unlocked` variants |
| Status | documented |

**Signature** -- `int fileno(FILE *stream);` `int feof(FILE *stream);`
`int ferror(FILE *stream);` `void clearerr(FILE *stream);`

**Semantics** -- `fileno` exposes the descriptor behind a stream
(`STDIN_FILENO` etc. are 0/1/2, manual, *Descriptors and Streams*); it
returns `-1` on an invalid or non-file stream. `feof`/`ferror` test the
stream's two sticky indicators; they are mutually exclusive for narrow
streams, and positioning calls clear the EOF flag. `clearerr` resets
both. Because the indicators are sticky, testing them *before* an
operation is meaningless -- test after failure.

**Edge cases** -- clearing the error flag and retrying a failed stream
operation is wrong: a partially failed write may have committed an
unknown amount, and a failed read can leave the offset misplaced; seek
to a known position before retrying (manual, *Error Recovery*). Most
stream errors are not retryable anyway; the notable exception is
`EINTR`, avoidable by installing handlers with `SA_RESTART`. `errno`
after a stream failure carries the underlying `read`/`write` value
(manual, *EOF and Errors*).
