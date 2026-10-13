# open_by_handle_at(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | name_to_handle_at: x64 303 / i386 341 / arm64-generic 264 / arm32 370; open_by_handle_at: x64 304 / i386 342 / arm64-generic 265 / arm32 371 |
| Since (kernel) | 2.6.39 for both (man VERSIONS; glibc 2.14); `AT_HANDLE_FID` 6.5 (worklog 1-d fetched page) |
| Man page | man2/open_by_handle_at.2 covers both (cached, 2021-08-27); `name_to_handle_at.2` is a roff `.so` alias |
| glibc wrapper | Yes for both; `<fcntl.h>`, needs `_GNU_SOURCE` (glibc 2.14) |
| Aliases covered | `name_to_handle_at` (SC-name_to_handle_at) |
| Ledger ID | SC-open_by_handle_at |

## Purpose

`name_to_handle_at()` returns an opaque file handle plus a mount ID for a
path; `open_by_handle_at()` reopens the file from that handle using a
descriptor into the same filesystem. The pair splits `openat()` into
export/reopen halves for userspace NFS servers and backup tooling
(researched BRIEF per the ledger).

## Synopsis

    #define _GNU_SOURCE
    #include <fcntl.h>
    int name_to_handle_at(int dirfd, const char *pathname,
                          struct file_handle *handle, int *mount_id, int flags);
    int open_by_handle_at(int mount_fd, struct file_handle *handle, int flags);

    struct file_handle {
        unsigned int  handle_bytes;  /* in: capacity, out: required/used */
        int           handle_type;
        unsigned char f_handle[];
    };

## Arguments and behavior

Set `handle_bytes` to the `f_handle` capacity (`MAX_HANDLE_SZ` 128 in the
installed header, not a guaranteed limit); a zero-sized call fails
`EOVERFLOW` and reports the required size, while `EOVERFLOW` with unchanged
`handle_bytes` means the filesystem offers no handle. Flags for
`name_to_handle_at()`: `AT_EMPTY_PATH`, `AT_SYMLINK_FOLLOW`.
`open_by_handle_at()` resolves the handle against `mount_fd` (`AT_FDCWD`
allowed); symlink handles need `O_PATH`. `AT_HANDLE_FID` (6.5) asks for an
identity-comparison-only handle that need not be reopenable (header
comment).

## Return value and errors

0 / new fd on success; -1 on error: `EOVERFLOW` (size negotiation),
`EINVAL` (handle_bytes over `MAX_HANDLE_SZ` or zero), `ENOENT`/`ENOTDIR`
(dirfd rules), `EOPNOTSUPP` (no handle decoding support), `EBADF`, `EFAULT`,
`ELOOP` (symlink without `O_PATH`), `EPERM` (`open_by_handle_at()` needs
`CAP_DAC_READ_SEARCH`), `ESTALE` (handle no longer valid, e.g. deleted file).

## Flags and constants

| Constant | Value | Meaning | Since |
|---|---|---|---|
| `AT_HANDLE_FID` | 0x200 (`AT_REMOVEDIR` value) | Handle for identity comparison, not reopen | 6.5 |
| `AT_SYMLINK_FOLLOW` | 0x400 | Dereference a symlinked pathname | header |
| `AT_EMPTY_PATH` | 0x1000 | Operate on `dirfd` itself | header |

## Security and notes

`CAP_DAC_READ_SEARCH` is a path-permission bypass, which is why the reopen
half is capability-gated; the cached page states only the capability name,
not its user-namespace scoping (worklog 1-d uncertainty). Filesystem
support is optional. See also [fanotify_init.md](fanotify_init.md),
[statmount.md](statmount.md), [open_tree.md](open_tree.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/open_by_handle_at.2`
  (`.so` alias `name_to_handle_at.2`)
- Online: https://man7.org/linux/man-pages/man2/open_by_handle_at.2.html
- `AT_HANDLE_FID`: worklog Task 1-d fetched open_by_handle_at.2 (6.5);
  installed `bits/fcntl-linux.h` / `linux/fcntl.h` (value 0x200)
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (303, 304)
