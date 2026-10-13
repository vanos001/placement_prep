# sched_setaffinity(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sched_setaffinity 203 / 241 / 122 / 241; sched_getaffinity 204 / 242 / 123 / 242 (cached kernel tables and ledger SC- rows; the hub row for sched_setaffinity carries 204/242/123/242, the getaffinity numbers -- values above are the per-call table entries) |
| Since (kernel) | 2.6 (hub/ledger); man VERSIONS: "The CPU affinity system calls were introduced in Linux kernel 2.5.8" -- both attributions stated |
| Man page | man2/sched_setaffinity.2 (local cache, dated 2021-03-22; covers sched_getaffinity) |
| glibc wrapper | Both in `<sched.h>` (`_GNU_SOURCE`); glibc symbols sched_setaffinity/sched_getaffinity @@GLIBC_2.3.4 (plus compat @GLIBC_2.3.3); wrapper history: cpusetsize as unsigned int in glibc 2.3, removed in 2.3.3, restored as size_t in 2.3.4 (man VERSIONS) |
| Aliases covered | sched_getaffinity |
| Ledger ID | SC-sched_setaffinity (family: SC-sched_getaffinity) |

## Purpose

A thread's CPU affinity mask is the set of CPUs on which it is eligible to run.
`sched_setaffinity()` sets the mask of the thread whose ID is `pid` (0 = calling
thread); if the thread is running off-mask it is migrated. `sched_getaffinity()`
writes the mask back into the caller's buffer. Pinning a thread to one CPU avoids
cache-invalidation cost when it migrates, and pairs with the `isolcpus` boot
option to dedicate CPUs (man page). For per-thread control from the POSIX threads
API use `pthread_setaffinity_np(3)`.

## Synopsis

    #define _GNU_SOURCE
    #include <sched.h>
    int sched_setaffinity(pid_t pid, size_t cpusetsize, const cpu_set_t *mask);
    int sched_getaffinity(pid_t pid, size_t cpusetsize, cpu_set_t *mask);

## Arguments and behavior

| Layer | Representation | Size facts |
|---|---|---|
| glibc `cpu_set_t` | struct with fixed bit array; manipulate via `CPU_SET(3)` macros | 128 bytes fixed, max CPU number 1023; `__CPU_SETSIZE` 1024 in glibc bits/cpu-set.h |
| kernel syscall | `unsigned long *` bit mask; `cpusetsize` in bytes | no size restriction on the raw call; raw sched_getaffinity returns the number of bytes copied = min(cpusetsize, sizeof kernel cpumask_t); glibc wrapper returns 0 |

For systems whose kernel affinity mask is larger than 1024 CPUs,
`sched_getaffinity(pid, sizeof(cpu_set_t), &mask)` fails with `EINVAL`; the mask
must then be dynamically allocated (`CPU_ALLOC(3)`) and sized by probing with
increasing sizes (man page "Handling systems with large CPU affinity masks").

## Return value and errors

0 on success (raw getaffinity: byte count), -1 on error with `errno`: `EFAULT`
(invalid address), `EINVAL` (mask contains no CPU that is physically on the
system and permitted by cpuset cgroups / cpuset(7); or `cpusetsize` smaller than
the kernel mask -- getaffinity always, setaffinity in kernels before 2.6.9),
`EPERM` (setaffinity: caller needs `CAP_SYS_NICE` in the target's user namespace
or an effective UID equal to the target's real or effective UID), `ESRCH`.

## Flags and constants

No flags. The effective run set is the intersection of `mask`, the CPUs present,
and any cpuset restriction, imposed silently (man NOTES).

## Security and notes

A child created by `fork(2)` inherits the parent's mask; the mask is preserved
across `execve(2)`. Affinity is a per-thread attribute: pass the value from
`gettid(2)`. The i386 and arm32 table rows invoke the compat handlers
(compat_sys_sched_setaffinity / compat_sys_sched_getaffinity per
syscall_32.tbl); the arm64-generic rows are the same native numbers 122/123.
See also the getcpu(2) page in this hub (not yet written; see the hub
[overview](overview.md)) and [sysinfo(2)](sysinfo.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/sched_setaffinity.2`
- Kernel tables: `source-cache/kernel/syscall_64.tbl`, `syscall_32.tbl`,
  `syscall_generic.tbl`, `syscall_arm.tbl`
- Headers: installed glibc `bits/cpu-set.h` (`__CPU_SETSIZE` 1024)
- Online: https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html
