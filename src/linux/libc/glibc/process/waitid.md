# `waitid` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-waitid (triage row; not in the glibc manual) |
| Header | `sys/wait.h` |
| Provenance | POSIX.1-2001 (glibc gates: `_XOPEN_SOURCE`, or `_POSIX_C_SOURCE >= 200809L` since 2.12) |
| Wraps | `waitid(2)` (5th raw `rusage` argument hidden by wrapper) |
| Status | documented |

**Semantics** -- wait with *structured* reporting: `idtype` selects
`P_PID`, `P_PGID`, `P_ALL`, or `P_PIDFD` (Linux 5.4: wait on a pidfd --
immune to PID reuse); `options` is a mask of `WEXITED`, `WSTOPPED`,
`WCONTINUED`, `WNOWAIT` (leave the child in a waitable state), `WNOHANG`.
The result lands in a `siginfo_t`: `si_pid`, `si_uid`, `si_code`
(`CLD_EXITED`, `CLD_KILLED`, `CLD_DUMPED`, `CLD_STOPPED`, `CLD_TRAPPED`,
`CLD_CONTINUED`) and `si_status`.

**Return and errors** -- 0 on success and also when `WNOHANG` found
nothing; `-1` with `ECHILD` (no such child -- including when SIGCHLD is
`SIG_IGN`), `EINTR`, `EINVAL`. With `WNOHANG` and nothing to report,
POSIX.1-2008 TC1 requires `si_pid`/`si_signo` zeroed -- Linux does, but
portable code should zero `si_pid` first and test it after.

**Edge cases** -- a process can wait on itself via `P_PID` with its own
PID only if it is its own child (never) -- the useful self-check is
`ECHILD` after `P_ALL` to prove no children remain. `waitid` is the only
member of the family that reports *why* a child stopped via `si_code`
rather than `WSTOPSIG` guesswork.

**References** -- `waitid(2)` section of `wait(2)`; syscall view:
[waitid](../../../syscalls/process/overview.md).
