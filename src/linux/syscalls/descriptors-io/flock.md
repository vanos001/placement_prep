# flock(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 73 / 143 / 32 / 143 (cached kernel tables; hub agrees) |
| Since (kernel) | 2.0 as a system call of its own (man NOTES: since kernel 2.0 not emulated via fcntl; hub agrees) |
| Man page | man2/flock.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in <sys/file.h> |
| Aliases covered | none |
| Ledger ID | SC-flock |

## Purpose

flock() applies or removes an advisory lock on the open file referred to by fd. Locks are associated with the open file description, not the process: descriptors created by fork(2) or dup(2) refer to the same lock and any of them can modify or release it, while a second open(2) of the same file yields an independently lockable description. Locks survive execve(2) and can be placed regardless of the open mode.

## Synopsis

```c
#include <sys/file.h>
int flock(int fd, int operation);
```

## Arguments and behavior

| Operation (sys/file.h) | Value | Meaning |
|---|---|---|
| LOCK_SH | 1 | Shared lock; many holders allowed |
| LOCK_EX | 2 | Exclusive lock; single holder |
| LOCK_UN | 8 | Release this process's lock |
| LOCK_NB | 4 | OR with SH/EX: do not block; fail with EWOULDBLOCK |

A blocking call waits while an incompatible lock is held; a file cannot hold shared and exclusive locks at once, and re-locking converts the existing lock (conversion is not atomic: the old lock is dropped first, so another process may slip in).

## Return value and errors

Returns 0 on success; -1 with errno: EBADF, EINTR (interrupted while waiting), EINVAL (bad operation), ENOLCK (out of lock memory), EWOULDBLOCK (LOCK_NB and the file is locked).

## Flags and constants

flock() versus fcntl(2) byte-range (POSIX/F_SETLK) locks, per the man page's NOTES:

| Property | flock() | fcntl(2) record locks |
|---|---|---|
| Scope | Whole file | Byte ranges |
| Associated with | Open file description | Process (per process/inode pair) |
| Released by | LOCK_UN or closing all duplicate fds | Closing any fd for the file (2.0+ behavior) |
| Inheritance | Kept by fork children via shared description | Child does not inherit |
| execve() | Preserved | Preserved |
| Interaction | None with fcntl locks (since 2.0 in-kernel implementation) | None with flock() |
| Deadlock detection | None | Yes |

## Security and notes

- Advisory only: any process with suitable file permissions can ignore the lock and do I/O.
- Over NFS, flock() did nothing before 2.6.11, was emulated as whole-file fcntl locks from 2.6.12 (so the two interact), and can be forced local with the local_lock mount option since 2.6.37; over SMB the locks became remotely visible (and effectively mandatory) from 5.5.

## References

- man2/flock.2 in the cached man-pages tree (dated 2021-03-22).
- Header: /usr/include/x86_64-linux-gnu/sys/file.h (LOCK_* values).
- [Syscalls ledger](../ledger.md) row SC-flock; see fcntl.md for the F_SETLK command group.
- [Domain hub](overview.md) for status and sibling pages.
