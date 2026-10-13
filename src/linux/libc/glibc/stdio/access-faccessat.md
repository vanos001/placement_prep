# `access` / `faccessat` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

**Signature** -- `int access(const char *path, int mode);` `int
faccessat(int dirfd, const char *path, int mode, int flags);` --
`unistd.h`; `mode` is `F_OK`/`R_OK`/`W_OK`/`X_OK`.

**Libc side** -- checks *real* UID/GID (unlike actual opens, which use
effective IDs); `faccessat` adds the `dirfd` model plus `AT_EACCESS`
(effective IDs) and `AT_SYMLINK_NOFOLLOW`. GNU extras `euidaccess` and
`eaccess` check effective IDs by path. Return `0` or `-1`+`errno`
(`EACCES`, `ENOENT`, `EROFS`, ... -- full list in the
[syscall chapter](../../../syscalls/descriptors-io/overview.md) `access` entry, which
also tells the `faccessat2` story: the raw `faccessat` syscall has no
flags argument, so pre-2.33 glibc emulated `AT_*` via `fstatat`; the
installed glibc still exports only `faccessat`, no `faccessat2`
symbol). TOCTOU-prone by design.
