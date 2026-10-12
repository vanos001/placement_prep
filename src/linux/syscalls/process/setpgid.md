# setpgid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 109 / 57 / 154 / 57 |
| Since (kernel) | 1.0 |
| Man page | man2/setpgid.2 (cached roff, dated 2021-03-22, covers all four names); man2/getpgid.2, getpgrp.2, setpgrp.2 are one-line .so aliases to setpgid.2 |
| glibc wrapper | setpgid(3), getpgid(3), getpgrp(3), setpgrp(3) all @@GLIBC_2.2.5 (nm -D, glibc 2.41); getpgid gated by _XOPEN_SOURCE >= 500 or _POSIX_C_SOURCE >= 200809L (since glibc 2.12); the BSD getpgrp(pid)/setpgrp(pid, pgid) variants are no longer exposed by unistd.h since glibc 2.19 (setpgid.2, SYNOPSIS and DESCRIPTION) |
| Aliases covered | getpgid (121 / 132 / 155 / 132, SC-getpgid); getpgrp (111 / 65 / - / 65, SC-getpgrp; x86_64 syscall 111, wrapper elsewhere per worklog 1-a); setpgrp (no syscall numbers, SC-setpgrp; libc-only) |
| Ledger ID | SC-setpgid |

## Purpose

setpgid() sets the process group ID (PGID) of a process; getpgid()/getpgrp() read it. Process groups are the unit that shell job control and terminal signal delivery operate on: a Ctrl-C typed at a controlling terminal goes to the foreground process group.

## Synopsis

```c
#include <unistd.h>
int setpgid(pid_t pid, pid_t pgid);
pid_t getpgid(pid_t pid);
pid_t getpgrp(void);                 /* POSIX.1 version */
int setpgrp(void);                   /* System V version */
```

## Arguments and behavior

setpgid(pid, pgid): pid 0 means the calling process; pgid 0 makes the process join a group whose ID equals its own PID (setpgid.2, DESCRIPTION). When a process moves to an existing group -- as shells do when building pipelines -- both groups must be in the same session: the target group's session ID must match the joiner's. The System V setpgrp(void) is exactly setpgid(0, 0). The BSD setpgrp(pid, pgid) and getpgrp(pid) were wrappers over setpgid/getpgid and are gone from unistd.h since glibc 2.19; the POSIX.1 getpgrp(void) always returns the caller's PGID. A child created by fork(2) inherits the parent's PGID, and the PGID survives execve(2) (setpgid.2, NOTES).

## Return value and errors

setpgid()/setpgrp() return 0 on success, -1 with errno on failure; getpgid() returns a process group ID (setpgid.2, RETURN VALUE). Errors (setpgid.2, ERRORS): EACCES, changing the group of a child that already execve'd; EINVAL, pgid less than 0; EPERM, the session rules -- moving a process into a group in a different session, changing the group of a child that is in a different session, or changing the group ID of a session leader; ESRCH, getpgid(): pid matches no process, or setpgid(): pid is neither the caller nor a child of the caller.

## Flags and constants

None.

## Security and notes

The EPERM rules encode the session invariant: a process cannot smuggle another process's group across a session boundary, and a session leader must keep its group. Orphaned stopped process groups get SIGHUP + SIGCONT; background groups reading the terminal are stopped with SIGTTIN, and only the foreground group may read (setpgid.2, NOTES). bash(1)-style job control is the canonical user of these calls. Cross-reference: [setsid](setsid.md), [getsid](getsid.md), [fork](fork.md), [wait4](wait4.md).

## References

- https://man7.org/linux/man-pages/man2/setpgid.2.html
- /usr/include/unistd.h (setpgrp(void) comment: exactly setpgid(0, 0))
- worklog Task 1-a (session family, SC-getpgrp/SC-setpgrp notes)
