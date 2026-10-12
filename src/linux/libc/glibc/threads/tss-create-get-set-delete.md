# `tss_create` / `tss_get` / `tss_set` / `tss_delete` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `threads.h` |
| Standards | C11 section 7.26 (ISO C threads) |
| Exported | all four `@@GLIBC_2.34` plus compat `@GLIBC_2.28` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety notes, *ISO C Thread-local Storage* node) |
| Ledger ID | GLIBC-tss_create, GLIBC-tss_get, GLIBC-tss_set, GLIBC-tss_delete |

## Declaration and gates

```c
#include <threads.h>

#define TSS_DTOR_ITERATIONS 4                        /* threads.h:36 */

int  tss_create(tss_t *tss_key, tss_dtor_t destructor);
                                                     /* threads.h:223 */
void *tss_get(tss_t tss_key);                        /* threads.h:227 */
int  tss_set(tss_t tss_key, void *val);              /* threads.h:231 */
void tss_delete(tss_t tss_key);                      /* threads.h:235 */
```

No feature-test gate; `tss_dtor_t` is `void (*)(void *)`
(`threads.h:38`). The POSIX counterpart family is documented in
[pthread-key-create-pthread-getspecific-tsd-family](../process/pthread-key-create-pthread-getspecific-tsd-family.md).

## Semantics

`tss_create` creates a key and stores it in `*tss_key`; the same key may
be used by every thread, but the value bound through `tss_set` is
maintained per thread and persists for that thread's life. When
`destructor` is non-NULL it runs when the thread finishes by calling
`thrd_exit` -- but never on `tss_delete` or `exit` (manual, *ISO C
Thread-local Storage*). `tss_create` returns `thrd_success`, or
`thrd_error` with `*tss_key` left undefined. `tss_set` stores `val` for
the current thread; `tss_get` returns the current thread's value and
`0` on failure; `tss_delete` invalidates the key. `TSS_DTOR_ITERATIONS`
bounds how often destructors may be re-run when a destructor creates
new thread-local storage.

## Gotchas and portability

- Destructors do not run at process exit or on `tss_delete`; free
  per-thread resources before either.
- C++ `thread_local` objects are destroyed before thread-specific data,
  so the manual warns against referencing them from these destructors.
- musl 1.2.5: `tss_get` is a weak alias of `__pthread_getspecific`
  (`musl src/thread/pthread_getspecific.c:11`); the other three have
  their own `.c` files; `TSS_DTOR_ITERATIONS` is also `4`
  (`musl include/threads.h:25`).

## References

- glibc manual: `threads.texi`, node *ISO C Thread-local Storage*
- header: `/usr/include/threads.h` lines 36-38, 223-235
- symbols: `nm -D --with-symbol-versions libc.so.6`
