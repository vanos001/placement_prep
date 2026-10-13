# C: Process Termination, Exit Status, and Signals

This chapter covers how C programs terminate normally and abnormally, how exit
statuses are produced and represented on Linux, and how C programs register,
mask, and handle signals. It also covers the POSIX process-creation and
wait-family APIs as they are used from C on Linux. The baseline references are
the ISO C11 standard draft **N1570** (sections cited as `§5.1.2.2.3`,
`§7.14.1.1`, `§7.22.4.x`), **POSIX.1-2017** (IEEE Std 1003.1-2017), the Linux
**man-pages** (man 2 / man 3 / man 7), and the **glibc** behavior described by
those man pages. C23 changes are included only where they could be verified
against the cppreference C23-dated pages (cppreference is a community mirror of
the standard text, not the standard itself; standard wording here is quoted
from N1570 directly).

Scoping statement: this chapter separates four layers that are frequently
conflated — what **ISO C** guarantees, what **POSIX** adds, what **glibc**
implements, and what the **Linux kernel** ultimately does. Each claim below is
attributed to a layer.

---

## 1. Syntax and Semantics

### 1.1 `main` and returning from it

ISO C requires `main` to be declared as `int main(void)` or
`int main(int argc, char *argv[])` (or equivalent; N1570 §5.1.2.2.1). The
return type must be `int`. The critical termination rule is N1570 §5.1.2.2.3
*Program termination*:

> If the return type of the main function is a type compatible with int, a
> return from the initial call to the main function is equivalent to calling
> the exit function with the value returned by the main function as its
> argument; reaching the `}` that terminates the main function returns a value
> of 0. If the return type is not compatible with int, the termination status
> returned to the host environment is unspecified.

Two points matter for exit-status work. First, falling off the end of `main`
is **not** an undefined or unspecified status — it is defined to return 0.
Second, the footnote to §5.1.2.2.3 notes that when `main` returns normally,
the lifetimes of objects with automatic storage duration declared in `main`
have ended *before* `exit` runs — automatic objects are destroyed by returning
from `main`, not by `exit` itself. This distinction is invisible in C (which
has no destructors) but becomes visible in C++ (see [cpp.md](./cpp.md)).

```c
#include <stdlib.h>

int main(int argc, char *argv[]) {
    if (argc < 2)
        return 1;              /* equivalent to exit(1) */
    /* falling off the end returns 0 */
}
```

A POSIX implementation invokes the program through the C runtime (`crt1.o` in
glibc's case), which calls `main` and passes its return value to `exit(3)`.

### 1.2 The termination functions

Canonical signatures (N1570 §7.22.4; C23 `[[noreturn]]` spelling verified via
cppreference):

```c
#include <stdlib.h>

void            exit(int status);          /* until C11 */
_Noreturn void  exit(int status);          /* C11 .. C17 */
[[noreturn]] void exit(int status);        /* C23 */

_Noreturn void  _Exit(int status);         /* C99 (spelled [[noreturn]] in C23) */
_Noreturn void  quick_exit(int status);    /* C11 */
_Noreturn void  abort(void);               /* C23: [[noreturn]] void abort(void); */

int  atexit(void (*func)(void));           /* C89 */
int  at_quick_exit(void (*func)(void));    /* C11 */
```

The execution model of each (all wording from N1570):

- **`exit(status)`** (§7.22.4.4) causes *normal* program termination. First,
  all functions registered by `atexit` are called in reverse order of
  registration (with the documented interleaving rule relative to
  static-object lifetime; §7.22.4.4¶3). Next, *all open streams with unwritten
  buffered data are flushed, all open streams are closed, and all files
  created by `tmpfile` are removed* (¶4). Finally, control returns to the host
  environment: `0` or `EXIT_SUCCESS` → implementation-defined successful
  status; `EXIT_FAILURE` → implementation-defined unsuccessful status;
  anything else is implementation-defined (¶5). Handlers registered with
  `at_quick_exit` are **not** called. Calling `exit` more than once, or
  calling `quick_exit` in addition to `exit`, is undefined behavior (¶2).
- **`_Exit(status)`** (§7.22.4.5) causes *normal* termination but calls no
  `atexit` handlers, no `at_quick_exit` handlers, and no signal handlers.
  Whether streams are flushed or closed is *implementation-defined*. On
  Linux/glibc this maps directly onto the process-termination path (see
  §3.2).
- **`quick_exit(status)`** (§7.22.4.7) runs only the `at_quick_exit`
  handlers, in reverse order, then calls `_Exit(status)`. It runs no `atexit`
  handlers and no signal handlers, and *if a signal is raised while
  `quick_exit` is executing, the behavior is undefined* (¶2).
- **`abort()`** (§7.22.4.1) causes *abnormal* termination by raising
  `SIGABRT` — "unless the signal SIGABRT is being caught and the signal
  handler does not return". Whether open streams are flushed, closed, or
  temporary files removed is *implementation-defined*. The implementation
  returns an implementation-defined *unsuccessful* status to the host.
- **`atexit(func)`** (§7.22.4.2) / **`at_quick_exit(func)`** (§7.22.4.3)
  register handlers for the two independent lists; the lists are distinct
  (footnote 297 explicitly says applications may need to register the same
  function with both). Implementations must support at least 32 entries each.
  Both return 0 on success, nonzero on failure.

```c
#include <stdio.h>
#include <stdlib.h>

static void on_normal(void)  { puts("atexit: normal path");  }
static void on_quick(void)   { puts("at_quick_exit: quick path"); }

int main(void) {
    atexit(on_normal);        /* runs for exit / return-from-main */
    at_quick_exit(on_quick);  /* runs only for quick_exit */
    quick_exit(0);
}
/* Output: at_quick_exit: quick path      (exit status 0)
   on_normal is never called. */
```

### 1.3 Exit-status representation and truncation

ISO C models the status as an `int` handed to the *host environment*; it does
not define the bit format. POSIX and Linux define it precisely:

- `exit(3)` / `_exit(2)`: the value `status & 0xFF` becomes the process exit
  status collected by the parent (man 2 `_exit`). Only the low 8 bits
  survive; `exit(256)` looks like `exit(0)` and `exit(-1)` looks like
  `exit(255)`.
- The parent reads a 16-bit *wait status* integer and decodes it with macros
  (§3.3, §5.4).
- The Linux kernel's exit path is `exit_group(2)` (all threads) or `exit(2)`
  (single thread); the status travels through the wait state to the parent
  (see [../../syscalls/process/_exit.md](../../syscalls/process/_exit.md)).

Portable programs should restrict statuses to `0–255`, and treat `0` as
success; POSIX `sh`-family consumers map other statuses by convention
([../exit-status/conventions.md](../exit-status/conventions.md)).

### 1.4 Normal vs. exceptional termination, and cleanup ordering

The paths and their cleanup guarantees:

| Path | `atexit` handlers | `at_quick_exit` handlers | stdio flush | Streams closed | Mechanism on Linux |
|---|---|---|---|---|---|
| return from `main` | yes | no | yes | yes | return → `exit()` |
| `exit(status)` | yes | no | yes | yes | glibc exit → `_exit`/`exit_group` |
| `quick_exit(status)` | no | yes (reverse) | no (`_Exit` semantics) | implementation-defined | `at_quick_exit` list → `_Exit` |
| `_Exit(status)` / `_exit(status)` | no | no | no | implementation-defined | `exit_group(2)` syscall (glibc ≥ 2.3) |
| `abort()` | no | no | implementation-defined | implementation-defined | `raise(SIGABRT)` → `SIGABRT` → core dump possible |
| Signal death (uncatched) | no | no | no | no | kernel kills the process |

Notes verified from the sources:

- glibc's `exit(3)` runs `atexit(3)` *and* `on_exit(3)` handlers in reverse
  registration order; if such a handler calls `_exit(3)` or kills itself with
  a signal, "none of the remaining functions is called, and further exit
  processing (in particular, flushing of stdio(3) streams) is abandoned"
  (man 3 `exit`). Calling `exit` or `longjmp` out of a registered handler is
  undefined behavior (man 3 `exit`; N1570 §7.22.4.4¶3).
- A call to `execve(2)` discards `atexit` registrations (man 3 `exit`, NOTES).
- glibc `abort(3)` unblocks `SIGABRT`, raises it, and if it returns (handler
  swallowed it) re-raises with the default disposition restored, so `abort`
  cannot return and normally produces a core dump (man 3 `abort`; kernel
  `do_coredump` decides whether a core file is written —
  [../exit-status/lifecycle.md](../exit-status/lifecycle.md)).

### 1.5 Undefined and implementation-defined behavior relevant to exit/signals

- **Dereferencing an invalid pointer is not "a SIGSEGV" in the C standard.**
  It is undefined behavior; the kernel's SIGSEGV delivery is the *typical
  implementation consequence* on Linux, but the standard grants no meaning to
  it. The same applies to SIGFPE (integer divide by zero) and SIGILL.
- **Returning from a handler for SIGFPE/SIGILL/SIGSEGV** is undefined behavior
  (N1570 §7.14.1.1¶3); returning from a handler for "any other
  implementation-defined value corresponding to a computational exception" is
  also UB.
- **Calling `exit` from a signal handler is not async-signal-safe.** Only
  `abort`, `_Exit`, `quick_exit`, and `signal(sig, …)` (for the same `sig`)
  may be called from a handler under C11 rules (§7.14.1.1¶5). Note that
  `exit` is *not* in that list — the flush and atexit machinery is not
  reentrant. `_Exit` is allowed because it does no cleanup.
- **Handler restrictions** (§7.14.1.1¶5): if the signal occurred other than as
  a result of `abort`/`raise`, the behavior is undefined if the handler
  *refers to any object with static or thread storage duration* that is not a
  lock-free atomic object, other than by assigning to an object declared as
  `volatile sig_atomic_t`. The safest portable idiom is exactly that:

```c
#include <signal.h>
#include <stdlib.h>

static volatile sig_atomic_t got_signal = 0;

static void handler(int sig) {      /* async-signal-safe */
    got_signal = sig;               /* allowed: volatile sig_atomic_t store */
}

int main(void) {
    if (signal(SIGINT, handler) == SIG_ERR)
        return 1;
    while (!got_signal)
        ;                           /* spin; real code uses sigsuspend/sigwait */
    _Exit(got_signal + 128);        /* allowed in a handler; convention only */
}
```

- **`signal()` in a multithreaded program is UB** under C11 (§7.14.1.1, listed
  in Annex J); use POSIX `sigaction(2)` and `pthread_sigmask(3)` instead.
- Whether **SIG_IGN is installed for some signals at startup** is
  implementation-defined (§7.14.1.1¶6).
- **C23**: the only change verified for this chapter is the migration of the
  `_Noreturn` function specifier to the standard `[[noreturn]]` attribute in
  the program-termination signatures (cppreference, C23 column). Beyond that,
  no exit/signal semantic changes are claimed here.

### 1.6 Common misconceptions

- *"`return` and `exit` are the same."* From `main`, equivalent status-wise
  (§5.1.2.2.3); from any other function, `return` does not terminate anything.
- *"`exit` is like `_exit`."* `exit` runs atexit handlers and flushes stdio;
  `_Exit`/`_exit` guarantee neither.
- *"`abort` is a reliable way to exit with a status."* `abort` produces an
  implementation-defined unsuccessful status, may core-dump, and its SIGABRT
  handler semantics make the result observer-dependent.
- *"Handlers can call printf."* No — not async-signal-safe (see
  [../interfaces/async-signal-safety.md](../interfaces/async-signal-safety.md)).

---

## 2. Standard-Library and Runtime API Inventory

Signatures below are verified against N1570 for ISO C functions and against
POSIX.1-2017/man-pages for POSIX functions. "Threading" notes describe
POSIX-specified behavior on Linux/glibc.

### 2.1 Termination and registration (ISO C, `<stdlib.h>`)

**`exit`** — `_Noreturn void exit(int status);` (§7.22.4.4)
Runs atexit handlers in reverse registration order, flushes and closes all
open streams, removes `tmpfile` files, returns `status` to the host (0xFF
truncation on Linux). Not callable from a signal handler. On Linux the
underlying kernel work is `exit_group(2)` (glibc ≥ 2.3, man 2 `_exit`).
Reference: N1570 §7.22.4.4; man 3 exit.

**`_Exit`** — `_Noreturn void _Exit(int status);` (§7.22.4.5)
Normal termination classification, but no handler lists run and flushing is
implementation-defined. glibc implements it over `_exit(2)`.

**`quick_exit`** — `_Noreturn void quick_exit(int status);` (§7.22.4.7)
Runs only `at_quick_exit` handlers (reverse order), then `_Exit(status)`. UB
if a signal arrives during its execution. Useful as a "no-destructor
teardown" path for multi-runtime programs (e.g. libraries that must not run
global cleanup registered by others).

**`abort`** — `_Noreturn void abort(void);` (§7.22.4.1)
Raises `SIGABRT`; abnormal termination unless a handler catches it and does
not return. Flush/close are implementation-defined (in practice not flushed).
Produces the standard crash path with possible core dump.

**`atexit`** — `int atexit(void (*func)(void));` (§7.22.4.2)
Registers a normal-termination handler. ≥32 registrations guaranteed. Not
thread-safe relative to process death — a concurrent `exit` and `atexit` is a
race.

**`at_quick_exit`** — `int at_quick_exit(void (*func)(void));` (§7.22.4.3)
Same contract for the `quick_exit` list.

### 2.2 Signals (ISO C `<signal.h>`, POSIX extensions)

**`signal`** — `void (*signal(int sig, void (*func)(int)))(int);` (§7.14.1.1)
Installs `SIG_DFL`, `SIG_IGN`, or a handler. After a handler runs, whether
the implementation re-installs `SIG_DFL` or blocks a set of signals during
handling is implementation-defined (§7.14.1.1¶2) — the classic
SysV-vs-BSD portability hazard, which POSIX.1-2017 does **not** remove: its
`signal` page defers to ISO C and says only that "the `sigaction()` function
provides a more comprehensive and reliable mechanism for controlling signals;
new applications should use `sigaction()` rather than `signal()`" (POSIX
`signal`, APPLICATION USAGE). Use `sigaction` explicitly. Returns `SIG_ERR`
on failure with `errno` set.

**`raise`** — `int raise(int sig);` (§7.14.2)
Sends `sig` to the executing program; the handler is invoked synchronously
and `raise` returns after it. Returns 0 on success. In a POSIX process,
glibc implements `raise` as `pthread_kill`/`tgkill` to the calling thread
(man 3 raise).

**POSIX signal interfaces** (`<signal.h>`; POSIX.1-2017):

```c
int sigaction(int sig, const struct sigaction *restrict act,
              struct sigaction *restrict oact);
int sigprocmask(int how, const sigset_t *restrict set, sigset_t *restrict oset);
int sigpending(sigset_t *set);
int sigsuspend(const sigset_t *sigmask);
int sigwait(const sigset_t *restrict set, int *restrict sig);
int pthread_sigmask(int how, const sigset_t *restrict set,
                    sigset_t *restrict oset);
int pthread_kill(pthread_t thread, int sig);
int kill(pid_t pid, int sig);
int sigqueue(pid_t pid, int signo, union sigval value);
```

- `sigaction(2)` per-signal struct `sigaction` (`sa_handler`/`sa_sigaction`,
  `sa_mask`, `sa_flags` including `SA_RESTART`, `SA_SIGINFO`,
  `SA_NOCLDSTOP`, `SA_NOCLDWAIT`, and Linux's `SA_RESTORER` trampoline,
  which is glibc-internal). `sigaction` with `SA_SIGINFO` delivers
  `siginfo_t` and supports queued real-time signals.
- `sigprocmask(2)` changes the thread signal mask — in a multithreaded
  program, POSIX explicitly says its use is unspecified and
  `pthread_sigmask(3)` must be used.
- `sigpending(2)` returns the pending set (process-directed and
  thread-directed signals pending for the caller).
- `sigsuspend(2)` atomically replaces the mask and waits — the race-free way
  to wait for a handler to run.
- `sigwait(3)` consumes one pending signal synchronously; the recommended
  pattern is to block the signal in all threads at startup and dedicate one
  thread to `sigwait` (POSIX `sigwait`; man 3 sigwait).
- `pthread_sigmask(3)` is the per-thread mask interface; `how` ∈
  {`SIG_BLOCK`, `SIG_SETMASK`, `SIG_UNBLOCK`}.
- `pthread_kill(3)` targets one thread. If `sig` is 0, no signal is sent but
  error checking still occurs (man 3 pthread_kill). A process-directed
  signal sent to a thread is process-wide once delivered.
- `kill(2)` sends to a process or process group; `sigqueue(2)` sends a
  queued signal with a `union sigval` payload (real-time semantics).

Deeper interface details live in [../interfaces/sigaction-signal.md](../interfaces/sigaction-signal.md)
and [../interfaces/signal-masks.md](../interfaces/signal-masks.md).

### 2.3 Process creation and waiting (POSIX)

```c
#include <unistd.h>
pid_t fork(void);
extern char **environ;
int execve(const char *path, char *const argv[], char *const envp[]);
int execl(const char *path, const char *arg0, ... /*, (char *)0 */);
int execle(const char *path, const char *arg0, ... /*, (char *)0,
           char *const envp[]*/);
int execlp(const char *file, const char *arg0, ... /*, (char *)0 */);
int execv(const char *path, char *const argv[]);
int execvp(const char *file, char *const argv[]);

#include <sys/wait.h>
pid_t wait(int *stat_loc);
pid_t waitpid(pid_t pid, int *stat_loc, int options);
int   waitid(idtype_t idtype, id_t id, siginfo_t *infop, int options);

#include <spawn.h>
int posix_spawn(pid_t *restrict pid, const char *restrict path,
                const posix_spawn_file_actions_t *file_actions,
                const posix_spawnattr_t *restrict attrp,
                char *const argv[restrict], char *const envp[restrict]);
int posix_spawnp(pid_t *restrict pid, const char *restrict file,
                 const posix_spawn_file_actions_t *file_actions,
                 const posix_spawnattr_t *restrict attrp,
                 char *const argv[restrict], char *const envp[restrict]);
```

- `fork(2)`: duplicates the calling process; the child gets a unique PID and a
  copy of the address space (COW on Linux). The child inherits copies of open
  file descriptors that share the same open file descriptions (shared offsets,
  shared status flags — man 2 fork). The exec-family `l`/`v` suffixes choose
  list vs. array arguments, `e` chooses an explicit environment, `p` enables
  `$PATH` search (`execvp`/`execlp`); `fexecve` opens the executable by fd.
- `wait(2)`/`waitpid(2)` block (or poll with `WNOHANG`) for a child state
  change; `waitid(2)` selects by `idtype_t` and can return `siginfo_t`.
  Options `WUNTRACED`/`WCONTINUED` report stopped/continued children
  (POSIX `wait`; `WCONTINUED` is XSI).
- `posix_spawn(3)` is a combined create-and-exec primitive; glibc implements
  it efficiently (often via `clone(CLONE_VM|CLONE_VFORK)`), and it avoids
  most fork-hazards (see §6).

### 2.4 Shell execution (ISO C + POSIX)

```c
#include <stdlib.h>
int system(const char *command);

#include <stdio.h>
FILE *popen(const char *command, const char *mode);
int   pclose(FILE *stream);
```

`system(3)` runs `/bin/sh -c command` and returns the *wait status* (not a
plain exit code) on POSIX; when `command` is NULL it reports whether a shell
is available. `popen(3)` runs the command with one end of a pipe wired to the
child's stdout (mode `"r"`) or stdin (mode `"w"`). Both interpolate through
the shell — see §5.6 for quoting hazards.

---

## 3. Process Lifecycle and Termination

### 3.1 Creation and the four layers

A Linux C program is: (1) a POSIX process, (2) an ISO C execution environment
inside it, (3) linked against glibc, (4) made of kernel threads. `fork` gives
the child a *copy* of all four; `execve` replaces the C/runtime image but
keeps the process identity, file descriptors, and signal mask, while
dispositions set to `SIG_IGN` are preserved and *caught* dispositions reset
to default; glibc resets stdio state and removes atexit registrations
(man 3 exit, NOTES: "a call to execve(2) removes registrations created using
atexit(3)"). Disposition rules per POSIX `exec`.

### 3.2 Terminating: the layered view of "exit"

1. **ISO C layer**: `exit` = atexit list + stdio flush/close + host status.
2. **POSIX layer**: `_Exit`/`_exit` = immediate termination, no handlers, no
   flush; POSIX adds: descriptors close, children reparent, `SIGCHLD` to
   parent (POSIX `_exit`; man 2 `_exit`).
3. **glibc layer**: the `_exit` wrapper invokes the `exit_group` syscall so
   *all threads* die (man 2 `_exit`, glibc ≥ 2.3).
4. **Kernel layer**: `exit_group(2)` terminates the thread group; the raw
   `exit(2)` syscall terminates one thread only. Reparenting and `SIGCHLD`
   happen when the last thread exits
   ([../../syscalls/process/_exit.md](../../syscalls/process/_exit.md)).

Returning from `main` is `exit(main())` (§5.1.2.2.3), so the full normal path
is: automatic objects end → atexit handlers (reverse) → stdio flush/close →
kernel `exit_group` → status to parent → zombie until `wait`.

`vfork(2)` deserves its warning: the child shares the parent's memory
(including the stack) until it execs or exits, and it "must not ... call any
other function before successfully calling `_exit(3)` or one of the exec(3)
family" — in particular the child must not call `exit(3)`, which would run
the *parent's* handlers and flush the parent's stdio buffers (man 2 vfork).

### 3.3 Exit status as the parent sees it

The parent decodes a 16-bit wait status with macros:

| Macro | Meaning |
|---|---|
| `WIFEXITED(status)` | child exited normally |
| `WEXITSTATUS(status)` | low 8 bits of the child's exit status |
| `WIFSIGNALED(status)` | child was killed by a signal |
| `WTERMSIG(status)` | which signal killed it |
| `WCOREDUMP(status)` | (Linux) a core was dumped |
| `WIFSTOPPED(status)` / `WSTOPSIG(status)` | stopped (needs `WUNTRACED`) |
| `WIFCONTINUED(status)` | continued (needs `WCONTINUED`) |

Normal exit and signal death are *mutually exclusive representations* in the
same integer; a process killed by `SIGKILL` has no exit code, and an
observed `exit code 137` from a shell is the *shell's* `128+15` convention,
not a wait-status field ([../exit-status/lifecycle.md](../exit-status/lifecycle.md),
[../exit-status/conventions.md](../exit-status/conventions.md)).

### 3.4 Process vs. thread vs. child termination

- `return`/`exit`/`_Exit`/`abort` terminate the **process** (all threads).
- `pthread_exit(3)` terminates only the **calling thread**; the process lives
  while any thread remains. A process whose last thread exits dies with the
  semantics of the last thread's exit.
- A **child** is terminated by the parent sending it a signal (`kill(2)`) and
  reaped by `wait`. A parent that exits without waiting leaves the child to
  be reparented; an unreaped dead child is a **zombie** (§5.5).
- Detached threads (created with `PTHREAD_CREATE_DETACHED` or detached via
  `pthread_detach`) need no join; at process exit their stacks are simply
  reclaimed by the kernel teardown — but note their code is still running
  while atexit handlers execute, so shutdown ordering is a race unless
  coordinated (see §6).

---

## 4. Signals and OS Interaction

### 4.1 Registration

`sigaction(2)` is the POSIX registration primitive; C's `signal(3)` is
specified to behave as BSD-style (no re-install hazard) but is best avoided
in new code. `SA_SIGINFO` selects the `sa_sigaction(int, siginfo_t *, void *)`
form and is required to receive `sigqueue` payloads. Handlers installed with
`sigaction` with `SA_RESTART` make blocking syscalls restart instead of
failing with `EINTR` (man 2 sigaction; cross-link
[../../syscalls/signals-time/rt_sigaction.md](../../syscalls/signals-time/rt_sigaction.md)).

### 4.2 Masking and delivery

Each thread has a mask (`pthread_sigmask`); process-directed signals are
delivered to any thread that does not block them; thread-directed signals
(`pthread_kill`, `tgkill`) go to the chosen thread (Linux-specific
`tgkill(2)` is what glibc uses internally —
[../interfaces/tgkill.md](../interfaces/tgkill.md)). Standard signals do not
queue (multiple pending instances collapse to one); real-time signals
(`SIGRTMIN..SIGRTMAX`) do queue
([../signals/real-time-signals.md](../signals/real-time-signals.md)).
`SIGKILL` and `SIGSTOP` cannot be caught, blocked, or ignored (man 7 signal;
POSIX). `SIGSTOP`/`SIGTSTP`/`SIGTTIN`/`SIGTTOU` stop the process;
`SIGCONT` resumes it (job control — [../signals/standard-signals.md](../signals/standard-signals.md)).

### 4.3 Async-signal-safety and safe communication

The C11 handler rules (§1.5) plus the Linux async-signal-safe function list
(man 7 signal-safety) define what a handler may do. Safe patterns for
handler→application communication:

1. **Flag + `volatile sig_atomic_t`** (C11-portable), optionally a lock-free
   atomic object (C11 `_Atomic` if lock-free).
2. **Self-pipe / `signalfd`**: handler (or blocked-signal design) writes a
   byte; main loop polls (Linux; see
   [../interfaces/signalfd-pidfd.md](../interfaces/signalfd-pidfd.md) and
   [../../syscalls/net-ipc/signalfd.md](../../syscalls/net-ipc/signalfd.md)).
3. **`sigwait`-thread**: block the signal everywhere, wait for it in a
   dedicated thread — no handler at all, no safety restrictions.
4. **`sigsuspend`** for a handler-driven wait without lost-wakeup races.

Calling `printf`, `malloc`, or `exit` from a handler is unsafe; `write(2)`,
`_exit(2)`, and `sigaction` are safe.

### 4.4 Where the runtime changes OS semantics

- glibc turns `raise()` into a thread-directed send; it interposes
  `SIGABRT` bookkeeping for `abort` (if a `SIGABRT` handler returns, glibc
  restores the default disposition and re-raises — man 3 abort).
- Libraries may install their own handlers at init time; programs must not
  assume the man 7 signal default table applies unmodified after library
  initialization — check with `sigaction(SIGX, NULL, &old)`.
- `fork(2)` in a multithreaded program: the child may safely call only
  async-signal-safe functions until `execve` (man 2 fork) — this includes
  signal setup.

---

## 5. Subprocess and Child-Process Management

### 5.1 Canonical fork/exec/wait example

```c
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    pid_t pid = fork();
    if (pid == -1) { perror("fork"); return 1; }
    if (pid == 0) {                       /* child */
        execlp("grep", "grep", "-c", "root", "/etc/passwd", (char *)NULL);
        perror("execlp");                 /* exec failed: child still here */
        _exit(127);                       /* _exit: do not flush parent stdio */
    }
    int status = 0;                       /* parent */
    if (waitpid(pid, &status, 0) == -1) { perror("waitpid"); return 1; }
    if (WIFEXITED(status))
        printf("exit=%d\n", WEXITSTATUS(status));
    else if (WIFSIGNALED(status))
        printf("killed by %d%s\n", WTERMSIG(status),
               WCOREDUMP(status) ? " (core dumped)" : "");
    return 0;
}
/* Output: exit=...  (depends on system file; grep count of "root") */
```

Key discipline points, each anchored in the sources:

- **Child error path uses `_exit`**, not `exit`, to avoid running atexit
  handlers and flushing *inherited* stdio buffers twice (§3.2; man 2 vfork
  explains the hazard explicitly for vfork; for fork the child inherits the
  parent's buffered-but-unflushed data and would flush a duplicate on `exit`).
- **Always close unused pipe ends** in both parent and child after `pipe(2)`;
  holding a write end open in the parent makes the child's read never see EOF.
- **`execvp` failure statuses**: the child never returns from a successful
  exec; on failure it should `_exit(127)` or `_exit(126)` by convention
  ([../exit-status/conventions.md](../exit-status/conventions.md)).

### 5.2 Waiting: blocking, polling, options, waitid

```c
pid_t w = waitpid(pid, &status, 0);      /* block */
pid_t w = waitpid(pid, &status, WNOHANG); /* poll: 0 if still running */
pid_t w = waitpid(-1, &status, WNOHANG | WUNTRACED | WCONTINUED);
int r = waitid(P_PID, (id_t)pid, &info, WEXITED | WSTOPPED | WCONTINUED
                                      | WNOHANG);
```

`waitpid` selects by PID, `0` (process group of the caller), `-1` (any
child), or a negative PGID. `waitid` offers `WNOWAIT` (leave the child in a
waitable state) and richer cause reporting via `siginfo_t`
(`si_code` `CLD_EXITED`, `CLD_KILLED`, `CLD_STOPPED`, …). Without `WNOHANG`,
these calls are interruptible (`EINTR`).

### 5.3 Signaling and terminating children

`kill(pid, sig)` sends a signal (0 as `sig` tests existence); `sigqueue(pid,
sig, (union sigval){ .sival_int = x })` queues with a payload. Terminate
politely with `SIGTERM`, escalate to `SIGKILL` after a deadline — there is no
POSIX API to "wait or timeout"; the program implements it with
`timer_create`/`SIGALRM`, `signalfd`, or a waiter thread. `kill(-pgid, sig)`
addresses a process group — pair with `setpgid(2)` in the child to isolate
job-control signaling.

### 5.4 Pipes, redirection, stdio inheritance

Use `pipe(2)` + `dup2(2)` in the child before exec to wire stdin/stdout;
`posix_spawn_file_actions_adddup2/addclose` does the same without forking
hazards. `popen(3)` covers the single-stream case. Watch for:

- **Pipe buffer fill (deadlock)**: a 64 KiB default pipe fills; if the parent
  writes a large stdin stream while the child writes a large stdout stream,
  both block. Use two loops/threads or `posix_spawn` with careful sequencing.
- **Inherited descriptors**: children inherit *all* fds; leaked descriptors
  keep pipe EOF pending in unrelated descendants. `closefrom(3)`/
  `posix_spawn_file_actions_addclose` (or Linux `close_range(2)`) is the
  hygiene fix ([../../syscalls/descriptors-io/close_range.md](../../syscalls/descriptors-io/close_range.md)).
- **stdio buffering**: `popen`'s FILE is fully buffered; if the parent writes
  with stdio and then `exec`s a child without flushing, data is lost — the
  classic `ls | wc`-in-C bug.

### 5.5 Zombies, orphans, SIGCHLD

A terminated-but-unwaited child is a zombie (kernel keeps exit status until
reaped). Setting `SIGCHLD` to `SIG_IGN` (or `SA_NOCLDWAIT`) makes children
auto-reap (implementation-defined whether SIGCHLD is then sent — POSIX
`_exit`). A long-running parent should either reap in a `SIGCHLD` handler
loop (`while (waitpid(-1, &st, WNOHANG) > 0);`) or use `signalfd`/`sigwait`.
Orphans are reparented to init (PID 1) or the nearest subreaper
(`prctl(PR_SET_CHILD_SUBREAPER)`).

### 5.6 Argument arrays vs. shell execution

`execlp("sh", "sh", "-c", cmd, NULL)` and `system(cmd)`/`popen(cmd, "r")` run
the string through `/bin/sh`. Concatenating untrusted data into `cmd` is
command injection (`system("ls " user_input)` executes `; rm -rf …`). The
exec-family and `posix_spawn` take **argv arrays**; arguments pass verbatim
with no shell metacharacter interpretation. Rule of thumb: arrays for
everything programmatic; shell strings only for operator-supplied, fully
trusted commands.

### 5.7 posix_spawn as the modern default

`posix_spawn` combines fork+exec atomically-ish, supports file actions
(dup2/close/open), attribute flags (`POSIX_SPAWN_SETSIGMASK`,
`POSIX_SPAWN_SETPGROUP`), and avoids the multithreaded-fork hazards of §6. On
glibc it is implemented without a full address-space copy. Prefer it over raw
fork/exec in libraries and threaded programs (man 3 posix_spawn).

---

## 6. Concurrency and Resource Semantics

### 6.1 Threads and process-wide termination

Only the initial thread runs `main`; *any* thread calling
`exit`/`_Exit`/`abort` kills the whole process (glibc `_exit` →
`exit_group`, §3.2). `pthread_exit(3)` is the per-thread exit.
`pthread_cancel(3)` requests cancellation of another thread — thread
termination, not process termination; cancellation points and cleanup
handlers (`pthread_cleanup_push`) govern what runs. Note that a *fatal*
thread-directed signal (e.g. `pthread_kill(t, SIGKILL)`) still terminates the
whole process, not just the target thread
([../../sysprog/process-control.md](../../sysprog/process-control.md)
for the wider picture).

Signals in threaded programs: use `pthread_sigmask(3)` to direct signals to a
dedicated thread (C11's `signal()` in a multithreaded program is UB, §1.5);
`pthread_kill(3)` exists for thread-directed delivery with non-fatal signals
(`sig == 0` still performs error checking — man 3 pthread_kill).

### 6.2 fork in threaded programs

After `fork()` in a multithreaded program the child holds a single thread
replica; locks held by other (vanished) threads stay locked, so only
async-signal-safe calls are safe until exec (man 2 fork). glibc additionally
provides `pthread_atfork(3)` handlers (prepare/parent/child) used internally
to reinitialize stdio and malloc locks; relying on them is fragile — use
`posix_spawn` in threaded designs.

### 6.3 fd and resource ownership

Fork duplicates fd *numbers* sharing one open file description (shared
offsets, shared `O_APPEND`); both parent and child must close their copies.
`FILE*` stdio objects are *not* shared — the child's buffer is a copy
(duplicate-flush hazard, §5.1). malloc arenas, mutexes, and condition
variables belong to the address space: valid in the pre-exec child only for
async-signal-safe use.

### 6.4 Races, deadlocks, leaks at shutdown

- **Race**: `exit` on thread A while thread B is inside a malloc call that an
  atexit handler also calls → lock state is fine here (exit runs handlers on
  the exiting thread, others may still run) but any *data* B writes after A
  decided to exit may be lost; coordinate with joins or flags.
- **Deadlock**: atexit handler waiting on a mutex held by a killed/blocked
  thread; handler calling into a stopped child's pipe.
- **Leak**: `_Exit` paths skip stdio flush by design; unflushed `FILE*` data
  is lost, not leaked to the OS. fd leaks across fork are the real leak
  vector (§5.4).

---

### Coverage ledger

Statuses: **documented** = covered above with verified signature and
reference; **source-limited** = a named primary source was unreachable (state
what is missing). Signature sources: N1570 (ISO C), POSIX.1-2017
(pubs.opengroup.org/onlinepubs/9699919799), man-pages (man7.org).

| API | Canonical signature | Status | Reference |
|---|---|---|---|
| `exit` | `_Noreturn void exit(int status);` (C11; `[[noreturn]]` in C23) | documented | N1570 §7.22.4.4; man 3 exit |
| `_Exit` | `_Noreturn void _Exit(int status);` | documented | N1570 §7.22.4.5; POSIX `_Exit` |
| `quick_exit` | `_Noreturn void quick_exit(int status);` | documented | N1570 §7.22.4.7 |
| `abort` | `_Noreturn void abort(void);` | documented | N1570 §7.22.4.1; man 3 abort |
| `atexit` | `int atexit(void (*func)(void));` | documented | N1570 §7.22.4.2; man 3 atexit |
| `at_quick_exit` | `int at_quick_exit(void (*func)(void));` | documented | N1570 §7.22.4.3 |
| `signal` | `void (*signal(int sig, void (*func)(int)))(int);` | documented | N1570 §7.14.1.1; man 2 signal |
| `raise` | `int raise(int sig);` | documented | N1570 §7.14.2; man 3 raise |
| `sigaction` | `int sigaction(int sig, const struct sigaction *restrict act, struct sigaction *restrict oact);` | documented | POSIX `sigaction`; man 2 sigaction |
| `sigprocmask` | `int sigprocmask(int how, const sigset_t *restrict set, sigset_t *restrict oset);` | documented | POSIX `sigprocmask`; man 2 |
| `sigpending` | `int sigpending(sigset_t *set);` | documented | POSIX `sigpending`; man 2 |
| `sigsuspend` | `int sigsuspend(const sigset_t *sigmask);` | documented | POSIX `sigsuspend`; man 2 |
| `sigwait` | `int sigwait(const sigset_t *restrict set, int *restrict sig);` | documented | POSIX `sigwait`; man 3 |
| `pthread_sigmask` | `int pthread_sigmask(int how, const sigset_t *restrict set, sigset_t *restrict oset);` | documented | POSIX; man 3 |
| `pthread_kill` | `int pthread_kill(pthread_t thread, int sig);` | documented | POSIX; man 3 pthread_kill |
| `fork` | `pid_t fork(void);` | documented | POSIX `fork`; man 2 fork |
| `vfork` | (POSIX: removed since POSIX.1-2008) Linux: `pid_t vfork(void);` | documented | man 2 vfork; POSIX.1-2008 removed it |
| `execve` | `int execve(const char *path, char *const argv[], char *const envp[]);` | documented | POSIX `exec`; man 2 execve |
| `execl/execle/execlp/execv/execvp` | per POSIX `exec` synopsis (l/v/e/p variants) | documented | POSIX `exec`; man 3 exec |
| `fexecve` | `int fexecve(int fd, char *const argv[], char *const envp[]);` | source-limited | POSIX page fetched via `exec` listing; dedicated page not fetched — signature taken from the `exec` synopsis |
| `posix_spawn` | `int posix_spawn(pid_t *restrict pid, const char *restrict path, const posix_spawn_file_actions_t *file_actions, const posix_spawnattr_t *restrict attrp, char *const argv[restrict], char *const envp[restrict]);` | documented | POSIX; man 3 posix_spawn |
| `posix_spawnp` | same shape as `posix_spawn` with `const char *restrict file` + PATH search | documented | POSIX; man 3 posix_spawn |
| `wait` | `pid_t wait(int *stat_loc);` | documented | POSIX `wait`; man 2 wait |
| `waitpid` | `pid_t waitpid(pid_t pid, int *stat_loc, int options);` | documented | POSIX `wait`; man 2 wait |
| `waitid` | `int waitid(idtype_t idtype, id_t id, siginfo_t *infop, int options);` | documented | POSIX `waitid` |
| `kill` | `int kill(pid_t pid, int sig);` | documented | POSIX; man 2 kill |
| `sigqueue` | `int sigqueue(pid_t pid, int signo, union sigval value);` | documented | POSIX; man 2 sigqueue |
| `system` | `int system(const char *command);` | documented | N1570 §7.22.4.8; POSIX; man 3 system |
| `popen`/`pclose` | `FILE *popen(const char *command, const char *mode);` `int pclose(FILE *stream);` | documented | POSIX; man 3 popen |
| `pthread_exit` | `void pthread_exit(void *value_ptr);` | source-limited | POSIX page not fetched this session; referenced from man-7 cross-links only |
| `pthread_cancel` | `int pthread_cancel(pthread_t thread);` | source-limited | POSIX page not fetched this session; semantics summarized from cross-links |
| `environ` | `extern char **environ;` | documented | POSIX `exec` synopsis |

Counts: **33** inventoried · **31** documented · **2** source-limited ·
**0** remaining (everything identified was either documented or marked
source-limited with the missing source named).

---

## Related Topics

- Language siblings: [C++](./cpp.md) · [Rust](./rust.md) · [Go](./go.md)
- Signals: [Standard signals](../signals/standard-signals.md) ·
  [Real-time signals](../signals/real-time-signals.md) ·
  [Async-signal-safety](../interfaces/async-signal-safety.md)
- Interfaces: [kill and raise](../interfaces/kill-raise.md) ·
  [sigaction/signal](../interfaces/sigaction-signal.md) ·
  [signal masks](../interfaces/signal-masks.md) ·
  [sigwait/sigsuspend](../interfaces/sigwait-sigsuspend.md) ·
  [signalfd/pidfd](../interfaces/signalfd-pidfd.md)
- Exit status: [Lifecycle](../exit-status/lifecycle.md) ·
  [Conventions (0, 128+N, 137…)](../exit-status/conventions.md)
- Existing book pages: [signals overview](../../../linux/sysprog/signals.md) ·
  [process control](../../../linux/sysprog/process-control.md) ·
  [_exit(2)](../../../linux/syscalls/process/_exit.md) ·
  [execve(2)](../../../linux/syscalls/process/execve.md) ·
  [wait4(2)](../../../linux/syscalls/process/wait4.md) ·
  [kill(2)](../../../linux/syscalls/signals-time/kill.md)
- Containers (PID 1 semantics for C binaries):
  [containers/pid1-signals](../containers/pid1-signals.md)

## References

- ISO C11 draft N1570, §5.1.2.2.1, §5.1.2.2.3, §7.14.1.1, §7.14.2, §7.22.4 —
  WG14, https://port70.net/~nsz/c/c11/n1570.html (mirror of the WG14 draft)
- POSIX.1-2017 (IEEE Std 1003.1-2017), `exit`/`_Exit`, `fork`, `exec`, `wait`,
  `waitid`, `posix_spawn`, `kill`, `sigaction`, `sigprocmask`, `sigsuspend`,
  `sigwait`, `pthread_sigmask`, `pthread_kill`, `sigqueue`, `system`, `popen` —
  https://pubs.opengroup.org/onlinepubs/9699919799/
- Linux man-pages (retrieved 2026-10): exit(3), abort(3), atexit(3),
  raise(3), _exit(2), fork(2), vfork(2), execve(2), wait(2), kill(2),
  sigaction(2), sigprocmask(2), sigpending(2), sigsuspend(2), sigwait(3),
  pthread_kill(3), pthread_sigmask(3), sigqueue(2), posix_spawn(3),
  system(3), popen(3), signal-safety(7) — https://man7.org/linux/man-pages/
- cppreference C reference (mirror of the standard; used for C11→C23
  signature spelling), `exit`, `_Exit`, `abort`, `atexit`, `quick_exit`,
  `at_quick_exit`, `signal`, `raise` — https://en.cppreference.com/w/c/program
- glibc behavior (exit_group wrapper since 2.3) as documented in man 2
  `_exit`, NOTES section.
