# `raise`, `kill`, `killpg` (and the `tgkill` wrapper underneath) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-raise, GLIBC-kill, GLIBC-killpg, GLIBC-tgkill, GLIBC-gsignal |
| Header | `signal.h` (`raise` ungated; `kill` under `__USE_POSIX`; `killpg`, `gsignal` under `__USE_MISC`/XOPEN; `tgkill` under `__USE_GNU`) |
| Provenance | `raise`: ISO C; `kill`: POSIX.1; `killpg`: BSD; `tgkill`: Linux (manual) |
| Exported | `raise` and `gsignal` alias one address `@@GLIBC_2.2.5`; `kill`/`killpg` `@@GLIBC_2.2.5`; `tgkill` `@@GLIBC_2.30` (nm) |
| Thread-safety | MT-Safe / AS-safe (manual safety notes) |
| Wraps | `raise` uses `tgkill(2)`; `killpg` calls `kill(-pgid, sig)` (manual comment) |
| Status | documented |

**Semantics** -- `raise(sig)` signals the caller: single-threaded it equals
`kill(getpid(), sig)`; multithreaded it equals
`pthread_kill(pthread_self(), sig)` (raise.3), i.e. it is thread-directed.
`kill(pid, sig)` is process/group-directed: `pid > 0` one process (on Linux
the whole process even if a TID is passed), `0` the caller's process group,
`-1` all permitted processes, `< -1` process group `-pid`; `sig == 0`
probes for existence (manual, *Signaling Another Process*). `kill`
succeeds if at least one target got the signal; errors
`EINVAL`/`EPERM`/`ESRCH`. Permission: sender privileged, or real/effective
UID match; `SIGCONT` may cross within one session (manual). `killpg` sends
to process group `pgid`; `pgid == 0` means the caller's group (killpg.3).

**Gotchas and portability** -- since glibc 2.3.3 `raise` is `tgkill` with
the caller's TID (raise.3 NOTES); musl's `raise.c` uses `tkill` the same
way, and its `killpg` rejects negative `pgid` with `EINVAL`.

**References** -- `raise(3)`, `kill(2)`, `killpg(3)`; manual *Signaling
Yourself* / *Signaling Another Process* nodes; syscall view:
[kill](../../../syscalls/signals-time/kill.md), [tgkill](../../../syscalls/signals-time/tgkill.md).
