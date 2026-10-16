# adjtimex(2) / clock_adjtime(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | adjtimex 159 / 124 / 171 / 124; clock_adjtime 305 / 343 / 266 / 372 |
| Since (kernel) | adjtimex 1.0; clock_adjtime 2.6.39; clock_adjtime64 i386/arm 405 (5.1 time64 batch, ledger tag probe) |
| Man page | man2/adjtimex.2 (man-pages 6.19 HTML set, fetched 2026-10-17) -- one page covers adjtimex, clock_adjtime and ntp_adjtime |
| glibc wrapper | adjtimex(3) W @@GLIBC_2.2.5, ntp_adjtime(3) W @@GLIBC_2.2.5, clock_adjtime(3) T @@GLIBC_2.14 (nm -D, glibc 2.41) |
| Aliases covered | clock_adjtime (SC-clock_adjtime, "covered" by this entry); clock_adjtime64 (i386 405, SC-clock_adjtime64, time64 twin) |
| Ledger ID | SC-adjtimex |

## Purpose

adjtimex() reads and optionally tunes the parameters of the kernel's clock adjustment algorithm (David L. Mills' NTP discipline, RFC 5905): it takes a `struct timex`, updates the selected kernel parameters from its fields, and returns the same structure refreshed with current kernel values (adjtimex.2, DESCRIPTION). clock_adjtime() is the per-clock extension added in 2.6.39: it applies the same `timex` discipline to a specific clock identified by `clk_id` (CLOCK_REALTIME, CLOCK_TAI, ...), which is what chrony/ntpd use to discipline individual clocks (adjtimex.2, SYNOPSIS/DESCRIPTION).

## Synopsis

```c
#include <sys/timex.h>
int adjtimex(struct timex *buf);
int clock_adjtime(clockid_t clk_id, struct timex *buf);
int ntp_adjtime(struct timex *buf);   /* BSD alias, same syscall */
```

## Arguments and behavior

`buf->modes` selects which fields to apply -- ADJ_OFFSET, ADJ_FREQUENCY, ADJ_MAXERROR, ADJ_ESTERROR, ADJ_STATUS, ADJ_TIMECONST, ADJ_TICK, ADJ_SETOFFSET and combinations such as ADJ_OFFSET_SINGLESHOT; a `modes` of 0 is a pure read (adjtimex.2, DESCRIPTION, struct timex comment). The `offset` field is nanoseconds when the returned status has STA_NANO set, otherwise microseconds; `freq` is a scaled ppm value (adjtimex.2, NOTES). clock_adjtime() adds the clock selector as the first argument and rejects clocks the discipline does not apply to (adjtimex.2). The time64 twin clock_adjtime64 (i386/arm 405) carries a 64-bit `timex` layout so 32-bit ABIs survive 2038; glibc hides it exactly like the other *_time64 entries.

## Return value and errors

adjtimex()/clock_adjtime() return the clock state on success: one of TIME_OK, TIME_INS, TIME_DEL, TIME_OOP, TIME_WAIT, TIME_ERROR (adjtimex.2, RETURN VALUE). On error, -1 with errno: EFAULT (`buf` outside address space), EINVAL (attempt to set `buf->constant` to a value outside the range, or an invalid `modes`/`clk_id` combination), EPERM (`buf->modes` nonzero without CAP_SYS_TIME) (adjtimex.2, ERRORS).

## Flags and constants

Status bits in `buf->status`: STA_PLL, STA_PPSFREQ, STA_UNSYNC, STA_NANO, and the rest of the STA_* family (adjtimex.2, DESCRIPTION and <sys/timex.h>). Mode selectors ADJ_* as listed above (adjtimex.2). Clock states TIME_OK..TIME_ERROR are the positive return values.

## Security and notes

All mutating modes require CAP_SYS_TIME (value 25); the read path (modes 0) is unprivileged -- that split is why chronyd runs as root only for the disciplining step. NTP daemons drive phase (ADJ_OFFSET), frequency (ADJ_FREQUENCY) and tick length (ADJ_TICK) gradually; the STA_UNSYNC flag is how the kernel reports "no discipline active", which timesyncd clears. ntp_adjtime(3) is the BSD-compatibility name with its own ADJ_* constant set (adjtimex.2). For an interview-ready mental model: adjtimex is to the clock what [sysctl](../sched-misc/sysctl.md)-style knobs are to kernel tunables, but with a defined convergence algorithm. Cross-reference: [gettimeofday](gettimeofday.md), [clock_getres](clock_getres.md), [nanosleep](nanosleep.md), [stime](stime.md).

## References

- https://man7.org/linux/man-pages/man2/adjtimex.2.html
- https://www.rfc-editor.org/rfc/rfc5905 (NTPv4, Mills' algorithm)
- worklog: wrapper symbols adjtimex/ntp_adjtime W @@GLIBC_2.2.5, clock_adjtime @@GLIBC_2.14 verified with nm -D against glibc 2.41 (2026-10-17)
