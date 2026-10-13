# Rust: Process Termination, Exit Status, and Signals

Rust wraps the OS process model in an ownership discipline: what terminates a
process, what runs destructors (`Drop`), and how exit codes and child-process
statuses are represented are all expressed in types — `Termination`,
`ExitCode`, `ExitStatus`, `Output`. Rust's standard library deliberately
**does not provide a signal-handling API**; that is an ecosystem gap with
consequences documented in §4. This chapter covers Rust 1.61–1.8x era
behavior; version claims are tied to pages on **doc.rust-lang.org** (the
official `std` documentation) retrieved 2026-10, the **Rust Book**, the
**Cargo reference**, and the `std` source where a numeric fact (exit code
101) needed a primary anchor. The Linux/POSIX substrate is covered in
[c.md](./c.md); this chapter names only the deltas.

---

## 1. Syntax and Semantics

### 1.1 Returning from `main`

`main` may return:

- `()` — process exits with a successful status (implicit; the docs describe
  a `()`-returning main as "implicitly ... a successful termination",
  `ExitCode::SUCCESS` page).
- Any type implementing the **`Termination`** trait (since Rust **1.61.0**):

```rust
pub trait Termination {
    fn report(self) -> ExitCode;
}
```

  The docs: "A trait for implementing arbitrary return types in the main
  function. The C-main function only supports returning integers. So, every
  type implementing the Termination trait has to be converted to an integer.
  The default implementations are returning libc::EXIT_SUCCESS to indicate a
  successful execution. In case of a failure, libc::EXIT_FAILURE is returned."
  Implemented for `()`, `ExitCode`, `Infallible`, and
  `Result<T: Termination, E: Debug>` — returning `Err(e)` prints the error
  (via `Debug`) to stderr and exits with a failure status.
- **`ExitCode`** (1.61.0): `pub struct ExitCode(/* private fields */);` with
  `ExitCode::SUCCESS`, `ExitCode::FAILURE` constants and `impl From<u8> for
  ExitCode` for arbitrary codes. The docs warn: "Numeric values used in this
  type don't have portable meanings, and different platforms may mask
  different amounts of them" — on Linux, the low 8 bits, as everywhere else
  ([c.md](./c.md) §3.3).

```rust
fn main() -> ExitCode {
    let n = std::env::args().nth(1)
        .and_then(|s| s.parse::<u8>().ok());
    match n {
        Some(c) if c != 0 => ExitCode::from(c),  // arbitrary 8-bit code
        Some(_) => ExitCode::SUCCESS,
        None => ExitCode::FAILURE,               // libc EXIT_FAILURE path
    }
}
```

### 1.2 `std::process::exit`

```rust
pub fn exit(code: i32) -> !   // since 1.0.0
```

Official description: "Terminates the current process with the specified exit
code. This function will never return and will immediately terminate the
current process. The exit code is passed through to the underlying OS and
will be available for consumption by another process. Note that because this
function never returns, and that it terminates the process, **no destructors
on the current stack or any other thread's stack will be run**. If a clean
shutdown is needed it is recommended to only call this function at a known
point where there are no more destructors left to run; or, preferably, simply
return a type implementing Termination (such as ExitCode or Result) from the
main function and avoid this function altogether" (std `process::exit`).

Consequences: `Drop` impls do not run; buffered writers are never flushed;
locks stay held. `exit` runs from any thread and terminates the whole
process — there is no per-thread `exit` in Rust (thread termination is §6).

### 1.3 `std::process::abort`

```rust
pub fn abort() -> !   // since 1.17.0
```

Official description (std `process::abort`): "Terminates the process in an
abnormal fashion. The function will never return and will immediately
terminate the current process in a platform specific 'abnormal' manner. As a
consequence, no destructors on the current stack or any other thread's stack
will be run, Rust IO buffers (eg, from BufWriter) will not be flushed, and C
stdio buffers will (on most platforms) not be flushed. This is in contrast to
the default behavior of `panic!` which unwinds the current thread's stack and
calls all destructors. When panic='abort' is set ... panic! and abort are
similar. However, **panic! will still call the panic hook while abort will
not**." On Unix this bottoms out in the C `abort(3)` — SIGABRT, possible core
dump (see [c.md](./c.md) §2.1).

### 1.4 Panic strategies: unwind (default) vs. abort

The panic strategy is a **compilation profile setting**, not a language-level
switch. The Cargo reference (`profiles.panics`): "The panic setting controls
the `-C panic` flag which controls which panic strategy to use. The valid
options are: **'unwind'**: Unwind the stack upon panic. **'abort'**:
Terminate the process upon panic." Notes from the same page: with `unwind`,
"the actual value depends on the default of the target platform" (some
targets cannot unwind), and the test harness requires unwind.

- **unwind**: `panic!` unwinds the current thread; **destructors run**;
  `catch_unwind` can stop the unwinding (§2.5); if the panic reaches the main
  thread uncaught, the process exits non-zero.
- **abort**: `panic!` terminates the process immediately; destructors do not
  run; the panic hook still runs first (std `process::abort` docs); there is
  no unwinding and `catch_unwind` cannot catch it.

### 1.5 The panic hook and the exit path

- **`std::panic::set_hook`** (since 1.10.0):
  `pub fn set_hook(hook: Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>)`.
  "The panic hook is invoked when a thread panics, but before the panic
  runtime is invoked. As such, the hook will run with both the aborting and
  unwinding runtimes. The default hook, which is registered at startup,
  prints a message to standard error and generates a backtrace if requested"
  (std `panic::set_hook`).
- **Main-thread panic exit code**: the `std::thread` module docs state "If
  the main thread panics without the panic being caught, the application will
  exit with a non-zero exit code." The *specific* value is 101 — pinned in
  the std runtime source, `library/std/src/rt.rs`: on an uncaught panic from
  `main`, `catch_unwind(main).unwrap_or_else(...)` returns `101` as the
  process exit code (std source, retrieved 2026-10). So a panicking Rust
  program exits with **101**, not 1.
- **`std::panic::catch_unwind`** (since 1.9.0):
  `pub fn catch_unwind<F: FnOnce() -> R + UnwindSafe, R>(f: F) -> Result<R>`
  — "Invokes a closure, capturing the cause of an unwinding panic if one
  occurs. This function will return Ok with the closure's result if the
  closure does not panic, and will return Err(cause) if the closure panics."
  Under `panic=abort` it never sees the panic. The hook still runs before
  `catch_unwind` intercepts.

### 1.6 Ownership, `Drop`, and termination paths

| Path | `Drop` runs? | Panic hook runs? | IO buffers flushed? |
|---|---|---|---|
| return from `main` | yes — locals dropped | n/a | yes (as part of dropping `BufWriter`s etc.) |
| `main` returns `Err` | yes | n/a | yes, then status = failure |
| panic, unwind (default) | yes — unwinding drops frames | yes | yes (by drops) |
| panic, `panic=abort` | **no** | yes | no |
| `std::process::exit` | **no** (current and other threads) | n/a | no |
| `std::process::abort` | **no** | **no** | no |
| uncaught panic in spawned thread | that thread's frames unwind; process continues | yes | n/a |

`std::mem::forget` and `ManuallyDrop<T>` are the library mechanisms to *opt
out* of `Drop` on the normal path — relevant to exit semantics only in that
they remind us `Drop` is a language guarantee scoped to normal and unwind
paths, never to `exit`/`abort`. `mem::forget` is safe (no UB), which is why
Rust can afford destructors-not-run semantics on `exit` without unsafety.

### 1.7 Undefined behavior boundaries

Rust has no UB in "calling exit twice" or "exiting from a handler" — those
are OS-level realities, not language rules. Rust UB is confined to `unsafe`
contract violations (the Rustonomicon domain). Two relevant notes:

- Re-entrant `exit` (e.g. `Drop` impl calling `exit`) simply terminates
  mid-drop; the std docs' "known point with no more destructors to run"
  guidance covers the hazard.
- Hardware faults (SIGSEGV from `unsafe` bugs) are signals from the kernel;
  Rust defines no behavior for them — same implementation consequence framing
  as C ([c.md](./c.md) §1.5).

### 1.8 Common misconceptions

- *"`panic!` skips destructors."* False with the default unwind strategy;
  true only under `panic=abort`.
- *"Rust programs exit with 1 on panic."* They exit with **101** (std source
  `rt.rs`; docs say only "non-zero").
- *"`process::exit` runs `Drop` on other threads before exiting."* False —
  the docs say no destructors on any stack run.
- *"`Child` is killed when dropped."* False (§5.4) — this one bites daemons.

---

## 2. Standard-Library and Runtime API Inventory

All signatures verified against doc.rust-lang.org/std (retrieved 2026-10);
version annotations are the "since" versions printed in those docs.

### 2.1 Termination — `std::process`

| API | Signature | Since | Semantics |
|---|---|---|---|
| `process::exit` | `pub fn exit(code: i32) -> !` | 1.0.0 | immediate termination; no destructors anywhere; code passed to OS |
| `process::abort` | `pub fn abort() -> !` | 1.17.0 | abnormal termination; no destructors; no flush (Rust or C stdio); no panic hook |
| `process::id` | `pub fn id() -> u32` | 1.26.0 | current PID |
| `Termination` | `pub trait Termination { fn report(self) -> ExitCode; }` | 1.61.0 | main's return-type protocol |
| `ExitCode` | `pub struct ExitCode(/* private */);` + `SUCCESS`/`FAILURE` consts + `From<u8>` | 1.61.0 | representable exit status consumed by `Termination::report` |

### 2.2 Panic machinery — `std::panic`

| API | Signature | Since | Semantics |
|---|---|---|---|
| `catch_unwind` | `pub fn catch_unwind<F: FnOnce() -> R + UnwindSafe, R>(f: F) -> Result<R>` | 1.9.0 | capture unwinding panic as `Err(payload)`; hook already ran |
| `set_hook` | `pub fn set_hook(hook: Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>)` | 1.10.0 | replace global hook; default prints to stderr + backtrace if requested |
| `take_hook` | `pub fn take_hook() -> Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>` | 1.10.0 | retrieve current hook |
| `resume_unwind` | `pub fn resume_unwind(payload: Box<dyn Any + Send>) -> !` | 1.9.0 | continue unwinding (does not call the hook) |

### 2.3 Subprocesses — `std::process`

**`Command`** (builder):

```rust
use std::process::Command;
let out = Command::new("echo")            // program path (argv[0] name)
    .arg("-n")                            // fn arg<S: AsRef<OsStr>>(&mut self, arg: S) -> &mut Command
    .args(["hello", "world"])             // fn args<I, S>(&mut self, args: I) -> &mut Command
    .env("VAR", "value")                  // fn env<K, V>(&mut self, key: K, val: V) -> &mut Command
    .current_dir("/tmp")                  // fn current_dir<P: AsRef<Path>>(&mut self, dir: P) -> &mut Command
    .stdin(std::process::Stdio::null())   // fn stdin<T: Into<Stdio>>(&mut self, cfg: T) -> &mut Command
    .output()                             // fn output(&mut self) -> Result<Output>
    .expect("echo should run");
assert_eq!(out.stdout, b"hello world");
```

- `spawn()` — `fn spawn(&mut self) -> Result<Child>`: "Executes the command
  as a child process, returning a handle to it. **By default, stdin, stdout
  and stderr are inherited from the parent.**"
- `status()` — `fn status(&mut self) -> Result<ExitStatus>`: "Executes a
  command as a child process, waiting for it to finish and collecting its
  status." (stdio inherited.)
- `output()` — `fn output(&mut self) -> Result<Output>`: "By default, stdout
  and stderr are captured (and used to provide the resulting output). Stdin
  is not inherited from the parent and any attempt by the child process to
  read from the stdin stream will result in the stream immediately closing."
- Arguments are passed as an **array** to `execvp` — no shell, no quoting
  layer, no injection surface (§5.6).

**`Stdio`** — `Stdio::piped()`, `Stdio::inherit()`, `Stdio::null()`, plus
`From<ChildStdout>`/`From<ChildStderr>`/`From<ChildStdin>`/`From<File>` (std
`process::Stdio`).

**`Child`** (std `process::Child`):

| API | Signature | Notes |
|---|---|---|
| `id` | `pub fn id(&self) -> u32` | OS PID |
| `kill` | `pub fn kill(&mut self) -> Result<()>` | "Forces the child process to exit. If the child has already exited, Ok(()) is returned." |
| `wait` | `pub fn wait(&mut self) -> Result<ExitStatus>` | "Waits for the child to exit completely, returning the status that it exited with. This function will continue to have the same return value after it has been called at least once. The stdin handle to the child process, if any, will be closed before waiting." |
| `try_wait` | `pub fn try_wait(&mut self) -> Result<Option<ExitStatus>>` | non-blocking poll |
| `wait_with_output` | `pub fn wait_with_output(self) -> Result<Output>` | collects stdout/stderr (closes stdin first), waits |
| `stdin`/`stdout`/`stderr` | `pub stdin: Option<ChildStdin>` etc. | `Some` only when configured `Stdio::piped()` |

**`Output`** — `pub struct Output { pub status: ExitStatus, pub stdout:
Vec<u8>, pub stderr: Vec<u8> }` (std `process::Output`).

**`ExitStatus`** (std `process::ExitStatus`):

- `pub fn success(&self) -> bool` — "Was termination successful? **Signal
  termination is not considered a success**, and success is defined as a zero
  exit status."
- `pub fn code(&self) -> Option<i32>` — "Returns the exit code of the
  process, if any. In Unix terms the return value is the *exit status*: the
  value passed to exit, if the process finished by calling exit. **On Unix,
  this will return None if the process was terminated by a signal.**"
- `Display` renders like a shell report (e.g. `exit status: 0`,
  `signal: 9 (SIGKILL)` — rendering is informational).

**Unix extension trait** — `std::os::unix::process::ExitStatusExt`
(since 1.0.0, Unix only; "This trait cannot be implemented outside std"):

```rust
pub trait ExitStatusExt {
    fn from_raw(raw: i32) -> Self;
    fn signal(&self) -> Option<i32>;        // Some(sig) iff killed by a signal
    fn core_dumped(&self) -> bool;
    fn stopped_signal(&self) -> Option<i32>;
    fn continued(&self) -> bool;
    fn into_raw(self) -> i32;               // the raw waitpid status word
}
```

`into_raw`/`from_raw` expose the 16-bit wait-status word — the same integer
POSIX `wait` produces ([c.md](./c.md) §3.3,
[../exit-status/lifecycle.md](../exit-status/lifecycle.md)).

**Unix `CommandExt`** (std `os::unix::process::CommandExt`, 1.0.0):

| API | Signature / since | Notes |
|---|---|---|
| `uid`/`gid` | `fn uid(&mut self, id: u32) -> &mut Command` | child credential (setuid/setgid before exec) |
| `process_group` | `fn process_group(&mut self, pgroup: i32) -> &mut Command` — **1.64.0** | "Sets the process group ID (PGID) of the child process. Equivalent to a setpgid call in the child process... Process groups determine which processes receive signals." |
| `setsid` | `fn setsid(&mut self) -> &mut Command` | new session |
| `pre_exec` | `unsafe fn pre_exec<F>(&mut self, f: F) -> &mut Command where F: FnMut() -> io::Result<()> + Send + Sync + 'static` | closure runs after fork, before exec — async-signal-safety rules apply; this is the supported `pre_exec` hook (raw hazard, docs mark it unsafe) |
| `arg0` | `fn arg0<S>(&mut self, arg: S) -> &mut Command` | override argv[0] |
| `chroot` | `fn chroot(&mut self, path) -> &mut Command` | chroot before exec |

There is no `spawn_unwatched` in std — spawning is always via `spawn()`; the
"unwatched" concept exists only in third-party runtimes. If a reference for
such an API is needed, treat it as third-party.

---

## 3. Process Lifecycle and Termination

### 3.1 Startup

The std runtime (`library/std/src/rt.rs`, `lang_start`) initializes the
runtime, installs the default panic hook, calls `main`, and maps its
`Termination::report()` value to the process exit code (101 for an uncaught
main-thread panic; `libc::EXIT_SUCCESS`/`EXIT_FAILURE` for the default
`Termination` impls). After `main` returns, `libc::exit` runs — C atexit
handlers registered by native libraries still fire, and C stdio still flushes
(rt.rs calls `crate::sys::exit::unique_thread_exit()` then exits).

### 3.2 Terminating: normal vs. explicit vs. abnormal

- **Normal**: return from `main` (any `Termination` type) — all stacks in the
  process are *not* joined; other threads are killed mid-flight by the
  process teardown. Returning from main does not wait for spawned threads
  (thread module docs: "When the main thread of a Rust program terminates,
  the entire program shuts down, even if other threads are still running").
- **Explicit**: `process::exit(code)` — skips all `Drop`; use only after
  quiescing. `ExitCode` returned from `main` is the preferred expression.
- **Abnormal**: `process::abort()` (SIGABRT), uncaught main-thread panic
  (exit 101 after unwinding the main thread), `panic=abort` panics (no
  unwind), and hardware faults.
- The runtime never installs a SIGTERM/SIGINT handler: default OS behavior
  applies (§4.1).

### 3.3 Exit-status propagation

Exit code path: `Termination::report()` → `ExitCode` → OS (8-bit truncation
by the kernel, [c.md](./c.md) §3.3). `i32` codes passed to
`process::exit` are truncated to 8 bits by the OS on Linux — the std docs
note the portability masking caveat on `ExitCode`. A process killed by a
signal has no exit code; parents see `WIFSIGNALED`/`WTERMSIG` semantics via
`ExitStatusExt::signal()` and `code() == None`.

### 3.4 Process vs. thread vs. child

- **Process** termination: `exit`/`abort`/main-thread return/panic exit.
- **Thread** termination: function returns; or panics — a panic in a spawned
  thread unwinds only that thread; the panic is observable via
  `JoinHandle::join()` returning `Err(JoinError)`; the process continues
  (std `thread` module: "the thread will exit, but the panic may optionally
  be detected from a different thread with join"). No cooperative
  cancellation API in std (limitation; §6).
- **Child**: `Command::spawn` → `Child`; terminated with
  `Child::kill()` (SIGKILL on Unix); reaped by `wait`/`try_wait`/
  `wait_with_output` (§5).

---

## 4. Signals and OS Interaction

### 4.1 No standard signal API — a documented limitation

`std` contains **no** signal-registration, masking, or handler API. There is
no `std::signal`, no mask types, nothing in `std::os::unix::process` for
in-signal handling. Default OS dispositions therefore apply to an ordinary
Rust program: Ctrl-C (SIGINT) kills it, SIGTERM kills it, with no user code
involved (defaults per man 7 signal; see
[../signals/standard-signals.md](../signals/standard-signals.md)). The docs
only document the *panic* behavior of the runtime (§1.5) — everything else is
OS default.

### 4.2 Ecosystem solutions (third-party, not std guarantees)

- **signal-hook** (https://crates.io/crates/signal-hook, docs at
  https://docs.rs/signal-hook) — iterator/flag/pipe-based signal handling
  built on `sigaction` internally.
- **ctrlc** (https://crates.io/crates/ctrlc) — minimal Ctrl-C handling.
- **tokio::signal** (https://docs.rs/tokio/latest/tokio/signal/) — async
  signal streams (`signal::ctrl_c()`, `unix::signal(SignalKind::…)`) built on
  signal-hook-registry; integrates shutdown with async tasks.

These are **third-party crates**: they wrap the same OS primitives C uses
(sigaction/pthread_sigmask/signalfd) and are subject to the same
async-signal-safety discipline; they are not a std guarantee and have no
backwards-compatibility contract from the Rust project. For the underlying
semantics, read [../interfaces/sigaction-signal.md](../interfaces/sigaction-signal.md)
and [../interfaces/signal-masks.md](../interfaces/signal-masks.md).

### 4.3 Handlers vs. Rust code

If a handler *is* installed (via a crate or raw FFI), the C rules apply
verbatim: async-signal-safe functions only, `volatile`/atomic flag stores,
no allocator, no mutexes, no panicking (a panic in a handler tries to unwind
through foreign frames — with unwind strategy it may work by accident; with
`panic=abort` it aborts). Safe pattern: handler writes to a self-pipe or
atomic; Rust code polls it. See
[../interfaces/async-signal-safety.md](../interfaces/async-signal-safety.md).

### 4.4 Where the runtime changes OS semantics

The Rust runtime does not mask or redirect signals; it only:
- installs the default panic hook (not a signal handler),
- optionally uses `sigaltstack`-free normal stacks (no signal-stack games in
  std),
- spawns threads via pthreads; blocked-signal sets are inherited from the
  spawning thread, so signal masks *do* propagate to `std::thread::spawn`
  children via pthread defaults (OS behavior, not a std guarantee).

`std::os::unix::process::CommandExt::process_group` (1.64.0) is the one std
API that exists specifically to shape *signal delivery* to children: it
calls `setpgid` in the child so terminal signals (SIGINT/SIGQUIT from the
controlling terminal) do not reach the child — the docs say "Process groups
determine which processes receive signals."

---

## 5. Subprocess and Child-Process Management

### 5.1 Creation

`Command::new(program)` builds; `.arg/.args/.env/.envs/.env_remove/.env_clear/
.current_dir/.stdin/.stdout/.stderr` configure; `.spawn()/.status()/.output()`
execute. Program lookup: a plain name is resolved via `PATH` by `execvp`
semantics; **argument arrays are passed verbatim** — no shell interprets
metacharacters, so injection-by-quoting is structurally absent (§5.6).

### 5.2 Waiting, polling, termination

```rust
use std::process::{Command, Stdio};

let mut child = Command::new("sleep")
    .arg("3600")
    .stdout(Stdio::null())
    .spawn()?;

child.kill()?;                    // SIGKILL (kill(2)) on Unix
let st = child.wait()?;           // reap: zombie removed
assert!(st.success() == false);
#[cfg(unix)] {
    use std::os::unix::process::ExitStatusExt;
    assert_eq!(st.code(), None);          // signaled, not exited
    assert_eq!(st.signal(), Some(9));     // WTERMSIG equivalent
}
```

`kill()` maps to `kill(2)` with SIGKILL on Unix; `wait()` reaps (no zombie);
`try_wait()` polls without blocking. There is **no timeout parameter** —
implement timeouts with a timer thread that calls `kill` then `wait`, or
with `waitpid(WNOHANG)` polling in a loop (no std polling helper; `try_wait`
is the primitive).

### 5.3 Streams and pipe deadlocks

`Stdio::piped()` gives `Child.stdin/stdout/stderr` handles. The deadlock
pattern with `output()`:

- `output()` reads both pipes concurrently to EOF — safe.
- Manual `spawn()` + reading only `stdout` while the child floods `stderr`
  → the child blocks writing to stderr, you block reading stdout: deadlock.
  Fix: read both pipes (threads), or `stderr(Stdio::null())`, or
  `wait_with_output()` (which handles both), or `output()`.
- Writing to `child.stdin` while the child waits for EOF on stdout produces
  the mirror deadlock. The std docs for `Child::wait` note that the stdin
  handle is closed before waiting — dropping `child.stdin` explicitly is how
  you signal EOF to a pipeline stage.

Pipe buffers on Linux are 64 KiB by default (kernel `pipe` —
[../../syscalls/net-ipc/pipe.md](../../syscalls/net-ipc/pipe.md)); children
that out-write the buffer without being drained will block.

### 5.4 `Child` drop semantics — documented non-killing

std `process::Child` docs: "The standard library does not automatically wait
on child processes (not even if the Child is dropped), it is up to the
application developer to do so. As a consequence, dropping Child handles
without waiting on them first is not recommended in long-running
applications." So:

- Dropping a `Child` **does not kill** the child and **does not reap** it —
  the child keeps running and (after exit) becomes a **zombie** until the
  parent exits or waits. Daemons must track children and `wait` them, or use
  a reaper thread.
- **tokio** (third-party) changes this: `tokio::process::Command::kill_on_drop(bool)`
  — "Controls whether a kill operation should be invoked" when the child is
  dropped (docs.rs tokio 1.53.2, `process::Command`). With std there is no
  equivalent flag.

### 5.5 Environment, cwd, inherited fds

`.env()` sets/overrides; without any `.env*` call the child inherits the
parent's environment (std docs for `Command`). `.current_dir()` sets the
child cwd ("Sets the working directory for the child process", std docs).
The child inherits all open file descriptors marked inheritable — on Unix
that is effectively every fd (CLOEXEC is applied by std on its own internal
fds; *your* fds are inherited unless opened with `O_CLOEXEC`) — the classic
leaked-fd hazard from [c.md](./c.md) §5.4 applies; `pre_exec` can
`close_range`/close them (unsafe, §2.3 CommandExt).

### 5.6 Argument-array safety vs. shell execution

There is **no std shell-execution API** — `Command` never routes through
`/bin/sh`. Therefore: no quoting layer, no `$()` expansion, no `;` chaining,
no injection through crafted arguments. If a shell is genuinely needed
(`sh -c`), it must be explicit — `Command::new("sh").arg("-c").arg(script)`
— and then the script string is untrusted input again: validate or quote it
(compare C §5.6 of [c.md](./c.md), [../shells/bash.md](../shells/bash.md)).

### 5.7 Sync vs. async

`output()`/`status()` are synchronous (block the calling thread). `spawn()`
+ `Child` is the async-by-OS primitive; **`std` has no async executor** —
for async child management with cancellation, `tokio::process` (third-party)
provides `kill_on_drop`, cancellation tokens, and async `wait` (docs.rs
tokio). On the std side, cancellation = your own flag + `kill()` + `wait()`.

---

## 6. Concurrency and Resource Semantics

### 6.1 Threads

- `std::thread::spawn` returns a **`JoinHandle`**: "A JoinHandle detaches the
  associated thread when it is dropped, which means that there is no longer
  any handle to the thread and no way to join on it" (std
  `thread::JoinHandle`). Dropping ≠ terminating: detached threads run until
  the process dies.
- `join()` — `pub fn join(self) -> Result<T>` — blocks and surfaces panics as
  `Err(JoinError)` (`JoinError::is_panic()`); the process survives a panicking
  non-main thread (std `thread::JoinHandle` docs).
- **Scoped threads** — `std::thread::scope` (since **1.63.0**):
  `pub fn scope<'env, F, T>(f: F) -> T where F: for<'scope> FnOnce(&'scope
  Scope<'scope, 'env>) -> T` — borrows from the caller are safe because the
  scope joins all spawned threads before returning. Panics inside the scope
  propagate after joins.
- **No cancellation** in std: there is no `thread::cancel`; cooperative
  shutdown uses channels/atomics. This is a documented design (std `thread`
  module; no cancellation API exists in its index).

### 6.2 Ownership, drops, and resources

- `Drop` is the cleanup protocol: files closed, locks released, pipes
  flushed (for buffered writers, on drop *if* the drop runs). Every
  termination path table in §1.6 is a statement about which drops execute.
- fd ownership: `ChildStdin/ChildStdout/ChildStderr` and `File` own fds;
  drops close them (via the OS). Double-close is impossible without
  `unsafe` (as-raw-fd reborrowing).
- **`panic=abort` + drop skipping** changes crash semantics: buffered logs
  and telemetry are lost on abort; programs needing crash-safe output write
  unbuffered or install `SIGABRT` handling via a crate (third-party).

### 6.3 Races, deadlocks, leaks

- **Race**: `process::exit` from thread A while thread B is inside a drop
  that flushes — B's work is lost mid-operation; coordinate shutdown.
- **Deadlock**: waiting on a mutex that a panicking-but-aborting thread held
  (panic=abort skips poisoning); or the §5.3 double-pipe deadlock.
- **Leak**: un-reaped children (§5.4) are the signature Rust subprocess
  leak; also `JoinHandle`-less detached threads that outlive their borrowed
  data are prevented at compile time (scoped threads) or leak via
  `'static` captures.
- **Poisoning**: `Mutex` poisoning is the std guard against observing
  inconsistent state after a panicking unwind — not present on abort paths.

---

### Coverage ledger

Statuses: **documented** = covered above with verified signature and
reference; **source-limited** = a named primary source was unreachable
(missing source stated). Signature source of truth: doc.rust-lang.org/std
docs (retrieved 2026-10); std source `library/std/src/rt.rs` for the
exit-101 fact; docs.rs for tokio items.

| API | Canonical signature | Status | Reference |
|---|---|---|---|
| `process::exit` | `pub fn exit(code: i32) -> !` (1.0.0) | documented | std process::exit |
| `process::abort` | `pub fn abort() -> !` (1.17.0) | documented | std process::abort |
| `Termination` | `pub trait Termination { fn report(self) -> ExitCode; }` (1.61.0) | documented | std process::Termination |
| `ExitCode` | `pub struct ExitCode(/* private */);` (1.61.0), `SUCCESS`/`FAILURE`, `From<u8>` | documented | std process::ExitCode |
| `panic::catch_unwind` | `pub fn catch_unwind<F: FnOnce() -> R + UnwindSafe, R>(f: F) -> Result<R>` (1.9.0) | documented | std panic::catch_unwind |
| `panic::set_hook` | `pub fn set_hook(hook: Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>)` (1.10.0) | documented | std panic::set_hook |
| `panic::take_hook` | `pub fn take_hook() -> Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>` (1.10.0) | documented | std panic::take_hook |
| `panic::resume_unwind` | `pub fn resume_unwind(payload: Box<dyn Any + Send>) -> !` (1.9.0) | documented | std panic::resume_unwind |
| `Command::new` | `pub fn new(program: impl AsRef<OsStr>) -> Command` | documented | std process::Command (constructor per docs) |
| `Command::arg` | `fn arg<S: AsRef<OsStr>>(&mut self, arg: S) -> &mut Command` | documented | std process::Command::arg |
| `Command::args` | `fn args<I, S>(&mut self, args: I) -> &mut Command` | documented | std process::Command::args |
| `Command::env` | `fn env<K, V>(&mut self, key: K, val: V) -> &mut Command` | documented | std process::Command::env |
| `Command::current_dir` | `fn current_dir<P: AsRef<Path>>(&mut self, dir: P) -> &mut Command` | documented | std process::Command::current_dir |
| `Command::stdin/stdout/stderr` | `fn stdin<T: Into<Stdio>>(&mut self, cfg: T) -> &mut Command` | documented | std process::Command::stdin |
| `Command::spawn` | `fn spawn(&mut self) -> Result<Child>` | documented | std process::Command::spawn |
| `Command::status` | `fn status(&mut self) -> Result<ExitStatus>` | documented | std process::Command::status |
| `Command::output` | `fn output(&mut self) -> Result<Output>` | documented | std process::Command::output |
| `Stdio` | `piped()/inherit()/null()` constructors + From conversions | documented | std process::Stdio |
| `Child` | struct; `id/kill/wait/try_wait/wait_with_output`; `stdin/stdout/stderr` fields | documented | std process::Child |
| `Child::kill` | `pub fn kill(&mut self) -> Result<()>` | documented | std process::Child::kill |
| `Child::wait` | `pub fn wait(&mut self) -> Result<ExitStatus>` | documented | std process::Child::wait |
| `Child::try_wait` | `pub fn try_wait(&mut self) -> Result<Option<ExitStatus>>` | documented | std process::Child::try_wait |
| `Child::wait_with_output` | `pub fn wait_with_output(self) -> Result<Output>` | documented | std process::Child::wait_with_output |
| `Output` | `pub struct Output { pub status: ExitStatus, pub stdout: Vec<u8>, pub stderr: Vec<u8> }` | documented | std process::Output |
| `ExitStatus` | `success() -> bool`, `code() -> Option<i32>` (1.0.0) | documented | std process::ExitStatus |
| `ExitStatusExt` | `from_raw/signal/core_dumped/stopped_signal/continued/into_raw` (1.0.0, Unix) | documented | std os::unix::process::ExitStatusExt |
| `CommandExt::process_group` | `fn process_group(&mut self, pgroup: i32) -> &mut Command` (1.64.0) | documented | std os::unix::process::CommandExt |
| `CommandExt::pre_exec` | `unsafe fn pre_exec<F>(&mut self, f: F) -> &mut Command` | documented | std os::unix::process::CommandExt |
| `CommandExt::uid/gid/setsid/arg0/chroot` | per CommandExt trait page | documented | std os::unix::process::CommandExt |
| `process::id` | `pub fn id() -> u32` | documented | std process::id |
| `thread::JoinHandle` | `pub fn join(self) -> Result<T>`; drop detaches (1.0.0) | documented | std thread::JoinHandle |
| `thread::scope` | `pub fn scope<'env, F, T>(f: F) -> T` (1.63.0) | documented | std thread::scope |
| Signal API in std | none exists | documented | absence per std doc index |
| `signal-hook` crate | (third-party; sigaction-based) | source-limited | crates.io page blocked to automated fetch (HTTP 403); existence via docs.rs; signature-level docs not verified |
| `tokio::process::Command::kill_on_drop` | `pub fn kill_on_drop(&mut self, kill_on_drop: bool) -> &mut Command` (tokio 1.53.2, third-party) | documented | docs.rs tokio process::Command |
| `tokio::signal` | module (third-party) | documented | docs.rs tokio signal (module page fetched) |
| panic strategies | `panic = "unwind" \| "abort"` (Cargo profile) | documented | Cargo reference profiles |
| Main-thread panic exit code | non-zero per std docs; **101** per std source `rt.rs` | documented | std::thread module docs; library/std/src/rt.rs |

Counts: **37** inventoried · **36** documented · **1** source-limited ·
**0** remaining.

---

## Related Topics

- Language siblings: [C](./c.md) · [C++](./cpp.md) · [Go](./go.md)
- Exit status: [Lifecycle](../exit-status/lifecycle.md) ·
  [Conventions (0, 101, 128+N, 137)](../exit-status/conventions.md)
- Signals: [Standard signals](../signals/standard-signals.md) ·
  [Async-signal-safety](../interfaces/async-signal-safety.md) ·
  [signal masks](../interfaces/signal-masks.md) ·
  [signalfd/pidfd](../interfaces/signalfd-pidfd.md)
- Existing book pages: [process control](../../../linux/sysprog/process-control.md) ·
  [wait4(2)](../../../linux/syscalls/process/wait4.md) ·
  [pipe(2)](../../../linux/syscalls/net-ipc/pipe.md) ·
  [signals overview](../../../linux/sysprog/signals.md)
- Containers (zombie reaping, PID 1):
  [containers/pid1-signals](../containers/pid1-signals.md)

## References

- The Rust Standard Library documentation (doc.rust-lang.org/std, retrieved
  2026-10): `std::process` (module, `exit`, `abort`, `id`, `Termination`),
  `std::process::Command`, `std::process::Child`, `std::process::ExitStatus`,
  `std::process::ExitCode`, `std::process::Output`, `std::process::Stdio`,
  `std::os::unix::process::ExitStatusExt`,
  `std::os::unix::process::CommandExt`, `std::thread` (module, `JoinHandle`,
  `scope`), `std::panic` (`catch_unwind`, `set_hook`).
- Rust std source, `library/std/src/rt.rs` (github.com/rust-lang/rust,
  master, retrieved 2026-10) — exit code 101 for uncaught main-thread panic.
- The Rust Programming Language, ch. 9 (unrecoverable errors / panic!),
  https://doc.rust-lang.org/book/
- The Cargo Book, reference/profiles.html — `panic = "unwind" | "abort"`.
- tokio 1.53.2 docs (third-party): https://docs.rs/tokio/latest/tokio/process/struct.Command.html
  (`kill_on_drop`), https://docs.rs/tokio/latest/tokio/signal/ —
  and signal-hook: https://crates.io/crates/signal-hook (docs at docs.rs/signal-hook).
- POSIX.1-2017 `wait`/`kill` and Linux man-pages for the underlying
  wait-status encoding cross-referenced in §5.2 —
  https://pubs.opengroup.org/onlinepubs/9699919799/, https://man7.org/linux/man-pages/
