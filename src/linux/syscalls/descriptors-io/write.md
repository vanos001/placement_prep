# write(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 1 / 4 / 64 / 4 |
| Since (kernel) | 1.0 |
| Man page | man2/write.2 |
| glibc wrapper | write() declared in <unistd.h>, POSIX.1-2001; thin wrapper, no kernel-specific emulation |
| Aliases covered | none (the RWF_* flag set below belongs to the pwritev2()/preadv2() forms documented on readv.md) |
| Ledger ID | SC-write |

## Purpose

write() writes up to count bytes from buf to the file referred to by fd. For a seekable file the transfer starts at the file offset, which is advanced by the number of bytes written; with O_APPEND the offset is first moved to end of file and the adjust-plus-write is a single atomic step. Partial writes are normal and not errors: they happen when the medium is short of space, when RLIMIT_FSIZE is hit, or when a signal handler interrupts a blocked write after some bytes were transferred; the caller retries with a new write() for the rest. A successful return does not promise the data reached disk; errors can be delayed until a later write(), fsync(2), or close(2).

## Synopsis

```c
#include <unistd.h>
ssize_t write(int fd, const void *buf, size_t count);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd | Descriptor open for writing; otherwise EBADF. Writing a pipe or socket whose read end is closed fails EPIPE and also raises SIGPIPE. |
| buf | Source buffer; EFAULT if outside the address space. O_DIRECT may impose alignment on buf, count, and the file offset (EINVAL). |
| count | Transfer bound; Linux caps it at 0x7ffff000 (2,147,479,552) bytes on 32-bit and 64-bit alike. count == 0 on a regular file may still detect errors; on other objects the result is unspecified. |

EINTR rule (man2/write.2 NOTES): interrupted before any byte is written, the call fails EINTR; interrupted after at least one byte, it returns the partial count.

## Return value and errors

Success returns the number of bytes written (possibly fewer than count). Error: -1 and errno: EAGAIN (nonblocking and would block; POSIX allows EAGAIN or EWOULDBLOCK on sockets), EBADF, EDESTADDRREQ (unconnected datagram socket), EDQUOT, EFAULT, EFBIG (file size or RLIMIT_FSIZE exceeded), EINTR, EINVAL (object unsuitable; O_DIRECT alignment), EIO (low-level inode write error; since Linux 4.13 write-back errors may be reported by a later write() and will be reported by a later fsync(2); lost NFS lock), ENOSPC, EPERM (operation prevented by a file seal, see fcntl.md), EPIPE (with SIGPIPE). Other errors depend on the object.

## Flags and constants

write() itself takes no flags. The per-I/O RWF_* flags are the fifth argument of pwritev2() (and preadv2() for the read-side ones). Values from /usr/include/x86_64-linux-gnu/bits/uio-ext.h (glibc 2.41) and include/uapi/linux/fs.h (kernel master); "since" from the cached man2/readv.2 plus the man-pages 6.19 readv.2 fetched from man7.org (fetched copy kept at source-cache/fetched/readv.2.current.plain).

| Flag | Value | Since | Meaning |
|---|---|---|---|
| RWF_HIPRI | 0x1 | 4.6 | High-priority polled I/O; only meaningful with O_DIRECT |
| RWF_DSYNC | 0x2 | 4.7 | Per-write O_DSYNC; only meaningful for pwritev2() |
| RWF_SYNC | 0x4 | 4.7 | Per-write O_SYNC; only meaningful for pwritev2() |
| RWF_NOWAIT | 0x8 | 4.14 | Do not wait for data that is not immediately available; returns EAGAIN if it would have to read from storage; only meaningful for preadv2() |
| RWF_APPEND | 0x10 | 4.16 | Per-write O_APPEND; offset ignored, data always appended; offset -1 still updates the current offset |
| RWF_NOAPPEND | 0x20 | 6.9 | Do not honor O_APPEND for this pwritev2(); historical bug where O_APPEND silently ignored the offset is bypassed |
| RWF_ATOMIC | 0x40 | 6.11 | Torn-write protection (see below) |
| RWF_DONTCACHE | 0x80 | 6.14 | Drop the instantiated page-cache pages of the range when the I/O completes; write-dirtied ranges are kicked off for writeback; a hint, no hard guarantees; EOPNOTSUPP if unsupported |
| RWF_NOSIGNAL | 0x100 | (kernel master uapi) | Suppress SIGPIPE for pipe/socket writes; present in kernel headers, not described in man-pages 6.19 readv.2 |

RWF_ATOMIC note (sourced from man-pages 6.19 readv.2, fetched from man7.org; matches worklog 1-c): requests that the write to a regular file on a block-based filesystem be issued with torn-write protection: on power or hardware failure the write lands all or none, never a mix of old and new data. Constraints: total write length must be a power of 2 within [stx_atomic_write_unit_min, stx_atomic_write_unit_max] from statx(2); the offset must be naturally aligned to the write length; iovcnt is capped by stx_atomic_write_segments_max; works only with O_DIRECT (buffered writes unsupported); O_SYNC or O_DSYNC (or RWF_SYNC on the same call) is required to guarantee consistency between the in-core file state and the device. Violations fail with EINVAL. The statx side of these fields is on statx.md. RWF_ATOMIC is absent from the cached man-pages snapshot; the host glibc 2.41 headers define RWF_ATOMIC (0x40) but their RWF_SUPPORTED mask stops there, so RWF_DONTCACHE and RWF_NOSIGNAL are not defined by the installed headers.

## Security and notes

- O_APPEND gives atomic append: the seek and the write are one step; on NFS, concurrent appends can still corrupt files because appending is simulated client-side.
- Delayed-error honesty: only fsync(2) tells you the data is on stable storage; on NFS a successful write may not even have reserved space.
- Writing an executable, swap file, or module being loaded fails ETXTBSY at open() time, not at write() time (open.md).
- File seals (F_SEAL_WRITE, F_SEAL_GROW) make write() fail EPERM on sealed memfds (fcntl.md).

## References

- man2/write.2 in the cached man-pages tree (dated 2021-03-22); man2/readv.2 for the RWF_* versions, plus the man-pages 6.19 readv.2 fetched from man7.org (source-cache/fetched/readv.2.current.plain).
- Constants: /usr/include/x86_64-linux-gnu/bits/uio-ext.h; kernel master include/uapi/linux/fs.h (fetched copy source-cache/fetched/k-uapi-fs.h).
- [Syscalls ledger](../ledger.md) row SC-write; sibling pages [read](read.md), [readv](readv.md), [fcntl](fcntl.md), [statx](statx.md); [domain hub](overview.md).
