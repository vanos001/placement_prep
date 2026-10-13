# `sigemptyset`, `sigfillset`, `sigaddset` (signal set operations) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-sigemptyset, -sigfillset, -sigaddset, -sigdelset, -sigismember, -sigisemptyset, -sigorset, -sigandset |
| Header | `signal.h` |
| Provenance | POSIX.1-2001 (gate `_POSIX_C_SOURCE`); GNU ops need `_GNU_SOURCE` |
| Exported | all default `@@GLIBC_2.2.5` (nm, libc.so.6 2.41 x86_64) |
| Thread-safety | MT-Safe (sigsetops.3 attributes table) |
| Wraps | no syscall: in-process bit-set code (manual: sigemptyset "just memsets all of set to zero") |
| Status | documented |

**Semantics** -- `sigset_t` is opaque (integer or struct type; the manual
forbids direct manipulation). Every set must be initialized with
`sigemptyset` (exclude all signals) or `sigfillset` (include all) before
`sigaddset`/`sigdelset`/`sigismember` or the GNU ops touch it; results are
undefined otherwise (sigsetops.3). `sigemptyset`/`sigfillset` always return
0 (manual, *Signal Sets*). `sigaddset`/`sigdelset` return 0 or -1 with
`EINVAL` for an invalid signal number; `sigismember` returns 1 / 0 / -1.
Set edits never block or unblock anything (manual).

**GNU extensions** -- under `_GNU_SOURCE`, `sigisemptyset` (1 if empty),
`sigorset`/`sigandset` (dest = union / intersection of left and right,
0 or -1); nonstandard, avoid in portable code (sigsetops.3).

**Gotchas and portability** -- glibc `sigfillset` excludes the two
real-time signals NPTL uses internally (sigsetops.3 NOTES); musl's
`sigfillset.c` clears the same two bits, so "filled" is not "every number".
musl also ships the GNU ops and `bsd_signal` but has no `sysv_signal`.

**References** -- `sigsetops(3)`; manual *Signal Sets* node; musl
`src/signal/sigfillset.c`; syscall view: [rt_sigprocmask](../../../syscalls/signals-time/rt_sigprocmask.md).
