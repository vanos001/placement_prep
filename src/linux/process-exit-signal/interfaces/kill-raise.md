# kill(2), raise(3), and the kill utility (IF-001, IF-002)

Sending a signal has four distinct front doors: the `kill(2)` system call (process or process
group), `raise(3)` (self, thread-aware), `pthread_kill(3)` (self or same-process thread — see
[tgkill](./tgkill.md)), and two *command-line* layers, the shell `kill` **builtin** and the
external `/bin/kill` **utility**. They differ in semantics, portability, and who gets signaled.

## kill(2) — the primitive (IF-001)

```c
#include <signal.h>            /* feature test: _POSIX_C_SOURCE */
int kill(pid_t pid, int sig);
```

**Category**: libc wrapper that is a 1:1 pass-through to the `kill(2)` system call — the libc
function and the syscall have the same name and contract (per
[kill(2)](https://man7.org/linux/man-pages/man2/kill.2.html)). Kernel entry since Linux 1.0;
x86-64 number 62 (see the per-syscall page
[kill(2)](../../syscalls/signals-time/kill.md)).

The `pid` argument selects the target set (per kill(2)):

| `pid` | Target |
|-------|--------|
| `> 0` | The process with that PID. |
| `0`   | Every process in the *caller's* process group. |
| `-1`  | Every process the caller has permission to signal, **except init (PID 1)**; on Linux the caller itself is excluded. |
| `< -1` | Every process in process group `−pid`. |

`sig = 0` sends nothing but still performs existence and permission checks — the canonical
liveness probe (`ESRCH` means no such process, `EPERM` means it exists but you may not signal
it) (per kill(2)).

**Permission rules** (per kill(2)): the sender needs `CAP_KILL` in the target's user namespace,
or its real *or* effective UID must equal the target's real *or saved set-* UID; for `SIGCONT`
it suffices that sender and receiver share a session. Unprivileged processes therefore cannot
signal setuid binaries of other users — root (or `CAP_KILL`) can signal anything. Only signals
that init has installed handlers for can be sent to PID 1. The POSIX-conforming rule was
adopted in Linux 1.3.78; earlier kernels used variants (history in kill(2)).

**Return value and errors**: `0` on success (for a group target, "success" means at least one
signal was sent); `-1` with `EINVAL` (invalid signal), `EPERM` (no permission for *any*
target), or `ESRCH` (no such process/group; note an existing zombie still counts as existing
until waited) (per kill(2)).

**Async-signal safety**: `kill(2)` is on the POSIX async-signal-safe list (per
[signal-safety(7)](https://man7.org/linux/man-pages/man7/signal-safety.7.html)), so it is one
of the few "rich" actions a signal handler may legitimately perform (the classic example:
handler sends itself `SIGTERM`'s next stage or awakens a helper).

POSIX self-signal guarantee: if a process signals itself and the sending thread does not block
the signal and no other thread would handle it, at least one unblocked signal must be
delivered to the sending thread before `kill()` returns (per kill(2) NOTES).

### kill(1): utility vs builtin

POSIX defines `kill` as a **shell utility** with synopsis `kill -s signal_name pid...`,
`kill -l [exit_status]`, and (XSI) the compact forms `kill -signal_name pid...` and
`kill -signal_number pid...` (per
[POSIX kill(1posix)](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/kill.html)).
It performs "actions equivalent to the `kill()` function" — including the job-control job-ID
form (`kill -TERM %1`) when invoked in the shell's own execution environment.

Every POSIX shell additionally implements `kill` as a **builtin** (bash, dash, zsh per their
manuals), so `kill` usually does *not* exec anything in scripts. Two consequences:

1. Job specs (`%1`) work in builtins; the external `/bin/kill` cannot see shell job tables.
2. When the PATH must be forced (`env kill` / `/bin/kill`), behavior differences become
   visible — see below.

The external program itself comes in two flavors on Linux distros:

- **procps-ng `/bin/kill`** (bookworm: `kill [options] <pid>...`): options `-s, --signal`,
  `-q, --queue` (RT signal with `sigqueue`), `-l, --list`, `-L, --table` (per `kill(1)` as
  shipped by procps-ng).
- **GNU coreutils `kill`** (`/usr/bin/kill`): usage `kill [-s SIGNAL | -SIGNAL] PID...`,
  `kill -l [SIGNAL]...`, `kill -t [SIGNAL]...` (per
  [`src/kill.c`](https://github.com/coreutils/coreutils/blob/master/src/kill.c) in the coreutils
  source). Its source handles `-n` with the comment "not documented, but is for Bash
  compatibility".

The **bash builtin** documents the superset form (per `bash(1)`):

```text
kill [-s sigspec | -n signum | -sigspec] [pid | jobspec] ...
kill -l|-L [sigspec | exit_status]
```

i.e. `-s NAME` (case-insensitive, with or without `SIG` prefix), `-n NUMBER`, the bare
`-NUMBER`/`-NAME` forms, and `-l`/`-L` listing; it returns true if at least one signal was
sent. **`-n` is a bash/coreutils extension, not POSIX** — POSIX `kill` has `-s` and the XSI
compact forms only. Note also the POSIX parsing subtlety: if the first operand is a negative
integer it is interpreted as a `-signal_number` option, not as a negative PID — negative PIDs
should be preceded by `--` (per POSIX kill utility).

## raise(3) — self-directed signaling (IF-002)

```c
#include <signal.h>
int raise(int sig);
```

**Category**: libc function, specified by C11 (7.14.2.1) and POSIX.1-2008 (per
[raise(3)](https://man7.org/linux/man-pages/man3/raise.3.html)). It is *not* a syscall; there
is no `raise` syscall on Linux.

**Underlying syscall (verified, glibc)**: per raise(3) HISTORY, since glibc 2.3.3 `raise()` is
implemented by calling **`tgkill(2)`**; older glibc used `kill(2)`. In glibc source
(`sysdeps/posix/raise.c`), `raise(sig)` is exactly `__pthread_kill(__pthread_self(), sig)`,
and `pthread_kill` for the calling thread issues `tgkill(getpid(), gettid(), sig)` — see
[tgkill](./tgkill.md). **This is why `raise()` is thread-directed**: in a multithreaded
program it is equivalent to `pthread_kill(pthread_self(), sig)`, whereas in a single-threaded
program it is equivalent to `kill(getpid(), sig)` (per raise(3)).

Consequences of the thread-directed implementation:

- The signal's *thread-directed* pending instance lands on the caller only; other threads never
  see it (unless it is process-directed by nature — kernel-generated — in which case it is
  process-directed regardless of who raised it).
- If the signal is blocked in the calling thread it stays pending *there* — precisely like any
  other thread-directed signal.
- If it is unblocked, glibc's `pthread_kill` self-path performs the `tgkill` with no signal
  blocking, so delivery (handler run) happens before `raise()` returns — matching the POSIX
  requirement quoted above for `kill()` (see glibc `nptl/pthread_kill.c` comment and raise(3)).

**Return value**: `0` on success, nonzero on failure — *not* `-1`+`errno` (raise(3)); glibc
maps the underlying error into the return and sets `errno`. **Thread safety**: MT-Safe (per
raise(3) ATTRIBUTES). `raise()` is also on the async-signal-safe list (signal-safety(7)) — it
is the correct way for a handler to re-raise a fatal signal after restoring its disposition.

C11 vs POSIX nuance: C11 only specifies `raise` as sending the signal *to the program*; the
"equivalent to `pthread_kill(pthread_self(),…)` in threads" wording is POSIX.1-2008/libc
behavior (per raise(3)).

## Minimal examples

```c
/* kill-liveness.c — check a PID and send SIGTERM.
 * cc kill-liveness.c -o kill-liveness && ./kill-liveness <pid>
 */
#include <signal.h>
#include <stdio.h>
#include <errno.h>

int main(int argc, char **argv) {
    pid_t pid = (pid_t)atoi(argv[1]);
    if (kill(pid, 0) == -1) {           /* existence + permission probe */
        perror("kill(pid, 0)");         /* ESRCH: gone; EPERM: not ours */
        return 1;
    }
    if (kill(pid, SIGTERM) == -1) {
        perror("kill(pid, SIGTERM)");
        return 1;
    }
    puts("SIGTERM sent");
    return 0;
}
```

```c
/* raise-self.c — SIGUSR1 is thread-directed to the raiser.
 * Expected output: "handler in thread (tid differs per run)" then "returned".
 */
#define _GNU_SOURCE
#include <signal.h>
#include <pthread.h>
#include <stdio.h>

static void handler(int sig) {
    printf("handler got %d in tid %ld\n", sig, gettid());
}

int main(void) {
    struct sigaction sa = { .sa_handler = handler };
    sigaction(SIGUSR1, &sa, NULL);
    raise(SIGUSR1);                      /* handler runs before raise returns */
    puts("returned");
    return 0;
}
```

```console
$ kill -l                 # shell builtin: list signals
$ kill -USR1 4242         # compact -sigspec form (POSIX XSI)
$ kill -n 15 4242         # -n: bash/coreutils extension
$ /bin/kill -s TERM -- -12345   # external utility, negative PGID after --
```

## Practical notes

- Prefer `kill(pid, 0)` over reading `/proc/<pid>` for liveness of processes you own — it
  encodes the permission model.
- In multithreaded code, decide deliberately between `raise()`/`pthread_kill` (thread-directed)
  and `kill(getpid(), …)` (process-directed, delivered to an arbitrary unblocked thread).
- For race-free signaling of a child you spawned, prefer `pidfd_send_signal(2)` —
  [signalfd and pidfd](./signalfd-pidfd.md) — because a plain PID can be recycled.

## Related Topics

- [tgkill and pthread_kill](./tgkill.md) — the thread-directed primitive beneath `raise()`
- [sigaction and signal](./sigaction-signal.md) — install the dispositions these signals hit
- [Standard signals](../signals/standard-signals.md) — what each signal means
- [kill(2) per-syscall page](../../syscalls/signals-time/kill.md)
- [pidfd_send_signal(2) per-syscall page](../../syscalls/process/pidfd_send_signal.md)
- [Exit status conventions](../../process-exit-signal-coverage.md) — shell reporting of signal deaths

## References

- *kill(2)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man2/kill.2.html>
- *raise(3)*, Linux man-pages 6.19, <https://man7.org/linux/man-pages/man3/raise.3.html>
- *kill — terminate or signal processes*, POSIX.1-2017 Shell & Utilities, <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/kill.html>
- *procps-ng kill(1)* (Debian bookworm package), <https://manpages.debian.org/bookworm/procps/kill.1.en.html>
- *coreutils `src/kill.c`* (usage and `-n` handling), <https://github.com/coreutils/coreutils/blob/master/src/kill.c>
- *bash(1)*, `kill` builtin (verified against Debian bash package man page), <https://manpages.debian.org/bookworm/bash/bash.1.en.html>; upstream manual <https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html>
- *glibc source*, `sysdeps/posix/raise.c`, `nptl/pthread_kill.c` (verified via the bminor read-only mirror of sourceware git), <https://github.com/bminor/glibc/blob/master/sysdeps/posix/raise.c>
- *signal-safety(7)*, <https://man7.org/linux/man-pages/man7/signal-safety.7.html>
