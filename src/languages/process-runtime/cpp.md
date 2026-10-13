# C++: Language Semantics, Standard Library, Process APIs, and Subprocesses

C++ inherits C's process model whole — the same `exit` family, the same
signal machinery, the same `fork`/`exec`/wait-status substrate — and then
layers on top of it the two mechanisms that change everything about process
lifecycle: **destructors** (RAII) and **stack unwinding** (exceptions). Every
question this part asks — *what runs when the process dies?* — therefore has
a C++-specific answer that C's answer does not predict: `std::exit` runs
destructors for objects it never saw declared, exceptions escape `main` into
`std::terminate`, and a `std::thread` destroyed while joinable kills the
whole process. This chapter documents those answers over the six mandatory
areas, with every claim labeled by layer: **[ISO C++]** (the ISO C++ standard),
**[POSIX]**, **[glibc-libstdc++]**, **[Linux]**.

**Declared scope** (all sources retrieved 2026-10-13):

- **ISO C++23** (ISO/IEC 14882:2024), verified against the Committee Draft
  **N4950** (open-std.org) — the C++23 DIS text. C++26 deltas were checked
  against the current working draft at **eel.is/c++draft** (generated
  2026-08-23) and are flagged where they touch in-scope wording.
- **en.cppreference.com** (the signature reference of record for this part)
  was **Cloudflare-blocked from this environment at retrieval time**; every
  signature below was therefore transcribed directly from the standard
  drafts named above (N4950 / eel.is anchors), which is the stronger source.
  The affected ledger rows record this substitution in
  [ledger-cpp.md](./ledger-cpp.md).
- **libstdc++/GCC substrate**: GCC **14.2.0** (Debian) installed headers were
  inspected for the implementation layer (`<cstdlib>`, `<stop_token>`);
  glibc current stable **2.44** per sourceware.org/glibc (released
  2026-07-25). The glibc manual (gnu.org) was unreachable in this
  environment — the same limitation recorded in [./c.md](./c.md).
- **POSIX.1-2024** (IEEE Std 1003.1-2024, Issue 8) via
  pubs.opengroup.org/onlinepubs/9799919799 and **man-pages 6.19**
  (man7.org, dated 2026-06-05) for the OS layer that C++ programs call
  directly when the standard library stops.

The **exit/signal slice** of C++ — `main` return versus `std::exit`, the
cleanup table, signal-handler basics, `std::system` — already has a dedicated
chapter in the Linux part:
[../../linux/process-exit-signal/languages/cpp.md](../../linux/process-exit-signal/languages/cpp.md).
That chapter and this one do not contradict: this chapter uses the C++23
baseline (that one cites cppreference-organized clause names), goes deeper on
*why* each termination path skips or runs destructors, and extends into
subprocesses and concurrency. The C substrate is
[./c.md](./c.md) — this chapter only repeats what C++ **changes or adds**.
Sibling Section-G chapters: [./c.md](./c.md), [./rust.md](./rust.md); part
hub: [./index.md](./index.md). Interview-topic companions:
[../cpp/modern-cpp.md](../cpp/modern-cpp.md),
[../cpp/concurrency.md](../cpp/concurrency.md),
[../cpp/stl.md](../cpp/stl.md).

---

## 1. Syntax and Semantics

### 1.1 `main`: the one function the standard owns

**[ISO C++]** (N4950 §6.9.3.1, `[basic.start.main]`):

- A hosted program shall contain **exactly one** function called `main`,
  belonging to the **global scope**. Executing the program starts a *main
  thread of execution* in which `main` is invoked.
- It shall not be named by an expression; its linkage is
  implementation-defined; declaring it `deleted`, `inline`, `static`,
  `constexpr`, or `consteval` is ill-formed; it shall not be a coroutine.
  (Unlike C, C++ also forbids `main`'s recursion *by name* — "the function
  main shall not be named by an expression" — and gives `main` C++ language
  linkage.)
- The two portable forms are unchanged from C:
  `int main() { }` and `int main(int argc, char* argv[]) { }`; `argc` is
  non-negative, `argv[argc]` is `0`, and any further optional parameters
  should be added after `argv` (recommended practice only).
- **Return semantics**: a `return` statement in `main` has the effect of
  leaving `main` (destroying its automatic objects) *and then* calling
  `std::exit` with the returned value. If control flows off the end of
  `main`, the effect is `return 0;`. This is the load-bearing asymmetry with
  C: in C++ the *destructors of `main`'s automatic objects run before*
  `std::exit`, on every `return` path — but **not** when the code calls
  `std::exit` directly (§3.2).
- Calling `std::exit` during the destruction of an object with static or
  thread storage duration is **undefined behavior**
  (`[ub:basic.start.main.exit.during.destruction]` in the C++26 working
  draft's UB annex ordering).

```cpp
#include <cstdio>

struct Guard {
    ~Guard() { std::puts("guard destroyed"); }
};

int main() {
    Guard g;
    std::puts("body");
    return 0;
}
/* Expected output (in this order):
   body
   guard destroyed        <- main's automatic object, BEFORE exit machinery
   exit status 0
   Contrast: calling std::exit(0) after "body" would print ONLY "body" —
   the Guard destructor is skipped (§3.2). */
```

### 1.2 Storage duration — the lifetime rule that decides what exit destroys

**[ISO C++]** (N4950 §6.8.6, `[basic.stc]`) defines four storage durations,
and §3 of this chapter is essentially their interaction with termination:

| Duration | Declared by | Lifetime ends | Destroyed by `std::exit`? |
|---|---|---|---|
| **static** | namespace-scope objects; `static`/`extern` block-scope objects; class static data members | end of program | **yes** (after current thread's thread-duration objects) |
| **thread** | `thread_local` | end of the declaring thread | **yes**, for the objects of the *calling* thread only |
| **automatic** | block-scope non-`static`, function parameters | end of scope | **no** — never |
| **dynamic** | `new`/`delete` (or allocator-managed) | `delete` expression | **no** — leaked ( reclaimed by the OS at process death) |

Two lifetime facts C programmers never see:

1. **Dynamic initialization is deferred and ordered by rule**
   (`[basic.start.dynamic]`): dynamic initialization of a non-block variable
   with static storage duration is **ordered** if its definition is
   appearance-ordered before another's *in the same translation unit*,
   **partially-ordered** (inline variables), or **unordered** (across
   translation units / template specializations) — unordered initializations
   are **indeterminately sequenced** relative to each other. It is also
   *implementation-defined* whether dynamic initialization of a non-inline
   variable happens before the first statement of `main`.
2. **Block-scope statics initialize on first pass** (`[stmt.dcl]`): a
   function-local `static` (or `thread_local`) is initialized the first time
   control passes through its declaration; if the initializer throws, the
   initialization is retried next entry; and "if control enters the
   declaration concurrently while the variable is being initialized, the
   concurrent execution shall wait for completion" — **magic statics**, the
   C++11 guarantee (verified in N4950, §8.4).

### 1.3 The static initialization order fiasco — and its standard cure

Cross-translation-unit dynamic initialization is **indeterminately
sequenced**: `A.cpp` defines `Config g_cfg{/*...*/}` and `B.cpp` defines
`Logger g_log{g_cfg.tag()}` — whether `g_cfg` is constructed before `g_log`
is unspecified. Reading a not-yet-initialized object with static storage
duration is undefined behavior (before C++23's constant-initialization
rescue, which only helps if the initializer is a constant expression). The
standard-shaped cure is the **construct-on-first-use idiom** — a
function-local static, whose ordering is defined (first use) *and* whose
initialization is thread-safe (§1.2 item 2):

```cpp
// config.h / config.cpp — replace a namespace-scope global with a local static
Config& config() {
    static Config instance{/*...*/};   // initialized on first call, thread-safe
    return instance;
}
/* Expected: the first call constructs exactly once even under concurrent
   calls from multiple std::threads; later calls see the completed object.
   Remaining hazard: the object is destroyed at exit in reverse construction
   order — a destructor running later must not call config() again (§3.7). */
```

### 1.4 RAII and the special member functions

**[ISO C++]** RAII is not a library feature; it is the composition of three
rules: (a) automatic-storage objects are destroyed when scope exits,
(b) destruction is **deterministic and reverse-of-construction** within a
scope, (c) destructors may run *without* the scope exiting normally — via
exception propagation. The standard-library types that guard process
resources (`std::thread`, `std::jthread`, `std::lock_guard`,
`std::unique_lock`, `std::future`, stream buffers) are RAII types whose
destructors are where the process-level semantics live (§6).

The contract every RAII type owes the termination paths: a destructor must
not let an exception escape (§1.5), must not block indefinitely on
resources that may already be gone at exit time (§3.7), and must assume
nothing about other static objects' lifetime once `std::exit` is running
(`[basic.start.term]`'s UB rules, §1.6).

### 1.5 Exceptions: throw, stack unwinding, `noexcept`

**[ISO C++]** (N4950 §14.3 `[except.throw]`): throwing an exception
*completes evaluation of the throw-expression*, then transfers control to
the nearest matching handler by **stack unwinding** — "the destructor is
invoked for each automatic object with automatic storage duration
constructed since the try-block was entered... Each object with automatic
storage duration is destroyed if it has been completely constructed or
partially constructed (subobjects destroyed in reverse order of their
construction)". Temporaries are destroyed as unwinding passes them.

Destructors during unwinding (N4950 §14.3, `[except.ctor]` + Note 5):
"If a destructor directly invoked by stack unwinding exits via an exception,
**std::terminate is invoked**" — and this is trigger (1.4) of
`[except.terminate]` (§3.6). The pattern rule: destructors may throw only if
nothing is currently unwinding; the only portable way to know is
`std::uncaught_exceptions()` (the C++17 count-returning form).

**`noexcept`** (N4950 §14.5 `[except.spec]`): a function with a
non-throwing exception specification that lets an exception try to leave —
trigger (1.3): "when the search for a handler encounters the outermost
block of a function with a non-throwing exception specification" — calls
`std::terminate`. Unwinding behavior in that situation is
**implementation-defined**: "it is implementation-defined whether the stack
is unwound, unwound partially, or not unwound at all" before `terminate`.
This is why `std::thread`'s constructor, `std::mutex::lock`, and the
termination family are declared `noexcept` — and why user RAII destructors
(implicitly `noexcept(true)`) turn any thrown cleanup error into
`std::terminate` instead of a handled failure.

**Exceptions escaping `main`** are just the no-handler case (trigger 1.2):
the mechanism searches, finds nothing (assuming no enclosing `try`), and
calls `std::terminate` — *before* `std::exit` is ever considered. An
uncaught exception therefore does **not** run `atexit` handlers, does not
flush streams through `exit` machinery, and produces an
implementation-defined status. Wrap `main`'s body in a `try`/`catch` (or
translate exceptions to exit codes) if that is not the intent:

```cpp
#include <cstdio>
#include <stdexcept>

static int run(int argc, char** argv);   // may throw

int main(int argc, char* argv[]) {
    try {
        return run(argc, argv);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "fatal: %s\n", e.what());
        return 2;                        // conventional failure code, your choice
    }
    /* Expected: any exception derived from std::exception becomes status 2
       with a one-line diagnostic instead of std::terminate/abort. */
}
```

### 1.6 Normal vs. exceptional termination — the C++ vocabulary

**[ISO C++]** classifies: *normal* termination is returning from `main`,
`std::exit`, `std::quick_exit`, `std::_Exit`; *abnormal* is `std::abort`
and everything that routes through `std::terminate` (which by default calls
`abort`). Signal death from an external signal is not a language category
at all (§4). **[POSIX]** adds the parent-side classes `WIFEXITED` /
`WIFSIGNALED` / `WIFSTOPPED` (see [./c.md](./c.md) §3.5 for the wait-status
word). The full cleanup-per-path matrix is §3.8; the one-line summary is:
**only `return` from `main` runs automatic-object destructors; only
`return`/`std::exit` run static-object destructors, `atexit` handlers, and
stream flushing; `std::quick_exit`, `std::_Exit`, `std::abort`, and
`std::terminate` run none of the above** (with the narrow exceptions their
own clauses specify).

### 1.7 Undefined / unspecified / implementation-defined behavior in scope

Not a full UB catalog (see [../cpp/modern-cpp.md](../cpp/modern-cpp.md) for
the language-wide survey) — the rows that decide process behavior:

| Behavior | Status | Anchor (N4950) |
|---|---|---|
| Calling `std::exit` during destruction of a static/thread object | **UB** | `[basic.start.main]` / working-draft UB list |
| Re-entering a function whose block-scope static (or thread) object was already destroyed, during static destruction | **UB** if control passes through the declaration | `[basic.start.term]`p4 |
| Using a standard-library object/function in a way that races destruction of static objects at exit | **UB** (does not *happen before* destruction completion) | `[basic.start.term]`p6 + Note 3 |
| Signal handler includes a non-signal-safe evaluation | **UB** | `[support.signal]`p3 (§4.2) |
| Data race between threads (non-atomic, unsynchronized) | **UB** | `[intro.races]` |
| Whether `atexit` called without happening-before `exit` succeeds | *unspecified* | `[support.start.term]`p6 |
| Whether `at_quick_exit` called without happening-before all `quick_exit`s succeeds | *unspecified* | `[support.start.term]`p10 |
| Unwinding before `std::terminate` (no-handler / `noexcept` cases) | *implementation-defined* (may be partial or absent) | `[except.terminate]`p2 |
| Status value the host environment receives (`0`/`EXIT_SUCCESS`/`EXIT_FAILURE`/other) | *implementation-defined* | `[support.start.term]`p9(9.3) |
| Whether dynamic initialization of a non-inline static object completes before `main`'s first statement | *implementation-defined* (deferred init allowed) | `[basic.start.dynamic]`p3 |
| Whether streams are flushed/closed by `_Exit`/`abort` | *implementation-defined* (per ISO C semantics these functions adopt) | `[support.start.term]`p3/p5; C17 §7.22.4.4/7.22.4.1 |
| `main`'s linkage | *implementation-defined* | `[basic.start.main]`p3 |
| Whether a freestanding environment requires `main` | *implementation-defined* | `[basic.start.main]`p1 |

### 1.8 Version deltas that change in-scope semantics (C++11 → C++23)

| Version | Delta in scope | Anchor |
|---|---|---|
| **C++11** | `thread_local` storage duration; `std::quick_exit`/`at_quick_exit` added; magic statics (thread-safe local-static init) become a requirement; `std::terminate` exceptions thrown from a `std::thread`'s function (previously a destructor-terminate design); `std::future`/`std::async` introduced with the blocking-future-destructor rule; `std::mutex`/RAII lock types standardized | N4950 §6.8.6.3, §17.5, §8.4, §33.4, §33.10 |
| **C++14/17** | `std::uncaught_exceptions()` (count form); `std::scoped_lock` for multi-mutex dead-lock-free acquisition; `std::shared_mutex` | N4950 §14.6.3, §33.6.5 |
| **C++20** | `std::jthread` (auto-join + stop request) and `std::stop_token`/`stop_source`/`stop_callback`; `std::atomic_ref`; free-standing `std::atomic` wait/notify | N4950 §33.4.4, §33.3 |
| **C++23** | No semantic change to the termination family (the family's `[[noreturn]]` declarations, the signal-safe-evaluation handler rules, and the exit effects sequence are stable wording in N4950); ISO/IEC 14882:2024 published | N4950 §17.5, §17.13.5 |
| **C++26 (working draft, checked)** | `[support.signal]` reorganized as a *signal-safe evaluation* list (already present in N4950); `[basic.start.main]` exit-during-destruction case promoted to named UB (`[ub:...]`); contract-violation handling gains handlers — none change the termination family's semantics | eel.is/c++draft `[support.signal]`, `[basic.start.main]` |

### 1.9 Misconceptions

- *"Throwing from a destructor is fine if someone catches it."* Only if
  nothing else is unwinding at that moment. A destructor invoked *by stack
  unwinding* that exits via an exception calls `std::terminate`
  (`[except.terminate]` (1.4)); you cannot portably detect "am I unwinding"
  except with `std::uncaught_exceptions()`.
- *"`std::exit` is a normal return from `main`."* It is the **second half**
  of returning from `main`. Calling it directly skips every automatic object
  still alive in every call frame — including `main`'s own (§3.2).
- *"`noexcept` destructors are a formality."* They are the rule that makes
  RAII compositional: all destructors are implicitly `noexcept(true)`, so a
  cleanup operation that can fail must swallow or report the error, never
  throw it across an unwinding stack (§1.5).
- *"Static objects are always initialized before `main`."* Dynamic
  initialization may be deferred past `main`'s first statement
  (implementation-defined, `[basic.start.dynamic]`p3) — visible as a
  not-yet-constructed global accessed from a pre-`main` thread or from a
  static destructor of another TU.
- *"The process exits when `main` returns, so worker threads can still be
  running."* Returning from `main` **does not wait for threads**; it calls
  `std::exit`, which runs static destruction while other threads may still
  execute — the exact race `[basic.start.term]`p6 declares UB (§3.7, §6.1).
- *"Exceptions from a signal handler can be caught."* Throwing from a signal
  handler is UB outright (`[support.signal]` (3.4)) — there is no unwinding
  machinery at signal-raise point to catch anything (§4.2).

---

## 2. Standard-Library and Runtime API Inventory

Signatures are transcribed from the C++23 draft N4950 (open-std.org) — the
`<cstdlib>` synopsis (`[cstdlib.syn]` §17.2.2), the termination functions
(`[support.start.term]` §17.5), `<exception>` (`[exception.terminate]`
§17.9.5), `<csignal>` (`[csignal.syn]` §17.13.4, `[support.signal]`
§17.13.5), `<thread>`/`<stop_token>` (§33.3–33.4), `<future>` (§33.10), and
`<mutex>` (§33.6) — all retrieved 2026-10-13. Implementation spellings in
[libc++-libstdc++] rows quote the GCC 14.2.0 headers. `noexcept`-ness is
part of the signature; note `std::exit` is **not** `noexcept`.

### 2.1 Termination and environment — `<cstdlib>`

| API | Canonical signature (N4950) | Semantics / notes | Since |
|---|---|---|---|
| `exit` | `[[noreturn]] void exit(int status);` — *not* `noexcept` | §3.2: current thread's `thread_local` dtors → static dtors + `atexit` (reverse; interleaved) → C streams flushed & closed, `tmpfile` files removed → host status. Automatic objects **not** destroyed. | C++98 (C89) |
| `_Exit` | `[[noreturn]] void _Exit(int status) noexcept;` | "terminated without executing destructors for objects of automatic, thread, or static storage duration and without calling functions passed to atexit()"; stream disposition implementation-defined (C17 §7.22.4.5). Marked **signal-safe**. | C++11 |
| `quick_exit` | `[[noreturn]] void quick_exit(int status) noexcept;` | runs only `at_quick_exit` handlers (reverse order) on the **calling thread**, destroys **no objects**, then calls `_Exit(status)`; exception in a registered handler → `std::terminate`; signal-safe iff the registered functions are. | **C++11** |
| `abort` | `[[noreturn]] void abort() noexcept;` | C semantics: raises `SIGABRT`; no destructors, no `atexit`; stream flush/close implementation-defined. Marked **signal-safe**. | C++98 |
| `atexit` | `int atexit(c-atexit-handler* f) noexcept;` / `int atexit(atexit-handler* f) noexcept;` (two overloads) | register normal-termination handler; ≥32 registrations; zero on success; called once **per registration**; unspecified to succeed unless it happens-before `exit`. | C++98 (C89) |
| `at_quick_exit` | `int at_quick_exit(c-atexit-handler* f) noexcept;` / `int at_quick_exit(atexit-handler* f) noexcept;` | same contract for the `quick_exit` list (≥32); the two lists are **distinct** (Note 5). | **C++11** |
| `EXIT_SUCCESS` / `EXIT_FAILURE` | `#define EXIT_SUCCESS /* see below */` (+ `EXIT_FAILURE`) | consumed by `exit`/`_Exit`/`quick_exit`; the host-status mapping is implementation-defined (§3.4). | C++98 |
| `getenv` | `char* getenv(const char* name);` | borrowed pointer into the environment; must not be modified by the program; **"Calls to the function getenv shall not introduce a data race provided that nothing modifies the environment"** — and the note names the modifiers: *POSIX `setenv`/`putenv`* (`[support.runtime]` §17.13.1). | C++98 |
| `system` | `int system(const char* string);` | implementation-defined command processor; POSIX sharpens to `/bin/sh -c` + wait status (§5.1–5.2). | C++98 |

**[glibc-libstdc++]** the GCC 14.2.0 `<cstdlib>` header implements the
family as C-library calls with C++ linkage, e.g.
`extern "C" void quick_exit(int) _GLIBCXX_NOTHROW _GLIBCXX_NORETURN;` and
`extern "C" void _Exit(int) _GLIBCXX_NOTHROW _GLIBCXX_NORETURN;` — the
`_GLIBCXX_NOTHROW` spelling is the C++ `noexcept` contract over the C
function. glibc's `exit(3)` runs `atexit` **and** `on_exit` handlers in
reverse registration order and drops both lists across `execve(2)`
(man7 exit(3); details in [./c.md](./c.md) §2.1/§3.4).

### 2.2 Termination machinery — `<exception>`

| API | Canonical signature (N4950 §17.9.5) | Semantics / notes | Since |
|---|---|---|---|
| `std::terminate` | `[[noreturn]] void terminate() noexcept;` | enters the current terminate handler; **must not return**; unwinding behavior depends on the trigger situation (§3.6). | C++98 |
| `terminate_handler` | `using terminate_handler = void(*)();` | required behavior: terminate execution without returning to the caller; **default behavior: the implementation's default terminate_handler calls `abort()`**. | C++98 |
| `set_terminate` | `terminate_handler set_terminate(terminate_handler f) noexcept;` | install handler; returns the previous one; it is unspecified whether a null pointer designates the default handler. | C++98 |
| `get_terminate` | `terminate_handler get_terminate() noexcept;` | current handler; may be a null pointer value (Note). | **C++11** |

### 2.3 Signals — `<csignal>`

| API | Canonical signature (N4950 §17.13.4) | Semantics / notes | Since |
|---|---|---|---|
| `signal` | `signal-handler* signal(int sig, signal-handler* func);` with `extern "C" using signal-handler = void(int);` (exposition-only name) | install `SIG_DFL`/`SIG_IGN`/handler; "a call to the function signal synchronizes with any resulting invocation of the signal handler so installed"; **signal-safe** when invoked from a handler with the same `sig` (§4.2). Contents of `<csignal>` are the same as C `<signal.h>`. | C++98 (C89) |
| `raise` | `int raise(int sig);` | send to the executing program/thread; runs the handler synchronously. | C++98 |
| `sig_atomic_t` | `using sig_atomic_t = /* see below */;` | integer type accessed atomically; the `volatile std::sig_atomic_t` carve-out in the data-race rules (§4.3). | C++98 |

That is the **complete** C++-standard signal surface: the standard adds *no*
signal-handling API of its own beyond inheriting C's (§4.1). Everything
else — `sigaction`, masks, `sigwait`, `signalfd` — is the POSIX layer used
from C++ (§4.4).

### 2.4 Threads and stop tokens — `<thread>` / `<stop_token>`

| API | Canonical signature (N4950 §33.3–33.4) | Semantics / notes | Since |
|---|---|---|---|
| `std::thread` | `class thread;` ctor `template<class F, class... Args> explicit thread(F&& f, Args&&... args);` | new thread of execution running `invoke(f, args...)`; **"if the invocation of invoke terminates with an uncaught exception, terminate is invoked"** (`[thread.thread.constr]`). | **C++11** |
| `std::thread::~thread` | `~thread();` | **"If joinable(), invokes terminate. Otherwise, has no effects."** (`[thread.thread.destr]`) — the joinable-destructor rule (§6.2). | C++11 |
| `thread::join` / `detach` / `joinable` | `void join();` `void detach();` `bool joinable() const noexcept;` | join: block until the thread completes, then release state; error conditions include `no_such_process`, `invalid_argument` (not joinable). detach: release without waiting. | C++11 |
| `thread::hardware_concurrency` | `static unsigned int hardware_concurrency() noexcept;` | hint: number of concurrent threads supported; may return 0. | C++11 |
| `std::jthread` | `class jthread;` with `stop_source get_stop_source() noexcept;` `stop_token get_stop_token() const noexcept;` `bool request_stop() noexcept;` | "the same as class thread with the additional abilities to provide a stop_token to the new thread of execution, make stop requests, and **automatically join**" (`[thread.jthread.class]`). | **C++20** |
| `std::stop_token` | `bool stop_requested() const noexcept;` `bool stop_possible() const noexcept;` | shared-ownership handle on a stop state; the query side of cooperative cancellation. | **C++20** |
| `std::stop_source` | `bool request_stop() noexcept;` `stop_token get_token() const noexcept;` `bool stop_requested() const noexcept;` | request side; first `request_stop()` wins, associated callbacks fire. | **C++20** |
| `std::stop_callback` | `template<class C> class stop_callback;` with `template<class C> stop_callback(stop_token, C&&);` | RAII callback registration; invoked on first stop request by any associated source. | **C++20** |

### 2.5 Async and futures — `<future>`

| API | Canonical signature (N4950 §33.10) | Semantics / notes | Since |
|---|---|---|---|
| `std::async` | `template<class F, class... Args> future<invoke_result_t<decay_t<F>, decay_t<Args>...>> async(launch policy, F&& f, Args&&... args);` (+ overload without `policy`) | creates a shared state and launches: `launch::async` → new thread; `launch::deferred` → stored, run lazily in the thread calling `get`/`wait`; **no policy** (or `async\|deferred`) → implementation chooses (§6.5). | **C++11** |
| `std::future` | `R future::get();` `void wait() const;` `template<class Rep, class Period> future_status wait_for(...) const;` `wait_until(...)` `~future();` | `get`: return the stored value or **rethrow the stored exception**; `valid()==false` afterwards. The destructor releases the shared state; **for a state created by `async` with `launch::async`, the last future "shall block until the associated thread has completed, as if joined"** (`[futures.async]`). | **C++11** |
| `std::shared_future` | `shared_future<R>(future<R>&&);` | many-consumer view; `get()` may be called repeatedly; no blocking-destructor rule beyond releasing the last reference. | C++11 |

### 2.6 Mutual exclusion — `<mutex>`

| API | Canonical signature (N4950 §33.6) | Semantics / notes | Since |
|---|---|---|---|
| `std::mutex` | `void lock();` `bool try_lock() noexcept;` `void unlock();` `using native_handle_type = /* implementation-defined */;` | blocking exclusive ownership; `lock` may throw `system_error` (deadlock may surface as `resource_deadlock_would_occur` — "might be observed", not guaranteed); not recursive (recursive lock by the owner is UB). | **C++11** |
| `std::lock_guard` | `explicit lock_guard(mutex_type& m);` `lock_guard(mutex_type& m, adopt_lock_t);` (copy deleted) | strictly scoped RAII lock: `m.lock()` in the constructor, `m.unlock()` in the destructor; zero overhead, no unlock() path. | C++11 |
| `std::unique_lock` | `unique_lock() noexcept;` `explicit unique_lock(mutex_type& m);` `unique_lock(mutex_type& m, defer_lock_t) noexcept;` `unique_lock(mutex_type& m, try_to_lock_t);` `unique_lock(mutex_type& m, adopt_lock_t);` + timed ctors | movable lock with `owns_lock()` state; the lock type required for `std::condition_variable` waits. | C++11 |
| `std::scoped_lock` | `explicit scoped_lock(MutexTypes&... m);` `explicit scoped_lock(adopt_lock_t, MutexTypes&... m);` | acquires **several** mutexes with deadlock-avoidance (`std::lock` algorithm) in one scope-exit release. | **C++17** |

### 2.7 What the C++ standard library does **not** have

No `fork`/`exec`/`wait`/`popen`-with-fds, no `sigaction`/`sigprocmask`/
`sigwait`, no `pipe`/`dup2`/`fcntl`, no timed child-wait, no process-group
control. The standard's only process-creation primitive is `std::system`
and its only environment reader is `std::getenv`. On Linux, C++ programs
use the POSIX layer *from C++* — same headers, same C linkage — and the
C++-specific hazards are §5.5–5.9. The concurrency library stops at
threads/futures/mutexes; it has no process-level sibling.

---

## 3. Process Creation and Termination

### 3.1 Startup: the `main` → `std::exit` pipeline

1. **[ISO C++]** the implementation runs dynamic initialization of static
   objects (timing implementation-defined, §1.2), invokes `main` on the main
   thread, and treats `return v;` (or falling off the end → `return 0`) as
   *destroy `main`'s automatic objects, then call `std::exit(v)`*
   (`[basic.start.main]`p5).
2. **[POSIX]** `main` receives `argc`/`argv`/`environ` handed over by the
   loader; the runtime startup (`crt1.o`) framed the call (POSIX `exec`,
   `posix_spawn`).
3. **[glibc-libstdc++]** `std::exit` = C `exit`: `atexit`/`on_exit` lists in
   reverse order, stdio flushed and closed, `_exit` wrapper
   (man7 exit(3)).
4. **[Linux]** `_exit(2)` → `exit_group(2)` — all threads die, the parent
   gets `SIGCHLD` and the exit status (man7 _exit(2)).

```cpp
// exit vs return — the destructor asymmetry
#include <cstdio>
struct Log { ~Log() { std::puts("~Log"); } };

static void via_return() { Log l; std::puts("return path"); }
static void via_exit()   { Log l; std::puts("exit path"); std::exit(0); }

int main(int argc, char**) {
    if (argc > 1) via_exit(); else via_return();
}
/* Expected: "./a.out"        → "return path", "~Log"  (dtor ran)
             "./a.out x"      → "exit path"           (dtor skipped)
   exit status 0 in both cases. */
```

### 3.2 `std::exit`: the exact sequence, and why automatic objects die silently

**[ISO C++]** (`[support.start.term]`p9, quoted effects):

1. **(9.1)** First, objects with **thread storage duration associated with
   the current thread** are destroyed. Next, objects with **static storage
   duration are destroyed** and functions registered by `atexit` are called
   (order per `[basic.start.term]`, §3.5). *"(Objects with automatic storage
   duration are not destroyed as a result of calling exit())"* — and a
   registered function that **exits via an exception** calls
   `std::terminate` (§3.5).
2. **(9.2)** Next, **all open C streams with unwritten buffered data are
   flushed, all open C streams are closed**, and files created by `tmpfile`
   are removed.
3. **(9.3)** Finally, control returns to the host: `0`/`EXIT_SUCCESS` →
   implementation-defined successful status; `EXIT_FAILURE` →
   implementation-defined unsuccessful; otherwise implementation-defined.

**Why automatic objects are not destroyed — the mechanistic answer.**
Stack unwinding is a **per-thread, per-stack** protocol: it walks the
*calling thread's* call frames, executing cleanup code compiled into each
frame's landing pad, and it is driven by the exception machinery of that
thread's own execution. At `std::exit` time the standard faces a thread
calling `exit` from *anywhere* in any call stack — possibly while other
threads are mid-unwind — and there is no language-defined way to re-enter
the unwinding protocol of a different thread's stack, or to "unwind" frames
without the exception flow the protocol is defined around. The designers'
choice: `exit` destroys what has an *implementation-defined manageable
registry* (static/thread-duration objects, whose destruction order the
standard specifies) and simply does not touch automatic storage. That is
also why `atexit` handlers run **on the thread that called `exit`**, while
other threads may still be running concurrently — the standard's own
defense is the happens-before UB rule of `[basic.start.term]`p6 (§3.7).
This is exactly the same gap C has; C++ only adds more code (destructors)
in the blast radius. Returning from `main` is the only path where
automatic objects of one frame (`main`'s) are destroyed *and* the exit
sequence follows.

### 3.3 `atexit` / `at_quick_exit`: registration contracts

- Reverse-order invocation; a function registered *n* times runs *n* times
  (N4950 footnote to `[support.start.term]`p9: "A function is called for
  every time it is registered"). A handler that registers another handler
  runs before handlers registered earlier than its own registration —
  LIFO to the end.
- Concurrency: "It is unspecified whether a call to `atexit()` that does
  not happen before a call to `exit()` will succeed" — register everything
  before threads that might exit, or serialize yourself. The same clause
  exists for `at_quick_exit` (with the stronger form: happens-before *all*
  `quick_exit` calls).
- **Exception in a handler → `std::terminate`** (trigger (1.7)). A handler
  must not throw; there is no unwinding to catch it.
- The `atexit` and `at_quick_exit` lists are distinct (Note 5); a library
  that wants cleanup under both `exit` and `quick_exit` registers with
  both.
- **[glibc]** ≥32 is the standard minimum; glibc dynamically grows the
  list (man7 exit(3)) — and `execve(2)` clears all registrations (§5.5).

```cpp
#include <cstdio>
#include <cstdlib>

static void a() { std::puts("a"); }
static void b() { std::puts("b"); }

int main() {
    std::atexit(a);
    std::atexit(b);
    std::atexit(a);            // registered twice: runs twice, innermost first
    std::at_quick_exit(a);
    std::quick_exit(0);        // runs ONLY the quick_exit list
}
/* Expected output: "a" (from at_quick_exit), exit status 0.
   The atexit list (a,b,a) is never invoked on the quick_exit path. */
```

### 3.4 `std::quick_exit` and `std::_Exit`: the no-destructor paths

- `quick_exit(status)`: calls the `at_quick_exit` handlers **on the thread
  that called `quick_exit`** — which can be any thread, so "registered
  functions cannot rely on the identity of objects with thread storage
  duration" (N4950 Note 6) — destroys **no objects**, then calls
  `_Exit(status)`. It is *signal-safe iff* the registered functions are.
  Use case: a library that must not execute someone else's `atexit`
  cleanup (or risk deadlocking on a mutex held by a thread that no longer
  exists) still gets its own teardown, then an immediate `_Exit`.
- `_Exit(status)`: nothing runs — no destructors of any storage duration,
  no `atexit`/`at_quick_exit`, stream flush/close
  implementation-defined. **[POSIX]** the paired `_exit(2)` *shall not*
  flush open streams (POSIX `_Exit`/`_exit` page); `_Exit` and `_exit` are
  functionally equivalent on POSIX systems. The child-side pattern is
  §5.6: **fork-exec children that fail to exec must `_exit`, never
  `exit`**.
- Exit status reaches the parent through the OS: **[POSIX]** the value is
  truncated to the **low 8 bits** for `wait()`/`waitpid()` observers
  (`status & 0377`); the full value is available from `waitid()` and the
  `SIGCHLD` `siginfo_t`. `exit(256)` reports as `0`; `exit(-1)` as `255`
  (POSIX `_Exit`; man7 wait(2) `WEXITSTATUS`).

### 3.5 Static-object destruction at exit: order rules and the UB edges

**[ISO C++]** (`[basic.start.term]`):

- `std::exit` is *sequenced before* the destructions it triggers; returning
  from `main` invokes `std::exit` (p1).
- **Order**: if the completion of construction (or dynamic initialization)
  of static object A *strongly happens before* that of B, then B's
  destructor is sequenced **before** A's — destruction is the reverse of
  construction completion, per translation unit for ordered
  initializations; statically (constantly) initialized objects are
  destroyed *as if* they had been dynamically initialized first
  (p3).
- **`thread_local` first**: objects with thread storage duration of a given
  thread are destroyed when the thread's initial function returns **or**
  when that thread calls `std::exit`; that destruction *strongly happens
  before* any static-duration destruction (p2). So at exit, the exiting
  thread's `thread_local`s go first, then statics.
- **Interleaving with `atexit`**: an `atexit` call that happens after an
  object's construction runs *before* that object's destructor; an
  `atexit` call that happens before an object's initialization runs after
  the destructor (p5) — one LIFO list weaving objects and handlers.
- **UB edge 1** (p4): a function whose block-scope static/thread object was
  already destroyed, called *during* static destruction, and flowing
  through the declaration again → **undefined behavior** (the construct-on-
  first-use idiom of §1.3 has a destruct-order shadow).
- **UB edge 2** (p6 + Note 3): using a standard-library object or function
  in a way that does not *happen before* the completion of static
  destruction → **UB**. Note 3 is explicit about the fix: "Terminating
  every thread before a call to `std::exit` or the exit from main is
  sufficient, but not necessary" — join your threads, then exit.
- Destruction of a static/thread object **exits via an exception** →
  `std::terminate` (trigger (1.6)).

### 3.6 `std::terminate`: every trigger, and what unwinds

**[ISO C++]** `[except.terminate]` (N4950 §14.6.2) — the note enumerates the
situations that invoke `std::terminate`; the in-scope ones:

1. (1.2) the exception-handling mechanism **cannot find a handler** for a
   thrown exception (includes exceptions escaping `main`);
2. (1.3) the handler search encounters the outermost block of a
   **`noexcept`** function (the noexcept-violation case);
3. (1.4) **destruction of an object during stack unwinding** exits by
   throwing;
4. (1.5) **initialization** of a non-block variable with static or thread
   storage duration exits via an exception;
5. (1.6) **destruction** of a static/thread object exits via an exception;
6. (1.7) execution of a function registered with `std::atexit` or
   `std::at_quick_exit` exits via an exception;
7. (1.8) a re-throw (`throw;`) with no exception being handled;
8. (1.10) **the initial function of a `std::thread` exits via an
   exception** (§6.1);
9. (1.12) the destructor or move-assignment of a `std::thread` referring to
   a **joinable** thread (§6.2);
10. (1.13) a `wait`/`wait_until`/`wait_for` on a condition variable fails
    to meet a postcondition.

And the unwind rules per situation (p2): with **no matching handler** it is
*implementation-defined* whether the stack is unwound before `terminate`;
same implementation-defined latitude (possibly *partial* unwinding) for the
`noexcept` case; **in all other situations the stack shall NOT be unwound**
before `terminate`. A `terminate_handler` must terminate without returning;
the **default handler calls `abort()`** — which is why an uncaught
exception surfaces to the OS as SIGABRT death (often with a core dump)
rather than as an "exception" exit code, and why the default status for
this path is the implementation's abort status (134 in shell arithmetic on
Linux, i.e. 128+SIGABRT — a *platform* observation, not a standard
guarantee; see
[../../linux/process-exit-signal/languages/cpp.md](../../linux/process-exit-signal/languages/cpp.md)
§3.3).

```cpp
#include <cstdio>
#include <exception>

int main() {
    std::set_terminate([]() noexcept {
        std::fprintf(stderr, "custom terminate handler\n");
        std::abort();                       // must not return
    });
    throw 42;                               // no handler anywhere
}
/* Expected: "custom terminate handler" on stderr, then the process dies
   by SIGABRT (status 134 via a shell; WIFSIGNALED + WTERMSIG=SIGABRT
   via wait). No unwinding is required before the handler runs. */
```

### 3.7 Threads + exit: the race the standard names, the hazard libstdc++ shares

The three-way interaction to design around:

- **`std::exit` from any thread is legal and terminates the process** —
  the exit sequence runs *on the calling thread*: its `thread_local`s, then
  statics, then streams. Other threads keep running through the teardown.
  Any library object they touch may be mid-destruction → `[basic.start.term]`p6
  UB. The Note's advice is the design rule: **join every thread you own
  before any thread exits the process** (or before `main` returns).
- **`std::thread` + `std::exit`'s sibling hazard**: a joinable `std::thread`
  whose destructor runs — e.g. an automatic `thread` object in a frame
  that a `return` from `main` just unwound — calls `std::terminate`
  (§6.2). "Exit while workers run" can therefore become *abnormal*
  termination instead of graceful exit, purely by object layout.
- **`atexit`-handler deadlock**: a static object's destructor or `atexit`
  handler that waits on a mutex held by an already-dead (or never-joined)
  thread blocks `exit` forever — thread death releases no locks (POSIX
  `pthread_exit`; same shape as [./c.md](./c.md) §6.5).

### 3.8 Consolidated: what runs on each termination path

| Termination path | automatic dtors (any frame) | current-thread `thread_local` dtors | static dtors + `atexit` | `at_quick_exit` | C streams flushed | Status to host | Mechanism [glibc]/[Linux] |
|---|---|---|---|---|---|---|---|
| `return v;` from `main` | **main's only** | no (main's own, if any — yes) | yes | no | yes | `v` (8-bit truncation) | `exit(v)` → `exit_group(2)` |
| `std::exit(v)` from any thread | no | **yes (calling thread)** | yes | no | yes | `v` | same |
| `std::quick_exit(v)` | no | no | no | **yes** | no | `v` (via `_Exit`) | `at_quick_exit` list → `_Exit` → `exit_group(2)` |
| `std::_Exit(v)` / `_exit(v)` | no | no | no | no | impl-defined / **no** (`_exit`) | `v` | `exit_group(2)` directly |
| `std::abort()` | no | no | no | no | impl-defined (glibc: no) | SIGABRT death | `raise(SIGABRT)` (+ core per RLIMIT_CORE) |
| uncaught exception → `terminate` → default handler → `abort` | impl-defined unwind first (no-handler case) | no | no | no | impl-defined | SIGABRT death | as above |
| death by external signal (SIGINT/SIGTERM/…) | no | no | no | no | no | `WIFSIGNALED` | kernel default action |

(`thread_local` dtors of *other* threads run when those threads exit, not
at process exit. `main`'s `thread_local` objects are destroyed by the
p2 rule on the exit path.)

### 3.9 Process vs. thread vs. child

- **Process** — `return`/`std::exit`/`std::quick_exit`/`std::_Exit`/
  `std::abort`/`std::terminate`-via-abort terminate it, **from any
  thread**; **[Linux]** the mechanism is always `exit_group(2)` for the
  exit family (all threads die).
- **Thread** — `std::thread`/`std::jthread` end when the function returns
  or is joined; a thread cannot "exit the process" without one of the
  functions above. POSIX `pthread_exit` exists for the C layer and
  terminates *only* the calling thread — **[glibc-libstdc++]** calling
  `pthread_exit` (or `glibc`'s internal equivalent) from a C++ thread
  frame skips C++ destructors: it is a stack-teardown, not unwinding.
  Do not mix; use thread-function returns.
- **Child** — created by the OS layer (§5); its status is only observable
  after reaping; C++ has no `std::child` type — you own the `pid_t` and
  the wait, so wrap it in RAII (§5.5, §6.7).

---

## 4. Signals and OS Interaction

### 4.1 The layering: the C++ standard adds nothing to C's signal surface

**[ISO C++]** the entire standard signal API is `<csignal>`, whose contents
are "the same as the C standard library header `<signal.h>`"
(N4950 §17.13.4): `std::signal`, `std::raise`, `std::sig_atomic_t`, the
`SIG*` macros. There is no C++ mask API, no queueing, no sigwait, no
per-thread delivery rules — **[ISO C++]** does not even define what a
signal does to threads. Everything beyond the pair of functions is the
**[POSIX]** layer used *from C++*: same function names, C linkage, same
semantics as documented in [./c.md](./c.md) §4 — `sigaction`,
`pthread_sigmask`, `sigwait`, `sigsuspend`, `kill`, `raise`'s
thread-directed behavior. Do not build a "C++ signal library" mental model;
build "C signal layer + C++ handler-language rules", which is exactly the
next two subsections.

### 4.2 What a C++ handler may evaluate: the signal-safe list

**[ISO C++]** (N4950 `[support.signal]`p3) — an evaluation is *signal-safe*
unless it includes any of:

1. a call to **any standard-library function**, except (a) *plain lock-free
   atomic operations* and (b) functions explicitly identified as
   signal-safe (`_Exit`, `quick_exit`, `abort`, and `signal(sig, …)` with
   the same `sig` are the ones this chapter uses);
2. an **access to an object with thread storage duration**;
3. a **`dynamic_cast`** expression;
4. **throwing an exception**;
5. control entering a **try-block** or function-try-block;
6. initialization of a static-storage variable requiring **dynamic
   initialization**;
7. waiting for completion of a static variable's initialization (the magic-
   statics lock).

A handler invocation containing a non-signal-safe evaluation is **UB**. The
consequences are sharper than C's list: in C++ a handler may not even
*enter a try block*, may not `dynamic_cast`, and may not touch
`thread_local` — and the Note makes explicit that `new`/`delete` through
the library allocator is excluded (no allocation). The C++-specific
victims: RAII destructors in the interrupted frame are *not* run by signal
delivery, and any handler that would "throw to unwind out of the signal"
is doubly UB — throwing is UB (rule 4) and there is no handler search
across the kernel interruption point.

### 4.3 Handler→program communication that the standard blesses

- **`volatile std::sig_atomic_t`**: the data-race rules carve out — "Two
  accesses to the same object of type `volatile std::sig_atomic_t` do not
  result in a data race if both occur in the same thread, even if one or
  more occurs in a signal handler" — with the happens-before sandwich that
  makes the flag visible to the interrupted thread (N4950, the
  `[intro.races]`/`[intro.progress]` clause family; wording quoted in the
  C23 parallel at [./c.md](./c.md) §4.4).
- **Plain lock-free atomics** (`std::atomic` members where
  `is_lock_free()`/`atomic_is_lock_free` hold — the *plain* operations
  only, no waiting/notify in a handler): defined, non-racy
  (`[support.signal]`p2).
- Everything else — `iostreams`, mutexes, allocation, `std::exit` — is UB
  (§4.2). Note `std::exit` is *not* on the safe list; the signal-safe
  terminators are `abort`/`_Exit`/`quick_exit`.
- **[POSIX]** widens the callable set to the async-signal-safe list
  (man7 signal-safety(7) — reachable and verified this session: "An
  async-signal-safe function is one that can be safely called... from a
  signal-handling function"), which is how the self-pipe trick
  (`write(2)`) works from a C++ handler.

### 4.4 POSIX layer from C++: registration, masks, delivery

The POSIX contracts are [./c.md](./c.md) §4.1–4.3 and §4.7; the C++-side
deltas are:

- **Which thread receives**: **[POSIX]** process-directed signals go to
  *any* thread not blocking them; thread-directed (`pthread_kill`,
  `raise`) go to the target. From C++ this means a handler can run on
  **any** `std::thread` — your handler's accesses must therefore obey the
  §4.2 rules *and* be correct in that thread's context. The standard
  pattern from C++: block the signal in all threads at startup
  (`pthread_sigmask` before spawning), then a dedicated `std::thread` runs
  `sigwait` in a loop — **no handler runs**, so the full C++ library is
  usable in that loop. This is the C++-idiomatic replacement for
  async-signal-safety gymnastics:

```cpp
// sigwait-thread pattern (POSIX layer used from C++)
#include <csignal>
#include <pthread.h>
#include <thread>

static void shutdown_thread() {           // runs as a std::thread function
    sigset_t set;
    sigemptyset(&set);
    sigaddset(&set, SIGINT);
    sigaddset(&set, SIGTERM);
    int sig = 0;
    for (;;) {
        if (sigwait(&set, &sig) != 0) return;   // consumes one blocked signal
        // full C++ library usable here: no handler context, no UB list
        break;                                  // demo: single-shot
    }
    /* request_shutdown(); */                   // atomics, queues, iostreams: all fine
}

static void block_signals_everywhere() {    // call before spawning threads
    sigset_t set;
    sigemptyset(&set);
    sigaddset(&set, SIGINT);
    sigaddset(&set, SIGTERM);
    pthread_sigmask(SIG_BLOCK, &set, nullptr);
}
/* Expected: SIGINT/SIGTERM never invoke a handler; the sigwait thread
   observes them synchronously and coordinates shutdown via normal C++. */
```

- **RAII does not compose with handlers**: a signal handler interrupting a
  frame with automatic objects leaves those objects alive (no unwinding);
  the §4.2 list forbids the constructs that would let cleanup run. Cleanup
  on signal death is a design decision — sigwait-thread (above),
  signalfd (**[Linux]** `signalfd(2)`: signals as a pollable fd, zero
  handler context), or the `volatile sig_atomic_t` flag checked at safe
  points — not something the exception system can provide.
- **`SIGABRT` from `std::abort`**: if a POSIX handler catches SIGABRT and
  returns, glibc restores the default disposition and re-raises (man7
  abort(3)); `std::abort` therefore cannot return regardless of handlers.

---

## 5. Subprocess and Child-Process Management

### 5.1 `std::system`: what the return value actually is

**[ISO C++]** `int system(const char* string);` — `string == nullptr`
tests for a command processor (nonzero iff present); otherwise the effect
and the return value are **implementation-defined**. **[POSIX]** fixes
every open end (POSIX `system` page, verified this session):

- the child is created and invokes the shell as
  `execl(<shell path>, "sh", "-c", "--", command, (char *)0);`
  — **[glibc]** `<shell path>` is `/bin/sh` (man7 system(3));
- the return value is the **full wait status word** of that shell — not an
  exit code. Decode it, never compare it directly:

```cpp
#include <cstdlib>
#include <cstdio>
#include <sys/wait.h>

int run(const char* cmd) {
    int status = std::system(cmd);
    if (status == -1) return 127;             // child could not be created
    if (WIFEXITED(status))  return WEXITSTATUS(status);   // 0..255
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
    return 126;                                // stopped/continued: decide policy
}
/* Expected: run("true") == 0; run("exit 3") == 3;
   run("kill -9 $$") == 137 (128+SIGKILL). The 128+N band is YOUR decoder's
   convention mirroring the shell's — the raw status word needs W* macros. */
```

- **Signal discipline while waiting** (POSIX `system`): the parent
  *ignores SIGINT and SIGQUIT* and *blocks SIGCHLD* until the command
  terminates. Consequences: your process will not die of terminal Ctrl-C
  aimed at the child's process group (and may *miss* its own fatal signal
  — hence "check the return value"), and a SIGCHLD handler elsewhere in
  your program will not see other children reaped mid-`system`.

### 5.2 Injection: the string API's permanent hazard

`std::system` interprets its argument as a *shell program*:
`std::system(("ls " + dir).c_str())` with `dir == "/; rm -rf /"` executes
two commands. Concatenating untrusted data — including filenames with
metacharacters, environment-derived strings, or user input — is command
injection. The safe path is the **argv-array** interfaces: `execv`-family
and `posix_spawn` pass arguments verbatim with no shell layer (§5.4).
Reserve `system`/`popen` for operator-supplied, trusted command lines, and
quote defensively when you must interpolate (`shlex`-style single-quoting
is *your* job; the shell sees the whole string).

### 5.3 `std::getenv`: borrowed pointer, single-threaded mutation

**[ISO C++]** `char* getenv(const char* name);` returns a pointer to the
value string; the program **must not modify it** and it "may be overwritten
by a subsequent call" to `getenv` (C17 §7.22.4.6 semantics, which the C++
clause adopts). Threading: N4950 `[support.runtime]` — calls to `getenv`
"shall not introduce a data race provided that nothing modifies the
environment", with the note naming **POSIX `setenv`/`putenv`** as the
modifiers. So: concurrent `getenv` is fine; concurrent
`getenv`+`setenv` is a data race you own — serialize environment mutation
(or restrict it to pre-thread startup). **[POSIX]** `setenv` copies,
`putenv` aliases the caller's string (ownership asymmetry documented in
[./c.md](./c.md) §2.3).

### 5.4 `popen`/`pclose` and the POSIX process trio from C++

**`<cstdio>`** `FILE* popen(const char* command, const char* mode);` /
`int pclose(FILE* stream);` — **[POSIX]**: runs `command` via the shell
with one pipe end wired to the child (`"r"`: read child's stdout; `"w"`:
write child's stdin); `pclose` waits for the shell and returns its **wait
status** (same decoding as `system`), or -1/`ECHILD` if already reaped.
**[glibc]** mode `'e'` (since glibc 2.9) sets `FD_CLOEXEC` on the
descriptor (man7 popen(3)). Both `popen` and `system` are shell-in-the-loop
APIs — the injection analysis of §5.2 applies unchanged.

**[POSIX]** from C++ (signatures verified against POSIX.1-2024 and
transcribed in [./c.md](./c.md) §5.2–5.4; repeated here because this is
the C++ chapter's OS inventory):

```cpp
#include <unistd.h>        // fork, exec*, _exit
#include <sys/wait.h>      // wait, waitpid, waitid, W* macros
#include <spawn.h>         // posix_spawn, posix_spawnp

pid_t fork(void);                                   // [POSIX] (Issue 8 adds _Fork)
int execv(const char* path, char* const argv[]);    // + execl/execle/execlp/execve/execvp/fexecve
pid_t waitpid(pid_t pid, int* stat_loc, int options);
int waitid(idtype_t idtype, id_t id, siginfo_t* infop, int options);
int posix_spawn(pid_t* pid, const char* path,
                const posix_spawn_file_actions_t* file_actions,
                const posix_spawnattr_t* attrp,
                char* const argv[], char* const envp[]);
```

### 5.5 `fork` from C++: the multithreaded hazard, exactly

**[POSIX]** in a multithreaded process the fork child holds "a replica of
the calling thread and its entire address space, possibly including the
states of mutexes", and "the application shall ensure that the child
process only executes async-signal-safe operations until such time as one
of the exec functions is successful". From C++ this bites harder:

- every `std::mutex` locked by a vanished thread stays locked in the
  child — including the allocator's internal lock, so `new`, `malloc`,
  `std::string` construction, and *any* function that might allocate are
  all potential immediate deadlocks;
- C++ destructors of the child's automatic objects *can* run (a `return`
  from the fork-child scope unwinds normally) — but any destructor that
  locks, allocates, or writes a stream may deadlock on those frozen locks;
  **the child's code between `fork` and `exec` must be C-style**:
  async-signal-safe calls only, then `exec` or `_exit`;
- unwinding across `exec` is impossible by construction: a successful
  `exec` overwrites the image; stack frames, exception state, and static
  teardown plans all vanish.

Mitigations, in order of preference: `posix_spawn` (no fork window in your
code at all), `fork` + async-signal-safe + `exec`/`_exit` discipline,
**[Linux]** `vfork`-style variants through `posix_spawn` internals
(man7 posix_spawn(3): glibc uses vfork/clone paths internally).

### 5.6 Exec-failure propagation: no exceptions across `exec`, so use 127 or a pipe

There is no return from a successful `exec`, and a *failed* `exec` returns
-1/errno in the child — which must not run the parent's cleanup. The two
documented propagation shapes:

1. **Status-convention**: child `_exit(127)` (command not found / exec
   failed) or `_exit(126)` (found, not executable) — the same values POSIX
   assigns the shell and `system`, which makes parent-side decoding
   uniform (§5.1). Caveat: 127 is *conventional*, so a parent cannot
   distinguish "exec failed" from "the program exited 127" without a
   side-channel.
2. **Side-channel byte (CLOEXEC pipe)**: `pipe2(fds, O_CLOEXEC)`
   (**[Linux]**) before `fork`; child (after `exec` succeeds) the write
   end closes automatically; parent reads: EOF = exec succeeded, one
   errno byte = exec failed. **[POSIX]**-only alternative: plain `pipe`
   + explicit `fcntl(F_SETFD, FD_CLOEXEC)`.

```cpp
// RAII child with exec-failure propagation (skeleton)
#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <sys/wait.h>
#include <fcntl.h>

struct Child {
    pid_t pid = -1;
    ~Child() {                       // ownership: kill+reap if still running
        if (pid > 0) { ::kill(pid, SIGKILL); int st; ::waitpid(pid, &st, 0); }
    }
};

static bool spawn(const char* const argv[]) {
    int errpipe[2];
    if (pipe2(errpipe, O_CLOEXEC) != 0) return false;   // [Linux] O_CLOEXEC
    Child c;
    c.pid = fork();
    if (c.pid == 0) {                                   // child: AS-safe zone
        execv(argv[0], const_cast<char* const*>(argv));
        ssize_t e = errno;                              // exec failed
        ssize_t ignored = ::write(errpipe[1], &e, sizeof e);
        (void)ignored;
        _exit(127);                                     // NOT exit(): no parent cleanup
    }
    ::close(errpipe[1]);                                // parent: read end only
    int e = 0;
    ssize_t n = ::read(errpipe[0], &e, sizeof e);       // blocks until EOF or byte
    ::close(errpipe[0]);
    return n == 0;                                      // EOF == exec succeeded
}
/* Expected: spawn({"/bin/true", nullptr}) -> true (pipe EOFs);
   spawn({"/no/such", nullptr}) -> false with errno delivered (then child
   reported as _exit(127) by the reaper). */
```

### 5.7 fd inheritance, CLOEXEC, and RAII ownership

Children inherit **every** descriptor without `FD_CLOEXEC` across `exec`
— the leak default. Hygiene set (details in [./c.md](./c.md) §5.9):
`O_CLOEXEC`/`pipe2` at creation (**[Linux]**), `fcntl(F_SETFD,
FD_CLOEXEC)` (**[POSIX]**), `posix_spawn_file_actions_addclose`/`adddup2`
for explicit child-side shaping, **[Linux]** `close_range(2)` (since
5.9) to sweep. From C++, the wrapper rule: any RAII fd type (`int` in a
destructor-closing struct) must set `O_CLOEXEC` *at creation*, because a
constructor-then-fork window is exactly where leaks happen — and a
`double close` after fd-number reuse can silently corrupt an unrelated
stream (the classic no-borrow-checker failure, [./c.md](./c.md) §6.3).

### 5.8 Zombies, SIGCHLD, and reaping from C++

A terminated-but-unwaited child is a zombie until reaped (finite PIDs;
[./c.md](./c.md) §5.7 for the full strategy list). C++-specific notes:

- Reaping in a **SIGCHLD handler** is constrained by §4.2: `waitpid` and
  `waitid` are on the POSIX async-signal-safe list (man7
  signal-safety(7)), so the classic
  `while (waitpid(-1, &st, WNOHANG) > 0);` body is safe — but no C++
  library calls in that handler.
- The **sigwait-thread pattern** (§4.4) reaps in a normal thread instead:
  block SIGCHLD process-wide, dedicated thread loops on `sigwait`, calls
  `waitpid`/`waitid` with full C++ library freedom.
- `SIGCHLD` to `SIG_IGN` or `SA_NOCLDWAIT`: children auto-reap, never
  become zombies — but then `waitpid` cannot retrieve their status; a
  design that wants exit codes must reap explicitly.

### 5.9 Timeouts and cancellation: polling `WNOHANG`, retrying `EINTR`

POSIX has no timed child-wait. The building blocks (unchanged from
[./c.md](./c.md) §5.10, restated because every C++ wrapper needs them):

- **Poll**: `waitpid(pid, &st, WNOHANG)` on a timer tick; 0 return = still
  running; at deadline `kill(pid, SIGTERM)`, grace period, `SIGKILL`, then
  reap. A killed child surfaces as `WIFSIGNALED`/`WTERMSIG == SIGKILL`
  (exit status 143/137 through the 128+N decoder), not as an error.
- **`EINTR` discipline**: `waitpid`/`waitid`/`read` on pipes fail with
  `EINTR` when a caught signal arrives (POSIX documents the failure);
  retry — do not treat as error. Or install handlers with `SA_RESTART`
  where the operation is restartable ([./c.md](./c.md) §4.6).
- **Cancellation of the *waiting*, not the child**: the waiting thread can
  be unblocked by `pthread_kill`/eventfd; the child still needs the
  kill-and-reap ladder. `std::stop_token` (§6.4) fits the wait loop
  cleanly: check `stop_requested()` between `WNOHANG` polls.

---

## 6. Concurrency and Resource Semantics

### 6.1 `std::thread`: uncaught exceptions end the process

**[ISO C++]** (`[thread.thread.constr]`): "If the invocation of invoke
terminates with an uncaught exception, **terminate is invoked**" — a
thread function has no caller to catch anything, so `throw` inside a
thread function is `main`-level fatal by default. The wrapping rule
(mirror of §1.5's `main` wrapper): make top-level thread functions
`noexcept`-at-the-boundary — catch, convert to exit codes/flags/queues.

### 6.2 `std::thread` destruction: the joinable-terminate rule

**[ISO C++]** (`[thread.thread.destr]`, quoted §2.4): a joinable `thread`
object destroyed → `std::terminate`. The standard's Note explains the
design: neither implicit join (performance surprise, unbounded block) nor
implicit detach (correctness surprise) is defensible, so the standard
makes you choose **before** the destructor. Trigger (1.12) covers
move-assignment too — overwriting a joinable `thread` kills the process.
The practical rules: every `std::thread` is either joined or detached on
every path, or (C++20) you use `std::jthread` and the decision is made
for you.

```cpp
#include <thread>
#include <cstdio>

static void worker() { std::puts("worker done"); }

int main(int argc, char**) {
    if (argc > 1) {
        std::thread t(worker);
        std::puts("about to return with joinable thread");
        return 0;                 // t joinable at scope exit -> std::terminate!
    }
    std::thread t(worker);
    t.join();                     // must join (or detach) before destruction
    return 0;
}
/* Expected: "./a.out"      → "worker done", exit 0.
             "./a.out x"     → "about to return..." then terminate → abort
                               (SIGABRT; 134 through a shell). */
```

### 6.3 join/detach and the error surface

`join()` blocks until the thread function completes, then releases the
state (`joinable() == false` afterwards); error conditions include
`no_such_process` (not valid), `invalid_argument` (not joinable),
`resource_unavailable_would_block`. `detach()` releases without waiting —
a detached thread outliving `main` races static destruction (§3.7): the
standard's exit-time UB rules apply to it verbatim. Neither `join` nor
`detach` may be called on the `thread` object representing the *calling*
thread (`resource_deadlock_would_occur` for self-join).

### 6.4 `std::jthread` + `std::stop_token`: cooperative cancellation as RAII

`std::jthread` (C++20) = `std::thread` + a `stop_source` the thread
function can observe + automatic join at destruction. The cancellation
protocol is cooperative: the canceller calls `request_stop()`, the worker
polls `stop_token::stop_requested()` (or registers a `stop_callback` for
push-style wakeup), and the destructor joins. This composes with §5.9:
the stop token cancels the *wait loop*, while the OS-level child needs
the TERM→KILL ladder.

```cpp
#include <thread>
#include <chrono>
#include <cstdio>

int main() {
    std::jthread t([](std::stop_token st) {
        while (!st.stop_requested()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        std::puts("worker observed stop");
    });
    std::this_thread::sleep_for(std::chrono::milliseconds(30));
    t.request_stop();          // explicit; the destructor would do it anyway
}                              // destructor: request_stop() + join()
/* Expected: "worker observed stop" then clean exit 0 — no join needed,
   no terminate possible from the destructor. */
```

### 6.5 `std::async` and the blocking-future destructor

**[ISO C++]** (`[futures.async]`): with `launch::async` the function runs
"as if in a new thread of execution represented by a thread object"; with
`launch::deferred` it is stored and runs lazily **in the thread that calls
`get`/`wait`**; and if the caller passes no policy (or the OR of both),
"implementations should defer invocation or ... run eagerly" — i.e. **the
implementation chooses**, so portability requires asking
`future::wait_for(0s) == future_status::deferred` before assuming a
thread exists. The destructor rule: **the last `future` from an
`async` `launch::async` call "shall block until the associated thread has
completed, as if joined"** — a forgotten `auto f = std::async(...)`
semicolon is a synchronous block disguised as fire-and-forget. The
deferred case blocks in the destructor *too* — running the whole deferred
computation at scope exit.

### 6.6 `std::mutex` and the RAII lock guards

`std::mutex::lock()` blocks; it may throw `system_error`
(`resource_deadlock_would_occur` **might** be observed — not guaranteed),
so lock acquisition is the one RAII constructor that can fail visibly.
Hold locks with `std::lock_guard` (strict scope), `std::unique_lock`
(movable, condition-variable compatible), `std::scoped_lock` (multi-mutex
deadlock-avoiding, C++17). There is no poison-and-recover: if a thread
dies with a mutex held (e.g. by `std::terminate` unwinding rules §3.6),
every subsequent `lock()` blocks forever — the C++ counterpart of C's
fork-deadlock (§5.5) is *terminate-deadlock*: a `terminate` handler or
`atexit`/destructor that locks a mutex held anywhere else hangs `exit`.

### 6.7 `thread_local`: destruction order at thread exit and process exit

**[ISO C++]** (`[basic.start.term]`p2, quoted §3.5): a thread's
`thread_local` objects are destroyed when its initial function returns
**or** when that thread calls `std::exit`; the exiting thread's
`thread_local` destruction *strongly happens before* static destruction.
Design consequences: a `thread_local` destructor may not call into a
static object that a *later*-destroyed static might also touch (order is
only defined within the same thread's exit sequence); handlers running on
"some" thread (§4.4) must not touch `thread_local` state at all (§4.2
rule 2); and `thread_local` in a `quick_exit`/`at_quick_exit` context is
off-limits (N4950 Note 6, §3.4).

### 6.8 Standard streams: constructed before `main`, never destroyed, flushed at exit

**[ISO C++]** (`[iostream.objects.overview]`): the `cin`/`cout`/`cerr`
objects are constructed before the body of `main` begins (via
`ios_base::Init`), and "the objects are **not destroyed** during program
execution"; including `<iostream>` behaves as if it defined an
`ios_base::Init` instance with **static storage duration**.
**[glibc-libstdc++]** that static `Init` object's destruction (running in
the §3.5 static-destruction sequence at `exit` time) is what flushes the
standard C++ streams on normal termination — libstdc++'s `Init` destructor
flushes `cout`/`cerr`/`clog` and calls `stdio_sync_filebuf` teardown.
Consequences: `_Exit`/`quick_exit`/`abort`/`terminate` paths skip that
flush (§3.8) — flush explicitly (`std::cout.flush()`, or `<< std::endl`)
before choosing those exits; and `std::ios_base::sync_with_stdio(false)`
decouples C++ streams from C stdio buffering, which changes the fork
interaction below.

### 6.9 stdio buffering × fork: the double-output bug, C++ edition

**[glibc-libstdc++]**/**[POSIX]** (mechanism in [./c.md](./c.md) §6.4):
`fork` copies the process image *including unflushed stdio and iostream
buffers*. If the parent had pending output at `fork` time, the child
inherits a copy; a child that later calls `exit` (or returns from `main`)
flushes it — **output appears twice**. The C++-specific wrinkle: the
buffer in question may be `std::cout`'s (a `filebuf`) rather than C
stdio's; with `sync_with_stdio(true)` (default) both share the C stream,
so one flush covers both. Discipline, unchanged in shape: **flush
everything before forking**, use `_exit` on child error paths (§5.6), and
in the exec-child never rely on `exit`-time flushing you deliberately
skipped. Buffering × redirection (the `ls | wc` bug) applies to
`std::cout` exactly as to `stdout` — full-buffered when the fd is a
pipe/FILE, line-buffered on a terminal.

### 6.10 fd/handle ownership and the leak/deadlock inventory

- **fd ownership via RAII**: wrap `int` fds in a destructor-closing type
  (with `O_CLOEXEC` at creation, §5.7); wrap `FILE*` in a
  `unique_ptr`-with-`fclose` deleter; remember the descriptor *number* is
  shared state across fork — one owner per fd, close in exactly one place,
  or the double-close/reuse corruption of [./c.md](./c.md) §6.3 applies.
- **Leaks in scope**: unjoined joinable `std::thread`s (terminate at
  destruction or leak resources), unreaped children (zombies, §5.8),
  un-CLOEXEC'd fds crossing exec (§5.7), dynamic storage never deleted
  (reclaimed wholesale by the OS at exit — a lifetime concern, not a
  termination one), and detached threads racing static destruction
  (§3.7).
- **Deadlocks in scope**: lock held during `fork` (child-frozen mutexes,
  §5.5); mutex held across `std::terminate`/`abort` teardown; `atexit`
  handler waiting on a dead thread's lock (§3.7); the async
  blocking-destructor surprise (§6.5) as a "deadlock" against your own
  latency budget.

---

## Coverage ledger

The per-item coverage ledger for this chapter is
[ledger-cpp.md](./ledger-cpp.md) (IDs `PL-CPP-001`…`PL-CPP-075`, G4
schema). Rollup at publication: **Inventoried: 75 / Documented: 74 /
Remaining: 0 / Source-limited: 1**. The single source-limited row is the
`std::jthread` destructor's exact clause wording: the
en.cppreference.com page (signature reference of record) was
Cloudflare-blocked at retrieval and the working-draft section fetched
verified the class-level contract ("automatically join", `[thread.jthread.class]`)
without transcribing the destructor paragraph. Signature sources of truth:
C++23 DIS **N4950** (open-std.org) and the C++ working draft
(eel.is/c++draft, generated 2026-08-23); the GCC 14.2.0 libstdc++ headers
for the implementation layer; POSIX.1-2024 (pubs.opengroup.org, Issue 8)
and man-pages 6.19 (man7.org) for the OS layer.

## References

1. ISO/IEC 14882:2024 — C++23 Committee Draft **N4950** (open-std.org,
   https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2023/n4950.pdf;
   retrieved 2026-10-13): §6.8.6 `[basic.stc]` (storage durations), §6.9.3
   `[basic.start]` (`[basic.start.main]`, `[basic.start.dynamic]`,
   `[basic.start.term]` — startup, init order, fiasco ordering, magic
   statics interplay, termination/destruction order, exit-time UB),
   §8.4 `[stmt.dcl]` (block-scope static/thread init: first-pass, retry,
   concurrent wait), §14.3–14.6 `[except.*]` (throw, unwinding,
   destructors during unwinding, `noexcept`, `terminate` triggers (1.1)–
   (1.13) and unwind rules), §17.2.2 `[cstdlib.syn]` +
   §17.5 `[support.start.term]` (exit/_Exit/quick_exit/abort/atexit/
   at_quick_exit/EXIT_*/effects sequence), §17.13.1 `[support.runtime]`
   (getenv data-race carve-out), §17.13.4–17.13.5 `[csignal.syn]`/
   `[support.signal]` (signal-safe evaluation list, `sig_atomic_t`),
   §17.9.5 `[exception.terminate]` (terminate_handler/set_terminate/
   get_terminate), §31.7.1 `[iostream.objects.overview]` (ios_base::Init),
   §33.3–33.4 `[thread.stoptoken]`/`[thread.threads]` (thread/jthread/
   stop_token/stop_source/stop_callback, destructor rules),
   §33.6 `[thread.mutex]`, §33.10 `[futures]` (async, future, blocking
   destructor "as if joined").
2. C++ working draft (eel.is/c++draft, generated 2026-08-23 from the LaTeX
   sources; retrieved 2026-10-13): `[support.signal]` reorganized
   signal-safe list, `[basic.start.main]` UB anchor
   (`[ub:basic.start.main.exit.during.destruction]`), `[support.env]`/
   `[support.start.term]` current-anchor cross-checks; used to flag C++26
   deltas only — all normative quotes above are from N4950.
3. POSIX.1-2024 / Issue 8 (pubs.opengroup.org/onlinepubs/9799919799,
   retrieved 2026-10-13): `system` (`execl(<shell path>, "sh", "-c",
   "--", command, (char*)0)`; SIGINT/SIGQUIT ignored, SIGCHLD blocked;
   -1/127/wait-status return), `popen`/`pclose`, `posix_spawn`
   (synopsis verified; file_actions/attrp semantics), `_Exit`/`_exit`
   (`status & 0377` truncation), `wait`/`waitid` (`WIFEXITED`/
   `WEXITSTATUS`/`WIFSIGNALED`/`WTERMSIG`/`WNOHANG`, `EINTR`), `fork`
   (multithreaded-fork AS-safe rule), `exec` (no return on success),
   `getenv`/`setenv`/`putenv` (ownership asymmetry),
   `pthread_exit` (thread death releases no process resources) — the
   POSIX-function behavioral details are additionally consolidated in
   [./c.md](./c.md) (verified the same day against the same Issue-8
   pages).
4. Linux man-pages **6.19** (man7.org, dated 2026-06-05; retrieved
   2026-10-13): signal-safety(7) ("An async-signal-safe function is one
   that can be safely called..." — async-signal-safe list and rationale),
   exit(3), abort(3), _exit(2) (`exit_group`), wait(2) (`WEXITSTATUS`
   low 8 bits), system(3) (`/bin/sh`), popen(3) (mode `'e'` since
   glibc 2.9), posix_spawn(3) (glibc vfork/clone internals),
   fork(2), pipe(2)/pipe2(2) (`O_CLOEXEC`), fcntl(2), close_range(2)
   (since Linux 5.9), signal(7), pthreads(7).
5. Toolchain / runtime substrate (retrieved 2026-10-13):
   sourceware.org/glibc — current stable glibc **2.44** (released
   2026-07-25); GCC **14.2.0** (Debian) installed libstdc++ headers
   inspected for the implementation layer: `<cstdlib>` (e.g.
   `extern "C" void quick_exit(int) _GLIBCXX_NOTHROW _GLIBCXX_NORETURN;`),
   `<stop_token>` present (C++20 support confirmed in the local
   toolchain). The GNU libc manual (gnu.org) was unreachable from this
   environment (limitation also recorded in [./c.md](./c.md)); no claim
   in this chapter depends on it.
6. en.cppreference.com/w/cpp — signature reference of record for this
   part; **Cloudflare-blocked from this environment at retrieval time**
   (2026-10-13; "Just a moment..." challenge on every page fetch,
   including /w/cpp/utility/program/exit and /w/cpp/error/set_terminate).
   All signatures were transcribed from N4950 instead (stronger primary
   source); affected rows are marked in [ledger-cpp.md](./ledger-cpp.md).
7. Sibling chapters and cross-links:
   [../../linux/process-exit-signal/languages/cpp.md](../../linux/process-exit-signal/languages/cpp.md)
   (exit/signal slice), [./c.md](./c.md) (C substrate),
   [./rust.md](./rust.md) (Section-G sibling), part hub
   [./index.md](./index.md); interview-topic pages
   [../cpp/modern-cpp.md](../cpp/modern-cpp.md),
   [../cpp/concurrency.md](../cpp/concurrency.md),
   [../cpp/stl.md](../cpp/stl.md).
