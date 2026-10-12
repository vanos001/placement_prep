# `pthread_rwlock_clockrdlock` / `pthread_rwlock_clockwrlock` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` (rwlock block, `__USE_GNU` nested in `__USE_UNIX98 || __USE_XOPEN2K`) |
| Standards | POSIX.1-2024 (manual standards note, *Waiting with Explicit Clocks* node; no separate man3 page in the cached man-pages set) |
| Exported | `pthread_rwlock_clockrdlock@@GLIBC_2.34` plus compat `@GLIBC_2.30`; `pthread_rwlock_clockwrlock@@GLIBC_2.34` plus compat `@GLIBC_2.30` (nm, host glibc 2.41); 64-bit-time redirects `__pthread_rwlock_clock{rd,wr}lock64` |
| Thread-safety | MT-Safe (manual safety notes: `@asulock`, `@aculock`) |
| Ledger ID | GLIBC-pthread_rwlock_clockrdlock, GLIBC-pthread_rwlock_clockwrlock |

## Declaration and gates

```c
#include <pthread.h>

int pthread_rwlock_clockrdlock(pthread_rwlock_t *restrict rwlock,
                               clockid_t clockid,
                               const struct timespec *restrict abstime);
                                                         /* :1004 */
int pthread_rwlock_clockwrlock(pthread_rwlock_t *restrict rwlock,
                               clockid_t clockid,
                               const struct timespec *restrict abstime);
                                                         /* :1051 */
```

Both are guarded by `#ifdef __USE_GNU` inside the rwlock block opened by
`#if defined __USE_UNIX98 || defined __USE_XOPEN2K`
(`/usr/include/pthread.h` line 961; clock variants at 1004-1020 and
1051-1067). The base rwlock family is covered in
[pthread-rwlock-family](../process/pthread-rwlock-family.md).

## Semantics

Both behave like `pthread_rwlock_timedrdlock` /
`pthread_rwlock_timedwrlock` except that the absolute timeout `abstime`
is measured against the clock named by `clockid` instead of the
`CLOCK_REALTIME` default of the timed variants (manual, *Waiting with
Explicit Clocks*). Currently `clockid` must be `CLOCK_MONOTONIC` or
`CLOCK_REALTIME`, and any other value makes the call fail with `EINVAL`
(manual, both entries). Everything else -- reader/writer acquisition
rules, blocking -- is the timed rwlock behavior the manual references.

## Gotchas and portability

- The motivating use is timeout arithmetic: measure deadlines against
  `CLOCK_MONOTONIC` so real-time clock adjustments cannot shrink or
  stretch a wait.
- Adopted by POSIX.1-2024 like the other explicit-clock waits
  (`pthread_cond_clockwait`, `sem_clockwait`), but glibc still gates the
  prototypes behind `_GNU_SOURCE`.
- musl 1.2.5: absent -- `musl src/thread/` has the plain and timed
  rwlock calls only, no `*clock*` variants.

## Errors

- `EINVAL`: `clockid` is neither `CLOCK_MONOTONIC` nor
  `CLOCK_REALTIME` (manual, *Waiting with Explicit Clocks*). Errors of
  the underlying timed acquisition are not enumerated on the clock
  variants in the cached manual.

## References

- glibc manual: `threads.texi`, node *Waiting with Explicit Clocks*
- header: `/usr/include/pthread.h` lines 961, 1004-1020, 1051-1067
- symbols: `nm -D --with-symbol-versions libc.so.6`
