# Python: Language Semantics, Standard Library, Process APIs, and Subprocesses

Python is the case study of a **runtime-mediated process model**: the language
specification barely mentions processes at all, and nearly everything this
chapter covers — exit status, signal delivery, child processes, file
descriptor ownership — is defined by the **CPython implementation** sitting
between Python code and the kernel. That makes the layer discipline used
throughout this part especially important here. Every claim below is labeled
with its layer: **[language]** (the Python reference and library
specification), **[CPython]** (the reference interpreter's documented
implementation behavior), **[POSIX]** / **[Linux]** (the OS substrate), and
**[Windows delta]** where the platform behaves differently.

**Declared scope** (all sources retrieved 2026-10-13):

- **CPython 3.15.0**, the current stable release per
  [python.org/downloads](https://www.python.org/downloads/) ("Download
  Python 3.15.0") — `docs.python.org/3` serves the 3.15.0 documentation and
  every signature below was verified against it. The previous feature line
  (3.14.8 per `docs.python.org/3.14/`) is the fallback version where a
  versionchanged note matters. CPython-specific claims cite
  docs.python.org and, where a numeric fact lives only in the source, the
  CPython source tree at [github.com/python/cpython](https://github.com/python/cpython)
  (`Python/pylifecycle.c`, `Lib/subprocess.py`, `Lib/threading.py`).
- **PEPs as normative references** for cross-cutting semantics:
  [PEP 475](https://peps.python.org/pep-0475/) (EINTR retry),
  [PEP 446](https://peps.python.org/pep-0446/) (non-inheritable fds),
  [PEP 442](https://peps.python.org/pep-0442/) (safe object finalization).
- **Platform**: Linux as primary target; POSIX deltas labeled where CPython's
  availability markers differ; Windows deltas named briefly where behavior
  diverges (they are large for signals and process creation).
- Python has **no ISO-C-style undefined-behavior catalog**: the language
  reference defines nearly all observable semantics. The genuinely
  unspecified areas that remain (§1.7) are implementation-defined by
  *silence*, and the two big ones — `__del__` timing and the memory model —
  are CPython implementation facts, not language guarantees.

The exit-status/signal slice of Python — `sys.exit` mechanics, the `128+N`
convention, Ctrl-C → exit 130 — already has a dedicated chapter in the Linux
part: [../../linux/process-exit-signal/languages/python.md](../../linux/process-exit-signal/languages/python.md).
That chapter is the status-and-signal *decoder ring*; this chapter is the
full language/runtime documentation project and supersedes none of it —
where both cover the same ground they agree. Sibling Section-G chapters:
[./c.md](./c.md) (C is also CPython's substrate — every CPython claim about
`fork`/`exec`/signals below ultimately routes through it), [./cpp.md](./cpp.md),
[./nodejs.md](./nodejs.md) (the other VM-mediated runtime in this part). Part
hub: [./index.md](./index.md). Interview-topic companions:
[../python/gil.md](../python/gil.md) (GIL mechanics — §6.1 here leans on it),
[../python/asyncio.md](../python/asyncio.md),
[../python/free-threaded.md](../python/free-threaded.md) (the GIL-free
build changes several §4/§6 claims; noted inline where it does).

---

## 1. Syntax and Semantics

### 1.1 Names, objects, and evaluation order

**[language]** The reference model is name→object binding: "Names refer to
objects. Names are introduced by name binding operations" (reference
§4.2.1). A variable is a slot in a namespace holding a reference; assignment
never copies the object, it rebinds the name. Consequences that matter for
process semantics: passing a file descriptor *number*, a `Popen` object, or
a `Thread` object to a child or another module shares the *object*, and the
object's `__del__` may run wherever the last reference dies — not where the
creator's scope ends.

**Evaluation order** is fully specified — no C-style unsequenced UB:
"Python evaluates expressions from left to right. Notice that while
evaluating an assignment, the right-hand side is evaluated before the
left-hand side" (reference §6.16). So in `f() or g()`, `f()` runs first, and
in `a = f()` the call `f()` happens before `a` is rebound. Short-circuit
`and`/`or` and the conditional expression are the only operations that
skip evaluation of an operand. There is no equivalent of C's sequence-point
violations; the closest thing is that a mutating expression evaluated inside
its own right-hand side is *specified* (e.g. `a, a[:] = a, []`), not
undefined.

```python
# Expected: "R" printed before "L"; b is the original list object.
def r(): print("R"); return [1]
def l(): print("L")
a = r() if False else r()   # RHS (r()) evaluated, then bound to a
b = a; a.append(2)          # b and a are the same object: b == [1, 2]
```

### 1.2 Scopes and name resolution (the "LEGB" order)

**[language]** Name resolution is defined as: "When a name is used in a code
block, it is resolved using the nearest enclosing scope" (reference
§4.2.2). Concretely the lookup walks: local (function) scope → enclosing
function scopes (only if the name is not local but is captured) → module
global scope → builtins; a miss raises `NameError`, and using a function
local before binding raises `UnboundLocalError` (a `NameError` subclass)
because "the local variables of a code block can be determined by scanning
the entire text of the block for name binding operations" — binding is
block-static, not flow-sensitive. `global` / `nonlocal` re-target the
binding. Resolution happens at runtime for free variables, so a module-level
name rebound later is seen by functions called later — this is exactly the
mechanism that makes module-global *state* (locks, `Popen` registries like
`subprocess._active`) shared process-wide, and exactly the mechanism that
breaks during interpreter shutdown when module globals are torn down
(§3.7).

```python
x = "global"
def outer():
    x = "enclosing"
    def inner():
        return x          # nearest enclosing scope: "enclosing"
    return inner()
# Expected: "enclosing" — global "x" is shadowed, never consulted.
```

### 1.3 Object lifetime: refcounting, cycle GC, and PEP 442 finalization

**[CPython]** (implementation-defined; other interpreters may differ)
CPython destroys an object at a deterministic point: when its reference
count reaches zero, `__del__` runs immediately, synchronously, on the
thread that dropped the last reference. Reference cycles defeat
refcounting, so a generational **cycle collector** (the `gc` module)
periodically finds unreachable groups; since
[PEP 442](https://peps.python.org/pep-0442/) (Python 3.4) it finalizes
cycle members safely — `__del__` methods are called once, objects that
become reachable again during finalization are revived, and `gc.garbage`
is empty by default instead of accumulating uncollectable objects. `__del__`
is invoked at most once per object (data-model guarantee), and calling it
again is suppressed.

**[language]** What the *specification* guarantees is much weaker: `__del__`
is not guaranteed to run at any particular time, and — load-bearing for this
chapter — "It is not guaranteed that `__del__()` methods are called for
objects that still exist when the interpreter exits" (data model §3.1.13).
CPython does attempt a final collection at shutdown, but cleanup must never
depend on it: explicit `close()`, context managers (§1.5), and
`try/finally` are the guarantees; `__del__` is a backstop. `weakref`
callbacks, `os.register_at_fork` hooks, and `atexit` are the other
lifetime-anchored hooks §5–§6 build on.

### 1.4 Exceptions: the `BaseException` split

**[language]** All exceptions inherit from `BaseException`, but user code
is specified to catch `Exception` (reference & `exceptions` library docs).
Direct children of `BaseException`: `SystemExit`, `KeyboardInterrupt`,
`GeneratorExit`, and the rest of `Exception` below. This split *is* the
process-semantics design: `sys.exit()` works by raising `SystemExit`, so a
broad `except Exception:` cannot accidentally swallow an exit request or a
Ctrl-C — both propagate past it. Catching `BaseException` is how one *does*
observe them (and must usually re-raise; §3.3).

```python
import sys
try:
    sys.exit(3)
except Exception:
    print("never printed")     # SystemExit is not an Exception
finally:
    print("finally always runs")
# Expected: "finally always runs", then exit status 3.
```

### 1.5 `try/except/else/finally` and context managers

**[language]** The `try` statement composes: `except` clauses match the
first matching class in MRO order; `else` runs only if no exception was
raised in the `try` body; `finally` runs on *every* exit path — normal,
exception, `return`/`break`/`continue`, and `SystemExit` — and an exception
(or return value) raised *in* `finally` replaces the in-flight one, which is
the standard way cleanup code masks the real error. Chained context:
the replaced exception is preserved as `__context__` (§1.6).

**Context managers** (`with`) are the idiomatic RAII: an object with
`__enter__`/`__exit__`; on exception, `__exit__(exc_type, exc, tb)` is
called with the exception triple and *suppresses the exception if it
returns true*, otherwise it propagates. `with` guarantees `__exit__` on
every path out of the block, including `return` and `SystemExit` — which is
why `subprocess.Popen` as a context manager (§5.9) and `open()` are the
correct resource patterns, and `__del__` is not.

```python
class Guard:
    def __enter__(self): print("enter"); return self
    def __exit__(self, t, v, tb):
        print("exit", t is None)
        return False  # do not suppress
with Guard():
    import sys; sys.exit(0)
# Expected: "enter" then "exit False" — SystemExit passes through __exit__
# (return value False), then the interpreter exits 0.
```

### 1.6 Exception chaining: `__context__`, `__cause__`, `__traceback__`

**[language]** When a new exception is raised while another is being
handled, "the new exception's `__context__` attribute is automatically set
to the handled exception" (exceptions docs); `raise X from Y` sets
`__cause__` explicitly and `__suppress_context__ = True`. The default
traceback printer renders both chains ("During handling of the above
exception, another exception occurred" / direct cause form). Every
exception carries `__traceback__` — the frame chain — which is what makes
`traceback.print_exc()`, logging `exc_info=True`, and post-mortem
re-raising at process boundaries (a worker catching, serializing, and
re-raising in the parent) lossless. Cleanup written in `finally` and in
`__exit__` must therefore *not* raise casually: a raise there chains and
prints, but the original exception is superseded.

```python
try:
    1 / 0
except ZeroDivisionError:
    raise ValueError("cleanup failed")   # implicit chaining
# Expected traceback ends with:  "During handling of the above exception,
#  another exception occurred:"  then the ValueError.
# Explicit form:  raise ValueError("cleanup failed") from zero_div  →
#   "The above exception was the direct cause ..."
```

### 1.7 Generators, coroutines, and cleanup (`close()`, `GeneratorExit`, `aclose()`)

**[language]** A generator paused at a `yield` holds live frames, open
resources, and `try/finally` state, so GC or explicit teardown must unwind
it. `gen.close()` raises `GeneratorExit` *at the suspension point*; a
well-behaved generator's `finally` blocks run, and the generator must not
yield again (a second yield raises `RuntimeError: generator ignored
GeneratorExit`). Async coroutines are symmetric: `aclose()` awaits
`GeneratorExit` inside the coroutine, and an *unawaited* coroutine that is
garbage-collected produces a "coroutine was never awaited" warning — the
async analogue of a resource leak. Process relevance: a worker generator
holding a `Popen` or a pipe should either be used as a context manager
itself or be closed explicitly on error paths; relying on cycle-GC timing
to run the generator's `finally` (§1.3) is what makes child processes
appear to "leak" non-deterministically.

```python
def worker():
    try:
        while True:
            yield "tick"
    finally:
        print("worker cleaned up")
g = worker(); next(g)
g.close()          # Expected: "worker cleaned up" (GeneratorExit → finally)
```

### 1.8 Normal vs exceptional termination

**[language]** Python has no panics and no `abort()` keyword; termination
vocabulary is:

| Path | Mechanism | Visible result |
|---|---|---|
| Script ends / `main` returns | falling off the main module | interpreter shutdown (§3.7), status 0 |
| Explicit exit | `sys.exit(arg)` raises `SystemExit` | same shutdown, status = arg mapping (§3.2) |
| Uncaught exception | exception reaches top level | traceback to stderr, **status 1** |
| Uncaught `SystemExit` | not handled anywhere | **no traceback**, status = arg |
| Raw OS exit | `os._exit(n)` / `os.abort()` | no shutdown at all (§3.5–§3.6) |

### 1.9 In-scope undefined / implementation-defined areas

Python's reference manual defines essentially all observable semantics, so
this is a *silence* list rather than a UB catalog:

- **`__del__` timing** — unspecified when (or whether) finalizers run
  (§1.3). [language-silent, CPython-defined].
- **Memory model** — the reference does not define an execution/memory
  model at all; atomicity of attribute assignment, the visibility of
  mutations across threads, and the effect of the GIL are CPython
  implementation facts (§6.1), not language guarantees.
  [../python/gil.md](../python/gil.md).
- **String interning** — small-string/identifier interning is unspecified;
  `sys.intern()` is the only specified way to request it. Affects only
  identity checks (`is` on strings), never equality.
- **Signal delivery interleaving** — *between which two bytecodes* a
  pending Python signal handler runs is unspecified (§4.1); only the
  thread (main) and the coarse timing model are specified.
- **Destruction order at shutdown** — module teardown order and which
  globals remain importable inside `__del__` (§3.9).

### 1.10 Version deltas 3.9 → 3.15 affecting in-scope semantics

- **3.9** — `Popen(..., group=, user=, extra_groups=, umask=)` added
  (POSIX child credential/permission setup pre-exec).
- **3.11** — `Popen(process_group=)` added (setpgid(0, value) pre-exec);
  exception groups (`except*`) added — relevant to cleanup code that runs
  multiple sub-closings and must not lose any error.
- **3.12** — `os.fork()` in a multi-threaded process raises
  `DeprecationWarning` when detectable (§6.2); subinterpreter restriction:
  `os.fork()` and `preexec_fn` raise `RuntimeError` (3.12 formalized what
  3.8 introduced for `fork` in subinterpreters).
- **3.15** — `Popen.wait(timeout=...)` uses an efficient event-driven
  mechanism on Linux ≥ 5.3 (`os.pidfd_open` + `select.poll`) and macOS/BSD
  instead of a poll-sleep loop (docs versionchanged).
- Free-threaded build note: the GIL-free build (optional since 3.13) makes
  §4.1's "handlers run between bytecodes" and §6.1's memory-model claims
  build-dependent rather than universal — see
  [../python/free-threaded.md](../python/free-threaded.md).

### 1.11 Misconceptions

- "`sys.exit()` is a hard exit" — it raises a catchable `SystemExit`
  (§3.3); `except BaseException:` will intercept it, `finally` runs, and
  `os._exit()` is the hard exit.
- "GC frees deterministically" — only refcount dropping the last reference
  is deterministic, and only in CPython; cycles, freelists, and interpreter
  shutdown make `__del__` timing non-deterministic in general (§1.3).
- "`finally` won't run if the process is exiting" — it runs for
  `SystemExit` and exceptions; it does *not* run under `os._exit()`, and
  daemon threads are stopped without running `finally` (§6.5).
- "`shell=False` still needs escaping" — the opposite: "this library will
  not implicitly choose to call a system shell … all characters, including
  shell metacharacters, can safely be passed to child processes"
  (subprocess docs); injection enters via `shell=True` (§5.11).
- "The child's `returncode` is always the child's exit code" — on POSIX a
  **negative** value `-N` means the child was killed by signal *N*
  (§5.8).

---

## 2. Standard-Library and Runtime API Inventory

All signatures below were verified verbatim against docs.python.org/3
(CPython 3.15.0 docs, retrieved 2026-10-13); version annotations are the
docs' own `Added/Changed in version` notes. Availability markers
(`Availability: Unix`, etc.) are quoted as the docs state them. Ownership
column states who closes/flushes what.

### 2.1 `sys` and `os` — termination primitives

| API | Canonical signature (verified) | Semantics / side effects / ownership | Reference |
|---|---|---|---|
| `sys.exit` | `sys.exit(arg=0)` — raises `SystemExit` | Signals intent to exit; int → status (0 = success); `None` → 0; any other object → printed to **stderr**, status 1. Catchable; cleanup honored. | [sys](https://docs.python.org/3/library/sys.html#sys.exit) |
| `SystemExit` | `SystemExit(code=0)` (exc class; `.code` attribute) | Inherits `BaseException`, not `Exception`. Unhandled → interpreter exits, **no traceback**. | [exceptions](https://docs.python.org/3/library/exceptions.html#SystemExit) |
| `os._exit` | `os._exit(n, /)` — `None` | "Exit the process with status n, without calling cleanup handlers, flushing stdio buffers, etc." Docs: normally only used in the child after `fork()`. | [os](https://docs.python.org/3/library/os.html#os._exit) |
| `os.abort` | `os.abort()` — `None` | "Generate a SIGABRT signal to the current process." Unix: default → core dump; Windows: exit code 3. **Does not call** a Python SIGABRT handler. | [os](https://docs.python.org/3/library/os.html#os.abort) |
| `atexit.register` | `atexit.register(func, *args, **kwargs)` — returns *func* (decorator-usable) | Registers normal-termination handler; handlers run at interpreter shutdown in **reverse** (LIFO) order; same func may be registered repeatedly. | [atexit](https://docs.python.org/3/library/atexit.html#atexit.register) |
| `atexit.unregister` | `atexit.unregister(func)` — `None` | Removes *all* registrations of *func* (uses `==`); silently no-op if absent. Registering/unregistering from within a running handler is documented undefined. | [atexit](https://docs.python.org/3/library/atexit.html#atexit.unregister) |

### 2.2 `signal` — registration and delivery control

| API | Canonical signature (verified) | Semantics / notes | Reference |
|---|---|---|---|
| `signal.signal` | `signal.signal(signalnum, handler)` → previous handler | Handler is a 2-arg callable (signum, frame) or `SIG_IGN`/`SIG_DFL`. "When threads are enabled, this function can only be called from the main thread of the main interpreter" else `ValueError`. Windows: only `SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGBREAK`. | [signal](https://docs.python.org/3/library/signal.html#signal.signal) |
| `signal.getsignal` | `signal.getsignal(signalnum)` → handler | Returns the callable, `SIG_IGN`, `SIG_DFL`, or `None` ("not installed from Python"). | [signal](https://docs.python.org/3/library/signal.html#signal.getsignal) |
| `signal.set_wakeup_fd` | `signal.set_wakeup_fd(fd, *, warn_on_full_buffer=True)` → old fd | On each caught signal, signal number written as **one byte** to fd; fd must be non-blocking; `-1` disables; main-thread-only. The signal→event-loop bridge (§4.4). | [signal](https://docs.python.org/3/library/signal.html#signal.set_wakeup_fd) |
| `signal.pthread_sigmask` | `signal.pthread_sigmask(how, mask)` → old mask set | Fetch/alter the *calling thread's* signal mask; `how` ∈ `SIG_BLOCK`, `SIG_UNBLOCK`, `SIG_SETMASK`. `Availability: Unix`. | [signal](https://docs.python.org/3/library/signal.html#signal.pthread_sigmask) |
| `signal.sigpending` | `signal.sigpending()` → set | Signals pending for delivery to the calling thread. `Availability: Unix`. | [signal](https://docs.python.org/3/library/signal.html#signal.sigpending) |
| `signal.sigwait` | `signal.sigwait(sigset)` → signum | Synchronously accept one pending signal (removes from pending). The dedicated-signal-thread primitive. `Availability: Unix`. | [signal](https://docs.python.org/3/library/signal.html#signal.sigwait) |
| `signal.raise_signal` | `signal.raise_signal(signum)` — `None` | Sends a signal to the calling process (3.8+). | [signal](https://docs.python.org/3/library/signal.html#signal.raise_signal) |
| `signal.valid_signals` | `signal.valid_signals()` → set | Valid signal numbers on this platform (3.8+); alongside constants `SIG_DFL`, `SIG_IGN`, `SIGINT`, `SIGTERM`, `SIGKILL`, `SIGCHLD`, … | [signal](https://docs.python.org/3/library/signal.html#signal.valid_signals) |

### 2.3 `subprocess` — the sanctioned child-process API

| API | Canonical signature (verified) | Semantics / notes | Reference |
|---|---|---|---|
| `subprocess.Popen` | `subprocess.Popen(args, bufsize=-1, executable=None, stdin=None, stdout=None, stderr=None, preexec_fn=None, close_fds=True, shell=False, cwd=None, env=None, universal_newlines=None, startupinfo=None, creationflags=0, restore_signals=True, start_new_session=False, pass_fds=(), *, group=None, extra_groups=None, user=None, umask=-1, encoding=None, errors=None, text=None, pipesize=-1, process_group=None)` | Execvpe-like on POSIX, `CreateProcess` on Windows. Full parameter semantics in §5.1. No `env_merge` parameter exists — `env` (a complete mapping) is the only environment argument; to extend, copy `os.environ` and update. | [subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.Popen) |
| `subprocess.run` | `subprocess.run(args, *, stdin=None, input=None, stdout=None, stderr=None, capture_output=False, shell=False, cwd=None, timeout=None, check=False, encoding=None, errors=None, text=None, env=None, universal_newlines=None, **other_popen_kwargs)` → `CompletedProcess` | High-level one-shot; `timeout`/`input`/`check`/`capture_output` are *not* passed through. Timeout → child killed and waited for, then `TimeoutExpired` re-raised (§5.10). | [subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.run) |
| `CompletedProcess` | `CompletedProcess(args, returncode, stdout=None, stderr=None)` | Result record of `run()`: `.args`, `.returncode`, `.stdout`, `.stderr` (populated only when captured). `.check_returncode()` raises `CalledProcessError` on non-zero. | [subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.CompletedProcess) |
| `subprocess.call` | `subprocess.call(args, *, stdin=None, stdout=None, stderr=None, shell=False, cwd=None, timeout=None, **other_popen_kwargs)` → int returncode | Legacy: `run(...).returncode` without capture. | [subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.call) |
| `subprocess.check_call` | `subprocess.check_call(args, *, stdin=None, stdout=None, stderr=None, shell=False, cwd=None, timeout=None, **other_popen_kwargs)` — `None` | Legacy: raises `CalledProcessError` on non-zero. | [subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.check_call) |
| `subprocess.check_output` | `subprocess.check_output(args, *, stdin=None, stderr=None, shell=False, cwd=None, encoding=None, errors=None, universal_newlines=None, timeout=None, text=None, **other_popen_kwargs)` → bytes/str | Legacy: capture stdout, raise `CalledProcessError` (with `.output`) on non-zero. | [subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.check_output) |
| Exception family | `SubprocessError` ← `SubprocessError` subclasses `CalledProcessError`, `TimeoutExpired` | All module exceptions inherit `SubprocessError` (3.3+). `TimeoutExpired` carries `.cmd`, `.timeout`, and post-capture `.stdout/.stderr` partial output. | [subprocess](https://docs.python.org/3/library/subprocess.html#exceptions) |
| Constants | `subprocess.PIPE`, `subprocess.DEVNULL`, `subprocess.STDOUT` | Special values for `stdin/stdout/stderr`: pipe, null device, and "same as stdout" (merging stderr into stdout). | [subprocess](https://docs.python.org/3/library/subprocess.html#subprocess.PIPE) |

### 2.4 `asyncio` and `multiprocessing` (brief, verified)

| API | Canonical signature (verified) | Semantics / notes | Reference |
|---|---|---|---|
| `asyncio.create_subprocess_exec` | `asyncio.create_subprocess_exec(program, *args, stdin=None, stdout=None, stderr=None, limit=65536, **kwds)` → coroutine → `asyncio.subprocess.Process` | Argument-array child with an event-loop-integrated `Process` wrapper (§5.13); `limit` bounds StreamReader buffers. | [asyncio-subprocess](https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.create_subprocess_exec) |
| `asyncio.create_subprocess_shell` | `asyncio.create_subprocess_shell(cmd, stdin=None, stdout=None, stderr=None, limit=65536, **kwds)` → coroutine → `Process` | Same but through the shell — same injection surface as `shell=True` (§5.11). | [asyncio-subprocess](https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.create_subprocess_shell) |
| `multiprocessing.Process` | `multiprocessing.Process(group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None)` | Separate *interpreter* via OS process; `.daemon` (default inherited), `.exitcode` (`None` while running; negative = killed by signal), `.join()`. Start methods (`fork`/`spawn`/`forkserver`) change semantics — see §5.14. | [multiprocessing](https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Process) |

---

## 3. Process Creation and Termination

### 3.1 The four termination doors

A CPython process terminates through exactly one of: normal completion of
the main module, an uncaught exception, an explicit raw OS call
(`os._exit`/`os.abort`), or an external signal the runtime does not
intercept. `sys.exit()` is *not* a separate door — it is the second one
wearing a coat. **[CPython]** the interpreter catches `SystemExit` at top
level, runs the shutdown sequence, and calls C `exit(sts)`.

### 3.2 `sys.exit(arg)` argument mapping — verified text

**[language]** From the sys docs (retrieved 2026-10-13): "The optional
argument arg can be an integer giving the exit status (defaulting to zero),
or another type of object. If it is an integer, zero is considered
'successful termination' … Most systems require it to be in the range
0–127, and produce undefined results otherwise. … If another type of object
is passed, None is equivalent to passing zero, and any other object is
printed to stderr and results in an exit code of 1."

```python
import sys
sys.exit(7)            # shell sees 7
sys.exit("bad input")  # "bad input" on stderr, exit status 1
sys.exit(None)         # exit status 0
```

**[POSIX/Linux]** the status byte a shell observes is the low 8 bits of the
value passed to C `exit()` — an `int` argument is truncated mod 256 by the
*OS*, not by Python (exit codes ≥ 256 wrap: `sys.exit(256)` looks like 0 to
the parent). Full decoding table incl. the `128+N` convention:
[../../linux/process-exit-signal/languages/python.md](../../linux/process-exit-signal/languages/python.md).

### 3.3 `SystemExit` propagation and re-raise

**[language]** `SystemExit` propagates like any exception: it runs `finally`
blocks and context-manager `__exit__` calls on the way out; `except
BaseException:` can catch it, and *re-raising* (`bare raise` or `raise`)
resumes the exit — the interpreter's top-level handler is what turns the
(un)caught `SystemExit` into a status. A handler that catches `SystemExit`
and does not re-raise effectively cancels the exit request. In a non-main
thread the semantics change completely: `sys.exit()` raises `SystemExit` in
*that thread only* — the docs state "it will only exit the process when
called from the main thread, and the exception is not intercepted" (§3.8).

### 3.4 Uncaught exception → traceback, status 1

**[language/CPython]** An uncaught exception (other than `SystemExit`) is
printed by the interpreter as a traceback to stderr and the process exits
with status 1. No `atexit` skipping, no flush skipping — the normal
shutdown sequence (§3.7) still runs. `KeyboardInterrupt` behaves the same
way (traceback, status 1) *unless* the parent decodes it as SIGINT via the
`128+N` convention — which happens only when the process dies *from* the
signal, not from Python raising (see the Linux-part chapter for the
distinction).

### 3.5 `os._exit(n)`: the raw door

**[language/POSIX]** "Exit the process with status n, without calling
cleanup handlers, flushing stdio buffers, etc." — no `atexit`, no
`threading._shutdown`, no stdio flush, no module teardown, no
`__del__`. Data still in userspace buffers (Python file objects *and* the
C stdio layer) is lost. The docs' stated use case is the `fork()` child:
after fork, the child should exec or `_exit` — never return through the
parent's normal path (which would run the parent's cleanup twice; §6.3).

### 3.6 `os.abort()`: SIGABRT to self

**[CPython/POSIX]** "Generate a SIGABRT signal to the current process" —
on Unix the default SIGABRT action kills with a core-dump disposition; the
parent's shell sees signal 6 semantics. Critically, "calling this function
will not call the Python signal handler registered for SIGABRT" — it
bypasses the Python handler machinery entirely, and therefore also skips
the entire Python shutdown sequence. Exit status at the shell:
`128+SIGABRT(6)` = 134 with the usual core/`WCOREDUMP` caveat.

### 3.7 Interpreter shutdown sequence (`Py_FinalizeEx`)

**[CPython]** (verified against `Python/pylifecycle.c` and the module
docs) For the main interpreter, after the main script ends (including an
uncaught-exception traceback and the top-level `SystemExit` handling):

1. `wait_for_thread_shutdown()` — calls `threading._shutdown()`
   (`Lib/threading.py`: "Wait until the Python thread state of all
   non-daemon threads get deleted"), i.e. **join all non-daemon threads
   first**.
2. Pending calls are flushed, then `_PyAtExit_Call()` runs **`atexit`
   handlers in LIFO order** (C and Python registrations). The CPython
   source wraps steps 1–2 in a loop "until none of them run anything"
   (finalization callbacks may create threads or handlers may re-register).
3. Module teardown: the interpreter clears modules and runs a final
   GC collection; `__del__` finalizers may run here (PEP 442 semantics,
   §1.3), under the weakened environment of §3.9.
4. **stdio flush**: `sys.stdout`/`sys.stderr` are flushed. The sys docs
   state the numeric fact: "If an error occurs in the cleanup after the
   Python interpreter has caught SystemExit (such as an error flushing
   buffered data in the standard streams), the exit status is changed to
   **120**" — matched in the source (`pylifecycle.c`: `_Py_Finalize() < 0`
   → `sts = 120; exit(sts);`).
5. `exit(sts)` — one C-level exit for the whole process.

**[CPython]** Daemon threads are *not* joined — they are killed abruptly
wherever they are (§6.5). For subinterpreters, `atexit` handlers are per
interpreter: "each interpreter has its own stack of exit handlers, which
are executed when the interpreter shuts down" (atexit docs, 3.12+
multi-interpreter wording).

### 3.8 Current process vs thread vs child

**[language]** `sys.exit()` raises in the calling thread; only the *main*
thread's `SystemExit` reaches the interpreter's exit path. `threading.
Thread(target=sys.exit)` silently terminates just that thread (the
exception is swallowed by the thread machinery). A child process created
via `fork`/`multiprocessing`/`subprocess` shares nothing of this: its exit
status is a wait-status the parent must reap (§5.7), and the child's
`sys.exit(int)` is the parent's `CompletedProcess.returncode`. **[POSIX]**
`os.fork()` gives the child a copy of the entire Python runtime state —
which is precisely why forking a threaded CPython is hazardous (§6.2).

### 3.9 Module teardown and globals during `__del__`

**[language]** Data model, verbatim: "`__del__()` can be executed during
interpreter shutdown. As a consequence, the global variables it needs to
access (including other modules) may already have been deleted or set to
None. Python guarantees that globals whose name begins with a single
underscore are deleted from their module before other globals are
deleted". Historically (pre-3.4) *all* module globals were forcibly set to
None at shutdown; current CPython tears down module dicts at finalization
and makes no ordering promise beyond the underscore rule. Practical rule:
shutdown-time finalizers must not import, must not rely on module-level
objects, and should catch their own exceptions (an exception escaping
`__del__` is printed as "Exception ignored in:" and never changes the exit
status).

### 3.10 `atexit`: exact current behavior — verified text

**[language]** atexit docs (retrieved 2026-10-13), verbatim key points:

- "At exit, all registered exit handlers are called in the reverse order
  in which they were registered. If you register A, B, and C, at
  interpreter shutdown time they will be run in the order C, B, A."
- "If an exception is raised during execution of an exit handler, a
  traceback is printed (unless SystemExit is raised) and the exception
  information is saved. After all exit handlers have had a chance to run,
  the last exception to be raised is re-raised." — so **one failing handler
  does not stop later handlers**; exceptions are accumulated and the last
  one re-raised at the end (which then becomes an uncaught exception →
  traceback, status 1, after the normal sequence).
- "The effect of registering or unregistering functions from within a
  cleanup function is undefined."
- Handlers may run arbitrary Python code after yours — a handler must not
  assume it is the last to run.

```python
import atexit, sys
def a(): print("A")
def b(): print("B"); raise RuntimeError("boom")
def c(): print("C")
for f in (a, b, c): atexit.register(f)
# Expected on exit: C, B (traceback printed), A — then the RuntimeError
# re-raised at the very end → traceback + exit status 1.
```

---

## 4. Signals and OS Interaction

### 4.1 The CPython delivery model: flag now, Python later

**[CPython]** (implementation model, clearly documented) "A Python signal
handler does not get executed inside the low-level (C) signal handler.
Instead, the low-level signal handler sets a flag which tells the virtual
machine to execute the corresponding Python signal handler at a later
point (for example, at the next bytecode instruction)." Consequences,
documented verbatim in the signal docs: catching synchronous SIGFPE/SIGSEGV
from C code is futile (Python returns into the faulting code); "a
long-running calculation implemented purely in C … may run uninterrupted
for an arbitrary amount of time"; and "If the handler raises an exception,
it will be raised 'out of thin air' in the main thread." The in-between
bytecodes are unspecified (§1.9). This model is what makes Python handlers
async-signal-*safe* by construction — the C handler only sets a flag — and
it is GIL-dependent: the main thread must hold or acquire the GIL to run
the Python part ([../python/gil.md](../python/gil.md)).

### 4.2 Defaults and persistence

**[CPython]** "A small number of default handlers are installed: SIGPIPE is
ignored (so write errors on pipes and sockets can be reported as ordinary
Python exceptions) and SIGINT is translated into a KeyboardInterrupt
exception if the parent process has not changed it." Once set, a handler
stays installed — "Python emulates the BSD style interface regardless of
the underlying implementation" (no System-V one-shot reset) — "with the
exception of the handler for SIGCHLD, which follows the underlying
implementation." SIGPIPE-ignored is a real semantic fork from C child
processes and is exactly why `subprocess` restores signals in the child
(§5.5): a Python parent that execs a child without restoring would leave
the child with SIGPIPE ignored, and the child's writes to dead pipes would
return EPIPE errors instead of dying.

### 4.3 Main-thread-only registration and execution

**[language/CPython]** "Python signal handlers are always executed in the
main Python thread of the main interpreter, even if the signal was
received in another thread. This means that signals can't be used as a
means of inter-thread communication." And registration: `signal.signal()`
and `signal.set_wakeup_fd()` raise `ValueError` off the main thread. The
docs add a warning that synchronization primitives (`threading.Lock`)
must not be acquired inside handlers — re-entry deadlock risk since the
handler interrupts an arbitrary bytecode in the main thread.

### 4.4 EINTR and PEP 475: what a signal does to blocking calls

**[CPython, PEP 475]** Since Python 3.5, "system calls failing with EINTR
are retried automatically" (PEP 475 title): the C level retries the
interrupted syscall after running the Python handler, so application code
sees neither `InterruptedError` nor a short read/write. The one visible
semantic is on sleeps — `time.sleep` docs, verbatim: "The function now
sleeps at least seconds even if the sleep is interrupted by a signal,
except if the signal handler raises an exception (see PEP 475 for the
rationale)". So `time.sleep(10)` interrupted at t=2 by a handled SIGCHLD
resumes sleeping to t=10; a `signal.alarm`-based timeout needs the handler
to *raise* to cut the sleep short. Pre-3.5 code catching
`InterruptedError` is obsolete.

### 4.5 `set_wakeup_fd`: the safe handler→loop bridge

**[CPython]** Because Python-level handler bodies cannot run concurrently
with arbitrary main-thread code (§4.1), the documented escape hatch is a
*byte pipe*: `signal.set_wakeup_fd(fd)` makes the C-level handler write
the signal number as one byte to `fd`, which any `poll`/`select`/event
loop can watch. Contract (docs, verified): fd must be **non-blocking**;
"if too many signals arrive too quickly, then the buffer may become full,
and some signals may be lost" — hence `warn_on_full_buffer=True` (3.8+)
emits a warning when bytes are dropped; the caller must drain fd before
the next poll; main-thread-only. This is the mechanism under every
event-loop signal integration (§4.7) — the same role Node.js assigns to
its libuv signal pipe ([./nodejs.md](./nodejs.md)).

### 4.6 Blocking, examining, synchronously waiting: the POSIX trio

**[POSIX via CPython]** `signal.pthread_sigmask(how, mask)` manipulates
the *calling thread's* mask; `signal.sigpending()` reports pending
signals; `signal.sigwait(sigset)` synchronously accepts one. All marked
`Availability: Unix`. The canonical pattern — mask the signal everywhere,
spawn a thread that `sigwait()`s and performs the cleanup — moves all
signal *logic* onto a normal thread with no "out of thin air" exceptions
(§4.1), at the cost of `threading` machinery. `signal.raise_signal(signum)`
(3.8+) sends a signal to the calling process — the specified way to
self-deliver (e.g. re-raising SIGINT after logging, the
"restore-default-then-kill" idiom in the Linux-part chapter).

### 4.7 Handler exceptions and the asyncio integration

**[CPython]** A handler that raises delivers the exception in the main
thread at the next bytecode boundary — including inside `try` blocks the
signal was never aimed at. Standard idiom:

```python
import signal
def handler(signum, frame):
    raise KeyboardInterrupt     # surfaces at a defined-ish point in main
signal.signal(signal.SIGTERM, handler)
```

**[CPython]** `loop.add_signal_handler(signum, callback, *args)` (Unix
event loops) registers a callback "invoked by loop, along with other
queued callbacks and runnable coroutines of that event loop. Unlike
signal handlers registered using signal.signal(), a callback registered
with this function is allowed to interact with the event loop" — it is
implemented over `set_wakeup_fd` (§4.5), is main-loop-scoped (must be
called on the loop's thread, `RuntimeError`/`ValueError` per docs), and
coexists poorly with code that also installs `signal.signal` handlers for
the same signal (last writer wins at the OS level). Uses
`loop.remove_signal_handler` to undo.

### 4.8 Windows deltas (brief)

**[Windows delta]** `signal.signal()` accepts only `SIGABRT, SIGFPE,
SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGBREAK`; delivery is emulated via
console control events, not POSIX signals. `os.kill(pid, sig)` sends
`CTRL_C_EVENT`/`CTRL_BREAK_EVENT` only to console processes sharing a
console (e.g. children started with `creationflags=CREATE_NEW_PROCESS_
GROUP`); "Any other value for sig will cause the process to be
unconditionally killed by the TerminateProcess API". `Popen.send_signal`
maps `SIGTERM → TerminateProcess` (Windows docs note). All §4.4–§4.7
mechanisms (`pthread_sigmask`, `sigwait`, `set_wakeup_fd` except as
implemented for the loop) are Unix-only.

---

## 5. Subprocess and Child-Process Management

### 5.1 `Popen` constructor surface (verified 3.15.0)

The full signature is in §2.3. The parameters that carry process semantics:

- `args` — sequence (recommended) or string. With `shell=True` on POSIX
  the docs specify the equivalent of
  `Popen(['/bin/sh', '-c', args[0], args[1], ...])`; extra sequence items
  become *shell* arguments, not command arguments — a classic
  injection/misparse trap.
- `stdin/stdout/stderr` — `None` (inherit), `PIPE`, `DEVNULL`, an existing
  fd, or a file object. `stderr=subprocess.STDOUT` merges into stdout's
  pipe.
- `bufsize` — passed to `open()` for the pipe file objects: `0`
  unbuffered, `1` line-buffered (text mode only), positive = buffer size,
  negative = `io.DEFAULT_BUFFER_SIZE`.
- `executable` — replacement program while keeping `args[0]` as argv[0].
- `cwd` — child chdir before exec (POSIX: also affects relative-path
  resolution of the executable).
- `env` — complete replacement environment (no partial-merge parameter
  exists; §2.3).
- `text`/`encoding`/`errors` — text-mode pipes (3.7+ alias `text`).
- `preexec_fn`, `close_fds`, `pass_fds`, `restore_signals`,
  `start_new_session`, `process_group`, `group`/`extra_groups`/`user`,
  `umask` — child-side POSIX setup, each detailed below.
- `pipesize` (3.10+) — pipe buffer size hint; `startupinfo`/`creationflags`
  — Windows only.

### 5.2 `preexec_fn`: the documented deadlock hazard

**[CPython/POSIX]** Docs, verbatim: "If preexec_fn is set to a callable
object, this object will be called in the child process just before the
child is executed. (POSIX only)" and "The preexec_fn parameter is NOT SAFE
to use in the presence of threads in your application. The child process
could deadlock before exec is called." The mechanism is the fork-in-
threaded-process hazard (§6.2): the child runs Python code in a runtime
whose locks (allocator, GIL, import lock) may be held by threads that do
not exist in the child. The docs explicitly redirect: "If you need to
modify the environment for the child use the env parameter rather than
doing it in a preexec_fn. The start_new_session and process_group
parameters should take the place of code using preexec_fn to call
os.setsid() or os.setpgid() in the child." Since 3.8/3.12 it also raises
`RuntimeError` in subinterpreters.

### 5.3 fd inheritance: `close_fds`, `pass_fds`, PEP 446

**[CPython/PEP 446]** Since PEP 446 (3.4) all fds CPython creates (pipes,
files, sockets) are **non-inheritable by default**, and `os.pipe()`
documents "The new file descriptor is non-inheritable". `Popen(close_fds
=True)` (the default since 3.2) closes everything except 0/1/2 in the
child pre-exec; `pass_fds` (3.2+) is the opt-in allowlist — "Providing any
pass_fds forces close_fds to be True" — and passing an fd there implies
making it inheritable. `os.get_inheritable(fd)` /
`os.set_inheritable(fd, flag)` are the per-fd controls; `os.dup2(fd, fd2,
inheritable=True)` documents that dup2 results are inheritable by default.
This is why a random open file in the parent does not silently leak into
every child — the POSIX default CPython overrides deliberately
([./c.md](./c.md) §6 for the raw syscall semantics).

### 5.4 Process groups, sessions, credentials, umask — the pre-exec parameters

**[POSIX via CPython]** Each is performed in the child between fork and
exec, lock-free, and is the *sanctioned* replacement for `preexec_fn`:

| Parameter | Effect (docs, verified) | Since |
|---|---|---|
| `start_new_session=True` | `setsid()` in the child — new session, detached from controlling terminal | 3.2 |
| `process_group=0` (or pgid) | `setpgid(0, value)` in the child — new process group without new session (e.g. keep the terminal, enable group signaling) | 3.11 |
| `group=` / `extra_groups=` / `user=` | `setregid()`/`setgroups()`/`setreuid()` in the child; strings resolved via `grp`/`pwd`. Note: "Specifying user will not drop existing supplementary group memberships! The caller must also pass extra_groups=()" | 3.9 |
| `umask=0o022` | `umask()` call in the child | 3.9 |

All marked `Availability: POSIX` in the docs. Ordering is
umask/group/user before exec; signals are also reset (§5.5) in the same
window.

### 5.5 `restore_signals=True`

**[CPython/POSIX]** Docs, verbatim: "If restore_signals is true (the
default) all signals that Python has set to SIG_IGN are restored to
SIG_DFL in the child process before the exec. Currently this includes the
SIGPIPE, SIGXFZ and SIGXFSZ signals." (The docs list those three; SIGPIPE
is the one Python ignores by default, §4.2.) Disabling it leaves the child
with the parent's ignored/dispositions — appropriate only when the child
is another Python program that would set them itself.

### 5.6 Waiting: `poll`, `wait`, the pipe deadlock, and event-driven waits

**[CPython]** `poll()` checks without blocking (returns `None` or sets
`.returncode`); `wait(timeout=None)` blocks. The docs carry the canonical
deadlock warning verbatim: "This will deadlock when using stdout=PIPE or
stderr=PIPE and the child process generates enough output to a pipe such
that it blocks waiting for the OS pipe buffer to accept more data. Use
Popen.communicate() when using pipes to avoid that." With a timeout, the
3.15 docs note the implementation detail: "if timeout is not None, use
efficient event-driven implementation on Linux >= 5.3 and macOS / BSD"
(`os.pidfd_open()` + `select.poll()`; kqueue on BSD/macOS; the historical
fallback was a poll-and-sleep loop). Timeout expiry raises `TimeoutExpired`
and "It is safe to catch this exception and retry the wait".

### 5.7 `communicate()` and zombies

**[CPython]** `communicate(input=None, timeout=None)` reads stdout+stderr
to EOF (concurrently, via threads or selector internals), feeds `input`
to stdin, then waits — the only safe generic way to drain pipes. On
timeout: "The child process is **not killed** if the timeout expires" and
"Catching this exception and retrying communication will not lose any
output"; but "Supplying input to a subsequent post-timeout communicate()
call is in undefined behavior". The docs' cleanup pattern is explicit:
kill on `TimeoutExpired`, then a second `communicate()` to finish reaping.
Zombies: an unreaped child lingers until parent exit; `Popen` guards
against this itself (§5.9's `_active` list), and for raw `os.fork` parents
the reaper is `os.waitpid(pid, 0)` or polling `os.waitpid(pid, os.WNOHANG)`
/ `os.waitid(..., WNOHANG)` (returns `None` when no child is ready).

### 5.8 `send_signal` / `terminate` / `kill` / `returncode` / `pid`

**[CPython/POSIX]** `send_signal(sig)` sends to the child ("Do nothing if
the process completed"); `terminate()` sends `SIGTERM` on POSIX;
`kill()` sends `SIGKILL` on POSIX; on Windows `kill() is an alias for
terminate()` and both call `TerminateProcess`. `returncode`: "Exit status
of the child process. … A negative value -N indicates that the child was
terminated by signal N (POSIX only)" — the docs' own encoding of the
wait-status; decoding the raw status word is `os.waitstatus_to_exitcode`
(§5.9). `pid` is the child's OS pid.

### 5.9 Context manager, destructor, and the `_active` reaper

**[CPython]** `Popen` supports `with` — docs: "on exit, standard file
descriptors are closed, and the process is waited for" (context manager
support added 3.2). The destructor contract, source + docs: "Popen
destructor now emits a ResourceWarning warning if the child process is
still running" (3.6), and `Lib/subprocess.py` goes further —
`Popen.__del__` calls `_internal_poll(_deadstate=_maxsize)` and, if the
child is still running, appends the object to the module-level `_active`
list; `_cleanup()` runs at every subsequent `Popen` creation and
synchronously `_internal_poll`s everything in `_active` "to avoid zombie
processes" (source comment). Net semantics: an abandoned, still-running
`Popen` is reaped opportunistically at the next Popen creation or at
interpreter exit — a GC-anchored safety net (§6.8), not a substitute for
`wait()`.

### 5.10 `subprocess.run` and the timeout contract

**[language/CPython]** `run()` builds a `Popen`, calls `communicate()`,
and returns a `CompletedProcess`. Docs, verbatim on timeout: "The timeout
argument is passed on to Popen.communicate(). If the timeout expires, the
child process will be killed and waited for. The TimeoutExpired exception
will be re-raised after the child process has terminated." So unlike bare
`communicate()`, **`run()` kills and reaps the child on timeout** — the
exception surfaces only after the kill+wait completes, and
`TimeoutExpired.stdout/.stderr` carry partial output where captured.
`check=True` raises `CalledProcessError` on non-zero returncode, carrying
`.returncode`, `.cmd`, and captured output. Also documented: "The initial
process creation itself cannot be interrupted on many platform APIs so you
are not guaranteed to see a timeout exception until at least after however
long process creation takes."

### 5.11 `shell=True`, injection, and `shlex`

**[language]** Security considerations section, verbatim: "Unlike some
other popen functions, this library will not implicitly choose to call a
system shell. This means that all characters, including shell
metacharacters, can safely be passed to child processes." — `shell=False`
(default) is the injection defense; with `shell=True` "it is the
application's responsibility to ensure that all whitespace and
metacharacters are quoted". The stdlib tool is `shlex.split()` (correct
tokenization of a shell line into args) and, since 3.8, `shlex.join
(split_command)` — "Concatenate the tokens of the list split_command and
return a string. This function is the inverse of split()" — for building
*display* shell lines from trusted tokens. Note the honest caveat:
`shlex.quote`/`join` quote for `/bin/sh` and are not a security boundary
for arbitrary user data.

```python
import subprocess, shlex
subprocess.run(["ls", "-l", user_path])          # safe: no shell
subprocess.run("ls -l " + shlex.join([user_path]),  # WRONG pattern shown
               shell=True)                        # for contrast; never do this
subprocess.run(f"ls -l {shlex.quote(user_path)}", shell=True)  # quoted, still second-best
```

### 5.12 Legacy trio and child-side exec failure

**[language]** `call`/`check_call`/`check_output` are thin wrappers over
`run()` (§2.3) kept for compatibility. One verified semantic that surprises:
"Exceptions raised in the child process, before the new program has started
to execute, will be re-raised in the parent. The most common exception
raised is OSError" (docs) — a missing executable surfaces in the *parent*
as `FileNotFoundError`, not as a child exit code, provided the fast-path
`posix_spawn` is not taken (the 3.8 versionchanged notes the WSL/QEMU
exception: with `posix_spawn`, "no longer raise an exception on errors like
missing program, but the child process fails with a non-zero returncode").

### 5.13 `asyncio` subprocesses

**[CPython]** `asyncio.create_subprocess_exec(program, *args, ...)` and
`create_subprocess_shell(cmd, ...)` (§2.4) return an
`asyncio.subprocess.Process` — "designed to have a similar API to the
subprocess.Popen class" with coroutine `communicate()`/`wait()`, and
`send_signal/terminate/kill` (same POSIX/Windows mapping as `Popen`).
Semantics that differ from sync `subprocess`: output arrives through
`StreamReader`s bounded by `limit=65536` (overflow pauses the transport
rather than growing memory); waiting is integrated with the loop, so a
cancelled `wait()`/`communicate()` propagates cancellation without the
"kill on timeout" side contract `run()` has (kill-then-reap is *your* code
in asyncio). Use `exec` unless shell syntax is genuinely needed (same
injection analysis as §5.11). The event loop itself relies on the
child-watch machinery (pidfd on modern Linux) to reap children.

### 5.14 `multiprocessing` (brief) and the raw `os` process APIs

**[CPython/POSIX]** `multiprocessing.Process` (§2.4) runs *Python* in a
child — via `fork` (copy the interpreter), `spawn` (fresh interpreter +
pickled target), or `forkserver` — selected by the start method; only
`fork` preserves parent memory and shares nothing after return. `.daemon
=True` children are terminated when the parent exits (no `atexit`-like
grace), `.exitcode` is `None` while running, else the wait-status (again:
negative = signal). `os`-level family, all verified against the os docs:

| API | Canonical signature (verified) | Semantics |
|---|---|---|
| `os.fork` | `os.fork()` → int (0 child / pid parent) | Copy the whole runtime; OSError on failure. 3.12: `DeprecationWarning` if multiple threads detected (§6.2); RuntimeError in subinterpreters (3.8+). |
| `os.forkpty` | `os.forkpty()` → `(pid, fd)` | Fork with a new pseudo-terminal as child's controlling terminal; fd = master end, non-inheritable. (POSIX-ish; docs prefer `pty` module for portability.) |
| `os.execv` family | `os.execv(path, args)`; `os.execve(path, args, env)`; `os.execvp(file, args)`; `os.execvpe(file, args, env)` (+`execl*` variants) | Replace the current process image; "they do not return"; errors → OSError in the (still-Python) caller. Docs: "Open file objects and descriptors are not flushed, so if there may be data buffered on these open files, you should flush them". |
| `os.wait` / `os.waitpid` | `os.wait()` → `(pid, status)`; `os.waitpid(pid, options, /)` → `(pid, status)` | Reap a child; raw 16-bit wait status; `WNOHANG` option for non-blocking; `ChildProcessError` when nothing to wait for. |
| `os.waitid` | `os.waitid(idtype, id, options, /)` → `siginfo_t`-like or `None` | Fine-grained: `P_PID/P_PGID/P_ALL/P_PIDFD` (Linux), `WEXITED/WSTOPPED/WCONTINUED`, `WNOHANG/WNOWAIT`; `WNOHANG` → `None` when nothing ready. |
| `os.waitstatus_to_exitcode` | `os.waitstatus_to_exitcode(status)` → int | Exit status if `WIFEXITED`, else `-signum` if signaled (else raises). The sanctioned status decoder (the docs also expose `WEXITSTATUS/WIFSIGNALED/…`). |
| `os.posix_spawn` | `os.posix_spawn(path, argv, env, *, file_actions=None, setpgroup=None, resetids=False, setsid=False, setsigmask=(), setsigdef=(), scheduler=None)` → pid | Wraps `posix_spawn(3)`: fork+exec fast path *without* running Python in the child — no `preexec_fn` equivalent; child-side setup expressed as `file_actions` (`os.POSIX_SPAWN_OPEN/CLOSE/DUP2`) plus `setpgroup/setsid/setsigmask/...`. Docs: "Most users should use subprocess.run() instead." |
| `os.posix_spawnp` | `os.posix_spawnp(path, argv, env, *, ...same...)` → pid | Same; resolves `path` via `PATH`. Both 3.8+. |
| `os.spawn*` | `os.spawnl(mode, path, ...)`, `spawnle/spawnlp/spawnlpe/spawnv/spawnve/spawnvp/spawnvpe` | Legacy composite exec/spawn family; `mode` `P_WAIT`/`P_NOWAIT`. Prefer `subprocess`. |
| `os.kill` / `os.killpg` | `os.kill(pid, sig, /)`; `os.killpg(pgid, sig, /)` | Send signal to process / process group. Windows: only `CTRL_C_EVENT`/`CTRL_BREAK_EVENT` special-cased, else `TerminateProcess` (§4.8). |
| `os.pipe` / `os.pipe2` | `os.pipe()` → `(r, w)`; `os.pipe2(flags, /)` → `(r, w)` | fds non-inheritable (PEP 446); `pipe2` sets `O_NONBLOCK`/`O_CLOEXEC` atomically (Unix; the C `pipe2(2)` race-free creation). |
| `os.dup2` | `os.dup2(fd, fd2, inheritable=True)` → fd2 | Atomic re-di rection used to build child stdio; result inheritable by default (docs). |
| `os.setsid` | `os.setsid()` → int (new pgid) | New session for the calling process — what `start_new_session=True` does pre-exec in the child. |

---

## 6. Concurrency and Resource Semantics

### 6.1 The GIL: signals, extensions, and what "thread" means here

**[CPython]** One thread executes Python bytecode at a time (GIL); threads
are OS threads, so a *process* has real concurrency only where the GIL is
released (C extensions, I/O, `time.sleep`). Three consequences in scope:

1. **Signal delivery** (§4.1) requires the main thread to run bytecode;
   a main thread blocked in a GIL-holding C extension delays *all*
   Python-level signal handling. The same mechanism Node.js solves with
   its libuv signal pipe is solved here by `set_wakeup_fd` (§4.5) —
   background in [../python/gil.md](../python/gil.md) and
   [../python/asyncio.md](../python/asyncio.md).
2. **Fork safety**: `os.fork()` copies only the calling thread into a
   runtime whose locks may be held by absent threads (§6.2).
3. **Memory model**: visibility of mutations between threads is an
   implementation artifact of the GIL, not a language guarantee — the
   free-threaded build removes the artifact
   ([../python/free-threaded.md](../python/free-threaded.md)).

### 6.2 fork × threads: the documented hazard and `os.register_at_fork`

**[CPython/POSIX]** os docs, verbatim (3.12 versionchanged): "If Python is
able to detect that your process has multiple threads, os.fork() now
raises a DeprecationWarning. We chose to surface this as a warning, when
detectable, to better inform developers of a design problem that the POSIX
platform specifically notes as not supported. Even in code that appears to
work, it has never been safe to mix threading with os.fork() on POSIX
platforms." The sanctioned hooks are `os.register_at_fork(*, before=None,
after_in_parent=None, after_in_child=None)` (3.7+) — run around *every*
fork (`os.fork() or similar process cloning APIs`), which is how libraries
re-seed locks in children. `multiprocessing`'s `fork` start method inherits
all of this; `spawn` avoids it by re-exec'ing a fresh interpreter.

### 6.3 Buffering × fork duplication

**[CPython/POSIX]** `fork()` duplicates the *address space*, including
userspace stdio and Python-level buffers. Anything buffered in the parent
at fork time appears twice logically: the child inherits a copy and, if it
execs a shell that prints and exits through inherited stdio, output
interleaves/duplicates. Hence the os docs' exec warning (§5.14: "flush
them before calling exec") and the child-must-`_exit`-or-exec rule
(§3.5). `subprocess.Popen` is immune by construction: the child's stdio is
re-wired with `dup2` pre-exec and the Python-side pipe objects exist only
in the parent.

### 6.4 fd inheritance review (PEP 446) as a resource-ownership rule

**[CPython]** Non-inheritable-by-default (§5.3) means: a `Popen` without
`pass_fds` cannot leak a database socket or lock fd into a child; `dup2`
is explicitly opted in; `os.pipe2(O_CLOEXEC)` builds race-free pipes for
raw `fork`/`exec` code. The C-level account of the same flags is
[./c.md](./c.md) §6; the Python-specific part is *who* sets the flags:
CPython sets non-inheritable at creation time, per PEP 446.

### 6.5 Daemon threads: abrupt stop, no cleanup

**[language/CPython]** threading docs, verbatim: "Daemon threads are
abruptly stopped at shutdown. Their resources (such as open files,
database transactions, etc.) may not be released properly. If you want
your threads to stop gracefully, make them non-daemonic." Concretely: no
`finally`, no context-manager `__exit__`, no `__del__` for work in flight.
The interpreter exits "when no alive non-daemon threads are left" —
`threading._shutdown` joins them (§3.7 step 1) — so a hung non-daemon
thread hangs process exit; a daemon thread's hung work dies with the
process.

### 6.6 Deadlocks: join + full pipes

**[CPython/POSIX]** The two standard deadlocks, both documented: (1)
`Popen.wait()` with `stdout=PIPE` while the child fills the pipe — child
blocks writing, parent blocks waiting (§5.6 quote) → always `communicate`
or dedicated reader threads. (2) The symmetric shutdown deadlock: parent
`join()`s a worker that writes to a pipe nobody drains. Pipe capacity is
an OS page-count fact (64 KiB default on Linux; `pipesize=`/`F_SETPIPE_SZ`
as hints) — not a queue, and filling it stalls the child. The asyncio
variants replace the reader threads with loop-integrated StreamReaders
bounded by `limit` (§5.13).

### 6.7 Races: `preexec_fn` and the module's own reaper

**[CPython]** Beyond the fork-safety deadlock (§5.2), `preexec_fn` code
races with the parent's threads for duplicated library state (locale,
malloc arenas). Even the stdlib reaper documents a race: `_cleanup()`
source notes "This can happen if two threads create a new Popen instance"
on the `_active.remove` path — harmless there, but a reminder that
`Popen` objects are not designed for cross-thread ownership; one owner
thread, others pass pids/signals through it.

### 6.8 Leaks: unclosed pipes, zombies, and the GC's role

**[CPython]** Forgetting to close the parent ends of child pipes leaks fds
(`ResourceWarning: unclosed` under `-W error::ResourceWarning` /
dev-mode); abandoning a running `Popen` triggers the §5.9 machinery:
`ResourceWarning` at `__del__`, `_active`-list reaping at the next Popen
creation, final reaping at interpreter exit. Raw `os.fork` code has no
such net — the parent *must* `wait`/`waitpid`, else zombies accumulate
until parent exit (§5.7). The GC tie-in: all of these are *resources*,
and Python's GC is a memory collector with PEP 442 finalization as a
backstop (§1.3) — deterministic resource release is `with`/`finally`,
not `__del__`.

### 6.9 `with`-blocks and the cleanup hierarchy

**[language]** The sanctioned cleanup ladder, in order of strength:
`with` context managers (deterministic, exception-safe, §1.5) →
`try/finally` → explicit `close()` in an error path → `atexit`
(process-lifetime, §3.10) → `__del__`/GC (backstop, §1.3) → OS reclamation
at `_exit`/process death (everything, abruptly — the only thing that
closes fds and drops locks held by *killed* daemon threads and un-reaped
children). For `Popen` specifically: `with Popen(...) as p: ...` closes
the stdio pipes and waits (blocking!) on block exit; for non-blocking
ownership use explicit `terminate()`/`communicate()` on error paths and
`wait()` on success paths.

---

## Coverage ledger

Every documented API/behavior row above is inventoried one-to-one in
[./ledger-python.md](./ledger-python.md) as `PL-PY-001` … `PL-PY-080`
(**80 rows**: 80 documented, 0 remaining, 0 source-limited), ordered by
chapter section: §1 → 001–012, §2 → 013–031, §3 → 032–040, §4 → 041–049,
§5 → 050–071, §6 → 072–080. Signatures in the ledger are transcribed
verbatim from the docs.python.org pages cited per row.

## References

Sources retrieved 2026-10-13; every signature and quoted behavioral claim
in this chapter was checked against one of these.

1. **CPython 3.15.0 documentation** (docs.python.org/3 — serves 3.15.0 per
   the docs front page; stable version confirmed at
   python.org/downloads and docs.python.org/3.14/ for the prior line):
   [sys](https://docs.python.org/3/library/sys.html),
   [exceptions](https://docs.python.org/3/library/exceptions.html),
   [atexit](https://docs.python.org/3/library/atexit.html),
   [signal](https://docs.python.org/3/library/signal.html),
   [subprocess](https://docs.python.org/3/library/subprocess.html),
   [os](https://docs.python.org/3/library/os.html),
   [time](https://docs.python.org/3/library/time.html),
   [threading](https://docs.python.org/3/library/threading.html),
   [multiprocessing](https://docs.python.org/3/library/multiprocessing.html),
   [asyncio subprocess](https://docs.python.org/3/library/asyncio-subprocess.html),
   [asyncio event loop](https://docs.python.org/3/library/asyncio-eventloop.html),
   [gc](https://docs.python.org/3/library/gc.html),
   [shlex](https://docs.python.org/3/library/shlex.html),
   [data model](https://docs.python.org/3/reference/datamodel.html),
   [expressions §6.16](https://docs.python.org/3/reference/expressions.html#evaluation-order),
   [execution model §4.2](https://docs.python.org/3/reference/executionmodel.html).
2. **CPython source** (github.com/python/cpython, `main` at retrieval):
   `Python/pylifecycle.c` (shutdown loop: `wait_for_thread_shutdown` →
   `_PyAtExit_Call`; `_Py_Finalize() < 0 → sts = 120`),
   `Lib/subprocess.py` (`Popen.__del__`/`_active`/`_cleanup`),
   `Lib/threading.py` (`_shutdown` docstring, `_register_atexit`).
3. **PEPs**: [PEP 475](https://peps.python.org/pep-0475/) (EINTR retry),
   [PEP 446](https://peps.python.org/pep-0446/) (non-inheritable fds),
   [PEP 442](https://peps.python.org/pep-0442/) (safe finalization).
4. **In-book cross-references**:
   [../../linux/process-exit-signal/languages/python.md](../../linux/process-exit-signal/languages/python.md),
   [./c.md](./c.md), [./index.md](./index.md),
   [../python/gil.md](../python/gil.md),
   [../python/asyncio.md](../python/asyncio.md),
   [../python/free-threaded.md](../python/free-threaded.md).
