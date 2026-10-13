# ioctl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 16 / 54 / 29 / 54 |
| Since (kernel) | 1.0 |
| Man page | man2/ioctl.2 |
| glibc wrapper | ioctl() declared in <sys/ioctl.h> as int ioctl(int fd, unsigned long request, ...); POSIX specifies the request parameter as int, glibc's prototype is the unsigned long form (man2/ioctl.2 comment); third argument is an untyped pointer, typed per request by user headers |
| Aliases covered | none |
| Ledger ID | SC-ioctl |

## Purpose

ioctl() is the catch-all for device and object operations that do not fit the read/write stream model: the fd selects an object, the request code selects an operation, and argp is an untyped pointer to the operation's in/out memory. There is no single standard: arguments, return values, and semantics vary by driver, and this page documents the dispatch model and the major request groups, not an exhaustive device list (per-request man pages listed under ioctl_* in man2 do that; man2/ioctl.2 SEE ALSO).

Kernel dispatch (verified against torvalds master fs/ioctl.c, fetched to source-cache/fetched/master-fs-ioctl.c; consistent with worklog 1-f / crossref XR-013 which documents the call as ioctl -> fs/ioctl dispatch -> driver unlocked_ioctl): SYSCALL_DEFINE3(ioctl) first runs the LSM security_file_ioctl() hook, then do_vfs_ioctl(), a VFS-wide switch that handles the generic commands below. If no generic command matches it returns -ENOIOCTLCMD and vfs_ioctl() hands the request to the file's driver method filp->f_op->unlocked_ioctl(); a driver with no method yields ENOTTY. Regular files get a small extra pre-dispatch layer (file_ioctl()) for the positional requests handled in the fs layer.

## Synopsis

```c
#include <sys/ioctl.h>
int ioctl(int fd, unsigned long request, ...);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd | Open file descriptor; the valid request set depends on what fd refers to. |
| request | 32-bit device-dependent command code (see encoding below). |
| argp | Untyped pointer (traditionally char *) to the request's argument memory; requests without an argument ignore it. |

Request encoding (man2/ioctl.2, macros in <asm/ioctl.h>): 2 direction bits (00 none, 01 write, 10 read, 11 read/write), 14 size bits (sizeof of the argument type), 8-bit type grouping a driver or purpose, 8-bit serial number. The size bits are explicitly unreliable -- buggy macros and legacy values are common -- and the encoding varies across architectures, so it must not be used to validate buffers. Old-style 16-bit constants (driver type byte + serial byte, e.g. TCGETS 0x00005401 with 0x54 = 'T' for the terminal driver) still exist alongside.

Major request groups (not exhaustive):

| Group | Examples | Handled where |
|---|---|---|
| VFS generic close/exec flags | FIOCLEX, FIONCLEX | do_vfs_ioctl(), kernel-wide |
| Nonblocking / async | FIONBIO, FIOASYNC | do_vfs_ioctl() (equivalents of fcntl F_SETFL bits) |
| Size and byte counts | FIOQSIZE, FIGETBSZ, FIONREAD | do_vfs_ioctl() (FIONREAD on regular files returns size - f_pos; otherwise falls through to the driver) |
| Filesystem freeze and mapping | FIFREEZE, FITHAW, FS_IOC_FIEMAP | do_vfs_ioctl() |
| Reflink and dedupe | FICLONE, FICLONERANGE, FIDEDUPERANGE | do_vfs_ioctl(); detailed on ioctl_ficlonerange(2)/ioctl_fideduperange(2) |
| Inode flags and xattrs | FS_IOC_GETFLAGS, FS_IOC_SETFLAGS, FS_IOC_FSGETXATTR, FS_IOC_FSSETXATTR | do_vfs_ioctl() (chattr-style flags) |
| Misc fs identity (master) | FS_IOC_GETFSUUID, FS_IOC_GETFSSYSFSPATH | do_vfs_ioctl() in the master tree, newer than the cached man page |
| Terminals | TCGETS/TCSETS, TIOCGWINSZ, ... | tty driver via ->unlocked_ioctl; documented on ioctl_tty(2) |
| Driver-specific | everything else | the fd's own ->unlocked_ioctl() |

## Return value and errors

Usually 0 on success; a few requests use the return value as an output parameter and return a nonnegative value. On error, -1 and errno: EBADF (bad fd), EFAULT (argp points outside the address space), EINVAL (request or argp invalid for the object), ENOTTY (fd is not associated with a character special device, or the request does not apply to the kind of object fd references). Driver methods return their own additional errno values.

## Flags and constants

No flag argument; request codes are constants. The _IO(type,nr) / _IOR / _IOW / _IOWR macros build request values from a type letter, serial number, and argument type (man2/ioctl.2). Generic command constants live in <asm-generic/ioctls.h>, <linux/fs.h>, and friends; their numeric values are architecture-dependent through the encoding, so pages here quote names, not numbers.

## Security and notes

- ENOTTY is the traditional wrong-error for "not a tty" checks and also the generic "request not supported by this object" answer; do not treat it as a terminal-only error.
- open() of a device can have side effects (carrier waits, resets); opening with O_NONBLOCK avoids blocking (man2/ioctl.2 NOTES).
- LSM note in the kernel source: new generic commands require compat-mode-compatible argument sizes and a heads-up to the LSM mailing list (master fs/ioctl.c comment).
- The historical BKL-holding .ioctl file operation and compat_sys_ioctl plumbing are outside the scope of the documented dispatch chain above; the cached man page and the master source only establish the ->unlocked_ioctl() path used here (source-limited, per crossref XR-013).

## References

- man2/ioctl.2 in the cached man-pages tree (dated 2021-03-22).
- Kernel dispatch: torvalds master fs/ioctl.c (fetched copy source-cache/fetched/master-fs-ioctl.c; SYSCALL_DEFINE3 -> do_vfs_ioctl -> vfs_ioctl -> f_op->unlocked_ioctl), cross-checked with crossref XR-013 in src/linux/crossref/ledger.md and worklog 1-f.
- [Syscalls ledger](../ledger.md) row SC-ioctl; siblings [fcntl](fcntl.md), [open](open.md); [domain hub](overview.md).
