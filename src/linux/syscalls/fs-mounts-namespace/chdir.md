# chdir(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | chdir: x64 80 / i386 12 / arm64-generic 49 / arm32 12; fchdir: x64 81 / i386 133 / arm64-generic 50 / arm32 133 |
| Since (kernel) | 1.0 (hub; both calls) |
| Man page | man2/chdir.2 covers both (local cache, dated 2021-03-22); man2/fchdir.2 is a roff `.so` alias -> chdir.2 |
| glibc wrapper | Yes; `chdir()` / `fchdir()` in `<unistd.h>`; fchdir feature gates: `_XOPEN_SOURCE >= 500` or `_POSIX_C_SOURCE >= 200809L` (glibc >= 2.12) or `_BSD_SOURCE` (glibc <= 2.19) |
| Aliases covered | `fchdir` (SC-fchdir, grouped here) |
| Ledger ID | SC-chdir |

## Purpose

`chdir()` changes the current working directory of the calling process to
`path`; `fchdir()` does the same for the directory open on `fd`. The working
directory is the starting point for resolving relative pathnames, is inherited
by children created with `fork(2)`, and is left unchanged by `execve(2)`. It is
per-process (threads share it) and is one of the three roots of pathname
resolution alongside the root directory ([chroot.md](chroot.md)) and the mount
tree ([overview.md](overview.md)).

## Synopsis

    #include <unistd.h>
    int chdir(const char *path);
    int fchdir(int fd);

## Arguments and behavior

| Call | Argument | Notes |
|---|---|---|
| `chdir()` | `path` | Pathname of the new working directory |
| `fchdir()` | `fd` | Open descriptor referring to a directory |

`fchdir()` is the fd-based escape hatch used by shells after `open()` on a
candidate directory and by programs that must not depend on path strings; it
also lets a process return to a directory it could reach before a
[chroot(2)](chroot.md) call, which is part of the documented chroot escape
pattern. The man page's fchdir section lists no special flags or gate macros
beyond the feature-test requirements in the field table.

## Return value and errors

Returns 0 on success, -1 on error with `errno` set. `chdir()` errors per the
man page: `EACCES` (search permission denied on a path component),
`EFAULT`, `EIO`, `ELOOP`, `ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `ENOTDIR`.
`fchdir()` errors: `EACCES` (search permission denied on the directory open on
`fd`), `EBADF` (invalid descriptor), `ENOTDIR`. Filesystems may return other
errors.

## Security and notes

No capability is involved; success requires ordinary filesystem search
(execute) permission on every component traversed. `fchdir()` can bypass
path-based access control that watches directory changes: a process holding an
open directory fd can re-enter it even if the path is later revoked or hidden
by mounts, so sandboxes must close or constrain directory fds. Combined with
`pivot_root(2)` ([pivot_root.md](pivot_root.md)), the man page idiom
`chdir(new_root); pivot_root(".", "."); umount2(".", MNT_DETACH)` relies on
`chdir()` ordering; see [umount2.md](umount2.md).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/chdir.2`, `.so` alias `fchdir.2`
- Online: https://man7.org/linux/man-pages/man2/chdir.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (80, 81),
  `syscall_32.tbl` (12, 133), `syscall_generic.tbl` (49, 50)
- Declarations: installed `/usr/include/unistd.h` (glibc 2.41)
