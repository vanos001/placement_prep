# Exit-Status Lifecycle and Conventions

This section traces a process from the moment it begins terminating to the moment another
process (or a shell) observes a single integer summarizing what happened. It separates three
layers that are often confused: **termination** (what the process itself does through
`exit(3)`, `_exit(2)`, `abort(3)`, or signal death), **status collection** (what the parent
reads through `wait(2)`, `waitpid(2)`, or `waitid(2)` and how the kernel encodes it), and
**status reporting** (what a shell's `$?`, a service manager, or a container runtime
ultimately surfaces). The same distinction explains why exit codes carry far less information
than most practitioners assume.

| Page | Coverage | IDs |
|------|----------|-----|
| [Lifecycle](./lifecycle.md) | `exit`/`_exit`/`_Exit` semantics, the `wait` family, the exact 16-bit wait-status bit layout on Linux, `WIFEXITED`/`WEXITSTATUS`/`WIFSIGNALED`/`WTERMSIG`/`WCOREDUMP`/`WIFSTOPPED`/`WSTOPSIG`/`WIFCONTINUED` macros, 8-bit truncation, zombies and reaping, stopped/continued children | EX-001 – EX-009 |
| [Conventions](./conventions.md) | Common status values (0, 1, 2, 126, 127, 128+N, 130, 137, 139, 143), what guarantees vs conventions vs tool-specific codes they are, and the additional evidence required before any single integer can be treated as a root cause | EX-010 – EX-012 |

## Scope and verification

Behavioral claims in this section are cited to [wait(2)](https://man7.org/linux/man-pages/man2/wait.2.html),
[exit(3)](https://man7.org/linux/man-pages/man3/exit.3.html), [\_exit(2)](https://man7.org/linux/man-pages/man2/_exit.2.html),
and POSIX.1-2017 XCU §2.8, with the wait-status bit layout verified against the kernel UAPI
header `include/uapi/linux/wait.h`. Claims about shell-visible statuses are cited to the shell
manuals ([Bash](../shells/bash.md), [Dash](../shells/dash.md), [Zsh](../shells/zsh.md)) and are
kept separate from kernel- and POSIX-level facts.

## Related Topics

- [Signals — Deep Reference](../signals/index.md) — the other half of a termination story: statuses whose low bits name a signal instead of an exit code
- [Signal interfaces](../interfaces/index.md) — `kill`, `sigaction`, and the wait-family syscalls behind this section
- [Shell behavior](../shells/index.md) — the reporting layer: `127`, `128+N`, and `pipefail` per shell
- [Operational troubleshooting](../troubleshooting/index.md) — these codes in practice, with decision trees
- [Containers](../containers/index.md) — the same statuses propagated (and transformed) through runtimes and orchestrators
- [Process control (existing chapter)](../../sysprog/process-control.md) — survey-level `fork`/`exec`/`wait` material this section deepens

## References

- *wait(2), waitpid(2), waitid(2)*, Linux man-pages — <https://man7.org/linux/man-pages/man2/wait.2.html>
- *exit(3)*, Linux man-pages — <https://man7.org/linux/man-pages/man3/exit.3.html>
- *\_exit(2)*, Linux man-pages — <https://man7.org/linux/man-pages/man2/_exit.2.html>
- *POSIX.1-2017 XCU Chapter 2*, The Open Group — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html>
