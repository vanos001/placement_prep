# `fread` / `fwrite` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-fread (group) |
| Header | `stdio.h` |
| Provenance | ISO C; `_unlocked` variants GNU |
| Status | documented |

**Signature** -- `size_t fread(void *ptr, size_t size, size_t nmemb, FILE
*stream);` `size_t fwrite(const void *ptr, size_t size, size_t nmemb,
FILE *stream);`

**Semantics** -- element-oriented block I/O: `nmemb` elements of `size`
bytes each. `fread` returns the number of *complete elements* read, which
may be short on end-of-file or error; a trailing partial element is
discarded, leaving the stream at the true end of file (manual, *Block
Input/Output*). `fwrite` normally returns `nmemb`; anything less is an
error (for example, out of space). Zero `size` or `nmemb` returns zero
and touches nothing. The file position indicator advances by the bytes
actually transferred (`fread(3)`).

**Return and errors** -- `fread` cannot distinguish EOF from error;
callers must test `feof`/`ferror` (`fread(3)`). `errno` reflects the
underlying `read`/`write` failures (manual, *EOF and Errors*).

**Edge cases** -- a short count from `fwrite` means buffered data may
have been partially committed; the recovery advice in the manual
(*Error Recovery*) is to seek to a known position rather than blindly
retry. Both are cancellation points in glibc (headers).

**References** -- `man3/fread.3`; glibc manual *Block Input/Output*.
