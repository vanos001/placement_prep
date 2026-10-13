# `dup` / `dup2` / `dup3` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

**Signature** -- `int dup(int oldfd);` `int dup2(int oldfd, int newfd);`
`int dup3(int oldfd, int newfd, int flags);` -- `unistd.h`.

**Libc side** -- `dup` = `fcntl(oldfd, F_DUPFD, 0)`; `dup2` performs the
close-and-copy atomically and treats `oldfd` invalid as a no-op that
does not close `newfd` (manual, *Duplicating Descriptors*). `dup3` is
GNU (`_GNU_SOURCE`, symbol `GLIBC_2.9` on installed glibc) and accepts
only `O_CLOEXEC`; POSIX.1-2024 adopted it. Duplicates share one file
offset and status flags but not descriptor flags. The redirection recipe
(`dup2` before `exec`) and the syscall numbers live in
[Descriptors and File I/O](../../../syscalls/descriptors-io/overview.md) `dup` entry.
