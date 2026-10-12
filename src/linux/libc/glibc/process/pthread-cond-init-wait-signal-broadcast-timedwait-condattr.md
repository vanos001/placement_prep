# `pthread_cond_*` (init, wait, signal, broadcast, timedwait + condattr) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_cond_init, -destroy, -wait, -signal, -broadcast, -timedwait, -clockwait, -condattr_init, -destroy, -getclock, -setclock, -getpshared, -setpshared |
| Header | `pthread.h` |
| Provenance | POSIX.1; `clockwait` glibc 2.30 (POSIX.1-2024); cond_wait/signal symbol version GLIBC_2.3.2 |
| Wraps | futex requeue/wake; no syscall while uncontended |
| Status | documented |

**Semantics** -- condition variables pair a wait queue with a caller
supplied mutex. `pthread_cond_wait(cond, mutex)` **atomically** unlocks
the mutex and blocks; on return the mutex is re-locked -- this atomicity
is the whole point (no lost-wakeup window between unlock and sleep).
`pthread_cond_signal` wakes at least one waiter, `pthread_cond_broadcast`
wakes all; both are no-ops (still success) with no waiters. The
contract is shared with the ISO C twins documented in the manual
(`cnd_wait`: "atomically unlocks the mutex ... blocks ... The mutex is
locked again before the function returns").

**The loop discipline** -- because POSIX permits *spurious wakeups* and
because another thread can steal the predicate between wakeup and
re-lock, waiting code must recheck the condition in a `while` loop; the
glibc `pthread_cond_clockwait` safety annotation additionally documents
the sharp edge that a signal handler interrupting between the internal
unlock and the sleep can double-unlock the mutex -- handlers must not
touch the same cond/mutex pair.

**Timed forms** -- `pthread_cond_timedwait` measures `abstime` against
the clock chosen by `pthread_condattr_setclock` (default
`CLOCK_REALTIME`); `pthread_cond_clockwait` (2.30) takes the clockid
explicitly (`CLOCK_MONOTONIC`/`CLOCK_REALTIME`), which is how you wait
without `CLOCK_REALTIME` jumps. `PTHREAD_COND_INITIALIZER` covers
statics.

**References** -- glibc manual *ISO C Condition Variables*, *Waiting
with Explicit Clocks*; `pthread_condattr(3)` family.
