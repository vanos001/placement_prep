# `thrd_create` / `thrd_exit` / `thrd_join` / `thrd_detach` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `threads.h` |
| Standards | C11 section 7.26 (ISO C threads) |
| Exported | all four `@@GLIBC_2.34` plus compat `@GLIBC_2.28` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety notes, *ISO C Thread Management* node) |
| Ledger ID | GLIBC-thrd_create, GLIBC-thrd_exit, GLIBC-thrd_join, GLIBC-thrd_detach |

## Declaration and gates

```c
#include <threads.h>

typedef int (*thrd_start_t)(void *);                  /* threads.h:41 */

int  thrd_create(thrd_t *thr, thrd_start_t func, void *arg);
                                                      /* threads.h:81 */
void thrd_exit(int res) __attribute__((__noreturn__));/* threads.h:108 */
int  thrd_detach(thrd_t thr);                         /* threads.h:112 */
int  thrd_join(thrd_t thr, int *res);                 /* threads.h:116 */
```

No feature-test gate. `thrd_start_t` is `int (*)(void *)` -- unlike the
POSIX `void *(*)(void *)` start routine, the C11 result code is an `int`.

## Semantics

`thrd_create` starts a new thread running `func(arg)` and stores its
identifier in `*thr`; it may return `thrd_success`, `thrd_nomem` or
`thrd_error` (manual, *ISO C Thread Management*). Returning from the
start function is equivalent to calling `thrd_exit` with the return
value. `thrd_exit` terminates the calling thread with result `res`; if
the process is still single-threaded the call is equivalent to `exit`
with `EXIT_SUCCESS`. `thrd_join` blocks until the thread finishes,
stores its result in `*res` when non-NULL, and its return
synchronizes-with the thread's termination. `thrd_detach` releases the
thread's resources at exit; the parent is never notified. Calling
`thrd_join` or `thrd_detach` a second time on the same thread, or from
two threads, is undefined behavior; both return only `thrd_success` or
`thrd_error`.

## Gotchas and portability

- Join or detach every joinable thread; there is no C11 equivalent of
  the POSIX `PTHREAD_CREATE_DETACHED` attribute
  ([attribute family](pthread-attr-init-destroy-detachstate.md)).
- POSIX-side lifecycle calls live in
  [pthread-create](../process/pthread-create.md) and
  [pthread-join](../process/pthread-join-and-pthread-detach.md).
- musl 1.2.5: `thrd_create`/`thrd_exit`/`thrd_join` have their own
  `.c` files; `thrd_detach` is an alias inside
  `musl src/thread/pthread_detach.c`.

## References

- glibc manual: `threads.texi`, node *ISO C Thread Management*
- header: `/usr/include/threads.h` lines 44, 81-116
- symbols: `nm -D --with-symbol-versions libc.so.6`
