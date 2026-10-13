# perf_event_open(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 298 / 336 / 241 / 364 (cached kernel tables; hub agrees) |
| Since (kernel) | 2.6.31 as perf_counter_open(), renamed perf_event_open() in 2.6.32 (man VERSION) |
| Man page | man2/perf_event_open.2 (local cache, dated 2021-08-27) |
| glibc wrapper | None: glibc provides no wrapper, necessitating syscall(2) (man page); no perf_event symbol in libc (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-perf_event_open |

## Purpose

perf_event_open() creates a file descriptor that measures one performance event; descriptors can be grouped (group_fd argument) so events are scheduled onto the PMU as a unit and their counts are comparable. Events are either counting (aggregates gathered with read(2)) or sampling (measurements written to an mmap(2) ring buffer). Enable/disable goes through ioctl(2) or prctl(2). This one syscall is the kernel-side basis of the perf(1) tooling and of many profilers.

## Synopsis

```c
#include <linux/perf_event.h>   /* PERF_* constants */
#include <linux/hw_breakpoint.h>
int syscall(SYS_perf_event_open, struct perf_event_attr *attr,
            pid_t pid, int cpu, int group_fd, unsigned long flags);
```

## Arguments and behavior

pid/cpu select the target: 0/-1 self on any CPU, pid>0/-1 a specific thread, 0/cpu self-on-CPU, -1/cpu all processes on a CPU (privileged), -1/-1 invalid. group_fd links an event into a group led by the first event (group_fd -1). flags: PERF_FLAG_FD_CLOEXEC (3.14), PERF_FLAG_FD_NO_GROUP, PERF_FLAG_FD_OUTPUT (broken since 2.6.35), PERF_FLAG_PID_CGROUP (2.6.39). The perf_event_attr structure (versioned via its size field; PERF_ATTR_SIZE_VER0 64 through VER8 136 in the installed header) carries type (PERF_TYPE_HARDWARE 0, SOFTWARE 1, TRACEPOINT 2, HW_CACHE 3, RAW 4, BREAKPOINT 5), config, sample_period/sample_freq, sample_type, read_format, and a bitfield of modifiers (exclude_user/kernel/hv, precise_ip, inherit, enable_on_exec, write_backward, cgroup, and others).

## Return value and errors

Returns the new event fd; -1 with errno: EBADF/EFAULT/EINVAL (bad attr size or fields), EACCES/EPERM (privilege), ESRCH (pid missing), EAGAIN (pinned/exclusive contention), EBUSY, EMFILE/ENOSPC, ENODEV, EOPNOTSUPP, E2BIG, and others (full list in the man page).

## Flags and constants

Access is gated by /proc/sys/kernel/perf_event_paranoid: 2 = user-space measurements only (default since 4.6), 1 = kernel and user (default before 4.6), 0 = plus CPU-specific data, -1 = no restrictions; its existence is the official probe for perf_event support. Related sysctls: perf_event_max_sample_rate, perf_event_max_stack, perf_event_mlock_kb.

## Security and notes

- CAP_PERFMON (since 5.8) is the least-privilege capability for performance monitoring; it replaces CAP_SYS_ADMIN for the pid == -1 system-wide case, and since 5.9 it replaces the ptrace PTRACE_MODE_READ_REALCREDS check for pid > 0 monitoring (man page).
- Monitoring another process requires ptrace-mode read access otherwise; the paranoid sysctl bounds what unprivileged users may measure.

## References

- man2/perf_event_open.2 in the cached man-pages tree (dated 2021-08-27).
- Header: /usr/include/linux/perf_event.h (PERF_TYPE_*, PERF_ATTR_SIZE_VER*).
- [Syscalls ledger](../ledger.md) row SC-perf_event_open; [Domain hub](overview.md).
