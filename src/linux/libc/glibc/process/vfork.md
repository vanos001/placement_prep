# `vfork` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-vfork |
| Header | `unistd.h` |
| Provenance | BSD; POSIX.1-2001 marked OBSOLETE, removed in POSIX.1-2008 |
| Wraps | `vfork(2)` = `clone(CLONE_VM\|CLONE_VFORK\|SIGCHLD)`; falls back to `fork` where no vfork syscall exists |
| Status | documented |

**Semantics** -- create a child that *shares* the parent's address space
and stack until it calls `_exit(2)` or an `exec` function, while the
calling thread is suspended. The POSIX contract is almost pure
undefined behavior: the child may only modify a `pid_t` holding the
return value, must not return from (or `longjmp` out of) the function
that called `vfork`, and must call no other function before
`_exit`/`exec`. Violations corrupt the *parent*: the manual's example of
danger is signal handlers and, in multithreaded programs, a parent
thread dropping credentials while the privileged child still shares its
memory.

**glibc layer** -- NPTL's `vfork` does **not** run `pthread_atfork`
handlers (LinuxThreads did). Signals sent to the parent arrive only
after the child releases the shared memory. The value of `vfork` today
is mostly historical: `fork(2)` is copy-on-write anyway; vfork avoids
page-table copies and can exist on MMU-less systems -- which is also why
`posix_spawn` builds on `CLONE_VM|CLONE_VFORK` internally since glibc
2.24 rather than on user-visible `vfork`.

**Edge cases** -- feature-test gated (`_DEFAULT_SOURCE`, or
`_XOPEN_SOURCE >= 500` with `!_POSIX_C_SOURCE >= 200809L`). An
implementation where `vfork` == `fork` is fully compliant, so nothing
can be relied on beyond the UB-safe subset: compute args, exec, `_exit`.

**References** -- `vfork(2)` (standard, Linux, historic sections), glibc
manual *Creating a Process*; syscall view:
[vfork](../../../syscalls/process/overview.md).
