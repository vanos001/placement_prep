# `thrd_current` / `thrd_equal` / `thrd_sleep` / `thrd_yield` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `threads.h` |
| Standards | C11 section 7.26 (ISO C threads) |
| Exported | `thrd_current@@GLIBC_2.28`, `thrd_equal@@GLIBC_2.28`, `thrd_sleep@@GLIBC_2.28` (weak), `thrd_yield@@GLIBC_2.28` (nm, host glibc 2.41; no 2.34 version bump) |
| Thread-safety | MT-Safe (manual safety notes, *ISO C Thread Management* node) |
| Ledger ID | GLIBC-thrd_current, GLIBC-thrd_equal, GLIBC-thrd_sleep, GLIBC-thrd_yield |

## Declaration and gates

```c
#include <threads.h>

thrd_t thrd_current(void);                            /* threads.h:87 */
int    thrd_equal(thrd_t lhs, thrd_t rhs);            /* threads.h:84 */
int    thrd_sleep(const struct timespec *time_point,
                  struct timespec *remaining);        /* threads.h:94 */
void   thrd_yield(void);                              /* threads.h:121 */
```

No feature-test gate. With `__USE_EXTERN_INLINES` glibc also offers an
inline `thrd_equal` that is a plain pointer comparison
(`threads.h:124-130`); `thrd_sleep` redirects to `__thrd_sleep64`
under 64-bit time (`threads.h:98-102`).

## Semantics

`thrd_current` returns the calling thread's identifier. `thrd_equal`
compares two identifiers: non-zero when they refer to the same thread,
`0` otherwise (manual, *ISO C Thread Management*). `thrd_sleep` blocks
the current thread for at least the *duration* `*time_point` -- not an
absolute time -- and may wake early on a signal that is not ignored, in
which case the unused remainder is stored in `*remaining` when non-NULL.
It returns `0` if it slept for the requested duration, `-1` if
interrupted by a signal, and another negative number on failure
(manual). `thrd_yield` hints the scheduler to let other threads run; it
returns nothing and cannot fail observably.

## Gotchas and portability

- `thrd_sleep` takes a relative duration while POSIX `nanosleep`-style
  APIs in this encyclopedia take absolute or clock-selected arguments.
- No cached man page or manual node marks `thrd_sleep` as a
  cancellation point, so no such claim is made here.
- musl 1.2.5: `thrd_sleep` wraps `clock_nanosleep(CLOCK_REALTIME)` and
  maps every non-interrupt failure to `-2`
  (`musl src/thread/thrd_sleep.c`); `thrd_current` aliases
  `pthread_self` (`musl src/thread/pthread_self.c`).

## References

- glibc manual: `threads.texi`, node *ISO C Thread Management*
- header: `/usr/include/threads.h` lines 84-121
- symbols: `nm -D --with-symbol-versions libc.so.6`
