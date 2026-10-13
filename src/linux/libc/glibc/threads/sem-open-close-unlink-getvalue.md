# `sem_open` / `sem_close` / `sem_unlink` / `sem_getvalue` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `semaphore.h` (`sem_open.3` also lists `fcntl.h` for `O_*` and `sys/stat.h` for mode constants) |
| Standards | POSIX.1-2001, POSIX.1-2008 (named semaphores) |
| Exported | `sem_open@@GLIBC_2.34`, `sem_close@@GLIBC_2.34`, `sem_unlink@@GLIBC_2.34`, `sem_getvalue@@GLIBC_2.34`, all plus compat `@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all four (ATTRIBUTES tables of `sem_open(3)`, `sem_close(3)`, `sem_unlink(3)`, `sem_getvalue(3)`) |
| Ledger ID | GLIBC-sem_open, GLIBC-sem_close, GLIBC-sem_unlink, GLIBC-sem_getvalue |

## Declaration and gates

```c
#include <fcntl.h>        /* O_* constants */
#include <sys/stat.h>     /* mode constants */
#include <semaphore.h>

sem_t *sem_open(const char *name, int oflag);                 /* :42 */
sem_t *sem_open(const char *name, int oflag,
                mode_t mode, unsigned int value);             /* :42 */
int sem_close(sem_t *sem);                                    /* :46 */
int sem_unlink(const char *name);                             /* :49 */
int sem_getvalue(sem_t *restrict sem, int *restrict sval);    /* :106 */
```

No feature-test gate: these four are declared unconditionally in
`/usr/include/semaphore.h` (lines 42-49, 106-107). The unnamed-semaphore
half of the API is in
[sem-init-destroy-wait-trywait-timedwait-clockwait-post](sem-init-destroy-wait-trywait-timedwait-clockwait-post.md).

## Semantics

`sem_open` creates (with `O_CREAT`, supplying `mode` and initial
`value`; `mode` is masked against the umask) or opens the named
semaphore `name`, failing with `SEM_FAILED` and `errno` on error; with
both `O_CREAT` and `O_EXCL` an existing name is an error
(`sem_open(3)`). `sem_close` releases the calling process's resources
for the semaphore; the semaphore itself survives. `sem_unlink` removes
the name immediately; the object is destroyed once every process that
has it open closes it (`sem_unlink(3)`). `sem_getvalue` stores the
current value; POSIX allows 0 or a negative waiter count for a
semaphore with blocked waiters -- Linux takes the 0 form
(`sem_getvalue(3)`).

## Gotchas and portability

- The manual's safety notes record that glibc locates the mounted shmfs
  for named semaphores once via `pthread_once`
  (`threads.texi`, *POSIX Semaphores* node comments).
- musl 1.2.5: `sem_open.c` also implements `sem_close` and creates its
  backing files under `/dev/shm` (`musl src/thread/sem_open.c:118,168`).

## Errors

- `sem_open`: `EACCES`, `EEXIST`, `EINVAL` (bad `value` past
  `SEM_VALUE_MAX`, or `name` of just "/"), `EMFILE`, `ENAMETOOLONG`,
  `ENFILE`, `ENOENT`, `ENOMEM` (`sem_open(3)`).
- `sem_close`/`sem_getvalue`: `EINVAL` (invalid `sem`; the glibc
  `sem_getvalue` currently does not validate it).
- `sem_unlink`: `EACCES`, `ENAMETOOLONG`, `ENOENT`.

## References

- man3: `sem_open(3)`, `sem_close(3)`, `sem_unlink(3)`,
  `sem_getvalue(3)` (`source-cache/man-pages-sparse/man3/`)
- glibc manual: `threads.texi`, node *POSIX Semaphores*
- header: `/usr/include/semaphore.h` lines 42-49, 106-107
- symbols: `nm -D --with-symbol-versions libc.so.6`
