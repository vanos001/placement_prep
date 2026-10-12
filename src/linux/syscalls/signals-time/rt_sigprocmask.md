# rt_sigprocmask(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | rt_sigprocmask: 14 / 175 / 135 / 175 (ledger SC-rt_sigprocmask; verified syscall_64.tbl line 26, syscall_generic.tbl line 171, syscall_32.tbl line 190); legacy sigprocmask: - / 126 / - / 126 (ledger SC-sigprocmask; verified syscall_32.tbl line 141) |
| Since (kernel) | rt_sigprocmask 2.2 (sigprocmask.2: rt_* split "with the addition of real-time signals in Linux 2.2"); legacy sigprocmask 1.0 (ledger SC-sigprocmask) |
| Man page | man2/sigprocmask.2 (cached); rt_sigprocmask.2 is an .so alias ("\.so man2/sigprocmask.2") |
| glibc wrapper | glibc sigprocmask(3) transparently calls rt_sigprocmask() and hides sigsetsize (sigprocmask.2, C library/kernel differences); it silently ignores attempts to block the two NPTL-internal real-time signals |
| Aliases covered | rt_sigprocmask (kernel name), legacy sigprocmask (i386/arm32 slot 126, 32-bit sigset_t ABI) |
| Ledger ID | SC-rt_sigprocmask, SC-sigprocmask |

## Purpose

rt_sigprocmask() fetches and/or changes the calling thread's signal mask: the set of signals whose delivery is currently blocked. The rt_* form exists because the original sigprocmask() could carry only a 32-bit sigset_t, which stopped fitting the real-time signal range in Linux 2.2 (sigprocmask.2, C library/kernel differences).

## Synopsis

```c
#include <signal.h>
int sigprocmask(int how, const sigset_t *set, sigset_t *oldset);
/* kernel ABI */
int rt_sigprocmask(int how, const kernel_sigset_t *set,
                   kernel_sigset_t *oldset, size_t sigsetsize);
```

## Arguments and behavior

how selects the operation (values from glibc bits/sigaction.h): SIG_BLOCK 0 (new mask = union of current mask and set), SIG_UNBLOCK 1 (remove the members of set; unblocking a non-blocked signal is permitted), SIG_SETMASK 2 (mask = set). If set is NULL the mask is unchanged and how is ignored, but the current mask is still stored into oldset; both may be NULL (sigprocmask.2). The kernel call takes sigsetsize, a fixed architecture-specific value equal to sizeof(kernel_sigset_t) (_NSIG/8, 8 bytes on most archs, 16 on MIPS; sigprocmask.2 comment). sigset_t objects are manipulated with the sigsetops(3) functions.

## Return value and errors

0 on success; -1 with errno on failure (sigprocmask.2). Errors: EFAULT (set or oldset outside the address space); EINVAL (invalid how, or kernel does not support the sigsetsize passed).

## Flags and constants

SIG_BLOCK 0, SIG_UNBLOCK 1, SIG_SETMASK 2 (glibc bits/sigaction.h). SIGKILL and SIGSTOP cannot be blocked; attempts are silently ignored (sigprocmask.2 NOTES).

## Security and notes

Each thread has its own mask; sigprocmask() is unspecified in multithreaded processes, so threads must use pthread_sigmask(3) (sigprocmask.2; the man page is the canonical pointer). fork() copies the parent mask; the mask survives execve(). If SIGBUS, SIGFPE, SIGILL, or SIGSEGV is generated while blocked, behavior is undefined unless kill(2), sigqueue(3), or raise(3) generated the signal.

## References

- https://man7.org/linux/man-pages/man2/sigprocmask.2.html
- /usr/include/x86_64-linux-gnu/bits/sigaction.h (SIG_BLOCK/UNBLOCK/SETMASK values)
- worklog Task 1-e (sigsetsize semantics; time64-era mask handling unchanged)
