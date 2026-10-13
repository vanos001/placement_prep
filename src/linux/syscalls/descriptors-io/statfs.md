# statfs(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | statfs 137 / 99 / 43 / 99; fstatfs 138 / 100 / 44 / 100; statfs64 - / 268 / - / 266; fstatfs64 - / 269 / - / 267 (per-call table below) |
| Since (kernel) | statfs/fstatfs 1.0; statfs64/fstatfs64 2.6 (man NOTES; hub agrees) |
| Man page | man2/statfs.2 (fstatfs.2 is a .so alias of it; local cache, dated 2021-03-22) |
| glibc wrapper | Declared in <sys/statfs.h> (or <sys/vfs.h>, which includes it); glibc wrappers transparently handle the 64-bit variants |
| Aliases covered | fstatfs, statfs64, fstatfs64 |
| Ledger ID | SC-statfs, SC-fstatfs, SC-statfs64, SC-fstatfs64 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| statfs | 137 | 99 | 43 | 99 | 1.0 |
| fstatfs | 138 | 100 | 44 | 100 | 1.0 |
| statfs64 | - | 268 | - | 266 | 2.6 |
| fstatfs64 | - | 269 | - | 267 | 2.6 |

## Purpose

statfs() returns information about the filesystem containing path; fstatfs() does the same for the open file referred to by fd. The buffer is a struct statfs (defined approximately in the man page): f_type (filesystem magic), f_bsize (optimal transfer block size), f_blocks/f_bfree/f_bavail (total/free/free-to-unprivileged blocks), f_files/f_ffree (inodes), f_fsid (filesystem ID), f_namelen (maximum filename length), f_frsize (fragment size, since 2.6), and f_flags (mount flags, since 2.6.36). Fields a filesystem does not define are 0.

## Synopsis

```c
#include <sys/statfs.h>
int statfs(const char *path, struct statfs *buf);
int fstatfs(int fd, struct statfs *buf);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| path / fd | Filesystem to query, by path or by open fd. |
| buf | struct statfs to fill; the 64-bit twins use struct statfs64 with widened fields. |

f_type takes *_SUPER_MAGIC constants (about 80 listed in the man page; most live in /usr/include/linux/magic.h, for example EXT4_SUPER_MAGIC 0xef53, TMPFS_MAGIC 0x01021994, BTRFS_SUPER_MAGIC 0x9123683e, PROC_SUPER_MAGIC 0x9fa0).

## Return value and errors

Returns 0 on success; -1 with errno: EACCES, EBADF (fstatfs), EFAULT, EINTR, EIO, ELOOP, ENAMETOOLONG, ENOENT, ENOMEM, ENOSYS (filesystem does not support the call), ENOTDIR, EOVERFLOW (a value does not fit the returned struct). From 2.6.38 to 3.1 fstatfs() wrongly failed with ENOSYS on pipe fds.

## Flags and constants

f_flags is a mask of mount flags: ST_MANDLOCK, ST_NOATIME, ST_NODEV, ST_NODIRATIME, ST_NOEXEC, ST_NOSUID, ST_RDONLY, ST_RELATIME, ST_SYNCHRONOUS, and ST_NOSYMFOLLOW (since 5.10). Note ST_MANDLOCK (mandatory locking permitted) has been moot since the feature's removal pinned to v5.15 (worklog 1-c fcntl.md note). The kernel's ST_* values match the MS_* mount flags in <linux/mount.h> only for the low bits; glibc defines ST_* in <sys/mount.h>/<sys/statfs.h>.

## Security and notes

- LSB deprecates statfs()/fstatfs() in favor of statvfs(3)/fstatvfs(3), the POSIX API.
- __fsword_t is a glibc-internal type; unsigned int suffices for portability.
- f_fsid's content is deliberately unspecified ("Nobody knows what f_fsid is supposed to contain"); some systems restrict it to the superuser because it feeds NFS filehandles.
- The 64-bit twins exist because the original calls predate large files; glibc hides them.

## References

- man2/statfs.2 in the cached man-pages tree; .so alias fstatfs.2.
- [Syscalls ledger](../ledger.md) rows SC-statfs, SC-fstatfs, SC-statfs64, SC-fstatfs64.
- Siblings: [stat](stat.md), [truncate](truncate.md) (the *64 twin pattern).
- [Domain hub](overview.md) for status and sibling pages.
