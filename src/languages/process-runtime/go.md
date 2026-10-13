# Go: Language Semantics, Standard Library, Process APIs, and Subprocesses

Go is the case study of a **runtime-owned concurrency model with a
process-transparent ABI**: goroutines are scheduled by the Go runtime onto an
unbounded pool of OS threads, the runtime installs its own signal handlers
and multiplexes them to channels, and `os/exec` maps `fork`/`exec`/`wait` onto
a struct (`exec.Cmd`) whose cancellation and pipe plumbing are written in
library code, not the kernel. Every claim below is labeled with its layer:
**[language spec]** (go.dev/ref/spec), **[std lib documented]** (pkg.go.dev
rendered doc comments), **[runtime implementation]** (Go source behavior,
verified but not part of any spec), and **[Linux]** / **[Windows delta]** for
the OS substrate.

**Declared scope** (all sources retrieved **2026-10-13**):

- **Go 1.27.2**, the current stable release per the official download feed
  [go.dev/dl/?mode=json](https://go.dev/dl/?mode=json) (top entry
  `"version": "go1.27.2", "stable": true`). Every signature below was
  verified against the doc comments as rendered on pkg.go.dev, fetched for
  this chapter from the source tree at tag `go1.27.2`
  ([github.com/golang/go](https://github.com/golang/go) — the exact doc text
  that pkg.go.dev renders) and cross-checked on
  [pkg.go.dev/runtime](https://pkg.go.dev/runtime) and
  [pkg.go.dev/syscall](https://pkg.go.dev/syscall) directly. Numeric facts
  that exist only in the implementation are cited to the source file and
  labeled **[runtime implementation]**.
- **Platform**: Linux (linux/amd64) as primary target; POSIX deltas labeled
  where Go's own docs make the distinction; Windows deltas named briefly in
  §4.9 and §5.12 (they are large for signals and command-line quoting).
- Language-level unspecified areas (map iteration order, goroutine
  scheduling, run-time error values) are called out in §1.7 — Go has no
  undefined-behavior catalog; the compiler refuses or the runtime panics.

The exit-status/signal slice of Go — `main`-return vs `os.Exit` vs `log.Fatal`
vs panic exit codes, the `128+N` shell convention, and the signal default
table — already has a dedicated chapter:
[../../linux/process-exit-signal/languages/go.md](../../linux/process-exit-signal/languages/go.md).
That chapter is the status-and-signal *decoder ring*; this chapter is the
full language/runtime documentation project and agrees with it everywhere
they overlap. Sibling Section-G chapters: [./c.md](./c.md) (the OS substrate
Go's runtime abstracts — `fork`/`exec`/`wait`/pipe mechanics live there),
[./rust.md](./rust.md), [./python.md](./python.md) (the other GC runtime in
this part). Part hub: [./index.md](./index.md). Go-specific companions in the
languages part: [../go/concurrency-deep.md](../go/concurrency-deep.md)
(scheduler deep dive — §1.4 and §6.1 lean on it),
[../go/channels.md](../go/channels.md) (channel mechanics behind every
supervision pattern in §5/§6),
[../go/memory-model.md](../go/memory-model.md) (the happens-before edges that
§6.2's `sync` claims cite).

**Reading map**: §1 language semantics → §2 verified API inventory → §3
termination paths (with the per-path cleanup table) → §4 signals → §5
subprocesses → §6 concurrency and resource semantics. The coverage ledger at
the end inventories every row.

---

## 1. Syntax and Semantics

### 1.1 Functions, multiple returns, and the `error` convention

**[language spec]** Functions may return multiple values, and the Go
convention is `(result T, err error)`:

```go
// ParseInt is the canonical (value, error) shape.
func parseInts(ss ...string) ([]int, error) {
    out := make([]int, 0, len(ss))
    for i, s := range ss {
        n, err := strconv.Atoi(s)
        if err != nil {
            return nil, fmt.Errorf("arg %d %q: %w", i, s, err)
        }
        out = append(out, n)
    }
    return out, nil
}
```

**[language spec]** The predeclared `error` type is a plain interface:

```go
type error interface {
    Error() string
}
```

"with the nil value representing no error" (go.dev/ref/spec, *Errors*).

**[std lib documented]** Error *wrapping* is a documented library protocol,
not language syntax: `fmt.Errorf(format string, a ...any) (err error)`
embeds a wrapped error when the format string contains `%w`, and
[errors](https://pkg.go.dev/errors) inspects the tree:

| API | Signature (verbatim, Go 1.27.2) | Notes |
|---|---|---|
| `fmt.Errorf` | `func Errorf(format string, a ...any) (err error)` | `%w` verb wraps one error; `%v` does not |
| `errors.Unwrap` | `func Unwrap(err error) error` | one step down the tree, nil at the end |
| `errors.Is` | `func Is(err, target error) bool` | identity/equality walk, incl. `Is(error) bool` methods |
| `errors.As` | `func As(err error, target any) bool` | first match assigned to `target`; target must be a non-nil pointer to a type implementing error or to an interface |
| `errors.Join` | `func Join(errs ...error) error` | multi-error tree (Go 1.20) |

Expected behavior:

```go
_, err := parseInts("10", "x")
if err != nil && errors.Is(err, strconv.ErrSyntax) {
    fmt.Println("bad number:", err)
    // prints: bad number: arg 1 "x": strconv.Atoi: parsing "x": invalid syntax
}
```

The `%w` chain is what makes `errors.Is`/`As` work across library boundaries;
without `%w` the inner error is only text.

### 1.2 panic and recover — exact mechanics

**[language spec]** A panic unwinds *the goroutine it occurs in*:

> While executing a function F, an explicit call to panic or a run-time panic
> terminates the execution of F. Any functions deferred by F are then
> executed as usual. Next, any deferred functions run by F's caller are run,
> and so on up to any deferred by the top-level function in the executing
> goroutine. At that point, the program is terminated and the error condition
> is reported, including the value of the argument to panic. This termination
> sequence is called panicking. (go.dev/ref/spec, *Handling panics*)

So **panicking never crosses a goroutine boundary**: a panic in goroutine A
unwinds only A. But when it reaches the top of A, **the whole program
terminates** — see §3.6.

**[language spec]** `recover` has three precise rules:

> The return value of recover is nil when the goroutine is not panicking or
> recover was not called directly by a deferred function. Conversely, if a
> goroutine is panicking and recover was called directly by a deferred
> function, the return value of recover is guaranteed not to be nil. To
> ensure this, calling panic with a nil interface value (or an untyped nil)
> causes a run-time panic.

Consequences that surprise people: calling `recover()` inside a nested
deferred function (a deferred function that itself defers) returns nil;
`recover()` called from a non-deferred function returns nil; and `panic(nil)`
is rewritten by the spec so it can still be recovered distinctly.

**Run-time panics** (nil map write, index out of range, division by zero,
nil dereference, close of closed channel, send on closed channel, etc.) are
not a separate mechanism:

> Execution errors such as attempting to index an array out of bounds trigger
> a run-time panic equivalent to a call of the built-in function panic with a
> value of the implementation-defined interface type runtime.Error. … The
> exact error values that represent distinct run-time error conditions are
> unspecified. (go.dev/ref/spec, *Run-time panics*)

```go
func main() {
    m := map[string]int(nil)
    m["k"] = 1 // run-time panic: assignment to entry in nil map
    // Output (exact text unspecified): panic: assignment to entry in nil map
    // [goroutine stack], exit status 2
}
```

**[std lib documented]** An unrecovered panic prints a stack trace and exits
with **code 2** — this is documented in the runtime package docs via
`GOTRACEBACK`: "By default, a failure prints a stack trace for the current
goroutine, eliding functions internal to the run-time system, and then exits
with exit code 2" ([pkg.go.dev/runtime](https://pkg.go.dev/runtime),
`GOTRACEBACK` environment variable section). The stack trace goes to stderr.
`GOTRACEBACK=all|system|crash` widens the dump; `crash` raises `SIGABRT`
instead of exiting (so the shell decodes 134, not 2). On Unix, if the binary
is setuid/setgid-like, the runtime forces `GOTRACEBACK=none` (same source).

### 1.3 defer — LIFO, argument evaluation, named results

**[language spec]** (*Defer statements*):

> Each time a "defer" statement executes, the function value and parameters
> to the call are evaluated as usual and saved anew but the actual function
> is not invoked. Instead, deferred functions are invoked immediately before
> the surrounding function returns, in the reverse order they were deferred.

Three consequences, all spec-level:

1. **LIFO** order (the spec's own example: `for i := 0; i <= 3; i++ { defer
   fmt.Print(i) }` "prints 3 2 1 0 before surrounding function returns").
2. **Arguments are evaluated at defer time** — `defer log.Close(f)` saves `f`
   *now*; `defer f.Close()` evaluates the receiver `f` now but the *call*
   happens later, so a later reassignment of `f` is not observed.
3. **Named result parameters** are mutable by deferred closures:

```go
// f returns 42 — the spec's own example
func f() (result int) {
    defer func() {
        // result is accessed after it was set to 6 by the return statement
        result *= 7
    }()
    return 6
}
```

**[runtime implementation]** Go 1.14 made defer "almost zero overhead"
(open-coded defers; [go.dev/doc/go1.14](https://go.dev/doc/go1.14)), so
`defer` is no longer a hot-path performance concern. `defer` in a loop keeps
each deferral until the *function* returns, not the iteration — the classic
fd-leak bug (§6.3); move the loop body into a helper or close explicitly.

### 1.4 Goroutines

**[language spec]** (*Go statements*): "The function value and parameters are
evaluated as usual in the calling goroutine, but unlike with a regular call,
program execution does not wait for the invoked function to complete.
Instead, the function begins executing independently in a new goroutine.
When the function terminates, its goroutine also terminates. If the function
has any return values, they are discarded when the function completes."

- There is **no goroutine handle or id** in the language or std lib; you
  reach a goroutine only through channels, shared memory, or `context`.
- **[language spec]** main does not join: "When that function invocation
  returns, the program exits. It does not wait for other (non-main)
  goroutines to complete." A goroutine killed at exit gets *no* defers run.
- **[runtime implementation]** Scheduling is cooperative + signal-based
  preemption (§4.8); the number of OS threads running user code is capped by
  `GOMAXPROCS` (§1.7); blocked syscalls do not count against it.
- A goroutine leak (blocked forever on a channel or a full pipe) never kills
  the process — it only burns stacks and fds; §6.6.

### 1.5 Packages, `init()`, visibility

**[language spec]** (*Package initialization*): imported packages are
initialized first; within a package, package-level variables initialize in
dependency order, then `init()` functions run ("each package's `init`
functions run in the order they appear in source"; files are presented in
lexical file-name order "to ensure reproducible initialization behavior").
`main` runs last, on the **main goroutine**.

Visibility is purely lexical: identifiers starting uppercase are exported to
importers; everything else is package-private. There is no per-file or
per-directory access control beyond the package. `init()` is a legitimate
place to call `signal.Notify` early (§4.2), but note the runtime fact that
all init functions run on the startup thread (§4.8).

### 1.6 Scope, lifetime, zero values, escape analysis, GC

**[language spec]** Go has block scope and no explicit lifetime: variables
live as long as reachable. The **zero value** of every type is well-defined
(`0`, `false`, `""`, `nil` for pointers/maps/channels/slices/functions/
interfaces; a struct is zeroed field-wise), so an uninitialized
`exec.Cmd{}` or `sync.WaitGroup{}` is immediately usable — a deliberate
design point the std lib relies on.

**[runtime implementation]** *Escape analysis* decides stack vs heap
allocation; an object whose address escapes (stored in an interface, sent
over a channel, captured by a goroutine) is heap-allocated and later
collected by the GC. The GC is concurrent — "The Go GC, however, is not fully
stop-the-world and does most of its work concurrently with the application"
([go.dev/doc/gc-guide](https://go.dev/doc/gc-guide)) — with brief pauses, and
it provides **no destruction ordering**: finalizers (§6.4) are best-effort.

### 1.7 Unspecified / implementation-defined areas (in scope)

| Area | Status | Source |
|---|---|---|
| Map iteration order | Unspecified: "The iteration order over maps is not specified and is not guaranteed to be the same from one iteration to the next" | [language spec], go.dev/ref/spec |
| Goroutine scheduling (which P/thread runs a goroutine, when it yields) | Implementation-defined; only `GOMAXPROCS` is documented | [runtime documented] pkg.go.dev/runtime |
| Run-time panic error values | "The exact error values that represent distinct run-time error conditions are unspecified" | [language spec] |
| Exit status outside [0,125] | "For portability, the status code should be in the range [0, 125]" — values ≥ 128 collide with signal encodings | [std lib documented] pkg.go.dev/os `Exit` |

`GOMAXPROCS`: "The GOMAXPROCS variable limits the number of operating system
threads that can execute user-level Go code simultaneously. There is no limit
to the number of threads that can be blocked in system calls on behalf of Go
code; those do not count against the GOMAXPROCS limit"
([pkg.go.dev/runtime](https://pkg.go.dev/runtime)). Since **Go 1.25** the
default is container-aware: "On Linux, the runtime considers the CPU
bandwidth limit of the cgroup containing the process… In container runtime
systems like Kubernetes, cgroup CPU bandwidth limits generally correspond to
the 'CPU limit' option", and it is periodically re-updated; both behaviors
turn off if you set `GOMAXPROCS` yourself
([go.dev/doc/go1.25](https://go.dev/doc/go1.25)). This matters for subprocess
CPU accounting — §6.8.

### 1.8 Version deltas affecting in-scope semantics

| Version | Change | In-scope effect |
|---|---|---|
| 1.14 | Async goroutine preemption | Unix programs "receive more signals"; slow syscalls can fail with `EINTR` ([go1.14 notes](https://go.dev/doc/go1.14)); §4.8 |
| 1.16 | `signal.NotifyContext` | Context-based signal cancellation (§4.2) |
| 1.18 | Generics ("Type Parameters Proposal") | e.g. generic supervision helpers in §5/§6 ([go1.18 notes](https://go.dev/doc/go1.18)) |
| 1.19 | `exec.ErrDot` | PATH entries resolving to the current directory error instead of running ([go.dev/blog/path-security]) (§5.1) |
| 1.20 | `Cmd.Cancel`, `Cmd.WaitDelay`, `ErrWaitDelay` | Cancellation overhaul of `os/exec` ([go1.20 notes](https://go.dev/doc/go1.20)); §5.11 |
| 1.21 | `sync.OnceFunc`/`OnceValue`/`OnceValues` | One-shot init helpers (§6.2) |
| 1.22 | Loop variables per-iteration | "Previously, the variables declared by a 'for' loop were created once and updated by each iteration. In Go 1.22, each iteration of the loop creates new variables" ([go1.22 notes](https://go.dev/doc/go1.22)) — closure capture in subprocess callback loops (e.g. one `Cancel` per command) is no longer an aliasing bug when the module's `go` line is ≥ 1.22 |
| 1.25 | Container-aware `GOMAXPROCS`; `sync.WaitGroup.Go` | Default parallelism in cgroups; one-call goroutine spawning (§6.2, §6.8) |

The module's `go` directive (and the toolchain resolution introduced in
1.21) decides which semantics a given build gets — loop-variable semantics
follow the `go` line, not the installed toolchain.

### 1.9 Misconceptions

- **"panic always crashes the program."** False: a `recover` in a deferred
  function of the *panicking goroutine* stops the panic (§1.2). It *is* true
  that no goroutine can recover another goroutine's panic.
- **"`os.Exit` runs my defers."** False, and spec-of-record: "The program
  terminates immediately; deferred functions are not run"
  ([pkg.go.dev/os](https://pkg.go.dev/os) `Exit`). Same for `log.Fatal*`
  (§3.5).
- **"A panic in a goroutine only kills that goroutine."** False: the process
  dies with exit code 2 (§3.6); `main` cannot catch it.
- **"`main` waits for my goroutines."** False (§1.4). Not waiting is the
  documented behavior, not an accident.
- **"Signals are handled by my goroutines."** No — the runtime handles all
  signals on its own terms and *delivers* async ones to channels (§4.1).
- **"`exec.Command("ls | wc")` runs a pipeline."** No shell is involved
  (§5.1); you get a literal program named `ls | wc`.

---

## 2. Standard-Library and Runtime API Inventory

All signatures verbatim from the doc comments rendered at
pkg.go.dev for Go 1.27.2 (retrieved 2026-10-13). "Since" annotations
reproduced only where verified (release notes listed in References).
Concurrency-safety and ownership notes are quoted or condensed from the same
docs.

### 2.1 `os` — process handle, termination, startup

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `os.Exit` | `func Exit(code int)` | "The program terminates immediately; deferred functions are not run." Portability note: code in [0,125]. | pkg.go.dev/os |
| `os.Process` | `type Process struct { Pid int; … }` | Handle to a process. `Pid` field; other methods below. | pkg.go.dev/os |
| `Process.Signal` | `func (p *Process) Signal(sig Signal) error` | "Sending Interrupt on Windows is not implemented." | pkg.go.dev/os |
| `Process.Kill` | `func (p *Process) Kill() error` | "Kill does not wait until the Process has actually exited." SIGKILL underneath. | pkg.go.dev/os |
| `Process.Wait` | `func (p *Process) Wait() (*ProcessState, error)` | Reaps and "releases any resources associated with the Process". Must be a child. | pkg.go.dev/os |
| `Process.Release` | `func (p *Process) Release() error` | "Release only needs to be called if Process.Wait is not." | pkg.go.dev/os |
| `Process.WithHandle` | `func (p *Process) WithHandle(f func(handle uintptr)) error` | pidfd/Windows handle window; "supported on Linux 5.4 or later (pidfd) and Windows". | pkg.go.dev/os |
| `os.ProcessState` | `type ProcessState struct { … }` | From `Wait`. `func (p *ProcessState) Exited() bool`, `Success() bool`, `ExitCode() int` (−1 "if the process hasn't exited or was terminated by a signal"), `Sys() any` (→ `syscall.WaitStatus` on Unix), `SysUsage() any` (→ `*syscall.Rusage`), `String() string`, `Pid() int`, `UserTime() time.Duration`, `SystemTime() time.Duration`. | pkg.go.dev/os |
| `os.StartProcess` | `func StartProcess(name string, argv []string, attr *ProcAttr) (*Process, error)` | Low-level; `os/exec` is the high-level path. `ProcAttr{Dir string; Env []string; Files []*File; Sys *syscall.SysProcAttr}`. | pkg.go.dev/os |
| `os.Interrupt` / `os.Kill` | `Interrupt Signal = syscall.SIGINT` / `Kill Signal = syscall.SIGKILL` | "The only signal values guaranteed to be present in the os package on all systems are os.Interrupt … and os.Kill …" (`Signal` interface: `String() string; Signal()`). | pkg.go.dev/os |

### 2.2 `log` — print-then-exit / print-then-panic

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `log.Fatal*` | `func Fatal(v ...any)`, `func Fatalf(format string, v ...any)`, `func Fatalln(v ...any)` | "equivalent to l.Print() followed by a call to os.Exit(1)" — **defers do not run** (§3.5). | pkg.go.dev/log |
| `log.Panic*` | `func Panic(v ...any)`, `func Panicf(format string, v ...any)`, `func Panicln(v ...any)` | "equivalent to l.Print() followed by a call to panic()" — recoverable, unlike `Fatal`. | pkg.go.dev/log |
| `log.Logger` | `type Logger struct { … }` with methods `(l *Logger) Fatal(v ...any)` etc. | Package-level functions use the default logger (stderr, date+time flags). | pkg.go.dev/log |

### 2.3 `os/signal` — notification model

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `signal.Notify` | `func Notify(c chan<- os.Signal, sig …os.Signal)` | Relays signals to `c`; **must have buffer space** (§4.2). No signals listed = all. Since: package inception. | pkg.go.dev/os/signal |
| `signal.NotifyContext` | `func NotifyContext(parent context.Context, signals …os.Signal) (ctx context.Context, stop context.CancelFunc)` | Since Go 1.16. Context done on signal; `context.Cause` describes which signal. | pkg.go.dev/os/signal |
| `signal.Stop` | `func Stop(c chan<- os.Signal)` | "When Stop returns, it is guaranteed that c will receive no more signals." | pkg.go.dev/os/signal |
| `signal.Reset` | `func Reset(sig …os.Signal)` | Undoes Notify; "If no signals are provided, all signal handlers will be reset." Restores Go's *default* disposition (not necessarily the system's). | pkg.go.dev/os/signal |
| `signal.Ignore` | `func Ignore(sig …os.Signal)` | Makes signals no-ops; `func Ignored(sig os.Signal) bool` reports current state. | pkg.go.dev/os/signal |

### 2.4 `os/exec` — the subprocess surface

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `exec.Command` | `func Command(name string, arg …string) *Cmd` | Sets only `Path` and `Args`. PATH lookup via `LookPath` when `name` has no separator. **Not deprecated** — `CommandContext` is for cancellation, not deprecation. | pkg.go.dev/os/exec |
| `exec.CommandContext` | `func CommandContext(ctx context.Context, name string, arg …string) *Cmd` | Since Go 1.7; since 1.20 implemented via `Cmd.Cancel` (kill on ctx done by default). Panics on nil ctx. | pkg.go.dev/os/exec |
| `exec.Cmd` | `type Cmd struct { Path string; Args []string; Env []string; Dir string; Stdin io.Reader; Stdout io.Writer; Stderr io.Writer; ExtraFiles []*os.File; SysProcAttr *syscall.SysProcAttr; Process *os.Process; ProcessState *os.ProcessState; Err error; Cancel func() error; WaitDelay time.Duration; … }` | "A Cmd cannot be reused after calling its Cmd.Start, Cmd.Run, Cmd.Output, or Cmd.CombinedOutput methods." Unexported plumbing beyond the listed fields. | pkg.go.dev/os/exec |
| `Cmd.Start` | `func (c *Cmd) Start() error` | "After a successful call to Cmd.Start the Cmd.Wait method must be called in order to release associated system resources." | pkg.go.dev/os/exec |
| `Cmd.Wait` | `func (c *Cmd) Wait() error` | Waits for exit **and** for I/O copying goroutines. "Wait must not be called concurrently from multiple goroutines. A custom Cmd.Cancel function should not call Wait." Returns `*ExitError` for non-zero exit. | pkg.go.dev/os/exec |
| `Cmd.Run` | `func (c *Cmd) Run() error` | `Start()` + `Wait()`. | pkg.go.dev/os/exec |
| `Cmd.Output` | `func (c *Cmd) Output() ([]byte, error)` | Captures stdout; if `Stderr == nil`, also captures stderr into `ExitError.Stderr` (prefix+suffix saver). | pkg.go.dev/os/exec |
| `Cmd.CombinedOutput` | `func (c *Cmd) CombinedOutput() ([]byte, error)` | stdout+stderr into one buffer. | pkg.go.dev/os/exec |
| `Cmd.StdinPipe` | `func (c *Cmd) StdinPipe() (io.WriteCloser, error)` | "The pipe will be closed automatically after Cmd.Wait sees the command exit." Caller closes early to signal EOF. | pkg.go.dev/os/exec |
| `Cmd.StdoutPipe` | `func (c *Cmd) StdoutPipe() (io.ReadCloser, error)` | "It is thus incorrect to call Wait before all reads from the pipe have completed. For the same reason, it is incorrect to call Cmd.Run when using StdoutPipe." | pkg.go.dev/os/exec |
| `Cmd.StderrPipe` | `func (c *Cmd) StderrPipe() (io.ReadCloser, error)` | Same contract as `StdoutPipe`. | pkg.go.dev/os/exec |
| `Cmd.Environ` | `func (c *Cmd) Environ() []string` | Best-effort snapshot of the env the command would run with. | pkg.go.dev/os/exec |
| `exec.ExitError` | `type ExitError struct { *os.ProcessState; Stderr []byte }` | `Error()` is `ProcessState.String()` (e.g. `exit status 1`, `signal: killed`). `ExitCode()` via embedded `ProcessState`. | pkg.go.dev/os/exec |
| `exec.LookPath` | `func LookPath(file string) (string, error)` | Error satisfying `errors.Is(err, exec.ErrDot)` for cwd-relative hits (Go 1.19+). | pkg.go.dev/os/exec |
| `exec.ErrWaitDelay` | `var ErrWaitDelay = errors.New("exec: WaitDelay expired before I/O complete")` | Returned by `Wait` when pipes stay open past `WaitDelay` after successful exit. Since Go 1.20. | pkg.go.dev/os/exec |

**Deprecation status of `exec.Command`**: verified at retrieval — the doc
comment carries **no** "Deprecated:" marker; the Go 1.20 note on
`CommandContext` describes it as the cancellation mechanism, and the package
steers users to `Cmd.Cancel`/`WaitDelay` rather than away from `Command`.

### 2.5 `runtime` — goroutine lifecycle, scheduling, finalizers

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `runtime.Goexit` | `func Goexit()` | Runs all defers of the calling goroutine, then terminates *that goroutine only* (§3.7). | pkg.go.dev/runtime |
| `runtime.GOMAXPROCS` | `func GOMAXPROCS(n int) int` | Query/change the documented thread limit; `n<=0` queries. Manual calls disable Go 1.25 auto-updates. | pkg.go.dev/runtime |
| `runtime.LockOSThread` | `func LockOSThread()` / `func UnlockOSThread()` | Pins goroutine to thread; unlocked-on-exit ⇒ "the thread will be terminated". | pkg.go.dev/runtime |
| `runtime.SetFinalizer` | `func SetFinalizer(obj any, finalizer any)` | "There is no guarantee that finalizers will run before a program exits" (§6.4). Docs prefer `runtime.AddCleanup`. | pkg.go.dev/runtime |
| `runtime.NumCPU` | `func NumCPU() int` | Logical CPUs; distinct from `GOMAXPROCS`. | pkg.go.dev/runtime |
| `runtime.GC` | `func GC()` | Runs one GC; no relation to process shutdown. | pkg.go.dev/runtime |

### 2.6 `syscall` — frozen substrate (Linux)

The package docs are explicit about its role: "The primary use of syscall is
inside other packages that provide a more portable interface to the system,
such as 'os', 'time' and 'net'. Use those packages rather than this one if
you can," and: "Most of the functions, types, and constants defined in this
package are also available in the golang.org/x/sys package. That package has
more system call support than this one, and most new code should prefer that
package" ([pkg.go.dev/syscall](https://pkg.go.dev/syscall)). The package is
frozen in practice — Go does not extend it — but it is not deprecated, and
`os`, `os/exec`, and `os/signal` all expose its types.

| API | Canonical signature (linux) | Semantics / notes | Reference |
|---|---|---|---|
| `syscall.Kill` | `func Kill(pid int, sig Signal) (err error)` | Generated wrapper over kill(2). `pid <= 0` means process group (§5.8) — [Linux]. | pkg.go.dev/syscall |
| `syscall.WaitStatus` | `type WaitStatus uint32` with `func (w WaitStatus) Exited() bool`, `ExitStatus() int`, `Signaled() bool`, `Signal() Signal`, `CoreDump() bool`, `Stopped() bool`, `StopSignal() Signal`, `Continued() bool`, `TrapCause() int` | Method set verified for linux. Decodes wait(2) status words. | pkg.go.dev/syscall |
| `syscall.SysProcAttr` | `type SysProcAttr struct { Chroot string; Credential *Credential; Ptrace bool; Setsid bool; Setpgid bool; Setctty bool; Noctty bool; Ctty int; Foreground bool; Pgid int; Pdeathsig Signal; Cloneflags uintptr; … PidFD *int }` | Linux extras; see §5.8–§5.10. | pkg.go.dev/syscall |
| `syscall.Credential` | `type Credential struct { Uid uint32; Gid uint32; Groups []uint32; NoSetGroups bool }` | Drop privileges in the child (§5.9). | pkg.go.dev/syscall |

### 2.7 `sync` — primitives used by process supervision

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `sync.WaitGroup` | `type WaitGroup struct { … }`; `func (wg *WaitGroup) Add(delta int)`, `func (wg *WaitGroup) Done()`, `func (wg *WaitGroup) Wait()`, `func (wg *WaitGroup) Go(f func())` | `Go` added in Go 1.25. Add/Wait ordering rules in §6.2. | pkg.go.dev/sync |
| `sync.Mutex` | `type Mutex struct { … }`; `func (m *Mutex) Lock()`, `func (m *Mutex) Unlock()`, `func (m *Mutex) TryLock() bool` | "the n'th call to Mutex.Unlock 'synchronizes before' the m'th call to Mutex.Lock for any n < m" (memory model). | pkg.go.dev/sync |
| `sync.Once` | `type Once struct { … }`; `func (o *Once) Do(f func())` | "If f panics, Do considers it to have returned; future calls of Do return without calling f." Plus `sync.OnceFunc(f func()) func()` (1.21). | pkg.go.dev/sync |

---

## 3. Process Creation and Termination

### 3.1 Startup: what runs before `main`

**[language spec]** Imported packages initialize (variables in dependency
order, then their `init()` functions), then the main package's variables,
then the main package's `init()` functions, then `main`. **[runtime
implementation]** The runtime boots before any of that: it opens std fds
0/1/2 on `/dev/null` if missing, sets up the signal handlers (§4.1), starts
the GC and scheduler. "All init functions are run on the startup thread.
Calling LockOSThread from an init function will cause the main function to be
invoked on that thread" (pkg.go.dev/runtime `LockOSThread`) — the documented
hook for init-time thread state.

### 3.2 The per-path termination table

The single most exam-relevant artifact in this chapter. All rows verified
against the sources cited in §3.3–§3.8 and §4.

| Termination path | Trigger | Exit status to parent | Defers in *current* goroutine | Defers in *other* goroutines | Buffered writers flushed | Finalizers |
|---|---|---|---|---|---|---|
| `main` returns | normal return | 0 | ✅ run (main is just a function) | ❌ none | ❌ not by runtime | ❌ not guaranteed |
| `os.Exit(n)` | explicit | n | ❌ "deferred functions are not run" | ❌ none | ❌ not by runtime | ❌ not guaranteed |
| `log.Fatal*` | explicit | 1 (always) | ❌ (it *is* `os.Exit(1)`) | ❌ none | ❌ (print to the logger's writer is synchronous; a `bufio` wrapping it is not flushed) | ❌ not guaranteed |
| `panic` → recovered | deferred `recover` in panicking goroutine | — (execution continues) | ✅ unwound defers ran | n/a | n/a | n/a |
| `panic` → unrecovered | any goroutine | **2** + stack trace on stderr | ✅ all defers of the panicking goroutine ran during unwind | ❌ none | ❌ | ❌ not guaranteed |
| `runtime.Goexit` | goroutine-scoped | — (goroutine only) | ✅ all defers run | — | — | — |
| Default signal death (SIGINT/SIGTERM/SIGHUP, not notified) | OS | wait status `WIFSIGNALED`, shell shows `128+N` | ❌ | ❌ | ❌ | ❌ |
| SIGQUIT default (not notified) | OS / `^\` | killed by SIGQUIT, **all-goroutine stack dump** on stderr first | ❌ | ❌ | ❌ | ❌ |

**[runtime implementation]** The runtime makes no attempt to flush `fmt` or
`bufio` state at exit: `os.Exit` calls `runtime_beforeExit(code)` (race
detector / coverage hooks only) and then the `exit_group` syscall. What
"nothing runs at exit" means precisely: no finalizers, no other goroutine's
defers, no channel drains.

### 3.3 `os.Exit` — precisely

**[std lib documented]** Full doc text: "Exit causes the current program to
exit with the given status code. Conventionally, code zero indicates success,
non-zero an error. The program terminates immediately; deferred functions are
not run." Plus the portability note: "For portability, the status code should
be in the range [0, 125]."

```go
func main() {
    defer fmt.Println("cleanup") // NEVER printed
    fmt.Println("work")
    os.Exit(3)
    // stdout: work  (unbuffered fmt directly to fd 1 — already out)
    // exit status 3
}
```

With a buffered writer the loss is worse: `w := bufio.NewWriter(os.Stdout); w.WriteString("hi"); os.Exit(0)` — "hi" is never written, because the buffer
lives in Go memory and nothing flushes it (§6.4).

Exit-status range and truncation: Go passes `code` straight through
`syscall.Exit` → `exit_group` [runtime implementation]. **[Linux]** The
kernel keeps 8 bits in the wait status, so a parent using `waitpid` observes
`code & 0xFF`; 128–255 overlap the signal encoding (shell convention
`128+N`). Encoding details and the `128+N` decoder:
[../../linux/process-exit-signal/languages/go.md](../../linux/process-exit-signal/languages/go.md)
and the C substrate [./c.md](./c.md) §exit-status.

### 3.4 Returning from `main` vs `os.Exit`

**[language spec]** "Program execution begins by initializing the program and
then invoking the function main in package main. When that function
invocation returns, the program exits. It does not wait for other (non-main)
goroutines to complete." The *runtime* performs the exit (status 0) after
`main` returns — functionally `main` returning ≈ `os.Exit(0)` *except* that
`main`'s own defers run on the return path, and nothing else does either way.

`os.Exit` can be called from **any** goroutine — including a supervision
goroutine deciding the process is done — which is why "who calls Exit" is a
design decision in Go servers (usually exactly one place, after `signal`
handling, §4.10).

### 3.5 `log.Fatal*`

**[std lib documented]** `Fatal` is "equivalent to l.Print() followed by a
call to os.Exit(1)" (likewise `Fatalf`/`Fatalln`). Two precise consequences:

- The **exit status is always 1**, regardless of how you might want to map
  errors — you cannot pass a code through `log.Fatal`.
- **Defers do not run** (it is `os.Exit(1)`), so `log.Fatal` inside a
  function that owns a `defer f.Close()` leaks the descriptor and skips
  cleanup. Prefer returning errors up to `main` and exiting there.

`log.Panic*` is the recoverable sibling: print, then `panic()` — defers run
during the unwind, and a `recover` sees the printed value.

### 3.6 Unrecovered panic — including in *any* goroutine

**[std lib documented]** Exit code 2 and the stack trace are documented
behavior of the runtime failure path (`GOTRACEBACK`, pkg.go.dev/runtime, §1.2).
**[language spec]** The panicking sequence stops at the top of *the panicking
goroutine*, and "At that point, the program is terminated":

```go
func main() {
    defer fmt.Println("main defer") // never printed: main is not panicking,
                                    // and non-panicking goroutines' defers
                                    // are discarded when the process exits
    go func() {
        defer fmt.Println("worker defer") // printed: panicking goroutine's
                                          // defers run during the unwind
        panic("boom")
    }()
    time.Sleep(time.Hour) // main never wakes
    // stderr: panic: boom … goroutine 6 [running] …
    // stdout: worker defer
    // exit status 2  (shell $? = 2, NOT 128+N — the runtime exits cleanly)
}
```

### 3.7 `runtime.Goexit` — goroutine-only termination

**[std lib documented]** (verbatim):

> Goexit terminates the goroutine that calls it. No other goroutine is
> affected. Goexit runs all deferred calls before terminating the goroutine.
> Because Goexit is not a panic, any recover calls in those deferred
> functions will return nil.
>
> Calling Goexit from the main goroutine terminates that goroutine without
> func main returning. Since func main has not returned, the program
> continues execution of other goroutines. If all other goroutines exit, the
> program crashes.
>
> It crashes if called from a thread not created by the Go runtime.

The `testing` package is the documented consumer: `t.FailNow` (and helpers
built on it, like `t.Fatal`) must be called from the test goroutine precisely
because they call `runtime.Goexit` — defers in the test function run (that's
how `t.Cleanup`/defers still fire), but the test binary continues.

### 3.8 Current process vs goroutine vs thread vs child

- **Goroutine**: terminable only by itself (`Goexit`), by panicking, or by
  cooperative cancellation (`context`, channels). No external kill exists.
- **OS thread**: the runtime owns threads; there is no API to kill a thread.
  `LockOSThread` *pins* — "If the calling goroutine exits without unlocking
  the thread, the thread will be terminated" — that is the closest thing to
  thread destruction, and it destroys the goroutine's thread only when the
  goroutine exits.
- **Current process**: `os.Exit` (§3.3), `main` return (§3.4), panic (§3.6),
  or a default-action signal (§3.2). No `abort()` equivalent except
  `GOTRACEBACK=crash`-style SIGABRT via runtime failure.
- **Child process**: `Process.Kill`/`Signal` — asynchronous, requires `Wait`
  to reap (§5.6, §5.11). Killing the parent does not kill children (unless
  `Pdeathsig`, §5.10, or process-group kills, §5.8).

---

## 4. Signals and OS Interaction

### 4.1 The runtime model: no async-signal-safety rules for Go code

**[std lib documented]** All signals are received by handlers installed by
the runtime. Synchronous signals (SIGBUS, SIGFPE, SIGSEGV, when caused by
execution) "Go programs will convert a synchronous signal into a run-time
panic" — so a Go nil-dereference is a Go panic (exit 2), not a SIGSEGV death
(os/signal package doc). Asynchronous signals are either acted on by default
(§4.3) or relayed to `Notify` channels. **[runtime implementation]** Delivery
to channels happens on a runtime-spawned goroutine (the signal-recv loop is
started lazily by the first `Notify` — source comment, Issue 21576); the
handler thread forwards signals received on non-Go threads back to C code
(cgo case, §4.7). Consequence: Go code never runs *in* a signal handler, so
POSIX async-signal-safety does not constrain it — but this also means signal
→ goroutine wakeup latency is scheduling, not instant.

### 4.2 `signal.Notify` — buffering and drop semantics

**[std lib documented]** (verbatim, the whole contract):

> Notify causes package signal to relay incoming signals to c. If no signals
> are provided, all incoming signals will be relayed to c. Otherwise, just
> the provided signals will.
>
> Package signal will not block sending to c: the caller must ensure that c
> has sufficient buffer space to keep up with the expected signal rate. For a
> channel used for notification of just one signal value, a buffer of size 1
> is sufficient.

So: **no queueing, no coalescing guarantee** — if the channel is full, the
signal is dropped (the runtime "will not block"). Multiple `Notify` calls
with the same channel expand its signal set; only `Stop` shrinks it.
Multiple channels can each receive independent copies. `Notify` for a
signal *changes its disposition* (§4.4); the only uncatchable signals are
"The signals SIGKILL and SIGSTOP [which] may not be caught by a program, and
therefore cannot be affected by this package."

```go
ch := make(chan os.Signal, 1)            // buffer 1: the documented size for one signal
signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
sig := <-ch
log.Printf("shutting down on %v", sig)   // first signal: graceful path
os.Exit(0)                               // second SIGINT is NOT guaranteed delivered
```

### 4.3 `signal.NotifyContext` (Go 1.16+)

**[std lib documented]** (verbatim):

> NotifyContext returns a copy of the parent context that is marked done
> (its Done channel is closed) when one of the listed signals arrives, when
> the returned stop function is called, or when the parent context's Done
> channel is closed, whichever happens first.
>
> The stop function unregisters the signal behavior, which, like
> signal.Reset, may restore the default behavior for a given signal. …
> If a signal causes the returned context to be canceled, calling
> context.Cause on it will return an error describing the signal.
>
> The stop function releases resources associated with it, so code should
> call stop as soon as the operations running in this Context complete.

It wires a `size-1` channel internally; `ctx` is cancelable by parent,
signal, or `stop()`; `context.Cause(ctx)` yields e.g.
`interrupt signal received`. This is the modern plumbing for §5.11's
`CommandContext`.

### 4.4 What changes after `Notify` — defaults and restoration

**[std lib documented]** Default behavior table (package doc, verbatim):

> By default, a synchronous signal is converted into a run-time panic. A
> SIGHUP, SIGINT, or SIGTERM signal causes the program to exit. A SIGQUIT,
> SIGILL, SIGTRAP, SIGABRT, SIGSTKFLT, SIGEMT, or SIGSYS signal causes the
> program to exit with a stack dump. A SIGTSTP, SIGTTIN, or SIGTTOU signal
> gets the system default behavior (these signals are used by the shell for
> job control). The SIGPROF signal is handled directly by the Go runtime to
> implement runtime.CPUProfile. Other signals will be caught but no action
> will be taken.

"Exit" here means dying *by signal* (shell decodes `128+N`); "exit with a
stack dump" for SIGQUIT prints all-goroutine stacks **and** still terminates
by SIGQUIT — unless you `Notify` it, in which case you own it.

Disposition changes: "Notify disables the default behavior for a given set of
asynchronous signals… Specifically, it applies to the signals SIGHUP, SIGINT,
SIGQUIT, SIGABRT, and SIGTERM. It also applies to the job control signals
SIGTSTP, SIGTTIN, and SIGTTOU… It also applies to some signals that otherwise
cause no action: SIGUSR1, SIGUSR2, SIGPIPE, SIGALRM, SIGCHLD, SIGCONT,
SIGURG, …" So after `Notify(SIGINT)`: SIGINT no longer kills the process at
all. After `Notify(SIGTSTP)`: job-control suspension is suppressed (a
commonly hit surprise in TUI programs).

Restoration semantics: `Reset(sig…)` undoes Notify and "will restore the
system default behavior for the signal, while Ignore will cause the system to
ignore the signal entirely" (package doc). `Stop(c)` detaches channel `c`;
only when *all* channels for a signal are stopped/reset/ignored does the
default return. Special startup cases, verbatim: "If the Go program is
started with either SIGHUP or SIGINT ignored (signal handler set to SIG_IGN),
they will remain ignored" (until you Notify them). And signal-mask handling:
the runtime explicitly unblocks the sync signals, SIGILL, SIGTRAP, SIGSTKFLT,
SIGCHLD, SIGPROF and on Linux signals 32 (SIGCANCEL) and 33 (SIGSETXID);
"Subprocesses started by os/exec will inherit the modified signal mask"
(§5.12).

### 4.5 SIGPIPE — the fd-number special case

**[std lib documented]** (package doc, verbatim, condensed):

> If the program has not called Notify to receive SIGPIPE signals, then the
> behavior depends on the file descriptor number. A write to a broken pipe on
> file descriptors 1 or 2 (standard output or standard error) will cause the
> program to exit with a SIGPIPE signal. A write to a broken pipe on some
> other file descriptor will take no action on the SIGPIPE signal, and the
> write will fail with a [syscall.EPIPE] error.
>
> If the program has called Notify to receive SIGPIPE signals, the file
> descriptor number does not matter. The SIGPIPE signal will be delivered to
> the Notify channel, and the write will fail with a [syscall.EPIPE] error.

Rationale in the doc: "by default, command line programs will behave like
typical Unix command line programs, while other programs will not crash with
SIGPIPE when writing to a closed network connection." Death by SIGPIPE is a
*signaled* death: the parent sees `WIFSIGNALED` (shell `141` = 128+13) —
decode in [../../linux/process-exit-signal/languages/go.md](../../linux/process-exit-signal/languages/go.md).

### 4.6 Sending signals: `syscall.Kill` and friends

**[std lib documented]** `syscall.Kill(pid int, sig Signal) (err error)` is
the raw kill(2) wrapper; negative `pid` targets a process group (**[Linux]**
kill(2) semantics — see [./c.md](./c.md)). The `syscall` package's status
(§2.6) applies: prefer `Process.Signal(syscall.SIGTERM)` for a child you
hold a `*os.Process` for, and `syscall.Kill(-pgid, sig)` for groups (§5.8).
There is no `os`-level `killpg` wrapper; composing `syscall.Kill` with
`SysProcAttr.Setpgid` is the documented-in-source pattern.

### 4.7 cgo interplay

**[std lib documented]** (os/signal package doc, *Go programs that use cgo or
SWIG*, verbatim rules): "If the non-Go code installs any signal handlers, it
must use the SA_ONSTACK flag with sigaction. Failing to do so is likely to
cause the program to crash if the signal is received." C handlers for sync
signals (SIGBUS/SIGFPE/SIGSEGV) should invoke the Go handler if the fault
happened in Go code, or "some Go run-time panics will not occur as expected."
The Go handler on a non-Go thread generally forwards signals to non-Go
handlers; "If the non-Go code should not change the signal mask on any
threads created by the Go runtime." For `-buildmode=c-shared`/`c-archive`,
the runtime keeps existing handlers (turning on SA_ONSTACK) and installs
only sync-signal + SIGPIPE handlers by default. Bottom line: with cgo in the
binary, Go's signal story is a documented cooperation protocol, not a
monopoly.

### 4.8 Runtime interactions: preemption, GC, threads

- **Async preemption uses SIGURG** — **[runtime implementation]** the runtime
  source names it: "sigPreempt is the signal used for non-cooperative
  preemption… We use SIGURG because it meets all of these criteria" (runtime
  source, `const sigPreempt = _SIGURG`). The user-visible, documented part:
  "Goroutines are now asynchronously preemptible" and Unix programs "will
  receive more signals… programs that use packages like syscall or
  golang.org/x/sys/unix will see more slow system calls fail with EINTR
  errors" ([go.dev/doc/go1.14](https://go.dev/doc/go1.14)); it can be
  disabled with `GODEBUG=asyncpreemptoff=1` (runtime docs). Your own SIGURG
  handler in C must therefore tolerate spurious delivery.
- **GC**: "The Go GC … is not fully stop-the-world and does most of its work
  concurrently" (gc-guide); brief STW pauses exist for scheduler operations
  (including `GOMAXPROCS` changes). Signal delivery is not blocked by GC —
  the runtime handler runs on an alternate signal stack on every thread
  (that's why cgo handlers must use SA_ONSTACK, §4.7).
- **LockOSThread + init**: `LockOSThread` called from `init` pins the whole
  `main` to the startup thread (§3.1) — the documented way to guarantee
  process-wide thread-affine state before `main`. Signal handling is
  unaffected: the runtime handler is installed at startup on all threads
  regardless of pinning.

### 4.9 Windows deltas (brief)

**[Windows delta]** "On Windows a ^C (Control-C) or ^BREAK (Control-Break)
normally cause the program to exit. If Notify is called for os.Interrupt, ^C
or ^BREAK will cause os.Interrupt to be sent on the channel, and the program
will not exit. os.Interrupt is the only signal that can be used on Windows."
`Process.Signal(os.Interrupt)` "is not implemented" on Windows; closing the
process handle or Kill are the practical paths (pkg.go.dev/os/signal, /os).

### 4.10 Canonical graceful-shutdown pattern

```go
func main() {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop() // restore default disposition before exiting

    srvDone := serve(ctx) // hypothetical server honoring ctx
    <-ctx.Done()          // first SIGINT/SIGTERM: disposition now owned by us
    log.Print("shutting down")

    // Force path: a second signal re-arms nothing; arm a raw handler to exit hard.
    force := make(chan os.Signal, 1)
    signal.Notify(force, os.Interrupt, syscall.SIGTERM)
    go func() {
        if _, ok := <-force; ok {
            os.Exit(130) // convention: operator insists
        }
    }()

    select {
    case <-srvDone:
    case <-time.After(30 * time.Second):
        os.Exit(124) // forced timeout; defers skipped on purpose
    }
    stop() // restores defaults; later SIGTERM kills us by signal
}
```

Expected behavior: first Ctrl-C cancels `ctx` (drain path runs, exit 0 or
124); second Ctrl-C exits 130 immediately (defers skipped); if the operator
had never armed `force`, the *second* SIGINT would be dropped (channel full,
§4.2) — buffer 1 per signal is the documented minimum.

---

## 5. Subprocess and Child-Process Management

### 5.1 Creation: `exec.Command` / `CommandContext` — no shell, ever

**[std lib documented]** "Command returns the Cmd struct to execute the named
program with the given arguments… If name contains no path separators,
Command uses LookPath to resolve name to a complete path if possible." The
returned `Cmd` has only `Path`/`Args` set — **no shell interpretation**:
pipes, globs, `&&`, quotes are ordinary characters. Injection-safety is
therefore structural; the shell is opt-in and *must* take a fully-controlled
string:

```go
// VULNERABLE — user text becomes shell script:
exec.Command("sh", "-c", "grep -e '"+userPattern+"' data.txt")

// SAFE — user text arrives as a shell *argument* ($1), never as script text:
exec.Command("sh", "-c", "grep -e \"$1\" data.txt", "sh", userPattern)
```

The last form is safe because the user pattern arrives as a positional shell
parameter, not as parsed script text. Even better: drop the shell entirely
(`exec.Command("grep", "-e", userPattern, "data.txt")`). Windows quirk
(documented): processes get one command-line string; "Command combines and
quotes Args into a command line string with an algorithm compatible with
applications using CommandLineToArgvW… Notable exceptions are msiexec.exe and
cmd.exe (and thus, all batch files)" — `SysProcAttr.CmdLine` is the escape
hatch ([Windows delta]).

PATH resolution deltas: since Go 1.19, "this package will not resolve a
program using an implicit or explicit path entry relative to the current
directory… these functions return an error err satisfying
errors.Is(err, ErrDot)" (LookPath doc). `Command` never returns the error by
itself; it stores it in `Cmd.Err`, and `Start` refuses to run — the
documented override is `errors.Is(cmd.Err, exec.ErrDot)`.

### 5.2 `Cmd` field semantics (verified contract highlights)

- `Env`: nil ⇒ inherit parent env; "If Env contains duplicate environment
  keys, only the last value in the slice for each duplicate key is used."
  `Cmd.Environ()` previews the effective env.
- `Dir`: child cwd; on Unix also sets the child's `PWD` (long documented
  discussion of getcwd aliasing in the `Dir` doc).
- `Stdin/Stdout/Stderr`: nil ⇒ `/dev/null`; `*os.File` ⇒ passed directly
  (no copying goroutine); anything else ⇒ **a goroutine copies over an OS
  pipe** and "Wait does not complete until the goroutine reaches EOF or
  encounters an error or a nonzero WaitDelay expires."
- Same-writer rule: "If Stdout and Stderr are the same writer, and have a
  type that can be compared with ==, at most one goroutine at a time will
  call Write" — i.e. interleaving is safe by mutex, not by content.
- `ExtraFiles`: "entry i becomes file descriptor 3+i" — §5.7.
- `Err`: `LookPath` error (e.g. `exec.ErrNotFound`, `exec.ErrDot`), checked
  by `Start`.
- `Process`/`ProcessState`: filled by `Start`/`Wait`.

### 5.3 Start / Wait / Run — the resource contract

**[std lib documented]** `Start`: "After a successful call to Cmd.Start the
Cmd.Wait method must be called in order to release associated system
resources." `Wait` waits for the process **and** all I/O copying goroutines,
then "releases any resources associated with the Cmd." Concurrency rules,
verbatim: "Wait must not be called concurrently from multiple goroutines. A
custom Cmd.Cancel function should not call Wait." A `Cmd` cannot be reused
after Start/Run/Output/CombinedOutput. Skipping `Wait` leaks the process
(slot/fd) and, since Go 1.20, is detectable: `GODEBUG=execwait=2` installs a
finalizer that panics with "exec: Cmd started a Process but leaked without a
call to Wait (set GODEBUG=execwait=2 to capture stacks for debugging)"
**[runtime implementation]** (verified in the exec source; the godebug hook
is for debugging leaks).

### 5.4 Pipes and the deadlock rules

**[std lib documented]** The three pipe methods have asymmetric contracts:

- `StdinPipe() (io.WriteCloser, error)`: "The pipe will be closed
  automatically after Cmd.Wait sees the command exit. A caller need only call
  Close to force the pipe to close sooner." Not closing ⇒ child may wait for
  EOF forever.
- `StdoutPipe() (io.ReadCloser, error)`: "Cmd.Wait will close the pipe after
  seeing the command exit, so most callers need not close the pipe
  themselves. It is thus incorrect to call Wait before all reads from the
  pipe have completed. For the same reason, it is incorrect to call Cmd.Run
  when using StdoutPipe." (Same text for `StderrPipe`.)

The classic deadlock, both directions (**[Linux]** pipe capacity applies):

```go
// DEADLOCK: child fills the 64KiB stdout pipe and blocks; Wait blocks on the
// copying goroutine that can't finish because nobody is reading.
cmd := exec.Command("yes")
if err := cmd.Run(); err != nil { ... } // Run attaches /dev/null; safe.
// Correct shape: drain while waiting.
stdout, _ := cmd.StdoutPipe()
_ = cmd.Start()
r := bufio.NewScanner(stdout)           // read concurrently with Wait below
go func() { for r.Scan() { } }()
_ = cmd.Wait()                           // now returns
```

Or let the library copy for you (`cmd.Stdout = &buf`) and call `Run()` —
then `Wait` (inside `Run`) coordinates draining correctly.

### 5.5 Timeouts and cancellation: `CommandContext`, `Cancel`, `WaitDelay` (Go 1.20)

**[std lib documented]** `CommandContext` "sets the command's Cancel function
to invoke the Kill method on its Process, and leaves its WaitDelay unset."
The two fields, verbatim-contract:

- `Cancel func() error`: "If Cancel is non-nil, the command must have been
  created with CommandContext and Cancel will be called when the command's
  Context is done… If the command exits with a success status after Cancel is
  called, and Cancel does not return an error equivalent to os.ErrProcessDone,
  then Wait and similar methods will return a non-nil error: either an error
  wrapping the one returned by Cancel, or the error from the Context." Setting
  `Cancel = nil` disables the kill — "nothing will happen immediately when the
  command's Context is done, but a nonzero WaitDelay will still take effect."
- `WaitDelay time.Duration`: "it bounds the time spent waiting on two sources
  of unexpected delay in Wait: a child process that fails to exit after the
  associated Context is canceled, and a child process that exits but leaves
  its I/O pipes unclosed… If the child process has failed to exit… it will be
  terminated using os.Process.Kill. Then, if the I/O pipes… are still open,
  those pipes are closed…" and "If pipes are closed due to WaitDelay, no
  Cancel call has occurred, and the command has otherwise exited with a
  successful status, Wait and similar methods will return ErrWaitDelay
  instead of nil." With `WaitDelay == 0` (default), "I/O pipes will be read
  until EOF, which might not occur until orphaned subprocesses of the command
  have also closed their descriptors for the pipes."

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
cmd := exec.CommandContext(ctx, "tar", "-xf", bigTar)
cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr
start := time.Now()
err := cmd.Run()
// Typical outcomes:
//   finishes in 2s      → err == nil
//   ignores SIGKILL? impossible — Kill is SIGKILL; it dies by t+5s+ε
//   → err is *ExitError{signal: killed} (exit by signal), ~5s elapsed
fmt.Println(err, time.Since(start).Round(time.Second))
```

Graceful-then-forced pattern: custom `Cancel` sending SIGTERM, `WaitDelay`
forcing SIGKILL:

```go
cmd := exec.CommandContext(ctx, "nginx", "-s", "quit")
cmd.Cancel = func() error { return cmd.Process.Signal(syscall.SIGTERM) }
cmd.WaitDelay = 10 * time.Second // SIGKILL the straggler and unblock pipe copies
```

### 5.6 `os.Process` / `os.ProcessState` — waiting and status

`Process.Wait` reaps (zombie gone on return) and returns `*ProcessState`.
`ProcessState` decode surface (§2.1): `Exited()`, `Success()`,
`ExitCode()` — "or −1 if the process hasn't exited or was terminated by a
signal" — `Sys()` → `syscall.WaitStatus`, `SysUsage()` → `*syscall.Rusage`
("matches struct rusage as defined in the getrusage(2) manual page"),
`UserTime`/`SystemTime` (self+children on Unix), and `String()` whose exact
forms ("exit status 1", "signal: killed", "stop signal: SIGTTIN",
"continued", " (core dumped)") are verified in the os source
**[runtime implementation]**. `exec.ExitError.Error()` is exactly that
string. Zombies: a child that exits and is never `Wait`ed stays a zombie
**[Linux]**; `exec.Cmd` owners must call `Wait` even after `Kill`
(`Kill` "does not wait until the Process has actually exited"). Orphans
reparent to init/PID 1 **[Linux]** — subprocesses of your subprocess are not
your problem unless they hold your pipes (§5.5).

### 5.7 `ExtraFiles` — fd passing

**[std lib documented]** "ExtraFiles specifies additional open files to be
inherited by the new process. It does not include standard input, standard
output, or standard error. If non-nil, entry i becomes file descriptor 3+i."
And: "ExtraFiles is not supported on Windows." Child side reads them with
`os.NewFile(3, …)` (fd 0/1/2 are std streams; 3+i numbering is the
documented ABI):

```go
r, w, _ := os.Pipe()
defer w.Close()
cmd := exec.Command("./child")
cmd.ExtraFiles = []*os.File{w}        // child sees this as fd 3
_ = cmd.Start()
w.Close()                             // parent drops its copy so child sees EOF
// child: f := os.NewFile(uintptr(3), "pipe"); io.ReadAll(f)
```

### 5.8 Process groups and sessions

**[std lib documented]** (linux `SysProcAttr`, verbatim field docs):
"Setpgid sets the process group ID of the child to Pgid, or, if Pgid == 0, to
the new child's process ID." "Setsid: Create session." "Foreground places the
child process group in the foreground. This implies Setpgid. The Ctty field
must be set to the descriptor of the controlling TTY." (Also `Setctty`:
"Ctty must be a descriptor number in the child process: an index into
ProcAttr.Files.") Signaling a whole tree then uses kill(2)'s group form
**[Linux]**:

```go
cmd := exec.Command("/bin/sh", "-c", "sleep 100 & sleep 101")
cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
_ = cmd.Start()
_ = syscall.Kill(-cmd.Process.Pid, syscall.SIGTERM) // negative pid ⇒ group
_, _ = cmd.Process.Wait()                            // reap after
```

Killing the group also removes the "orphaned grandchildren keep my pipe open"
hang from §5.5.

### 5.9 Dropping credentials

**[std lib documented]** `syscall.Credential{Uid, Gid uint32; Groups
[]uint32; NoSetGroups bool}` passed as `SysProcAttr.Credential` makes the
child setuid/setgid before exec (**[Linux]** implementation; the child runs
as `Uid`/`Gid` — e.g. run a network listener handed over via
`ExtraFiles`/socket activation as an unprivileged user).

### 5.10 `Pdeathsig` — parent-death signal and its thread caveat

**[std lib documented]** (verbatim): "Pdeathsig, if non-zero, is a signal
that the kernel will send to the child process when the creating thread dies.
Note that the signal is sent on thread termination, which may happen before
process termination. There are more details at https://go.dev/issue/27505."
This is the prctl `PR_SET_PDEATHSIG` mechanism **[Linux]** — and the caveat
is structural in Go: the "creating thread" is whatever runtime thread happens
to execute the clone, not the process, and that thread can exit at any time.
Consequence: `Pdeathsig` alone is not a reliable "kill my child when I die"
mechanism; pair it with Setpgid and explicit cleanup, or drive it from a
locked thread (see issue 27505 discussion).

### 5.11 Waiting patterns: goroutine + channel + context

Go has no blocking-with-timeout `waitpid` API; you compose it:

```go
func runWithTimeout(cmd *exec.Cmd, d time.Duration) error {
    if err := cmd.Start(); err != nil {
        return err
    }
    done := make(chan error, 1)
    go func() { done <- cmd.Wait() }() // exactly one Wait, in one goroutine
    select {
    case err := <-done:
        return err
    case <-time.After(d):
        _ = cmd.Process.Kill()         // async: returns before death
        return <-done                  // then reap (required; zombie otherwise)
    }
}
```

Rules encoded above: one `Wait` total (§2.4); `Kill` then *still* `Wait`
(zombie); the channel buffers 1 so the waiting goroutine never leaks. For
multi-child supervision, fan each child into its own goroutine and multiplex
with channels ([../go/channels.md](../go/channels.md)); or use
`CommandContext` + `WaitDelay` and let the library own the goroutines
(§5.5).

### 5.12 How creation actually works; Windows deltas

**[runtime implementation]** There is no `posix_spawn` API in the std lib and
no direct wrapper. `exec.Cmd.Start` → `os.StartProcess` → `syscall.StartProcess`
→ `forkAndExecInChild`, which on Linux performs a raw `clone` with
`CLONE_VM | CLONE_VFORK` (plus `CLONE_PIDFD` when `SysProcAttr.PidFD` is
requested; verified in syscall/exec_linux.go) — i.e. vfork-style sharing of
the parent's address space with a CLOEXEC error-reporting pipe, and
`runtime_BeforeFork/AfterFork` hooks around it. Implementation may change;
the observable contract is the documented one above.

**[Windows delta]** `Command` quoting (CommandLineToArgvW, cmd.exe/batch
exceptions, `SysProcAttr.CmdLine`), `LookPath` extension search via
`PATHEXT`, no `ExtraFiles`, `Interrupt` unimplemented, `Credential`/`Setpgid`
not applicable — the Linux `SysProcAttr` fields simply don't exist for the
windows build (pkg.go.dev/syscall per-GOOS docs).

---

## 6. Concurrency and Resource Semantics

### 6.1 Goroutines, channels, and process supervision

The supervision unit in Go is the goroutine, not the thread: one goroutine
per child (`done <- cmd.Wait()`), one owner goroutine per long-lived stream
drain, and one canceller (`CommandContext`'s internal watch goroutine).
Channels are the join points ([../go/channels.md](../go/channels.md)).
Practical invariants:

- Exactly one `Wait` per `Cmd` (§2.4) — "concurrently" is a documented
  prohibition; fan-in via a buffered channel instead.
- Every goroutine that can block on a child's pipe needs an exit path
  (context + `WaitDelay`, §5.5) or the goroutine leaks even though the child
  died (§6.6).
- Cancellation must reach children explicitly: canceling the parent's
  context kills nothing but your own code unless children were created with
  `CommandContext` on a derived ctx.

### 6.2 `sync` in supervision code — verified contracts

- **WaitGroup** (§2.7): "Note that calls with a positive delta that occur
  when the counter is zero must happen before a Wait. Calls with a negative
  delta, or calls with a positive delta that start when the counter is
  greater than zero, may happen at any time… If a WaitGroup is reused to
  wait for several independent sets of events, new Add calls must happen
  after all previous Wait calls have returned" (Add doc). Since Go 1.25,
  violating this is detected at runtime — the implementation panics with
  "sync: WaitGroup misuse: Add called concurrently with Wait"
  ([runtime implementation], verified in sync source; Go 1.25 release notes
  document the new `WaitGroup.Go` helper that sidesteps Add/Done pairs:
  `wg.Go(task)` adds and spawns in one call). `Done` "synchronizes before"
  the `Wait` it unblocks (memory model;
  [../go/memory-model.md](../go/memory-model.md)).
- **Mutex**: "the n'th call to Mutex.Unlock 'synchronizes before' the m'th
  call to Mutex.Lock for any n < m" — the documented edge you rely on when a
  supervision goroutine publishes child state under a mutex.
- **Once/OnceFunc**: "If f panics, Do considers it to have returned; future
  calls of Do return without calling f" — a panicking one-shot init is *not*
  retried; `sync.OnceFunc(f func()) func()` (1.21) returns a closure with
  the same semantics.

### 6.3 fd ownership — explicit `Close`, finalizers are not cleanup

**[std lib documented]** `os.File.Fd` doc: "If f is garbage collected, a
finalizer may close the descriptor, making it invalid; see
runtime.SetFinalizer for more information on when a finalizer might be run."
So `*os.File` values do have a closing finalizer **[runtime
implementation]** (set in the os package) — but the runtime's own caveat
governs: "The finalizer is scheduled to run at some arbitrary time after the
program can no longer reach the object… There is no guarantee that finalizers
will run before a program exits, so typically they are useful only for
releasing non-memory resources associated with an object during a long-running
program" (runtime.SetFinalizer doc). Translation for subprocess work: rely on
finalizers only as a leak *net* during long runs; for correctness, close
what you open (`StdinPipe`'s writer to signal EOF, `ExtraFiles` parent-side
copies, `Process.Release` when you won't Wait). `defer` in loops leaks fds
until function exit (§1.3).

### 6.4 Buffering vs exit paths

**[std lib documented]** From `runtime.SetFinalizer`'s doc (the clearest
statement in the std lib): "it would be a mistake to depend on a finalizer to
flush an in-memory I/O buffer such as a bufio.Writer, because the buffer
would not be flushed at program exit." Combined with §3.2: `os.Exit`,
`log.Fatal`, panic-death, and signal-death all skip user-space flushes.
`fmt.Print*` to the default stderr/stdout `os.File`s is unbuffered, which is
why examples in §3 appear on the terminal even under `os.Exit`; a `bufio`
layer breaks that. `log`'s default output is unbuffered stderr too.

### 6.5 Deadlocks

Ranked by frequency in real code:

1. **Full child stdout pipe + `Wait`** — §5.4; fix by draining or
   `cmd.Stdout = &buf` or `WaitDelay`.
2. **`StdinPipe` never closed** — child waits for EOF; parent waits for
   child. "if the command being run will not exit until standard input is
   closed, the caller must close the pipe" (StdinPipe doc).
3. **`Wait` before draining `StdoutPipe`** — documented as *incorrect* (§5.4).
4. **Grandchildren holding pipes** — child exits, its child keeps fd open;
   `WaitDelay` or process-group kill (§5.5, §5.8).
5. **Second `signal` channel full** — dropped signals make the force-exit
   path never fire (§4.2); buffer 1 per signal, per the docs.
6. **`Once.Do` recursion** — "if f causes Do to be called, it will deadlock"
   (Once doc).

### 6.6 Races and leaks

- **Races**: mutating `Cmd` fields after `Start` is a data race (the copy
  goroutines and the watch goroutine read them); `Wait` twice concurrently
  is a documented prohibition (§2.4); `Process.Release` concurrently with
  `Wait` — `Release` is only for the not-Waiting path (§2.1). Build with
  `-race`; the memory model edges are in
  [../go/memory-model.md](../go/memory-model.md).
- **Goroutine leaks**: an abandoned `StdoutPipe` leaves the library's copy
  goroutine blocked on read until the pipe closes (which `Wait` would do —
  so *not* calling `Wait` leaks the goroutine *and* fds). An unbuffered
  signal channel doesn't leak goroutines but loses signals.
- **Process leaks**: children without `Wait` become zombies **[Linux]**;
  `GODEBUG=execwait=2` panics on the leaking `Cmd` with the creation stack
  (§5.3). `Process.Release` renders the handle unusable — "Release only needs
  to be called if Process.Wait is not" — and (implementation note) sets
  `Pid` to −1 on non-Windows.
- **fd leaks**: `ExtraFiles` parent-side copies must be closed after `Start`
  (§5.7); `defer`-in-loop (§1.3); `StdinPipe` writer left open (§6.5).

### 6.7 GC interaction

The GC never touches OS resources directly; it only schedules finalizers
(best-effort, timing-unspecified, §6.3). Two documented levers:
`runtime.SetFinalizer` (legacy) and `runtime.AddCleanup` ("New Go code should
consider using AddCleanup instead, which is much less error-prone" —
SetFinalizer doc). For `exec.Cmd` specifically the leak detector uses a
finalizer-like hook under `GODEBUG=execwait=2` (§5.3). At process exit,
finalizers are simply not guaranteed — plan cleanup on defers and exit paths,
not on GC.

### 6.8 `GOMAXPROCS` × subprocess CPU accounting

`GOMAXPROCS` limits *Go* threads executing Go code (§1.7); it says nothing
about your children — a child process gets its own threads and its own
scheduling under the kernel. Since Go 1.25 the default `GOMAXPROCS` tracks
the cgroup CPU bandwidth limit on Linux (§1.7), which is the *same* control
that governs the CPU your children burn if they share your cgroup: the
runtime will read the limit for itself, but **the budget is shared** — a
multi-core cgroup limit of 2 means parent goroutines + children together
cannot exceed 2 CPUs' worth. Setting `GOMAXPROCS` manually (env or call)
disables the automatic updates and only affects Go threads, never children
(go1.25 release notes; runtime docs). For strict accounting, put children in
their own cgroup via `SysProcAttr.CgroupFD`/`UseCgroupFD` (linux
`SysProcAttr`, §2.6).

---

## Related Topics

- Exit-status decoding, `128+N`, signal tables, shell conventions:
  [../../linux/process-exit-signal/languages/go.md](../../linux/process-exit-signal/languages/go.md)
- OS substrate (`fork`/`exec`/`wait`/pipe mechanics, SIGPIPE, zombies):
  [./c.md](./c.md)
- Part hub and sibling language chapters: [./index.md](./index.md)
- Scheduler deep dive: [../go/concurrency-deep.md](../go/concurrency-deep.md)
- Channel mechanics behind every pattern in §5/§6:
  [../go/channels.md](../go/channels.md)
- Happens-before edges cited by §6.2:
  [../go/memory-model.md](../go/memory-model.md)

## Coverage ledger

The machine-readable ledger for this chapter is
[./ledger-go.md](./ledger-go.md): **80 rows** (`PL-GO-001`…`PL-GO-080`),
ordered by section — §1 → 001–011, §2 → 012–048, §3 → 049–055, §4 → 056–062,
§5 → 063–074, §6 → 075–080.

**Rollup: Inventoried: 80 / Documented: 80 / Remaining: 0 / Source-limited: 0**
(all cited sources were reachable at retrieval, 2026-10-13).

## References

All retrieved **2026-10-13**. pkg.go.dev pages render the doc comments of
go1.27.2; source files were fetched from the same tag for verification.

1. **Version/scope**: go.dev/dl/?mode=json — `go1.27.2` stable.
2. **Language specification**: go.dev/ref/spec — *Go statements*, *Defer
   statements*, *Handling panics*, *Run-time panics*, *Errors*, *Package
   initialization*, *Program execution*.
3. **os**: pkg.go.dev/os (`Exit`, `Process`, `ProcessState`, `StartProcess`,
   `ProcAttr`, `Signal`, `Interrupt`, `Kill`); source:
   src/os/proc.go, src/os/exec.go, src/os/exec_posix.go, src/os/file.go
   (github.com/golang/go @ go1.27.2).
4. **os/exec**: pkg.go.dev/os/exec (`Command`, `CommandContext`, `Cmd` +
   `Cancel`/`WaitDelay`/`ExtraFiles`, `Start`/`Wait`/`Run`/`Output`/
   `CombinedOutput`, `StdinPipe`/`StdoutPipe`/`StderrPipe`, `ExitError`,
   `LookPath`/`ErrDot`, `ErrWaitDelay`, `Environ`); source:
   src/os/exec/exec.go, src/os/exec/lookpath.go.
5. **os/signal**: pkg.go.dev/os/signal (package doc: default behavior table,
   SIGPIPE, cgo/SWIG, Windows; `Notify`, `NotifyContext`, `Stop`, `Reset`,
   `Ignore`, `Ignored`); source: src/os/signal/doc.go, src/os/signal/signal.go.
6. **log**: pkg.go.dev/log (`Fatal*`, `Panic*`, `Logger`); source:
   src/log/log.go.
7. **runtime**: pkg.go.dev/runtime (`Goexit`, `GOMAXPROCS` variable +
   `GOMAXPROCS`, `LockOSThread`, `SetFinalizer`, `GOTRACEBACK`,
   `asyncpreemptoff`); source: src/runtime/panic.go, src/runtime/extern.go,
   src/runtime/mfinal.go, src/runtime/signal_unix.go (sigPreempt = SIGURG).
8. **sync**: pkg.go.dev/sync (`WaitGroup` incl. `Go`, `Mutex`, `Once`,
   `OnceFunc`); source: src/sync/waitgroup.go, src/sync/mutex.go,
   src/sync/once.go, src/sync/oncefunc.go.
9. **syscall**: pkg.go.dev/syscall (linux: `Kill`, `WaitStatus` methods,
   `SysProcAttr`, `Credential`); source: src/syscall/syscall_linux.go,
   src/syscall/exec_linux.go (`CLONE_VM|CLONE_VFORK`, `Pdeathsig`).
10. **errors / fmt**: pkg.go.dev/errors (`Is`, `As`, `Unwrap`, `Join`),
    pkg.go.dev/fmt (`Errorf`, `%w`); source: src/errors/wrap.go,
    src/fmt/errors.go.
11. **Release notes**: go.dev/doc/go1.14 (async preemption, EINTR), go1.16
    (NotifyContext), go1.18 (generics), go1.20 (Cmd.Cancel/WaitDelay),
    go1.21 (OnceFunc), go1.22 (per-iteration loop variables), go1.25
    (container-aware GOMAXPROCS, WaitGroup.Go).
12. **GC guide**: go.dev/doc/gc-guide (concurrent, non-fully-STW).
13. **Path security**: go.dev/blog/path-security (ErrDot background).
