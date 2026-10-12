# io_setup(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | io_setup 206 / 245 / 0 / 243; io_destroy 207 / 246 / 1 / 244; io_getevents 208 / 247 / 4 / 245; io_submit 209 / 248 / 2 / 246; io_cancel 210 / 249 / 3 / 247; io_pgetevents 333 / 385 / 292 / 399; io_pgetevents_time64 - / 416 / - / 416 (hub) |
| Since (kernel) | 2.6 for io_setup/io_destroy/io_getevents/io_submit/io_cancel (hub; io_setup.2 VERSIONS: "first appeared in Linux 2.5" -- conflict recorded, worklog 1-g); io_pgetevents 4.18 (ledger row); time64 twin 5.1-era |
| Man page | man2/io_setup.2, io_destroy.2, io_submit.2, io_cancel.2, io_getevents.2 (all cached); io_pgetevents has no man page in the cached tree (man-pages 6.19 does not ship one) -- sourced from fs/aio.c; overview aio.7 fetched (source-cache/fetched/aio.7.txt) |
| glibc wrapper | none for any of them ("There is no glibc wrapper"; libaio supplies wrappers with io_context_t types and negated-errno returns, io_setup.2 NOTES) |
| Aliases covered | io_destroy, io_submit, io_cancel, io_getevents, io_pgetevents, io_pgetevents_time64 (ledger grouping) |
| Ledger ID | SC-io_setup (+ SC-io_destroy, SC-io_submit, SC-io_cancel, SC-io_getevents, SC-io_pgetevents, SC-io_pgetevents_time64) |

## Purpose

Legacy Linux AIO (async I/O): io_setup() creates an AIO context for
concurrent processing of `nr_events` operations and returns an
aio_context_t handle; io_submit() queues iocbs (IO_CMD_PREAD, PWRITE,
FSYNC, FDSYNC and vectors); io_cancel() attempts to cancel one queued
iocb; io_getevents() reaps completed events (blocking until min_nr when
timeout allows); io_pgetevents() is io_getevents plus an atomic
sigmask save/replace like pselect/ppoll (fs/aio.c io_pgetevents body);
io_destroy() tears the context down. This is the 2.5-era kernel state
machine interface, distinct from POSIX AIO (aio.7) and from io_uring
([io_uring_setup](io_uring_setup.md)).

## Synopsis

```c
#include <linux/aio_abi.h>
long io_setup(unsigned nr_events, aio_context_t *ctx_idp);
long io_destroy(aio_context_t ctx_id);
long io_submit(aio_context_t ctx_id, long nr, struct iocb **iocbpp);
long io_cancel(aio_context_t ctx_id, struct iocb *iocb,
               struct io_event *result);
long io_getevents(aio_context_t ctx_id, long min_nr, long nr,
                  struct io_event *events, struct timespec *timeout);
long io_pgetevents(aio_context_t ctx_id, long min_nr, long nr,
                   struct io_event *events,
                   struct __kernel_timespec *timeout,
                   const struct __aio_sigset *sig);
```

## Arguments and behavior

`ctx_idp` must be initialized to 0 and must not name an existing
context (fs/aio.c: `if (unlikely(ctx || nr_events == 0)) return
-EINVAL;`). iocb fields aio_lio_opcode, aio_fildes, aio_buf, aio_nbytes,
aio_offset drive the operation; aio_flags may set IOCB_FLAG_RESFD
(eventfd notification) and IOCB_FLAG_IOPRIO (aio_reqprio) (installed
/usr/include/linux/aio_abi.h). io_getevents waits until min_nr events
are reaped or `timeout` (NULL = block indefinitely) expires;
io_pgetevents' sig argument is `struct __aio_sigset { sigset_t
__user *sigmask; size_t sigsetsize; }` (fs/aio.c struct). The time64
twin (i386 416) takes struct __kernel_timespec.

## Return value and errors

Raw convention: 0 or the reaped-event count on success; negated errno
on failure (the libaio wrapper returns negated numbers; via syscall(2)
you get -1/errno). Notable: `EAGAIN` (nr_events over aio-max-nr),
`EFAULT`, `EINVAL`, `ENOMEM`, `ENOSYS`; io_getevents `EINTR`
(io_getevents.2); io_submit returns number of iocbs queued or the
negated error of the first failed one (io_submit.2); io_cancel
`EINPROGRESS` when cancellation is not possible (io_cancel.2).

## Flags and constants

IOCB_FLAG_RESFD (1 << 0), IOCB_FLAG_IOPRIO (1 << 1), IO_CMD_* opcodes
from <linux/aio_abi.h>; limits /proc/sys/fs/aio-nr, aio-max-nr
(io_setup.2 EAGAIN).

## Security and notes

- Deprecated-in-practice: development stopped in favor of io_uring
  (5.1); the man pages and aio.7 point new users at io_uring.
- Since conflict: syscalls(2)/hub say 2.6, io_setup.2 VERSIONS says
  "first appeared in Linux 2.5" (worklog 1-g records both).
- io_pgetevents (4.18) and io_pgetevents_time64 have no man pages;
  semantics here are from fs/aio.c.

## References

- Cached man pages: man2/io_{setup,destroy,submit,cancel,getevents}.2;
  fetched aio.7 (source-cache/fetched/aio.7.txt).
- Kernel source: source-cache/fetched/master-fs-aio.c;
  header /usr/include/linux/aio_abi.h.
- Numbers: hub [overview](overview.md); ledger io_* rows.
