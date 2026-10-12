# `sigaltstack`, `sigstack` (libc wrappers and stack-size macros) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status. The kernel side of `sigaltstack` is documented in the syscall chapter: [sigaltstack](../../../syscalls/signals-time/sigaltstack.md).

| Field | Value |
|---|---|
| ID | GLIBC-sigaltstack, GLIBC-sigstack |
| Header | `signal.h` (sizes in `bits/sigstack.h`; legacy `struct sigstack` in `bits/types/struct_sigstack.h`) |
| Provenance | `sigaltstack`: XPG (manual); gates `_XOPEN_SOURCE >= 500`, or `_POSIX_C_SOURCE >= 200809L` since glibc 2.12; `sigstack`: 4.2BSD, superseded |
| Exported | `sigaltstack` W `@@GLIBC_2.2.5`; `sigstack` T `@@GLIBC_2.2.5` (nm) |
| Thread-safety | MT-Safe (manual safety notes: syscall on Linux) |
| Wraps | `sigaltstack(2)` |
| Status | documented |

**Semantics** -- register an alternate stack (`stack_t`: `ss_sp`,
`ss_size`, `ss_flags`) for handlers installed with `SA_ONSTACK`;
`SS_ONSTACK` marks the stack in use, `SS_DISABLE` disables it. Errors:
`EINVAL` (disabling a stack in use), `ENOMEM` (size at or below
`MINSIGSTKSZ`) per the manual *Signal Stack* node; sigaltstack.2 adds
`EPERM` (changing an active stack) and kernel alignment of `ss_sp`. With
`SA_ONSTACK` but no installed stack the normal stack is used (manual).

**Stack-size macros, the glibc 2.34 change** -- `bits/sigstack.h` on this
host defines `MINSIGSTKSZ` 2048 and `SIGSTKSZ` 8192; since glibc 2.34,
with `_GNU_SOURCE` or `_DYNAMIC_STACK_SIZE_SOURCE`, both become
non-constant: `sysconf(_SC_MINSIGSTKSZ)` / `sysconf(_SC_SIGSTKSZ)`
(NEWS; `bits/sigstksz.h`), for dynamically sized register sets (Arm SVE).

**Gotchas and portability** -- the alternate stack is per-thread: a new
thread does not inherit the creator's (pthread_create.3). `sigstack`
(4.2BSD) predates `sigaltstack` (4.4BSD) and forces the caller to know the
stack growth direction (sigaltstack.2 History; manual). musl validates
`ss_size < MINSIGSTKSZ` -> `ENOMEM` and `SS_ONSTACK` -> `EINVAL` in user
space before the syscall (`src/signal/sigaltstack.c`).

**References** -- `sigaltstack(2)`; manual *Signal Stack* node; glibc NEWS
2.34.
