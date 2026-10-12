# pidfd_send_signal(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 424 / 424 / 424 / 424 |
| Since (kernel) | 5.1 |
| Man page | man2/pidfd_send_signal.2 (cached roff, dated 2021-03-22; VERSIONS: first appeared in Linux 5.1) |
| glibc wrapper | cached man page says no wrapper; glibc 2.36 added pidfd_send_signal (glibc NEWS "Version 2.36"; nm -D shows @@GLIBC_2.36 on glibc 2.41); musl 1.2.5 has none (no match in musl src/include) |
| Aliases covered | none |
| Ledger ID | SC-pidfd_send_signal |

## Purpose

pidfd_send_signal() sends a signal to the process referred to by a PID file descriptor (pidfd) -- a stable reference that closes the PID-recycling race kill(2) cannot avoid.

## Synopsis

```c
#include <signal.h>
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_pidfd_send_signal, int pidfd, int sig,
            siginfo_t *info, unsigned int flags);
```

## Arguments and behavior

pidfd refers to the target process; it can be obtained by opening a /proc/[pid] directory, with pidfd_open(2), or from clone(2)/clone3(2) with CLONE_PIDFD (pidfd_send_signal.2, NOTES). sig is the signal to send. If info is non-NULL it is a siginfo_t populated per rt_sigqueueinfo(2); if it is NULL the kernel supplies the values kill(2) would: si_signo = signal number, si_errno = 0, si_code = SI_USER, si_pid = caller's PID, si_uid = caller's real UID (pidfd_send_signal.2, DESCRIPTION). flags is reserved and must be 0. The caller must be in the same PID namespace as the target or in an ancestor of it. The race story (NOTES): traditional PID-addressed interfaces can hit the wrong process after the intended target dies and its PID is recycled; with a pidfd the call fails with ESRCH once that process has terminated and been waited on.

## Return value and errors

0 on success, -1 with errno (pidfd_send_signal.2, RETURN VALUE). Errors: EBADF, pidfd is not a valid PID file descriptor; EINVAL, sig invalid; EINVAL, the caller cannot signal the target from its PID namespace; EINVAL, flags is not 0; EPERM, no permission to send the signal; EPERM, pidfd does not refer to the caller and info->si_code is invalid (rt_sigqueueinfo rules); ESRCH, the target has terminated and been waited on.

## Flags and constants

SI_USER, SI_QUEUE (/usr/include/signal.h via the SI_* definitions the man page names); flags currently only 0.

## Security and notes

Signal permission follows the usual kill(2) rules (EPERM above); the siginfo path inherits rt_sigqueueinfo(2)'s anti-forgery checks. pidfds are pollable and can be passed between processes, making them the foundation of the newer pidfd API family. Cross-reference: [pidfd_open](pidfd_open.md), [pidfd_getfd](pidfd_getfd.md), [clone](clone.md).

## References

- https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html
- /home/z/my-project/source-cache/glibc-sparse/NEWS (Version 2.36: pidfd_send_signal added)
- nm -D /lib/x86_64-linux-gnu/libc.so.6 (pidfd_send_signal @@GLIBC_2.36)
- worklog Task 1-a (pidfd family entries)
