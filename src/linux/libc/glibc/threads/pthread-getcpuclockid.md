# `pthread_getcpuclockid` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` plus `time.h` for `clockid_t`; declared under `__USE_XOPEN2K` |
| Standards | POSIX.1-2001, POSIX.1-2008 (`pthread_getcpuclockid(3)`); glibc since 2.2 |
| Exported | `pthread_getcpuclockid@@GLIBC_2.34` plus compat `@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`pthread_getcpuclockid(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-pthread_getcpuclockid |

## Declaration and gates

```c
#include <pthread.h>
#include <time.h>

int pthread_getcpuclockid(pthread_t thread, clockid_t *clockid);
                                                          /* :1315 */
```

The declaration sits in a `#ifdef __USE_XOPEN2K` block of
`/usr/include/pthread.h` (lines 1314-1318), i.e.
`_POSIX_C_SOURCE >= 200112L`.

## Semantics

`pthread_getcpuclockid` stores the ID of the CPU-time clock of `thread`
in `*clockid`. That clock measures CPU time consumed by that thread
alone and can be read with `clock_gettime(2)` (and, where supported,
`clock_settime(2)`) exactly like any other clock
(`pthread_getcpuclockid(3)`). When `thread` is the calling thread, the
returned ID refers to the same clock as the special
`CLOCK_THREAD_CPUTIME_ID` clock ID (man NOTES). The function returns 0
on success and a nonzero error number otherwise; typical use is
profiling or per-thread timeouts measured in consumed CPU time rather
than wall time.

## Gotchas and portability

- Per-thread CPU-time clocks are a runtime capability, not a compile-time
  one: the failure mode is `ENOENT`, so test on the target system.
- The related process-wide clock is `CLOCK_PROCESS_CPUTIME_ID`; timers
  driven by such clocks live on the time side of this encyclopedia
  ([timer-alarm-sleep](../fs/timer-alarm-sleep.md)).
- musl 1.2.5: present as `musl src/thread/pthread_getcpuclockid.c`.

## Errors

- `ENOENT`: per-thread CPU-time clocks are not supported by the system.
- `ESRCH`: no thread with the given ID exists
  (`pthread_getcpuclockid(3)` ERRORS).

## References

- man3: `pthread_getcpuclockid(3)`
  (`source-cache/man-pages-sparse/man3/`)
- glibc manual: `threads.texi`, node *POSIX Threads Other APIs*
- header: `/usr/include/pthread.h` lines 1314-1318
- symbols: `nm -D --with-symbol-versions libc.so.6`
