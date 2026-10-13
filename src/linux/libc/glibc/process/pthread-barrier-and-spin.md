# `pthread_barrier_*` and `pthread_spin_*` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_barrier_init, -wait, -destroy, -barrierattr_init, -destroy, -setpshared, -getpshared; GLIBC-pthread_spin_init, -destroy, -lock, -trylock, -unlock |
| Header | `pthread.h` (both groups declared under `__USE_XOPEN2K`) |
| Provenance | POSIX.1-2001; spin and barrier calls glibc 2.2 (compat symbols), `barrierattr_getpshared` 2.3.3 |
| Exported | all default `@@GLIBC_2.34` with compat `@GLIBC_2.2.5`; `getpshared` compat `@GLIBC_2.3.3` (nm) |
| Thread-safety | MT-Safe (manual safety notes; man attributes for spin) |
| Wraps | futexes (barrier) and atomic compare-exchange loops (spin) in libc |
| Status | documented |

**Barriers** -- `init(barrier, attr, count)` arms a barrier for `count`
threads (`EINVAL` when count is zero or overflows an internal counter);
the first `count-1` callers of `wait` sleep, and the count-th releases all.
Exactly one caller per batch gets `PTHREAD_BARRIER_SERIAL_THREAD` (-1),
the rest get 0; the barrier re-arms. Destroying while threads wait is
forbidden, and it must be destroyed before re-initialization (manual
*POSIX Barriers*). Process sharing rides on `barrierattr_setpshared`;
the manual defers pshared details ("documentation TBD").

**Spin locks** -- `init(lock, pshared)` with `PTHREAD_PROCESS_PRIVATE` or
`PTHREAD_PROCESS_SHARED`; `lock` spins testing the word until it can
acquire, `trylock` returns `EBUSY` immediately, `unlock` wakes one
spinner. Locking a lock the caller already holds, or any use of an
uninitialized lock, is undefined behavior (pthread_spin_*.3).
`EAGAIN`/`ENOMEM` for init are documented by POSIX but do not occur on
glibc (man comment); `EDEADLOCK` is not detected by glibc.

**Gotchas and portability** -- spin locks pay off only under real-time
scheduling (`SCHED_FIFO`/`SCHED_RR`); under `SCHED_OTHER` a preempted
holder makes peers burn CPU, and a deadlock spins forever (man NOTES).
musl's `pthread_spin_lock.c` is a bare CAS-plus-`a_spin` loop.

**References** -- manual *POSIX Barriers* and *POSIX Spin Locks* nodes;
`pthread_spin_init(3)`; musl `src/thread/pthread_barrier_wait.c`.
