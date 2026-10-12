# open(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | open 2 / 5 / - / 5; openat 257 / 295 / 56 / 322; creat 85 / 8 / - / 8 (per-call table below) |
| Since (kernel) | open 1.0; creat 1.0; openat 2.6.16 (glibc 2.4) |
| Man page | man2/open.2 (creat.2 and openat.2 are .so aliases of it) |
| glibc wrapper | open/openat/creat declared in <fcntl.h>; openat needs _POSIX_C_SOURCE >= 200809L (glibc 2.10+; _ATFILE_SOURCE before); since glibc 2.26 the open() wrapper issues the openat() system call |
| Aliases covered | openat, creat |
| Ledger ID | SC-open, SC-openat, SC-creat |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| open | 2 | 5 | - | 5 | 1.0 |
| openat | 257 | 295 | 56 | 322 | 2.6.16 |
| creat | 85 | 8 | - | 8 | 1.0 |

Hub row note: the domain hub's grouped row shows creat's number set (85 / 8 / - / 8) because one row cannot hold three calls; the per-call values above are the ledger values. There is no `open` slot on arm64-generic: glibc's open() there resolves to openat (56), consistent with the glibc 2.26+ wrapper behavior (man2/open.2 C library/kernel differences; worklog 1-c numbering notes).

## Purpose

open() resolves pathname and returns a new file descriptor referring to a new open file description; the descriptor is the lowest-numbered free one and the file offset starts at 0. The open file description carries the file offset and the file status flags; duplicated descriptors and fork children share it, while separate open() calls create separate descriptions. openat() is the dirfd-relative form of the same operation; creat() is exactly open(pathname, O_CREAT | O_WRONLY | O_TRUNC, mode). The flags argument splits into one access mode plus file creation flags (which affect the open itself) and file status flags (which affect later I/O and are partly readable/changeable through fcntl(2)).

## Synopsis

```c
#include <fcntl.h>
int open(const char *pathname, int flags);
int open(const char *pathname, int flags, mode_t mode);
int openat(int dirfd, const char *pathname, int flags, ...);
int creat(const char *pathname, mode_t mode);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| pathname | Path to open; may create the file if O_CREAT is set. |
| flags | One access mode (O_RDONLY/O_WRONLY/O_RDWR) ORed with creation and status flags (table below). |
| mode | Permission bits for a created file; required when O_CREAT or O_TMPFILE is set, ignored otherwise. Effective mode is mode & umask in the absence of a default ACL. |
| dirfd (openat) | Absolute pathname: dirfd ignored. Relative + AT_FDCWD: relative to cwd. Relative + fd: relative to that directory, which must be opened O_RDONLY or O_PATH. Passing an invalid fd as dirfd makes any relative pathname fail EBADF, a trick to require an absolute path. |

O_* constants (values from /usr/include/asm-generic/fcntl.h and bits/fcntl-linux.h, x86-64 octal; "since" from man2/open.2):

| Constant | Value | Since | Note |
|---|---|---|---|
| O_RDONLY, O_WRONLY, O_RDWR | 0, 1, 2 | - | Access mode is the low 2 bits; nonstandard access mode 3 is a check-only fd used by some drivers |
| O_CREAT | 00000100 | - | Create as regular file; owner = euid; group by SysV/BSD semantics per parent set-GID bit |
| O_EXCL | 00000200 | - | With O_CREAT: fail EEXIST if the file exists; symlinks not followed. Alone: only block-device EBUSY check (Linux 2.6+) |
| O_NOCTTY | 00000400 | - | Do not make the terminal the controlling terminal |
| O_TRUNC | 00001000 | - | Truncate existing regular file opened for writing |
| O_APPEND | 00002000 | - | Position at EOF before each write, atomically in one step |
| O_NONBLOCK / O_NDELAY | 00004000 | - | Nonblocking open and I/O; no effect on regular files and block devices |
| O_DSYNC | 00010000 | - | Data-integrity completion (like fdatasync per write) |
| O_ASYNC | 020000 | - | Signal-driven I/O (SIGIO); glibc header constant, kernel headers use the FASYNC synonym |
| O_LARGEFILE | 00100000 | - | 32-bit large-file support; _FILE_OFFSET_BITS=64 preferred |
| O_DIRECTORY | 00200000 | 2.1.126 | Fail ENOTDIR if pathname is not a directory |
| O_NOFOLLOW | 00400000 | 2.1.126 | Fail ELOOP if the basename is a symlink |
| O_NOATIME | 01000000 | 2.6.8 | Do not update st_atime; needs ownership or CAP_FOWNER |
| O_CLOEXEC | 02000000 | 2.6.23 | Set FD_CLOEXEC atomically at open time |
| O_SYNC | 04010000 | 2.6.33 | File-integrity completion; before 2.6.33 O_SYNC behaved like O_DSYNC and O_DSYNC kept the old bit |
| O_DIRECT | 00040000 | 2.4.10 | Minimize cache effects; alignment limits vary by filesystem and kernel version |
| O_PATH | 010000000 | 2.6.39 | Location-only fd: read/write/ioctl/mmap fail EBADF; close, dup, F_GETFD/F_GETFL, fstat (3.6), fchdir (3.5) and *at dirfd use work |
| O_TMPFILE | 020200000 | 3.11 | Unnamed temporary regular file in the given directory; needs O_WRONLY or O_RDWR; filesystem support required |

AT_* constants for this family: openat() itself takes no flags argument; the only AT_* constant it uses is the dirfd special value AT_FDCWD = -100 (/usr/include/linux/fcntl.h). The other AT_* bits (AT_SYMLINK_NOFOLLOW, AT_EMPTY_PATH, and so on) belong to the other *at() calls and are documented on their pages (fstatat on stat.md, statx on statx.md).

## Return value and errors

On success all three calls return the new nonnegative file descriptor. On error, -1 and errno: EACCES (search/permission denied, including the protected_fifos and protected_regular sysctl cases), EBADF (openat: relative path with invalid dirfd), EBUSY (O_EXCL on a mounted block device), EDQUOT, EEXIST (O_CREAT|O_EXCL), EFAULT, EINTR (blocked open of a slow device interrupted), EINVAL (O_DIRECT unsupported, invalid flag, O_TMPFILE misuse), EISDIR, ELOOP, EMFILE/ENFILE, ENAMETOOLONG, ENOENT, ENOMEM, ENOSPC, ENOTDIR, ENXIO, EOPNOTSUPP (O_TMPFILE unsupported), EOVERFLOW (32-bit open of a >2 GiB file; EFBIG before 2.6.24), EPERM (O_NOATIME without ownership; write blocked by a file seal, see fcntl.md), EROFS, ETXTBSY (writing a running executable, swap file, or module being loaded), EWOULDBLOCK (incompatible lease).

## Security and notes

- O_CLOEXEC is the fd-leak defense: setting FD_CLOEXEC via a separate fcntl(F_SETFD) after open() races with a concurrent fork+execve in multithreaded programs and can leak the fd into the child (man2/open.2, and the same warning on fcntl.md F_SETFD).
- O_NOATIME requires the caller's effective UID to match the file owner, or CAP_FOWNER in the caller's user namespace; otherwise EPERM.
- Writing can be refused with EPERM by F_SEAL_SHRINK/GROW/WRITE seals on a memfd (fcntl.md).
- O_PATH descriptors are the /proc/self/fd/N idiom for exec/fexecve without read permission; O_PATH needs no permission on the object itself, only search permission on the path prefix.
- openat2 (kernel 5.6; x64 437 / i386 437 / g64 437 / arm32 437) extends openat with struct open_how and RESOLVE_* restrictions; it has its own hub row and page (openat2.md), not covered here.

## References

- man2/open.2 in the cached man-pages tree (dated 2021-08-27); .so aliases creat.2, openat.2.
- Constants: /usr/include/asm-generic/fcntl.h, /usr/include/x86_64-linux-gnu/bits/fcntl-linux.h, /usr/include/linux/fcntl.h.
- [Syscalls ledger](../ledger.md) rows SC-open, SC-openat, SC-creat; kernel tables in source-cache/kernel.
- [Domain hub](overview.md) for status and sibling pages.
