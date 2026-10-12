# umask(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 95 / 60 / 166 / 60 (cached kernel tables; hub agrees) |
| Since (kernel) | 1.0 |
| Man page | man2/umask.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in <sys/stat.h>; plain POSIX wrapper |
| Aliases covered | none |
| Ledger ID | SC-umask |

## Purpose

umask() sets the calling process's file mode creation mask to mask & 0777 and returns the previous value. The umask is used by open(2), mkdir(2), and other file-creating calls to turn permission bits off from the mode argument: a file created with mode 0666 under a umask of 022 gets 0644. If the parent directory has a default ACL, the umask is ignored and the inherited ACL plus the mode argument determine the permissions instead.

## Synopsis

```c
#include <sys/stat.h>
mode_t umask(mode_t mask);
```

## Arguments and behavior

mask is a file permission bit mask (S_IRUSR and friends, inode(7)); only the low 0777 bits are used. The typical default is S_IWGRP | S_IWOTH (022). The call always succeeds and cannot fail.

## Return value and errors

Returns the previous umask. No error conditions exist.

## Flags and constants

Permission bit constants for mask come from <sys/stat.h> (S_IRUSR 0400, S_IWUSR 0200, S_IXUSR 0100, and the group/other equivalents). There is no flag argument.

## Security and notes

- The read-modify-restore idiom (umask(0) then restore) is not atomic and races in multithreaded programs; the man page calls this out explicitly.
- Since Linux 4.7 the umask of any process is visible as the Umask field of /proc/[pid]/status, so a process can read its own umask from /proc/self/status without changing it.
- Children created by fork(2) inherit the umask; execve(2) leaves it unchanged.
- The umask affects POSIX IPC objects (mq_open(3), sem_open(3), shm_open(3)), FIFOs, and UNIX domain sockets; it does not affect System V IPC objects (msgget(2), semget(2), shmget(2)).
- It cannot be set by another process, and there is no way to fetch it without setting it (other than the /proc field above).

## References

- man2/umask.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-umask; kernel tables in source-cache/kernel.
- Siblings: [open](open.md) (mode & umask application), [stat](stat.md).
- [Domain hub](overview.md) for status and sibling pages.
