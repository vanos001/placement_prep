# chmod(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | chmod: x64 90 / i386 15 / arm64-generic none / arm32 15; fchmod: x64 91 / i386 94 / arm64-generic 52 / arm32 94; fchmodat: x64 268 / i386 306 / arm64-generic 53 / arm32 333; fchmodat2: x64 452 / i386 452 / arm64-generic 452 / arm32 452 |
| Since (kernel) | chmod, fchmod 1.0; fchmodat 2.6.16 (man VERSIONS, glibc 2.4); fchmodat2 6.6 (worklog 1-d tag probe of asm-generic unistd.h: present v6.6, absent v6.5; ledger date "--") |
| Man page | man2/chmod.2 covers all three legacy names (local cache, dated 2021-08-27); fchmodat2 has no man page (man7.org 404 per worklog 1-d) |
| glibc wrapper | chmod / fchmod / fchmodat: yes, `<sys/stat.h>`; fchmodat2: no wrapper on installed glibc 2.41 (only `SYS_fchmodat2` in `<bits/syscall.h>`) |
| Aliases covered | `fchmod` (SC-fchmod), `fchmodat` (SC-fchmodat), `fchmodat2` (SC-fchmodat2) |
| Ledger ID | SC-chmod |

## Purpose

The chmod family changes a file's mode bits: the nine permission bits plus the
set-user-ID (`S_ISUID` 04000), set-group-ID (`S_ISGID` 02000) and sticky
(`S_ISVTX` 01000) bits. The members differ only in how the file is named:
`chmod()` dereferences a pathname, `fchmod()` operates on an open descriptor,
`fchmodat()` resolves a relative pathname against `dirfd`, and `fchmodat2()`
(kernel 6.6) supplies the kernel interface with the `flags` word that the
raw `fchmodat` system call lacks.

## Synopsis

    #include <sys/stat.h>
    int chmod(const char *pathname, mode_t mode);
    int fchmod(int fd, mode_t mode);

    #include <fcntl.h>      /* AT_* constants */
    #include <sys/stat.h>
    int fchmodat(int dirfd, const char *pathname, mode_t mode, int flags);

    int syscall(SYS_fchmodat2, int dirfd, const char *pathname,
                mode_t mode, unsigned int flags);   /* since 6.6 */

## Arguments and behavior

`mode` is ORed from the `S_*` bit table (`S_ISUID` 04000, `S_ISGID` 02000,
`S_ISVTX` 01000 and the nine `S_I[RWX]` permission bits 00400 through
00001; full list in `inode(7)`). `fchmodat()` follows
the `*at()` convention: relative `pathname` resolves against `dirfd`
(`AT_FDCWD` means the working directory; absolute paths ignore `dirfd`).
Its `flags` accepts 0 or `AT_SYMLINK_NOFOLLOW`, but the man page states this
flag is not currently implemented (fails `ENOTSUP`). An unprivileged caller
without `CAP_FSETID` that is not in the file's group gets the `S_ISGID` bit
silently cleared. On NFS, restricting permissions affects already open files
immediately.

## Return value and errors

Returns 0 on success, -1 on error with `errno` set: `EACCES` (search denied on
a path prefix), `EBADF` (bad `fd` or `dirfd`), `EFAULT`, `EINVAL` (bad
`fchmodat` flag), `EIO`, `ELOOP`, `ENAMETOOLONG`, `ENOENT`, `ENOMEM`,
`ENOTDIR`, `EPERM` (euid is not the owner and no `CAP_FOWNER`; file immutable
or append-only), `EROFS`, `ENOTSUP` (`AT_SYMLINK_NOFOLLOW` on `fchmodat`).

## Flags and constants

| Constant | Value | Meaning | Since |
|---|---|---|---|
| `AT_SYMLINK_NOFOLLOW` | 0x100 | Act on the symlink itself, not the target | header (`<fcntl.h>`) |
| `AT_FDCWD` | -100 | Interpret relative `pathname` against the cwd | header |

## Security and notes

Permission to change the mode requires the caller's effective UID to match the
file owner or `CAP_FOWNER`. On some filesystems only the superuser may set the
sticky bit; writing a file can clear the set-user-ID/set-group-ID bits
(depending on `CAP_FSETID`). fchmodat2 note (worklog 1-d, flagged uncertain
there): glibc 2.40-era releases route the POSIX `fchmodat()` wrapper to
`fchmodat2` on kernels that have it; the installed glibc 2.41 exposes no
`fchmodat2` symbol, so the claim rests on the worklog note, not on local
verification. Related ownership changes: [chown.md](chown.md); directory
creation: [mkdir.md](mkdir.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/chmod.2`
- Online: https://man7.org/linux/man-pages/man2/chmod.2.html
- fchmodat2 version pin: worklog Task 1-d (asm-generic `unistd.h` probes v6.5/v6.6);
  wrapper absence: `bits/syscall.h` on installed glibc 2.41
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (90, 91, 268, 452)
