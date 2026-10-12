# `pthread_sigmask` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_sigmask |
| Header | `signal.h` (declared in `bits/sigthread.h`, included under `__USE_POSIX199506` or `__USE_UNIX98`) |
| Provenance | POSIX.1-1995; man gate `_POSIX_C_SOURCE >= 199506L || _XOPEN_SOURCE >= 500` |
| Exported | default `@@GLIBC_2.32` with compat `@GLIBC_2.2.5` (nm, libc.so.6 2.41 x86_64) |
| Thread-safety | MT-Safe (pthread_sigmask.3 attributes) |
| Wraps | `rt_sigprocmask(2)` (musl `src/thread/pthread_sigmask.c`) |
| Status | documented |

**Semantics** -- examine or change the signal mask of the *calling thread*;
`how` is `SIG_BLOCK` (union), `SIG_UNBLOCK` (remove), or `SIG_SETMASK`
(replace); `oldset` receives the previous mask, and a null `set` queries
without changing (manual *Process Signal Mask*). Returns 0 or an error
number directly, never -1; errors are those of `sigprocmask` (`EINVAL` for
a bad `how`) (pthread_sigmask.3).

**Why not `sigprocmask`** -- each thread owns its own mask and there is no
single process mask; POSIX marks `sigprocmask` in a multithreaded process
"unspecified", so use `pthread_sigmask` there (manual *Process Signal
Mask*).

**Gotchas and portability** -- a new thread inherits a copy of its
creator's mask (pthread_sigmask.3 NOTES; manual *Initial Thread Signal
Mask* shows `pthread_attr_setsigmask_np` as the per-attribute alternative).
glibc silently ignores attempts to block the two real-time signals NPTL
uses internally (pthread_sigmask.3 NOTES). The mask survives `fork` and
`exec` (manual). musl additionally validates `how` up front and clears the
two internal-signal bits out of the returned old mask
(`src/thread/pthread_sigmask.c`).

**References** -- `pthread_sigmask(3)`, `rt_sigprocmask(2)`; manual
*Process Signal Mask* node; syscall view:
[rt_sigprocmask](../../../syscalls/signals-time/rt_sigprocmask.md);
thread context: [threads](../../../sysprog/threads.md).
