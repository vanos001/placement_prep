# idle(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / 112 / -- / -- |
| Since (kernel) | -- in the ledger columns (pre-2.0 era call); removed in 2.3.13 (idle.2 HISTORY) |
| Man page | man2/idle.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none (declared [[deprecated]] for direct syscall(2) use on the i386 tables that kept it) |
| Aliases covered | none |
| Ledger ID | SC-idle |

## Purpose

idle() was the bootstrap syscall that turned process 0 into the idle task: mark the process's pages swappable, lower its priority, and enter the main scheduling loop, never returning (idle.2, DESCRIPTION). It exists in the i386 table as slot 112 purely as a leftover of that bootstrap design.

## Synopsis

```c
#include <unistd.h>
[[deprecated]] int idle(void);
```

## Arguments and behavior

No arguments; no user-callable behavior at all: "Only process 0 may call idle(). Any user process, even a process with superuser permission, will receive EPERM" (idle.2, DESCRIPTION). The modern kernel has no userspace idle syscall at all -- the idle loop lives in kernel/cpu/idle.c behind cpuidle, and process 0 is built, not bootstrapped through a syscall.

## Return value and errors

Never returns for process 0; always -1 for a user process (idle.2, RETURN VALUE). Errors: EPERM, always, for user processes (idle.2, ERRORS).

## Flags and constants

None.

## Security and notes

A user-callable slot that only the kernel's first process could ever use is a nice interview example of a privileged-by-identity (not by capability) check. syscalls(2) lists idle(2) among the never-implemented-for-users calls alongside the [unimplemented](unimplemented.md) set. Cross-reference: [setup](setup.md), [unimplemented](unimplemented.md), [sched_yield](sched_yield.md).

## References

- https://man7.org/linux/man-pages/man2/idle.2.html
- man-pages syscalls(2) (idle listed in the unimplemented/removed discussion)
