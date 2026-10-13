# fsopen(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 430 / i386 430 / arm64-generic 430 / arm32 430 |
| Since (kernel) | 5.2 (man HISTORY; hub) |
| Man page | not in local man2 cache; fetched from man7.org -> `source-cache/fetched/fsopen.2.html` / `.txt` (man-pages 6.19) |
| glibc wrapper | Yes, since glibc 2.36 (man HISTORY; glibc NEWS); declared in `<sys/mount.h>` (installed glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-fsopen |

## Purpose

`fsopen()` opens the fd-based mount API: it creates a blank filesystem
configuration context for the filesystem named by `fsname`, places it in creation
mode, and returns a file descriptor for it. A configuration context is an
in-kernel pending transaction whose parameters are supplied with
[fsconfig(2)](fsconfig.md), instantiated with `FSCONFIG_CMD_CREATE`, and turned
into a detached mount object with [fsmount(2)](fsmount.md). The context
descriptor is also a diagnostic channel: `read(2)` returns queued driver messages
prefixed `e` (error), `w` (warning) or `i` (information); empty queue gives
`ENODATA`.

## Synopsis

    #include <sys/mount.h>
    int fsopen(const char *fsname, unsigned int flags);

## Arguments and behavior

| Argument | Meaning |
|---|---|
| `fsname` | Filesystem name; valid values listed in `/proc/filesystems` |
| `flags` | `FSOPEN_CLOEXEC` or 0 |

The workflow documented by the man page: fsconfig(2) to set parameters ->
fsconfig(2) `FSCONFIG_CMD_CREATE` -> fsmount(2) to get a mount object fd ->
[move_mount(2)](move_mount.md) to attach, or use the mount fd as an
`O_PATH`-like dirfd in `*at()` calls. Contexts move between modes (creation,
"awaiting-mount", reconfiguration via [fspick(2)](fspick.md), failed) and the
mode decides which operations are permitted.

## Return value and errors

Returns a new file descriptor on success, -1 on error with `errno` set.
Errors per the man page: `EFAULT` (NULL or bad `fsname`), `EINVAL` (unknown
flag), `EMFILE` / `ENFILE` (fd limits), `ENODEV` (filesystem unsupported),
`ENOMEM`, `EPERM` (missing `CAP_SYS_ADMIN`).

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `FSOPEN_CLOEXEC` | 0x00000001 | Set `FD_CLOEXEC` on the new descriptor |

(`include/uapi/linux/mount.h`; glibc `<sys/mount.h>` mirrors it.)

## Security and notes

The calling process must have `CAP_SYS_ADMIN` to create a filesystem
configuration context (man page); in practice this means `CAP_SYS_ADMIN` in the
user namespace that owns the caller's mount namespace story of
`mount_namespaces(7)`. The message queue has limited depth so messages can be
lost; a `read(2)` buffer too small for the next message returns `EMSGSIZE` and
silently consumes the message (documented BUGS section). Master UAPI
(`master-include-uapi-linux-mount.h`) defines no `FSOPEN_NAMESPACE` flag; the
namespace-creating variants live on fsmount / open_tree (post-v6.18 additions,
release unverified).

## References

- Fetched man page: `source-cache/fetched/fsopen.2.txt` (from
  https://man7.org/linux/man-pages/man2/fsopen.2.html, man-pages 6.19)
- Constants: kernel UAPI `include/uapi/linux/mount.h`
  (`source-cache/fetched/master-include-uapi-linux-mount.h`)
- glibc NEWS section "Version 2.36" (`source-cache/glibc-sparse/NEWS`)
- Siblings: [fsconfig.md](fsconfig.md), [fsmount.md](fsmount.md),
  [fspick.md](fspick.md), hub [overview.md](overview.md)
