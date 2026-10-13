# inotify_add_watch(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 254 / i386 292 / arm64-generic 27 / arm32 317 |
| Since (kernel) | 2.6.13 (inotify merged in 2.6.13; man VERSIONS) |
| Man page | man2/inotify_add_watch.2 (cached, 2021-03-22); mask bits documented in inotify.7 (fetched, man-pages 6.19) |
| glibc wrapper | Yes; `<sys/inotify.h>` (glibc 2.4) |
| Aliases covered | none |
| Ledger ID | SC-inotify_add_watch |

## Purpose

`inotify_add_watch()` adds a new watch, or modifies an existing watch, for the
file named by `pathname`, on the inotify instance referred to by `fd`. It
returns the watch descriptor (wd) that later `read(2)`s report inside
`inotify_event` structures. The companion calls are
[inotify_init.md](inotify_init.md) (create the instance) and
[inotify_rm_watch.md](inotify_rm_watch.md) (remove a watch).

## Synopsis

    #include <sys/inotify.h>
    int inotify_add_watch(int fd, const char *pathname, uint32_t mask);

## Arguments and behavior

`fd` must be an inotify instance descriptor; the caller needs read permission
on `pathname`. `mask` is an OR of `IN_*` event bits plus the control bits in
the table below. If the inode is already watched by this instance (possibly
via a different link), the existing wd is returned and the mask is updated
(ORed with `IN_MASK_ADD`, replaced otherwise). If the object was not watched,
a new wd is allocated. Event delivery and the queue tunables
(`/proc/sys/fs/inotify/max_user_watches`, `max_queued_events`,
`max_user_instances`) are covered in inotify.7 and on the
[inotify_init.md](inotify_init.md) page.

## Return value and errors

Returns the watch descriptor on success, -1 on error: `EACCES`, `EBADF`,
`EEXIST` (`IN_MASK_CREATE` on an already watched object), `EFAULT`, `EINVAL`
(no valid event bits; both `IN_MASK_ADD` and `IN_MASK_CREATE`; `fd` not an
inotify descriptor), `ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `ENOSPC` (per-user
watch limit reached), `ENOTDIR` (`IN_ONLYDIR` on a non-directory).

## Flags and constants (mask bits, values from `<linux/inotify.h>`)

| Constant | Value | Meaning | Since |
|---|---|---|---|
| `IN_ACCESS` | 0x00000001 | File was accessed | 2.6.13 |
| `IN_MODIFY` | 0x00000002 | File was modified | 2.6.13 |
| `IN_ATTRIB` | 0x00000004 | Metadata changed | 2.6.13 |
| `IN_CLOSE_WRITE` | 0x00000008 | Writable file closed | 2.6.13 |
| `IN_CLOSE_NOWRITE` | 0x00000010 | Unwritable file closed | 2.6.13 |
| `IN_OPEN` | 0x00000020 | File was opened | 2.6.13 |
| `IN_MOVED_FROM` | 0x00000040 | Moved out of watched dir | 2.6.13 |
| `IN_MOVED_TO` | 0x00000080 | Moved into watched dir | 2.6.13 |
| `IN_CREATE` | 0x00000100 | File created in watched dir | 2.6.13 |
| `IN_DELETE` | 0x00000200 | File deleted in watched dir | 2.6.13 |
| `IN_DELETE_SELF` | 0x00000400 | Watched object itself deleted | 2.6.13 |
| `IN_MOVE_SELF` | 0x00000800 | Watched object itself moved | 2.6.13 |
| `IN_UNMOUNT` | 0x00002000 | Backing filesystem unmounted | 2.6.13 |
| `IN_Q_OVERFLOW` | 0x00004000 | Event queue overflowed | 2.6.13 |
| `IN_IGNORED` | 0x00008000 | Watch was removed | 2.6.13 |
| `IN_ONLYDIR` | 0x01000000 | Watch only directories | 2.6.15 |
| `IN_DONT_FOLLOW` | 0x02000000 | Do not follow symlinks | 2.6.15 |
| `IN_EXCL_UNLINK` | 0x04000000 | Skip events for unlinked objects | 2.6.36 |
| `IN_MASK_CREATE` | 0x10000000 | Fail with EEXIST instead of re-watching | 4.18 |
| `IN_MASK_ADD` | 0x20000000 | OR into the existing watch mask | header (glibc 2.5; no kernel date pinned in sources) |
| `IN_ISDIR` | 0x40000000 | Event subject is a directory (returned, not settable) | 2.6.13 |
| `IN_ONESHOT` | 0x80000000 | Deliver one event, then remove the watch | 2.6.13 |

The header also composes `IN_CLOSE`, `IN_MOVE` and `IN_ALL_EVENTS`. Removing
a watch (explicitly or by deleting the object) generates `IN_IGNORED`
([inotify_rm_watch.md](inotify_rm_watch.md)); before 2.6.36 `IN_ONESHOT`
did not emit that follow-up event, since 2.6.36 it does (inotify.7 BUGS).

## Security and notes

This is a Linux-specific API. Hard limits (`max_user_watches` etc.) and the
`IN_IGNORED`-after-unlink behavior are described in the fetched inotify.7.
Fanotify is the privileged, mount-wide alternative:
[fanotify_init.md](fanotify_init.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/inotify_add_watch.2`
- Online: https://man7.org/linux/man-pages/man2/inotify_add_watch.2.html
- Mask overview: `source-cache/fetched/inotify.7.txt` (man-pages 6.19)
- Constants: `/usr/include/x86_64-linux-gnu/linux/inotify.h`, `sys/inotify.h`
