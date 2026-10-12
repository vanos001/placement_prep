# `semop` / `semtimedop` - glibc

> Split from the chapter *glibc: Inter-Process Communication* into the
> per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/sem.h` (`semop` line 67 unconditional; `semtimedop` lines 72-73 under `__USE_GNU`, with a `__USE_TIME64_REDIRECTS` redirect to `__semtimedop64`; `struct sembuf` lines 40-45) |
| Standards | SVr4, POSIX.1-2001 (`semop`); `semtimedop` needs `_GNU_SOURCE` in glibc (semop.2 feature-test note) |
| Exported | `semop@@GLIBC_2.2.5` (T), `semtimedop@@GLIBC_2.3.3` (W) (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES tables in semop.2; thin syscall wrappers (the wait is kernel-side) |
| Ledger ID | GLIBC-semop, GLIBC-semtimedop |

## Declaration and gates

```c
#include <sys/sem.h>

int semop(int semid, struct sembuf *sops, size_t nsops);   /* sys/sem.h:67 */

#ifdef __USE_GNU   /* sys/sem.h:69-84 */
int semtimedop(int semid, struct sembuf *sops, size_t nsops,
               const struct timespec *timeout);
#endif

struct sembuf {                 /* sys/sem.h:40-45 */
    unsigned short int sem_num; /* semaphore number in the set, from 0 */
    short int sem_op;           /* operation */
    short int sem_flg;          /* IPC_NOWAIT, SEM_UNDO */
};
#define SEM_UNDO 0x1000         /* bits/sem.h:33 */
```

## Semantics

`semop` applies the `nsops` operations in `sops` **in array order and
atomically** -- all or nothing (semop.2). Per operation: a positive
`sem_op` adds to `semval` and always proceeds; zero waits for `semval`
to become 0 ("wait-for-zero"); negative decrements, blocking while
`semval < |sem_op|`, unless `IPC_NOWAIT` makes the call fail with
`EAGAIN`. `SEM_UNDO` maintains a per-process `semadj` so the operation is
reversed when the process exits -- the standard defense against dying
while holding a semaphore (semop.2). On success `sem_otime` is updated.
`semtimedop` (kernel 2.5.52, backported to 2.4.22; glibc 2.3.3, semop.2
VERSIONS) bounds any blocking with `timeout`: expiry fails with `EAGAIN`
and no operation is applied; NULL behaves exactly like `semop`; a signal
interrupt (`EINTR`) leaves `timeout` unchanged.

## Gotchas and portability

- Atomicity is per-call: batching operations in one `semop` call is the
  only way to avoid deadlocks between them.
- `SEM_UNDO` adjustments apply at process exit; a thread exiting inside
  a multithreaded process does not end the process, so undo may not fire
  when expected.
- glibc gates `semtimedop` behind `__USE_GNU`; musl 1.2.5 declares it
  unconditionally with a time64 `__REDIR` (`include/sys/sem.h` lines
  57-65) -- all four SysV sem functions exist in musl.
- Raw page: [semop](../../../syscalls/net-ipc/semop.md).

## Errors

`E2BIG` (`nsops > SEMOPM`), `EACCES`, `EAGAIN` (`IPC_NOWAIT` or timeout
expired), `EFAULT`, `EFBIG` (bad `sem_num`), `EIDRM`, `EINTR`, `EINVAL`,
`ENOMEM`, `ERANGE` (resulting `semval` over `SEMVMX`) (semop.2 ERRORS).

## References

- man2: `semop.2` (covers `semtimedop`; `semtimedop.2` is a `.so` link)
- glibc manual: `ipc.texi`, node *Semaphores*
- headers: `/usr/include/x86_64-linux-gnu/sys/sem.h`, `bits/sem.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
