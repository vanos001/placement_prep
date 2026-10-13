# ipc(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | - / 117 / - / - (hub; i386 only) |
| Since (kernel) | 1.0 (hub; the SysV IPC multiplexer has been there since the beginning on the multiplexed ABIs) |
| Man page | man2/ipc.2 (cached, dated 2021-03-22) |
| glibc wrapper | none ("glibc provides no wrapper for ipc(), necessitating the use of syscall(2)"; user programs call msgget(2)/semget(2)/... which the C library maps to ipc() on multiplexed ABIs) |
| Aliases covered | none (the calls it dispatches have their own pages) |
| Ledger ID | SC-ipc |

## Purpose

ipc() is the common kernel entry point for the System V IPC calls on
architectures that multiplex them: message queues, semaphores, and
shared memory. The `call` argument selects which IPC function to invoke;
the remaining arguments are passed through (ipc.2). On x86-64 and ARM
there is no ipc() syscall: msgctl(2), semctl(2), shmctl(2) and the rest
are separate syscalls there (ipc.2 NOTES) -- hence the "-" in the hub
x64/g64/arm columns and 117 on i386.

## Synopsis

```c
#include <linux/ipc.h>
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_ipc, unsigned int call, int first,
            unsigned long second, unsigned long third,
            void *ptr, long fifth);
```

## Arguments and behavior

`call` values, verified in installed /usr/include/linux/ipc.h (the
kernel ipc/syscall.c dispatches on exactly these):

| Call | Value | Dispatches to |
|---|---|---|
| SEMOP | 1 | [semop](semop.md) |
| SEMGET | 2 | [semget](semget.md) |
| SEMCTL | 3 | semctl(2) ([semget](semget.md) page) |
| SEMTIMEDOP | 4 | [semop](semop.md) (semtimedop) |
| MSGSND | 11 | [msgget](msgget.md) (msgsnd) |
| MSGRCV | 12 | msgget page (msgrcv; ptr is a struct ipc_kludge pointer) |
| MSGGET | 13 | [msgget](msgget.md) |
| MSGCTL | 14 | msgget page (msgctl) |
| SHMAT | 21 | [shmget](shmget.md) (shmat; result returned via ptr) |
| SHMDT | 22 | shmget page (shmdt) |
| SHMGET | 23 | [shmget](shmget.md) |
| SHMCTL | 24 | shmget page (shmctl) |

Versioning of ctl operations is selected with IPC_64 (0x0100) versus
IPC_OLD (0) in the call path (linux/ipc.h).

## Return value and errors

Whatever the dispatched syscall returns; invalid `call` values fail
with EINVAL (kernel ipc/syscall.c default case).

## Flags and constants

IPC_PRIVATE (key_t 0), IPC_CREAT (00001000), IPC_EXCL (00002000),
IPC_NOWAIT (00004000) are the shared flag bits (linux/ipc.h); per-call
constants live on the pages listed above.

## Security and notes

- User programs should never call ipc() directly; it exists for libc
  implementors (ipc.2). Only standard library implementors and kernel
  hackers need it (ipc.2).
- The socket-side multiplexer with the same design is socketcall
  ([socketcall](socketcall.md)).

## References

- Cached man page: source-cache/man-pages-sparse/man2/ipc.2.
- Call numbers: /usr/include/linux/ipc.h; kernel dispatch
  source-cache/fetched/master-ipc-syscall.c.
- Numbers: hub [overview](overview.md); ledger SC-ipc (i386 117).
