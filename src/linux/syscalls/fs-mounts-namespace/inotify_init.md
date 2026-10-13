# inotify_init(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | inotify_init: x64 253 / i386 291 / arm64-generic none / arm32 316; inotify_init1: x64 294 / i386 332 / arm64-generic 26 / arm32 360 |
| Since (kernel) | inotify_init 2.6.13; inotify_init1 2.6.27 (man VERSIONS) |
| Man page | man2/inotify_init.2 covers both (local cache, dated 2020-04-11); man2/inotify_init1.2 is a roff `.so` alias; the API overview man7/inotify.7 is not in the local cache and was fetched -> `source-cache/fetched/inotify.7.html` / `.txt` |
| glibc wrapper | Yes; `inotify_init()` glibc 2.4, `inotify_init1()` glibc 2.9 (man VERSIONS); declared in `<sys/inotify.h>` (installed glibc 2.41) |
| Aliases covered | `inotify_init1` (SC-inotify_init1, grouped here) |
| Ledger ID | SC-inotify_init |

## Purpose

`inotify_init()` creates a new inotify instance and returns the file descriptor
of its event queue; watches are then added with inotify_add_watch(2) and
removed with inotify_rm_watch(2). `inotify_init1()` is the flags-taking
variant. The asm-generic table has only the `inotify_init1` number (26), which
is why the arm64-generic column shows none for the plain call (worklog 1-d and
the hub note this).

## Synopsis

    #include <sys/inotify.h>
    int inotify_init(void);
    int inotify_init1(int flags);

## Arguments and behavior

| Call | Argument | Notes |
|---|---|---|
| `inotify_init()` | none | Equivalent to `inotify_init1(0)` |
| `inotify_init1()` | `flags` | `IN_CLOEXEC` and/or `IN_NONBLOCK`, bitwise OR |

`IN_NONBLOCK` sets `O_NONBLOCK` on the open file description (reads of the
queue then fail with `EAGAIN` when empty instead of blocking);
`IN_CLOEXEC` sets `FD_CLOEXEC`. Both constants equal `O_CLOEXEC` /
`O_NONBLOCK` in `<linux/inotify.h>`, saving extra `fcntl(2)` calls.

## Return value and errors

Returns a new file descriptor on success, -1 on error with `errno` set.
Errors per the man page: `EINVAL` (`inotify_init1` with an invalid flags
value), `EMFILE` (per-user limit on inotify instances reached, or the
per-process open file descriptor limit reached), `ENFILE` (system-wide file
table limit), `ENOMEM`.

## Flags and constants

Event and watch-mask bits (values from `include/linux/inotify.h`, same set as
the installed headers; semantics per fetched inotify.7):

| Constant | Value | Class | Meaning |
|---|---|---|---|
| `IN_ACCESS` | 0x00000001 | event | File was accessed |
| `IN_MODIFY` | 0x00000002 | event | File was modified |
| `IN_ATTRIB` | 0x00000004 | event | Metadata changed |
| `IN_CLOSE_WRITE` | 0x00000008 | event | Writable file closed |
| `IN_CLOSE_NOWRITE` | 0x00000010 | event | Unwritable file closed |
| `IN_OPEN` | 0x00000020 | event | File opened |
| `IN_MOVED_FROM` | 0x00000040 | event | Moved out of watched dir (cookie pairs with MOVED_TO) |
| `IN_MOVED_TO` | 0x00000080 | event | Moved into watched dir |
| `IN_CREATE` | 0x00000100 | event | Subfile created |
| `IN_DELETE` | 0x00000200 | event | Subfile deleted |
| `IN_DELETE_SELF` | 0x00000400 | event | Watched object deleted |
| `IN_MOVE_SELF` | 0x00000800 | event | Watched object moved |
| `IN_UNMOUNT` | 0x00002000 | event | Backing filesystem unmounted |
| `IN_Q_OVERFLOW` | 0x4000 | event | Queue overflowed (wd = -1) |
| `IN_IGNORED` | 0x8000 | event | Watch removed (see inotify.7) |
| `IN_CLOSE` | WRITE\|NOWRITE | mask | Shorthand |
| `IN_MOVE` | MOVED_FROM\|MOVED_TO | mask | Shorthand |
| `IN_ONLYDIR` | 0x01000000 | watch | Only watch directories |
| `IN_DONT_FOLLOW` | 0x02000000 | watch | Do not dereference symlink |
| `IN_EXCL_UNLINK` | 0x04000000 | watch | Skip events for unlinked children |
| `IN_MASK_CREATE` | 0x10000000 | watch | Fail if watch exists (added with inotify_add_watch) |
| `IN_MASK_ADD` | 0x20000000 | watch | OR into an existing watch mask |
| `IN_ISDIR` | 0x40000000 | event | Subject was a directory |
| `IN_ONESHOT` | 0x80000000 | watch | Deliver one event, then remove watch |

Tunables named by inotify.7: `/proc/sys/fs/inotify/max_user_instances`,
`max_user_watches`, `max_queued_events`.

## Security and notes

No capability is required; limits are per-user and reachable through the
`/proc/sys/fs/inotify/` tunables above. Events carry an `inotify_event`
struct (wd, mask, cookie, len, name) defined in `<sys/inotify.h>`. Queue
overflow is signaled with `IN_Q_OVERFLOW` rather than a failed read; `IN_IGNORED`
arrives when a watch is killed (file deleted, filesystem unmounted). Related
pages in the hub: inotify_add_watch(2), inotify_rm_watch(2) --
[overview.md](overview.md).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/inotify_init.2`, `.so` alias `inotify_init1.2`
- Fetched overview: `source-cache/fetched/inotify.7.txt` (from
  https://man7.org/linux/man-pages/man7/inotify.7.html)
- Constants: installed `/usr/include/linux/inotify.h`, `/usr/include/x86_64-linux-gnu/sys/inotify.h`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (253, 294), `syscall_generic.tbl` (26)
