# `semctl` / `semget` - glibc

> Split from the chapter *glibc: Inter-Process Communication* into the
> per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/sem.h` (`semctl` line 52 with a `__USE_TIME64_REDIRECTS` redirect to `__semctl64`; `semget` line 64 -- both unconditional); constants from `bits/sem.h` |
| Standards | SVr4, POSIX.1-2001 (semctl.2, semget.2 CONFORMING TO) |
| Exported | `semctl@@GLIBC_2.2.5` (T), `semget@@GLIBC_2.2.5` (T) (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES tables in semctl.2/semget.2; thin syscall wrappers |
| Ledger ID | GLIBC-semctl, GLIBC-semget |

## Declaration and gates

```c
#include <sys/sem.h>

int semctl(int semid, int semnum, int cmd, ...);   /* sys/sem.h:52 */
int semget(key_t key, int nsems, int semflg);      /* sys/sem.h:64 */

#define SEM_UNDO 0x1000   /* bits/sem.h:33 (used by semop, listed here) */
#define GETPID 11         /* bits/sem.h:35-42 */
#define GETVAL 12
#define GETALL 13
#define GETNCNT 14
#define GETZCNT 15
#define SETVAL 16
#define SETALL 17
/* __USE_MISC: SEM_STAT 18, SEM_INFO 19, SEM_STAT_ANY 20 (bits/sem.h:58-62) */
#define _SEM_SEMUN_UNDEFINED 1   /* bits/sem.h:56 */
```

## Semantics

`semget(key, nsems, semflg)` returns the identifier of the System V
semaphore set for `key`: an existing one, or a new set of `nsems`
semaphores when `key == IPC_PRIVATE` or `IPC_CREAT` is set and no set
exists; `IPC_CREAT|IPC_EXCL` fails with `EEXIST` if it already exists
(semget.2). POSIX leaves the values of a new set's semaphores
*indeterminate* -- Linux zeroes them, but a portable program must run a
first `semctl` `SETVAL`/`SETALL` (semget.2, "Semaphore initialization").
`semctl` performs control operations on set `semid` or its
`semnum`-th semaphore: `IPC_STAT`/`IPC_SET`/`IPC_RMID` on the set,
`GETVAL`/`SETVAL`, `GETALL`/`SETALL`, `GETPID`, `GETNCNT`, `GETZCNT`, and
the Linux extras `IPC_INFO`/`SEM_INFO`/`SEM_STAT(_ANY)` (semctl.2; the
`__USE_MISC`-gated constants match bits/sem.h). With 4 arguments the
fourth is **`union semun`, defined by the calling program** -- glibc
deliberately does not define it and instead defines
`_SEM_SEMUN_UNDEFINED` (bits/sem.h lines 44-56; semctl.2 says "The
calling program must define this union").

## Gotchas and portability

- The varargs prototype means no type checking: pass the union *by
  value* exactly as semctl.2 shows, or garbage follows.
- On 32-bit/time64 setups `semctl` may redirect to `__semctl64`
  (`__USE_TIME64_REDIRECTS`, sys/sem.h lines 51-61) -- the kernel
  distinguishes old/new layouts by the `IPC_64` flag (semctl.2 NOTES).
- `SEM_STAT_ANY` (glibc 2.32-era addition, `__USE_MISC`) reads another
  owner's stats without permission checks.
- musl 1.2.5: both present, same gates (`include/sys/sem.h` lines 55-56).

## Errors

`semget`: `EACCES`, `EEXIST`, `EINVAL`, `ENOENT`, `ENOMEM`, `ENOSPC`
(semget.2). `semctl`: `EACCES`, `EFAULT`, `EIDRM`, `EINVAL`, `EPERM`,
`ERANGE` (semctl.2 ERRORS). Raw pages:
[semget](../../../syscalls/net-ipc/semget.md),
[ipc](../../../syscalls/net-ipc/ipc.md).

## References

- man2: `semctl.2`, `semget.2`
- glibc manual: `ipc.texi`, node *Semaphores* (System V subsection)
- headers: `/usr/include/x86_64-linux-gnu/sys/sem.h`, `bits/sem.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
