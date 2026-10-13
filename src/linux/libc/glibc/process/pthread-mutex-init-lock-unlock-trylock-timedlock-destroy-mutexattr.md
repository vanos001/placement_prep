# `pthread_mutex_*` (init, lock, unlock, trylock, timedlock, destroy + mutexattr) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_mutex_init, -destroy, -lock, -unlock, -trylock, -timedlock, -clocklock, -mutexattr_init, -destroy, -gettype, -settype |
| Header | `pthread.h` |
| Provenance | POSIX.1; `clocklock` adopted by POSIX.1-2024 (glibc 2.30) |
| Wraps | futexes; `PTHREAD_MUTEX_*` encoded in the `pthread_mutex_t` itself |
| Status | documented |

**Semantics** -- lock/unlock discipline with static initializers
(`PTHREAD_MUTEX_INITIALIZER`, `..._RECURSIVE_INITIALIZER_NP`,
`..._ERRORCHECK_INITIALIZER_NP`) or `pthread_mutex_init` with an
attribute object. Mutex **kinds** via `pthread_mutexattr_settype`:
`PTHREAD_MUTEX_NORMAL` (relock/unlock-by-non-owner = undefined behavior),
`PTHREAD_MUTEX_ERRORCHECK` (relock -> `EDEADLK`, wrong-owner unlock ->
`EPERM`), `PTHREAD_MUTEX_RECURSIVE` (relock counts, needs matching
unlocks), `PTHREAD_MUTEX_DEFAULT` -- which on glibc is *aliases*
`PTHREAD_MUTEX_NORMAL` (verified in `pthread.h`), so "default" gives no
error checking.

**Return and errors** -- 0 or error number. `lock`: `EAGAIN` (too many
recursive locks), `EDEADLK` (error-check: caller owns it), `EINVAL`,
plus robust-mutex states `EOWNERDEAD`/`ENOTRECOVERABLE`.
`trylock`: `EBUSY` when held. `unlock`: `EPERM` when not owner.
`timedlock`/`clocklock`: `ETIMEDOUT` (abstime already past and lock
unavailable = immediate timeout), `EDEADLK`, `EOWNERDEAD`,
`ENOTRECOVERABLE`; `clocklock` accepts `CLOCK_MONOTONIC`/`REALTIME`
explicitly instead of the condattr-style clock default.

**glibc layer** -- locking is futex-based: uncontended lock/unlock is a
userspace atomic with zero syscalls (that is why mutex traces are quiet
until contention). POSIX mutex protocols (`PRIO_INHERIT` etc.) and
robust lists ride on `set_robust_list(2)`/futex flags -- kernel view in
[process.md](../../../syscalls/process/overview.md).

**References** -- glibc manual *POSIX Mutexes*; `pthread_mutexattr_*`
man pages.
