# fspick(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 433 / i386 433 / arm64-generic 433 / arm32 433 |
| Since (kernel) | 5.2 (man HISTORY; hub) |
| Man page | not in local man2 cache; fetched from man7.org -> `source-cache/fetched/fspick.2.html` / `.txt` (man-pages 6.19) |
| glibc wrapper | Yes, since glibc 2.36 (man HISTORY; glibc NEWS); declared in `<sys/mount.h>` (installed glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-fspick |

## Purpose

`fspick()` creates a filesystem configuration context for the filesystem
instance already mounted at `path` and puts it into reconfiguration mode -- the
fd-based counterpart of `mount(8) -o remount`. The resulting fd is fed to
[fsconfig(2)](fsconfig.md) to stage parameter changes, which are applied with
`FSCONFIG_CMD_RECONFIGURE`. Unlike `MS_REMOUNT` on [mount(2)](mount.md), the
context starts as a copy of the extant parameters, so a reconfigure only
applies parameters explicitly changed with fsconfig; mount(2) remount clears
whatever is not re-specified.

## Synopsis

    #include <fcntl.h>   /* AT_* constants */
    #include <sys/mount.h>
    int fspick(int dirfd, const char *path, unsigned int flags);

## Arguments and behavior

| Argument | Meaning |
|---|---|
| `dirfd` / `path` | `*at()` resolution: absolute path ignores `dirfd`; `AT_FDCWD`; empty path with `FSPICK_EMPTY_PATH` operates on `dirfd` directly (any file type) |
| `flags` | `FSPICK_*` bits (table below) |

The returned fd also supports the diagnostic `read(2)` message channel
described in [fsopen.md](fsopen.md) (prefixes `e` / `w` / `i`, `ENODATA` when
empty), with an independent queue per context.

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `FSPICK_CLOEXEC` | 0x00000001 | Set `FD_CLOEXEC` on the new descriptor |
| `FSPICK_SYMLINK_NOFOLLOW` | 0x00000002 | Do not follow a trailing symlink; pick the filesystem the link itself resides on |
| `FSPICK_NO_AUTOMOUNT` | 0x00000004 | Do not trigger the terminal automount point |
| `FSPICK_EMPTY_PATH` | 0x00000008 | Empty path operates on `dirfd` |

(Values from `include/uapi/linux/mount.h`.)

## Return value and errors

Returns a new file descriptor on success, -1 on error with `errno` set.
Errors per the man page: `EPERM` (missing `CAP_SYS_ADMIN`), `EBADF` (relative
path with invalid `dirfd`), `EFAULT`, `EINVAL` (invalid flag), `EACCES`
(search permission denied in path prefix), `ELOOP`, `ENAMETOOLONG`, `ENOENT`
(missing component; empty path without `FSPICK_EMPTY_PATH`), `ENOTDIR`,
`EMFILE`, `ENFILE`, `ENOMEM`.

## Security and notes

The calling process must have `CAP_SYS_ADMIN` to create the configuration
context (man page); applying the changes with `FSCONFIG_CMD_RECONFIGURE` again
requires `CAP_SYS_ADMIN` (see [fsconfig.md](fsconfig.md)). Man page example
equivalences: `fspick(AT_FDCWD, "/tmp", FSPICK_CLOEXEC)` + set `ro` +
`FSCONFIG_CMD_RECONFIGURE` is "roughly equivalent" to
`mount(NULL, "/tmp", NULL, MS_REMOUNT | MS_RDONLY, NULL)` with the caveat that
mount(2) would also reset parameters such as `MS_DIRSYNC` / `MS_SYNCHRONOUS`.
Interaction with the reconfigure path of fsmount-created contexts is described
in [fsmount.md](fsmount.md).

## References

- Fetched man page: `source-cache/fetched/fspick.2.txt` (from
  https://man7.org/linux/man-pages/man2/fspick.2.html, man-pages 6.19)
- Constants: kernel UAPI `include/uapi/linux/mount.h`
  (`source-cache/fetched/master-include-uapi-linux-mount.h`)
- glibc NEWS "Version 2.36" (`source-cache/glibc-sparse/NEWS`)
