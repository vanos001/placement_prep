# getrusage(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 98 / 77 / 165 / 77 |
| Since (kernel) | 1.0 |
| Man page | man2/getrusage.2 (cached roff, dated 2021-03-22; split out of getrlimit.2 in 2004 per the page header) |
| glibc wrapper | getrusage@@GLIBC_2.2.5 (nm -D, glibc 2.41); musl: src/misc/getrusage.c, time64 redirect `__getrusage_time64` (include/sys/resource.h line 109) |
| Aliases covered | none |
| Ledger ID | SC-getrusage |

## Purpose

getrusage() returns resource usage measures -- CPU time, page-fault counts, context-switch counts, I/O counts -- for the calling process (`RUSAGE_SELF`), for all terminated-and-waited children (`RUSAGE_CHILDREN`), or for the calling thread (`RUSAGE_THREAD`, since 2.6.26, gated on `_GNU_SOURCE`) (getrusage.2, DESCRIPTION).

## Synopsis

```c
#include <sys/resource.h>
int getrusage(int who, struct rusage *usage);
```

## Arguments and behavior

`usage` points to a `struct rusage` of 16 `long`/`timeval` fields. Field-by-field, verified against getrusage.2:

| Field | Meaning | State |
|---|---|---|
| `ru_utime` | User CPU time (timeval) | maintained |
| `ru_stime` | System CPU time | maintained |
| `ru_maxrss` | Max resident set size in kilobytes; for `RUSAGE_CHILDREN` the largest child's RSS | since 2.6.32 |
| `ru_ixrss`, `ru_idrss`, `ru_isrss` | Integral shared/data/stack memory | unmaintained, always 0 on Linux |
| `ru_minflt` | Page faults serviced without I/O (reclaims) | maintained |
| `ru_majflt` | Page faults that required I/O | maintained |
| `ru_nswap` | Swaps | unmaintained |
| `ru_inblock` / `ru_oublock` | Block I/O operations | since 2.6.22 |
| `ru_msgsnd` / `ru_msgrcv` / `ru_nsignals` | IPC messages, signals | unmaintained |
| `ru_nvcsw` / `ru_nivcsw` | Voluntary / involuntary context switches | since 2.6 |

`RUSAGE_CHILDREN` aggregates children that have terminated and been waited for; grandchildren count too when every intermediate descendant waited (getrusage.2, DESCRIPTION). Unmaintained fields are zeroed by the kernel for compatibility with other systems (getrusage.2, DESCRIPTION).

## Return value and errors

0 on success, -1 with `errno`: `EFAULT` (usage outside accessible address space) or `EINVAL` (invalid `who`) (getrusage.2, ERRORS).

## Security and notes

Historically getrusage(2) underreported when `SIGCHLD` was being ignored; that nonconformance is fixed since 2.6.9 (getrusage.2 page header note). `RUSAGE_THREAD` needs `_GNU_SOURCE` before including any header (getrusage.2, DESCRIPTION). The child-accounting contract is what makes process monitors (time(1), shells' `%` job stats) work without reading /proc per child; wait4(2) and wait4.md expose the same struct on wait. The data source is the task's accounting fields, the same ones BSD accounting writes to the acct(5) file format (cross-ref: [acct.md](acct.md)). For live totals of an arbitrary other process, /proc/`<pid>`/stat is the interface, not getrusage.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/getrusage.2`
- Online: https://man7.org/linux/man-pages/man2/getrusage.2.html
- Header: /usr/include/x86_64-linux-gnu/sys/resource.h (`struct rusage`, `RUSAGE_*`)
- Kernel tables: source-cache/kernel/syscall_64.tbl (98), syscall_32.tbl (77), syscall_generic.tbl (165), syscall_arm.tbl (77)
- musl: source-cache/musl-clone/musl/src/misc/getrusage.c, include/sys/resource.h
- Ledger row SC-getrusage
