# getpid(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | getpid: 39 / 20 / 172 / 20; getppid: 110 / 64 / 173 / 64; gettid: 186 / 224 / 178 / 224 |
| Since (kernel) | getpid/getppid 1.0; gettid 2.4.11 (gettid.2 VERSIONS) |
| Man page | man2/getpid.2 (cached, dated 2021-03-22; documents getpid and getppid; getppid.2 is a .so alias of getpid.2, verified in cache); man2/gettid.2 (cached, dated 2021-03-22) |
| glibc wrapper | getpid(3)/getppid(3) (GLIBC_2.2.5); gettid(3) since glibc 2.30 (gettid.2 VERSIONS; installed glibc exports gettid@@GLIBC_2.30 via nm -D) |
| Aliases covered | getppid, gettid |
| Ledger ID | SC-getpid, SC-getppid, SC-gettid |

## Purpose

getpid() returns the caller's process ID (the thread-group ID, TGID), getppid() the parent's PID, and gettid() the caller's kernel thread ID (TID). In a single-threaded process PID == TID; in a multithreaded process all threads share the PID and each has a unique TID (getpid.2, gettid.2). These are the identity primitives used for signals, /proc paths, locking, and temp-file naming.

## Synopsis

```c
#include <unistd.h>
pid_t getpid(void);
pid_t getppid(void);

#define _GNU_SOURCE
#include <unistd.h>
pid_t gettid(void);
```

## Arguments and behavior

No arguments; all three always succeed. getppid() returns the PID of the creator, or, after the parent died, of the reparenting target: init(1) or the nearest subreaper set via prctl(2) PR_SET_CHILD_SUBREAPER (getpid.2). If the parent lives in a different PID namespace, getppid() returns 0 (getpid.2, NOTES). A thread created with clone(2) CLONE_THREAD shares the TGID; a clone/fork child that is a thread-group leader has TID == TGID (gettid.2, NOTES). The TID is not the POSIX pthread_self(3) value (gettid.2).

## Return value and errors

Return the requested ID; never fail, no errno (getpid.2, gettid.2 ERRORS: "always successful").

## Flags and constants

None.

## Security and notes

glibc 2.3.4 through 2.24 cached the PID inside getpid(), which returned the parent's PID in children of raw-syscall fork/clone users; the cache was removed in glibc 2.25, so getpid() now always issues the syscall (getpid.2, C library/kernel differences; clone.2 BUGS). On Alpha a single getxpid() syscall returns both PID and parent PID, hidden by the wrappers (getpid.2). Thread libraries read the TID at thread start via set_tid_address(2)/CLONE_CHILD_SETTID rather than calling gettid repeatedly. Cross-reference: [clone](clone.md), [set_tid_address](set_tid_address.md), [prctl](prctl.md), [ptrace](ptrace.md).

## References

- https://man7.org/linux/man-pages/man2/getpid.2.html (getppid.2 is its .so alias)
- https://man7.org/linux/man-pages/man2/gettid.2.html
- kernel/sys.c (SYSCALL_DEFINE0(getpid)/gettid/getppid verified by fetching torvalds master kernel/sys.c; worklog 1-a did not list this file)
- /usr/include/unistd.h
