# `pthread_barrier_init` / `pthread_barrier_wait` / `pthread_barrier_destroy` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` (POSIX barriers; declared under `__USE_XOPEN2K`) |
| Standards | POSIX barriers (manual, *POSIX Barriers* node; no man3 page in the cached man-pages set) |
| Exported | all three `@@GLIBC_2.34` plus compat `@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all three (manual safety notes, *POSIX Barriers* node) |
| Ledger ID | GLIBC-pthread_barrier_init, GLIBC-pthread_barrier_wait, GLIBC-pthread_barrier_destroy |

## Declaration and gates

```c
#include <pthread.h>

int pthread_barrier_init(pthread_barrier_t *restrict barrier,
                         const pthread_barrierattr_t *restrict attr,
                         unsigned int count);                     /* :1254 */
int pthread_barrier_destroy(pthread_barrier_t *barrier);          /* :1260 */
int pthread_barrier_wait(pthread_barrier_t *barrier);             /* :1264 */

#define PTHREAD_BARRIER_SERIAL_THREAD -1                          /* :193 */
```

Declarations live in the `#ifdef __USE_XOPEN2K` block
(`/usr/include/pthread.h` lines 1225-1270), i.e. the
`_POSIX_C_SOURCE >= 200112L` feature set; the serial constant is
guarded by the same macro (`pthread.h:187-194`). The sibling
`pthread_barrierattr_*` calls are outside this batch's ledger rows.

## Semantics

A barrier synchronizes a fixed number of threads: `pthread_barrier_init`
arms it for `count` threads (`attr` is typically NULL for a
process-private barrier). The first `count - 1` callers of
`pthread_barrier_wait` block; the `count`-th releases the whole batch.
Exactly one caller of each batch -- unspecified which -- gets
`PTHREAD_BARRIER_SERIAL_THREAD`, the others get 0, and the barrier
immediately re-arms for the next batch (manual, *POSIX Barriers*).
`pthread_barrier_destroy` releases resources; destroying a barrier with
threads still waiting, or re-initializing one in use, is undefined
behavior. A cycle does not require a destroy/init pair -- the manual
only requires the barrier to be destroyed before it is re-initialized.

## Gotchas and portability

- Process-shared barriers ride on `pthread_barrierattr_setpshared`; the
  manual defers those details ("documentation TBD").
- musl 1.2.5: `pthread_barrier_{init,wait,destroy}.c` all present under
  `musl src/thread/`.

## Errors

- `EINVAL`: `count` is zero, or large enough to overflow an internal
  counter (manual, *POSIX Barriers*). `pthread_barrier_wait` and
  `pthread_barrier_destroy` are documented to always succeed on glibc.

## References

- glibc manual: `threads.texi`, node *POSIX Barriers*
- header: `/usr/include/pthread.h` lines 187-194, 1225-1270
- symbols: `nm -D --with-symbol-versions libc.so.6`
