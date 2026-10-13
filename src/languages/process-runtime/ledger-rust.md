# Coverage Ledger — Rust (Section G)

**Language project:** Rust — *Language Semantics, Standard Library, Process
APIs, and Subprocesses* (chapter: [rust.md](./rust.md)).

**Scope:** current stable Rust, verified as `std` **1.99.0** (build
`b940084d7`, 2026-09-28) on doc.rust-lang.org — retrieved **2026-10**.
Covers the six Section-G areas for Rust: syntax/semantics as they bear on
process lifecycle, std inventory (process/panic/thread/sync surface),
process creation & termination, signals & OS interaction, subprocess
management, concurrency & resource semantics.

**Verification sources (with dates):**
- doc.rust-lang.org/std — module + item pages for `std::process`,
  `std::panic`, `std::thread`, `std::sync::Mutex`, `std::io::BufWriter`,
  `std::os::unix::process`, `std::os::fd` (build 1.99.0; retrieved 2026-10).
- doc.rust-lang.org/reference — *Behavior considered undefined*,
  *Destructors* (retrieved 2026-10).
- doc.rust-lang.org/cargo/reference/profiles.html — `panic` setting
  (retrieved 2026-10).
- github.com/rust-lang/rust (master, retrieved 2026-10): `library/std/src/rt.rs`
  (exit 101; `unique_thread_exit`; `stack_overflow::init()`),
  `library/std/src/sys/pal/unix/mod.rs` (SIGPIPE ignore at startup; std fd
  sanitization), `library/std/src/process.rs` (`Termination for Result`).
- docs.rs — signal-hook 0.4.5, ctrlc 3.5.2, tokio 1.53.2 (named/linked only;
  retrieved 2026-10).
- Since-versions are only those printed on the cited doc pages; nothing is
  inferred.

**Status definitions:** `documented` = behavior/signature verified against a
cited primary source and explained in the chapter (verified-absent APIs count
as documented limitations); `source-limited` = a named primary source was
unreachable or out of the declared source-of-record scope (missing source
stated in the row); `researched`/`not-started` = not used in this ledger.

**Rollup:** Inventoried: 76 / Documented: 73 / Remaining: 0 / Source-limited: 3

| ID | Language/API or behavior | Canonical signature | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|---|
| PL-RS-001 | `main` entry point: return type must implement `Termination`; no parameters; runtime wraps via `lang_start` | — | §1.1, §3.2 | std::process::Termination; std source `rt.rs` | std 1.99.0 docs; all platforms | documented |
| PL-RS-002 | Drop scopes: reverse declaration order; parameter/temporary scopes; `mem::forget`/`ManuallyDrop` suppression is safe; types may not rely on destructors for soundness | — | §1.2 | Reference: Destructors | Reference, current stable | documented |
| PL-RS-003 | `?` operator: early `return Err(From::from(e))` on `Err`; yields value on `Ok`; panics orthogonal to `Result` | — | §1.3 | std::process::Termination (`Debug` bound); std Result docs | stable Rust | documented |
| PL-RS-004 | UB categories in scope: data races; dangling/misaligned pointer access; invalid values | — | §1.7 | Reference: Behavior considered undefined | stable Rust (list may grow/shrink per Reference) | documented |
| PL-RS-005 | UB: unwinding past a stack frame that does not allow unwinding (`"C-unwind"` through `"C"`); FFI panic boundary rule | — | §1.7, §3.9 | Reference: Behavior considered undefined (undefined.call); std panic::catch_unwind | stable Rust | documented |
| PL-RS-006 | Edition delta: `before_exec` made `unsafe` via the edition mechanism; deprecated for `pre_exec` (1.37.0) | — | §1.8, §5.7 | std os::unix::process::CommandExt | Unix; before_exec since 1.15.0, deprecated 1.37.0 | documented |
| PL-RS-007 | `std::process::exit` | `pub fn exit(code: i32) -> !` | §2.1, §3.3 | std::process::exit | since 1.0.0; all platforms | documented |
| PL-RS-008 | `std::process::abort` | `pub fn abort() -> !` | §2.1, §3.5 | std::process::abort | since 1.17.0; all platforms | documented |
| PL-RS-009 | Current/parent PID accessors | `pub fn id() -> u32`; `pub fn parent_id() -> u32` | §2.1 | std::process::id; std::os::unix::process::parent_id | id since 1.26.0 (all); parent_id since 1.27.0 (Unix) | documented |
| PL-RS-010 | `Termination` trait and complete implementor list (`!`, `()`, `ExitCode`, `Infallible`, `Result<T: Termination, E: Debug>`) | `pub trait Termination { fn report(self) -> ExitCode; }` | §3.2 | std::process::Termination | since 1.61.0 | documented |
| PL-RS-011 | `ExitCode`: private representation; `SUCCESS`/`FAILURE`; `From<u8>`; `PartialEq` only (no `Eq`/`Hash`/raw access); `Default` = SUCCESS | `pub struct ExitCode(/* private fields */)` | §2.1, §3.4 | std::process::ExitCode | since 1.61.0; Default since 1.75.0; `exit_process` nightly | documented |
| PL-RS-012 | `main` returning `Result`: `Err` prints `Error: {err:?}` to stderr, exits `ExitCode::FAILURE`; `Debug` (not `Display`) bound | — | §3.2 | std source `process.rs` (`Termination for Result`); std::process::Termination | since 1.61.0 | documented |
| PL-RS-013 | `std::panic::set_hook` | `pub fn set_hook(hook: Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>)` | §2.2, §3.7 | std::panic::set_hook | since 1.10.0; panics if called from a panicking thread | documented |
| PL-RS-014 | `std::panic::take_hook`: returns current hook, registers default hook in its place | `pub fn take_hook() -> Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send + 'static>` | §2.2, §3.7 | std::panic::take_hook | since 1.10.0 | documented |
| PL-RS-015 | `std::panic::catch_unwind`: unwinding panics only; hook ran first; payload-drop hazard; foreign-exception unspecified outcomes | `pub fn catch_unwind<F: FnOnce() -> R + UnwindSafe, R>(f: F) -> Result<R>` | §2.2, §3.8 | std::panic::catch_unwind | since 1.9.0 | documented |
| PL-RS-016 | `std::panic::resume_unwind`: continues unwind without hook; aborts under `panic="abort"` | `pub fn resume_unwind(payload: Box<dyn Any + Send>) -> !` | §2.2 | std::panic::resume_unwind | since 1.9.0 | documented |
| PL-RS-017 | `std::panic::panic_any`: arbitrary `Any + Send` payload, reachable via `PanicHookInfo::payload` | `pub fn panic_any<M: 'static + Any + Send>(msg: M) -> !` | §2.2 | std::panic::panic_any | since 1.51.0 | documented |
| PL-RS-018 | `PanicHookInfo<'_>` hook parameter type (payload + location; `!Send`/`!Sync`); nightly `update_hook` chain helper | `pub struct PanicHookInfo<'a> { /* private fields */ }` | §2.2, §3.7 | std::panic::PanicHookInfo; core::panic::PanicInfo deprecation note | since 1.81.0; update_hook nightly (`panic_update_hook`) | documented |
| PL-RS-019 | `UnwindSafe` auto trait + `AssertUnwindSafe` wrapper for the `catch_unwind` bound | `pub auto trait UnwindSafe { }` | §2.2, §3.8 | std::panic::UnwindSafe | since 1.9.0 | documented |
| PL-RS-020 | Mutex poisoning: `lock`/`try_lock` return `Result`; `into_inner` recovery; documented blind spots (Drop/hook-held locks, foreign exceptions) | `pub fn lock(&self) -> Result<MutexGuard<'_, T>, PoisonError<MutexGuard<'_, T>>>` | §2.4, §6.6 | std::sync::Mutex | since 1.0.0; `into_inner` 1.2.0 | documented |
| PL-RS-021 | `thread::spawn` bounds (`Send + 'static`), panic on OS failure; join-or-detach resource-leak note | `pub fn spawn<F, T>(f: F) -> JoinHandle<T> where F: FnOnce() -> T + Send + 'static, T: Send + 'static` | §2.3, §6.2 | std::thread::spawn | since 1.0.0 | documented |
| PL-RS-022 | `JoinHandle::join` surfaces thread panics as `Err` | `pub fn join(self) -> Result<T>` | §2.3, §6.3 | std::thread::JoinHandle | since 1.0.0 | documented |
| PL-RS-023 | `JoinHandle::is_finished` non-blocking check; dropping `JoinHandle` detaches the thread | `pub fn is_finished(&self) -> bool` | §2.3, §6.1 | std::thread::JoinHandle | is_finished since 1.61.0; detach-on-drop 1.0.0 | documented |
| PL-RS-024 | Thread configuration & sizing: `Builder` name/stack_size/spawn (`io::Result`); unsafe `spawn_unchecked`; `available_parallelism`; default stack 2 MiB Tier-1; `RUST_MIN_STACK` | `pub fn spawn<F, T>(self, f: F) -> Result<JoinHandle<T>>`; `pub unsafe fn spawn_unchecked<F, T>(self, f: F) -> Result<JoinHandle<T>>`; `pub fn available_parallelism() -> Result<NonZero<usize>>` | §2.3, §6.2 | std::thread module; std::thread::Builder; std::thread::available_parallelism | Builder/spawn 1.0.0; spawn_unchecked 1.82.0; available_parallelism 1.59.0 | documented |
| PL-RS-025 | `thread::scope` + `Builder::spawn_scoped`: joins all unjoined scoped threads before returning; thread-local destructors may lag; panics if auto-joined threads panicked | `pub fn scope<'env, F, T>(f: F) -> T where F: for<'scope> FnOnce(&'scope Scope<'scope, 'env>) -> T` | §2.3, §6.2 | std::thread::scope; std::thread::Builder::spawn_scoped | both since 1.63.0 | documented |
| PL-RS-026 | `BufWriter` flush-on-drop: drop attempts flush, **errors ignored**; explicit `flush()` required for observable errors | — | §6.5 | std::io::BufWriter (Drop docs) | since 1.0.0 | documented |
| PL-RS-027 | `exit` status truncation: 8 LSB on most Unix (`process::exit(0x0100)` → 0 on Linux, 256 on Windows); `i32`→wait-status exit byte | — | §3.3 | std::process::exit (Platform-specific behavior) | since 1.0.0; per-platform masking | documented |
| PL-RS-028 | `exit` runs `atexit` handlers and ELF `fini` sections; concurrent Rust-`exit` + C-`exit` documented as UB (single runtime lock-mitigated; multiple runtimes unsynchronized); exit-race with other threads' drops → coordinate shutdown | — | §3.3, §6.7 | std::process::exit (Safe interop with C code) | current implementation note; since 1.0.0 | documented |
| PL-RS-029 | Panic strategies: Cargo `panic = "unwind" \| "abort"`; unwind defers to target default; tests/build scripts/proc macros ignore the setting | — | §3.6 | Cargo Book: profiles.panics | Cargo reference (retrieved 2026-10) | documented |
| PL-RS-030 | `panic="abort"` consequences: no destructors, no unwinding, `catch_unwind` blind, but **panic hook still runs**; contrast `process::abort` (no hook) | — | §3.5, §3.6 | std::process::abort; Cargo Book | current stable | documented |
| PL-RS-031 | Default panic hook + pipeline order: registered at startup, prints to stderr, backtrace if requested; hook runs before the panic runtime (both runtimes) | — | §3.7 | std::panic::set_hook | since 1.10.0 wording | documented |
| PL-RS-032 | Main-thread panic → process exit code **101**; docs say only "non-zero"; `rt.rs` anchor; payload-drop wrapped in `catch_unwind` | — | §3.10 | std source `rt.rs`; std::thread module | implementation anchor (master, 2026-10) | documented |
| PL-RS-033 | Panic in `extern "C"` fn: caught at boundary, process aborted; destructors up to boundary may or may not run | — | §3.9 | std::panic::catch_unwind; Reference: Destructors | stable Rust | documented |
| PL-RS-034 | Cleanup-per-path matrix: normal return / `Err` / unwind / `panic=abort` / `exit` / `abort` / FFI boundary × (Drop, hook, atexit, flush, status) | — | §1.6, §3.10 | std::process; std::panic; Reference: Destructors | current stable | documented |
| PL-RS-035 | Runtime startup/shutdown: fd 0/1/2 sanitization; SIGPIPE set to ignore; stack-overflow guard init; single-threaded `libc::exit` guard | — | §3.1, §4.5 | std source `rt.rs`; `sys/pal/unix/mod.rs` | Unix runtime (source anchor, master 2026-10) | documented |
| PL-RS-036 | No std signal-registration/masking API — verified absence; consequences (default dispositions; graceful shutdown not expressible in std) | — | §4.1 | std::process module doc (scope statement); std doc index | std 1.99.0 | documented |
| PL-RS-037 | libc-crate FFI pattern for signal registration: `unsafe` block, `extern "C" fn` handler, async-signal-safety obligations, atomic shared state | — | §4.3 | libc crate (third-party); POSIX sigaction rules via book interfaces chapters | third-party crate; [platform Unix] | documented |
| PL-RS-038 | signal-hook crate: registry/iterator/pipe signal handling (named, linked; internals not inventoried) | — | §4.2 | docs.rs/signal-hook (0.4.5) | third-party | source-limited |
| PL-RS-039 | ctrlc crate: minimal Ctrl-C callback (named, linked; internals not inventoried) | — | §4.2 | docs.rs/ctrlc (3.5.2) | third-party | source-limited |
| PL-RS-040 | tokio::signal / tokio::process: async signal streams + `kill_on_drop` (named, linked; not deeply inventoried) | — | §4.2, §5.4 | docs.rs/tokio (1.53.2) | third-party | source-limited |
| PL-RS-041 | `Command::new` defaults: no args, inherit env/cwd, inherit stdio for spawn/status, pipes for output; PATH search when relative; "ls -l" literal caveat | `pub fn new<S: AsRef<OsStr>>(program: S) -> Command` | §5.1 | std::process::Command | since 1.0.0 | documented |
| PL-RS-042 | `Command::arg`/`args`: literal argument passing, no shell layer | `pub fn arg<S: AsRef<OsStr>>(&mut self, arg: S) -> &mut Command`; `pub fn args<I, S>(&mut self, args: I) -> &mut Command where I: IntoIterator<Item = S>, S: AsRef<OsStr>` | §5.1 | std::process::Command::arg/args | since 1.0.0 | documented |
| PL-RS-043 | `Command::env`/`envs`/`env_remove`/`env_clear`: explicit mappings override inheritance; removal blocks inheritance | `pub fn env<K, V>(&mut self, key: K, val: V) -> &mut Command where K: AsRef<OsStr>, V: AsRef<OsStr>` (envs since 1.19.0) | §5.1 | std::process::Command::env etc. | 1.0.0 / 1.19.0 | documented |
| PL-RS-044 | `Command::current_dir`: child cwd; relative-program ambiguity documented as platform-specific and unstable | `pub fn current_dir<P: AsRef<Path>>(&mut self, dir: P) -> &mut Command` | §5.1 | std::process::Command::current_dir | since 1.0.0 | documented |
| PL-RS-045 | `Command::stdin/stdout/stderr`: defaults inherit (spawn/status) vs piped (output) | `pub fn stdin<T: Into<Stdio>>(&mut self, cfg: T) -> &mut Command` (stdout/stderr symmetric) | §5.1 | std::process::Command::stdin | since 1.0.0 | documented |
| PL-RS-046 | `Command::spawn`: documented error taxonomy (not found, permission, resources); post-start outcomes via `ExitStatus`, not `Err` | `pub fn spawn(&mut self) -> Result<Child>` | §5.1 | std::process::Command::spawn (§Errors) | since 1.0.0 | documented |
| PL-RS-047 | `Command::status`: spawn + wait, stdio inherited; child failure is `Ok` | `pub fn status(&mut self) -> Result<ExitStatus>` | §5.1 | std::process::Command::status | since 1.0.0 | documented |
| PL-RS-048 | `Command::output`: capture stdout+stderr (piped), stdin closes immediately on child read; `Ok` regardless of child exit/signal | `pub fn output(&mut self) -> Result<Output>` | §5.1 | std::process::Command::output | since 1.0.0 | documented |
| PL-RS-049 | `Command` accessors: `get_program`/`get_args`/`get_envs`/`get_current_dir` | `pub fn get_program(&self) -> &OsStr`; `pub fn get_args(&self) -> CommandArgs<'_>`; `pub fn get_envs(&self) -> CommandEnvs<'_>`; `pub fn get_current_dir(&self) -> Option<&Path>` | §5.1 | std::process::Command (get_*) | since 1.57.0; `get_resolved_envs`/`get_env_clear` nightly | documented |
| PL-RS-050 | Platform deltas for spawn: Unix searches child env `PATH` (execvp fallback `/bin:/usr/bin` if removed); Windows pre-resolution search order; cmd.exe/.bat argument hazards + `raw_arg` | — | §5.1, §5.10 | std::process::Command (Platform-specific behavior); Command::arg (Windows warning) | [platform Unix] / [platform Windows] | documented |
| PL-RS-051 | `Child` struct + stream fields (`Option` per piped stream) + `id` | `pub struct Child { pub stdin: Option<ChildStdin>, pub stdout: Option<ChildStdout>, pub stderr: Option<ChildStderr>, /* private */ }`; `pub fn id(&self) -> u32` | §5.2 | std::process::Child | 1.0.0; id since 1.3.0 | documented |
| PL-RS-052 | `Child::kill`: SIGKILL equivalent on Unix; `Ok(())` if already exited; error-kind mapping not a contract | `pub fn kill(&mut self) -> Result<()>` | §5.2 | std::process::Child::kill | since 1.0.0 | documented |
| PL-RS-053 | `Child::wait`: closes piped stdin before waiting; idempotent after first call | `pub fn wait(&mut self) -> Result<ExitStatus>` | §5.2 | std::process::Child::wait | since 1.0.0 | documented |
| PL-RS-054 | `Child::try_wait`: non-blocking; reaps PID on Unix; does **not** drop stdin (unlike `wait`) | `pub fn try_wait(&mut self) -> Result<Option<ExitStatus>>` | §5.2 | std::process::Child::try_wait | since 1.18.0 | documented |
| PL-RS-055 | `Child::wait_with_output`: consumes child; closes stdin; drains stdout+stderr to EOF concurrently | `pub fn wait_with_output(self) -> Result<Output>` | §5.2 | std::process::Child::wait_with_output | since 1.0.0 | documented |
| PL-RS-056 | `Child` drop: **no `Drop` impl** — no kill, no reap; zombie-exhaustion warning; no std `kill_on_drop` | — | §5.4 | std::process::Child (Warning) | std 1.99.0 docs | documented |
| PL-RS-057 | `ChildStdin`/`ChildStdout`/`ChildStderr`: Read/Write impls; AsFd/AsRawFd/IntoRawFd; `From<OwnedFd>` for ChildStdin (1.74.0) and reverse `From<ChildStdin> for OwnedFd`/`Stdio` | `impl Write for ChildStdin` (1.0.0); `impl From<OwnedFd> for ChildStdin` | §5.8, §6.4 | std::process::ChildStdin | 1.0.0; From\<OwnedFd\> since 1.74.0; [platform Unix] fd traits | documented |
| PL-RS-058 | `ExitStatus::success` / `code`: success = zero status, signal death not success; `code()` `None` on signal death; 8-bit truncation + runtime-invented codes (255/254/127/126) | `pub fn success(&self) -> bool`; `pub fn code(&self) -> Option<i32>` | §5.3 | std::process::ExitStatus | since 1.0.0; Default 1.73.0; `exit_ok` nightly | documented |
| PL-RS-059 | `ExitStatusExt::signal` / `into_raw`: WIFSIGNALED→WTERMSIG mapping; raw wait-status word; shell 128+N conversion is the shell's doing | `fn signal(&self) -> Option<i32>`; `fn into_raw(self) -> i32` | §5.3, §5.6 | std::os::unix::process::ExitStatusExt | signal/into_raw since 1.0.0; Unix only | documented |
| PL-RS-060 | `ExitStatusExt::from_raw`: builds from a **wait status** (not exit status); bit layout not POSIX-specified; per-OS conventions documented; `ExitStatusError::from_raw(0)` panics | `fn from_raw(raw: i32) -> Self` | §5.3 | std::os::unix::process::ExitStatusExt::from_raw | since 1.12.0; Unix only | documented |
| PL-RS-061 | `ExitStatusExt::core_dumped` / `stopped_signal` / `continued`: WCOREDUMP / WSTOPSIG (WUNTRACED) / WIFCONTINUED (WCONTINUED) | `fn core_dumped(&self) -> bool`; `fn stopped_signal(&self) -> Option<i32>`; `fn continued(&self) -> bool` | §5.3 | std::os::unix::process::ExitStatusExt | since 1.58.0; Unix only | documented |
| PL-RS-062 | `Output` struct: status + raw stdout/stderr `Vec<u8>`; `exit_ok` nightly | `pub struct Output { pub status: ExitStatus, pub stdout: Vec<u8>, pub stderr: Vec<u8> }` | §5.3 | std::process::Output | since 1.0.0 | documented |
| PL-RS-063 | `Stdio`: `piped`/`inherit`/`null`; piped-volume deadlock warning; `From` conversions (ChildStdin/Out/Err, File, Stdout/Stderr, OwnedFd, PipeReader/PipeWriter) | `pub fn piped() -> Stdio`; `pub fn inherit() -> Stdio`; `pub fn null() -> Stdio` | §5.5 | std::process::Stdio | since 1.0.0 | documented |
| PL-RS-064 | `CommandExt::uid`/`gid`: setuid/setgid in child; spawn fails on error; implicit `setgroups(0, NULL)` note | `fn uid(&mut self, id: u32) -> &mut Command`; `fn gid(&mut self, id: u32) -> &mut Command` | §5.7 | std::os::unix::process::CommandExt | since 1.0.0; Unix only | documented |
| PL-RS-065 | `CommandExt::pre_exec`: closure after fork/before exec; async-signal-safety constraints; allocating-error caveat (`Error::new`/`Error::other`); `always_abort` before hook; panic-format safety caveat | `unsafe fn pre_exec<F>(&mut self, f: F) -> &mut Command where F: FnMut() -> Result<()> + Send + Sync + 'static` | §5.7 | std::os::unix::process::CommandExt::pre_exec | since 1.34.0; Unix only | documented |
| PL-RS-066 | `CommandExt::exec`: execvp replacing current process; no fork; exit-like destructor semantics; broken-state warning on error | `fn exec(&mut self) -> Error` | §5.7 | std::os::unix::process::CommandExt::exec | since 1.9.0; Unix only | documented |
| PL-RS-067 | `CommandExt::arg0`: argv[0] override | `fn arg0<S>(&mut self, arg: S) -> &mut Command where S: AsRef<OsStr>` | §5.7 | std::os::unix::process::CommandExt::arg0 | since 1.45.0; Unix only | documented |
| PL-RS-068 | `CommandExt::process_group`: setpgid-in-child; signal-delivery scoping rationale (terminal SIGINT/SIGQUIT); PGID 0 = child PID | `fn process_group(&mut self, pgroup: i32) -> &mut Command` | §4.1, §5.7 | std::os::unix::process::CommandExt::process_group | since 1.64.0; Unix only | documented |
| PL-RS-069 | `CommandExt` nightly remainder + deprecated member: `groups` (`setgroups`), `chroot` (`process_chroot`), `setsid` (`process_setsid`); `before_exec` deprecated 1.37.0 | `fn setsid(&mut self, setsid: bool) -> &mut Command` (nightly) | §5.7 | std::os::unix::process::CommandExt | nightly-only on 1.99.0; Unix only | documented |
| PL-RS-070 | No timeout API on `Command`/`Child` — verified absence; standard poll+kill+wait workaround pattern; [third-party] tokio async cancellation | — | §5.9 | std::process::Child (method set); docs.rs tokio | std 1.99.0; pattern all platforms | documented |
| PL-RS-071 | No shell by default: literal argv, structurally no quoting layer; `sh -c` opt-in reintroduces the injection surface | — | §5.10 | std::process::Command::arg/args (no-shell statement) | current stable | documented |
| PL-RS-072 | Zombies/orphans: std never reaps implicitly; reaping = wait/try_wait/wait_with_output; orphan reparenting on parent death | — | §5.4, §5.11 | std::process::Child (Warning) | [Linux]/POSIX substrate | documented |
| PL-RS-073 | Main-thread return terminates the program; other threads' destructors may not run; no implicit join-all | — | §6.1 | std::thread module (threading model) | current stable | documented |
| PL-RS-074 | No thread cancellation API in std; cooperative shutdown via channels/atomics — verified absence | — | §3.11, §6.2 | std::thread module item index | std 1.99.0 | documented |
| PL-RS-075 | fd/handle ownership: `OwnedFd` / `BorrowedFd` lifetime model; `FromRawFd::from_raw_fd` unsafe ownership assertion | `pub trait FromRawFd { unsafe fn from_raw_fd(fd: RawFd) -> Self; }` | §6.4 | std::os::fd (OwnedFd, FromRawFd) | os::fd home since 1.66.0; method since 1.1.0; [platform Unix]-family | documented |
| PL-RS-076 | Pipe-buffer deadlock geometry: drain both streams concurrently (wait_with_output/output); wait() closes stdin; explicit stdin drop signals EOF | — | §5.2, §5.5 | std::process::Stdio (piped warning); Child::wait docs | current stable; pipe capacity [Linux] | documented |

**Counts:** Inventoried **76** · Documented **73** · Remaining **0** ·
Source-limited **3** (PL-RS-038 signal-hook, PL-RS-039 ctrlc, PL-RS-040
tokio — third-party crates: named and linked per Section-G scope, but their
internal signal-delivery machinery is outside the std-docs source of record;
docs.rs metadata pages were reachable and are cited).

IDs are contiguous `PL-RS-001`…`PL-RS-076`, ordered by chapter section.
Verified-absent surfaces (no signal API, no timeout API, no thread
cancellation, no `Child` Drop) are counted as `documented` limitations,
matching the ledger conventions of the part hub [index.md](./index.md).
