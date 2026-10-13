# sched_setscheduler(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sched_setscheduler 144 / 156 / 119 / 156; sched_getscheduler 145 / 157 / 120 / 157; sched_setparam 142 / 154 / 118 / 154; sched_getparam 143 / 155 / 121 / 155 (cached kernel tables syscall_64.tbl, syscall_32.tbl, syscall_generic.tbl, syscall_arm.tbl; ledger SC- rows agree. The hub rows for sched_setscheduler and sched_setparam carry the get-variant numbers 145/157/120/157 and 143/155/121/155) |
| Since (kernel) | 2.0 (hub/ledger; neither cached man page has a VERSIONS section) |
| Man page | man2/sched_setscheduler.2 + man2/sched_setparam.2 (local cache, both dated 2021-03-22) |
| glibc wrapper | All four declared in `<sched.h>` (POSIX `_POSIX_PRIORITY_SCHEDULING`); `SCHED_OTHER`, `SCHED_BATCH`, `SCHED_IDLE`, `SCHED_DEADLINE`, `SCHED_RESET_ON_FORK` require `_GNU_SOURCE` per installed glibc bits/sched.h |
| Aliases covered | sched_getscheduler, sched_setparam, sched_getparam (separate cached man pages folded here per task brief; hub/ledger rows SC-sched_setparam/SC-sched_getparam point at sched_setparam.md, not written by this task -- merge note) |
| Ledger ID | SC-sched_setscheduler (family: SC-sched_getscheduler, SC-sched_setparam, SC-sched_getparam) |

## Purpose

`sched_setscheduler()` sets both the scheduling policy and the parameters of the
thread whose ID is `pid` (0 = calling thread); `sched_getscheduler()` returns the
thread's current policy. `sched_setparam()` / `sched_getparam()` set / fetch only
the parameters (`struct sched_param { int sched_priority; }` -- in the current
implementation the single field) belonging to the thread's existing policy.
Scheduling policy and parameters are per-thread attributes on Linux: pass the
value from `gettid(2)` for a specific thread, `getpid(2)` for the main thread.

## Synopsis

    #include <sched.h>
    int sched_setscheduler(pid_t pid, int policy, const struct sched_param *param);
    int sched_getscheduler(pid_t pid);
    int sched_setparam(pid_t pid, const struct sched_param *param);
    int sched_getparam(pid_t pid, struct sched_param *param);

## Arguments and behavior

| Policy | Value (installed linux/sched.h) | Class | param->sched_priority |
|---|---|---|---|
| `SCHED_OTHER` | 0 | normal time-sharing | must be 0 |
| `SCHED_FIFO` | 1 | real-time first-in first-out | 1 .. 99 |
| `SCHED_RR` | 2 | real-time round-robin | 1 .. 99 |
| `SCHED_BATCH` | 3 | "batch" execution (Linux-specific) | must be 0 |
| `SCHED_IDLE` | 5 | very low priority background (Linux-specific) | must be 0 |
| `SCHED_DEADLINE` | 6 | deadline policy; settable only via [sched_setattr(2)](sched_setattr.md) | n/a |

The static priority range for `SCHED_FIFO`/`SCHED_RR` is what
[sched_get_priority_max(2)](sched_get_priority_max.md) reports. glibc's
bits/sched.h additionally defines `SCHED_ISO` 4 and `SCHED_EXT` 7; neither is
documented as a supported policy in the cached man pages, and the installed
kernel uapi linux/sched.h defines only 0, 1, 2, 3, 5, 6.

Since Linux 2.6.32, `SCHED_RESET_ON_FORK` (0x40000000) can be ORed into
`policy` so that children created by `fork(2)` do not inherit privileged
policies (man page).

## Return value and errors

`sched_setscheduler()`/`sched_setparam()` return 0 on success;
`sched_getscheduler()` returns the nonnegative policy; `sched_getparam()`
returns 0. On error all return -1 with `errno`: `EINVAL` (negative `pid`, NULL
`param`, unknown policy, or `param` invalid for the policy), `EPERM`
(insufficient privileges; sched_setparam.2 names `CAP_SYS_NICE`), `ESRCH`
(no thread with that ID). POSIX.1 says `sched_setscheduler()` should return the
previous policy; Linux always returns 0 (man-page BUGS section).

## Flags and constants

See the policy table above; the only ORable flag is `SCHED_RESET_ON_FORK`
0x40000000 (also usable through [sched_setattr(2)](sched_setattr.md) as
`SCHED_FLAG_RESET_ON_FORK`).

## Security and notes

Real-time policies require privilege rules documented in sched(7); sched_setparam.2
gives `EPERM` when the caller lacks `CAP_SYS_NICE`. With POSIX threads use
`pthread_setschedparam(3)` / `pthread_getschedparam(3)` /
`pthread_setschedprio(3)` instead of these calls (man NOTES).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/sched_setscheduler.2`,
  `sched_setparam.2` (2021-03-22)
- Constants: installed `/usr/include/linux/sched.h`, glibc `bits/sched.h`
- Kernel tables: `source-cache/kernel/syscall_64.tbl`, `syscall_32.tbl`,
  `syscall_generic.tbl`, `syscall_arm.tbl`
- Online: https://man7.org/linux/man-pages/man2/sched_setscheduler.2.html
