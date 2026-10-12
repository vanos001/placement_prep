# `pthread_attr_init` / `pthread_attr_destroy` / `pthread_attr_getdetachstate` / `pthread_attr_setdetachstate` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` |
| Standards | POSIX.1-2001, POSIX.1-2008 (`pthread_attr_init(3)`, `pthread_attr_setdetachstate(3)`) |
| Exported | `pthread_attr_init@@GLIBC_2.2.5`, `pthread_attr_destroy@@GLIBC_2.2.5` (weak), `pthread_attr_getdetachstate@@GLIBC_2.2.5`, `pthread_attr_setdetachstate@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe both pairs (`pthread_attr_init(3)`, `pthread_attr_setdetachstate(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-pthread_attr_init, GLIBC-pthread_attr_destroy, GLIBC-pthread_attr_getdetachstate, GLIBC-pthread_attr_setdetachstate |

## Declaration and gates

```c
#include <pthread.h>

int pthread_attr_init(pthread_attr_t *attr);                      /* :285 */
int pthread_attr_destroy(pthread_attr_t *attr);                   /* :288 */
int pthread_attr_getdetachstate(const pthread_attr_t *attr,
                                int *detachstate);                /* :292 */
int pthread_attr_setdetachstate(pthread_attr_t *attr, int detachstate);
                                                                  /* :297 */
```

No feature-test gate: the four declarations sit in the always-visible
part of `pthread.h` (`/usr/include/pthread.h` lines 285-300). The other
attribute setters are covered in
[pthread-attr-affinity-sigmask-np](pthread-attr-affinity-sigmask-np.md)
and the full-family view in
[pthread-attr-family](../process/pthread-attr-family.md).

## Semantics

`pthread_attr_init` fills an opaque `pthread_attr_t` with the default
attribute values; re-initializing an already initialized object is
undefined behavior (`pthread_attr_init(3)`). `pthread_attr_destroy`
releases any resources and has no effect on threads already created
from the object; a destroyed object may be re-initialized, and any
other use is undefined. `pthread_attr_setdetachstate` stores
`PTHREAD_CREATE_JOINABLE` (the default) or `PTHREAD_CREATE_DETACHED`,
deciding whether threads created from `attr` must be joined or clean
themselves up; `pthread_attr_getdetachstate` reads it back. All four
return 0 on success or a nonzero error number.

## Gotchas and portability

- A joinable thread that is never joined or detached leaks its
  resources (`pthread_attr_setdetachstate(3)` NOTES).
- POSIX.1 documents `ENOMEM` for `pthread_attr_init`; on Linux these
  calls always succeed (`pthread_attr_init(3)` ERRORS).
- musl 1.2.5: setter `musl src/thread/pthread_attr_setdetachstate.c`,
  getters bundled in `musl src/thread/pthread_attr_get.c`.

## References

- man3: `pthread_attr_init(3)`, `pthread_attr_setdetachstate(3)`
  (`source-cache/man-pages-sparse/man3/`)
- glibc manual: `threads.texi`, node *Creating and Destroying Threads*
- header: `/usr/include/pthread.h` lines 281-300
- symbols: `nm -D --with-symbol-versions libc.so.6`
