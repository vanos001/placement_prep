# `sigsuspend`, `sigwait`, `sigwaitinfo` (the wait-for-signal trio) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-sigsuspend, GLIBC-sigwait, GLIBC-sigwaitinfo, GLIBC-sigtimedwait (triage rows) |
| Header | `signal.h` (`sigsuspend` `_POSIX_C_SOURCE`; `sigwait` `__USE_POSIX199506`; `sigwaitinfo`/`sigtimedwait` `__USE_POSIX199309`) |
| Provenance | POSIX.1-2001; `sigtimedwait` POSIX.1b (header gate) |
| Exported | all `@@GLIBC_2.2.5`; internal `__sigtimedwait` `GLIBC_PRIVATE` (nm) |
| Thread-safety | MT-Safe; `sigwait*` are cancellation points (header comment) |
| Wraps | `rt_sigsuspend(2)` / `rt_sigtimedwait(2)` |
| Status | documented |

**Semantics** -- `sigsuspend(set)` swaps the calling thread's mask to
`set`, sleeps until a signal whose action is a handler or termination
arrives, then restores the previous mask; it always returns -1 with `EINTR`
(manual *Sigsuspend*; sigsuspend.2). The atomic mask swap inside one
syscall is what removes the `pause()` race. `sigwait(set, &sig)` suspends
until a signal in `set` is pending and accepts it (removes it from
pending), returning the number; it returns an error number directly
(`EINVAL`; documented as not occurring for glibc) and is implemented via
`sigtimedwait(2)` (sigwait.3). `sigwaitinfo`/`sigtimedwait` additionally
fill a `siginfo_t`, retrieve pending signals in the usual ordering, and
take a timeout (zero = poll; `EAGAIN` on expiry; `EINTR` only from a
handler for a signal outside `set`) (sigwaitinfo.2). Recommended pattern:
block the set first and install no handlers (sigwaitinfo.2 NOTES).

**Gotchas and portability** -- glibc silently ignores the two NPTL-internal
RT signals in `sigwait` (sigwait.3 NOTES). musl: `sigwait` is
`sigtimedwait(mask, &si, NULL)` and `sigsuspend` a raw `rt_sigsuspend`
(`src/signal/sigwait.c`, `sigsuspend.c`).

**References** -- `sigsuspend(2)`, `sigwait(3)`, `sigwaitinfo(2)`; manual
*Sigsuspend* node; [rt_sigsuspend](../../../syscalls/signals-time/rt_sigsuspend.md).
