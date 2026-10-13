# Rust: Language Semantics, Standard Library, Process APIs, and Subprocesses

Rust makes process lifecycle questions type-system questions. What runs on
termination is `Drop`; what the parent sees is `ExitCode`/`ExitStatus`; what
kills a child is a `Command` builder; and the language guarantees about
ownership — which this chapter treats as in-scope *only* where they meet
process exit, signals, and subprocesses — determine exactly which destructors
execute on each termination path. The standard library deliberately provides
**no signal-registration API**, and `Child` deliberately does **not** kill or
reap on drop; both gaps have practical consequences documented below.

**Declared scope.** This chapter documents **current stable Rust, verified as
`std` 1.99.0 (build `b940084d7`, dated 2026-09-28) on doc.rust-lang.org,
retrieved 2026-10**. Sources of record: the official standard-library
documentation (doc.rust-lang.org/std — module and item pages), the **Rust
Reference** (doc.rust-lang.org/reference) for language rules, the **Cargo
Book** (doc.rust-lang.org/cargo) for profile/panic-strategy configuration, and
the rust-lang/rust source tree **only** for numeric facts needing a primary
anchor (exit code 101; SIGPIPE startup behavior). Every signature and
since-version below was checked against those pages during this retrieval
window; nothing is claimed universally beyond this scope. The sibling chapter
[../../linux/process-exit-signal/languages/rust.md](../../linux/process-exit-signal/languages/rust.md)
covered the exit/signal slice for the 1.61–1.8x era; this chapter extends that
work to the current stable line and corrects three items (nightly-only
`CommandExt` methods, per-method `ExitStatusExt` since-versions, and the
documented `atexit`/concurrent-`exit` behavior of `process::exit`).

**Reading map.** Ownership/borrowing/lifetime *tutorials* live in
[../rust/ownership.md](../rust/ownership.md) and
[../rust/lifetimes.md](../rust/lifetimes.md); the `unsafe` toolbox in
[../rust/unsafe.md](../rust/unsafe.md). The OS substrate (wait-status words,
signal dispositions, zombies) lives in the Linux part, starting from
[../../linux/process-exit-signal/index.md](../../linux/process-exit-signal/index.md).
Sibling Section-G chapters: [./c.md](./c.md), [./cpp.md](./cpp.md),
[./index.md](./index.md). Layer labels used throughout: **[std guarantee]**,
**[platform Unix]**, **[Linux]**, **[third-party]**.

---

## 1. Syntax and Semantics

### 1.1 Items, functions, and the program entry point

A Rust program is a crate: a tree of *items* (functions, `struct`, `enum`,
`trait`, `impl`, `const`, `static`, modules). The binary entry point is `fn
main`; `std` wraps it in a runtime start function (`lang_start` in
`library/std/src/rt.rs`, verified in source) that initializes the runtime,
installs the default panic hook, runs `main`, and converts its return value to
a process exit code via the `Termination` trait (§3.2).

Constraints the compiler enforces: `main` takes no parameters in normal use
(the `std` runtime receives `argc`/`argv` itself and exposes them through
`std::env`), and its return type must implement `Termination` (§3.2) — which
excludes `String` and every other non-implementing type.

### 1.2 Expressions, blocks, and temporaries

Rust is expression-oriented: almost everything evaluates to a value; `;`
discards it. Block structure drives *drop scopes* — the Reference's
destructor rules ([std guarantee], reference/destructors.html):

- Local variables drop when their enclosing block ends, **in reverse
  declaration order**.
- Function parameters drop after the body's locals.
- Temporary values live until the end of the enclosing statement (temporary
  scopes), with defined exceptions (e.g. temporary lifetime extension in
  `let` initializers).

Two facts matter disproportionately for process semantics:

1. **Destructors are not soundness-critical.** The Reference is explicit:
   besides the drop scopes it defines, "types may not safely rely on a
   destructor being run for soundness" — and `mem::forget`/`ManuallyDrop`
   are *safe* ways to skip a destructor.
2. **Every non-unwinding termination path suspends the drop protocol**
   (§1.6, §3.10).

The full drop-scope table (function parameters, locals, temporaries,
operands, promotion) is in the Reference; the interview-level tutorial
treatment of ownership and move semantics is in
[../rust/ownership.md](../rust/ownership.md).

### 1.3 `enum`, `struct`, `Result`/`Option`, and `?`

Error propagation is built on two enums and one operator:

```rust
use std::num::ParseIntError;

fn double(s: &str) -> Result<i32, ParseIntError> {
    let n: i32 = s.parse()?; // `?`: unwraps Ok; on Err, early `return Err(From::from(e))`
    Ok(n * 2)
}

fn main() {
    assert_eq!(double("21"), Ok(42));   // expected: Ok(42)
    assert!(double("x").is_err());      // expected: Err(ParseIntError); no panic
}
```

`?` performs a *conversion*, not a throw (`From::from(e)`); `Result`/`Option`
are ordinary values. Panics (§1.4) are a separate, orthogonal mechanism for
unrecoverable invariant violations — `Result`/`Option` are the *recoverable*
channel and never by themselves terminate the process. The idiomatic deep
dive is in the book's error-handling pages; for this chapter the
load-bearing consequence is: a `main` returning `Result` prints the error and
exits `1` (§3.2), while a `?`-propagated error inside `main` reaches exactly
that path.

`Option<T>` is the "absence" enum; `unwrap`/`expect` on `None` **panics**
(§1.4) rather than exiting.

### 1.4 Panics: the exceptional path inside the language

A panic is a thread-level fatal event with a defined pipeline ([std
guarantee], std::panic::set_hook): **panic hook runs first → then the panic
runtime** (unwind *or* abort, per compilation strategy §3.6). Panics arise
from `panic!`, `assert*!`, `unwrap`/`expect`, arithmetic-overflow checks in
debug builds (release builds may wrap — overflow checking is profile-dependent),
array-bounds violations, and assorted `std` precondition checks.

Key semantics:

- A panic **unwinds the current thread by default**, running destructors of
  that thread's frames (Cargo's `panic` setting can change this to abort;
  §3.6).
- A panic in a non-main thread is **observable** via `JoinHandle::join() ->
  Err(JoinError)` and does not end the process; an uncaught panic on the main
  thread ends the process with exit code **101** (§3.10).
- The panic hook is a **global resource** and runs for *both* runtimes
  (unwinding and aborting) — a `panic=abort` panic still prints the default
  hook message, while `std::process::abort()` calls no hook (§3.5).
- `catch_unwind` can stop an unwinding panic (§3.8); `panic_any` raises a
  panic with a non-string payload; `resume_unwind` continues unwinding
  without calling the hook.

### 1.5 Ownership, borrowing, lifetimes — the process-semantics slice

The full tutorial treatment is in [../rust/ownership.md](../rust/ownership.md)
and [../rust/lifetimes.md](../rust/lifetimes.md). What this chapter needs is
the intersection with termination:

- **`Drop` is the cleanup protocol.** Files close, locks release, pipes
  flush, children get stdin closed — all through `Drop` impls, all only on
  paths where destructors run.
- **Drop order is reverse declaration order** within a scope; `struct` fields
  drop in declaration order unless the type has a custom `Drop` (which drops
  fields itself). Declared drop order is a Reference rule, not folklore.
- **`Send`/`Sync` are the concurrency safety markers** (§6.2); `UnwindSafe`
  is the analogous marker for the `catch_unwind` boundary (§3.8).
- **Moves and borrows are checked at compile time**, so "double close" of a
  file descriptor is impossible in safe code: an owned fd wrapper
  (`OwnedFd`, `File`, `ChildStdin`) has exactly one owner, and closing is
  that owner's `Drop` (§6.5).

### 1.6 Normal vs. exceptional vs. explicit termination

Termination comes in three families, and the definitive per-path cleanup
matrix (which `Drop`s run, whether the panic hook and C `atexit` run, whether
buffers flush, what status the parent sees) is table §3.10 — every row of it
is a statement about which destructors execute. One Reference rule belongs
here because it is about scope, not process calls:

> "when a panic reaches a non-unwinding ABI boundary, either no destructors
> will run, or all destructors up until the ABI boundary will run."

### 1.7 Undefined-behavior boundaries in scope

Rust has no UB category for "exit while a mutex is held" or "exit twice" —
those are OS-level realities, not language rules. UB in Rust is confined to
the Reference's *Behavior considered undefined* list, and only two entries
bear on process/subprocess code ([std guarantee] for the list itself):

- **Data races** — unsynchronized concurrent access where at least one access
  is a write. This is why sharing signal-handler state requires atomics or
  the `Sync` types of §6.2, and why `static mut` is unsafe.
- **Accessing a place that is dangling or based on a misaligned pointer** —
  the classic `unsafe` failure behind "the handler dereferenced freed
  memory".
- **Calling a function with the wrong call ABI, or unwinding past a stack
  frame that does not allow unwinding** — e.g. a `"C-unwind"` function
  invoked through a `"C"` function pointer; the FFI panic case of §3.9.
- **Producing an invalid value** and **violating assumptions of the Rust
  runtime** (the latter "most assumptions ... are currently not explicitly
  documented").

Safe code cannot trigger any of these; `unsafe` code must uphold them (the
full unsafe contract, without duplication, is in
[../rust/unsafe.md](../rust/unsafe.md)). Consequence: a Rust program whose
`unsafe` code faults gets a hardware signal (SIGSEGV etc.) with no language
level answer — the same kernel-level reality as C (§4).

### 1.8 Edition and version deltas in scope

Versions below are the since-versions printed on the current std doc pages
(verified 2026-10). Editions are a compatibility axis independent of versions:
the one verified edition-relevant delta in this area is that `before_exec`
"got deprecated in favor of the unsafe `pre_exec`. Meanwhile, Rust gained the
ability to make an existing safe method fully unsafe in a new edition, which
is how `before_exec` became `unsafe`" (std CommandExt docs).

| Feature | Since | Bearing on process/termination/subprocess code |
|---|---|---|
| `Termination`, `ExitCode` | 1.61.0 | typed `main` return / exit codes |
| `ExitCode: Default` | 1.75.0 | `ExitCode::default()` = `SUCCESS` |
| `ExitStatus: Default` | 1.73.0 | default = successful completion |
| `Command::get_program/get_args/get_envs/get_current_dir` | 1.57.0 | introspecting a builder |
| `ExitStatusExt::{core_dumped, stopped_signal, continued}` | 1.58.0 | signal-decoding breadth |
| `ExitStatusExt::from_raw` | 1.12.0 | constructing wait statuses |
| `CommandExt::pre_exec` | 1.34.0 | pre-exec child customization |
| `CommandExt::exec` | 1.9.0 | replace-process (execvp) |
| `CommandExt::arg0` | 1.45.0 | argv[0] override |
| `CommandExt::process_group` | 1.64.0 | child signal delivery scoping |
| `Child::try_wait` | 1.18.0 | non-blocking reap |
| `From<OwnedFd> for ChildStdin` | 1.74.0 | hand a raw fd to a child |
| `panic::panic_any` | 1.51.0 | non-string panic payloads |
| `PanicHookInfo` hook type | 1.81.0 | replaces `PanicInfo` in hook signatures |
| `thread::scope`, `Builder::spawn_scoped` | 1.63.0 | borrowing scoped threads |
| `JoinHandle::is_finished` | 1.61.0 | non-blocking join idiom |
| `Builder::spawn_unchecked` | 1.82.0 | unsafe relaxed-lifetime spawn |
| `thread::available_parallelism` | 1.59.0 | worker sizing |

### 1.9 Misconceptions

- *"`panic!` aborts the process."* False by default: panic unwinds the
  current thread and runs destructors; only the `panic="abort"` profile
  (or an FFI boundary) turns a panic into process death.
- *"Rust programs exit with 1 on panic."* They exit with **101** (std source
  `rt.rs`; the docs say only "non-zero").
- *"`main` can return `String`."* No — return types are exactly the
  `Termination` implementors (§3.2): `()`, `ExitCode`, `Infallible`, `!`,
  `Result<T, E: Debug>`.
- *"`process::exit` lets other threads finish and drop their locals."* False:
  "no destructors on the current stack or any other thread's stack will be
  run" (std docs).
- *"Dropping a `Child` kills it."* False — std installs no such `Drop`
  (§5.4).
- *"Rust has no UB."* Safe Rust has no UB; `unsafe` Rust has a defined UB
  list (§1.7).
- *"The runtime installs a SIGINT handler."* It does not; default OS
  dispositions apply (§4.1).

---

## 2. Standard-Library and Runtime API Inventory

All signatures below were transcribed from doc.rust-lang.org/std item pages
for the declared build (1.99.0, retrieved 2026-10); "since" values are those
printed on the pages. Panics/errors are listed where the docs document them.

### 2.1 `std::process` — current-process surface

| API | Canonical signature | Since | Semantics / notes |
|---|---|---|---|
| `process::exit` | `pub fn exit(code: i32) -> !` | 1.0.0 | immediate termination; **no destructors anywhere**; runs `atexit` handlers; 8-bit truncation on most Unix (§3.3) |
| `process::abort` | `pub fn abort() -> !` | 1.17.0 | abnormal termination; no destructors; no buffer flush; **no panic hook**; SIGABRT on Unix (§3.5) |
| `process::id` | `pub fn id() -> u32` | 1.26.0 | OS-assigned PID of this process |
| `process::Termination` | `pub trait Termination { fn report(self) -> ExitCode; }` | 1.61.0 | `main`'s return-value protocol (§3.2) |
| `process::ExitCode` | `pub struct ExitCode(/* private fields */)` | 1.61.0 | `SUCCESS`/`FAILURE` consts, `From<u8>`, `PartialEq` (no `Eq`/`Hash`/raw access); `Default` since 1.75.0 |
| `os::unix::process::parent_id` | `pub fn parent_id() -> u32` | 1.27.0 | parent PID **[platform Unix]** |

Documented panics: none of the above. Documented UB hazard: calling `exit`
concurrently with C's `exit` (§3.3).

### 2.2 `std::panic` — panic machinery

| API | Canonical signature | Since | Semantics / notes |
|---|---|---|---|
| `set_hook` | `pub fn set_hook(hook: Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>)` | 1.10.0 | replaces the global hook; panics if called from a panicking thread |
| `take_hook` | `pub fn take_hook() -> Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>` | 1.10.0 | unregisters the hook, **registering the default hook in its place** |
| `catch_unwind` | `pub fn catch_unwind<F: FnOnce() -> R + UnwindSafe, R>(f: F) -> Result<R>` | 1.9.0 | catches unwinding panics only; hook already ran; payload in `Err` (§3.8) |
| `resume_unwind` | `pub fn resume_unwind(payload: Box<dyn Any + Send>) -> !` | 1.9.0 | continues unwinding **without** invoking the hook; aborts under `panic="abort"` |
| `panic_any` | `pub fn panic_any<M: 'static + Any + Send>(msg: M) -> !` | 1.51.0 | panic with arbitrary payload; reachable via `PanicHookInfo::payload` |
| `PanicHookInfo<'a>` | `pub struct PanicHookInfo<'a> { /* private fields */ }` | 1.81.0 | hook parameter type; exposes payload + location; `!Send`/`!Sync` |
| `update_hook` | `pub fn update_hook<F>(hook_fn: F)` | **nightly** (`panic_update_hook`) | atomic take-then-chain; not in stable |
| `UnwindSafe` | `pub auto trait UnwindSafe { }` | 1.9.0 | marker for types safe to cross a `catch_unwind` boundary |
| `AssertUnwindSafe` | `pub struct AssertUnwindSafe<F>(pub F)` | 1.9.0 | opt-out wrapper for the `UnwindSafe` bound |

On std < 1.81 the hook parameter type was `std::panic::PanicInfo`; the current
docs route hook users to `PanicHookInfo` (the `core::panic::PanicInfo` page
defers to it).

### 2.3 `std::thread` — thread surface

| API | Canonical signature | Since | Semantics / notes |
|---|---|---|---|
| `thread::spawn` | `pub fn spawn<F, T>(f: F) -> JoinHandle<T> where F: FnOnce() -> T + Send + 'static, T: Send + 'static` | 1.0.0 | panics if the OS cannot create the thread (use `Builder::spawn` to recover) |
| `JoinHandle::join` | `pub fn join(self) -> Result<T>` | 1.0.0 | blocks; surfaces panics as `Err` |
| `JoinHandle::is_finished` | `pub fn is_finished(&self) -> bool` | 1.61.0 | non-blocking join support |
| `JoinHandle` drop | `impl Drop` — **detaches** | 1.0.0 | "A JoinHandle detaches the associated thread when it is dropped" |
| `Builder::new/name/stack_size` | `pub fn new() -> Builder`; `pub fn name(self, name: String) -> Builder`; `pub fn stack_size(self, size: usize) -> Builder` | 1.0.0 | configuration factory |
| `Builder::spawn` | `pub fn spawn<F, T>(self, f: F) -> Result<JoinHandle<T>>` | 1.0.0 | `io::Result` for thread-creation failure; panics if a set name contains NUL |
| `Builder::spawn_scoped` | `pub fn spawn_scoped<'scope, 'env, F, T>(self, scope: &'scope Scope<'scope, 'env>, f: F) -> Result<ScopedJoinHandle<'scope, T>>` | 1.63.0 | borrowing threads inside a scope |
| `thread::scope` | `pub fn scope<'env, F, T>(f: F) -> T where F: for<'scope> FnOnce(&'scope Scope<'scope, 'env>) -> T` | 1.63.0 | joins all unjoined scoped threads before returning (§6.3) |
| `Builder::spawn_unchecked` | `pub unsafe fn spawn_unchecked<F, T>(self, f: F) -> Result<JoinHandle<T>>` | 1.82.0 | unsafe: relaxed lifetime bounds |
| `thread::available_parallelism` | `pub fn available_parallelism() -> Result<NonZero<usize>>` | 1.59.0 | worker sizing hint |

Default stack size: "Currently, it is 2 MiB on all Tier-1 platforms"
(module docs); `RUST_MIN_STACK` env override; the **main thread's stack size
is not determined by Rust**.

### 2.4 Concurrency primitives bearing on termination

| API | Canonical signature | Since | Semantics / notes |
|---|---|---|---|
| `Mutex<T>::lock` | `pub fn lock(&self) -> Result<MutexGuard<'_, T>, PoisonError<MutexGuard<'_, T>>>` | 1.0.0 | returns `Err` when the previous holder panicked — poisoning (§6.7) |
| `Mutex<T>::is_poisoned` | `pub fn is_poisoned(&self) -> bool` | 1.0.0 | advisory check |
| `PoisonError::into_inner` | `pub fn into_inner(self) -> T` | 1.2.0 | recover the guard despite poisoning ("Poisoning is only advisory") |

The poisoning docs also document their own blind spots: panics *while a lock
is held* inside a `Drop` or panic hook can leave the mutex unpoisoned, and
foreign exceptions "do not currently trigger poisoning".

### 2.5 API surface deliberately **not** in std

- No signal registration/masking API (§4.1).
- No child-process timeout API (§5.9); no `kill_on_drop` flag for `Child`
  (§5.4); no async runtime; no `spawn_unwatched`-style reaper-less spawn —
  std `Child` *is* unwatched until you wait (§5.4).
- `Command::get_resolved_envs`/`get_env_clear` and `ExitCode::exit_process`,
  `ExitStatus::exit_ok`, `ChildExt::{send_signal, send_process_group_signal,
  kill_process_group, pidfd}`, `CommandExt::{groups, chroot, setsid}` are
  **nightly-only** on this build (feature-gated on the respective pages).

---

## 3. Process Creation and Termination

### 3.1 Runtime startup and shutdown skeleton

`lang_start` (std source `library/std/src/rt.rs`, retrieved 2026-10) does,
in order: sanitize std fds 0/1/2 (opening `/dev/null` for any that are
closed), set SIGPIPE to ignore (§4.5), initialize stack-overflow guard
handling, run `main` inside `catch_unwind`, map an escaping main-thread panic
to exit code **101**, run runtime `cleanup()`, and finally exit via a
single-threaded `libc::exit` path ("Guard against multiple threads calling
`libc::exit` concurrently"). This is implementation code cited as the primary
anchor for numeric facts, not a stability contract.

### 3.2 `main` return types and the `Termination` protocol

Exact trait (std docs, since 1.61.0):

```rust
pub trait Termination {
    fn report(self) -> ExitCode;
}
```

Implementors on the current docs (complete list): `!`, `()`, `ExitCode`,
`Infallible`, and `Result<T, E> where T: Termination, E: Debug`. The docs:
"A trait for implementing arbitrary return types in the main function. The
C-main function only supports returning integers... The default
implementations are returning `libc::EXIT_SUCCESS` to indicate a successful
execution. In case of a failure, `libc::EXIT_FAILURE` is returned."

- `()` / `ExitCode::SUCCESS` → exit 0.
- `ExitCode::from(n)` → exit `n` (8-bit, §3.3).
- `Infallible`/`!` → statically can't fail.
- `Result<T: Termination, E: Debug>`: `Ok` recurses into `T::report`; `Err(e)`
  prints `Error: {err:?}` to stderr and exits with `ExitCode::FAILURE`
  (implementation in std source `process.rs`, stable since 1.61.0 — note the
  **`Debug`**, not `Display`, bound; that is why `Box<dyn Error>` works and a
  `Display`-only error type does not).

### 3.3 `std::process::exit` — the explicit non-return

```rust
pub fn exit(code: i32) -> !   // since 1.0.0
```

Verified documentation quotes ([std guarantee]):

> "Terminates the current process with the specified exit code. This function
> will never return... **no destructors on the current stack or any other
> thread's stack will be run.**"

> "In its current implementation, this function will execute exit handlers
> registered with `atexit` as well as other platform-specific exit handlers
> (e.g. `fini` sections of ELF shared objects)."

So on Linux the *C-level* atexit machinery does run (C stdio therefore
flushes), while *Rust* destructors and Rust's `BufWriter` drop-flush do not.
Practical consequences: locks stay held mid-acquisition; log buffers vanish;
`Child` handles are orphaned without reaping (zombies, §5.11); and because
returning from `main` "is equivalent to calling `exit`", the same atexit
machinery also runs on normal return.

**Exit-status truncation.** The docs' platform section: "On most Unix-like
platforms, only the eight least-significant bits are considered. For example,
the exit code for this example will be `0` on Linux, but `256` on Windows:
`process::exit(0x0100);`". An `i32` argument is thus narrowed to the wait
status's exit-code byte by the OS ([Linux]: low 8 bits, per
[../../linux/process-exit-signal/languages/rust.md](../../linux/process-exit-signal/languages/rust.md)
and the C chapter [./c.md](./c.md)). `ExitCode` cannot express out-of-range
codes precisely because of this (its docs: "different platforms may mask
different amounts of them").

**Concurrency hazard (documented UB).** The `exit` page's "Safe interop with
C code" section states that concurrent `exit` from Rust while another thread
calls C `exit`/`quick_exit` (or C's `main` returns) "can still cause undefined
behavior"; Rust mitigates with a lock for Rust-vs-Rust concurrency, but a
binary containing multiple Rust runtimes ("multiple `cdylib` or `staticlib`")
has "separate locks" and may still race. Single-threaded exit discipline or
synchronization is the programmer's obligation.

### 3.4 `ExitCode` — the typed exit status

`pub struct ExitCode(/* private fields */)` (1.61.0) with `SUCCESS`,
`FAILURE`, `From<u8>`, `PartialEq` (deliberately **no** `Eq`/`Hash`/raw-value
access "for forwards compatibility with potentially unusual targets"), and
`Default = SUCCESS` (1.75.0). Its docs fix the vocabulary used throughout:

> "`ExitCode` is intended for terminating the currently running process, via
> the `Termination` trait, in contrast to `ExitStatus`, which represents the
> termination of a child process. These APIs are separate due to platform
> compatibility differences and it is not generally possible to exactly
> reproduce an `ExitStatus` from a child for the current process after the
> fact."

`ExitCode::exit_process` exists but is nightly-only
(`exitcode_exit_method`).

### 3.5 `std::process::abort` — the abnormal exit

```rust
pub fn abort() -> !   // since 1.17.0
```

Verified documentation ([std guarantee]):

> "no destructors on the current stack or any other thread's stack will be
> run, Rust IO buffers (eg, from `BufWriter`) will not be flushed, and C
> stdio buffers will (on most platforms) not be flushed."

> "When `panic="abort"` is set... `panic!` and `abort` are similar. However,
> **`panic!` will still call the panic hook while `abort` will not.**"

**[platform Unix]**: "On Unix, the process will terminate with signal
`SIGABRT`, which typically means that the shell prints 'Aborted'" — the same
C `abort(3)` bottoming-out documented for C in [./c.md](./c.md); core-dump
behavior follows the platform's core-dump rules. Contrast with `exit`: no
atexit handlers, no hook, no flush of any kind.

### 3.6 Panic strategies: unwind (default) vs. abort

The Cargo Book (`profile.panics`, verified 2026-10): "The `panic` setting
controls the `-C panic` flag which controls which panic strategy to use. The
valid options are: `"unwind"`: Unwind the stack upon panic. `"abort"`:
Terminate the process upon panic." When `"unwind"` is selected, "the actual
value depends on the default of the target platform" (some targets cannot
unwind); "Tests, benchmarks, build scripts, and proc macros ignore the
`panic` setting" and the test harness requires unwind.

Consequences for `Drop`:

- **unwind**: panics drop frames on the panicking thread; `catch_unwind` can
  intercept; mutex poisoning works (§6.7).
- **abort**: `panic!` terminates the process immediately; destructors do not
  run; the panic hook *still runs first* (std `abort` docs quote above), so
  the message is printed; `catch_unwind` cannot see the panic
  ("This function only catches unwinding panics, not those that abort the
  process").

### 3.7 Panic hooks

The **default hook**, "registered at startup, prints a message to standard
error and generates a backtrace if requested" (std::panic::set_hook docs).
Backtrace control is via `RUST_BACKTRACE`-style environment values; the hook
receives a `PanicHookInfo<'_>` (payload + source location).

- `set_hook` replaces the global hook. "The panic hook is a global resource."
- `take_hook` unregisters and returns the current hook, **registering the
  default hook in its place** — the standard way to restore default reporting
  after chaining.
- Both **panic if called from a panicking thread** (documented §Panics).
- The hook runs "when a thread panics, but before the panic runtime is
  invoked. As such, the hook will run with both the aborting and unwinding
  runtimes" — i.e., it runs under `panic="abort"` too, and before any
  `catch_unwind` interception.
- Chaining (wrap-and-continue) is a nightly convenience (`update_hook`);
  in stable you `take_hook`, wrap in a closure, and `set_hook` the wrapper.

### 3.8 `catch_unwind`, `UnwindSafe`, and the payload hazard

```rust
pub fn catch_unwind<F: FnOnce() -> R + UnwindSafe, R>(f: F) -> Result<R>   // 1.9.0
```

Verified semantics ([std guarantee]):

- Returns `Ok(result)` or `Err(payload)` where the payload is "the object
  with which panic was originally invoked".
- "It is not recommended to use this function for a general try/catch
  mechanism" — `Result` is the normal error channel.
- "This function only catches unwinding panics, not those that abort the
  process."
- "If a custom panic hook has been set, it will be invoked before the panic
  is caught" — hook, then interception.
- The `UnwindSafe` bound "encodes the concept of exception safety in the
  type system" (an auto trait, 1.9.0); `AssertUnwindSafe` is the documented
  escape hatch.
- Dropping the returned `Err` can itself panic: "be careful in how you drop
  the result... it contains the panic payload, and dropping that may in turn
  panic!" (the std runtime itself wraps payload-drop in a second
  `catch_unwind` for exactly this reason — `rt.rs`).
- Foreign exceptions thrown through a `"C-unwind"` ABI into `catch_unwind`
  produce one of two behaviors, "and it is unspecified which will occur":
  abort after running `f`'s destructors, or `Err` with an opaque type.

### 3.9 Unwinding across FFI boundaries

The `catch_unwind` page states the contract ([std guarantee]):

> "Rust functions that are expected to be called from foreign code that does
> not support unwinding (such as C compiled with `-fno-exceptions`) should be
> defined using `extern "C"`, which ensures that if the Rust code panics, it
> is automatically caught and the process is aborted."

So: a panic inside an `extern "C" fn` is caught at the boundary and converted
to a process abort — destructors between the panic and the boundary may run
(Reference: "either no destructors will run, or all destructors up until the
ABI boundary will run"). Deliberate unwind across a non-unwinding boundary is
in the Reference's UB list ("unwinding past a stack frame that does not allow
unwinding") unless the boundary is declared `"C-unwind"`. Under
`panic="abort"`, no unwinding reaches the boundary at all — the abort
happens at the panic site. This is the mechanism that makes signal-handler
shims of §4.3 dangerous: a panic inside a handler called from kernel context
cannot unwind safely and typically aborts.

### 3.10 Runtime shutdown and what cleanup runs on each path

[std guarantee] unless marked. Composition of §1.6, §3.3, §3.5, and `rt.rs`:

| Termination | Rust destructors | Panic hook | C `atexit` / stdio flush | Rust `BufWriter` flush | Exit status |
|---|---|---|---|---|---|
| return from `main` | current thread's locals; **other threads killed mid-flight** ("When the main thread of a Rust program terminates, the entire program shuts down, even if other threads are still running, and any destructors on the remaining threads' stacks may not be executed") | n/a | yes / yes | yes (drop-based) | `report()` value |
| `main` returns `Err` | yes | n/a | yes / yes | yes | `1` + `Error: {err:?}` |
| main-thread panic (unwind) | main thread's frames | yes | yes / yes | yes | **101** (`rt.rs`: `unwrap_or_else` returns 101) |
| spawned-thread panic | that thread's frames | yes | n/a (process continues) | n/a | unchanged |
| `process::exit(n)` | none, any thread | no | **yes** / yes | **no** | `n & 0xff` on most Unix |
| `process::abort()` | none | **no** | no / no | **no** | SIGABRT [platform Unix] |
| `panic="abort"` panic | none | **yes** | no / no | **no** | abort |
| OS default signal death (SIGTERM/SIGINT) | none (no handler installed) | n/a | no / no | **no** | signal death, parent sees signal (§4) |

### 3.11 Process vs. thread vs. child

- **Process**: exit paths above; `process::id()` (1.26.0) is the PID.
- **Thread**: terminated by returning from its closure; a panic ends only
  that thread, observable via `join() -> Err` ("the thread will exit, but the
  panic may optionally be detected from a different thread with `join`").
  There is **no cancellation API** in std — no `thread::cancel`; cooperative
  shutdown is via channels/atomics. Dropping a `JoinHandle` detaches.
- **Child**: created by `Command::spawn`; terminated by the child itself or
  `Child::kill()` (SIGKILL [platform Unix]); reaped only by explicit
  `wait`/`try_wait`/`wait_with_output` (§5).

---

## 4. Signals and OS Interaction

### 4.1 The documented gap: no std signal API

`std` contains **no** signal-registration, masking, or handler API — there is
no `std::signal`, no mask types, nothing in `std::os::unix::process` for
handler installation. The std::process module doc confirms its own scope:
"This module is mostly concerned with spawning and interacting with child
processes, but it also provides `abort` and `exit` for terminating the
current process" — that is the entire termination-adjacent surface. The
**consequences**:

- Default OS dispositions govern an ordinary Rust program: Ctrl-C (SIGINT)
  terminates it, SIGTERM terminates it, SIGPIPE would terminate it — except
  the runtime modifies exactly one disposition (§4.5).
- Graceful-shutdown behavior (trap SIGTERM, close listeners, flush, exit 0)
  is **not expressible in std** and must come from third-party crates or FFI.
- Signal-related *status interpretation* of children, by contrast, is fully
  in std via `ExitStatusExt` (§5.6).

The closest std feature to "signal policy" is `CommandExt::process_group`
(§5.8): "Process groups determine which processes receive signals" — std
shapes *delivery to children*, but never *reception*.

### 4.2 Third-party crates (named, linked, not deeply inventoried)

**[third-party]** — these are ecosystem crates, not std guarantees, with no
Rust-project compatibility contract:

- **signal-hook** — docs.rs/signal-hook (0.4.5 at retrieval): iterator-, flag-,
  and pipe-based signal handling; internally splits a `signal-hook-registry`
  core from the blocking interfaces. The registry pattern is the accepted way
  to keep handler code async-signal-safe: the handler only enqueues.
- **ctrlc** — docs.rs/ctrlc (3.5.2 at retrieval): minimal Ctrl-C/SIGINT
  handling with a plain callback.
- **tokio::signal** — docs.rs/tokio → `tokio::signal` module (tokio 1.53.2 at
  retrieval): async streams (`signal::ctrl_c()`, `unix::signal(SignalKind::…)`
  — Unix-gated), integrating shutdown into async task trees; also provides
  `tokio::process` with `kill_on_drop` (§5.4).

For the OS-level semantics these wrap (sigaction rules, masks, signalfd), the
book's interface chapters are authoritative:
[../../linux/process-exit-signal/interfaces/sigaction-signal.md](../../linux/process-exit-signal/interfaces/sigaction-signal.md).

### 4.3 The libc-FFI pattern and what the programmer owes the ABI

Without a crate, registration goes through the **[third-party] `libc` crate**
(or raw `extern` declarations). Sketch (illustrative — exact libc signatures
are the crate's contract, not std's):

```rust
use std::sync::atomic::{AtomicBool, Ordering};

static GOT_SIGINT: AtomicBool = AtomicBool::new(false);

extern "C" fn on_sigint(_sig: i32) {
    // async-signal-safe: one lock-free store, no allocator, no locks, no panic
    GOT_SIGINT.store(true, Ordering::SeqCst);
}

fn main() {
    unsafe {
        // signal(2) shown for brevity; POSIX-correct code uses sigaction(2)
        libc::signal(libc::SIGINT, on_sigint as usize);
    }
    while !GOT_SIGINT.load(Ordering::SeqCst) { /* poll or block elsewhere */ }
}
```

What the programmer owes the ABI (per POSIX sigaction rules, which std does
not soften):

1. **Async-signal-safety**: only lock-free atomics, `volatile` writes, or
   `write(2)`-style syscalls inside the handler; no allocation, no mutexes,
   no `println!`, no panicking (a panic here tries to unwind through
   non-Rust frames — §3.9 says that aborts, at best).
2. **Valid pointers**: `sigaction` structs must be fully initialized; the
   handler address must be a real `extern "C" fn`; this is `unsafe` Rust
   territory ([../rust/unsafe.md](../rust/unsafe.md)).
3. **Shared state hygiene**: `static mut` is unsafe to access and racy;
   atomics (as above) or the registry pattern of §4.2 are the standard
   answers.

### 4.4 Signals and threads

- **Which thread runs the handler**: with `signal(2)`/`sigaction(2)` semantics
  a directed signal is handled by *some* thread that does not block it —
  process-directed signals may be delivered to any eligible thread; the
  blocking set is per-thread and **inherited by `std::thread::spawn`
  children through pthread creation** (OS inheritance, not a std guarantee).
- **Handler-state restrictions**: the hook or closure runs on the delivering
  thread, so any state it touches must be `Sync` (atomics, `Mutex` is unsafe
  in-handler per §4.3); `PanicHookInfo` is `!Send`/`!Sync` for the same
  reason hooks are not arbitrary code.
- **Signals vs panics are orthogonal**: SIGSEGV from buggy `unsafe` is a
  hardware signal; std installs stack-overflow guard-page detection for
  *stack overflow* reporting at startup (`stack_overflow::init()`, std source
  `rt.rs`) but no general fault handler.

### 4.5 Where the runtime *does* change OS semantics

[std guarantee] with source anchors; both are implementation-verified rather
than reference-documented:

1. **SIGPIPE is set to ignore at startup.** Std source (`sys/pal/unix/mod.rs`,
   retrieved 2026-10): "By default, some platforms will send a *signal* when
   an EPIPE error would otherwise be delivered... Hence, we set SIGPIPE to
   ignore when the program starts up in order to prevent this problem." So
   writing to a closed pipe yields `io::Error` (EPIPE) rather than killing
   the process — a real departure from raw C defaults that surprises nobody
   who has debugged a C program and surprises every C programmer reading
   Rust logs. Command-spawned children are unaffected unless they are Rust
   too (each Rust runtime sets its own).
2. **Std fds are sanitized.** At startup std ensures fds 0/1/2 are open,
   opening `/dev/null` for any that are closed (same source) — closing
   stdin/stdout before spawning children cannot silently leak low-numbered
   fds into the child's `Stdio::inherit()`.
3. Everything else — handlers, masks, timers — is untouched: the runtime is
   thin. POSIX vs Linux deltas: both facts above are Unix-runtime behavior
   ([platform Unix]); the *underlying* disposition rules are documented in
   the book's Linux signal chapters.

---

## 5. Subprocess and Child-Process Management

### 5.1 `Command` — the builder surface

`pub struct Command { /* private fields */ }` (1.0.0). Constructor and
defaults ([std guarantee], std::process::Command):

> `pub fn new<S: AsRef<OsStr>>(program: S) -> Command` — "No arguments to the
> program / Inherit the current process's environment / Inherit the current
> process's working directory / Inherit stdin/stdout/stderr for `spawn` or
> `status`, but create pipes for `output`". "If `program` is not an absolute
> path, the `PATH` environment variable will be searched in an OS-defined
> way."

| API | Canonical signature | Since | Notes |
|---|---|---|---|
| `arg` | `pub fn arg<S: AsRef<OsStr>>(&mut self, arg: S) -> &mut Command` | 1.0.0 | one literal argument; "the argument is not passed through a shell" |
| `args` | `pub fn args<I, S>(&mut self, args: I) -> &mut Command where I: IntoIterator<Item = S>, S: AsRef<OsStr>` | 1.0.0 | many literal arguments |
| `env` | `pub fn env<K, V>(&mut self, key: K, val: V) -> &mut Command where K: AsRef<OsStr>, V: AsRef<OsStr>` | 1.0.0 | insert/override; explicit values take precedence over inherited |
| `envs` | `pub fn envs<I, K, V>(&mut self, vars: I) -> &mut Command` | 1.19.0 | bulk `env` |
| `env_remove` | `pub fn env_remove<K: AsRef<OsStr>>(&mut self, key: K) -> &mut Command` | 1.0.0 | removes explicit value **and prevents inheritance** |
| `env_clear` | `pub fn env_clear(&mut self) -> &mut Command` | 1.0.0 | no inheritance at all |
| `current_dir` | `pub fn current_dir<P: AsRef<Path>>(&mut self, dir: P) -> &mut Command` | 1.0.0 | child cwd; relative-`program` + `current_dir` interaction is "platform specific and unstable" per docs |
| `stdin` | `pub fn stdin<T: Into<Stdio>>(&mut self, cfg: T) -> &mut Command` | 1.0.0 | default inherit (spawn/status), piped (output) |
| `stdout` | `pub fn stdout<T: Into<Stdio>>(&mut self, cfg: T) -> &mut Command` | 1.0.0 | same defaults |
| `stderr` | `pub fn stderr<T: Into<Stdio>>(&mut self, cfg: T) -> &mut Command` | 1.0.0 | same defaults |
| `spawn` | `pub fn spawn(&mut self) -> Result<Child>` | 1.0.0 | async-by-OS start; `io::Error` only for spawn-time failures |
| `status` | `pub fn status(&mut self) -> Result<ExitStatus>` | 1.0.0 | spawn + wait, stdio inherited |
| `output` | `pub fn output(&mut self) -> Result<Output>` | 1.0.0 | spawn + capture both streams + wait |
| `get_program` | `pub fn get_program(&self) -> &OsStr` | 1.57.0 | introspection |
| `get_args` | `pub fn get_args(&self) -> CommandArgs<'_>` | 1.57.0 | excludes argv[0] |
| `get_envs` | `pub fn get_envs(&self) -> CommandEnvs<'_>` | 1.57.0 | explicit mappings only; `None` value = removed |
| `get_current_dir` | `pub fn get_current_dir(&self) -> Option<&Path>` | 1.57.0 | `None` = inherit |

Documented error taxonomy for `spawn` ([std guarantee]): program not found
(bare name absent from `PATH`), permission denied (incl. seccomp policy),
and resource exhaustion; "An error is only returned for failures that occur
while the child is being spawned. Once the child has started successfully...
anything that happens to it afterwards — including being terminated by a
signal — is reported through its `ExitStatus` rather than as an error."
`output()`/`status()` add read/wait failures; an unsuccessful child exit or
signal death is **`Ok`**, with the outcome in the status. Documented panics:
none on this surface.

`Command` is reusable: "you can call builder methods after spawning a process
and then spawn a new process with the modified settings" (docs example).

**PATH resolution deltas** [platform Unix] / [platform Windows]: on Unix the
searched `PATH` comes from the *child's* environment — if `env_remove`/
`env_clear` drops `PATH` without replacement, "`execvp` falls back to an
OS-defined default (typically `/bin:/usr/bin`), not the parent's `PATH`".
On Windows, Rust resolves the executable itself before `CreateProcessW`
(child `PATH` if explicitly set → current executable's directory → system
directory → Windows directory → parent's `PATH`). These are documented
current behaviors, flagged by the docs themselves as changeable.

### 5.2 The `Child` handle

```rust
pub struct Child {
    pub stdin: Option<ChildStdin>,
    pub stdout: Option<ChildStdout>,
    pub stderr: Option<ChildStderr>,
    /* private fields */
}
```

`Some` only for streams configured `Stdio::piped()`. The docs recommend
`child.stdin.take()` to avoid partially moving the handle.

| API | Canonical signature | Since | Semantics / notes |
|---|---|---|---|
| `id` | `pub fn id(&self) -> u32` | 1.3.0 | child PID |
| `kill` | `pub fn kill(&mut self) -> Result<()>` | 1.0.0 | "This is equivalent to sending a SIGKILL on Unix platforms"; `Ok(())` if already exited |
| `wait` | `pub fn wait(&mut self) -> Result<ExitStatus>` | 1.0.0 | "The stdin handle to the child process, if any, will be closed before waiting" — EOF signaling; idempotent result afterwards |
| `try_wait` | `pub fn try_wait(&mut self) -> Result<Option<ExitStatus>>` | 1.18.0 | non-blocking; "If the child has exited then on Unix the process ID is reaped"; "unlike `wait`, this function will not attempt to drop stdin" |
| `wait_with_output` | `pub fn wait_with_output(self) -> Result<Output>` | 1.0.0 | consumes the child; closes stdin; drains both pipes to EOF; returns `Output` |

The docs' own deadlock warning applies to any hand-rolled feed-drain
combination ("Writing more than a pipe buffer's worth of input to stdin
without also reading stdout and stderr at the same time may cause a
deadlock", std::process::Stdio) — see §5.5.

### 5.3 `Output`, `ExitStatus`

```rust
pub struct Output {
    pub status: ExitStatus,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}
```

(raw bytes — decoding is the caller's job). `ExitStatus`
(`pub struct ExitStatus(/* private fields */)`, 1.0.0) represents "every
possible disposition of a process. On Unix this is the wait status. It is not
simply an exit status (a value passed to `exit`)". Methods:

| API | Canonical signature | Since | Semantics |
|---|---|---|---|
| `success` | `pub fn success(&self) -> bool` | 1.0.0 | "Signal termination is not considered a success, and success is defined as a zero exit status" |
| `code` | `pub fn code(&self) -> Option<i32>` | 1.0.0 | exit status if exited normally; "On Unix, this will return `None` if the process was terminated by a signal"; also documents 8-bit truncation and runtime-invented codes ("often, for example, 255, 254, 127 or 126") |
| `Display` | `impl Display for ExitStatus` | 1.0.0 | "For proper error reporting of failed processes, print the value" — format is informational |
| `Default` | successful-completion status | 1.73.0 | |

**[platform Unix]** `ExitStatusExt` (trait, 1.0.0; "This trait cannot be
implemented outside std") — verified per-method since-versions:

| Method | Signature | Since | Maps to |
|---|---|---|---|
| `from_raw` | `fn from_raw(raw: i32) -> Self` | 1.12.0 | build from a **wait status** ("The value should be a wait status, not an exit status"; bit layout not POSIX-specified; docs walk the signal/exit conventions) |
| `signal` | `fn signal(&self) -> Option<i32>` | 1.0.0 | `WIFSIGNALED` → `WTERMSIG`; then `code()` is `None` |
| `core_dumped` | `fn core_dumped(&self) -> bool` | 1.58.0 | `WCOREDUMP` |
| `stopped_signal` | `fn stopped_signal(&self) -> Option<i32>` | 1.58.0 | `WSTOPSIG` — "only possible if the status came from a `wait`... passed `WUNTRACED`" |
| `continued` | `fn continued(&self) -> bool` | 1.58.0 | `WIFCONTINUED` — requires `WCONTINUED` |
| `into_raw` | `fn into_raw(self) -> i32` | 1.0.0 | the raw 16-bit wait-status word |

The `signal` docs also encode the shell convention cross-reference: "many
shells convert the signal number into an exit code by adding 128. For
example, a command run under `sh` that receives a `SIGTERM` canonically
causes the shell to report an exit code of `15 + 128`, i.e. `143`" — i.e.
that 128+N is a *shell* behavior, not an OS one; a Rust parent watching a
signaled child sees `code() == None` and `signal() == Some(N)` directly.

`ExitStatus::exit_ok` (nightly, `exit_status_error`) is the future
`Result`-flavored check.

### 5.4 `Child` drop semantics — documented non-killing, non-reaping

Verified documentation ([std guarantee], std::process::Child):

> "There is no implementation of `Drop` for child processes, so if you do not
> ensure the `Child` has exited then it will continue to run, even after the
> `Child` handle to the child process has gone out of scope."

> "The standard library does not automatically wait on child processes (not
> even if the `Child` is dropped), it is up to the application developer to
> do so. As a consequence, dropping `Child` handles without waiting on them
> first is not recommended in long-running applications."

Consequences:

- Dropping a `Child` **does not kill** and **does not reap**. The child keeps
  running; after it exits it is a **zombie** until the parent waits or exits
  (the Child docs' Warning: "Leaving too many zombies around may exhaust
  global resources (for example process IDs)").
- On parent death the orphaned child (and any zombie) is reparented to the
  system reaper ([Linux]: `pid_namespaces(7)` semantics — see the Linux
  part of this book).
- **std has no `kill_on_drop`.** [third-party] tokio's
  `tokio::process::Command::kill_on_drop(bool)` provides that opt-in; std
  offers nothing similar, and long-lived daemons must track `Child` handles
  and wait them (or delegate reaping to a dedicated thread).

### 5.5 Streams and the pipe-buffer deadlock

`Stdio` (`pub struct Stdio(/* private fields */)`, 1.0.0) constructors:
`piped()`, `inherit()`, `null()` ("the equivalent of attaching the stream to
`/dev/null`"). `From` conversions verified on the page:
`From<ChildStdin>`, `From<ChildStdout>`, `From<ChildStderr>`,
`From<File>`, `From<Stdout>`, `From<Stderr>`, `From<OwnedFd>`,
`From<PipeReader>`, `From<PipeWriter>` — the child-stream conversions are
how the classic two-process pipeline is built (std::process module example:
`Stdio::from(echo_child.stdout...)`).

The deadlock geometry ([std guarantee] warning quoted in §5.2; pipe capacity
is a kernel property [Linux], 64 KiB default — see the book's pipe pages):

- `output()`/`wait_with_output()` drain stdout and stderr **concurrently** —
  safe for any child output volume.
- `spawn()` + read only stdout while the child writes more than a pipe
  buffer of stderr → the child blocks on stderr, the parent blocks on
  stdout: **classic two-pipe deadlock**. Fixes: drain both (threads or
  `wait_with_output`), or `stderr(Stdio::null())`, or `inherit()`.
- Writing to `child.stdin` while also waiting → mirror deadlock: the child
  blocks writing stdout while the parent blocks writing stdin. `wait()`'s
  documented "stdin handle... closed before waiting" exists precisely to
  break one half of this; for feed-then-read pipelines, drop
  `child.stdin` explicitly to signal EOF before draining, or feed from a
  spawned thread (the `rev` example in std Stdio docs does exactly this).

### 5.6 Status interpretation end-to-end

```rust
use std::process::{Command, Stdio};
use std::os::unix::process::ExitStatusExt; // [platform Unix]

let mut child = Command::new("sleep").arg("3600").spawn()?;
child.kill()?;                                   // SIGKILL on Unix
let st = child.wait()?;                          // reap
assert!(!st.success());
assert_eq!(st.code(), None);                     // signal death: no exit code
assert_eq!(st.signal(), Some(9));                // WTERMSIG equivalent
assert!(!st.core_dumped());                      // SIGKILL dumps no core
```

For `sh -c "cmd"` wrappers remember §5.3: only the *shell's* status is
visible; the documented 128+N conversion (§5.3) is the shell's doing, so
`Command::new("sh").arg("-c").arg(script).status()` returning
`code() == Some(143)` means the *inner command* died of SIGTERM, while
`signal() == Some(15)` means the shell itself did. Design wrappers that need
the distinction accordingly (or use `process_group` + direct signaling).

### 5.7 Unix `CommandExt` — the platform extension surface

**[platform Unix]** `std::os::unix::process::CommandExt` (trait, 1.0.0; "This
trait cannot be implemented outside std"). Verified current method set:

| Method | Signature | Since | Semantics / notes |
|---|---|---|---|
| `uid` | `fn uid(&mut self, id: u32) -> &mut Command` | 1.0.0 | `setuid` in child; failure fails the spawn; triggers `setgroups(0, NULL)` unless `groups` set |
| `gid` | `fn gid(&mut self, id: u32) -> &mut Command` | 1.0.0 | `setgid` in child |
| `pre_exec` | `unsafe fn pre_exec<F>(&mut self, f: F) -> &mut Command where F: FnMut() -> Result<()> + Send + Sync + 'static` | 1.34.0 | closure after fork, before exec (§ below) |
| `exec` | `fn exec(&mut self) -> Error` | 1.9.0 | replace current process via `execvp`; **no fork** (§ below) |
| `arg0` | `fn arg0<S>(&mut self, arg: S) -> &mut Command where S: AsRef<OsStr>` | 1.45.0 | argv[0] override |
| `process_group` | `fn process_group(&mut self, pgroup: i32) -> &mut Command` | 1.64.0 | "Equivalent to a `setpgid` call in the child process, but may be more efficient... Process groups determine which processes receive signals" — `0` uses the child PID as PGID |
| `groups` | `fn groups(&mut self, groups: &[u32]) -> &mut Command` | **nightly** (`setgroups`) | supplementary groups |
| `chroot` | `fn chroot<P: AsRef<Path>>(&mut self, dir: P) -> &mut Command` | **nightly** (`process_chroot`) | chroot before exec |
| `setsid` | `fn setsid(&mut self, setsid: bool) -> &mut Command` | **nightly** (`process_setsid`) | new session |
| `before_exec` | `unsafe fn before_exec<F>(...)` | 1.15.0 | **deprecated since 1.37.0** — "use `pre_exec` instead" |

*Note:* the sibling exit-signal chapter listed `setsid` and `chroot` as
available; per the current docs both (and `groups`) are nightly-only on this
build — correct your expectations accordingly.

**`pre_exec` contract** (verified docs): runs "in the context of the child
process after a `fork`... a very constrained environment where normal
operations like `malloc`, accessing environment variables through
`std::env` or acquiring a mutex are not guaranteed to work (due to other
threads perhaps still running when the `fork` was run)" — the async-signal-
safety discipline again; "the list of allocating functions includes
`Error::new` and `Error::other`. To signal a non-trivial error, prefer
`panic!`"; std calls `std::panic::always_abort` (nightly API) before the
hook, so hook panics abort rather than unwind, "safe only if all the format
arguments for the panic message can be safely formatted". This is the one
place safe-looking Rust runs inside the fork window — treat it like a signal
handler (§4.3).

**`exec` contract**: "On success this function will not return, and
otherwise it will return an error"; "`exec` not returning has the same
implications as calling `process::exit` — no destructors on the current
stack or any other thread's stack will be run"; and the warning that on
error "the process may be in a 'broken state'... the working directory,
environment variables, signal handling settings, various user/group
information, or aspects of stdio file descriptors may have changed" —
non-transactional by design.

### 5.8 `ChildStdin`/`ChildStdout`/`ChildStderr` and fd ownership

**[platform Unix]** these stream types implement `Read`/`Write` (1.0.0),
`AsFd`/`AsRawFd`, and `IntoRawFd`; `From<OwnedFd> for ChildStdin` (and
siblings) since 1.74.0 lets you hand a specific fd to a child; conversely
`From<ChildStdin> for OwnedFd` extracts the raw descriptor into an owned
wrapper. The `unsafe` boundary is `FromRawFd::from_raw_fd` (method since
1.1.0, now in `std::os::fd`): constructing an owning wrapper from an integer
asserts exclusive ownership — misuse causes double-close (UB at the OS
layer). Ownership rules are §6.5; the unsafe-toolbox survey is
[../rust/unsafe.md](../rust/unsafe.md).

### 5.9 Timeout and cancellation — the documented gap and the standard pattern

std has **no timeout parameter** on `Command`/`Child` and no async
cancellation. The standard workaround pattern (all std; shown inside
`fn main() -> std::io::Result<()>`):

```rust
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

fn main() -> std::io::Result<()> {
    let child = Arc::new(Mutex::new(
        Command::new("worker").stdout(Stdio::null()).spawn()?,
    ));
    let timed_out = Arc::new(AtomicBool::new(false));
    let (c, flag) = (Arc::clone(&child), Arc::clone(&timed_out));
    std::thread::spawn(move || {
        let start = Instant::now();
        while start.elapsed() < Duration::from_secs(30) {
            if c.lock().unwrap().try_wait().map(|s| s.is_some()).unwrap_or(true) {
                return;                        // child already exited
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        let _ = c.lock().unwrap().kill();      // SIGKILL at deadline
        flag.store(true, Ordering::SeqCst);
    });
    let status = child.lock().unwrap().wait()?; // reaps either way
    if timed_out.load(Ordering::SeqCst) { /* timed out: status is signal-death */ }
    Ok(())
}
```

Invariants the pattern must preserve: kill-then-wait (reap) even on timeout
(§5.4); a timed-out kill surfaces as signal death in the status; polling via
`try_wait` keeps the main thread free. [third-party] tokio::process provides
async `wait` + cancellation; std provides the primitives only.

### 5.10 Argument-array safety vs. shell strings

- `Command` **never routes through a shell**: "the arguments are not passed
  through a shell, but given literally to the program. This means that shell
  syntax like quotes, escaped characters, word splitting, glob patterns,
  variable substitution, etc. have no effect" (arg/args docs). Argument
  arrays go to `execve`/`execvp` verbatim — the injection surface
  `sh -c`-style wrappers have is structurally absent.
- The builder's one documented footgun: "`Command::new` is only intended to
  accept the path of the program. If you pass a program path along with
  arguments like `Command::new("ls -l").spawn()`, it will try to search for
  `ls -l` literally" (docs Caveats).
- **Opt-in shell**: `Command::new("sh").arg("-c").arg(script)` reintroduces
  every quoting hazard; the script string is untrusted input again (shell
  conventions in the book's shell chapters; C's `system()` analysis in
  [./c.md](./c.md)).
- **[platform Windows] deltas** (named briefly): `cmd.exe`/`.bat` decode
  arguments non-standardly and "are therefore vulnerable to malicious input"
  (docs warning; `raw_arg` exists for manual encoding); executable
  resolution uses the Windows search order of §5.1 and `.exe` may be
  omitted. POSIX `execve`-style argument semantics are the Unix contract.

### 5.11 Zombies and orphans

- **Zombie**: exited child not yet waited. std never reaps implicitly
  (§5.4 quote); `wait`/`try_wait`/`wait_with_output` are the reapers
  (`try_wait`: "on Unix the process ID is reaped"). Daemons: track children,
  reap on SIGCHLD — impossible in pure std without a signal handler (§4) —
  or poll with `try_wait`, or exit the parent and let the reaper inherit.
- **Orphan**: parent died first; reparented to the system reaper ([Linux];
  in containers the PID-1 reaping rules of the Linux part of this book
  apply).
- `process::exit` abandons children *and* their statuses: the dying process
  can no longer wait, so any still-unreaped zombie is only reaped when the
  parent itself is reaped by init.

---

## 6. Concurrency and Resource Semantics

### 6.1 The threading model

"An executing Rust program consists of a collection of native OS threads,
each with their own stack and local state" (std::thread module). There is no
scheduler, no green threads, no GC — threads are pthreads ([platform Unix])
and the module docs' model statements govern:

> "When the main thread of a Rust program terminates, the entire program
> shuts down, even if other threads are still running, and any destructors
> on the remaining threads' stacks may not be executed."

So: **main-thread return is a process kill switch for other threads** —
another reason graceful shutdown wants explicit join-on-shutdown (or a
`Termination` type whose `report` coordinates workers before returning).

### 6.2 `Send`/`Sync` and scoped threads

`spawn`'s bounds (`F: FnOnce() -> T + Send + 'static, T: Send + 'static`)
make data races across threads unrepresentable in safe code: shared mutable
state must be `Sync` (behind `Arc<Mutex<_>>`, atomics, etc.), transferred
state must be `Send`. **Scoped threads** (`thread::scope`, 1.63.0) relax the
`'static` bound: "scoped threads can borrow non-'static data, as the scope
guarantees all threads will be joined at the end of the scope. All threads
spawned within the scope that haven't been manually joined will be
automatically joined before this function returns." Two documented caveats:
joining waits only for the thread's main function — "even when this function
returns, destructors of thread-local variables in these threads might still
be running" — and "If any of the automatically joined threads panicked, this
function will panic."

Stack sizes: `Builder::stack_size` or `RUST_MIN_STACK`; default "2 MiB on
all Tier-1 platforms" (module docs, subject to change); the main thread's
stack is OS-provided and not Rust-determined.

### 6.3 Thread panic isolation

A panicking spawned thread: hook runs → that thread's frames unwind →
`join()` yields `Err(JoinError)` → process continues. Only the main thread's
panic ends the process (101). Under `panic="abort"`, any thread's panic ends
the process — the isolation property is a property of the *strategy*, not
the thread. `JoinError::is_panic()` distinguishes panic-termination from
normal completion; `is_finished()` (1.61.0) supports poll-based joins.

### 6.4 fd/handle ownership

Ownership maps OS resources onto the type system:

- Owning wrappers: `File`, `OwnedFd` (1.66.0 at its `std::os::fd` home),
  `ChildStdin/ChildStdout/ChildStderr`, `Child` itself (a process handle).
  Drop closes/releases exactly once — the double-close hazard is reachable
  only through `unsafe` (`from_raw_fd` on a borrowed fd, or raw-pointer
  aliasing games).
- Borrowing views: `AsFd`/`BorrowedFd<'a>` ("BorrowedFd values cannot
  outlive..." their owner — lifetime-typed, per the `std::os::unix::io`
  module docs).
- The escape hatches — `AsRawFd`/`IntoRawFd`/`FromRawFd` — are the documented
  unsafe contract: "Constructs a new instance of Self from the given raw
  file descriptor... will take responsibility for closing it" (FromRawFd
  docs). `mem::forget` on an owning wrapper *leaks* the fd (safe but a
  resource leak, §6.8).
- `Child`'s streams are fds under the hood; `wait()` closing `child.stdin`
  (§5.2) is std exercising exactly this ownership protocol on your behalf.

### 6.5 Buffering and flush-on-drop

Verified BufWriter docs ([std guarantee]):

> "It is critical to call `flush` before `BufWriter<W>` is dropped. Though
> dropping will attempt to flush the contents of the buffer, any errors that
> happen in the process of dropping will be ignored. Calling `flush` ensures
> that the buffer is empty and thus dropping will not even attempt to
> flush."

Consequences by termination path: on normal return, drop-flush runs but
**swallows errors** (a full disk during teardown is silent); on
`process::exit`/abort/`panic="abort"`/signal death, drop-flush never runs at
all (§3.10). Crash-safe output therefore writes unbuffered (or flushes
explicitly before exit points); `flush()` returning `Err` is the only
observable signal. `Child::wait` closing the child's stdin is the
pipe-flush equivalent on the subprocess side (§5.2).

### 6.6 Mutex poisoning

Verified (std::sync::Mutex docs): "The mutexes in this module implement a
strategy called 'poisoning' where a mutex becomes poisoned if it recognizes
that the thread holding it has panicked. Once a mutex is poisoned, all other
threads are unable to access the data by default as it is likely tainted."
`lock`/`try_lock` return `Result`; `PoisonError::into_inner` recovers the
guard ("Poisoning is only advisory"). The docs' honesty section matters for
subprocess-style code: panics while holding a lock *inside a `Drop` or panic
hook* can leave the mutex unpoisoned, locks acquired across panic contexts
behave unexpectedly, and "Foreign exceptions do not currently trigger
poisoning". Poisoning also does not exist on abort paths — there is no
thread left to consult it.

### 6.7 Deadlocks, races, and leaks — the process-adjacent inventory

- **Pipe deadlock** (§5.5) — the classic; documented by std and structural.
- **Exit race**: `process::exit` from thread A while thread B is mid-`Drop`
  (flushing, releasing a lock) — B's work is lost mid-operation; plus the
  documented concurrent-`exit` UB with C (§3.3). Coordinate shutdown through
  a join barrier before any thread calls `exit`.
- **Lock-order deadlock**: std does not detect or prevent it; poisoning (§6.6)
  only marks the *aftermath* of panics.
- **Thread leak**: detached threads that never terminate hold `'static`
  captures forever — the spawn docs: "It is the responsibility of the
  program to either eventually join threads it creates or detach them;
  otherwise, a resource leak will result." Scoped threads close the
  borrow-safety hole; they cannot close a never-terminating closure.
- **Child leak / zombie accumulation** (§5.4, §5.11) — the signature Rust
  subprocess leak; reaping is the fix.
- **fd leaks**: forgotten owned wrappers (safe `mem::forget`), inherited fds
  smuggled into children (leaked-fd hazard; on Unix your fds are inherited
  unless `O_CLOEXEC` — std's own fds set CLOEXEC, yours don't), or
  `pre_exec` closures that fail to close (§5.7).

### 6.8 Drop during unwinding vs. exit vs. abort — consolidated

| Phase | `Drop` runs? | Notes |
|---|---|---|
| normal scope exit | yes, reverse declaration order | Reference drop scopes |
| unwinding panic | yes, frame by frame | payload-drop may re-panic (§3.8) |
| `panic="abort"` | no | hook still ran (§3.6) |
| `process::exit` | no, all threads | atexit still runs (§3.3) |
| `process::abort` | no | nothing runs (§3.5) |
| unwinding into `extern "C"` | up to the boundary, or none | Reference rule (§3.9) |
| main-thread return with live threads | current thread only | others killed (§6.1) |
| scope end (`thread::scope`) | locals after joins; thread-locals *may lag* | documented TL caveat (§6.2) |

The design consequence repeats from §1.5: Rust *guarantees* drop on the
normal and unwind paths, and *explicitly disclaims* it everywhere else —
which is why every "graceful shutdown" design in this chapter reduces to
"get the last exit to be a return from `main`".

---

## Coverage ledger

The per-item coverage ledger for this chapter is
[ledger-rust.md](./ledger-rust.md) (IDs `PL-RS-001`…`PL-RS-076`, G4 schema).
Rollup at publication: **Inventoried: 76 / Documented: 73 / Remaining: 0 /
Source-limited: 3** — the source-limited rows are the third-party crates
(ctrlc, signal-hook, tokio) whose *internal* signal-delivery machinery is
outside the std-docs source of record (crates named and linked; not deeply
inventoried, per Section-G scope discipline). Signature source of truth:
doc.rust-lang.org/std item pages for build 1.99.0 (retrieved 2026-10);
Rust Reference for language rules; Cargo Book for panic profiles;
rust-lang/rust source for numeric anchors (exit 101; SIGPIPE startup).

## References

1. The Rust Standard Library documentation — doc.rust-lang.org/std (build
   1.99.0, `b940084d7`, 2026-09-28; retrieved 2026-10): `std::process`
   (module; `exit`, `abort`, `id`; `Termination`, `ExitCode`, `Command`,
   `Child`, `ExitStatus`, `Output`, `Stdio`, `ChildStdin`), `std::panic`
   (`set_hook`, `take_hook`, `catch_unwind`, `resume_unwind`, `panic_any`,
   `update_hook`, `PanicHookInfo`, `UnwindSafe`), `std::thread` (module;
   `spawn`, `scope`, `JoinHandle`, `Builder`, `available_parallelism`),
   `std::sync::Mutex`, `std::io::BufWriter`, `std::os::unix::process`
   (`CommandExt`, `ExitStatusExt`, `parent_id`), `std::os::fd`
   (`OwnedFd`, `FromRawFd`).
2. The Rust Reference — doc.rust-lang.org/reference (retrieved 2026-10):
   *Behavior considered undefined*; *Destructors* (drop scopes; Not running
   destructors; Process termination without unwinding).
3. The Cargo Book — doc.rust-lang.org/cargo/reference/profiles.html
   (retrieved 2026-10): the `panic` profile setting (`unwind`/`abort`).
4. rust-lang/rust source (master, retrieved 2026-10):
   `library/std/src/rt.rs` (exit code 101; `unique_thread_exit`;
   `stack_overflow::init()`), `library/std/src/sys/pal/unix/mod.rs`
   (SIGPIPE set to ignore at startup; std fd sanitization),
   `library/std/src/process.rs` (`Termination for Result` impl: `Error:
   {err:?}` + `ExitCode::FAILURE`).
5. Third-party crates (named, not deeply inventoried; docs.rs, retrieved
   2026-10): signal-hook 0.4.5 (docs.rs/signal-hook), ctrlc 3.5.2
   (docs.rs/ctrlc), tokio 1.53.2 (docs.rs/tokio — `tokio::signal`,
   `tokio::process::Command::kill_on_drop`); libc crate (github.com/rust-lang/libc)
   as the FFI substrate of §4.3.
6. Sibling chapters: [../../linux/process-exit-signal/languages/rust.md](../../linux/process-exit-signal/languages/rust.md)
   (exit/signal slice, 1.61–1.8x era); [./c.md](./c.md) and
   [./cpp.md](./cpp.md) (C-family substrate of wait-status words and
   `atexit`); part hub [./index.md](./index.md).
7. Interview-topic cross-links: [../rust/ownership.md](../rust/ownership.md),
   [../rust/lifetimes.md](../rust/lifetimes.md),
   [../rust/unsafe.md](../rust/unsafe.md).
