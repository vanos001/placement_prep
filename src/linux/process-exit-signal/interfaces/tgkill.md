# tgkill(2) and tkill(2) — Thread-Directed Signals (IF-013)

`kill(2)` targets a process; the kernel then picks an arbitrary unblocked thread to receive a
process-directed signal (see
[Signal masks](./signal-masks.md)). When you need the signal to land on **one specific
thread**, the kernel primitive is `tgkill(2)` — and it is what `raise(3)` and
`pthread_kill(3)` are built on (see [kill-raise](./kill-raise.md)).

## Canonical declarations

```c
/* tgkill — kernel syscall; glibc provides a wrapper since glibc 2.30 */
#include <signal.h>
int tgkill(pid_t tgid, pid_t tid, int sig);

/* tkill — obsolete predecessor; NO glibc wrapper, use syscall(2) */
#include <signal.h>       /* SIG* constants */
#include <sys/syscall.h>  /* SYS_* constants */
#include <unistd.h>
[[deprecated]] int syscall(SYS_tkill, pid_t tid, int sig);
```

**Category**: `tgkill(2)` is a Linux-only syscall (man-pages classify it "Linux"; POSIX has no
equivalent — the POSIX-level interface is `pthread_kill(3)`). Kernel entries: `tkill` since
Linux 2.4.19/2.5.4; `tgkill` since Linux 2.5.75, glibc wrapper since glibc 2.30 (per
[tgkill.2/tkill.2](https://man7.org/linux/man-pages/man2/tgkill.2.html) HISTORY). See the
per-syscall page [tgkill(2)](../../syscalls/signals-time/tgkill.md) for syscall numbers.

Semantics (per tgkill.2): send signal `sig` to the thread with ID `tid` in thread group
`tgid`. **Both** identifiers must match — the pair `(tgid, tid)` is validated, which is
exactly the fix for `tkill`'s flaw: `tkill(tid, sig)` allowed the same TID to be signaled
after a thread exited and the TID was recycled into an unrelated thread, delivering the signal
to the wrong process. With `tgkill`, if the target thread died and its TID was reused inside a
*different* process, the `tgid` check fails and the caller gets `ESRCH`. (The residual race —
TID recycled by a *new thread of the same process* — is inherent; libraries close it with
locking, see below.)

Errors (per tgkill.2):

| errno | Cause |
|-------|-------|
| `EAGAIN` | `RLIMIT_SIGPENDING` reached, or insufficient kernel memory, for a real-time signal (see [real-time signals](../signals/real-time-signals.md)) |
| `EINVAL` | invalid `tid`, `tgid`, or `sig` |
| `EPERM` | permission denied — same rules as `kill(2)` (sender UID/CAP_KILL vs target credentials) |
| `ESRCH` | no thread with that `(tgid, tid)` pair exists |

Both calls are described by the man page as "raw system call interfaces, meant for internal
thread library use" — application code should call `pthread_kill(3)` instead.

## How glibc builds pthread_kill(3) on tgkill (verified in glibc source)

In glibc's `nptl/pthread_kill.c`:

- For the **calling thread** (`THREAD_SELF`), it reads the current kernel TID with `gettid(2)`
  and issues `tgkill(getpid(), tid, signo)` directly — with a comment noting this must use the
  actual TID so it refers to the current thread even after `vfork`, and that the signal is
  delivered immediately (synchronously) because nothing blocks it.
- For **another thread**, glibc takes the target's `exit_lock`, and if `pd->exiting` is set it
  *does not send at all* — the comment explains that sending would be unobservable or could
  hit "a new, unrelated thread that has reused the TID"; instead `pthread_kill` reports
  `ESRCH`. Otherwise it calls `tgkill(__getpid(), pd->tid, signo)`.
- This locking is the userspace half of the TID-recursion race protection the kernel's `tgid`
  check cannot provide; `raise(3)` is `__pthread_kill(__pthread_self(), sig)` (see
  `sysdeps/posix/raise.c`).

`pthread_kill(3)` semantics at the POSIX layer: sends `sig` to the specified thread; if the
signal is blocked by that thread it stays pending *for that thread*; a signal number of 0
performs error checking only. It returns an error number (`ESRCH` if the thread is gone) —
pthread convention, not `-1`/`errno`.

## Races and correctness notes

- **Thread may exit**: between reading `gettid()`-style handles and calling `tgkill`, the
  target can exit; kernel-side you get `ESRCH` (or, worst case pre-locking, TID reuse).
  Library-side, glibc's `exit_lock` closes the observable reuse window. `pthread_kill(3)` is
  therefore the recommended surface, per tgkill.2's "meant for internal thread library use".
- **Signal disposition is still process-wide**: `tgkill` chooses the *target*; the *action*
  (handler/default/ignore) is the process disposition, and if the signal is blocked in the
  target thread it queues as thread-directed pending (per signal(7) thread-directed rules).
- **Synchronous faults cannot be redirected**: you cannot meaningfully `tgkill` a hardware
  exception to another thread — the kernel raised it where the fault happened.
- `tgkill` is on neither POSIX nor the async-signal-safe lists' *application* surface, but
  `pthread_kill(3)` *is* async-signal-safe (POSIX.1-2008 TC1, per signal-safety(7)) — making
  "handler pokes a specific worker thread" a legal pattern.

## Minimal example

```c
/* tgkill-demo.c — direct a SIGUSR1 at one worker thread.
 * Expected: "worker: got SIGUSR1" printed by the worker (not main),
 * then "worker exiting".
 */
#define _GNU_SOURCE
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

static void handler(int sig) { (void)sig; printf("worker: got SIGUSR1\n"); }

static void *worker(void *arg) {
    (void)arg;
    sigset_t opt_in;
    sigemptyset(&opt_in);
    sigaddset(&opt_in, SIGUSR1);
    pthread_sigmask(SIG_UNBLOCK, &opt_in, NULL); /* worker opts in (it inherited
                                                    the blocked mask) */
    pause();                       /* sleeps until the directed signal arrives */
    printf("worker exiting\n");
    return NULL;
}

int main(void) {
    struct sigaction sa = { .sa_handler = handler };
    sigemptyset(&sa.sa_mask);
    sigaction(SIGUSR1, &sa, NULL);

    sigset_t block;
    sigemptyset(&block);
    sigaddset(&block, SIGUSR1);
    pthread_sigmask(SIG_BLOCK, &block, NULL);  /* main must not steal the signal;
                                                  the worker inherits this mask */
    pthread_t worker_tid;
    pthread_create(&worker_tid, NULL, worker, NULL);

    sleep(1);                                  /* let worker opt in */
    pthread_kill(worker_tid, SIGUSR1);         /* => tgkill(getpid(), tid, SIGUSR1) */
    pthread_join(worker_tid, NULL);
    return 0;
}
```

For the fully synchronous variant — worker stays blocked and `sigwait(3)`s the signal — see
[signal-masks](./signal-masks.md); that form has no handler and no interruption at all.

## Related Topics

- [kill, raise, and the kill utility](./kill-raise.md) — `raise(3)` sits on this call
- [Signal masks](./signal-masks.md) — thread-directed pending vs process-directed
- [signalfd and pidfd](./signalfd-pidfd.md) — `PIDFD_THREAD` + `pidfd_send_signal(2)` as the modern race-free alternative
- [Standard signals](../signals/standard-signals.md) — delivery-to-arbitrary-thread rule
- Per-syscall page: [tgkill(2)](../../syscalls/signals-time/tgkill.md); glibc rows [GLIBC-tgkill](../../libc/ledger-glibc.md), [GLIBC-pthread_kill](../../libc/ledger-glibc.md)

## References

- *tkill(2) / tgkill(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/tgkill.2.html>
- *signal(7)*, <https://man7.org/linux/man-pages/man7/signal.7.html> (thread-directed signals; tgkill implements pthread_kill)
- *signal-safety(7)*, <https://man7.org/linux/man-pages/man7/signal-safety.7.html> (pthread_kill on the safe list)
- *glibc source*, `nptl/pthread_kill.c`, `sysdeps/posix/raise.c` (verified via the bminor read-only mirror of sourceware git), <https://github.com/bminor/glibc/blob/master/nptl/pthread_kill.c>
