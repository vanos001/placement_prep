# `fsync` / `fdatasync` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

**Signature** -- `int fsync(int fd);` `int fdatasync(int fd);` --
`unistd.h`.

**Libc side** -- block until the kernel has flushed: `fsync` all data
plus metadata, `fdatasync` data only (metadata may lag, manual,
*Synchronizing I/O operations*). Returns `0` or `-1`+`errno` (`EBADF`,
`EINVAL` in the manual's list; `EIO`/`EROFS` at the syscall layer, see
the `sync` family entry of
[Descriptors and File I/O](../../../syscalls/descriptors-io/overview.md)). `fsync` is a
cancellation point. glibc never calls these implicitly -- the manual is
explicit that `write` returning (and therefore `fflush` completing)
does not imply the media got the data; programs that need durability
call `fsync(fileno(f))` after `fflush(f)`. The whole-system `sync` and
per-file `syncfs` variants are documented at the syscall layer.
