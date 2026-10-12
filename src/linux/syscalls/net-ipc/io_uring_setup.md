# io_uring_setup(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | io_uring_setup 425; io_uring_enter 426; io_uring_register 427 -- same on all four (hub + cached tables) |
| Since (kernel) | 5.1 (hub/ledger; the man7 pages carry no VERSIONS section) |
| Man page | man2/io_uring_setup.2, io_uring_enter.2, io_uring_register.2 -- fetched from man7.org into source-cache/fetched/ (man-pages 6.19, liburing-maintained) |
| glibc wrapper | none: no io_uring symbols in glibc 2.41 (nm -D); synopsis uses <liburing.h> or raw syscall(2) |
| Aliases covered | io_uring_enter (SC-io_uring_enter), io_uring_register (SC-io_uring_register), documented inline |
| Ledger ID | SC-io_uring_setup |

## Purpose

io_uring_setup() creates an io_uring instance: a submission queue (SQ)
and completion queue (CQ) of at least `entries` entries, shared
between userspace and kernel so initiating and completing I/O needs no
copies. It returns an fd used for io_uring_enter(2) (submit/complete;
SC-io_uring_enter) and io_uring_register(2) (register resources;
SC-io_uring_register). An eventfd can be registered so completions
surface in an event loop (see [eventfd](eventfd.md)). The mmap(2)-ed
offsets are returned in `params->sq_off`/`cq_off`
(IORING_FEAT_SINGLE_MMAP, 5.4, allows one mmap for both rings).

## Synopsis

```c
#include <liburing.h>
int io_uring_setup(u32 entries, struct io_uring_params *params);
```

## Arguments and behavior

params passes options in and carries back sizes, `features` and the
mmap offsets; resv must be zeroed. IORING_SETUP_* flags (values from
/usr/include/linux/io_uring.h; brief group overview):

| Flag | Value | Since | Meaning |
|---|---|---|---|
| IORING_SETUP_IOPOLL | 1U<<0 | 5.1 | busy-wait completions; O_DIRECT storage only |
| IORING_SETUP_SQPOLL | 1U<<1 | 5.1 | kernel SQ-polling thread; zero-syscall submission |
| IORING_SETUP_SQ_AFF | 1U<<2 | 5.1 | bind poll thread to sq_thread_cpu |
| IORING_SETUP_CQSIZE | 1U<<3 | 5.1 | app-defined cq_entries |
| IORING_SETUP_CLAMP | 1U<<4 | 5.1 | clamp oversized ring sizes |
| IORING_SETUP_ATTACH_WQ | 1U<<5 | 5.1 | share wq_fd's worker pool |
| IORING_SETUP_R_DISABLED | 1U<<6 | 5.10 | start disabled; enable via io_uring_register |
| IORING_SETUP_SUBMIT_ALL | 1U<<7 | 5.18 | keep submitting past an error |
| IORING_SETUP_COOP_TASKRUN / TASKRUN_FLAG | 1U<<8 / 1U<<9 | 5.19 | avoid IPIs; IORING_SQ_TASKRUN flag |
| IORING_SETUP_SQE128 / CQE32 | 1U<<10 / 1U<<11 | 5.19 | 128-byte SQEs / 32-byte CQEs |
| IORING_SETUP_SINGLE_ISSUER | 1U<<12 | 6.0 | single submitter hint, kernel-enforced |
| IORING_SETUP_DEFER_TASKRUN | 1U<<13 | 6.1 | defer work to GETEVENTS enter calls |
| IORING_SETUP_NO_MMAP / REGISTERED_FD_ONLY / NO_SQARRAY | 1U<<14/15/16 | 6.5 / 6.5 / 6.6 | caller-provided ring memory; registered-only fd; direct-indexed SQ |
| IORING_SETUP_HYBRID_IOPOLL, CQE_MIXED, SQ_REWIND | in headers/newer pages | 6.x+ | in linux/io_uring.h / current man7 page; release pins unverified |

io_uring_enter(fd, to_submit, min_complete, flags, sig) submits SQEs
and/or waits: IORING_ENTER_GETEVENTS waits for min_complete events;
EXT_ARG (5.11) passes a struct io_uring_getevents_arg {sigmask,
sigmask_sz, pad, ts} adding a timeout; REGISTERED_RING uses a
registered fd index; SQPOLL rings use SQ_WAKEUP/SQ_WAIT. SQEs may be
reused once the syscall reports them consumed -- the kernel copies
what it still needs. io_uring_register(fd, opcode, arg, nr_args)
registers long-lived resources -- buffers (pinned iovecs charged to
RLIMIT_MEMLOCK, used via IORING_OP_READ/WRITE_FIXED), files,
eventfds, personalities, restrictions -- and enables R_DISABLED
rings.

## Return value and errors

setup: new fd; errors include EINVAL (nonzero resv, unsupported flag,
bad entries/cq_entries, SQ_AFF without SQPOLL), EMFILE, ENFILE,
ENOMEM, EPERM (SQPOLL without privilege; or io_uring_disabled sysctl
= 2, or = 1 without CAP_SYS_ADMIN/io_uring_group), ENXIO (bad
ATTACH_WQ fd) (fetched io_uring_setup.2). enter returns the number of
SQEs consumed -- errors for particular SQEs arrive as CQEs, not errno
(fetched io_uring_enter.2 RETURN VALUE; EAGAIN/EBADF/EBUSY/EEXIST/
EFAULT/EINTR/EINVAL/ENXIO/EOPNOTSUPP/EOWNERDEAD/EBADFD/EBADR listed
there). register returns 0 or a negative errno (fetched
io_uring_register.2).

## Flags and constants

See the IORING_SETUP_* table; enter flags IORING_ENTER_GETEVENTS,
SQ_WAKEUP, SQ_WAIT, EXT_ARG, REGISTERED_RING, ABS_TIMER (6.12),
EXT_ARG_REG (6.13), NO_IOWAIT (6.15) are in the fetched
io_uring_enter.2 and /usr/include/linux/io_uring.h.

## Security and notes

Not multiplexed, not aliased: all four arch columns agree (425-427).
The kernel can disable io_uring entirely via
/proc/sys/kernel/io_uring_disabled (fetched page). SQPOLL history:
before 5.11 it needed pre-registered files (IORING_REGISTER_FILES)
and root; 5.11 relaxed to CAP_SYS_NICE; 5.13+ unprivileged. The man
pages are maintained in liburing, not man-pages proper (worklog
1-g); header values above verified in /usr/include/linux/io_uring.h.

## References

- Fetched pages: source-cache/fetched/io_uring_setup.2.txt, io_uring_enter.2.txt, io_uring_register.2.txt (man7.org, man-pages 6.19; worklog 1-g).
- Flags: /usr/include/linux/io_uring.h (installed).
- Numbers/Since: hub overview.md; source-cache/kernel/syscall_64.tbl (425-427).
- Worklog Task 1-g (liburing-maintained note; io_* 2.6 vs 2.5 conflict concerns the legacy AIO family, not io_uring).
