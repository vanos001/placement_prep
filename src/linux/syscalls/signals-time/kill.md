# kill(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | kill: 62 / 37 / 129 / 37 (ledger SC-kill; verified syscall_64.tbl line 74, syscall_32.tbl line 52, syscall_generic.tbl line 165, syscall_arm.tbl line 52) |
| Since (kernel) | 1.0 (ledger SC-kill; kill.2 Linux-notes history starts at kernel 1.0) |
| Man page | man2/kill.2 (cached) |
| glibc wrapper | kill(3) is the direct syscall wrapper (kill.2); glibc killpg(3) is the POSIX process-group convenience form covered here (kill.2 SEE ALSO) |
| Aliases covered | killpg(3) (library form, sends to a process group) |
| Ledger ID | SC-kill |

## Purpose

kill() sends any signal to any process group or process (kill.2). It is the one primitive behind raise(3), process termination, job control kicks, and the kill(1)/killall(1) commands; permissions, not capabilities of the signal payload, are the only gate.

## Synopsis

```c
#include <signal.h>
int kill(pid_t pid, int sig);
```

## Arguments and behavior

The pid argument selects the target (kill.2): pid > 0 sends to the process with that ID; pid = 0 sends to every process in the caller's process group; pid = -1 sends to every process the caller may signal except init (pid 1); pid < -1 sends to every process in process group -pid. If sig is 0, no signal is sent but existence and permission checks still run, which makes kill(pid, 0) the standard liveness probe. Permission: the caller needs CAP_KILL in the target's user namespace, or its real or effective UID must equal the target's real or saved set-user-ID; for SIGCONT it suffices that sender and receiver share a session (kill.2).

## Return value and errors

0 on success (at least one signal was sent); -1 with errno on error (kill.2). Errors: EINVAL (invalid signal); EPERM (no permission to signal any target); ESRCH (target process or group does not exist; an existing zombie also yields ESRCH semantics only after wait, kill.2 notes an existing zombie is a process that terminated but was not waited for).

## Flags and constants

No flags. sig is a signal number; the signal table lives in signal.7 (worklog 1-e fetched man7.org signal.7 for the table: standard signals 1-31, real-time SIGRTMIN-SIGRTMAX, on x86 SIGRTMIN 34 / SIGRTMAX 64 with glibc, kernel range 32-64).

## Security and notes

Only signals init (pid 1) has installed handlers for can be delivered to it (kill.2). On Linux kill(-1, sig) does not signal the calling process itself. POSIX requires self-signals to be delivered before kill() returns when the sending thread does not block the signal. Permission rules changed across kernels; the POSIX-conforming rule (real/effective vs real/saved-set UID) was adopted in 1.3.78. Kernels up to 2.6.7 had a bug returning EPERM for process-group sends when the caller lacked permission for any (not all) member (kill.2 BUGS).

## References

- https://man7.org/linux/man-pages/man2/kill.2.html
- worklog Task 1-e (signal.7 table facts, fetched from man7.org)
- [tgkill](tgkill.md) (thread-directed sends), [overview](overview.md)
