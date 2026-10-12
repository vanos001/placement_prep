# readv(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | readv 19 / 145 / 65 / 145; writev 20 / 146 / 66 / 146; preadv 295 / 333 / 69 / 361; pwritev 296 / 334 / 70 / 362; preadv2 327 / 378 / 286 / 392; pwritev2 328 / 379 / 287 / 393 (per-call table below) |
| Since (kernel) | readv, writev 2.0; preadv, pwritev 2.6.30 (glibc 2.10); preadv2, pwritev2 4.6 (glibc 2.26) |
| Man page | man2/readv.2 (writev.2, preadv.2, pwritev.2, preadv2.2, pwritev2.2 are .so aliases of it) |
| glibc wrapper | all six declared in <sys/uio.h>: readv/writev POSIX.1-2001; preadv/pwritev under __USE_MISC (man page: _DEFAULT_SOURCE since glibc 2.19, _BSD_SOURCE before); preadv2/pwritev2 under __USE_GNU (GNU extension); host glibc 2.41 exports preadv/pwritev@@GLIBC_2.10 and preadv2/pwritev2@@GLIBC_2.26 (nm -D); the raw preadv/pwritev syscalls take offset as two unsigned longs, unpacked by the wrapper |
| Aliases covered | writev, preadv, pwritev, preadv2, pwritev2 |
| Ledger ID | SC-readv, SC-writev, SC-preadv, SC-pwritev, SC-preadv2, SC-pwritev2 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| readv | 19 | 145 | 65 | 145 | 2.0 |
| writev | 20 | 146 | 66 | 146 | 2.0 |
| preadv | 295 | 333 | 69 | 361 | 2.6.30 |
| pwritev | 296 | 334 | 70 | 362 | 2.6.30 |
| preadv2 | 327 | 378 | 286 | 392 | 4.6 |
| pwritev2 | 328 | 379 | 287 | 393 | 4.6 |

Hub row note: the domain hub groups all six calls in one row keyed to readv.md and shows preadv's number set (295 / 333 / 69 / 361) with Since 2.6.30; the per-call values above are the ledger values (SC-readv, SC-writev, SC-preadv, SC-pwritev, SC-preadv2, SC-pwritev2).

## Purpose

readv() reads iovcnt buffers from the file referred to by fd into the array of iovec structures ("scatter input"); writev() writes iovcnt buffers out ("gather output"). Buffers are processed in array order: iov[0] is completely filled (or written) before iov[1]. The transfer is atomic with respect to other users of the same open file description: writev() output lands as a single block that is not intermingled with other writers' output, and readv() reads a contiguous block even if other threads sharing the description read concurrently. preadv()/pwritev() add an explicit offset and leave the file offset unchanged (the fd must be seekable); preadv2()/pwritev2() add a per-call flags argument, and treat offset -1 as "use and update the current file offset". These are the only calls in the read/write family that carry per-I/O RWF_* flags; plain read() and write() (read.md, write.md) take none.

## Synopsis

```c
#include <sys/uio.h>
ssize_t readv(int fd, const struct iovec *iov, int iovcnt);
ssize_t writev(int fd, const struct iovec *iov, int iovcnt);
ssize_t preadv(int fd, const struct iovec *iov, int iovcnt, off_t offset);
ssize_t pwritev(int fd, const struct iovec *iov, int iovcnt, off_t offset);
ssize_t preadv2(int fd, const struct iovec *iov, int iovcnt, off_t offset, int flags);
ssize_t pwritev2(int fd, const struct iovec *iov, int iovcnt, off_t offset, int flags);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd | File descriptor as for read()/write() (read.md, write.md); for preadv/pwritev the fd must be capable of seeking, otherwise lseek() errors apply. |
| iov | Array of struct iovec { void *iov_base; size_t iov_len; } processed in array order. |
| iovcnt | Number of iovec elements; 0 < iovcnt <= IOV_MAX (1024 on modern Linux, /usr/include/x86_64-linux-gnu/bits/uio_lim.h __IOV_MAX 1024; it was 16 in Linux 2.0 days). Out of range: EINVAL. |
| offset (p* forms) | File offset for the transfer; the file offset is not changed, except preadv2/pwritev2 with offset -1 use and update the current offset. |
| flags (v2 forms) | OR of RWF_* flags (table below); unknown flag bits fail EOPNOTSUPP. |

## Return value and errors

Success returns the number of bytes read or written; a short transfer is not an error (read.md, write.md). On error, -1 and errno: the errors of read(2)/write(2) for all six calls, plus the lseek(2) errors (ESPIPE and friends) for the offset forms, plus EINVAL (sum of iov_len values overflows ssize_t; iovcnt < 0 or above the permitted maximum) and EOPNOTSUPP (unknown flag in flags). RWF_NOWAIT returns EAGAIN when data would have to be fetched from storage (see the 5.9/5.10 bug note below).

## Flags and constants

RWF_* values from /usr/include/x86_64-linux-gnu/bits/uio-ext.h (glibc 2.41, included by <sys/uio.h> under __USE_GNU); "since" from the cached man2/readv.2 plus man-pages 6.19 readv.2 fetched from man7.org (source-cache/fetched/readv.2.current.plain, per worklog 1-c):

| Flag | Value | Since | Meaning |
|---|---|---|---|
| RWF_HIPRI | 0x1 | 4.6 | High-priority polled I/O; only meaningful with O_DIRECT |
| RWF_DSYNC | 0x2 | 4.7 | Per-write O_DSYNC; only meaningful for pwritev2() |
| RWF_SYNC | 0x4 | 4.7 | Per-write O_SYNC; only meaningful for pwritev2() |
| RWF_NOWAIT | 0x8 | 4.14 | Do not wait for data that is not immediately available; returns EAGAIN rather than reading from storage; only meaningful for preadv2() |
| RWF_APPEND | 0x10 | 4.16 | Per-write O_APPEND; offset ignored, data appended; offset -1 still updates the current offset |
| RWF_NOAPPEND | 0x20 | 6.9 | Do not honor O_APPEND for this pwritev2() |
| RWF_ATOMIC | 0x40 | 6.11 | Torn-write protection; see write.md for the full constraint list and statx.md for stx_atomic_write_* |
| RWF_DONTCACHE | 0x80 | 6.14 | Drop instantiated page-cache pages when the I/O completes; a hint, EOPNOTSUPP if unsupported |
| RWF_NOSIGNAL | 0x100 | (kernel master uapi) | Suppress SIGPIPE for pipe/socket writes; in kernel headers, not described in man-pages 6.19 readv.2 |

RWF_ATOMIC and RWF_DONTCACHE are absent from the cached 2021 man-pages snapshot; the host glibc 2.41 headers define RWF_ATOMIC (0x40) but their RWF_SUPPORTED mask stops there, so RWF_DONTCACHE and RWF_NOSIGNAL are not defined by the installed headers (verified against bits/uio-ext.h).

## Security and notes

- Atomicity caveat: the single-block guarantee is per open file description; with O_APPEND, POSIX appends remain subject to the NFS client-side corruption caveat noted on write.md.
- POSIX XSI 2.9.7 offset-atomicity: before Linux 3.14 concurrent reads/writes sharing an open file description could overlap; fixed in 3.14 (man2/read.2 BUGS, same rule covers readv/writev).
- Historical glibc fallback: with early kernels whose IOV_MAX was 16, the glibc readv()/writev() wrappers emulated the call with a temporary buffer and read()/write(); this was needed only for kernels older than 2.6.18 and glibc 2.20+ always calls the syscall directly (man2/readv.2, Historical C library/kernel differences).
- Linux 5.9 and 5.10 bug: preadv2() with RWF_NOWAIT may return 0 even when not at end of file (man2/readv.2 BUGS).
- readv()/writev() are POSIX (first appeared in 4.2BSD); preadv/pwritev are nonstandard but on modern BSDs; preadv2/pwritev2 are Linux-specific.

## References

- man2/readv.2 in the cached man-pages tree (dated 2021-08-27); .so aliases writev.2, preadv.2, pwritev.2, preadv2.2, pwritev2.2.
- man-pages 6.19 readv.2 fetched from man7.org (source-cache/fetched/readv.2.current.plain) for RWF_ATOMIC / RWF_DONTCACHE / RWF_NOAPPEND (worklog 1-c).
- Constants: /usr/include/x86_64-linux-gnu/sys/uio.h, bits/uio-ext.h, bits/uio_lim.h; kernel master include/uapi/linux/fs.h (source-cache/fetched/k-uapi-fs.h).
- [Syscalls ledger](../ledger.md) rows SC-readv, SC-writev, SC-preadv, SC-pwritev, SC-preadv2, SC-pwritev2; siblings [read](read.md), [write](write.md); [domain hub](overview.md).
