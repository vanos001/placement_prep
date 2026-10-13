# `cnd_init` / `cnd_signal` / `cnd_broadcast` / `cnd_wait` / `cnd_timedwait` / `cnd_destroy` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `threads.h` |
| Standards | C11 section 7.26 (ISO C threads) |
| Exported | all six `@@GLIBC_2.34` plus compat `@GLIBC_2.28` (nm, host glibc 2.41); `cnd_timedwait` has a `__cnd_timedwait64` time64 redirect |
| Thread-safety | MT-Safe (manual safety notes, *ISO C Condition Variables* node) |
| Ledger ID | GLIBC-cnd_init, GLIBC-cnd_signal, GLIBC-cnd_broadcast, GLIBC-cnd_wait, GLIBC-cnd_timedwait, GLIBC-cnd_destroy |

## Declaration and gates

```c
#include <threads.h>

int  cnd_init(cnd_t *cond);                                   /* threads.h:181 */
int  cnd_signal(cnd_t *cond);                                 /* threads.h:185 */
int  cnd_broadcast(cnd_t *cond);                              /* threads.h:189 */
int  cnd_wait(cnd_t *cond, mtx_t *mutex);                     /* threads.h:192 */
int  cnd_timedwait(cnd_t *restrict cond, mtx_t *restrict mutex,
                   const struct timespec *restrict time_point);
                                                              /* threads.h:198 */
void cnd_destroy(cnd_t *cond);                                /* threads.h:215 */
```

No feature-test gate; the only conditional piece is the 64-bit-time
redirect of `cnd_timedwait` to `__cnd_timedwait64`
(`threads.h:203-209`).

## Semantics

`cnd_init` creates a condition variable identified by `*cond` and may
return `thrd_success`, `thrd_nomem` or `thrd_error`. `cnd_signal` unblocks
one waiting thread, `cnd_broadcast` all of them; with no waiters both do
nothing and still return `thrd_success` (manual, *ISO C Condition
Variables*). `cnd_wait` atomically unlocks `mutex`, blocks until
signaled, then locks the mutex again before returning. `cnd_timedwait`
does the same but also returns when the calendar time `*time_point` is
reached -- an absolute time, so a duration must be computed by the caller.
`cnd_destroy` releases the variable; waiting threads at destroy time are
undefined behavior, as is `cnd_wait` without the mutex held.

## Gotchas and portability

- Spurious wakeups are part of the model: recheck the predicate in a loop
  and keep it in the same mutex used for `cnd_wait`.
- C11 offers no clock choice for `cnd_timedwait`; the clock-selecting
  variants live on the POSIX side
  ([pthread_cond_clockwait](../process/pthread-cond-init-wait-signal-broadcast-timedwait-condattr.md)).
- musl 1.2.5: one `.c` file per function (`musl src/thread/cnd_*.c`),
  same return-code contract.

## References

- glibc manual: `threads.texi`, nodes *ISO C Condition Variables*,
  *ISO C Threads Return Values*
- header: `/usr/include/threads.h` lines 181-215
- symbols: `nm -D --with-symbol-versions libc.so.6`
