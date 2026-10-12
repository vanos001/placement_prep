# lseek(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | lseek 8 / 19 / 62 / 19; _llseek - / 140 / - / 140 (per-call table below) |
| Since (kernel) | lseek 1.0; _llseek 1.2 |
| Man page | man2/lseek.2; man2/llseek.2 (whose only .so alias is _llseek.2) |
| glibc wrapper | lseek() declared in <unistd.h>, POSIX.1-2001, thin wrapper; _llseek has no glibc wrapper, only syscall(2) (man2/llseek.2); the 32-bit libc layer for large offsets is lseek64(3) |
| Aliases covered | _llseek |
| Ledger ID | SC-lseek, SC-_llseek |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| lseek | 8 | 19 | 62 | 19 | 1.0 |
| _llseek | - | 140 | - | 140 | 1.2 |

_llseek exists only on 32-bit ABIs that need to pass a 64-bit offset in two register halves; the 64-bit arches have no slot, which is why the domain hub lists it as a separate grouped row (SC-_llseek: x64 --, i386 140, g64 --, arm 140, Since 1.2).

## Purpose

lseek() repositions the file offset of the open file description associated with fd. The offset is a property of the open file description, not of the descriptor or the file: it is shared by duplicates (dup.md) and by children after fork, so a seek through one descriptor moves the position seen through the others. The offset may be set beyond end of file without changing the file size; reading a gap later returns zero bytes until data is written there (holes). SEEK_DATA and SEEK_HOLE (kernel 3.1) map the data/hole layout of sparse files for backup and copy tools, with the honest limitation that a filesystem may report no holes at all. _llseek is the 32-bit form of the same operation: it takes offset_high and offset_low, computes (offset_high << 32) | offset_low, repositions exactly like lseek(), and writes the resulting 64-bit offset back through a result pointer instead of a return value.

## Synopsis

```c
#include <unistd.h>
off_t lseek(int fd, off_t offset, int whence);

/* raw _llseek, no glibc wrapper */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS__llseek, unsigned int fd, unsigned long offset_high,
            unsigned long offset_low, loff_t *result, unsigned int whence);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd | Open file descriptor; EBADF if not open. Pipes, sockets, and FIFOs are not seekable: ESPIPE (on Linux, a terminal device also fails ESPIPE). |
| offset | Byte offset interpreted per whence; may move before or beyond end of file. |
| whence | SEEK_SET (0): offset from file start. SEEK_CUR (1): offset from current position. SEEK_END (2): offset from file size. SEEK_DATA (3) and SEEK_HOLE (4), since 3.1, need _GNU_SOURCE from <unistd.h>: adjust to the next data or hole location at or beyond offset; fail ENXIO if offset is past EOF (and for SEEK_DATA in a trailing hole). |
| _llseek: result | loff_t (64-bit signed) pointer receiving the new offset; EFAULT if unreachable. |

SEEK_* values from /usr/include/unistd.h (SEEK_SET 0, SEEK_CUR 1, SEEK_END 2; SEEK_DATA 3, SEEK_HOLE 4 under _GNU_SOURCE). Filesystems supporting SEEK_DATA/SEEK_HOLE per man2/lseek.2: Btrfs 3.1, OCFS 3.2, XFS 3.5, ext4 3.8, tmpfs 3.8, NFS 3.18, FUSE 4.5, GFS2 4.15.

## Return value and errors

lseek() returns the resulting offset as bytes from the beginning of the file, or (off_t) -1 with errno: EBADF, EINVAL (invalid whence; resulting offset negative or beyond the end of a seekable device), ENXIO (SEEK_DATA/SEEK_HOLE conditions above), EOVERFLOW (result not representable in off_t), ESPIPE. _llseek() returns 0 on success, -1 with errno: EBADF, EFAULT (copying the result failed), EINVAL (invalid whence).

## Flags and constants

None: lseek()/ _llseek() take no flag arguments. Hole mapping interacts with fallocate(2) modes and statx DAX state, both documented on their own pages (see the [domain hub](overview.md)).

## Security and notes

- The offset is shared state: an lseek() through any duplicated descriptor races with concurrent readers using other duplicates of the same open file description.
- O_APPEND makes every write() move to end of file regardless of lseek() (man2/lseek.2 NOTES); the append-position itself is atomic per write (open.md, write.md).
- lseek() does not extend the file; seeking past EOF and writing leaves a hole that reads as zeros.
- A filesystem is never obliged to report holes: SEEK_HOLE may always answer "end of file", and explicit zero runs may not be reported as holes (man2/lseek.2).
- _llseek is Linux-specific; the man page's own note is "you probably want to use the lseek(2) wrapper function instead". The llseek(3) library function is a different, obsolete thing, documented under lseek64(3).
- glibc's lseek() wrapper handles the off_t size details per architecture; with _FILE_OFFSET_BITS=64 there is one 64-bit lseek on modern 64-bit systems (man2/lseek.2 C library/kernel differences).

## References

- man2/lseek.2 and man2/llseek.2 in the cached man-pages tree (both dated 2021-03-22); _llseek.2 is an .so alias of llseek.2.
- Constants: /usr/include/unistd.h (SEEK_*).
- [Syscalls ledger](../ledger.md) rows SC-lseek, SC-_llseek; kernel tables in source-cache/kernel; siblings [dup](dup.md), [read](read.md), [readv](readv.md); [domain hub](overview.md).
