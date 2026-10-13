# setsid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 112 / 66 / 157 / 66 |
| Since (kernel) | 1.0 |
| Man page | man2/setsid.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | setsid(3) @@GLIBC_2.2.5 (nm -D, glibc 2.41); prototype in unistd.h |
| Aliases covered | none |
| Ledger ID | SC-setsid |

## Purpose

setsid() creates a new session. The calling process becomes the session leader (session ID = its PID), the leader of a new process group (PGID = its PID), and the only member of both. This is how daemons detach from a controlling terminal and how shells start background jobs in their own session.

## Synopsis

```c
#include <unistd.h>
pid_t setsid(void);
```

## Arguments and behavior

No arguments. If the calling process is not a process group leader, setsid() creates a new session with the caller as leader and sole member; the new session initially has no controlling terminal (setsid.2, DESCRIPTION). A process group leader is a process whose PGID equals its PID. If that is already true of the caller, the call fails with EPERM -- disallowed so a group leader cannot slip into a new session while the rest of its group stays behind, breaking the strict two-level session/process-group hierarchy (setsid.2, NOTES). To guarantee success, fork(2), have the parent _exit(2), and let the child -- which cannot be a group leader -- call setsid(). A child inherits its parent's session ID, and the session ID survives execve(2) (setsid.2, NOTES).

## Return value and errors

On success the new session ID is returned; on error (pid_t) -1 with errno (setsid.2, RETURN VALUE). Errors: EPERM, the process group ID of any process equals the PID of the calling process -- in particular, the caller is already a process group leader (setsid.2, ERRORS).

## Flags and constants

None.

## Security and notes

Controlling-terminal consequences (setsid.2, NOTES): if the session's terminal hangs up and CLOCAL is not set, the session leader is sent SIGHUP; when a session leader terminates, SIGHUP goes to the foreground process group of the controlling terminal. The setsid(1) utility wraps this for launching commands in new sessions. Cross-reference: [setpgid](setpgid.md), [getsid](getsid.md), [fork](fork.md), [_exit](_exit.md).

## References

- https://man7.org/linux/man-pages/man2/setsid.2.html
- /usr/include/unistd.h (setsid prototype)
- worklog Task 1-a (session family facts)
