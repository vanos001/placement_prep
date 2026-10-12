# C++: Process Termination, Exit Status, and Signals

C++ layers three termination models on top of the OS process: **normal
termination** driven by `return`/`std::exit`, **quick termination** driven by
`std::quick_exit`, and **abnormal termination** driven by `std::abort` and the
exception machinery (`std::terminate`). The recurring question — *"which
destructors run on which path?"* — decides how RAII interacts with process
death, and this chapter answers it path by path. It also covers the C signal
API as used from C++, the interaction between signals and exceptions, and
subprocess management with `std::system` plus the POSIX interfaces available
from C++ on Linux.

Reference policy: standard wording is cited by C++ standard clause names
(`[basic.start.term]`, `[except.terminate]`, `[support.start.term]`) as
organized by **cppreference** (https://en.cppreference.com/w/cpp), which is a
community mirror of the ISO C++ standard, not the standard itself — signatures
below were verified against the cppreference pages named in the References
section (retrieved 2026-10). OS-level behavior cited from POSIX.1-2017 and
Linux man-pages. The C substrate is documented in [c.md](./c.md); this
chapter only repeats what C++ changes or adds.

---

## 1. Syntax and Semantics

### 1.1 `main` and its return value

```cpp
int main() { /* ... */ }
int main(int argc, char* argv[]) { /* ... */ }
```

`main` has type `int`. Returning from `main` — by a `return` statement or by
reaching the end of the function — *performs normal function termination*
(destroys the automatic objects of the function) and then executes
`std::exit` with the returned value (or `0` for an implicit return)
(cppreference, `std::exit`, "Relationship with the main function"; C++
standard [basic.start.main]). The essential asymmetry: **returning from
`main` runs destructors of `main`'s automatic objects; calling `std::exit`
from anywhere does not** ([basic.start.term]; cppreference notes "Stack is
not unwound: destructors of variables with automatic storage duration are
not called").

### 1.2 The termination functions

Canonical signatures (cppreference; all `<cstdlib>`):

```cpp
[[noreturn]] void exit(int exit_code);          // until C++11: void exit(int);
[[noreturn]] void _Exit(int exit_code) noexcept;        // since C++11
[[noreturn]] void quick_exit(int exit_code) noexcept;   // since C++11
[[noreturn]] void abort() noexcept;             // since C++11: void abort();

int atexit(/* c-atexit-handler or atexit-handler */* func) noexcept; // C++11 noexcept
int at_quick_exit(/* atexit-handler */* func) noexcept;              // since C++11
```

The `atexit`-handler exposition types distinguish `extern "C"` and
`extern "C++"` linkage functions (cppreference `std::atexit`); ordinary C++
function pointers work for both, and `extern "C"` functions are additionally
acceptable for `atexit`.

**`std::exit(code)`** — *normal* termination. In order (cppreference
`std::exit`, matching [basic.start.term]/[support.start.term]):

1. Objects with **static storage duration** are destroyed and `std::atexit`
   functions are called: non-local static objects are destroyed in reverse
   order of the completion of their constructor; atexit functions run in
   reverse order of registration; the two sequences interleave so that a
   function registered before an object's initialization is called after that
   object is destroyed (the full rule is on the cppreference page).
2. **All C streams are flushed and closed.**
3. Files created by `std::tmpfile` are removed.
4. Control returns to the host environment: `0`/`EXIT_SUCCESS` →
   implementation-defined successful status; `EXIT_FAILURE` → unsuccessful;
   otherwise implementation-defined.

Note what is missing: **no stack unwinding occurs**, so automatic objects are
not destroyed. Thread-local objects *are* destroyed on this path — cppreference
(`std::exit`, step 1) specifies that "the destruction of thread-local objects
is sequenced-before the first destructor for a static object", and that a
throwing thread-local destructor calls `std::terminate`. Calling `std::exit`
more than once, or calling `quick_exit` in addition to `exit`, is undefined
behavior.

**`std::quick_exit(code)`** — *quick* termination. Runs only functions
registered with `at_quick_exit`, in reverse registration order; if an
exception tries to propagate out of any of them, `std::terminate` is called;
afterwards calls `std::_Exit(exit_code)` (cppreference `std::quick_exit`).
Nothing else is destroyed or flushed: no static destructors, no atexit list,
no stream flush, no automatic-object destruction. This is the supported
"exit without any cleanup machinery" path for processes sharing a runtime
with libraries whose destructors must not run.

**`std::_Exit(code)`** — *normal classification, zero cleanup*. "Destructors
of variables with automatic, thread local and static storage durations are
not called. Functions passed to `std::at_quick_exit()` or `std::atexit()` are
not called. Whether open resources such as files are closed is implementation
defined" (cppreference `std::_Exit`). Status mapping as for `exit`.

**`std::abort()`** — *abnormal* termination. "Destructors of variables with
automatic ... storage durations are not called"; unless `SIGABRT` is being
caught by a handler installed with `std::signal` and the handler does not
return, the process terminates (cppreference `std::abort`). No flush, no
handler lists, no unwinding.

### 1.3 THE cleanup table

| Path | Automatic objects (`main` or any frame) | Static/thread-local storage objects | `atexit` handlers | `at_quick_exit` handlers | C streams flushed | Exception unwinding |
|---|---|---|---|---|---|---|
| `return n;` from `main` | destroyed (normal return) | destroyed (via `std::exit` step 1) | yes (reverse) | no | yes | n/a — already returned |
| `std::exit(n)` | **not** destroyed | destroyed (reverse ctor order, interleaved with atexit) | yes | no | yes | no unwinding |
| `std::quick_exit(n)` | no | no | no | yes (reverse) | no | no |
| `std::_Exit(n)` | no | no | no | no | impl-defined | no |
| `std::abort()` | no | no | no | no | no (impl-defined) | no |
| uncaught exception → `std::terminate` | no further destructors after unwinding stops | no | no | no | no | stack unwinding may have started before `terminate` |
| `std::thread` dtor on joinable thread | local dtor ran; then `std::terminate` → `std::abort` | no | no | no | no | no |

The single most consequential row: `std::exit` **skips** destruction of
automatic objects. A code path that builds RAII objects on the stack and then
calls `std::exit` on error (a common C-style idiom) leaks everything those
objects were managing — file handles closed only at process exit, mutexes,
transactions. Prefer exceptions or returning a status from `main`.

### 1.4 Static-object destruction order

Non-local (namespace-scope and class-static) objects are constructed in order
of definition within a translation unit; the order *across* translation units
is unspecified — the static initialization order fiasco. Destruction at
`std::exit` reverses the order of *construction completion*, and the atexit
machinery interleaves registered functions and destroyed objects (cppreference
`std::exit` step 1a–1c). Function-local statics are constructed on first
control pass through their declaration (C++11+ magic statics) and destroyed in
reverse order of construction completion; a function-local static initialized
during construction of a subobject of a class or array is destroyed only
after all subobjects/elements were destroyed (cppreference, defect-report
refinement). Consequence: destructors of static objects must not depend on
other static objects being alive — at program end, "reverse of construction"
is the only ordering guarantee, and it is per-program, not per-library.

### 1.5 Exceptions, unwinding, `noexcept`, `std::terminate`

- **Stack unwinding** destroys automatic objects as an exception propagates.
  This is C++'s only mechanism that *runs* destructors without returning
  normally.
- **`std::terminate()`** — `[[noreturn]] void terminate() noexcept;`
  (`<exception>`). Called by the runtime when the program cannot continue:
  an exception is thrown and not caught; during unwinding a destructor throws;
  an exception escapes a `noexcept` function; `std::thread` is destroyed
  while joinable; `at_quick_exit` handlers throw; and other listed cases
  (cppreference `std::terminate`). It invokes the current terminate handler.
- **Default terminate handler calls `std::abort`** (cppreference
  `std::terminate`), so an uncaught exception ends the process with an
  implementation-defined unsuccessful status (glibc: SIGABRT, typically exit
  status 134 in shells' `128+6` convention — a *convention*, see
  [../exit-status/conventions.md](../exit-status/conventions.md)).
- **`std::set_terminate`** —
  `std::terminate_handler set_terminate(std::terminate_handler f) noexcept;`
  installs a handler; `f` "shall terminate execution of the program without
  returning to its caller, otherwise the behavior is undefined" (cppreference
  `std::set_terminate`). `std::get_terminate()` returns the current handler.
- **`noexcept` violations** call `std::terminate` directly at the throw site
  (the stack may or may not have been unwound — permitted to unwind, standard
  doesn't require it; code must not depend on destructors running).
- **`std::unexpected` / `unexpected_handler`** were deprecated in C++11 and
  **removed in C++17** along with dynamic exception specifications
  (`throw(X)`); do not build on them (cppreference `std::unexpected`).

```cpp
#include <cstdio>
#include <cstdlib>
#include <exception>

struct Guard {
    const char* name;
    ~Guard() { std::printf("destroy %s\n", name); }
};

Guard g0{"static g0"};                    // destroyed by std::exit

static void on_exit_fn() { std::printf("atexit fn\n"); }

int main() {
    atexit(on_exit_fn);
    Guard g1{"auto g1"};                  // destroyed ONLY if main returns
    std::printf("exiting\n");
    std::exit(0);
}
/* Typical output (no g1!):
   exiting
   atexit fn
   destroy static g0
   (order of atexit fn vs g0 depends on registration order: fn registered
    after g0's construction, so fn is called first) */
```

### 1.6 Common misconceptions

- *"Exceptions during shutdown are caught somewhere."* No: an exception that
  escapes a static destructor or an atexit handler reaches `std::terminate`.
- *"`std::terminate` is like throwing."* It is `[[noreturn]]`, `noexcept`,
  and by default `abort()` — no cleanup.
- *"`std::quick_exit` is a faster `std::exit`."* It is a *different* contract:
  only `at_quick_exit` handlers run.
- *"Signals can be handled with C++ exceptions."* No (§4).
- *"The standard library has a process class."* It does not — see §5.

---

## 2. Standard-Library and Runtime API Inventory

All signatures verified against cppreference (see References for URLs;
retrieved 2026-10).

### 2.1 `<cstdlib>` — termination

| API | Signature (C++11+ spelling) | Key semantics |
|---|---|---|
| `std::exit` | `[[noreturn]] void exit(int exit_code);` | static dtors + atexit, stream flush/close, tmpfile removal, then host status; auto objects not destroyed; re-entry UB |
| `std::_Exit` | `[[noreturn]] void _Exit(int exit_code) noexcept;` | no dtors (auto/thread-local/static), no at_quick_exit/atexit, resource close impl-defined |
| `std::quick_exit` | `[[noreturn]] void quick_exit(int exit_code) noexcept;` | at_quick_exit only (reverse); throwing handler → `std::terminate`; then `_Exit` |
| `std::abort` | `[[noreturn]] void abort() noexcept;` | raises SIGABRT via C signal machinery; auto dtors not called; flush impl-defined |
| `std::atexit` | `int atexit(/*c-atexit-handler*/ * func) noexcept;` (+ `extern "C++"` variant) | runs on `std::exit` or return from `main`; reverse order |
| `std::at_quick_exit` | `int at_quick_exit(/*atexit-handler*/ * func) noexcept;` | runs on `std::quick_exit`; throwing handler → terminate |
| `EXIT_SUCCESS`, `EXIT_FAILURE` | macros | portable status vocabulary; other values implementation-defined |
| `std::system` | `int system(const char * command);` | host command processor (`/bin/sh -c` on POSIX); returns implementation-defined value, "usually the value that the invoked program returns"; NULL checks for a shell |

On POSIX, the `std::system` return value is the *wait status* produced by
`waitpid` — decode with the `WIFEXITED`/`WEXITSTATUS`/`WIFSIGNALED`/
`WTERMSIG` macros from `<sys/wait.h>`; it is **not** a plain exit code
(POSIX `system`). `std::system` runs the string through the shell: quoting
and injection hazards apply (§5.4).

### 2.2 `<exception>` — diagnostics

| API | Signature | Semantics |
|---|---|---|
| `std::terminate` | `[[noreturn]] void terminate() noexcept;` | runtime-invoked for uncaught exceptions, noexcept violations, throwing during unwinding, joinable-thread destruction, at_quick_exit throws, etc. |
| `std::set_terminate` | `std::terminate_handler set_terminate(std::terminate_handler f) noexcept;` | installs handler; must not return; returns previous |
| `std::get_terminate` | `std::terminate_handler get_terminate() noexcept;` | current handler (C++11) |
| `std::terminate_handler` | `using terminate_handler = void (*)();` | handler type |
| `std::current_exception`, `std::rethrow_exception`, `std::exception_ptr` | per cppreference | usable inside a terminate handler to capture the active exception |
| `std::unexpected` / `unexpected_handler` | removed in C++17 | legacy dynamic exception specification machinery; do not use |

### 2.3 Signals (`<csignal>`, inherited from C)

| API | Signature | Notes for C++ |
|---|---|---|
| `std::signal` | `void (*signal(int sig, void (*func)(int)))(int);` | C semantics; handler restrictions below |
| `std::raise` | `int raise(int sig);` | synchronous send |
| `SIGABRT` | macro | raised by `std::abort`; catchable |
| `sig_atomic_t` | type | handler-safe flag storage |

A C++ signal handler may not do C++ work: throwing from a handler, or
resuming past a hardware fault, leads to `std::terminate` or undefined
behavior (§4.2). The C11 handler restriction list (`abort`, `_Exit`,
`quick_exit`, `signal(sig, …)` for the same signal, assignments to
`volatile sig_atomic_t`, lock-free atomics) carries over — C++ standard
[except.handle]/[intro.execution] defer to the C model for signal
asynchrony; cppreference documents `std::signal` as the C function.

### 2.4 `<thread>`

| API | Signature | Termination-relevant semantics |
|---|---|---|
| `std::thread::~thread` | `~thread();` | if `joinable() == true`, **`std::terminate()` is called** (cppreference) |
| `std::thread::join` | `void join();` | blocks; rethrows the thread's exception if any |
| `std::thread::detach` | `void detach();` | releases association; detached threads keep running at process exit and are killed with the process |
| `std::this_thread::exit`? | — | does not exist; threads end by returning or throwing (→ `std::terminate` for uncaught) |

An exception that escapes a thread's top-level function calls
`std::terminate` (thread boundary is not a catch boundary).

---

## 3. Process Lifecycle and Termination

### 3.1 Creation

The C++ standard says nothing about process creation; on Linux a C++ program
is created exactly as a C program is — `fork`/`exec` by a parent, runtime
startup (`crt1.o` → static initializers → `main`). Static/global constructors
run before `main`; their exceptions (if uncaught) call `std::terminate`.
Destruction of static objects happens on the `std::exit` path only.

### 3.2 Terminating — full flow

- `return` from `main` → automatic objects of `main` destroyed → `std::exit(ret)`
  → static dtors + atexit → C stream flush/close → host status.
- `std::exit(n)` from any function/thread → (no auto destruction!) → static
  dtors + atexit → flush/close → host status. Multiple calls UB.
- `std::quick_exit(n)` → at_quick_exit handlers (reverse) → `std::_Exit(n)`.
- `std::_Exit(n)` / POSIX `_exit(n)` → kernel termination path
  (`exit_group(2)`), no user-space cleanup.
- `std::abort()` → `raise(SIGABRT)` → unless caught-and-does-not-return,
  kernel kills the process (core dump per `core(5)` settings); glibc abort
  re-raises with default disposition if the handler returns.
- Uncaught exception → unwinding (auto dtors run!) → `std::terminate` →
  current handler → `std::abort` by default.

### 3.3 Exit status propagation

Statuses pass through the OS as the 8-bit `status & 0xFF` collected via the
wait family (POSIX; [c.md](./c.md) §3.3). The C++ standard itself only
defines `0`/`EXIT_SUCCESS` → "successful", `EXIT_FAILURE` → "unsuccessful",
everything else implementation-defined. Signal death has *no* exit code in
the wait status; parents distinguish it via `WIFSIGNALED`. In C++ the common
producer paths are: normal return (the value), uncaught exception (abort →
SIGABRT), `std::abort` (SIGABRT), and direct `std::exit` values.

### 3.4 Process vs. thread vs. child

- Process termination: any of the §1.2 functions from any thread.
- Thread termination: a `std::thread` function returns or throws (throw →
  `std::terminate` for the process); the main thread returning from `main`
  ends the process; detached threads cannot be joined and are killed with
  the process; destroying a joinable `std::thread` is a bug → terminate.
- Child process: `std::system`/`popen`/POSIX `fork`+`exec`; termination is
  signaled via `kill(2)`; status via `wait(2)` — C++ has no standard types
  for any of this (§5).

---

## 4. Signals and OS Interaction

### 4.1 Registration and masking

C++ inherits the C/POSIX API unchanged: `std::signal`, and on POSIX
`sigaction`, `sigprocmask`, `pthread_sigmask` (`<csignal>` only declares the
C subset; `<signal.h>` on a POSIX system exposes the rest). There are no C++
RAII wrappers in the standard library; hand-rolling one must consider that
handlers run on any thread and that installing a handler is process-wide.
Details of the underlying interfaces:
[../interfaces/sigaction-signal.md](../interfaces/sigaction-signal.md),
[../interfaces/signal-masks.md](../interfaces/signal-masks.md).

### 4.2 Handlers must not throw

- Throwing out of a signal handler has no defined behavior: the unwinder is
  not async-signal-safe; depending on when the signal arrived (inside
  unwinding, inside allocation) the process dies via `std::terminate` or
  corrupts state. Treat "handler throws" as UB.
- The C11 handler restriction list applies (only `volatile sig_atomic_t`
  stores, lock-free atomics, `abort`/`_Exit`/`quick_exit`/same-signal
  `signal` calls; on Linux, the man 7 signal-safety function list) — see
  [c.md](./c.md) §1.5 and
  [../interfaces/async-signal-safety.md](../interfaces/async-signal-safety.md).
- Returning from a `SIGFPE`/`SIGILL`/`SIGSEGV` handler is undefined behavior
  (C11 §7.14.1.1); on glibc it usually re-executes the faulting instruction.
- Interaction of signals with exceptions is unspecified/undefined: a signal
  delivered while an exception is propagating and the handler then calls
  `std::abort` is the only well-defined combined action.

### 4.3 Safe handler→application communication

Same toolbox as C: `volatile std::sig_atomic_t` flags (C++ gives
`std::atomic<T>` for lock-free atomic objects — allowed by C11 §7.14.1.1 when
`is_lock_free()` holds; `volatile std::sig_atomic_t` remains the portable
floor), self-pipe/eventfd, `signalfd` (Linux), or a `sigwait`-dedicated
thread. A recommended C++ pattern is to block signals in worker threads at
startup with `pthread_sigmask`, then `sigwait` in a dedicated thread that
sets an atomic and lets normal code initiate shutdown — no handler safety
rules apply at all there.

### 4.4 Runtime interactions

- Global constructors may install signal handlers; ordering with respect to
  other static initialization is unspecified across TUs.
- `std::abort` *unblocks* SIGABRT before raising (POSIX/C rule), so a program
  that masked SIGABRT still dies.
- Third-party runtimes (sanitizers, JVM-embedding, profiler agents) install
  their own handlers; compose via `sigaction` chaining — outside the standard,
  OS-level topic ([../interfaces/sigaction-signal.md](../interfaces/sigaction-signal.md)).

---

## 5. Subprocess and Child-Process Management

### 5.1 What the standard has (and has not)

The C++ standard library has **no process-spawning facility** — there is no
`std::process`, no `std::popen` wrapper class, no child handles. (Rust has
`std::process::Command`, Go has `os/exec`; C++ has only `std::system`.) This
is a documented gap: C++ programs on Linux either use `std::system`, inherit
the C API (`popen`, `fork`/`exec`, `posix_spawn`, `waitpid`), or use a
third-party library (e.g. Boost.Process, subprocess libraries — third-party,
not standard). Everything in this section therefore relies on the C/POSIX
substrate described in [c.md](./c.md) §5.

### 5.2 `std::system` and `popen`

```cpp
#include <cstdlib>
#include <cstdio>
#include <sys/wait.h>

int main() {
    int st = std::system("printf 'hi\n'");     // /bin/sh -c "printf 'hi\n'"
    if (st == -1) return 127;                  // fork/wait failure
    if (WIFEXITED(st))
        std::printf("exit=%d\n", WEXITSTATUS(st));   // e.g. exit=0
    else if (WIFSIGNALED(st))
        std::printf("signal=%d\n", WTERMSIG(st));
    return 0;
}
```

- Return value is implementation-defined in the standard; POSIX pins it to
  the waitpid-format status (POSIX `system`). -1 if the child could not be
  created; `127` from the shell if the command could not be executed.
- `std::popen` does not exist as such — use `::popen` from `<cstdio>` (POSIX;
  C standard has `_popen` on Windows only).

### 5.3 fork/exec/wait from C++

Use the C signatures (§2 of [c.md](./c.md)) directly. C++-specific hazards:

- **fork + C++ runtime**: after `fork` in a multithreaded program, the child
  may run only async-signal-safe code until `exec`; that includes *no C++
  allocation, no iostreams, no exception throwing*. Constructors of global
  objects are not re-run; atexit handlers are inherited but then discarded by
  exec (man 3 exit).
- **Prefer `posix_spawn(3)`** for spawning from threaded C++ — glibc
  implements it without a full fork copy and it supports file actions
  (dup2/close) for stream redirection.
- **Exceptions and waitpid**: wrap wait loops so `EINTR` is retried; do not
  let an exception escape an atexit-style reaper.

### 5.4 Shell execution risks

`std::system` and `::popen` interpolate the string into `/bin/sh -c` —
untrusted input is command injection (`std::system(("curl " + url).c_str())`
executes anything after `;`). The safe pattern is argv arrays through
`execvp`/`posix_spawn` (§5.3). When a shell is required, quote with
`shlex`-style rules and validate inputs; never embed raw strings.

### 5.5 Streams, pipes, buffers

- `popen` gives one `FILE*`; the other end is inherited. Buffering: the
  parent's stdio buffer must be flushed before `pclose`'s status is
  meaningful; child stdio is block-buffered when not a tty — use `stdbuf`
  or explicit flushes in the child.
- Classic deadlock: parent writes large data to a child that is also writing
  large data back through a single pipe pair. Solve with two loops, threads,
  or `poll`. Same rules as C (§5.4 of [c.md](./c.md)).

### 5.6 Waiting, termination, zombies

`waitpid(pid, &st, 0)` reaps; `WNOHANG` polls; a `SIGCHLD` handler can reap
asynchronously (async-signal-safe: `waitpid` is on the safe list). Unreaped
children become zombies; a C++ long-running daemon should own a reaper or
`SA_NOCLDWAIT`. To terminate: `kill(pid, SIGTERM)`, escalate to `SIGKILL`
after a deadline — the standard library offers no timeout; build one with
threads/timers as in C.

---

## 6. Concurrency and Resource Semantics

### 6.1 Threads and destruction

- `std::thread` destructor with a joinable thread calls `std::terminate`
  (cppreference `std::thread::~thread`) — always `join()` or `detach()`
  before scope exit. This is the most common accidental `abort()` in threaded
  C++.
- Exceptions cannot cross thread boundaries; an escaping exception terminates
  the process, not just the thread.
- There is no cooperative cancellation in `std::thread`; use
  `std::stop_token`/`std::jthread` (C++20) for cooperative stops —
  `std::jthread` also joins in its destructor, fixing the terminate hazard.
  (C++20; cppreference `std::jthread`.)

### 6.2 RAII across termination paths

RAII guarantees exist **only on paths that destroy automatic objects**:
normal returns, exceptions that are caught, and unwinding up to
`std::terminate`. They do **not** exist on `std::exit` (auto objects
skipped), `quick_exit`, `_Exit`, `abort`, or signal death. Practical rules:

- Put cleanup that must run on `std::exit` into static objects or `atexit`
  handlers; cleanup that must run on all paths must not depend on RAII at
  all.
- File descriptors and locks owned by automatic objects in `main` will
  survive until process exit if `std::exit` is called — usually harmless at
  process death, but ordering-sensitive flushes (databases, protocols) break.
- Threads still running during `std::exit` race with static destructors:
  the standard provides no synchronization for "shutdown barrier"; design
  one (join-all + flag) before calling `exit`.

### 6.3 Races, deadlocks, leaks

- **Race**: two threads calling `std::exit` concurrently — UB (multiple exit
  calls). Serialize termination.
- **Deadlock**: a static destructor joining a thread that waits on a mutex
  held by an already-destroyed object; atexit handler waiting on a stopped
  child's pipe.
- **Leak**: none at process death (kernel reclaims), but *state loss*: the
  flush ordering table (§1.3) is the checklist for what is actually persisted.

---

### Coverage ledger

Statuses: **documented** = covered above with verified signature and
reference; **source-limited** = named primary source unreachable this
session (missing source stated). Signature source of truth: cppreference
pages (mirror of the ISO C++ standard, as stated in §1), POSIX.1-2017 where
noted.

| API | Canonical signature | Status | Reference |
|---|---|---|---|
| `std::exit` | `[[noreturn]] void exit(int exit_code);` (since C++11) | documented | cppreference `utility/program/exit`; [basic.start.term] |
| `std::_Exit` | `[[noreturn]] void _Exit(int exit_code) noexcept;` (C++11) | documented | cppreference `utility/program/_Exit` |
| `std::quick_exit` | `[[noreturn]] void quick_exit(int exit_code) noexcept;` (C++11) | documented | cppreference `utility/program/quick_exit` |
| `std::abort` | `[[noreturn]] void abort() noexcept;` (C++11) | documented | cppreference `utility/program/abort` |
| `std::atexit` | `int atexit(/*c-atexit-handler*/* func) noexcept;` (+ `extern "C++"` variant) | documented | cppreference `utility/program/atexit` |
| `std::at_quick_exit` | `int at_quick_exit(/*atexit-handler*/* func) noexcept;` (C++11) | documented | cppreference `utility/program/at_quick_exit` |
| `std::terminate` | `[[noreturn]] void terminate() noexcept;` | documented | cppreference `error/terminate`; [except.terminate] |
| `std::set_terminate` | `std::terminate_handler set_terminate(std::terminate_handler f) noexcept;` | documented | cppreference `error/set_terminate` |
| `std::get_terminate` | `std::terminate_handler get_terminate() noexcept;` (C++11) | documented | cppreference `error/get_terminate` (signature per that page) |
| `std::unexpected` / `unexpected_handler` | `void unexpected();` (deprecated C++11, removed C++17) | documented | cppreference `error/unexpected` |
| `std::system` | `int system(const char * command);` | documented | cppreference `utility/program/system`; POSIX `system` for wait-status packing |
| `std::signal` | `void (*signal(int sig, void (*func)(int)))(int);` | documented | cppreference `utility/program/signal`; C11 §7.14.1.1 |
| `std::raise` | `int raise(int sig);` | documented | cppreference `utility/program/raise`; C11 §7.14.2 |
| `std::sig_atomic_t` | `typedef /*...*/ sig_atomic_t;` | documented | cppreference `utility/program/sig_atomic_t` |
| `std::thread::~thread` | `~thread();` — joinable ⇒ `std::terminate()` | documented | cppreference `thread/thread/~thread` |
| `std::thread::join` | `void join();` | documented | cppreference `thread/thread/join` |
| `std::thread::detach` | `void detach();` | documented | cppreference `thread/thread/detach` |
| `std::jthread` (C++20) | `class jthread;` — joins on destruction, cooperative `stop_token` | source-limited | cppreference `thread/jthread` page not fetched this session; existence/semantics summarized from cross-links |
| `EXIT_SUCCESS` / `EXIT_FAILURE` | macros in `<cstdlib>` | documented | cppreference `utility/program/EXIT_success` pages |
| `::popen` / `::pclose` (POSIX from C++) | `FILE *popen(const char *command, const char *mode);` `int pclose(FILE *stream);` | documented | POSIX `popen`; man 3 popen |
| `fork`/`exec`/`wait`/`posix_spawn`/`kill`/`waitpid` (POSIX from C++) | signatures as in [c.md](./c.md) ledger | documented | POSIX.1-2017; man-pages (see c.md) |
| C++ standard process facility | none exists (no `std::process`) | documented | absence per cppreference standard-library index |

Counts: **22** inventoried · **21** documented · **1** source-limited ·
**0** remaining.

---

## Related Topics

- Language siblings: [C](./c.md) · [Rust](./rust.md) · [Go](./go.md)
- Exit status: [Lifecycle](../exit-status/lifecycle.md) ·
  [Conventions (0, 128+N, 134, 139, 143)](../exit-status/conventions.md)
- Signals: [Standard signals](../signals/standard-signals.md) ·
  [Async-signal-safety](../interfaces/async-signal-safety.md) ·
  [sigaction/signal](../interfaces/sigaction-signal.md) ·
  [signal masks](../interfaces/signal-masks.md)
- Existing book pages: [signals overview](../../../linux/sysprog/signals.md) ·
  [process control](../../../linux/sysprog/process-control.md) ·
  [C++ deep dive](../../../dsa/chapters/ch90-cpp-deep-dive.md)
- Containers: [PID 1 and signals](../containers/pid1-signals.md)

## References

- cppreference C++ reference (community mirror of the ISO C++ standard —
  stated as such; retrieved 2026-10):
  https://en.cppreference.com/w/cpp/utility/program/exit,
  https://en.cppreference.com/w/cpp/utility/program/_Exit,
  https://en.cppreference.com/w/cpp/utility/program/quick_exit,
  https://en.cppreference.com/w/cpp/utility/program/abort,
  https://en.cppreference.com/w/cpp/utility/program/atexit,
  https://en.cppreference.com/w/cpp/utility/program/at_quick_exit,
  https://en.cppreference.com/w/cpp/utility/program/system,
  https://en.cppreference.com/w/cpp/error/terminate,
  https://en.cppreference.com/w/cpp/error/set_terminate,
  https://en.cppreference.com/w/cpp/error/unexpected,
  https://en.cppreference.com/w/cpp/thread/thread/~thread
- ISO C++ standard clause names used: [basic.start.main],
  [basic.start.term], [except.terminate], [support.start.term] (as organized
  by cppreference).
- POSIX.1-2017: `system`, `popen`, `wait`, `_Exit` —
  https://pubs.opengroup.org/onlinepubs/9699919799/
- Linux man-pages: exit(3), abort(3), popen(3), wait(2), signal-safety(7) —
  https://man7.org/linux/man-pages/
- C11 draft N1570 §7.14.1.1 (signal handler rules inherited by C++) —
  https://port70.net/~nsz/c/c11/n1570.html
