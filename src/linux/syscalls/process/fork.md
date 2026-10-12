# fork(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 57 / 2 / - / 2 |
| Since (kernel) | 1.0 |
| Man page | man2/fork.2 (cached roff, dated 2021-03-22); no aliases |
| glibc wrapper | fork(3): since glibc 2.3.3 the NPTL wrapper calls clone(2) with flags = SIGCHLD and runs pthread_atfork(3) handlers (fork.2, C library/kernel differences) |
| Aliases covered | none; arm64-generic has no fork number (hub g64 column is "-"), consistent with worklog 1-a: arm64 has no fork/vfork syscalls |
| Ledger ID | SC-fork |

## Purpose

fork() creates a child process by duplicating the calling process. The child gets a copy-on-write copy of the parent's address space and then both continue from the call site. For new code, posix_spawn(3) or the clone(2)/clone3(2) family is preferred when fine control or vfork-style sharing is needed.

## Synopsis

```c
#include <unistd.h>
pid_t fork(void);
```

## Arguments and behavior

No arguments. On success the parent receives the child's PID and the child receives 0. Per fork.2, the child differs from the parent in that it has its own unique PID; resource usage and CPU-time counters are reset to zero; its pending-signal set is empty; and it does not inherit memory locks, semaphore adjustments, process-associated record locks, timers, or outstanding asynchronous I/O. Linux-specific differences: the prctl(2) PR_SET_PDEATHSIG setting is reset, the default timer slack is copied from the parent, MADV_DONTFORK mappings are not inherited, MADV_WIPEONFORK ranges are zeroed in the child, ioperm(2) bits are not inherited, and the child's termination signal is fixed to SIGCHLD. The child is single-threaded (only the calling thread survives), so until execve(2) it may safely call only async-signal-safe functions (fork.2, NOTES).

## Return value and errors

0 in the child, child's PID in the parent, -1 with errno on failure. Main errors (fork.2):

| Error | Meaning |
|---|---|
| EAGAIN | Process/thread limit hit: RLIMIT_NPROC, /proc/sys/kernel/threads-max, /proc/sys/kernel/pid_max, or a cgroup pids.max limit; or the caller runs under SCHED_DEADLINE without the reset-on-fork flag |
| ENOMEM | Kernel could not allocate the needed structures; or the target PID namespace has no live init |
| ENOSYS | fork() unsupported on this platform (for example, hardware without an MMU) |
| ERESTARTNOINTR | Since 2.6.17: interrupted by a signal and restarted; visible only during a trace |

## Flags and constants

None. The child termination signal is hard-wired to SIGCHLD, value 17 (/usr/include/asm-generic/signal.h).

## Security and notes

The glibc fork wrapper invokes pthread_atfork(3) handlers; a clone(2) call does not (clone.2, NOTES). In a multithreaded program the child inherits a locked-mutex snapshot it can deadlock on; use pthread_atfork(3) or posix_spawn(3). Under vfork-style constraints the child may only write a pid_t variable before execve/_exit (see vfork.2). Cross-reference: [clone](clone.md), [wait4](wait4.md), [_exit](_exit.md).

## References

- https://man7.org/linux/man-pages/man2/fork.2.html
- kernel/fork.c (source file named in worklog 1-a)
- /usr/include/asm-generic/signal.h (SIGCHLD value)
