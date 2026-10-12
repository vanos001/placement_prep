# `fork` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

## Processes

| Field | Value |
|---|---|
| ID | GLIBC-fork, GLIBC-_Fork |
| Header | `unistd.h` |
| Provenance | fork: POSIX.1; _Fork: GNU, adopted by POSIX.1-2024 |
| Wraps | `clone(2)` (since glibc 2.3.3), not the `fork` syscall |
| Status | documented |

**Semantics** -- duplicate the calling process: 0 in the child, child's PID
in the parent, -1/`errno` on failure. The child keeps copies of open file
descriptors (sharing file offset and open-file status flags) and inherits
the signal mask and dispositions, but starts with an *empty* pending-signal
set, zeroed CPU-time counters, no inherited record locks (`fcntl(2)` locks;
`flock`/OFD locks *are* inherited), no alarms, and -- the part that matters
for threads -- only a single thread: the one that called `fork`.

**glibc layer** -- the wrapper runs the `pthread_atfork` *prepare* handlers
(reverse registration order), issues `clone(SIGCHLD)`, then runs *parent*
handlers in the parent and *child* handlers in the child (registration
order), re-initializing internal locks so the child's stdio/loader state
is usable. That re-initialization is exactly what plain `_Fork`
(GLIBC_2.34, verified via `nm -D`) skips: no atfork callbacks, no internal
state reset -- the child may call only async-signal-safe functions such as
`dup2` or `execve`.

**Return and errors** -- `EAGAIN` (`RLIMIT_NPROC`, `threads-max`,
`pid_max`, cgroup `pids.max`, or `SCHED_DEADLINE` without reset-on-fork),
`ENOMEM`, `ENOSYS` (no-MMU platforms).

**Edge cases** -- after `fork` in a multithreaded program the child may
call only async-signal-safe functions until `execve`; mutexes locked by
other threads stay locked forever in the child. `vfork` and (since 2.24)
`posix_spawn` do *not* run atfork handlers.

**Example**

```c
pid_t pid = fork();
if (pid == 0) {                 /* child: exec, don't linger */
   execl("/bin/ls", "ls", NULL);
   _exit(127);                 /* NOT exit(): would flush copied stdio */
}
```

**References** -- `fork(2)`, `pthread_atfork(3)`, glibc manual
*Creating a Process*; syscall view: [clone](../../../syscalls/process/overview.md).
