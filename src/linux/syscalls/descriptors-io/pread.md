# pread(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | pread64 17 / 180 / 67 / 180; pwrite64 18 / 181 / 68 / 181 (per-call table below) |
| Since (kernel) | 2.1.60 (i386 table entries 2.1.69, man VERSIONS); renamed to *64 in kernel 2.6 with unchanged numbers (man C library/kernel differences); hub shows -- |
| Man page | man2/pread.2 (pwrite.2 is a .so alias of it; local cache, dated 2021-03-22) |
| glibc wrapper | pread/pwrite need _XOPEN_SOURCE >= 500 or _POSIX_C_SOURCE >= 200809L (glibc 2.12+); wrappers handle the *64 renaming transparently |
| Aliases covered | pread, pwrite, pread64, pwrite64 |
| Ledger ID | SC-pread64, SC-pwrite64 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| pread64 | 17 | 180 | 67 | 180 | 2.1.60 |
| pwrite64 | 18 | 181 | 68 | 181 | 2.1.60 |

## Purpose

pread() reads up to count bytes from fd at absolute offset into buf without changing the file offset; pwrite() writes count bytes from buf at absolute offset without changing the file offset. The fd must be seekable. Because the position is passed per call, multiple threads can perform positioned I/O on one shared open file description without racing on the shared file offset -- the use case the man page names for multithreaded applications (plain read/write.md share one offset).

## Synopsis

```c
#include <unistd.h>
ssize_t pread(int fd, void *buf, size_t count, off_t offset);
ssize_t pwrite(int fd, const void *buf, size_t count, off_t offset);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd | Seekable file descriptor (pipe/FIFO fail; see lseek errors). |
| buf / count | Destination/source buffer and byte count; short transfers are not an error. |
| offset | Absolute position from the start of the file; the file offset is left unchanged. |

## Return value and errors

Returns the number of bytes transferred (0 from pread() means EOF); -1 with errno on error. pread() can fail with any read(2) or lseek(2) error, pwrite() with any write(2) or lseek(2) error.

## Flags and constants

No flag arguments. The kernel slots were named pread/pwrite until 2.6 and pread64/pwrite64 since, with the same numbers; on 32-bit architectures the 64-bit offset argument forces register-alignment variants (syscall(2)). The glibc preadv/pwritev and preadv2/pwritev2 families (readv.md) add iovec scatter-gather and RWF_* flags on top of the same positioned-offset model.

## Security and notes

- BUGS (man page): POSIX requires O_APPEND to have no effect on where pwrite() writes, but Linux appends to the end of the file regardless of offset when the file was opened O_APPEND (kernel bug 43178).
- Positioned I/O does not remove the need for locking when a file is modified concurrently by several writers; it only removes the shared-offset race.

## References

- man2/pread.2 in the cached man-pages tree; .so alias pwrite.2.
- [Syscalls ledger](../ledger.md) rows SC-pread64, SC-pwrite64; kernel tables in source-cache/kernel.
- Siblings: [read](read.md), [write](write.md), [lseek](lseek.md), [readv](readv.md).
