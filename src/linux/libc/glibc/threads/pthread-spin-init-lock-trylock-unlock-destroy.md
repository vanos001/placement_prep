# `pthread_spin_init` / `pthread_spin_lock` / `pthread_spin_trylock` / `pthread_spin_unlock` / `pthread_spin_destroy` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` (declared under `__USE_XOPEN2K`) |
| Standards | POSIX.1-2001 (`pthread_spin_init(3)`, `pthread_spin_lock(3)`); feature test `_POSIX_C_SOURCE >= 200112L` |
| Exported | all five `@@GLIBC_2.34` plus compat `@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety notes, *POSIX Spin Locks* node; man pages carry no ATTRIBUTES table for the lockers) |
| Ledger ID | GLIBC-pthread_spin_init, GLIBC-pthread_spin_lock, GLIBC-pthread_spin_trylock, GLIBC-pthread_spin_unlock, GLIBC-pthread_spin_destroy |

## Declaration and gates

```c
#include <pthread.h>

int pthread_spin_init(pthread_spinlock_t *lock, int pshared);     /* :1230 */
int pthread_spin_destroy(pthread_spinlock_t *lock);               /* :1234 */
int pthread_spin_lock(pthread_spinlock_t *lock);                  /* :1238 */
int pthread_spin_trylock(pthread_spinlock_t *lock);               /* :1242 */
int pthread_spin_unlock(pthread_spinlock_t *lock);                /* :1246 */
```

All five sit in the `#ifdef __USE_XOPEN2K` block of
`/usr/include/pthread.h` (lines 1225-1248). `pshared` is
`PTHREAD_PROCESS_PRIVATE` or `PTHREAD_PROCESS_SHARED`
(`pthread.h:145-150`, unconditional enum).

## Semantics

`pthread_spin_init` prepares an unlocked spinlock; process-private is
the default choice, process-shared locks may live in shared memory and
are a POSIX option glibc supports (`pthread_spin_init(3)`).
`pthread_spin_lock` spins testing the word until it can acquire the
lock; `pthread_spin_trylock` returns `EBUSY` immediately instead;
`pthread_spin_unlock` releases it and one waiting spinner acquires it.
Locking a lock the caller already holds, unlocking a lock the caller
does not hold, initializing twice, destroying a held or never
initialized lock, and operating on copies of the object are all
undefined behavior (`pthread_spin_init(3)`, `pthread_spin_lock(3)`).

## Gotchas and portability

- Spin locks pay off only under real-time scheduling (`SCHED_FIFO`,
  possibly `SCHED_RR`); under `SCHED_OTHER` a preempted holder makes
  peers burn CPU, and a deadlocked pair spins forever. The man pages
  call non-RT use "probably a design mistake".
- The POSIX counterparts with blocking are the mutex family
  ([mutex page](../process/pthread-mutex-init-lock-unlock-trylock-timedlock-destroy-mutexattr.md)).
- musl 1.2.5: all five `.c` files present under `musl src/thread/`.

## Errors

- `EBUSY` (`trylock`): lock held by another thread. `EDEADLOCK`
  (`lock`): deadlock detected -- not detected by glibc
  (`pthread_spin_lock(3)`).
- `EAGAIN`/`ENOMEM` (`init`): documented by POSIX but the man page notes
  they do not occur in the glibc implementation.

## References

- man3: `pthread_spin_init(3)`, `pthread_spin_lock(3)`
  (`source-cache/man-pages-sparse/man3/`)
- glibc manual: `threads.texi`, node *POSIX Spin Locks*
- header: `/usr/include/pthread.h` lines 1225-1248
- symbols: `nm -D --with-symbol-versions libc.so.6`
