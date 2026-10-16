# time(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 201 / 13 / -- / -- |
| Since (kernel) | 1.0 |
| Man page | man2/time.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | time(3) i @@GLIBC_2.2.5 (nm -D, glibc 2.41; the i = ifunc -- glibc dispatches to vDSO/clock_gettime-based fast paths where available) |
| Aliases covered | none; grouped family: [stime](stime.md) (set), gettimeofday (get with sub-second precision) |
| Ledger ID | SC-time |

## Purpose

time() returns the current calendar time as the number of seconds since the Epoch, 1970-01-01 00:00:00 +0000 (UTC); if `tloc` is non-NULL, the same value is also stored there (time.2, DESCRIPTION). It is the coarse wall-clock read: whole seconds, CLOCK_REALTIME semantics, no timezone involvement.

## Synopsis

```c
#include <time.h>
time_t time(time_t *_Nullable tloc);
```

## Arguments and behavior

One optional out-parameter `tloc` duplicating the return value (time.2, DESCRIPTION). The value is CLOCK_REALTIME in whole seconds -- settable, discplined by NTP, subject to jumps (see [clock_adjtime](clock_adjtime.md)). There is no arm64/asm-generic entry (g64/arm `--` in the ledger): 64-bit generic ABIs access the clock through gettimeofday/clock_gettime paths, and glibc implements time(3) on top of clock_gettime(2) there.

## Return value and errors

Returns the seconds count; on error, ((time_t) -1) is returned with errno set -- EFAULT is the only documented error (`tloc` invalid) (time.2, RETURN VALUE/ERRORS). Note the classic caveat: a legitimate time value could theoretically equal (time_t) -1 only at the Epoch boundary; the real-world hazard is 32-bit time_t overflow in 2038.

## Flags and constants

None.

## Security and notes

No capability needed to read the clock. Interview-relevant notes: (1) time(3) in glibc may not issue the syscall at all -- the ifunc symbol above reflects vDSO acceleration; (2) whole-second resolution means timing loops must use clock_gettime(CLOCK_MONOTONIC) instead; (3) paired with [stime](stime.md) for the legacy write path. Cross-reference: [gettimeofday](gettimeofday.md), [stime](stime.md), [clock_adjtime](clock_adjtime.md), [times](times.md).

## References

- https://man7.org/linux/man-pages/man2/time.2.html
- worklog: wrapper symbol time i @@GLIBC_2.2.5 (ifunc) verified with nm -D against glibc 2.41 (2026-10-17)
