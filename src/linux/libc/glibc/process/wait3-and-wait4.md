# `wait3` and `wait4` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-wait3, GLIBC-wait4 |
| Header | `sys/wait.h` |
| Provenance | BSD; `wait3` obsolete (removed by POSIX.1-2008), `wait4` Linux/BSD extension |
| Wraps | `wait4(2)` |
| Status | documented |

**Semantics** -- `wait4(pid, status, options, rusage)` is `waitpid` plus a
`struct rusage` with the reaped child's resource usage -- filled only if
the child *terminated*, not if it stopped. `wait3(status, options,
rusage)` is the fixed form `waitpid(-1, status, options)` plus rusage;
the glibc manual calls it "now obsolete" but still exports it (symbol
GLIBC_2.2.5, `nm -D`-verified). New code should use `waitpid` +
`getrusage(RUSAGE_CHILDREN)`, or `waitid` for per-child precision.

**References** -- `wait3(2)`/`wait4(2)` (one page), glibc manual *BSD
Wait Functions*; syscall view: [wait4](../../../syscalls/process/overview.md).
