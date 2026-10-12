# Python: Exit Status, Signals, and Process Lifecycle

**ID range:** LG-PY-001 … LG-PY-006 — **Version scope:** Python 3.12/3.13/3.14 stable behavior; all claims verified against the CPython 3.13 C-API manual (docs.python.org/3.13) and the docs.python.org/3 library reference as served at retrieval time (2026-10; the `/3` URL currently serves the 3.15 development docs). Where a behavior is CPython-implementation-specific rather than a Python-language guarantee, that is stated explicitly.

Python programs terminate processes through exceptions (`SystemExit`), through the `os` module's raw process calls, and through the `signal`/`subprocess`/`multiprocessing` modules. The interpreter sits between the Python code and the kernel: most of the time the OS primitives (exit status, signal delivery, wait status) are *reinterpreted* by the CPython runtime, and knowing where that reinterpretation happens is the point of this chapter.

---

## 1. Syntax and Semantics of Termination (LG-PY-001)

### 1.1 The normal path: `sys.exit` and `SystemExit`

Canonical signature ([sys.exit](https://docs.python.org/3/library/sys.html#sys.exit)):

```python
sys.exit(arg=0) -> NoReturn   # raises SystemExit(arg)
```

The documented argument semantics, quoted from the *System-specific parameters and functions* page:

> "The optional argument arg can be an integer giving the exit status (defaulting to zero), or another type of object. If it is an integer, zero is considered "successful termination" and any nonzero value is considered "abnormal termination" by shells and the like. Most systems require it to be in the range 0–127, and produce undefined results otherwise. … If another type of object is passed, None is equivalent to passing zero, and any other object is printed to stderr and results in an exit code of 1."

`sys.exit` "only" raises an exception; the docs state three consequences precisely:

- It terminates the process only when called from the **main thread** and the exception is **not intercepted**.
- `finally` clauses of enclosing `try` statements are honored.
- The exit attempt can be intercepted at an outer level (`except SystemExit:` in a caller cancels the exit).

`SystemExit` itself ([Built-in Exceptions](https://docs.python.org/3/library/exceptions.html#SystemExit)):

> "It inherits from `BaseException` instead of `Exception` so that it is not accidentally caught by code that catches `Exception`."

So the classic mistake is fatal to correctness:

```python
try:
    work()
except Exception:          # does NOT catch SystemExit, KeyboardInterrupt
    log.error("failed")
# SystemExit propagates past this handler
```

When `SystemExit` is not handled, "the Python interpreter exits; no stack traceback is printed."

**`SystemExit` constructor values → exit status**

| Value passed to `sys.exit` / `SystemExit(...)` | Status seen by parent | Traceback printed? |
|---|---|---|
| omitted / `None` | 0 | no |
| `int` (e.g. `2`) | that integer (conventionally 0–127) | no |
| non-`int` object (e.g. `"some error message"`) | 1, object printed to stderr | no |

This mapping is verified from both the `sys.exit` doc and the `SystemExit` doc; it is also visible in CPython's `handle_system_exit` in `Python/pythonrun.c` (verified in the 3.13 source: integer check first, otherwise write the object to `sys.stderr` and set `exitcode = 1`).

**Cleanup-error override.** `sys.exit` docs, *Changed in version 3.6*: "If an error occurs in the cleanup after the Python interpreter has caught `SystemExit` (such as an error flushing buffered data in the standard streams), the exit status is changed to **120**." Status 120 therefore means "failed to flush stdio during interpreter shutdown" — it can override the status you asked for.

### 1.2 Unhandled exceptions

An exception that is not `SystemExit`, propagating out of the top-level code, is printed by `sys.excepthook` as a traceback on stderr and the interpreter exits with status **1** (verified in CPython 3.13 `Python/pythonrun.c`, `_Py_HandleSystemExit`/`_PyErr_PrintEx`: the non-integer-exit path sets `exitcode = 1`).

### 1.3 The abnormal paths: `os._exit` and `os.abort`

```python
os._exit(n) -> NoReturn
os.abort()  -> NoReturn
```

`os._exit` ([os docs](https://docs.python.org/3/library/os.html#os._exit)):

> "Exit the process with status n, without calling cleanup handlers, flushing stdio buffers, etc." … "The standard way to exit is `sys.exit(n)`. `_exit()` should normally only be used in the child process after a `fork()`."

That means `atexit` handlers, `finally` blocks already in flight, buffered `io` data, and interpreter finalization are all skipped — the process issues the `exit_group`/`_exit`-equivalent immediately.

`os.abort` ([os docs](https://docs.python.org/3/library/os.html#os.abort)):

> "Generate a SIGABRT signal to the current process. On Unix, the default behavior is to produce a core dump; on Windows, the process immediately returns an exit code of 3. Be aware that calling this function will not call the Python signal handler registered for SIGABRT with `signal.signal()`."

So on Linux a Python program killed via `os.abort()` dies **by signal 6** (`WSIGNALED 6` from `os.waitpid`, `128+6=134` in `$?` via the shell), not with an exit status — even if you installed a SIGABRT handler.

The `os` module also exports the BSD `sysexits.h` constants (`os.EX_OK`, `os.EX_USAGE`, `os.EX_NOINPUT`, …) "defined and can be used with `_exit()`, although they are not required."

### 1.4 `atexit`: ordered interpreter-shutdown hooks

Canonical API ([atexit docs](https://docs.python.org/3/library/atexit.html)):

```python
atexit.register(func, *args, **kwargs) -> func   # usable as a decorator
atexit.unregister(func) -> None
```

Verified semantics:

- Handlers run **in reverse registration order** (LIFO): "If you register A, B, and C, at interpreter shutdown time they will be run in the order C, B, A."
- Exceptions inside a handler: "a traceback is printed (unless `SystemExit` is raised) and the exception information is saved. After all exit handlers have had a chance to run, the last exception to be raised is re-raised." They are not silently swallowed — but the re-raise happens at the end of shutdown and the process still exits (with 1).
- Handlers are **not** run: "when the program is killed by a signal not handled by Python, when a Python fatal internal error is detected, or when `os._exit()` is called."
- *Changed in 3.12*: "Attempts to start a new thread or `os.fork()` a new process in an exit handler now leads to `RuntimeError`."
- The effect of registering/unregistering from within a cleanup function is undefined.
- In multi-interpreter programs each interpreter has its own handler stack (3.12+).

### 1.5 Interpreter shutdown sequence (CPython)

The full internal sequence of `Py_FinalizeEx` is documented in the C API manual ([Initialization, Finalization, and Threads](https://docs.python.org/3.13/c-api/init.html#Py_FinalizeEx)). Verified facts a Python-level programmer needs:

- Finalization must happen on the main thread of the main interpreter; `Py_FinalizeEx` "undoes all initializations made by `Py_Initialize()`".
- Documented caveats: module destruction order is unspecified ("done in random order"); `__del__` methods may fail when they depend on other objects/modules; dynamically loaded extension modules are not unloaded; circular-reference memory is not freed.
- `Py_FinalizeEx` must never be called from shutdown code itself ("it must not be called by any code that may be run as part of the interpreter shutdown process, such as atexit handlers, object finalizers, or any code that may be run while flushing the stdout and stderr files").
- If flushing buffered data fails during finalization it returns `-1`, and the launcher turns that into exit code 120 (CPython 3.13 `Modules/main.c`: `if (Py_FinalizeEx() < 0) { exitcode = 120; }`) — consistent with the 3.6 note in the `sys.exit` docs.
- Language-level ordering facts documented in the library reference: `threading` shutdown joins non-daemon threads, `atexit` callbacks run, then stdio is flushed. Daemon threads are abruptly stopped at interpreter exit — they receive no cleanup guarantee (see *Concurrency*, §7).

### 1.6 Exit-status derivation table

| Termination path | Exit status seen by parent | Source |
|---|---|---|
| Return from `__main__` | 0 | `sys.exit` docs (implicit `exit(0)`) |
| `sys.exit()` / `sys.exit(None)` | 0 | `sys.exit` docs |
| `sys.exit(7)` | 7 | `sys.exit` docs |
| `sys.exit("msg")` | 1, `msg` on stderr | `sys.exit` docs |
| Unhandled ordinary exception | 1 + traceback | CPython 3.13 `pythonrun.c` (`exitcode = 1`), matches observable behavior |
| Unhandled `KeyboardInterrupt` (Ctrl-C, default SIGINT) | shell reports **130**; CPython re-raises SIGINT | CPython implementation, see §4.3 — not stated in language docs |
| `os._exit(n)` | n (skips all cleanup) | `os._exit` docs |
| `os.abort()` | killed by SIGABRT: `WIFSIGNALED`, shell 134; Windows: status 3 | `os.abort` docs |
| stdio flush error during shutdown after `SystemExit` | 120 (overrides requested status) | `sys.exit` docs *Changed in 3.6* |
| Killed by unhandled signal (e.g. `kill -TERM`) | terminated by signal; shell `$?` = 128+15 | OS behavior, not Python |

### 1.7 Misconceptions

- **"`sys.exit` ends the process."** No — it raises an exception; it can be caught, and it is a no-op-ish for process termination if raised in a non-main thread ("it will only exit the process when called from the main thread").
- **"`except Exception` catches everything."** It deliberately does not catch `SystemExit`/`KeyboardInterrupt`/`GeneratorExit` (all `BaseException` subclasses).
- **"`atexit` runs on SIGTERM."** It does not: signals not handled by Python bypass the hook mechanism entirely.
- **"`os._exit(0)` is a fast clean exit."** It is *fast* but not *clean* — buffered data and registered handlers are lost, which is why the docs confine it to forked children.
- **"Exit status is a byte with no range rules."** The `sys.exit` docs warn: "Most systems require it to be in the range 0–127, and produce undefined results otherwise."

---

## 2. Standard-Library and Runtime API Inventory (LG-PY-002)

Signatures below were verified against the fetched documentation pages cited in the ledger. All of these are **CPython** module features (the `signal` module model in particular is CPython-specific, not a language guarantee).

### `sys`

| API | Verified signature / contract | Key semantics |
|---|---|---|
| `sys.exit` | `sys.exit([arg])` | Raises `SystemExit`; see §1.1; main-thread-only for process exit; finally honored; interceptable |
| `sys.stderr` | `io.TextIOWrapper` | Destination for `sys.exit("msg")` output and tracebacks |

### `os` — termination and process primitives

| API | Verified signature | Key semantics |
|---|---|---|
| `os._exit` | `os._exit(n, /)` | Immediate exit; no cleanup handlers, no stdio flush |
| `os.abort` | `os.abort()` | SIGABRT to self; core dump on Unix; does **not** invoke Python SIGABRT handler |
| `os.fork` | `os.fork() -> int` | 0 in child, child pid in parent; `OSError` on error; **DeprecationWarning since 3.12 when multiple threads detected**; auditing event `os.fork` |
| `os.execv` | `os.execv(path, args)`; also `execve(path, args, env)`, `execvp(file, args)`, `execvpe(file, args, env)` | Replace current process; "they do not return"; errors → `OSError`; "Open file objects and descriptors are not flushed" before exec |
| `os.system` | `os.system(command) -> int` | Runs via C `system()`; on Unix "the return value is the exit status of the process encoded in the format specified for `wait()`" (use `WEXITSTATUS` to decode); system-dependent on other platforms |
| `os.waitpid` | `os.waitpid(pid, options, /) -> (pid, status)` | Unix: waits for child; `pid=-1` any child, `0` any child in our process group, `<-1` process group `-pid`; `WNOHANG` → `(0, 0)` if none ready |
| `os.kill` | `os.kill(pid, sig, /)` | Send signal; `Availability: Unix, Windows…`; Windows quirks with `CTRL_C_EVENT`/`TerminateProcess` |
| `os.killpg` | `os.killpg(pgid, sig, /)` | Signal to process group; Unix |
| `os.setsid` | `os.setsid()` | New session; Unix |
| `os.getpgrp` | `os.getpgrp() -> int` | Current process group; Unix |
| `os.WIFEXITED` | `os.WIFEXITED(status) -> bool` | True if exited normally (exit/`_exit`/return from main) |
| `os.WEXITSTATUS` | `os.WEXITSTATUS(status) -> int` | "should be employed only if `WIFEXITED()` is true" |
| `os.WIFSIGNALED` | `os.WIFSIGNALED(status) -> bool` | True if terminated by a signal |
| `os.WTERMSIG` | `os.WTERMSIG(status) -> int` | Signal number; only if `WIFSIGNALED()` true |
| `os.WCOREDUMP` | `os.WCOREDUMP(status, /) -> bool` | Only if `WIFSIGNALED()` true |
| `os.WIFSTOPPED` / `os.WSTOPSIG` | `… -> bool / int` | Stop status; only meaningful with `WUNTRACED` or under ptrace |
| `os.WIFCONTINUED` | `os.WIFCONTINUED(status) -> bool` | SIGCONT resume; use with `WCONTINUED` |
| `os.WNOHANG` / `os.WUNTRACED` / `os.WCONTINUED` | int flags | Non-blocking wait; report stopped; report continued |

Status decoding example (raw `os`-level style, equivalent to what `subprocess` wraps):

```python
import os
pid, status = os.waitpid(child_pid, 0)   # blocking reap; (0,0) possible with WNOHANG
if os.WIFEXITED(status):
    code = os.WEXITSTATUS(status)         # normal exit, 0-255
elif os.WIFSIGNALED(status):
    sig = os.WTERMSIG(status)             # e.g. 15 -> shell $? would be 143
    coredump = os.WCOREDUMP(status)
```

### `signal` module (CPython-specific model)

All signatures verified against the [signal docs](https://docs.python.org/3/library/signal.html):

| API | Verified signature | Key semantics |
|---|---|---|
| `signal.signal` | `signal.signal(signalnum, handler) -> handler` | handler is callable `(signalnum, frame)` or `SIG_DFL`/`SIG_IGN`; returns previous handler; **ValueError unless called from the main thread of the main interpreter**; handler stays installed (BSD emulation) except SIGCHLD |
| `signal.getsignal` | `signal.getsignal(signalnum) -> handler \| SIG_IGN \| SIG_DFL \| None` | `None` = handler not installed from Python |
| `signal.alarm` | `signal.alarm(time) -> int` | SIGALRM after `time` seconds (integer); one alarm at a time; returns seconds remaining on previous alarm; Unix |
| `signal.setitimer` | `signal.setitimer(which, seconds, interval=0)` | `ITIMER_REAL`→SIGALRM, `ITIMER_VIRTUAL`→SIGVTALRM, `ITIMER_PROF`→SIGPROF; returns old values |
| `signal.raise_signal` | `signal.raise_signal(signum)` (3.8+) | Send a signal to the calling process |
| `signal.set_wakeup_fd` | `signal.set_wakeup_fd(fd, *, warn_on_full_buffer=True)` | Signal number written as one byte to fd when a handled signal arrives; fd must be non-blocking; returns old fd; the documented library pattern to wake `poll`/`select` loops |
| `signal.pthread_sigmask` | `signal.pthread_sigmask(how, mask) -> set` | `SIG_BLOCK`/`SIG_UNBLOCK`/`SIG_SETMASK`; returns old mask as a set of `Signals` enums |
| `signal.pthread_kill` | `signal.pthread_kill(thread_id, signalnum)` | Signal one thread; useful "to force a running system call to fail with `InterruptedError`"; `signalnum=0` = existence check |
| `signal.sigpending` | `signal.sigpending() -> set` (3.3+) | Signals pending for the calling thread |
| `signal.sigwait` | `signal.sigwait(sigset) -> int` (3.3+) | Synchronously accept one of sigset; returns signal number |
| `signal.SIG_DFL` / `signal.SIG_IGN` | enum members | Default action / ignore |

Defaults CPython installs (documented): **SIGPIPE ignored** ("so write errors on pipes and sockets can be reported as ordinary Python exceptions") and **SIGINT → `KeyboardInterrupt`**. A handler, once set, remains installed — Python emulates BSD `signal()` regardless of the platform's `signal(2)` semantics — except SIGCHLD which "follows the underlying implementation".

### `subprocess` (headline API; details in §6)

| API | Verified signature |
|---|---|
| `subprocess.run` | `run(args, *, stdin=None, input=None, stdout=None, stderr=None, capture_output=False, shell=False, cwd=None, timeout=None, check=False, encoding=None, errors=None, text=None, env=None, universal_newlines=None, **other_popen_kwargs) -> CompletedProcess` |
| `subprocess.Popen` | `Popen(args, bufsize=-1, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None, close_fds=True, shell=False, cwd=None, env=None, universal_newlines=None, startupinfo=None, creationflags=0, restore_signals=True, start_new_session=False, pass_fds=(), *, group=None, extra_groups=None, user=None, umask=-1, encoding=None, errors=None, text=None, pipesize=-1, process_group=None)` |
| `subprocess.CompletedProcess` | attributes `args`, `returncode`, `stdout`, `stderr`; method `check_returncode()` |
| `subprocess.CalledProcessError` / `TimeoutExpired` | exceptions carrying `returncode` / `cmd`, `timeout`, `output`, `stderr` |

### `faulthandler` (brief, verified)

`faulthandler` ([docs](https://docs.python.org/3/library/faulthandler.html)) dumps Python tracebacks on fatal signals (`SIGSEGV`, `SIGFPE`, `SIGABRT`, …), on timeouts, and on user signal (default `SIGUSR1`). `faulthandler.enable()` installs handlers; `faulthandler.disable()` removes them. This is the documented tool for the synchronous-error case the `signal` docs call out: catching `SIGFPE`/`SIGSEGV` with `signal.signal()` "makes little sense" because Python will return from the handler into the faulting C code.

---

## 3. Process Lifecycle and Termination (LG-PY-003)

**Creation.** The process starts when the OS `exec`s the interpreter; CPython installs its default signal dispositions (SIGPIPE ignored, SIGINT handler), runs module import, and executes the module named on the command line. Embedded interpreters can skip signal-handler installation (`Py_InitializeEx(initsigs=0)`, documented in the C API: "skips initialization registration of signal handlers, which may be useful when CPython is embedded").

**Normal termination.** Returning from the entry module is equivalent to `sys.exit(0)`. The interpreter then: shuts down `threading` (joins non-daemon threads), runs `atexit` handlers LIFO, performs GC/finalization passes, and flushes stdio. Status 0 unless a handler raised (→ re-raised at the end; status 1) or a flush failed (→ 120).

**Explicit termination.** `sys.exit(n)` (graceful, exception-based), `os._exit(n)` (immediate, cleanup-free), `os.abort()` (crash-style, SIGABRT). `sys.exit` from a worker thread only unwinds that thread — the process keeps running.

**Abnormal termination.** Unhandled exception → traceback + 1. Unhandled `KeyboardInterrupt` → CPython-specific SIGINT re-raise (§4.3). External signal with default disposition → the process dies by signal; Python code never runs; `atexit` does not run.

**Process vs thread vs child.** `sys.exit`/`SystemExit` in a `threading.Thread` ends only that thread. `os._exit`/`os.abort` affect the whole process (and thus all threads). Child processes are separate OS processes created by `subprocess`/`multiprocessing`/`os.fork`; terminating the parent does not terminate them (they are re-parented to init — orphans), and `multiprocessing.Process.terminate` explicitly warns "descendant processes of the process will not be terminated – they will simply become orphaned."

---

## 4. Signals and OS Interaction (LG-PY-004)

### 4.1 The CPython signal model (implementation-specific, clearly)

The documented mechanism ([signal docs, "Execution of Python signal handlers"]):

> "A Python signal handler does not get executed inside the low-level (C) signal handler. Instead, the low-level signal handler sets a flag which tells the virtual machine to execute the corresponding Python signal handler at a later point (for example, at the next bytecode instruction)."

Consequences documented verbatim:

- Catching synchronous signals is pointless: catching `SIGFPE`/`SIGSEGV` "makes little sense … Python will return from the signal handler to the C code, which is likely to raise the same signal again, causing Python to apparently hang."
- A long pure-C computation (e.g. regex over a huge body) "may run uninterrupted for an arbitrary amount of time, regardless of any signals received."
- If a handler raises, the exception "will be raised 'out of thin air' in the main thread."
- **Warning:** "Synchronization primitives such as `threading.Lock` should not be used within signal handlers. Doing so can lead to unexpected deadlocks."

### 4.2 Threads and handlers

> "Python signal handlers are always executed in the main Python thread of the main interpreter, even if the signal was received in another thread. This means that signals can't be used as a means of inter-thread communication." — and — "only the main thread of the main interpreter is allowed to set a new signal handler" (elsewhere: calling `signal.signal` from another thread raises `ValueError`).

For per-thread signal control, Python exposes the POSIX thread-level primitives: `signal.pthread_sigmask` (block/unblock per calling thread), `signal.pthread_kill` (direct a signal at one thread), `signal.sigpending`, `signal.sigwait`.

### 4.3 Default dispositions, Ctrl-C, and the 130 convention

- Default SIGINT behavior: a handler that raises `KeyboardInterrupt` (documented).
- When `KeyboardInterrupt` goes **unhandled**, the language docs only promise interpreter exit; the CPython implementation (verified in CPython 3.13 `Modules/main.c`, function `exit_sigint`, comment referencing bpo-1054041) resets SIGINT to `SIG_DFL` and `kill(getpid(), SIGINT)`s itself so that "a calling process such as a shell may not know about the user's ^C" otherwise; if that fails it returns `SIGINT + 128` (130). So `$?` after Ctrl-C is conventionally 130 — **implementation behavior of CPython on POSIX, not a language guarantee**.
- SIGPIPE is ignored by default so `BrokenPipeError` surfaces as an exception; `subprocess.restore_signals` exists precisely to undo this in children (§6.2).

### 4.4 EINTR and PEP 475

[PEP 475](https://peps.python.org/pep-0475/) (Python 3.5): "System call wrappers provided in the standard library should be retried automatically when they fail with EINTR." Since 3.5, stdlib I/O calls are auto-retried on `EINTR`, and the signal handler runs before the retry — application code normally never sees `InterruptedError` for EINTR. This is a Python runtime decision that *changes* raw POSIX semantics (where `EINTR` is the caller's problem); note it interacts with the deferred-handler model: the handler runs between the failed syscall and the retry.

### 4.5 Safe handler → application communication

The documented pattern is `signal.set_wakeup_fd`: on each handled signal the runtime writes the signal number as one byte to a non-blocking fd (with `warn_on_full_buffer=True` it emits a warning if the buffer is full so data loss is visible). A selector loop then wakes and processes the signal in normal code — the recommended way to integrate signals with `select`/`poll`/asyncio loops. Within pure-Python handlers, use plain attribute writes / `queue.SimpleQueue` (not locks); the docs only document the wakeup-fd mechanism as the sanctioned cross-thread notification.

### 4.6 POSIX vs Linux-specific

Everything in `signal`/`os` signal handling above is POSIX-generic; nothing in the documented API is Linux-only except the platform gates shown per function ("Availability: Unix"), and Linux is included. Windows diverges sharply (only a subset of signals settable, `CTRL_C_EVENT`/`CTRL_BREAK_EVENT`, `TerminateProcess` semantics in `os.kill`) — those Windows paths are out of scope here beyond noting their existence.

---

## 5. Subprocess and Child-Process Management (LG-PY-005)

### 5.1 `subprocess.Popen`: creation

The verified constructor (full signature in §2) wraps `fork`/`exec` on POSIX ("the class uses `os.execvpe()`-like behavior"). Important documented arguments:

- **`args`** — "a sequence of program arguments or else a single string"; "it is recommended to pass args as a sequence." Warning from the docs: "For maximum reliability, use a fully qualified path for the executable."
- **`bufsize=-1`** — pipe buffering (`0` unbuffered, `1` line, `-1` default).
- **`stdin/stdout/stderr`** — `None` (inherit), `subprocess.PIPE`, `subprocess.DEVNULL`, an int fd, or a file object.
- **`preexec_fn`** — callable run in the child before exec. Warning, quoted: "The preexec_fn parameter is NOT SAFE to use in the presence of threads in your application. The child process could deadlock before exec is called." Note: "If you need to modify the environment for the child use the env parameter rather than doing it in a preexec_fn. The start_new_session and process_group parameters should take the place of code using preexec_fn to call `os.setsid()` or `os.setpgid()` in the child." Not supported in subinterpreters (3.8+, `RuntimeError`).
- **`close_fds=True`** — default: "all file descriptors except 0, 1 and 2 will be closed before the child process is executed."
- **`shell=False`** — default; see §5.4 for the security implications of `True`.
- **`cwd`, `env`** — child working directory and environment mapping (env replaces, not appends).
- **`start_new_session`** — "the `setsid()` system call will be made in the child process prior to the execution" (POSIX; since 3.2).
- **`process_group`** — non-negative int → "`setpgid(0, value)` … in the child process" (POSIX; **added 3.11**).
- **`restore_signals=True`** — "all signals that Python has set to `SIG_IGN` are restored to `SIG_DFL` in the child process before the exec. Currently this includes the SIGPIPE, SIGXFZ and SIGXFSZ signals." This is why a Python-spawned child sees normal SIGPIPE despite the parent ignoring it.
- **`pass_fds`** — fds kept open in the child (implies `close_fds` behavior adjustments).

### 5.2 Waiting, polling, signaling, status

Verified method semantics:

- `Popen.poll()` — "Check if child process has terminated. Set and return returncode attribute. Otherwise, returns None."
- `Popen.wait(timeout=None)` — sets/returns `returncode`; raises `TimeoutExpired` on timeout ("It is safe to catch this exception and retry the wait"). Deadlock note, quoted verbatim: *"This will deadlock when using stdout=PIPE or stderr=PIPE and the child process generates enough output to a pipe such that it blocks waiting for the OS pipe buffer to accept more data. Use Popen.communicate() when using pipes to avoid that."* On Linux ≥ 5.3 the implementation uses `os.pidfd_open()` + `select.poll()` for event-driven waits (documented).
- `Popen.communicate(input=None, timeout=None)` — writes input, drains stdout/stderr, waits; returns `(stdout_data, stderr_data)`. On timeout: "The child process is not killed if the timeout expires, so in order to cleanup properly a well-behaved application should kill the child process and finish communication." Retrying after timeout "will not lose any output"; supplying new input post-timeout is "undefined behavior".
- `Popen.send_signal(sig)` — "Sends the signal signal to the child. Do nothing if the process completed."
- `Popen.terminate()` — POSIX: SIGTERM. `Popen.kill()` — POSIX: SIGKILL.
- `Popen.returncode` — documented in `CompletedProcess`/`Popen`: **"A negative value -N indicates that the child was terminated by signal N (POSIX only)."** This is the canonical signal-death representation in Python's API (not 128+N).

```python
import subprocess, signal
p = subprocess.Popen(["sleep", "100"])
p.terminate()                    # SIGTERM
if p.wait(timeout=5) != 0:       # -15 here: terminated by signal 15
    ...
p2 = subprocess.Popen(["sleep", "100"])
p2.kill()                        # SIGKILL
print(p2.wait())                 # -9
```

### 5.3 `subprocess.run`: the high-level path

Verified semantics (from the `run` docs):

- `timeout` → "internally passed on to `Popen.communicate()`. If the timeout expires, **the child process will be killed and waited for**. The `TimeoutExpired` exception will be re-raised after the child process has terminated." (Note the contrast with bare `communicate`, which does not kill.)
- `check=True` → non-zero exit raises `CalledProcessError` carrying `returncode` and captured output.
- `capture_output=True` → both streams `PIPE` (mutually exclusive with explicit `stdout`/`stderr`).
- `input=...` feeds stdin (implies `stdin=PIPE`).
- On signal death, `CompletedProcess.returncode` is `-N` per the rule above; `CalledProcessError.returncode` likewise.

```python
import subprocess
try:
    r = subprocess.run(["sleep", "100"], timeout=2)
except subprocess.TimeoutExpired as e:
    print(e.timeout, e.output, e.stderr)      # child already killed by run()
```

### 5.4 Shell execution vs argument arrays (security)

The module's *Security Considerations* section, quoted:

> "Unlike some other popen functions, this library will not implicitly choose to call a system shell. This means that all characters, including shell metacharacters, can safely be passed to child processes. If the shell is invoked explicitly, via `shell=True`, it is the application's responsibility to ensure that all whitespace and metacharacters are quoted appropriately to avoid shell injection vulnerabilities. On some platforms, it is possible to use `shlex.quote()` for this escaping."

The docs' canonical shellshot example (from the `exec()` family warning, mirrored for `shell=True` usage):

```python
# filename is user-controlled:
subprocess.run(["ls", filename])   # safe: no shell, filename stays ONE argument
cmd = "ls " + filename             # filename="x; rm -rf ~" -> arbitrary execution
subprocess.run(cmd, shell=True)    # UNSAFE with untrusted input
```

### 5.5 Zombies, timeouts, cancellation

- A child that exits is a zombie until reaped by `wait`/`poll`/`communicate` (or `os.waitpid`). Long-lived parents that spawn children without waiting accumulate zombies.
- Timeouts: `run(timeout=…)` kills and reaps; `Popen.wait(timeout=…)`/`communicate(timeout=…)` raise `TimeoutExpired` and leave the child running — your cleanup code must `kill()` then finish waiting.
- Cancellation: there is no built-in "cancel" — you compose `send_signal`/`terminate`/`kill` with waiting. `Popen.__del__` warns (ResourceWarning) if the child is still running at GC time.
- `asyncio.create_subprocess_exec(program, *args, stdin=None, stdout=None, stderr=None, limit=65536, **kwds)` and `asyncio.create_subprocess_shell(cmd, …)` return asyncio `Process` objects; documented hazard: "If the process object is garbage collected while the process is still running, the child process will be killed."
- `multiprocessing.Process`: `terminate()` — "On POSIX this is done using the SIGTERM signal … Note that exit handlers and finally clauses, etc., will not be executed." with the documented Warning about corrupting pipes/queues and deadlocking on held locks; `kill()` — SIGKILL; `join([timeout])`; `exitcode` — `None` while running, `0` if `run()` returned, `N` if `sys.exit(N)`, `1` on uncaught exception, **`-N` if terminated by signal N**. Start methods: `spawn` (default on Windows/macOS), `fork` (POSIX; the docs note "safely forking a multithreaded process is problematic"), `forkserver`. Python 3.12 additionally deprecates `os.fork` in multi-threaded processes (warning in `os.fork` docs).

### 5.6 Platform notes

All process APIs above carry "Availability: Unix" or POSIX-only markers in the docs (`os.fork`, `os.killpg`, `os.setsid`, `preexec_fn`, `start_new_session`, `process_group`, `restore_signals`, `signal.alarm`). The Linux-specific optimization worth knowing: `Popen.wait` uses `pidfd_open` on Linux ≥ 5.3 (documented), and `os.pidfd_open` itself is exposed since 3.9 ("Availability: Linux >= 5.3").

---

## 6. Concurrency and Resource Semantics (LG-PY-006)

**Threads at shutdown.** Only non-daemon threads block interpreter exit (`threading._shutdown` joins them before `atexit`); daemon threads are terminated abruptly at interpreter exit with no `finally` execution guarantee. Handler-code restrictions at shutdown: since 3.12, `threading.Thread.start()` or `os.fork()` inside an `atexit` handler raises `RuntimeError` (documented race-condition fix).

**fd ownership.** The parent's `Popen.stdin/stdout/stderr` are Python file objects wrapping the pipe ends; closing them yourself while `communicate` manages them is a conflict. `close_fds=True` (default) stops the child from inheriting unrelated fds; `pass_fds` re-opens holes deliberately. After `exec`-family calls, the docs warn: "Open file objects and descriptors are not flushed" — flush before `os.execv*`.

**Buffering.** Pipe capacity is finite; the `Popen.wait` deadlock warning (§5.2) is the canonical pipe-buffer-exhaustion statement in the docs. Child output buffering interacts with this: a child whose stdout is a pipe (block-buffered by libc) may hold data in its own userspace buffer that only flushes at exit — hence the value of `communicate`/line buffering, and of `flush()` in the child.

**Races and leaks.**

- `preexec_fn` + threads → documented child-side deadlock before exec.
- Using locks inside signal handlers → documented deadlocks; handler code runs in the main thread while arbitrary bytecode may hold the lock.
- fork + threads: `os.fork` docs warn that FreeBSD/Cygwin "have known issues when using `fork()` from a thread", and 3.12 added the multi-thread `DeprecationWarning`.
- `multiprocessing.Process.terminate` while the child holds a lock/semaphore → documented cross-process deadlock risk; while using a pipe/queue → documented corruption.
- Unclosed `Popen` objects leak fds and can zombie children; `Popen` emits `ResourceWarning` for still-running children at collection. `multiprocessing.Process.close()` raises `ValueError` if the process is still running ("releasing all resources associated with it" otherwise).

**GC/runtime effects.** The deferred signal-handler model means handler code executes at bytecode boundaries — it can observe objects mid-mutation unless you design for that (simple flag/queue writes). asyncio subprocesses are killed by GC if you drop the object (documented above). These are CPython-runtime behaviors, not Python-language guarantees; other implementations (PyPy etc.) differ in scheduling and finalization details.

---

### Coverage ledger

Statuses: `documented` = verified against the cited source with signature and semantics recorded above; `source-limited` = a named primary source was unreachable or does not document the behavior.

| API | Canonical signature | Status | Reference |
|---|---|---|---|
| LG-PY-001 `sys.exit` | `sys.exit([arg])` | documented | [sys.exit docs](https://docs.python.org/3/library/sys.html#sys.exit) |
| LG-PY-001 `SystemExit` | `SystemExit(arg=0)` (BaseException subclass) | documented | [exceptions docs](https://docs.python.org/3/library/exceptions.html#SystemExit) |
| LG-PY-001 `os._exit` | `os._exit(n, /)` | documented | [os docs](https://docs.python.org/3/library/os.html#os._exit) |
| LG-PY-001 `os.abort` | `os.abort()` | documented | [os docs](https://docs.python.org/3/library/os.html#os.abort) |
| LG-PY-001 `atexit` | `atexit.register(func, *args, **kwargs)` / `atexit.unregister(func)` | documented | [atexit docs](https://docs.python.org/3/library/atexit.html) |
| LG-PY-001 exit-status derivation table | (§1.6) | documented (CPython source verified for rows the docs omit) | [sys.exit docs](https://docs.python.org/3/library/sys.html#sys.exit); CPython 3.13 `Modules/main.c` |
| LG-PY-001 interpreter shutdown (Py_FinalizeEx) | C API `int Py_FinalizeEx()` | documented | [C API init, 3.13](https://docs.python.org/3.13/c-api/init.html#Py_FinalizeEx) |
| LG-PY-002 `signal.signal` | `signal.signal(signalnum, handler) -> handler` | documented | [signal docs](https://docs.python.org/3/library/signal.html#signal.signal) |
| LG-PY-002 `signal.alarm` / `setitimer` | `alarm(time) -> int` / `setitimer(which, seconds, interval=0)` | documented | [signal docs](https://docs.python.org/3/library/signal.html#signal.setitimer) |
| LG-PY-002 `getsignal` / `raise_signal` | `getsignal(signalnum)` / `raise_signal(signum)` (3.8+) | documented | [signal docs](https://docs.python.org/3/library/signal.html#signal.raise_signal) |
| LG-PY-002 `set_wakeup_fd` | `set_wakeup_fd(fd, *, warn_on_full_buffer=True)` | documented | [signal docs](https://docs.python.org/3/library/signal.html#signal.set_wakeup_fd) |
| LG-PY-002 `pthread_sigmask` / `pthread_kill` / `sigpending` / `sigwait` | verified signatures in §2 | documented | [signal docs](https://docs.python.org/3/library/signal.html#signal.pthread_sigmask) |
| LG-PY-002 PEP 475 EINTR auto-retry | — | documented | [PEP 475](https://peps.python.org/pep-0475/) |
| LG-PY-002 `faulthandler` | `faulthandler.enable()` / `disable()` | documented | [faulthandler docs](https://docs.python.org/3/library/faulthandler.html) |
| LG-PY-003 lifecycle/termination paths | (§1.6, §3) | documented | as LG-PY-001 |
| LG-PY-004 signal model, threads, SIGINT→130 | — | documented (130 re-raise = CPython implementation, verified in source; marked as such) | [signal docs](https://docs.python.org/3/library/signal.html); CPython 3.13 `Modules/main.c::exit_sigint` |
| LG-PY-005 `subprocess.run` | verified full signature (§2) | documented | [subprocess docs](https://docs.python.org/3/library/subprocess.html#subprocess.run) |
| LG-PY-005 `subprocess.Popen` | verified full signature (§2) | documented | [subprocess docs](https://docs.python.org/3/library/subprocess.html#subprocess.Popen) |
| LG-PY-005 `Popen.wait/communicate/poll/send_signal/terminate/kill` | verified (§5.2) incl. deadlock warnings | documented | [subprocess docs](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.wait) |
| LG-PY-005 returncode −N rule | "A negative value -N indicates that the child was terminated by signal N (POSIX only)." | documented | [subprocess docs](https://docs.python.org/3/library/subprocess.html#subprocess.CompletedProcess.returncode) |
| LG-PY-005 Security Considerations (shell=True) | quoted §5.4 | documented | [subprocess docs](https://docs.python.org/3/library/subprocess.html#security-considerations) |
| LG-PY-005 `asyncio.create_subprocess_exec/shell` | verified signatures (§5.5) | documented | [asyncio-subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) |
| LG-PY-005 `multiprocessing.Process.terminate/kill/join/exitcode` | verified (§5.5) | documented | [multiprocessing docs](https://docs.python.org/3/library/multiprocessing.html) |
| LG-PY-005 `os.fork/execv*/system/waitpid/kill/killpg/setsid/getpgrp` + W-constants | verified signatures (§2) | documented | [os docs](https://docs.python.org/3/library/os.html#os.waitpid) |
| LG-PY-006 concurrency/fd/buffering semantics | (§6) | documented | as above |
| Devguide "interpreter internals" page (Py_Finalize walkthrough) | — | source-limited | devguide.python.org internals page unreachable at retrieval; C-API 3.13 page used instead |

**Counts:** inventoried 26 rows; documented 25; remaining 0; source-limited 1 (devguide internals walkthrough — replaced by the C-API manual; no API left undocumented).

## Related Topics

- [Java](../java.md) — shutdown hooks vs Python `atexit`; `Process.waitFor` exit codes vs `returncode` −N.
- [Node.js](../nodejs.md) — event-loop drain vs interpreter finalization; `child_process` `(code, signal)` vs Python's −N.
- [OCaml](../ocaml.md) — `at_exit` LIFO vs Python `atexit`; `Unix.process_status` vs `os.WIFEXITED`.
- [Signals overview](../signals/index.md) — kernel-level semantics Python's `signal` module wraps.
- [Exit status conventions](../exit-status/index.md) — where 0–127, 128+N, and 120 fit system-wide.
- [Interface ledger](../interfaces/index.md) — the syscall layer underneath `subprocess`.

## References

1. *sys — System-specific parameters and functions*, Python 3.13/3.14/3.15 docs, docs.python.org/3/library/sys.html (retrieved 2026-10).
2. *Built-in Exceptions — SystemExit*, Python 3 docs, docs.python.org/3/library/exceptions.html (retrieved 2026-10).
3. *os — Miscellaneous operating system interfaces*, Python 3 docs, docs.python.org/3/library/os.html (retrieved 2026-10).
4. *atexit — Exit handlers*, Python 3 docs, docs.python.org/3/library/atexit.html (retrieved 2026-10).
5. *signal — Set handlers for asynchronous events*, Python 3 docs, docs.python.org/3/library/signal.html (retrieved 2026-10).
6. *subprocess — Subprocess management*, Python 3 docs, docs.python.org/3/library/subprocess.html (retrieved 2026-10).
7. *PEP 475 — Retry system calls failing with EINTR*, Finlai/Brandl et al., peps.python.org/pep-0475 (retrieved 2026-10).
8. *faulthandler — Dump the Python traceback*, Python 3 docs, docs.python.org/3/library/faulthandler.html (retrieved 2026-10).
9. *asyncio — Subprocess*, Python 3 docs, docs.python.org/3/library/asyncio-subprocess.html (retrieved 2026-10).
10. *multiprocessing — Process-based parallelism*, Python 3 docs, docs.python.org/3/library/multiprocessing.html (retrieved 2026-10).
11. *Initialization, Finalization, and Threads (Py_FinalizeEx)*, Python 3.13 C API manual, docs.python.org/3.13/c-api/init.html (retrieved 2026-10).
12. CPython 3.13 source, `Modules/main.c` (`exit_sigint`) and `Python/pythonrun.c` (`handle_system_exit`), github.com/python/cpython at tag v3.13.0 (retrieved 2026-10).
