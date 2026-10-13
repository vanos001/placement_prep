# Cross-Language Comparison: Process, Signals, and Subprocess Semantics

This chapter compares the eight language chapters of this part **side by side
without assuming their semantics are equivalent**. Every row below traces to a
verified claim in one of the part chapters, each of which documented its
behavior against a declared primary source; where two chapters' verified facts
disagree (or one corrects the other), the discrepancy is stated, not smoothed
over. The exit/signal-scoped comparison in the Linux part
([../../linux/process-exit-signal/languages/comparison.md](../../linux/process-exit-signal/languages/comparison.md))
owns status decoding and the `128+N` convention in depth; this chapter
cross-links it and stays on the language/runtime layer.

**How to read it.** Nine dimensions, one `##` section each, in the order the
part's chapters cover them: termination doors (§1), cleanup guarantees (§2),
failure statuses (§3), signals (§4), subprocesses (§5), child-status types
(§6), pipes and streams (§7), threading restrictions (§8), portability and
versions (§9). Each section pairs a comparison table with an "asymmetries that
bite" paragraph — the table is the lookup, the prose is the part where
equivalent-looking APIs diverge. Citations are compact: `([c.md §3.2](./c.md),
POSIX.1-2024 _Exit)` means "verified in c.md §3.2 against POSIX.1-2024's
`_Exit` page"; follow the chapter for the full signature and ledger row. A
guarantee stated here is exactly as strong as its chapter's label —
`[std lib documented]` is a contract, `[HotSpot implementation]`/
`[runtime implementation]` is observable behavior of one implementation, and
`source-limited` means the chapter said so explicitly (see
[Recorded discrepancies](#recorded-discrepancies-between-chapters)).

**The eight declared versions** (one line each; full source sets in
[References](#references)):

- **C** — ISO C17 (draft N2310) baseline with C23 deltas (N3220), glibc 2.44,
  POSIX.1-2024, Linux man-pages 6.19 ([c.md](./c.md), fetched 2026-10-13).
- **C++** — ISO C++23 DIS N4950 (C++26 working draft cross-checked), GCC 14.2.0
  libstdc++ headers, glibc 2.44, POSIX.1-2024 ([cpp.md](./cpp.md), retrieved
  2026-10-13; cppreference was blocked, signatures transcribed from N4950).
- **Python** — CPython 3.15.0 (docs.python.org/3, CPython source, PEPs
  442/446/475) ([python.md](./python.md), retrieved 2026-10-13).
- **Go** — Go 1.27.2 (go.dev/dl JSON feed; pkg.go.dev doc comments at tag
  `go1.27.2`; Go source for implementation facts) ([go.md](./go.md), retrieved
  2026-10-13).
- **Java** — JDK 25 LTS (Javadoc, JLS SE 25, JEPs, `jdk-25+36` source
  spot-checks) ([java.md](./java.md), retrieved 2026-10-13).
- **Rust** — `std` 1.99.0 (build `b940084d7`, 2026-09-28; doc.rust-lang.org
  std/Reference/Cargo Book; std source for numeric anchors)
  ([rust.md](./rust.md), retrieved 2026-10).
- **Node.js** — v24.21.0 LTS "Krypton" (nodejs.org/docs/latest-v24.x/api,
  event-loop guide, libuv 1.52.1) ([nodejs.md](./nodejs.md), retrieved
  2026-10-13).
- **OCaml** — OCaml 5.5.1 (source tree at tag `5.5.1`, ocaml.org/manual/5.5)
  ([ocaml.md](./ocaml.md), verified 2026-10-13).

Grounding statement: every claim below was verified in the cited chapter
against the chapter's declared official source during the 2026-10 retrieval
window. Facts that a chapter could only source-implement (labeled
`[HotSpot implementation]`, `[runtime implementation]`, source-limited) are
relabeled here the same way — the label survives the comparison.

---

## 1. Normal return and explicit process termination

All eight runtimes convert a returned entry point into the same OS mechanism —
a status byte delivered to the parent — but **who converts, and what runs
first, differs at every layer** ([c.md §3.1–3.5](./c.md), ISO C23 N3220
§5.1.2.3.4/§7.24.4; [cpp.md §3.1–3.2](./cpp.md), N4950 `[basic.start.main]`/
`[support.start.term]`).

| Language | Entry-point return means… | Who builds the OS status | Explicit exit family | Truncation to wait-status |
|---|---|---|---|---|
| C | *Equivalent to `exit(main_value)`*; falling off the end returns **0** (defined) | C runtime `exit` → `_exit` → `exit_group(2)` [Linux] | `exit` / `_Exit` (C99+) / `quick_exit` (C11+) / `_exit` (POSIX) / `abort` | `status & 0xFF` for `wait`/`waitpid`; full value via `waitid`/SIGCHLD `siginfo_t` ([c.md §3.5](./c.md), POSIX `_Exit`) |
| C++ | Destroy `main`'s automatic objects, then `std::exit(v)` — *only `main`'s frame unwinds* | Same C substrate | `std::exit` / `std::quick_exit` / `std::_Exit` / `std::abort` | Same 8-bit rule ([cpp.md §3.4](./cpp.md), POSIX `_Exit`) |
| Python | Main module completes → interpreter shutdown → C `exit(0)` | CPython `Py_FinalizeEx` → C `exit(sts)` | `sys.exit(arg)` (raises `SystemExit`), `os._exit(n)` (raw), `os.abort()` | OS truncates `int` mod 256; docs recommend 0–127; non-int arg prints to stderr and exits **1** ([python.md §3.2](./python.md), sys docs) |
| Go | `main` returns → program exits, **not waiting for other goroutines**; defers in `main` run, nothing else does | Runtime: `syscall.Exit` → `exit_group` | `os.Exit(n)` (defers *not* run), `log.Fatal*` (always 1), unrecovered panic (2) | Doc note: keep status in `[0, 125]`; kernel keeps 8 bits ([go.md §3.3](./go.md), pkg.go.dev/os) |
| Java | `main` returning ends only the main thread; JVM exits when the **last non-daemon thread** ends, then hooks run | JVM termination → OS process exit | `System.exit(n)` ≡ `Runtime.exit(n)` (hooks), `Runtime.halt(n)` (no hooks) | `exit(3)` keeps the least significant byte — `exit(300)` is observed as 44; **the JDK docs do not document this**, it is OS behavior ([java.md §3.9](./java.md), man-pages exit(3)) |
| Rust | `Termination::report(self) -> ExitCode`; `Err` prints `Error: {err:?}` and exits `FAILURE` (1) | `lang_start` → single-threaded `libc::exit` | `std::process::exit(i32)` (no destructors), `std::process::abort()` | "On most Unix-like platforms, only the eight least-significant bits are considered" — docs' own example: `exit(0x0100)` is 0 on Linux, **256 on Windows** ([rust.md §3.3](./rust.md), std `process::exit`) |
| Node.js | Event loop drains (no referenced handles left) → `'exit'` listeners → exit 0 | Node/V8 teardown | `process.exit([code])` (sync, async I/O dropped), `process.exitCode` (preferred channel), `process.abort()` | Not language-documented; OS-level 8-bit rule applies ([nodejs.md §3.3–3.4](./nodejs.md), process docs) |
| OCaml | Link-order unit initializers run, then an **implicit `exit 0`** | `Stdlib.exit` → `caml_sys_exit` → C `exit` | `Stdlib.exit n` (hooks + `flush_all`), `Unix._exit n` (nothing runs) | `caml_do_exit` ends in C `exit(retcode)` → `status & 0xFF` ([ocaml.md §3.2/3.6](./ocaml.md), `stdlib.ml`/`sys.c`) |

**Asymmetries that bite.**

- *Same syntax, different blast radius.* `return` from `main` in C++
  unwinds `main`'s frame (automatic objects destroyed) before `std::exit`;
  `std::exit` called anywhere else destroys **no automatic objects at all**
  — that is a documented standard sentence, not an implementation quirk
  ([cpp.md §3.2](./cpp.md), N4950 `[support.start.term]`p9). Go's `main`
  return runs only `main`'s defers; `os.Exit` runs **nobody's** defers
  ([go.md §3.2–3.3](./go.md), pkg.go.dev/os "deferred functions are not run").
- *Who waits.* Java is the outlier: returning from `main` does not terminate
  the process while any non-daemon thread lives ([java.md §3.2](./java.md),
  JLS §12.8); Go explicitly does not wait for goroutines ([go.md §3.4](./go.md),
  language spec); Rust does the opposite — when the main thread terminates the
  whole program shuts down and remaining threads' destructors "may not be
  executed" ([rust.md §3.10](./rust.md), std `thread` docs).
- *Truncation is documented in some chapters and absent in others.* POSIX/C
  state `status & 0377` normatively; Rust's docs show the Linux/Windows
  divergence; Java's docs are silent and java.md anchored the fact in
  man-pages `exit(3)` — treat "my exit code was 300" as a bug in five of the
  eight chapters' terms ([java.md §3.9](./java.md)).

## 2. Cleanup and finalization guarantees

The core comparison. Legend: **✅ runs** · **❌ does not run** · **⚠ partial /
conditionally** · **— no such mechanism**. Rows cite their chapter once
(first column); every cell is that chapter's verified per-path table
([c.md §3.4](./c.md), [cpp.md §3.8](./cpp.md), [python.md §3.7](./python.md),
[go.md §3.2](./go.md), [java.md §3.8](./java.md), [rust.md §3.10](./rust.md),
[nodejs.md §3.3/3.5](./nodejs.md), [ocaml.md §3.3](./ocaml.md)).

| Language | Path | Destructors / defers / `finally` | `atexit`-family / hooks | Finalizers / GC-anchored cleanup | Buffered output flushed |
|---|---|---|---|---|---|
| C | normal return / `exit(n)` | — (no destructors) | ✅ `atexit` reverse order | — | ✅ (stdio flush+close) |
| C | `quick_exit` / `_Exit`/`_exit` | — | ❌ (`at_quick_exit` only / none) | — | ❌ (`_exit` shall not flush) |
| C | `abort()` / signal death | — | ❌ | — | ❌ (glibc practice) |
| C++ | `return` from `main` | ✅ `main`'s automatics | ✅ (statics + `atexit` woven LIFO) | ✅ static/thread-duration dtors | ✅ |
| C++ | `std::exit(v)` any thread | ❌ automatics never | ✅ calling thread's `thread_local` dtors first, then statics + `atexit` | ⚠ other threads keep running through teardown (UB if they touch dying objects) | ✅ |
| C++ | `quick_exit` / `_Exit` | ❌ | ❌ (`at_quick_exit` only / none) | ❌ | ❌ / impl-defined |
| C++ | uncaught exception → `terminate` → `abort` | ⚠ impl-defined whether stack unwinds first (no-handler case); **shall not** unwind otherwise | ❌ | ❌ | ❌ (glibc) |
| Python | normal completion / uncaught exception (status 1) | ✅ `finally`/`__exit__` on the way out | ✅ `atexit` LIFO, after non-daemon threads joined | ✅ `__del__` may run at final GC (weakened globals) | ✅ (flush failure ⇒ status **120**) |
| Python | `sys.exit(n)` | ✅ (it is an exception) | ✅ | ✅ | ✅ |
| Python | `os._exit(n)` | ❌ | ❌ | ❌ | ❌ |
| Python | `os.abort()` | ❌ (bypasses even the Python SIGABRT handler) | ❌ | ❌ | ❌ |
| Go | `main` returns | ✅ `main`'s defers only | — (no atexit mechanism) | ❌ finalizers not guaranteed | ❌ runtime does not flush `bufio` |
| Go | `os.Exit(n)` / `log.Fatal` | ❌ any goroutine | — | ❌ | ❌ |
| Go | unrecovered panic (any goroutine) | ✅ panicking goroutine's defers; ❌ all others | — | ❌ | ❌ |
| Go | default signal death | ❌ | — | ❌ | ❌ |
| Java | `main` returns, last non-daemon ends | ✅ normal execution until shutdown begins | ✅ shutdown hooks, unspecified order, concurrent | ❌ `finalize`/`Cleaner` not guaranteed | ⚠ (no documented flush of Java buffers; `System.out` is typically line-flushed) |
| Java | `System.exit(n)` / signal (no `-Xrs`) | ❌ `finally`/TWR close at JVM termination | ✅ hooks (the *only* guaranteed app callback) | ❌ | ❌ |
| Java | `Runtime.halt(n)` / SIGKILL | ❌ | ❌ | ❌ | ❌ |
| Rust | `return` from `main` | ✅ current thread's locals; ⚠ other threads killed mid-flight | ✅ C `atexit` runs (documented current implementation) | ❌ (no finalizers; `Drop` is the mechanism) | ✅ `BufWriter` drop-flush on unwind paths |
| Rust | `process::exit(n)` | ❌ **no destructors, any thread** | ⚠ C `atexit` + `fini` sections *do* run (documented implementation) | ❌ | ❌ Rust `BufWriter` lost; C stdio flushed |
| Rust | `abort()` / `panic="abort"` / signal death | ❌ | ❌ (abort runs no hook; `panic="abort"` **does** run the panic hook first) | ❌ | ❌ |
| Node.js | loop drains / `process.exitCode` | ✅ pending async work completes first | ✅ `'exit'` listeners (synchronous only) — *the one "immediate" exit that still runs user callbacks* | ❌ GC plays no role in cleanup | ⚠ async stdout writes **may be lost** on `process.exit()` |
| Node.js | `process.exit(n)` | ❌ pending async I/O dropped | ✅ `'exit'` listeners run | ❌ | ❌ (often truncated) |
| Node.js | `process.abort()` / uncaught (status 1) | ❌ | ⚠ `'exit'` listeners run before abort in practice — **undocumented**, do not rely | ❌ | ❌ |
| OCaml | `exit n` / implicit `exit 0`/`2` | ✅ (OCaml has no destructors; `Fun.protect ~finally` is the idiom) | ✅ `flush_all` → `Domain.at_exit` → `Stdlib.at_exit`, LIFO | ✅ `Gc.finalise` at GC; ⚠ `caml_shutdown` only with `OCAMLRUNPARAM=c` | ✅ **flush before hooks** (unlike C/C++/Python) |
| OCaml | uncaught exception (exit 2) | — | ✅ `do_at_exit` wrapped in `try…with _ -> ()` — raising hooks **silently swallowed** | ✅ | ✅ |
| OCaml | `Unix._exit` / default signal death | ❌ | ❌ | ❌ | ❌ |

**Asymmetries that bite.**

- **`exit()` is a family of five different contracts, not one.** C/C++ run
  `atexit` on `exit` only; Rust's `process::exit` still runs the *C* `atexit`
  and ELF `fini` sections (documented implementation) while running **zero**
  Rust destructors — so a C library's cleanup fires but your `Drop`/`BufWriter`
  does not ([rust.md §3.3](./rust.md), std `process::exit`). Go's `os.Exit`
  runs nothing at all; Python's `atexit` runs; Java's hooks run but its
  finalizers never do; Node's `'exit'` listeners run but must be synchronous;
  OCaml flushes *first* and then runs two hook chains. Five runtimes, five
  answers to "what does exit mean".
- **Hook-order inversion.** OCaml flushes stdio **before** running hooks
  ([ocaml.md §3.2](./ocaml.md), `stdlib.mli`); C/C++ flush **after** the
  `atexit` list ([c.md §3.1](./c.md), man7 exit(3)); Python flushes after
  `atexit` **and** module teardown ([python.md §3.7](./python.md),
  `pylifecycle.c`). A logging hook that prints relies on different guarantees
  in each runtime.
- **Handler exceptions are policy, not accidents.** C++: an `atexit` handler
  that throws calls `std::terminate` ([cpp.md §3.3](./cpp.md)); Python:
  handler exceptions are accumulated and the last one re-raised *after* all
  handlers ran, changing the final status to 1 ([python.md §3.10](./python.md),
  atexit docs); OCaml: swallowed in the uncaught path, fatal in the normal
  `exit` path ([ocaml.md §3.3](./ocaml.md), `printexc.ml`); C: no policy —
  a handler can `exit` recursively (UB-adjacent) or return to the list.
- **`exec` wipes the board in C-family children.** After a successful `exec`
  no `atexit`/`at_quick_exit`/`pthread_atfork` registration survives
  ([c.md §3.4/5.2](./c.md), POSIX `exec`) — which is exactly why the fork-child
  error path must be `_exit(127)`, a rule every chapter in this part restates
  for its own substrate ([cpp.md §5.6](./cpp.md), [python.md §3.5](./python.md),
  [ocaml.md §5.2](./ocaml.md)).

## 3. Exceptions, panics, fatal errors, and abort behavior

Default failure statuses, and whether each is a documented guarantee or
implementation behavior ([python.md §3.4](./python.md),
[go.md §3.6](./go.md), [rust.md §3.1/3.10](./rust.md),
[ocaml.md §3.4](./ocaml.md), [java.md §3.6](./java.md),
[nodejs.md §3.2/3.6](./nodejs.md), [cpp.md §3.6](./cpp.md)):

| Language | Trigger | Default status | Guarantee level | Source behind the number |
|---|---|---|---|---|
| Python | uncaught exception (non-`SystemExit`) | **1** | documented ([language]/[CPython]) | docs.python.org sys/exceptions; traceback to stderr |
| Python | flush error during finalization | **120** | documented + source | sys docs + `pylifecycle.c` |
| Go | unrecovered panic in *any* goroutine | **2** | documented ([std lib documented]) | pkg.go.dev/runtime (`GOTRACEBACK`); process exits cleanly, **not** 128+N |
| Rust | main-thread panic (unwind) | **101** | implementation-anchored | std `rt.rs` "map escaping main-thread panic to 101"; labeled "not a stability contract" |
| Rust | `main` returns `Err` | **1** | documented | `Termination` → `ExitCode::FAILURE` |
| OCaml | uncaught exception | **2** | documented | `stdlib.mli` "implicit `exit 2`"; `printexc.c` `exit(2)` verified |
| OCaml | `Unix.handle_unix_error` | **2** | documented | `unix.mli` |
| Java | uncaught exception in `main` (last non-daemon) | **1** | **implementation behavior** | JLS/Javadoc silent; HotSpot launcher observed 1 (sibling chapter table) |
| Node.js | uncaught fatal exception | **1** | documented | v24 exit-codes table |
| Node.js | V8 fatal error / bootstrap failure | **5** / **3, 4, 10** / **9** / **13** / **14** | documented | v24 exit-codes table |
| C++ | uncaught exception → `terminate` → default handler → `abort` | SIGABRT death (shell 134 = 128+SIGABRT on Linux) | mechanism standard; **status is a platform observation**, not a standard number | N4950 `[except.terminate]`p2; default handler calls `abort()` |
| C | `assert` failure / `abort()` | SIGABRT death | standard mechanism | ISO C §7.2.1.1 / §7.22.4.1 |
| Go | *no abort equivalent* — closest is `GOTRACEBACK=crash` runtime failure | — | documented knob | pkg.go.dev/runtime ([go.md §3.8](./go.md)) |

**Numeric collisions — same byte, different contract.** Exit code **2** is a
Go panic (documented runtime failure path), an OCaml uncaught exception
(documented `stdlib.mli`), and — per Node's own table — *unused, "reserved by
Bash for builtin misuse"* ([nodejs.md §3.2](./nodejs.md)). Exit code **1** is
"uncaught exception" in Python and Node (documented), `FAILURE` in Rust
(documented), `log.Fatal` in Go (documented, hardcoded), and merely a launcher
convention in Java (implementation). Code **101** is only Rust's panic.
A monitoring rule like "nonzero ⇒ error" survives; any rule keyed to a
specific value does not, unless you have checked which chapter documents it.

**Abort behavior.** C's `abort()` unblocks SIGABRT, raises it, and re-raises
past a returning handler (glibc; man7 abort(3)); C++ `std::terminate` bottoms
out in the same `abort()`; Python's `os.abort()` explicitly bypasses the
Python-level SIGABRT handler and the whole shutdown sequence; Rust's
`process::abort()` skips even the panic hook, while `panic="abort"` still runs
the hook first (documented asymmetry, [rust.md §3.5](./rust.md)); Node's
`process.abort()` is unavailable in Worker threads; OCaml has no OCaml-level
abort — an `abort()` variant exists only behind the runtime-internal
`caml_abort_on_uncaught_exn` knob ([ocaml.md §3.4](./ocaml.md)); Java's
moral equivalent is `Runtime.halt` — no hooks, no sequence, straight to the OS
([java.md §3.4](./java.md), `Runtime` docs).

## 4. Signal registration and handling

Eight models, none equivalent ([c.md §4.1–4.7](./c.md), POSIX.1-2024
`sigaction`/`sigwait`; [cpp.md §4.1–4.4](./cpp.md), N4950 `[support.signal]`;
[python.md §4.1–4.7](./python.md), signal docs + PEP 475;
[go.md §4.1–4.5](./go.md), os/signal docs; [java.md §4.1–4.3](./java.md),
`java` manual; [rust.md §4.1–4.5](./rust.md), std docs + std source;
[nodejs.md §4.1–4.6](./nodejs.md), process docs; [ocaml.md §4.1–4.4](./ocaml.md),
`sys.mli`/`unix.mli`/intfc manual).

| Language | Registration model | Handler runs… | Who changes default dispositions |
|---|---|---|---|
| C | ISO `signal()` (thin, impl-defined rearm) + POSIX `sigaction` (masks, `SA_*`, queuing); `sigwait` thread as the handler-free pattern | **in the kernel interruption frame**, on any thread not blocking the signal; async-signal-safe list only | Only the program (and libraries — query with `sigaction(sig, NULL, &old)`); glibc's `signal()` = BSD semantics over `sigaction(2)` |
| C++ | `<csignal>` = C's header verbatim; **no** C++ mask/queue/sigwait API; POSIX layer used from C++ | same frame as C; the C++ signal-safe list additionally forbids `dynamic_cast`, `throw`, entering a try block, and `thread_local` access | Only the program (C substrate) |
| Python | `signal.signal()` → C handler **sets a flag**; Python handler runs later at a bytecode boundary | in the **main thread only**, between bytecodes; registration off the main thread raises `ValueError` | Startup: SIGPIPE → `SIG_IGN`, SIGINT → `KeyboardInterrupt`; persists BSD-style except SIGCHLD; `set_wakeup_fd` bridges to loops |
| Go | `signal.Notify(ch, sigs…)` — delivery to a channel; `NotifyContext` (1.16) | on a runtime-spawned goroutine — **Go code never runs inside a signal handler**; no async-signal-safety rules for Go code | **The runtime, at startup**: sync signals → runtime panics; SIGHUP/SIGINT/SIGTERM exit; SIGQUIT dumps; SIGPROF profiling; SIGURG preemption; `Notify` re-arms the listed set; `Reset`/`Ignore`/`Stop` restore |
| Java | **No public API.** Shutdown hooks only; `sun.misc.Signal` is internal (`jdk.unsupported`), rejects VM-used signals, dispatches handlers on a *fresh* `MAX_PRIORITY` thread | never in the signal frame; hooks run concurrently as threads during the shutdown sequence | **The JVM**: installs handlers for SIGHUP/SIGINT/SIGTERM (hooks) and SIGQUIT (thread dump); `-Xrs` stops all of it — masks untouched, no handlers, user code must call `System.exit` |
| Rust | **`std` has none** — no registration, masking, or handler API; FFI (`libc` crate) or third-party (`signal-hook`, `ctrlc`, `tokio::signal`), none covered by Rust-project compatibility | whatever thread the OS picks (any non-blocker); masks inherited by `std::thread::spawn` children (OS inheritance, not a std guarantee) | The runtime changes exactly **one** disposition: SIGPIPE is set to `SIG_IGN` at startup (plus fd 0/1/2 sanitization); everything else is untouched |
| Node.js | `process.on('SIGINT', …)` — event listeners; `process.kill(pid, sig)` sends to any pid | as ordinary JS on the event loop, later; a blocked loop (e.g. `spawnSync`) delays handling indefinitely | **Node/libuv**: SIGPIPE ignored by default; SIGTERM/SIGINT default handlers reset terminal mode and exit 128+N — *installing a listener removes that default* (Node stops exiting) |
| OCaml | `Sys.signal` / `Sys.set_signal` (`Signal_default`/`_ignore`/`_handle`); **no `Unix.sigaction`/`Unix.sys_signal`** (verified-absent); `Unix.sigwait` (5.4), `Thread.wait_signal` | **at safe points** — the kernel frame only sets a flag; `caml_process_pending_actions` runs handlers/finalisers/GC; allocation-free loops delay delivery (pump with `Sys.poll_actions`, 5.3) | The runtime: signal setup at startup; native SIGSEGV/SIGTRAP/SIGFPE handlers installed at `caml_startup`, reset at `caml_shutdown` (documented FFI constraint); `Sys.catch_break` turns Ctrl-C into `Sys.Break` |

**Asymmetries that bite.**

- *Three architectures, one goal.* C/C++/Rust-FFI run handler code **inside
  the kernel frame** and pay the async-signal-safety tax (C++ pays more: no
  try-blocks, no `dynamic_cast`, no `thread_local`). Python, OCaml, Go, and
  Node all defer to a safe context (flag-then-bytecodes, safe points, runtime
  goroutine, event loop) and are async-signal-safe *by construction* — the
  cost is delivery latency and, in Python's case, main-thread serialization.
  Java splits the difference: hooks are normal threads, but you cannot learn
  *which* signal fired ([java.md §4.1](./java.md), `java` manual).
- *Drop-when-full is documented exactly once.* Go's `Notify` channel "will not
  block sending" — an unbuffered or full channel **silently drops** signals;
  the docs specify buffer size 1 per signal as sufficient
  ([go.md §4.2](./go.md), os/signal doc). Python's `set_wakeup_fd` documents
  the mirror-image hazard (full pipe ⇒ lost signals, `warn_on_full_buffer`);
  Node listeners cannot drop (event loop is the queue); C/OCaml standard
  signals collapse while pending (one delivery), which is POSIX, not language.
- *Dispositions leak into children selectively.* Python restores
  `SIG_IGN`→`SIG_DFL` for SIGPIPE (et al.) in `subprocess` children by default
  (`restore_signals=True`); Go children **inherit the runtime's modified
  signal mask** (documented); POSIX exec resets *caught* → default but keeps
  *ignored* → ignored ([c.md §4.5](./c.md)) — three different "what does my
  child see" answers ([python.md §5.5](./python.md), [go.md §4.4](./go.md)).

## 5. Subprocess creation, waiting, cancellation, and termination

API-model table ([c.md §5](./c.md), [cpp.md §5](./cpp.md),
[python.md §5](./python.md), [go.md §5](./go.md), [java.md §5](./java.md),
[rust.md §5](./rust.md), [nodejs.md §5](./nodejs.md), [ocaml.md §5](./ocaml.md)):

| Language | Creation surface | Shell by default? | Timeout built-in | Auto-kill on timeout | Kill / destroy ladder |
|---|---|---|---|---|---|
| C | `fork`+`exec*`, `posix_spawn(file_actions, attrs)`, `system`, `popen` | only `system`/`popen` (`sh -c --`) | **none** | — | manual: `alarm`+`SIGALRM`, `WNOHANG` polling, `sigtimedwait`/`signalfd` [Linux]; kill, then **reap** |
| C++ | C substrate (`std::system` impl-defined; POSIX fixed: returns the **wait status word**), `popen`/`pclose` | only `system`/`popen` | **none** | — | manual: `WNOHANG` poll → SIGTERM → grace → SIGKILL → reap ([cpp.md §5.9](./cpp.md)) |
| Python | `subprocess.run/Popen`; `os.posix_spawn` (3.8+); asyncio variants | `shell=False` default (injection defense is structural); `shell=True` = `/bin/sh -c` | ✅ `run(timeout=)`, `Popen.wait(timeout=)`, `communicate(timeout=)` | **`run` kills + waits, then raises `TimeoutExpired`**; bare `wait`/`communicate` raise **without killing** ([python.md §5.10/5.7](./python.md)) | `terminate()` SIGTERM → `kill()` SIGKILL; `send_signal`; `_active` list opportunistically reaps abandoned children |
| Go | `exec.Command`/`CommandContext` — **no shell, ever** (shell is opt-in as an explicit argv) | never | ✅ `context` deadline + `Cancel`/`WaitDelay` (Go 1.20) | context done → `Cancel` (default `Process.Kill` = SIGKILL); `WaitDelay` bounds stragglers: kills, closes pipes, returns `ErrWaitDelay` ([go.md §5.5](./go.md), os/exec docs) | `Process.Signal(SIGTERM)` → `Kill` (SIGKILL); `Wait` **required even after Kill** (zombie); manual goroutine+`select` pattern pre-1.20 |
| Java | `ProcessBuilder` argv array (+ `startPipeline`); `Runtime.exec` legacy | never (shell only if you ask for `sh -c`) | ✅ `waitFor(timeout, unit)` / `waitFor(Duration)` (@since 24) | **NO** — timeout returns `false` and kills nothing; the kill ladder is documented user code ([java.md §5.3](./java.md)) | `destroy()` → SIGTERM, `destroyForcibly()` → SIGKILL (source-verified `ProcessHandleImpl_unix.c`; pid-reuse guarded by start time); `onExit()` (since 9) for async supervision |
| Rust | `std::process::Command` builder — **never a shell**; `CommandExt::exec` (replace self) | never | **none in std** — documented gap | — | `Child::kill()` = SIGKILL directly (no SIGTERM step in std); **`Drop` neither kills nor reaps** (documented); poll `try_wait` + kill pattern ([rust.md §5.4/5.9](./rust.md)) |
| Node.js | `spawn` (no shell), `exec` (**always** a shell, buffered, 1 MiB `maxBuffer`), `execFile`, `fork` (+IPC); sync variants block the loop | `exec`/`execSync` only | ✅ `timeout` option (v15.13.0/v14.18.0), `signal: AbortSignal` (v15.5.0) | kills with `killSignal` (default SIGTERM) — **exactly one signal, no SIGKILL escalation**; manual grace-timer ladder for the stubborn ([nodejs.md §5.10](./nodejs.md)) | `subprocess.kill([signal])` default SIGTERM; `killed` ≠ terminated; libuv reaps after `'exit'` |
| OCaml | `Unix.system`/`Sys.command` (shell string), `create_process[_env]` (argv + fd redirects), `open_process*` family | `system`/`Sys.command`/`open_process*` string forms | **none** (no `wait4`/`waitid`, no timed wait — verified-absent) | — | `Unix.kill pid SIGTERM` → `SIGKILL`; timeout via `Unix.alarm` + handler, `waitpid [WNOHANG]` polling, or `Unix.select` on pipes ([ocaml.md §5.11](./ocaml.md)) |

**Asymmetries that bite.**

- *Four auto-kill semantics under the same word "timeout".* Python `run()`
  kills **and reaps** before raising (exception carries partial output);
  Node kills with one configurable signal and reports `signal`-death in
  `'exit'`; Go kills via `Cancel` and — uniquely — also bounds *pipe draining*
  with `WaitDelay` (a child that exits but leaves pipes open is still cleaned
  up); **Java kills nothing** — `waitFor(timeout)` returning `false` is a poll
  result, and the SIGTERM-then-SIGKILL ladder is explicitly your code
  ([java.md §5.3](./java.md), Process docs). C, C++, Rust, and OCaml offer no
  timeout at all; their chapters document the same composition by hand.
- *Injection posture is a default, not a feature.* Python (`shell=False`),
  Go (`Command`), Rust (`Command`), Java (`ProcessBuilder`), Node (`spawn`/
  `execFile`), and OCaml (`create_process`, `open_process_args*`) pass argv
  verbatim with no shell layer; the shell-string APIs (`system`, `popen`,
  Python `shell=True`, Node `exec`, OCaml `Unix.system`) all carry the same
  documented injection warning, with language-specific mitigations:
  `shlex.quote`/`join` (not a security boundary, per python.md),
  `Filename.quote_command` (OCaml, documented), or passing user data as a
  positional shell parameter (`sh -c 'grep -e "$1"' sh "$user"`, go.md §5.1).
- *Exec-failure reporting splits two ways.* Python raises
  `FileNotFoundError` in the **parent** (unless the `posix_spawn` fast path
  was taken — 3.8 versionchanged); Java throws typed `IOException`; Node
  emits `'error'` (ENOENT) with `'exit'` possibly never firing; C-family and
  OCaml children must self-report — conventionally `_exit(127)`, though
  OCaml's raw exec failure actually raises `Unix_error` **inside the child**
  (fatal → exit 2) unless you wrap it ([ocaml.md §5.2](./ocaml.md),
  `execvp.c` verified); Go reports `exec.ErrNotFound` from `Start`.
- *One-Wait contracts differ.* Go: exactly one `Wait`, mandatory, and
  `GODEBUG=execwait=2` detects leaks via panic-on-finalizer; Rust: no
  implicit reap ever (zombie warning in the docs); Node: reaping is implicit
  after `'exit'` (libuv); Python: `Popen.__del__` + module-level `_active`
  reaper as a GC-anchored net; Java: `waitFor`/`onExit` reap; C/OCaml: every
  child needs exactly one `waitpid`/`close_process*` or a SIGCHLD reaper.

## 6. Child-process status types and signal interpretation

Representation table ([c.md §3.5/5.3](./c.md), [cpp.md §5.1](./cpp.md),
[python.md §5.8](./python.md), [go.md §5.6](./go.md),
[java.md §5.7](./java.md), [rust.md §5.3/5.6](./rust.md),
[nodejs.md §5.12](./nodejs.md), [ocaml.md §5.3](./ocaml.md)):

| Language | Type a parent holds | Signal-death representation | Lossy? |
|---|---|---|---|
| C / C++ | raw `int` wait-status word | decode with `WIFSIGNALED`/`WTERMSIG`/`WCOREDUMP` (the last newly standardized in POSIX.1-2024) | No — the full kernel word, macros standardized |
| Python | `Popen.returncode: int` | **negative `-N`** means "terminated by signal N" (POSIX only, documented); raw status via `os.waitpid` + `os.waitstatus_to_exitcode` | `-N` loses core-dump/stopped bits; raw status keeps them |
| Go | `*os.ProcessState` | `ExitCode()` returns **−1** as a sentinel when "the process hasn't exited or was terminated by a signal"; full decode via `Sys().(syscall.WaitStatus)`; `String()` forms ("signal: killed") verified in os source | `ExitCode()` alone is unusable for signals; `WaitStatus` is lossless |
| Java | `int` from `waitFor`/`exitValue` | **128+N** — an implementation convention from `jdk-25+36` source (`WTERMSIG_RETURN(status) = WTERMSIG(status) + 0x80`, "what all Unix shells do"); **no JDK documentation defines it** (ledger PL-JV-073, source-limited) | Yes: `exit(143)` by the child is indistinguishable from SIGTERM death; no core/stopped info at all |
| Rust | `ExitStatus` (the wait status on Unix) | `code() → None` + `ExitStatusExt::signal() → Some(N)`, plus `core_dumped`/`stopped_signal`/`continued` | No — near-lossless; docs note 128+N is *shell* behavior, not OS |
| Node.js | `'exit'`/`'close'` `(code, signal)` — **exactly one non-null**; `spawnSync` `{status, signal}` (`status: null` on signal); `util.convertProcessSignalToExitCode` (v24.14.0) maps the convention | `signal` as the string name (`'SIGTERM'`) | Loses core-dump bit; the code/signal exclusivity is documented and enforced |
| OCaml | `process_status` ADT: `WEXITED of int \| WSIGNALED of Sys.signal \| WSTOPPED of Sys.signal` (signal payloads typed since 5.4) | the constructor **is** the signal attribution | Loses `WCOREDUMP` and `WIFCONTINUED` (no constructors for them) |

**Asymmetries that bite — and the attribution method.**

- *Three incompatible encodings of the same event.* A SIGKILLed child is
  `returncode = -9` for a Python parent, `ExitCode() == -1` (check
  `WaitStatus`) for a Go parent, `exitValue() == 137` for a Java parent,
  `code == null, signal == 'SIGKILL'` for a Node parent, `signal() == Some(9)`
  for a Rust parent, `WSIGNALED Sys.sigkill` for OCaml. Portable libraries
  must normalize, and "137" is *never* a kernel fact — it is the shell's
  `128+N` arithmetic applied after decoding ([c.md §3.5](./c.md),
  [rust.md §5.3](./rust.md)).
- *Attribution needs the right evidence tier.* Decodable-in-process: C/C++
  macros, Rust `ExitStatusExt`, OCaml ADT, Go `WaitStatus`. Convention-tier
  (needs corroboration): Java's 128+N (source-verified, undocumented), Node's
  `signal` name (documented, but no core-dump bit), Python's `-N`
  (documented, POSIX-only). When a wrapper (`sh -c`) sits in between, only
  the wrapper's status is visible — Rust's docs spell out the two-case
  attribution (`code()==Some(143)` ⇒ inner command died of SIGTERM via the
  shell's encoding; `signal()==Some(15)` ⇒ the shell itself died),
  [rust.md §5.6](./rust.md). The evidence-first method (raw wait-status →
  `waitid`/`siginfo_t` → `/proc`/strace when the word is gone) is the
  [decision tree](../../linux/process-exit-signal/troubleshooting/decision-tree.md);
  the per-value folklore lives in
  [common-status-values.md](../../linux/process-exit-signal/troubleshooting/common-status-values.md).
- *KeyboardInterrupt is a Python-only trap*: an uncaught `KeyboardInterrupt`
  exits **1 with a traceback** because Python raised it — the `128+2` shell
  view happens only when the process actually dies *from* SIGINT
  ([python.md §3.4](./python.md)); every other chapter here dies by signal on
  Ctrl-C unless it catches it.

## 7. Pipe and stream behavior

Deadlock exposure and fd defaults ([c.md §5.6/6.4](./c.md),
[cpp.md §6.8–6.9](./cpp.md), [python.md §5.6–5.7/6.6](./python.md),
[go.md §5.4](./go.md), [java.md §5.2](./java.md), [rust.md §5.5](./rust.md),
[nodejs.md §6.4](./nodejs.md), [ocaml.md §5.7/5.10](./ocaml.md)):

| Language | Safe-drain construct (built-in) | Naive wait-before-drain deadlocks? | Parent-side buffering | fd-inheritance default |
|---|---|---|---|---|
| C / C++ | none — hand-rolled `poll`/`select` loops; `popen` is one-pipe only | **yes** (any two-pipe setup); fork copies unflushed stdio → double output | stdio full-buffered on pipes; C++ `cout` filebuf shares C stream by default | **inherit everything** without `FD_CLOEXEC` — `O_CLOEXEC`/`pipe2`/`close_range` are opt-in hygiene |
| Python | `Popen.communicate()` (drains both pipes concurrently, then waits) | **yes** — the docs' canonical deadlock warning on `wait()` with `stdout=PIPE` | `bufsize=-1` default on the parent pipe file objects | **non-inheritable by default** (PEP 446); `close_fds=True` since 3.2; `pass_fds` allowlist |
| Go | give `Cmd` a writer (`cmd.Stdout = &buf`) + `Run()`; or drain `StdoutPipe` concurrently | **yes** — `Wait` blocks on the I/O goroutine that can't finish | copying goroutine + your writer's buffering | nil Stdin/Stdout/Stderr → `/dev/null`; `ExtraFiles` → fd `3+i`; no blanket CLOEXEC story — you own fds |
| Java | drain all streams concurrently (threads / `CompletableFuture`); `redirectErrorStream(true)`; `Redirect.to(file)/DISCARD/INHERIT` | **yes** — the `Process` Javadoc caution; worked two-pipe deadlock in java.md | none on `Process` streams (raw pipes) | `Redirect.PIPE` default; `Redirect.INHERIT` opt-in per stream |
| Rust | `output()`/`wait_with_output()` (drain both, then reap); `wait()` closes stdin first (EOF signaling) | **yes** — std's own Stdio warning on hand-rolled feed/drain | none (`Output` is raw bytes) | `spawn`/`status` **inherit** stdio, `output` pipes — defaults differ *per method* |
| Node.js | drain via `'data'`/streams, or `exec`/`execFile` buffered capture (removes the deadlock, adds 1 MiB `maxBuffer` truncation) | **yes** — one undrained pipe stalls the child | parent-side Node streams; pipe writes **asynchronous** (vs TTY sync) — the `process.exit` truncation trap | stdio `'pipe'` default; `'inherit'`/numeric fds opt-in; `'ipc'` channel unique to Node |
| OCaml | `open_process*` + read-to-EOF before `close_process*`; `Unix.select` pump for three-channel I/O | **yes** — the documented `open_process_full` deadlock (write stdin while stdout fills) | OCaml `out_channel` **buffered** — "be careful to call `Stdlib.flush`" (documented warning) | **not close-on-exec by default** — `?cloexec:true` or `set_close_on_exec` opt-in, emphatically recommended |

**Asymmetries that bite.**

- *The 64 KiB cliff is universal; the escape hatch is not.* Every chapter
  documents the same kernel fact (Linux default pipe capacity, per pipe(7)/pipe(2))
  and the same two-party deadlock; only Python (`communicate`), Go (writer on
  `Cmd`), Rust (`wait_with_output`), Java (concurrent drain + redirect
  modes), and Node (buffering APIs) ship a library-level fix. C, C++, and
  OCaml give you the parts, not the pattern.
- *Who flushes your data.* OCaml's `exit` flushes channels **first** (§2);
  C/C++ flush stdio inside `exit` **after** `atexit`; Python flushes
  `sys.stdout/stderr` last, and a failure there silently rewrites your status
  to **120**; Rust's `BufWriter` flush is a **drop** side effect — so it runs
  on unwind/return but not on `process::exit`/`abort`; Go's runtime never
  flushes `bufio` on any path; Node's async pipe writes can be severed by
  `process.exit()`. Same bug report, five root causes.
- *Inheritance philosophy splits three ways.* Python flips POSIX's default
  (non-inheritable fds + `close_fds=True`); C/C++/OCaml keep the POSIX leak
  default with opt-in `CLOEXEC` hygiene; Go, Java, Rust, and Node replace the
  question with per-stream APIs (`ExtraFiles` fd 3+i, `Redirect`, `Stdio`,
  `stdio` arrays) — in which fds beyond 0–2 are *always* an explicit act.
  Fork-copying of unflushed stdio buffers (the double-output bug) is a C/C++
  special: Python/Go/Rust/Node children don't inherit parent stdio buffers
  because the child execs a new image or never runs parent-language cleanup.

## 8. Threading and runtime restrictions

Signal-handler thread restrictions × what happens to other threads on exit
([c.md §4.7/6.5](./c.md), [cpp.md §3.7/6.1–6.2](./cpp.md),
[python.md §4.3/6.5](./python.md), [go.md §3.6/4.1](./go.md),
[java.md §3.3–3.6](./java.md), [rust.md §3.10/4.4](./rust.md),
[nodejs.md §3.9/4.6](./nodejs.md), [ocaml.md §4.4/6.1](./ocaml.md)):

| Language | Handler thread restriction | Other threads at process exit |
|---|---|---|
| C | POSIX: process-directed signals to any thread not blocking; `signal()` in a threaded program is **UB** per ISO C; sigwait-thread is the clean pattern | `exit` from any thread is legal; `atexit` runs **on the exiting thread while others still run** (concurrent `atexit` racing `exit` is unspecified; touching dying objects is UB); last-thread-death ⇒ status 0 |
| C++ | inherits C's model; handler may not touch `thread_local` (§4 list); sigwait-thread via `std::thread` is the idiomatic replacement | `std::exit` from any thread; a **joinable `std::thread` destroyed during main's unwind calls `std::terminate`** — "exit while workers run" can become abnormal termination by object layout; join-then-exit is the documented fix |
| Python | main thread only, at bytecode boundaries (GIL-dependent; build-dependent in the free-threaded build); handler exceptions land "out of thin air" in main | `threading._shutdown` joins all **non-daemon** threads (a hung one hangs exit); **daemon threads killed abruptly — no `finally`, no `__exit__`, no `__del__`** (documented) |
| Go | none for Go code — runtime multiplexes onto a goroutine; cgo handlers need `SA_ONSTACK` (documented interop contract) | `main` return doesn't wait; **an unrecovered panic in any goroutine kills the process** (exit 2); `os.Exit` from any goroutine is a design decision (usually one place) |
| Java | hooks are ordinary threads (concurrent, unspecified order, coded defensively per the API Note); `sun.misc.Signal` dispatches on a fresh max-priority thread | **non-daemon threads keep the JVM alive** — `main` returning is not exit; at JVM termination all threads are frozen mid-instruction: no `finally`, no uncaught handlers, no TWR close (documented); daemons get no grace; virtual threads are daemon by construction |
| Rust | no std API; with FFI the handler lands on any non-blocker thread; `std::thread::spawn` children inherit the pthread mask (OS behavior) | **main-thread termination ends the program**, and remaining threads' destructors "may not be executed" (documented); a spawned-thread panic ends only that thread (`join() → Err`) |
| Node.js | no JS handler runs in the signal frame (libuv converts to an event); **a blocked loop defers signal handling indefinitely** (sync APIs, `spawnSync`) | one JS thread + libuv threadpool; **Workers have no signals** and no `process.abort()`; a Worker dying never ends the process (its own `'exit'` event does not propagate); cluster workers are separate processes |
| OCaml | handlers deferred to safe points; POSIX thread model for systhreads (self-directed to the sender, external to one non-blocker); `Sys.Break` "will arise in any one of the active threads" and keeps arising (documented); which *domain* receives an external signal is source-limited | no `Domain.kill`/`Thread.kill` (verified-absent); `Domain.join` also joins that domain's systhreads; **`Unix.fork` fails if any domain has been spawned** and is documented hazardous with threads (the multicore rule) |

**Asymmetries that bite.**

- *The "who owns shutdown" question has four answers.* Java: non-daemon
  threads own it (they can veto exit indefinitely). Python: the main thread
  owns it (non-daemon join first, daemons slaughtered). Rust: the main thread
  owns it absolutely (its return kills the rest). Go: nobody owns it — any
  goroutine's panic is process-fatal, and only `os.Exit`/`main`-return end the
  show. Writing "portable" supervision code means picking the most restrictive
  model (Java's) and adapting down.
- *Signal handling under load.* Python's and OCaml's deferred models degrade
  the same way: a CPU-bound loop without bytecode boundaries (Python) or
  allocation points (OCaml) delays delivery unboundedly — Python has no pump
  short of reaching a bytecode; OCaml documents `Sys.poll_actions` (5.3) as
  the manual pump ([ocaml.md §4.1](./ocaml.md), `sys.mli`). Go and Node defer
  to schedulers that always run eventually. C/C++/Rust-FFI deliver instantly,
  into the least safe context of the eight.

## 9. Portability and version dependencies

**Windows deltas (brief; each row cites the chapter that verified it).**

| Language | Windows divergence (verified form) | Chapter |
|---|---|---|
| Python | `signal.signal` limited to 7 signals; `os.kill` maps non-CTRL signals to `TerminateProcess`; `kill()` is an alias of `terminate()` on `Popen` | [python.md §4.8/5.8](./python.md) |
| Go | only `os.Interrupt` exists; `Process.Signal(os.Interrupt)` "is not implemented"; no `ExtraFiles`; `SysProcAttr` Linux fields absent; `Command` quoting via `CommandLineToArgvW` with cmd.exe/batch exceptions | [go.md §4.9/5.12](./go.md) |
| Java | console control events (CTRL_C/CLOSE/LOGOFF/SHUTDOWN) drive hooks; CTRL_BREAK → thread dumps; `-Xrs` installs no console handler; no SIGTERM — `destroy()` is terminate-style (check `supportsNormalTermination()`) | [java.md §4.5/5.9](./java.md) |
| Rust | exit codes **not** truncated (`process::exit(0x0100)` is 256); `cmd.exe`/`.bat` argument decoding "vulnerable to malicious input" — `raw_arg` escape hatch; executable resolution order differs | [rust.md §3.3/5.10](./rust.md) |
| Node.js | no signals: `SIGINT`/`SIGTERM`/`SIGKILL` via `kill()` emulate unconditional termination; `SIGBREAK` (Ctrl+Break); `SIGHUP` on console close with ~10 s hard kill; group-kill throws | [nodejs.md §4.2/4.7](./nodejs.md) |
| OCaml | signal mask primitives raise `Invalid_argument`; `Unix.kill` emulates only `sigkill` → child exits with code **1067** (changed in 5.5 — previously 0); `Unix.fork` raises `Invalid_argument` | [ocaml.md §4.3/5.4/5.1](./ocaml.md) |
| C / C++ | chapters are Linux/POSIX-scoped; C23/C++23 wording is platform-neutral but the process layer cited (fork/exec/wait/sigaction) is the POSIX substrate | [c.md](./c.md), [cpp.md](./cpp.md) |

**Version-gated features** (each verified by the named chapter; the entry
point for the underlying official source is that chapter's References).

| Feature | Since | Verified by |
|---|---|---|
| POSIX `_Fork` (AS-safe fork), `FD_CLOFORK`, `WCOREDUMP` standardization | POSIX.1-2024 (Issue 8) | [c.md §5.1/5.9/5.3](./c.md) |
| `close_range(2)` | Linux 5.9 | [c.md §5.9](./c.md) |
| C23 `[[noreturn]]`, library renumbering (7.22→7.24) | C23 (N3220) | [c.md §1.5](./c.md) |
| Python: PEP 446 non-inheritable fds / PEP 475 EINTR retry | 3.4 / 3.5 | [python.md §5.3/4.4](./python.md) |
| Python `Popen(process_group=)` | 3.11 | [python.md §1.10/5.4](./python.md) |
| Python pidfd-based `wait(timeout)` on Linux ≥ 5.3 | 3.15 | [python.md §1.10/5.6](./python.md) |
| `os.fork()` DeprecationWarning in threaded processes | 3.12 | [python.md §1.10/6.2](./python.md) |
| Go `signal.NotifyContext` / `exec.ErrDot` / `Cmd.Cancel`+`WaitDelay`+`ErrWaitDelay` | 1.16 / 1.19 / 1.20 | [go.md §1.8/4.3/5.5](./go.md) |
| Go `GODEBUG=execwait=2` leak detection | 1.20 | [go.md §5.3](./go.md) |
| Java `Process.onExit`, `ProcessHandle`, `Redirect.DISCARD` | 9 | [java.md §1.11/5.5](./java.md) |
| Java finalization deprecated for removal (JEP 421; `finalize` still present in 25) | 18 | [java.md §1.11/1.8](./java.md) |
| Java `waitFor(Duration)` / no-pin `synchronized` (JEP 491) / flexible main (JEP 512) | 24 / 24 / 25 | [java.md §1.11](./java.md) |
| Rust `Termination`/`ExitCode`, `ExitCode: Default` | 1.61 / 1.75 | [rust.md §1.8/3.2/3.4](./rust.md) |
| Rust `CommandExt::process_group` | 1.64 | [rust.md §1.8/5.7](./rust.md) |
| Rust `ExitStatusExt::{core_dumped, stopped_signal, continued}` | 1.58 | [rust.md §5.3](./rust.md) |
| Node `timeout` option / `AbortSignal` / abort-specific `killSignal` | v15.13.0/v14.18.0 / v15.5.0 / v15.11.0 | [nodejs.md §5.2/5.10](./nodejs.md) |
| Node `util.convertProcessSignalToExitCode` / DEP0190 (args + `shell:true`) | v24.14.0 / v23.11.0/v22.15.0 | [nodejs.md §5.12/1.10](./nodejs.md) |
| OCaml safe-point pump `Sys.poll_actions` / typed `Sys.signal` + `Unix.sigwait` + `sigio`/`sigwinch` | 5.3 / 5.4 | [ocaml.md §1.11/4.3](./ocaml.md) |
| OCaml `Unix.unsetenv`; `Unix.kill` Windows → 1067; `Mutex`/`Condition`/`Semaphore` promoted to Stdlib | 5.5 | [ocaml.md §1.11](./ocaml.md) |

## Recorded discrepancies between chapters

Per the grounding rule, conflicts are stated rather than resolved:

1. **Rust chapter vs. its own sibling.** rust.md explicitly corrects the
   older exit/signal-scoped Rust chapter on three items: `CommandExt::setsid`
   and `chroot` (and `groups`) are **nightly-only** on the current build
   (the sibling listed them as available); `before_exec` is deprecated-since-
   1.37 in favor of `unsafe pre_exec`; and `process::exit` runs C `atexit`/
   `fini` per the current documented implementation. Where the two disagree,
   rust.md (std 1.99.0) is authoritative for this part.
2. **Java signal-death status is undocumented by design** (ledger PL-JV-073,
   source-limited): the 128+N value comes from `jdk-25+36` source, while
   Python/Node/Rust document their own encodings. This comparison labels the
   Java row implementation-tier, not because the behavior is secret, but
   because the *specification* is silent.
3. **OCaml native SIGSEGV→`Stack_overflow`** conversion is source-limited in
   5.5.1 (`fail_nat.c` references a handler `signals_nat.c` no longer
   contains — ledger PL-OC-035); ocaml.md and this chapter claim only the
   C-level consequence (uncaught ⇒ exit 2).
4. **glibc manual unreachable** for both C-layer chapters (c.md, cpp.md):
   glibc-behavior claims are anchored in man-pages 6.19 pages instead, and
   ledger-c marks the affected rows. cpp.md additionally substituted N4950
   for cppreference (blocked) — a *stronger* source, noted for transparency.

## Related Topics

- Part hub and ledger schema: [./index.md](./index.md) — the G4 ledger status
  vocabulary (`documented`/`source-limited`) used throughout this chapter.
- The exit/signal-scoped comparison — status decoding, `128+N`, per-signal
  defaults, shell interplay — lives in
  [../../linux/process-exit-signal/languages/comparison.md](../../linux/process-exit-signal/languages/comparison.md);
  this chapter's §6 deliberately *relates* to it rather than repeating the
  decoder tables.
- Evidence-first attribution of a child's death (raw wait-status →
  `waitid`/`siginfo_t` → external observation):
  [../../linux/process-exit-signal/troubleshooting/decision-tree.md](../../linux/process-exit-signal/troubleshooting/decision-tree.md).
- Folklore values (137, 143, 134, 126/127) with their actual guarantees:
  [../../linux/process-exit-signal/troubleshooting/common-status-values.md](../../linux/process-exit-signal/troubleshooting/common-status-values.md).
- Per-language deep dives: the eight chapters linked from
  [§1–§9](#1-normal-return-and-explicit-process-termination) above; the OS
  substrate beneath every row: [./c.md](./c.md).

## References

Primary-source sets as declared by each chapter (all retrieved 2026-10; the
per-claim anchors are in the chapters themselves):

- **C** ([c.md](./c.md)): ISO/IEC 9899:2017 draft
  [N2310](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n2310.pdf) + C23
  [N3220](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n3220.pdf) + C99
  [N1256](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1256.pdf)
  (open-std.org); POSIX.1-2024 / Issue 8
  ([pubs.opengroup.org/onlinepubs/9799919799](https://pubs.opengroup.org/onlinepubs/9799919799/));
  Linux man-pages 6.19 ([man7.org/linux/man-pages](https://man7.org/linux/man-pages/),
  2026-06-05); glibc 2.44 version per [sourceware.org/glibc](https://sourceware.org/glibc/)
  (glibc manual unreachable — man-pages-anchored instead).
- **C++** ([cpp.md](./cpp.md)): ISO C++23 DIS
  [N4950](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2023/n4950.pdf)
  (open-std.org) with C++26 working-draft cross-checks
  ([eel.is/c++draft](https://eel.is/c++draft/), generated 2026-08-23);
  POSIX.1-2024 ([9799919799](https://pubs.opengroup.org/onlinepubs/9799919799/));
  man-pages 6.19 ([man7.org](https://man7.org/linux/man-pages/));
  GCC 14.2.0 libstdc++ headers ([gcc.gnu.org](https://gcc.gnu.org/));
  en.cppreference.com Cloudflare-blocked at retrieval — signatures
  transcribed from N4950.
- **Python** ([python.md](./python.md)): CPython 3.15.0 documentation
  ([docs.python.org/3](https://docs.python.org/3/): [sys](https://docs.python.org/3/library/sys.html),
  [atexit](https://docs.python.org/3/library/atexit.html),
  [signal](https://docs.python.org/3/library/signal.html),
  [subprocess](https://docs.python.org/3/library/subprocess.html),
  [os](https://docs.python.org/3/library/os.html),
  [threading](https://docs.python.org/3/library/threading.html),
  [multiprocessing](https://docs.python.org/3/library/multiprocessing.html),
  [asyncio](https://docs.python.org/3/library/asyncio.html)); CPython source
  ([github.com/python/cpython](https://github.com/python/cpython):
  `pylifecycle.c`, `subprocess.py`, `threading.py`); PEPs
  [442](https://peps.python.org/pep-0442/),
  [446](https://peps.python.org/pep-0446/),
  [475](https://peps.python.org/pep-0475/).
- **Go** ([go.md](./go.md)): Go 1.27.2 per the [go.dev/dl JSON
  feed](https://go.dev/dl/?mode=json); [pkg.go.dev](https://pkg.go.dev/)
  doc comments ([os](https://pkg.go.dev/os),
  [os/exec](https://pkg.go.dev/os/exec),
  [os/signal](https://pkg.go.dev/os/signal),
  [runtime](https://pkg.go.dev/runtime),
  [syscall](https://pkg.go.dev/syscall),
  [log](https://pkg.go.dev/log),
  [context](https://pkg.go.dev/context)) fetched at tag `go1.27.2`; Go
  [release notes](https://go.dev/doc/devel/release) (1.14/1.16/1.19/1.20/
  1.22/1.25); `syscall/exec_linux.go` for implementation facts
  ([go source](https://github.com/golang/go/tree/master/src/syscall)).
- **Java** ([java.md](./java.md)): JDK 25 Javadoc
  ([docs.oracle.com/en/java/javase/25](https://docs.oracle.com/en/java/javase/25/));
  [JLS SE 25](https://docs.oracle.com/javase/specs/jls/se25/html/index.html);
  [`java` command manual](https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html);
  JEPs [395](https://openjdk.org/jeps/395), [409](https://openjdk.org/jeps/409),
  [421](https://openjdk.org/jeps/421), [444](https://openjdk.org/jeps/444),
  [491](https://openjdk.org/jeps/491), [512](https://openjdk.org/jeps/512);
  OpenJDK `jdk-25+36` source
  ([github.com/openjdk/jdk](https://github.com/openjdk/jdk):
  ProcessImpl.java, ProcessHandleImpl*.c, sun/misc/Signal.java,
  Integer.java); man-pages [exit(3)](https://man7.org/linux/man-pages/man3/exit.3.html).
- **Rust** ([rust.md](./rust.md)): std 1.99.0 docs
  ([doc.rust-lang.org/std](https://doc.rust-lang.org/std/):
  [process](https://doc.rust-lang.org/std/process/index.html),
  [panic](https://doc.rust-lang.org/std/panic/index.html),
  [thread](https://doc.rust-lang.org/std/thread/index.html),
  [os::unix::process](https://doc.rust-lang.org/std/os/unix/process/index.html));
  Rust [Reference](https://doc.rust-lang.org/reference/); Cargo Book
  ([panic strategy](https://doc.rust-lang.org/cargo/reference/profiles.html));
  std source ([rt.rs](https://github.com/rust-lang/rust/blob/master/library/std/src/rt.rs),
  [sys/pal/unix/mod.rs](https://github.com/rust-lang/rust/blob/master/library/std/src/sys/pal/unix/mod.rs))
  for the 101/SIGPIPE numeric anchors.
- **Node.js** ([nodejs.md](./nodejs.md)): nodejs.org/docs/latest-v24.x/api
  ([process](https://nodejs.org/docs/latest-v24.x/api/process.html),
  [child_process](https://nodejs.org/docs/latest-v24.x/api/child_process.html),
  [worker_threads](https://nodejs.org/docs/latest-v24.x/api/worker_threads.html),
  [cluster](https://nodejs.org/docs/latest-v24.x/api/cluster.html),
  [events](https://nodejs.org/docs/latest-v24.x/api/events.html),
  [os](https://nodejs.org/docs/latest-v24.x/api/os.html),
  [util](https://nodejs.org/docs/latest-v24.x/api/util.html),
  [cli](https://nodejs.org/docs/latest-v24.x/api/cli.html),
  [modules/esm](https://nodejs.org/docs/latest-v24.x/api/esm.html));
  event-loop guide (nodejs.org/learn); libuv 1.52.1 docs
  ([docs.libuv.org](https://docs.libuv.org/) — threadpool);
  [nodejs.org/dist/index.json](https://nodejs.org/dist/index.json) for the
  version declaration.
- **OCaml** ([ocaml.md](./ocaml.md)): OCaml 5.5.1 source tree
  ([github.com/ocaml/ocaml](https://github.com/ocaml/ocaml/tree/5.5.1) tag
  `5.5.1`: stdlib/*.mli, otherlibs/unix/unix.mli,
  otherlibs/systhreads/thread.mli, runtime/*.c);
  [ocaml.org/manual/5.5](https://ocaml.org/manual/5.5/) (language manual +
  [intfc.html](https://ocaml.org/manual/5.5/intfc.html) +
  [runtime.html](https://ocaml.org/manual/5.5/runtime.html));
  [ocaml.org/releases/latest](https://ocaml.org/releases/latest).
- **Exit/signal part sources leaned on**: the Linux part's per-language
  chapters (`../../linux/process-exit-signal/languages/{c,cpp,python,go,java,
  rust,nodejs,ocaml}.md`) — cited by the language chapters above as their
  "decoder ring" siblings (e.g. LG-JA-005 for the Java 128+N conclusion,
  LG-OC-* for OCaml status conventions) — plus the troubleshooting decision
  tree and common-status-values pages linked in Related Topics.
