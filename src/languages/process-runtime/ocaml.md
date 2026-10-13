# OCaml: Language Semantics, Standard Library, Process APIs, and Subprocesses

**Declared scope (verified 2026-10-13):** OCaml **5.5.1**, released 2026-09-05 and
listed as the latest release on [ocaml.org/releases/latest](https://ocaml.org/releases/latest/)
on the retrieval date. Every signature below was transcribed from the OCaml 5.5.1
sources (`stdlib/*.mli`, `otherlibs/unix/unix.mli`, `otherlibs/systhreads/thread.mli`,
runtime `runtime/*.c`) fetched from github.com/ocaml/ocaml at tag `5.5.1`, cross-checked
against the rendered library manual at `ocaml.org/manual/5.5/api/*` and the language
manual at `ocaml.org/manual/5.5/*.html`. APIs the task brief asked about that **do not
exist in 5.5.1** (`Sys.exit`, `Sys.setenv`/`Sys.unsetenv`, `Sys.break_exception`,
`Sys.error_message`, `Unix.sys_signal`, `Unix.sigaction`, `Unix.wait4`/`waitid`,
`Thread.kill`, `signalfd`/`pidfd` bindings) are recorded as **verified-absent**, never
invented. Platform: Linux; POSIX deltas and Windows degradations are labeled where the
documentation states them. Behaviors that neither the 5.5 manual nor the 5.5.1 sources
document are explicitly marked **undocumented/source-limited**, not reconstructed.

Layer labels used throughout:

- **[language]** — OCaml the language, per the 5.5 language manual (`expr.html`,
  `patterns.html`, `comp.html`, …).
- **[OCaml runtime]** — the `runtime/*.c` support program that bytecode and native
  executables link; mediates startup, exit, signals, GC.
- **[Stdlib]** / **[Unix library]** — the standard library (`Stdlib`, `Sys`,
  `Printexc`, `Domain`, `Gc`, `Fun`, `Effect`, `Mutex`, `Condition`, `Semaphore`)
  and the `unix` library binding POSIX (`Unix`), both part of the official
  distribution.
- **[POSIX]** / **[Linux]** — kernel-level behavior the bindings wrap.

**Reading map.** This chapter is the Section G deep dive. The exit/signal-scoped
companion is [OCaml: Exit Status, Signals, and Process Lifecycle](../../linux/process-exit-signal/languages/ocaml.md)
(IDs `LG-OC-*`; this chapter uses `PL-OC-*` and does not duplicate its ledger).
Hub: [Process & Runtime Semantics by Language](./index.md). The OS substrate under
every OCaml call is documented in [C: ISO C, POSIX, and Linux process APIs](./c.md).
Comparisons live in the sibling chapters ([python.md](./python.md),
[go.md](./go.md), [java.md](./java.md), [nodejs.md](./nodejs.md)) and the hub's
comparison page.

---

## 1. Syntax and Semantics

### 1.1 Expressions, `let`-bindings, scoping [language]

OCaml is an eager, call-by-value, expression-oriented language. A program is a
sequence of *structure items*; the top-level item conventionally used as "main" is a
unit binding `let () = …`. Bindings are lexically scoped; `let … in` introduces a
local scope, and shadowing is permitted. An *imperative* binding `let x = e1 and y =
e2` (the parallel `and` form) and the simple `let x = e1 in e2` differ in scope, not
in evaluation order — see §1.3 for what the manual actually specifies.

Compilation-unit structure is the process-level analogue of scoping: per the
[compilation units chapter](https://ocaml.org/manual/5.5/comp.html), command-line
order on the `ocamlc`/`ocamlopt` line is the link order, and "compilation units are
initialized in that order at run-time, and it is a link-time error to use a component
of a unit before having initialized it." This is the documented rule behind OCaml's
"main is the initializer of the last linked unit" behavior (§3.1).

### 1.2 Functions: currying, labeled and optional arguments [language]

Functions are first-class and n-ary application is curried application: `f a b` is
`(f a) b`. Labeled arguments (`f ~key:value`) and optional arguments
(`f ?(opt=default) ()`) are part of the core language; the standard library uses
them heavily (e.g. `Fun.protect ~finally:… work`, `Unix.dup ~cloexec:true fd`).
Two application operators with fixed precedence exist in `Stdlib` (verified
signatures, `stdlib.mli`):

```ocaml
external ( |> ) : 'a -> ('a -> 'b) -> 'b = "%revapply"   (* left-assoc pipeline *)
external ( @@ ) : ('a -> 'b) -> 'a -> 'b = "%apply"      (* right-assoc apply  *)
external ignore : 'a -> unit = "%ignore"                 (* discard a result   *)
```

`x |> f |> g` is exactly `g (f x)`; `g @@ f @@ x` is exactly `g (f x)`. These are
documented as operators, not magic: they exist to control precedence around
side-effecting calls such as `Sys.command` and `Unix.kill`.

### 1.3 Evaluation order — the manual says "not specified" [language]

This is a frequently mis-stated area, so here are the exact 5.5 sentences
([The OCaml language, 7. Expressions](https://ocaml.org/manual/5.5/expr.html), retrieved 2026-10-13):

- Function application: "**The order in which the expressions `expr`, `argument 1`,
  …, `argument n` are evaluated is not specified.**"
- Tuple expressions: "The evaluation order of the subexpressions **is not
  specified**."
- Record construction: "The order in which `expr 1` to `expr n` are evaluated **is
  not specified**."

Historically the compiler evaluated such expressions right-to-left, and older
manuals/FAQs described that; the 5.5 manual deliberately declines to specify. The
practical rules this chapter draws, strictly within the manual's authority:

- Never let two side-effecting subexpressions (e.g. `Unix.write` on one side, a
  `ref` update on the other) share an application, tuple, or record literal and
  depend on their relative order. Sequence them with `let … in` or `;`.
- Sequencing `e1; e2` and `let x = e1 in e2` are the documented ordered forms.

Example of the hazard (order of the two writes is unspecified by the manual):

```ocaml
(* DON'T: both orderings are legal per the manual *)
let () = ignore (Unix.write fd buf1 0 n, Unix.write fd buf2 0 n)
(* DO: explicit sequence *)
let () = let (_ : int) = Unix.write fd buf1 0 n in
         let (_ : int) = Unix.write fd buf2 0 n in ()
```

### 1.4 Variants, pattern matching, exhaustiveness [language]

Variant types (`type t = A | B of int`) are closed and their constructors are
statically known, so the compiler type-checks every `match` for **exhaustiveness**
and unreachable-case redundancy; an incomplete match is a compile-time diagnostic
(the pattern-matching warning family), and code does not compile with warnings as
errors until every constructor is covered or explicitly disregarded. This is
compile-time checking, not a runtime `MatchFailure` path — although the runtime
still defines `exception Match_failure of (string * int * int)` (verified,
`stdlib.mli`) for the cases that survive compilation (polymorphic variants, `Obj`
abuse).

The extensional variant `exn` is the type of exceptions and is *extensible*: any
`exception E of t` declaration adds a constructor to it (§1.5).

**Refutation cases.** The brief asks for the `pattern -> .` refutation-case syntax
(introduced 4.07). Its documentation page could not be located in the 5.5 manual
pages fetched (`expr.html`, `patterns.html`, `extn.html` contain no "refut*"
wording) — recorded as **source-limited** (PL-OC-005) rather than paraphrased from
memory.

### 1.5 Exceptions: declaration, raise, try-with [language]

`exception E of …` declares a constructor of the extensible type `exn`. `raise e`
aborts evaluation of the current expression and unwinds to the nearest enclosing
handler; `try e with p -> …` catches by pattern; `match x with … | exception e ->
…` (an expression-level extension since 4.02) handles an exception raised while
evaluating the *scrutinee*. The two standard constructors used for precondition
failures are verified from `stdlib.mli`:

```ocaml
val failwith : string -> 'a     (** Raise exception [Failure] with the given string. *)
val invalid_arg : string -> 'a  (** Raise exception [Invalid_argument] with the given string. *)
```

**Exceptions are unchecked.** Nothing in the language or library annotates which
exceptions a function can raise; there is no `throws` clause and no obligation to
handle anything. Uncaught exceptions terminate the process with exit code 2 (§3.4).

`Stdlib` also defines (verified) `exception Failure of string`,
`exception Invalid_argument of string`, `exception Match_failure`,
`exception Assert_failure of (string * int * int)`, and — important for this
chapter — `exception Exit`:

> "The `Exit` exception is not raised by any library function. It is provided for
> use in your programs." (`stdlib.mli`, 5.5.1)

That sentence settles a common misconception: **`Stdlib.exit` does not raise
`Exit`** — `exit` is implemented as `do_at_exit (); sys_exit retcode` (`stdlib.ml`,
verified §3.2) and terminates directly. Raising `Exit` yourself is an ordinary
uncaught exception unless you catch it (exit status 2 per §3.4, not your chosen
code).

### 1.6 Backtraces [OCaml runtime]

From the [runtime chapter](https://ocaml.org/manual/5.5/runtime.html) (verified
2026-10-13):

- `ocamlrun -b`: "When the program aborts due to an uncaught exception, print a
  detailed 'back trace' of the execution, showing where the exception was raised
  and which function calls were outstanding at this point. The back trace is
  printed only if the bytecode executable contains debugging information, i.e. was
  compiled and linked with the `-g` option to `ocamlc`."
- `OCAMLRUNPARAM=b` — "Trigger the printing of a stack backtrace when an uncaught
  exception aborts the program. An optional argument can be provided: `b=0` turns
  backtrace printing off; `b=1` is equivalent to `b`…; `b=2` [loads] debugging
  information at program startup time instead of at backtrace printing time. `b=2`
  can be used if the runtime is unable to load debugging information at backtrace
  printing time, for example if there are no file descriptors available."

Native executables need `-g` at link time for location information; without debug
info the backtrace is an exception-only frame list or absent. `Printexc.record_backtrace
: bool -> unit` toggles recording at runtime (§2).

### 1.7 Modules and functors as the organizing unit [language]

OCaml has no namespaces separate from its module system: `Sys`, `Unix`, `Gc`,
`Domain`, `Thread` are modules, and a functor `module M = F(X)` is a function from
modules to modules. For this chapter the relevant consequence is dependency
architecture: the `Stdlib` module is auto-linked; `Sys`/`Gc`/`Domain` live in the
standard library; the `Unix` library is a separate *library* (`unix.cma`/`unix.cmxa`,
linked via `-package unix` / `-linkpkg` with ocamlfind, or `unix` with dune) that
wraps POSIX. A program that never links `unix` cannot call `Unix.fork` — the split
between [Stdlib]/[Unix library] layers below is a real, linkable boundary.

### 1.8 Mutable state [language]

Three verified forms: `ref` cells (`Stdlib`: `type 'a ref = { mutable contents : 'a }`),
`mutable` record fields, and fixed-length `Atomic.t` cells (sequential consistency
guaranteed per `Atomic.mli`). Fields marked `mutable` are updated with `x.f <- e`.
Mutable state is how signal handlers (§4.1) and `at_exit` hooks communicate with
program logic; the unsynchronized-access caveat applies — the standard library
annotates such globals with `[@@alert unsynchronized_access …]` (verified on
`Sys.interactive`, `Sys.enable_runtime_warnings`), and cross-domain sharing needs
`Atomic` or locks (§6).

### 1.9 Values and GC: minor/major heap, finalisers [OCaml runtime]

The OCaml 5 runtime gives every **domain** its own minor heap and shares the major
heap; `Gc` exposes the knobs (verified, `gc.mli`):

```ocaml
external minor : unit -> unit = "caml_gc_minor"        (* trigger minor collection  *)
external major : unit -> unit = "caml_gc_major"        (* finish current major cycle slice *)
external full_major : unit -> unit = "caml_gc_full_major"
external compact : unit -> unit = "caml_gc_compaction"
val finalise : ('a -> unit) -> 'a -> unit
val finalise_last : (unit -> unit) -> 'a -> unit
val finalise_release : unit -> unit
```

`finalise` documented timing (verbatim, `gc.mli`): "`f` will be called with `v` as
argument **at some point between the first time `v` becomes unreachable** … **and
the time `v` is collected by the GC**. … Each instance will be called once (**or
never, if the program terminates before `v` becomes unreachable**)." Two process-level
consequences: finalisers are *not* deterministic cleanup (use `Fun.protect` /
`at_exit` for that, §3), and **finalisers do not run at process exit for values
still reachable** — exactly the wording above.

`Gc.stat : unit -> stat` "causes a full major collection" (verified doc), so it is
not free; `Gc.quick_stat` is the cheap variant. Runtime GC parameters come from
`OCAMLRUNPARAM` (`s=` minor-heap words, `h=` major-heap policy, `l=` stack size,
`v=` verbosity, …) and "correspond to fields of the control record documented in
Module Gc" ([runtime manual](https://ocaml.org/manual/5.5/runtime.html)).

### 1.10 Tail calls [language]

Long-running daemons in OCaml are conventionally written as tail-recursive loops;
self-tail-recursion is compiled as a loop by the OCaml implementation, which is why
`OCAMLRUNPARAM` documents a fixed-size runtime stack (`l=`, §1.9): "This is relevant
to both the byte-code runtime and the native code runtime: OCaml always uses its own
stack and not the [system stack]" (runtime manual, verified fragment). The precise
normative wording of a *guarantee* of proper tail calls is **not present in the 5.5
language manual pages fetched** — recorded as **source-limited** (PL-OC-012). What
is citable: the dedicated runtime stack with a configurable size, and the
`Stack_overflow` exception of §3.5 that exists when the limit is hit non-tail-recursively.

### 1.11 Version deltas 4.14 → 5.5 relevant to this chapter

All verified against the 5.5.1 sources and `@since` annotations:

- **Multicore runtime (5.0+)**: `Domain` module; effects (`Effect`); `Unix.fork`
  fails once a domain has been spawned (§5.1); signal handling moves to the
  safe-point model (§4.1); `Thread.exit` re-implemented as an exception (§6.4).
- **`Stdlib.Condition`, `Stdlib.Mutex`, `Stdlib.Semaphore`** are standard-library
  modules in 5.5 (verified: `stdlib/mutex.mli`, `stdlib/condition.mli`,
  `stdlib/semaphore.mli`); `Thread` and `Event` remain in the `threads` library
  (`otherlibs/systhreads/`).
- **5.3**: `Sys.poll_actions : unit -> unit` — "Run any pending runtime actions,
  such as minor collections, major GC slices, signal handlers, finalizers, or
  memprof callbacks" (`sys.mli`); `Domain.self_index` (5.3).
- **5.4**: `Sys.signal`'s argument and `Unix.kill`'s second argument become
  `Sys.signal`-typed (`type signal = int` with platform-independent negative
  numbers, `signal_of_int`/`signal_to_int`/`signal_to_string` added);
  `Sys.sigio`/`Sys.sigwinch` added; `Unix.sigwait` added (§4.4);
  `Sys.io_buffer_size` added; `Thread.set_current_thread_name` added (5.4).
- **5.5**: `Unix.unsetenv` added; `Sys.runtime_executable` added; `Domain.count`
  added; `Gc.Tweak` added; `Unix.kill` on Windows changed to exit code 1067
  (previously 0) — verified in the `kill` doc (§5.6).
- **Removed/never-present**: `Sys.exit` (removed long ago; only `Stdlib.exit`),
  `Thread.kill` (absent from `thread.mli` in 5.5.1 — verified), `Sys.setenv`/
  `Sys.unsetenv` (only `Unix.putenv`/`Unix.unsetenv` exist — verified absent from
  `sys.mli`).

### 1.12 Misconceptions (each verified above)

- "`Sys.exit 1`" — no such binding in 5.5.1; it is `Stdlib.exit` (§2).
- "`exit` raises `Exit`" — no; `Exit` "is not raised by any library function" (§1.5).
- "OCaml guarantees left-to-right (or right-to-left) argument order" — the 5.5
  manual says "not specified" for application/tuples/records (§1.3).
- "Exceptions are checked / must be caught" — unchecked; uncaught ⇒ exit 2 (§1.5, §3.4).
- "Finalisers are cleanup hooks" — timing is GC-dependent and may never run (§1.9).
- "`try … with` around a long computation protects against Ctrl-C" — only if
  `Sys.catch_break true` was called; default SIGINT terminates (§4.2).

---

## 2. Standard-Library and Runtime API Inventory

Signatures are the exact 5.5.1 declarations. "v-a" = verified-absent.

### 2.1 `Stdlib` (process-relevant surface)

| API | Canonical signature | Semantics (documented) |
|---|---|---|
| `exit` | `val exit : int -> 'a` | Flush all output channels; run `Domain.at_exit` then `at_exit` callbacks; terminate with status (§3.2) |
| `Exit` | `exception Exit` | "not raised by any library function"; no exit-status meaning |
| `at_exit` | `val at_exit : (unit -> unit) -> unit` | LIFO; runs on `exit`, normal termination, uncaught exception, `caml_shutdown` |
| `do_at_exit` | `val do_at_exit : unit -> unit` | Internal ("for system use only. Do not call directly", `stdlib.mli`); runs domain-local hooks then the `at_exit` chain (`stdlib.ml` verified) |
| `failwith` | `val failwith : string -> 'a` | Raises `Failure s` |
| `invalid_arg` | `val invalid_arg : string -> 'a` | Raises `Invalid_argument s` |
| `flush_all` | `val flush_all : unit -> unit` | "Flush all open output channels; ignore errors." |
| `prerr_endline` | `val prerr_endline : string -> unit` | Print + newline on stderr, flush stderr |
| `ignore` | `external ignore : 'a -> unit = "%ignore"` | Discard value |
| `\|>`, `@@` | `external ( \|> ) : 'a -> ('a -> 'b) -> 'b = "%revapply"` / `external ( @@ ) : ('a -> 'b) -> 'a -> 'b = "%apply"` | Application operators (§1.2) |

`Sys.exit` — **v-a** (no `exit` in `sys.mli` 5.5.1; the only exit function is
`Stdlib.exit`).

### 2.2 `Sys`

| API | Canonical signature | Notes (documented) |
|---|---|---|
| `argv` | `external argv : string array = "%sys_argv"` | Command line; `argv.(0)` is the command name |
| `executable_name` | `val executable_name : string` | File containing the executable; absolute or relative per platform/bytecode |
| `runtime_executable` | `val runtime_executable : string` | The running runtime (`ocamlrun` in bytecode); **since 5.5** |
| `getenv` | `external getenv : string -> string = "caml_sys_getenv"` | `@raise Not_found` if unbound |
| `getenv_opt` | `val getenv_opt : string -> string option` | Since 4.05 |
| `setenv`/`unsetenv` | — | **v-a** in `Sys` (5.5.1); `Unix.putenv`/`Unix.unsetenv` are the documented way |
| `command` | `external command : string -> int = "caml_sys_system_command"` | Shell-interpreted (`sh`; `cmd.exe` on Windows); quoting via `Filename.quote_command` (§5.7); the 5.5 doc does *not* state a 127-on-failure rule (that is documented for `Unix.system`) |
| `file_exists` | `external file_exists : string -> bool = "caml_sys_file_exists"` | |
| `os_type` | `val os_type : string` | `"Unix"` / `"Win32"` / `"Cygwin"` |
| `word_size` | `val word_size : int` | 32 or 64 |
| `backend_type` | `val backend_type : backend_type` | `Native \| Bytecode \| Other of string` (since 4.04) |
| `ocaml_version` | `val ocaml_version : string` | e.g. `"5.5.1"` |
| `poll_actions` | `external poll_actions : unit -> unit = "%poll"` | Runs pending signal handlers/finalisers/GC slices; **since 5.3** |
| `enable_runtime_warnings` | `val enable_runtime_warnings : bool -> unit` | Warns when an `open_*` channel is finalized unclosed — useful leak detector (§6.6) |

Signal surface (§4): `type signal = int` (since 5.4),
`type signal_behavior = Signal_default \| Signal_ignore \| Signal_handle of (signal -> unit)`,
`external signal : signal -> signal_behavior -> signal_behavior = "caml_install_signal_handler"`
(returns the *previous* behavior), `val set_signal : signal -> signal_behavior -> unit`,
the POSIX constants `sigabrt … sigwinch` (`sigio`/`sigwinch` since 5.4),
`signal_of_int`/`signal_to_int`/`signal_to_string` (since 5.4),
`exception Break`, `val catch_break : bool -> unit`.
`Sys.break_exception` and `Sys.error_message` — **v-a** in 5.5.1 (the error-string
helper is `Unix.error_message : Unix.error -> string`).

### 2.3 `Printexc`

| API | Canonical signature | Notes |
|---|---|---|
| `default_uncaught_exception_handler` | `val default_uncaught_exception_handler : exn -> raw_backtrace -> unit` | "prints the exception and backtrace on standard error output" |
| `set_uncaught_exception_handler` | `val set_uncaught_exception_handler : (exn -> raw_backtrace -> unit) -> unit` | Called after `at_exit` hooks have run (§3.4); a raising handler triggers the documented double-fatal path |
| `record_backtrace` / `backtrace_status` | `val record_backtrace : bool -> unit` / `val backtrace_status : unit -> bool` | Runtime toggle; initial value from the `b` OCAMLRUNPARAM flag |
| `get_backtrace` | `val get_backtrace : unit -> string` | |
| `get_callstack` | `val get_callstack : int -> raw_backtrace` | Since 4.01 |

### 2.4 Runtime controls (`OCAMLRUNPARAM`)

Verified from the [runtime chapter](https://ocaml.org/manual/5.5/runtime.html):
`b` (backtrace; `b=0/1/2` variants, §1.6), `c` (`cleanup_on_exit` — "Shut the
runtime down gracefully on exit (see `caml_shutdown`…). The option also enables
pooling"; visible to leak checkers), `l=` (runtime stack size — "OCaml always uses
its own stack"), and the GC parameters `s=`, `h=`, `i=`, `o=`, `O=`, `v=`, … which
"correspond to fields of the control record documented in Module Gc". `Sys.runtime_parameters
: unit -> string` returns the effective settings (4.03+).

### 2.5 `Gc` surface in scope

`minor`/`major`/`full_major`/`compact`/`major_slice` (§1.9),
`finalise`/`finalise_last`/`finalise_release`, `create_alarm : (unit -> unit) -> alarm`
/`delete_alarm` (callback "at the end of major GC cycles… on the same domain that
created the alarm"), `stat` (forces a full major collection), `quick_stat`,
`counters`, `minor_words`, `get`/`set` of `control`, `Tweak` (5.5).

---

## 3. Process Creation and Termination

### 3.1 Runtime startup [OCaml runtime]

`ocamlc` emits bytecode run by `ocamlrun` (or `-custom`); `ocamlopt` emits native
executables. In both cases entry is the runtime's `caml_main`/`caml_startup`
(`runtime/startup_nat.c`, verified: `void caml_main(char_os **argv) { caml_startup(argv); }`),
which initializes the runtime (signal setup, GC), then evaluates the linked
compilation units' initializers **in link order** (§1.1), then performs the
documented "implicit `exit 0`" (§3.3). If the last initializer raises, the startup
code calls `caml_fatal_uncaught_exception` (verified call sites,
`startup_nat.c`/`startup_byt.c`). The toplevel `ocaml` is a different program:
`Sys.interactive` is `true` there (verified doc), and no `exit 0`-style process
semantics apply to toplevel phrases.

### 3.2 `Stdlib.exit` — exact mechanics [Stdlib]

Verified implementation, `stdlib.ml` 5.5.1:

```ocaml
let do_at_exit () =
  (!do_domain_local_at_exit) ();      (* runs Domain.at_exit hooks  *)
  (atomic_get exit_function) ()       (* runs the Stdlib.at_exit chain *)

let exit retcode =
  do_at_exit ();
  sys_exit retcode                    (* C primitive caml_sys_exit *)
```

Documented behavior (`stdlib.mli`): "Terminate the process… All open output
channels are flushed with `flush_all`. The callbacks registered with `Domain.at_exit`
are called followed by those registered with `Stdlib.at_exit`. An implicit
`exit 0` is performed each time a program terminates normally. An implicit
`exit 2` is performed if the program terminates early because of an uncaught
exception."

So the full shutdown sequence on `exit n` is: **`flush_all` → `Domain.at_exit`
hooks (LIFO, per domain) → `Stdlib.at_exit` hooks (LIFO, process-wide) →
`caml_sys_exit n`**. In the runtime, `caml_sys_exit` calls `caml_do_exit`
(`runtime/sys.c`, verified), which emits GC stats if `v` verbosity asks for them,
destroys runtime events, notifies the debugger (bytecode only), runs
`caml_shutdown` **iff** `cleanup_on_exit` (the `OCAMLRUNPARAM=c` flag) is set,
terminates the runtime's own signal handlers, and finally performs the C
`exit(retcode)`.

`Stdlib.exit` does **not** raise `Exit` (§1.5) and does not return (`int -> 'a`).
`do_at_exit` itself is exposed in `stdlib.mli` only under the "system use only — do
not call directly" marker (§2.1); do not build on it.

### 3.3 Termination triggers for `at_exit` [Stdlib]

Verified list: registered functions run when the program (a) "executes `exit`",
(b) "terminates, either normally or because of an uncaught exception", (c)
"executes the C function `caml_shutdown`". They are called "in 'last in, first
out' order". They are **not** run when the process dies by signal with default
disposition (SIGKILL/SIGTERM/SIGINT without `catch_break`) or by `Unix._exit`.

Exceptions raised *inside* `at_exit` handlers: in the normal `exit` path they are
not caught by anything registered — the exception propagates out of
`do_at_exit` and, since `exit` never got to `sys_exit`, the process terminates via
the uncaught-exception machinery (§3.4). In the *uncaught-exception* path the
runtime wraps the whole `do_at_exit` in `try … with _ -> ()` (verified,
`printexc.ml`: `(try Stdlib.do_at_exit () with _ -> ()); …`) — there, a raising
`at_exit` hook is silently swallowed so that the original exception can be
reported. That asymmetry is a verifiable, load-bearing detail.

### 3.4 Uncaught exceptions → "Fatal error: exception …", exit 2 [OCaml runtime]

The verified chain, byte-for-byte:

1. `caml_fatal_uncaught_exception(exn)` (`runtime/printexc.c`) calls the
   `Printexc.handle_uncaught_exception` callback.
2. That OCaml function (`stdlib/printexc.ml`, `handle_uncaught_exception'`)
   captures the backtrace, runs `Stdlib.do_at_exit ()` with all exceptions
   swallowed (§3.3), then calls the current `uncaught_exception_handler`
   (default = `Printexc.default_uncaught_exception_handler`).
3. The default handler prints **`Fatal error: exception %s`** (verified format
   string, `printexc.ml`) followed by the backtrace if enabled (§1.6).
4. Back in `printexc.c`: "**exit(2)**" (verified: `} else { exit(2); }`; an
   `abort()` variant exists behind `caml_abort_on_uncaught_exn`, a runtime-internal
   knob not exposed through the OCaml API).

Replacing the handler with `Printexc.set_uncaught_exception_handler` changes step
3; the documented caveat (per 5.2 manual text carried in the LG chapter, still the
mechanics here) is that when your handler runs, `at_exit` hooks have *already* run,
so you must flush what you write. If the replacement handler itself raises, the
runtime prints both "Fatal error: exception %s" and "Fatal error in uncaught
exception handler: exception %s" (verified strings, `printexc.ml`).

```ocaml
(* uncaught.ml — expected behavior *)
let () = failwith "boom"
(* $ ocamlc uncaught.ml -o uncaught && ./uncaught; echo $?
     Fatal error: exception Failure("boom")
     2
   $ ocamlc -g uncaught.ml -o uncaught && OCAMLRUNPARAM=b ./uncaught; echo $?
     Raised at Uncaught in file "uncaught.ml", line 1, characters 9-23
     Called from Uncaught in file "uncaught.ml", line 1, characters 9-23
     Fatal error: exception Failure("boom")
     2                                                              *)
```

### 3.5 Stack overflow [language]/[OCaml runtime]

The runtime owns its stack with a configurable size (`OCAMLRUNPARAM l=size`,
§1.10). Exceeding it during OCaml evaluation raises the **catchable**
`Stack_overflow` exception (the runtime's exception table contains
`caml_exn_Stack_overflow`, `runtime/fail_nat.c`, verified). Caught → your handler
runs and the process continues; uncaught → the standard §3.4 path, "Fatal error:
exception Stack_overflow", exit 2. What is *not* documented in the 5.5 manual or
the fetched 5.5.1 runtime files is the native-code SIGSEGV→`Stack_overflow`
conversion path (the `fail_nat.c` comment references a `segv_handler in
signals_nat.c`, but the 5.5.1 `signals_nat.c` no longer contains one) — that
mechanism is **source-limited** (PL-OC-035). The C-level consequence is
non-controversial: a stack overflow that escapes as an uncaught exception exits 2
via §3.4.

### 3.6 Exit-status range and truncation [OCaml runtime]/[POSIX]

`caml_do_exit` ends with the C `exit(retcode)` (verified, `sys.c`), so the status
the parent observes through `wait`/`waitpid` is the POSIX-truncated
`status & 0xFF` (see the C chapter's exit(3) coverage). OCaml adds nothing: any
`int` is accepted, the low 8 bits are what survives. The three *documented* OCaml
statuses are: implicit `exit 0` (normal), `exit 2` (uncaught exception, §3.4), and
`Unix.handle_unix_error`'s "prints a message … and **exits with code 2**"
(verified, `unix.mli`). `Unix.system`'s shell-failure value `WEXITED 127` is a
*child* status convention, §5.7.

### 3.7 "Process" vs domain vs thread vs child [language]/[OCaml runtime]

The OCaml process is the OS process; exit from anywhere ends everything (§3.2).
Inside it: **domains** (`Domain.spawn`) are parallel units with their own minor
heaps; **systhreads** (`Thread.create`) are preemptively scheduled threads within a
domain. Neither is individually killable by documented API — there is no
`Domain.kill` (verified-absent from `domain.mli`) and no `Thread.kill` (verified-absent
from `thread.mli`); threads end by returning (or `raise Thread.Exit`, §6.4), and a
domain ends when its function returns — `Domain.join` then "tries to join those
systhreads … before returning" (verified doc, `domain.mli`). A forked child is a
whole new process (§5.1). Concurrency semantics are §6.

### 3.8 `Unix._exit` — the no-finalization path [Unix library]

```ocaml
val _exit : int -> 'a
```

Verified doc: "Terminate the calling process immediately… Unlike `Stdlib.exit`,
`Unix._exit` performs **no finalization whatsoever**: functions registered with
`at_exit` are not called, input/output channels are not flushed, and the C
run-time system is not finalized either. The typical use of `_exit` is after a
`Unix.fork` operation, when the child process runs into a fatal error and must
exit… output channels should not be flushed by the child process, as the parent
process may flush them again later, resulting in duplicate output."

---

## 4. Signals and OS Interaction

### 4.1 The delivery model: deferred to safe points [OCaml runtime]

The one-sentence manual model ([Interfacing C with OCaml](https://ocaml.org/manual/5.5/intfc.html), verified 2026-10-13):
allocation functions "are guaranteed not to run any OCaml code, including
finalisers, signal handlers and other threads running on the same domain. Instead,
their execution is delayed to a later safe point. The function
`caml_process_pending_actions` from `<caml/signals.h>` executes any pending signal
handlers and finalisers, Memprof callbacks, preemptive systhread switching, and
requested minor and major garbage collections. In particular, it can raise
asynchronous exceptions and cause mutations on the OCaml heap from the same
domain."

Consequences, all derived from that documented model:

- An OCaml handler installed via `Sys.signal` does **not** run inside the kernel's
  signal frame; it runs when the interrupted OCaml code reaches a safe point. An
  allocation-free loop can delay delivery indefinitely — `Sys.poll_actions` (5.3+)
  is the documented manual pump for such loops (§2.2).
- Because handlers run as ordinary OCaml code at safe points, **async-signal-safety
  is a non-issue at the OCaml level**: the runtime defers everything to a context
  where the allocator and GC are legal. This is the same architectural answer as
  CPython's, documented here for OCaml.
- Exceptions raised inside a handler are ordinary exceptions that "propagate into
  the interrupted OCaml code" — the `caml_process_pending_actions` doc says
  precisely that it "can raise asynchronous exceptions" (verified). A `Sys.Break`
  or handler-raised exception can therefore surface at almost any allocation point.
- C-FFI interplay: C stubs that can run long without allocating are *supposed* to
  call `caml_process_pending_actions` regularly (same manual section, verified);
  their author should also mind the native runtime's own SIGSEGV/SIGTRAP/SIGFPE
  handlers: "the native-code runtime system may install signal handlers for one or
  several of the SIGSEGV, SIGTRAP and SIGFPE signals when `caml_startup` is called,
  and reset these signals to their default behaviors when `caml_shutdown` is
  called. The main program written in C should not try to handle these signals
  itself." (verified quote). The GC-signal interplay is visible in
  `runtime/signals_nat.c`: the signal-handling slot exists so that generated code
  can call `caml_garbage_collection` at allocation points — i.e. SIGALRM-class
  delivery and collection scheduling share the safe-point machinery.

### 4.2 `Sys.signal`, `signal_behavior`, `catch_break`, `Break` [Stdlib]

```ocaml
type signal_behavior =
  | Signal_default | Signal_ignore | Signal_handle of (signal -> unit)

external signal :
  signal -> signal_behavior -> signal_behavior = "caml_install_signal_handler"
val set_signal : signal -> signal_behavior -> unit
exception Break          (* raised on interactive interrupt if catch_break enabled *)
val catch_break : bool -> unit
```

`Sys.signal` "Return[s] the behavior previously associated with the signal" and
raises `Invalid_argument` "if the signal number is invalid (or not available on
your system)" (verified doc). `catch_break` "governs whether interactive interrupt
(ctrl-C) terminates the program or raises the `Break` exception. Call
`catch_break true` to enable raising `Break`, and `catch_break false` to let the
system terminate the program on user interrupt." Multi-threaded caveat (verified):
"Inside multi-threaded programs, the `Break` exception will arise in any one of the
active threads, and will keep arising on further interactive interrupt until all
threads are terminated. Use signal masks from `Thread.sigmask` to direct the
interrupt towards a specific thread."

```ocaml
let () =
  Sys.catch_break true;                       (* Ctrl-C becomes Sys.Break *)
  try
    (* long-running serve loop *)
    Unix.sleep 3600
  with Sys.Break ->
    prerr_endline "interrupted; shutting down";
    exit 130                                  (* conventional 128+SIGINT *)
```

Note there is **no `Unix.sys_signal` and no `Unix.sigaction`** in 5.5.1 (verified
absent; the Unix module's Signals section itself says installation is performed
via `Sys.signal`/`Sys.set_signal`). One-shot old-behavior recovery is `Sys.signal`'s
return value.

### 4.3 Blocking and inspecting: `Unix` mask primitives [Unix library]

```ocaml
type sigprocmask_command = SIG_SETMASK | SIG_BLOCK | SIG_UNBLOCK
val sigprocmask : sigprocmask_command -> Sys.signal list -> Sys.signal list
(** returns the set of previously blocked signals *)
val sigpending : unit -> Sys.signal list
val sigsuspend : Sys.signal list -> unit
val sigwait : Sys.signal list -> Sys.signal        (* since 5.4 *)
val pause : unit -> unit
val alarm : int -> int                              (* SIGALRM after n seconds *)
val sleep : int -> unit
val sleepf : float -> unit                          (* since 4.03 *)
```

Documented notes: `sigsuspend` "atomically sets the blocked signals to `sigs` and
waits for a non-ignored, non-blocked signal to be delivered. On return, the
blocked signals are reset to their initial value." `sigwait` (5.4) "removes this
signal from the set of pending signals, and returns the number of this signal.
Signal handlers attached to the signals in `sigs` will not be invoked. The signals
`sigs` are expected to be blocked before calling `sigwait`." On Windows all of
these raise `Invalid_argument` ("no inter-process signals on Windows" — verified).
When the systhreads library is linked, `Unix.sigprocmask` operates on the current
thread's mask (documented in the LG chapter from the same source lineage; the
thread-level tool is `Thread.sigmask`, §4.4).

### 4.4 Which thread/domain sees the signal? [POSIX]/[OCaml runtime]

The `Thread` module's documented model (verified, `thread.mli`): "**Signal
handling follows the POSIX thread model: signals generated by a thread are
delivered to that thread; signals generated externally are delivered to one of the
threads that does not block it.** Each thread possesses a set of blocked signals,
which can be modified using `Thread.sigmask`. This set is inherited at thread
creation time. Per-thread signal masks are supported only by the system thread
library under Unix." The tools:

```ocaml
val sigmask : Unix.sigprocmask_command -> int list -> int list
val wait_signal : int list -> int          (* since 4.05; like sigwait for threads *)
```

For domains, the manual documents the safe-point deferral (§4.1) but does **not**
specify which domain's pending-actions queue receives an externally generated
signal, nor a documented API for targeting a domain — beyond the safe-point model
this area is **source-limited** (PL-OC-038), the same boundary the LG chapter
flagged for 5.2. What is documented and portable: block the signal in worker
threads/domains, let the (unblocked) thread that should handle it use
`Thread.wait_signal`/`Unix.sigwait`, and never mix `Sys.signal` handlers with
`sigwait` on the same signal (the doc says handlers "will not be invoked" for
`sigwait`ed signals).

### 4.5 Verified-absent OS-integration surfaces

Checked against 5.5.1 `unix.mli`/`sys.mli`: no `signalfd`, no `pidfd`, no
`Unix.sigaction`, no `Unix.sys_signal`, no rt-signals API. If you need them you
write C stubs (§4.6) or drop to the [Linux] layer documented in
[c.md](./c.md). The absence is consistent with the safe-point model: OCaml-level
code never handles signals *inside* the kernel frame, so `signalfd` buys little.

### 4.6 FFI interplay (brief) [OCaml runtime]

C stubs see the runtime, not the OS signal model: long-running C should call
`caml_process_pending_actions` (§4.1) so deferred handlers/finalisers/GC proceed;
allocation from C is the documented safe point boundary; the native runtime
pre-empts your own SIGSEGV/SIGTRAP/SIGFPE handlers (verified quote, §4.1). A C
stub that blocks a signal must restore the mask before returning to OCaml, or the
program's `Thread.sigmask`-based routing (§4.4) breaks — that discipline is POSIX
layer, not OCaml-documented.

---

## 5. Subprocess and Child-Process Management

### 5.1 `Unix.fork` — and the multicore rule [Unix library]

```ocaml
val fork : unit -> int
```

Verified doc: "Fork a new process. The returned integer is 0 for the child
process, the pid of the child process for the parent process. **It fails if the
OCaml process is multi-core (any domain has been spawned).** In addition, **if any
thread from the `Thread` module has been spawned, then the child process might be
in a corrupted state.** `@raise Invalid_argument` on Windows… `@raise Failure` if
any domain has been spawned."

The documented rule is exactly: fork **before** `Domain.spawn` (enforced) and
**before** `Thread.create` (unenforced hazard — the POSIX guarantee is that only
the calling thread survives in the child; §6.5). The GC×fork interaction follows
from the domain model: each domain owns a minor heap, so a forked child inherits
one coherent domain's heaps — there is no documented multi-domain fork support
because the documented behavior is failure, not copying.

### 5.2 The exec family [Unix library]

All four verified, all `-> 'a` (they never return on success):

```ocaml
val execv   : string -> string array -> 'a
val execve  : string -> string array -> string array -> 'a   (* + environment *)
val execvp  : string -> string array -> 'a                   (* PATH search   *)
val execvpe : string -> string array -> string array -> 'a   (* PATH + env    *)
```

Documented semantics: "`execv prog args` executes the program in file `prog`,
with the arguments `args`, and the current process environment. Note that the
first argument, `args.(0)`, is by convention the filename of the program being
executed, just like `Sys.argv.(0)`. These `execv*` functions **never return**: on
success, the current program is replaced by the new one." There are **no
list-based `execl` variants** in the OCaml API — the argument is always a `string
array` (verified; the mission-brief `execl` does not exist in `unix.mli`).

**Exec failure — verified from the implementation** (`otherlibs/unix/execvp.c`,
same shape in `execv.c`/`execve.c`): after the C `execvp` returns (failure), the
stub calls `caml_uerror("execvp", path)` — i.e. the child **raises
`Unix.Unix_error`**, it does **not** `_exit(127)`. In a fork+exec child, an
unhandled `Unix_error` therefore takes the uncaught-exception path: "Fatal error:
exception Unix.Unix_error(Unix.ENOENT, "execvp", …)", **exit 2**. The documented
recommendation for child error paths is `Unix._exit` (§3.8), precisely to avoid
running OCaml cleanup in a forked child; wrap your exec:

```ocaml
let () =
  match Unix.fork () with
  | 0 -> (try Unix.execvp "prog" [| "prog"; "-x" |] with
          | Unix.Unix_error (e, f, a) ->
              prerr_endline (Printf.sprintf "%s: %s: %s" f a (Unix.error_message e));
              exit 127)                 (* or Unix._exit 127: no parent-buffer flush *)
  | pid -> ignore pid
```

(`exit 127` here is your own convention, matching shell behavior; `Unix._exit 127`
is the stricter fork-safe form per the `_exit` doc.)

### 5.3 Waiting: `wait`, `waitpid`, `process_status`, `wait_flag` [Unix library]

```ocaml
type process_status =
  | WEXITED   of int          (* terminated normally by exit; the return code      *)
  | WSIGNALED of Sys.signal   (* killed by a signal; the signal number             *)
  | WSTOPPED  of Sys.signal   (* stopped by a signal; the signal number            *)

type wait_flag = WNOHANG | WUNTRACED
val wait    : unit -> int * process_status
val waitpid : wait_flag list -> int -> int * process_status
```

Verified: `wait` "Wait[s] until one of the children processes die, and return[s]
its pid and termination status" (`Invalid_argument` on Windows). `waitpid` pid
conventions: `-1` any child, `0` any child in our process group, negative =
process group, positive = that pid. Flags: `WNOHANG` — "Do not block if no child
has died yet, but immediately return with a pid equal to 0"; `WUNTRACED` — "Report
also the children that receive stop signals." `WSTOPPED` is therefore reachable
via `waitpid [WUNTRACED]` (or a ptrace attach), not from plain `wait`. Since 5.4
the signal payloads are `Sys.signal`-typed (§1.11) — decode with
`Sys.signal_to_int` before formatting `128+N` strings. Verified-absent: no
`wait4`, no `waitid`, no rusage — **no timeout parameter anywhere in the wait
family** (§5.11).

### 5.4 `Unix.kill` [Unix library]

```ocaml
val kill : int -> Sys.signal -> unit
```

Verified: "`kill pid signal` sends signal number `signal` to the process with id
`pid`." Windows note (5.5): only `Sys.sigkill` is emulated, "causing the receiving
process to exit with code ERROR_PROCESS_ABORTED (1067). Before OCaml 5.5, the
receiving process exited with code 0." POSIX pid-reuse hazard applies (§6.6).

### 5.5 `Unix.system` and `Sys.command` — the shell-string pair [Unix library]/[Stdlib]

```ocaml
val system : string -> process_status     (* /bin/sh -c string; waits *)
val Sys.command : string -> int           (* same shape, integer status *)
```

`Unix.system` verified doc: "Execute the given command, wait until it terminates,
and return its termination status. The string is interpreted by the shell
`/bin/sh` … and therefore can contain redirections, quotes, variables, etc. To
properly quote whitespace and shell special characters occurring in file names or
command arguments, the use of `Filename.quote_command` is recommended. **The
result `WEXITED 127` indicates that the shell couldn't be executed.**"

Injection hazard is structural: any user data in the string is shell input. The
documented defense is `Filename.quote_command` (verified signature,
`stdlib/filename.mli`):

```ocaml
val quote_command :
  string -> ?stdin:string -> ?stdout:string -> ?stderr:string -> string list -> string
(* "suitable for use as an argument to Sys.command, Unix.system, and the
    Unix.open_process functions" *)
```

```ocaml
let user = "x; rm -rf ~" in
Sys.command ("ls " ^ user)                             (* UNSAFE: two commands *)
Sys.command (Filename.quote_command "ls" [user])       (* SAFE: one argument  *)
```

Version nuance (verified above): `Sys.command`'s 5.5 doc does not spell out the
127-on-shell-failure rule; only `Unix.system` documents `WEXITED 127`.

### 5.6 `create_process` — exec with redirects, no shell [Unix library]

```ocaml
val create_process :
  string -> string array -> file_descr -> file_descr -> file_descr -> int
val create_process_env :
  string -> string array -> string array -> file_descr -> file_descr ->
    file_descr -> int
```

Verified: "creates a new process that executes the program in file `prog`, with
arguments `args` … The pid of the new process is returned immediately … The
standard input and outputs of the new process are connected to the descriptors
`stdin`, `stdout` and `stderr`. Passing e.g. `Unix.stdout` for `stdout` prevents
the redirection … The executable file `prog` is searched in the path."
(`create_process_env` adds the environment array.) This is the
argument-array, injection-free workhorse: internally fork + dup2 + exec (documented
as "connected to the descriptors").

### 5.7 The `open_process` family — channels over child pipes [Unix library]

Shell-string forms (parsed by `/bin/sh`, injection-prone):

```ocaml
val open_process_in   : string -> in_channel
val open_process_out  : string -> out_channel
val open_process      : string -> in_channel * out_channel
val open_process_full : string -> string array -> in_channel * out_channel * in_channel
(* the SECOND argument of open_process_full is the ENVIRONMENT (verified) *)
```

Argument-array forms (since 4.08; "more robust and more efficient alternative" —
verified doc):

```ocaml
val open_process_args      : string -> string array -> in_channel * out_channel
val open_process_args_in   : string -> string array -> in_channel
val open_process_args_out  : string -> string array -> out_channel
val open_process_args_full : string -> string array -> string array ->
                               in_channel * out_channel * in_channel
```

Pids (4.08+): `process_in_pid : in_channel -> int`, `process_out_pid : out_channel -> int`,
`process_pid : in_channel * out_channel -> int`, `process_full_pid :
in_channel * out_channel * in_channel -> int`.

Reaping — each close waits and returns the child's status:

```ocaml
val close_process_in   : in_channel -> process_status
val close_process_out  : out_channel -> process_status
val close_process      : in_channel * out_channel -> process_status
val close_process_full : in_channel * out_channel * in_channel -> process_status
```

Documented buffering warning (`open_process_out`): "Warning: writes on output
channels are buffered, hence be careful to call `Stdlib.flush` at the right times
to ensure correct synchronization."

**The documented deadlock** (worked example): with `open_process_full`, the child
writes more stdout than the OS pipe buffer holds while the parent is still writing
its stdin; both block forever, and `close_process_full` — which "wait[s] for the
associated command to terminate" — never returns:

```ocaml
(* DEADLOCK: 'yes' floods stdout; our stdin write blocks once the pipe fills;
   nothing drains the child's stdout, so the child blocks too. *)
let ic, oc, _ec = Unix.open_process_full "yes hello" [||] in
output_string oc "ignored\n"; flush oc;
ignore (close_process_full (ic, oc, _ec))
(* correct discipline: read ic to EOF (or select-pump all three) BEFORE
   writing stdin; then close_process_full reaps. *)
```

### 5.8 `open_connection` / `shutdown_connection` (brief) [Unix library]

```ocaml
val open_connection : sockaddr -> in_channel * out_channel
val shutdown_connection : in_channel -> unit
```

Verified: buffered channels over a connected socket; "The two channels … share a
descriptor to a socket. Therefore, when the connection is over, you should call
`Stdlib.close_out` on the output channel, which will also close [the input
channel]" — `shutdown_connection` only transmits the EOF condition to the server
and "does not close the socket and the channels used by the connection."

### 5.9 Environment [Unix library]

```ocaml
val environment : unit -> string array     (* "variable=value" strings; empty if special privileges *)
val unsafe_environment : unit -> string array   (* since 4.06 *)
val getenv : string -> string              (* identical to Sys.getenv; Not_found if unbound *)
val unsafe_getenv : string -> string       (* ignores the privileged-process guard *)
val putenv : string -> string -> unit      (* set name=value in the process environment *)
val unsetenv : string -> unit              (* since 5.5 *)
```

All verified. Ownership note (documented shape): these manipulate the process
environment as arrays of strings; `putenv` sets the variable for this process and
its future children (`create_process_env`/`execve` pass explicit environments
instead). There is no documented lifetime hazard in the OCaml API; the [POSIX]
`setenv`-vs-`putenv` ownership distinction lives below the binding.

### 5.10 Pipes, fds, and close-on-exec [Unix library]

```ocaml
val pipe : ?cloexec:bool -> unit -> file_descr * file_descr
(* first component: read end; second: write end *)
val dup  : ?cloexec:bool -> file_descr -> file_descr
val dup2 : ?cloexec:bool -> file_descr -> file_descr -> unit  (* closes dst first *)
val set_close_on_exec   : file_descr -> unit
val clear_close_on_exec : file_descr -> unit
val read  : file_descr -> bytes -> int -> int -> int
val write : file_descr -> bytes -> int -> int -> int   (* LOOPS until all written *)
val single_write : file_descr -> bytes -> int -> int -> int
val close : file_descr -> unit
val stdin / stdout / stderr : file_descr
val in_channel_of_descr : file_descr -> in_channel
val out_channel_of_descr : file_descr -> out_channel
val descr_of_in_channel : in_channel -> file_descr
val descr_of_out_channel : out_channel -> file_descr
```

All verified. Close-on-exec default: descriptors are **not** close-on-exec unless
you pass `?cloexec:true` (4.14-era optional arguments, present in 5.5.1) or call
`set_close_on_exec` — whose doc is emphatic: "A descriptor with the close-on-exec
flag is automatically closed when the current process starts another program with
one of the `exec`, `create_process` and `open_process` functions. … it is highly
recommended to set all file descriptors 'close-on-exec', except in the very few
cases where a file descriptor actually needs to be inherited" (verified).
`write` loops to completion; `single_write` writes at most once (verified).

Select-based timeout pattern for child output (documented signature):

```ocaml
val select :
  file_descr list -> file_descr list -> file_descr list -> float ->
    file_descr list * file_descr list * file_descr list
(* float timeout in seconds; negative = unbounded wait *)
```

```ocaml
(* read a child's stdout with a 2 s idle timeout *)
let rec drain ic fd acc =
  let r, _, _ = Unix.select [fd] [] [] 2.0 in
  if r = [] then acc                               (* timeout: idle child *)
  else match input_char ic with                    (* buffered channel over fd *)
    | ch -> drain ic fd (ch :: acc)
    | exception End_of_file -> acc
```

`Unix.sleep : int -> unit`, `Unix.sleepf : float -> unit` (4.03+) for whole-process
pauses (§4.3).

### 5.11 Timeouts, cancellation, zombies, error paths

- **No built-in child timeout or cancellation** exists in the documented 5.5.1
  surface (no `wait4`/`waitid`, no wait timeout — §5.3). Patterns: `Unix.alarm` +
  a `Signal_handle` for `Sys.sigalrm` that `Unix.kill`s the child, then
  `waitpid`; or `waitpid [WNOHANG]` polling; or `select` pumping as above. All
  composition, no API — the absence is verified.
- **Zombies**: every `fork`ed child or `open_process*` shell needs exactly one
  `wait`/`waitpid`/`close_process*`. Reaping discipline: a `Signal_handle Sys.sigchld`
  handler that `waitpid [WNOHANG] (-1)`s in a loop reaps asynchronously — the
  handler runs at safe points (§4.1), so the loop must tolerate `Unix_error
  (ECHILD, …)` races. `waitpid` on an already-reaped pid raises `Unix_error (ECHILD,…)`
  (POSIX layer, below the binding).
- **Error model** (verified): "all the functions of this module (except
  `error_message` and `handle_unix_error`) are liable to raise the `Unix_error`
  exception whenever the underlying system call signals an error" —
  `exception Unix_error of error * string * string` (errno code, function name,
  argument); the `error` variant is huge and POSIX-shaped: `E2BIG` ("Argument
  list too long" — the documented code you get when the exec argument limit is
  hit), `EACCES`, `EAGAIN`, `EBADF`, `ECHILD`, `EINTR` ("Function interrupted by
  signal"), `ENOENT`, … `Unix.error_message : error -> string` renders them;
  `Unix.handle_unix_error : ('a -> 'b) -> 'a -> 'b` "prints a message describing
  the error and exits with code 2". There is **no Python-PEP-475-style
  auto-retry**: `EINTR` surfaces to you (explicit retry pattern, LG chapter).
  Cleanup on error paths is yours: `Fun.protect ~finally` around anything holding
  fds/channels (§6.6).

---

## 6. Concurrency and Resource Semantics

### 6.1 Domains [language]/[OCaml runtime]

```ocaml
val Domain.spawn : (unit -> 'a) -> 'a t          (* @raise Failure on insufficient resources *)
val Domain.join : 'a t -> 'a                     (* re-raises the domain's uncaught exception *)
val Domain.at_exit : (unit -> unit) -> unit      (* domain-local, LIFO *)
val Domain.before_first_spawn : (unit -> unit) -> unit  (* FIFO; Invalid_argument after first spawn *)
val Domain.is_main_domain : unit -> bool
val Domain.count : unit -> int                   (* since 5.5 *)
val Domain.recommended_domain_count : unit -> int
```

All verified. `join` "If `d` raises an uncaught exception, then that is re-raised
by `join d`. If the domain has created any systhreads …, then it tries to join
those systhreads … before returning." **Domains cannot be killed** (§3.7): the
only cancellation shapes are cooperative (an effect handler, §6.3) or
process-level.

### 6.2 Effects (brief) [language]

`Effect.perform : 'a t -> 'a` with deep/shallow handlers (`Effect.Deep.try_with :
('b -> 'a) -> 'b -> 'a effect_handler -> 'a`; exceptions `Effect.Unhandled of 'a t`,
`Effect.Continuation_already_resumed` — all verified, `stdlib/effect.mli`). For
process management the relevant use is structured cancellation: perform a
`Cancel` effect inside a worker, let a supervisor's handler decide between
shutdown and continuation — the continuation-based design avoids the "kill"
problem of §3.7 at the cost of writing the protocol yourself; performance of
effect handlers (allocation per continuation capture) is implementation
characterization, not documented behavior, and is not asserted here.

### 6.3 The `Thread` module in 5.x [Unix library]

```ocaml
type t
val create : ('a -> 'b) -> 'a -> t
val self : unit -> t
val id : t -> int
val set_current_thread_name : string -> unit     (* since 5.4 *)
exception Exit
val exit : unit -> unit                          (* @deprecated "Use 'raise Thread.Exit' instead." *)
val delay : float -> unit
val join : t -> unit
val yield : unit -> unit
val sigmask : Unix.sigprocmask_command -> int list -> int list
val wait_signal : int list -> int
val default_uncaught_exception_handler : exn -> unit
val set_uncaught_exception_handler : (exn -> unit) -> unit
```

All verified against `otherlibs/systhreads/thread.mli` (5.5.1). Documented
termination model: a thread ends when its function "returns, either normally or by
raising the `Thread.Exit` exception or by raising any other uncaught exception.
In the last case, the uncaught exception is **printed on standard error, but not
propagated back to the parent thread**." `Thread.exit` (deprecated) now "raise[s]
the `Thread.Exit` exception", and per its `@before 5.0` note the old
implementation "was not based on raising an exception, and not running finalizers
and catch-all handlers" — so 5.x `raise Thread.Exit` **runs `Fun.protect`
finalizers and catch-all handlers** (verified doc). **`Thread.kill` is
verified-absent** in 5.5.1 (§3.7).

Deprecated leftovers, kept for compatibility, all documented "Use Unix.* instead"
(verified): `wait_timed_read`/`wait_timed_write`/`select`/`wait_pid` (§6.7 for the
fork relevance).

### 6.4 `Mutex` / `Condition` (now Stdlib) [Stdlib]

```ocaml
(* stdlib/mutex.mli, 5.5.1 *)
val Mutex.create : unit -> t
val Mutex.lock : t -> unit
val Mutex.try_lock : t -> bool
val Mutex.unlock : t -> unit
val Mutex.protect : t -> (unit -> 'a) -> 'a
(* stdlib/condition.mli, 5.5.1 *)
val Condition.create : unit -> t
val Condition.wait : t -> Mutex.t -> unit
val Condition.signal : t -> unit
val Condition.broadcast : t -> unit
```

All verified (`Semaphore` and `Event` likewise exist — `stdlib/semaphore.mli`,
`otherlibs/systhreads/event.mli`). Classic races in this chapter's domain:

- **at_exit + threads**: the LIFO chain runs wherever `exit` was called (§3.2);
  handlers touching shared state guarded by a `Mutex` must be able to take that
  mutex from the exiting thread — a worker holding the lock while the main thread
  calls `exit` deadlocks the hook. Documented-adjacent discipline: `at_exit`
  handlers should not block (nothing in the docs unblocks them).
- **Signal handler + shared state**: handlers run at safe points *inside* whatever
  thread takes the delivery (§4.4); share via `Atomic` or masks, not plain
  mutable fields.

### 6.5 `Unix.fork` × threads — the POSIX hazard [POSIX]

POSIX guarantees only the calling thread exists in the child; every other
thread's locks, conditions and runtime state vanish mid-flight. OCaml's
documentation echoes it as the verified "if any thread from the `Thread` module
has been spawned, then the child process might be in a corrupted state" (§5.1) —
and the POSIX-shaped rule for OCaml programs is: fork only before any
`Thread.create`/`Domain.spawn`, and in the child run only `exec*`/`_exit`-style
code (§5.2, §3.8). A mutex locked at fork time in a threaded program is the
classic child-side deadlock the docs' "corrupted state" covers without spelling
out (marked as implied, not quoted).

### 6.6 fd and channel ownership; buffering; leaks [Stdlib]/[Unix library]

- `Unix.file_descr` is abstract (verified); `in_channel`/`out_channel` are
  buffered Stdlib channels that *wrap* fds (`in_channel_of_descr`/`out_channel_of_descr`,
  §5.10). Closing rules: `close_out` flushes then closes; closing both a channel
  and its underlying fd separately double-closes — pick one owner. The runtime
  warns about channels finalized unclosed when `Sys.enable_runtime_warnings true`
  is set (verified, §2.2) — the documented leak detector for this exact class.
- Mixing layers (`Unix.read` on the fd of a buffered `in_channel`) is the classic
  desync: the channel's buffer holds bytes the raw read will never see. The
  documented warning is the `open_process_out` buffering note (§5.7) and the
  `_exit` duplicate-flush note (§3.8); both generalize.
- `close_process*` closes the pipes and reaps; forgetting it leaks a zombie (§5.11);
  forgetting `flush` before `close_process_out` truncates the child's input.
- `exit`'s `flush_all` "ignore[s] errors" (§2.1): a failing disk does not change
  your exit status; data loss on abnormal paths is structural (§3.3).

### 6.7 GC × fork; deadlocks; finalisers [OCaml runtime]

- **GC × fork**: the child inherits the single-domain heaps (§5.1); `OCAMLRUNPARAM=c`
  (`cleanup_on_exit`, §2.4) is the documented mode where the runtime actually runs
  `caml_shutdown` at exit — a leak-checker-friendly exit. Forked children that
  `exec` immediately never collect anything, which is fine.
- **Deadlocks** (documented consequences, worked in §5.7): full-pipe with
  `open_process_full`; `close_process*` waiting on a child blocked on our full
  pipe; `Condition.wait` without `Mutex.unlock` under `exit` (§6.4).
- **Finalisers are not process cleanup** (§1.9): timing is GC-determined and
  may never run; use `Fun.protect ~finally` (verified signature:
  `val protect : finally:(unit -> unit) -> (unit -> 'a) -> 'a`) for
  exception-safe scoping and `at_exit`/`Domain.at_exit` for process/domain exit.
- **`Thread.wait_pid`** (deprecated) exists precisely because `Unix.waitpid` in a
  threaded program blocks the *process* in pre-5.x threading; with the 5.x
  effect-based scheduler the documented advice is simply "Use `Unix.waitpid`
  instead" (verified).

---

## Related Topics

- [OCaml: Exit Status, Signals, and Process Lifecycle](../../linux/process-exit-signal/languages/ocaml.md)
  — the exit/signal-scoped chapter (IDs `LG-OC-*`); §3/§4 here generalize it.
- [Process & Runtime Semantics by Language (hub)](./index.md) — schema of this
  part, per-language rollups.
- [C: ISO C, POSIX, and Linux process APIs](./c.md) — the `fork`/`execve`/`waitpid`/
  `sigaction` substrate every OCaml binding wraps.
- [Python](./python.md) — PEP 475 auto-retry vs OCaml's explicit `EINTR`; `atexit`
  LIFO mirror.
- [Go](./go.md) — `os/exec` pipe discipline vs `open_process_full` deadlock.
- [Node.js](./nodejs.md) — shell-string injection lesson (`child_process.exec` vs
  `Sys.command`).
- [Java](./java.md) — shutdown hooks (unspecified order) vs `at_exit` (LIFO).

## Coverage ledger

The per-entry ledger for this chapter is [ledger-ocaml.md](./ledger-ocaml.md):
**80 rows** (`PL-OC-001` … `PL-OC-080`), section map §1→001–013, §2→014–028,
§3→029–038, §4→039–049, §5→050–070, §6→071–080; 77 documented, 3 source-limited
(PL-OC-005 refutation-case doc anchor, PL-OC-012 tail-call normative wording,
PL-OC-035 native SIGSEGV→`Stack_overflow` conversion), 0 remaining. Verified-absent
APIs are documented rows whose signature column records the absence
(`Sys.exit`, `Sys.setenv`/`unsetenv`, `Sys.break_exception`, `Sys.error_message`,
`Unix.sys_signal`, `Unix.sigaction`, `Unix.wait4`/`waitid`, `execl` variants,
`Thread.kill`, `Domain.kill`, `signalfd`/`pidfd`).

## References

1. *Release index*: OCaml 5.5.1 (released 2026-09-05), ocaml.org/releases/latest
   (retrieved 2026-10-13).
2. *Stdlib*: OCaml 5.5.1 `stdlib/stdlib.mli` + `stdlib/stdlib.ml`
   (github.com/ocaml/ocaml, tag 5.5.1) and ocaml.org/manual/5.5/api/Stdlib.html
   (retrieved 2026-10-13).
3. *Sys*: OCaml 5.5.1 `stdlib/sys.mli`; ocaml.org/manual/5.5/api/Sys.html
   (retrieved 2026-10-13).
4. *Printexc*: OCaml 5.5.1 `stdlib/printexc.mli` + `stdlib/printexc.ml` +
   `runtime/printexc.c` (`caml_fatal_uncaught_exception`, `exit(2)`)
   (retrieved 2026-10-13).
5. *Unix library*: OCaml 5.5.1 `otherlibs/unix/unix.mli`;
   ocaml.org/manual/5.5/api/Unix.html; exec stubs `otherlibs/unix/execv.c`,
   `execve.c`, `execvp.c` (exec-failure → `caml_uerror`) (retrieved 2026-10-13).
6. *Runtime startup/exit*: OCaml 5.5.1 `runtime/startup_nat.c`,
   `startup_byt.c`, `runtime/sys.c` (`caml_do_exit`), `runtime/fail_nat.c`,
   `runtime/signals_nat.c` (retrieved 2026-10-13).
7. *Threads*: OCaml 5.5.1 `otherlibs/systhreads/thread.mli`, `event.mli`,
   `st_stubs.c` dir listing; `stdlib/mutex.mli`, `stdlib/condition.mli`,
   `stdlib/semaphore.mli` (retrieved 2026-10-13).
8. *Domain & GC*: OCaml 5.5.1 `stdlib/domain.mli`, `stdlib/gc.mli` (retrieved
   2026-10-13).
9. *Effect & Fun & Filename*: OCaml 5.5.1 `stdlib/effect.mli`, `stdlib/fun.mli`,
   `stdlib/filename.mli` (`quote_command`) (retrieved 2026-10-13).
10. *Language manual*: ocaml.org/manual/5.5/expr.html (evaluation-order wording),
    patterns.html, comp.html (unit initialization order) (retrieved 2026-10-13).
11. *Runtime manual*: ocaml.org/manual/5.5/runtime.html (`ocamlrun -b`,
    `OCAMLRUNPARAM` b/c/l/GC params) (retrieved 2026-10-13).
12. *C interface manual*: ocaml.org/manual/5.5/intfc.html (safe points,
    `caml_process_pending_actions`, SIGSEGV/SIGTRAP/SIGFPE handlers) (retrieved
    2026-10-13).
