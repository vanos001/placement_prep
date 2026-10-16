# times(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 100 / 43 / 153 / 43 |
| Since (kernel) | 1.0 |
| Man page | man2/times.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | times(3) W @@GLIBC_2.2.5 (nm -D, glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-times |

## Purpose

times() stores the CPU time accounting of the calling process into `struct tms`: user and system time of the process itself (`tms_utime`, `tms_stime`) and of all waited-for terminated children (`tms_cutime`, `tms_cstime`) (times.2, DESCRIPTION). The return value is the uptime in clock ticks -- a monotonic anchor that lets callers turn two samples into elapsed wall time.

## Synopsis

```c
#include <sys/times.h>
clock_t times(struct tms *buf);
```

## Arguments and behavior

`buf` receives the four accounting fields (times.2, DESCRIPTION, struct tms). Children's times fold in only after wait(2)-style reaping (the "waited-for terminated" wording; see [wait4](../process/wait4.md)). The tick unit comes from sysconf(_SC_CLK_TCK) -- nominally 100, not CLOCKS_PER_SEC (times.2, NOTES; clock(3) uses a different unit with the same clock_t type, a classic confusion). `buf` may be NULL to fetch only the uptime return value (kernel convention; the man page documents the struct fill as the purpose).

## Return value and errors

Returns the elapsed real time in clock ticks since an arbitrary point (boot); -1 on error with errno set (times.2, RETURN VALUE). Errors: EFAULT (`buf` invalid). BUGS note: on i386 there is a small window (~41 seconds) after boot where times() can return -1 falsely, and the same false -1 can occur when the tick counter wraps the 32-bit clock_t (times.2, BUGS) -- the reason long-lived systems sample uptime via clock_gettime(CLOCK_BOOTTIME) instead.

## Flags and constants

None (units from sysconf(_SC_CLK_TCK)).

## Security and notes

No capability involved; the accounting shown is the same data getrusage(2) exposes with finer granularity (see [getrusage](../process/getrusage.md)). POSIX requires tms_cutime/tms_cstime to include only reaped children, which is why a still-running child's CPU time never appears. For benchmarking, prefer clock_gettime(CLOCK_PROCESS_CPUTIME_ID); times() remains the portable-and-cheap coarse probe. Cross-reference: [getrusage](../process/getrusage.md), [wait4](../process/wait4.md), [time](time.md), [sysinfo](../sched-misc/sysinfo.md).

## References

- https://man7.org/linux/man-pages/man2/times.2.html
- worklog: wrapper symbol times W @@GLIBC_2.2.5 verified with nm -D against glibc 2.41 (2026-10-17)
