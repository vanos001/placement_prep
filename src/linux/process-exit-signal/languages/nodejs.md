# Node.js: Exit Status, Signals, and Process Lifecycle

**ID range:** LG-NO-001 … LG-NO-005 — **Version scope:** Node.js 22 LTS; all claims verified against the API documentation pinned to `nodejs.org/docs/latest-v22.x/api/` (retrieved 2026-10), with per-feature `Added in:` markers quoted where version sensitivity matters. Windows differences are noted briefly; Linux is the reference platform.

Node.js inverts the classical model: there is no `main` function to return from — the process lives exactly as long as the **event loop has work**, and exit codes are set by properties (`process.exitCode`) rather than return values. Termination is therefore about *draining* or *not draining* the loop, and about the small set of APIs that bypass it.

---

## 1. Syntax and Semantics of Termination (LG-NO-001)

### 1.1 Normal completion: the loop drains

Documented in the *Exit codes* section of [`process`](https://nodejs.org/docs/latest-v22.x/api/process.html#exit-codes):

> "Node.js will normally exit with a 0 status code when no more async operations are pending."

There is no `return` from "main": when the event loop has no timers, I/O, or handles left, the process exits with code 0 (after emitting `'beforeExit'`, which may add more work — see §2).

### 1.2 `process.exit([code])`: the synchronous trapdoor

Verified signature and history (v20.0.0: "Only accepts a code of type number, or of type string if it represents an integer"; added v0.1.13):

```text
process.exit([code <integer> | <string> | <null> | <undefined>])   // default: 0
```

Documented behavior, quoted:

> "The `process.exit()` method instructs Node.js to terminate the process synchronously with an exit status of `code`. If `code` is omitted, exit uses either the 'success' code 0 or the value of `process.exitCode` if it has been set. Node.js will not terminate until all the 'exit' event listeners are called."

> "Calling `process.exit()` will force the process to exit as quickly as possible **even if there are still asynchronous operations pending that have not yet completed fully, including I/O operations to `process.stdout` and `process.stderr`**."

The docs then give the canonical misuse example — printing usage to stdout and immediately exiting:

> "The reason this is problematic is because writes to `process.stdout` in Node.js are sometimes asynchronous and may occur over multiple ticks of the Node.js event loop. Calling `process.exit()`, however, forces the process to exit before those additional writes to stdout can be performed."

The documented fix is to set the code and let the loop drain:

```js
// How to properly set the exit code while letting the process exit gracefully:
if (someConditionNotMet()) {
  printUsageToStdout();
  process.exitCode = 1;
}
```

Why stdout can be async at all: when stdout/stderr is a **TTY they are synchronous**; when **piped they are asynchronous** — so the truncation hazard in §1.2 typically strikes in CI logs and `| less` pipelines, not on a terminal. This is the documented behavior of the Node.js runtime; libuv implements it.

### 1.3 `process.exitCode`: the preferred exit channel

Verified ([process.exitCode](https://nodejs.org/docs/latest-v22.x/api/process.html#processexitcode)) — "A number which will be the process exit code, when the process either exits gracefully, or is exited via `process.exit()` without specifying a code", with the docs' own shell session:

```console
$ node -e 'process.exitCode = 9'; echo $?
9
$ node -e 'process.exit(42)'; echo $?
42
$ node -e 'process.exitCode = 9; process.exit(42)'; echo $?
42
```

An explicit `process.exit(n)` argument always wins over a previously set `process.exitCode`. The value "can also be set implicitly by Node.js when unrecoverable errors occur". Since v20.0.0 only numbers (or integer strings) are accepted.

### 1.4 `process.abort()`

> "The `process.abort()` method causes the Node.js process to exit immediately and generate a core file. This feature is not available in Worker threads."

That is the SIGABRT path: on Linux the process dies with signal 6 (shell `$?` = 134), not with an exit status. The docs tie it to core generation (subject to `RLIMIT_CORE`/core-pattern, an OS matter).

### 1.5 `uncaughtException` and the default exit 1

Documented ([Event: 'uncaughtException'](https://nodejs.org/docs/latest-v22.x/api/process.html#event-uncaughtexception)):

> "By default, Node.js handles such exceptions by printing the stack trace to stderr and exiting with code 1, **overriding any previously set `process.exitCode`**. Adding a handler for the `'uncaughtException'` event overrides this default behavior. Alternatively, change the `process.exitCode` in the `'uncaughtException'` handler which will result in the process exiting with the provided exit code. Otherwise, in the presence of such handler the process will exit with 0."

The handler receives `(err, origin)`; `origin` is `'uncaughtException'` or `'unhandledRejection'` ("when an exception happens in a Promise based async context (or if a Promise is rejected) and `--unhandled-rejections` flag set to `strict` or `throw` (which is the default) and the rejection is not handled"). The docs' caution: correct use is to clean up and *then* `process.exit(1)` — resuming normal operation is "not safe".

### 1.6 `unhandledRejection` and the throw-mode default

`'unhandledRejection'` (added v1.4.1) fires "whenever a Promise is rejected and no error handler is attached to the promise within a turn of the event loop." Registering a listener overrides the default; without a listener the default mode (`throw` since **Node 15**) converts the rejection into an uncaught exception — feeding the §1.5 path (exit 1). (`--unhandled-rejections=throw|strict|warn|none|warn-with-error-code` selects the mode.)

### 1.7 The documented exit-code table

The full table from the Node.js 22 `process` docs ([Exit codes](https://nodejs.org/docs/latest-v22.x/api/process.html#exit-codes)), copied exactly:

| Code | Name | Meaning (documented text, condensed) |
|---|---|---|
| 0 | — | Normal exit: no more async operations pending |
| 1 | Uncaught Fatal Exception | "There was an uncaught exception, and it was not handled by a domain or an `'uncaughtException'` event handler." |
| 2 | — | "Unused (reserved by Bash for builtin misuse)" |
| 3 | Internal JavaScript Parse Error | Bootstrapping source caused a parse error; "extremely rare, and generally can only happen during development of Node.js itself." |
| 4 | Internal JavaScript Evaluation Failure | Bootstrap evaluation "failed to return a function value" |
| 5 | Fatal Error | "There was a fatal unrecoverable error in V8. Typically a message will be printed to stderr with the prefix `FATAL ERROR`." |
| 6 | Non-function Internal Exception Handler | "There was an uncaught exception, but the internal fatal exception handler function was somehow set to a non-function, and could not be called." |
| 7 | Internal Exception Handler Run-Time Failure | The internal handler "itself threw an error while attempting to handle it" |
| 8 | — | "Unused. In previous versions of Node.js, exit code 8 sometimes indicated an uncaught exception." |
| 9 | Invalid Argument | "Either an unknown option was specified, or an option requiring a value was provided without a value." |
| 10 | Internal JavaScript Run-Time Failure | Bootstrap function "threw an error when the bootstrapping function was called" |
| 12 | Invalid Debug Argument | "`--inspect` and/or `--inspect-brk` options were set, but the port number chosen was invalid or unavailable." |
| 13 | Unsettled Top-Level Await | "`await` was used outside of a function in the top-level code, but the passed Promise never settled." |
| 14 | Snapshot Failure | V8 startup snapshot build failed (documented in v22) |
| >128 | Signal Exits | "If Node.js receives a fatal signal such as SIGKILL or SIGHUP, then its exit code will be 128 plus the value of the signal code. This is a standard POSIX practice, since exit codes are defined to be 7-bit integers, and signal exits set the high-order bit …" |

Codes 11 (and formerly others) are simply absent from the table; the docs enumerate only what is used.

### 1.8 Termination-path table

| Termination path | Parent observes | Source |
|---|---|---|
| Event loop drains, no `exitCode` set | 0 | documented |
| `process.exitCode = 3`, loop drains | 3 | documented |
| `process.exit(5)` | 5 (pending async I/O may be lost) | documented |
| Uncaught exception, no handler | 1 + stack trace (overrides `exitCode`) | documented |
| Unhandled rejection (default `throw` mode) | 1 | documented (`--unhandled-rejections` default) |
| `process.abort()` | killed by SIGABRT; shell `$?` = 134 | documented (core file) |
| `process.kill(pid, 'SIGKILL')` on self | killed by signal 9; shell `$?` = 137 | `process.kill` docs + OS semantics |
| External `kill -TERM`, no handler | Node "will perform a sequence of cleanup actions and then will re-raise the handled signal" → shell 143 | documented (child_process `'exit'` event note, §4.3) |
| Fatal V8 error | 5 | documented |

### 1.9 Misconceptions

- **"`process.exit()` flushes stdout first."** It does not — the documented stdout-truncation hazard is §1.2.
- **"Setting `process.exitCode` inside an `uncaughtException` handler is enough."** Without a handler the default *overrides* `exitCode` with 1; with a handler you control it — the docs state both halves.
- **"Registering `process.on('SIGTERM', ...)` adds handling."** It *replaces* the default: "If one of these signals has a listener installed, its default behavior will be removed (Node.js will no longer exit)" — forgetting to actually exit turns SIGTERM into a no-op.
- **"Exit code 8 means uncaught exception."** "Unused. In previous versions of Node.js, exit code 8 sometimes indicated an uncaught exception" — it is 1 now.
- **"Worker threads can abort the process."** `process.abort()` is not available in Worker threads (documented).

---

## 2. Standard-Library and Runtime API Inventory (LG-NO-002)

All signatures verified against the Node.js 22 docs (module `node:process`, `node:child_process`, `node:worker_threads`).

### `process` — termination-relevant surface

| API | Verified signature | Key semantics |
|---|---|---|
| `process.exit` | `process.exit([code])` | Synchronous termination; v20+ type restrictions; does not wait for pending async callbacks; runs `'exit'` listeners first |
| `process.exitCode` | `<integer> \| <string> \| <null> \| <undefined>` (default `undefined`) | Graceful exit code; explicit `exit(n)` overrides; implicit set by unrecoverable errors |
| `process.abort` | `process.abort()` | Immediate exit + core file; not in Worker threads |
| `process.kill` | `process.kill(pid[, signal])` | Signal sender ("it is really just a signal sender, like the kill system call"); default `'SIGTERM'`; throws if pid does not exist; signal `0` tests existence; Windows throws on process groups |
| `process.pid` / `process.ppid` | `<integer>` | Own pid; parent pid |
| Event `'exit'` | `(code) => {}` | Emitted for `process.exit()` or loop drain; listeners "must only perform synchronous operations"; "There is no way to prevent the exiting of the event loop at this point" |
| Event `'beforeExit'` | `(code) => {}` | "emitted when Node.js empties its event loop and has no additional work to schedule"; listener "can make asynchronous calls, and thereby cause the Node.js process to continue"; **not** emitted for `process.exit()` or uncaught exceptions |
| Event `'uncaughtException'` | `(err, origin) => {}` | Overrides default exit-1 behavior; origin ∈ `'uncaughtException'` \| `'unhandledRejection'` |
| Event `'unhandledRejection'` | `(reason, promise) => {}` | Overrides default throw-mode for that rejection |
| Signal events | `process.on('SIGINT', (signal) => {})` | See §4 |

### `worker_threads` — brief, verified

- `worker.terminate()` → `Promise`: "Stop all JavaScript execution in the worker thread as soon as possible. Returns a Promise for the exit code that is fulfilled when the `'exit'` event is emitted." (v12.5.0 made it fully asynchronous.)
- Worker event `'exit'`: "If the worker exited by calling `process.exit()`, the exitCode parameter is the passed exit code. If the worker was terminated, the exitCode parameter is 1."
- Signals are **not** available on Worker threads ("Signals are not available on Worker threads" — `process` docs), so signal-driven shutdown is a main-thread concern only.

---

## 3. Process Lifecycle and Termination (LG-NO-003)

**Creation.** The `node` binary starts, bootstraps the runtime (codes 3/4/10 are bootstrap failures, §1.7), evaluates the entry point (ESM or CJS), and then the event loop takes over.

**Normal shutdown.** The loop runs until no handles/references remain; `'beforeExit'` fires (a listener may schedule more work and keep the process alive — the documented "loop will drain again" semantics); when truly nothing remains, `'exit'` fires with the effective code and the process terminates. `'exit'` listener rules: synchronous only; a `setTimeout` registered there "will never occur" (documented example).

**Explicit termination.** `process.exit(n)` — synchronous, skips pending async completions, fires `'exit'` listeners; `process.exitCode = n` — deferred until natural drain; `process.abort()` — SIGABRT crash path.

**Abnormal termination.** Uncaught exception → exit 1 (default) or your handler's choice. Fatal signal → 128+N per the documented Signal-Exits rule; for SIGINT/SIGTERM specifically Node intercepts, cleans up, and re-raises (§4.3), which makes the shell-visible result 128+N as well.

**Process vs thread vs child.** Worker threads terminate independently (`worker.terminate()`; exit code 1 on termination) and cannot receive signals. Child processes are separate OS processes (`child_process`, §5); killing the main process orphans them unless `detached`+`unref` semantics were chosen deliberately. `process.kill(process.pid, sig)` terminates *this* process; `subprocess.kill()` terminates a child — the docs stress the first "is really just a signal sender, like the kill system call."

---

## 4. Signals and OS Interaction (LG-NO-004)

### 4.1 Signal events: registration and default-removal

Documented (*Signal events*):

> "Signal events will be emitted when the Node.js process receives a signal. Please refer to signal(7) for a listing of standard POSIX signal names such as `'SIGINT'`, `'SIGHUP'`, etc." — "The signal handler will receive the signal's name (`'SIGINT'`, `'SIGTERM'`, etc.) as the first argument."

Registered listeners run as ordinary event-loop callbacks — **not** inside a C signal handler; libuv's signal handling defers the event to the loop (the runtime's abstraction over `signalfd`/`sigaction` machinery; the docs do not commit to a mechanism, only to the observable event semantics). Key documented defaults:

> "'SIGTERM' and 'SIGINT' have default handlers on non-Windows platforms that reset the terminal mode before exiting with code 128 + signal number. If one of these signals has a listener installed, its default behavior will be removed (Node.js will no longer exit)."

> "'SIGPIPE' is ignored by default. It can have a listener installed."

> "'SIGUSR1' is reserved by Node.js to start the debugger. It's possible to install a listener but doing so might interfere with the debugger."

> "'SIGHUP' … On non-Windows platforms, the default behavior of SIGHUP is to terminate Node.js, but once a listener has been installed its default behavior will be removed."

Signals on Windows are approximated (console control events; "SIGTERM is not supported on Windows, it can be listened on" — brief note; out of Linux scope).

### 4.2 `process.kill` and self-signaling

`process.kill(pid[, signal='SIGTERM'])` sends signals to any process (permissions permitting). Documented details: throws if the pid does not exist; "a signal of 0 can be used to test for the existence of a process"; "Even though the name of this function is `process.kill()`, it is really just a signal sender, like the kill system call. The signal sent may do something other than kill the target process."

### 4.3 Node's own SIGINT/SIGTERM interception (re-raise behavior)

A documented runtime behavior, from the `child_process` `'exit'` event text:

> "Node.js establishes signal handlers for SIGINT and SIGTERM and Node.js processes will not terminate immediately due to receipt of those signals. Rather, Node.js will perform a sequence of cleanup actions and then will re-raise the handled signal."

So even with *no* listener, SIGTERM's exit is mediated by the runtime: cleanup, then re-raise → default action → shell reports 143. This parallels CPython's `exit_sigint` re-raise; in Node's case the statement lives in the child_process docs rather than the `process` docs.

### 4.4 Safe handler → application communication; runtime restrictions

- Signal listeners are event-loop callbacks: within them you may do anything Node code can do (unlike POSIX async-signal-safety). The "async-signal-safety" problem is absorbed by libuv — this is the runtime abstracting OS semantics.
- The corresponding restriction: signal events only fire when the loop runs. A process stuck in a synchronous loop or blocked on a sync `spawnSync`/`execSync` call does not process signals until it returns.
- Signals are process-wide and delivered to the main thread's loop; Worker threads cannot listen (documented), so per-thread signal routing is out of the model entirely.
- POSIX vs Linux-specific: nothing in Node's documented signal surface is Linux-only beyond availability notes; defaults above are "on non-Windows platforms".

---

## 5. Subprocess and Child-Process Management (LG-NO-005)

### 5.1 The four creation APIs

Verified signatures (Node 22):

```text
child_process.spawn(command[, args][, options])            -> ChildProcess (EventEmitter, streams)
child_process.exec(command[, options][, callback])         -> ChildProcess (shell; buffered output)
child_process.execFile(file[, args][, options][, callback])-> ChildProcess (no shell by default)
child_process.fork(modulePath[, args][, options])          -> ChildProcess (Node child + IPC channel)

child_process.spawnSync(command[, args][, options])        -> Object { pid, output, stdout, stderr, status, signal, error }
child_process.execSync(command[, options])                 -> Buffer | string
child_process.execFileSync(file[, args][, options])        -> Buffer | string
```

`spawn`/`execFile` = argument-array APIs (no shell) — safe against injection. `exec`/`execSync` (and any API with `shell: true`) run `/bin/sh` — see §5.4.

### 5.2 Options that matter (verified, with version markers)

- `cwd`, `env` (default `process.env`), `argv0`, `uid`, `gid`, `serialization` (`'json'`/`'advanced'`, v13.2/12.16), `windowsHide` (v8.8), `shell` (spawn, v5.7).
- `stdio` — `'pipe' | 'overlapped' | 'ignore' | 'inherit'` shorthand or an array of per-fd directives (`[0, 1, 2, 'ipc']` for fork-style). Documented: `'pipe'` creates the streams exposed as `child.stdin/stdout/stderr`; `'ignore'` attaches `/dev/null`; `'inherit'` passes the parent's stdio; `'ipc'` creates the message channel (at most one per child). Extra fds can create additional pipes (`child.stdio[fd]`). Notable documented caveat: pipe fds "are not actual Unix pipes and therefore the child process can not use them by their descriptor files, e.g. `/dev/fd/2` or `/dev/stdout`."
- `timeout` (v15.13/14.18) + `killSignal` (default `'SIGTERM'`) + `signal` (`AbortSignal`, v15.5/14.17) + `killSignal` for AbortSignal (v15.11/14.18): on timeout or abort the child is killed with `killSignal`.
- `maxBuffer` (exec/execFile/sync): "Largest amount of data in bytes allowed on stdout or stderr. If exceeded, the child process is terminated and any output is truncated. … Default: `1024 * 1024`."
- `detached` (v0.7.10): "On non-Windows platforms, if `options.detached` is set to true, the child process will be made the leader of a new process group and session" (setsid(2) semantics). "By default, the parent will wait for the detached child process to exit. To prevent the parent process from waiting for a given subprocess to exit, use the `subprocess.unref()` method."

### 5.3 ChildProcess properties: the live status surface

Verified property semantics (Node 22):

| Property | Type | Documented meaning |
|---|---|---|
| `subprocess.pid` | `<integer> \| <undefined>` | Child pid; "If the child process fails to spawn due to errors, then the value is `undefined` and `error` is emitted" |
| `subprocess.exitCode` | `<integer> \| <null>` | "indicates the exit code of the child process. If the child process is still running, the field will be `null`" |
| `subprocess.signalCode` | `<string> \| <null>` | "indicates the signal received by the child process if any, else `null`" |
| `subprocess.killed` | `<boolean>` | "Set to `true` after `subprocess.kill()` is used to successfully send a signal to the child process. … The `killed` property does not indicate that the child process has been terminated." |
| `subprocess.spawnfile` | `<string>` | "the name of the executable file … For `child_process.exec()`, its value will be the name of the shell in which the child process is launched" |
| `subprocess.spawnargs` | `<Array>` | "the full list of command-line arguments the child process was launched with" |
| `subprocess.stdio` | `<Array>` | "A sparse array of pipes to the child process, corresponding with positions in the `stdio` option … that have been set to the value `'pipe'`. `subprocess.stdio[0]`, `[1]`, `[2]` are also available as `subprocess.stdin`, `subprocess.stdout`, `subprocess.stderr`" |

The `killed` vs `signalCode` vs `exitCode` distinction matters: `killed` records *your* action, `signalCode`/`exitCode` record the *child's* outcome. Polling them is legal but the events are the synchronization points.

### 5.4 `'exit'` vs `'close'` vs `'error'` — status retrieval

Quoted verbatim (the exact parameter semantics):

- `'exit'` `(code, signal)`: "If the process exited, `code` is the final exit code of the process, otherwise `null`. If the process terminated due to receipt of a signal, `signal` is the string name of the signal, otherwise `null`. **One of the two will always be non-null.**" … "When the `'exit'` event is triggered, child process stdio streams might still be open."
- `'close'` `(code, signal)`: "emitted after a process has ended **and the stdio streams of a child process have been closed**. This is distinct from the `'exit'` event, since multiple processes might share the same stdio streams. The `'close'` event will always emit after `'exit'` was already emitted, or `'error'` if the child process failed to spawn."
- `'error'`: emitted when "The process could not be spawned. / The process could not be killed. / Sending a message to the child process failed. / The child process was aborted via the `signal` option." … "**The `'exit'` event may or may not fire after an error has occurred.** When listening to both the `'exit'` and `'error'` events, guard against accidentally invoking handler functions multiple times."

```js
const { spawn } = require('node:child_process');
const child = spawn('sh', ['-c', 'exit 3']);
child.on('exit', (code, signal) => console.log('exit', code, signal));  // exit 3 null
child.on('close', (code, signal) => console.log('close', code, signal));
const killed = spawn('sleep', ['100']);
killed.kill('SIGKILL');
killed.on('exit', (code, signal) => console.log(code, signal));         // null 'SIGKILL'
```

Sync result object (`spawnSync`), verified field semantics: `pid`; `output` array; `stdout`/`stderr` (elements of `output`); **`status` `<number> | <null>` — "The exit code of the subprocess, or null if the subprocess terminated due to a signal"**; **`signal` `<string> | <null>` — "The signal used to kill the subprocess, or null if the subprocess did not terminate due to a signal"**; `error` (spawn failure or timeout). This is the dual representation — exactly one of `status`/`signal` is non-null, mirroring the `'exit'` event.

`exec`'s callback contract: `(error, stdout, stderr)`; "On error, `error` will be an instance of Error. The `error.code` property will be the exit code of the process. By convention, any exit code other than 0 indicates an error. `error.signal` will be the signal that terminated the process."

### 5.4.1 The `'spawn'` event and stream-time guarantees

Beyond `'exit'`/`'close'`/`'error'`, the `ChildProcess` API documents one more lifecycle event:

- `'spawn'` (added v15.1.0): "emitted once when the child process spawns successfully." Combined with `'error'`, this gives the two-sided spawn outcome: success → `'spawn'`; failure → `'error'` (and per §5.4, `'exit'` "may or may not fire").

Stream references remain valid after the child exits; `subprocess.stdin` is `null` when stdin was not `'pipe'`, and writes to a `null` stream throw — check the `stdio` configuration before writing. `subprocess.ref()` / `subprocess.unref()` flip the loop-reference bit documented in §5.7 ("By default, the parent will wait for the detached child process to exit").

### 5.5 Shell execution and injection (documented warning)

`exec`/`execSync` docs, quoted:

> "Spawns a shell then executes the command within that shell, buffering any generated output. The command string passed to the `exec` function is processed directly by the shell and special characters (vary based on shell) need to be dealt with accordingly" — with the docs' own quoting examples ("Double quotes are used so that the space in the path is not interpreted as a delimiter of multiple arguments"), followed by the hard rule:

> "**Never pass unsanitized user input to this function. Any input containing shell metacharacters may be used to trigger arbitrary command execution.**"

The same sentence appears in the `spawnSync` docs gated on `shell: true` ("If the `shell` option is enabled, do not pass unsanitized user input to this function."). The safe pattern is the argument-array API:

```js
// user input "x; rm -rf ~"
exec(`ls ${userInput}`);                       // UNSAFE: shell metacharacters execute
spawn('ls', [userInput]);                      // SAFE: one argument, no shell
execFile('ls', [userInput], cb);               // SAFE
```

Note the Node 22 history entry: v22.15.0 deprecates "Passing `args` when `shell` is set to true" for spawn/execFile — combining an args array with a shell string was always ambiguous and is now formally discouraged.

### 5.6 Termination, timeouts, aborts

- `subprocess.kill([signal])` — "sends a signal to the child process. If no argument is given, the process will be sent the `'SIGTERM'` signal. … This function returns `true` if `kill(2)` succeeds, and `false` otherwise." Documented hazards: "The ChildProcess object may emit an `'error'` event if the signal cannot be delivered. Sending a signal to a child process that has already exited is not an error but may have unforeseen consequences. Specifically, if the process identifier (PID) has been reassigned to another process, the signal will be delivered to that process instead."
- `timeout` option: after the deadline the child receives `killSignal` (SIGTERM default) — set `killSignal: 'SIGKILL'` for hard kills; for `spawnSync`, "When a timeout has been encountered and `killSignal` is sent, the method won't return until the process has completely exited. If the process intercepts and handles the SIGTERM signal and doesn't exit, the parent process will wait until the child process has exited."
- `AbortSignal`: pass `signal` (an `AbortController.signal`); aborting kills the child (with `killSignal` for spawn, v15.11+) and emits `'error'` ("The child process was aborted via the `signal` option").
- Timeouts and aborts surface in sync APIs as `result.error` (with `error.signal`/`error.code` per the callback contract above).

### 5.7 Pipe buffering, deadlocks, zombies, orphans

- Pipe deadlock: the documented guidance is to consume `child.stdout`/`child.stderr` when using `'pipe'` — a child writing more than the pipe buffer with nobody reading blocks in `write(2)` (same OS mechanism as the Java `Process` warning; Node's default `exec` family buffers for you but then `maxBuffer` kills at 1 MiB). Backpressure on `child.stdin` likewise: do not `child.stdin.end()` while the child still expects input, and do not write without respecting drain events.
- Buffering: children's libc buffers their stdout when piped (block-buffered); interleaving of a child's stdout/stderr in `exec`'s merged strings reflects the child's own flush behavior, not Node's.
- Zombies: a reaped child requires the parent to read its status — Node does this internally when `'exit'`/`'close'` observers exist; for `detached`+`unref` children the parent may exit first, leaving the child to be re-parented (orphan), which is the intended "daemonize" use. (The docs document the setsid semantics and `unref`; they do not document libuv's internal reaping mechanism — that detail is intentionally left at the documented level here.)
- Inherited descriptors: with `stdio: 'ignore'` Node opens `/dev/null` (documented); with numeric fd entries the child gets *that* fd; `close_fds`-style hygiene is not provided — pass only what the child needs.
- Windows differences (brief): no SIGTERM delivery, `process.kill` throws on process groups, `detached` gives the child its own console window, quoting is handled by Node's argument joining with `windowsVerbatimArguments` escape hatch.

---

## 6. Concurrency and Resource Semantics (LG-NO-006)

**Event-loop model.** All child-process events (`'exit'`, `'close'`, `'error'`, stream data) are delivered on the main thread's loop — no locks exist or are needed. The single-threaded constraint cuts both ways: `spawnSync`/`execSync`/`execFile` (sync) block the *entire* process, including signal processing (§4.4) — a documented reason to prefer async APIs in servers.

**Streams and backpressure.** `child.stdin` is a Writable; ignoring `'drain'` while writing large data grows memory rather than blocking (Node buffers), but the *child* still experiences the pipe fill. `'close'` after `'exit'` is the documented synchronization point for "child done *and* output drained" — use it for completion logic that depends on output.

**fd ownership.** Pipe fds belong to the parent's `ChildProcess` streams; `unref()` (and `channel.unref()`) remove the child from the loop's reference count so the parent can exit with the child still running (documented in `options.detached`). Not closing `child.stdin` keeps the loop alive — the classic "node won't exit" symptom, fixed by `child.stdin.end()` or `unref()`.

**Cancellation.** `AbortController` → `signal` option is the sanctioned cancellation path (v15.5+); `kill()` remains the manual one. There is no graceful-shutdown cascade API — orchestrate SIGTERM-then-SIGKILL yourself with timers.

**Races and leaks.** `'error'` + `'exit'` double-fire requires guard code (documented). `subprocess.exitCode`/`signalCode` properties update when known — checking `subprocess.killed` only tells you *you called kill*, not that the child died (documented). Abandoned `ChildProcess` objects with open pipe streams keep the event loop referenced (leak of process lifetime).

### 6.1 End-to-end pattern: graceful shutdown with children

```js
const { spawn } = require('node:child_process');

const child = spawn('long-runner', [], { stdio: ['pipe', 'pipe', 'inherit'] });
let shuttingDown = false;

function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  child.kill('SIGTERM');               // graceful request
  const hardKill = setTimeout(() => child.kill('SIGKILL'), 5000);
  child.once('exit', (code, sig) => {  // 'close' if you also need output drained
    clearTimeout(hardKill);
    process.exitCode = code ?? 1;      // propagate child's fate
  });
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));
// NOTE: registering these listeners REMOVED Node's default exit-on-SIGTERM/SIGINT;
// the process now only exits when this code decides it does.
```

Read the pieces against the documentation: default-removal (§4.1), kill return value and PID-reuse warning (§5.3/§5.6), `'exit'` nullability (§5.4), `exitCode` propagation (§1.3).

---

### Coverage ledger

Statuses: `documented` = verified against the Node.js 22 API docs with signature and semantics recorded; `source-limited` = a named primary source was unreachable or silent.

| API | Canonical signature | Status | Reference |
|---|---|---|---|
| LG-NO-001 `process.exit` | `process.exit([code])` | documented | [process.html#processexitcode](https://nodejs.org/docs/latest-v22.x/api/process.html#processexit) |
| LG-NO-001 `process.exitCode` | `<integer> \| <string> \| <null> \| <undefined>` | documented | [process.html#processexitcode](https://nodejs.org/docs/latest-v22.x/api/process.html#processexitcode) |
| LG-NO-001 `process.abort` | `process.abort()` | documented | [process.html#processabort](https://nodejs.org/docs/latest-v22.x/api/process.html#processabort) |
| LG-NO-001 exit-code table (0–14, >128) | (§1.7, copied verbatim) | documented | [process.html#exit-codes](https://nodejs.org/docs/latest-v22.x/api/process.html#exit-codes) |
| LG-NO-001 `'uncaughtException'` default exit 1 | `(err, origin) => {}` | documented | [process.html#event-uncaughtexception](https://nodejs.org/docs/latest-v22.x/api/process.html#event-uncaughtexception) |
| LG-NO-001 `'unhandledRejection'` / throw default | `(reason, promise) => {}` | documented | [process.html#event-unhandledrejection](https://nodejs.org/docs/latest-v22.x/api/process.html#event-unhandledrejection) |
| LG-NO-002 `'beforeExit'` / `'exit'` events | `(code) => {}` | documented | [process.html#event-beforeexit](https://nodejs.org/docs/latest-v22.x/api/process.html#event-beforeexit) |
| LG-NO-002 `worker.terminate()` + `'exit'` | `worker.terminate() -> Promise<integer>` | documented | [worker_threads.html](https://nodejs.org/docs/latest-v22.x/api/worker_threads.html#workerterminatecallback) |
| LG-NO-003 lifecycle/termination paths | (§1.8, §3) | documented | as LG-NO-001 |
| LG-NO-004 signal events + default removal | `process.on('SIGTERM' \| 'SIGINT' \| …, (signal) => {})` | documented | [process.html#signal-events](https://nodejs.org/docs/latest-v22.x/api/process.html#signal-events) |
| LG-NO-004 `process.kill` | `process.kill(pid[, signal])` | documented | [process.html#processkillpid-signal](https://nodejs.org/docs/latest-v22.x/api/process.html#processkillpid-signal) |
| LG-NO-004 SIGINT/SIGTERM intercept + re-raise | — | documented (child_process 'exit' note) | [child_process.html#event-exit](https://nodejs.org/docs/latest-v22.x/api/child_process.html#event-exit) |
| LG-NO-005 `child_process.spawn` | `spawn(command[, args][, options])` | documented | [child_process.html#child_processspawncommand-args-options](https://nodejs.org/docs/latest-v22.x/api/child_process.html#child_processspawncommand-args-options) |
| LG-NO-005 `spawnSync` return object | `{ pid, output, stdout, stderr, status, signal, error }` | documented | [child_process.html#child_processspawnsynccommand-args-options](https://nodejs.org/docs/latest-v22.x/api/child_process.html#child_processspawnsynccommand-args-options) |
| LG-NO-005 `exec` / `execSync` (shell; injection) | `exec(command[, options][, callback])` | documented (warning quoted §5.4) | [child_process.html#child_processexeccommand-options-callback](https://nodejs.org/docs/latest-v22.x/api/child_process.html#child_processexeccommand-options-callback) |
| LG-NO-005 `execFile` / `execFileSync` | `execFile(file[, args][, options][, callback])` | documented | [child_process.html#child_processexecfilefile-args-options-callback](https://nodejs.org/docs/latest-v22.x/api/child_process.html#child_processexecfilefile-args-options-callback) |
| LG-NO-005 `fork` (IPC) | `fork(modulePath[, args][, options])` | documented | [child_process.html#child_processforkmodulepath-args-options](https://nodejs.org/docs/latest-v22.x/api/child_process.html#child_processforkmodulepath-args-options) |
| LG-NO-005 `'exit'`/`'close'`/`'error'` semantics | (§5.3, quoted) | documented | [child_process.html#event-exit](https://nodejs.org/docs/latest-v22.x/api/child_process.html#event-exit) |
| LG-NO-005 `subprocess.kill([signal])` | returns `boolean` | documented (PID-reuse warning quoted) | [child_process.html#subprocesskillsignal](https://nodejs.org/docs/latest-v22.x/api/child_process.html#subprocesskillsignal) |
| LG-NO-005 `stdio` option / `detached` / `unref` / timeouts / AbortSignal / maxBuffer | verified option list (§5.2) | documented | [child_process.html#optionsstdio](https://nodejs.org/docs/latest-v22.x/api/child_process.html#optionsstdio) |
| LG-NO-006 concurrency/fd/backpressure semantics | (§6) | documented | as above |
| libuv internal zombie-reaping mechanism | — | source-limited (libuv book/design docs not fetched; documented-level behavior only stated) | — |

**Counts:** inventoried 22 rows; documented 21; remaining 0; source-limited 1 (libuv-internal reaping mechanics — deliberately kept at the documented behavior level; no public API left undocumented).

## Related Topics

- [Python](../python.md) — `subprocess` −N vs Node's `(code, signal)` duality; `atexit` vs `'exit'`-event rules.
- [Java](../java.md) — `Process.waitFor` timeout returns `false` vs Node's `timeout`+`killSignal` auto-kill.
- [OCaml](../ocaml.md) — shell-string APIs (`Sys.command`, `Unix.open_process_in`) vs Node's `exec` — same injection lesson.
- [Signals overview](../signals/index.md) — SIGTERM/SIGINT defaults Node re-implements and re-raises.
- [Exit status conventions](../exit-status/index.md) — 128+N, reserved codes (2 = Bash builtin misuse).
- [Interface ledger](../interfaces/index.md) — pipes, `waitpid`, `setsid` beneath `child_process`.

## References

1. *process*, Node.js v22 API documentation (latest-v22.x), nodejs.org/docs/latest-v22.x/api/process.html (retrieved 2026-10).
2. *child_process*, Node.js v22 API documentation, nodejs.org/docs/latest-v22.x/api/child_process.html (retrieved 2026-10).
3. *worker_threads*, Node.js v22 API documentation, nodejs.org/docs/latest-v22.x/api/worker_threads.html (retrieved 2026-10).
