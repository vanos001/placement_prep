# Go: Process Termination, Exit Status, and Signals

Go programs run on a runtime that owns threads, scheduling, and signal
delivery, so "how does my program terminate" has more answers than in C:
normal return from `main` (deferred calls run), `os.Exit` (deferred calls do
**not** run), `log.Fatal*` (exit 1), unrecovered `panic` (exit 2 with a stack
dump), `runtime.Goexit` (goroutine-scoped), and OS signals with a
channel-based handler model. Subprocess management lives in `os/exec`, whose
`Cmd`/`Process`/`ProcessState` types map directly onto `fork`/`exec`/`wait`
plus `SIGKILL`-based cancellation. This chapter documents each path with
verified signatures and quotes from the official references: the **Go
language specification** (go.dev/ref/spec), **pkg.go.dev** standard-library
documentation (retrieved 2026-10; pages rendered for linux/amd64, site
reported module version go1.27.2; per-API "added in goN.NN" annotations
reproduced where stated), and the **Go 1.20 release notes** for `Cmd.Cancel`/
`WaitDelay`. The OS substrate is covered in [c.md](./c.md) — this chapter
names the deltas and the runtime abstraction.

---

## 1. Syntax and Semantics

### 1.1 Returning from `main` vs. `os.Exit`

```go
package main

func main() {
    defer println("defer runs")   // runs if main returns
    // ... return  → exit status 0
}
```

Per the Go spec's *Defer statements*: "deferred functions are invoked
immediately before the surrounding function returns, in the reverse order
they were deferred" (go.dev/ref/spec, Defer statements). When the surrounding
function is `main`, the process then exits with status 0.

**`os.Exit`** (pkg.go.dev/os):

```go
func Exit(code int)
```

> "Exit causes the current program to exit with the given status code.
> Conventionally, code zero indicates success, non-zero an error. **The
> program terminates immediately; deferred functions are not run.** For
> portability, the status code should be in the range [0, 125]." — pkg.go.dev/os#Exit

The `[0, 125]` portability note is a documented recent addition to the docs
reflecting the shell's 126/127 reservations
([../exit-status/conventions.md](../exit-status/conventions.md)); the kernel
still truncates to the low 8 bits ([c.md](./c.md) §3.3).

The decision rule: returning from `main` runs defers; `os.Exit` is a
hard stop. Buffered `bufio.Writer`/`log` output is flushed only if the
program does it explicitly (or via defers) *before* calling `os.Exit` — the
classic "last log lines missing" bug.

### 1.2 `log.Fatal*` and `panic`

- **`log.Fatal(v ...any)` / `Fatalf` / `Fatalln`**: "The Fatal functions call
  `os.Exit(1)` after writing the log message" (pkg.go.dev/log). Deferred
  functions do **not** run.
- **`panic`**: per the spec (*Handling panics*): "While executing a function
  F, an explicit call to panic or a run-time panic terminates the execution of
  F. Any functions deferred by F are then executed as usual. Next, any
  deferred functions run by F's caller are run, and so on up to any deferred
  by the top-level function in the executing goroutine. At that point, the
  program is terminated and the error condition is reported, including the
  value of the argument to panic." Defers **run** on the panicking goroutine,
  then the process dies.
- **Exit code on unrecovered panic**: the runtime docs state that a failure
  "prints a stack trace for the current goroutine, eliding functions internal
  to the run-time system, and **then exits with exit code 2**" (pkg.go.dev/
  runtime, GOTRACEBACK section). `GOTRACEBACK=none` omits the stack traces.
- **`recover`** works only inside deferred functions of the panicking
  goroutine (spec, Handling panics); recovering stops the panic and the
  process survives.

**Which defers run, per path**:

| Termination path | Deferred calls on current goroutine | Deferred calls on other goroutines | Exit status |
|---|---|---|---|
| return from `main` | yes | no (process exits) | 0 (or reported value) |
| `os.Exit(code)` | **no** | no | `code` (8-bit) |
| `log.Fatal*` | **no** | no | 1 |
| unrecovered `panic` | yes (unwind current goroutine) | no | **2** + stack dump |
| `runtime.Goexit()` | yes (current goroutine only) | unaffected | — (see below) |
| `os.Exit` inside a deferred call | nothing further runs | no | that code |

### 1.3 `runtime.Goexit` and goroutine exits

```go
func Goexit()
```

> "Goexit terminates the goroutine that calls it. No other goroutine is
> affected. Goexit runs all deferred calls before terminating the goroutine.
> Because Goexit is not a panic, any recover calls in those deferred functions
> will return nil. Calling Goexit from the main goroutine terminates that
> goroutine without func main returning. Since func main has not returned, the
> program continues execution of other goroutines. If all other goroutines
> exit, the program crashes. It crashes if called from a thread not created by
> the Go runtime." — pkg.go.dev/runtime#Goexit

`runtime.Goexit` is what a `t.Fatal`-style test failure and some libraries use
to unwind a single goroutine without panicking. Note the asymmetry with
`os.Exit`: Goexit is goroutine-scoped and runs defers; Exit is process-scoped
and runs none.

### 1.4 Exit status representation

- `os.Exit(code)` → the kernel keeps `code & 0xFF`; `os.ProcessState.ExitCode()`
  returns it on the parent side ([c.md](./c.md) §3.3 for the encoding).
- Panic death is *not* an exit code — the runtime prints the trace and calls
  the OS exit with 2; a parent sees a normal exit with status 2 (no signal).
- Signal death: `ExitCode()` returns -1 and `Exited()` returns false; the
  signal is recovered from `ProcessState.Sys().(syscall.WaitStatus)` (§5.5).

### 1.5 Undefined/implementation-defined corners

Go has no UB, but has documented runtime behaviors that differ from the OS
default table (see §4.4), plus these practical caveats:

- `os.Exit` called from multiple goroutines concurrently: the first call wins;
  the process dies immediately — other goroutines' writes in flight may be
  partially flushed or lost (no guarantee is documented).
- A `panic` inside a deferred call during panic unwinding replaces the
  in-flight panic (spec, Handling panics) — the process still exits 2.
- `os.Exit` does not run `runtime.SetFinalizer` functions; finalizers are a
  GC-side mechanism with no ordering guarantee relative to exit.

### 1.6 Common misconceptions

- *"Defers always run."* Not on `os.Exit`/`log.Fatal` — only on return/panic/
  Goexit.
- *"Panic exits with status 1."* It exits with **2** (runtime docs).
- *"`recover` anywhere can stop a panic."* Only directly in a deferred
  function of the panicking goroutine.
- *"A goroutine panic kills the process."* Only when unrecovered; a panicking
  goroutine unwinds and the panic then terminates the whole program — there
  is no per-goroutine containment except `recover` in that goroutine's defers.

---

## 2. Standard-Library and Runtime API Inventory

Signatures verified against pkg.go.dev (retrieved 2026-10, linux/amd64
rendering). "Added" versions are the site's annotations.

### 2.1 Process termination — `os`, `log`, `runtime`

| API | Signature | Added | Semantics |
|---|---|---|---|
| `os.Exit` | `func Exit(code int)` | — | immediate termination; defers not run; [0,125] portability note |
| `os.Getpid` | `func Getpid() int` | — | current PID (for kill-by-parent patterns) |
| `log.Fatal/Fatalf/Fatalln` | `func Fatal(v ...any)` etc. | — | write message, then `os.Exit(1)` |
| `runtime.Goexit` | `func Goexit()` | — | goroutine-scoped exit; defers run; recover yields nil |
| `panic` / `recover` builtins | `func panic(interface{})` / `func recover() interface{}` (spec) | — | unwinding + defer execution; unrecovered → exit 2 |
| `runtime.GOMAXPROCS` | `func GOMAXPROCS(n int) int` | — | runtime thread budget (§6.1) |

### 2.2 Signals — `os/signal` and `os`

```go
func Notify(c chan<- os.Signal, sig ...os.Signal)          // added go1.0
func Stop(c chan<- os.Signal)                              // added go1.1
func Reset(sig ...os.Signal)                               // added go1.5
func Ignore(sig ...os.Signal)                              // added go1.5
func Ignored(sig os.Signal) bool                           // added go1.5
func NotifyContext(parent context.Context, signals ...os.Signal) (ctx context.Context, stop context.CancelFunc) // added go1.16
```

> "Notify causes package signal to relay incoming signals to c. If no signals
> are provided, all incoming signals will be relayed to c. Otherwise, just the
> provided signals will. **Package signal will not block sending to c: the
> caller must ensure that c has sufficient buffer space to keep up with the
> expected signal rate. For a channel used for notification of just one
> signal value, a buffer of size 1 is sufficient.**" — pkg.go.dev/os/signal#Notify

- `Stop(c)`: "causes package signal to stop relaying incoming signals to c…
  When Stop returns, it is guaranteed that c will receive no more signals."
- `Reset(sig…)`: undoes prior `Notify` for those signals (restores default).
- `Ignore(sig…)`: marks signals to be ignored ("If they are received by the
  program, nothing will happen").
- `NotifyContext(parent, signals…)`: "returns a copy of the parent context
  that is marked done (its Done channel is closed) when one of the listed
  signals arrives, when the returned stop function is called, or when the
  parent context's Done channel is closed, whichever happens first."
- `os.Signal` is the interface type; concrete values come from `syscall`
  (`syscall.SIGTERM`, `syscall.SIGKILL`, …) and `os.Interrupt`/`os.Kill`.

### 2.3 Subprocesses — `os/exec`

```go
func LookPath(file string) (string, error)                       // PATH search
func Command(name string, arg ...string) *Cmd
func CommandContext(ctx context.Context, name string, arg ...string) *Cmd // added go1.7

type Cmd struct {
    Stdin  io.Reader        // wired to child stdin when non-nil
    Stdout, Stderr io.Writer
    ExtraFiles []*os.File   // fd 3+i in the child (not on Windows)
    SysProcAttr *syscall.SysProcAttr
    Process     *os.Process        // after Start
    ProcessState *os.ProcessState  // after Wait
    Err  error                     // LookPath error, if any
    Cancel func() error            // added go1.20
    WaitDelay time.Duration         // added go1.20
}

func (c *Cmd) Start() error
func (c *Cmd) Run() error                     // Start + Wait
func (c *Cmd) Wait() error
func (c *Cmd) Output() ([]byte, error)
func (c *Cmd) CombinedOutput() ([]byte, error)
func (c *Cmd) StdinPipe() (io.WriteCloser, error)
func (c *Cmd) StdoutPipe() (io.ReadCloser, error)
func (c *Cmd) StderrPipe() (io.ReadCloser, error)
func (c *Cmd) Environ() []string              // added go1.19
func (c *Cmd) String() string                 // added go1.13
```

- `Run`: "Run starts the specified command and waits for it to complete. The
  returned error is nil if the command runs, has no problems copying stdin,
  stdout, and stderr, and exits with a zero exit status."
- `Wait`: "Wait waits for the command to exit and waits for any copying to
  stdin or copying from stdout or stderr to complete… If any of c.Stdin,
  c.Stdout or c.Stderr are not an *os.File, Wait also waits for the respective
  I/O loop copying to or from the process to complete. **Wait must not be
  called concurrently from multiple goroutines.**… Wait releases any
  resources associated with the Cmd." On non-zero exit, `Wait` returns an
  `*ExitError`.
- `ExitError` embeds `*os.ProcessState` (and carries a `Stderr` byte slice
  when populated by `Output`).
- Errors: `ErrNotFound` ("executable file not found in $PATH"), `ErrWaitDelay`
  ("exec: WaitDelay expired before I/O complete"), and `*exec.Error` from
  `LookPath` classification failures.

### 2.4 `os.Process` and `os.ProcessState`

```go
func (p *Process) Signal(sig Signal) error
func (p *Process) Kill() error
func (p *Process) Wait() (*ProcessState, error)
func (p *Process) Release() error

func (p *ProcessState) ExitCode() int
func (p *ProcessState) Exited() bool
func (p *ProcessState) Success() bool
func (p *ProcessState) Pid() int
func (p *ProcessState) Sys() any        // syscall.WaitStatus on Unix
func (p *ProcessState) SysUsage() any   // *syscall.Rusage on Unix
```

> `Kill`: "Kill causes the Process to exit immediately. Kill does not wait
> until the Process has actually exited. **This only kills the Process
> itself, not any other processes it may have started.**" — pkg.go.dev/os#Process.Kill

`Signal` sends any signal ("Sending Interrupt on Windows is not implemented");
`Release` frees OS resources without waiting (the process is then not waitable
through this handle — see §5.5 for zombie discipline).

### 2.5 `syscall.WaitStatus` and `syscall.SysProcAttr` (Linux)

```go
// syscall.WaitStatus methods (linux/amd64, pkg.go.dev/syscall):
func (w WaitStatus) Exited() bool          // WIFEXITED
func (w WaitStatus) ExitStatus() int       // WEXITSTATUS
func (w WaitStatus) Signaled() bool        // WIFSIGNALED
func (w WaitStatus) Signal() Signal        // terminating signal
func (w WaitStatus) CoreDump() bool        // WCOREDUMP
func (w WaitStatus) Stopped() bool         // WIFSTOPPED
func (w WaitStatus) StopSignal() Signal    // WSTOPSIG
func (w WaitStatus) Continued() bool       // WIFCONTINUED
func (w WaitStatus) TrapCause() int
```

`SysProcAttr` (fields verified on the linux/amd64 page; most relevant here):

```go
type SysProcAttr struct {
    Chroot     string
    Credential *Credential
    Ptrace     bool
    Setsid     bool   // create session
    Setpgid    bool   // "Setpgid sets the process group ID of the child
                      //  to Pgid, or, if Pgid == 0, to the new child's
                      //  process ID."
    Pgid       int
    Pdeathsig  Signal // "a signal that the kernel will send to the child
                      //  process when the creating thread dies… There are
                      //  more details at https://go.dev/issue/27505."
    Cloneflags uintptr
    // …
    Foreground bool
    Ctty       int
}
```

`Pdeathsig` deserves its caution: the kernel delivers it when the *creating
thread* dies, which may precede process death — Go's M:N scheduling means the
"creating thread" can exit independently of the parent goroutine and process
(documented pointer to golang.org/issue/27505).

---

## 3. Process Lifecycle and Termination

### 3.1 Startup and runtime

The Go runtime starts, spins up its scheduler and system goroutines (GC,
scavenger, signal-forwarding machinery), then calls `main`. `main` runs on
the *main goroutine*; when it returns, the process exits with status 0 after
running `main`'s defers. There is no "atexit" API; cleanup is expressed as
deferred calls or explicit shutdown functions.

### 3.2 Normal vs. explicit vs. abnormal termination

- **Normal**: `main` returns (defers run, status 0); or `main` returns after a
  recovered panic.
- **Explicit**: `os.Exit(code)` — immediate, no defers; `log.Fatal*` = message
  + `os.Exit(1)`.
- **Abnormal**: unrecovered panic (defers on the panicking goroutine, then
  exit 2 + stack dump), runtime fatal errors (also exit 2), or OS signal
  death (no exit code; §4).
- Return-from-entry vs. explicit termination: the only difference visible
  outside the process is the status value; inside, it is exactly the defer
  table in §1.2.

### 3.3 Terminating a process vs. a goroutine vs. a child

- **Process**: `os.Exit`, fatal panic, or last-goroutine death via `Goexit`
  chain ("If all other goroutines exit, the program crashes" — runtime docs).
- **Goroutine**: function returns; `runtime.Goexit()` (defers run);
  unrecovered panic (defers run, then process dies); there is no
  `goroutine.Kill` — cancellation is cooperative via channels/context.
- **Child**: `Process.Signal`/`Kill`; reaped by `Process.Wait` or
  `exec.Cmd.Wait`. `Kill` is SIGKILL on Unix; it does not wait and does not
  touch the child's own children (Process.Kill docs, §2.4) — process-group
  kill via `Setpgid`/`syscall.Kill(-pgid, …)` is the remedy (§5.4).

### 3.4 Exit-status propagation to parents

A Go process's status reaches its parent through the standard wait channel:
normal exit → `WEXITSTATUS`; signal death → `WIFSIGNALED` + `WTERMSIG`
(coding identical to [c.md](./c.md) §3.3). Go's own children report through
`os.ProcessState`: `ExitCode()` returns -1 when signaled (`Exited()` false),
and `Sys().(syscall.WaitStatus)` exposes `Signaled()`/`Signal()`/`CoreDump()`
(§2.5). Shells observing a Go process killed by SIGTERM report `143` — the
shell's `128+15` convention, not a Go construct
([../exit-status/conventions.md](../exit-status/conventions.md)).

---

## 4. Signals and OS Interaction

### 4.1 The runtime abstraction: no async-signal-safety rules for Go code

The documented model (pkg.go.dev/os/signal): the package "relay[s] incoming
signals to c" — your code receives signals as values on a channel and handles
them as *ordinary goroutine code*, not as a low-level handler. All the C
async-signal-safety restrictions ([c.md](./c.md) §4.3,
[../interfaces/async-signal-safety.md](../interfaces/async-signal-safety.md))
do not apply to the receiving code: it allocates, channels, locks — because
it runs on a normal goroutine scheduled by the runtime after the runtime's
internal signal machinery has done its work. The mechanics of that internal
machinery are runtime implementation, not a documented API; the documented
contract is: Notify registers, signals arrive on the channel, non-blocking
send, buffer-size-1 suffices for single-signal channels.

### 4.2 Registration and delivery rules

- `Notify(c, sigs…)` disables the *default behavior* for those signals while
  registered ("Notify disables the default behavior for a given set of
  signals" — os/signal docs, *Changing the behavior* section).
- Multiple channels can register the same signal; each receives a copy.
  `Stop` guarantees no further sends after return; `Reset` restores defaults.
- Delivery is process-scoped: any goroutine reading the channel observes it.
  There is no per-goroutine signal API.
- **Cannot be caught**: "The signals SIGKILL and SIGSTOP may not be caught by
  a program, and therefore cannot be affected by this package" (os/signal
  docs). `SIGTRAP` likewise has runtime semantics (see §4.4 default table) —
  it is listed among signals whose default action produces a stack dump and
  exit; do not build on catching it.

### 4.3 Default behavior table (verified, os/signal docs)

| Signal class | Default Go behavior |
|---|---|
| Synchronous (`SIGBUS`, `SIGFPE`, `SIGSEGV` from program execution) | converted into a run-time panic |
| `SIGHUP`, `SIGINT`, `SIGTERM` | program exits |
| `SIGQUIT`, `SIGILL`, `SIGTRAP`, `SIGABRT`, `SIGSTKFLT`, `SIGEMT`, `SIGSYS` | exit **with a stack dump** |
| `SIGTSTP`, `SIGTTIN`, `SIGTTOU` | system default (job control) |
| `SIGPROF` | consumed by the runtime for `runtime.CPUProfile` |
| all other signals | caught by runtime, no action taken |

Startup-inheritance rules from the same docs: if started with `SIGHUP` or
`SIGINT` ignored (`SIG_IGN`), they remain ignored; a non-empty inherited
signal mask is generally honored, except the runtime explicitly unblocks the
synchronous signals, `SIGILL`, `SIGTRAP`, `SIGSTKFLT`, `SIGCHLD`, `SIGPROF`,
and — on Linux — signals **32 (`SIGCANCEL`)** and **33 (`SIGSETXID`)** (used
internally by glibc). "Subprocesses started by os.Exec, or by os/exec, will
inherit the modified signal mask."

### 4.4 `SIGPIPE` and shutdown patterns

The os/signal documentation carries a dedicated SIGPIPE section (behavior
differs for writes to descriptors 1/2 versus other broken pipes — consult the
package docs before piping Go stderr). Canonical graceful-shutdown pattern:

```go
package main

import (
    "context"
    "log"
    "os"
    "os/signal"
    "syscall"
)

func main() {
    ctx, stop := signal.NotifyContext(context.Background(),
        syscall.SIGINT, syscall.SIGTERM)
    defer stop()

    <-ctx.Done()               // unblocked by ^C or SIGTERM
    log.Println("shutting down")
    // drain workers, flush buffers, close servers here (all plain Go code)
    os.Exit(0)                 // careful: skips remaining defers
}
```

`NotifyContext` (go1.16+) composes signal handling with `context`-based
cancellation — including `exec.CommandContext` (§5.4). For signals you must
consume without a context, the buffered-channel pattern (buffer ≥ 1) plus
`signal.Stop` on shutdown keeps the contract of §2.2.

### 4.5 POSIX vs. Linux-specific notes

The `os/signal` API is portable; the *constants* are platform (`syscall.SIG*`).
Linux specifics visible in this chapter's verified docs: `Pdeathsig`
(SysProcAttr), signals 32/33 unblocking (glibc internals), `Pgid`/`Setpgid`
process-group control. The kernel-level view of everything above — delivery,
masking, pending sets — is in
[../interfaces/signal-masks.md](../interfaces/signal-masks.md) and
[../signals/standard-signals.md](../signals/standard-signals.md).

---

## 5. Subprocess and Child-Process Management

### 5.1 Creation: `exec.Command` / `CommandContext`

```go
cmd := exec.Command("grep", "-c", "root", "/etc/passwd") // argv array; no shell
cmd.Dir = "/tmp"                                         // child cwd
cmd.Env = append(os.Environ(), "FOO=bar")                // default: parent env
out, err := cmd.Output()                                 // captures stdout
```

- `Command(name, args…)` builds a `Cmd`; `Run`/`Output`/`CombinedOutput` are
  one-shot; `Start`/`Wait` for streaming.
- `LookPath` resolves a bare name via `$PATH`; its failure classification is
  reported as `*exec.Error` or `ErrNotFound`. Since Go 1.19 executables in the
  current directory are no longer found by relative-name resolution quirks —
  see the package overview and the "path security" blog (linked from the
  package docs: https://go.dev/blog/path-security).
- **No shell**: arguments pass verbatim to `execve` — there is no quoting
  layer and thus no shell-injection surface (compare C's `system(3)` hazard,
  [c.md](./c.md) §5.6). Running a shell is always explicit:
  `exec.Command("sh", "-c", script)` — and then `script` is a full shell
  string subject to injection if it embeds untrusted data.

### 5.2 Streams, pipes, and the deadlock rules

`Stdin`/`Stdout`/`Stderr` accept `io.Reader`/`io.Writer`; when they are not
`*os.File`, `exec` spawns copying goroutines and `Wait` waits for them
(Wait docs, §2.3). Pipe-handle forms:

```go
stdin, _  := cmd.StdinPipe()   // io.WriteCloser
stdout, _ := cmd.StdoutPipe()  // io.ReadCloser
```

> "Cmd.Wait will close the pipe after seeing the command exit, so most
> callers need not close the pipe themselves. **It is thus incorrect to call
> Wait before all reads from the pipe have completed.**" — pkg.go.dev/os/exec#Cmd.StdoutPipe

Deadlock taxonomy (all verified consequences of the docs above):

- **Unread pipe fills** (Linux default 64 KiB,
  [../../syscalls/net-ipc/pipe.md](../../syscalls/net-ipc/pipe.md)): child
  blocks writing; if you are blocked writing to its stdin too — deadlock. Use
  `Output()` (reads both streams concurrently), or drain both with separate
  goroutines, or `CombinedOutput`.
- **Wait-before-drain**: violates the StdoutPipe contract above → missed data
  or blockage; always drain to EOF, then `Wait`.
- **Orphaned pipe holders**: the child's own grandchildren inheriting the
  stdout pipe keep it open; `Wait`'s I/O-copy loop does not finish until the
  last holder closes — `WaitDelay` (§5.4) exists precisely for this case.

`ExtraFiles`: "If non-nil, entry i becomes file descriptor 3+i" in the child
(pkg.go.dev/os/exec#Cmd) — the standard socket/file passing mechanism.

### 5.3 Waiting, polling, statuses

```go
err := cmd.Run()                    // start + wait; *ExitError on nonzero exit
err := cmd.Start(); err = cmd.Wait() // streaming form

var ee *exec.ExitError
if errors.As(err, &ee) {
    if ws, ok := ee.Sys().(syscall.WaitStatus); ok {
        if ws.Signaled() { fmt.Println("signal:", ws.Signal()) }
        if ws.CoreDump() { fmt.Println("core dumped") }
        fmt.Println("exit:", ws.ExitStatus())
    }
}
```

`ProcessState.ExitCode()` gives the code (-1 when signaled); `Success()`
mirrors zero-exit. `Cmd.Process` exposes `Signal`/`Kill` for out-of-band
control; there is no stdlib wait-with-timeout — implement with a timer
goroutine calling `Process.Kill`, or (Go 1.20+) `CommandContext` +
`WaitDelay`.

### 5.4 Cancellation: `CommandContext`, `Cancel`, `WaitDelay`

```go
func CommandContext(ctx context.Context, name string, arg ...string) *Cmd // go1.7
```

> "The provided context is used to interrupt the process (by calling
> cmd.Cancel or os.Process.Kill) if the context becomes done before the
> command completes on its own. CommandContext sets the command's Cancel
> function to invoke the Kill method on its Process, and leaves its WaitDelay
> unset. The caller may change the cancellation behavior by modifying those
> fields before starting the command." — pkg.go.dev/os/exec#CommandContext

`Cmd.Cancel func() error` and `Cmd.WaitDelay time.Duration` were added in
**Go 1.20** ("The new Cmd fields Cancel and WaitDelay specify the behavior of
the Cmd when its associated Context is canceled or its process exits with
I/O pipes still held open by a child process" — Go 1.20 release notes,
go.dev/doc/go1.20). Semantics (pkg.go.dev/os/exec#Cmd):

- If the command exits *successfully* after `Cancel` was called and `Cancel`
  did not return an error wrapping `os.ErrProcessDone`, `Wait` returns a
  non-nil error (either wrapping Cancel's error or the context error); a
  non-success exit keeps the usual status.
- `WaitDelay` bounds two delay sources: a child that fails to exit after
  context cancellation, and a child that exits but leaves I/O pipes open.
  When it elapses: the child is killed with `os.Process.Kill` if needed, and
  open pipes are closed to unblock readers.
- If pipes were closed due to `WaitDelay`, no Cancel ran, and the command
  otherwise exited successfully, `Wait` returns `ErrWaitDelay`.
- Graceful alternative: set `Cancel` yourself to send `SIGTERM` and set
  `WaitDelay` to escalate — the documented path to SIGTERM-then-SIGKILL.

### 5.5 Zombies, orphans, and process groups

- `Cmd.Wait`/`Process.Wait` reap the child (no zombie). A child killed with
  `Kill` but never waited becomes a zombie until the Go process exits (then
  the next ancestor reaps it — PID 1 or a subreaper).
- `Process.Release()` releases the OS handle for processes you intentionally
  do not wait on (documented use: fire-and-forget children) — but the child
  still becomes a zombie on death unless something reaps it; for daemons,
  keep a waiter goroutine per child or use `WaitDelay`-style cleanup.
- **Orphans/grandchildren**: `Process.Kill` does not kill descendants
  (Process.Kill docs). Group-kill pattern: `SysProcAttr{Setpgid: true}`, then
  `syscall.Kill(-cmd.Process.Pid, syscall.SIGTERM)`; `process_group`-equivalent
  control in Rust is `CommandExt::process_group` ([rust.md](./rust.md) §2.3).
- `Pdeathsig` (SysProcAttr) asks the kernel to signal the child when the
  *creating thread* dies — with Go's M:N threading the creating thread can
  exit while the parent process lives, which is the documented footgun
  (issue 27505 reference in pkg.go.dev/syscall).

### 5.6 Sync vs. async, timeouts

One-shot helpers (`Run`, `Output`, `CombinedOutput`) block the goroutine —
fine for CLI tools; servers prefer `Start` + explicit pipes + `Wait` under a
`context`. Timeout pattern (pre-1.20 and post-1.20):

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
cmd := exec.CommandContext(ctx, "longjob")
cmd.WaitDelay = 2 * time.Second   // go1.20+: grace period before kill+pipes
out, err := cmd.Output()
// ctx.Err() == context.DeadlineExceeded if the deadline fired
```

---

## 6. Concurrency and Resource Semantics

### 6.1 Goroutines, threads, GOMAXPROCS, and signals

The runtime multiplexes goroutines onto OS threads (M:N). `runtime.GOMAXPROCS`
sizes the scheduler's logical-processor count. Signal handling is
process-wide: the runtime installs its machinery per process, unblocks the
documented set (§4.3), and relays to registered channels. Because delivery is
via channels on ordinary goroutines, there are no handler-side restrictions —
but the *shutdown code* those goroutines run still races with everything
else; a signal arriving during another goroutine's `os.Exit` means the exit
wins and the notify channel never sees the signal (no ordering is
documented — design shutdown so exactly one goroutine decides to exit).

### 6.2 Resource ownership and cleanup guarantees

- **fds**: `os.File` owns its descriptor; close-on-drop does not exist — Go
  has no destructors, so fd lifetime is explicit (`Close`), typically via
  defer. Leaked `Cmd` pipe handles leak fds and keep EOF pending (§5.2).
- **Buffering**: `bufio.Writer` must be flushed before `os.Exit` (defers do
  not run on Exit); `log`'s default logger writes unbuffered to stderr.
- **GC/finalizers**: `runtime.SetFinalizer` is no substitute for `Close` —
  finalizers run at GC discretion and never after `os.Exit`.
- **Races**: `Wait` must not be called concurrently (Cmd.Wait docs); two
  goroutines signaling/killing the same `Process` is a logic race, not
  data-unsafe (the methods are safe to call, the *policy* isn't).
- **Deadlocks**: pipe-buffer exhaustion (§5.2), `Wait` before drain, and
  signal channels with zero buffer that nobody reads (Notify's non-blocking
  send then *drops* signals rather than blocking the runtime — the docs put
  the buffering obligation on you).
- **Leaks**: unreaped children (zombies); goroutines blocked forever on a
  pipe whose peer died; `Notify` channels never `Stop`ped keep the runtime's
  handler table growing.

---

### Coverage ledger

Statuses: **documented** = covered above with verified signature and
reference; **source-limited** = a named primary source was unreachable this
session (missing source stated). Signature source of truth: pkg.go.dev
(retrieved 2026-10; linux/amd64 rendering; site-reported module version
go1.27.2), go.dev/ref/spec, go.dev/doc/go1.20 release notes.

| API | Canonical signature | Status | Reference |
|---|---|---|---|
| `os.Exit` | `func Exit(code int)` | documented | pkg.go.dev/os#Exit |
| `os.Getpid` | `func Getpid() int` | documented | pkg.go.dev/os |
| `log.Fatal` | `func Fatal(v ...any)` | documented | pkg.go.dev/log (Fatal calls os.Exit(1)) |
| `log.Fatalf` | `func Fatalf(format string, v ...any)` | documented | pkg.go.dev/log |
| `log.Fatalln` | `func Fatalln(v ...any)` | documented | pkg.go.dev/log |
| `runtime.Goexit` | `func Goexit()` | documented | pkg.go.dev/runtime#Goexit |
| `panic` builtin | `func panic(interface{})` (spec) | documented | go.dev/ref/spec, Handling panics |
| `recover` builtin | `func recover() interface{}` (spec) | documented | go.dev/ref/spec, Handling panics |
| `signal.Notify` | `func Notify(c chan<- os.Signal, sig ...os.Signal)` | documented | pkg.go.dev/os/signal#Notify |
| `signal.Stop` | `func Stop(c chan<- os.Signal)` (go1.1) | documented | pkg.go.dev/os/signal#Stop |
| `signal.Reset` | `func Reset(sig ...os.Signal)` (go1.5) | documented | pkg.go.dev/os/signal#Reset |
| `signal.Ignore` | `func Ignore(sig ...os.Signal)` (go1.5) | documented | pkg.go.dev/os/signal#Ignore |
| `signal.Ignored` | `func Ignored(sig os.Signal) bool` (go1.5) | documented | pkg.go.dev/os/signal index |
| `signal.NotifyContext` | `func NotifyContext(parent context.Context, signals ...os.Signal) (ctx context.Context, stop context.CancelFunc)` (go1.16) | documented | pkg.go.dev/os/signal#NotifyContext |
| `os.Signal` | interface type; `os.Interrupt`, `os.Kill` values | documented | pkg.go.dev/os |
| `exec.Command` | `func Command(name string, arg ...string) *Cmd` | documented | pkg.go.dev/os/exec#Command |
| `exec.CommandContext` | `func CommandContext(ctx context.Context, name string, arg ...string) *Cmd` (go1.7) | documented | pkg.go.dev/os/exec#CommandContext |
| `exec.LookPath` | `func LookPath(file string) (string, error)` | documented | pkg.go.dev/os/exec#LookPath |
| `exec.Cmd` | struct: Stdin/Stdout/Stderr, ExtraFiles, SysProcAttr, Process, ProcessState, Err, Cancel (go1.20), WaitDelay (go1.20) | documented | pkg.go.dev/os/exec#Cmd; go.dev/doc/go1.20 |
| `Cmd.Start` | `func (c *Cmd) Start() error` | documented | pkg.go.dev/os/exec |
| `Cmd.Wait` | `func (c *Cmd) Wait() error` | documented | pkg.go.dev/os/exec#Cmd.Wait |
| `Cmd.Run` | `func (c *Cmd) Run() error` | documented | pkg.go.dev/os/exec#Cmd.Run |
| `Cmd.Output` | `func (c *Cmd) Output() ([]byte, error)` | documented | pkg.go.dev/os/exec#Cmd.Output |
| `Cmd.CombinedOutput` | `func (c *Cmd) CombinedOutput() ([]byte, error)` | documented | pkg.go.dev/os/exec |
| `Cmd.StdinPipe` | `func (c *Cmd) StdinPipe() (io.WriteCloser, error)` | documented | pkg.go.dev/os/exec |
| `Cmd.StdoutPipe` | `func (c *Cmd) StdoutPipe() (io.ReadCloser, error)` | documented | pkg.go.dev/os/exec#Cmd.StdoutPipe |
| `Cmd.StderrPipe` | `func (c *Cmd) StderrPipe() (io.ReadCloser, error)` | documented | pkg.go.dev/os/exec |
| `Cmd.Environ` | `func (c *Cmd) Environ() []string` (go1.19) | documented | pkg.go.dev/os/exec |
| `exec.ExitError` | `type ExitError struct { *os.ProcessState; Stderr []byte }` | documented | pkg.go.dev/os/exec |
| `exec.ErrNotFound` | `var ErrNotFound = errors.New("executable file not found in $PATH")` | documented | pkg.go.dev/os/exec |
| `exec.ErrWaitDelay` | `var ErrWaitDelay = errors.New("exec: WaitDelay expired before I/O complete")` | documented | pkg.go.dev/os/exec |
| `exec.Error` | `type Error struct { Name string; Err error }` (+ `Unwrap`, go1.13) | documented | pkg.go.dev/os/exec |
| `os.Process.Signal` | `func (p *Process) Signal(sig Signal) error` | documented | pkg.go.dev/os#Process.Signal |
| `os.Process.Kill` | `func (p *Process) Kill() error` | documented | pkg.go.dev/os#Process.Kill |
| `os.Process.Wait` | `func (p *Process) Wait() (*ProcessState, error)` | documented | pkg.go.dev/os |
| `os.Process.Release` | `func (p *Process) Release() error` | documented | pkg.go.dev/os |
| `os.ProcessState.ExitCode` | `func (p *ProcessState) ExitCode() int` | documented | pkg.go.dev/os |
| `os.ProcessState.Sys` | `func (p *ProcessState) Sys() any` | documented | pkg.go.dev/os |
| `syscall.WaitStatus` methods | `Exited/ExitStatus/Signaled/Signal/CoreDump/Stopped/StopSignal/Continued/TrapCause` | documented | pkg.go.dev/syscall (linux/amd64) |
| `syscall.SysProcAttr` fields | `Setpgid bool`, `Pgid int`, `Pdeathsig Signal`, `Setsid bool`, `Chroot`, `Credential`, `Cloneflags`, `Foreground`, `Ctty` | documented | pkg.go.dev/syscall (linux/amd64) |
| `syscall.Kill` | `func Kill(pid int, sig Signal) (err error)` | source-limited | pkg.go.dev/syscall page fetched but per-function rendering not extracted this session; existence/behavior follows POSIX kill(2) — verify signature text before quoting |
| `runtime.GOMAXPROCS` | `func GOMAXPROCS(n int) int` | documented | pkg.go.dev/runtime |
| `runtime.SetFinalizer` | `func SetFinalizer(obj, finalizer any)` | source-limited | listed in runtime index on the fetched page; dedicated doc text not extracted — verify wording before quoting |
| Deferred-call semantics per path | return/Exit/Fatal/panic/Goexit table (§1.2) | documented | go.dev/ref/spec (Defer statements, Handling panics); pkg.go.dev/os#Exit; pkg.go.dev/runtime |
| Default signal behavior table | §4.3 (verified list incl. signals 32/33 on Linux) | documented | pkg.go.dev/os/signal overview |

Counts: **45** inventoried · **43** documented · **2** source-limited ·
**0** remaining.

---

## Related Topics

- Language siblings: [C](./c.md) · [C++](./cpp.md) · [Rust](./rust.md)
- Exit status: [Lifecycle](../exit-status/lifecycle.md) ·
  [Conventions (0, 128+N, 137, 143)](../exit-status/conventions.md)
- Signals: [Standard signals](../signals/standard-signals.md) ·
  [Real-time signals](../signals/real-time-signals.md) ·
  [signal masks](../interfaces/signal-masks.md) ·
  [kill and raise](../interfaces/kill-raise.md) ·
  [signalfd/pidfd](../interfaces/signalfd-pidfd.md)
- Existing book pages: [process control](../../../linux/sysprog/process-control.md) ·
  [_exit(2)](../../../linux/syscalls/process/_exit.md) ·
  [execve(2)](../../../linux/syscalls/process/execve.md) ·
  [waitid(2)](../../../linux/syscalls/process/waitid.md) ·
  [pipe(2)](../../../linux/syscalls/net-ipc/pipe.md)
- Containers (PID 1, graceful shutdown of Go services):
  [containers/pid1-signals](../containers/pid1-signals.md) ·
  [containers/docker](../containers/docker.md)

## References

- Go language specification — *Defer statements*, *Handling panics* —
  https://go.dev/ref/spec (retrieved 2026-10).
- pkg.go.dev standard-library documentation (retrieved 2026-10; linux/amd64
  rendering; site-reported module version go1.27.2):
  https://pkg.go.dev/os (Exit, Process, ProcessState, Signal),
  https://pkg.go.dev/os/signal (Notify, Stop, Reset, Ignore, NotifyContext,
  default-behavior overview, SIGPIPE section),
  https://pkg.go.dev/os/exec (Cmd, Command, CommandContext, Cancel, WaitDelay,
  pipes, ExitError, ErrNotFound, ErrWaitDelay, LookPath),
  https://pkg.go.dev/syscall (WaitStatus, SysProcAttr),
  https://pkg.go.dev/log (Fatal family),
  https://pkg.go.dev/runtime (Goexit, GOTRACEBACK/exit code 2, GOMAXPROCS).
- Go 1.20 release notes (Cmd.Cancel / Cmd.WaitDelay) —
  https://go.dev/doc/go1.20.
- Go blog, "Path security" (exec.LookPath changes referenced from the
  os/exec package overview) — https://go.dev/blog/path-security.
- POSIX.1-2017 and Linux man-pages for the underlying
  wait-status/kill/setpgid semantics cross-referenced in §3.4/§5.5 —
  https://pubs.opengroup.org/onlinepubs/9699919799/,
  https://man7.org/linux/man-pages/.
