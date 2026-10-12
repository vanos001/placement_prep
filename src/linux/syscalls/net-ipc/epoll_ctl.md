# epoll_ctl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 233 / 255 / 21 / 251 (hub + cached tables) |
| Since (kernel) | 2.6 (hub; epoll_ctl.2 roff comment: "To be precise: kernel 2.5.44") |
| Man page | man2/epoll_ctl.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | glibc 2.3.2 (VERSIONS; nm: epoll_ctl@@GLIBC_2.3.2) |
| Aliases covered | none |
| Ledger ID | SC-epoll_ctl |

## Purpose

epoll_ctl() is the control plane of an epoll instance: it adds,
modifies, or removes entries in the "interest list" of the epoll file
descriptor `epfd` -- the list of file descriptors whose readiness
[epoll_wait](epoll_wait.md) will report. The interface supports any
fd that supports poll(2) (epoll_ctl.2 NOTES); regular files and
directories fail with EPERM.

## Synopsis

```c
#include <sys/epoll.h>
int epoll_ctl(int epfd, int op, int fd, struct epoll_event *event);
```

## Arguments and behavior

`op` (epoll_ctl.2):

| Op | Effect |
|---|---|
| EPOLL_CTL_ADD | add fd (plus its open file description) with `event` to the interest list |
| EPOLL_CTL_MOD | change the settings of an existing fd to `event` |
| EPOLL_CTL_DEL | deregister fd; `event` ignored, may be NULL since 2.6.9 |

`event` is `struct epoll_event { uint32_t events; epoll_data_t data;
}` with `epoll_data_t` a union of ptr/fd/u32/u64 -- the kernel stores
`data` and hands it back via epoll_wait. events mask:

| Bit | Since | Note |
|---|---|---|
| EPOLLIN / EPOLLOUT | - | readable / writable |
| EPOLLRDHUP | 2.6.17 | stream peer closed or shut write half |
| EPOLLPRI | - | exceptional condition (see POLLPRI in poll(2)) |
| EPOLLERR / EPOLLHUP | - | always reported; need not be set |
| EPOLLET | - | edge-triggered instead of default level-triggered |
| EPOLLONESHOT | 2.6.2 | disable fd after one event; rearm via EPOLL_CTL_MOD |
| EPOLLWAKEUP | 3.5 | hold wakeup source while event pending; needs CAP_BLOCK_SUSPEND, else silently ignored |
| EPOLLEXCLUSIVE | 4.5 | exclusive wakeup mode against thundering herd; ADD-only, restricted mask |

EPOLLET, EPOLLONESHOT, EPOLLWAKEUP, EPOLLEXCLUSIVE are input-only --
never returned by epoll_wait.

## Return value and errors

Zero on success; -1 with errno (epoll_ctl.2): EBADF, EEXIST (ADD of
an already-registered fd), EINVAL (epfd not epoll; fd == epfd; bad
op; invalid events with EPOLLEXCLUSIVE; MOD with/after EXCLUSIVE),
ELOOP (circular epoll nesting or depth > 5), ENOENT (MOD/DEL of an
unregistered fd), ENOMEM, ENOSPC (/proc/sys/fs/epoll/max_user_watches
exhausted), EPERM (target does not support epoll, e.g. regular file).

## Flags and constants

See events table above; EPOLLEXCLUSIVE may only be combined with
EPOLLIN, EPOLLOUT, EPOLLWAKEUP, EPOLLET (EPOLLHUP/EPOLLERR allowed
but redundant), and only in EPOLL_CTL_ADD.

## Security and notes

EPOLL_CTL_DEL with NULL event requires kernel 2.6.9+; portable code
passes a non-NULL pointer (epoll_ctl.2 BUGS). EPOLLWAKEUP is silently
ignored without CAP_BLOCK_SUSPEND -- robust applications double-check
the capability (BUGS). Level- vs edge-trigger discipline and the
starvation pitfall are covered on epoll(7) and in
[epoll_wait](epoll_wait.md).

## References

- Cached man page: source-cache/man-pages-sparse/man2/epoll_ctl.2.
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- glibc symbol: nm -D libc.so.6 (glibc 2.41, worklog 3-f).
