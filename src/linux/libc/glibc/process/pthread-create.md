# `pthread_create` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

## Threads (NPTL)

| Field | Value |
|---|---|
| ID | GLIBC-pthread_create, GLIBC-pthread_self, GLIBC-pthread_equal |
| Header | `pthread.h` |
| Provenance | POSIX.1-1996; NPTL implementation; symbol version GLIBC_2.34 (compat GLIBC_2.2.5) |
| Wraps | `clone(2)`/`clone3(2)` with thread flags (`CLONE_VM\|CLONE_FILES\|CLONE_SIGHAND\|CLONE_THREAD\|...`) |
| Status | documented |

**Semantics** -- start a thread running `start_routine(arg)`; store its
`pthread_t` in `*thread`. `attr == NULL` means defaults. Inheriting
rules: the new thread gets a copy of the creator's signal mask, an empty
pending-signal set, and does **not** inherit the alternate signal stack;
it inherits the FP environment, capabilities and CPU affinity mask.

**Error return convention (the interview trap)** -- returns **0 or an
error number directly**: it does not set `errno` and never returns -1.
Errors: `EAGAIN` (resources or a system limit: `RLIMIT_NPROC`,
`threads-max`, `pid_max`), `EINVAL` (bad attr), `EPERM` (sched policy
not permitted). Set `errno = s; perror(...)` to report.

**Attributes and stack size defaults** -- `pthread_attr_t` knobs:
detachstate (default `PTHREAD_CREATE_JOINABLE`), scope, inheritsched,
schedpolicy/param, guardsize (default one page, 4096), stackaddr/
stacksize. NPTL default stack: `RLIMIT_STACK` at program start if
finite, else per-architecture (x86_64 2 MiB, i386 2 MiB, IA-64 32 MiB).
Under `_GNU_SOURCE`/`_DYNAMIC_STACK_SIZE_SOURCE` (glibc 2.34),
`PTHREAD_STACK_MIN` itself becomes `sysconf(_SC_THREAD_STACK_MIN)`.

**Edge cases** -- which thread runs first after creation is
indeterminate (absent real-time scheduling); returning from
`start_routine` is `pthread_exit(return_value)`; `pthread_equal`
compares IDs; `pthread_self` returns the caller's.

**Example**

```c
pthread_t t; int s = pthread_create(&t, NULL, worker, arg);
if (s != 0) { errno = s; perror("pthread_create"); }
```

**References** -- `pthread_create(3)`, `pthread_attr_init(3)`,
`clone(2)`; manual *Creating and Destroying Threads*; syscall view:
[clone](../../../syscalls/process/overview.md); model context:
[threads](../../../sysprog/threads.md).
