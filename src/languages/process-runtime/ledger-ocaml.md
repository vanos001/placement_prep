# Coverage Ledger — OCaml (Section G)

**Scope:** OCaml 5.5.1 (current stable, released 2026-09-05; verified on
ocaml.org/releases/latest), Linux platform, POSIX deltas labeled. Chapter:
[./ocaml.md](./ocaml.md). Section map: §1 syntax/semantics → 001–013; §2
stdlib/runtime inventory → 014–028; §3 process creation/termination → 029–038; §4
signals/OS interaction → 039–049; §5 subprocess management → 050–070; §6
concurrency/resources → 071–080.

**Sources & retrieval dates (all 2026-10-13):** github.com/ocaml/ocaml tag `5.5.1`
— `stdlib/stdlib.mli`, `stdlib/stdlib.ml`, `stdlib/sys.mli`, `stdlib/printexc.mli`,
`stdlib/printexc.ml`, `stdlib/domain.mli`, `stdlib/gc.mli`, `stdlib/effect.mli`,
`stdlib/fun.mli`, `stdlib/filename.mli`, `stdlib/mutex.mli`,
`stdlib/condition.mli`, `stdlib/semaphore.mli`, `otherlibs/unix/unix.mli`,
`otherlibs/unix/execv.c`, `execve.c`, `execvp.c`,
`otherlibs/systhreads/thread.mli`, `runtime/printexc.c`, `startup_nat.c`,
`startup_byt.c`, `sys.c`, `fail_nat.c`, `signals_nat.c`; ocaml.org/manual/5.5/
— api/Stdlib.html, api/Sys.html, api/Unix.html, api/Printexc.html, expr.html,
patterns.html, comp.html, runtime.html, intfc.html; ocaml.org/releases/latest.

**Status definitions:** `documented` = behavior + signature verified against the
cited official source and explained in the chapter; `source-limited` = claim is
true-but-citable-only-in-part (the exact normative anchor was not found in the
fetched official pages); verified-absent APIs are `documented` rows whose
signature column records the verified absence (challenge rule: never invent).

**Rollup: Inventoried: 80 / Documented: 77 / Remaining: 0 / Source-limited: 3**

| ID | Language/API or behavior | Canonical signature | Documentation path | Authoritative reference | Version/platform scope | Status |
|---|---|---|---|---|---|---|
| PL-OC-001 | let-bindings, scoping, compilation-unit initialization order | — | ./ocaml.md §1.1 | manual/5.5/comp.html ("initialized in that order at run-time") | OCaml 5.5.1 [language] | documented |
| PL-OC-002 | functions: currying, labeled/optional args, application operators | `external ( \|> ) : 'a -> ('a -> 'b) -> 'b = "%revapply"`; `external ( @@ ) : ('a -> 'b) -> 'a -> 'b = "%apply"`; `external ignore : 'a -> unit = "%ignore"` | ./ocaml.md §1.2 | stdlib/stdlib.mli (5.5.1) | OCaml 5.5.1 [language] | documented |
| PL-OC-003 | evaluation order of application/tuples/records | — ("The order … is not specified" ×3) | ./ocaml.md §1.3 | manual/5.5/expr.html (retrieved 2026-10-13) | OCaml 5.5.1 [language] | documented |
| PL-OC-004 | variants, pattern matching, exhaustiveness checking | — | ./ocaml.md §1.4 | manual/5.5/expr.html + patterns.html; `exception Match_failure of (string * int * int)` in stdlib.mli | OCaml 5.5.1 [language] | documented |
| PL-OC-005 | refutation cases (`pattern -> .`) | — | ./ocaml.md §1.4 | no "refut*" wording found in manual/5.5 expr/patterns/extn pages | OCaml 5.5.1 [language] | **source-limited** |
| PL-OC-006 | exceptions: extensible `exn`, unchecked, no throws clauses | `val failwith : string -> 'a`; `val invalid_arg : string -> 'a`; `exception Exit` | ./ocaml.md §1.5 | stdlib/stdlib.mli (5.5.1) | OCaml 5.5.1 [language] | documented |
| PL-OC-007 | raise/try-with/match-exception semantics; `exit` does not raise `Exit` | `exception Exit` ("not raised by any library function") | ./ocaml.md §1.5, §3.2 | stdlib.mli + stdlib/stdlib.ml 5.5.1 | OCaml 5.5.1 [language] | documented |
| PL-OC-008 | backtraces: `ocamlrun -b`, `OCAMLRUNPARAM=b/b=0/b=1/b=2`, `-g` linking | — | ./ocaml.md §1.6 | manual/5.5/runtime.html (verbatim options) | OCaml 5.5.1 [OCaml runtime] | documented |
| PL-OC-009 | modules/functors organize the libraries; `unix` is a separate library | — | ./ocaml.md §1.7 | manual/5.5/comp.html; distribution layout (stdlib vs otherlibs) | OCaml 5.5.1 [language] | documented |
| PL-OC-010 | mutable state: ref, mutable fields, Atomic; unsynchronized-access alerts | `val enable_runtime_warnings : bool -> unit` (alert-annotated) | ./ocaml.md §1.8 | stdlib/sys.mli 5.5.1 | OCaml 5.5.1 [language] | documented |
| PL-OC-011 | GC heaps; finaliser timing "between … and … or never"; full_major | `val finalise : ('a -> unit) -> 'a -> unit`; `val finalise_last : (unit -> unit) -> 'a -> unit`; `external full_major : unit -> unit = "caml_gc_full_major"` | ./ocaml.md §1.9 | stdlib/gc.mli (5.5.1, verbatim timing doc) | OCaml 5.5.1 [OCaml runtime] | documented |
| PL-OC-012 | tail calls; runtime-owned stack (`OCAMLRUNPARAM l=`) | — | ./ocaml.md §1.10 | manual/5.5/runtime.html (stack wording); no normative tail-call wording in expr.html | OCaml 5.5.1 [language]+[runtime] | **source-limited** |
| PL-OC-013 | version deltas 4.14→5.5 (multicore, 5.3 poll_actions, 5.4 signal type/sigwait, 5.5 unsetenv) | `external poll_actions : unit -> unit = "%poll"`; `type signal = int`; `val unsetenv : string -> unit` | ./ocaml.md §1.11 | stdlib/sys.mli, otherlibs/unix/unix.mli (@since annotations) | OCaml 5.3–5.5 | documented |
| PL-OC-014 | `Stdlib.exit` flushes + Domain.at_exit + at_exit + sys_exit; no optional args | `val exit : int -> 'a` | ./ocaml.md §3.2 | stdlib.mli + stdlib/stdlib.ml 5.5.1 (`let exit retcode = do_at_exit (); sys_exit retcode`) | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-015 | `Exit` exception has no exit-status meaning | `exception Exit` | ./ocaml.md §1.5 | stdlib.mli 5.5.1 ("not raised by any library function") | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-016 | `at_exit` LIFO; trigger list (exit/normal/uncaught/caml_shutdown) | `val at_exit : (unit -> unit) -> unit` | ./ocaml.md §3.3 | stdlib.mli 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-017 | `do_at_exit` internal; domain-local hooks then at_exit chain | `val do_at_exit : unit -> unit` ("for system use only") | ./ocaml.md §3.2 | stdlib.mli + stdlib/stdlib.ml 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-018 | failwith/invalid_arg/Failure/Invalid_argument | `val failwith : string -> 'a`; `val invalid_arg : string -> 'a` | ./ocaml.md §1.5 | stdlib.mli 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-019 | flush_all/prerr_endline; flush errors ignored at exit | `val flush_all : unit -> unit`; `val prerr_endline : string -> unit` | ./ocaml.md §2.1 | stdlib.mli 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-020 | Sys.argv / executable_name / runtime_executable (5.5) | `external argv : string array = "%sys_argv"`; `val runtime_executable : string` | ./ocaml.md §2.2 | stdlib/sys.mli 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-021 | Sys.getenv/getenv_opt; Sys.setenv/unsetenv verified-absent | `external getenv : string -> string = "caml_sys_getenv"`; `val getenv_opt : string -> string option` | ./ocaml.md §2.2 | stdlib/sys.mli 5.5.1 (no setenv/unsetenv bindings) | OCaml 5.5.1 [Stdlib] | documented (v-a recorded) |
| PL-OC-022 | Sys.command shell semantics + Filename.quote_command; no 127 sentence in 5.5 doc | `external command : string -> int = "caml_sys_system_command"`; `val quote_command : string -> ?stdin:string -> ?stdout:string -> ?stderr:string -> string list -> string` | ./ocaml.md §5.7 | stdlib/sys.mli + stdlib/filename.mli 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-023 | Sys.file_exists/os_type/word_size/backend_type/ocaml_version | `val backend_type : backend_type`; `val ocaml_version : string` | ./ocaml.md §2.2 | stdlib/sys.mli 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-024 | Sys.signal/set_signal/signal_behavior; returns previous behavior; `type signal = int` (5.4) | `external signal : signal -> signal_behavior -> signal_behavior = "caml_install_signal_handler"`; `val set_signal : signal -> signal_behavior -> unit` | ./ocaml.md §4.2 | stdlib/sys.mli 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-025 | Sys.catch_break / Break; multithreaded routing caveat | `val catch_break : bool -> unit`; `exception Break` | ./ocaml.md §4.2 | stdlib/sys.mli 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-026 | Sys POSIX signal constants + signal_of_int/to_int/to_string (5.4) | `val sigchld : signal`; `val signal_to_int : signal -> int`; `val sigwinch : signal` (5.4) | ./ocaml.md §2.2 | stdlib/sys.mli 5.5.1 | OCaml 5.4–5.5.1 | documented |
| PL-OC-027 | Printexc surface incl. uncaught-exception handler replacement | `val set_uncaught_exception_handler : (exn -> raw_backtrace -> unit) -> unit`; `val default_uncaught_exception_handler : exn -> raw_backtrace -> unit` | ./ocaml.md §2.3, §3.4 | stdlib/printexc.mli + printexc.ml 5.5.1 | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-028 | OCAMLRUNPARAM (b, c=cleanup_on_exit, l, GC params ↔ Gc.control) | — | ./ocaml.md §2.4 | manual/5.5/runtime.html; gc.mli control record | OCaml 5.5.1 [OCaml runtime] | documented |
| PL-OC-029 | startup: caml_main/caml_startup, unit initializers, fatal on init exception | `void caml_main(char_os **argv)` | ./ocaml.md §3.1 | runtime/startup_nat.c + startup_byt.c (5.5.1); manual/5.5/comp.html | OCaml 5.5.1 [OCaml runtime] | documented |
| PL-OC-030 | exit sequence: flush_all → Domain.at_exit → at_exit → caml_sys_exit → C exit | `val exit : int -> 'a` | ./ocaml.md §3.2 | stdlib.ml + runtime/sys.c `caml_do_exit` (verified tail: `exit(retcode)`) | OCaml 5.5.1 [Stdlib]+[runtime] | documented |
| PL-OC-031 | implicit `exit 0` / implicit `exit 2` | — | ./ocaml.md §3.2 | stdlib.mli exit doc (verbatim) | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-032 | at_exit triggers; NOT on signal death or Unix._exit | `val at_exit : (unit -> unit) -> unit` | ./ocaml.md §3.3 | stdlib.mli trigger list; unix.mli `_exit` doc | OCaml 5.5.1 [Stdlib] | documented |
| PL-OC-033 | exceptions in at_exit handlers: raise in exit path; swallowed in uncaught path | — | ./ocaml.md §3.3–3.4 | stdlib/printexc.ml 5.5.1 (`(try Stdlib.do_at_exit () with _ -> ())`) | OCaml 5.5.1 [OCaml runtime] | documented |
| PL-OC-034 | uncaught exception → "Fatal error: exception %s" → exit 2 (abort variant behind caml_abort_on_uncaught_exn) | — | ./ocaml.md §3.4 | runtime/printexc.c `caml_fatal_uncaught_exception` + printexc.ml format strings | OCaml 5.5.1 [OCaml runtime] | documented |
| PL-OC-035 | stack overflow: catchable Stack_overflow; runtime-owned stack; native SIGSEGV conversion path | `caml_exn_Stack_overflow` (runtime exception table) | ./ocaml.md §3.5 | runtime/fail_nat.c; manual/5.5/runtime.html (l=); conversion handler absent from 5.5.1 signals_nat.c | OCaml 5.5.1 [OCaml runtime] | **source-limited** |
| PL-OC-036 | exit-status truncation to 8 bits via C exit; handle_unix_error exits 2 | `val handle_unix_error : ('a -> 'b) -> 'a -> 'b` | ./ocaml.md §3.6 | runtime/sys.c; otherlibs/unix/unix.mli ("exits with code 2") | OCaml 5.5.1 + POSIX | documented |
| PL-OC-037 | process vs domain vs thread vs child; no Domain.kill; no Thread.kill | `val Domain.join : 'a t -> 'a` (joins systhreads) | ./ocaml.md §3.7 | stdlib/domain.mli; otherlibs/systhreads/thread.mli (both kill-free, verified) | OCaml 5.5.1 [language] | documented (v-a recorded) |
| PL-OC-038 | `Unix._exit` — no finalization, fork-safe child exit | `val _exit : int -> 'a` | ./ocaml.md §3.8 | otherlibs/unix/unix.mli (verbatim) | OCaml 5.5.1 [Unix library] | documented |
| PL-OC-039 | signal delivery deferred to safe points; `Sys.poll_actions` (5.3) pump | `external poll_actions : unit -> unit = "%poll"` | ./ocaml.md §4.1 | manual/5.5/intfc.html (caml_process_pending_actions quote); stdlib/sys.mli | OCaml 5.3–5.5.1 [OCaml runtime] | documented |
| PL-OC-040 | handler exceptions propagate into interrupted code (async exceptions) | — | ./ocaml.md §4.1 | manual/5.5/intfc.html ("can raise asynchronous exceptions") | OCaml 5.5.1 [OCaml runtime] | documented |
| PL-OC-041 | native runtime installs SIGSEGV/SIGTRAP/SIGFPE handlers; C program must not | — | ./ocaml.md §4.1, §4.6 | manual/5.5/intfc.html (verbatim) | OCaml 5.5.1 native [OCaml runtime] | documented |
| PL-OC-042 | Unix.sigprocmask + sigprocmask_command; redirect semantics with threads | `val sigprocmask : sigprocmask_command -> Sys.signal list -> Sys.signal list` | ./ocaml.md §4.3 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 (Sys.signal-typed since 5.4) | documented |
| PL-OC-043 | sigpending / sigsuspend; Windows Invalid_argument | `val sigpending : unit -> Sys.signal list`; `val sigsuspend : Sys.signal list -> unit` | ./ocaml.md §4.3 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1; POSIX; Windows delta | documented |
| PL-OC-044 | Unix.sigwait (since 5.4); handlers not invoked for sigwait-ed signals | `val sigwait : Sys.signal list -> Sys.signal` | ./ocaml.md §4.3 | otherlibs/unix/unix.mli (@since 5.4) | OCaml 5.4–5.5.1 | documented |
| PL-OC-045 | pause / alarm / sleep / sleepf | `val pause : unit -> unit`; `val alarm : int -> int`; `val sleep : int -> unit`; `val sleepf : float -> unit` | ./ocaml.md §4.3 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 (sleepf 4.03+) | documented |
| PL-OC-046 | Thread.sigmask / wait_signal; POSIX thread signal model (external → one unblocked thread; masks inherited) | `val sigmask : Unix.sigprocmask_command -> int list -> int list`; `val wait_signal : int list -> int` | ./ocaml.md §4.4 | otherlibs/systhreads/thread.mli 5.5.1 (model paragraph verbatim) | OCaml 5.5.1 [POSIX threads] | documented |
| PL-OC-047 | Ctrl-C routing: catch_break + Break + sigmask discipline; exit 130 convention | `val catch_break : bool -> unit`; `exception Break` | ./ocaml.md §4.2 | stdlib/sys.mli (verbatim thread caveat) | OCaml 5.5.1 | documented |
| PL-OC-048 | verified-absent integration surfaces: signalfd, pidfd, Unix.sigaction, Unix.sys_signal, wait4/waitid | — (none exist in unix.mli/sys.mli 5.5.1) | ./ocaml.md §4.5 | otherlibs/unix/unix.mli + stdlib/sys.mli full-surface checks | OCaml 5.5.1 | documented (v-a recorded) |
| PL-OC-049 | FFI: caml_process_pending_actions contract for C stubs; GC/signal shared safe-point machinery | — | ./ocaml.md §4.1, §4.6 | manual/5.5/intfc.html; runtime/signals_nat.c | OCaml 5.5.1 [OCaml runtime]+[C API] | documented |
| PL-OC-050 | Unix.fork: multicore rule (Failure after Domain.spawn), thread corruption hazard, Windows Invalid_argument | `val fork : unit -> int` | ./ocaml.md §5.1 | otherlibs/unix/unix.mli (verbatim) | OCaml 5.5.1; multicore since 5.0 | documented |
| PL-OC-051 | execv / execve (environment array) | `val execv : string -> string array -> 'a`; `val execve : string -> string array -> string array -> 'a` | ./ocaml.md §5.2 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 | documented |
| PL-OC-052 | execvp / execvpe (PATH search; no `execl` variants exist) | `val execvp : string -> string array -> 'a`; `val execvpe : string -> string array -> string array -> 'a` | ./ocaml.md §5.2 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 | documented (execl v-a recorded) |
| PL-OC-053 | exec failure raises Unix_error in the child (no `_exit(127)`); execvpe path-search emulation | — | ./ocaml.md §5.2 | otherlibs/unix/execvp.c (`caml_uerror("execvp", path)`), execv.c, execve.c | OCaml 5.5.1 [Unix library] | documented |
| PL-OC-054 | Unix.wait / waitpid + wait_flag (WNOHANG returns pid 0; WUNTRACED) | `val wait : unit -> int * process_status`; `val waitpid : wait_flag list -> int -> int * process_status` | ./ocaml.md §5.3 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1; Windows delta | documented |
| PL-OC-055 | process_status constructors (WEXITED int; WSIGNALED/WSTOPPED of Sys.signal since 5.4) | `type process_status = WEXITED of int \| WSIGNALED of Sys.signal \| WSTOPPED of Sys.signal` | ./ocaml.md §5.3 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 (int-arg form pre-5.4) | documented |
| PL-OC-056 | Unix.kill; Windows 5.5 change to exit code 1067 | `val kill : int -> Sys.signal -> unit` | ./ocaml.md §5.6 | otherlibs/unix/unix.mli 5.5.1 (verbatim) | OCaml 5.5.1 | documented |
| PL-OC-057 | Unix.system: /bin/sh -c, WEXITED 127 on shell-exec failure | `val system : string -> process_status` | ./ocaml.md §5.5 | otherlibs/unix/unix.mli (verbatim) | OCaml 5.5.1; POSIX | documented |
| PL-OC-058 | create_process / create_process_env (arg-array, fd redirects, PATH search) | `val create_process : string -> string array -> file_descr -> file_descr -> file_descr -> int` | ./ocaml.md §5.6 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 | documented |
| PL-OC-059 | open_process_in / open_process_out (shell strings; buffering warning) | `val open_process_in : string -> in_channel`; `val open_process_out : string -> out_channel` | ./ocaml.md §5.7 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 | documented |
| PL-OC-060 | open_process / open_process_full (second arg = environment) | `val open_process : string -> in_channel * out_channel`; `val open_process_full : string -> string array -> in_channel * out_channel * in_channel` | ./ocaml.md §5.7 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 | documented |
| PL-OC-061 | open_process_args family (since 4.08, no shell) | `val open_process_args : string -> string array -> in_channel * out_channel`; `val open_process_args_full : string -> string array -> string array -> in_channel * out_channel * in_channel` | ./ocaml.md §5.7 | otherlibs/unix/unix.mli 5.5.1 | OCaml 4.08–5.5.1 | documented |
| PL-OC-062 | close_process family reaps and returns process_status; process_*_pid (4.08) | `val close_process_full : in_channel * out_channel * in_channel -> process_status`; `val process_full_pid : in_channel * out_channel * in_channel -> int` | ./ocaml.md §5.7 | otherlibs/unix/unix.mli 5.5.1 | OCaml 4.08–5.5.1 | documented |
| PL-OC-063 | open_process_full pipe deadlock (undrained stdout × stdin write) and drain discipline | — | ./ocaml.md §5.7 (worked example) | unix.mli close_process doc ("wait for the associated command to terminate") | OCaml 5.5.1; POSIX pipe buffers | documented |
| PL-OC-064 | open_connection / shutdown_connection (shared socket descriptor; close_out closes both) | `val open_connection : sockaddr -> in_channel * out_channel`; `val shutdown_connection : in_channel -> unit` | ./ocaml.md §5.8 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 | documented |
| PL-OC-065 | environment / unsafe_environment / getenv / unsafe_getenv / putenv / unsetenv (5.5) | `val environment : unit -> string array`; `val putenv : string -> string -> unit`; `val unsetenv : string -> unit` | ./ocaml.md §5.9 | otherlibs/unix/unix.mli 5.5.1 (@since tags) | OCaml 5.5.1 (unsetenv 5.5+) | documented |
| PL-OC-066 | pipe / dup / dup2 with `?cloexec`; stdin/stdout/stderr | `val pipe : ?cloexec:bool -> unit -> file_descr * file_descr`; `val dup2 : ?cloexec:bool -> file_descr -> file_descr -> unit` | ./ocaml.md §5.10 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 (cloexec args) | documented |
| PL-OC-067 | set_close_on_exec / clear_close_on_exec; default is NOT close-on-exec; security note | `val set_close_on_exec : file_descr -> unit` | ./ocaml.md §5.10 | otherlibs/unix/unix.mli (verbatim security paragraph) | OCaml 5.5.1 | documented |
| PL-OC-068 | read/write/close semantics (write loops; single_write once); channel-of-descr bridges | `val read : file_descr -> bytes -> int -> int -> int`; `val write : file_descr -> bytes -> int -> int -> int`; `val in_channel_of_descr : file_descr -> in_channel` | ./ocaml.md §5.10 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 | documented |
| PL-OC-069 | Unix.select (float timeout, negative = unbounded) for child-output timeouts | `val select : file_descr list -> file_descr list -> file_descr list -> float -> file_descr list * file_descr list * file_descr list` | ./ocaml.md §5.10 | otherlibs/unix/unix.mli 5.5.1 | OCaml 5.5.1 | documented |
| PL-OC-070 | Unix_error model: error variant (E2BIG/EACCES/EAGAIN/EBADF/ECHILD/EINTR/ENOENT…), error_message, handle_unix_error; no EINTR auto-retry; zombie reaping + no built-in child timeout/cancellation | `exception Unix_error of error * string * string`; `val error_message : error -> string` | ./ocaml.md §5.11 | otherlibs/unix/unix.mli 5.5.1 (module note verbatim) | OCaml 5.5.1; POSIX | documented |
| PL-OC-071 | Domain.spawn / join (Failure on resources; re-raises; joins systhreads) | `val spawn : (unit -> 'a) -> 'a t`; `val join : 'a t -> 'a` | ./ocaml.md §6.1 | stdlib/domain.mli 5.5.1 | OCaml 5.0–5.5.1 | documented |
| PL-OC-072 | Domain.at_exit (domain-local LIFO) / before_first_spawn (FIFO) / is_main_domain / count (5.5) / recommended_domain_count | `val at_exit : (unit -> unit) -> unit` (Domain); `val count : unit -> int` | ./ocaml.md §6.1 | stdlib/domain.mli 5.5.1 (@since tags) | OCaml 5.5.1 | documented |
| PL-OC-073 | domains cannot be killed (no Domain.kill in 5.5.1); cooperative cancellation | — | ./ocaml.md §3.7, §6.1 | stdlib/domain.mli full-surface check | OCaml 5.5.1 | documented (v-a recorded) |
| PL-OC-074 | Thread surface 5.5: create/self/id/join/yield/delay; uncaught → stderr, not propagated | `val create : ('a -> 'b) -> 'a -> t`; `val join : t -> unit` | ./ocaml.md §6.3 | otherlibs/systhreads/thread.mli 5.5.1 | OCaml 5.x (effects-based) | documented |
| PL-OC-075 | Thread.Exit exception; Thread.exit deprecated (5.x = exception; pre-5.0 different behavior); no Thread.kill | `exception Exit`; `val exit : unit -> unit [@@ocaml.deprecated "Use 'raise Thread.Exit' instead."]` | ./ocaml.md §6.3 | otherlibs/systhreads/thread.mli 5.5.1 (@before 5.0 note) | OCaml 5.0–5.5.1 | documented |
| PL-OC-076 | deprecated Thread fd/wait wrappers (wait_timed_read/write, select, wait_pid — "Use Unix.*") | `val wait_pid : int -> int * Unix.process_status` (deprecated) | ./ocaml.md §6.3, §6.7 | otherlibs/systhreads/thread.mli 5.5.1 | OCaml 5.5.1 | documented |
| PL-OC-077 | Mutex/Condition moved to Stdlib; Semaphore/Event; Mutex.protect (5.2+) | `val Mutex.protect : t -> (unit -> 'a) -> 'a`; `val Condition.wait : t -> Mutex.t -> unit` | ./ocaml.md §6.4 | stdlib/mutex.mli, stdlib/condition.mli, stdlib/semaphore.mli, otherlibs/systhreads/event.mli (5.5.1) | OCaml 5.5.1 | documented |
| PL-OC-078 | at_exit × threads race (hook must not block on held mutex); handler/shared-state discipline | — | ./ocaml.md §6.4 | stdlib.mli at_exit trigger list + sys.mli catch_break caveat (consequences drawn) | OCaml 5.5.1 | documented |
| PL-OC-079 | fork × threads POSIX hazard (only calling thread survives); OCaml doc wording "corrupted state"; GC × fork (single-domain heaps) | `val fork : unit -> int` | ./ocaml.md §6.5, §6.7 | otherlibs/unix/unix.mli + POSIX.1 fork guarantee | OCaml 5.5.1 + POSIX | documented |
| PL-OC-080 | fd/channel ownership: close_out flushes+owns fd, double-close hazard, runtime-warnings leak detector, finalisers not for process cleanup, Fun.protect for error paths | `val protect : finally:(unit -> unit) -> (unit -> 'a) -> 'a` (Fun); `val enable_runtime_warnings : bool -> unit` (Sys) | ./ocaml.md §6.6, §6.7 | stdlib/fun.mli, stdlib/sys.mli, gc.mli finalise timing | OCaml 5.5.1 | documented |

**Verification notes:** 77/80 rows carry a direct official-source anchor fetched on
2026-10-13. The 3 source-limited rows are exact-boundary findings, not gaps:
PL-OC-005 (refutation-case syntax not documented in the fetched 5.5 manual pages),
PL-OC-012 (no normative tail-call wording in the 5.5 language manual; runtime-stack
behavior cited instead), PL-OC-035 (native SIGSEGV→`Stack_overflow` conversion
referenced only by a stale comment in `runtime/fail_nat.c`). Verified-absent APIs
(`Sys.exit`, `Sys.setenv`/`unsetenv`, `Sys.break_exception`, `Sys.error_message`,
`Unix.sys_signal`, `Unix.sigaction`, `Unix.wait4`/`waitid`, `execl` variants,
`Thread.kill`, `Domain.kill`, `signalfd`/`pidfd`) are recorded inside documented
rows per the never-invent rule; the sibling exit/signal chapter
(`../../linux/process-exit-signal/languages/ocaml.md`, IDs `LG-OC-001..006`) holds
the 5.2-era absence history.
