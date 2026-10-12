# utimensat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | utimensat: x64 280 / i386 320 / arm64-generic 88 / arm32 348; utimensat_time64: i386 412 / arm32 412 (arm64-generic/x64 none); futimesat: x64 261 / i386 299 / arm64-generic none / arm32 326; utime: x64 132 / i386 30 / arm64-generic none / arm32 none; utimes: x64 235 / i386 271 / arm64-generic none / arm32 269 |
| Since (kernel) | utimensat 2.6.22 (man VERSIONS; glibc 2.6); futimesat 2.6.16; utime 1.0; utimes 2.2 (ledger); utimensat_time64: time64 twin, ledger date "--" |
| Man page | man2/utimensat.2 covers utimensat/futimens (cached, 2021-08-27); man2/utime.2 covers utime/utimes (`utimes.2` is a roff `.so` alias); man2/futimesat.2 (cached, 2021-08-27) |
| glibc wrapper | `utimensat()` since glibc 2.6 (`_POSIX_C_SOURCE >= 200809L`); `futimens()` since glibc 2.6 (library function over the utimensat syscall); `utime()` / `utimes()` / `futimesat()` in `<sys/time.h>` / `<utime.h>` |
| Aliases covered | `utime` (SC-utime), `utimes` (SC-utimes), `futimesat` (SC-futimesat), `utimensat_time64` (SC-utimensat_time64), plus the libc-only `futimens` |
| Ledger ID | SC-utimensat |

## Purpose

`utimensat()` sets a file's atime and mtime with nanosecond precision --
the modern replacement for the second-resolution `utime()` and the
microsecond-resolution `utimes()`, and the obsoleting call for `futimesat()`.
`futimens()` (libc only) does the same through an open descriptor.

## Synopsis

    #include <fcntl.h>      /* AT_* constants */
    #include <sys/stat.h>
    int utimensat(int dirfd, const char *pathname,
                  const struct timespec times[2], int flags);
    int futimens(int fd, const struct timespec times[2]);

    #include <utime.h>      /* utime(); utimes() in <sys/time.h> */
    int utime(const char *pathname, const struct utimbuf *times);
    int utimes(const char *pathname, const struct timeval times[2]);

## Arguments and behavior

`times[0]` is the new atime, `times[1]` the new mtime; each is seconds plus
nanoseconds since the Epoch, truncated down to the filesystem's resolution.
Special `tv_nsec` values: `UTIME_NOW` (set to the current time) and
`UTIME_OMIT` (leave unchanged); `tv_sec` is ignored in both cases. `times ==
NULL` sets both timestamps to now. `utimensat()` follows the `*at()`
convention; `flags` is 0 or `AT_SYMLINK_NOFOLLOW` (act on the link itself).
Nonstandard kernel feature: with `pathname == NULL`, `utimensat()` operates
on `dirfd` directly -- that is how the library implements `futimens()`, and
glibc's own `utimensat()` wrapper rejects NULL with `EINVAL`. `utime()` /
`utimes()` take a `struct utimbuf` / two `struct timeval`s; NULL sets both
to the current time. `futimesat()` is the 2.6.16 dirfd ancestor of
`utimensat()` (NULL `pathname` means "use dirfd"), obsoleted by it.

## Return value and errors

Returns 0 on success, -1 on error: `EACCES` (setting both to now without
being owner, write-access, or privileged via `CAP_FOWNER` /
`CAP_DAC_OVERRIDE`), `EBADF`, `EFAULT`, `EINVAL` (bad `flags`; bad `tv_nsec`
outside 0..999999999 and not `UTIME_NOW`/`UTIME_OMIT`; NULL `pathname`
without `AT_FDCWD` when `AT_SYMLINK_NOFOLLOW`), `ELOOP`, `ENAMETOOLONG`,
`ENOENT`, `ENOTDIR`, `EPERM` (changing to a non-current time without
ownership/`CAP_FOWNER`; append-only or immutable files), `EROFS`, `ESRCH`
(search denied on a prefix).

## Flags and constants

| Constant | Meaning | Since |
|---|---|---|
| `UTIME_NOW` | Special `tv_nsec`: set timestamp to current time | 2.6.22 |
| `UTIME_OMIT` | Special `tv_nsec`: leave timestamp unchanged | 2.6.22 |
| `AT_SYMLINK_NOFOLLOW` | 0x100: operate on the symlink itself | header |
| `AT_FDCWD` | -100: relative paths resolve against the cwd | header |

## Security and notes

Setting timestamps to a value other than the current time requires ownership
or `CAP_FOWNER`; setting both to now requires only write access (this is why
`touch(1)` works on files you can write). With both `tv_nsec` fields set to
`UTIME_OMIT`, no ownership or permission checks happen at all and the call
succeeds even for a nonexistent path. Immutable files cannot have
timestamps changed; append-only files only to the current time. Before
2.6.26, `tv_sec` had to be 0 alongside `UTIME_NOW`/`UTIME_OMIT`, and the
`times == NULL` / double-`UTIME_NOW` cases were not permission-equivalent
(man BUGS). The i386/arm32 412 entries are the time64 twin
(`utimensat_time64`) of the 32-bit-time_t ABI era. The read side of file
timestamps is `stat(2)` / `statx(2)`; ownership changes are on
[chown.md](chown.md).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/utimensat.2`, `utime.2`
  (`.so` alias `utimes.2`), `futimesat.2`
- Online: https://man7.org/linux/man-pages/man2/utimensat.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (132, 235, 261, 280),
  `syscall_32.tbl` (30, 271, 299, 320, 412)
- Ledger rows SC-utime / SC-utimes / SC-futimesat / SC-utimensat_time64 for dates
