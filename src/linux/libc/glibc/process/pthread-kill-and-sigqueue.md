# `pthread_kill`, `sigqueue` (and GNU `pthread_sigqueue`) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_kill, GLIBC-sigqueue, GLIBC-pthread_sigqueue (triage row) |
| Header | `signal.h` (`pthread_kill` via `bits/sigthread.h`; `sigqueue` under `__USE_POSIX199309`; `pthread_sigqueue` under `__USE_GNU`) |
| Provenance | `pthread_kill`: POSIX.1-2001; `sigqueue`: POSIX.1b (`_POSIX_C_SOURCE >= 199309`); `pthread_sigqueue`: GNU, first appeared glibc 2.11 |
| Exported | `pthread_kill` `@@GLIBC_2.34` (compat `@GLIBC_2.2.5`); `pthread_sigqueue` `@@GLIBC_2.34` (compat `@GLIBC_2.11`); `sigqueue` `@@GLIBC_2.2.5` (nm) |
| Thread-safety | MT-Safe (man attributes tables) |
| Wraps | `tgkill(2)` / `rt_sigqueueinfo(2)` (sigqueue.3 C library/kernel notes) |
| Status | documented |

**Semantics** -- `pthread_kill(thread, sig)` asynchronously directs `sig`
to a thread in the caller's process; `sig == 0` performs error checking
only; returns 0 or an error number (`EINVAL` invalid signal)
(pthread_kill.3). Dispositions stay process-wide: a handler runs in the
target thread, but stop/continue/terminate actions hit the whole process;
POSIX.1-2008 recommends `ESRCH` for a dead thread ID, yet a stale ID is
undefined behavior and can crash (pthread_kill.3 NOTES).
`sigqueue(pid, sig, value)` queues a signal plus a `union sigval` (int or
pointer); an `SA_SIGINFO` handler reads it as `si_value` with
`si_code == SI_QUEUE`; errors `EAGAIN` (queue limit), `EINVAL`, `EPERM`,
`ESRCH` (sigqueue.3). The wrapper fills the kernel's `siginfo_t`:
`si_signo`, `si_code = SI_QUEUE`, `si_pid = getpid()`, `si_uid = getuid()`,
`si_value` (sigqueue.3). `pthread_sigqueue` is the same payload to a
thread of the same process; `ENOSYS` possible (pthread_sigqueue.3).

**Gotchas and portability** -- glibc `pthread_kill` rejects the two
NPTL-internal RT signals with `EINVAL`; musl serializes with a `killlock`
around `tkill` (`src/thread/pthread_kill.c`) and builds identical
`si_*` fields in `sigqueue.c`.

**References** -- `pthread_kill(3)`, `sigqueue(3)`, `pthread_sigqueue(3)`,
`rt_sigqueueinfo(2)`; [tgkill](../../../syscalls/signals-time/tgkill.md).
