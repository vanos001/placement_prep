# `pthread_attr_setaffinity_np` / `pthread_attr_getaffinity_np` / `pthread_attr_setsigmask_np` / `pthread_attr_getsigmask_np` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` (`_GNU_SOURCE`) |
| Standards | nonstandard GNU extensions (`_np`); affinity pair since glibc 2.3.4, sigmask pair since glibc 2.32 (`pthread_attr_setaffinity_np(3)`, `pthread_attr_setsigmask_np(3)` VERSIONS) |
| Exported | `pthread_attr_setaffinity_np@@GLIBC_2.32` plus compat `@GLIBC_2.3.4`/`@GLIBC_2.3.3`; `pthread_attr_getaffinity_np@@GLIBC_2.34` plus compat `@GLIBC_2.3.4`/`@GLIBC_2.3.3`; both sigmask functions `@@GLIBC_2.32` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all four (`pthread_attr_setaffinity_np(3)`, `pthread_attr_setsigmask_np(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-pthread_attr_setaffinity_np, GLIBC-pthread_attr_getaffinity_np, GLIBC-pthread_attr_setsigmask_np, GLIBC-pthread_attr_getsigmask_np |

## Declaration and gates

```c
#define _GNU_SOURCE
#include <pthread.h>

int pthread_attr_setaffinity_np(pthread_attr_t *attr, size_t cpusetsize,
                                const cpu_set_t *cpuset);        /* :394 */
int pthread_attr_getaffinity_np(const pthread_attr_t *attr,
                                size_t cpusetsize, cpu_set_t *cpuset);
                                                                 /* :401 */
int pthread_attr_setsigmask_np(pthread_attr_t *attr,
                               const sigset_t *sigmask);         /* :411 */
int pthread_attr_getsigmask_np(const pthread_attr_t *attr,
                               sigset_t *sigmask);               /* :417 */
#define PTHREAD_ATTR_NO_SIGMASK_NP (-1)                          /* :422 */
```

All four sit in one `#ifdef __USE_GNU` block of
`/usr/include/pthread.h` (lines 393-430). The per-thread equivalents are
in [pthread-getaffinity-setaffinity-np](pthread-getaffinity-setaffinity-np.md).

## Semantics

`pthread_attr_setaffinity_np` stores a CPU affinity mask in the
attribute object, restricting the CPUs of threads later created with it;
`pthread_attr_getaffinity_np` copies it out (`pthread_attr_setaffinity_np(3)`).
`pthread_attr_setsigmask_np` stores the initial signal mask of the new
thread; a NULL `sigmask` unsets the attribute so the mask is inherited
from the creating thread. `pthread_attr_getsigmask_np` returns 0 and
the mask when set, or the special value `PTHREAD_ATTR_NO_SIGMASK_NP`
when unset (manual, *Initial Thread Signal Mask*). The manual notes
that `pthread_getattr_np` does not recover the thread's signal mask,
so the getter reports unset for such objects.

## Gotchas and portability

- glibc 2.3.3 only shipped these affinity functions without the
  `cpusetsize` argument (`pthread_attr_setaffinity_np(3)` NOTES).
- musl 1.2.5: none of the four exists (`musl src/thread/` has no
  `*affinity*` or `*sigmask*` attr files).

## Errors

- `EINVAL` (`setaffinity_np`): `cpuset` names a CPU outside the kernel
  range. `EINVAL` (`getaffinity_np`): a CPU of the stored mask lies
  outside `cpusetsize`. `ENOMEM` (`setaffinity_np`): allocation failed
  (`pthread_attr_setaffinity_np(3)`).
- `ENOMEM` (`setsigmask_np`): memory allocation failed
  (`pthread_attr_setsigmask_np(3)`).

## References

- man3: `pthread_attr_setaffinity_np(3)`, `pthread_attr_setsigmask_np(3)`
  (`source-cache/man-pages-sparse/man3/`)
- glibc manual: `threads.texi`, nodes *Thread CPU Affinity*,
  *Initial Thread Signal Mask*
- header: `/usr/include/pthread.h` lines 393-430
- symbols: `nm -D --with-symbol-versions libc.so.6`
