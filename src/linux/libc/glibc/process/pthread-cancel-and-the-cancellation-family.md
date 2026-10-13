# `pthread_cancel` and the cancellation family - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_cancel, GLIBC-pthread_setcancelstate, GLIBC-pthread_setcanceltype, GLIBC-pthread_testcancel, GLIBC-_pthread_cleanup_push, GLIBC-_pthread_cleanup_pop (+ _restore/_push_defer triage rows) |
| Header | `pthread.h` |
| Provenance | POSIX.1-1996; `pthread_cancel` symbol version GLIBC_2.34 (compat GLIBC_2.2.5) |
| Wraps | internal signal + futex machinery (NPTL uses the first real-time signal, 32) |
| Status | documented |

**Semantics** -- `pthread_cancel(thread)` queues a cancellation request;
whether/when it fires is the *target's* choice: cancelability **state**
`PTHREAD_CANCEL_ENABLE` (default) or `DISABLE` (request stays queued)
via `pthread_setcancelstate`, and **type** `PTHREAD_CANCEL_DEFERRED`
(default) or `PTHREAD_CANCEL_ASYNCHRONOUS` via `pthread_setcanceltype`.


> **Recovered portion.** The persisted source snapshot ends here; cancellation points, `pthread_testcancel`, cleanup handlers and the remaining thread/signal/job-control families are being re-authored from the glibc manual and man3 pages.
