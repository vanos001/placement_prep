# `sleep`, `usleep`, `nanosleep` - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-sleep, GLIBC-nanosleep (ledger family: Date and Time), GLIBC-usleep (triage row) |
| Header | `unistd.h`; `nanosleep`: `time.h` |
| Provenance | sleep: POSIX.1; nanosleep: POSIX.1-2001; usleep: 4.3BSD, removed by POSIX.1-2008 |
| Wraps | `nanosleep(2)` (glibc `sleep`; other systems may use `alarm(2)`+`SIGALRM`) |
| Status | documented |

**Semantics** -- `sleep(seconds)` returns 0, or the *remaining seconds* if
a signal that is not ignored (or caught with a handler that returns)
arrived first. `nanosleep(req, rem)` is the POSIX-precise form: on
`EINTR` the unslept time is stored in `*rem`; `clock_nanosleep(2)` adds
clock selection. `usleep(usec)` is the obsolete microsecond variant --
`EINVAL` for `usec >= 1000000`, `int` return only since glibc 2.2.2.

**SIGCHLD/SIGALRM interplay (the traps)** --

- sleep ends early on *any* delivered signal; a chatty `SIGCHLD` stream
 therefore starves `sleep` -- the man-page attributes row marks `sleep`
 `MT-Unsafe sig:SIGCHLD/linux` for exactly this class of disturbance,
 and the manual warns against re-`sleep(remaining)` loops because every
 signal shifts the wakeup by a second; compute a deadline and loop
 instead.
- Historically `sleep` was implemented with `alarm(2)`/`SIGALRM`, so
 mixing `alarm` and `sleep` is a bad idea in general; **on glibc it is
 safe** because "sleep does not work by means of SIGALRM" (manual,
 *Sleeping*). Modifying `SIGALRM` disposition from a handler while
 sleeping, or `longjmp`ing out, is undefined. `usleep`'s interaction
 with `alarm`, `setitimer` and timers is simply unspecified.
- `nanosleep` has no alarm coupling; it is the building block of the
 other two.

**References** -- `sleep(3)`, `usleep(3)`, `nanosleep(2)`, manual
*Sleeping*; syscall view: [nanosleep](../../../syscalls/signals-time/overview.md).
