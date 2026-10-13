# C: Language Semantics, Standard Library, Process APIs, and Subprocesses

C is the language the process model was written in: `fork`, `exec`, the wait
status word, `atexit`, and signal masks are all C APIs first. That makes C the
reference point for every other chapter in this part — and also the language
where the largest gap separates what the **ISO C standard** says, what
**POSIX** adds, what **glibc** implements, and what the **Linux kernel**
finally does. This chapter documents C as a complete documentation project
over six areas: syntax and semantics insofar as they bear on process
lifecycle, the standard-library/runtime inventory, process creation and
termination, signals and OS interaction, subprocess management, and
concurrency/resource semantics. Every claim is labeled with its layer:
**[ISO C]**, **[POSIX]**, **[glibc]**, **[Linux]**.

**Declared scope** (all sources fetched 2026-10-13):

- **ISO C17** (ISO/IEC 9899:2017, draft **N2310**, open-std.org) as the
  language baseline, with **C23 deltas** verified against the C23 working
  draft **N3220** (ISO/IEC 9899:2024, open-std.org). C99 deltas verified
  against N1256 (ISO/IEC 9899:TC3). Where a clause is cited as `§7.22.4.4`
  it is the C17 numbering; C23 renumbered the library (§1.5).
- **glibc 2.44**, current stable per sourceware.org/glibc (released
  2026-07-25). The glibc manual (gnu.org) was unreachable from this
  environment at retrieval time; every glibc-behavior claim below is instead
  anchored in the man-pages pages that document glibc behavior, and the
  affected rows are marked in [ledger-c.md](./ledger-c.md).
- **POSIX.1-2024** (IEEE Std 1003.1-2024, Issue 8), via
  pubs.opengroup.org/onlinepubs/9799919799 and the **man-pages 6.19**
  project (man7.org, dated 2026-06-05).
- **Linux kernel UAPI** where relevant: the kernel-level claims here are
  anchored in the man-pages pages that document kernel behavior
  (`exit_group(2)`, `fork(2)`, `wait(2)`, `sigaction(2)`); the
  git.kernel.org source browser was bot-protected at retrieval time, so
  rows that wanted the raw UAPI headers are marked `source-limited`.

The exit/signal slice of C — the same territory as this chapter's §3 and §4 —
already has a dedicated chapter in the Linux part:
[../../linux/process-exit-signal/languages/c.md](../../linux/process-exit-signal/languages/c.md)
(N1570/C11-based, POSIX.1-2017-era). That chapter and this one do not
contradict each other: this chapter supersedes its *clause numbers* with the
C17/C23 baseline and extends it with the subprocess and concurrency areas.
Sibling Section-G chapters: [./cpp.md](./cpp.md), [./rust.md](./rust.md);
part hub: [./index.md](./index.md). Interview-topic companions:
[../c/posix.md](../c/posix.md), [../c/undefined-behavior.md](../c/undefined-behavior.md),
[../c/memory-management.md](../c/memory-management.md).

---

## 1. Syntax and Semantics

### 1.1 Translation units, linkage, and storage duration

A C program is a set of **translation units** — each source file after
preprocessing. **[ISO C]** (N2310 §6.2.2): identifiers at file scope have
*external* linkage by default, *internal* linkage if declared `static`, and
*no* linkage if declared inside a block. The same object declared `extern`
in two translation units is one object; tentative definitions (a file-scope
`int x;` with no initializer) are merged by the linker. There is no module
system: header files are textual inclusion, and ODR-style guarantees do not
exist — two translation units can declare the same object with different
types and the standard has nothing to say about the resulting program.

**Storage duration** (N2310 §6.2.4) is the lifetime rule that matters for
process semantics:

- **static** — objects at file scope or declared `static` live for the whole
  program execution, constructed-before-`main` by the runtime in practice
  (initialized before program startup per §5.1.2).
- **automatic** — block-scoped objects live until their block exits. The
  footnote to N2310 §5.1.2.2.3 makes this load-bearing for `main`: when
  `main` *returns*, automatic objects of `main` have already been destroyed
  before `exit` runs; when `main` calls `exit`, they have not. Invisible in
  C, visible in C++ ([./cpp.md](./cpp.md)).
- **allocated** — `malloc`/`free` (N2310 §7.22.3); ownership is manual and
  *not* tied to any scope or stack frame. Process termination is therefore
  the one "cleanup" that drops all allocated storage at once — the OS
  reclaims it, which is why leaks matter little for exit-only programs and a
  lot for long-lived daemons ([../c/memory-management.md](../c/memory-management.md)).
- **thread** — `_Thread_local` (C11+); lifetime of the declaring thread.

### 1.2 `main` and program startup

**[ISO C]** The hosted entry point must be `int`:

- C17 (N2310 §5.1.2.2.1): `int main(void)` or
  `int main(int argc, char *argv[])` "or equivalent; or in some other
  implementation-defined manner."
- C23 (N3220 §5.1.2.3.2): same constraint, renumbered; the "equivalent"
  footnote now explicitly blesses `char **argv` and `typeof(1)` as the
  return type.

Parameter rules (both standards): `argc` is nonnegative, `argv[argc]` is
`NULL`, the strings are modifiable and retain their last-stored values
between startup and termination. `argv[0]` is the program name, empty string
if unavailable. **[POSIX]** adds that `argc`/`argv`/`environ` are how
`execve(2)`'s arrays reach the program, and `environ` is initialized from
`execve`'s `envp` (POSIX `exec`; POSIX `posix_spawn`).

### 1.3 Evaluation: sequencing, data races, and the in-scope UB inventory

**[ISO C]** (N2310 §5.1.2.4, C23 same): *sequenced before* is the pairwise
order between evaluations; evaluations that are not sequenced relative to
each other are **unsequenced**; *indeterminately sequenced* means one is
sequenced before the other but it is unspecified which. Consequences:

- Two unsequenced modifications of the same object (or a modification and a
  read other than to determine the stored value) are **undefined behavior**
  — the classic `i = i++` family.
- A **data race** — "two conflicting actions in different threads, at least
  one of which is not atomic, and neither happens before the other" — is
  **undefined behavior** (N2310 §5.1.2.4; listed in Annex J). This is the
  clause behind every rule in §4.5 and §6: shared state touched by a signal
  handler or a second thread without atomics/locks is not "racy", it is UB.

The **undefined / unspecified / implementation-defined behavior in scope**
for this chapter (not a full UB catalog — the survey is
[../c/undefined-behavior.md](../c/undefined-behavior.md)):

| Behavior | Status | Anchor |
|---|---|---|
| Handler refers to non-atomic static/thread object (beyond `volatile sig_atomic_t` assignment) | UB | N2310 §7.14.1.1¶5; N3220 §7.14.1.1¶5 |
| Handler calls library functions other than `abort`, `_Exit`, `quick_exit`, (C23: lock-free `<stdatomic.h>` functions), `signal(sig,…)` | UB | same clauses |
| Returning from a handler for SIGFPE/SIGILL/SIGSEGV | UB | N2310 §7.14.1.1¶3 |
| Using `signal()` in a multi-threaded program | UB | N2310 §7.14.1.1 (Annex J.2); N3220 §7.14.1.1¶8 |
| `exit` called more than once, or `exit` + `quick_exit` mixed | UB | N2310 §7.22.4.4¶2 |
| `quick_exit` twice or `quick_exit` + `exit` mixed | UB | N2310 §7.22.4.7¶2 |
| Signal raised while `quick_exit` executes | UB | N2310 §7.22.4.7¶2 |
| `longjmp` out of an `atexit`/`at_quick_exit` handler | UB | N2310 §7.22.4.4¶3 |
| Calling `exit`/`longjmp` out of a glibc-registered handler (atexit or on_exit) | UB (glibc: "none of the remaining functions is called, and further exit processing … is abandoned" if the handler does not return) | man7 exit(3); N1570 §7.22.4.4¶3 |
| Data race between threads | UB | N2310 §5.1.2.4 |
| Whether `atexit` called concurrently with `exit` succeeds | *unspecified* | N2310 §7.22.4.2 ("It is unspecified whether a call to the atexit function that does not happen before the exit function is called will succeed") |
| Whether streams are flushed/closed on `_Exit`/`abort` | *implementation-defined* | N2310 §7.22.4.5/§7.22.4.1 |
| Which signals are `SIG_IGN` at program startup | *implementation-defined* | N2310 §7.14.1.1¶6 |
| Handler re-install/mask behavior after `signal()` | *implementation-defined* | N2310 §7.14.1.1¶3 |

### 1.4 Normal vs. abnormal termination — the vocabulary

**[ISO C]** defines exactly two classes (N2310 §7.22.4): *normal*
termination is `exit`, `_Exit`, `quick_exit`, and returning from `main`;
*abnormal* termination is `abort` (via `raise(SIGABRT)`). Signal death from
an external signal is not an ISO C category at all — the standard only sees
that execution stopped. **[POSIX]** classifies for the parent: normal
termination → `WIFEXITED`; signal death → `WIFSIGNALED`; stopping →
`WIFSTOPPED` (§3.5, §5.3).

### 1.5 Version deltas that change in-scope semantics

| Version | Delta in scope | Anchor |
|---|---|---|
| **C89/C99** | `atexit`, `exit`, `abort`, `system`, `signal`, `raise` exist; `main` termination rule §5.1.2.2.3 | N1256 §5.1.2.2.3 |
| **C99** | `_Exit` added (C99 numbering §7.20.4.4; `exit` §7.20.4.3); `atexit` minimum 32 | N1256 §7.20.4.4 |
| **C11** | `quick_exit`/`at_quick_exit` added (§7.22.4.7/§7.22.4.3); `_Noreturn` specifier; atomics: handler may touch *lock-free* atomic objects; `<threads.h>` optional via `__STDC_NO_THREADS__` | N2310 §7.22.4.7, §7.14.1.1, §6.10.9 |
| **C17** | No feature changes — bug-fix revision; in-scope wording identical to C11 | N2310 (ISO/IEC 9899:2017) |
| **C23** | `[[noreturn]]` attribute replaces `_Noreturn` in all termination prototypes; library clause renumbered: stdlib 7.22→**7.24** (`exit` §7.24.4.4), hosted-`main` 5.1.2.2→**5.1.2.3**; handler rules extended to `<stdatomic.h>` functions and `constexpr` objects; `<threads.h>` still optional | N3220 §5.1.2.3.4, §7.24.4.4, §7.14.1.1¶5, §7.28 |

Two cross-version constants of life worth stating once: the implementation
shall support **at least 32** `atexit` and 32 `at_quick_exit` registrations
(C17 §7.22.4.2/4.3), and `atexit`/`at_quick_exit` lists are *distinct* — the
footnotes explicitly tell applications they may need to register the same
function with both.

### 1.6 Misconceptions

- *"`exit(1)` is a failure and `exit(0)` is success because the C standard
  says so."* The standard says only that `0`/`EXIT_SUCCESS` and
  `EXIT_FAILURE` map to implementation-defined successful/unsuccessful
  statuses (N2310 §7.22.4.4¶5). It is POSIX and the shell that fix the
  convention (§3.5).
- *"Falling off the end of `main` gives an unspecified status."* No — it is
  **defined** to return 0 (C17 §5.1.2.2.3).
- *"`_Exit` is just a portable name for `_exit`."* On POSIX they are
  required to be functionally equivalent (POSIX `_Exit`), but `_Exit` is
  ISO C (C99+) and `_exit` is POSIX; their ISO/POSIX *contract* differs
  (§3.2).
- *"`abort` flushes stdio on the way out."* Implementation-defined per ISO
  C; in practice glibc does not flush ([glibc]: man7 abort(3) —
  raise(SIGABRT) path, no stdio teardown).
- *"`signal()` is safe in threads because glibc makes it thread-safe."*
  ISO C says UB (§7.14.1.1); POSIX requires thread-safety and says so in the
  `signal` RATIONALE ("However, POSIX.1 has required signal() to be
  thread-safe since before threads were added to the ISO C standard") — but
  new POSIX code should still use `sigaction()` (§4.1).
- *"`atexit` handlers run when the program is killed by a signal."* They do
  not; only `exit`-family paths run them (§3.4).

---

## 2. Standard-Library and Runtime API Inventory

Signatures are transcribed from the cited standards and man pages for the
declared versions (retrieved 2026-10-13). C23 spelling shown where the
prototype changed; C17 spelling in §1.5.

### 2.1 Termination and registration — `<stdlib.h>` [ISO C]

| API | Canonical signature (C23 spelling; C17 uses `_Noreturn`) | Semantics / notes |
|---|---|---|
| `exit` | `[[noreturn]] void exit(int status);` (§7.24.4.4) | normal termination: `atexit` handlers in reverse registration order (a handler may register more; each is called as many times as registered), then all open streams flushed and closed, `tmpfile` files removed, control to host. `at_quick_exit` handlers are **not** called. Double-`exit`/`exit`+`quick_exit` is UB. |
| `_Exit` | `[[noreturn]] void _Exit(int status);` (§7.24.4.5) | normal termination classification; **no** `atexit`/`at_quick_exit`/signal handlers; flush/close implementation-defined. Since **C99**. |
| `quick_exit` | `[[noreturn]] void quick_exit(int status);` (§7.24.4.7) | runs only `at_quick_exit` handlers (reverse order), then `_Exit(status)`. No `atexit` handlers, no signal handlers; UB if a signal is raised during its execution. Since **C11**. |
| `abort` | `[[noreturn]] void abort(void);` (§7.24.4.1) | abnormal termination: raise `SIGABRT`; if caught and the handler does not return, `abort` does not complete; flush/close implementation-defined; unsuccessful status. |
| `atexit` | `int atexit(void (*func)(void));` (§7.24.4.2) | register normal-termination handler; ≥32 registrations; 0 on success, nonzero on failure; unspecified whether a call concurrent with `exit` succeeds. |
| `at_quick_exit` | `int at_quick_exit(void (*func)(void));` (§7.24.4.3) | same contract for the `quick_exit` list; ≥32 entries. Since **C11**. |
| `system` | `int system(const char *string);` (§7.24.4.8) | `NULL`: nonzero iff a command processor exists. Non-NULL: pass string to the processor; return value implementation-defined; "can then cause the program calling system to behave in a non-conforming manner or to terminate." POSIX sharpens everything (§5.5). |
| `getenv` | `char *getenv(const char *name);` (§7.24.4.6) | returns pointer to the associated string; "shall not be modified by the program, but may be overwritten by a subsequent call to the getenv function"; **not required to avoid data races** with threads that modify the environment; the set of names and the method of altering the list are implementation-defined — which is exactly where POSIX steps in (§2.3). |
| `assert` | `void assert(scalar expression);` (§7.2.1.1) | on failure writes diagnostics to stderr and calls `abort`; compile-out when `NDEBUG` is defined at the last `<assert.h>` inclusion; the macro is redefined each time `<assert.h>` is included per the current `NDEBUG` state. |

**[glibc]** man7 exit(3) adds implementation detail the standard leaves
open: `exit` runs `atexit` **and** `on_exit` handlers in reverse
registration order; a handler that does not return (`_exit`, or killing
itself) abandons all remaining handlers *and* stdio flushing; "a call to
execve(2) removes registrations created using atexit(3) and on_exit(3)."

### 2.2 Signals — `<signal.h>` [ISO C] and POSIX additions

| API | Canonical signature | Layer | Semantics / notes |
|---|---|---|---|
| `signal` | `void (*signal(int sig, void (*func)(int)))(int);` | [ISO C] §7.14.1.1 | install `SIG_DFL`/`SIG_IGN`/handler. Post-handler reinstall-vs-block behavior implementation-defined; multi-threaded use is UB per ISO C (§4.7). Returns previous handler or `SIG_ERR` (+ `errno`). |
| `raise` | `int raise(int sig);` | [ISO C] §7.14.2.1 | send to the executing program/thread; handler runs synchronously, `raise` returns after it; 0 on success. [POSIX]: to the *thread* — effectively `pthread_kill(pthread_self(), sig)`. |
| `sigaction` | `int sigaction(int sig, const struct sigaction *restrict act, struct sigaction *restrict oact);` | [POSIX] | examine/modify per-signal action; `act == NULL` queries. The preferred interface (§4.2). |
| `sigprocmask` | `int sigprocmask(int how, const sigset_t *restrict set, sigset_t *restrict oset);` | [POSIX] | change calling thread's mask; "its behavior is unspecified if called from a multi-threaded process" (POSIX `pthread_sigmask`). |
| `pthread_sigmask` | `int pthread_sigmask(int how, const sigset_t *restrict set, sigset_t *restrict oset);` | [POSIX] | per-thread mask; returns the error number directly (not -1/errno); `how` ∈ {`SIG_BLOCK`, `SIG_SETMASK`, `SIG_UNBLOCK`}. |
| `sigpending` | `int sigpending(sigset_t *set);` | [POSIX] | pending-and-blocked set for the calling thread. |
| `sigsuspend` | `int sigsuspend(const sigset_t *sigmask);` | [POSIX] | atomically replace mask and wait for an unblocked signal; always returns -1 with `EINTR` when it returns. The race-free wait primitive (§4.3). |
| `sigwait` | `int sigwait(const sigset_t *restrict set, int *restrict sig);` | [POSIX] | synchronously consume one pending signal from `set` (which must be blocked); returns error number; never `EINTR`. No handler runs. |
| `pause` | `int pause(void);` | [POSIX] | suspend until a signal whose action is to run a handler or terminate; returns -1/`EINTR` only after a caught handler returns. |
| `alarm` | `unsigned alarm(unsigned seconds);` | [POSIX] | schedule `SIGALRM` after *realtime* seconds; 0 cancels a pending alarm; requests are not stacked; returns seconds remaining of a previous request. |
| `kill` | `int kill(pid_t pid, int sig);` | [POSIX] | pid > 0: that process; 0: caller's process group; -1: all permitted processes; < -1: process group \|pid\|. `sig == 0` is the null signal: permission check only. |

### 2.3 Environment — `<stdlib.h>`/`<unistd.h>`

| API | Canonical signature | Layer | Ownership / notes |
|---|---|---|---|
| `environ` | `extern char **environ;` | [POSIX] (declared in POSIX; also `exec` synopsis) | NULL-terminated array of `"name=value"` strings; created by `execve(2)`'s `envp`; forked children inherit a copy. [Linux] layout documented in man7 environ(7). |
| `getenv` | `char *getenv(const char *name);` | [ISO C] | must not modify the returned string; POSIX RATIONALE: the ISO-C "internal buffer" allowance "is no longer permitted" — the return value points into the environment itself. |
| `setenv` | `int setenv(const char *envname, const char *envval, int overwrite);` | [POSIX] | **copies** the string; fails with `EINVAL` if name contains `=`; existing name + `overwrite == 0` → success, no change; may `ENOMEM`. |
| `unsetenv` | `int unsetenv(const char *name);` | [POSIX] | removes variable; name with `=` or empty is `EINVAL`; absence is success; "shall update the list of pointers to which environ points." |
| `putenv` | `int putenv(char *string);` | [POSIX] | **the string becomes part of the environment** — "altering the string shall change the environment"; the caller must keep it alive and not modify/free it (or deliberately use that aliasing). Passing `name=` without `=` … a `name` with no `=` may unset. |
| `clearenv` | `int clearenv(void);` | [glibc] (SVID/BSD; `_DEFAULT_SOURCE`) | clears the entire environment; glibc man page notes it uses/behaves like `environ = NULL`, with the attendant leak caveats. Not in ISO C or POSIX (POSIX RATIONALE: "The clearenv() function was considered but rejected"). |

**Ownership asymmetry is the trap**: `setenv` copies; `putenv` aliases;
`getenv` returns a borrowed, mutable-only-by-the-implementation pointer; and
`getenv` is *not required to avoid data races* with a concurrent
`setenv`/`unsetenv` in another thread — serialize environment mutation
yourself or restrict it to single-threaded startup.

### 2.4 What ISO C does **not** have

Everything in §5 (fork/exec/wait/spawn/pipe/popen), the POSIX signal
interfaces of §2.2 beyond `signal`/`raise`, `pthreads` (§6), and
`_exit(2)` are **outside ISO C**. ISO C's only process-model primitives are
the termination family and `system`. A freestanding implementation has no
`main`, no `exit` (freestanding program termination is
implementation-defined — N3220 §5.1.2.2), and none of the above. This
layering is why the same C source can be valid ISO C and still not be
portable to Windows without a POSIX layer.

---

## 3. Process Creation and Termination

### 3.1 The `main` → `exit` pipeline, in four layers

1. **[ISO C]** A return from the initial call to `main` is *equivalent to
   `exit(main_value)`*; reaching the closing `}` of `main` returns 0
   (N2310 §5.1.2.2.3, N3220 §5.1.2.3.4). Automatic objects of `main` are
   destroyed by the return before this `exit` runs.
2. **[POSIX]** The runtime startup (`crt1.o` in glibc's case) invokes
   `main` as a C function call with `argc`/`argv` and an initialized
   `environ` (POSIX `posix_spawn` documents both facts from the parent
   side).
3. **[glibc]** `exit(3)` runs the `atexit`/`on_exit` lists, flushes and
   closes all stdio streams, removes `tmpfile` files, then calls the
   `_exit` wrapper.
4. **[Linux]** `_exit(2)` invokes the `exit_group(2)` system call — since
   glibc 2.3 — terminating *all threads* of the process; the parent gets
   `SIGCHLD` and the status stays readable by `wait` until reaped (man7
   _exit(2) NOTES).

```c
#include <stdio.h>
#include <stdlib.h>

static void log_close(void) { fprintf(stderr, "atexit: flushing logs\n"); }

int main(int argc, char *argv[]) {
    atexit(log_close);
    if (argc < 2) return 1;      /* == exit(1): atexit runs, stdio flushed */
    printf("starting %s\n", argv[1]);  /* line-buffered on tty; flushed by exit */
}                                /* falling off the end == exit(0) */
/* Expected: "starting x\n" then "atexit: flushing logs\n" for any argv;
   only "atexit: flushing logs\n" then status 1 when invoked with no args. */
```

### 3.2 The termination functions, side by side

All wording below is [ISO C] (N2310 §7.22.4 = N3220 §7.24.4) except where a
layer is labeled.

| Function | Handlers run | Signal handlers | stdio flush | Streams closed | Classified | Standard-version |
|---|---|---|---|---|---|---|
| `return` from `main` | yes (via `exit`) | n/a | yes | yes | normal | all |
| `exit(status)` | `atexit` (reverse) | not called | **yes** | yes | normal | C89+ |
| `_Exit(status)` | none | not called | implementation-defined | implementation-defined | normal | **C99+** |
| `_exit(status)` | none | not called | **shall not flush** (POSIX) | "whether open streams are closed (without flushing) is implementation-defined" | normal | POSIX |
| `quick_exit(status)` | `at_quick_exit` only (reverse) | not called | no (`_Exit` path) | implementation-defined | normal | **C11+** |
| `abort()` | none | runs SIGABRT handler; if it returns, termination proceeds | implementation-defined | implementation-defined | **abnormal** | C89+ |

POSIX precision on the exit-status plumbing [POSIX] (POSIX `_Exit`/`_exit`
page): the value made available to `wait()`/`waitpid()` is
`status & 0377` — the **low 8 bits**; "the full value shall be available
from waitid() and in the siginfo_t passed to a signal handler for SIGCHLD."
The `_Exit()`/`_exit()` pair "shall not call functions registered with
atexit() nor at_quick_exit(), nor any registered signal handlers" and "open
streams shall not be flushed."

**[glibc]** `abort(3)` first *unblocks* `SIGABRT`, then raises it; if a
handler catches it and returns, glibc restores the default disposition and
re-raises — `abort` cannot return (man7 abort(3)). **[Linux]** the SIGABRT
death follows the normal core-dump rules (RLIMIT_CORE, `core_pattern`).

### 3.3 `atexit` / `at_quick_exit` ordering and concurrency

- Registration order defines invocation order *reversed*: A, B, C
  registered → C, B, A called. A handler registering another handler adds
  it to the front of the remaining list — so late registrations run early
  ([glibc] man7 exit(3) documents this explicitly; ISO C's "called after
  any previously registered functions that had already been called at the
  time it was registered" says the same).
- A handler runs *as many times as it was registered* (C17 §7.22.4.4 fn.).
- **Concurrency**: the C17/C23 wording is a happens-before statement — a
  concurrent `atexit` racing the `exit` call is *unspecified* to succeed
  (§1.3 table). Register your handlers before any thread can exit.
- The two lists are independent; registering a function with both is the
  documented pattern for `exit`-and-`quick_exit` cleanup (N2310 fn. to
  §7.22.4.2/§7.22.4.3).
- `quick_exit` is the sanctioned "other runtimes may keep their state"
  path: a library that must not run someone else's `atexit` cleanup
  terminates via `quick_exit` with only its own `at_quick_exit` handlers.

```c
#include <stdlib.h>
#include <stdio.h>

static void a(void) { puts("a"); }
static void b(void) { puts("b"); }

int main(void) {
    atexit(a);
    atexit(b);
    atexit(a);            /* registered twice: runs twice, innermost-first */
    return 0;
}
/* Expected output:
   a        <- last-registered 'a'
   b
   a        <- first-registered 'a'
   exit status 0 */
```

### 3.4 What actually runs on each path — consolidated

Composition of §2.1, §3.1–§3.3, and man7 exit(3)/abort(3)/_exit(2):

| Termination path | `atexit` | `at_quick_exit` | SIGABRT handler | stdio flushed | Mechanism [glibc]/[Linux] |
|---|---|---|---|---|---|
| return from `main` | yes | no | n/a | yes | `exit()` → `exit_group(2)` |
| `exit(n)` | yes | no | n/a | yes | same |
| `quick_exit(n)` | no | yes | not called | no (`_Exit`) | `at_quick_exit` list → `_Exit` |
| `_Exit(n)` / `_exit(n)` | no | no | not called | no | `exit_group(2)` directly |
| `abort()` | no | no | yes (return → re-raise) | no (practice) | `raise(SIGABRT)` → SIGABRT (+possible core) |
| death by unhandled signal (SIGINT/SIGTERM/…) | no | no | — | no | kernel default action |

Two practical consequences follow. First, **only the `exit`-family paths
are "graceful"** — a program that wants output delivered under every
termination must either funnel all exits through `return`/`exit`, or flush
explicitly before calling `_Exit`/`abort`. Second, `execve(2)` discards
`atexit` registrations ([glibc] man7 exit(3) NOTES; POSIX `exec`: "any
functions previously registered by the atexit(), at_quick_exit(), or
pthread_atfork() functions are no longer registered") — a fork-child that
execs carries no parent-cleanup baggage.

### 3.5 Exit status vs. wait status — the distinction that breaks programs

The child calls `exit(int)`; the parent reads an `int` from `wait(2)`.
These are **different representations**:

- The child's `status` is truncated to **8 bits** for `wait()`/`waitpid()`
  observers ([POSIX] `status & 0377`, quoted §3.2; [Linux] man7 wait(2):
  `WEXITSTATUS` = "least significant 8 bits"). `exit(256)` is
  indistinguishable from `exit(0)`; `exit(-1)` reports as 255.
- `waitid(2)` and the `SIGCHLD` `siginfo_t` carry the *full* value per
  POSIX.1-2024 — a portable-program design point (portable programs should
  nonetheless restrict themselves to 0–255 because 8-bit observers are
  everywhere).
- The parent's `int` is a **wait status word**: `WIFEXITED`/
  `WEXITSTATUS`/`WIFSIGNALED`/`WTERMSIG`/`WCOREDUMP`/`WIFSTOPPED`/
  `WSTOPSIG`/`WIFCONTINUED` decode it (§5.3). Normal-exit and
  signaled-exit are mutually exclusive encodings; there is no "exit code
  137" in the word — 128+N is a shell convention applied *after* decoding.
- A zero wait-status word means exactly: the child returned 0 from `main`,
  or called `_exit`/`exit(0)`, or "was terminated because the last thread
  in the process terminated" (POSIX `wait`) — the thread-lifecycle escape
  hatch that produces status 0 without any explicit `exit`.
- `EXIT_SUCCESS`/`EXIT_FAILURE` are ISO C macros whose
  *values* are implementation-defined; POSIX fixes the observable
  convention: status 0 = success.

### 3.6 Process vs. thread vs. child

- **Process**: `return`/`exit`/`_Exit`/`abort` terminate it. Any thread may
  call them; the kernel mechanism (`exit_group`) kills all threads.
- **Thread**: `pthread_exit(value_ptr)` terminates only the calling thread
  (§6.1). When the **last** thread of a process terminates — with no
  explicit `exit` anywhere — the process terminates with exit status 0
  (POSIX `wait`: the zero wait-status word's third cause). ISO C's
  `<threads.h>` offers the analogous `thrd_exit`
  (optional header — `__STDC_NO_THREADS__` may be defined, C11/C23 alike).
- **Child**: terminated by sending it a signal (`kill(2)`) or waiting for
  it to exit itself; its status exists only after reaping (§5.7).
- **[POSIX]** `raise(sig)` is thread-directed in POSIX; `kill(pid, sig)` is
  process-directed. A fatal thread-directed signal still terminates the
  whole process — threads are kernel tasks sharing a PID; "thread death"
  vs "process death" is decided by the signal's action and the kernel's
  group-exit logic, not by which thread was targeted.

---

## 4. Signals and OS Interaction

### 4.1 The four layers of "signal handling"

- **[ISO C]** has one primitive: `signal()`. Its semantics are
  deliberately thin: after a handler runs, whether the implementation
  re-executes `signal(sig, SIG_DFL)` or blocks a set of signals during
  handling is implementation-defined (N2310 §7.14.1.1¶3) — the historical
  SysV (re-install default, handler becomes one-shot) vs BSD (reliable,
  mask-during-handler) split. ISO C also allows `SIG_IGN` to be installed
  for implementation-defined signals at startup (¶6).
- **[POSIX]** adds the real machinery: `sigaction` with a per-signal
  `struct sigaction` (`sa_handler`/`sa_sigaction` union, `sa_mask`,
  `sa_flags`), masks, delivery rules, `SA_*` flags, and queuing for
  real-time signals. POSIX `signal`'s APPLICATION USAGE is the canonical
  advice: sigaction "provides a more comprehensive and reliable mechanism
  for controlling signals; new applications should use sigaction() rather
  than signal()."
- **[glibc]** implements C `signal(3)` as a wrapper over `sigaction(2)`
  with BSD semantics (handler stays installed, `SA_RESTART` behavior) —
  "By default, in glibc 2 and later, the signal() wrapper function does not
  invoke the kernel system call. Instead, it calls sigaction(2) using flags
  that supply BSD semantics" (man7 signal(2)); the kernel's raw `signal`
  syscall is System V semantics and is not what glibc programs get.
- **[Linux]** the kernel delivers via the `rt_sigaction` syscall family;
  glibc installs a `SA_RESTORER` trampoline internally; syscalls interrupted
  by handlers are restarted or fail with `EINTR` per `SA_RESTART` and the
  kernel's per-syscall restartability list (man7 signal(7),
  sigaction(2)).

### 4.2 `sigaction` — the registration primitive

```c
int sigaction(int sig, const struct sigaction *restrict act,
              struct sigaction *restrict oact);
```

The struct has at least: `void(*)(int) sa_handler`, `sigset_t sa_mask`
(additional signals blocked during handler execution), `int sa_flags`,
`void(*)(int, siginfo_t *, void *) sa_sigaction` (storage may overlap with
`sa_handler` — never use both) (POSIX `sigaction`). Flags that change
process semantics:

| Flag | Effect |
|---|---|
| `SA_RESTART` | syscall restart instead of `EINTR` on interruption (kernel decides which syscalls are restartable) |
| `SA_SIGINFO` | use `sa_sigaction` three-argument handler; required for `sigqueue` payloads |
| `SA_NOCLDSTOP` | with SIGCHLD: no notification when children stop/continue |
| `SA_NOCLDWAIT` | with SIGCHLD: "do not transform children into zombies" — auto-reap (§5.7); POSIX leaves unspecified whether SIGCHLD is still generated; on Linux it **is** generated (man7 sigaction(2)) |
| `SA_NODEFER` | do not add the signal to the mask during its own handler |
| `SA_ONSTACK` | deliver on the alternate stack (`sigaltstack`) — cleared across `exec` (POSIX `exec`: "alternate signal stacks are not preserved and the SA_ONSTACK flag shall be cleared for all signals") |

`SIGKILL` and `SIGSTOP` cannot be added to a mask or caught/ignored —
"this restriction shall be enforced by the system without causing an error
to be indicated" (POSIX `sigaction`; man7 signal(7)).

### 4.3 Masks, delivery, and the wait patterns

- Each thread has its own mask; **[POSIX]** `pthread_sigmask` is the
  multithreaded interface (`sigprocmask` in a multithreaded process is
  *unspecified*). A new thread inherits the creating thread's mask and
  starts with an empty pending set (POSIX `pthread_create`).
- **Delivery**: process-directed signals are delivered to any thread not
  blocking them; thread-directed (`pthread_kill`, `raise`) go to the
  target. A standard signal pending for a process is pending *once*
  — duplicates collapse; real-time signals queue.
- **Race-free waiting**: `sigsuspend(&waitmask)` atomically swaps the mask
  and sleeps, closing the lost-wakeup window between "unblock" and "sleep".
  The other standard pattern is the **sigwait thread**: block the signal in
  *all* threads at startup, then a dedicated thread consumes it with
  `sigwait(&set, &sig)` — no handler runs, so no async-signal-safety
  restrictions apply (POSIX `sigwait`; man7 pthreads(7)).

```c
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

static volatile sig_atomic_t got_usr1 = 0;   /* [ISO C]-safe flag */

static void on_usr1(int sig) { (void)sig; got_usr1 = 1; }

int main(void) {
    struct sigaction sa = {0};
    sa.sa_handler = on_usr1;          /* no SA_RESTART: see §4.6 */
    if (sigaction(SIGUSR1, &sa, NULL) == -1) { perror("sigaction"); exit(1); }
    raise(SIGUSR1);                   /* synchronous; handler runs first */
    printf("flag=%d\n", got_usr1);    /* expected: flag=1 */
    return 0;
}
```

### 4.4 Handler→program communication and its limits

**[ISO C]** (N3220 §7.14.1.1¶5, quoted in §1.3): the handler may *only*
assign to a `volatile sig_atomic_t`, read/write **lock-free** atomic
objects, call `abort`/`_Exit`/`quick_exit` (and, C23, lock-free
`<stdatomic.h>` functions and `constexpr` objects), or re-install itself
with `signal(sig, …)`. Everything else — `printf`, `malloc`, `exit`,
mutexes — is UB by the standard.

**[POSIX]** widens this to an explicit safe list (man7 signal-safety(7)):
`write`, `_exit`, `sigaction`, `kill`, `sigsuspend`, `waitpid`, and others
are async-signal-safe; the man page explains *why* the rest are not — e.g.
stdio keeps a shared buffer whose internal state a handler corruption
would wreck. The practical rules:

1. The portable subset is the ISO C one; treat the POSIX list as the
   POSIX-platform extension.
2. Communication patterns, safest first: flag + `volatile sig_atomic_t`;
   lock-free atomics (C11 `_Atomic`, if lock-free); self-pipe (handler
   `write(2)`s a byte; main loop selects on it); `sigwait`-thread (no
   handler at all).
3. `sig_atomic_t` guarantees atomic *access* only — not memory ordering,
   not multi-field updates; one variable, one value, written once per
   delivery.

### 4.5 Default dispositions and exec-time resets

- **[POSIX]** on `exec`: default → default; `SIG_IGN` → `SIG_IGN`
  (**except SIGCHLD**, where ignore-or-default after exec is unspecified);
  caught → default; masks and pending sets carry into the new image's
  initial thread; alternate stacks do not survive (§4.2).
- **[Linux]** default actions are documented per signal in man7 signal(7)
  (term/core/stop/cont/ignore). Libraries may install handlers at init;
  never assume the default table applies to your process — query with
  `sigaction(SIGX, NULL, &old)`.

### 4.6 `EINTR`, `SA_RESTART`, and the interruptible world

Without `SA_RESTART`, a caught signal interrupts blocking syscalls: they
return -1/`EINTR`. POSIX requires programs to handle this (`waitpid`,
`waitid`, `pause` all document `EINTR`); the classic retry loops exist
because `SA_RESTART` is per-signal opt-in and some operations are not
restartable regardless (e.g. `poll` with a timeout was historically
non-restartable). Design either for `EINTR` retries everywhere, or block
signals around critical waits, or use `sigwait`-style consumption.

### 4.7 Signals and threads — the layered rules

- **[ISO C]**: `signal()` in a multithreaded program is UB (N3220
  §7.14.1.1¶8; Annex J). The standard has no thread-aware signal API at
  all.
- **[POSIX]**: `signal()` must be thread-safe (RATIONALE quote §1.6), but
  `sigaction` is still the recommended interface; masks are per-thread
  (`pthread_sigmask`); handlers run on *some* thread that has the signal
  unblocked.
- **[glibc]/[Linux]**: `raise()` is implemented over `pthread_kill`/`tgkill`
  to the calling thread (man7 raise(3)); glibc interposes SIGABRT handling
  for `abort` (§3.2).

---

## 5. Subprocess and Child-Process Management

### 5.1 `fork` — what is copied, what is reset

**[POSIX]** `pid_t fork(void);` / `pid_t _Fork(void);` (Issue 8 added
`_Fork`: like `fork` but never runs `pthread_atfork` handlers and is
async-signal-safe — the MT-safe primitive). The child is an exact copy of
the calling process except: a unique PID, a different parent, and — for
`fork` in a multithreaded process — "the new process shall contain a
replica of the calling thread and its entire address space, possibly
including the states of mutexes"; the child "shall only execute
async-signal-safe operations until such time as one of the exec functions
is successful" (POSIX `fork`).

**[glibc]/[Linux]** the address-space "copy" is **copy-on-write**: pages
are shared read-only and duplicated on first write, so fork costs page
tables and bookkeeping, not the whole image (man7 fork(2)). Inherited:
open file descriptors (sharing the same *open file descriptions* — offsets
and status flags are shared, not copied), the environment copy, signal
mask, current/ root directory, umask, resource limits, controlling
terminal. Not inherited: memory locks, per-process timers (`alarm(2)` among
them — the child's alarm queue is empty), pending signals (child's pending
set is empty), process-associated record locks, semaphore adjustments,
CPU-time counters (man7 fork(2) list).

### 5.2 The `exec` family — suffix semantics and layer membership

**[POSIX]** (Issue 8 `exec` page, verbatim synopsis):

```c
extern char **environ;
int execl(const char *path, const char *arg0, ... /*, (char *)0 */);
int execle(const char *path, const char *arg0, ... /*, (char *)0,
           char *const envp[]*/);
int execlp(const char *file, const char *arg0, ... /*, (char *)0 */);
int execv(const char *path, char *const argv[]);
int execve(const char *path, char *const argv[], char *const envp[]);
int execvp(const char *file, char *const argv[]);
int fexecve(int fd, char *const argv[], char *const envp[]);
```

| Suffix | Meaning | Notes |
|---|---|---|
| `l` | argument *list* terminated by `(char *)0` | `execl`, `execlp`, `execle` |
| `v` | argument *vector* (`argv[argc] == NULL`) | `execv`, `execvp`, `execve`, `fexecve` |
| `e` | caller supplies `envp` (else `environ` is inherited) | `execle`, `execve`, `execvpe`, `fexecve` |
| `p` | `PATH` search for *file* without `/` | `execlp`, `execvp`; glibc adds `execvpe` |
| `f` | executable referenced by open **fd** (`fexecve`) | avoids path lookup races; pair with `O_CLOEXEC` control |

- `execvpe` is **[glibc] (GNU extension)** — not in POSIX.1-2024 (the exec
  page has no `execvpe`); it is `execvp` plus explicit `envp`
  (man7 exec(3)).
- PATH search ([glibc] man7 exec(3)): colon-separated `PATH` of the
  caller's environment; if unset, a default list from
  `confstr(_CS_PATH)` (typically `/bin:/usr/bin`). `execvpe` searches
  using the caller's `PATH`, not the `envp` argument's.
- **ENOEXEC fallback**: `execlp`/`execvp` (and `execvpe`) on a file that
  would fail with `ENOEXEC` shall instead run it as a script via a command
  interpreter: `execl(<shell path>, <name>, file, <args>, (char *)0)`
  (POSIX `exec`). A failed exec of a *real binary* returns -1; there is no
  return from a successful exec: "There shall be no return from a
  successful exec, because the calling process image is overlaid by the
  new process image."
- Conventional failure statuses: children that cannot exec `_exit(127)`
  (command not found) or `_exit(126)` (found, not executable) — the
  statuses POSIX assigns to `sh` for the same conditions, and the
  documented `system()` interpreter-failure value (§5.5).

**[POSIX]** exec-time state resets (complete list on the `exec` page):
signal dispositions per §4.5; mask/pending inherited; alternate stacks
dropped; `atexit`/`at_quick_exit`/`pthread_atfork` registrations dropped;
effective-IDs per setuid/setgid bits and ST_NOSUID; all other attributes
are inherited — which is why "leak an fd into a child" is the default, not
the exception (§5.9).

### 5.3 The wait family and status macros

```c
#include <sys/wait.h>
pid_t wait(int *stat_loc);
pid_t waitpid(pid_t pid, int *stat_loc, int options);
int   waitid(idtype_t idtype, id_t id, siginfo_t *infop, int options);
```

- `wait(&st)` = `waitpid(-1, &st, 0)`. `waitpid` pid semantics: `-1` any
  child; `> 0` that child; `0` same process group; `< -1` process group
  `|pid|`. Options: `WNOHANG` (poll — returns 0 when none of the selected
  children have status available), `WUNTRACED` (also report stopped
  children), `WCONTINUED` (report continued children; still **[XSI]**
  marked in POSIX.1-2024).
- `waitid(idtype, id, infop, options)` selects by `P_PID`/`P_PGID`/`P_ALL`
  with `WEXITED`/`WSTOPPED`/`WCONTINUED`/`WNOHANG`/`WNOWAIT` (leave the
  child waitable). On success returns 0 and fills `siginfo_t`
  (`si_code` `CLD_EXITED`/`CLD_KILLED`/…, `si_status`). With `WNOHANG` and
  nothing to report it returns 0 with `si_pid == 0`-style empty info per
  the POSIX "2.12 Status Information" rules.
- **Macros** (POSIX `wait`; man7 wait(2)): `WIFEXITED`,
  `WEXITSTATUS` (low 8 bits), `WIFSIGNALED`, `WTERMSIG`,
  `WCOREDUMP` — **newly standardized in POSIX.1-2024** ("this macro shall
  evaluate to a non-zero value if the creation of a core image … was
  attempted"; non-zero does not guarantee a file exists, e.g.
  `RLIMIT_CORE = 0`), `WIFSTOPPED`/`WSTOPSIG`, `WIFCONTINUED`.
- `EINTR`: without `WNOHANG` both `wait` and `waitpid` are interruptible
  (documented failure). The value of `stat_loc` is *undefined* when the
  call fails.
- **[POSIX]** multiple threads blocked in `wait()`-family calls: exactly
  one is woken per child state change (2.12 Status Information).

**BSD heritage**: `pid_t wait3(int *wstatus, int options, struct rusage
*rusage);` and `pid_t wait4(pid_t pid, int *wstatus, int options, struct
rusage *rusage);` are [glibc]/[Linux] (man7 wait4(2)); `wait3` was removed
from POSIX with Issue 7 and survives in glibc under `_DEFAULT_SOURCE`
feature-test rules; `wait4` was never POSIX. They add `rusage` of the
reaped child. New code uses `waitid` (or Linux `wait4` where rusage
matters).

### 5.4 `posix_spawn` / `posix_spawnp` — the modern default

```c
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

- Return: 0 on success (child PID stored through non-NULL `pid`), otherwise
  an **error number as the return value** (not -1/errno). "If this error
  occurs after the calling process successfully returns … the child process
  may exit with exit status 127" — internal housekeeping failures are
  reported through the child's 127, the same convention as `system`
  (POSIX `posix_spawn`).
- **file_actions** (`posix_spawn_file_actions_init/addopen/adddup2/
  addclose/adddup2` semantics applied in order in the child between spawn
  and exec) are the fd-redirection mechanism without forking your own
  address space; **attrs** set flags like `POSIX_SPAWN_SETSIGMASK`,
  `POSIX_SPAWN_SETSIGDEF`, `POSIX_SPAWN_SETPGROUP`, `POSIX_SPAWN_RESETIDS`
  (and glibc's `POSIX_SPAWN_USEVFORK`).
- **[glibc]** implements spawn without a full fork: before glibc 2.24 it
  used `vfork(2)` (or `clone(CLONE_VM|CLONE_VFORK)`); current glibc uses
  fork-based or vfork-style paths chosen per attribute/file_actions
  complexity (man7 posix_spawn(3) VERSIONS/NOTES). Consequence for
  libraries: `posix_spawn` sidesteps the multithreaded-fork hazards of §6.5
  — prefer it in threaded code.

### 5.5 `system` and `popen` — shell in the loop

```c
int system(const char *command);                 /* <stdlib.h> */
FILE *popen(const char *command, const char *mode);   /* <stdio.h> */
int   pclose(FILE *stream);
```

**[POSIX]** `system` is specified as: create a child with `fork()`, and the
child invokes the shell as

```c
execl(<shell path>, "sh", "-c", "--", command, (char *)0);
```

while the parent "shall ignore the SIGINT and SIGQUIT signals, and shall
block the SIGCHLD signal, while waiting for the command to terminate"
(POSIX `system`). That signal discipline is why a program using `system`
does not die of terminal Ctrl-C aimed at the child's process group — and
why the standard warns the application may *miss* a fatal signal and must
check the return value instead. Return value: -1 (child could not be
created / status unavailable, `errno` set), `127`-style (interpreter could
not execute), otherwise the **wait status** of the shell — decode with the
`W*` macros, never compare directly. `command == NULL` → nonzero iff a
shell exists.

**[glibc]** `system(3)` uses `/bin/sh` (man7 system(3)); ISO C leaves the
command processor implementation-defined, so `system` is a POSIX-behavior
function in ISO-C clothing.

**`popen`** runs `command` with one pipe end wired to the child's
(`"r"`: child stdout → readable stream; `"w"`: child stdin ← writable
stream; POSIX.1-2024 also specifies that the `FD_CLOFORK` flag is cleared
on both ends). `pclose` waits like `waitpid` on the shell process and
returns its wait status; -1/`ECHILD` if the status is gone. **[glibc]**
adds mode `'e'` since glibc 2.9: sets `FD_CLOEXEC` on the underlying
descriptor (man7 popen(3)). Beware: `popen` streams are fully buffered;
`fflush`/`pclose` ordering matters for interleaved writes.

**Injection hazard.** Both functions interpret their argument as a shell
*program*: `system("ls " dir)` with `dir = "/; rm -rf /"` executes two
commands. Concatenating untrusted data into `command` is command
injection — including *indirect* injection through filenames with
metacharacters. The argv-based interfaces (`execve`-family,
`posix_spawn`) pass arguments verbatim with no shell layer; use them for
anything programmatic, and reserve `system`/`popen` for operator-supplied,
trusted command strings.

### 5.6 Pipes and redirection — the canonical pattern

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    int fds[2];
    if (pipe(fds) == -1) { perror("pipe"); return 1; }
    pid_t pid = fork();
    if (pid == -1) { perror("fork"); return 1; }
    if (pid == 0) {                        /* child: pipe -> stdout */
        close(fds[0]);
        dup2(fds[1], STDOUT_FILENO);
        close(fds[1]);
        execlp("grep", "grep", "-c", "root", "/etc/passwd", (char *)NULL);
        _exit(127);                        /* exec failed: never flush parent stdio */
    }
    close(fds[1]);                         /* parent: read end only */
    char buf[64];
    ssize_t n = read(fds[0], buf, sizeof buf - 1);
    close(fds[0]);
    int status = 0;
    waitpid(pid, &status, 0);              /* reap; EINTR-safe loop in production */
    if (WIFEXITED(status) && n > 0) {
        buf[n] = '\0';
        printf("grep said %s", buf);       /* expected: "grep said N\n" */
        return 0;
    }
    return 1;
}
```

Discipline points, each anchored earlier: close unused ends *in both
processes* (a stray write-end keeps readers from ever seeing EOF); the
child's error path uses `_exit` (§3.4 — do not run the parent's atexit
handlers or flush the duplicated stdio buffers); `dup2(fds[1],
STDOUT_FILENO)` closes the new fd's previous target atomically; an
`exec`-less child should `close` its copy of everything it does not need.
**[Linux]** pipe capacity is finite (default 64 KiB, queryable via
`fcntl(fd, F_GETPIPE_SZ)`) — readers and writers must progress in
parallel or deadlock (§6.4, man7 pipe(2)/fcntl(2)).

### 5.7 SIGCHLD, zombies, and reaping

A terminated-but-unwaited child is a **zombie**: the kernel keeps the exit
status until reaped. Reaping strategies, POSIX-portable first:

1. Wait for each child you spawn (`waitpid`/`waitid`) — the normal case.
2. A `SIGCHLD` handler whose *entire body* is
   `while (waitpid(-1, &st, WNOHANG) > 0);` — reaps all pending deaths
   without leaking (both calls are async-signal-safe).
3. `sigaction`'s `SA_NOCLDWAIT` for SIGCHLD, or `SIGCHLD` set to `SIG_IGN`:
   children are auto-reaped, never becoming zombies. POSIX leaves it
   unspecified whether SIGCHLD is then generated; **[Linux]** generates it
   (man7 sigaction(2)) — do not rely on a SIGCHLD count with this setting.
4. In threaded servers: block SIGCHLD everywhere and reap in a dedicated
   `sigwait` thread (§4.3).

Unreaped zombies are a resource leak (process IDs are finite); a parent
that exits without reaping leaves its zombies to be reaped by their new
parent ([Linux]: init or the nearest subreaper).

### 5.8 `EINTR` discipline for subprocess code

Every blocking call in the loop — `waitpid`, `read`/`write` on pipes,
`pause`, `sigsuspend` — can fail with `EINTR` when a caught signal arrives
(§4.6). Retry on `EINTR`; do not treat it as an error. Alternatively
install handlers with `SA_RESTART` so the kernel retries for you where
possible — but note `EINTR` still surfaces for non-restartable operations,
so robust code does both.

### 5.9 fd inheritance, CLOEXEC, and `close_range`

Children inherit **all** file descriptors across `fork`, and after `exec`
they keep every descriptor whose close-on-exec flag is clear. The hygiene
set:

- `O_CLOEXEC` on `open`/`pipe2`-style creation ([Linux]) or
  `fcntl(fd, F_SETFD, FD_CLOEXEC)` ([POSIX]) — descriptors auto-close on
  successful exec, so a leaked fd never reaches an exec'd child.
- `posix_spawn_file_actions_addclose`/`adddup2` — explicit child-side fd
  shaping with no fork window.
- **[Linux]** `int close_range(unsigned int first, unsigned int last, int
  flags);` (man7 close_range(2), since Linux 5.9) — close everything from
  `first` to `last` in the pre-exec child.
- **[POSIX]** Issue 8 introduces `FD_CLOFORK` (close-on-fork) — visible in
  the `popen` page's specification of the pipe ends; Linux code today
  typically uses `O_CLOEXEC` + `close_range` instead.

The two failure shapes: a *leaked fd into an exec'd child* keeps pipe EOFs
pending in unrelated descendants; a *double-close* (two owners of one
descriptor, e.g. after careless `dup2` bookkeeping) can silently steal a
reused fd number from an unrelated object (§6.3).

### 5.10 Timeouts and cancellation — there is no `wait_with_timeout`

POSIX has no timed wait for children. Documented building blocks:

- **`alarm(n)` + `SIGALRM`**: arm the timer, block `SIGALRM`, `waitpid`;
  on the alarm either `kill(pid, SIGKILL)` then reap, or longjmp-free
  designs using a `sigwait` thread that kills and lets the waiter proceed.
- **Polling**: `waitpid(pid, &st, WNOHANG)` on a timer tick (nanosleep or
  `poll(NULL, 0, timeout)`), kill at the deadline, reap — the same
  kill-then-reap invariant every other language chapter here needs.
- **`sigtimedwait`/`signalfd` [Linux]**: wait for SIGCHLD with a timeout
  instead of polling.

Whatever the mechanism: the deadline path must still reap (zombie rules
§5.7), and a timed-out kill surfaces to the parent as `WIFSIGNALED` with
`WTERMSIG == SIGKILL` — not as an "error" from wait.

---

## 6. Concurrency and Resource Semantics

### 6.1 pthread essentials for process lifecycle

```c
int  pthread_create(pthread_t *restrict thread, const pthread_attr_t *restrict attr,
                    void *(*start_routine)(void*), void *restrict arg);
int  pthread_join(pthread_t thread, void **retval);
int  pthread_detach(pthread_t thread);
_Noreturn void pthread_exit(void *value_ptr);
int  pthread_cancel(pthread_t thread);
int  pthread_sigmask(int how, const sigset_t *restrict set, sigset_t *restrict oset);
```

(POSIX `pthread_*` pages; glibc implements pthreads as native Linux
threads — man7 pthreads(7).)

- Returning from `start_routine` is *as if* `pthread_exit(return_value)` —
  except for the thread `main` ran in: returning from `main` is as if
  `exit(return_value)` (POSIX `pthread_create`) — i.e. **process** death.
- `pthread_exit` terminates the calling thread only: cancellation cleanup
  handlers run (reverse order), TSS destructors run, and "Thread
  termination does not release any application visible process resources,
  including, but not limited to, mutexes and file descriptors, nor does it
  perform any process-level cleanup actions, including … calling any
  atexit() routines" (POSIX `pthread_exit`). The process dies only when
  its last thread exits.
- `pthread_join` reaps the thread (joinable by default); `pthread_detach`
  or `attr` with `PTHREAD_CREATE_DETACHED` makes it self-releasing. An
  unjoined, undetached joinable thread leaks its resources — the
  thread-level zombie.
- Thread signal state: new threads inherit the creating thread's *mask*
  and have an empty pending set (§4.3) — the standard "block early,
  `sigwait` in a dedicated thread" pattern depends on it.

### 6.2 Cancellation: `pthread_cancel`, points, cleanup handlers

`pthread_cancel(t)` requests cancellation; the target's *cancelability
state* (`PTHREAD_CANCEL_ENABLE` default / `DISABLE`) and *type* (deferred
default / asynchronous) decide when it takes effect. With deferred
cancellation the request is honored only at **cancellation points** — the
POSIX-defined list of blocking functions (`read`, `write`, `waitpid`,
`nanosleep`, `pthread_join`, …). At cancellation: pushed cleanup handlers
run in reverse push order, then TSS destructors, then the thread
terminates (POSIX `pthread_cancel`/`pthread_cleanup_push`). It is not an
error to cancel an already-terminated (zombie) thread. Design consequence:
a canceled thread holding a mutex or an fd must push cleanup handlers that
release it — cancellation is *not* exception-safe cleanup by default, and
asynchronous cancellation can tear the thread apart mid-operation.

```c
pthread_cleanup_push(close_pipe_fd, wr_fd);   /* runs if canceled/exited early */
/* ... blocking work ... */
pthread_cleanup_pop(1);                        /* pop with execute */
```

### 6.3 fd ownership across fork/exec — no borrow checker here

`fork` duplicates fd *numbers*; both copies refer to one **open file
description** — one file offset, one status-flag set (man7 fork(2)). So:
parent and child share a pipe's seek state (pipes have none, files do);
`lseek` in one is visible to the other; closing your copy does not affect
the other's. Ownership problems this creates, with no language-level
protection ([../c/pointers.md](../c/pointers.md) covers the pointer-side
equivalents):

- **Double close**: two code paths own "the" fd; the second `close(fd)`
  may close a number that `open`/`accept` reissued in between — corrupting
  an unrelated stream. Ownership discipline (one owner per fd; close in
  exactly one place) is manual.
- **Leak into children**: every fd without `FD_CLOEXEC` crosses `exec`
  (§5.9).
- **Half-open pipes**: a parent that forgets to close a write end after
  spawning prevents any reader from seeing EOF — the child's output loop
  blocks forever.

### 6.4 stdio buffering × fork — the double-flush and lost-output bugs

**[glibc]/[POSIX]** stdio has three modes (man7 stdio(3), setbuf(3)):
**unbuffered** (stderr by default), **line buffered** (stdout on a
terminal), **full/block buffered** (stdout to a file or pipe). At startup
the standard streams are set accordingly (man7 stdin(3): "stdout is
line-buffered when it points to a terminal"). The process semantics:

- **fork copies the stdio buffers.** If the parent had unflushed data
  buffered at `fork` time, the *child* holds a copy too; a child that
  calls `exit` flushes it → output appears **twice**. Fix: flush before
  forking, or `_exit` in the child on its error paths (§3.4).
- **exec discards the buffers.** Unflushed stdio data in a child that
  execs is lost (the new image replaces stdio state).
- **Buffering × redirection** is the `ls | wc`-in-C bug: a program whose
  stdout is a pipe is *fully* buffered, so interleaving `printf` and
  `write(STDOUT_FILENO, …)` reorders output. `setvbuf(stdout, NULL,
  _IOLBF, 0)` (or `fflush` at the seams) restores sanity.
- **Handler safety**: all stdio functions are async-signal-unsafe (man7
  signal-safety(7) explains the shared-buffer corruption scenario) —
  the §4.4 rules follow.

### 6.5 Deadlocks and races: the fork window and the exit race

- **malloc between fork and exec in a threaded parent.** After `fork` in a
  multithreaded process the child has one thread; every mutex held by a
  *vanished* thread stays locked forever in the child — including glibc's
  malloc and stdio locks. The child calling `malloc`, `printf`, or even
  `execlp`'s PATH handling that allocates can deadlock instantly (POSIX
  `fork`: "the application shall ensure that the child process only
  executes async-signal-safe operations until … exec"). Modern answers:
  `posix_spawn` (§5.4), `_Fork` + careful pre-exec code, or `pthread_atfork`
  prepare handlers that lock everything (now obsolescent, §6.7).
- **The exit race**: thread A calls `exit` while thread B is mid-`malloc`
  or mid-stdio-write. `exit` runs `atexit` handlers on the exiting thread
  while other threads may still run concurrently — the standard's own
  answer is that a concurrent `atexit` call "does not happen before the
  exit" is *unspecified* to succeed (§3.3), and a data race with anything
  the handlers touch is UB (§1.3). Coordinate: join/flag all threads
  before any thread exits the process.
- **atexit handler deadlock**: a handler that waits on a mutex held by a
  thread that has already terminated (its locks are not released by thread
  death — POSIX `pthread_exit` quote, §6.1) blocks `exit` forever. Same
  shape as the Rust poison/drop interactions in [./rust.md](./rust.md),
  with no poisoning to rescue you.
- **double-close** (§6.3) is the race that survives code review.

### 6.6 Resource leaks

- **fd leaks on error paths**: an early `return` between `pipe` and
  `close`, or between `socket` and `dup2`, leaks one descriptor per event —
  long-running servers exhaust `RLIMIT_NOFILE`, and leaked fds inside
  long-lived children keep pipes un-EOF. Audit paths; use `close_range`/
  `posix_spawn` file actions (§5.9).
- **Zombie accumulation**: parents that never reap (§5.7) — the
  signature unmanaged-child leak; every PID is a kernel task slot.
- **Unjoined threads**: joinable threads that are neither joined nor
  detached leak thread resources until process exit.
- **Allocated memory** at exit is reclaimed wholesale by the OS — leaks
  matter for lifetime, not for termination ([../c/memory-management.md](../c/memory-management.md)).

### 6.7 `pthread_atfork` — registered, obsolescent, and what replaced it

```c
int pthread_atfork(void (*prepare)(void), void (*parent)(void), void (*child)(void));
```

prepare handlers run before `fork` processing, parent/child handlers after
it in the respective processes (POSIX `pthread_atfork`; [glibc] man7
pthread_atfork(3)). **POSIX.1-2024 marks `pthread_atfork()` as
obsolescent** (Issue 8 change history: "Austin Group Defect 851 is
applied, marking pthread_atfork() as obsolescent"), and `exec` clears its
registrations (§3.4). The direction of travel: `_Fork()` (no fork
handlers, async-signal-safe) for raw process creation, `posix_spawn` for
exec-shaped needs, and explicit child-side code instead of magic
re-initialization handlers. glibc itself uses fork handlers internally to
make `fork` in a threaded program less fatal, but relying on that invisible
repair is not a design.

---

## Coverage ledger

The per-item coverage ledger for this chapter is
[ledger-c.md](./ledger-c.md) (IDs `PL-C-001`…`PL-C-082`, G4 schema).
Rollup at publication: **Inventoried: 82 / Documented: 81 / Remaining: 0 /
Source-limited: 1** — the single source-limited row is the raw Linux UAPI
wait-status header (`include/uapi/linux/wait.h`): git.kernel.org was
bot-protected and raw.githubusercontent rate-limited at retrieval, so
kernel-side wait-status claims are anchored in man-pages 6.19 instead.
Signature sources of truth: ISO C17 draft N2310 and C23 draft N3220
(open-std.org); POSIX.1-2024 (pubs.opengroup.org, Issue 8); man-pages 6.19
(man7.org); glibc version verified via sourceware.org/glibc. The glibc
manual (gnu.org) was unreachable (see ledger header); glibc-behavior rows
cite the man pages that document glibc instead.

## References

1. ISO/IEC 9899:2017 — C17 draft **N2310** (open-std.org,
   https://www.open-std.org/jtc1/sc22/wg14/www/docs/n2310.pdf; retrieved
   2026-10-13): §5.1.2.2 (hosted environment, `main`, program termination),
   §5.1.2.4 (execution semantics, data races), §6.2.2 (linkage), §6.2.4
   (storage durations), §7.2.1.1 (`assert`/`NDEBUG`), §7.14.1.1 (`signal`),
   §7.14.2.1 (`raise`), §7.22.4 (termination family, `system`).
2. ISO/IEC 9899:2024 — C23 working draft **N3220** (open-std.org,
   https://www.open-std.org/jtc1/sc22/wg14/www/docs/n3220.pdf; retrieved
   2026-10-13): §5.1.2.3.2/5.1.2.3.4 (startup/termination, C23 numbering),
   §7.14.1.1 (handler rules incl. `constexpr`/`<stdatomic.h>` relaxations),
   §7.24.4.1–7.24.4.8 (`[[noreturn]]` prototypes; renumbered library),
   §7.28 (`<threads.h>`, `__STDC_NO_THREADS__` still applies).
3. ISO/IEC 9899:TC3 — C99 draft **N1256** (open-std.org,
   https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1256.pdf; retrieved
   2026-10-13): §5.1.2.2.3, §7.20.4.3–7.20.4.4 (`exit`, `_Exit` added in
   C99), signal-handler rules of the era.
4. POSIX.1-2024 / Issue 8 (pubs.opengroup.org/onlinepubs/9799919799,
   retrieved 2026-10-13): `exec` (full family synopsis incl. `fexecve`;
   disposition/mask/`SA_ONSTACK`/`atexit`-drop rules), `fork` (incl.
   `_Fork`), `_Exit`/`_exit` (`status & 0377`; waitid full value),
   `wait` (macros incl. `WCOREDUMP` now standardized), `waitid`,
   `posix_spawn`, `system` (`sh -c --`; SIGINT/SIGQUIT/SIGCHLD
   discipline), `popen` (`FD_CLOFORK`), `sigaction`, `sigprocmask`,
   `pthread_sigmask`, `sigpending`, `sigsuspend`, `sigwait`, `pause`,
   `alarm`, `kill`, `raise`, `getenv`, `setenv`, `putenv`, `unsetenv`,
   `environ`, `pthread_create`, `pthread_join`, `pthread_detach`,
   `pthread_exit`, `pthread_cancel`, `pthread_cleanup_push`,
   `pthread_atfork` (obsolescent per Issue 8 change history), `assert`.
5. Linux man-pages **6.19** (man7.org, dated 2026-06-05; retrieved
   2026-10-13): fork(2), vfork(2), execve(2), exec(3) (`execvpe` GNU),
   wait(2) (macros; POSIX.1-2024 annotations), wait4(2) (`wait3` history),
   posix_spawn(3) (glibc vfork/clone implementation notes), system(3),
   popen(3) (mode `'e'`), signal(2) (BSD-vs-SysV glibc semantics),
   sigaction(2) (flags; `SA_NOCLDWAIT` on Linux), sigprocmask(2),
   sigpending(2), sigsuspend(2), sigwait(3), pause(2), alarm(2), kill(2),
   raise(3), signal-safety(7), signal(7), pipe(2), dup(2), close(2),
   close_range(2), open(2), fcntl(2), setenv(3), getenv(3), putenv(3),
   unsetenv(3), clearenv(3), environ(7), stdio(3), stdin(3), setbuf(3),
   exit(3) (`on_exit`, execve-drops-registrations), abort(3), atexit(3),
   _exit(2) (`exit_group` since glibc 2.3), assert(3), pthreads(7),
   pthread_create(3), pthread_join(3), pthread_exit(3), pthread_cancel(3),
   pthread_cleanup_push(3), pthread_atfork(3).
6. glibc project — sourceware.org/glibc (retrieved 2026-10-13): current
   stable version 2.44 (released 2026-07-25), development 2.45. The GNU C
   Library manual (gnu.org/software/libc/manual) was unreachable from this
   environment at retrieval; no claim in this chapter depends on it.
7. Sibling chapters and cross-links:
   [../../linux/process-exit-signal/languages/c.md](../../linux/process-exit-signal/languages/c.md)
   (exit/signal slice, N1570+POSIX.1-2017), [./cpp.md](./cpp.md),
   [./rust.md](./rust.md), part hub [./index.md](./index.md);
   interview-topic pages [../c/posix.md](../c/posix.md),
   [../c/undefined-behavior.md](../c/undefined-behavior.md),
   [../c/memory-management.md](../c/memory-management.md),
   [../c/pointers.md](../c/pointers.md).
