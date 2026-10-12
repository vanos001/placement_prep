# Real-Time Signals

The real-time signal range (`SIGRTMIN`–`SIGRTMAX`) is the part of the Linux signal space with
**queueing** and **ordering** guarantees, added by POSIX.1b and implemented in Linux 2.2+. This
chapter covers placement (`SIG-035`), queueing (`SIG-036`), delivery order (`SIG-037`), limits
and `EAGAIN` (`SIG-038`), `sigqueue(3)`/`rt_sigqueueinfo(2)` (`SIG-039`), and the practical
trade-offs and misconceptions (`SIG-040`). The standard signals' no-queue semantics are covered
in [Standard signals](./standard-signals.md).

## Placement: kernel range vs libc reservation (SIG-035)

Per [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html):

- **The kernel** supports a range of 33 real-time signals, numbered **32 to 64**, on every
  architecture except mips. The kernel UAPI headers define `SIGRTMIN 32` and
  `SIGRTMAX _NSIG` (= 64); mips defines `_NSIG 128`, so its kernel range is **32 to 127**
  (verified in `arch/mips/include/uapi/asm/signal.h`). POSIX.1-2001 requires only
  `_POSIX_RTSIG_MAX` (8) real-time signals.
- **glibc with NPTL** internally uses two real-time signals and adjusts `SIGRTMIN` accordingly,
  so on a typical glibc system `SIGRTMIN` is **34** and `SIGRTMAX` 64 (per signal(7); the
  reservation is also visible in the man pages for sigprocmask(2)/sigwait(3), which state that
  the glibc wrappers *silently ignore* attempts to block or wait for the two NPTL-internal
  real-time signals). The older LinuxThreads implementation used three, shifting `SIGRTMIN` to
  35 on those systems. See also [nptl(7)](https://man7.org/linux/man-pages/man7/nptl.7.html).
- **musl** does the same thing with different numbers: it reserves signals 32–34
  (`SIGTIMER 32`, `SIGCANCEL 33`, `SIGSYNCCALL 34`, verified in musl's
  `src/internal/pthread_impl.h`) and its `SIGRTMIN` function returns **35** with
  `SIGRTMAX = _NSIG-1` (verified in musl's `src/signal/sigrtmin.c`/`sigrtmax.c`).
- Both glibc and musl implement `SIGRTMIN`/`SIGRTMAX` as **runtime function calls**, not
  compile-time constants (glibc: `__libc_current_sigrtmin`), precisely because the value can
  depend on the threading implementation in use.

The operational rule that follows (per signal(7)): *never hardcode real-time signal numbers*.
Always use `SIGRTMIN+n` and check at runtime that `SIGRTMIN+n <= SIGRTMAX`.

```c
#include <signal.h>

int n = 2;                      /* second application-reserved RT signal */
if (SIGRTMIN + n > SIGRTMAX) {  /* runtime check — SIGRTMIN is a function call */
    /* out of real-time signal budget */
}
```

Unlike standard signals, real-time signals have **no predefined meaning**: the whole range is
available for application-defined purposes, and the default action for an unhandled real-time
signal is to terminate the process (per signal(7)).

## Queuing guarantees (SIG-036)

Real-time signals are distinguished from standard signals by three properties, per signal(7)
and [POSIX.1-2017](https://pubs.opengroup.org/onlinepubs/9699919799/) (XSH 2.4 *Signal
Concepts*):

1. **Multiple instances queue.** If the same real-time signal is generated several times while
   blocked, one pending instance is retained *per generation*, not collapsed. (Standard
   signals collapse to one pending instance.)
2. **A value may accompany the signal** — `union sigval`, an `int` or pointer — delivered
   through `si_value` of `siginfo_t` when the receiver installs the handler with `SA_SIGINFO`
   (or retrieves it from `sigwaitinfo(2)`/`sigtimedwait(2)`).
3. **Guaranteed delivery order** — see the next section.

The queue is bounded by `RLIMIT_SIGPENDING` (below), which is what makes "queued" and "lost
with `EAGAIN`" two sides of the same design. Note the kernel's `siginfo` for a queued signal is
allocated from a per-user pool when the signal is *generated* — the resource is released again
when the signal is consumed (`sigwaitinfo(2)`, handler, or default action).

## Delivery ordering (SIG-037)

Per signal(7):

- Multiple real-time signals of the **same type** are delivered in the order they were sent
  (FIFO within one signal number).
- **Different** real-time signal types are delivered starting with the **lowest-numbered**
  signal — low numbers have the *highest* priority. (POSIX.1-2017 states the same rule for the
  `SIGRTMIN`–`SIGRTMAX` range: "the lowest numbered shall be selected first".)
- If both standard and real-time signals are pending, POSIX leaves the choice unspecified;
  **Linux delivers standard signals first** in this case (per signal(7)) — the same priority
  rule applies to what `sigwaitinfo(2)` selects when both classes are in the wait set.

## Limits: RLIMIT_SIGPENDING, EAGAIN, history (SIG-038)

Per [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html) and
[getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html):

- POSIX suggests `_POSIX_SIGQUEUE_MAX` (32) queued signals per process; Linux does something
  different. **Up to and including Linux 2.6.7** there was a *system-wide* limit, tunable via
  `/proc/sys/kernel/rtsig-max` (current usage visible in `rtsig-nr`). **Since Linux 2.6.8**
  these files are gone and the limit is the per-user resource limit
  **`RLIMIT_SIGPENDING`** — a limit on the number of signals that may be queued *for the real
  user ID of the calling process*.
- `RLIMIT_SIGPENDING` counts **both** standard and real-time queued signals, but it is
  **enforced only for `sigqueue(3)`**: `kill(2)` can always queue one instance of any signal
  that is not already queued to the process (per getrlimit(2)). In other words, the limit is a
  cap on *extra* queued instances, not on basic notification.
- When the limit is reached (or kernel memory for the queue entry is unavailable), queued
  sends fail: `sigqueue(3)` returns `-1` with `EAGAIN` (per
  [sigqueue(3)](https://man7.org/linux/man-pages/man3/sigqueue.3.html)); the raw `tgkill(2)`
  reports `EAGAIN` for a real-time signal when `RLIMIT_SIGPENDING` is hit or memory is short
  (per [tgkill(2)](https://man7.org/linux/man-pages/man2/tgkill.2.html)). Well-behaved senders
  must treat `EAGAIN` as back-pressure and retry later.
- The default limit on Linux is typically a few thousand per user (commonly 8192) — check
  `ulimit -i` / `prlimit` rather than trusting a constant, and note it is *per real UID*, so
  one user's runaway child can exhaust the budget of everything else they run.

## Sending queued signals with a value (SIG-039)

[`sigqueue(3)`](https://man7.org/linux/man-pages/man3/sigqueue.3.html) is the POSIX interface:

```c
#include <signal.h>
int sigqueue(pid_t pid, int sig, const union sigval value);

union sigval {
    int    sival_int;
    void  *sival_ptr;
};
```

Permission checking is the same as `kill(2)`, and `sig` = 0 is a liveness probe as with
`kill(2)` (per sigqueue(3)). On Linux, sigqueue(3) is implemented on top of the raw
[`rt_sigqueueinfo(2)`](https://man7.org/linux/man-pages/man2/rt_sigqueueinfo.2.html) system
call; the glibc wrapper initializes the kernel's `siginfo_t` argument as
`si_signo = sig`, `si_code = SI_QUEUE`, `si_pid = getpid()`, `si_uid = getuid()`,
`si_value = val` (per sigqueue(3) VERSIONS). `rt_sigqueueinfo(2)` has no glibc wrapper; its
thread-directed sibling `rt_tgsigqueueinfo(2)` (Linux ≥ 2.6.31) targets one thread
(`tgid`, `tid`) and backs `pthread_sigqueue(3)`.

The kernel is deliberately suspicious of user-supplied `siginfo_t`: per rt_sigqueueinfo(2),
for any target other than the caller itself, `si_code` must be **less than zero** — it cannot
be `SI_USER` or `SI_KERNEL` (kill/kernel-generated markers) and, since Linux 2.6.39, cannot be
`SI_TKILL` — otherwise the call fails with `EPERM`. This prevents forging "the kernel sent
SIGSEGV at address X" records.

On the receiving side, the queued value arrives via `si_value`/`si_int`/`si_ptr` when the
handler was installed with `SA_SIGINFO` (or via `sigwaitinfo(2)`'s `info` argument);
`si_pid`/`si_uid` identify the sender (per sigqueue(3) and sigaction(2)).

## Practical trade-offs and misconceptions (SIG-040)

- **Misconception: "real-time signals are for real-time scheduling."** They are not. The name
  comes from POSIX.1b's real-time extensions; the signals carry no scheduling semantics. They
  are *reliable, queueable, ordered* signals for application events.
- **Misconception: "only real-time signals queue at all."** Precise version: standard signals
  collapse while blocked (one pending instance, see
  [Standard signals](./standard-signals.md)); a standard signal *sent with `sigqueue(3)`*
  carries its `siginfo` value and keeps the value of the first instance while pending, but
  still never queues more than one instance. POSIX.1-2017 words it carefully: with `SA_SIGINFO`
  set and resources available, the signal "shall be queued"; without `SA_SIGINFO`, `sigqueue()`
  guarantees only that the signal is sent *at least once*, and whether the value arrives is
  unspecified.
- **Misconception: "`SA_SIGINFO` is required for queuing."** No — queuing is a kernel-side
  property (bounded by `RLIMIT_SIGPENDING`), independent of how the receiver handles the
  signal. `SA_SIGINFO` only controls the *handler form* (and thus whether your program can see
  `si_value`). Installing a one-argument handler for an RT signal still gets one delivery per
  queued instance; it just cannot read the payload (per sigaction(2)/sigqueue(3)).
- **Why glibc's reservation matters in practice**: a library that grabs `SIGRTMIN` for itself
  collides with NPTL's internal signals 34–35 (or musl's 32–34). Always start at `SIGRTMIN+n`
  with `n` chosen so third-party libraries and your own code do not overlap, and propagate the
  choice through plugin APIs.
- **Alternatives worth considering**: for event delivery into event loops, `signalfd(2)`
  (kernel ≥ 2.6.22) or the self-pipe trick often integrate better than RT signals — see
  [signalfd and pidfd](../interfaces/signalfd-pidfd.md) and
  [Async-signal safety](../interfaces/async-signal-safety.md). For timer-style events,
  `timerfd_create(2)` avoids signals entirely. RT signals remain the right tool when you need
  *many distinct ordered events with small payloads* and a process-wide (not per-fd) channel.

## Related Topics

- [Standard signals](./standard-signals.md) — the non-queueing half and the arch numbering table
- [Signals overview](../../sysprog/signals.md) — survey-level RT signal usage
- [Sigwait and sigsuspend](../interfaces/sigwait-sigsuspend.md) — synchronous consumption of queued signals
- [signalfd and pidfd](../interfaces/signalfd-pidfd.md) — fd-based signal consumption
- [Per-syscall page: kill(2)](../../syscalls/signals-time/kill.md), [rt_sigaction(2)](../../syscalls/signals-time/rt_sigaction.md)

## References

- *signal(7) — overview of signals*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man7/signal.7.html>
- *sigqueue(3)*, man-pages 6.19, <https://man7.org/linux/man-pages/man3/sigqueue.3.html>
- *rt_sigqueueinfo(2) / rt_tgsigqueueinfo(2)*, man-pages 6.19, <https://man7.org/linux/man-pages/man2/rt_sigqueueinfo.2.html>
- *getrlimit(2) / setrlimit(2) / prlimit(2)*, man-pages 6.19, <https://man7.org/linux/man-pages/man2/getrlimit.2.html> (RLIMIT_SIGPENDING)
- *sigwaitinfo(2) / sigtimedwait(2)*, man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigtimedwait.2.html>
- *tgkill(2)*, man-pages 6.19, <https://man7.org/linux/man-pages/man2/tgkill.2.html>
- *POSIX.1-2017*, The Open Group, <https://pubs.opengroup.org/onlinepubs/9699919799/> (XSH 2.4 Signal Concepts; `sigqueue()`, `sigwaitinfo()`)
- *nptl(7)*, Linux man-pages, <https://man7.org/linux/man-pages/man7/nptl.7.html>
- *musl libc source* (reservation and `SIGRTMIN` values, verified): `src/internal/pthread_impl.h`, `src/signal/sigrtmin.c`, <https://git.musl-libc.org/cgit/musl/tree/src/signal>
- *Linux kernel UAPI headers*: [`arch/mips/include/uapi/asm/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/arch/mips/include/uapi/asm/signal.h), [`include/uapi/asm-generic/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/asm-generic/signal.h)
