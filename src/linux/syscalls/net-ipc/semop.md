# semop(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | semop 65 / - / 193 / 298; semtimedop 220 / - / 192 / 312; semtimedop_time64 - / 420 / - / 420 (hub) |
| Since (kernel) | semop 2.0 (hub); semtimedop first in 2.5.52, backported to 2.4.22 (semop.2 VERSIONS); semtimedop_time64 is a 5.1-era time64 twin (worklog 1-g) |
| Man page | man2/semop.2 (cached, dated 2021-03-22; canonical page for semop and semtimedop) |
| glibc wrapper | yes; semtimedop needs _GNU_SOURCE; glibc semtimedop support since 2.3.3 (semop.2 VERSIONS) |
| Aliases covered | semtimedop, semtimedop_time64 (SC-semtimedop, SC-semtimedop_time64, grouped per ledger) |
| Ledger ID | SC-semop (+ SC-semtimedop, SC-semtimedop_time64) |

## Purpose

semop() atomically performs an array of operations (struct sembuf:
sem_num, sem_op, sem_flg) on the semaphores of set `semid`: either all
operations proceed or none do. Positive sem_op adds to semval (never
blocks); zero is a wait-for-zero operation; negative sem_op subtracts
when semval is large enough, otherwise the thread sleeps in semncnt.
semtimedop() adds a `timeout` bounding the sleep (EAGAIN on expiry;
NULL timeout = plain semop) (semop.2).

## Synopsis

```c
#include <sys/sem.h>
int semop(int semid, struct sembuf *sops, size_t nsops);
int semtimedop(int semid, struct sembuf *sops, size_t nsops,
               const struct timespec *timeout);
```

## Arguments and behavior

`sem_flg` may hold IPC_NOWAIT (fail with EAGAIN instead of blocking)
and SEM_UNDO (operation is undone at process exit via the per-process,
per-semaphore semadj bookkeeping; semadj lists survive execve but not
fork; clone(2) CLONE_SYSVSEM shares the list). Success sets sempid to
the caller and updates sem_otime. Permissions: alter for +/- and undo,
read for wait-for-zero. SEM_UNDO allocation failure gives ENOMEM;
sem_op + semval above SEMVMX gives ERANGE (semop.2). On i386 there are
no dedicated slots: glibc uses the [ipc](ipc.md) multiplexer (SEMTIMEDOP
= 4) -- the "-" hub columns; the time64 twin i386 420 takes a 64-bit
timespec.

## Return value and errors

0 on success; -1 with `errno`: `E2BIG` (nsops > SEMOPM, 500),
`EACCES`, `EAGAIN`, `EFAULT`, `EFBIG` (sem_num out of range),
`EIDRM` (set removed), `EINTR`, `EINVAL` (bad semid/nsops), `ENOMEM`
(SEM_UNDO structures), `ERANGE` (SEMVMX exceeded).

## Flags and constants

IPC_NOWAIT (00004000), SEM_UNDO (0x1000 in <sys/sem.h>) in sem_flg;
SEMOPM/SEMVMX limits from <linux/sem.h> (SEMOPM 500).

## Security and notes

- semop is never automatically restarted after a signal handler runs,
  regardless of SA_RESTART (semop.2 NOTES).
- SETVAL/SETALL on [semget](semget.md)'s semctl clear all processes'
  semadj for that semaphore (semop.2).

## References

- Cached man page: source-cache/man-pages-sparse/man2/semop.2
  (semtimedop covered there).
- Numbers: hub [overview](overview.md); ledger semop/semtimedop rows.
