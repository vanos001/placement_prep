# `lseek` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

**Signature** -- `off_t lseek(int fd, off_t offset, int whence);`

**Libc side** -- returns the resulting offset or `(off_t)-1`+`errno`
(`ESPIPE` on pipes). `SEEK_SET`/`SEEK_CUR`/`SEEK_END` are shared with
`fseek`. `lseek(fd, 0, SEEK_CUR)` is the idiom for reading the position
(manual, *File Position Primitive*). `lseek64` (LFS) exists for
32-bit hosts; with `_FILE_OFFSET_BITS == 64` `lseek` maps to it. The
descriptor-side model (shared OFD offsets, `ESPIPE`, sparse-file
`SEEK_HOLE`/`SEEK_DATA` GNU extensions) is the `lseek` entry of
[Descriptors and File I/O](../../../syscalls/descriptors-io/overview.md).
