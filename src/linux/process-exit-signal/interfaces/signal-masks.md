# Signal Masks and Pending Signals — sigprocmask, pthread_sigmask, sigpending (IF-005 – IF-007)

Blocking turns a signal from "interrupts you now" into "sits in the pending set until
unblocked". This chapter covers the three mask/pending interfaces: `sigprocmask(2)`
(IF-005), `pthread_sigmask(3)` (IF-006), and `sigpending(2)` (IF-007) — and the
thread-vs-process pending semantics that make multithreaded signal code subtle. The delivery
rules they implement are in [Standard signals](../signals/standard-signals.md).

## sigprocmask(2) (IF-005)

```c
#include <signal.h>              /* _POSIX_C_SOURCE */
int sigprocmask(int how, const sigset_t *_Nullable restrict set,
                sigset_t *_Nullable restrict oldset);
```

**Category**: libc wrapper around `rt_sigprocmask(2)` (kernel syscall since Linux 2.2; see
[rt-sig-syscalls](./rt-sig-syscalls.md) and
[rt_sigprocmask(2)](../../syscalls/signals-time/rt_sigprocmask.md)). POSIX.1 (per
[sigprocmask(2)](https://man7.org/linux/man-pages/man2/sigprocmask.2.html)).

The `how` values (per sigprocmask(2)):

| `how` | Effect |
|-------|--------|
| `SIG_BLOCK` | new mask = union(current, `set`) |
| `SIG_UNBLOCK` | remove `set` from the mask (unblocking a non-blocked signal is allowed) |
| `SIG_SETMASK` | new mask = `set` |

`set == NULL` means "leave the mask, just fetch it into `oldset`"; both NULL is legal but
pointless. Return `0`/`-1`; errors `EFAULT`, `EINVAL` (bad `how`).

**Notes that matter** (per sigprocmask(2)):

- `SIGKILL` and `SIGSTOP` cannot be blocked; attempts are **silently ignored**.
- The signal mask is **per thread**. `sigprocmask()`'s use in a *multithreaded* process is
  **unspecified** by POSIX — in practice glibc applies it to the calling thread only, but
  portable code uses `pthread_sigmask(3)` there.
- `fork(2)` copies the mask; the mask survives `execve(2)` (so a blocked signal you forget to
  unblock poisons the execed program).
- If `SIGBUS`, `SIGFPE`, `SIGILL`, or `SIGSEGV` are generated *while blocked*, the behavior is
  undefined unless they came from `kill(2)`/`sigqueue(3)`/`raise(3)` — a synchronous fault
  cannot be deferred.
- glibc's wrapper **silently ignores** attempts to block the two NPTL-internal real-time
  signals (per sigprocmask(2) VERSIONS; see
  [Real-time signals](../signals/real-time-signals.md)).
- Kernel-ABI note: the *kernel's* `how` constants are not the POSIX numbers on all
  architectures (asm-generic 0/1/2, alpha & mips 1/2/3, sparc 1/2/4 — verified in the UAPI
  headers); the glibc wrapper maps your POSIX constants. Never use raw `rt_sigprocmask(2)`
  values in application code — details in [rt-sig-syscalls](./rt-sig-syscalls.md).

Sets are manipulated with `sigemptyset(3)`, `sigfillset(3)`, `sigaddset(3)`, `sigdelset(3)`,
`sigismember(3)` (see `sigsetops(3)`).

## pthread_sigmask(3) (IF-006)

```c
#include <signal.h>     /* _POSIX_C_SOURCE >= 199506L || _XOPEN_SOURCE >= 500 */
int pthread_sigmask(int how, const sigset_t *set, sigset_t *oldset);
```

**Category**: POSIX threads function; on glibc today it is in libc (historically libpthread),
a thin wrapper over the same `rt_sigprocmask(2)` syscall (per
[pthread_sigmask(3)](https://man7.org/linux/man-pages/man3/pthread_sigmask.3.html)).

Differences from `sigprocmask(2)` (per pthread_sigmask(3)):

- Its use in multithreaded programs **is** explicitly specified by POSIX — it always operates
  on the calling thread's mask.
- **Return convention is pthread-style**: `0` on success, otherwise an *error number*
  (not `-1` with `errno`).
- Same silent ignoring of `SIGKILL`/`SIGSTOP` and of the NPTL-internal RT signals.
- A **new thread inherits a copy of its creator's mask** — this inheritance is the foundation
  of the "block early, then spawn" pattern below. MT-Safe.

Thread-safety and race posture: the mask change itself is atomic with respect to signal
delivery for the calling thread, but the *window* between installing a mask and the next
action is where process-directed signals get delivered to whichever thread is unblocked —
hence the discipline: block in all threads (inheritance or explicit loop), keep handlers'
dispositions process-wide, and consume deliberately.

## sigpending(2) (IF-007)

```c
#include <signal.h>
int sigpending(sigset_t *set);
```

**Category**: libc wrapper around `rt_sigpending(2)` (kernel ≥ 2.2 with `sigsetsize`
argument; glibc hides it) (per
[sigpending(2)](https://man7.org/linux/man-pages/man2/sigpending.2.html)).

Per sigpending(2) NOTES: the set returned to a thread is **the union of the thread-directed
pending signals and the process-directed pending signals** — the same set the kernel would
consider for delivery to that thread, filtered by nothing else. Two properties worth quoting:

- A signal that is blocked *and* has disposition `SIG_IGN` never enters the pending set.
- After `fork(2)` the child's pending set is **empty**; the pending set survives `execve(2)`.

The same data is externally visible in `/proc/<pid>/status` (`SigPnd` = thread-directed of the
main thread, `ShdPnd` = process-directed) and `/proc/<pid>/task/<tid>/status` per thread (per
signal(7) NOTES). glibc ≤ 2.2.1 had a wrapper bug not reporting pending RT signals (per
sigpending(2) BUGS, historical).

## Thread-local vs process-directed pending — the multithreaded picture

Per signal(7):

- Disposition is per-process; mask and thread-directed pending are per-thread.
- A process-directed signal is delivered to **any one** thread that does not block it —
  kernel's choice among eligible threads is arbitrary.
- A thread-directed signal (hardware exception, `tgkill`/`pthread_kill`) is pending for that
  thread only.
- `sigpending(2)` reports the union view described above.

Practical consequence: in a multithreaded program, "unblock in one thread" only *narrows* who
can receive a process-directed signal; it does not target it. To *target*, block everywhere
and consume synchronously ([sigwait family](./sigwait-sigsuspend.md)) or use
`pthread_kill(3)`/`tgkill(2)` ([tgkill](./tgkill.md)).

## Examples

Block-unblock around a critical section, single-threaded idiom:

```c
/* critical.c — protect a region from SIGINT/SIGTERM */
#include <signal.h>

void critical_region(void) {
    sigset_t block, old;
    sigemptyset(&block);
    sigaddset(&block, SIGINT);
    sigaddset(&block, SIGTERM);
    sigprocmask(SIG_BLOCK, &block, &old);   /* atomic mask update */
    /* ... code that must not be interrupted ... */
    sigprocmask(SIG_SETMASK, &old, NULL);   /* restore; pending signals now deliver */
}
```

Multithreaded: dedicate one thread to signals (from pthread_sigmask(3)'s documented example,
condensed):

```c
/* sigthread.c — block early, then let one thread sigwait() them.
 * Expected: "Signal handling thread got signal 3" for kill -QUIT <pid>,
 *           "got signal 10" for kill -USR1 <pid>.
 */
#include <pthread.h>
#include <signal.h>
#include <stdio.h>

static void *sig_thread(void *arg) {
    sigset_t *set = arg;
    int sig;
    for (;;) {
        sigwait(set, &sig);                       /* consumes the signal */
        printf("Signal handling thread got signal %d\n", sig);
    }
}

int main(void) {
    sigset_t set;
    sigemptyset(&set);
    sigaddset(&set, SIGQUIT);
    sigaddset(&set, SIGUSR1);
    pthread_sigmask(SIG_BLOCK, &set, NULL);       /* 1) block in main */
    pthread_t t;
    pthread_create(&t, NULL, sig_thread, &set);   /* 2) inherits the mask */
    pause();                                      /* main keeps working */
    return 0;
}
```

Inspect pending signals:

```c
sigset_t pend;
sigpending(&pend);
if (sigismember(&pend, SIGUSR1)) { /* SIGUSR1 waiting for this thread's view */ }
```

## Related Topics

- [Sigwait and sigsuspend](./sigwait-sigsuspend.md) — consume blocked signals deliberately
- [sigaction and signal](./sigaction-signal.md) — `sa_mask` is the handler-scoped mask
- [Standard signals](../signals/standard-signals.md) — pending-set semantics, no queueing
- [rt_sigprocmask(2) kernel ABI](./rt-sig-syscalls.md) and [per-syscall page](../../syscalls/signals-time/rt_sigprocmask.md)
- [glibc ledger rows](../../libc/ledger-glibc.md) — `sigprocmask`, `pthread_sigmask`, `sigpending`

## References

- *sigprocmask(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigprocmask.2.html>
- *pthread_sigmask(3)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man3/pthread_sigmask.3.html>
- *sigpending(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigpending.2.html>
- *sigprocmask*, *pthread_sigmask*, *sigpending*, POSIX.1-2017, <https://pubs.opengroup.org/onlinepubs/9699919799/functions/sigprocmask.html>, <https://pubs.opengroup.org/onlinepubs/9699919799/functions/pthread_sigmask.html>, <https://pubs.opengroup.org/onlinepubs/9699919799/functions/sigpending.html>
- *signal(7)*, <https://man7.org/linux/man-pages/man7/signal.7.html> ("Signal mask and pending signals")
