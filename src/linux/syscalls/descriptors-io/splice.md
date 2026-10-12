# splice(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | splice 275 / 313 / 76 / 340; vmsplice 278 / 316 / 75 / 343; tee 276 / 315 / 77 / 342 (per-call table below) |
| Since (kernel) | splice, vmsplice, tee 2.6.17 (glibc 2.5 for all three) |
| Man page | man2/splice.2, man2/vmsplice.2, man2/tee.2 (three separate man pages; grouped on this page per task 3-c2 -- the domain hub currently lists tee.md and vmsplice.md as separate rows, a merge decision flagged in the worklog) |
| glibc wrapper | all three need _GNU_SOURCE and are declared in <fcntl.h>; host glibc 2.41 exports splice@@GLIBC_2.5, vmsplice@@GLIBC_2.5, tee@@GLIBC_2.5 (nm -D); the splice return type was long before glibc 2.7 |
| Aliases covered | vmsplice, tee (brief sections below) |
| Ledger ID | SC-splice, SC-vmsplice, SC-tee |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| splice | 275 | 313 | 76 | 340 | 2.6.17 |
| tee | 276 | 315 | 77 | 342 | 2.6.17 |
| vmsplice | 278 | 316 | 75 | 343 | 2.6.17 |

## Purpose

The splice family moves data between descriptors without copying it between kernel and user address space. All three operate on the kernel's pipe buffer -- a set of reference-counted pointers to pages of kernel memory -- giving user space control over an arbitrary kernel buffer (man2/splice.2 NOTES). "Copying" between buffers means duplicating page pointers and bumping reference counts, not touching the data. splice() moves data between fd_in and fd_out, where at least one side must be a pipe (since 2.6.31 both may be); tee() duplicates up to len bytes from one pipe into another without consuming the source, so the same bytes can be spliced onward afterwards; vmsplice() maps user memory ranges into a pipe (fd open for writing) or fills user ranges from a pipe (fd open for reading). The classic pipeline is input device -> splice into pipe -> tee to fork the stream -> splice one branch to storage and another to a consumer, all zero-copy where the driver supports it.

## Synopsis

```c
#define _GNU_SOURCE
#include <fcntl.h>
ssize_t splice(int fd_in, off64_t *off_in, int fd_out, off64_t *off_out,
               size_t len, unsigned int flags);
ssize_t vmsplice(int fd, const struct iovec *iov, size_t nr_segs,
                 unsigned int flags);
ssize_t tee(int fd_in, int fd_out, size_t len, unsigned int flags);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd_in / fd_out (splice) | If the fd refers to a pipe, the matching off argument must be NULL. If it does not refer to a pipe: NULL off uses and updates the file offset; non-NULL off points to the start offset and leaves the file offset unchanged. |
| len | Transfer bound. |
| fd (vmsplice) | Must refer to a pipe; write-open maps user pages in, read-open copies pipe data out (true splicing exists only in the to-pipe direction; the opposite is a copy). |
| iov / nr_segs (vmsplice) | iovec array (struct iovec as on readv.md), nr_segs <= IOV_MAX (1024). |
| fd_in / fd_out (tee) | Both must refer to pipes and must not be the same pipe (EINVAL). |
| flags | SPLICE_F_* bit mask (table below) shared by all three calls. |

## Return value and errors

splice() returns the number of bytes spliced; 0 means end of input (for a pipe input: no data and no writers). vmsplice() returns bytes transferred to the pipe. tee() returns bytes duplicated; 0 means no data and no writers on fd_in. On error, -1 and errno: EAGAIN (SPLICE_F_NONBLOCK or O_NONBLOCK and the operation would block), EBADF (splice: bad fds or wrong read/write mode; vmsplice: fd not valid or not a pipe), EINVAL (splice: target filesystem does not support splicing, target opened O_APPEND -- so since 2.6.27, offset given for a nonseekable object, neither fd is a pipe, fd_in and fd_out are the same pipe; vmsplice: nr_segs above IOV_MAX or unaligned memory with SPLICE_F_GIFT; tee: not a pipe or same pipe), ENOMEM, ESPIPE (splice: non-NULL off for a pipe).

## Flags and constants

| Flag | Value | Applies to | Meaning |
|---|---|---|---|
| SPLICE_F_MOVE | (bit 0) | splice (no-op there since 2.6.21); vmsplice: enables later SPLICE_F_MOVE after SPLICE_F_GIFT | Hint to move pages instead of copying; initial implementation was buggy, so since 2.6.21 it is accepted but does nothing |
| SPLICE_F_NONBLOCK | (bit 1) | all three | Nonblocking on the pipe side only; fds may still block unless O_NONBLOCK |
| SPLICE_F_MORE | (bit 2) | splice (vmsplice/tee: no effect yet) | More data coming; hint for socket output, related to MSG_MORE and TCP_CORK |
| SPLICE_F_GIFT | (bit 3) | vmsplice only | Gift user pages to the kernel; the memory must never be modified again and must be page-aligned in address and length; enables a later SPLICE_F_MOVE (otherwise MOVE must copy) |

Values are flags, not numbers exposed as ABI constants on all headers; the numeric bit order (0..3) is from the kernel's include/uapi/linux/splice.h ordering as described by man2/splice.2 and man2/vmsplice.2 semantics.

## Security and notes

- vmsplice buffer lifetime: after vmsplice() the kernel references your pages; unlike write(), a successful return does not free you to reuse the buffer -- modifying gifted memory desynchronizes page cache and disk data (man2/vmsplice.2 header comment). This is the family's main footgun.
- SPLICE_F_NONBLOCK applies to the pipe operations only; blocking still happens on the file descriptors themselves unless they are O_NONBLOCK (man2/splice.2).
- Append mode is rejected: splicing to an O_APPEND-opened target fails EINVAL (2.6.27 behavior note in the man page error list).
- Splice support is filesystem-dependent; a target that does not support it fails EINVAL, so portable code needs the read()/write() fallback.
- vmsplice's to-user direction copies; only user-to-pipe truly splices (man2/vmsplice.2 NOTES).
- Related zero-copy paths: sendfile() (sendfile.md) for the socket-out special case, copy_file_range() for file-to-file (see [domain hub](overview.md) row).

## tee(2) and vmsplice(2) -- brief

tee(2) duplicates pipe content by grabbing references to the input pages; nothing is consumed from fd_in, so a subsequent splice() can still read the same data (man2/tee.2). SPLICE_F_MOVE and SPLICE_F_GIFT have no effect for tee(). vmsplice(2) is the user-memory side of the family: it fills a pipe from user pages (write-open fd) or drains a pipe into user memory (read-open fd, a plain copy). Its SPLICE_F_GIFT semantics and the IOV_MAX limit are covered above; its errors are EAGAIN, EBADF, EINVAL, ENOMEM as listed.

## References

- man2/splice.2, man2/vmsplice.2 (both 2021-03-22), man2/tee.2 (2020-06-09) in the cached man-pages tree.
- [Syscalls ledger](../ledger.md) rows SC-splice, SC-vmsplice, SC-tee; siblings [sendfile](sendfile.md), [readv](readv.md) (iovec struct), [read](read.md); [domain hub](overview.md).
