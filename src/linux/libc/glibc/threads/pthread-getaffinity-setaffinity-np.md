# `pthread_setaffinity_np` / `pthread_getaffinity_np` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` (`_GNU_SOURCE`) |
| Standards | nonstandard GNU extensions (`pthread_setaffinity_np(3)`); glibc since 2.3.4 |
| Exported | `pthread_setaffinity_np@@GLIBC_2.34` plus compat `@GLIBC_2.3.4`/`@GLIBC_2.3.3`; `pthread_getaffinity_np@@GLIBC_2.32` plus compat `@GLIBC_2.3.4`/`@GLIBC_2.3.3` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe both (`pthread_setaffinity_np(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-pthread_setaffinity_np, GLIBC-pthread_getaffinity_np |

## Declaration and gates

```c
#define _GNU_SOURCE
#include <pthread.h>

int pthread_setaffinity_np(pthread_t thread, size_t cpusetsize,
                           const cpu_set_t *cpuset);         /* :489 */
int pthread_getaffinity_np(pthread_t thread, size_t cpusetsize,
                           cpu_set_t *cpuset);               /* :494 */
```

Both sit in a `#ifdef __USE_GNU` block of `/usr/include/pthread.h`
(lines 476-496). The attribute-object variants are covered in
[pthread-attr-affinity-sigmask-np](pthread-attr-affinity-sigmask-np.md);
CPU sets are manipulated with the `CPU_*` macros from `sched.h`.

## Semantics

`pthread_setaffinity_np` sets the CPU affinity mask of `thread` to
`*cpuset`; if the thread is currently running on a CPU outside the new
set, the kernel migrates it. `pthread_getaffinity_np` copies the
thread's current mask out. `cpusetsize` is the byte size of the buffer,
typically `sizeof(cpu_set_t)` (`pthread_setaffinity_np(3)`). Both are
thin wrappers over the `sched_setaffinity(2)` /
`sched_getaffinity(2)` system calls (man NOTES). After a successful
set, the CPUs the thread actually runs on are the intersection of the
requested set, the CPUs present, and any `cpuset(7)` restrictions;
these restrictions are silently imposed (man NOTES). A thread created
afterwards inherits a copy of its creator's affinity mask
(`pthread_setaffinity_np(3)` NOTES).

## Gotchas and portability

- glibc 2.3.3 only shipped these functions without the `cpusetsize`
  argument, always passing `sizeof(cpu_set_t)` to the kernel (man NOTES).
- musl 1.2.5: no `pthread_setaffinity_np`/`pthread_getaffinity_np` at
  all (`musl src/thread/` has no affinity files).

## Errors

- `EFAULT`: invalid address. `EINVAL`: set variant -- mask has no CPU
  present on the system or permitted by cpuset restrictions, or a CPU
  outside the kernel range; get variant -- `cpusetsize` smaller than the
  kernel mask. `ESRCH`: no such thread
  (`pthread_setaffinity_np(3)` ERRORS).

## References

- man3: `pthread_setaffinity_np(3)` (covers both)
  (`source-cache/man-pages-sparse/man3/`)
- glibc manual: `threads.texi`, node *Thread CPU Affinity*
- header: `/usr/include/pthread.h` lines 476-496
- symbols: `nm -D --with-symbol-versions libc.so.6`
