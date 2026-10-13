# seccomp(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 317 / 354 / 277 / 383 (cached kernel tables; hub agrees) |
| Since (kernel) | 3.17 (man VERSIONS: "The seccomp() system call first appeared in Linux 3.17"; hub agrees). Per-arch BPF filter support per the man page: x86-64 / i386 / x32 since 3.5, ARM and s390 since 3.8, MIPS 3.16, ARM-64 3.19, PowerPC and Tile 4.3 |
| Man page | man2/seccomp.2 (local cache, dated 2021-08-27) |
| glibc wrapper | None; call via `syscall(SYS_seccomp, operation, flags, args)` (man page; nm -D on glibc 2.41 shows no seccomp symbol). libseccomp is the recommended front end (man NOTES) |
| Aliases covered | none (prctl PR_SET_SECCOMP is an equivalent interface, see below) |
| Ledger ID | SC-seccomp |

## Purpose

`seccomp()` operates on the Secure Computing (seccomp) state of the calling
process: it installs the hard-coded strict filter or a caller-supplied BPF
filter program that inspects every system call and returns a verdict, or it
queries action support and notification sizes. Background reading in this book
(architecture, threat model, libseccomp programming -- not duplicated here):
[kernel security overview](../../kernel/security/seccomp.md) and
[userspace programming guide](../../sysprog/seccomp.md).

## Synopsis

    #include <linux/seccomp.h>
    int syscall(SYS_seccomp, unsigned int operation, unsigned int flags,
                void *args);

## Arguments and behavior

| Operation | Value | Behavior (man page) |
|---|---|---|
| `SECCOMP_SET_MODE_STRICT` | 0 | Only read(2), write(2), _exit(2) (not exit_group) and sigreturn(2) allowed; anything else kills the thread. Needs `CONFIG_SECCOMP`. flags must be 0, args NULL. Equals `prctl(PR_SET_SECCOMP, SECCOMP_MODE_STRICT)` |
| `SECCOMP_SET_MODE_FILTER` | 1 | args points to `struct sock_fprog` (BPF program). Needs `CONFIG_SECCOMP_FILTER` and either `CAP_SYS_ADMIN` or the `no_new_privs` bit (`prctl(PR_SET_NO_NEW_PRIVS, 1)`), else `EACCES`. Equals `prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, args)` when flags is 0 |
| `SECCOMP_GET_ACTION_AVAIL` | 2 (4.14) | args points to a u32 action; tests kernel support |
| `SECCOMP_GET_NOTIF_SIZES` | 3 (5.0) | args points to `struct seccomp_notif_sizes` |

Mode constants (linux/seccomp.h): `SECCOMP_MODE_DISABLED` 0,
`SECCOMP_MODE_STRICT` 1, `SECCOMP_MODE_FILTER` 2.

## Return value and errors

0 on success; on `SECCOMP_FILTER_FLAG_TSYNC` failure the return value is the ID
of the first thread that could not synchronize; otherwise -1 with `errno`:
`EACCES`, `EBUSY` (a NEW_LISTENER filter already installed), `EFAULT`,
`EINVAL` (unknown operation; invalid flags; invalid or oversized filter program
-- more than `BPF_MAXINSNS` 4096 instructions), `ENOMEM` (total filters would
exceed `MAX_INSNS_PER_PATH` 32768 instructions), `EOPNOTSUPP`, `ESRCH`.

## Flags and constants

Filter flags for `SECCOMP_SET_MODE_FILTER` (installed linux/seccomp.h; since
values from the cached man page where documented):

| Flag | Value | Since |
|---|---|---|
| `SECCOMP_FILTER_FLAG_TSYNC` | 1UL << 0 | initial (no since given in man) |
| `SECCOMP_FILTER_FLAG_LOG` | 1UL << 1 | 4.14 |
| `SECCOMP_FILTER_FLAG_SPEC_ALLOW` | 1UL << 2 | 4.17 |
| `SECCOMP_FILTER_FLAG_NEW_LISTENER` | 1UL << 3 | 5.0 (returns a supervisor fd for `SECCOMP_RET_USER_NOTIF`; at most one such filter per thread) |
| `SECCOMP_FILTER_FLAG_TSYNC_ESRCH` | 1UL << 4 | header-sourced only; not in the cached man page; since unverified |
| `SECCOMP_FILTER_FLAG_WAIT_KILLABLE_RECV` | 1UL << 5 | header-sourced only; since unverified |

Filter return actions, in decreasing order of precedence (man page; values from
linux/seccomp.h):

| Action | Value | Since | Effect |
|---|---|---|---|
| `SECCOMP_RET_KILL_PROCESS` | 0x80000000U | 4.14 | terminate whole process as though by SIGSYS; syscall not run |
| `SECCOMP_RET_KILL_THREAD` (= `SECCOMP_RET_KILL`) | 0x00000000U | original | terminate the calling thread; unsafe for multithreaded processes |
| `SECCOMP_RET_TRAP` | 0x00030000U | original | thread-directed SIGSYS, `si_code` = `SYS_SECCOMP` |
| `SECCOMP_RET_ERRNO` | 0x00050000U | original | return `SECCOMP_RET_DATA` as errno without running the call |
| `SECCOMP_RET_USER_NOTIF` | 0x7fc00000U | 5.0 | forward to the supervisor fd; ENOSYS if none attached |
| `SECCOMP_RET_TRACE` | 0x7ff00000U | original | notify a ptrace tracer (`PTRACE_O_TRACESECCOMP`); ENOSYS without one |
| `SECCOMP_RET_LOG` | 0x7ffc0000U | 4.14 | log, then execute the syscall |
| `SECCOMP_RET_ALLOW` | 0x7fff0000U | original | execute the syscall |

Masks: `SECCOMP_RET_ACTION_FULL` 0xffff0000U, `SECCOMP_RET_ACTION` 0x7fff0000U,
`SECCOMP_RET_DATA` 0x0000ffffU. An unknown action is treated as
`SECCOMP_RET_KILL_PROCESS` (since 4.14) or `SECCOMP_RET_KILL_THREAD` (4.13 and
earlier). All filters run, most recently installed first; the highest-precedence
action wins.

## Security and notes

The `no_new_privs` requirement prevents an unprivileged process from filtering
setuid-root execution into a trap (man page explains the setuid scenario).
`/proc/sys/kernel/seccomp/actions_avail` and `actions_logged` (4.14) expose and
control audit logging of actions. Filters are inherited across fork/clone when
allowed, and preserved across execve(2) when allowed; further filters may be
added only if prctl(2)/seccomp(2) are still allowed by the current filter.
Before 5.4, x32-range syscall numbers must be denied explicitly by policies.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/seccomp.2`; companion
  `seccomp_unotify.2` in the cache
- Headers: installed `/usr/include/linux/seccomp.h`
- Book cross-links (background): `src/linux/kernel/security/seccomp.md`,
  `src/linux/sysprog/seccomp.md`
- Online: https://man7.org/linux/man-pages/man2/seccomp.2.html
