# chown(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | chown: x64 92 / i386 182 / arm64-generic none / arm32 182; fchown: x64 93 / i386 95 / arm64-generic 55 / arm32 95; lchown: x64 94 / i386 16 / arm64-generic none / arm32 16; fchownat: x64 260 / i386 298 / arm64-generic 54 / arm32 325; chown32: i386 212 / arm32 212; fchown32: i386 207 / arm32 207; lchown32: i386 198 / arm32 198 |
| Since (kernel) | chown 2.2 (ledger; see history note below), fchown 1.0, lchown 1.0, fchownat 2.6.16 (glibc 2.4), the *32 32-bit-ID calls 2.4 |
| Man page | man2/chown.2 covers chown/fchown/lchown/fchownat (cached, 2021-08-27); `chown32.2` is a roff `.so` alias of chown.2 |
| glibc wrapper | Yes for all POSIX names (`<unistd.h>`); the *32 variants are raw i386/arm32 entry points with no glibc wrappers -- glibc's `chown()` handles the 16-vs-32-bit variation transparently |
| Aliases covered | `fchown` (SC-fchown), `lchown` (SC-lchown), `fchownat` (SC-fchownat), `chown32` (SC-chown32), `fchown32` (SC-fchown32), `lchown32` (SC-lchown32) |
| Ledger ID | SC-chown |

## Purpose

The chown family changes the owner and/or group of a file. `chown()`
dereferences a pathname, `lchown()` does not, `fchown()` takes an open
descriptor, and `fchownat()` combines dirfd-relative resolution with a
`flags` word. Passing -1 for `owner` or `group` leaves that ID unchanged.

## Synopsis

    #include <unistd.h>
    int chown(const char *pathname, uid_t owner, gid_t group);
    int fchown(int fd, uid_t owner, gid_t group);
    int lchown(const char *pathname, uid_t owner, gid_t group);

    #include <fcntl.h>      /* AT_* constants */
    #include <unistd.h>
    int fchownat(int dirfd, const char *pathname,
                 uid_t owner, gid_t group, int flags);

## Arguments and behavior

`fchownat()` follows the `*at()` convention; `flags` is 0 or a combination of
`AT_EMPTY_PATH` (since 2.6.39; empty `pathname` operates on `dirfd` itself,
`_GNU_SOURCE`) and `AT_SYMLINK_NOFOLLOW` (act like `lchown()`). Only a caller
with `CAP_CHOWN` may change the owner; the owner may change the group to any
group they belong to, and `CAP_CHOWN` may set any group. On NFS with UID
mapping the semantics are deliberately violated.

## Return value and errors

Returns 0 on success, -1 with `errno`: `EACCES`, `EBADF` (bad `fd`/`dirfd`),
`EFAULT`, `EINVAL` (bad `fchownat` flag), `EIO` (fchown low-level I/O error),
`ELOOP`, `ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `ENOTDIR`, `EPERM` (missing
privilege; immutable or append-only file), `EROFS`.

## Flags and constants

| Constant | Value | Meaning | Since |
|---|---|---|---|
| `AT_EMPTY_PATH` | 0x1000 | Operate on `dirfd` itself when `pathname` is empty | 2.6.39 |
| `AT_SYMLINK_NOFOLLOW` | 0x100 | Do not dereference `pathname` (like `lchown`) | header |
| `AT_FDCWD` | -100 | Relative paths resolve against the cwd | header |

## Security and notes

Changing the owner or group of an executable by an unprivileged user clears
`S_ISUID`/`S_ISGID`; since 2.2.13 root is treated like other users. Any owner
or group change clears file capability sets. Ownership of newly created files
follows the `grpid`/`nogrpid` mount options and the parent's set-group-ID bit
(man NOTES). Historical numbering (man "Historical details"): the original
calls supported only 16-bit UIDs; 2.4 added the *32 calls with 32-bit IDs,
which survive on i386/arm32 tables only. Before 2.1.81 `chown()` did not
follow symlinks; 2.1.86 moved the old no-follow semantics to the `lchown`
number. Ledger note: SC-chown32/SC-fchown32/SC-lchown32 sit in the process
section pointing at `process/chown.md` (worklog 1-a triage); this page covers
them. Mode changes: [chmod.md](chmod.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/chown.2` (`.so` alias `chown32.2`)
- Online: https://man7.org/linux/man-pages/man2/chown.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (92, 93, 94, 260),
  `syscall_32.tbl` (182, 95, 16, 298, 212, 207, 198), `syscall_arm.tbl`
- Ledger rows SC-chown32/fchown32/lchown32 for the *32 numbers
