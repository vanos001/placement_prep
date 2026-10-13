# sched_setattr(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sched_setattr 314 / 351 / 274 / 380; sched_getattr 315 / 352 / 275 / 381 (cached kernel tables and ledger SC- rows; the hub row for sched_setattr carries 315/352/275/381, the getattr numbers) |
| Since (kernel) | 3.14 (man VERSIONS: "These system calls first appeared in Linux 3.14"; hub agrees) |
| Man page | man2/sched_setattr.2 (local cache, dated 2021-03-22; covers sched_getattr). Flag-since values beyond the cache taken from man7.org current page (man-pages 6.19), fetched this session |
| glibc wrapper | Cached 2021 man page: "glibc provides no wrappers for these system calls, necessitating the use of syscall(2)". Installed glibc 2.41 disagrees: it exports sched_setattr / sched_getattr @@GLIBC_2.41 and declares them in bits/sched.h. Both sources named |
| Aliases covered | sched_getattr |
| Ledger ID | SC-sched_setattr (family: SC-sched_getattr) |

## Purpose

`sched_setattr()` sets the scheduling policy and extended attributes of the
thread whose ID is `pid` (0 = calling thread) via a `struct sched_attr`, a
size-tagged structure that can grow without breaking the old fixed ABI of
[sched_setscheduler(2)](sched_setscheduler.md)/sched_setparam(2). It is a
superset of sched_setscheduler(2), sched_setparam(2), nice(2) and (except for
setting priorities of whole users/groups) setpriority(2) (man NOTES).
`sched_getattr()` fetches the same attributes.

## Synopsis

    #include <linux/sched/types.h>   /* SCHED_*, struct sched_attr (kernel uapi) */
    int syscall(SYS_sched_setattr, pid_t pid, struct sched_attr *attr,
                unsigned int flags);            /* flags must be 0 */
    int syscall(SYS_sched_getattr, pid_t pid, struct sched_attr *attr,
                unsigned int size, unsigned int flags);

## Arguments and behavior

struct sched_attr (installed linux/sched/types.h and glibc bits/sched.h):

| Field | Meaning |
|---|---|
| `size` | sizeof(struct sched_attr); oversize structs must zero-pad or fail `E2BIG`; undersize tails are treated as 0 (man) |
| `sched_policy` | one of the `SCHED_*` policies; `SCHED_DEADLINE` is settable only here |
| `sched_flags` | zero or more `SCHED_FLAG_*` bits (table below) |
| `sched_nice` | nice value -20 (high) .. +19 (low) for `SCHED_OTHER` / `SCHED_BATCH` |
| `sched_priority` | static priority 1..99 for `SCHED_FIFO` / `SCHED_RR`, else 0 |
| `sched_runtime`, `sched_deadline`, `sched_period` | `SCHED_DEADLINE` parameters in nanoseconds; see sched(7) |
| `sched_util_min`, `sched_util_max` | utilization clamp, range [0, 1024], both since Linux 5.3 (man7.org current); a value of `UINT32_MAX` removes a clamp, since Linux 5.11 (man7.org current) |

Size constants: `SCHED_ATTR_SIZE_VER0` 48 (first published struct), `VER1` 56
(adds util fields) per linux/sched/types.h.

## Return value and errors

0 on success, -1 with `errno`: `EINVAL` (NULL `attr`; negative `pid`; nonzero
`flags`; size below 48 or above one page; unknown policy or flag; invalid
priority or deadline parameters), `E2BIG` (setattr: oversize struct with nonzero
excess; getattr: buffer too small), `EBUSY` (`SCHED_DEADLINE` admission-control
failure), `EPERM` (insufficient privilege, or the thread's affinity mask does
not include all CPUs -- required for deadline), `ESRCH`. Bugs: up to 3.15
`E2BIG` was reported as `EFAULT`; up to 5.3 getattr returned `EFBIG` for the
small-buffer case (man page).

## Flags and constants

| Flag | Value | Since |
|---|---|---|
| `SCHED_FLAG_RESET_ON_FORK` | 0x01 | initial (man) |
| `SCHED_FLAG_RECLAIM` | 0x02 | 4.13 (cached man) |
| `SCHED_FLAG_DL_OVERRUN` | 0x04 | 4.16 (cached man); overrun notification is a process-directed SIGXCPU, flagged "probably a bug" in the man page |
| `SCHED_FLAG_KEEP_POLICY` | 0x08 | header-sourced only (installed glibc bits/sched.h, linux/sched.h); not documented in either man page; kernel since-value unverified |
| `SCHED_FLAG_KEEP_PARAMS` | 0x10 | header-sourced only; kernel since-value unverified |
| `SCHED_FLAG_UTIL_CLAMP_MIN` | 0x20 | 5.3 (man7.org current) |
| `SCHED_FLAG_UTIL_CLAMP_MAX` | 0x40 | 5.3 (man7.org current) |

Combinations `SCHED_FLAG_KEEP_ALL` (0x18) and `SCHED_FLAG_UTIL_CLAMP` (0x60)
are defined in the headers.

## Security and notes

Setting privileged policies or deadline parameters requires privilege per
sched(7) rules (man gives `EPERM`). Deadline scheduling additionally requires
the affinity mask to cover every CPU. For a pointer to the deadline policy
model, see sched(7) and the SCHED_DEADLINE row of
[sched_setscheduler(2)](sched_setscheduler.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/sched_setattr.2`
- Online (current): https://man7.org/linux/man-pages/man2/sched_setattr.2.html
- Headers: installed `/usr/include/linux/sched/types.h`, glibc `bits/sched.h`
- Kernel tables: `source-cache/kernel/syscall_64.tbl`, `syscall_32.tbl`,
  `syscall_generic.tbl`, `syscall_arm.tbl`
