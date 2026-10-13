# `isatty` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

**Signature** -- `int isatty(int fd);` -- `unistd.h`.

**Libc side** -- returns `1` if `fd` refers to a terminal, else `0` with
`errno` set: `EBADF` (invalid fd) or `ENOTTY` (`isatty(3)`). That it
*sets* `errno` on the zero path -- rather than merely returning zero --
matters for code that reports `strerror(errno)` unconditionally.
Typical use: pick buffering or output format by `isatty(STDOUT_FILENO)`.
Terminal attribute access itself is the `tcgetattr` family, not this
predicate.
