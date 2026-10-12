# `pthread_key_create` / `pthread_getspecific` (TSD family) - glibc

> Split from the chapter *glibc: Process, Threads and Signals* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-pthread_key_create, GLIBC-pthread_key_delete, GLIBC-pthread_getspecific, GLIBC-pthread_setspecific |
| Header | `pthread.h` |
| Provenance | POSIX.1-1996; symbol versions GLIBC_2.34 (compat GLIBC_2.2.5) |
| Wraps | TLS machinery (thread pointer + DTV), no syscall on get/set |
| Status | documented |

**Semantics** -- dynamic thread-specific data: `pthread_key_create(key,
destructor)` allocates a process-wide key visible to all threads; each
thread binds its own `void *` via `pthread_setspecific` and reads it
with `pthread_getspecific` (initially NULL). At thread exit, destructors
run in an unspecified order -- cancellation step 2 in
`pthread_cancel(3)`'s sequence -- each on that thread's value.

**Destructor rules** -- `pthread_key_delete` does **not** run the
destructor (for the calling thread or anyone) and does not free bound
values; the C++11 `thread_local` objects are destroyed *before* TSD
destructors, so a destructor must not touch `thread_local` state or use
such objects as its argument. The ISO C twin (`tss_create` etc.) bounds
destructor re-runs with `TSS_DTOR_ITERATIONS` -- relevant when a
destructor itself creates TSD.

**glibc layer** -- glibc implements this over ELF TLS: the key table
hangs off the thread pointer, so `getspecific` is a couple of loads with
no syscall; a signal handler interrupting `pthread_setspecific`
mid-allocation is the documented AC-unsafe window. `errno` itself is
the canonical TSD user in a threaded program.

**Example**

```c
static pthread_key_t log_key;
pthread_key_create(&log_key, free);
pthread_setspecific(log_key, strdup(name));
char *name = pthread_getspecific(log_key);
```

**References** -- glibc manual *Thread-specific Data*;
`pthread_key_create(3)` semantics via `pthreads(7)`.
