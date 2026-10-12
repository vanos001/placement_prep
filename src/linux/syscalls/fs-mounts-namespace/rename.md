# rename(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | rename: x64 82 / i386 38 / arm64-generic none / arm32 38; renameat: x64 264 / i386 302 / arm64-generic none / arm32 329; renameat2: x64 316 / i386 353 / arm64-generic 276 / arm32 382 |
| Since (kernel) | rename 1.0 (POSIX API, 4.3BSD lineage); renameat 2.6.16; renameat2 3.15 (man VERSIONS) |
| Man page | man2/rename.2 covers all three (local cache, dated 2021-08-27); renameat.2 / renameat2.2 are roff `.so` aliases |
| glibc wrapper | Yes; `rename()` / `renameat()` in `<stdio.h>` (renameat glibc 2.4, `_POSIX_C_SOURCE >= 200809L` since 2.10); `renameat2()` glibc 2.28 under `_GNU_SOURCE` |
| Aliases covered | `renameat` (SC-renameat), `renameat2` (SC-renameat2) -- RENAME_* flags documented here per task spec |
| Ledger ID | SC-rename |

## Purpose

`rename()` changes the name or location of a file, atomically replacing
`newpath` if it exists: another process never observes `newpath` missing,
though a window can exist where both names refer to the file. Hard links and
open file descriptors to `oldpath` are unaffected. `renameat()` adds two
dirfd-relative path resolutions; `renameat2()` adds a `flags` word, and a
zero-flags `renameat2()` equals `renameat()`. The asm-generic table has only
`renameat2` (276); the plain and `renameat` numbers are absent on arm64-generic
(hub / worklog 1-d).

## Synopsis

    #include <stdio.h>
    int rename(const char *oldpath, const char *newpath);

    #include <fcntl.h>      /* AT_* constants */
    #include <stdio.h>
    int renameat(int olddirfd, const char *oldpath,
                 int newdirfd, const char *newpath);
    int renameat2(int olddirfd, const char *oldpath,
                  int newdirfd, const char *newpath, unsigned int flags);

## Arguments and behavior

`renameat()` applies the `*at()` convention to both paths (absolute paths
ignore the dirfd; `AT_FDCWD`; relative paths resolve against the dirfd).
Renaming a directory requires `newpath` to be nonexistent or an empty
directory; renaming onto an existing directory of the wrong type fails with
`EISDIR`. If `oldpath` and `newpath` are hard links to the same file, the call
succeeds without doing anything. If the operation fails after `newpath`
existed, an instance of `newpath` is guaranteed to remain. Renaming across
filesystems fails with `EXDEV`; glibc's `renameat()` wrapper falls back to
`rename()` via `/proc/self/fd` symlinks on kernels without renameat (Glibc
notes).

## Flags and constants (renameat2)

| Flag | Value | Since | Meaning |
|---|---|---|---|
| `RENAME_NOREPLACE` | 1<<0 | 3.15 | Fail with `EEXIST` instead of overwriting `newpath`; atomic create-if-absent. Incompatible with `RENAME_EXCHANGE`. Needs filesystem support: ext4 3.15; btrfs, tmpfs, cifs 3.17; xfs 4.0; many more (ext2, reiserfs, jfs, vfat, ...) 4.9 |
| `RENAME_EXCHANGE` | 1<<1 | 3.15 | Atomically exchange `oldpath` and `newpath`; both must exist and may be of different types (e.g. non-empty directory vs symlink) |
| `RENAME_WHITEOUT` | 1<<2 | 3.18 | Rename and leave a "whiteout" at the source atomically; meaningful for overlay/union layers; outside overlays it appears as a character device {0,0}; needs `CAP_MKNOD` like mknod; fs support: tmpfs 3.18, ext4 3.18, xfs 4.1, f2fs 4.2, btrfs 4.7, ubifs 4.9. Incompatible with `RENAME_EXCHANGE` |

## Return value and errors

Returns 0 on success, -1 on error with `errno` set. Errors per the man page:
`EACCES` (write permission on source/target directory or search permission in
a prefix), `EBUSY` (directory in use as cwd/root/mount point and the system
chooses to report it), `EDQUOT`, `EFAULT`, `EINVAL` (`newpath` is a path
prefix of `oldpath`), `EISDIR`, `ELOOP`, `EMLINK`, `ENAMETOOLONG`, `ENOENT`,
`ENOMEM`, `ENOSPC`, `ENOTDIR`, `ENOTEMPTY` / `EEXIST` (target a non-empty
directory), `EPERM` / `EACCES` (sticky-bit `S_ISVTX` rules failing
`CAP_FOWNER`; unsupported rename type), `EROFS`, `EXDEV`, and `EINVAL` /
`ENOSYS` / `EOPNOTSUPP` for unsupported or conflicting `renameat2` flags on
filesystems lacking support.

## Security and notes

Ordinary filesystem permissions govern the call; `RENAME_WHITEOUT` requires
`CAP_MKNOD`. The sticky-bit rules make `/tmp`-style directories safe for
renaming entries owned by other users. BUGS section: on NFS, a rename may have
taken effect server-side even when the call reports failure (retransmitted RPC
after a server crash). Watch-related filesystem events surface through inotify
-- see [inotify_init.md](inotify_init.md); mount-point interactions with the
mount API live in [mount.md](mount.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/rename.2`, `.so` aliases `renameat.2`, `renameat2.2`
- Online: https://man7.org/linux/man-pages/man2/rename.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (82, 264, 316),
  `syscall_generic.tbl` (276)
- Constants: `RENAME_*` in installed `<linux/fs.h>` / glibc `<stdio.h>` gates
