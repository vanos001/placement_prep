# `readv` / `writev` / `pread` / `pwrite` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

**Signature** -- `ssize_t readv(int fd, const struct iovec *iov, int
iovcnt);` `ssize_t writev(int fd, const struct iovec *iov, int iovcnt);`
`ssize_t pread(int fd, void *buf, size_t count, off_t offset);` `ssize_t
pwrite(int fd, const void *buf, size_t count, off_t offset);` --
`sys/uio.h` for the vector pair, `unistd.h` for the positioned pair.

**Libc side** -- scatter/gather and positioned I/O translate like
`read`/`write`: byte counts, `0` = EOF, `-1`+`errno`. `pread`/`pwrite`
add `EINVAL` (negative offset) and `ESPIPE` (unseekable) without moving
the file offset. Declared under XSI gates; `pread64`/`pwrite64` are the
LFS twins (manual, *Input and Output Primitives*). The GNU
`preadv2`/`pwritev2` flag-taking variants (glibc gates on
`_GNU_SOURCE`) are covered with `RWF_*` flags in the
[syscall chapter](../../../syscalls/descriptors-io/overview.md) `preadv2`/`pwritev2`
entry.
