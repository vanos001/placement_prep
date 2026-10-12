# wait4(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | wait4: 61 / 114 / 260 / 114; waitpid: - / 7 / - / - (i386 only) |
| Since (kernel) | 1.0 (hub; waitpid number present on i386 since 1.0 per ledger) |
| Man page | man2/wait4.2 (cached, dated 2021-03-22; documents wait3 and wait4); waitpid is documented in man2/wait.2 (waitpid.2 is a .so alias of wait.2, verified in cache) |
| glibc wrapper | wait4(3), waitpid(3), wait3(3) all exist (glibc 2.41 exports wait4@@GLIBC_2.2.5, waitpid@@GLIBC_2.2.5, wait3@@GLIBC_2.2.5); wait() is a library function implemented as wait4 (wait.2); on architectures without a waitpid syscall the wrapper calls wait4 (wait.2, C library/kernel differences) |
| Aliases covered | wait3, waitpid |
| Ledger ID | SC-wait4, SC-waitpid |

## Purpose

wait4() waits for a child (or children) to change state and additionally returns the child's resource usage in a struct rusage; it is the syscall behind wait(3), waitpid(3), and wait3(3). wait4.2 marks wait3/wait4 nonstandard and recommends waitpid(2) or waitid(2) for new programs.

## Synopsis

```c
#include <sys/wait.h>
pid_t wait4(pid_t pid, int *wstatus, int options, struct rusage *rusage);
pid_t wait3(int *wstatus, int options, struct rusage *rusage);
```

## Arguments and behavior

pid selects the wait set exactly as for waitpid(2) (wait.2): < -1 any child whose process group ID equals |pid|; -1 any child; 0 any child in the caller's process group; > 0 the child with that PID. options is an OR of wait flags (table below); wstatus receives an encoded status to decode with WIFEXITED/WEXITSTATUS/WIFSIGNALED/WTERMSIG/WCOREDUMP/WIFSTOPPED/WSTOPSIG/WIFCONTINUED macros (wait.2). If rusage is non-NULL it is filled with accounting for the waited child, as getrusage(2) describes (wait4.2). wait3 is equivalent to waitpid(-1, wstatus, options) plus rusage. The call blocks until a selected child changes state (terminates, stops, or continues per options) or a signal interrupts it; it returns immediately if a waitable child already exists.

## Return value and errors

Returns the PID of the child whose state changed; 0 if WNOHANG was set and no waitable child exists; -1 with errno on failure (wait.2):

| Error | Meaning |
|---|---|
| ECHILD | No unwaited-for children (or the selected child does not exist / is not a child; SIGCHLD set to SIG_IGN makes children non-waitable) |
| EINTR | WNOHANG not set and an unblocked signal or SIGCHLD was caught |
| EINVAL | Invalid options |
| ESRCH | waitpid with pid equal to INT_MIN |

## Flags and constants

| Constant | Value | Meaning (source: /usr/include/linux/wait.h) |
|---|---|---|
| WNOHANG | 0x00000001 | return immediately if no child has exited |
| WUNTRACED / WSTOPPED | 0x00000002 | also report stopped (non-traced) children |
| WCONTINUED | 0x00000008 | also report children resumed by SIGCONT (since 2.6.10) |
| __WCLONE | (see wait.2) | wait only for "clone" children (exit signal other than SIGCHLD) |
| __WALL | (see wait.2) | wait for all children regardless of clone type (since 2.4) |
| __WNOTHREAD | (see wait.2) | do not wait for other threads' children (since 2.4) |

__WCLONE/__WALL/__WNOTHREAD are Linux-specific (wait.2, Linux notes); since 4.7 __WALL is implied for ptraced children. Since 4.7 these options also work with waitid(2).

## Security and notes

A waited child is reaped (zombie resources released); SIGCHLD disposition SIG_IGN or SA_NOCLDWAIT makes children self-reaping and turns wait into an ECHILD wait (wait.2, POSIX section; 2.4 and earlier kernels deviated). Since 2.4 a thread can wait for children of other threads in its thread group by default. Cross-reference: [waitid](waitid.md), [fork](fork.md), [_exit](_exit.md), [ptrace](ptrace.md).

## References

- https://man7.org/linux/man-pages/man2/wait4.2.html
- https://man7.org/linux/man-pages/man2/wait.2.html (waitpid.2 is its .so alias)
- kernel/exit.c (source file named in worklog 1-a)
- /usr/include/linux/wait.h, /usr/include/x86_64-linux-gnu/bits/waitflags.h
