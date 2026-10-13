# musl: threads

| Field | Value |
|---|---|
| musl version | 1.2.5 (WHATSNEW) |
| Key source files | `src/thread/pthread_create.c`, `src/internal/pthread_impl.h`, `src/thread/default_attr.c`, `src/thread/synccall.c`, `src/unistd/setxid.c`, `src/thread/pthread_mutexattr_setprotocol.c`, `src/thread/{cnd_*,mtx_*,tss_*,call_once}.c` |
| glibc counterpart pages | [pthread_create](../glibc/process/pthread-create.md), [pthread_attr family](../glibc/process/pthread-attr-family.md), [cancellation](../glibc/process/pthread-cancel-and-the-cancellation-family.md), [pthread_kill/sigqueue](../glibc/process/pthread-kill-and-sigqueue.md), [pthread_sigmask](../glibc/process/pthread-sigmask.md) |
| Ledger | MUSL-family-pthread / MUSL-family-threads rows; ledger-musl.md `pthread.h` (108), `threads.h` (25) |

## Implementation notes

1:1 threads via the arch `clone` wrapper with `CLONE_VM|...|CLONE_SETTLS|
CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID` (`src/thread/pthread_create.c`).
Each thread mmaps guard + stack + TLS + TSD in one region; the thread pointer
(`tp`) points at the TCB described by `struct __pthread`
(`src/internal/pthread_impl.h`). Defaults come from `default_attr.c`:
`DEFAULT_STACK_SIZE` 131072 and `DEFAULT_GUARD_SIZE` 8192
(`pthread_impl.h`), overridable via `pthread_setattr_default_np` (declared
`include/pthread.h`). C11 `threads.h` (cnd/mtx/tss/call_once) is implemented
in `src/thread/` on the same primitives. set*id in a multithreaded process
broadcasts through `__synccall` (`src/thread/synccall.c`): a signal stops
every thread, each runs the callback, and partial failure of setxid SIGKILLs
the process (`src/unistd/setxid.c`). Note: no "TPIE" token exists in
`src/thread/` (rg); the thread-pointer notes above are the closest sourced
content (brief's TPIE reference unverified).

## Deltas vs glibc (verified)

- `PTHREAD_STACK_MIN` is 2048 (`include/limits.h`); glibc 2.41 x86-64 uses
  16384 and can make it dynamic (`bits/pthread_stack_min-dynamic.h`).
- No `pthread_sigqueue` (rg; glibc exports it, `@@GLIBC_2.34`, nm -D).
- `PTHREAD_PRIO_PROTECT` returns ENOTSUP; `PTHREAD_PRIO_INHERIT` probes
  `FUTEX_LOCK_PI` (`pthread_mutexattr_setprotocol.c`).
- 1.2.1 WHATSNEW added `PTHREAD_NULL`; 1.2.2 lifted child restrictions after
  fork of a multithreaded parent and added `_Fork`; 1.2.5 made `clone`
  consistent with `_Fork`.

## Porting notes

Assumptions of an 8 MiB default stack (glibc derives it from RLIMIT_STACK,
pthread_create(3)) break at musl's 128 KiB; size stacks explicitly.
`pthread_sigqueue` needs a signal-to-thread redesign. set*id cost is O(threads)
by design.
