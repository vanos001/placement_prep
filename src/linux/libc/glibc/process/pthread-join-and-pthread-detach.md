# `pthread_join` and `pthread_detach` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_join, GLIBC-pthread_detach, GLIBC-pthread_tryjoin_np, GLIBC-pthread_timedjoin_np, GLIBC-pthread_clockjoin_np |
| Header | `pthread.h` |
| Provenance | join/detach: POSIX.1; `*_np` trio: GNU (2.3.3 / 2.3.3 / 2.30) |
| Wraps | futex-based join in libc (no syscall on the fast path) |
| Status | documented |

**Semantics** -- `pthread_join(thread, &retval)` waits for a *joinable*
thread and fetches its exit value (`PTHREAD_CANCELED` = `(void *) -1` if
it was canceled). `pthread_detach(thread)` makes termination
self-cleaning; every thread must be joined *or* detached exactly once or
it lingers as a "zombie thread" -- and there is deliberately **no**
`waitpid(-1)`-style join-any. All threads are peers: any thread can join
any other.

**Return and errors** -- 0 or error number (not `errno`): join --
`EDEADLK` (self-join or detected cycle), `EINVAL` (not joinable or
already being joined), `ESRCH`; detach -- `EINVAL`, `ESRCH`. Joining a
detached or already-joined thread is undefined.

**glibc layer** -- GNU extensions relax the blocking: `pthread_tryjoin_np`
returns `EBUSY` immediately, `pthread_timedjoin_np` adds an absolute
`CLOCK_REALTIME` deadline returning `ETIMEDOUT`, and
`pthread_clockjoin_np` (2.30) takes an explicit clockid (`CLOCK_MONOTONIC`
or `CLOCK_REALTIME`). Note the glibc manual's *Waiting with Explicit
Clocks* text says these "return `EBUSY`" on timeout -- the man page
(`pthread_tryjoin_np(3)`) documents `ETIMEDOUT` and that is what the
implementation returns; the manual wording is a defect.

**References** -- `pthread_join(3)`, `pthread_detach(3)`,
`pthread_tryjoin_np(3)`.
