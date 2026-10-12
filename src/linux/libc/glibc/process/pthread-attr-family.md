# `pthread_attr_*` (attribute object family) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status. Consumer: [pthread_create](pthread-create.md).

| Field | Value |
|---|---|
| ID | GLIBC-pthread_attr_init, -destroy, -setdetachstate, -getdetachstate, -setstacksize, -getstacksize, -setguardsize, -getguardsize, -setstack, -getstack, -setstackaddr/-getstackaddr (triage), -setscope, -gets, -setinheritsched, -gets, -setschedpolicy, -gets, -setschedparam, -gets |
| Header | `pthread.h` |
| Provenance | POSIX.1-1996; `setstackaddr`/`getstackaddr` obsolete (marked obsolete in POSIX.1-2001, pthread_attr_setstackaddr.3) |
| Exported | `init`/`destroy`/`setdetachstate`/`setscope`/`setschedpolicy`/`setschedparam`/`setinheritsched` `@@GLIBC_2.2.5`; stack/guard setters default `@@GLIBC_2.34` with compat `@GLIBC_2.2.5` (nm) |
| Thread-safety | attributes objects are not synchronized; set them before `pthread_create` |
| Wraps | no syscall; the object is consumed by `clone(2)` flags and rlimits at creation |
| Status | documented |

**Semantics** -- `pthread_attr_init` fills an opaque object with defaults
(pthread_attr_init.3); `destroy` releases it and never affects already
created threads. Defaults: `detachstate` `PTHREAD_CREATE_JOINABLE`
(pthread_attr_setdetachstate.3); `guardsize` one page, ignored when the
stack address is set by the application (pthread_attr_setguardsize.3);
`stacksize` minimum `PTHREAD_STACK_MIN` 16384 on this x86_64 host
(`bits/pthread_stack_min.h`), dynamic `sysconf(_SC_THREAD_STACK_MIN)`
under `_GNU_SOURCE`/`_DYNAMIC_STACK_SIZE_SOURCE` since 2.34.

**Errors** -- all return 0 or an error number: `EINVAL` bad value for
`setdetachstate`, `setstacksize`/`setstack` (below `PTHREAD_STACK_MIN`),
`setscope`, `setinheritsched`; `ENOTSUP` for `PTHREAD_SCOPE_PROCESS`
(not supported on Linux); `setguardsize` always succeeds on Linux per its
man page.

**Gotchas and portability** -- defaults for the non-stack knobs are
implementation choice, so query them rather than assume; musl rejects
`setdetachstate` values other than 0/1 and clamps `setstacksize`
(`src/thread/pthread_attr_*.c`).

**References** -- `pthread_attr_init(3)` and the per-attribute man pages;
manual *Creating and Destroying Threads* node.
