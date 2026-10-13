# openat2(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 437 / 437 / 437 / 437 (cached kernel tables; hub agrees) |
| Since (kernel) | 5.6 (man VERSIONS) |
| Man page | man2/openat2.2 (local cache, dated 2021-03-22); struct open_how cross-checked against kernel include/uapi/linux/openat2.h (master, fetched this session) |
| glibc wrapper | None: glibc provides no wrapper, necessitating syscall(2) (man page) |
| Aliases covered | none |
| Ledger ID | SC-openat2 |

## Purpose

openat2() is an extension of openat(2) and a superset of it. Instead of a flags int it takes an extensible struct open_how, which carries the O_* flags, the mode, and a resolve mask that restricts how every component of the pathname is resolved. The use case is letting trusted programs open untrusted paths safely: absolute symlinks, ".." escapes, magic links (/proc/[pid]/fd/*), and mount-point crossings can each be forbidden. Unlike openat(2), which ignores unknown flag bits, openat2() rejects unknown or conflicting flags and modes with EINVAL.

## Synopsis

```c
#include <linux/openat2.h>      /* struct open_how, RESOLVE_* */
#include <fcntl.h>              /* O_* constants */
int openat2(int dirfd, const char *pathname,
            struct open_how *how, size_t size);
```

## Arguments and behavior

struct open_how (kernel include/uapi/linux/openat2.h) has three __u64 fields:

| Field | Contents |
|---|---|
| flags | The O_* flags of openat(2); unknown or conflicting bits fail EINVAL. |
| mode | Permission bits for O_CREAT/O_TMPFILE; bits outside 07777 fail, and nonzero mode without O_CREAT or O_TMPFILE fails. |
| resolve | RESOLVE_* mask; unknown bits fail. The structure must be zero-filled; size is an implicit version number. |

RESOLVE_* flags (values from include/uapi/linux/openat2.h):

| Flag | Value | Meaning |
|---|---|---|
| RESOLVE_NO_XDEV | 0x01 | Fail EXDEV if resolution crosses a mount point (including bind mounts) |
| RESOLVE_NO_MAGICLINKS | 0x02 | Fail ELOOP on procfs-style magic links |
| RESOLVE_NO_SYMLINKS | 0x04 | Fail ELOOP on any symlink component; implies NO_MAGICLINKS |
| RESOLVE_BENEATH | 0x08 | Reject resolution escaping dirfd (absolute paths, ".." tricks) |
| RESOLVE_IN_ROOT | 0x10 | Treat dirfd as the root while resolving (per-open chroot(2) analog) |
| RESOLVE_CACHED | 0x20 | Fail EAGAIN unless the lookup can be served from cache |

## Return value and errors

Returns a new fd on success; -1 with errno: all openat(2) errors plus E2BIG (unsupported extension, nonzero size mismatch), EAGAIN (IN_ROOT/BENEATH could not rule out a ".." escape, or RESOLVE_CACHED would need I/O), EINVAL, ELOOP, EXDEV (escape detected, or NO_XDEV crossing).

## Flags and constants

The master UAPI header adds OPENAT2_REGULAR (1 << 32) in how.flags ("only open regular files"), not present in the 2021 man page; since-version unverified here, kernel-source provenance noted.

## Security and notes

- Zero-fill struct open_how (designated initializers or memset) so future fields stay no-ops; an all-nonzero size probe can discover kernel support via E2BIG.
- BENEATH/IN_ROOT currently also disable magic links, but the man page says this may change: pass RESOLVE_NO_MAGICLINKS explicitly.
- With O_PATH | O_NOFOLLOW the call may return an fd to the magic link/symlink itself instead of failing.

## References

- man2/openat2.2 in the cached man-pages tree (dated 2021-03-22).
- Kernel headers fetched this session: include/uapi/linux/openat2.h, fs/open.c (source-cache/fetched/master-uapi-openat2.h, master-fs-open.c).
- [Syscalls ledger](../ledger.md) row SC-openat2; sibling [open](open.md) documents the O_* flags.
