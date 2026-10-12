# OCaml: Exit Status, Signals, and Process Lifecycle

**ID range:** LG-OC-001 … LG-OC-006 — **Version scope:** OCaml 5.2 manual (ocaml.org/manual/5.2/api/, retrieved 2026-10); signatures were cross-checked against the `stdlib/sys.mli` and `otherlibs/unix/unix.mli` sources of the OCaml 5.2 tree. Every signature in this chapter was copied from fetched documentation; APIs that the spec asked about but that **do not exist** in OCaml 5.2 (`Sys.exit` as a `Sys` member, `Unix.sigaction`, `Unix.wait4`, `Unix.ProcessInfo`, `Sys.break_exception`, `Sys.error_message`) are explicitly recorded as verified-absent rather than invented. OCaml 5's multicore effects runtime changes some of the classic guarantees; only officially documented deltas are stated, and undocumented areas are marked as such.

OCaml gives you two layers: the *Stdlib/Sys* layer (portable, guarded by the runtime) and the *Unix* layer (a thin binding over POSIX, loaded via `#load "unix.cma"` / linked with `-package unix`). The runtime mediates every signal and every exit; the chapter tracks where that mediation changes kernel semantics.

---

## 1. Syntax and Semantics of Termination (LG-OC-001)

### 1.1 `Stdlib.exit` — canonical signature and exact semantics

From the [Stdlib documentation](https://ocaml.org/manual/5.2/api/Stdlib.html):

```ocaml
val exit : int -> 'a
```

> "Terminate the process, returning the given status code to the operating system: usually 0 to indicate no errors, and a small positive integer to indicate failure. **All open output channels are flushed with `flush_all`.** The callbacks registered with `Domain.at_exit` are called followed by those registered with `at_exit`."

> "An implicit `exit 0` is performed each time a program terminates normally. An implicit `exit 2` is performed if the program terminates early because of an uncaught exception."

Notes on the type: `int -> 'a` means `exit` can appear anywhere any type is expected (it never returns) — the idiomatic `raise (Exit status)`-style plumbing of other languages is unnecessary. `Exit` is also a *predefined exception* (`exception Exit` in Stdlib); raising it does **not** set an exit status — only `exit n` or an uncaught exception does.

**`Sys.exit` does not exist.** Verification result: the OCaml 5.2 `Sys` module documentation and the `stdlib/sys.mli` source contain no `exit` binding; the only exit function in the standard library is `Stdlib.exit` (in scope unqualified after `open Stdlib`, which is the default). Older texts saying `Sys.exit` are wrong for every modern OCaml; code referring to `Sys.exit` fails to compile. This is recorded in the ledger as a verified absence.

### 1.2 `at_exit` and shutdown ordering

```ocaml
val at_exit : (unit -> unit) -> unit
```

> "Register the given function to be called at program termination time. The functions registered with `at_exit` will be called when the program does any of the following: executes `exit`; terminates, either normally or because of an uncaught exception; executes the C function `caml_shutdown`. The functions are called in **'last in, first out'** order: the function most recently added with `at_exit` is called first." ([Stdlib docs](https://ocaml.org/manual/5.2/api/Stdlib.html))

So cleanup registered *last* runs *first* — the reverse of Java's unspecified hook order and the same LIFO discipline as Python's `atexit`.

```ocaml
let () =
  at_exit (fun () -> prerr_endline "handler A");
  at_exit (fun () -> prerr_endline "handler B");
  (* prints: handler B, then handler A *)
  exit 0
```

Exceptions raised *inside* `at_exit` handlers are printed by the runtime as `Uncaught exception ... in at_exit function` style fatal errors (the runtime does not swallow them silently; behavior beyond that is runtime-internal and not specified in the 5.2 manual — marked undocumented).

**Domain-local variant (OCaml 5):** [Domain.at_exit](https://ocaml.org/manual/5.2/api/Domain.html) — "at_exit f registers f to be called when the current domain exits. Note that at_exit callbacks are domain-local and only apply to the calling domain," also LIFO. `Stdlib.exit` runs `Domain.at_exit` callbacks **before** the process-wide `at_exit` callbacks (quoted in §1.1) — a documented ordering you can rely on when a domain-local resource must be freed before process-wide finalization.

### 1.3 `flush_all` and channel buffering at exit

```ocaml
val flush_all : unit -> unit   (* "Flush all open output channels; ignore errors." *)
```

`exit` calls it for you, with the documented caveat that flush **errors are ignored** — a failing disk does not change your exit status. Channels left with buffered data at a non-`exit` termination (e.g. `Unix._exit`, or death by signal) lose that data; the [Unix docs](https://ocaml.org/manual/5.2/api/Unix.html) for `open_process_out` warn exactly this: "Warning: writes on output channels are buffered, hence be careful to call flush at the right times to ensure correct synchronization."

### 1.4 Uncaught exceptions → exit code 2

The documented chain: an uncaught exception terminates the program; the runtime prints the exception (and, if enabled, a backtrace) via `Printexc.default_uncaught_exception_handler` — "prints the exception and backtrace on standard error output" ([Printexc docs](https://ocaml.org/manual/5.2/api/Printexc.html)) — and performs "an implicit `exit 2`" (Stdlib docs, quoted §1.1). Two verified subtleties:

- `Printexc.set_uncaught_exception_handler fn` replaces that printer, and the docs note: "when `fn` is called **all the functions registered with `at_exit` have already been called**. Because of this you must make sure any output channel `fn` writes on is flushed." So the ordering is: `at_exit` handlers → uncaught-exception handler → process exits 2.
- Backtraces require debug information: `ocamlrun -b` / `OCAMLRUNPARAM=b` ("Trigger the printing of a stack backtrace when an uncaught exception aborts the program"; `b=2` forces debug-info load at startup — [runtime manual](https://ocaml.org/manual/5.2/runtime.html)), and for bytecode "the back trace is printed only if the bytecode executable contains debugging information, i.e. was compiled and linked with the `-g` option."

```console
$ cat boom.ml
let () = failwith "boom"
$ ocamlc boom.ml -o boom && ./boom; echo $?
Fatal error: exception Failure("boom")
2
$ ocamlc -g boom.ml -o boom && OCAMLRUNPARAM=b ./boom; echo $?
Raised at Boom.fun in file "boom.ml", line 1, characters 9-23
Called from Boom.fun in file "boom.ml", line 1, characters 9-23
Fatal error: exception Failure("boom")
2
```

### 1.5 `Unix._exit` — the immediate path

```ocaml
val _exit : int -> 'a
```

> "Terminate the calling process immediately, returning the given status code to the operating system … **Unlike `exit`, `Unix._exit` performs no finalization whatsoever: functions registered with `at_exit` are not called, input/output channels are not flushed, and the C run-time system is not finalized either.**"

> "The typical use of `Unix._exit` is after a `Unix.fork` operation, when the child process runs into a fatal error and must exit. In this case, it is preferable to not perform any finalization action in the child process … For example, output channels should not be flushed by the child process, as the parent process may flush them again later, resulting in duplicate output." ([Unix docs](https://ocaml.org/manual/5.2/api/Unix.html))

### 1.6 Exit-status derivation table

| Termination path | Status seen by parent | Source |
|---|---|---|
| Top-level `let () = ()` completes | 0 ("implicit `exit 0`") | Stdlib docs |
| `exit 5` (or any `exit n`) | 5, after flush + `Domain.at_exit` + `at_exit` | Stdlib docs |
| Uncaught exception | **2** + message (+ backtrace if `b` flag) | Stdlib docs; runtime manual |
| `Unix._exit 3` | 3 immediately, no cleanup | Unix docs |
| `Sys.command` / `Unix.system` child ran and exited n | that child's code (as `process_status`/`int`) | Unix docs (`WEXITED 127` rule below) |
| Shell could not be executed by `Unix.system` | `WEXITED 127` | Unix docs, quoted verbatim |
| Process killed by signal (e.g. `kill -TERM`) | dies by signal; shell `$?` = 128+N (143 for TERM) | OS behavior (not OCaml-documented) |
| `Stdlib.exit` handler crashed / flush error | flush errors ignored; handler-crash behavior runtime-internal | documented/undocumented split noted |

**The 127 rule, precisely:** the 5.2 manual documents `WEXITED 127` for `Unix.system` ("The result WEXITED 127 indicates that the shell couldn't be executed"). The 5.2 `Sys.command` entry documents only "Execute the given shell command and return its exit code" — the older manual's "returns 127 if the command could not be executed" sentence was dropped in this version; treat 127 for shell-exec failure as verified for `Unix.system` and version-specific for `Sys.command` (same implementation path, but the current `Sys.command` doc no longer spells it out).

### 1.7 Misconceptions

- **"`Sys.exit 1` is the API."** No such function (verified §1.1); it is `Stdlib.exit`.
- **"Raising `Exit` exits with an error status."** `raise Exit` is an ordinary exception; uncaught it yields exit **2**, not 1. There is no documented status-1 path in OCaml at all.
- **"`at_exit` runs on SIGKILL/SIGTERM."** No: only `exit`, normal termination, uncaught exception, or `caml_shutdown` trigger it (documented list §1.2). A signal with default disposition kills without running handlers.
- **"`exit` cannot fail."** Flush errors are ignored (documented), but `at_exit` handlers can raise — and those are not swallowed.
- **"Forking is free."** On OCaml 5 `Unix.fork` "fails if the OCaml process is multi-core (any domain has been spawned)" and "if any thread from the `Thread` module has been spawned, then the child process might be in a corrupted state" (both quoted from the Unix docs).

---

## 2. Standard-Library and Runtime API Inventory (LG-OC-002)

### `Stdlib`

| API | Verified signature | Semantics |
|---|---|---|
| `exit` | `val exit : int -> 'a` | Flush all; `Domain.at_exit` then `at_exit`; implicit 0/2 rules |
| `at_exit` | `val at_exit : (unit -> unit) -> unit` | LIFO; called on exit/normal term/uncaught exception/`caml_shutdown` |
| `flush_all` | `val flush_all : unit -> unit` | Flush everything; ignore errors |
| `Exit` (exception) | `exception Exit` | Predefined; no special exit-status meaning |

### `Sys` (5.2)

| API | Verified signature | Semantics |
|---|---|---|
| `argv` | `val argv : string array` | Command line; first element is the command name |
| `executable_name` | `val executable_name : string` | File containing the running executable ("may be absolute or relative … depending on the platform and whether the program was compiled to bytecode or a native executable") |
| `getenv` | `val getenv : string -> string` | "Raises `Not_found` if the variable is unbound" |
| `getenv_opt` | `val getenv_opt : string -> string option` | Since 4.05 |
| `command` | `val command : string -> int` | Shell (`/bin/sh`, `cmd.exe` on Windows); quoting rules differ per shell; "`Filename.quote_command` performs the appropriate quoting given a command name, a list of arguments, and optional file redirections" |
| `signal` | `val signal : int -> signal_behavior -> signal_behavior` | "Set the behavior of the system on receipt of a given signal. The first argument is the signal number. **Return the behavior previously associated with the signal.** If the signal number is invalid (or not available on your system), an `Invalid_argument` exception is raised." |
| `set_signal` | `val set_signal : int -> signal_behavior -> unit` | "Same as `Sys.signal` but return value is ignored." |
| `signal_behavior` | `type signal_behavior = Signal_default \| Signal_ignore \| Signal_handle of (int -> unit)` | "`Signal_handle f`: call function f, giving it the signal number as argument." |
| `sigabrt … sigusr2` | `val sigint : int` (et al.) | "Signal numbers for the standard POSIX signals" — e.g. `sigabrt` "Abnormal termination", `sigalrm` "Timeout", `sigint` "Interactive interrupt". "Note that they are not the numbers used by the OS" (Unix docs on `process_status` — Sys constants are logical, mapped per platform) |
| `Break` (exception) | `exception Break` | "Exception raised on interactive interrupt if `Sys.catch_break` is enabled." |
| `catch_break` | `val catch_break : bool -> unit` | "governs whether interactive interrupt (ctrl-C) terminates the program or raises the `Break` exception. Call `catch_break true` to enable raising `Break` … Inside multi-threaded programs, the Break exception will arise in any one of the active threads, and will keep arising on further interactive interrupt until all threads are terminated. Use signal masks from `Thread.sigmask` to direct the interrupt towards a specific thread." |

**Verified absent from `Sys` 5.2:** `Sys.exit` (§1.1), `Sys.break_exception` (not in the 5.2 `sys.mli`/manual), `Sys.error_message` (the error-string helper is `Unix.error_message`, verified in `unix.mli`). No invented APIs here — these are the verification results the challenge asks for.

### `Printexc`

| API | Verified signature | Semantics |
|---|---|---|
| `get_backtrace` | `val get_backtrace : unit -> string` | Same text `print_backtrace` would print |
| `record_backtrace` | `val record_backtrace : bool -> unit` | Toggle recording; initially off "unless the b flag is given … through the OCAMLRUNPARAM variable" |
| `backtrace_status` | `val backtrace_status : unit -> bool` | Whether recording is on |
| `get_callstack` | `val get_callstack : int -> raw_backtrace` | "top of the call stack on the current program point (for the current thread), with at most n entries" (since 4.01) |
| `default_uncaught_exception_handler` | `val default_uncaught_exception_handler : exn -> raw_backtrace -> unit` | "prints the exception and backtrace on standard error output" (since 4.11) |
| `set_uncaught_exception_handler` | `val set_uncaught_exception_handler : (exn -> raw_backtrace -> unit) -> unit` | Ordering note (§1.4); exceptions raised by `fn` printed with both backtraces |

### Runtime controls

- `OCAMLRUNPARAM=b[=0|1|2]` and `ocamlrun -b` — backtrace control (§1.4, quoted from the runtime manual).
- `OCAMLRUNPARAM=c` ("cleanup_on_exit") — "Shut the runtime down gracefully on exit (see `caml_shutdown` …)"; documented as an option to detect leaks with memory debuggers.
- The native runtime may install handlers for SIGSEGV/SIGTRAP/SIGFPE itself: "the native-code runtime system may install signal handlers for one or several of the SIGSEGV, SIGTRAP and SIGFPE signals when `caml_startup` is called, and reset these signals to their default behaviors when `caml_shutdown` is called. The main program written in C should not try to handle these signals itself." ([C interface manual](https://ocaml.org/manual/5.2/intfc.html)) — i.e. your own SIGSEGV handler and the OCaml native runtime conflict.

---

## 3. Process Lifecycle and Termination (LG-OC-003)

**Creation.** `ocamlc`/`ocamlopt` produce bytecode (run by `ocamlrun` unless `-custom`) or native executables. The runtime initializes (signal setup, GC domains) and evaluates the compilation-unit initializers — OCaml's "main" is the *initializer of the last linked module*, conventionally `let () = ...`.

**Normal termination.** Initializers complete → implicit `exit 0` → `flush_all` → `Domain.at_exit` callbacks → `at_exit` callbacks → `caml_shutdown` (with `OCAMLRUNPARAM=c` or under `caml_shutdown` embedding, the C runtime finalizes).

**Explicit termination.** `Stdlib.exit n` (clean) or `Unix._exit n` (immediate, for forked children). There is no `abort()` equivalent in the documented API surface of 5.2 (`Stdlib`/`Sys`/`Unix`) — a crash-style abort would go through `raise` or external code; recorded as a verified absence of the convenience API.

**Abnormal termination.** Uncaught exception → printed (2). Signal → kernel default or your `Sys.signal` behavior; death by unhandled signal bypasses all OCaml cleanup, leaving zombies to the parent and buffered channel data lost.

**Process vs thread vs child.** Domains (`Domain.spawn`) and systhreads (`Thread.create`) live inside the process; `exit` from anywhere ends everything. `Unix.fork` duplicates the process — with the multicore restrictions quoted in §1.7 (fails if domains exist; corrupted-state risk with threads). Children are created via `Unix.fork`/`execv*`, `Unix.create_process`, or the `open_process` family; killing your process orphans them (re-parented to init); killing a child without `wait`/`waitpid`/`close_process*` leaves a zombie.

---

## 4. Signals and OS Interaction (LG-OC-004)

### 4.1 Installing handlers: `Sys.signal` only — and `Unix.sigaction` does not exist

The 5.2 Unix module's *Signals* section states, verbatim:

> "Note: installation of signal handlers is performed via the functions `Sys.signal` and `Sys.set_signal`."

Verification result on the frequent claim of a `Unix.sigaction` API: **there is no `sigaction`, `signal_behavior`, or `process_behavior` binding in `otherlibs/unix/unix.mli`** in OCaml 5.2 (nor in 4.14, 4.06, 4.02, 4.00, or 3.12 — checked in the sources). The one-shot "return the previous behavior" API *is* `Sys.signal`, which returns the old `signal_behavior` — the functional-style equivalent people expect from `sigaction(2)`. The ledger records `Unix.sigaction` as verified-absent rather than documenting a signature that does not exist.

The runtime's delivery model (documented in the C-interface manual): OCaml signal handlers do not run inside the kernel's C signal frame; pending handlers run at runtime *safe points* — "the function `caml_process_pending_actions` from `<caml/signals.h>` executes any pending signal handlers and finalisers, Memprof callbacks, preemptive systhread switching, and requested minor and major garbage collections" — i.e. handlers are deferred like CPython's, and a compute loop that never allocates may delay them. (How precisely OCaml 5's multicore scheduler distributes signals across domains beyond what is quoted here is **not documented in the 5.2 manual** — marked undocumented.)

### 4.2 The handler vocabulary

```ocaml
type signal_behavior = Signal_default | Signal_ignore | Signal_handle of (int -> unit)
val signal : int -> signal_behavior -> signal_behavior  (* returns previous behavior *)
val set_signal : int -> signal_behavior -> unit
```

Example — the documented Ctrl-C choice:

```ocaml
let () =
  Sys.catch_break true;                          (* Ctrl-C raises Break instead of killing *)
  try
    (* ... long computation ... *)
    ()
  with Sys.Break -> prerr_endline "interrupted"; exit 130
```

`Sys.catch_break true/false` is the documented front-end for SIGINT disposition; `false` = "let the system terminate the program on user interrupt." The multi-threaded caveat is quoted in §2 (Break arises in "any one of the active threads"; use `Thread.sigmask` to route it).

Blocking/inspecting signals at the POSIX level is in `Unix`:

```ocaml
type sigprocmask_command = SIG_SETMASK | SIG_BLOCK | SIG_UNBLOCK
val sigprocmask : sigprocmask_command -> int list -> int list   (* returns previous mask *)
val sigpending  : unit -> int list
val sigsuspend  : int list -> unit
val pause       : unit -> unit
val alarm       : int -> int           (* SIGALRM after n seconds; returns previous alarm *)
val sleep       : int -> unit          (* integer seconds *)
val sleepf      : float -> unit        (* since 4.03 *)
```

Verified semantics: `sigprocmask` "returns the set of previously blocked signals"; "When the systhreads version of the `Thread` module is loaded, this function redirects to `Thread.sigmask`. I.e., `sigprocmask` only changes the mask of the current thread." `sigsuspend` "atomically sets the blocked signals to `sigs` and waits for a non-ignored, non-blocked signal to be delivered. On return, the blocked signals are reset to their initial value." `pause` "Wait[s] until a non-ignored, non-blocked signal is delivered." The Windows note on all of these: `Invalid_argument` ("no inter-process signals on Windows").

### 4.3 `EINTR` and `Unix.Unix_error`

The `Unix` error model: "Every function in this module raises `Unix_error` with an informative message when the underlying system call signals an error"; the exception is `exception Unix_error of error * string * string`, where `error` is a large variant including `EINTR` — "Function interrupted by signal." Unlike Python (PEP 475 auto-retry), OCaml does **not** retry for you: the documented pattern is explicit handling, with `Unix.handle_unix_error : ('a -> 'b) -> 'a -> 'b` as the helper that prints the message and exits (per `unix.mli`: "applies f to x and returns the result. If the exception `Unix_error` is raised, it prints a message and exits"; `error_message : error -> string` renders codes as text).

```ocaml
(* EINTR retry pattern — explicit, unlike Python's PEP 475 *)
let rec read_all fd buf off len =
  try Unix.read fd buf off len with
  | Unix.Unix_error (Unix.EINTR, _, _) -> read_all fd buf off len
```

### 4.4 Safe handler → application communication; runtime restrictions

- Handlers installed via `Signal_handle f` run at safe points (§4.1); they may raise exceptions ("asynchronous exceptions" per the interface manual's `caml_process_pending_actions` text), which then propagate into the interrupted OCaml code.
- The documented interplay rules you can rely on: allocation functions "are guaranteed not to run any OCaml code, including finalisers, signal handlers and other threads running on the same domain. Instead, their execution is delayed to a later safe point" (interface manual, since 4.10).
- The canonical safe-communication pattern in documented APIs: set a mutable flag / use `Thread.sigmask` + `Unix.sigsuspend`/`sigwait`-style blocking calls. (There is no documented `signalfd` binding in 5.2's Unix module — verified absent from the manual.)
- POSIX vs Linux-specific: everything above is POSIX-generic via the Unix library; nothing Linux-specific is documented beyond availability. Windows degradations are noted per-API (`Invalid_argument`).

---

## 5. Subprocess and Child-Process Management (LG-OC-005)

### 5.1 Raw primitives

```ocaml
val fork : unit -> int                        (* 0 in child, child pid in parent *)
val execv  : string -> string array -> 'a     (* never returns *)
val execve : string -> string array -> string array -> 'a
val execvp : string -> string array -> 'a     (* PATH search *)
val execvpe: string -> string array -> string array -> 'a
```

Verified: `execv*` "never return: on success, the current program is replaced by the new one"; "`args.(0)` is by convention the filename of the program being executed, just like `Sys.argv.(0)`"; failure raises `Unix_error`. The fork caveat is quoted in §1.7 — on OCaml 5, `fork` fails outright in multicore programs; with systhreads the child "might be in a corrupted state." On Windows the whole family degrades (CRT spawn semantics; `Invalid_argument` for `fork`/`wait`).

### 5.2 Waiting and status

```ocaml
type process_status =
  | WEXITED   of int   (* "terminated normally by exit; the argument is the return code." *)
  | WSIGNALED of int   (* "killed by a signal; the argument is the signal number." *)
  | WSTOPPED  of int   (* "stopped by a signal; the argument is the signal number." *)

type wait_flag = WNOHANG | WUNTRACED

val wait    : unit -> int * process_status
val waitpid : wait_flag list -> int -> int * process_status
```

Verified: `wait` "Wait[s] until one of the children processes die, and return[s] its pid and termination status" (`Invalid_argument` on Windows — "Use `Unix.waitpid` instead"). `waitpid` pid conventions match POSIX: "`-1` means wait for any child. A pid of `0` means wait for any child in the same process group as the current process. Negative pid arguments represent process groups." `WNOHANG` — "Do not block if no child has died yet, but immediately return with a pid equal to 0"; `WUNTRACED` — "Report also the children that receive stop signals." The `WSTOPPED` constructor therefore exists and is reachable with `WUNTRACED` (or under ptrace), even though plain `wait` rarely reports it.

**Verified absent in 5.2:** no `Unix.wait4`, no `Unix.waitid`, no `Unix.ProcessInfo` (checked `unix.mli`/manual). If you need rusage, it is not in the documented 5.2 API.

### 5.3 `Unix.system`, `Sys.command`, and quoting

```ocaml
val system : string -> process_status
val Sys.command : string -> int
```

`Unix.system` — "Execute the given command, wait until it terminates, and return its termination status. The string is interpreted by the shell `/bin/sh` … and therefore can contain redirections, quotes, variables, etc. To properly quote whitespace and shell special characters occurring in file names or command arguments, the use of `Filename.quote_command` is recommended. **The result `WEXITED 127` indicates that the shell couldn't be executed.**"

`Sys.command` is the `int`-status twin (§1.6 records the 127 version difference). Injection surface: both pass the whole string to `/bin/sh`; the documented defense is `Filename.quote_command cmd args`:

```ocaml
(* user input: "x; rm -rf ~" *)
Sys.command ("ls " ^ user_input)                       (* UNSAFE: shell interprets *)
Sys.command (Filename.quote_command "ls" [user_input]) (* SAFE: quoted single argument *)
```

### 5.4 `create_process` — the exec-with-redirects workhorse

```ocaml
val create_process :
  string -> string array -> file_descr -> file_descr -> file_descr -> int
val create_process_env :
  string -> string array -> string array -> file_descr -> file_descr -> file_descr -> int
```

Verified: "creates a new process that executes the program in file `prog`, with arguments `args` … The pid of the new process is returned immediately … The standard input and outputs of the new process are connected to the descriptors `stdin`, `stdout` and `stderr`. Passing e.g. `Unix.stdout` for `stdout` prevents the redirection … The executable file `prog` is searched in the path." (`create_process_env` adds an environment array.) This is the argument-array API — no shell, no injection surface.

### 5.5 The `open_process` family — pipes with a reaping contract

Shell-string variants (parsed by `/bin/sh`):

```ocaml
val open_process_in  : string -> in_channel                 (* child stdout -> channel *)
val open_process_out : string -> out_channel                (* channel -> child stdin *)
val open_process     : string -> in_channel * out_channel
val open_process_full: string -> string array -> in_channel * out_channel * in_channel
                        (* second argument is the ENVIRONMENT (verified) *)
```

Argument-array variants (since 4.08, "more robust and more efficient alternative" — quoted from the `open_process_in` doc):

```ocaml
val open_process_args     : string -> string array -> in_channel * out_channel
val open_process_args_in  : string -> string array -> in_channel
val open_process_args_out : string -> string array -> out_channel
val open_process_args_full: string -> string array -> string array -> in_channel * out_channel * in_channel
```

Reaping (each returns the child's `process_status`, reaping the zombie):

```ocaml
val close_process_in   : in_channel -> process_status
val close_process_out  : out_channel -> process_status
val close_process      : in_channel * out_channel -> process_status
val close_process_full : in_channel * out_channel * in_channel -> process_status
```

Verified pids: `process_in_pid`, `process_out_pid`, `process_pid`, `process_full_pid` (4.08+) — "the pid of a process opened via … or the pid of the shell opened via …".

**Deadlock hazard (documented pattern):** with `open_process`/`open_process_full`, writing to the child while never draining its stdout (or vice versa) fills the OS pipe buffer and blocks both processes. `close_process_*` waits for termination — if you forgot to drain, that wait never returns. The documented reading-order discipline for `open_process_full` is to read stdout and stderr to EOF *before* (or interleaved with) writing stdin, then `close_process_full`. The buffered-writes warning is quoted in §1.3.

**Zombie risk:** every `open_process*` needs exactly one matching `close_process*`; a program that spawns and exits (or forgets) leaves the child unreaped — a zombie until the process exits. There is no `WNOHANG`-style polling on channels; use `Unix.waitpid [WNOHANG]` + `Unix.process_*_pid` if you must poll.

### 5.6 Sync vs async, timeouts, cancellation

Everything in the documented `Unix` module is synchronous. There is no documented timeout or cancellation API for child processes in 5.2 (`Unix` has no `wait4`/`waitid`, §5.2); the composition is: `alarm`/`SIGALRM` + handler that kills the child (`Unix.kill pid Sys.sigterm`), then `waitpid` — all hand-rolled. Lwt/Async/Eio provide async wrappers but are third-party relative to the 5.2 manual and are not documented here.

---

## 6. Concurrency and Resource Semantics (LG-OC-006)

**Domains and threads.** OCaml 5 runs multiple domains (each with its own minor heap and a domain-local `Domain.at_exit`); systhreads multiplex within domains. Documented lifecycle facts: `Stdlib.exit` ends the whole process regardless of which domain calls it; `Domain.at_exit` fires when *that domain* exits; `Unix.fork` fails in multicore programs (quoted). The docs' catch_break note (§2) shows signals + threads interacting through `Thread.sigmask` — the documented per-thread routing tool.

**fd ownership.** Channels (`in_channel`/`out_channel`) own their fd and buffer; `Unix` descriptors (`file_descr`) are raw. Mixing layers (flushing vs `Unix.read` on the same fd) is the classic desync; the documented warnings are the `open_process_out` buffering note and the `_exit` duplicate-flush note (§1.5). `create_process` transfers fds to the child by dup2 semantics (documented as "connected to the descriptors"); closing parent-side ends after use to avoid pipe-hold-open bugs.

**Buffering.** Stdlib channels buffer; `flush_all` at `exit` covers normal paths only. Anything killed by signal or `_exit` loses buffered data (documented implications quoted).

**Races, deadlocks, leaks.**

- `at_exit` handlers run LIFO — a handler that depends on a resource freed by an *earlier-registered* handler is correct (it runs first); the reverse ordering is a use-after-free race the type system cannot see.
- `Sys.signal` handlers racing with user code: they run at safe points (§4.1), but shared mutable state still needs `Atomic`/locks — nothing in the docs promises handler exclusivity beyond safe-point deferral.
- `open_process*` without `close_process*` → zombie; `close_process*` without drained pipes → deadlock (both consequences of documented semantics).
- `Unix.kill` on a reaped/reused pid signals an unrelated process — the POSIX pid-reuse hazard applies; `Unix.waitpid` on an already-waited pid raises `Unix_error` (ECHILD path).
- Multicore: forking after `Domain.spawn` is a documented hard failure; `Mutex` held across `fork` in threaded programs is the classic child-side deadlock (implied by the docs' "corrupted state" warning — the specific mutex interaction is not spelled out in the 5.2 manual and is marked as such).

**GC/runtime effects.** Finalisers and signal handlers are all funneled through `caml_process_pending_actions` (documented, §4.1); allocation-free loops defer both. `OCAMLRUNPARAM=c` enables graceful runtime shutdown (`caml_shutdown`) — documented as the mode where C-runtime finalization runs and leak-checkers see a clean exit.

---

### Coverage ledger

Statuses: `documented` = verified against the cited OCaml 5.2 manual/source with signature and semantics recorded; `verified-absent` = the API was checked for and does not exist in 5.2 (challenge rule: never invent); `source-limited` = documented source silent/unreachable.

| API | Canonical signature | Status | Reference |
|---|---|---|---|
| LG-OC-001 `Stdlib.exit` | `val exit : int -> 'a` | documented | [Stdlib.html](https://ocaml.org/manual/5.2/api/Stdlib.html) |
| LG-OC-001 `Stdlib.at_exit` | `val at_exit : (unit -> unit) -> unit` (LIFO) | documented | [Stdlib.html](https://ocaml.org/manual/5.2/api/Stdlib.html) |
| LG-OC-001 `Stdlib.flush_all` | `val flush_all : unit -> unit` | documented | [Stdlib.html](https://ocaml.org/manual/5.2/api/Stdlib.html) |
| LG-OC-001 `Domain.at_exit` | `val at_exit : (unit -> unit) -> unit` (domain-local) | documented | [Domain.html](https://ocaml.org/manual/5.2/api/Domain.html) |
| LG-OC-001 uncaught exception → exit 2 + Printexc | — | documented | Stdlib + [Printexc.html](https://ocaml.org/manual/5.2/api/Printexc.html) + runtime manual |
| LG-OC-001 `Sys.exit` | — | verified-absent | 5.2 Sys docs + `stdlib/sys.mli` (no `exit` binding) |
| LG-OC-001 `Unix._exit` | `val _exit : int -> 'a` | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-002 `Sys.signal`/`set_signal`/`signal_behavior` | `val signal : int -> signal_behavior -> signal_behavior` | documented | [Sys.html](https://ocaml.org/manual/5.2/api/Sys.html) |
| LG-OC-002 `Sys.catch_break`/`Break` | `val catch_break : bool -> unit`; `exception Break` | documented | [Sys.html](https://ocaml.org/manual/5.2/api/Sys.html) |
| LG-OC-002 `Sys.command` | `val command : string -> int` | documented (127 sentence version-difference recorded) | [Sys.html](https://ocaml.org/manual/5.2/api/Sys.html) |
| LG-OC-002 `Sys.getenv`/`getenv_opt`/`executable_name`/`argv` | verified signatures (§2) | documented | [Sys.html](https://ocaml.org/manual/5.2/api/Sys.html) |
| LG-OC-002 `Sys.break_exception` | — | verified-absent | 5.2 `sys.mli` (no binding) |
| LG-OC-002 `Sys.error_message` | — | verified-absent (helper lives in `Unix`: `error_message : error -> string`) | `unix.mli` |
| LG-OC-002 `Printexc` surface | get_backtrace/record_backtrace/backtrace_status/get_callstack/default+set_uncaught_exception_handler | documented | [Printexc.html](https://ocaml.org/manual/5.2/api/Printexc.html) |
| LG-OC-002 `OCAMLRUNPARAM b/c`, `ocamlrun -b` | — | documented | [runtime.html](https://ocaml.org/manual/5.2/runtime.html) |
| LG-OC-004 `Unix.kill` | `val kill : int -> int -> unit` | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-004 `Unix.sigprocmask`/`sigpending`/`sigsuspend`/`pause`/`alarm`/`sleep`/`sleepf` | verified signatures (§4.2) | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-004 `Unix.sigaction` | — | verified-absent (checked 5.2, 4.14, 4.06, 4.02, 4.00, 3.12 `unix.mli`; manual: handlers via `Sys.signal`) | [Unix.html Signals note](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-004 OCaml 5 multicore signal-delivery model beyond safe-point deferral | — | source-limited (not specified in the 5.2 manual) | [intfc.html](https://ocaml.org/manual/5.2/intfc.html) |
| LG-OC-005 `Unix.fork`/`execv*` | verified signatures (§5.1) | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-005 `Unix.wait`/`waitpid`/`process_status`/`wait_flag` | verified (§5.2) incl. WSTOPPED | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-005 `Unix.wait4`/`waitid`/`ProcessInfo` | — | verified-absent | 5.2 `unix.mli` |
| LG-OC-005 `Unix.system` (WEXITED 127) / `Filename.quote_command` | `val system : string -> process_status` | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-005 `Unix.create_process`/`create_process_env` | verified signatures (§5.4) | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-005 `open_process*` / `open_process_args*` / `close_process*` / `process_*_pid` | verified signatures (§5.5) | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html) |
| LG-OC-006 `Unix.Unix_error`/`error_message`/`handle_unix_error` | `exception Unix_error of error * string * string`; `error_message : error -> string`; `handle_unix_error : ('a -> 'b) -> 'a -> 'b` | documented | [Unix.html](https://ocaml.org/manual/5.2/api/Unix.html); `unix.mli` |
| LG-OC-006 concurrency/fd/buffering semantics | (§6) | documented | as above |

**Counts:** inventoried 27 rows; documented 21; verified-absent 5 (`Sys.exit`, `Sys.break_exception`, `Sys.error_message`, `Unix.sigaction`, `Unix.wait4`/`waitid`/`ProcessInfo` counted as one family row); remaining 0; source-limited 1 (OCaml 5 multicore signal-delivery details beyond the documented safe-point model — flagged rather than guessed).

## Related Topics

- [Python](../python.md) — `atexit` LIFO mirror image; PEP 475 auto-retry vs OCaml's explicit `EINTR` handling.
- [Java](../java.md) — shutdown-hook ordering (unspecified) vs `at_exit` (LIFO); `Process.waitFor` vs `process_status`.
- [Node.js](../nodejs.md) — shell-string APIs (`exec` vs `Sys.command`) share the injection lesson.
- [Signals overview](../signals/index.md) — the kernel semantics `Sys.signal`/`Unix.sigprocmask` bind.
- [Exit status conventions](../exit-status/index.md) — exit 2, 127, and 128+N in the wider system.
- [Interface ledger](../interfaces/index.md) — `fork`, `execve`, `wait4`, `sigaction` at the syscall layer.

## References

1. *Module Stdlib*, OCaml 5.2 manual, ocaml.org/manual/5.2/api/Stdlib.html (retrieved 2026-10).
2. *Module Sys*, OCaml 5.2 manual, ocaml.org/manual/5.2/api/Sys.html (retrieved 2026-10).
3. *Module Unix*, OCaml 5.2 manual, ocaml.org/manual/5.2/api/Unix.html (retrieved 2026-10).
4. *Module Printexc*, OCaml 5.2 manual, ocaml.org/manual/5.2/api/Printexc.html (retrieved 2026-10).
5. *Module Domain*, OCaml 5.2 manual, ocaml.org/manual/5.2/api/Domain.html (retrieved 2026-10).
6. *Chapter 25 (Runtime system / ocamlrun) — OCAMLRUNPARAM*, OCaml 5.2 manual, ocaml.org/manual/5.2/runtime.html (retrieved 2026-10).
7. *Chapter 22 (Interfacing C with OCaml) — signals, safe points, `caml_process_pending_actions`*, OCaml 5.2 manual, ocaml.org/manual/5.2/intfc.html (retrieved 2026-10).
8. OCaml 5.2 sources: `stdlib/sys.mli`, `otherlibs/unix/unix.mli` (github.com/ocaml/ocaml, tag 5.2, retrieved 2026-10) — used to verify absent APIs (`Sys.exit`, `Sys.break_exception`, `Sys.error_message`, `Unix.sigaction`, `Unix.wait4`) and the `handle_unix_error` signature.
9. OCaml 4.14 / 4.06 / 4.02 / 4.00 / 3.12 `otherlibs/unix/unix.mli` (github.com/ocaml/ocaml, retrieved 2026-10) — used to establish the historical absence of `Unix.sigaction`.
