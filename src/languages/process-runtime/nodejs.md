# Node.js: Runtime Semantics, Standard Library, Process APIs, and Subprocesses

**Declared scope (retrieved 2026-10-13):** Node.js **v24.21.0 'Krypton'** — the current LTS
line per [`nodejs.org/dist/index.json`](https://nodejs.org/dist/index.json) (embedded
V8 13.6.233.17, libuv 1.52.1, OpenSSL 3.5.8; the current non-LTS release that day was
v26.11.1). All signatures and behavioral claims below were verified against the API
reference pinned to [`nodejs.org/docs/latest-v24.x/api/`](https://nodejs.org/docs/latest-v24.x/api/)
— `process.html`, `child_process.html`, `worker_threads.html`, `cluster.html`,
`events.html`, `os.html`, `util.html`, `modules.html`, `esm.html`, `cli.html` — plus the
event-loop guide at [`nodejs.org/learn`](https://nodejs.org/learn/asynchronous-work/event-loop-timers-and-nexttick)
and the libuv threadpool manual ([docs.libuv.org](https://docs.libuv.org/en/v1.x/threadpool.html)).
Reference platform: **Linux**; POSIX deltas are labeled inline, Windows differences are
brief and labeled. The JavaScript language surface follows the ECMAScript engine
(V8 13.6) as exposed by Node; layer labels: **[JS language]** for pure ECMAScript
semantics, **[Node documented]** for runtime/library contracts, **[libuv]** for
libuv-originated behavior, **[Linux/POSIX]** for OS-level behavior.

This chapter is the Section G deep dive. The exit/signal-scoped sibling chapter
[Node.js: Exit Status, Signals, and Process Lifecycle](../../linux/process-exit-signal/languages/nodejs.md)
(LG-NO-001…005) covers the same termination APIs from the Linux exit-status angle;
here we cover the *language and runtime* in full. See also the hub
[Process & Runtime Semantics by Language](./index.md), and the sibling chapters
[Python](./python.md), [Go](./go.md); Node-specific engine internals:
[Node.js](../javascript/nodejs.md), [V8](../javascript/v8.md).

Reading map: §1 language + event loop; §2 verified API inventory; §3 termination
doors; §4 signals; §5 `node:child_process`; §6 concurrency, pipes, leaks, races.

---

## 1. Syntax and Semantics

### 1.1 Functions, `this` binding, closures [JS language]

Three callable shapes matter for process code:

- **Declarations/expressions** get a dynamic `this` (call-site or `new`).
- **Arrow functions** capture `this` lexically from the enclosing scope and cannot be
  used as constructors. This is *the* correctness lever in Node callback code: a
  `process.on('SIGTERM', () => this.shutdown())` closes over the enclosing `this`,
  while `process.on('SIGTERM', function () { this.shutdown() })` has `this` equal to
  the `process` object (an `EventEmitter` dispatches with the emitter as receiver).
- **Closures** capture variable bindings, not values — a callback registered on
  `process` outlives the scope that created it, so captured locals live until the
  process exits unless the listener is removed (see §6.5 on listener leaks).

```js
// Expected: "t: 1" then "f: undefined" — the non-arrow listener loses `this`.
const obj = { t: 1, register() {
  process.on('arrow',   () => console.log('t:', this.t));
  process.on('regular', function () { console.log('f:', this.t); });
}};
obj.register();
process.emit('arrow'); process.emit('regular');
```

### 1.2 Classes, prototypes, and field initialization [JS language]

`class` declarations are prototypes + a real function under the hood: methods live on
`Class.prototype`, `static` on the constructor, and instance fields are installed by
the constructor (super first). Two process-relevant consequences:

- Field initializers run **before** the constructor body, so a field holding a
  rejected `Promise` (a classic unhandled-rejection source, see §1.8) rejects before
  any `.catch()` in the constructor body could attach.
- `class` bodies are strict mode; `throw` inside a getter called during construction
  propagates synchronously and becomes an uncaught exception on the loop (§3.6).

### 1.3 Promises: states, chaining, rejection [JS language]

A Promise is exactly one of *pending*, *fulfilled*, or *rejected*; transitions are
irreversible. Chaining with `.then/.catch/.finally` builds a derived promise each
step; a handler's return value resolves the derived promise, a thrown error rejects
it. Rejection propagates down the chain until a rejection handler is found; a chain
with no rejection handler makes the *final* promise rejected — and Node then classifies
it as unhandled (§1.8). `.finally(f)` passes the outcome through unchanged (`f`'s
return value is ignored unless it is a promise that rejects).

```js
// Expected: "A" then "B" — value flows through then; error jumps to catch.
Promise.resolve(1)
  .then(v => { console.log('A'); return v + 1; })
  .then(v => { throw new Error('boom'); })
  .catch(e => console.log('B', e.message === 'boom'));
```

### 1.4 async/await: sugar over promise chains [JS language]

An `async function` wraps its body in a promise: `return v` resolves it, `throw e`
rejects it. Each `await expr` suspends the function and reschedules the remainder as
a reaction on the awaited promise — semantically identical to `.then(...)`, which is
why an `await` inside a loop is a promise chain in disguise. Exceptions thrown in the
resumed code reject the enclosing promise; an `await` of a rejected promise throws at
the resume point, so `try/catch` works exactly as for synchronous code.

```js
// Expected: prints "tick" (a macrotask timer) AFTER "micro" —
// await resumption is a microtask and runs before timers.
(async () => { try { await Promise.reject(new Error('x')); } catch { console.log('caught'); } })();
queueMicrotask(() => console.log('micro'));
setTimeout(() => console.log('tick'), 0);
```

### 1.5 Errors: subclasses, `throw` vs rejection [JS language]

`Error` and subclasses (`TypeError`, `RangeError`, `ReferenceError`, …) capture a
`.stack` at construction. Node adds its own families: `SystemError`
(`err.syscall`, `err.code`, `err.errno` — e.g. `ENOENT` from spawn, §5.9),
`AbortError` (signal-driven termination, §5.10), and operation-code errors such as
`ERR_INVALID_ARG_TYPE` thrown by argument validation. Semantically:

- `throw` in synchronous code unwinds the stack to the nearest `try/catch`; nothing
  on the loop can intercept it → uncaught exception (§3.6).
- `throw` inside a `.then` callback or after an `await` rejects the current promise.
- The two meet in one place: `'uncaughtException'` fires with `origin` set to
  `'unhandledRejection'` when a rejected promise reaches the top under
  `--unhandled-rejections=throw|strict` (§3.7).

### 1.6 Modules: CommonJS `require` vs ESM `import` [Node documented]

Node supports two module systems with different evaluation models (documented in
[`modules.html`](https://nodejs.org/docs/latest-v24.x/api/modules.html) and
[`esm.html`](https://nodejs.org/docs/latest-v24.x/api/esm.html)):

- **CommonJS** (`require`, `module.exports`, `.cjs` or `.js` without
  `"type": "module"`): synchronous load-and-evaluate — dependencies are resolved,
  wrapped, evaluated *before* the requiring module continues; a module's exports are
  assigned incrementally during evaluation. `require` may be called conditionally.
- **ESM** (`import`/`export`, `.mjs` or `"type": "module"`): the full module graph is
  parsed, *then* instantiated and evaluated depth-first post-order. **Top-level
  `await` is ESM-only**; it suspends evaluation of the importing graph until the
  awaited promise settles.
- **`require(esm)`**: since v24.15.0 this is *no longer experimental* (unflagged since
  v23.0.0/v22.12.0/v20.19.0). It works only if the ESM "is fully synchronous (contains
  no top-level await)"; otherwise `ERR_REQUIRE_ASYNC_MODULE` is thrown
  ([modules.html#requireesm](https://nodejs.org/docs/latest-v24.x/api/modules.html)).

```js
// CJS: side effects of the dependency print BEFORE "main continues".
// a.js: console.log('dep');  main.cjs: require('./a'); console.log('main continues');
// ESM: "main continues" (or an earlier await resumption) prints first, then 'dep'.
```

Module resolution is a process-visible operation: the loader performs filesystem
access before evaluation, and a failed resolution throws (`Cannot find module …` /
`ERR_MODULE_NOT_FOUND`) — at `require` time synchronously, during ESM static loading
as a fatal startup error.

### 1.7 The event loop: phases, microtasks, `nextTick` vs `setImmediate` [Node documented]/[libuv]

The event loop is the *scheduler*: one JS thread executes a queue of callbacks per
phase, then advances ([the Node.js Event Loop](https://nodejs.org/learn/asynchronous-work/event-loop-timers-and-nexttick)).
Phases, in one iteration:

| Phase | Executes |
|---|---|
| **timers** | `setTimeout`/`setInterval` callbacks (timers can also run before entering the loop) |
| **pending callbacks** | I/O callbacks deferred to the next loop iteration (e.g. some TCP errors) |
| **idle, prepare** | internal only |
| **poll** | new I/O events; executes almost all I/O callbacks; blocks here when idle (unless `setImmediate` is pending or timers are due) |
| **check** | `setImmediate()` callbacks |
| **close callbacks** | e.g. `socket.on('close', …)` |

Documented ordering notes: since libuv 1.45.0 (Node 20), **timers run after the poll
phase** in each iteration (backwards-compatible with one timer run before entering);
"Between each run of the event loop, Node.js checks if it is waiting for any
asynchronous I/O or timers and shuts down cleanly if there are not any" — this is the
normal-termination path of §3.1.

**Microtasks vs macrotasks.** Promise reactions and `queueMicrotask` run on the
**microtask queue**, which is drained *immediately after the current operation on the
JS stack completes* — including between each phase. Timers, I/O callbacks,
`setImmediate`, and close callbacks are macrotasks. **`process.nextTick`** (added
v0.1.26) adds to the "next tick queue … fully drained after the current operation on
the JavaScript stack runs to completion and before the event loop is allowed to
continue". Per the v24 docs:

- In **CJS** modules, `nextTick` callbacks run **before** `queueMicrotask` ones.
- In **ESM** modules the order **reverses**: `queueMicrotask` callbacks run before
  `nextTick` ones, because module evaluation is itself processed as part of the
  microtask queue.

```js
// CJS file. Expected: nextTick, resolve, microtask — then (if loop kept alive) timers.
Promise.resolve().then(() => console.log('resolve'));
queueMicrotask(() => console.log('microtask'));
process.nextTick(() => console.log('nextTick'));
setTimeout(() => console.log('timer'), 0);
```

`process.nextTick` is marked **Stability: 3 - Legacy** (since v22.7.0/v20.18.0; the
docs say "Use queueMicrotask() instead"). An infinitely recursive `nextTick` or
microtask starves the loop entirely: I/O callbacks never run, and the process cannot
be exited by the normal drain path (§3.1).

### 1.8 Uncaught exceptions vs unhandled rejections [Node documented]

Default behaviors (verified in v24 docs; both are version-gated):

- **Uncaught exception** (an exception "bubbles all the way back to the event loop"):
  "By default, Node.js handles such exceptions by printing the stack trace to stderr
  and exiting with code 1, overriding any previously set `process.exitCode`"
  ([process.html#event-uncaughtexception](https://nodejs.org/docs/latest-v24.x/api/process.html#event-uncaughtexception)).
- **Unhandled rejection** (a Promise rejected "and no error handler is attached to the
  promise within a turn of the event loop"): with the default
  `--unhandled-rejections=throw` mode — the default **since v15.0.0** (flag added
  v12.0.0/v10.17.0; before v15 a warning was emitted) — an unhandled `'unhandledRejection'`
  hook raises the rejection "as an uncaught exception", i.e. print + exit 1.

Version archaeology for rejections (from the event's History): event added v1.4.1;
unhandled rejections emit a process warning since v6.6.0; not handling them
deprecated since v7.0.0; crash-by-default since v15.0.0. Both defaults were already in
force throughout the v18/v20/v22 LTS lines; v24 does not change them.

### 1.9 Normal vs exceptional termination [Node documented]

Normal termination: the loop drains (§3.1) → `'beforeExit'` → `'exit'` → OS exit with
`process.exitCode` (default 0). Exceptional termination: uncaught exception (exit 1 by
default), `process.exit(n)` (immediate), `process.abort()` (§3.5), fatal signal
(exit status 128+N, §3.2), or unhandled rejection in `throw` mode. The distinction
matters for cleanup: only the *drain* path and monitorable events give cleanup code a
chance to run; `SIGKILL` and `process.exit` give none.

### 1.10 Version deltas affecting in-scope semantics (v22 LTS → v24 LTS)

Verified deltas in the in-scope surface:

| Change | Versions | Effect |
|---|---|---|
| `require(esm)` no longer experimental | v24.15.0 (unflagged v23.0.0/v22.12.0) | synchronous ESM loadable from CJS without flags |
| `util.convertProcessSignalToExitCode(signal)` added | v24.14.0 | signal→POSIX exit-code mapping is now an API, not shell lore (§5.12) |
| `spawn`/`execFile`: "Passing `args` when `shell` is set to true is deprecated" | v23.11.0/v22.15.0 (DEP0190) | mixing args array with `shell: true` formally deprecated (§5.5) |
| `process.nextTick` Stability 3 - Legacy | v22.7.0/v20.18.0 | docs push `queueMicrotask()` |
| Timers after poll | libuv 1.45.0 / Node 20 | timer-vs-`setImmediate` ordering edge cases changed |
| Exit code 13 wording: "Unsettled Top-Level Await" | v24 docs (v22 said "Unfinished…") | same behavior, table text updated |

### 1.11 Misconceptions

- **"`process.exit()` flushes stdout first."** False: it "will force the process to
  exit as quickly as possible even if there are still asynchronous operations pending
  … including I/O operations to `process.stdout` and `process.stderr`" — output can be
  truncated/lost (§3.3).
- **"`process.exit()` is like `return` from main."** False: it runs `'exit'` listeners
  synchronously and terminates; it does not unwind the JS stack, does not run `finally`
  blocks, and does not drain the loop.
- **"Installing a `SIGINT` handler is additive."** False: it *replaces* the default —
  after `process.on('SIGINT', …)`, Ctrl+C no longer terminates (§4.2).
- **"`subprocess.killed === true` means the child exited."** False — it means
  `kill()` successfully sent a signal (docs verbatim, §5.8).
- **"GC cleans up child process handles."** False: Node does no finalizer-driven
  process cleanup (§6.8).

---

## 2. Standard-Library and Runtime API Inventory

All signatures below were transcribed from the v24 API reference on 2026-10-13
(`Added in` markers quoted from the docs). Stability markers follow the documented
scale (1-Stable, 2-Stable, 3-Legacy…). Only the in-scope surface is inventoried:
the `node:process`, `node:os`, `node:util`, and `node:events` APIs that bear on
process lifecycle, signals, and subprocess management.

### 2.1 `node:process` — the process object

| API | Canonical signature (v24) | Semantics / notes | Reference |
|---|---|---|---|
| `process.exit` | `process.exit([code])` | synchronous termination; v20.0.0: only `number`, or `string` that is an integer; default 0 | [process.html#processexitcode](https://nodejs.org/docs/latest-v24.x/api/process.html#processexit) |
| `process.exitCode` | `<integer> \| <string> \| <null> \| <undefined>` property | code used "when the process either exits gracefully, or is exited via `process.exit()` without specifying a code"; default `undefined` | [#processexitcode](https://nodejs.org/docs/latest-v24.x/api/process.html#processexitcode) |
| `process.abort` | `process.abort()` | "exit immediately and generate a core file"; not available in Worker threads; v0.7.0 | [#processabort](https://nodejs.org/docs/latest-v24.x/api/process.html#processabort) |
| `process.kill` | `process.kill(pid[, signal])` | signal sender (like `kill(2)`); `signal` default `'SIGTERM'`; throws if pid does not exist; signal `0` probes existence | [#processkillpid-signal](https://nodejs.org/docs/latest-v24.x/api/process.html#processkillpid-signal) |
| `process.pid` | `process.pid` → `<integer>` | PID of the process; v0.1.15 | [#processpid](https://nodejs.org/docs/latest-v24.x/api/process.html#processpid) |
| `process.nextTick` | `process.nextTick(callback[, ...args])` | next-tick queue; **Stability: 3 - Legacy** since v22.7.0/v20.18.0 | [#processnexttickcallback-args](https://nodejs.org/docs/latest-v24.x/api/process.html#processnexttickcallback-args) |
| `process.env` | `process.env` → `<Object>` | copy semantics: mutations are *not* reflected outside the process; workers get a copy (v11.14.0) | [#processenv](https://nodejs.org/docs/latest-v24.x/api/process.html#processenv) |
| `process.chdir` | `process.chdir(directory)` | synchronous `chdir(2)`; throws on failure; v0.1.17 | [#processchdirdirectory](https://nodejs.org/docs/latest-v24.x/api/process.html#processchdirdirectory) |
| `process.cwd` | `process.cwd()` → `<string>` | current working directory | [#processcwd](https://nodejs.org/docs/latest-v24.x/api/process.html#processcwd) |
| `process.umask` | `process.umask([mask])` | returns / sets file-mode creation mask; child processes inherit it; v0.1.19 | [#processumaskmask](https://nodejs.org/docs/latest-v24.x/api/process.html#processumaskmask) |
| `process.setuid` / `process.setgid` | `process.setuid(id)` / `process.setgid(id)` | id numeric or name; name resolution **blocks**; privileged (see §4.5) | [#processsetuidid](https://nodejs.org/docs/latest-v24.x/api/process.html#processsetuidid) |
| `process.initgroups` / `process.groups` | `process.initgroups(user, extraGroup)` | reads `/etc/group`, initializes group access list; requires root or `CAP_SETGID`; v0.9.4 | [#processinitgroupsuser-extragroup](https://nodejs.org/docs/latest-v24.x/api/process.html#processinitgroupsuser-extragroup) |
| events | `process.on('exit' \| 'beforeExit' \| 'uncaughtException' \| 'unhandledRejection' \| 'uncaughtExceptionMonitor' \| 'SIGINT' \| …, listener)` | `process` is an `EventEmitter`; event contracts in §3.8/§3.6/§4.1 | [#process-events](https://nodejs.org/docs/latest-v24.x/api/process.html#process-events) |

### 2.2 `node:os`, `node:util`, `node:events` (in-scope items only)

| API | Canonical signature (v24) | Semantics / notes | Reference |
|---|---|---|---|
| `os.availableParallelism` | `os.availableParallelism()` → `<integer>` | returns an estimate of the default parallelism a program should use; added v19.4.0/v18.14.0; docs: do **not** use `os.cpus().length` for this | [os.html#osavailableparallelism](https://nodejs.org/docs/latest-v24.x/api/os.html#osavailableparallelism) |
| `util.convertProcessSignalToExitCode` | `util.convertProcessSignalToExitCode(signal)` → `<number>` | signal name → POSIX exit code (128 + signal number); throws on invalid name; added **v24.14.0** | [util.html#utilconvertprocesssignaltoexitcodesignal](https://nodejs.org/docs/latest-v24.x/api/util.html#utilconvertprocesssignaltoexitcodesignal) |
| `events.setMaxListeners` | `events.setMaxListeners(n[, ...eventTargets])` | sets max listeners per event; with no targets sets the default for all newly created emitters; v15.4.0 | [events.html#eventssetmaxlistenersn-eventtargets](https://nodejs.org/docs/latest-v24.x/api/events.html#eventssetmaxlistenersn-eventtargets) |
| `events.defaultMaxListeners` | `<number>` property | "By default, a maximum of 10 listeners can be registered for any single event"; v0.11.2 | [events.html#eventsdefaultmaxlisteners](https://nodejs.org/docs/latest-v24.x/api/events.html#eventsdefaultmaxlisteners) |
| `events.EventEmitter` | `emitter.on(name, listener)` / `emitter.emit(name[, ...args])` | the substrate of `process` and `ChildProcess`; dispatch is synchronous on the emitting thread | [events.html#class-eventemitter](https://nodejs.org/docs/latest-v24.x/api/events.html#class-eventemitter) |

`util.parseArgs` and the wider `node:util` surface are out of scope here — they do not
interact with process lifecycle.

---

## 3. Process Creation and Termination

### 3.1 Normal termination: the loop drains

From the exit-codes section, verbatim: "Node.js will normally exit with a 0 status
code when no more async operations are pending." What keeps the loop alive is the set
of **referenced handles**: open sockets/files, active timers, IPC channels, signal
listeners, worker threads, referenced child processes. Every handle type that has an
`unref()` (`subprocess.unref()`, `worker.unref()`, `subprocess.channel.unref()`,
`port.unref()`) removes its keep-alive vote; the process then exits when the last
reference is dropped. "Between each run of the event loop, Node.js checks if it is
waiting for any asynchronous I/O or timers and shuts down cleanly if there are not
any" — after emitting `'beforeExit'` (§3.8), which may add more work.

```js
// Expected: prints "done", exits 0. The timer is the last handle; once it fires
// the loop is empty and the process exits — no process.exit() needed.
console.log('done');
setTimeout(() => {}, 100);
```

### 3.2 Exit-status range: the documented table

The v24 `process` docs exit-code table, condensed (see
[process.html#exit-codes](https://nodejs.org/docs/latest-v24.x/api/process.html#exit-codes)):

| Code | Meaning |
|---|---|
| `0` | normal exit (no pending async operations) |
| `1` | **Uncaught Fatal Exception** — uncaught exception not handled by a domain or `'uncaughtException'` handler |
| `2` | unused (reserved by Bash for builtin misuse) |
| `3`, `4`, `10` | internal JavaScript parse/evaluation/run-time failure during bootstrapping (rare) |
| `5` | Fatal Error — fatal unrecoverable error in V8, message prefixed `FATAL ERROR` |
| `6`, `7` | internal exception-handler failures |
| `8` | unused (previously sometimes uncaught exception) |
| `9` | **Invalid Argument** — unknown option or option missing a value |
| `12` | **Invalid Debug Argument** — invalid `--inspect` port |
| `13` | **Unsettled Top-Level Await** — top-level `await` promise never settled |
| `14` | **Snapshot Failure** — V8 startup snapshot build failed |
| `>128` | **Signal Exits** — `128 + signal number` (e.g. `SIGABRT`=6 → 134); "a standard POSIX practice" |

### 3.3 `process.exit([code])` — stops immediately

Verified contract (added v0.1.13; v20.0.0 restricts `code` to numbers or integer
strings): the method "instructs Node.js to terminate the process **synchronously**
with an exit status of `code`. If `code` is omitted, exit uses either the 'success'
code 0 or the value of `process.exitCode` if it has been set. Node.js will not
terminate until all the `'exit'` event listeners are called." And:

> "Calling `process.exit()` will force the process to exit as quickly as possible even
> if there are still asynchronous operations pending that have not yet completed
> fully, including I/O operations to `process.stdout` and `process.stderr`."

The docs' own warning: stdout writes "are sometimes asynchronous and may occur over
multiple ticks of the Node.js event loop. Calling `process.exit()`, however, forces
the process to exit **before** those additional writes to stdout can be performed" —
their example of misuse is `printUsageToStdout(); exit(1);`. Whether stdout writes are
synchronous depends on the destination (pipe vs TTY; §6.4), which is why
truncation-on-`exit` is intermittent and hard to reproduce in a debugger. The docs'
prescription: set `process.exitCode` instead, or — "If it is necessary to terminate
the Node.js process due to an error condition, throwing an uncaught error and
allowing the process to terminate accordingly is safer than calling `process.exit()`."

```js
// WRONG (docs' example): may print nothing on a piped stdout.
console.log('usage: …'); process.exit(1);
// RIGHT: loop drains after the synchronous work; code 1 is used at exit.
console.log('usage: …'); process.exitCode = 1;
```

### 3.4 `process.exitCode` — the preferred channel

Type `<integer> | <string> | <null> | <undefined>`, default `undefined` (added
v0.11.8): "A number which will be the process exit code, when the process either exits
gracefully, or is exited via `process.exit()` without specifying a code." An explicit
`process.exit(n)` argument wins over a previously set `exitCode`. Node itself may set
it implicitly on unrecoverable errors. Combining with async work is the standard
graceful-shutdown shape:

```js
// Expected: "cleanup done" printed, exit status 3 — the loop drains naturally
// after the async cleanup, then 'exit' sees exitCode = 3.
process.on('SIGTERM', () => {
  process.exitCode = 3;
  doAsyncCleanup().then(() => console.log('cleanup done'));
  // nothing else scheduled → drain → exit 3
});
```

### 3.5 `process.abort()`

Added v0.7.0: "The `process.abort()` method causes the Node.js process to exit
immediately and generate a core file. This feature is not available in Worker
threads." It is the JS-callable analog of `abort(3)`: no cleanup, no `'exit'`-event
guarantees for pending I/O, core dump per the platform's core settings
([Linux core(5)](../../linux/process-exit-signal/languages/nodejs.md) discusses the
OS side). `'exit'` listeners still run before the abort in practice, but the docs
make no promise beyond "exit immediately"; do not rely on flushing.

### 3.6 Uncaught exceptions: default, monitor, capture

- **Default:** print stack trace to stderr, exit code **1**, overriding
  `process.exitCode` (§1.8, §3.2).
- **`'uncaughtException'` handler** `(err, origin) => {}` (added v0.1.18; `origin`
  added v12.0.0/v10.17.0): "Adding a handler for the `'uncaughtException'` event
  overrides this default behavior" — with a handler present the process exits **0**
  unless the handler sets `process.exitCode` or calls `process.exit()`. The docs'
  warning is blunt: the event "is a crude mechanism … used only as a last resort";
  "Exceptions thrown from within the event handler will not be caught. Instead the
  process will exit with a non-zero exit code and the stack trace will be printed.
  This is to avoid infinite recursion." Correct use: "perform synchronous cleanup of
  allocated resources … It is not safe to resume normal operation."
- **`'uncaughtExceptionMonitor'`** (v13.7.0/v12.17.0): "emitted before an
  `'uncaughtException'` event is emitted or a hook installed via
  `process.setUncaughtExceptionCaptureCallback()` is called"; it "does not change the
  behavior … The process will still crash if no `'uncaughtException'` listener is
  installed."

### 3.7 Unhandled rejections: `'unhandledRejection'` and `--unhandled-rejections`

Event signature `(reason, promise) => {}` (added v1.4.1). Emitted "whenever a Promise
is rejected and no error handler is attached to the promise within a turn of the
event loop." "If an `'unhandledRejection'` event is emitted but not handled it will be
raised as an uncaught exception." The full mode list
([cli.html#--unhandled-rejectionsmode](https://nodejs.org/docs/latest-v24.x/api/cli.html#--unhandled-rejectionsmode)):

| Mode | Behavior |
|---|---|
| `throw` (default since v15.0.0) | emit `'unhandledRejection'`; if no hook, raise as uncaught exception |
| `strict` | raise as uncaught exception; if handled, emit `'unhandledRejection'` |
| `warn` | always trigger a warning, do not crash |
| `warn-with-error-code` | emit event; if no hook, warn and set exit code 1 |
| `none` | silence all warnings |

Additionally: "If a rejection happens during the command line entry point's ES module
static loading phase, it will always raise it as an uncaught exception."

### 3.8 `'exit'` and `'beforeExit'` events

**`'exit'`** (v0.1.7), listener `(code) => {}`: emitted when the process is about to
exit because of either "The `process.exit()` method being called explicitly" or "The
Node.js event loop no longer having any additional work to perform." "There is no way
to prevent the exiting of the event loop at this point, and once all `'exit'`
listeners have finished running the Node.js process will terminate." **"Listener
functions must only perform synchronous operations"** — the docs show a
`setTimeout` inside an `'exit'` listener that "will never occur".

**`'beforeExit'`** (v0.11.12), listener `(code) => {}` invoked "with the value of
`process.exitCode` passed as the only argument": emitted "when Node.js empties its
event loop and has no additional work to schedule", and a listener "can make
asynchronous calls, and thereby cause the Node.js process to continue." Constraints,
verbatim: "The `'beforeExit'` event is **not emitted** for conditions causing explicit
termination, such as calling `process.exit()` or uncaught exceptions." Each
successfully re-scheduled batch of work leads to another `'beforeExit'` when the loop
drains again (bounded only by when your code stops scheduling); the docs warn it
"should not be used as an alternative to the `'exit'` event unless the intention is to
schedule additional work."

### 3.9 Worker threads and cluster workers vs the main process

A **Worker** (thread) dying does not end the process: the Worker emits `'exit'` with
`exitCode` (1 if terminated, the passed code if it called `process.exit()`) and "This
is the final event emitted by any Worker instance"
([worker_threads.html](https://nodejs.org/docs/latest-v24.x/api/worker_threads.html)).
Conversely, `process.exit()` in the main thread tears the whole process down. Signals
are "not available on Worker threads" and `process.abort()` is unavailable there.
**Cluster** workers are separate *processes* — "The worker processes are spawned using
the `child_process.fork()` method" — so a crashed worker is recovered by
`'exit'`-event supervision in the primary, not by in-process handlers; see
[cluster.html](https://nodejs.org/docs/latest-v24.x/api/cluster.html) and §6.3.

---

## 4. Signals and OS Interaction

### 4.1 Signal events: registration and default replacement

`process.on('SIGINT', (signal) => {})` — "The signal handler will receive the
signal's name (`'SIGINT'`, `'SIGTERM'`, etc.) as the first argument" and "Signals are
not available on Worker threads." The decisive semantics, verbatim from
[process.html#signal-events](https://nodejs.org/docs/latest-v24.x/api/process.html#signal-events):

> "'SIGTERM' and 'SIGINT' have default handlers on non-Windows platforms that reset
> the terminal mode before exiting with code 128 + signal number. **If one of these
> signals has a listener installed, its default behavior will be removed (Node.js
> will no longer exit).**"

So attaching a listener *replaces* the default disposition: a process with a `SIGINT`
listener ignores Ctrl+C until the listener re-raises or exits. Node's own cleanup
path for these signals is documented in the child `'exit'` event: "Node.js
establishes signal handlers for SIGINT and SIGTERM and Node.js processes will not
terminate immediately due to receipt of those signals. Rather, Node.js will perform a
sequence of cleanup actions and then will re-raise the handled signal."

### 4.2 The documented signal catalog (platform deltas)

| Signal | Node behavior (v24 docs) |
|---|---|
| `SIGINT` | terminal Ctrl+C supported on all platforms; "not generated when terminal raw mode is enabled" |
| `SIGTERM` | default handler on non-Windows (exit 128+15); "**'SIGTERM' is not supported on Windows, it can be listened on**" |
| `SIGKILL` | "**cannot have a listener installed, it will unconditionally terminate Node.js on all platforms**" |
| `SIGSTOP` | cannot have a listener installed |
| `SIGBREAK` | "delivered on Windows when Ctrl + Break is pressed. On non-Windows platforms, it can be listened on, but there is no way to send or generate it" |
| `SIGHUP` | default terminate on non-Windows; listener removes default; on Windows, console-close generates it and "Node.js will be unconditionally terminated by Windows about 10 seconds later" |
| `SIGPIPE` | "ignored by default. It can have a listener installed" |
| `SIGUSR1` | "reserved by Node.js to start the debugger"; installing a listener may interfere |
| `SIGWINCH` | console resize; Windows delivers only under specific tty conditions |
| `SIGBUS`, `SIGFPE`, `SIGSEGV`, `SIGILL` | "when not raised artificially using `kill(2)`, inherently leave the process in a state from which it is not safe to call JS listeners" |

Signal `0` "can be sent to test for the existence of a process, it has no effect if
the process exists, but will throw an error if the process does not exist."

### 4.3 `process.kill(pid[, signal])`

Added v0.0.6. "Even though the name of this function is `process.kill()`, it is really
just a signal sender, like the kill system call." Throws if the target pid does not
exist; signal `0` probes existence; on "Windows platforms will throw an error if the
pid is used to kill a process group" — so the POSIX pattern
`process.kill(-pid, 'SIGTERM')` (negative pid = process group, `kill(2)`) is
POSIX-only. The pid you pass is any OS pid, not just children — including
`process.pid` for self-signaling:

```js
// Expected: "Got SIGHUP signal." then "Exiting." (docs' example, abbreviated)
process.on('SIGHUP', () => console.log('Got SIGHUP signal.'));
setTimeout(() => { console.log('Exiting.'); process.exit(0); }, 100);
process.kill(process.pid, 'SIGHUP');
```

### 4.4 Signals and the event loop

A registered signal listener is itself an active handle: **a process that would
otherwise drain stays alive because it listens on signals.** Unlike child processes
and workers there is **no public `unref()` for signal events**; the mitigations are
(1) `process.removeListener(...)`/`removeAllListeners(...)` when the handler is no
longer needed, restoring the default disposition, and (2) careful design in
one-shot CLI tools where the signal listener *is* the keep-alive. There is no
async-signal-safety concept for JS here (§4.6).

### 4.5 Credentials, cwd, umask — synchronous OS mutations on the loop thread

`process.setuid(id)` / `process.setgid(id)` / `process.initgroups(user, extraGroup)` /
`process.umask(mask)` / `process.chdir(directory)` wrap `setuid(2)`, `setgid(2)`,
`initgroups(3)`, `umask(2)`, `chdir(2)` and are **synchronous** — they mutate OS-level
process state immediately and block the loop for the duration. Documented notes:

- `initgroups()` "reads the `/etc/group` file and initializes the group access list …
  a privileged operation that requires that the Node.js process either have root
  access or the CAP_SETGID capability."
- If a *username/group name* string is passed to `setuid`/`setgid`, the method
  "blocks while resolving the associated numeric ID".
- `umask(mask)` "sets the Node.js process's file mode creation mask. Child processes
  inherit the mask from the parent process. Returns the previous mask." (Relevant to
  §5: a spawned child's file-creation mode is the parent's umask unless the child
  changes it.)
- `chdir()` "changes the current working directory … or throws an exception if doing
  so fails" — and the new cwd is inherited by subsequently spawned children (§5.7).

Dropping privileges has the classic POSIX ordering constraint, visible in the docs'
own example: `initgroups` **before** `setgid`, then `setuid`, because both group and
user IDs must be changed while still privileged.

### 4.6 What replaces async-signal-safety

[Linux/POSIX] signal handlers must be async-signal-safe; **JS has no such constraint
because handlers are not OS handlers.** Node installs a small set of OS-level signal
handlers (libuv); receipt of a signal is turned into an event, and the *JS* listener
runs later as ordinary code on the event loop — single-threaded, no reentrancy, full
access to the heap. Two consequences: (1) JS listeners run only when the loop is
free — a loop blocked by a synchronous call (§5.7) delays signal handling
indefinitely; (2) the signals marked unsafe in §4.2 (`SIGSEGV` etc.) cannot be handled
in JS because at that point *no* JS can run safely. See the OS-side handler/receiver
split in [Exit Status, Signals, and Process Lifecycle](../../linux/process-exit-signal/languages/nodejs.md).

### 4.7 Windows deltas (brief)

"Windows does not support signals so has no equivalent to termination by signal, but
Node.js offers some emulation with `process.kill()`, and `subprocess.kill()`: sending
`SIGINT`, `SIGTERM`, and `SIGKILL` will cause the unconditional termination of the
target process, and afterwards, subprocess will report that the process was terminated
by signal." Console events (Ctrl+C, Ctrl+Break, window close) map to `SIGINT`,
`SIGBREAK`, `SIGHUP` as in §4.2.

---

## 5. Subprocess and Child-Process Management

`node:child_process` provides four asynchronous creation functions — "Each of these
alternatives are implemented on top of `child_process.spawn()` or
`child_process.spawnSync()`" — plus three synchronous variants
([child_process.html](https://nodejs.org/docs/latest-v24.x/api/child_process.html)).

### 5.1 The four creation APIs

| API | Canonical signature (v24) | Added in | Shell? | Returns / completes |
|---|---|---|---|---|
| `spawn` | `child_process.spawn(command[, args][, options])` | v0.1.90 | only if `options.shell` | `<ChildProcess>`, event-driven |
| `exec` | `child_process.exec(command[, options][, callback])` | v0.1.90 | **always** (`/bin/sh` or `ComSpec`) | `<ChildProcess>` + buffered `callback(error, stdout, stderr)` |
| `execFile` | `child_process.execFile(file[, args][, options][, callback])` | v0.1.91 | no (by default) | `<ChildProcess>` + buffered callback |
| `fork` | `child_process.fork(modulePath[, args][, options])` | v0.5.0 | no | `<ChildProcess>` with IPC channel |

### 5.2 `spawn` options in depth (verified v24)

From the spawn options table (version markers from the History block):

| Option | Type / default | Semantics |
|---|---|---|
| `cwd` | `<string>` \| `<URL>`; default inherit | working directory of the child; if given but nonexistent, child "emits an ENOENT error and exits immediately. ENOENT is also emitted when the command does not exist" |
| `env` | `<Object>`; default `process.env` | child environment; "undefined values in env will be ignored" |
| `argv0` | `<string>` (v6.4.0) | "Explicitly set the value of argv[0] sent to the child process" |
| `stdio` | `<Array>` \| `<string>` | §5.3 |
| `detached` | `<boolean>` | §5.4 |
| `uid`, `gid` | `<number>` | "Sets the user/group identity of the process (see setuid(2)/setgid(2))" — set pre-exec, POSIX; invalid ids surface as spawn `'error'` |
| `serialization` | `'json'` \| `'advanced'` (v13.2.0/v12.16.0) | IPC serialization kind (§5.6) |
| `shell` | `<boolean>` \| `<string>`; default `false` (v5.7.0) | "If true, runs command inside of a shell. Uses '/bin/sh' on Unix, and `process.env.ComSpec` on Windows" |
| `windowsVerbatimArguments` | `<boolean>`; default `false`; "Ignored on Unix" | no quoting/escaping on Windows; auto-true when shell is CMD |
| `windowsHide` | `<boolean>`; default `false` (v8.8.0) | hide the subprocess console window |
| `signal` | `<AbortSignal>` (v15.5.0/v14.17.0) | "allows aborting the child process using an AbortSignal" |
| `timeout` | `<number>` (v15.13.0/v14.18.0) | "In milliseconds the maximum amount of time the process is allowed to run. Default: undefined" |
| `killSignal` | `<string>` \| `<integer>`; default `'SIGTERM'` (v15.11.0/v14.18.0 for abort) | signal used when killed "by timeout or abort signal" |

Note what is **absent** from async `spawn`: `maxBuffer` is *not* a spawn option — it
exists only on the buffering APIs (`spawnSync`, `exec`, `execFile` and their sync
variants, §5.7). A streaming `spawn` never buffers, so it cannot overflow.

### 5.3 `options.stdio` — the fd plumbing

Default `'pipe'` = `['pipe','pipe','pipe']`. String shorthands: `'pipe'`,
`'overlapped'` (Windows overlapped I/O; "exactly the same as 'pipe' on non-Windows
systems"), `'ignore'` (`['ignore','ignore','ignore']`), `'inherit'`
(`['inherit','inherit','inherit']` or `[0,1,2]`). Array form: "each index corresponds
to an fd in the child. The fds 0, 1, and 2 correspond to stdin, stdout, and stderr…
**Additional fds can be specified to create additional pipes between the parent and
child**"; values per fd:

- `'pipe'` — parent end exposed as `subprocess.stdio[fd]`; the docs stress these "are
  not actual Unix pipes and therefore the child process can not use them by their
  descriptor files, e.g. `/dev/fd/2` or `/dev/stdout`".
- `'ipc'` — "Create an IPC channel for passing messages/file descriptors between
  parent and child. A ChildProcess may have at most one IPC stdio file descriptor."
- `'ignore'` — fd connected to `/dev/null` (child sees an open-but-empty fd).
- `'inherit'` (or numeric fd) — pass the parent's fd (or any fd number) through;
  numeric fds > 2 give arbitrary **fd inheritance**.

### 5.4 `options.detached`: process groups, setsid, and the unref pattern

Verbatim: "On non-Windows platforms, if `options.detached` is set to `true`, the child
process will be made the **leader of a new process group and session**" (i.e.
`setsid(2)`; see [options.detached](https://nodejs.org/docs/latest-v24.x/api/child_process.html#optionsdetached)).
"By default, the parent will wait for the detached child process to exit. To prevent
the parent process from waiting … use the `subprocess.unref()` method." And the
documented long-running-process pattern — the child "will not stay running in the
background after the parent exits unless it is provided with a stdio configuration
that is not connected to the parent":

```js
const { spawn } = require('node:child_process');
const subprocess = spawn(process.argv[0], ['child_program.js'], {
  detached: true,
  stdio: 'ignore',          // not connected to the parent's terminal
});
subprocess.unref();          // parent's loop no longer waits for the child
```

Because the detached child leads its own group, signals to the whole group from the
parent use the POSIX negative-pid form `process.kill(-subprocess.pid, 'SIGTERM')`
(§4.3; Windows throws on group pids). Orphaning: without `detached`, a child whose
parent dies is reparented to init and keeps running unless the group/session semantics
or an OS-level parent-death mechanism applies — Node has no built-in `PDEATHSIG`
option (contrast [Go's `Pdeathsig`](./go.md)).

### 5.5 `exec`: shell semantics, buffering, injection

`exec(command[, options][, callback])` — "Spawns a shell then executes the command
within that shell, **buffering any generated output**." Shell default: `'/bin/sh'` on
Unix, `process.env.ComSpec` on Windows. The docs' security paragraph is categorical:
"**Never pass unsanitized user input to this function.** Any input containing shell
metacharacters may be used to trigger arbitrary command execution." Also: "Unlike the
`exec(3)` POSIX system call, `child_process.exec()` does not replace the existing
process and uses a shell to execute the command."

- Callback `(error, stdout, stderr)`: on success `error` is `null`; on failure
  `error.code` is the child's exit code and `error.signal` "will be the signal that
  terminated the process". Non-zero exit ≠ JS exception: the callback fires either
  way.
- `maxBuffer` default **`1024 * 1024`** (1 MiB) per stream; "If exceeded, the child
  process is terminated and any output is truncated" (with the documented "maxBuffer
  and Unicode" caveat: truncation may split multi-byte characters).
- `timeout` (default 0) kills the child with `killSignal` if it runs longer.
- AbortSignal since v15.4.0.
- Promisified form exists via `util.promisify` (resolves `{stdout, stderr}`).

```js
// Expected: err non-null (exit code 1 via /bin/sh), stderr contains 'No such file'.
exec('cat missing-file', (err, stdout, stderr) => console.log(err.code, !!stderr));
// Injection example (docs): input `"The \\$HOME variable is $HOME"` is shell-interpreted.
```

### 5.6 `execFile` and `fork`

**`execFile(file[, args][, options][, callback])`** — "similar to `child_process.exec()`
except that it spawns the command directly **without first spawning a shell** by
default"; same buffered callback, same 1 MiB `maxBuffer`. Windows note: ".bat and .cmd
files are not executable on their own without a terminal, and therefore cannot be
launched using `child_process.execFile()`" — use `exec` or `spawn` with a shell.
`execFile` with `shell` set falls under DEP0190 ("Passing `args` when `shell` is set to
true is deprecated", v23.11.0/v22.15.0) — an argument array is only well-defined for
the no-shell path.

**`fork(modulePath[, args][, options])`** — "spawns a new Node.js process and invokes
a specified module with an IPC communication channel established that allows sending
messages between parent and child." Verified option deltas beyond spawn's:
`execPath` ("Executable used to create the child process"), `execArgv` (default
`process.execArgv` — Node's own flags propagate!), `silent` ("If `true`, stdin, stdout,
and stderr of the child process will be piped to the parent process, otherwise they
will be inherited"), `serialization` (`'json'` default; `'advanced'` — the
structured-clone-based channel that "can contain data that JSON is not able to
represent"). The child side is symmetric: `process.send()`, `process.on('message')`,
`process.disconnect()` (the `process` events `'message'`/`'disconnect'` exist "If the
Node.js process is spawned with an IPC channel").

```js
// parent.js                          // child.js (same dir)
const { fork } = require('node:child_process');
const child = fork('./child.js');
child.on('message', (m) => { console.log('from child:', m); child.disconnect(); });
child.send({ hello: 'world' });
// child.js: process.on('message', m => process.send({ echo: m.hello }));
// Expected: "from child: { echo: 'world' }", then child exits 0 once its loop drains.
```

**Cancellation/exit semantics of the IPC channel:** `subprocess.disconnect()` "Closes
the IPC channel between parent and child processes, allowing the child process to exit
gracefully once there are no other connections keeping it alive"; `connected` becomes
`false`; the `'disconnect'` event fires "when there are no messages in the process of
being received." An open IPC channel is a live handle — a forked child that never gets
`disconnect()` keeps the *child's* loop alive even after its work is done (§6.5), and
`subprocess.channel.ref()/unref()` (v7.1.0) toggle whether the channel keeps the
*parent's* loop alive.

### 5.7 The synchronous variants: `spawnSync`, `execFileSync`, `execSync`

All three (added v0.11.12) **block the Node.js event loop** until the child exits —
the docs: "the function will not return until the child process has fully closed" and
the family "can have significant impact on performance due to stalling the event loop
while spawned processes complete." While blocked: no JS runs — timers, I/O callbacks,
*and signal listeners* are all deferred (§4.6).

- **`spawnSync(command[, args][, options])`** returns
  `{ pid, output, stdout, stderr, status, signal, error }`; `status` is
  `<number> | <null>` ("exit code … or null if the subprocess terminated due to a
  signal"), `signal` the dual, `error` set "if the child process failed or timed out".
  Defaults: `encoding: 'buffer'`, `maxBuffer: 1024 * 1024` (1 MiB) — over-limit means
  "the child process is terminated and any output is truncated". `input` "will be
  passed as stdin to the spawned process … Supplying this value will override
  `stdio[0]`".
- **`execFileSync(file[, args][, options])`** / **`execSync(command[, options])`** —
  sync forms of `execFile`/`exec`: `execSync` still goes through a shell (same
  injection hazard), both return captured stdout with `encoding: 'utf8'` default.

```js
// Expected: blocks ~100 ms; prints status 7. Everything else on the loop waits.
const r = spawnSync('node', ['-e', 'setTimeout(()=>process.exit(7),100)']);
console.log('status', r.status, 'signal', r.signal); // status 7 signal null
```

### 5.8 The `ChildProcess` surface

Verified members (all on `child_process.html`):

| Member | Signature / type | Contract (docs, condensed) |
|---|---|---|
| `pid` | `<integer> \| <undefined>` (v0.1.90) | "If the child process fails to spawn due to errors, then the value is `undefined` and `error` is emitted" |
| `kill` | `subprocess.kill([signal])` → `<boolean>` (v0.1.90) | sends `signal`, default `'SIGTERM'`; "returns `true` if `kill(2)` succeeds, and `false` otherwise" |
| `killed` | `<boolean>` (v0.5.10) | "indicates whether the child process successfully received a signal from `subprocess.kill()`. **The `killed` property does not indicate that the child process has been terminated.**" |
| `exitCode` | `<integer>` \| `null` | exit code; `null` while running; `null` + `signalCode` set when signal-terminated |
| `signalCode` | `<string>` \| `null` | signal received by the child, else null |
| `ref` / `unref` | `subprocess.ref()` / `subprocess.unref()` (v0.7.10) | unref removes the child from the loop's reference count "allowing the parent to exit independently of the child, unless there is an established IPC channel" |
| `connected` | `<boolean>` (v0.7.2) | false after `disconnect()`; no more messages |
| `disconnect` | `subprocess.disconnect()` (v0.7.2) | closes the IPC channel; child may call `process.disconnect()` too |
| `send` | `subprocess.send(message[, sendHandle[, options]][, callback])` → `<boolean>` (v0.5.9; boolean flow-control since v5.0.0) | false = channel full/closed (backpressure signal); `sendHandle` passes servers/sockets |
| `stdio` | `<Array>` (v0.7.10) | sparse array of pipe streams per `'pipe'` fd; `[0],[1],[2]` aliased as `stdin`,`stdout`,`stderr`; `null` for non-pipe fds |
| `spawnargs` | `<Array>` | "the full list of command-line arguments the child process was launched with" |
| `spawnfile` | `<string>` | the executable file name |
| `channel` | `<object \| null>`; `channel.ref()/unref()` (v7.1.0) | IPC channel handle; unref "makes the IPC channel [not] keep the event loop of the parent process [active]" |

Events on the child (§5.9): `'exit'`, `'close'`, `'error'`, `'message'` (v0.5.9),
`'disconnect'` (v0.7.2), `'spawn'` ("emitted once the child process has spawned
successfully", v15.1.0/v14.17.0 — the guarantee that `subprocess.stdio` streams are
set).

### 5.9 `'exit'` vs `'close'` vs `'error'` — the exact documented rules

- **`'exit'`** `(code, signal)`: emitted "after the child process ends". "If the
  process exited, `code` is the final exit code of the process, otherwise `null`. If
  the process terminated due to receipt of a signal, `signal` is the string name of
  the signal, otherwise `null`. **One of the two will always be non-null.**" And the
  stream caveat: "When the `'exit'` event is triggered, child process stdio streams
  **might still be open**." (The docs also note the reaping link: "See `waitpid(2)`".)
- **`'close'`** `(code, signal)`: "emitted after a process has ended **and the stdio
  streams of a child process have been closed**. This is distinct from the `'exit'`
  event, since multiple processes might share the same stdio streams. **The `'close'`
  event will always emit after `'exit'` was already emitted, or `'error'` if the child
  process failed to spawn.**"
- **`'error'`**: emitted whenever (1) "The process could not be spawned"
  (`ENOENT`, bad `uid`/`gid`, cwd missing), (2) "The process could not be killed",
  (3) "Sending a message to the child process failed", (4) "The child process was
  aborted via the `signal` option". "The `'exit'` event **may or may not** fire after
  an error has occurred. When listening to both the `'exit'` and `'error'` events,
  guard against accidentally invoking handler functions multiple times."

The ordering contract is therefore: `'error'` (spawn failure) may be followed by
nothing; a successful run is `'exit'` then `'close'`; a signal death is still
`'exit'` then `'close'` with `code === null`. The classic race: code that reads child
stdout *after* `'exit'` can lose the tail — drain to `'close'` instead:

```js
const child = spawn('sh', ['-c', 'echo out; echo err >&2; exit 3']);
child.on('exit',  (code, signal) => console.log('exit', code, signal)); // exit 3 null
child.on('close', (code, signal) => console.log('close', code, signal)); // close 3 null
// Expected output order: 'exit 3 null' then 'close 3 null'.
```

Note the spawn-failure vs exit distinction: a child that spawns fine and exits
non-zero emits `'exit'` (code N) — **not** `'error'`; `'error'` with `ENOENT` means
the process never started. Idiomatically, `err.code === 'ENOENT'` (a
`SystemError`-family `Error` with `syscall: 'spawn …'`) is the spawn-failure
signature.

### 5.10 Timeout, AbortSignal, and the manual kill ladder

- `timeout` (v15.13.0/v14.18.0): after the limit, Node kills the child with
  `killSignal` (default `'SIGTERM'`); the subsequent `'exit'`/`'close'` report
  accordingly (`signal` set, `code` null) — for `exec`, `error.killed`/`error.signal`
  describe it. There is **no automatic SIGKILL escalation**: `timeout` sends exactly
  one signal.
- `signal: <AbortSignal>` (v15.5.0/v14.17.0): aborting kills with `killSignal`
  (abort-specific killSignal since v15.11.0/v14.18.0) and produces an `AbortError`
  (§1.5).
- The documented-gap ladder for unkillable children (SIGTERM-swallowing processes):
  send `kill()` (SIGTERM) → await `'close'` with a timer → `kill('SIGKILL')` after the
  grace period. Since "SIGKILL cannot have a listener" (§4.2), the SIGKILL is
  terminal by OS fiat — [Linux/POSIX] `kill(2)` semantics.

```js
// Expected: 'went down' (SIGTERM respected) OR 'hard kill' if the child ignores it.
const c = spawn('maybe-stubborn');
const t = setTimeout(() => { c.kill('SIGKILL'); console.log('hard kill'); }, 3000);
c.on('close', (code, signal) => { clearTimeout(t); console.log('went down', code, signal); });
c.kill(); // SIGTERM
```

### 5.11 Zombies, orphans, reaping [libuv]/[Linux/POSIX]

Node's exit event links reaping to the OS contract ("See `waitpid(2)`"): the libuv
process handle `waitpid()`s the child after `'exit'` fires, so **no zombie remains
once the parent has seen `'exit'`/'close'** — Node has no explicit `wait()`. If the
parent is blocked synchronously (§5.7), reaping waits with it. If the *parent* exits
first, children are orphaned and reparented to init/subreaper; they keep running —
Node provides no parent-death signal option; use `detached` + your own supervision or
an OS mechanism (§5.4, contrast [Go](./go.md) `Pdeathsig`, [Python](./python.md)
`prctl` via `preexec_fn`).

### 5.12 Exit-status retrieval and the code↔signal mapping

Retrieval points: `'exit'`/`'close'` `(code, signal)` (exactly one non-null, §5.9);
`subprocess.exitCode`/`subprocess.signalCode` while running; `spawnSync` result's
`status`/`signal`; `exec`'s `error.code`/`error.signal`. Mapping a signal death to
the POSIX convention (128 + signal number) is now a first-class API, added
**v24.14.0**: `util.convertProcessSignalToExitCode('SIGTERM') // 143`, and the child
`'exit'` docs point to it explicitly for the `code === null` case. The OS layer of
this mapping (wait-status `WIFSIGNALED`/`WTERMSIG` encoding) is the same one the
[Linux exit chapter](../../linux/process-exit-signal/index.md) covers for every
language.

---

## 6. Concurrency and Resource Semantics

### 6.1 The concurrency model: one JS thread plus the libuv threadpool

User JS runs on **one thread**; all process-level APIs (`process`, `ChildProcess`,
`EventEmitter` dispatch) are therefore single-threaded and need no locks. The
**threadpool** is a [libuv] mechanism: "Its default size is 4, but it can be changed
at startup time by setting the `UV_THREADPOOL_SIZE` environment variable to any value
(the absolute maximum is 1024)" and it is "global and shared across all event loops"
([libuv threadpool](https://docs.libuv.org/en/v1.x/threadpool.html)). It backs
filesystem, crypto, and `dns.lookup` work — which matters for process ops only
indirectly (e.g. a saturated threadpool delays the fs reads of a module loader or a
spawn's path resolution), *not* for the process management itself: `spawn` and signal
delivery are loop-side operations. For real CPU parallelism Node offers
`worker_threads` (§6.2); for parallelism *sizing*, `os.availableParallelism()`
(§2.2) — the docs explicitly warn against `os.cpus().length` for that purpose.

### 6.2 `worker_threads` (verified surface)

`new Worker(filename[, options])` (v10.5.0; Stability 2 - Stable). "Unlike
`child_process` or `cluster`, `worker_threads` can share memory" via transferred
`ArrayBuffer`s / `SharedArrayBuffer`. Events: `'online'`, `'message'`,
`'messageerror'`, `'error'`, `'exit'`. Termination:

- **`worker.terminate()`** — v10.5.0; since v12.5.0 "returns a Promise" (callback
  form deprecated) and "Terminating is now a fully asynchronous operation."
- **`'exit'`** `(exitCode)`: "If the worker exited by calling `process.exit()`, the
  `exitCode` parameter is the passed exit code. If the worker was terminated, the
  exitCode parameter is 1. This is the final event emitted by any Worker instance."
- `worker.ref()/unref()` (v10.5.0): an unref'd worker does not keep the main loop
  alive. MessagePorts (`parentPort`) are themselves ref/unref-able handles.

**Worker exit ≠ process exit**: the main thread's loop is untouched; conversely a
worker's `process.exit()` ends only the worker. A worker inherits a **copy** of
`process.env` by default (v11.14.0, §2.1) — mutating env in either side does not
propagate.

### 6.3 `cluster` (brief, verified)

"Clusters of Node.js processes can be used to run multiple instances of Node.js that
can distribute workloads among their application threads. When process isolation is
not needed, use the `worker_threads` module instead." Under the hood: "The worker
processes are spawned using the `child_process.fork()` method" — so every §5 rule
applies to cluster workers; `cluster.fork([env])` (v0.6.0) returns a
`cluster.Worker` (a superset of `ChildProcess` adding worker-id and IPC-primaries
plumbing). Ports are shared server sockets, not threads: one crashing worker is one
process death, supervised via the primary's `'exit'` event.

### 6.4 Pipes, buffering, and the classic deadlock

`'pipe'` stdio connects the child's fd to a parent-side Node stream. Two OS-level
facts govern everything:

- [Linux/POSIX] A pipe's kernel buffer is bounded (64 KiB here, per `pipe(7)`); a
  child writing past it **blocks** until the parent drains.
- [Node documented] Writes to a pipe `process.stdout` are asynchronous; to a TTY they
  may be synchronous (§3.3's truncation caveat).

The deadlock: parent spawns child with piped stdio and calls
`child.stdout.read()`-style buffered collection *only after* the child fills stderr's
pipe — the child blocks writing stderr while the parent blocks waiting for stdout.
The fix is exactly what `spawn` enables: drain all pipes concurrently (or
`stdio: 'ignore'` what you don't need). Note the related `exec`/`execFile` design
point: their maxBuffer buffering both bounds memory *and* removes the deadlock — the
docs' buffering implementation reads both pipes while the child runs.

### 6.5 fd ownership, stream closure, and leak patterns

Ownership rules: parent-side pipe streams are opened at spawn; they are **closed by
the runtime on `'close'`** (the close of stdio streams is what `'close'`
waits for). Documented leak patterns:

- **Not draining** a piped stream → child blocks (§6.4) and the fd pair never closes.
- **IPC channel never closed** → the forked child's loop never drains ("allowing the
  child process to exit gracefully once there are no other connections keeping it
  alive" — `disconnect()` is the documented closer).
- **Unref'd/detached children without stdio:'ignore'** → child holds the parent's
  terminal fds; parent exit does not daemonize it (§5.4).
- **`kill()`'s return value ignored** → `false` means `kill(2)` failed (e.g. process
  already reaped); treating it as success skips the fallback ladder (§5.10).

### 6.6 Event-listener leaks: `MaxListenersExceededWarning`

Default cap: "a maximum of 10 listeners can be registered for any single event"
(`events.defaultMaxListeners`, v0.11.2). Exceeding it emits a process warning whose
`name` property "is set to `'MaxListenersExceededWarning'`" with additional `emitter`,
`type`, and `count` properties — inspectable via `process.on('warning')` or
`--trace-warnings`. It is a heuristic, not a hard limit; a spawn-per-request server
adding a `'close'` listener per child grows listener arrays per emitter only if
emitters are reused. Raise deliberately per-emitter with
`emitter.setMaxListeners(n)` or globally with `events.setMaxListeners(n[, …targets])`
(§2.2); the cure for a real leak is `removeListener`/`once`, not a bigger cap. Note
the docs' caveat that `defaultMaxListeners` "has no effect on AbortSignal instances."

### 6.7 Races and ordering

- **`'exit'` / `'close'` / `'error'`**: fixed partial order — `'exit'` before
  `'close'`; `'close'` "will always emit after 'exit' … or 'error' if the child
  process failed to spawn"; `'exit'` "may or may not" follow `'error'` (§5.9). Any
  handler that must run once must be guarded against the `error`+`exit` double
  delivery.
- **`kill` during spawn**: between `spawn()` returning and the `'spawn'` event
  (v15.1.0/v14.17.0, "emitted once the child process has spawned successfully"),
  `pid` may be `undefined` and `kill()` may fail; the documented guard is waiting for
  `'spawn'` before interacting with stdio or signaling.
- **Sync block vs signals**: `spawnSync` (§5.7) delays all signal listeners; a
  SIGTERM arriving during a long sync child is handled only after it returns.
- **`beforeExit` re-arm**: code that schedules from `'beforeExit'` on every drain can
  keep the process alive forever (§3.8) — bound your retries.

### 6.8 GC plays no role in process cleanup

There are no finalizers on the process path: an unreachable `ChildProcess` is not
killed, an unclosed IPC channel is not disconnected, an undrained stream is not
closed — JS GC reclaims memory, not OS resources. (Compare
[Python's `Popen.__del__` ResourceWarning reaper](./python.md): CPython at least
warns and reaps; V8/Node does neither.) The documented cleanup APIs are explicit and
must be called: `kill()`/the timeout/AbortSignal machinery (§5.10),
`disconnect()` (§5.6), stream `.destroy()`, and `'close'` as the single "everything
is released" checkpoint.

```js
// Canonical one-child lifecycle, all rules of §5–§6 in 12 lines.
const child = spawn('longjob');
child.stdout.on('data', drain);          // 6.4 drain everything you pipe
child.on('error', guardOnce);            // 5.9 error may or may not precede exit
child.on('exit', (code, signal) => {});  // 5.9 exactly one of code/signal
child.on('close', (code, signal) => {    // 6.5 all fds closed here
  console.log(code ?? signal, 'resources released');
});
setTimeout(() => child.kill(), 60_000);  // 5.10 timeout ladder (SIGTERM first)
```

---

## Coverage ledger

The machine-checkable inventory for this chapter lives in
[ledger-nodejs.md](./ledger-nodejs.md) (schema: hub
[Coverage ledger schema](./index.md)). **Declared row count: 80** —
`PL-ND-001…PL-ND-080`, ordered by section: §1→001–012, §2→013–026, §3→027–038,
§4→039–045, §5→046–071, §6→072–080. All 80 rows are `documented` (every signature
verified against the v24 API reference on 2026-10-13); rollup:
**Inventoried: 80 / Documented: 80 / Remaining: 0 / Source-limited: 0**.

## Related Topics

- [Node.js: Exit Status, Signals, and Process Lifecycle](../../linux/process-exit-signal/languages/nodejs.md) — LG-NO exit/signal view of the same runtime
- [Process & Runtime Semantics by Language](./index.md) — Section G hub and ledger schema
- [Python](./python.md) / [Go](./go.md) — subprocess and signal models for comparison
- [Node.js](../javascript/nodejs.md) and [V8](../javascript/v8.md) — engine-level internals

## References

1. Node.js API (v24, `nodejs.org/docs/latest-v24.x/api/`, retrieved 2026-10-13): [process.html](https://nodejs.org/docs/latest-v24.x/api/process.html) (exit, exitCode, abort, kill, nextTick, env, chdir/cwd, umask, setuid/setgid/initgroups, events 'exit'/'beforeExit'/'uncaughtException'/'uncaughtExceptionMonitor'/'unhandledRejection', signal events, exit codes table).
2. [child_process.html](https://nodejs.org/docs/latest-v24.x/api/child_process.html) (spawn/exec/execFile/fork + sync variants, options.stdio/detached, ChildProcess class and events, shell requirements, DEP0190 history).
3. [worker_threads.html](https://nodejs.org/docs/latest-v24.x/api/worker_threads.html) (Worker, terminate, 'exit', ref/unref, MessagePort, stability history) and [cluster.html](https://nodejs.org/docs/latest-v24.x/api/cluster.html) (fork, child_process.fork relationship).
4. [events.html](https://nodejs.org/docs/latest-v24.x/api/events.html) (defaultMaxListeners, MaxListenersExceededWarning, setMaxListeners) and [os.html](https://nodejs.org/docs/latest-v24.x/api/os.html) (availableParallelism).
5. [util.html](https://nodejs.org/docs/latest-v24.x/api/util.html) (convertProcessSignalToExitCode, added v24.14.0).
6. [cli.html](https://nodejs.org/docs/latest-v24.x/api/cli.html) (`--unhandled-rejections=mode` list; throw default since v15.0.0) and [modules.html](https://nodejs.org/docs/latest-v24.x/api/modules.html) + [esm.html](https://nodejs.org/docs/latest-v24.x/api/esm.html) (require/ESM interop, require(esm) non-experimental v24.15.0, top-level await constraints).
7. Node.js Learn — [The Node.js Event Loop](https://nodejs.org/learn/asynchronous-work/event-loop-timers-and-nexttick) (phases, timers-after-poll libuv 1.45.0 note, nextTick vs setImmediate) (retrieved 2026-10-13).
8. Node.js release data: [nodejs.org/dist/index.json](https://nodejs.org/dist/index.json) (v24.21.0 'Krypton' LTS, 2026-09-07; v26.11.1 current; embedded V8 13.6.233.17 / libuv 1.52.1) (retrieved 2026-10-13).
9. libuv — [Threadpool](https://docs.libuv.org/en/v1.x/threadpool.html) (default size 4, `UV_THREADPOOL_SIZE` max 1024, global shared pool) (retrieved 2026-10-13).
10. In-repo cross-reference: [linux/process-exit-signal/languages/nodejs.md](../../linux/process-exit-signal/languages/nodejs.md) (LG-NO-001…005, Node 22 exit/signal scope, consistent with this chapter).
