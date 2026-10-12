# sigaction(2) and signal(2) — Installing Dispositions (IF-003, IF-004)

Two interfaces install signal dispositions: `sigaction(2)` — the POSIX-specified, fully
specified one — and `signal(2)` — the C-standard function whose handler semantics are
deliberately unspecified and which you should treat as legacy. This chapter documents the full
`struct sigaction`, every `sa_flags` bit, the `siginfo_t`/`si_code` contract, and the exact
glibc behavior that makes `signal(2)` a portability hazard.

## sigaction(2) (IF-003)

```c
#include <signal.h>              /* feature test: _POSIX_C_SOURCE */

int sigaction(int signum,
              const struct sigaction *_Nullable restrict act,
              struct sigaction *_Nullable restrict oldact);
```

**Category**: libc wrapper around the `rt_sigaction(2)` system call on Linux (the glibc wrapper
inserts its own signal trampoline — see
[rt_sig* kernel ABI](./rt-sig-syscalls.md)). POSIX.1 (man-pages 6.19: POSIX.1-2024; kernel
entry since Linux 2.2 as `rt_sigaction`, per
[sigaction(2)](https://man7.org/linux/man-pages/man2/sigaction.2.html)).

`signum` may be any valid signal **except `SIGKILL` and `SIGSTOP`** (`EINVAL` otherwise). If
`act` is non-NULL the disposition is installed; if `oldact` is non-NULL the previous one is
saved — so `sigaction(sig, NULL, &old)` is a query (per sigaction(2)). Errors: `EINVAL`
(invalid signal or `SIGKILL`/`SIGSTOP`), `EFAULT` (bad pointers).

### struct sigaction (glibc view)

```c
struct sigaction {
    void     (*sa_handler)(int);                            /* or ... */
    void     (*sa_sigaction)(int, siginfo_t *, void *);     /* when SA_SIGINFO */
    sigset_t  sa_mask;      /* extra signals to block during the handler */
    int       sa_flags;     /* OR of SA_* flags, table below */
    void    (*sa_restorer)(void);   /* internal: libc trampoline, not for apps */
};
```

Per sigaction(2): "On some architectures a union is involved: do not assign to both
`sa_handler` and `sa_sigaction`." `sa_restorer` is not intended for application use and POSIX
does not specify it. (The *kernel* `struct sigaction` differs per architecture — field order
and the `SA_RESTORER` bit vary; that is the subject of
[rt-sig-syscalls.md](./rt-sig-syscalls.md).)

Behavior on delivery: `sa_mask` signals are added to the thread's mask while the handler runs,
and the delivered signal itself is added too **unless** `SA_NODEFER`; after the handler
returns (via the trampoline's `sigreturn(2)`) the previous mask is restored (per sigaction(2)
and signal(7)). Attempts to put `SIGKILL`/`SIGSTOP` in `sa_mask` are silently ignored.

### sa_flags (all documented values)

| Flag | Effect (per sigaction(2)) | POSIX status |
|------|---------------------------|--------------|
| `SA_NOCLDSTOP` | If `signum == SIGCHLD`, do not notify when children stop/continue. | POSIX.1-1990 |
| `SA_NOCLDWAIT` | (Linux ≥ 2.6) If `signum == SIGCHLD`, children are not turned into zombies. POSIX leaves unspecified whether `SIGCHLD` is still generated; Linux *does* generate one. | XSI extension |
| `SA_NODEFER` | Do not auto-block the delivered signal during its handler (unless listed in `sa_mask`). Alias `SA_NOMASK`. | POSIX.1-2008 base |
| `SA_ONSTACK` | Run the handler on the `sigaltstack(2)` alternate stack; fall back to the normal stack if none is configured. | XSI extension |
| `SA_RESETHAND` | Restore `SIG_DFL` on handler entry (System V style). Alias `SA_ONESHOT`. | POSIX.1-2008 base |
| `SA_RESTART` | BSD semantics: automatically restart interruptible syscalls after the handler (see the restart table in signal(7)). | XSI extension |
| `SA_SIGINFO` | Handler takes `(int, siginfo_t *, void *)` via `sa_sigaction`. | POSIX.1-2008 base |
| `SA_RESTORER` | Internal: `sa_restorer` holds the libc trampoline. Never set it yourself. | Linux/libc |
| `SA_UNSUPPORTED` | (Linux ≥ 5.11) Probe bit: register with it set, re-query with `oldact`; if cleared, other `sa_flags` bits you asked about are reported accurately. | Linux |
| `SA_EXPOSE_TAGBITS` | (Linux ≥ 5.11) Preserve the architecture-defined tag bits (e.g. ARM MTE) in `siginfo.si_addr`. | Linux |

One quirk worth remembering: unknown `sa_flags` bits are **accepted silently** by Linux, and
before 5.11 a re-query did not clear them — hence the `SA_UNSUPPORTED` dance for feature
detection (per sigaction(2), including the sample probe program).

### SA_SIGINFO: siginfo_t fields and si_code

With `SA_SIGINFO`, the handler is `void handler(int sig, siginfo_t *info, void *ucontext)`.
Per sigaction(2), the interesting fields by cause:

- Always valid: `si_signo`, `si_errno` (generally unused on Linux), `si_code`.
- `kill(2)`/`sigqueue(3)`: `si_pid`, `si_uid`; `sigqueue(3)` also fills `si_int`/`si_ptr` (= `si_value`).
- POSIX timers: `si_overrun`, `si_timerid` (Linux extensions).
- `SIGCHLD`: `si_pid`, `si_uid`, `si_status`, `si_utime`, `si_stime` (CLD_* codes).
- `SIGILL`, `SIGFPE`, `SIGSEGV`, `SIGBUS`, `SIGTRAP`: `si_addr` (fault address; `si_trapno` on
  some arches), plus `si_addr_lsb` (`BUS_MCEERR_*`), `si_lower`/`si_upper` (`SEGV_BNDERR`),
  `si_pkey` (`SEGV_PKUERR`).
- `SIGIO`/`SIGPOLL`: `si_band`, `si_fd`.
- `SIGSYS` (seccomp `SECCOMP_RET_TRAP`): `si_call_addr`, `si_syscall`, `si_arch`.

`si_code` values (sigaction(2)); the generic ones apply to any signal:

| `si_code` | Meaning |
|-----------|---------|
| `SI_USER` | sent by `kill(2)` |
| `SI_KERNEL` | sent by the kernel |
| `SI_QUEUE` | sent by `sigqueue(3)` |
| `SI_TIMER` | POSIX/alarm/setitimer timer expired |
| `SI_MESGQ` | POSIX message queue notification |
| `SI_ASYNCIO` | AIO completed |
| `SI_TKILL` | `tgkill(2)`/`tkill(2)` |
| `SI_ASYNCNL` | async name lookup |
| `ILL_*` / `FPE_*` / `SEGV_*` / `BUS_*` / `TRAP_*` / `CLD_*` / `POLL_*` / `SYS_SECCOMP` / `SYS_USER_DISPATCH` / `EMT_TAGOVF` | signal-specific subcodes (full lists in sigaction(2)) |

Kernel BUGS note (sigaction(2)): for hardware-exception signals the kernel does not always
fill every relevant `siginfo_t` field — e.g. `x86 int` with a forbidden argument yields
`SIGSEGV` with all fields but `si_signo`/`si_code` zeroed.

## signal(2) — why it is a hazard (IF-004)

```c
#include <signal.h>
sighandler_t signal(int signum, sighandler_t handler);   /* sighandler_t: GNU */
/* standard form: void (*signal(int, void (*)(int)))(int); */
```

**Category**: libc function. The kernel also has a `signal(2)` syscall, but glibc does *not*
use it for `signal()` by default. Per
[signal(2)](https://man7.org/linux/man-pages/man2/signal.2.html):

- The **kernel's** `signal()` syscall provides **System V semantics** — equivalent to
  `SA_RESETHAND | SA_NODEFER`: the disposition resets to default on delivery and the signal is
  not blocked during the handler, so a rapid second delivery can re-enter the handler before
  it re-installs itself.
- **glibc ≥ 2** (default feature set: `_BSD_SOURCE`/`_DEFAULT_SOURCE`, which are defined by
  default) implements `signal()` *on top of `sigaction(2)`* with **BSD semantics** —
  equivalent to `SA_RESTART`: disposition persists, the signal is auto-blocked during its
  handler, and certain syscalls restart. If those macros are not defined, glibc `signal()`
  reverts to System V semantics.

So the *same source line* gets different flags depending on feature macros — this is precisely
the portability hazard POSIX acknowledges: POSIX.1 permits the variation, and signal(2) says
"the only portable use of signal() is to set a signal's disposition to SIG_DFL or SIG_IGN".
Related glibc variants make the choice explicit: `sysv_signal(3)` and `bsd_signal(3)` (and the
obsolete `sigvec(3)`). In a multithreaded process the effects of `signal()` are unspecified
(per signal(2) NOTES). `signal()` returns the previous handler or `SIG_ERR` with `errno` set.

**Why sigaction is preferred**: explicit flags instead of platform defaults, `sa_mask` control,
`SA_SIGINFO` payloads, defined `EINTR`/restart behavior via `SA_RESTART`, and well-defined
multithreaded behavior.

## Minimal example

```c
/* sigaction-demo.c — SA_SIGINFO handler printing si_code and sender.
 * Expected: run; kill -USR1 <pid> prints "SIGUSR1 code=SI_USER(=-1) from pid <N>".
 * (Exact SI_* numeric values vary; the symbolic names are the contract.)
 */
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <string.h>

static void handler(int sig, siginfo_t *info, void *ucontext) {
    (void)ucontext;
    printf("sig=%d si_code=%d sender_pid=%d\n",
           sig, info->si_code, info->si_pid);
}

int main(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = handler;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;   /* not SA_NODEFER/SA_RESETHAND */
    sigemptyset(&sa.sa_mask);
    sigaddset(&sa.sa_mask, SIGUSR2);         /* also block USR2 inside handler */

    if (sigaction(SIGUSR1, &sa, NULL) == -1) { perror("sigaction"); return 1; }
    printf("pid=%d — send: kill -USR1 %d\n", getpid(), getpid());
    pause();                                  /* see sigwait-sigsuspend.md */
    return 0;
}
```

Note the deliberate use of `SA_RESTART` (BSD behavior, opt-in) and the absence of
`SA_NODEFER` (recursive-handler protection stays on).

## Related Topics

- [rt_sigaction and the kernel ABI](./rt-sig-syscalls.md) — per-arch struct layout, `sa_restorer`, sigsetsize
- [Signal masks and pending signals](./signal-masks.md) — `sa_mask` interacts with the thread mask
- [Async-signal safety](./async-signal-safety.md) — what the handler may call
- [kill, raise, and the kill utility](./kill-raise.md) — the sending side
- [Per-syscall page: rt_sigaction(2)](../../syscalls/signals-time/rt_sigaction.md); glibc catalog row [GLIBC-sigaction](../../libc/ledger-glibc.md)
- [Signals overview](../../sysprog/signals.md) — survey-level handler examples

## References

- *sigaction(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigaction.2.html>
- *signal(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/signal.2.html>
- *sigaction*, POSIX.1-2017, <https://pubs.opengroup.org/onlinepubs/9699919799/functions/sigaction.html>
- *signal(7)*, <https://man7.org/linux/man-pages/man7/signal.7.html> (handler execution steps, restart table)
- *sigreturn(2)*, <https://man7.org/linux/man-pages/man2/sigreturn.2.html> (trampoline mechanics)
