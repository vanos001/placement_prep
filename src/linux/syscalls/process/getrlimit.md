# getrlimit(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | getrlimit: 97 / 76 / none / none; setrlimit: 160 / 75 / none / none; prlimit64: 302 / 340 / 261 / 369; ugetrlimit: none / 191 / none / 191 |
| Since (kernel) | getrlimit, setrlimit 1.0; prlimit64 2.6.36; ugetrlimit 2.4 |
| Man page | man2/getrlimit.2 covers getrlimit/setrlimit/prlimit (cached roff, dated 2021-03-22); ugetrlimit is covered in man2/syscalls.2 ("The old and the new kernel routines being named sys_old_getrlimit() (slot __NR_getrlimit) and sys_getrlimit() (slot __NR_ugetrlimit)") |
| glibc wrapper | getrlimit@@GLIBC_2.2.5, getrlimit64@@GLIBC_2.2.5, setrlimit@@GLIBC_2.2.5, getrusage's neighbor prlimit@@GLIBC_2.13 and prlimit64@@GLIBC_2.13 (nm -D, glibc 2.41); prlimit(3) gates: _GNU_SOURCE (getrlimit.2, SYNOPSIS) |
| Aliases covered | setrlimit (SC-setrlimit), prlimit64 (SC-prlimit64), ugetrlimit (SC-ugetrlimit) |
| Ledger ID | SC-getrlimit |

## Purpose

getrlimit() and setrlimit() get and set per-process resource limits; prlimit64() is the modern combined call that can read another process's limits, set them, or both in one invocation (getrlimit.2, DESCRIPTION). Each resource has a soft limit (what the kernel enforces) and a hard limit (ceiling for the soft limit). This page groups the whole rlimit call family; the resources themselves are listed under "Resources".

## Synopsis

```c
#include <sys/resource.h>
int getrlimit(int resource, struct rlimit *rlim);
int setrlimit(int resource, const struct rlimit *rlim);
int prlimit(pid_t pid, int resource,
            const struct rlimit *new_limit,
            struct rlimit *old_limit);

struct rlimit {
    rlim_t rlim_cur;  /* Soft limit */
    rlim_t rlim_max;  /* Hard limit (ceiling for rlim_cur) */
};
```

## Arguments and behavior

`resource` selects one of the `RLIMIT_*` constants (see below). An unprivileged process may raise its soft limit up to the hard limit and may irreversibly lower its hard limit; raising the hard limit or setting another process's limits requires `CAP_SYS_RESOURCE` in the initial user namespace (getrlimit.2, DESCRIPTION). `RLIM_INFINITY` (all-ones `rlim_t`) means "no limit" in both directions. `prlimit()` with `pid` 0 acts on the caller; for a different target the caller needs `CAP_SYS_RESOURCE` or the same real/effective/saved-set UID and GID as the target, plus ptrace-read access rules described in the man page (getrlimit.2, DESCRIPTION). Either of `new_limit`/`old_limit` may be NULL.

## Return value and errors

0 on success, -1 with `errno` (getrlimit.2, RETURN VALUE): `EFAULT`, `EINVAL` (bad `resource`), `EPERM` (unprivileged caller tried to raise a hard limit or touch a process it may not), and `EPERM` rules for setrlimit-specific cases (getrlimit.2, ERRORS).

## Resources and constants

Values below are the x86_64/glibc enumeration order from `/usr/include/x86_64-linux-gnu/bits/resource.h` (verified on this host; the kernel's uapi `asm-generic/resource.h` uses the same order):

| Constant | # | Effect (getrlimit.2) |
|---|---|---|
| `RLIMIT_CPU` | 0 | CPU seconds; soft limit sends `SIGXCPU` (once per second past the soft limit), hard limit `SIGKILL` |
| `RLIMIT_FSIZE` | 1 | Max file size in bytes; exceeding sends `SIGXFSZ`, or `EFBIG` if caught/blocked |
| `RLIMIT_DATA` | 2 | Data segment + heap; since 4.7 also enforced on `mmap()` (`ENOMEM`) |
| `RLIMIT_STACK` | 3 | Stack bytes; controls SIGSEGV-on-deep-recursion and stack-growth checks |
| `RLIMIT_CORE` | 4 | Max core(5) dump size in bytes; 0 disables dumps |
| `RLIMIT_RSS` | 5 | No effect since 2.4 (kept for compatibility) |
| `RLIMIT_NPROC` | 6 | Max processes for the real UID (cap-aware; see fork.md) |
| `RLIMIT_NOFILE` | 7 | Max descriptor number +1 (`open`, `pipe`, `dup` return `EMFILE`) |
| `RLIMIT_MEMLOCK` | 8 | Bytes lockable via mlock(2) family |
| `RLIMIT_AS` | 9 | Virtual address space bytes (`brk`, `mmap`, `mremap` return `ENOMEM`) |
| `RLIMIT_LOCKS` | 10 | (2.4.0-2.4.24 only) flock(2)+lease lock count |
| `RLIMIT_SIGPENDING` | 11 | Queued signals for the caller's real UID |
| `RLIMIT_MSGQUEUE` | 12 | Bytes for POSIX message queues of the real UID |
| `RLIMIT_NICE` | 13 | Ceiling (as 20 - rlim_cur) for nice(2) adjustments |
| `RLIMIT_RTPRIO` | 14 | Real-priority ceiling (sched_setscheduler(2)) |
| `RLIMIT_RTTIME` | 15 | Microseconds of uninterrupted realtime CPU (`SCHED_FIFO`/`RR`) |
| `RLIM_NLIMITS` | 16 | Count of resources (not a settable limit) |

## Security and notes

Setuid/setgid transitions must not preserve arbitrary hard limits: the kernel resets several resources for privilege changes (getrlimit.2, NOTES on RLIMIT_* and execve interaction). The history is arch-shaped: asm-generic architectures (arm64, riscv, loongarch) never had getrlimit/setrlimit entry points at all -- they call prlimit64 directly, and the ledger's `none` numbers are the point, not an omission. On i386/arm32, Linux 2.4 widened the limit type and renumbered the call: the old 16-bit-era slot kept the name `getrlimit` and the new one landed in slot `ugetrlimit` (syscalls.2, "Old and new versions" list); glibc's `getrlimit()` calls whichever the running kernel prefers and falls back transparently. musl exposes `prlimit` in `sys/resource.h` and maps `prlimit64` to it with `#define prlimit64 prlimit` (musl-clone include/sys/resource.h line 58); musl implements getrusage/getrlimit/setrlimit/prlimit/personality in src/misc and src/linux (verified file list in the worklog). See also: [getrusage](getrusage.md) for usage statistics; [fork.md](fork.md) for `RLIMIT_NPROC` enforcement.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/getrlimit.2`; ugetrlimit history in `man2/syscalls.2`
- Online: https://man7.org/linux/man-pages/man2/getrlimit.2.html
- Header: /usr/include/x86_64-linux-gnu/bits/resource.h (enumeration order), /usr/include/sys/resource.h (prototypes)
- Kernel tables: source-cache/kernel/syscall_64.tbl (97, 160, 302), syscall_32.tbl (76, 75, 340, 191), syscall_generic.tbl (261), syscall_arm.tbl (369, 191)
- musl: source-cache/musl-clone/musl/src/misc/{getrlimit,setrlimit}.c, src/linux/prlimit.c, include/sys/resource.h
- Ledger rows SC-getrlimit, SC-setrlimit, SC-prlimit64, SC-ugetrlimit
