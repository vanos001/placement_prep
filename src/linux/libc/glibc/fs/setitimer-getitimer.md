# `setitimer` / `getitimer` (3) - glibc

> Per-function page for the BSD interval timers of the glibc Date and Time
> family; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. The one-shot
> `alarm` and the sleep family live on the sibling page
> [timer-alarm-sleep.md](./timer-alarm-sleep.md).

| Field | Value |
|---|---|
| Header | `sys/time.h` (`setitimer`, `getitimer`, `struct itimerval`, `ITIMER_*`); `unistd.h` (`ualarm`) |
| Standards | BSD (`setitimer`, `getitimer`), BSD/SVID (`ualarm`); the manual: "The setitimer and getitimer functions are derived from BSD Unix, while the alarm function is specified by POSIX" |
| Exported | `setitimer`/`getitimer`/`ualarm` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `setitimer` MT-Safe race:timer (one timer set shared by all threads; kernel serializes, last call wins), AS-Safe, AC-Safe; `getitimer` fully safe (manual annotations) |
| Ledger ID | GLIBC-setitimer, GLIBC-getitimer, GLIBC-ualarm (all not-started rows at write time) |

## Declaration and gates

```c
#include <sys/time.h>
#include <unistd.h>

struct itimerval {
    struct timeval it_interval;  /* reload period; zero = one-shot */
    struct timeval it_value;     /* time to first expiry; zero = off */
};

int setitimer(int which, const struct itimerval *restrict new,
              struct itimerval *restrict old);
int getitimer(int which, struct itimerval *old);
useconds_t ualarm(useconds_t value, useconds_t interval); /* unistd.h */
/* ualarm/usleep gate in unistd.h:
   (defined __USE_XOPEN_EXTENDED && !defined __USE_XOPEN2K8)
   || defined __USE_MISC */
```

## Semantics

Each process has three independent interval timers (manual, *Setting an
Alarm*): `ITIMER_REAL` counts elapsed time and delivers `SIGALRM`;
`ITIMER_VIRTUAL` counts user-space processor time and delivers `SIGVTALRM`;
`ITIMER_PROF` counts user plus system time and delivers `SIGPROF`. Only one
timer of each kind can be set; setting an unexpired one simply resets it,
and a non-NULL `old` receives the previous unexpired value. `it_value` zero
disables the alarm. The manual's portability note: `setitimer` is more
powerful than `alarm`, but `alarm` is more widely used. `ualarm` is the
microsecond one-shot-plus-interval alarm of the same real-time timer
(header comment; no manual node).

## Gotchas and portability

- The manual warns to install the signal handler before the first timer
  call: delivery before installation terminates the process, since
  termination is the default action for all three alarm signals.
- To interrupt a blocking syscall with `SIGALRM`, do not set `SA_RESTART`;
  with `signal(3)` the BSD semantics set the flag, so the manual says to
  use `sysv_signal` if `sigaction` cannot be used.
- Delivery is not punctual: "you shouldn't count on the signal arriving
  precisely when the timer expires" (manual).
- musl 1.2.5: `src/unistd/alarm.c` literally implements `alarm` on top of
  `setitimer(ITIMER_REAL, ...)`, rounding up the old remaining value.

## References

- glibc manual: `time.texi`, node *Setting an Alarm* (three timers, flags,
  alarm-via-setitimer example)
- man2: `setitimer.2`, `getitimer.2`, `alarm.2`; man3 `ualarm.3`
- headers: `/usr/include/x86_64-linux-gnu/sys/time.h`, `/usr/include/unistd.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
