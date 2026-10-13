# access(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | access 21 / 33 / - / 33; faccessat 269 / 307 / 48 / 334; faccessat2 439 / 439 / 439 / 439 (per-call table below) |
| Since (kernel) | access 1.0; faccessat 2.6.16 (glibc 2.4); faccessat2 5.8 |
| Man page | man2/access.2 (faccessat.2 and faccessat2.2 are .so aliases of it) |
| glibc wrapper | access declared in <unistd.h>; faccessat needs _POSIX_C_SOURCE >= 200809L (glibc 2.10+; _ATFILE_SOURCE before); no faccessat2 wrapper before glibc 2.33, which uses it where the kernel provides it |
| Aliases covered | faccessat, faccessat2 |
| Ledger ID | SC-access, SC-faccessat, SC-faccessat2 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| access | 21 | 33 | - | 33 | 1.0 |
| faccessat | 269 | 307 | 48 | 334 | 2.6.16 |
| faccessat2 | 439 | 439 | 439 | 439 | 5.8 |

Hub note: the hub's grouped row carries access's number set (21 / 33 / - / 33); the per-call values above are the ledger values.

## Purpose

access() checks whether the calling process can access the file named by pathname, dereferencing symbolic links. The check is made against the caller's real UID and GID rather than the effective IDs used for actual operations such as open(2), and it uses the permitted (not effective) capability set for root and an empty capability set for everyone else. It therefore answers "can the user who invoked this set-user-ID program access the file?", not "can I access the file?". faccessat() is the dirfd-relative form; faccessat2() (kernel 5.8) adds the flags argument the raw faccessat() slot never had.

## Synopsis

```c
#include <unistd.h>
int access(const char *pathname, int mode);

#include <fcntl.h>          /* AT_* constants */
int faccessat(int dirfd, const char *pathname, int mode, int flags);
int faccessat2(int dirfd, const char *pathname, int mode, int flags);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| pathname | File to check; symlinks are dereferenced (unless faccessat AT_SYMLINK_NOFOLLOW). |
| mode | F_OK (existence) or OR of R_OK, W_OK, X_OK; the call fails if any requested bit is denied. |
| dirfd | As in openat(2): relative paths resolve against dirfd or the cwd with AT_FDCWD; absolute paths ignore dirfd. |
| flags | AT_EACCESS (check with effective IDs) and AT_SYMLINK_NOFOLLOW; only honored by faccessat2(), never by the raw faccessat() slot. |

Mode constants (installed /usr/include/unistd.h): F_OK 0, X_OK 1, W_OK 2, R_OK 4. A privileged (real UID 0) caller passes X_OK for a regular file if any execute bit is set.

## Return value and errors

Returns 0 if all requested access types are granted; -1 with errno otherwise: EACCES, EBADF (faccessat: relative path, bad dirfd), EFAULT, EINVAL (bad mode or flag), EIO, ELOOP, ENAMETOOLONG, ENOENT, ENOMEM, ENOTDIR, EROFS (W_OK on a read-only filesystem), ETXTBSY (write access to a running executable).

## Flags and constants

AT_EACCESS and AT_SYMLINK_NOFOLLOW are implemented in glibc's faccessat() wrapper on top of the flagless kernel slot via fstatat(2), which ignores ACLs (man BUGS); glibc 2.33+ wrappers call faccessat2() directly when available.

## Security and notes

- The TOCTOU warning in the man page is explicit: check-then-open with access() is a security hole because the file can be swapped between the check and the use; prefer dropping privileges and opening, or just open() and check errno.
- access() checks only permission bits, not file type or contents; a writable directory does not mean the directory itself is writable as a file.
- NFSv2 with UID mapping and some FUSE mounts can give wrong results; the check runs on the client.
- MS_NOEXEC mounts have been honored since kernel 2.6.20.

## References

- man2/access.2 in the cached man-pages tree (dated 2021-08-27); .so aliases faccessat.2, faccessat2.2.
- Constants: /usr/include/unistd.h (F_OK/R_OK/W_OK/X_OK), /usr/include/linux/fcntl.h (AT_*).
- [Syscalls ledger](../ledger.md) rows SC-access, SC-faccessat, SC-faccessat2; kernel tables in source-cache/kernel.
- [Domain hub](overview.md) for status and sibling pages.
