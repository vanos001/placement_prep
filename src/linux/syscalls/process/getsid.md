# getsid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 124 / 147 / 156 / 147 |
| Since (kernel) | 2.0 |
| Man page | man2/getsid.2 (cached roff, dated 2021-03-22); man VERSIONS: "available on Linux since version 2.0" |
| glibc wrapper | getsid(3) @@GLIBC_2.2.5 (nm -D, glibc 2.41); gated by _XOPEN_SOURCE >= 500 or _POSIX_C_SOURCE >= 200809L (since glibc 2.12) (getsid.2, SYNOPSIS) |
| Aliases covered | none |
| Ledger ID | SC-getsid |

## Purpose

getsid() returns the session ID of a process. It is the read side of setsid(2), letting a caller find out which session a PID belongs to -- for example to identify the session leader (the process whose PID equals the session ID).

## Synopsis

```c
#include <unistd.h>
pid_t getsid(pid_t pid);
```

## Arguments and behavior

getsid(0) returns the session ID of the calling process; with a nonzero pid it returns the session ID of that process (getsid.2, DESCRIPTION). The feature-test gate and the Linux-since-2.0 availability are both on the cached page (SYNOPSIS and VERSIONS; a page comment also records libc support since libc 5.2.19).

## Return value and errors

On success a session ID; on error (pid_t) -1 with errno (getsid.2, RETURN VALUE). Errors (getsid.2, ERRORS): EPERM, a process with ID pid exists but is not in the same session as the caller and the implementation considers that an error; ESRCH, no process with ID pid exists.

## Flags and constants

None.

## Security and notes

"Linux does not return EPERM" (getsid.2, NOTES) -- the cross-session visibility rule POSIX allows is not enforced here, so any existing PID's session ID can be read. The EPERM row above therefore describes other implementations. For the session model (sessions, controlling terminals, foreground groups) see credentials(7), referenced from the page. Cross-reference: [setsid](setsid.md), [setpgid](setpgid.md).

## References

- https://man7.org/linux/man-pages/man2/getsid.2.html
- /usr/include/unistd.h (getsid prototype)
- worklog Task 1-a (session family facts)
