# `signal` / `sysv_signal` (the SysV signal() API) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-signal, GLIBC-sysv_signal, GLIBC-ssignal, GLIBC-bsd_signal (triage row) |
| Header | `signal.h` |
| Provenance | `signal`: ISO C (manual); `sysv_signal`: GNU; `ssignal`: SVID; `bsd_signal`: X/Open |
| Exported | `signal`/`ssignal`/`bsd_signal` share one address, `sysv_signal` separate; all `@@GLIBC_2.2.5` (nm) |
| Thread-safety | MT-Safe (manual safety notes flag the `siginterrupt` interaction) |
| Wraps | `sigaction(2)` internally (manual safety comments) |
| Status | documented |

**Semantics** -- install `SIG_DFL`, `SIG_IGN`, or a handler for `signum`;
return the previous action, or `SIG_ERR` with `EINVAL` on an invalid number
or an attempt to touch `SIGKILL`/`SIGSTOP` (manual, *Basic Signal
Handling*). Setting `SIG_IGN` (or `SIG_DFL` for a default-ignore signal)
discards pending instances even if blocked.

**SA_RESTART semantics** -- glibc's `signal` sets every `sigaction` flag to
zero except `SA_RESTART`, whose value follows the last `siginterrupt` call
(manual, *Flags for Sigaction*). With the flag set, a resumed `read`/`write`
continues after the handler returns; with it clear the call fails `EINTR`.

**BSD vs SysV history** -- SVID deinstalls the handler after one delivery;
BSD keeps it installed. glibc uses the BSD form by default (header: BSD
code is guarded by `__USE_MISC`; without it `signal` is redirected to
`__sysv_signal`); `_XOPEN_SOURCE` selects the SVID form. The manual's
verdict: unreliable, prefer `sigaction`. `ssignal`/`gsignal` are SVID
aliases. musl compiles `signal` with `SA_RESTART` and weak-aliases
`__sysv_signal` to it, so no SVID mode exists there (`src/signal/signal.c`).

**References** -- manual *Basic Signal Handling* node; `signal(2)`;
syscall view: [rt_sigaction](../../../syscalls/signals-time/rt_sigaction.md).
