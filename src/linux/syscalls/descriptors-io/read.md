# read(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 0 / 3 / 63 / 3 |
| Since (kernel) | 1.0 |
| Man page | man2/read.2 |
| glibc wrapper | read() declared in <unistd.h>, POSIX.1-2001; thin wrapper, no kernel-specific emulation |
| Aliases covered | none |
| Ledger ID | SC-read |

## Purpose

read() attempts to read up to count bytes from the file descriptor fd into buf. On seekable objects the transfer starts at the file offset, which is then advanced by the number of bytes actually read; at end of file the return is 0. A count of 0 may detect the documented errors but otherwise returns 0 with no side effects. Short reads are not errors: fewer bytes can be returned because only that much is available right now (pipes, terminals, sockets, end of file) or because the call was interrupted by a signal handler before any data arrived. The per-call RWF_* flag variants exist only on preadv2/pwritev2 (see readv.md and the flag table on write.md); plain read() takes no flags.

## Synopsis

```c
#include <unistd.h>
ssize_t read(int fd, void *buf, size_t count);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd | File descriptor open for reading; otherwise EBADF. Reading a directory fails with EISDIR. |
| buf | Destination buffer; EFAULT if outside the address space. With O_DIRECT the address, count, and file offset may need alignment or EINVAL. |
| count | Upper bound on the transfer. Linux caps the transfer at 0x7ffff000 (2,147,479,552) bytes on both 32-bit and 64-bit systems, returning the amount actually transferred. |

## Return value and errors

Success returns the number of bytes read (0 at end of file); the file position advances by that number. On error, -1 and errno, with the file position change unspecified. Errors: EAGAIN (O_NONBLOCK set and the read would block; POSIX allows EAGAIN or EWOULDBLOCK for sockets), EBADF, EFAULT, EINTR (interrupted by a signal before any data was read), EINVAL (object unsuitable for reading; O_DIRECT alignment; timerfd wrong buffer size), EIO (background process group reading its controlling terminal while ignoring or blocking SIGTTIN; low-level disk or tape I/O error; lost NFS advisory lock, an EIO that persists until the lock is removed or the fd closed), EISDIR. Other errors depend on the object connected to fd.

## Flags and constants

None: read() has no flags argument. Buffer-size and alignment behavior comes from O_DIRECT on open() (open.md). Per-I/O behavior flags (RWF_HIPRI, RWF_NOWAIT, and friends) exist only on the preadv2()/pwritev2() forms and are tabled on write.md.

## Security and notes

- POSIX XSI 2.9.7 requires read()/readv() file-offset updates to be atomic across threads sharing an open file description; before Linux 3.14 they were not, and concurrent reads could overlap. Fixed in 3.14 (man2/read.2 BUGS).
- On NFS, small reads may update st_atime only the first time because of client-side attribute caching.
- There is no automatic retry: glibc primitives fail with EINTR rather than restarting (glibc manual, Interrupted Primitives).
- The same 0x7ffff000 byte cap applies to write(), readv(), writev(), and sendfile() (their man pages).

## References

- man2/read.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-read; kernel table syscall_64.tbl (read = 0).
- Siblings: [write](write.md), [readv](readv.md), [open](open.md); [domain hub](overview.md).
