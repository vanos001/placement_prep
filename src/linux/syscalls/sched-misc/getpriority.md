# getpriority(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | getpriority 140 / 96 / 141 / 96; setpriority 141 / 97 / 140 / 97; nice -- (no x64 entry) / 34 / -- / 34 (cached kernel tables; the hub nice row carries no x64/g64 number because there is no nice syscall on those ABIs) |
| Since (kernel) | 1.0 (hub/ledger; the cached man pages give no VERSIONS section) |
| Man page | man2/getpriority.2 (cached 2021-08-27; covers setpriority) + man2/nice.2 (cached 2021-03-22) |
| glibc wrapper | getpriority/setpriority in `<sys/resource.h>`, nice in `<unistd.h>` (nice needs `_XOPEN_SOURCE` or, since glibc 2.19, `_DEFAULT_SOURCE`); all @@GLIBC_2.2.5 (nm -D). The glibc nice() wrapper composes getpriority + setpriority per the glibc manual (manual/resource.texi) |
| Aliases covered | setpriority, nice |
| Ledger ID | SC-getpriority (family: SC-setpriority, SC-nice) |

## Purpose

`getpriority()` / `setpriority()` get and set the scheduling priority -- the
"nice" value -- of a process, process group, or user selected by `which` and
`who`. nice(2) adds an increment to the calling thread's nice value; it deals
with the same attribute. A child created by `fork(2)` inherits the parent's nice
value, and the value is preserved across `execve(2)` (man pages).

## Synopsis

    #include <sys/resource.h>
    int getpriority(int which, id_t who);
    int setpriority(int which, id_t who, int prio);
    #include <unistd.h>
    int nice(int inc);

## Arguments and behavior

`which` selects the scope; `who == 0` means the calling process, its process
group, or its real UID respectively:

| `which` | Value (glibc bits/resource.h) | who is |
|---|---|---|
| `PRIO_PROCESS` | 0 | process ID |
| `PRIO_PGRP` | 1 | process group ID |
| `PRIO_USER` | 2 | user ID |

The nice value seen by user space ranges from -20 (highest priority) to +19
(lowest); `PRIO_MIN` is -20 and `PRIO_MAX` is 20 (bits/resource.h). Values
outside the range are silently clamped. The default is 0. The kernel internally
stores 40..1 and the glibc wrappers translate via `unice = 20 - knice` (man
"C library/kernel differences"). `getpriority()` returns the highest priority
(lowest numerical value) of any matching process; `setpriority()` sets all
matching processes. Since glibc 2.2.4 the nice() wrapper returns the new nice
value (POSIX conformance, obtained via getpriority(2) per nice.2); the raw
syscall (and glibc <= 2.2.3) returns 0.

## Return value and errors

getpriority()/nice() can legitimately return -1, so clear `errno` before the
call and check after. Errors: `EACCES` (setpriority: lowering the nice value
without privilege), `EINVAL` (`which` invalid), `EPERM` (target process found
but its effective UID matches neither the caller's effective nor real UID, and
the caller lacks `CAP_SYS_NICE`), `ESRCH` (no process matched). nice(2)
documents only `EPERM` (negative `inc` without privilege).

## Flags and constants

None beyond the `PRIO_*` table. Since Linux 2.6.12 an unprivileged process may
lower the nice value of a target within its `RLIMIT_NICE` soft limit
(getrlimit(2)); before 2.6.12 the EPERM rule required matching real UIDs,
since 2.6.12 it compares effective UIDs (man NOTES).

## Security and notes

Under NPTL the nice value is a per-thread attribute, not per-process as POSIX
assumes. Since the autogroup feature (Linux 2.6.38) the nice value often has
less effect than traditionally (man BUGS/NOTES). Kernel-side niceness interacts
with [sched_setattr(2)](sched_setattr.md) via `sched_nice`.

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/getpriority.2`,
  `nice.2`
- glibc manual: `source-cache/glibc-sparse/manual/resource.texi` (nice()
  equivalent definition)
- Headers: installed glibc `bits/resource.h` (`PRIO_*`, `PRIO_MIN/MAX`)
- Online: https://man7.org/linux/man-pages/man2/getpriority.2.html
