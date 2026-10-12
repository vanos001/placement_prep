# `fflush` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-fflush |
| Header | `stdio.h` |
| Provenance | ISO C; POSIX (`fflush_unlocked`) |
| Status | documented |

**Signature** -- `int fflush(FILE *stream);`

**Semantics** -- delivers buffered output to the kernel. `fflush(NULL)`
flushes **all** open output streams -- the strongest per-process
synchronization point between stdio and `write(2)`, and the standard
brace before `fork()` so parent and child do not duplicate buffered
data. `fflush` on an input stream discards buffered input on seekable
files but leaves the descriptor offset unpredictable (manual,
*Cleaning Streams*). Returns `0`, or `EOF` with `errno` from the
underlying `write`.

**fsync interplay** -- `fflush` moves data from the `FILE` buffer to the
page cache only; durability against crashes needs `fsync(fd)` on
`fileno(stream)` afterwards (manual, *Synchronizing I/O operations*:
`write` returning does not mean the media got the data). The two calls
are complementary: stdio-to-kernel, then kernel-to-device.

**Related** -- `_flushlbf` (GNU, `stdio_ext.h`) flushes only line
buffered streams; `__fpurge` discards an input buffer without delivering
it.
