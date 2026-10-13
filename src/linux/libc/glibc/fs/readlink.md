# `readlink` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [readlink(2)](../../../syscalls/descriptors-io/readlink.md); attribute
> side: [stat-family.md](stat-family.md).

| Field | Value |
|---|---|
| Header | `unistd.h` |
| Standards | POSIX.1-2001/2008, 4.4BSD (first appeared in 4.2BSD per `readlink.2`) |
| Exported | `readlink@@GLIBC_2.2.5`, `readlinkat@@GLIBC_2.4` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations; `readlink.2` carries no ATTRIBUTES table in man-pages 5.14) |
| Ledger ID | GLIBC-readlink |

## Declaration and gates

```c
#include <unistd.h>

ssize_t readlink(const char *restrict pathname,
                 char *restrict buf, size_t bufsiz);
ssize_t readlinkat(int dirfd, const char *restrict pathname,
                   char *restrict buf, size_t bufsiz);
```

`readlink` is declared inside the POSIX.1-2001 block of
`/usr/include/unistd.h` (prototype lines 838-841, block ends line 848
with the fortify attribute), matching `readlink.2`'s gate table
(`_XOPEN_SOURCE >= 500 || _POSIX_C_SOURCE >= 200112L`).
`readlinkat` (lines 851-855) is under `__USE_ATFILE`.

## Semantics

Places the contents of the symbolic link `pathname` into `buf` without
appending a terminating null byte, silently truncating to `bufsiz`,
and returns the number of bytes placed -- so a return equal to
`bufsiz` means truncation may have occurred and the call should be
retried with a larger buffer (manual *Symbolic Links*). `readlinkat`
resolves relative paths against `dirfd`; since Linux 2.6.39 an empty
`pathname` with an `O_PATH|O_NOFOLLOW` descriptor reads the link the
descriptor points at (`readlink.2`).

## Gotchas and portability

- No NUL termination is the classic bug: size the buffer from
  `lstat`'s `st_size` plus one, but treat zero (magic `/proc`, `/sys`
  links) as "unknown -- use PATH_MAX" and always trust the return
  value over `st_size` (`readlink.2` NOTES/EXAMPLES).
- Type history: glibc up to 2.4 declared the return as `int`; POSIX
  requires `ssize_t`, and glibc followed (`readlink.2` NOTES).
- On old kernels the `readlinkat` wrapper falls back to `readlink`
  through a constructed `/proc/self/fd` path (`readlink.2`, Glibc
  notes).
- musl 1.2.5: thin `SYS_readlink`/`SYS_readlinkat` wrappers
  (`src/unistd/readlink.c`, `src/unistd/readlinkat.c`), same
  no-termination contract; musl's `realpath` is the usual
  higher-level alternative when a resolved path is wanted.

## Errors

`EACCES`, `EFAULT`, `EINVAL` (non-positive `bufsiz`, or the final
component is not a symlink), `EIO`, `ELOOP`, `ENAMETOOLONG`, `ENOENT`,
`ENOMEM`, `ENOTDIR`; `readlinkat` adds `EBADF` and a second `ENOTDIR`
for a non-directory `dirfd` (`readlink.2`).

## References

- glibc manual: `filesys.texi`, node *Symbolic Links*
- man2: `readlink.2` (covers `readlinkat`)
- headers: `/usr/include/unistd.h` lines 838-856
- symbols: `nm -D --with-symbol-versions libc.so.6`
