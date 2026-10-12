# `system` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-system |
| Header | `stdlib.h` |
| Provenance | ISO C; POSIX.1-2001/2008 |
| Wraps | `clone`-based fork + `execl("/bin/sh","sh","-c",...)` + `waitpid` |
| Status | documented |

**Semantics** -- run *command* through the shell and return its wait
status. The documented signal dance in the caller for the duration of
the command: **`SIGCHLD` blocked, `SIGINT` and `SIGQUIT` ignored** -- set
and restored via `sigaction`/`sigprocmask` internally, so the parent
isn't killed by Ctrl-C aimed at the child and doesn't steal SIGCHLD from
`waitpid`. The child gets default dispositions for those signals.
POSIX.1 leaves it unspecified whether `pthread_atfork` handlers run;
glibc does not run them.

**Return encoding (interview favorite)** --

- `command == NULL`: nonzero iff a shell is available (real `/bin/sh`
 check since glibc 2.1.3; before that always 1).
- `-1` with `errno`: `fork`/`waitpid` failure.
- otherwise a **wait status** decode with `WIFEXITED`/`WEXITSTATUS`
 etc. -- *not* an exit code. Shell-unavailable/exec-failure surfaces as
 if the shell called `_exit(127)`; a command that legitimately exits
 127 is indistinguishable from that.

**Edge cases** -- never use from setuid/setgid programs (`PATH` and
shell-environment subversion); `system()` is MT-Safe and a cancellation
point; a command string starting with `-` is parsed by `sh -c` as an
option (undefined; prepend a space); calls from a loop are
uninterruptible unless you check `WIFSIGNALED`/`WTERMSIG == SIGINT`.

**References** -- `system(3)`, `sh(1)`; glibc manual *Running a
Command*.
