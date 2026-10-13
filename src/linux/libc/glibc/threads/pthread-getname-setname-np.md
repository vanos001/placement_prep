# `pthread_setname_np` / `pthread_getname_np` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` (`_GNU_SOURCE`) |
| Standards | nonstandard GNU extensions (`pthread_setname_np(3)`); glibc since 2.12 |
| Exported | both `@@GLIBC_2.34` plus compat `@GLIBC_2.12` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe both (`pthread_setname_np(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-pthread_setname_np, GLIBC-pthread_getname_np |

## Declaration and gates

```c
#define _GNU_SOURCE
#include <pthread.h>

int pthread_setname_np(pthread_t thread, const char *name);    /* :463 */
int pthread_getname_np(pthread_t thread, char *buf, size_t buflen);
                                                               /* :458 */
```

Both sit in a `#ifdef __USE_GNU` block of `/usr/include/pthread.h`
(lines 457-465).

## Semantics

By default every thread created by `pthread_create` inherits the
program name. `pthread_setname_np` gives `thread` the name `name`, a
NUL-terminated string of at most 16 bytes including the terminator
(i.e. 15 usable characters); `pthread_getname_np` copies the name into
`buf`, which should be at least 16 bytes, and NUL-terminates the result
(`pthread_setname_np(3)`). The manual notes the name shows up in `ps`
when listing individual threads (manual, *Thread Names*). Both calls
are implemented by writing and reading the thread's `comm` file,
`/proc/self/task/[tid]/comm` (man NOTES), and return 0 on success or a
nonzero error number.

## Gotchas and portability

- The name is kernel state, so it is visible in `/proc` output, `top`
  and core dumps even after the naming thread exits.
- `pthread_setname_np(pthread_self(), ...)` names the caller; naming
  another thread is allowed on Linux, unlike some other systems that
  restrict it to the calling thread.
- musl 1.2.5: both functions exist
  (`musl src/thread/pthread_setname_np.c`,
  `musl src/thread/pthread_getname_np.c`).

## Errors

- `ERANGE` (`setname_np`): the string exceeds the length limit.
- `ERANGE` (`getname_np`): buffer too small for the name.
- Both may additionally fail with the errors of `open(2)` when
  `/proc/self/task/[tid]/comm` cannot be opened
  (`pthread_setname_np(3)` ERRORS).

## References

- man3: `pthread_setname_np(3)` (covers `pthread_getname_np.3`, a
  `.so` link to it; `source-cache/man-pages-sparse/man3/`)
- glibc manual: `threads.texi`, node *Thread Names*
- header: `/usr/include/pthread.h` lines 457-465
- symbols: `nm -D --with-symbol-versions libc.so.6`
