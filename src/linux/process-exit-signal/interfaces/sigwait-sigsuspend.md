# Sigwait and Sigsuspend — Synchronous and Race-Free Waiting (IF-008 – IF-010)

Waiting for a signal sounds trivial — until you meet the race between "checking for work" and
"blocking". `pause(2)` alone loses signals that arrive between the check and the sleep. The
POSIX answer is the *atomic mask swap* of `sigsuspend(2)`; the threads answer is *synchronous
consumption* with `sigwait(3)`/`sigwaitinfo(2)`. This chapter covers both and contrasts
consumption via `sigwait` with delivery via a handler (IF-008, IF-009, IF-010).

## sigwait(3) (IF-008)

```c
#include <signal.h>        /* glibc: _POSIX_C_SOURCE >= 199506L since 2.26 */
int sigwait(const sigset_t *restrict set, int *restrict sig);
```

**Category**: libc function on Linux — per
[sigwait(3)](https://man7.org/linux/man-pages/man3/sigwait.3.html) it is implemented using
`sigtimedwait(2)` (i.e. the `rt_sigtimedwait(2)` syscall); POSIX specifies it as a function,
not a syscall. MT-Safe.

Semantics (per sigwait(3)): suspend the calling thread until one of the signals in `set`
becomes pending **for it**, then *accept* the signal — remove it from the pending set — and
store the number in `*sig`. For the signal to have a chance to be pending rather than
delivered to a handler, it must first be **blocked** (typically process-wide; see
[signal-masks](./signal-masks.md)). Return convention: `0` on success, otherwise an **error
number** (`EINVAL` for an invalid set member). glibc's `sigwait` silently ignores the two
NPTL-internal RT signals in `set` (per sigwait(3) VERSIONS).

Waiting for `SIGKILL`/`SIGSTOP` is silently ignored (same rule as blocking them).

## sigwaitinfo(2) / sigtimedwait(2) (IF-009)

```c
#include <signal.h>        /* _POSIX_C_SOURCE >= 199309L */
int sigwaitinfo(const sigset_t *restrict set, siginfo_t *_Nullable restrict info);
int sigtimedwait(const sigset_t *restrict set, siginfo_t *_Nullable restrict info,
                 const struct timespec *restrict timeout);
```

**Category**: `sigwaitinfo(3)` is a library function implemented on top of `sigtimedwait(2)`,
which itself wraps the `rt_sigtimedwait(2)` syscall (kernel ≥ 2.2, with `sigsetsize`
argument); per
[sigtimedwait.2](https://man7.org/linux/man-pages/man2/sigtimedwait.2.html). POSIX.1-2024
documents both; the raw syscall is Linux-only.

Differences from `sigwait(3)`: they **return the signal number as the function result**
(`> 0`), report errors the usual way (`-1` + `errno`), and can fill a `siginfo_t` — for a
`sigqueue(3)`-delivered real-time signal, `si_value` carries the payload; the queue resource
is released on consumption (per sigwaitinfo(2) and
[real-time-signals](../signals/real-time-signals.md)).

Selection and timeout semantics (per sigtimedwait.2 / POSIX):

- If several signals in `set` are pending, selection follows the usual ordering rules:
  lowest-numbered real-time signal first; standard-before-real-time on Linux; order among
  standard signals unspecified.
- `sigtimedwait` with a zero-valued `timeout` is a *poll*; with `timeout == NULL`, POSIX
  leaves the meaning unspecified and Linux treats it as `sigwaitinfo` (infinite wait).
- Errors: `EAGAIN` (timeout expired), `EINTR` (interrupted by a handler for a signal **not**
  in `set`), `EINVAL` (bad timeout).

Notes that shape real usage (per sigtimedwait.2):

- Block the signals in `set` beforehand (in *all* threads of the process), or the signal may be
  consumed by default disposition or a handler in another thread.
- If multiple threads wait for the same signal, **exactly one** of them receives each
  process-directed instance; which one is indeterminate.
- You **cannot** `sigwait` for synchronously generated signals: `SIGSEGV`/`SIGFPE`-class
  faults go to a handler or kill the process — sigwaitinfo/sigtimedwait are documented as
  unable to receive them.

On 32-bit architectures with 64-bit time_t (glibc ≥ 2.34 era), the timeout is marshalled
through the `rt_sigtimedwait_time64` syscall variant — an ABI detail glibc hides (Linux ≥ 5.1
time64 family). For IF-009 completeness: applications see only `sigtimedwait(3)`; the `*64`
split is a libc/kernel implementation detail.

## sigsuspend(2) (IF-010)

```c
#include <signal.h>        /* _POSIX_C_SOURCE */
int sigsuspend(const sigset_t *mask);
```

**Category**: libc wrapper around `rt_sigsuspend(2)` (kernel ≥ 2.2; per
[sigsuspend.2](https://man7.org/linux/man-pages/man2/sigsuspend.2.html)). POSIX.1.

Semantics: **atomically** replace the calling thread's mask with `mask`, then sleep until a
signal whose action is to run a handler (or terminate the process) arrives. If the signal
terminates, `sigsuspend` never returns; if it is caught, `sigsuspend` returns `-1` with
`errno == EINTR` **after the handler returns**, and the previous mask is restored by the
kernel (per sigsuspend.2). `SIGKILL`/`SIGSTOP` in `mask` are ignored (they cannot be
blocked). It *always* "fails" — `EINTR` is the success path.

### The race it exists to close

```c
/* WRONG — classic lost-wakeup race */
sigprocmask(SIG_BLOCK, &block, &old);
while (!work_pending())
    pause();                 /* if the signal arrives between the check and
                                pause(), it is delivered now (mask is still
                                blocking? no: pause() doesn't unblock) — the
                                wakeup is lost and we sleep forever */
sigprocmask(SIG_SETMASK, &old, NULL);
```

```c
/* RIGHT — atomic swap closes the window */
sigprocmask(SIG_BLOCK, &block, &old);
while (!work_pending())
    sigsuspend(&old);        /* unblocks AND sleeps in one atomic step:
                                a signal delivered after the check but before
                                the sleep is caught by sigsuspend itself */
sigprocmask(SIG_SETMASK, &old, NULL);
```

Per sigsuspend.2 NOTES, this block-then-suspend pattern is the canonical use: protect the
critical section with a blocked mask, then pass the *saved* mask to `sigsuspend`.

## Consuming via sigwait vs delivery via handler

| Aspect | `sigwait`/`sigwaitinfo` | handler via `sigaction` |
|--------|-------------------------|--------------------------|
| Execution context | an ordinary thread, full program state, any (thread-safe) code | async-signal-safe code only (see [async-signal-safety](./async-signal-safety.md)) |
| Error returns | ordinary return values/`siginfo` | none — return to interrupted code |
| Ordering/priority | respects the real-time ordering rules at selection time | same kernel ordering; ordering of *handler runs* follows delivery |
| Interaction with blocked mask | signal must be blocked or it may never reach `sigwait` | works whether or not blocked (unblocked signals interrupt anytime) |
| `EINTR` exposure | none for signals in `set` (they're consumed); `EINTR` if interrupted by a handler for a signal outside `set` | the interrupted syscall below the handler sees `EINTR` unless `SA_RESTART` |
| Typical use | dedicated signal thread in servers/daemons | minimal flags (`volatile sig_atomic_t`) in simple programs |

`EINTR` semantics summary (per sigtimedwait.2 and signal(7)): `sigwait`-family calls are
**never restarted** after interruption by a handler; `sigsuspend` is likewise never restarted
and always returns `-1`/`EINTR` — that is its defined control flow.

## Example — race-free wait with a timeout

```c
/* timedwait.c — consume SIGUSR1 synchronously, 5s timeout.
 * Expected: kill -USR1 <pid> => "got SIGUSR1 from pid N (code SI_USER)";
 *           no signal within 5s => "timed out: EAGAIN".
 */
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <time.h>
#include <errno.h>

int main(void) {
    sigset_t set;
    sigemptyset(&set);
    sigaddset(&set, SIGUSR1);
    sigprocmask(SIG_BLOCK, &set, NULL);        /* block so nothing else takes it */

    struct timespec ts = { .tv_sec = 5, .tv_nsec = 0 };
    siginfo_t si;
    int sig = sigtimedwait(&set, &si, &ts);
    if (sig == -1) {
        perror(errno == EAGAIN ? "timeout" : "sigtimedwait");
        return 1;
    }
    printf("got SIGUSR1 from pid %d (si_code %d)\n", si.si_pid, si.si_code);
    return 0;
}
```

## Related Topics

- [Signal masks and pending signals](./signal-masks.md) — the blocking half of the pattern
- [Real-time signals](../signals/real-time-signals.md) — ordering rules that `sigwaitinfo` implements
- [signalfd and pidfd](./signalfd-pidfd.md) — the fd-based alternative for event loops
- [Async-signal safety](./async-signal-safety.md) — why handler-based code is restricted
- Per-syscall pages: [rt_sigsuspend(2)](../../syscalls/signals-time/rt_sigsuspend.md), [pause(2)](../../syscalls/signals-time/pause.md); glibc rows [GLIBC-sigsuspend](../../libc/ledger-glibc.md), [GLIBC-sigwait](../../libc/ledger-glibc.md)

## References

- *sigwait(3)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man3/sigwait.3.html>
- *sigwaitinfo(2) / sigtimedwait(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigtimedwait.2.html>
- *sigsuspend(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigsuspend.2.html>
- *sigwait*, *sigwaitinfo*, *sigsuspend*, POSIX.1-2017, <https://pubs.opengroup.org/onlinepubs/9699919799/functions/sigwait.html>, <https://pubs.opengroup.org/onlinepubs/9699919799/functions/sigwaitinfo.html>, <https://pubs.opengroup.org/onlinepubs/9699919799/functions/sigsuspend.html>
- *signal(7)*, <https://man7.org/linux/man-pages/man7/signal.7.html> (interruption/restart rules)
