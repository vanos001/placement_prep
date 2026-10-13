# Cross-Language Comparison: Exit, Signals, and Process Lifecycle

This chapter compares the eight language chapters of this part —
[C](./c.md), [C++](./cpp.md), [Rust](./rust.md), [Go](./go.md),
[Python](./python.md), [Java](./java.md), [Node.js](./nodejs.md),
[OCaml](./ocaml.md) — along the nine dimensions that matter when the same
program must behave the same way regardless of implementation language
(XC-001..XC-009). Every claim is anchored in the cited documentation of the
language(s) involved; URLs are those of the sibling chapters' References
sections, spot-verified again for the specific statements made here
(retrieved 2026-10). Behavior that a language's documentation does not
guarantee is marked **impl** (implementation behavior) rather than stated as
fact.

Three recurring conclusions:

1. **Only the OS contract is shared.** The kernel's wait-status encoding, the
   8-bit truncation, the signal table, and `execve`'s disposition rules
   (man 7 `signal`) are identical for every language. Everything above that —
   what "return from main" cleans up, which code an uncaught exception
   produces — is per-runtime.
2. **The default exit codes for failure differ by language** (1, 2, 101, 134,
   unspecified) — a monitoring system keyed to "exit 1 = error" is wrong for
   half of them.
3. **Signal delivery is increasingly runtime-mediated.** C and C++ expose the
   kernel's async-signal-safety rules directly; Go, Python, Node.js, Java,
   and OCaml all defer handler execution into normal program flow, each with
   different latency and threading restrictions.

---

## XC-001 Normal return vs. explicit termination

"Return from `main`" is the one path every language defines — and they define
it *differently*.

| Language | "Return from main" means… | Explicit exits | What the explicit exit skips |
|---|---|---|---|
| C | A return from the initial call to `main` is equivalent to `exit(value)`; falling off the end is `exit(0)` (N1570 §5.1.2.2.3) | `exit`, `_Exit`, `quick_exit`, `abort` | `_Exit`/`quick_exit` skip `atexit` + flush; `abort` skips everything (§7.22.4) |
| C++ | Normal function termination — `main`'s automatic objects are destroyed — then `std::exit(returned)` ([basic.start.main]) | `std::exit`, `std::_Exit`, `std::quick_exit`, `std::abort` | `std::exit` does **not** unwind: automatic objects of active frames are not destroyed; `_Exit`/`abort` skip static-object destruction too |
| Rust | `main`'s return type implements `Termination::report() -> ExitCode` (1.61); `()` → `EXIT_SUCCESS` | `std::process::exit(code)`, `std::process::abort()` | `exit`/`abort` run **no destructors on any thread**; buffered writers never flush (std `process::exit`) |
| Go | `main` returns → deferred functions run in reverse order, then exit 0 (spec, *Defer statements*) | `os.Exit(code)`, `log.Fatal*` (= `os.Exit(1)`), `panic` | `os.Exit` is immediate: "deferred functions are not run" (pkg.go.dev/os#Exit) |
| Java | `main` returning (or the last non-daemon thread ending) initiates the *shutdown sequence*: hooks run concurrently in unspecified order, then the JVM stops abruptly | `System.exit(n)`, `Runtime.exit(n)`, `Runtime.halt(n)` | At JVM termination "finally clauses are not executed; uncaught exception handlers are not run" (Runtime Javadoc); `halt` skips the whole hook sequence |
| Python | Module code completing → implicit `exit 0`; `sys.exit(n)` raises `SystemExit(n)` which propagates like any exception (honors `finally`, catchable) | `os._exit(n)` | `os._exit` skips `atexit`, stdio flushing, interpreter finalization ("without calling cleanup handlers, flushing stdio buffers") |
| Node.js | No `main`: the process exits 0 "when no more async operations are pending" (event loop drains, after `'beforeExit'`) | `process.exit([code])`, `process.exitCode = n`, `process.abort()` | `process.exit` is synchronous: pending async work incl. stdout writes is lost; `'exit'` listeners do run |
| OCaml | Top-level phrase completes → implicit `exit 0` | `Stdlib.exit n`, `Unix._exit n` | `Unix._exit` runs no `at_exit`, flushes nothing, does not finalize the C runtime (Unix docs) |

The asymmetries worth internalizing:

- **C++ is the only language where return-from-main and the explicit exit
  differ in *scope*.** `return` from `main` destroys `main`'s stack objects;
  `std::exit(0)` called from the same place does not — it only destroys
  static/thread-local storage objects. A C-style `std::exit(err)` inside a
  RAII code path leaks everything on the stack above it (cpp.md §1.2).
- **Rust and Java treat "main returns" as a *protocol*, not a variable.**
  Rust's `Termination` (since 1.61) converts `Result`/`ExitCode` to a status;
  Java has no equivalent — the status of the threads-just-ended path is
  **unspecified** (only "by convention, nonzero indicates abnormal
  termination", `System.exit` docs), so an application needing a specific
  status must call `System.exit` explicitly (java.md §1.7).
- **Python's `sys.exit` is an exception, not a syscall.** `except
  Exception:` does not catch it (`SystemExit` inherits `BaseException`),
  but `except:` or `except BaseException:` cancels the exit — and `sys.exit`
  raised in a non-main thread only terminates that thread.
- **Node has two exit channels.** `process.exitCode = n` lets the loop drain
  (flushing async stdout); `process.exit(n)` overrides it and truncates
  pending output — the documented "print usage then `process.exit()`" bug
  (process docs, §1.2 of nodejs.md).
- **Go's `os.Exit` range note is new-ish but universal advice:** "For
  portability, the status code should be in the range [0, 125]" (pkg.go.dev/
  os#Exit) — 126/127 are shell reservations, 128+N is the signal band.

Sources: N1570 §5.1.2.2.3/§7.22.4 ([c.md](./c.md) §1.1–1.2);
[basic.start.main]/[basic.start.term] via cppreference
([cpp.md](./cpp.md) §1.1); std `process::exit`/`Termination` (verified this
session: "no destructors on the current stack or any other thread's stack
will be run"); go.dev/ref/spec + pkg.go.dev/os#Exit (verified quote);
Runtime/System Javadoc (quoted in java.md §1.1–1.2); docs.python.org
`sys.exit`/`os._exit`; nodejs.org process docs; ocaml.org Stdlib/Unix docs.

---

## XC-002 Cleanup guarantees per termination path

One table, rows = the five termination paths every runtime has, columns =
the eight languages. Cells name the cleanup machinery that **runs** on that
path. "—" = the language has no such mechanism on that path; "impl" =
implementation-defined/undocumented.

| Path | C | C++ | Rust | Go | Java | Python | Node.js | OCaml |
|---|---|---|---|---|---|---|---|---|
| Normal return | `atexit` LIFO + stdio flush/close (N1570 §7.22.4.4) | auto objects of `main` + static/thread-local dtors + `atexit` + stream flush | `Drop` on all locals in scope | defers (current goroutine) | shutdown hooks (unspecified order) | `atexit` LIFO, non-daemon-thread join, stdio flush; flush failure ⇒ status 120 | `'beforeExit'`/`'exit'` listeners, async stdout drained | `flush_all` + `Domain.at_exit` + `at_exit` LIFO |
| Explicit exit | `exit`: same as return-row; `_Exit`/`quick_exit`: only `at_quick_exit` list; nothing else | `std::exit`: static dtors + `atexit` + flush (no stack unwind); `quick_exit`: only `at_quick_exit`; `_Exit`: none | `process::exit`: none; `process::abort`: none | `os.Exit`/`log.Fatal`: none | `System.exit`/`Runtime.exit`: hooks run; `Runtime.halt`: none | `sys.exit`: full shutdown (`finally`, `atexit`); `os._exit`: none | `process.exit`: `'exit'` listeners only; `process.abort()`: none | `exit`: full list; `Unix._exit`: none |
| Uncaught exception / panic | n/a (no exceptions) | unwind (auto dtors) up to `terminate`; then default handler → `std::abort` — atexit/static dtors **not** run | unwind runs `Drop` on the panicking thread; then exit 101 (main thread) | defers of the panicking goroutine run, then exit 2 | uncaught-exception handler runs, thread dies; **process survives** unless it was the last non-daemon thread | `finally` blocks and `atexit` run, traceback printed, exit 1 | `'uncaughtException'` default: print + exit 1 (overrides `exitCode`) | `at_exit` runs *before* the uncaught-exception printer; implicit `exit 2` |
| abort/signal death (default action) | kernel kills: no atexit, no flush | same as C | `process::abort()` → SIGABRT; `panic=abort` panics skip `Drop` (hook still runs) | fatal signals exit (some with runtime stack dump); no defers | `kill`ed by signal: no hooks unless SIGINT/SIGTERM/SIGHUP (those *start* the hook sequence) | no `atexit` for unhandled signals (documented); `faulthandler` can still dump tracebacks | no listeners; `SIGINT`/`SIGTERM` get runtime cleanup + re-raise even without a listener | no `at_exit` (documented list is exit/normal/uncaught/`caml_shutdown` only) |
| `_exit`/halt equivalent | `_exit(2)`/`_Exit` | `std::_Exit` | `std::process::exit` | `os.Exit` | `Runtime.halt` | `os._exit` | `process.exit` | `Unix._exit` |

Rows two and five are deliberately the same column family: every runtime
grew a "get out now" primitive, and none of them runs *any* cleanup except
Node's `'exit'` listeners and Java's `halt`-contrast hooks (which `halt`
itself skips). The practical corollary: **code that must survive an
emergency stop belongs in a signal handler, a shutdown hook, or an
`atexit`-family callback — never in a destructor that `exit` would need to
run.**

Buffer-flush behavior deserves its own line: C/C++/OCaml flush stdio on
`exit` (OCaml documents that flush *errors are ignored*); Rust/Go never
flush buffered writers on `exit` (the Go "last log lines missing" bug,
go.md §1.1); Python flushes and, uniquely, **overrides your exit status
with 120 if the flush fails** (`sys.exit` docs, *Changed in 3.6*); Node
loses async stdout writes on `process.exit` (docs-quoted truncation
hazard).

Sources: [c.md](./c.md) §1.4 table; [cpp.md](./cpp.md) §1.3; rust.md §1.6;
go.md §1.2; java.md §1.1/§1.9; python.md §1.4–1.6; nodejs.md §1.8;
ocaml.md §1.2/§1.6. Underlying quotes: N1570, cppreference, pkg.go.dev,
docs.oracle.com, docs.python.org, nodejs.org, ocaml.org — all fetched and
verified in the sibling chapters; Rust std pages re-verified this session.

---

## XC-003 Exceptions, panics, fatal errors, abort: the default exit codes

The single most non-portable dimension. Verified defaults:

| Language | Failure mode | Default status seen by parent | Guarantee level |
|---|---|---|---|
| C | — (no exceptions; dereference fault is UB, typically SIGSEGV) | shell sees 139 (128+11) via signal death | OS behavior, not a C-language fact |
| C++ | uncaught exception → `std::terminate` → default handler → `std::abort()` | killed by SIGABRT → **134** in shells' 128+6 convention (glibc) | impl (C++ standard: impl-defined unsuccessful status; 134 is a convention) |
| Rust | `panic!` unwinds off `main`, uncaught | **101** (std source `library/std/src/rt.rs`; docs say only "non-zero") | impl-but-stable (docs: non-zero) |
| Rust | `panic = "abort"` profile, or `process::abort()` | SIGABRT → 134 convention | impl (Unix abort path) |
| Go | unrecovered `panic` (any goroutine) | **2** + goroutine stack dump (runtime docs, GOTRACEBACK section — verified quote this session) | documented |
| Go | synchronous fault (`SIGSEGV`/`SIGFPE`/`SIGBUS` from execution) | converted into a run-time panic → 2 | documented (os/signal default table) |
| Java | uncaught exception on `main`/last thread | **1** (launcher behavior) | impl — JDK docs specify no status |
| Python | unhandled ordinary exception | **1** + traceback (CPython `pythonrun.c`) | impl (docs promise only exit) |
| Python | unhandled `KeyboardInterrupt` (Ctrl-C) | **130** — CPython resets SIGINT to default and re-raises (`Modules/main.c::exit_sigint`) | impl, not a language guarantee |
| Python | stdio flush error during shutdown after `SystemExit` | **120**, overriding the requested status | documented (`sys.exit`, 3.6+) |
| Node.js | `'uncaughtException'`, no handler | **1**, "overriding any previously set `process.exitCode`" | documented (process docs) |
| Node.js | unhandled rejection, default `throw` mode (Node 15+) | feeds the exit-1 path | documented |
| Node.js | fatal V8 error | **5** (documented exit-codes table) | documented |
| OCaml | uncaught exception | **2** — "An implicit `exit 2` is performed if the program terminates early because of an uncaught exception" (Stdlib docs) | documented |
| OCaml | raising the predefined `Exit` exception uncaught | also 2 — `raise Exit` sets no status | documented (a common C-ism bug) |
| all | `abort()`-family (C `abort`, Python `os.abort`, Node `process.abort`, Rust `process::abort`, Go runtime `SIGABRT` default) | SIGABRT → 134 convention; core dump possible | OS + impl |

Non-equivalences to call out in cross-language tooling:

- **Rust 101 and Go 2 look "wrong" to a 1-based monitor but are the
  documented failure codes** of those runtimes; conversely Java's 1 and
  Python's 1 are implementation behavior the docs never promise.
- **C++'s 134 is not an exit code at all** — the process died by signal 6;
  a parent that only reads `WEXITSTATUS` on a raw wait status (Java does
  this) reports 134, while Node reports `(code=null, signal='SIGABRT')`.
  See XC-006.
- **OCaml's 2 collides with two other documented 2s**: the shell's
  "builtin misuse" reservation (Node's docs literally say "reserved by
  Bash for builtin misuse") and `grep`'s error code. Status 2 therefore
  cannot be interpreted without knowing the producer.
- Python is the only runtime that can **upgrade** your status silently
  (120 on flush failure).

Sources: quotes verified as marked — Rust `rt.rs` fact and Go runtime
"exit code 2" re-verified this session (doc.rust-lang.org/std, pkg.go.dev/
runtime); Node exit-codes table and OCaml Stdlib sentence quoted from the
cached official docs (nodejs.org/docs/latest-v22.x, ocaml.org/manual/5.2);
CPython paths verified in source per [python.md](./python.md) §1.2/§4.3.

---

## XC-004 Signal registration models

Five distinct models, from raw kernel mapping to full abstraction:

| Model | Languages | Registration | Where your code runs | Restrictions |
|---|---|---|---|---|
| Direct POSIX | C, C++ | `sigaction(2)`/`signal()` | inside the C signal frame | async-signal-safety only; no malloc/stdio/locks; returning from SIGFPE/SIGILL/SIGSEGV handlers is UB (N1570 §7.14.1.1) |
| Runtime-mediated, deferred to safe points | OCaml | `Sys.signal`/`Sys.set_signal` (`Signal_handle f`); `Unix.sigaction` does **not exist** (verified absent in 5.2 and back to 3.12) | at runtime *safe points* (`caml_process_pending_actions`) | allocation delays delivery; OCaml 5 multicore delivery details undocumented; `Sys.catch_break` for SIGINT |
| Deferred to main thread / VM loop | Python | `signal.signal()` | main thread of main interpreter, "at the next bytecode instruction" | only the main thread may install handlers; long C calls delay delivery; locks in handlers can deadlock (docs warning) |
| Channel / event-loop delivery | Go, Node.js | Go: `signal.Notify(ch, sigs…)`, `NotifyContext`; Node: `process.on('SIGTERM', …)` | ordinary goroutine / event-loop callback | Go: any goroutine may read; SIGKILL/SIGSTOP unaffected; Node: main thread only — **Worker threads cannot listen**; listeners only run while the loop runs |
| Shutdown-hook only | Java | `Runtime.addShutdownHook(Thread)` | concurrent threads, unspecified order, once | triggered only for SIGHUP/SIGINT/SIGTERM (java(1) `-Xrs` text); no per-signal handler API exists; no registration after the sequence begins |

The safety contract inverts between the two extremes. In C the *handler* is
the restricted thing (async-signal-safe functions only); in the five
managed runtimes the handler is ordinary code and the *runtime* absorbs the
unsafe work — with the cost that delivery is asynchronous in wall-clock
terms and skippable in pathological cases (a Python regex over a huge body,
a Go goroutine spinning without preemption, a Node process blocked in
`spawnSync` all delay or defer signal handling). Java is the outlier in the
other direction: there is no public API for arbitrary signals at all, and
`-Xrs` disables even the hook path ("signal handlers for these signals
aren't installed", java(1)).

Default-removal semantics also differ. Go's `Notify` "disables the default
behavior for a given set of signals"; Node's docs state a listener's
installation "will remove" the default (so a SIGTERM listener that forgets
to exit turns SIGTERM into a no-op); Python replaces the default with your
handler and nothing else happens on return; Java hooks run *in addition to*
the process eventually dying (the JVM exits after the sequence). Node and
CPython additionally intercept SIGINT/SIGTERM with no listener installed,
perform cleanup, and re-raise — which is why the shell observes 128+N even
for runtimes that technically handle the signal first (nodejs.md §4.3,
python.md §4.3).

Sources: [c.md](./c.md) §4; [cpp.md](./cpp.md) §4; [rust.md](./rust.md) §4
(std has no signal API; `signal-hook`/`tokio::signal` are third-party);
go.md §4.1–4.3; python.md §4.1–4.2; java.md §1.3 + java(1) `-Xrs`;
nodejs.md §4.1–4.3; ocaml.md §4.1–4.2. Kernel baseline: man 7 `signal`
(dispositions per-process; `execve` resets handled → default, leaves
ignored unchanged).

---

## XC-005 Subprocess creation, waiting, cancellation, termination

| Language | Creation API (primary) | Wait / poll | Timeout | Cancellation | Kill |
|---|---|---|---|---|---|
| C | `fork`+`exec*`, `posix_spawn(3)`, `system(3)`, `popen(3)` | `waitpid`/`waitid` (WNOHANG, WNOWAIT, siginfo) | none — hand-rolled (timer + SIGALRM, signalfd) | none — `kill(pid, sig)` | `kill` |
| C++ | *no standard facility* — C/POSIX substrate + `std::system`; third-party (Boost.Process) | as C | none | none | as C |
| Rust | `std::process::Command` (argv array) | `Child::wait`, `try_wait`, `wait_with_output` | none in std — timer thread + `kill` | none in std (third-party tokio: cancellation tokens, `kill_on_drop`) | `Child::kill` (SIGKILL) |
| Go | `os/exec.Cmd`, `CommandContext` (1.7) | `Run`/`Wait` (reaps + I/O) | `context` deadline + `WaitDelay` (1.20) | `context` cancel → `Cmd.Cancel` (default `Kill`) | `Process.Signal`, `Process.Kill` |
| Java | `ProcessBuilder` (argv array; `startPipeline`), legacy `Runtime.exec(String)` deprecated | `waitFor()`, `waitFor(t,u)`, `onExit()` future (9+) | `waitFor(timeout)` returns false — you `destroy()` | thread interruption of the waiter only; then `destroy()`/`destroyForcibly()` | `destroy` (SIGTERM), `destroyForcibly` (SIGKILL), `ProcessHandle.descendants()` tree walks |
| Python | `subprocess.Popen`/`run` (argv array; `shell=True` opt-in) | `wait`, `poll`, `communicate` | `run(timeout=…)` kills and reaps; `Popen.wait(timeout=…)` raises and leaves child running | none built-in — compose `send_signal` | `terminate()` SIGTERM, `kill()` SIGKILL |
| Node.js | `spawn`/`execFile` (argv), `exec` (**shell**), `fork` (IPC) | `'exit'`/`'close'` events, `spawnSync` result | `timeout` option (v15.13/14.18) → `killSignal` | `AbortSignal` option (v15.5/14.17) | `subprocess.kill([signal])` (SIGTERM default) |
| OCaml | `Unix.create_process` (argv + 3 fds), `Unix.system`/`Sys.command` (**shell**), `open_process*` | `Unix.wait`/`waitpid` (WNOHANG, WUNTRACED); `close_process*` reaps | none documented — `Unix.alarm` + handler + kill, hand-rolled | none | `Unix.kill` |

**Shell-vs-argv defaults — the injection-relevant split:**

- **Shell-string by default:** C `system`/`popen`, C++ `std::system`,
  Node `exec`/`execSync` (and any Node API with `shell: true`), OCaml
  `Sys.command`/`Unix.system`/`open_process*`. Node's docs are the bluntest:
  "Never pass unsanitized user input to this function."
- **Argv-array by default:** Go `os/exec`, Rust `Command`, Java
  `ProcessBuilder`, Python `subprocess` ("this library will not implicitly
  choose to call a system shell" — subprocess docs), Node
  `spawn`/`execFile`, OCaml `create_process`/`open_process_args*`
  (4.08+). Running a shell is always an explicit act:
  `exec.Command("sh","-c",s)`, `Command::new("sh").arg("-c").arg(s)`,
  `Popen(s, shell=True)`.
- Java's `Runtime.exec(String)` sits between: no shell, but its implicit
  whitespace tokenization corrupts arguments with spaces — the documented
  reason it is deprecated in JDK 21.
- POSIX-level escape hatches: C's `posix_spawn` with file actions avoids
  multithreaded-`fork` hazards (recommended in both C and C++ chapters);
  Python documents `preexec_fn` as "NOT SAFE… in the presence of threads"
  and offers `start_new_session`/`process_group` (3.11) instead; Rust's
  equivalent is `CommandExt::pre_exec` (unsafe) and `process_group` (1.64).

**Escalation patterns.** Only three ecosystems give you a documented
TERM-then-KILL ladder: Go (`Cancel` set to SIGTERM + `WaitDelay` to
escalate), Java (`waitFor` → `destroy` → `destroyForcibly`), Node
(`killSignal` for timeout/abort). Everywhere else the ladder is
hand-rolled — including in C, where a deadline timer, `kill(SIGTERM)`,
second timer, `kill(SIGKILL)`, `waitpid` is the pattern.

Sources: [c.md](./c.md) §5; [cpp.md](./cpp.md) §5.1 (documented gap);
rust.md §5.1–5.2; go.md §5.4 (CommandContext/Cancel/WaitDelay quotes);
java.md §5 (ProcessBuilder, deprecation quote); python.md §5.1/§5.3/§5.4;
nodejs.md §5.1–5.6 (version markers v14.17/15.5/15.13); ocaml.md §5.

---

## XC-006 Child-status representations

How each API hands you the fact "the child died by signal 11" — and what is
lost:

| Language | Representation | Signal death looks like | Lossless? |
|---|---|---|---|
| C / C++ (POSIX) | 16-bit wait status `int` + decode macros `WIFEXITED`/`WEXITSTATUS`/`WIFSIGNALED`/`WTERMSIG`/`WCOREDUMP`/`WIFSTOPPED` | `WIFSIGNALED(st)` true, `WTERMSIG(st)==11`, `WCOREDUMP(st)` maybe | **yes** — raw encoding, plus stop/continue via `waitid` `si_code` |
| Rust | `ExitStatus` + `code() -> Option<i32>`; Unix-only `ExitStatusExt`: `signal()`, `core_dumped()`, `into_raw()` | `code() == None`, `signal() == Some(11)` | yes on Unix (`into_raw` exposes everything) |
| Go | `ProcessState.ExitCode() int` (**−1 when signaled**); `Sys().(syscall.WaitStatus)` → `Signaled()`/`Signal()`/`CoreDump()`/`Stopped()`/`TrapCause()` | `ExitCode()==-1`; full detail only via the `WaitStatus` type assertion | yes via `Sys()`; `ExitCode()` alone is lossy (−1 also merely means "not exited normally") |
| Java | `exitValue()`/`waitFor()` plain `int` | **undocumented** — HotSpot reports 128+N (143/137), marked impl | **no** — the JDK docs define nothing for signal death |
| Python | `returncode: int`; "A negative value -N indicates that the child was terminated by signal N (POSIX only)" (subprocess docs) | `returncode == -11` | yes for exit/signal (core-dump flag not exposed) |
| Node.js | async: `'exit' (code, signal)` — "One of the two will always be non-null"; sync: `{status, signal}` | `code === null`, `signal === 'SIGSEGV'` | yes (names, not numbers) |
| OCaml | `Unix.process_status = WEXITED of int \| WSIGNALED of int \| WSTOPPED of int` | `WSIGNALED 11` | yes incl. stopped (which Python/Node hide); core-dump flag not exposed |

Cross-checks that catch real bugs:

- A Java parent around a segfaulting C helper sees `139`, a Node parent sees
  `(null, 'SIGSEGV')`, a Python parent sees `-11`, a Go parent's
  `ExitCode()` reports `-1` — four different encodings of one kernel event,
  all documented except Java's.
- The 8-bit truncation applies at the *exit* end everywhere
  (`exit(256)` ≡ `exit(0)`; man 2 `_exit` "status & 0xFF"), but signal
  death never enters the 8-bit field at all — it lives in the upper bits of
  the wait status that only the W-macros (or typed equivalents) decode.
  That is why "128+N" exists only in shell convention (XC-003 of
  [../troubleshooting/common-status-values.md] coverage) and why APIs that
  expose the raw status are strictly more informative than exit-code-only
  APIs.
- Stop/continue reporting: only C's `waitid` (`CLD_STOPPED`), the POSIX
  `WUNTRACED`/`WCONTINUED` options, Go's `WaitStatus.Stopped()`, and OCaml's
  `WSTOPPED` (with `WUNTRACED`) surface it; Python, Node, Java, and Rust's
  documented surfaces never report a stopped child.

Sources: man 2 `wait`/`waitid`; [c.md](./c.md) §3.3/§5.2;
rust.md §5.2 (`ExitStatusExt`); go.md §5.3/§5.5; java.md §5.4 (verification
result, quoted); python.md §5.2 (−N rule, quoted); nodejs.md §5.3–5.4
(verbatim event contract); ocaml.md §5.2 (variant docs, quoted).

---

## XC-007 Pipe and stream behavior

Every ecosystem documents (or fails to document) the same three hazards:
pipe-buffer deadlock, exit-vs-drain ordering, and fd inheritance.

| Language | Documented deadlock warning | Read-both helper | Exit/flush coupling | fd inheritance default |
|---|---|---|---|---|
| C | none *in an API doc* — `pipe(2)` mechanics; §5.4 rules: close unused ends, two loops | none — `popen` is one-directional | fork duplicates unflushed stdio → child must `_exit`, parent flush discipline | **all fds inherited**; leak hygiene is manual (`close_range`, `posix_spawn_file_actions_addclose`) |
| C++ | as C (`std::system`/`::popen`) | none | same double-flush hazard after fork | as C |
| Rust | §5.3: reading only `stdout` while child floods `stderr` deadlocks | `output()` / `wait_with_output()` read both concurrently | `Child` drop neither kills nor reaps (std docs); `stdin` closed on `wait` → EOF signal | child inherits fds not opened `O_CLOEXEC`; std closes only its own internal fds |
| Go | StdoutPipe: "incorrect to call Wait before all reads from the pipe have completed"; orphaned-pipe case via grandchildren → `WaitDelay` (1.20) closes pipes | `Output()`/`CombinedOutput()` | `Wait` waits for the I/O copy goroutines; buffers must be flushed *before* `os.Exit` | `ExtraFiles`: entry i = fd 3+i; stdio wiring explicit |
| Java | Process docs: "failure to promptly write the input stream or read the output stream of the process may cause the process to block, or even deadlock" | `redirectErrorStream(true)` merges; else two reader threads | streams live in the parent JVM; drain before `waitFor` | `Redirect.INHERIT`/`from`/`to`/`appendTo`; default is PIPE for all three |
| Python | `Popen.wait`: "This will deadlock when using stdout=PIPE or stderr=PIPE and the child process generates enough output…" | `communicate()` (drains both) | `run(timeout)` kills + reaps; `communicate(timeout)` does **not** kill | `close_fds=True` default; `pass_fds` to keep; `restore_signals=True` resets inherited SIG_IGN for SIGPIPE/SIGXFZ (sic)/SIGXFSZ |
| Node.js | consume `child.stdout`/`stderr` when piped; `exec` buffers but `maxBuffer` (1 MiB default) **kills** the child on overflow | `exec`/`execFile` buffered (with maxBuffer ceiling) | `'exit'` fires before stdio closes — `'close'` is the drained signal; `process.exit` can truncate *your own* async stdout | `stdio` directives: `'pipe'`/`'inherit'`/`'ignore'`(/dev/null)/fd numbers |
| OCaml | `open_process_full`: read stdout+stderr to EOF before/while writing stdin; `close_process_*` otherwise never returns | none — explicit interleaving discipline | `exit` flushes all channels (errors ignored); `Unix._exit`/signal death lose buffers | `create_process` wires exactly stdin/stdout/stderr; other fds follow fork semantics |

Two documentable asymmetries: Node is the only runtime that *terminates*
the child when output exceeds a limit (`maxBuffer`), which converts a
deadlock into a truncated-output bug; and Python's `communicate(timeout)`
raises `TimeoutExpired` without killing (the docs tell you to kill and
finish), while `subprocess.run(timeout)` *does* kill — an easy pair to
confuse. The 64 KiB Linux default pipe buffer underlies all of the
blocking arithmetic (see
[../../syscalls/net-ipc/pipe.md](../../syscalls/net-ipc/pipe.md)).

Sources: python.md §5.2 (verbatim wait/communicate quotes); rust.md §5.3;
go.md §5.2 (StdoutPipe contract, WaitDelay); java.md §5.2 (Process quote,
Redirect table); nodejs.md §5.2/§5.4/§5.7; c.md §5.4; ocaml.md §5.5;
cpp.md §5.5.

---

## XC-008 Threading and runtime restrictions

Which thread sees the signal, and what can the rest of the runtime do
about it?

- **C/C++**: dispositions are per-process; masks per-thread. Thread-directed
  delivery (`pthread_kill`/`tgkill`) is fully exposed — the only two
  languages in this set that give you the kernel's model unfiltered. A
  handler installed by any thread handles signals arriving on any thread;
  synchronous faults (SIGSEGV/SIGFPE) are delivered to the faulting thread.
  `signal()` in a multithreaded C program is UB (C11 Annex J rule recorded
  in c.md §1.5).
- **Rust**: `std::process::exit` from any thread kills the whole process
  with no destructor runs; a panic in a spawned thread unwinds only that
  thread and (std docs) the process continues — the asymmetry with Go/Java
  where any uncaught panic/exception in any thread can end the program.
- **Go**: signal delivery is process-scoped via channels — "there is no
  per-goroutine signal API" (go.md §4.2). The runtime installs its own
  handlers at startup, honors inherited SIG_IGN for SIGHUP/SIGINT,
  preserves (and passes on) a non-empty inherited signal mask to children
  of `os/exec` except for the signals it explicitly unblocks (incl. glibc's
  internal 32/33 on Linux) — all documented on pkg.go.dev/os/signal.
- **Python**: "Python signal handlers are always executed in the main
  Python thread of the main interpreter, even if the signal was received in
  another thread" — and only the main thread may install handlers;
  `sys.exit` from a worker thread is thread-scoped. For thread-directed
  control you drop to the POSIX layer: `signal.pthread_sigmask`,
  `signal.pthread_kill`, `signal.sigwait` (documented bindings).
- **Node.js**: signal listeners run on the main thread's event loop only —
  Worker threads cannot register them (documented); a loop blocked in sync
  work delays all signal processing. SIGUSR1 is reserved for the inspector.
- **Java**: shutdown hooks are threads running concurrently in unspecified
  order; after the sequence begins, registration is prohibited, daemon
  threads are cut off without `finally`, and a hook that calls
  `System.exit` deadlocks the shutdown (documented trap in java.md §1.2).
  Runtime exits vs thread exits: a non-daemon thread's uncaught exception
  does not exit the JVM unless it was the last one; any thread can start
  the shutdown via `System.exit`.
- **OCaml**: handlers run at safe points — allocation can delay them
  indefinitely in a compute loop (documented via `caml_process_pending_actions`).
  `Sys.Break` from Ctrl-C "arises in any one of the active threads"
  (multithreaded caveat). OCaml 5: `Unix.fork` fails outright in multicore
  programs and is thread-corrupting with systhreads — the fork-based
  subprocess model of C is effectively unavailable in modern OCaml;
  `create_process` is the supported path.

The GC/ownership interplay shows up in two places: Go's finalizers
(`runtime.SetFinalizer`) have no ordering guarantee relative to exit (and
`os.Exit` skips them), Java's finalization is deprecated for removal (JEP
421) with `Cleaner` as the replacement, and CPython's `__del__`/`atexit`
order is the documented "random order" of module teardown — none of these
mechanisms may own a resource that must be released before the process
dies by signal.

Sources: c.md §6; cpp.md §6; rust.md §1.6/§6; go.md §4.2/§4.3/§1.5;
python.md §4.1–4.2 (verbatim quotes); nodejs.md §4.4; java.md §1.1/§1.5/§6;
ocaml.md §1.7/§4.1; JEP 421.

---

## XC-009 Portability and version dependencies

Version-gated features (verified against each project's docs/release
notes), then the POSIX-only residue:

| Feature | Since | Notes |
|---|---|---|
| Rust `Termination`/`ExitCode` for `main` | 1.61.0 | `ExitCode::from(u8)` for arbitrary codes; docs warn codes are not portable |
| Rust `CommandExt::process_group` | 1.64.0 | Unix-only trait (`std::os::unix::process`) |
| Rust `ExitStatusExt` | 1.0.0 | **Unix-only** — Windows has its own `ExitStatusExt`; `code()` returns `Option` on all platforms |
| Go `CommandContext` | 1.7 | cancellation = kill by default |
| Go `Cmd.Cancel` + `Cmd.WaitDelay` | 1.20 | documented TERM-then-KILL composition; `ErrWaitDelay` |
| Go `signal.NotifyContext` / `Ignore` / `Reset` | 1.16 / 1.5 | context-based signal handling |
| Java `ProcessHandle`, `Process.onExit`, `startPipeline` | 9 | `ProcessHandle.Info` availability platform-dependent (docs) |
| Python `Popen(process_group=)` | 3.11 | `setpgid(0, value)` in the child (POSIX) |
| Python pidfd-based waiting | Linux ≥ 5.3 (docs note) | event-driven waits internally |
| Node `AbortSignal` for child processes | v15.5 / 14.17 | `killSignal` for abort since v15.11/14.18 |
| Node `timeout` child option | v15.13 / 14.18 | plus `killSignal` (SIGTERM default) |
| Node unhandled-rejection default `throw` | Node 15 | previously warn/none |
| OCaml `open_process_args*` + `process_*_pid` | 4.08 | "more robust and more efficient alternative" (Unix docs) |
| OCaml multicore `fork` restriction | 5.x | `Unix.fork` fails with domains spawned |
| `vfork` | removed from POSIX.1-2008 | Linux keeps it; C chapter treats it as a Linux extension |

**Windows-on-std caveats where documented**: Rust's `ExitStatusExt` (signal
numbers, raw wait status) is a Unix extension and the std process docs
explicitly say exit-code meanings/masking are platform-dependent; Go's
`syscall.WaitStatus` is a `syscall` (platform) type — pkg.go.dev renders it
per-OS; Node documents `SIGTERM` as "not supported on Windows" for kills
and approximates signals with console control events; Python's `-N`
returncode rule is marked "(POSIX only)" in the subprocess docs; Java's
`destroy` graceful-vs-forcible split is implementation-dependent per
`supportsNormalTermination()`.

**What remains POSIX-only everywhere** (documented as such per language):
`fork` in-thread hazards and `preexec_fn` restrictions (Python), raw
wait-status decoding (Rust `ExitStatusExt`, Go `syscall.WaitStatus`, C
macros), process groups/sessions beyond the APIs named above, pidfd
(Windows has no analogue), and the 128+N signal-exit band itself — which
POSIX XCU 2.8.2 states as "> 128" and the shells (and Node's docs) spell as
128+N.

Sources: doc.rust-lang.org/std (`Termination`, `ExitCode`, `ExitStatusExt`,
`CommandExt` — re-verified this session); pkg.go.dev (os, os/signal,
os/exec, syscall) + go.dev/doc/go1.20; docs.oracle.com JDK 21 (Process,
ProcessHandle, ProcessBuilder) + JDK 21 release notes for the v9 features;
docs.python.org 3 (subprocess, os, signal); nodejs.org v22 docs (version
markers as shown); ocaml.org 5.2 manual + `unix.mli` history (4.08 markers);
man 7 `signal`, POSIX.1-2017/2024 XCU.

---

## Related Topics

- Language chapters compared here: [C](./c.md) · [C++](./cpp.md) ·
  [Rust](./rust.md) · [Go](./go.md) · [Python](./python.md) ·
  [Java](./java.md) · [Node.js](./nodejs.md) · [OCaml](./ocaml.md)
- Signals: [Standard signals](../signals/standard-signals.md) ·
  [Real-time signals](../signals/real-time-signals.md) ·
  [Async-signal-safety](../interfaces/async-signal-safety.md) ·
  [signal masks](../interfaces/signal-masks.md) ·
  [sigwait/sigsuspend](../interfaces/sigwait-sigsuspend.md) ·
  [signalfd/pidfd](../interfaces/signalfd-pidfd.md)
- Troubleshooting: [Common status values](../troubleshooting/common-status-values.md) ·
  [Decision tree](../troubleshooting/decision-tree.md)
- Deployment targets: [Service managers](../service-managers/index.md) ·
  [Containers](../containers/index.md) ·
  [PID 1 and signals](../containers/pid1-signals.md)
- The exit-status part of this book (lifecycle, 0/128+N/137 conventions) is
  covered in the `exit-status/` chapter of this directory; the shell layer
  that produces 126/127/128+N is in `shells/`.

## References

- ISO C11 draft N1570 §5.1.2.2.3, §7.14.1.1, §7.22.4 —
  https://port70.net/~nsz/c/c11/n1570.html
- ISO C++ standard clauses via cppreference (`std::exit`, `std::terminate`,
  [basic.start.main]/[basic.start.term]) —
  https://en.cppreference.com/w/cpp/utility/program/exit ,
  https://en.cppreference.com/w/cpp/error/terminate
- Rust std (re-verified 2026-10): `std::process::exit`
  (https://doc.rust-lang.org/std/process/fn.exit.html),
  `std::process::Termination`
  (https://doc.rust-lang.org/std/process/trait.Termination.html),
  `std::process::ExitCode`, `std::os::unix::process::ExitStatusExt` —
  https://doc.rust-lang.org/std/
- Rust std source `library/std/src/rt.rs` (exit code 101) —
  https://github.com/rust-lang/rust
- Go: language spec (go.dev/ref/spec), pkg.go.dev/os#Exit (verified quote),
  pkg.go.dev/runtime (GOTRACEBACK, "exits with exit code 2" — verified),
  pkg.go.dev/os/signal, pkg.go.dev/os/exec (WaitDelay), go.dev/doc/go1.20 —
  https://pkg.go.dev/
- Java SE 21: `Runtime` (Shutdown Sequence), `System.exit`, `Process`,
  `ProcessBuilder`, `ProcessHandle`, java command `-Xrs` —
  https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html ,
  https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html ;
  JEP 421 — https://openjdk.org/jeps/421
- Python 3: `sys.exit`, `os._exit`/`os.abort`, `atexit`, `signal`,
  `subprocess` (Security Considerations, wait/communicate warnings),
  PEP 475; CPython 3.13 sources `Modules/main.c`, `Python/pythonrun.c` —
  https://docs.python.org/3/ , https://peps.python.org/pep-0475/
- Node.js v22: `process` (exit codes, `process.exit`, signal events),
  `child_process` (spawn/exec, `'exit'`/`'close'`, maxBuffer, AbortSignal)
  — https://nodejs.org/docs/latest-v22.x/api/process.html ,
  https://nodejs.org/docs/latest-v22.x/api/child_process.html
- OCaml 5.2: Stdlib (`exit`, `at_exit`, implicit exit 0/2), Sys (`signal`,
  `catch_break`), Unix (`_exit`, `system`, `create_process`,
  `open_process*`, `process_status`), Domain (`at_exit`), Printexc —
  https://ocaml.org/manual/5.2/ ; OCaml sources
  https://github.com/ocaml/ocaml (5.2, 4.14, 4.06, 4.02, 4.00, 3.12)
- Linux man-pages (man7.org): `signal(7)` (execve disposition rules —
  verified quote), `wait(2)`, `_exit(2)`, `execve(2)`, `pipe(2)` —
  https://man7.org/linux/man-pages/
- POSIX.1-2017/2024 XCU 2.8 (Exit Status; 126/127; >128 on signal death) —
  https://pubs.opengroup.org/onlinepubs/9699919799/
