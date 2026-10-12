# prctl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 157 / 172 / 167 / 172 |
| Since (kernel) | 2.2 (hub); individual options range from 2.1.57 (PR_SET_PDEATHSIG) to 5.11 (PR_SET_SYSCALL_USER_DISPATCH) - per-option values below |
| Man page | man2/prctl.2 (cached roff, dated 2021-03-22); no aliases |
| glibc wrapper | prctl(3) variadic wrapper, symbol version GLIBC_2.2.5 on installed glibc 2.41 (nm -D) |
| Aliases covered | none |
| Ledger ID | SC-prctl |

## Purpose

prctl() is a multiplexed interface: one syscall whose first argument selects among dozens of per-thread and per-process operations (defined in linux/prctl.h). It controls things that have no dedicated syscall: the process name, parent-death signal, dumpable flag, no_new_privs, seccomp installation, subreaper status, timer slack, capability bounding/ambient sets, and more (prctl.2). Careless use can confuse the user-space runtime (prctl.2 warning).

## Synopsis

```c
#include <sys/prctl.h>
int prctl(int option, unsigned long arg2, unsigned long arg3,
          unsigned long arg4, unsigned long arg5);
```

## Arguments and behavior

option selects the operation; arg2..arg5 are unsigned long whose meaning is defined per option - they carry integers, pointers (cast), or must be 0. Major option groups (values from /usr/include/linux/prctl.h; since-values from prctl.2):

| Group | Options (value) | Since |
|---|---|---|
| Parent death | PR_SET_PDEATHSIG (1), PR_GET_PDEATHSIG (2) | 2.1.57 / 2.3.15 |
| Dumpable | PR_GET_DUMPABLE (3), PR_SET_DUMPABLE (4) | 2.3.20 |
| Capabilities | PR_GET/SET_KEEPCAPS (7/8), PR_CAPBSET_READ (23), PR_CAPBSET_DROP (24), PR_CAP_AMBIENT (47) | 2.2.18 / 2.6.25 / 4.3 |
| Name | PR_SET_NAME (15), PR_GET_NAME (16): 16-byte comm | 2.6.9 / 2.6.11 |
| Seccomp | PR_GET_SECCOMP (21), PR_SET_SECCOMP (22) | 2.6.23 |
| Securebits | PR_GET/SET_SECUREBITS (27/28) | 2.6.26 |
| Timer slack | PR_SET_TIMERSLACK (29), PR_GET_TIMERSLACK (30) | 2.6.28 |
| Perf events | PR_TASK_PERF_EVENTS_DISABLE/ENABLE (31/32) | 2.6.31 |
| MCE kill | PR_MCE_KILL (33), PR_MCE_KILL_GET (34) | 2.6.32 |
| Memory map | PR_SET_MM (35) | 3.3 |
| Subreaper | PR_SET_CHILD_SUBREAPER (36), PR_GET_CHILD_SUBREAPER (37) | 3.4 |
| Tracer policy | PR_SET_PTRACER (0x59616d61) | 3.4 |
| no_new_privs | PR_SET_NO_NEW_PRIVS (38), PR_GET_NO_NEW_PRIVS (39) | 3.5 |
| Misc | PR_GET_TID_ADDRESS (40), PR_SET/GET_THP_DISABLE (41/42, 3.15), PR_SET/GET_FP_MODE (45/46, MIPS only), PR_SVE_SET/GET_VL (50/51, arm64 4.15), PR_GET/SET_SPECULATION_CTRL (52/53, 4.17), PR_PAC_RESET_KEYS (54, arm64 5.0), PR_SET/GET_TAGGED_ADDR_CTRL (55/56, arm64 5.4), PR_SET/GET_IO_FLUSHER (57/58, 5.6), PR_SET_SYSCALL_USER_DISPATCH (59, x86 5.11) | see left |

Argument typing example: PR_SET_PDEATHSIG takes a signal number in arg2; PR_GET_NAME takes a pointer in arg2; PR_CAP_AMBIENT takes a sub-operation in arg2 (PR_CAP_AMBIENT_IS_SET / RAISE / LOWER / CLEAR_ALL) and a capability in arg3, with arg4/arg5 required to be 0 (prctl.2).

## Return value and errors

Success: 0 for most options; the getters PR_CAPBSET_READ, PR_GET_DUMPABLE, PR_GET_KEEPCAPS, PR_GET_NO_NEW_PRIVS, PR_GET_SECUREBITS, PR_GET_TIMERSLACK, PR_GET_THP_DISABLE, PR_GET_TIMING, PR_MCE_KILL_GET, PR_GET_SPECULATION_CTRL, PR_CAP_AMBIENT + IS_SET (and PR_GET_SECCOMP if it returns) return the queried nonnegative value as the function result (prctl.2, RETURN VALUE). Failure: -1 with errno. Main errors (prctl.2): EINVAL (invalid option or argument), EACCES (PR_SET_SECCOMP filter mode without CAP_SYS_ADMIN and without no_new_privs; PR_SET_MM EXE_FILE not executable), EPERM (PR_CAPBSET_DROP without CAP_SETPCAP), EBADF (PR_SET_MM EXE_FILE bad fd), plus EFAULT and option-specific errors.

## Flags and constants

Values cited above come from /usr/include/linux/prctl.h. Related constants: SECCOMP_MODE_STRICT/_FILTER for PR_SET_SECCOMP; PR_CAP_AMBIENT_* sub-ops; PR_SET_MM_* sub-ops.

## Security and notes

no_new_privs set here disables set-user-ID/set-group-ID transformation and file capabilities at the next execve(2) (execve.2). PR_SET_DUMPABLE changes /proc/[pid] ownership semantics. PR_SET_PDEATHSIG is cleared across a set-user-ID exec (execve.2). PR_SET_SECCOMP is the pre-seccomp(2) way to install filters. PR_SET_CHILD_SUBREAPER changes reparenting for [wait4](wait4.md) and [_exit](_exit.md); PR_SET_PTRACER feeds the Yama LSM for [ptrace](ptrace.md).

## References

- https://man7.org/linux/man-pages/man2/prctl.2.html
- kernel/sys.c (SYSCALL_DEFINE5(prctl, ...) verified by fetching torvalds master kernel/sys.c; worklog 1-a did not list this file)
- /usr/include/linux/prctl.h, /usr/include/sys/prctl.h
