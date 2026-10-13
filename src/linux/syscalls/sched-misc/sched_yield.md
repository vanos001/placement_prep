# sched_yield(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 24 / 158 / 124 / 158 (cached kernel tables; hub agrees) |
| Since (kernel) | 2.0 (hub/ledger; no VERSIONS section in the cached man page) |
| Man page | man2/sched_yield.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in `<sched.h>` (POSIX `_POSIX_PRIORITY_SCHEDULING`); glibc symbol sched_yield@@GLIBC_2.2.5 (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-sched_yield |

## Purpose

`sched_yield()` causes the calling thread to relinquish the CPU: the thread is
moved to the end of the run queue for its static priority and a new thread gets
to run. If the calling thread is the only thread at the highest priority at that
moment, it simply continues to run (man page).

## Synopsis

    #include <sched.h>
    int sched_yield(void);

## Arguments and behavior

No arguments. The call is intended for use with the real-time policies
(`SCHED_FIFO`, `SCHED_RR`): an `SCHED_FIFO` thread yields to let equal-priority
threads run; under `SCHED_RR` it ends its quantum early. Strategic calls can
improve performance when the caller has just released a heavily contended
resource such as a mutex. The man page warns against calling it unnecessarily or
while still holding resources other threads need, and states that use with
nondeterministic policies such as `SCHED_OTHER` is unspecified and very likely
means the application design is broken.

## Return value and errors

On success returns 0. "In the Linux implementation, `sched_yield()` always
succeeds" (man ERRORS) -- the cached page documents no `errno` values.

## Flags and constants

None.

## Security and notes

Unprivileged; no capability required. Overuse causes unnecessary context
switches and degrades performance (man NOTES). Futex-based wait queues
([futex(2)](../process/futex.md)) are usually a better mechanism than
yield-loops for waiting on shared state.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/sched_yield.2`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (24), `syscall_32.tbl`
  (158), `syscall_generic.tbl` (124), `syscall_arm.tbl` (158)
- Online: https://man7.org/linux/man-pages/man2/sched_yield.2.html
