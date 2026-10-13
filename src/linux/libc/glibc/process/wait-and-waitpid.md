# `wait` and `waitpid` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-wait, GLIBC-waitpid |
| Header | `sys/wait.h` |
| Provenance | POSIX.1 |
| Wraps | `wait4(2)` (both; there is no waitpid syscall on x86-64) |
| Status | documented |

**Semantics** -- block until a child changes state (terminated, stopped,
continued) and reap it. `wait(&status)` == `waitpid(-1, &status, 0)`.
`pid` selection: `-1` any child (`WAIT_ANY`), `0` any child in caller's
process group (`WAIT_MYPGRP`), `> 0` that child, `< -1` process group
`-pid`. Options: `WNOHANG` (return 0 instead of blocking when no status
is available -- the SIGCHLD-handler polling idiom), `WUNTRACED`, and
`WCONTINUED` (with `WIFCONTINUED`).

**Status macros** -- decode `status` only through: `WIFEXITED`,
`WEXITSTATUS` (low 8 bits), `WIFSIGNALED`, `WTERMSIG`, `WCOREDUMP`
(BSD, POSIX.1-2024), `WIFSTOPPED`, `WSTOPSIG`, `WIFCONTINUED`. The
encoding is deliberately opaque -- never bit-twiddle it.

**Return and errors** -- PID of the reported child (0 with `WNOHANG` and
nothing ready); `-1` with `EINTR` (an unblocked signal or caught SIGCHLD
interrupted the wait; with `SA_RESTART` the call may instead restart),
`ECHILD` (no children left -- the classic "all reaped" loop terminator),
`EINVAL`.

**glibc layer** -- cancellation points in multithreaded programs; wrap
long waits in cleanup handlers. glibc's `wait` is documented as a call
to `wait4(2)`; the raw `waitid(2)` syscall's fifth `rusage` argument is
hidden by the wrapper.

**Example**

```c
int status;
pid_t w;
do { w = waitpid(pid, &status, WUNTRACED | WCONTINUED); }
while (w == -1 && errno == EINTR);
if (WIFEXITED(status))       printf("exit=%d\n", WEXITSTATUS(status));
else if (WIFSIGNALED(status)) printf("sig=%d\n", WTERMSIG(status));
```

**References** -- `wait(2)`; syscall view: [wait4](../../../syscalls/process/overview.md).
