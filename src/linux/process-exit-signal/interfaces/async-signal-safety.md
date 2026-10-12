# Async-Signal Safety — Writing Handlers That Do Not Blow Up (IF-017)

A signal handler interrupts your program at an arbitrary instruction boundary — possibly in
the middle of `malloc`, `printf`, or while a mutex is held. The rules for what a handler may
safely do are defined by POSIX and documented in
[signal-safety(7)](https://man7.org/linux/man-pages/man7/signal-safety.7.html); this chapter
explains the *why*, the safe-function list, the `volatile sig_atomic_t` idiom, the self-pipe
trick and its `signalfd(2)`/`eventfd(2)` successors, and the classic deadlock that motivates
all of it.

## The rule

Per signal-safety(7): an **async-signal-safe** function is one that can be called from within
a signal handler. POSIX.1 requires implementations to make a specific set of functions
async-signal-safe; anything else may be called only if you can argue reentrancy yourself. The
two accepted strategies (per signal-safety(7)):

1. The handler calls only async-signal-safe functions, and is reentrant with respect to the
   global data it touches.
2. Block signal delivery while calling unsafe functions or touching shared data — usually
   impractical at scale, so strategy 1 is the norm.

## Why functions are unsafe: reentrancy, locks, errno

- **Reentrancy** — stdio is the canonical example (per signal-safety(7)): buffered I/O keeps
  a static buffer plus counters/indexes. If the main program is inside `printf(3)` when the
  handler also calls `printf(3)`, the second call operates on half-updated state and produces
  garbage or crashes. Anything with static mutable state (`strtok(3)`, `getenv(3)`-style
  tables, `malloc`'s heap metadata) has the same defect.
- **Locks** — `malloc(3)` takes an internal lock; `syslog(3)` takes one; glibc's
  `aio_suspend(3)` uses `pthread_mutex_lock` and is explicitly listed as *not* safe in glibc
  (signal-safety(7) "Deviations in the GNU C library"). A handler that takes a lock the
  interrupted code already holds deadlocks instantly — see the example below.
- **errno** — most libc functions set `errno` on failure. A handler that calls any of them
  can clobber the `errno` value the interrupted code was about to inspect. POSIX guarantees
  (per signal-safety(7)): fetching and setting `errno` is async-signal-safe **provided** the
  handler saves it on entry and restores it before returning:

```c
static void handler(int sig) {
    int saved = errno;      /* save — the interrupted code may need it */
    /* ... only async-signal-safe calls ... */
    errno = saved;          /* restore */
}
```

- **Cancellation** — signal handlers that call cancellation points can break deferred
  cancellation regions (signal-safety(7) notes).

## The safe list, in practice

The complete POSIX list is a table in signal-safety(7) (with per-function additions through
POSIX.1-2008 TC2). The shapes that are safe are easy to remember:

- **Syscalls** — nearly all of section 2: `read`, `write`, `open`, `close`, `pipe`,
  `select`/`pselect`, `poll`, `kill`, `sigaction`, `sigprocmask`, `sigpending`, `sigsuspend`,
  `wait`/`waitpid`, `_exit`, `fcntl`, `dup`, `lseek`, `fstat`, `fsync`, `ftruncate`,
  `rename`, `unlink`, `chmod/chown`, `mkdir`, `socket` family, `accept`, `connect`,
  `send/recv`, `alarm`, `clock_gettime`, `time`, `uname`, `umask`… (full table in
  signal-safety(7)).
- **Narrow string/memory functions** — `memcpy`, `memset`, `strlen`, `strcmp`, `strlcpy`-style
  bounded forms, `strtok_r` (the `_r` reentrant variant, not `strtok`).
- **Signal-set helpers** — `sigemptyset`, `sigfillset`, `sigaddset`, `sigdelset`,
  `sigismember`; plus `raise`, `pthread_kill`, `pthread_self`, `siglongjmp` (with caveats).
- Everything else — `printf`, `malloc`, `syslog`, `pthread_mutex_lock`, `fopen`… — is off
  limits. Note `abort(3)` and `raise(3)` are safe; `exit(3)` is *not* (it runs `atexit`
  handlers and flushes stdio) — use `_exit(3)` from a handler.

## `volatile sig_atomic_t` — the only portable shared variable

The C standard (C11 7.14.1.1) restricts what a handler may access: objects of
`volatile sig_atomic_t` (and lock-free atomic objects, per C11 Annex/§7.14.1.1 as refined in
POSIX), plus lock-free `volatile sig_atomic_t`-qualified objects. `sig_atomic_t` is an
integer type that can be read/written atomically even when interrupted; `volatile` prevents
the compiler from caching it in a register across the wait loop. The canonical handler:

```c
/* sigflag.c — minimal, safe handler pattern.
 * Expected: Ctrl+C prints nothing during handling; after pause() returns,
 * "caught SIGINT (flag=1), exiting cleanly".
 */
#include <signal.h>
#include <stdio.h>

static volatile sig_atomic_t got_sigint = 0;   /* the whole handler contract */

static void handler(int sig) { got_sigint = 1; }   /* nothing else! */

int main(void) {
    struct sigaction sa = { .sa_handler = handler };
    sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, NULL);

    while (!got_sigint)
        pause();               /* or sigsuspend() for race-freedom */

    printf("caught SIGINT (flag=%d), exiting cleanly\n", got_sigint);
    return 0;
}
```

Modern alternative: C11/C++11 lock-free atomics (`volatile sig_atomic_t` for the C standard
case; `_Atomic`/`atomic_flag` where lock-free guarantees hold) — but the POSIX async-safe
contract for complex objects is still "don't".

## The mutex deadlock example

```c
/* deadlock.c — DO NOT RUN TO COMPLETION: this deadlocks by design.
 * The handler calls pthread_mutex_lock() on a mutex the interrupted
 * thread already holds — the same thread now blocks on itself forever.
 */
#include <pthread.h>
#include <signal.h>
#include <stdio.h>

static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;

static void bad_handler(int sig) {
    pthread_mutex_lock(&log_lock);      /* NOT async-signal-safe */
    fprintf(stderr, "got signal %d\n", sig);   /* also unsafe: stdio */
    pthread_mutex_unlock(&log_lock);
}

int main(void) {
    signal(SIGUSR1, bad_handler);
    pthread_mutex_lock(&log_lock);      /* main holds the lock... */
    raise(SIGUSR1);                     /* handler tries to take it again */
    puts("never reached");
    return 0;
}
```

The interrupted thread *is* the lock holder; the handler runs on the same thread and blocks
on a non-recursive mutex — the process wedges with the signal handler's stack frame frozen.
This is precisely the failure mode "only call async-signal-safe functions" exists to prevent.

## The self-pipe trick, and its successors

Handler code must be tiny — so the real work has to happen somewhere else. The classic
solution writes one byte to a pipe whose read end lives in the main event loop:

```c
/* selfpipe.c — handler does one write(2); the loop does the real work.
 * Expected: kill -USR1 <pid> => "event loop: SIGUSR1 processed".
 */
#include <signal.h>
#include <stdio.h>
#include <unistd.h>

static int sp[2];   /* sp[0] = read end, sp[1] = write end */

static void handler(int sig) {
    int saved = errno_var();            /* see note below */
    (void)sig;
    char b = (char)sig;
    write(sp[1], &b, 1);                /* async-signal-safe */
    errno = saved;
}
/* errno_var() stands for the usual "int saved = errno;" idiom — expanded
   in the real code below. */
```

with the loop end doing `select(2)`/`poll(2)`/`epoll` on `sp[0]`. Requirements and gotchas:
the pipe must be nonblocking (or the write can block if the pipe is full — use
`O_NONBLOCK`), the byte must be drained, and every byte written is one event.

Details done properly:

```c
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <sys/epoll.h>
#include <unistd.h>

static int spfd[2];

static void handler(int sig) {          /* only safe calls here */
    int saved = errno;
    char b = (char)sig;
    ssize_t r = write(spfd[1], &b, 1);  /* O_NONBLOCK pipe: never blocks */
    (void)r;
    errno = saved;
}

int main(void) {
    if (pipe(spfd)) { perror("pipe"); return 1; }
    /* set both ends nonblocking; add spfd[0] to your epoll instance;
       install `handler` for SIGINT/SIGTERM/SIGUSR1 via sigaction; then
       epoll_wait() and drain spfd[0] into your event queue. */
    (void)epoll_create(1);
    puts("self-pipe wired");
    pause();
}
```

Successors that replace the hand-rolled pipe (see
[signalfd and pidfd](./signalfd-pidfd.md) and
[eventfd(2)](../../syscalls/net-ipc/eventfd.md)):

- **`signalfd(2)`** — the kernel does what the self-pipe did: block the signals, then read
  full `signalfd_siginfo` records from an fd inside `epoll`. Richer payload, no byte draining,
  and consumption semantics identical to `sigwaitinfo`. This is the modern default.
- **`eventfd(2)`** — the reverse direction: a waitable counter fd for *other* threads or
  subsystems to wake the loop; often used alongside signalfd in the same epoll set.
- **`timerfd_create(2)`** — replaces `SIGALRM`-based timers in event loops entirely.

All three share the property that makes them superior to the self-pipe: the "handler" is the
event loop itself, running in normal context, where ordinary (thread-safe) code is legal.

## Safe handler patterns, summarized

1. Do the minimum in the handler: set a `volatile sig_atomic_t` flag, or write a byte /
   `kill()`/`_exit()` — nothing else.
2. Save and restore `errno` if the handler calls anything that can set it.
3. Prefer `sigaction` with explicit flags (no `SA_NODEFER` unless you know why) — see
   [sigaction and signal](./sigaction-signal.md).
4. Block the signals you handle in all threads and consume via `sigwaitinfo` or `signalfd`
   ([sigwait-sigsuspend](./sigwait-sigsuspend.md), [signalfd-pidfd](./signalfd-pidfd.md)) —
   then no async-signal-safety constraints apply to your logic at all.
5. If you must leave a handler early, `siglongjmp(3)` is safe per POSIX.1-2008 (with the
   caveat in signal-safety(7) that jumping out and then calling unsafe functions is undefined
   if the interruption happened inside one), and you own restoring the signal mask.

## Related Topics

- [sigaction and signal](./sigaction-signal.md) — installing the handler and its mask
- [Signal masks](./signal-masks.md) and [Sigwait and sigsuspend](./sigwait-sigsuspend.md) — deferral and consumption
- [signalfd and pidfd](./signalfd-pidfd.md) — the fd-based modernization
- [Signals overview](../../sysprog/signals.md) — survey-level coverage including the self-pipe trick
- [Per-syscall pages: signals and time](../../syscalls/signals-time/overview.md)

## References

- *signal-safety(7) — async-signal-safe functions*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man7/signal-safety.7.html>
- *signal(7)*, <https://man7.org/linux/man-pages/man7/signal.7.html> (handler execution steps, interruption rules)
- *signalfd(2)*, <https://man7.org/linux/man-pages/man2/signalfd.2.html>; *eventfd(2)*, <https://man7.org/linux/man-pages/man2/eventfd.2.html>
- *POSIX.1-2017*, <https://pubs.opengroup.org/onlinepubs/9699919799/> (XSH 2.4.3 Signal Actions; C11 §7.14.1.1 via ISO/IEC 9899:2011)
