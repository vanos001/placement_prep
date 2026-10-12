# sched_get_priority_max(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sched_get_priority_max 146 / 159 / 125 / 159; sched_get_priority_min 147 / 160 / 126 / 160; sched_rr_get_interval 148 / 161 / 127 / 161 (cached kernel tables; hub agrees; the time64 twin sched_rr_get_interval_time64 is 423 on i386 and arm32 per the hub and syscall_32.tbl / syscall_arm.tbl) |
| Since (kernel) | 2.0 (hub/ledger; no VERSIONS section in the cached man pages) |
| Man page | man2/sched_get_priority_max.2 (cached 2021-03-22; sched_get_priority_min.2 is a 34-byte .so alias of it) + man2/sched_rr_get_interval.2 (cached 2021-03-22) |
| glibc wrapper | All three declared in `<sched.h>` (POSIX `_POSIX_PRIORITY_SCHEDULING`) |
| Aliases covered | sched_get_priority_min, sched_rr_get_interval (hub/ledger point SC-sched_rr_get_interval at a separate sched_rr_get_interval.md page -- folded here per task brief; merge note) |
| Ledger ID | SC-sched_get_priority_max (family: SC-sched_get_priority_min, SC-sched_rr_get_interval) |

## Purpose

`sched_get_priority_max()` / `sched_get_priority_min()` return the maximum and
minimum static priority value usable with the scheduling algorithm identified by
`policy`. Higher numeric values are scheduled first, so the max is greater than
the min. The ranges are fixed and cannot be altered (man page). These calls are
how portable code discovers the argument range for
[sched_setscheduler(2)](sched_setscheduler.md) and sched_setparam(2).

`sched_rr_get_interval()` writes the round-robin time quantum of the thread
identified by `pid` (0 = calling thread) into the `timespec` pointed to by
`tp`; the thread should be running under `SCHED_RR`.

## Synopsis

    #include <sched.h>
    int sched_get_priority_max(int policy);
    int sched_get_priority_min(int policy);
    int sched_rr_get_interval(pid_t pid, struct timespec *tp);

## Arguments and behavior

`policy` is one of `SCHED_FIFO`, `SCHED_RR`, `SCHED_OTHER`, `SCHED_BATCH`,
`SCHED_IDLE`, `SCHED_DEADLINE`. On Linux the returned ranges are:

| Policy | min | max |
|---|---|---|
| `SCHED_FIFO`, `SCHED_RR` | 1 | 99 |
| `SCHED_OTHER`, `SCHED_BATCH`, `SCHED_IDLE`, `SCHED_DEADLINE` | 0 | 0 |

POSIX.1 requires a spread of at least 32 between min and max for `SCHED_FIFO`
and `SCHED_RR`, so portable applications should map a virtual priority range
onto the returned interval (man page).

## Return value and errors

The priority calls return the requested bound on success, -1 on error with
`errno` = `EINVAL` (unrecognized policy). `sched_rr_get_interval()` returns 0 on
success, -1 with `EFAULT` (bad `tp`), `EINVAL` (invalid `pid`), `ENOSYS` (very
old kernels), or `ESRCH` (no such process).

## Flags and constants

None for these calls. Notes from the cached sched_rr_get_interval.2: the old
(nonportable) mechanism of adjusting the quantum via the nice value was removed
starting with Linux 2.6.24; since Linux 3.9 the quantum can be read and set via
`/proc/sys/kernel/sched_rr_timeslice_ms`, a millisecond value defaulting to 100,
where writing 0 resets the default. The sched_rr_get_interval_time64 twin
(hub row: i386 423 / arm32 423, no Since, source-limited) exists so 32-bit ABIs
get a 64-bit `timespec`; on 64-bit ABIs the generic table entry 127 already maps
to the 64-bit handler.

## Security and notes

No capability is required to query the ranges or the quantum.

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/sched_get_priority_max.2`
  (+ .so alias sched_get_priority_min.2), `sched_rr_get_interval.2`
- Kernel tables: `source-cache/kernel/syscall_64.tbl`, `syscall_32.tbl`,
  `syscall_generic.tbl`, `syscall_arm.tbl`
- Online: https://man7.org/linux/man-pages/man2/sched_get_priority_max.2.html
