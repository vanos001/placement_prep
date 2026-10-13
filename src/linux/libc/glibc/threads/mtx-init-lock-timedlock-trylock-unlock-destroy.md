# `mtx_init` / `mtx_lock` / `mtx_timedlock` / `mtx_trylock` / `mtx_unlock` / `mtx_destroy` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `threads.h` |
| Standards | C11 section 7.26 (ISO C threads) |
| Exported | all six `@@GLIBC_2.34` plus compat `@GLIBC_2.28` (nm, host glibc 2.41); `mtx_timedlock` has a `__mtx_timedlock64` time64 redirect |
| Thread-safety | MT-Safe (manual safety notes; lockers are `@asulock`/`@aculock`) |
| Ledger ID | GLIBC-mtx_init, GLIBC-mtx_lock, GLIBC-mtx_timedlock, GLIBC-mtx_trylock, GLIBC-mtx_unlock, GLIBC-mtx_destroy |

## Declaration and gates

```c
#include <threads.h>

int  mtx_init(mtx_t *mutex, int type);            /* threads.h:137 */
int  mtx_lock(mtx_t *mutex);                      /* threads.h:141 */
int  mtx_timedlock(mtx_t *restrict mutex,
                   const struct timespec *restrict time_point);
                                                  /* threads.h:147 */
int  mtx_trylock(mtx_t *mutex);                   /* threads.h:163 */
int  mtx_unlock(mtx_t *mutex);                    /* threads.h:167 */
void mtx_destroy(mtx_t *mutex);                   /* threads.h:170 */
```

No feature-test gate; `mtx_timedwait`-style time64 redirect only
(`threads.h:151-156`). Types come from the `mtx_plain` / `mtx_recursive` /
`mtx_timed` enum (`threads.h:56-58`).

## Semantics

`mtx_init` creates the mutex; valid `type` values are `mtx_plain`,
`mtx_timed`, `mtx_plain | mtx_recursive` and `mtx_timed | mtx_recursive`;
only `thrd_success` or `thrd_error` is returned (manual, *ISO C Mutexes*).
`mtx_lock` blocks until acquired and is undefined on a non-recursive
mutex the caller already holds. `mtx_trylock` returns `thrd_busy`
instead of blocking. `mtx_timedlock` waits until the absolute calendar
time `*time_point`. `mtx_unlock` releases the mutex. Prior unlocks
synchronize-with successful lock operations, and all lock/unlock
operations on one mutex form a single total order. `mtx_destroy` with
waiters is undefined behavior. None of these set `errno`; failures are
reported as `thrd_error` (trylock: `thrd_busy`).

## Gotchas and portability

- `mtx_timedlock` on a mutex not created with `mtx_timed` is undefined
  behavior, unlike the POSIX errno contract.
- The POSIX counterparts (including `PTHREAD_MUTEX_RECURSIVE` attribute
  objects) are covered in
  [the mutex family page](../process/pthread-mutex-init-lock-unlock-trylock-timedlock-destroy-mutexattr.md).
- musl 1.2.5: one `.c` file per function (`musl src/thread/mtx_*.c`),
  same type constants in `include/threads.h`.

## References

- glibc manual: `threads.texi`, node *ISO C Mutexes*
- header: `/usr/include/threads.h` lines 56-58, 137-170
- symbols: `nm -D --with-symbol-versions libc.so.6`
