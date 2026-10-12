# `call_once` (3) - glibc

> Split from the chapter *glibc: Threads* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `threads.h` |
| Standards | C11 section 7.26 (ISO C threads); C23 also exposes the flag type from `stdlib.h`, C only |
| Exported | `call_once@@GLIBC_2.34` plus compat `call_once@GLIBC_2.28` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety note, *Call Once* node) |
| Ledger ID | GLIBC-call_once |

## Declaration and gates

```c
#include <threads.h>

typedef __once_flag once_flag;                         /* threads.h:61 */
#define ONCE_FLAG_INIT __ONCE_FLAG_INIT                /* threads.h:62 */

void call_once(once_flag *flag, void (*func)(void));   /* threads.h:175 */
```

No feature-test gate: `threads.h` declares `call_once` and the flag type in
every compilation mode. The manual notes that as of C23 `once_flag` and
`ONCE_FLAG_INIT` are also defined in `stdlib.h`, but only for C, not C++
(`threads.texi`, *Call Once*).

## Semantics

`call_once(flag, func)` invokes `func` exactly once, even if `call_once` is
invoked from several threads with the same `flag`. The completion of `func`
synchronizes-with all previous and subsequent calls to `call_once` with that
`flag`, so every caller observes the effects of the one execution (manual,
*Call Once*). `flag` must be initialized to `ONCE_FLAG_INIT` before first
use. The function returns `void` and reports no errors: a caller cannot
distinguish whether it ran `func` itself or another thread already did,
and a `func` that fails cannot trigger a retry.

## Gotchas and portability

- The POSIX twin is `pthread_once` with a `PTHREAD_ONCE_INIT` control,
  documented in [pthread_once](../process/pthread-once.md); the manual's
  ISO C section recommends `pthread.h` APIs for GNU systems in general.
- Exactly-once is per `flag` object; two distinct flags give two runs.
- musl 1.2.5: `call_once` is a real function
  (`musl src/thread/call_once.c`) and `ONCE_FLAG_INIT` is `0`
  (`musl include/threads.h:41`).

## References

- glibc manual: `threads.texi`, node *Call Once*
- header: `/usr/include/threads.h` lines 61-62, 175
- symbols: `nm -D --with-symbol-versions libc.so.6`
