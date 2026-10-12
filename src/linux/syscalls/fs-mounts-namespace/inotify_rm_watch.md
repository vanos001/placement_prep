# inotify_rm_watch(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 255 / i386 293 / arm64-generic 28 / arm32 318 |
| Since (kernel) | 2.6.13 (inotify merged in 2.6.13; man VERSIONS) |
| Man page | man2/inotify_rm_watch.2 (cached, 2021-03-22) |
| glibc wrapper | Yes; `<sys/inotify.h>` (glibc 2.4; the `wd` argument was typed `uint32_t` before glibc 2.10, `int` since) |
| Aliases covered | none |
| Ledger ID | SC-inotify_rm_watch |

## Purpose

`inotify_rm_watch()` removes the watch identified by the watch descriptor
`wd` from the inotify instance referred to by `fd`. It is one third of the
inotify API, next to [inotify_init.md](inotify_init.md) and
[inotify_add_watch.md](inotify_add_watch.md).

## Synopsis

    #include <sys/inotify.h>
    int inotify_rm_watch(int fd, int wd);

## Arguments and behavior

`fd` must refer to an inotify instance and `wd` to a watch previously
returned by `inotify_add_watch()` on that same instance. Removal is
asynchronous to readers: the kernel queues an `IN_IGNORED` event for this
watch descriptor, so a program that just keeps reading gets informed that the
watch is gone (the wd can then be retired). A watch can also be removed
implicitly -- when the watched object is deleted, moved, or its filesystem is
unmounted -- with the same `IN_IGNORED` notification.

## Return value and errors

Returns 0 on success, -1 on error: `EBADF` (`fd` is not a valid descriptor),
`EINVAL` (`wd` is not a valid watch descriptor on `fd`, or `fd` is not an
inotify file descriptor).

## Flags and constants

None; the call takes exactly the two arguments shown above.

## Security and notes

No permission check beyond holding the inotify descriptor: anyone who created
the instance may drop its watches. Related event constants (`IN_IGNORED`
0x00008000 and friends) are tabulated on
[inotify_add_watch.md](inotify_add_watch.md); queue behavior and the
`/proc/sys/fs/inotify/*` tunables are described in the fetched inotify.7 and
on [inotify_init.md](inotify_init.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/inotify_rm_watch.2`
- Online: https://man7.org/linux/man-pages/man2/inotify_rm_watch.2.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (255), `syscall_32.tbl` (293),
  `syscall_generic.tbl` (28)
- glibc type change note: comment in the cached roff source (glibc bug 7040)
