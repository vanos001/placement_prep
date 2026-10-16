# timerfd_settime64 / timerfd_gettime64

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / 411 / -- / 411 (settime64); -- / 410 / -- / 410 (gettime64) |
| Since (kernel) | 5.1 (time64 twins batch, man-pages syscalls(2); ledger tag probe "added 5.1") |
| Man page | man2/timerfd_settime.2 and man2/timerfd_gettime.2 (man-pages 6.19 HTML set, fetched 2026-10-17) describe the family; the time64 twins are covered in the same pages' 32-bit-architectures handling |
| glibc wrapper | timerfd_settime(3) / timerfd_gettime(3) @@GLIBC_2.8 (nm -D, glibc 2.41); the wrappers call the *64 entries on 32-bit kernels and hide them entirely |
| Aliases covered | timerfd_gettime64 (i386 410, SC-timerfd_gettime64); timerfd_settime64 (i386 411, SC-timerfd_settime64). Base timerfd_settime/timerfd_gettime live on [timerfd_create](timerfd_create.md) |
| Ledger ID | SC-timerfd_settime64 |

## Purpose

timerfd_settime64() and timerfd_gettime64() are the 64-bit-time twins of [timerfd_settime](timerfd_create.md) and timerfd_gettime(), created in the 5.1 y2038 batch so that 32-bit architectures could arm and read timers with 64-bit `struct __kernel_itimerspec` fields. They exist only on the 32-bit ABI tables (i386 410/411, arm32 410/411); x86_64 and asm-generic 64-bit ABIs use the base entries whose timespec is already 64-bit, which is why the ledger columns read `--` there.

## Synopsis

```c
/* kernel-side shapes; userspace sees the same timerfd API */
struct __kernel_itimerspec {
    struct __kernel_timespec it_interval;  /* 64-bit tv_sec/tv_nsec */
    struct __kernel_timespec it_value;
};
long syscall(SYS_timerfd_settime64, int fd, int flags,
             const struct __kernel_itimerspec *new_value,
             struct __kernel_itimerspec *old_value);
long syscall(SYS_timerfd_gettime64, int fd,
             struct __kernel_itimerspec *curr_value);
```

## Arguments and behavior

Argument-for-argument identical to the base calls (timerfd_settime.2, DESCRIPTION): `fd` from [timerfd_create](timerfd_create.md), `flags` with TFD_TIMER_ABSTIME and TFD_TIMER_CANCEL_ON_SET semantics unchanged, `new_value`/`old_value`/`curr_value` carrying interval and expiry -- with the only difference being 64-bit seconds/nanoseconds fields that keep working after January 2038 on 32-bit kernels. Everything the family page documents about expiration arithmetic, TFD_TIMER_ABSTIME clamping, and the ECANCELED re-arm quirk (man NOTES) applies verbatim to the twins.

## Return value and errors

0 on success; -1 with errno on the wrapper, negated error on the raw syscall: EINVAL (fd not a timerfd or bad flags), EFAULT (bad struct pointers), plus the flags-specific behavior documented on the family page (timerfd_settime.2, ERRORS).

## Flags and constants

TFD_TIMER_ABSTIME (1 << 0) and TFD_TIMER_CANCEL_ON_SET (1 << 1) -- same values as the base entry (timerfd_settime.2; /usr/include/sys/timerfd.h).

## Security and notes

The twins are invisible to correctly written userspace: glibc picks them when the target kernel provides them and falls back otherwise, which is why no portable program references SYS_timerfd_settime64 directly. The interesting interview angle is the ABI pattern -- one syscall number per (call x time-width) is the price of not breaking old binaries, the same pattern as clock_adjtime64, rt_sigtimedwait_time64, and futex_time64 (see [clock_adjtime](../signals-time/clock_adjtime.md), [sigtimedwait](../signals-time/sigtimedwait.md), [futex](../process/futex.md)). Cross-reference: [timerfd_create](timerfd_create.md), [nanosleep](../signals-time/nanosleep.md), [epoll_wait](epoll_wait.md).

## References

- https://man7.org/linux/man-pages/man2/timerfd_settime.2.html
- https://man7.org/linux/man-pages/man2/timerfd_gettime.2.html
- https://man7.org/linux/man-pages/man2/timerfd_create.2.html (family hub)
- worklog: wrapper symbols timerfd_settime/timerfd_gettime @@GLIBC_2.8 verified with nm -D against glibc 2.41 (2026-10-17)
