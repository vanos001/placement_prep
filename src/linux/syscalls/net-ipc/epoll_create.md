# epoll_create(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | epoll_create 213 / 254 / - / 250; epoll_create1 291 / 329 / 20 / 357 (hub + cached tables) |
| Since (kernel) | epoll_create 2.6 (hub; epoll_create.2 roff comment: "To be precise: kernel 2.5.44"); epoll_create1 2.6.27 (epoll_create.2 VERSIONS) |
| Man page | man2/epoll_create.2 (cached roff, dated 2021-03-22; epoll_create1.2 is a .so alias) |
| glibc wrapper | epoll_create glibc 2.3.2; epoll_create1 glibc 2.9 (VERSIONS) |
| Aliases covered | epoll_create1 (SC-epoll_create1, grouped per ledger) |
| Ledger ID | SC-epoll_create |

## Purpose

epoll_create() creates a new epoll(7) instance and returns a file
descriptor referring to it; that fd is used for all subsequent epoll
calls ([epoll_ctl](epoll_ctl.md), [epoll_wait](epoll_wait.md)). When
all fds referring to the instance are closed, the kernel destroys it
and releases its resources (epoll_create.2).

## Synopsis

```c
#include <sys/epoll.h>
int epoll_create(int size);
int epoll_create1(int flags);
```

## Arguments and behavior

`size` was an initial allocation hint for the number of descriptors
expected; since Linux 2.6.8 it is ignored but must still be greater
than zero, for backward compatibility of new applications on older
kernels (epoll_create.2 NOTES). epoll_create1() drops the obsolete
argument; with flags 0 it is the same as epoll_create().

## Return value and errors

New fd on success; -1 with errno (epoll_create.2): EINVAL (size not
positive; epoll_create1 invalid flags), EMFILE (per-process fd limit;
also the per-user /proc/sys/fs/epoll/max_user_instances limit), ENFILE,
ENOMEM.

## Flags and constants

| Flag | Effect |
|---|---|
| EPOLL_CLOEXEC | FD_CLOEXEC on the new fd (the only defined epoll_create1 flag) |

## Security and notes

The glibc wrappers: epoll_create since 2.3.2, epoll_create1 since
2.9 (VERSIONS; nm confirms epoll_create@@GLIBC_2.3.2,
epoll_create1@@GLIBC_2.9). musl 1.2.5 (src/linux/epoll.c, worklog
1-g) calls SYS_epoll_create1 first and falls back to SYS_epoll_create
with size 1 only when flags is 0 and the kernel lacks create1 -- the
reverse composition of what one might guess. The instance itself
supports poll(2)/epoll on its own fd (used to detect instance
events); for the wait side see [epoll_wait](epoll_wait.md). Kernel
version honesty: the man page prose says "added to the kernel in
version 2.6" with a comment noting 2.5.44 as the precise introduction
-- both recorded here.

## References

- Cached man page: source-cache/man-pages-sparse/man2/epoll_create.2 (epoll_create1.2 .so).
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- musl fallback: source-cache/musl-clone/musl/src/linux/epoll.c (worklog 1-g).
- glibc symbols: nm -D libc.so.6 (glibc 2.41, worklog 3-f).
