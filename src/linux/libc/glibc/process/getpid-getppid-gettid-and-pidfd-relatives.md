# `getpid`, `getppid`, `gettid` (and pidfd relatives) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-getpid, GLIBC-getppid, GLIBC-gettid, GLIBC-pidfd_getpid, GLIBC-pthread_gettid_np |
| Header | `unistd.h`; `pidfd_getpid`: `sys/pidfd.h` |
| Provenance | getpid/getppid: POSIX.1; gettid/pthread_gettid_np/pidfd_getpid: Linux |
| Wraps | `getpid`, `getppid`, `gettid(2)`, procfs-based `pidfd_getpid(2)` |
| Status | documented (GLIBC-pthread_gettid_np: source-limited) |

**Semantics** -- `getpid`/`getppid` return the process/parent process ID
and cannot fail. Linux threads share the process's PID (thread-group ID)
but each has a kernel thread ID (TID) from the same numbering space: the
main thread's TID equals the PID. `gettid` (GLIBC_2.30) returns the
calling thread's TID; the manual stresses it is "obtained from the Linux
kernel and is not subject to caching" -- the deliberate contrast is that
TIDs of exited threads are reused quickly, so `pidfd` handles or
`/proc` pinning are the durable way to name a thread.

**pidfd_getpid** (GLIBC_2.39) -- recover the PID behind a pidfd from
`pidfd_open`/`pidfd_spawn`; fails with `EBADF`, `ESRCH` (process
terminated), `EREMOTE` (PID untranslatable in caller's namespace),
`ENOENT`/`ENFILE`/`ENOMEM` (procfs-read paths).

**pthread_gettid_np** -- manual-documented (returns what `gettid` would
return on that thread; -1-or-old-TID unspecified for a dead-but-joinable
thread, UB if neither) but **not exported by the installed glibc 2.41**
(`nm -D` check; new manual text, newer release). Status: source-limited.

**References** -- `getpid(2)`, `gettid(2)`, `pidfd_open(2)`; manual
*Process Identification*; syscall view: [pidfd
family](../../../syscalls/process/overview.md).
