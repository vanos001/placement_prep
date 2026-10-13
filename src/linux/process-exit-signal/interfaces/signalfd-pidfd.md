# signalfd(2) and pidfd_send_signal(2) — FD-Based Signals (IF-011, IF-012)

Two modern Linux extensions reshape the signal model: `signalfd(2)` turns *receiving* signals
into reading a file descriptor (so signals join `epoll`/`poll`/`select` event loops), and
`pidfd_send_signal(2)` turns *sending* signals into an operation on a stable file-descriptor
handle, eliminating the PID-recycling race. This chapter covers application-level use; the
per-syscall pages [signalfd(2)](../../syscalls/net-ipc/signalfd.md) and
[pidfd_send_signal(2)](../../syscalls/process/pidfd_send_signal.md) document syscall numbers
and entry points.

## signalfd(2) / signalfd4(2) (IF-011)

```c
#include <sys/signalfd.h>
int signalfd(int fd, const sigset_t *mask, int flags);
/* flags: SFD_CLOEXEC | SFD_NONBLOCK (Linux >= 2.6.27; zero on <= 2.6.26) */
```

**Category**: libc wrapper around the `signalfd4(2)` syscall (glibc ≥ 2.9 uses `signalfd4`
when available; plain `signalfd(2)` — no `flags` — is the 2.6.22 original and has a hidden
`sizemask` argument the wrapper fills). Linux-only; kernel ≥ 2.6.22, glibc ≥ 2.8 (per
[signalfd(2)](https://man7.org/linux/man-pages/man2/signalfd.2.html); signalfd4 ≥ 2.6.27).

Calling with `fd == -1` creates a new descriptor bound to `mask`; calling with an existing
signalfd replaces its mask (a cheap way to change the subscription). Errors: `EBADF`,
`EINVAL`, `EMFILE`/`ENFILE`, `ENOMEM`, `ENODEV`.

### The must-block-before-read rule

Per signalfd(2): the signals you want via the fd **should normally be blocked**
(`sigprocmask(2)`/`pthread_sigmask(3)`) first — otherwise a signal generated before (or while)
you read it can be *delivered normally* (killing the process under default disposition, or
running a handler) instead of appearing on the fd. This is the single most common signalfd
bug. `SIGKILL`/`SIGSTOP` cannot be received via signalfd and are silently ignored in `mask`.

### read(2) format and consumption

Each pending signal yields one 128-byte `struct signalfd_siginfo`:

```c
struct signalfd_siginfo {
    uint32_t ssi_signo;    /* signal number */
    int32_t  ssi_errno;    /* unused */
    int32_t  ssi_code;     /* like siginfo_t.si_code (SI_USER, SI_QUEUE, ...) */
    uint32_t ssi_pid;      /* sender PID */
    uint32_t ssi_uid;      /* sender real UID */
    int32_t  ssi_fd;       /* SIGIO */
    uint32_t ssi_tid;      /* POSIX timer id */
    uint32_t ssi_band;     /* SIGIO band events */
    uint32_t ssi_overrun;  /* POSIX timer overrun */
    uint32_t ssi_trapno;
    int32_t  ssi_status;   /* SIGCHLD exit status/signal */
    int32_t  ssi_int;      /* sigqueue() int payload */
    uint64_t ssi_ptr;      /* sigqueue() pointer payload */
    uint64_t ssi_utime, ssi_stime;      /* SIGCHLD cpu times */
    uint64_t ssi_addr;                  /* fault address */
    uint16_t ssi_addr_lsb;              /* SIGBUS MCE lsb (>= 2.6.37) */
    uint8_t  pad[...];                  /* padded to 128 bytes */
};
```

Valid fields are determined by `ssi_code` — the same contract as `siginfo_t` (see
[sigaction and signal](./sigaction-signal.md)). `read(2)` returns as many structures as are
pending and fit in the buffer (buffer must be at least 128 bytes), and **consumes** the
signals: they are no longer pending for handlers or `sigwaitinfo(2)`. If nothing is pending,
`read(2)` blocks (or fails `EAGAIN` on a nonblocking fd). Historical note (signalfd(2) BUGS):
before Linux 2.6.25, `ssi_ptr` and `ssi_int` were not filled in for `sigqueue(3)`-sent
signals.

### epoll integration and fork/exec/thread semantics

- The fd is readable (`POLLIN`/`EPOLLIN`) when a subscribed signal is pending — so signals
  become first-class citizens of a `epoll_wait(2)` loop, which is the entire point (per
  signalfd(2); see also [epoll_ctl](../../syscalls/net-ipc/epoll_ctl.md)).
- **fork(2)**: the child inherits a copy of the fd, and reads in the child return *signals
  queued to the child*. **execve(2)**: the fd survives exec (unless `SFD_CLOEXEC`) and
  pre-exec pending signals remain readable — mirroring pending-signal semantics (per
  signalfd(2)).
- **Threads**: a thread reading the fd gets signals directed to *itself* and to the *process*;
  never another thread's directed signals (per signalfd(2)).
- **epoll after fork(2)**: `epoll_wait(2)` reports readiness only for signals sent to the
  registering process; a forked child reading its inherited fd will not see its parent's
  epoll instance wake. The documented workaround is for the child to close the inherited fd
  and create its own signalfd after `fork(2)` (per signalfd(2) "epoll(7) semantics").

Minimal event-loop skeleton:

```c
/* signalfd-loop.c — handle SIGINT/SIGTERM inside poll(2).
 * Expected: Ctrl+C prints "got SIGINT via signalfd"; kill -TERM exits cleanly.
 */
#include <signal.h>
#include <sys/signalfd.h>
#include <poll.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

int main(void) {
    sigset_t mask;
    sigemptyset(&mask);
    sigaddset(&mask, SIGINT);
    sigaddset(&mask, SIGTERM);
    sigprocmask(SIG_BLOCK, &mask, NULL);          /* 1) block FIRST */

    int sfd = signalfd(-1, &mask, SFD_CLOEXEC);   /* 2) then subscribe */

    for (;;) {
        struct pollfd pfd = { .fd = sfd, .events = POLLIN };
        poll(&pfd, 1, -1);
        struct signalfd_siginfo si;
        ssize_t n = read(sfd, &si, sizeof si);
        if (n != sizeof si) { perror("read"); return 1; }
        printf("got %s via signalfd\n",
               si.ssi_signo == SIGINT ? "SIGINT" : "SIGTERM");
        if (si.ssi_signo == SIGTERM) return 0;    /* graceful shutdown */
    }
}
```

## pidfd_open(2) and pidfd_send_signal(2) (IF-012)

```c
#include <sys/syscall.h>    /* pre-glibc-2.36 form; <sys/pidfd.h> has wrappers */
int syscall(SYS_pidfd_open, pid_t pid, unsigned int flags);
/* flags: PIDFD_NONBLOCK (>= 5.10), PIDFD_THREAD (>= 6.9); glibc >= 2.36 ships
   wrapper functions pidfd_open(3)/pidfd_send_signal(3), declared in <sys/pidfd.h>. */
```

```c
#include <linux/signal.h>   /* SIG* constants; SI_* from <signal.h> */
int syscall(SYS_pidfd_send_signal, int pidfd, int sig,
            siginfo_t *_Nullable info, unsigned int flags);
```

**Category**: raw syscalls. The man page (man-pages 6.19) documents no glibc wrapper for
`pidfd_send_signal(2)`, but glibc ≥ 2.36 does provide `pidfd_open(3)` and
`pidfd_send_signal(3)` (glibc NEWS, "Version 2.36"; declared in `<sys/pidfd.h>`), so current
glibc users need not call `syscall(2)` directly. `pidfd_send_signal` needs kernel ≥
5.1; `pidfd_open` ≥ 5.3 (per
[pidfd_open(2)](https://man7.org/linux/man-pages/man2/pidfd_open.2.html) and
[pidfd_send_signal(2)](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html); see
also [pidfd_open(2) page](../../syscalls/process/pidfd_open.md)).

A *pidfd* is a file descriptor that stably refers to one process (or, with `PIDFD_THREAD`,
one thread). Sources: `pidfd_open(2)`, `open("/proc/<pid>", O_RDONLY)`, `clone3(2)` with
`CLONE_PIDFD`, and `pidfd_getfd(2)`-style fd passing (per pidfd_send_signal NOTES). A pidfd is
pollable: when the target becomes a zombie the fd is readable (`EPOLLIN`), and after reaping
it hangs up (`EPOLLHUP`) — per pidfd_open NOTES — which is how modern supervisors wait
without `SIGCHLD` races.

**Why it beats `kill(2)`** (per pidfd_send_signal NOTES): PIDs are recycled. With
`kill(pid, sig)` the intended target may exit and a *different* process may receive the
signal. A pidfd is a stable reference: once the target terminates, `pidfd_send_signal` fails
with `ESRCH` instead of hitting an unrelated process. (One caveat from pidfd_open NOTES: a
zombie must still exist when you call `pidfd_open` — it is only guaranteed to refer to the
zombie if `SIGCHLD` has not been set to `SIG_IGN`, `SA_NOCLDWAIT` is not set, and nobody
reaped it; otherwise create the child with `clone(CLONE_PIDFD)`.)

### PIDFD_SIGNAL constants (Linux ≥ 6.9)

The `flags` argument of `pidfd_send_signal(2)` scopes the signal (per pidfd_send_signal(2)):

| Flag | Effect |
|------|--------|
| `0` (default) | scope inferred from the pidfd: thread-pidfd → that thread; process pidfd → the thread group |
| `PIDFD_SIGNAL_THREAD` | force delivery to the specific thread the pidfd refers to |
| `PIDFD_SIGNAL_THREAD_GROUP` | if the pidfd refers to a thread-group leader, signal the whole group even if the pidfd was created thread-scoped |
| `PIDFD_SIGNAL_PROCESS_GROUP` | if the pidfd refers to a process-group leader, signal the process group |

`pidfd_open(2)`'s `flags` are the analogous producer-side constants: `PIDFD_NONBLOCK` (5.10)
and `PIDFD_THREAD` (6.9) for thread-scoped pidfds — the pair (thread pidfd +
`pidfd_send_signal`) is the race-free replacement for `tkill(2)` (per pidfd_open(2)).

With `info == NULL`, delivery is exactly as if `kill(2)` had sent it (`si_code = SI_USER`,
sender pid/uid filled). A caller-supplied `info` follows the `rt_sigqueueinfo(2)` rules:
`si_code` must be `< 0` for any target other than the caller, else `EPERM` (per
pidfd_send_signal(2) and [rt_sigqueueinfo(2)](https://man7.org/linux/man-pages/man2/rt_sigqueueinfo.2.html)).
The caller must be in the target's PID namespace or an ancestor.

Errors: `EBADF` (not a pidfd), `EINVAL` (bad sig/flags/namespace), `EPERM` (permissions or
bogus `si_code`), `ESRCH` (target gone and reaped) (per pidfd_send_signal(2)).

Minimal race-free signaling:

```c
/* pidfd-kill.c — signal a child race-free.
 * Expected: ./pidfd-kill <pid> 15 => child dies by SIGTERM; if <pid> already
 * exited, ESRCH rather than signaling an unlucky recycled PID.
 */
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(int argc, char **argv) {
    char path[64];
    snprintf(path, sizeof path, "/proc/%s", argv[1]);
    int pidfd = open(path, O_RDONLY | O_CLOEXEC);   /* simplest pidfd source */
    if (pidfd < 0) { perror("open /proc"); return 1; }

    int rc = syscall(SYS_pidfd_send_signal,
                     pidfd, atoi(argv[2]), NULL, 0);
    if (rc) { perror("pidfd_send_signal"); return 1; }
    return 0;
}
```

## When to use which

- **Event loops** (one process, many event sources): `signalfd` + `epoll` — signals become
  ordinary readiness events; no handler restrictions apply on the read path.
- **Supervising other processes** (containers, shells, supervisors): `pidfd_send_signal` —
  immune to PID recycling; pollable lifecycle; thread- or group-scoped delivery since 6.9.
- Plain `kill(2)`/`raise(3)` remain correct for self-signaling and privileged tools — see
  [kill-raise](./kill-raise.md).

## Related Topics

- [kill, raise, and the kill utility](./kill-raise.md) — the classic sending path
- [tgkill](./tgkill.md) — thread-directed sending, pre-pidfd
- [Sigwait and sigsuspend](./sigwait-sigsuspend.md) — the other synchronous consumption style
- [Async-signal safety](./async-signal-safety.md) — signalfd vs self-pipe for handlers
- Per-syscall pages: [signalfd(2)](../../syscalls/net-ipc/signalfd.md), [pidfd_send_signal(2)](../../syscalls/process/pidfd_send_signal.md), [pidfd_open(2)](../../syscalls/process/pidfd_open.md), [eventfd(2)](../../syscalls/net-ipc/eventfd.md)

## References

- *signalfd(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/signalfd.2.html>
- *pidfd_send_signal(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html>
- *pidfd_open(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/pidfd_open.2.html>
- *rt_sigqueueinfo(2)*, <https://man7.org/linux/man-pages/man2/rt_sigqueueinfo.2.html> (siginfo rules reused by pidfd_send_signal)
- *signal(7)*, <https://man7.org/linux/man-pages/man7/signal.7.html>
