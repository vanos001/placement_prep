# ioprio_get(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | ioprio_get 252 / 290 / 31 / 315; ioprio_set 251 / 289 / 30 / 314 (per-call table below) |
| Since (kernel) | 2.6.13 (man VERSIONS; hub agrees) |
| Man page | man2/ioprio_set.2 (ioprio_get.2 is a .so alias of it; local cache, dated 2021-03-22) |
| glibc wrapper | None (man BUGS: glibc provides neither prototypes nor headers); no ioprio symbol in libc (nm -D on glibc 2.41); constants in <linux/ioprio.h> |
| Aliases covered | ioprio_set |
| Ledger ID | SC-ioprio_get, SC-ioprio_set |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| ioprio_get | 252 | 290 | 31 | 315 | 2.6.13 |
| ioprio_set | 251 | 289 | 30 | 314 | 2.6.13 |

## Purpose

ioprio_get() and ioprio_set() get and set the I/O scheduling class and priority of one or more threads. An ioprio value packs a class in the high bits and class data in the low bits (IOPRIO_CLASS_SHIFT 13; /usr/include/linux/ioprio.h). Priorities are honored only by I/O schedulers that support them (CFQ historically; the installed header names BFQ and mq-deadline) and only for reads and synchronous (O_DIRECT/O_SYNC) writes -- asynchronous write-back carries no program priority. Without an explicit setting, I/O priority follows the CPU nice value; ioprio 0 resets to that default (since 2.6.24).

## Synopsis

```c
int ioprio_get(int which, int who);
int ioprio_set(int which, int who, int ioprio);
```

## Arguments and behavior

| which (linux/ioprio.h) | Value | who means |
|---|---|---|
| IOPRIO_WHO_PROCESS | 1 | One PID/TID; 0 = calling thread |
| IOPRIO_WHO_PGRP | 2 | Process group ID; 0 = caller's group |
| IOPRIO_WHO_USER | 3 | UID; all processes with that real UID |

Classes (same header): IOPRIO_CLASS_NONE 0, IOPRIO_CLASS_RT 1 (real time; 8 levels, 0 highest; can starve the system), IOPRIO_CLASS_BE 2 (best effort, the default; 8 levels like nice), IOPRIO_CLASS_IDLE 3 (served only when nothing else wants the disk; no class data), IOPRIO_CLASS_INVALID 7. Macros: IOPRIO_PRIO_VALUE(class, data), IOPRIO_PRIO_CLASS(mask), IOPRIO_PRIO_DATA(mask); IOPRIO_NORM 4 is the fallback BE level.

## Return value and errors

ioprio_get() returns the highest ioprio among matching processes (class first, then level); ioprio_set() returns 0. On error -1 with errno: EINVAL (bad which or ioprio), EPERM (privilege rules below), ESRCH (no match).

## Flags and constants

Privilege rules (man NOTES): an unprivileged caller may change only processes whose real UID matches its real or effective UID, unless it holds CAP_SYS_NICE; setting IOPRIO_CLASS_RT requires CAP_SYS_ADMIN (setting IDLE required it only before 2.6.25).

## Security and notes

- Threads of one process do not share an I/O context by default (clone(2) CLONE_IO shares it), so setting per-process priority may require iterating TIDs from gettid(2).
- Scheduler selection is per device via /sys/block/<device>/queue/scheduler; see the sysfs ledger for the block class attributes.

## References

- man2/ioprio_set.2 in the cached man-pages tree; .so alias ioprio_get.2.
- Header: /usr/include/linux/ioprio.h (classes, WHO values, macros).
- [Syscalls ledger](../ledger.md) rows SC-ioprio_get, SC-ioprio_set.
- Siblings: [getpriority](getpriority.md) (nice coupling); [Domain hub](overview.md).
