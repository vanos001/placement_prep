# sendfile(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sendfile 40 / 187 / 71 / 187; sendfile64 - / 239 / - / 239 (per-call table below) |
| Since (kernel) | sendfile 2.2; sendfile64 2.6 (<sys/sendfile.h> present since glibc 2.1) |
| Man page | man2/sendfile.2 (sendfile64.2 is an .so alias of it) |
| glibc wrapper | sendfile() declared in <sys/sendfile.h>; host glibc 2.41 exports sendfile@@GLIBC_2.2.5 (nm -D); the glibc sendfile() wrapper transparently deals with the sendfile/sendfile64 kernel difference (man2/sendfile.2 NOTES) |
| Aliases covered | sendfile64 |
| Ledger ID | SC-sendfile, SC-sendfile64 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| sendfile | 40 | 187 | 71 | 187 | 2.2 |
| sendfile64 | - | 239 | - | 239 | 2.6 |

sendfile64 (2.6) is the large-offset twin for 32-bit ABIs: the same transfer with a wider type for the offset argument; there is no separate slot on 64-bit arches.

## Purpose

sendfile() copies data between two descriptors inside the kernel, avoiding the read-then-write round trip through user space. in_fd must be a descriptor whose file supports mmap(2)-like operations -- in practice a regular file or block device, never a socket -- and out_fd is the destination. The offset argument selects the semantics: NULL reads from in_fd's file offset and updates it; non-NULL reads from *offset and on return stores the offset past the last byte read, leaving in_fd's file offset untouched. Before 2.6.33 out_fd had to be a socket; since 2.6.33 it can be any file, and for a regular-file out_fd the file offset is adjusted. sendfile() transfers at most 0x7ffff000 (2,147,479,552) bytes per call, on 32-bit and 64-bit alike, and may write fewer bytes than requested -- the caller retries for the rest. It was designed for serving files over TCP: pair it with TCP_CORK to avoid small packets around the payload (man2/sendfile.2 NOTES).

## Synopsis

```c
#include <sys/sendfile.h>
ssize_t sendfile(int out_fd, int in_fd, off_t *offset, size_t count);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| out_fd | Destination descriptor, open for writing; socket-only before 2.6.33, any file since; O_APPEND on out_fd is not supported (EINVAL). |
| in_fd | Source descriptor, open for reading; must support mmap(2)-like operations (no sockets); EINVAL if it does not. |
| offset | NULL: use and update in_fd's file offset. Non-NULL: *offset is the start offset; on return it holds the offset after the last byte read; in_fd's file offset is unchanged. Non-NULL with a nonseekable in_fd is ESPIPE. |
| count | Number of bytes to copy; capped at 0x7ffff000. |

## Return value and errors

Success returns the number of bytes written to out_fd (possibly fewer than requested; retry with the remainder). On error, -1 and errno: EAGAIN (O_NONBLOCK and the write would block), EBADF (in_fd not open for reading or out_fd not open for writing), EFAULT (bad address), EINVAL (descriptor not valid or locked; mmap-like operation unavailable for in_fd; count negative; O_APPEND on out_fd), EIO (unspecified error while reading in_fd), ENOMEM (insufficient memory reading in_fd), EOVERFLOW (count too large -- would exceed the maximum size of the input or output file), ESPIPE (offset non-NULL but in_fd not seekable).

## Flags and constants

None: sendfile() takes no flags argument. Per-I/O behavior flags do not exist here; the richer generalization is splice() (splice.md) with its SPLICE_F_* mask, and copy_file_range() for file-to-file copies (see the [domain hub](overview.md)).

## Security and notes

- Zero-copy caveat: if out_fd is a socket or pipe with zero-copy support, the transferred portions of in_fd's file must remain unmodified until the reader consumes them (man2/sendfile.2 NOTES) -- do not truncate or rewrite the source mid-transfer.
- History quirk: in Linux 2.4 and earlier out_fd could be a regular file, the 2.6.x series removed that, and 2.6.33 restored it (man2/sendfile.2 NOTES).
- Fallback advice: applications should fall back to read()/write() when sendfile() fails with EINVAL or ENOSYS (filesystem without support, or pre-2.2 kernel).
- The 0x7ffff000 cap and the partial-write retry pattern are shared with read()/write()/readv()/writev() (read.md, write.md, readv.md).
- sendfile() changes neither file's offset when offset is non-NULL, which is what makes loops over file chunks safe.

## References

- man2/sendfile.2 in the cached man-pages tree (dated 2021-03-22); .so alias sendfile64.2.
- [Syscalls ledger](../ledger.md) rows SC-sendfile, SC-sendfile64; siblings [splice](splice.md), [read](read.md), [write](write.md); [domain hub](overview.md).
