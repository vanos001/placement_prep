# userfaultfd(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 323 / 374 / 282 / 388 |
| Since (kernel) | 4.3 |
| Man page | man2/userfaultfd.2 (cached, dated 2021-03-22); ioctl detail lives in ioctl_userfaultfd(2) |
| glibc wrapper | none (man page: glibc provides no wrapper; use syscall(2)) |
| Aliases covered | none |
| Ledger ID | SC-userfaultfd |

## Purpose

`userfaultfd()` creates a file descriptor for a **userfaultfd object**: a
kernel mechanism that delegates page-fault handling to user space. A
monitor thread (or a separate process, in non-cooperative mode) reads fault
events from the descriptor and resolves them with ioctls -- `UFFDIO_COPY`
to fill in real contents, `UFFDIO_ZEROPAGE` for zero pages. Use cases
(man NOTES): user-space paging, lazy restore for checkpoint/restore,
post-copy live migration of VMs and containers. When the last descriptor
is closed, all registrations are torn down and unread events flushed.

## Synopsis

```c
#include <fcntl.h>          /* O_CLOEXEC, O_NONBLOCK */
#include <sys/syscall.h>    /* SYS_userfaultfd */
#include <unistd.h>
int syscall(SYS_userfaultfd, int flags);
```

## Arguments and behavior

`flags` may contain `O_CLOEXEC` and `O_NONBLOCK` (changeable later via
`fcntl(2)`); other values give `EINVAL`. The object must first be enabled
with the `UFFDIO_API` ioctl -- a handshake negotiating the API version and
selecting feature bits; every other ioctl fails with `EINVAL` until then.
Ranges are then registered with `UFFDIO_REGISTER` in one or more modes
(table below). Reads return one or more `struct uffd_msg` events:
`UFFD_EVENT_PAGEFAULT` (4.3), and, since 4.11 with matching feature bits,
`UFFD_EVENT_FORK`, `UFFD_EVENT_REMAP`, `UFFD_EVENT_REMOVE`,
`UFFD_EVENT_UNMAP` for non-cooperative monitoring of layout changes.

## Return value and errors

New file descriptor on success; -1 with `errno` on failure. Documented
errors: `EINVAL` (unsupported flags), `EMFILE`/`ENFILE` (fd limits),
`ENOMEM`, and `EPERM` (since Linux 5.2: caller lacks `CAP_SYS_PTRACE` in
the initial user namespace while `/proc/sys/vm/unprivileged_userfaultfd`
is 0). `read(2)` on the descriptor fails with `EINVAL` before `UFFDIO_API`.

## Flags and constants

Creation flags `O_CLOEXEC` and `O_NONBLOCK` (values from `fcntl.h`).
Constants from installed `linux/userfaultfd.h`:

| Constant | Value | Note |
|---|---|---|
| UFFD_API | 0xAA | API version negotiated by UFFDIO_API |
| UFFDIO_REGISTER_MODE_MISSING | (1<<0) | fault on missing page (4.10) |
| UFFDIO_REGISTER_MODE_WP | (1<<1) | fault on write to write-protected page (5.7) |
| UFFDIO_REGISTER_MODE_MINOR | (1<<2) | minor-fault mode, shmem/hugetlbfs; header only in cache |
| UFFD_FEATURE_PAGEFAULT_FLAG_WP | (1<<0) | write-protect support probe |
| UFFD_FEATURE_EVENT_FORK / REMAP / REMOVE / UNMAP | (1<<1) / (1<<2) / (1<<3) / (1<<6) | non-cooperative event bits |
| UFFD_FEATURE_MISSING_HUGETLBFS / MISSING_SHMEM | (1<<4) / (1<<5) | missing-mode mapping coverage |
| UFFD_FEATURE_SIGBUS | (1<<7) | faults become SIGBUS, no notification (4.14) |
| UFFD_FEATURE_THREAD_ID | (1<<8) | embed faulting thread ID (4.14) |
| UFFD_FEATURE_MINOR_HUGETLBFS / MINOR_SHMEM | (1<<9) / (1<<10) | minor-mode coverage |
| UFFD_FEATURE_EXACT_ADDRESS | (1<<11) | registered range kept exact |
| UFFD_FEATURE_WP_HUGETLBFS_SHMEM / WP_UNPOPULATED / WP_ASYNC | (1<<12) / (1<<13) / (1<<15) | WP coverage extensions |
| UFFD_FEATURE_POISON / MOVE | (1<<14) / (1<<16) | UFFDIO_POISON / UFFDIO_MOVE support |
| UFFD_PAGEFAULT_FLAG_WRITE / FLAG_WP | bit flags | fault classification in uffd_msg |

`UFFD_FEATURE_SIGBUS` (4.14) turns faults into `SIGBUS` instead of
notifications, for monitor-less robustness use.

### ioctl list (brief)

`UFFDIO_API`, `UFFDIO_REGISTER`, `UFFDIO_UNREGISTER`, `UFFDIO_WAKE`,
`UFFDIO_COPY`, `UFFDIO_ZEROPAGE`, `UFFDIO_MOVE`, `UFFDIO_WRITEPROTECT`,
`UFFDIO_CONTINUE`, `UFFDIO_POISON` (names from installed
`linux/userfaultfd.h`; UFFDIO_CONTINUE/MOVE/POISON postdate the cached 2021
man page and are header-sourced only). Details belong to
ioctl_userfaultfd(2).

## Security and notes

- Unprivileged use is policy-controlled: since 5.2 the kernel returns
  `EPERM` unless the caller has `CAP_SYS_PTRACE` or the sysctl
  `vm.unprivileged_userfaultfd` is 1 (man ERRORS; the sysctl exists to
  blunt fault-handling side-channel attacks).
- Up to 4.11 only anonymous private mappings were supported; 4.11 added
  hugetlbfs and shmem (man VERSIONS). With `O_NONBLOCK` off, poll/select
  report POLLERR (documented oddity, man).
- Known bug: `UFFD_FEATURE_EVENT_FORK` + interrupted/failed fork can emit a
  stale descriptor and a spurious `UFFD_EVENT_FORK` (man BUGS).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/userfaultfd.2`
  (events, feature-bit behavior, EPERM/5.2, BUGS).
- Header: `/usr/include/linux/userfaultfd.h` (UFFD_API 0xAA, register
  modes, feature-bit values, ioctl command names).
- Numbers: hub [overview](overview.md); cached kernel syscall tables.
