# `remove` / `rename` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-remove (group) |
| Header | `stdio.h` (both) |
| Provenance | ISO C; POSIX.1-2008 adds `renameat` |
| Status | documented |

**Signature** -- `int remove(const char *filename);` `int rename(const
char *old, const char *new);` `int renameat(int oldfd, const char *old,
int newfd, const char *new);`

**Semantics** -- thin ISO C wrappers over the filesystem syscalls:
`remove` calls `unlink` on files and `rmdir` on directories (manual
comment, *Deleting Files*), dispatching on the path's type; `rename`
maps to `rename(2)`/`renameat(2)`, renaming atomically: there is no
instant at which `new` does not resolve, and if `old` and `new` are
different names for the same file POSIX requires success-with-no-change
(manual, *Renaming Files*). Directory rename semantics: a non-directory
`old` never overwrites a directory and vice versa; a renamed directory
may not be a subdirectory of its own destination. Both return `0` or
`-1` with `errno` (`ENOENT`, `EEXIST`/`ENOTEMPTY`, `EXDEV` for
cross-device `rename`, `EBUSY`, ...). For descriptor-level behavior and
kernel versions see
[Descriptors and File I/O](../../../syscalls/descriptors-io/overview.md).
