# mount(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 165 / i386 21 / arm64-generic 40 / arm32 21 |
| Since (kernel) | 1.0 |
| Man page | man2/mount.2 (cached man-pages-sparse, dated 2021-08-27) |
| glibc wrapper | Yes; declared in `<sys/mount.h>` (installed glibc 2.41) |
| Aliases covered | none; unmount side: `umount` / `umount2` pointer -> [umount2.md](umount2.md) |
| Ledger ID | SC-mount |

## Purpose

`mount()` is the legacy, string-based filesystem mounting interface. It attaches the
filesystem named by `source` (a device path, a directory or file, or a dummy string)
to the location named by `target`. The call is one of five operations, chosen by
testing `mountflags` in this order: remount (`MS_REMOUNT`), bind mount (`MS_BIND`),
propagation change (`MS_SHARED` / `MS_PRIVATE` / `MS_SLAVE` / `MS_UNBINDABLE`),
move (`MS_MOVE`), and otherwise create a new mount. The fd-based successor suite
(`fsopen`, `fsconfig`, `fsmount`, `move_mount`, `open_tree`, `fspick`,
`mount_setattr`) has its own pages in this directory; see [fsopen.md](fsopen.md).

## Synopsis

    #include <sys/mount.h>
    int mount(const char *source, const char *target,
              const char *filesystemtype, unsigned long mountflags,
              const void *data);

## Arguments and behavior

| Argument | Meaning |
|---|---|
| `source` | Device, directory/file to bind, or dummy string (ignored by remount/bind/move/propagation ops) |
| `target` | Mount point; must be the original target for `MS_REMOUNT` |
| `filesystemtype` | Value from `/proc/filesystems` (e.g. `ext4`, `tmpfs`); ignored except for a new mount |
| `mountflags` | Operation selector plus `MS_*` modifier flags (table below) |
| `data` | Filesystem-specific option string (comma-separated); interpreted by each driver |

`filesystemtype` and `data` are ignored for bind, move, and propagation operations.
The magic number `MS_MGC_VAL` (0xc0ed0000) in the top 16 bits was required before
Linux 2.4 and is ignored since.

## Flags and constants

| Constant | Value | Meaning | Since (man mount.2 / `<sys/mount.h>`) |
|---|---|---|---|
| `MS_RDONLY` | 1 | Mount read-only | 1.0 |
| `MS_NOSUID` | 2 | Ignore suid/sgid bits and file capabilities | 1.0 |
| `MS_NODEV` | 4 | Disallow device special files | 1.0 |
| `MS_NOEXEC` | 8 | Disallow program execution | 1.0 |
| `MS_SYNCHRONOUS` | 16 | Writes are synchronous (was `MS_SYNC`, renamed 1.1.69) | 1.0 |
| `MS_REMOUNT` | 32 | Alter flags of an existing mount | 1.0 |
| `MS_MANDLOCK` | 64 | Permit mandatory locking; since 4.5 needs `CAP_SYS_ADMIN` + `CONFIG_MANDATORY_FILE_LOCKING`; deprecated (no-op `mand` since 5.15 per fsconfig.2) | 1.0 |
| `MS_DIRSYNC` | 128 | Directory changes synchronous | 2.5.19 |
| `MS_NOSYMFOLLOW` | 256 | Do not follow symbolic links | 5.10 |
| `MS_NOATIME` | 1024 | Do not update access times | 1.0 |
| `MS_NODIRATIME` | 2048 | Do not update directory access times | 1.0 |
| `MS_BIND` | 4096 | Create bind mount | 2.4 |
| `MS_MOVE` | 8192 | Move subtree atomically | 2.4.18 |
| `MS_REC` | 16384 | Recursive bind / recursive propagation change | 2.4.11 |
| `MS_SILENT` | 32768 | Suppress kernel log warnings (supersedes `MS_VERBOSE`, 2.4.12) | 2.6.17 |
| `MS_POSIXACL` | 1<<16 | VFS does not apply the umask | header |
| `MS_UNBINDABLE` | 1<<17 | Change to unbindable | 2.6.15 |
| `MS_PRIVATE` | 1<<18 | Change to private | 2.6.15 |
| `MS_SLAVE` | 1<<19 | Change to slave | 2.6.15 |
| `MS_SHARED` | 1<<20 | Change to shared | 2.6.15 |
| `MS_RELATIME` | 1<<21 | Update atime relative to mtime/ctime | 2.6.20 |
| `MS_I_VERSION` | 1<<23 | Update inode i_version field | header |
| `MS_STRICTATIME` | 1<<24 | Always perform atime updates | 2.6.30 |
| `MS_LAZYTIME` | 1<<25 | Update on-disk [acm]times lazily | 4.0 |
| `MS_MGC_VAL` | 0xc0ed0000 | Magic flag (obsolete; ignored since 2.4) | pre-2.4 |

Per-mount-point flags since 2.4: `MS_NODEV`, `MS_NOEXEC`, `MS_NOSUID` (2.4),
`MS_NOATIME` / `MS_NODIRATIME` (2.6.16), `MS_RELATIME` (2.6.20); `MS_RDONLY`
per-mount since 2.6.16. Per-superblock: `MS_DIRSYNC`, `MS_LAZYTIME`, `MS_MANDLOCK`,
`MS_SILENT`, `MS_SYNCHRONOUS`. `MS_KERNMOUNT` (1<<22), `MS_ACTIVE` (1<<30) and
`MS_NOUSER` (1<<31) exist in the header but are kernel-internal. Remount can change
only the `MS_RMT_MASK` set (`MS_RDONLY`, `MS_SYNCHRONOUS`, `MS_MANDLOCK`,
`MS_I_VERSION`, `MS_LAZYTIME` plus the atime flags); `MS_DIRSYNC` and `MS_SILENT`
changes are silently ignored. Since 2.6.26, `MS_REMOUNT | MS_BIND` changes only the
per-mount flags. Since 3.17 a remount that names no atime flag preserves the
current atime mode.

Mount-lock note: the kernel marks mounts locked (kernel-internal `MNT_LOCK_*`
flags, not exposed in UAPI headers) when properties must not be altered across
user namespaces; a remount that would change locked flags fails with `EPERM`
and an unmount of a locked mount fails with `EINVAL` (man page pointers to
`mount_namespaces(7)`).

## Return value and errors

Returns 0 on success, -1 on error with `errno` set. Filesystem-independent errors
include `EPERM` (missing privilege or locked flag), `EBUSY` (stacking over an
existing mount of the same source/target; remount read-only with open writers),
`EINVAL` (invalid flag combination; move of a shared-parent mount; bind of an
unbindable mount; unprivileged-namespace bind without `MS_REC`), `ENODEV`
(unknown `filesystemtype`), `ENOTBLK` (source not a block device), `EROFS` or
`EACCES` (mounting a read-only filesystem without `MS_RDONLY`), `ELOOP`,
`ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `EFAULT`, `ENXIO`.

## Security and notes

Requires `CAP_SYS_ADMIN` for the mount namespace (owned user namespace rules per
`mount_namespaces(7)`); unprivileged mount namespaces (userns + `CLONE_NEWNS`)
allow restricted mounting, but bind mounts there require `MS_REC` to avoid
revealing submounts. Mount namespaces themselves date to 2.4.19. In containers,
prefer the fd-based API: [fsopen.md](fsopen.md), [fsconfig.md](fsconfig.md),
[fsmount.md](fsmount.md), [move_mount.md](move_mount.md), [open_tree.md](open_tree.md),
[fspick.md](fspick.md), [mount_setattr.md](mount_setattr.md). Unmounting is the
companion call, see [umount2.md](umount2.md); the hub also routes plain `umount`
from [overview.md](overview.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/mount.2`
- Online: https://man7.org/linux/man-pages/man2/mount.2.html
- Constants: `/usr/include/x86_64-linux-gnu/sys/mount.h`; kernel UAPI
  `include/uapi/linux/mount.h` (fetched: `source-cache/fetched/master-include-uapi-linux-mount.h`)
- Kernel implementation: `fs/namespace.c` (torvalds/linux master)
