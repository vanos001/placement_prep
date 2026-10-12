# pause(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 34 / 29 / - / 29 (ledger SC-pause; verified syscall_64.tbl line 46, syscall_32.tbl line 44, syscall_arm.tbl line 44; the arm64-generic table has no pause slot - hub column "-") |
| Since (kernel) | 1.0 (ledger SC-pause) |
| Man page | man2/pause.2 (cached) |
| glibc wrapper | pause(3) is the direct syscall wrapper (pause.2, <unistd.h>) |
| Aliases covered | none |
| Ledger ID | SC-pause |

## Purpose

pause() suspends the calling process or thread until a signal is delivered that either terminates the process or invokes a signal-catching function (pause.2). It is the minimal "sleep until signaled" primitive; every practical use replaces it with sigsuspend(2) or pselect(2)/ppoll(2), which swap the mask and wait atomically.

## Synopsis

```c
#include <unistd.h>
int pause(void);
```

## Arguments and behavior

Takes no arguments. The call returns only when a signal was caught and the signal-catching function returned (pause.2). Delivery depends on the thread's signal mask, so pause() alone cannot avoid the window where a signal arrives between the mask check and the sleep - exactly the race sigsuspend() closes.

## Return value and errors

pause() always returns -1 with errno set to EINTR (pause.2 RETURN VALUE and ERRORS). There is no success return; if the signal terminated the process, there is no return at all.

## Flags and constants

No flags, no tunables.

## Security and notes

Conforming to POSIX.1-2001, POSIX.1-2008, SVr4, 4.3BSD (pause.2). The syscall survives on x86_64, i386, and arm32 but has no slot in the generic (arm64) syscall table, so the 64-bit generic ABI exposes no pause number (hub column "-"; cached scripts/syscall.tbl generic has no pause row) - glibc still offers the wrapper where the kernel provides the call. For waiting with a temporarily replaced mask use rt_sigsuspend (this domain); for waiting with a timeout and a mask swap use pselect6/ppoll.

## References

- https://man7.org/linux/man-pages/man2/pause.2.html
- [rt_sigsuspend](rt_sigsuspend.md), [overview](overview.md)
