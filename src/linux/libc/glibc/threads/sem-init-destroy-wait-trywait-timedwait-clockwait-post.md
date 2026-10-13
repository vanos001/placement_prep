# `sem_init` / `sem_destroy` / `sem_wait` / `sem_trywait` / `sem_timedwait` / `sem_clockwait` / `sem_post` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `semaphore.h` |
| Standards | POSIX.1-2001, POSIX.1-2008 (`sem_wait(3)`, `sem_init(3)`, `sem_post(3)`); `sem_clockwait` POSIX.1-2024 (manual) |
| Exported | all seven `@@GLIBC_2.34`; the six POSIX.1-2001 functions plus compat `@GLIBC_2.2.5`, `sem_clockwait` plus compat `@GLIBC_2.30` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (ATTRIBUTES of `sem_wait(3)`, `sem_init(3)`, `sem_post(3)`, `sem_destroy(3)`) |
| Ledger ID | GLIBC-sem_init, GLIBC-sem_destroy, GLIBC-sem_wait, GLIBC-sem_trywait, GLIBC-sem_timedwait, GLIBC-sem_clockwait, GLIBC-sem_post |

## Declaration and gates

```c
#include <semaphore.h>

int sem_init(sem_t *sem, int pshared, unsigned int value);    /* :35 */
int sem_destroy(sem_t *sem);                                  /* :39 */
int sem_wait(sem_t *sem);                                     /* :55 */
int sem_trywait(sem_t *sem);                                  /* :100 */
int sem_post(sem_t *sem);                                     /* :103 */
int sem_getvalue(sem_t *restrict sem, int *restrict sval);    /* :106 */

#ifdef __USE_XOPEN2K
int sem_timedwait(sem_t *restrict sem,
                  const struct timespec *restrict abstime);   /* :63 */
#endif
#ifdef __USE_GNU
int sem_clockwait(sem_t *restrict sem, clockid_t clock,
                  const struct timespec *restrict abstime);   /* :81 */
#endif
```

`sem_timedwait` needs `_POSIX_C_SOURCE >= 200112L`, `sem_clockwait`
needs `_GNU_SOURCE`; all others are unconditional
(`/usr/include/semaphore.h` lines 35-107). Named-semaphore calls are in
[sem-open-close-unlink-getvalue](sem-open-close-unlink-getvalue.md).

## Semantics

`sem_init` initializes the unnamed semaphore at `*sem` to `value`;
`pshared == 0` makes it shared between the threads of a process,
nonzero makes it process-shared and requires placement in shared
memory (`sem_init(3)`). `sem_wait` decrements the semaphore, blocking
while it is zero; `sem_trywait` returns `EAGAIN` instead of blocking;
`sem_timedwait` adds an absolute `CLOCK_REALTIME` deadline -- if the
decrement can happen immediately it never times out, and `abstime` is
not validated in that case (`sem_wait(3)`). `sem_clockwait` measures
`abstime` against the given `clockid`, currently restricted to
`CLOCK_MONOTONIC` or `CLOCK_REALTIME` (manual, *POSIX Semaphores*).
`sem_post` increments and wakes one blocked waiter. `sem_destroy`
tears down an unnamed semaphore; destroying one with waiters is
undefined behavior.

## Cancellation points

The header marks exactly two of this group:
`sem_wait` and `sem_timedwait` are cancellation points
(`/usr/include/semaphore.h` comments at lines 52-54 and 59-61); the
other five carry no such marking.

## Gotchas and portability

- The manual's safety notes record that glibc's `sem_destroy` does
  nothing (`threads.texi` comment on the *POSIX Semaphores* node).
- musl 1.2.5: all live in `musl src/thread/` (no `src/semaphore/`
  dir); `sem_clockwait` is absent from `musl include/semaphore.h`.

## Errors

- `sem_wait`/`sem_trywait`/`sem_timedwait`: `EAGAIN` (trywait only),
  `EINTR`, `EINVAL` (invalid `sem` or bad `tv_nsec`), `ETIMEDOUT`
  (timedwait only) (`sem_wait(3)`).
- `sem_init`: `EINVAL` (`value` > `SEM_VALUE_MAX`), `ENOSYS`
  (process-shared semaphores unsupported) (`sem_init(3)`).
- `sem_post`: `EINVAL`, `EOVERFLOW` (maximum value would be exceeded)
  (`sem_post(3)`). `sem_destroy`: `EINVAL` (`sem_destroy(3)`).

## References

- man3: `sem_wait(3)`, `sem_init(3)`, `sem_destroy(3)`, `sem_post(3)`
  (`source-cache/man-pages-sparse/man3/`); no cached man page for
  `sem_clockwait`, cited from the manual
- glibc manual: `threads.texi`, node *POSIX Semaphores*
- header: `/usr/include/semaphore.h` lines 35-107
- symbols: `nm -D --with-symbol-versions libc.so.6`
