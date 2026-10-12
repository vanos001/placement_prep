# timerfd_create(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | timerfd_create 283 / 322 / 85 / 350; timerfd_settime 286 / 325 / 86 / 353; timerfd_gettime 287 / 326 / 87 / 354; timerfd_gettime64 410, timerfd_settime64 411 (i386 + arm32) (hub + cached tables) |
| Since (kernel) | 2.6.25 (hub; timerfd_create.2 VERSIONS "since kernel 2.6.25"); TFD_* flags 2.6.27; TFD_IOC_SET_TICKS 3.17 |
| Man page | man2/timerfd_create.2 (cached roff, dated 2021-03-22; timerfd_settime.2 and timerfd_gettime.2 are .so aliases) |
| glibc wrapper | glibc 2.8 (VERSIONS; nm: timerfd_*@@GLIBC_2.8) |
| Aliases covered | timerfd_settime (SC-timerfd_settime), timerfd_gettime (SC-timerfd_gettime), time64 twins (SC-timerfd_gettime64, SC-timerfd_settime64) |
| Ledger ID | SC-timerfd_create |

## Purpose

timerfd_create() creates a timer object that the kernel advances on a
chosen clock, and returns an fd referring to it; the trio is the
file-descriptor analogue of timer_create(2)/timer_settime(2)/
timer_gettime(2), with read(2) replacing timer_getoverrun(2)
(timerfd_create.2). The fd is readable when expirations occurred, so
timers plug directly into [poll](poll.md)/[select](select.md)/
[epoll_wait](epoll_wait.md) event loops.

## Synopsis

```c
#include <sys/timerfd.h>
int timerfd_create(int clockid, int flags);
int timerfd_settime(int fd, int flags,
                    const struct itimerspec *new_value,
                    struct itimerspec *old_value);
int timerfd_gettime(int fd, struct itimerspec *curr_value);
```

## Arguments and behavior

clockid (timerfd_create.2): CLOCK_REALTIME, CLOCK_MONOTONIC,
CLOCK_BOOTTIME (3.15, includes suspend time), CLOCK_REALTIME_ALARM
and CLOCK_BOOTTIME_ALARM (3.11; both can wake a suspended system and
require CAP_WAKE_ALARM). flags (since 2.6.27, values from
bits/timerfd.h): TFD_NONBLOCK (04000) sets O_NONBLOCK, TFD_CLOEXEC
(02000000) sets FD_CLOEXEC; through 2.6.26 flags must be 0.
timerfd_settime arms/disarms: it_value nonzero arms (absolute if
TFD_TIMER_ABSTIME, else relative), both fields zero disarms;
it_interval nonzero makes it periodic. TFD_TIMER_CANCEL_ON_SET (with
ABSTIME on a REALTIME clock) marks the timer cancelable on a
discontinuous clock change: pending/future reads fail with ECANCELED
(timerfd_create.2). timerfd_gettime returns the relative time to next
expiry and the interval (zero = disarmed / one-shot).

## Return value and errors

timerfd_create: new fd or -1 with EINVAL (bad clockid/flags), EMFILE,
ENFILE, ENODEV, ENOMEM, EPERM (alarm clocks without CAP_WAKE_ALARM).
settime/gettime: 0 or -1 with EBADF, EFAULT, EINVAL (fd not a timerfd;
bad tv_nsec; invalid flags), ECANCELED (see NOTES).

## Flags and constants

TFD_NONBLOCK, TFD_CLOEXEC (bits/timerfd.h); TFD_TIMER_ABSTIME (1<<0),
TFD_TIMER_CANCEL_ON_SET (1<<1) (sys/timerfd.h). ioctl
TFD_IOC_SET_TICKS (3.17, CONFIG_CHECKPOINT_RESTORE) rewrites the
expiration count for checkpoint/restore.

## Security and notes

read(2) yields an 8-byte host-order uint64 expiration count (EINVAL
below 8 bytes; blocks or EAGAIN when none pending). ECANCELED quirk
(NOTES): with ABSTIME+CANCEL_ON_SET on a REALTIME clock, rearming
after a clock jump returns -1/ECANCELED yet the timer IS rearmed --
kept for application compatibility. fork(2) shares the timer object;
execve(2) preserves an armed timer. time64 twins (worklog 1-g, ledger):
timerfd_gettime64/timerfd_settime64, i386/arm 410/411, added 5.1 by
the syscall_32.tbl v5.0-vs-v5.1 probe, using struct __kernel_timespec.

## References

- Cached man page: source-cache/man-pages-sparse/man2/timerfd_create.2 (settime/gettime .so).
- Flag values: /usr/include/x86_64-linux-gnu/bits/timerfd.h, sys/timerfd.h.
- Numbers: hub overview.md, ledger.md; source-cache/kernel/syscall_{64,32,generic,arm}.tbl.
- Worklog Tasks 1-e/1-g (time64 since-date probe).
