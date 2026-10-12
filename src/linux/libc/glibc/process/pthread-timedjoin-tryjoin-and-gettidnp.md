# `pthread_tryjoin_np`, `pthread_timedjoin_np` (and the unexported `pthread_gettid_np`) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status. Sibling: [pthread_join and pthread_detach](pthread-join-and-pthread-detach.md).

| Field | Value |
|---|---|
| ID | GLIBC-pthread_tryjoin_np, -timedjoin_np, -clockjoin_np; GLIBC-pthread_gettid_np (source-limited) |
| Header | `pthread.h` (`_GNU_SOURCE` per man page) |
| Provenance | GNU extensions; tryjoin/timedjoin first appeared glibc 2.3.3 (man VERSIONS); `clockjoin_np` compat symbol `GLIBC_2.31` (nm) |
| Exported | tryjoin/timedjoin default `@@GLIBC_2.34` with compat `@GLIBC_2.2.5`; `clockjoin_np` default `@@GLIBC_2.34` (nm); `pthread_gettid_np` NOT exported by host glibc 2.41 |
| Thread-safety | MT-Safe (man attributes; manual safety notes) |
| Wraps | futex wait on the thread descriptor |
| Status | documented (join trio); source-limited (gettid_np) |

**Semantics** -- `pthread_tryjoin_np` is a nonblocking `pthread_join`: it
returns `EBUSY` instead of blocking when the thread has not terminated
(manual *Joining Threads*; pthread_tryjoin_np.3). `pthread_timedjoin_np`
blocks at most until absolute `abstime` on `CLOCK_REALTIME`; on timeout
the man page documents `ETIMEDOUT` (plus `EINVAL` for a malformed
timespec, and it never returns `EINTR`). Conflict note: the manual's
*Joining Threads* text says `EBUSY` on timeout; the man page says
`ETIMEDOUT`, which matches the implementation -- carry `ETIMEDOUT`
(ledger correction from task 1-j). Man-page BUGS: the timeout is
internally measured against `CLOCK_MONOTONIC`, so discontinuous
`CLOCK_REALTIME` steps do not shorten it. A null `abstime` waits forever;
`pthread_clockjoin_np` takes an explicit clockid (`CLOCK_MONOTONIC` or
`CLOCK_REALTIME`) (manual).

**`pthread_gettid_np` (source-limited)** -- the manual documents it
(*Process Identification* node, Linux-specific: the `gettid(2)` value of
`thread`; unspecified -1 vs stale TID for a terminated joinable thread,
undefined if not running and not joinable), but it is absent from
installed headers and libc.so.6 2.41 (nm: only `gettid @@GLIBC_2.30`);
glibc NEWS in the 2.43-dev snapshot lists it as newly added. No claims
beyond the manual text are possible on this host.

**References** -- `pthread_tryjoin_np(3)`; manual *Joining Threads* node;
manual *Process Identification* node.
