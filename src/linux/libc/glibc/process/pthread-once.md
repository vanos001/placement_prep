# `pthread_once` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_once |
| Header | `pthread.h` |
| Provenance | POSIX.1-1996; symbol version GLIBC_2.34 (compat GLIBC_2.2.5) |
| Wraps | futex/atomic state machine in libc |
| Status | documented |

**Semantics** -- `pthread_once(once_control, init_routine)` invokes
`init_routine` exactly once per `once_control`, even under concurrent
calls from multiple threads; every caller returns only after the
initializer completed (completion synchronizes-with later calls).
`once_control` must be statically initialized to `PTHREAD_ONCE_INIT`
(0) -- it is not a mutex you may initialize at runtime.

**glibc layer** -- the classic implementation is a three-state atomic
(never / in-progress / done) plus a futex wait for callers that arrive
while the initializer is running; the fast path after the first call is
one acquire-load. Compared with C11 `call_once`, the pthread form takes
an explicit control object (C23 moved `once_flag`/`ONCE_FLAG_INIT` into
`stdlib.h`); compared with constructor attributes, `pthread_once` is
per-control-object and lazy -- it runs at first use, not at load time.

**Edge cases** -- `init_routine` itself calling `pthread_once` with the
same control deadlocks; throwing an exception out of the initializer
(through the callback frame) is outside the POSIX contract; never reuse
a `once_control` after error paths -- treat it as write-once state.

**References** -- glibc manual *POSIX Threads Other APIs*;
`pthread_once` man stub in the manual.
