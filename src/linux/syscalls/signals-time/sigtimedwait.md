# rt_sigtimedwait(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 128 / 177 / 137 / 177 |
| Since (kernel) | 2.2 |
| Man page | man2/rt_sigtimedwait.2 (man-pages 6.19 HTML set, fetched 2026-10-17) -- the sigwaitinfo/sigtimedwait/rt_sigtimedwait page |
| glibc wrapper | sigtimedwait(3) W @@GLIBC_2.2.5 / sigwaitinfo(3) (nm -D, glibc 2.41); wrappers call rt_sigtimedwait(2) with sigsetsize = sizeof(sigset_t) (rt_sigtimedwait.2, C library/kernel differences) |
| Aliases covered | rt_sigtimedwait_time64 (i386 421, SC-rt_sigtimedwait_time64, 5.1 time64 twin, ledger status researched) |
| Ledger ID | SC-rt_sigtimedwait |

## Purpose

rt_sigtimedwait() is the raw kernel call behind sigtimedwait(3)/sigwaitinfo(3): it suspends the calling thread until one of the signals in `set` becomes pending, and -- crucially -- delivers it synchronously: the signal is consumed from the pending set and returned as a `siginfo_t`, without ever running a signal handler (rt_sigtimedwait.2, DESCRIPTION). With a timeout it becomes a bounded wait (sigtimedwait); with a NULL timeout it waits indefinitely (sigwaitinfo).

## Synopsis

```c
#include <signal.h>
int sigtimedwait(const sigset_t *restrict set,
                 siginfo_t *_Nullable restrict info,
                 const struct timespec *restrict timeout);
/* raw: syscall(SYS_rt_sigtimedwait, set, info, timeout, sigsetsize) */
```

## Arguments and behavior

`set` selects the signals to wait for; `info` (optional) receives the siginfo of the consumed signal; `timeout` bounds the wait (NULL on the sigwaitinfo path). The raw call takes a fourth argument, `sigsetsize`, required to be sizeof(sigset_t) -- EINVAL otherwise (rt_sigtimedwait.2, C library/kernel differences). glibc wrappers silently ignore attempts to wait for the two real-time signals NPTL uses internally (rt_sigtimedwait.2, C library/kernel differences; nptl(7)). The time64 twin rt_sigtimedwait_time64 (i386 421) swaps the timespec for its 64-bit form; semantics unchanged.

## Return value and errors

Returns the signal number (> 0) on success; -1 with errno on failure (rt_sigtimedwait.2, RETURN VALUE). Errors: EAGAIN (no signal in `set` became pending within the timeout), EINTR (interrupted by a handler for a signal not in `set`), EINVAL (invalid `timeout`, or on the raw call a wrong `sigsetsize`) (rt_sigtimedwait.2, ERRORS).

## Flags and constants

None (sigset built with sigset(3) macros; SA_SIGINFO-style siginfo payload returned).

## Security and notes

The signals in `set` should be blocked before the wait, or the call can race an unblocked delivery into the handler (the classic synchronous-wait pattern from sigwaitinfo.2 DESCRIPTION). No capability is involved. EINTR semantics matter for cancellation points: POSIX makes sigtimedwait a cancellation point in threads. Interview angle: sigwaitinfo() vs sigtimedwait() vs handler-based delivery is the standard "synchronous vs asynchronous signal handling" question, and EAGAIN is the timeout answer that distinguishes it from pause(2). Cross-reference: [rt_sigaction](rt_sigaction.md), [rt_sigprocmask](rt_sigprocmask.md), [rt_sigpending](sigpending.md), [pause](pause.md), [rt_sigqueueinfo](rt_sigqueueinfo.md).

## References

- https://man7.org/linux/man-pages/man2/rt_sigtimedwait.2.html
- man-pages syscalls(2) version table (2.2)
- worklog: wrapper symbols sigtimedwait W @@GLIBC_2.2.5 verified with nm -D against glibc 2.41 (2026-10-17)
