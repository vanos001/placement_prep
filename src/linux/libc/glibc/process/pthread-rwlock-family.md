# `pthread_rwlock_*` (read-write lock family) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_rwlock_init, -destroy, -rdlock, -wrlock, -tryrdlock, -trywrlock, -unlock, -timedrdlock, -timedwrlock, -clockrdlock, -clockwrlock, -rwlockattr_init, -destroy, -setkind_np, -getkind_np, -setpshared, -getpshared |
| Header | `pthread.h` (declared under `__USE_UNIX98 || __USE_XOPEN2K`) |
| Provenance | POSIX.1b/UNIX98; `clockrdlock`/`clockwrlock` POSIX.1-2024 per manual, glibc 2.30 (nm compat symbol); `setkind_np` GNU, glibc 2.1 |
| Exported | lock/attr calls default `@@GLIBC_2.34` with compat `@GLIBC_2.2.5`; `clockrdlock`/`clockwrlock` compat `@GLIBC_2.30` (nm) |
| Thread-safety | MT-Safe (manual safety notes for the clock variants) |
| Wraps | futex-based state machine in libc |
| Status | documented |

**Semantics** -- many readers or one writer; `rdlock`/`wrlock` block,
`tryrdlock`/`trywrlock` fail with `EBUSY` when held (musl
`pthread_rwlock_tryrdlock.c`), `unlock` releases, `timedrdlock`/
`timedwrlock` bound the wait by an absolute `CLOCK_REALTIME` `abstime`,
and `clockrdlock`/`clockwrlock` take an explicit clockid (`EINVAL` unless
`CLOCK_MONOTONIC` or `CLOCK_REALTIME`) (manual *Waiting with Explicit
Clocks*).

**Lock kinds** (`pthread_rwlockattr_setkind_np`) -- `PTHREAD_RWLOCK_PREFER_READER_NP`
is the default: read locks are recursive and a reader is granted even while
writers wait, so writers starve as long as readers keep coming.
`PTHREAD_RWLOCK_PREFER_WRITER_NP` is ignored by glibc: recursive read locks
plus writer preference would deadlock trivially; use
`PTHREAD_RWLOCK_PREFER_WRITER_NONRECURSIVE_NP`, which avoids writer
starvation provided no recursive read locking. `PTHREAD_RWLOCK_DEFAULT_NP`
aliases the reader kind (pthread_rwlockattr_setkind_np.3; values in
`pthread.h`).

**Gotchas and portability** -- `setkind_np` is a glibc extension; musl
exports no kind attribute (`include/pthread.h`). No man3 page for
`pthread_rwlock_rdlock` exists in the cached man-pages tree, so error
lists beyond `EBUSY`/`EINVAL`/`ETIMEDOUT` are not asserted here
(unverified).

**References** -- `pthread_rwlockattr_setkind_np(3)`; manual *Waiting with
Explicit Clocks* node; musl `src/thread/pthread_rwlock_*.c`.
