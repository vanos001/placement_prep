# `alarm` / `sleep` / `usleep` / `nanosleep` (3) - glibc

> Per-function page for the sleep and one-shot alarm family of the glibc
> Date and Time chapter; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. The interval
> timers underneath `alarm` live on
> [setitimer-getitimer.md](./setitimer-getitimer.md).

| Field | Value |
|---|---|
| Header | `unistd.h` (`alarm`, `sleep`, `usleep`, `ualarm`); `time.h` (`nanosleep`, `clock_nanosleep`) |
| Standards | POSIX.1 (`alarm`, `sleep`, `nanosleep`); BSD (`ualarm`); POSIX.1-2001 declares `usleep` obsolete and POSIX.1-2008 removes it (man `usleep.3`) |
| Exported | `alarm`/`sleep`/`usleep`/`nanosleep` `@@GLIBC_2.2.5`; `clock_nanosleep` default `@@GLIBC_2.17` with `@GLIBC_2.2.5` compat alias (nm, host glibc 2.41) |
| Thread-safety | `alarm`/`setitimer`-class MT-Safe race:timer; `sleep` MT-Unsafe sig:SIGCHLD/linux (blocks SIGCHLD on Linux, manual annotation); `nanosleep` MT-Safe AS-Safe AC-Safe but a cancellation point (manual) |
| Ledger ID | GLIBC-alarm (not-started), GLIBC-sleep (documented), GLIBC-usleep (documented triage), GLIBC-nanosleep (documented) |

## Declaration and gates

```c
#include <unistd.h>
#include <time.h>

unsigned int alarm(unsigned int seconds);      /* 0 cancels */
unsigned int sleep(unsigned int seconds);      /* cancellation point */
int usleep(useconds_t useconds);               /* gated __USE_MISC or
                                                  XOPEN_EXTENDED minus
                                                  XOPEN2K8 (header) */
int nanosleep(const struct timespec *req, struct timespec *rem);
int clock_nanosleep(clockid_t clock, int flags,
                    const struct timespec *req, struct timespec *rem);
```

## Semantics

`alarm` schedules `SIGALRM` after `seconds`; the return is the seconds the
previous alarm still had, and zero cancels. `sleep` waits the full interval
or until a signal is delivered, returning the remaining seconds in the
latter case (manual, *Sleeping*). `nanosleep` takes nanosecond resolution,
rounds up to the system's timer resolution, writes the remaining time to
`rem` on `EINTR`, and rejects `tv_nsec` below 0 or at 1000 million with
`EINVAL` (manual). `clock_nanosleep` adds clock selection and
`TIMER_ABSTIME`, and returns the error number as a positive value instead of
using `errno` (manual).

## Gotchas and portability

- On GNU systems `sleep` does not use `SIGALRM`, so the manual says it is
  safe to use `sleep` and `SIGALRM` in one program; POSIX-portable code
  should not rely on that ("sleep might return prematurely on delivery of a
  SIGALRM" on some systems, manual).
- Do not retry `sleep(rem)` in a loop: accumulated signal timing skews the
  wakeup; the manual recommends computing the target calendar time.
- `usleep`/`ualarm` are the BSD leftovers - obsolete per the man page, still
  exported (nm), still cancellation points (header comment).
- musl 1.2.5: `src/time/nanosleep.c` is
  `__clock_nanosleep(CLOCK_REALTIME, 0, req, rem)`; `src/unistd/alarm.c`
  builds `alarm` from `setitimer`; musl has `usleep.c` in `src/unistd`.

## References

- glibc manual: `time.texi`, nodes *Setting an Alarm*, *Sleeping*
- man2: `nanosleep.2`, `alarm.2`; man3 `sleep.3`, `usleep.3`, `ualarm.3`
- headers: `/usr/include/unistd.h`, `/usr/include/time.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
