# signalfd(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | signalfd 282 / 321 / - / 349; signalfd4 289 / 327 / 74 / 355 (hub) |
| Since (kernel) | 2.6.22 (hub; signalfd.2 VERSIONS); signalfd4 since 2.6.27 (signalfd.2 VERSIONS) |
| Man page | man2/signalfd.2 (cached, dated 2021-03-22; covers both signalfd and signalfd4) |
| glibc wrapper | yes for signalfd since glibc 2.8 ("Working support is provided in glibc since version 2.8", man VERSIONS); SFD_* flags from <sys/signalfd.h> (values verified in installed bits/signalfd.h) |
| Aliases covered | signalfd4 (SC-signalfd4, grouped per ledger) |
| Ledger ID | SC-signalfd |

## Purpose

signalfd() creates a file descriptor that can be used to accept signals
targeted at the caller -- an alternative to a signal handler or
sigwaitinfo(2) with the advantage that the fd can be monitored by
select/poll/epoll ([poll](poll.md), [epoll_wait](epoll_wait.md)). The
signals in `mask` should normally be blocked with sigprocmask(2) so they
queue for the fd instead of taking their default dispositions. SIGKILL
and SIGSTOP in mask are silently ignored (signalfd.2).

## Synopsis

```c
#include <sys/signalfd.h>
int signalfd(int fd, const sigset_t *mask, int flags);
```

glibc presents one name; fd = -1 creates, otherwise mask replaces the
set of an existing signalfd. The 2.6.22 kernel signalfd had no flags;
2.6.27 added signalfd4 with flags (SFD_CLOEXEC, SFD_NONBLOCK), and
glibc routes to whichever the kernel has.

## Arguments and behavior

`mask` is a signal set (sigsetops(3) macros). read(2) returns one or
more `struct signalfd_siginfo` records (128 bytes each: ssi_signo,
ssi_code, ssi_pid, ssi_uid, ssi_int, ssi_ptr, ssi_addr, ... mirroring
siginfo_t fields) as long as signals are pending and fit. The read
consumes the signals: they are no longer pending for handlers or
sigwaitinfo(2). poll(2) reports POLLIN while masked signals are
pending. Multiple signalfd fds can watch different sets; a signal in
several masks can be read once from any of them.

## Return value and errors

New or existing fd on success; -1 with `errno`: `EBADF`, `EINVAL` (fd is
not a signalfd; invalid flags; nonzero flags on 2.6.26 and earlier),
`EMFILE`/`ENFILE`, `ENODEV` (anonymous inode device), `ENOMEM`.

## Flags and constants

SFD_* flags, values verified in installed
/usr/include/x86_64-linux-gnu/bits/signalfd.h:

| Flag | Value | Note |
|---|---|---|
| SFD_CLOEXEC | 02000000 | close-on-exec on the new fd |
| SFD_NONBLOCK | 00004000 | O_NONBLOCK on the open file description |

## Security and notes

- Queue interaction: signals accepted via the fd leave the pending
  queue only when read; the fd's mask is visible in /proc/[pid]/fdinfo
  (signalfd.2 NOTES). synchronously generated signals (SIGSEGV on bad
  memory, SIGFPE) cannot be delivered via signalfd -- handler only.
- signalfd vs sigwait: both dequeue directed/thread-directed signals
  synchronously; the fd integrates into poll/epoll loops and survives
  fork (child reads only signals queued to it) and execve; sigwaitinfo
  does not integrate with an event loop. Thread semantics: a read
  returns signals directed to the reading thread or the process, never
  another thread's (signalfd.2).
- epoll caveat: after fork the child's epoll_wait will not report the
  inherited fd ready (signalfd.2 "epoll semantics").

## References

- Cached man page: source-cache/man-pages-sparse/man2/signalfd.2.
- Flag values: /usr/include/x86_64-linux-gnu/bits/signalfd.h.
- Numbers/Since: hub [overview](overview.md); ledger SC-signalfd,
  SC-signalfd4.
