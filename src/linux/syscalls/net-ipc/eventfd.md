# eventfd(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | eventfd 284 / 323 / - / 351; eventfd2 290 / 328 / 19 / 356 (hub + cached tables) |
| Since (kernel) | eventfd 2.6.22 (hub, eventfd.2 VERSIONS); eventfd2 2.6.27 (eventfd.2 VERSIONS); EFD_SEMAPHORE 2.6.30 |
| Man page | man2/eventfd.2 (cached roff, dated 2021-03-22; eventfd2.2 is a .so alias) |
| glibc wrapper | working support since glibc 2.8 (2.7 present but "reportedly does not build"); since 2.9 the wrapper uses eventfd2 when available (eventfd.2 VERSIONS) |
| Aliases covered | eventfd2 (SC-eventfd2, flags variant) |
| Ledger ID | SC-eventfd |

## Purpose

eventfd() creates an "eventfd object" that can be used as an event
wait/notify mechanism by user applications and by the kernel, and
returns an fd referring to it. The object holds a kernel-maintained
unsigned 64-bit counter initialized to `initval`. It is the cheap,
single-fd alternative to a pipe for pure signaling and is the bridge
used by kernel subsystems (e.g. AIO, io_uring) to signal completion
into an event loop (eventfd.2 NOTES; see [io_uring_setup](io_uring_setup.md)).

## Synopsis

```c
#include <sys/eventfd.h>
int eventfd(unsigned int initval, int flags);
```

## Arguments and behavior

flags (eventfd.2; values from bits/eventfd.h):

| Flag | Since | Value | Effect |
|---|---|---|---|
| EFD_SEMAPHORE | 2.6.30 | 1 (octal 01) | semaphore-like reads: each read returns 1 and decrements the counter |
| EFD_NONBLOCK | 2.6.27 | 04000 | O_NONBLOCK on the open file description |
| EFD_CLOEXEC | 2.6.27 | 02000000 | FD_CLOEXEC on the fd |

Through Linux 2.6.26 the flags argument is unused and must be zero
(eventfd.2). read(2) returns an 8-byte host-order uint64 (EINVAL if
the buffer is smaller): without EFD_SEMAPHORE a nonzero counter is
returned and reset to 0; with EFD_SEMAPHORE a read returns 1 and
decrements the counter by 1; a zero counter blocks or returns EAGAIN
if nonblocking. This read-1/decrement behavior is implemented in
eventfd_ctx_do_read in fs/eventfd.c (worklog 1-g kernel read).
write(2) adds the supplied 8-byte value to the counter; the maximum
is 0xfffffffffffffffe, beyond which the write blocks or returns
EAGAIN; writing 0xffffffffffffffff fails with EINVAL. poll/select/
epoll: readable while counter > 0, writable while a write of at
least 1 would not block, POLLERR on counter overflow (read then
returns 0xffffffffffffffff).

## Return value and errors

New eventfd fd on success; -1 with errno: EINVAL (unsupported flags),
EMFILE, ENFILE, ENODEV (internal anonymous-inode mount failure),
ENOMEM.

## Flags and constants

EFD_* as in the table; glibc adds eventfd_t plus eventfd_read(3)/
eventfd_write(3) (eventfd.2 Additional glibc features).

## Security and notes

The fd is inherited across fork(2) (same underlying object) and
preserved across execve(2) unless FD_CLOEXEC is set. Kernel overhead
is much lower than a pipe and only one fd is needed (eventfd.2
NOTES).

## References

- Cached man page: source-cache/man-pages-sparse/man2/eventfd.2 (eventfd2.2 .so).
- Flag values: /usr/include/x86_64-linux-gnu/bits/eventfd.h.
- EFD_SEMAPHORE semantics: fs/eventfd.c via worklog Task 1-g.
- Numbers: hub overview.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
