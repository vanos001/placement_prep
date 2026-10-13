# `read` / `write` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

**Signature** -- `ssize_t read(int fd, void *buf, size_t count);`
`ssize_t write(int fd, const void *buf, size_t count);`

**Libc side** -- pure translation: bytes on success, `0` = EOF for
`read`, `-1`+`errno` on failure. Short counts are not errors and the
caller loops (manual, *Input and Output Primitives*). Both are
cancellation points in glibc; `write`'s data may land even when it
reports `EINTR`-style failure. `read` is the primitive underneath every
stream input function (manual). Syscall semantics, `EIO` on background
terminal reads, and `EAGAIN` aliasing are in the
[syscall chapter](../../../syscalls/descriptors-io/overview.md) `read`/`write` entries.
