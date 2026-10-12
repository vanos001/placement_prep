# _exit(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | exit: 60 / 1 / 93 / 1; exit_group: 231 / 252 / 94 / 248 |
| Since (kernel) | exit 1.0; exit_group 2.6 (hub) - exit_group.2 VERSIONS says "present since Linux 2.5.35"; both values recorded in worklog 1-a |
| Man page | man2/_exit.2 (cached, dated 2021-03-22) + man2/exit_group.2 (cached, dated 2021-06-20) |
| glibc wrapper | _exit(3)/_Exit(3); since glibc 2.3 the _exit wrapper invokes exit_group(2), not exit (both man pages, C library/kernel differences / NOTES; installed glibc exports _exit@@GLIBC_2.2.5 and _Exit@@GLIBC_2.2.5, no exit_group symbol) |
| Aliases covered | exit, exit_group, _Exit (C99 library twin of _exit) |
| Ledger ID | SC-exit, SC-exit_group |

## Purpose

_exit() terminates the calling process "immediately": no atexit(3) or on_exit(3) handlers run and stdio(3) streams are not flushed. exit_group() terminates all threads in the calling thread group. Use _exit in a fork child before execve, and exit(3) everywhere else; _Exit (C99, stdlib.h) is equivalent to _exit (_exit.2).

## Synopsis

```c
#include <unistd.h>
noreturn void _exit(int status);

#include <sys/syscall.h>     /* raw syscall only */
noreturn void syscall(SYS_exit_group, int status);
```

## Arguments and behavior

status: the value status & 0xFF becomes the process exit status collectable by wait(2) (0 = success convention, 0-255 representable). _exit closes open file descriptors, hands orphaned children to init(1) or the nearest subreaper set by prctl(2) PR_SET_CHILD_SUBREAPER, and sends SIGCHLD to the parent (_exit.2, DESCRIPTION). The raw exit syscall terminates only the calling thread; reparenting and SIGCHLD happen only if it is the last thread of the thread group. exit_group terminates all threads in the process; since glibc 2.3 this is what the _exit wrapper actually invokes. exit_group has no glibc wrapper (exit_group.2 note).

## Return value and errors

These calls never return and cannot fail; no errno is defined.

## Flags and constants

None. WEXITSTATUS(status) from sys/wait.h extracts the low 8 bits on the parent side (wait.2).

## Security and notes

Because descriptors are closed synchronously, _exit may stall waiting for pending output; call tcflush(3) first if that matters (_exit.2, NOTES). Which pending I/O is canceled is implementation-dependent. A vfork child may call _exit but must not call exit(3), which would run the parent's exit handlers and flush its stdio buffers (vfork.2). Cross-reference: [fork](fork.md), [wait4](wait4.md), [execve](execve.md), [prctl](prctl.md).

## References

- https://man7.org/linux/man-pages/man2/_exit.2.html
- https://man7.org/linux/man-pages/man2/exit_group.2.html
- kernel/exit.c (source file named in worklog 1-a)
- /usr/include/unistd.h, /usr/include/stdlib.h (_Exit)
