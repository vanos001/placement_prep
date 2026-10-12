# `chdir` / `fchdir` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [chdir(2)](../../../syscalls/fs-mounts-namespace/chdir.md).

| Field | Value |
|---|---|
| Header | `unistd.h` (both) |
| Standards | POSIX.1-2001/2008, SVr4, 4.4BSD (both; manual tags `fchdir` XPG) |
| Exported | `chdir@@GLIBC_2.2.5`, `fchdir@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations; `chdir(2)` carries no ATTRIBUTES table in man-pages 5.14) |
| Ledger ID | GLIBC-chdir, GLIBC-fchdir |

## Declaration and gates

```c
#include <unistd.h>

int chdir(const char *path);
int fchdir(int fd);
```

`chdir` is declared ungated (`/usr/include/unistd.h` line 517). `fchdir`
sits in the `#if defined __USE_XOPEN_EXTENDED || defined __USE_XOPEN2K8`
block at lines 519-523, matching the `chdir(2)` gate table
(`_XOPEN_SOURCE >= 500`, or `_POSIX_C_SOURCE >= 200809L` since glibc 2.12).

## Semantics

`chdir` sets the calling process's current working directory to `path`;
`fchdir` is identical except the directory is named by an open file
descriptor, typically `open(path, O_RDONLY | O_DIRECTORY)` or the
descriptor of a directory stream obtained with `dirfd(3)`
(`chdir(2)`, manual *Working Directory*). Both return 0 on success and
-1 on error. The working directory is the starting point for resolving
relative pathnames; a child created by `fork` inherits it and `execve`
leaves it unchanged (`chdir(2)` NOTES).

## Gotchas and portability

- The working directory is a process-wide property, not per-thread:
  one thread's `chdir` silently moves every other thread. Position the
  offsets differently with `openat`-family calls instead of roaming.
- The manual's standard save/restore advice is not `getcwd` +
  `chdir` but `open(".")` + `fchdir` -- faster and immune to
  `PATH_MAX` and unlink races (`getcwd(3)` NOTES).
- `getcwd(NULL, 0)` (glibc extension) and `get_current_dir_name` are
  covered in [getcwd-get_current_dir_name.md](getcwd-get_current_dir_name.md).
- musl 1.2.5: `chdir` is a bare `SYS_chdir` wrapper
  (`src/unistd/chdir.c`); `fchdir` adds a `/proc/self/fd`
  fallback so `fchdir` still works on systems without procfs mounted
  (`src/unistd/fchdir.c`).

## Errors

`chdir`: `EACCES`, `EFAULT`, `EIO`, `ELOOP`, `ENAMETOOLONG`, `ENOENT`,
`ENOMEM`, `ENOTDIR` (`chdir(2)`). `fchdir` drops the path errors and
adds `EBADF` (invalid fd); `EACCES` there means search permission
denied on the open directory. The manual additionally lists `EINTR`
and `EIO` for `fchdir` (filesys.texi, *Working Directory*).

## References

- glibc manual: `filesys.texi`, node *Working Directory*
- man2: `chdir.2` (covers `fchdir`; `fchdir.2` is a `.so` alias)
- headers: `/usr/include/unistd.h` lines 517, 519-523
- symbols: `nm -D --with-symbol-versions libc.so.6`
