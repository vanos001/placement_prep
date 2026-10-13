# process_madvise(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 440 / 440 / 440 / 440 |
| Since (kernel) | 5.10 |
| Man page | man2/process_madvise.2 (cached roff, dated 2021-06-20; VERSIONS: first appeared in Linux 5.10; optional, CONFIG_ADVISE_SYSCALLS) |
| glibc wrapper | cached man page says no wrapper (with a sourceware bug 27380 FIXME); glibc 2.36 added process_madvise (glibc NEWS "Version 2.36"; nm -D shows @@GLIBC_2.36 on glibc 2.41); musl 1.2.5 has none (no match in musl src/include) |
| Aliases covered | none |
| Ledger ID | SC-process_madvise |

## Purpose

process_madvise() applies madvise(2)-style memory advice to the address ranges of another process -- or of the calling process -- identified by a PID file descriptor. The motivating use is reclaiming cold pages of a target application to improve system-wide performance. Brief-to-mid entry.

## Synopsis

```c
#include <sys/mman.h>
#include <sys/uio.h>
#include <sys/syscall.h>
#include <unistd.h>
ssize_t syscall(SYS_process_madvise, int pidfd,
                const struct iovec *iovec, size_t vlen,
                int advice, unsigned int flags);
```

## Arguments and behavior

pidfd specifies the target process (per pidfd_open(2)); the iovec array (iov_base, iov_len from sys/uio.h) describes the address ranges, and vlen -- capped by IOV_MAX, i.e. sysconf(_SC_IOV_MAX) -- the number of elements (process_madvise.2, DESCRIPTION). advice accepts only the MADV_COLD and MADV_PAGEOUT subset (each deferring to madvise(2) semantics on the cached page); flags is reserved and must be 0. The vlen and iovec arguments are validated before any advice is applied: an oversized vlen or invalid iovec fails the whole call up front. If a later element points at an invalid region of the remote process, advice stops there -- a partial application (process_madvise.2, DESCRIPTION and RETURN VALUE).

## Return value and errors

On success the number of bytes advised, which may be less than requested when advice stopped partway -- callers must check for partial application; on error -1 with errno (process_madvise.2, RETURN VALUE). Errors: EBADF, pidfd invalid; EFAULT, ranges outside the target's address space; EINVAL, flags not 0; EINVAL, iov_len sum overflows ssize_t; EINVAL, vlen too large; ENOMEM, internal iovec copies could not be allocated; EPERM, no permission to access the target's address space; ESRCH, the target terminated and was waited on.

## Flags and constants

MADV_COLD, MADV_PAGEOUT (the only advice values the cached page defines for this call; /usr/include/x86_64-linux-gnu/sys/mman.h declares the MADV_* set); flags must be 0.

## Security and notes

Permission is governed by a ptrace access mode PTRACE_MODE_READ_REALCREDS check, and -- because of the performance side effects -- the caller must additionally hold CAP_SYS_ADMIN (process_madvise.2, DESCRIPTION). Support depends on CONFIG_ADVISE_SYSCALLS (VERSIONS). Cross-reference: [pidfd_open](pidfd_open.md), [pidfd_send_signal](pidfd_send_signal.md).

## References

- https://man7.org/linux/man-pages/man2/process_madvise.2.html
- /home/z/my-project/source-cache/glibc-sparse/NEWS (Version 2.36: process_madvise added)
- nm -D /lib/x86_64-linux-gnu/libc.so.6 (process_madvise @@GLIBC_2.36)
- worklog Task 1-a (pidfd family entries)
