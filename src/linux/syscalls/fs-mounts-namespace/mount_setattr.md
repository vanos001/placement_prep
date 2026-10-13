# mount_setattr(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 442 / i386 442 / arm64-generic 442 / arm32 442 |
| Since (kernel) | 5.12 (man VERSIONS; hub Since column shows "--", x64 table 442) |
| Man page | man2/mount_setattr.2 in local cache (dated 2021-08-27); newer online version at man7.org |
| glibc wrapper | Cached man page says "glibc provides no wrapper" (predates 2.36); glibc NEWS "Version 2.36" lists mount_setattr among the new Linux mount APIs; installed glibc 2.41 declares it in `<sys/mount.h>` |
| Aliases covered | none |
| Ledger ID | SC-mount_setattr |

## Purpose

`mount_setattr()` changes the properties of a mount or an entire mount tree in
one call: per-mount flags, the atime mode, the propagation type, and
ID-mapping. It is the attribute-setting leg of the fd-based suite
([fsmount.md](fsmount.md) and [open_tree.md](open_tree.md) produce the mount
fds it operates on) and supersedes `MS_REMOUNT` flag fiddling on
[mount(2)](mount.md).

## Synopsis

    #include <linux/fcntl.h>    /* AT_* constants */
    #include <linux/mount.h>    /* MOUNT_ATTR_* constants */
    #include <sys/syscall.h>
    #include <unistd.h>
    int syscall(SYS_mount_setattr, int dirfd, const char *pathname,
                unsigned int flags, struct mount_attr *attr, size_t size);

(struct mount_attr is also reachable via the glibc 2.36+ wrapper declared in
`<sys/mount.h>`; see the glibc wrapper field above for the source conflict.)

## Arguments and behavior

`pathname` resolution follows `*at()` rules: relative to `dirfd`, `AT_FDCWD`
for the working directory, or `AT_EMPTY_PATH` to operate on `dirfd` itself
(e.g. a detached mount fd). `size` should be `sizeof(struct mount_attr)`
(`MOUNT_ATTR_SIZE_VER0` = 32); the struct is extensible, so callers must
zero-fill it. The kernel first clears `attr_clr`, then sets `attr_set`; the
operation is idempotent for repeated identical calls.

    struct mount_attr {
        __u64 attr_set;     /* Mount properties to set */
        __u64 attr_clr;     /* Mount properties to clear */
        __u64 propagation;  /* Mount propagation type */
        __u64 userns_fd;    /* User namespace file descriptor */
    };

`propagation` is 0 (unchanged) or exactly one of `MS_PRIVATE`, `MS_SHARED`,
`MS_SLAVE`, `MS_UNBINDABLE` (from [mount.md](mount.md)).

## Flags and constants

`flags`: `AT_EMPTY_PATH`, `AT_RECURSIVE` (apply to the whole mount tree),
`AT_SYMLINK_NOFOLLOW`, `AT_NO_AUTOMOUNT`.

| `MOUNT_ATTR_*` | Value | attr_set effect | attr_clr effect |
|---|---|---|---|
| `MOUNT_ATTR_RDONLY` | 0x00000001 | Mount read-only | Remove read-only (fails `EBUSY` if files open for writing) |
| `MOUNT_ATTR_NOSUID` | 0x00000002 | Ignore suid/sgid bits and file capabilities | Remove the restriction |
| `MOUNT_ATTR_NODEV` | 0x00000004 | Disallow device special files | Remove the restriction |
| `MOUNT_ATTR_NOEXEC` | 0x00000008 | Disallow program execution | Remove the restriction |
| `MOUNT_ATTR__ATIME` | 0x00000070 | Mask for the atime enumeration (below) | Must be set wholly to change the atime mode |
| `MOUNT_ATTR_RELATIME` | 0x00000000 | atime relative to mtime/ctime (default) | - |
| `MOUNT_ATTR_NOATIME` | 0x00000010 | Never update atime | - |
| `MOUNT_ATTR_STRICTATIME` | 0x00000020 | Always update atime | - |
| `MOUNT_ATTR_NODIRATIME` | 0x00000080 | No atime updates for directories; combinable, implied by noatime | Remove the restriction |
| `MOUNT_ATTR_IDMAP` | 0x00100000 | ID-map the mount using the user namespace in `userns_fd` | Invalid (mapping cannot be changed) |
| `MOUNT_ATTR_NOSYMFOLLOW` | 0x00200000 | Do not follow symbolic links | Remove the restriction |

Atime values are an enumeration inside the `MOUNT_ATTR__ATIME` mask: switching
mode requires `MOUNT_ATTR__ATIME` in `attr_clr` (all mask bits, not partial)
and the new value in `attr_set`. ID-mapped mounts additionally require
`CAP_SYS_ADMIN` in the initial user namespace, the filesystem mounted in a
namespace owned by the initial user namespace, filesystem support (xfs, ext4,
FAT per the cached page), and a detached mount not yet visible in a namespace.

## Return value and errors

Returns 0 on success, -1 with `errno` set. Key errors: `EPERM` (missing
`CAP_SYS_ADMIN` in the initial user namespace; locked flags; initial user
namespace fd in `userns_fd`; re-mapping an ID-mapped mount), `EBUSY`
(read-only conversion with open writers), `EINVAL` (target not a mount point;
bad `attr_set` / `attr_clr` / `propagation` values; partial atime mask;
`userns_fd` not a user namespace or over `INT_MAX`; filesystem without
ID-mapped-mount support; mount outside the caller's namespace), `EBADF`,
`ENOENT`, `ENOMEM` / `ENOSPC` (peer group ID allocation for `MS_SHARED`).
Flag locking: attributes become locked when propagation crosses user namespaces
or when a new mount + user namespace pair is created (`CLONE_NEWUSER |
CLONE_NEWNS` in `clone(2)` / `unshare(2)`), preventing privilege escalation by
re-mounting read-only mounts as writable.

## Security and notes

The cached man page states the caller needs `CAP_SYS_ADMIN` in the initial user
namespace (its `EPERM` entry); quote it as the documented contract. The atime
and propagation fields reuse `MS_*`-adjacent semantics but are separate from
the `mount(2)` flag word. See [fsmount.md](fsmount.md) for the restriction that
`MOUNT_ATTR_IDMAP` cannot be passed through `fsmount()` `attr_flags`.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/mount_setattr.2`
- Online: https://man7.org/linux/man-pages/man2/mount_setattr.2.html
- Constants and struct: kernel UAPI `include/uapi/linux/mount.h`
  (`source-cache/fetched/master-include-uapi-linux-mount.h`); installed
  `/usr/include/linux/mount.h`
- glibc NEWS "Version 2.36" (`source-cache/glibc-sparse/NEWS`)
