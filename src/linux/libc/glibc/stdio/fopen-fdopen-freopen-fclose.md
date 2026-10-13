# `fopen` / `fdopen` / `freopen` / `fclose` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

## Overview

This chapter documents the glibc stdio layer (`FILE *` streams, formatted
I/O, the thin `unistd.h` syscall wrappers and the error-reporting helpers),
following the entry template defined in the
[encyclopedia overview](../../../interface-encyclopedia.md). Coverage is
ledger-driven: per-entry status lives in the
[glibc ledger](../../ledger-glibc.md) under the chapters *Input/Output on
Streams*, *Low-Level Input/Output*, *Error Reporting* and *Pipes and
FIFOs*. The raw syscall counterparts of the low-level entries are
documented in [Descriptors and File I/O](../../../syscalls/descriptors-io/overview.md);
entries here stay on the libc side of that boundary.

stdio is a **buffered** layer between the application and file descriptors.
Every `FILE` owns a user-space buffer, an error indicator, an end-of-file
indicator, an orientation flag and a recursive lock:

```text
application objects        FILE (libc, user space)         kernel
-----------------------    ----------------------------    ------------------
printf/fwrite args   -->   output buffer  ( BUFSIZ-ish )   page cache
fread/fgetc copy out <--   input buffer   ( refills )      inode / device
                                 |
                                 | flush points only
                                 v
                            write(2) / read(2) on fileno(stream)
```

A stream issues syscalls **only** at buffer boundaries: when the output
buffer is full, when it is explicitly or implicitly flushed, when an input
buffer must be refilled, and at close/position operations. Implicit flush
points (glibc manual, *Flushing Buffers*): buffer full; `fclose`; program
exit through `return` from `main` or `exit`; a newline on a line-buffered
stream; and any input operation on *any* stream that actually reads data
from its file. Unbuffered streams translate one `write(2)` per output
call; fully buffered streams amortize many calls into one. Default modes
(manual, *Buffering Concepts*; `stdio(3)`): newly opened streams are fully
buffered, streams on interactive devices start line buffered, and `stderr`
is not fully buffered. A descriptor's file offset only moves when stdio
touches the descriptor -- which is why mixing `FILE` output with raw
`write(2)` on the same descriptor interleaves unpredictably unless the
stream is flushed first (manual, *Stream/Descriptor Precautions*).

**Orientation.** A new stream is unoriented; the first I/O operation
fixes it as narrow (byte) or wide, and `freopen` resets it. The
`,ccs=CHARSET` suffix in a `fopen` mode pre-orients the stream wide.
Mixing narrow and wide operations on one oriented stream is undefined and
undiagnosed; `fwide` queries or fixes orientation before first use
(manual, *Streams and I18N*).

**Locking.** Each `FILE` carries a recursive lock that every non-`_unlocked`
stdio operation acquires implicitly, which is what makes POSIX stream
operations atomic per call (manual, *Streams and Threads*). Multi-call
sequences need explicit `flockfile`/`funlockfile`; hot loops use the
`_unlocked` variants under an external lock.

**Errors.** Narrow stream functions signal failure with `EOF` (glibc:
`-1`) or a short count, and set the stream's `feof`/`ferror` indicators;
`errno` is additionally set exactly as the underlying descriptor call
would set it (manual, *EOF and Errors*). Because `EOF` conflates
end-of-file with error, `feof`/`ferror` decide which happened.

| Field | Value |
|---|---|
| ID | GLIBC-fopen (group) |
| Header | `stdio.h` |
| Provenance | ISO C (`fopen`, `freopen`, `fclose`); POSIX (`fdopen`); Unix98 LFS twins (`fopen64`, `freopen64`); GNU (`fcloseall`) |
| Status | documented |

**Signature** -- `FILE *fopen(const char *path, const char *mode);` /
`FILE *fdopen(int fd, const char *mode);` / `FILE *freopen(const char
*path, const char *mode, FILE *stream);` / `int fclose(FILE *stream);`

**Modes.** `fopen` mode starts with `r`, `w` (truncate), `a` (append), or
the `+` variants for update; `b` is accepted but meaningless on POSIX.
glibc extension characters: `e` (close-on-exec on the underlying
descriptor), `x` (`O_EXCL`, ISO C11), `m` (mmap-backed, read only), `c`
(cancellation disabled in I/O). With `_FILE_OFFSET_BITS == 64` the names
become the `*64` LFS twins (manual, *Opening Streams*).

**Semantics.** `fdopen` wraps an existing descriptor; on glibc `w`/`w+`
do **not** truncate (the file is already open), `b` is rejected, and
glibc always checks that the descriptor's access mode permits the
requested stream mode (manual, *Descriptors and Streams*). `freopen`
closes then reopens within the same `FILE` object -- the portable way to
retarget `stdin`/`stdout`; glibc only supports `freopen` on
`fopen`-style and the three standard streams, and fails for
`popen`/`fmemopen`/`open_memstream`/`fopencookie` streams.

**Return and errors.** `fopen`/`fdopen`/`freopen` return `NULL` on
failure with `errno` from the underlying `open`; `fclose` returns `0` or
`EOF`. `fclose` flushes buffered output and discards buffered input;
checking its return is mandatory on output streams -- the final buffer
delivery can fail (disk full, deferred NFS errors, manual, *Closing
Streams*). After `fclose` the stream pointer is dead. `exit`/return from
`main` closes all streams; `abort` and fatal signals do not.

**Implementation path** -- `fopen` issues `openat` on modern kernels (no
`open` slot on arm64, see [Descriptors and File I/O](../../../syscalls/descriptors-io/overview.md)
`open` entry); `fclose` flushes then `close(2)`s.
