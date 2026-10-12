# process_vm_readv(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | process_vm_readv 310 / 347 / 270 / 376; process_vm_writev 311 / 348 / 271 / 377 (hub) |
| Since (kernel) | 3.2 (hub; man VERSIONS: "added in Linux 3.2") |
| Man page | man2/process_vm_readv.2 (cached, dated 2021-03-22; process_vm_writev.2 is the canonical companion -- both names on one page) |
| glibc wrapper | yes for both, in libc since glibc 2.15 (man VERSIONS); needs _GNU_SOURCE |
| Aliases covered | process_vm_writev (SC-process_vm_writev, grouped per ledger) |
| Ledger ID | SC-process_vm_readv |

## Purpose

process_vm_readv() transfers data from the address space of process
`pid` (the "remote process") into the calling process; process_vm_writev()
is the converse. Data moves directly between the two address spaces
without a kernel-space bounce, designed for fast message passing (a
single copy where pipes or shared memory would need two). Permission is
governed by a ptrace access mode PTRACE_MODE_ATTACH_REALCREDS check on
the target (man).

## Synopsis

```c
#include <sys/uio.h>
ssize_t process_vm_readv(pid_t pid,
                         const struct iovec *local_iov, unsigned long liovcnt,
                         const struct iovec *remote_iov, unsigned long riovcnt,
                         unsigned long flags);
ssize_t process_vm_writev(pid_t pid,
                          const struct iovec *local_iov, unsigned long liovcnt,
                          const struct iovec *remote_iov, unsigned long riovcnt,
                          unsigned long flags);
```

## Arguments and behavior

`local_iov`/`remote_iov` are arrays of `struct iovec { void *iov_base;
size_t iov_len; }` describing buffers in the caller and in `pid`.
Buffers are processed in array order; the local and remote element
lengths need not match, so one local buffer can be split across several
remote elements or vice versa. `flags` is unused and must be 0;
`liovcnt`/`riovcnt` must not exceed IOV_MAX. Counts and local_iov are
validated up front (all-or-nothing on those errors), but remote regions
are checked only just before the read/write, so an invalid remote_iov
element yields a partial transfer and no further elements are attempted
(man). Partial transfers happen at iovec-element granularity: a single
element is never split.

## Return value and errors

Number of bytes read/written on success (caller must compare against the
requested total). On error -1 with `errno`: `EFAULT` (local or remote
memory inaccessible), `EINVAL` (iov_len sum overflows ssize_t; flags
nonzero; counts too large), `ENOMEM` (kernel memory for iovec copies),
`EPERM` (no permission on the target address space), `ESRCH` (no such
pid). Transfers are not atomic in any way (man NOTES).

## Flags and constants

None: `flags` must be 0.

## Security and notes

- The PTRACE_MODE_ATTACH_REALCREDS check means the same users as
  ptrace(2): same-UID targets pass unless blocked by dumpability or LSMs.
- Reading unknown-length data (C strings) from a remote process: avoid
  spanning a page boundary in one remote_iov element, or a partial read
  will drop the rest (man).
- Worklog 1-b documents this pair among the memory chapter families;
  sibling pages link via [overview](overview.md).

## References

- Cached man page: source-cache/man-pages-sparse/man2/process_vm_readv.2
  (covers both names).
- Numbers/Since: hub [overview](overview.md); ledger
  SC-process_vm_readv, SC-process_vm_writev.
