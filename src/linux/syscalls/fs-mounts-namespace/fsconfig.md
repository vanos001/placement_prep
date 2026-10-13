# fsconfig(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 431 / i386 431 / arm64-generic 431 / arm32 431 |
| Since (kernel) | 5.2 (man HISTORY); `FSCONFIG_CMD_CREATE_EXCL` since 6.6 |
| Man page | not in local man2 cache; fetched from man7.org -> `source-cache/fetched/fsconfig.2.html` / `.txt` (man-pages 6.19) |
| glibc wrapper | Yes, since glibc 2.36 (man HISTORY; glibc NEWS); declared in `<sys/mount.h>` (installed glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-fsconfig |

## Purpose

`fsconfig()` supplies parameters to and issues commands against the filesystem
configuration context referenced by `fd` (created by [fsopen(2)](fsopen.md) or
[fspick(2)](fspick.md)). It is the counterpart of the option strings that
[mount(2)](mount.md) and mount(8) parse: `FSCONFIG_SET_*` commands stage
parameters, `FSCONFIG_CMD_*` commands trigger the filesystem driver. Staged
parameters take effect only when a create or reconfigure command is issued.

## Synopsis

    #include <sys/mount.h>
    int fsconfig(int fd, unsigned int cmd, const char *key,
                 const void *value, int aux);

## Arguments and behavior

| Command (value) | Arguments required | Behavior |
|---|---|---|
| `FSCONFIG_SET_FLAG` (0) | `key`; `value` NULL, `aux` 0 | Set boolean flag parameter (e.g. `ro`, `acl`) |
| `FSCONFIG_SET_STRING` (1) | `key`, string `value`, `aux` 0 | Set string parameter (e.g. `source`, `uid`) |
| `FSCONFIG_SET_BINARY` (2) | `key`, blob `value`, `aux` = length | Set blob parameter |
| `FSCONFIG_SET_PATH` (3) | `key`, path `value`, `aux` = dirfd | Resolve path like `openat(2)` |
| `FSCONFIG_SET_PATH_EMPTY` (4) | `key`, path `value`, `aux` = dirfd | As SET_PATH, but empty string operates on `aux` directly (`AT_EMPTY_PATH`-style, any file type) |
| `FSCONFIG_SET_FD` (5) | `key`, `value` NULL, `aux` = fd | Set file parameter; `FSCONFIG_SET_STRING` with a base-10 fd string also works for compatibility |
| `FSCONFIG_CMD_CREATE` (6) | `key`/`value` NULL, `aux` 0 | Instantiate the filesystem; once per context; puts context in "awaiting-mount" mode; may silently reuse an extant superblock (ro/rw mismatch then `EBUSY`) |
| `FSCONFIG_CMD_CREATE_EXCL` (8) | same as CMD_CREATE | Since 6.6: never reuse an extant superblock; `EBUSY` if one matches |
| `FSCONFIG_CMD_RECONFIGURE` (7) | `key`/`value` NULL, `aux` 0 | Apply staged parameters to the extant instance (main use: `fspick(2)`); context stays reusable |

## Return value and errors

Returns 0 on success, -1 on error with `errno` set. Notable errors: `EPERM`
(`CMD_CREATE` / `CMD_CREATE_EXCL` / `CMD_RECONFIGURE` without `CAP_SYS_ADMIN`),
`EBADF` (bad `fd` or `aux`), `EBUSY` (wrong context state; reconfigure to
read-only with open writers; `CMD_CREATE_EXCL` colliding with an existing
superblock), `EINVAL` (bad key/value/aux combination for `cmd`; parameter type
mismatch), `EACCES` (unsearchable path component; create on read-only source
without `ro`; block device on `MS_NODEV` mount), `ENOENT`, `ENOTBLK`, `ENXIO`,
`ENOMEM`, `EOPNOTSUPP` (unknown command), `EFAULT`, `ELOOP`, `ENAMETOOLONG`.
The context is not invalidated by a failed command, so callers can probe
parameter support one parameter at a time; driver diagnostics arrive through the
`read(2)` message channel of [fsopen.md](fsopen.md).

## Security and notes

`CAP_SYS_ADMIN` is required for the three `CMD_*` commands (man page). Generic
parameters with unified behavior: `ro`/`rw`, `dirsync`, `sync`/`async`,
`lazytime`/`nolazytime`, `mand`/`nomand` (no-op since 5.15, mandatory locking
deprecated), `source` (string; settable once), plus LSM parameters. Caveat from
the man page: many drivers only accept `FSCONFIG_SET_STRING` (parameters must
stay string-parseable for `mount(2)` compatibility); notably the generic
`source` parameter cannot be set with `FSCONFIG_SET_PATH`.

## References

- Fetched man page: `source-cache/fetched/fsconfig.2.txt` (from
  https://man7.org/linux/man-pages/man2/fsconfig.2.html, man-pages 6.19)
- Constants: kernel UAPI `include/uapi/linux/mount.h` (`enum fsconfig_command`)
- Siblings: [fsopen.md](fsopen.md), [fsmount.md](fsmount.md),
  [fspick.md](fspick.md), [mount_setattr.md](mount_setattr.md)
