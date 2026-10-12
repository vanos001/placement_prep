# `umask` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [umask(2)](../../../syscalls/descriptors-io/umask.md); the unreadable-mask
> problem: [getumask.md](getumask.md).

| Field | Value |
|---|---|
| Header | `sys/stat.h` |
| Standards | POSIX.1-2001/2008, SVr4, 4.3BSD |
| Exported | `umask@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual); the value it sets is process-global, so threads share it |
| Ledger ID | GLIBC-umask |

## Declaration and gates

```c
#include <sys/stat.h>

mode_t umask(mode_t mask);
```

Declared ungated at
`/usr/include/x86_64-linux-gnu/sys/stat.h` line 380, directly above the
Hurd-only `getumask` (lines 384-386).

## Semantics

Sets the calling process's file mode creation mask to `mask & 0777`
and returns the previous mask; it always succeeds (`umask.2`). Every
creator that takes a `mode` argument -- `open`, `creat`, `mkdir`,
`mkfifo`, `mknod`, POSIX IPC opens (`mq_open`, `sem_open`,
`shm_open`), UNIX-domain sockets --
computes the new node's permissions as `mode & ~umask`, so the mask is
the complement of the permissions you intend to grant (manual
*Assigning File Permissions*). A default ACL on the parent directory
overrides the umask entirely (`umask.2`). The shell initializes it at
login; `fork` inherits it and `execve` leaves it unchanged.

## Gotchas and portability

- Reading the mask requires writing it: the manual's canonical
  `read_umask` does `umask(0)` then restores -- nonatomic, so in a
  multithreaded program another thread can create a file through the
  wide-open window (`umask.2` NOTES). On Hurd use
  [getumask](getumask.md); since Linux 4.7 a process can read its own
  mask without changing it from `/proc/self/status`'s `Umask` field.
- Programs that must bypass the inherited mask should `fchmod` the
  opened file instead of mutating the process-wide mask -- the manual
  reserves `umask` changes "usually only for shells"
  (*Assigning File Permissions*).
- The mask never affects SysV IPC objects (`msgget`/`semget`/
  `shmget`) -- only POSIX IPC, FIFOs, files and sockets
  (`umask.2` NOTES).
- musl 1.2.5: bare `SYS_umask` wrapper, identical semantics
  (`src/stat/umask.c`). Grouped sibling page with the chmod/chown
  family: [chmod-umask-owners.md](chmod-umask-owners.md).

## Errors

None: "This system call always succeeds and the previous value of the
mask is returned" (`umask.2` RETURN VALUE).

## References

- glibc manual: `filesys.texi`, node *Assigning File Permissions*
- man2: `umask.2`
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h` lines 380-386
- symbols: `nm -D --with-symbol-versions libc.so.6`
