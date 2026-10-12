# stat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | stat 4 / 106 / - / 106; stat64 - / 195 / - / 195; fstat 5 / 108 / 80 / 108; fstat64 - / 197 / - / 197; lstat 6 / 107 / - / 107; lstat64 - / 196 / - / 196; newfstatat 262 / - / 79 / -; fstatat64 - / 300 / - / 327 (per-call table below) |
| Since (kernel) | stat, fstat, lstat 1.0; stat64, fstat64, lstat64 2.4; newfstatat, fstatat64 2.6.16 (glibc fstatat wrapper since 2.4) |
| Man page | man2/stat.2 (fstat.2, lstat.2, and fstatat.2 are .so aliases; newfstatat.2 is an .so alias of fstatat.2) |
| glibc wrapper | stat/fstat/lstat in <sys/stat.h>, POSIX; fstatat() needs _POSIX_C_SOURCE >= 200809L (glibc 2.10+; _ATFILE_SOURCE before); the underlying syscall the glibc fstatat() wrapper uses is called fstatat64() or, on some architectures, newfstatat() (man2/stat.2 C library/kernel differences) |
| Aliases covered | fstat, lstat, fstatat, stat64, fstat64, lstat64, fstatat64, newfstatat |
| Ledger ID | SC-stat, SC-fstat, SC-lstat, SC-stat64, SC-fstat64, SC-lstat64, SC-newfstatat, SC-fstatat64 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| stat | 4 | 106 | - | 106 | 1.0 |
| stat64 | - | 195 | - | 195 | 2.4 |
| fstat | 5 | 108 | 80 | 108 | 1.0 |
| fstat64 | - | 197 | - | 197 | 2.4 |
| lstat | 6 | 107 | - | 107 | 1.0 |
| lstat64 | - | 196 | - | 196 | 2.4 |
| newfstatat | 262 | - | 79 | - | 2.6.16 |
| fstatat64 | - | 300 | - | 327 | 2.6.16 |

Layout note for the merge step: the domain hub splits this family into rows pointing at stat.md, fstat.md, lstat.md, and fstatat.md; this single page covers the whole man2/stat.2 family (stat, fstat, lstat, fstatat and the *64 twins), with stat/lstat/fstat having no arm64-generic slots (glibc reaches them via newfstatat 79, matching man2/stat.2's strace observation) and the 32-bit ABIs carrying stat64/fstat64/lstat64/fstatat64 for large files (2.4).

## Purpose

These calls return information about a file into a struct stat: identity (st_dev, st_ino), type and permissions (st_mode), links and ownership (st_nlink, st_uid, st_gid), device ID for special files (st_rdev), size in bytes (st_size), preferred I/O block size (st_blksize), allocated 512-byte blocks (st_blocks), and nanosecond timestamps st_atim, st_mtim, st_ctim (since kernel 2.5.48; POSIX.1-2008 names). stat() and fstatat() follow symlinks; lstat() reports on the link itself; fstat() takes an already-open descriptor, so it needs no path permissions and is the way to stat an O_PATH descriptor via fstatat's AT_EMPTY_PATH. fstatat() generalizes all three: dirfd-relative lookup with the AT_* flags. Field layout varies across architectures and the structure has gone through three kernel-internal generations (__old_kernel_stat, stat, stat64) that glibc hides by calling the newest available call and repacking; on 64-bit systems there is a single call (man2/stat.2 C library/kernel differences).

## Synopsis

```c
#include <sys/stat.h>
int stat(const char *restrict pathname, struct stat *restrict statbuf);
int fstat(int fd, struct stat *statbuf);
int lstat(const char *restrict pathname, struct stat *restrict statbuf);

#include <fcntl.h>      /* Definition of AT_* constants */
#include <sys/stat.h>
int fstatat(int dirfd, const char *restrict pathname,
            struct stat *restrict statbuf, int flags);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| pathname | Target path (stat, lstat, fstatat); "" only with AT_EMPTY_PATH, in which case dirfd is the target and may be any file type, typically an O_PATH fd. |
| statbuf | Receives struct stat (field list in Purpose). |
| fd (fstat) | Open descriptor; the file itself is stat'ed without any path traversal. |
| dirfd (fstatat) | openat() model: AT_FDCWD for cwd-relative, else a directory fd; absolute pathname ignores it. |
| flags (fstatat) | 0 or OR of AT_EMPTY_PATH (2.6.39), AT_NO_AUTOMOUNT (2.6.38; stat/lstat behave as if it were set), AT_SYMLINK_NOFOLLOW (fstatat becomes lstat-like). |

## Return value and errors

0 on success; on error -1 and errno: EACCES (search permission denied on a path prefix), EBADF (fstat: fd not valid; fstatat: relative pathname with bad dirfd), EFAULT (bad statbuf/pathname address), EINVAL (fstatat: invalid flag), ELOOP, ENAMETOOLONG, ENOENT (missing component or dangling symlink; empty pathname without AT_EMPTY_PATH), ENOMEM, ENOTDIR (path prefix component; fstatat: non-directory dirfd with relative pathname), EOVERFLOW (size, inode number, or block count does not fit the 32-bit off_t/ino_t/blkcnt_t -- the classic case is a >2 GiB file stat'ed by a 32-bit program compiled without -D_FILE_OFFSET_BITS=64).

## Flags and constants

AT_* flags for fstatat are tabled under Arguments and behavior; values live in /usr/include/linux/fcntl.h (AT_SYMLINK_NOFOLLOW 0x100, AT_EMPTY_PATH 0x1000) and are shared with the other *at() calls. statx() (statx.md) is the mask-driven superset with creation time, mount IDs, and atomic-write limits.

## Security and notes

- No permission on the target file is needed; only search permission on the path prefix directories (man2/stat.2).
- TOCTOU discipline: stat() followed by open() races with renames and symlink swaps; prefer fstat() on the descriptor actually used, and openat()-relative traversal for path component isolation.
- st_blocks/st_blksize interpretations vary across systems and even across NFS mounts (man2/stat.2 CONFORMING TO).
- Fields may come from different moments under concurrent modification (man2/stat.2 Note) -- a stat() can report the old st_mode with the new st_uid.
- lstat() on a symlink: POSIX.1-2008 requires all fields except the mode bits to be valid; POSIX.1-2001 only required st_size and the file type.
- AT_EMPTY_PATH + O_PATH dirfd is the no-permission stat idiom noted on open.md (O_PATH section).

## References

- man2/stat.2 in the cached man-pages tree (dated 2021-08-27); .so aliases fstat.2, lstat.2, fstatat.2 (and newfstatat.2 via fstatat.2).
- Constants: /usr/include/linux/fcntl.h (AT_*); struct stat from glibc <sys/stat.h>.
- [Syscalls ledger](../ledger.md) rows SC-stat, SC-fstat, SC-lstat, SC-stat64, SC-fstat64, SC-lstat64, SC-newfstatat, SC-fstatat64; siblings [statx](statx.md), [open](open.md), [lseek](lseek.md); [domain hub](overview.md).
