# `pthread_getattr_default_np` / `pthread_setattr_default_np` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `pthread.h` (`_GNU_SOURCE`) |
| Standards | nonstandard GNU extensions (`pthread_getattr_default_np(3)`); glibc since 2.18 |
| Exported | `pthread_getattr_default_np@@GLIBC_2.34` plus compat `@GLIBC_2.18`; `pthread_setattr_default_np@@GLIBC_2.34` plus compat `@GLIBC_2.18` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe both (`pthread_getattr_default_np(3)` ATTRIBUTES; manual safety notes take locks around the process default) |
| Ledger ID | GLIBC-pthread_getattr_default_np, GLIBC-pthread_setattr_default_np |

## Declaration and gates

```c
#define _GNU_SOURCE
#include <pthread.h>

int pthread_getattr_default_np(pthread_attr_t *attr);         /* :407 */
int pthread_setattr_default_np(const pthread_attr_t *attr);   /* :426 */
```

Both sit in the `#ifdef __USE_GNU` block of `/usr/include/pthread.h`
(lines 393-430). They control the attribute values used when
[pthread_create](../process/pthread-create.md) is called with a NULL
`attr` argument.

## Semantics

`pthread_setattr_default_np` installs `*attr` -- a previously
initialized attribute object -- as the process-wide defaults for new
threads; `pthread_getattr_default_np` initializes `*attr` from those
defaults (`pthread_getattr_default_np(3)`). The supplied object must
satisfy the manual's constraints: every setting in it must be valid,
the stack address attribute must not be set, and a stack size of zero
means "leave the current default unchanged" (manual, *Default Thread
Attributes*). Both return 0 on success and a nonzero error number on
failure.

## Gotchas and portability

- Defaults are process state, not per-thread state: every later
  NULL-attr `pthread_create` sees the change, including from libraries.
- The defaults interact with the ulimit-based initial stack size
  mentioned on `pthread_create(3)`; query with
  `pthread_getattr_default_np` rather than assuming.
- musl 1.2.5: `pthread_setattr_default_np` exists but clamps the new
  stack and guard sizes to at least the previous values
  (`musl src/thread/pthread_setattr_default_np.c:21-22`); there is no
  `pthread_getattr_default_np`, and musl's process defaults are 128 KiB
  stack, 8192 guard (`musl src/internal/pthread_impl.h:197-198`).

## Errors

- `EINVAL` (`setattr_default_np`): an attribute setting is invalid, or
  the stack address attribute is set. `ENOMEM`
  (`setattr_default_np`): insufficient memory
  (`pthread_getattr_default_np(3)` ERRORS, manual *Default Thread
  Attributes*).

## References

- man3: `pthread_getattr_default_np(3)` (covers both)
  (`source-cache/man-pages-sparse/man3/`)
- glibc manual: `threads.texi`, node *Default Thread Attributes*
- header: `/usr/include/pthread.h` lines 393-430
- symbols: `nm -D --with-symbol-versions libc.so.6`
