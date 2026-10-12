# semget(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | semget 64 / 393 / 190 / 299; semctl 66 / 394 / 191 / 300 (hub) |
| Since (kernel) | 2.0 (hub; SysV semaphore syscalls since 1.0-era on the multiplexed ABIs, named slots since 2.0) |
| Man page | man2/semget.2 and man2/semctl.2 (both cached, dated 2021-03-22) |
| glibc wrapper | yes for both, in libc (header <sys/sem.h>); semget POSIX.1-2001/2008 |
| Aliases covered | semctl (SC-semctl, grouped per ledger) |
| Ledger ID | SC-semget (+ SC-semctl) |

## Purpose

System V semaphore sets. semget() returns the identifier of the set
for `key`, creating a set of `nsems` semaphores when key is
IPC_PRIVATE or no set exists and IPC_CREAT is given; semctl() performs
control operations on a set or a single semaphore: IPC_STAT, IPC_SET,
IPC_RMID, IPC_INFO, SEM_INFO, SEM_STAT, SEM_STAT_ANY (4.17), and the
per-semaphore commands GETVAL, SETVAL, GETALL, SETALL, GETPID, GETNCNT,
GETZCNT (semget.2, semctl.2; overview in svipc.7).

## Synopsis

```c
#include <sys/sem.h>
int semget(key_t key, int nsems, int semflg);
int semctl(int semid, int semnum, int cmd, ...);
/* union semun { int val; struct semid_ds *buf;
   unsigned short *array; struct seminfo *__buf; }; */
```

## Arguments and behavior

`semflg` low 9 bits are the permissions (open(2) style; write means
alter permission). IPC_CREAT|IPC_EXCL with an existing key fails with
EEXIST (open O_CREAT|O_EXCL analogy). `nsems` may be 0 when not
creating; creation limits it to SEMMSL. New sets have indeterminate
semaphore values (POSIX note): Linux zeroes them, but a portable
program initializes via SETVAL/SETALL and can use a nonzero sem_otime
(IPC_STAT) to detect initialization races (semget.2 "Semaphore
initialization"). semctl's fourth argument is the union semun the
caller must declare itself (semctl.2). Limits: SEMMNI (sets; 32,000
since 3.19), SEMMSL (per set; 32,000 since 3.19), SEMMNS (system-wide;
all via /proc/sys/kernel/sem fields) (semget.2).

## Return value and errors

Nonnegative identifier on success (semctl returns a value for the
GET*/IPC_INFO/SEM_INFO/SEM_STAT commands); -1 with `errno`:
`EACCES` (CAP_IPC_OWNER check), `EEXIST`, `EINVAL` (nsems out of range
or larger than the existing set; bad cmd), `ENOENT` (no set, no
IPC_CREAT), `ENOMEM`, `ENOSPC` (SEMMNI/SEMMNS exhausted), `EPERM`
(IPC_SET/IPC_RMID without owner or CAP_SYS_ADMIN).

## Flags and constants

IPC_CREAT 00001000, IPC_EXCL 00002000, IPC_NOWAIT 00004000,
IPC_PRIVATE (key 0) from <sys/ipc.h> / <linux/ipc.h>; SETVAL/GETALL
etc. from <sys/sem.h>; SEM_UNDO and IPC_NOWAIT are the sembuf flags on
[semop](semop.md).

## Security and notes

- Permission checks consult CAP_IPC_OWNER in the governing user
  namespace (semget.2/semctl.2); IPC_RMID needs owner or CAP_SYS_ADMIN.
- The set is not destroyed when the last user exits: it persists until
  IPC_RMID or reboot (svipc.7).

## References

- Cached man pages: source-cache/man-pages-sparse/man2/semget.2,
  man2/semctl.2; fetched svipc.7 (source-cache/fetched/svipc.7.txt).
- Numbers: hub [overview](overview.md); ledger sem* rows.
