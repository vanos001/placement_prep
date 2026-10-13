# `posix_spawn` and `posix_spawnp` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-posix_spawn, GLIBC-posix_spawnp + 25 file_actions/attr rows |
| Header | `spawn.h` |
| Provenance | POSIX.1-2001; glibc since 2.2 (symbol version GLIBC_2.15, compat GLIBC_2.2.5); `_np`/`SETSID`/`SETCGROUP` are GNU |
| Wraps | `clone(CLONE_VM\|CLONE_VFORK\|SIGCHLD)` + `execve`/`execveat` (glibc >= 2.24) |
| Status | documented |

**Semantics** -- spawn a child that runs `path` (`posix_spawn`) or searches
`PATH` like `execvp` (`posix_spawnp`), performing a bounded, declarative
set of pre-exec housekeeping. Return convention is unlike most libc: **0
or an error number** (no `errno`), and only the *clone step* can fail at
the parent; if any housekeeping or the exec itself fails in the child,
the child exits with **status 127** -- the caller discovers this only via
`waitpid`/`WEXITSTATUS`.

**file_actions** -- `posix_spawn_file_actions_init` then
`addopen`/`addclose`/`adddup2` (POSIX) or `addchdir_np`/`addfchdir_np`/
`addclosefrom_np`/`addtcsetpgrp_np` (GNU, `_MISC`), executed in child in
addition order, then `FD_CLOEXEC` descriptors close.

**attributes (`posix_spawnattr_*`)** -- flag-gated via `setflags`:
`POSIX_SPAWN_SETSIGMASK`, `SETSIGDEF`, `SETPGROUP` (pgroup 0 = new group
of its own), `SETSCHEDPARAM`/`SETSCHEDULER` (before glibc 2.14 requesting
the scheduler without parameters failed -- bug 12052), `RESETIDS`, and GNU
`POSIX_SPAWN_SETSID` (2.26), `SETCGROUP` (cgroup v2 fd), `USEVFORK`
(no-op since 2.24). `POSIX_SPAWN_SETSCHEDULER` needs `_GNU_SOURCE` for
`SETSID`/`SETCGROUP`/`USEVFORK` per `spawn.h`.

**glibc layer / why preferred** -- since 2.24 the child is created with
`clone(CLONE_VM|CLONE_VFORK)`: no page-table copy, parent suspended until
exec, and -- unlike `fork()` -- *no* `pthread_atfork` handlers run (POSIX
leaves this unspecified; glibc 2.24+ never runs them). That makes it
deterministic in libraries, and MMU-less systems can implement it. There
is no `posix_fexecve`; pass a `/proc/self/fd/N` path (or use GNU
`pidfd_spawn`/`pidfd_spawnp`, glibc 2.41 headers, `bits/spawn_ext.h`).

**References** -- `posix_spawn(3)`, `spawn.h`; syscall view:
[execve](../../../syscalls/process/overview.md).
