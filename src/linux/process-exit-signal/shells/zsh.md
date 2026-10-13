# zsh: `PIPE_FAIL`, `pipestatus`, and `TRAPNAL` (SH-009 — SH-011)

zsh implements the POSIX exit-status core (XCU 2.8/2.9/2.11) and then layers on two
distinctive mechanisms: the `PIPE_FAIL` option with the lowercase `$pipestatus` array, and
signal handling through `TRAPxxx` *functions* alongside the POSIX-style `trap` builtin. This
page documents both from the official zsh manual (fetched from the zsh project's own
documentation sources, `Doc/Zsh/*.yo`, plus distribution man-page renders), with the
bash/dash contrast drawn where the differences bite. Note on method: unlike
[bash.md](./bash.md) and [dash.md](./dash.md), zsh was not available in the research sandbox,
so the reproductions here quote documented behavior rather than show executed transcripts;
each claim cites its manual section.

## SH-009 — Pipeline status, `PIPE_FAIL`, and `$pipestatus`

Default (per the `PIPE_FAIL` option description — by stating what the *option* changes, the
manual fixes the default):

> By default, when a pipeline exits the exit status recorded by the shell and returned by
> the shell variable `$?` reflects that of the **rightmost element** of a pipeline. If this
> option is set, the exit status instead reflects the status of the rightmost element of the
> pipeline that was non-zero, or zero if all elements exited with zero status.

```zsh
setopt PIPE_FAIL        # zsh's spelling of bash's `set -o pipefail'
```

The per-element array is **`$pipestatus` — lowercase** (zsh manual, Parameters Used by the
Shell):

> `pipestatus <S> <Z>` — An array containing the exit statuses returned by all commands in
> the last pipeline.

Three portability-critical details around that one line:

- **Case**: zsh's `$pipestatus` vs bash's `$PIPESTATUS` — the two arrays are *not*
  interchangeable and a script sourcing bash snippets into zsh (or vice versa) silently
  reads an unset variable (under `setopt ERR_EXIT`/`nounset`-adjacent setups, that can be
  fatal in itself).
- **Indexing**: zsh array elements "are numbered beginning with 1, unless the `KSH_ARRAYS`
  option is set in which case they are numbered from zero" (manual, Array Parameters) — so
  `$pipestatus[1]` is the *first* pipeline element, whereas bash's `$PIPESTATUS[0]` is
  bash's first.
- **Emulation existence**: the `<Z>` flag on `pipestatus` means, per the manual's legend,
  "the parameter does not exist when the shell initializes in **sh or ksh emulation mode**"
  (`emulate sh`, `emulate ksh`, or a `zsh -c` under such emulation). zsh-as-sh drops the very
  array people use it for.

Like bash's, the array belongs to the *last* pipeline only and is clobbered by the next
simple command — capture immediately if you need it later. The pipeline status rules
otherwise follow POSIX 2.9.2 (last command; `!` negation), and there is no dash-style
"pipefail is missing" worry — current zsh documents `PIPE_FAIL` (option index `PIPE_FAIL`,
`NO_PIPE_FAIL`).

## SH-010 — Traps: `TRAPNAL` functions and the `trap` builtin

zsh offers two coexisting syntaxes, documented as equivalent "in most ways" (manual,
Functions / Trap Functions):

```zsh
TRAPINT() {             # function trap: own function environment
  # code                # signal number arrives as $1
}

trap 'echo code' INT    # list trap: runs in the caller's environment
```

The differences the manual itself calls out: function traps "have their own function
environment (line numbers, local variables, etc.) while the [list traps] use the environment
of the command in which they were called" — e.g. `trap 'print $LINENO' DEBUG` prints the
line number of the command after it, while `TRAPDEBUG() { print $LINENO; }` "will always
print the number zero".

### `TRAPNAL` semantics (manual, Trap Functions)

> If defined and non-null, this function will be executed whenever the shell catches a
> signal SIGNAL... The signal number will be passed as the first parameter to the function.
> If a function of this form is defined and null, the shell and processes spawned by it will
> ignore SIGNAL. **The return status from the function is handled specially. If it is zero,
> the signal is assumed to have been handled, and execution continues normally. Otherwise,
> the shell will behave as interrupted except that the return status of the trap is
> retained.**

That last rule has no bash analog: a `TRAPINT()` returning non-zero makes the shell act
*interrupted* with that status — a clean way to translate a caught signal into a `128+N`-style
script exit on your own terms.

### The `trap` builtin (manual, Shell Builtin Commands)

- Signal names: "Each `sig` can be given as a number, or as the name of a signal either with
  or without the string `SIG` in front (e.g. `1`, `HUP`, and `SIGHUP` are all the same
  signal)."
- `trap - sig` resets "to their defaults"; `trap '' sig` ignores.
- `ZERR`: "arg will be executed **after each command with a nonzero exit status**" — `ERR`
  is an alias for `ZERR` "on systems that have no SIGERR signal (this is the usual case)".
- `DEBUG`: executed before each command when `DEBUG_BEFORE_CMD` is set (the default), else
  after; with the default, setting `ERR_EXIT` inside the trap skips the following command,
  and `ZSH_DEBUG_CMD` exposes the command text.
- **`EXIT` inside a function is a function-exit trap**: "If `sig` is `0` or `EXIT` and the
  trap statement is executed inside the body of a function, then the command `arg` is
  executed after the function completes." — In bash the `EXIT` sigspec is shell-exit only;
  in zsh the same statement doubles as the function-return hook (`$?` at the trap's start is
  the function's return status).
- Trap nesting and subshells, verbatim: "`ZERR`, `DEBUG`, and `EXIT` traps are not executed
  inside other traps. **`ZERR` and `DEBUG` traps are kept within subshells, while other traps
  are reset.**" That is the reverse of bash/dash for ZERR/DEBUG: those two survive into
  `$( )` and `( )`, which matters for substitution-based instrumentation.

### Signal delivery rules (manual, Jobs & Signals)

> The `INT` and `QUIT` signals for an invoked command are ignored if the command is followed
> by `&` and the `MONITOR` option is not active. **The shell itself always ignores the
> `QUIT` signal.** Otherwise, signals have the values inherited by the shell from its parent
> (but see the `TRAPNAL` special functions...).

Same POSIX 2.11 baseline as bash/dash (async `SIGINT`/`SIGQUIT` ignore without monitor
mode), plus zsh's own hard ignore of `SIGQUIT`. In monitor mode, "each background job that
completes triggers any trap set for `CHLD`" — the zsh-side hook for child reaping in scripts
(kernel side: [lifecycle EX-008](../exit-status/lifecycle.md#ex-008--zombies-orphans-sigchld-and-who-reaps)).

## SH-011 — Command substitution, background jobs, and exit propagation

### `$?` and lists

Manual (Parameters Used by the Shell): "`? <S>` — The exit status returned by the last
command." (`status` is a read-only alias: "Same as `?`"). AND/OR lists, pipelines, and
conditionals follow POSIX 2.9.2–2.9.4 (last-command semantics; `!` negation), and zsh has no
documented deviation — the deviations live in `ERR_EXIT`, not in `$?` itself.

### `ERR_EXIT` — documented zsh behavior that differs from bash's `-e`

Verbatim (manual, Description of Options → ERR_EXIT):

> If a command has a non-zero exit status, execute the `ZERR` trap, if set, and exit.
>
> The option is ignored when executing the commands following `while`, `until`, `if`, or
> `elif`, a pipeline beginning with `!`, or any command other than the last in command list
> containing `&&` or `||`. Hence neither `if foo; then true; fi`, nor `foo && true` trigger
> exit when `foo` returns with a non-zero exit status. **Note that if `foo` is a function,
> the option is also ignored during its whole execution.**
>
> The option is also ignored when executing a complex command (`if`, `for`, `while`,
> `until`, `repeat`, `case`, `select`, `always`, or a list in braces) if its exit status
> comes from a command executed while the option is ignored.

The middle bolded sentence is the portable-scripting trap: bash suppresses `-e` for the
*call site* of a function in a `&&`/`||` list; zsh suppresses it *for the function's entire
body* (bash behaves the same way in verified observation — see
[bash.md SH-006](./bash.md#sh-006--status-propagation-lists-conditionals-functions-set--e) —
but only zsh's manual spells the rule out). The final sentence adds a rule bash lacks:
a compound command whose failure "comes from" a suppressed context does not trigger exit —
`if true; then false && true; fi` does not kill an `ERR_EXIT` zsh even though the `if`
itself returns non-zero. And unlike bash's `-e`, "this behaviour is not disabled in
interactive shells — a non-zero status on the command line causes the shell to exit."

One documented interaction to keep in mind for long-running scripts: "Exiting due to
`ERR_EXIT` has certain interactions with asynchronous jobs noted in [Signals]" — namely the
shell "will cause the shell to exit without waiting" for its implicit asynchronous jobs
(process substitutions, multios handlers), so an `ERR_EXIT` abort can strand those children.

### Command substitution and subshells

Command substitution follows POSIX 2.6.3 (subshell environment; status of the substitution =
last command in it). Two zsh-specific notes from the trap discussion above: `ZERR` and
`DEBUG` traps are *kept* within subshells (bash resets everything trapped), and the `<Z>`
emulation note on `pipestatus` means substitution code running under `emulate sh` loses
zsh-only facilities. For `errexit` inheritance into substitutions, zsh's manual does not
document a bash-`inherit_errexit`-equivalent option; the `ERR_EXIT` "complex command" rule
above is the documented zsh-side behavior — scripts needing the exact bash semantics should
set expectations explicitly rather than assume a port.

### Background jobs and `wait`

Manual (Shell Builtin Commands → wait):

> Wait for the specified jobs or processes. If `job` is not given then all currently active
> child processes are waited for. Each `job` can be either a **job specification or the
> process ID** of a job in the job table. The exit status from this command is that of the
> job waited for. If `job` represents an unknown job or process ID, a warning is printed
> (unless the `POSIX_BUILTINS` option is set) and the exit status is **127**.

Notables:

- `wait` takes jobspecs (`%1`, `%job`) *and* PIDs; there is **no `wait -n`** option in the
  documented builtin (as of the current manual) — bash's "wait for next job" convenience has
  no zsh equivalent; use `wait` with no args (all children) or per-job waits.
- zsh lets you `wait` on "recent processes (specified by process ID, not by job) that were
  running in the background **even if the process has exited**" (manual, wait) — a reaping
  window most shells close.
- `$!` gives the PID of the last background job; `&|`/`&!` launch *disowned* jobs that leave
  the job table immediately (manual, Jobs & Signals) — nothing to `wait` on afterwards, no
  status, no SIGHUP protection discussions: the job is on its own from birth.
- Job control (monitor mode) gives the job table, `jobs -l`, suspend/continue, and — with
  `NOTIFY` — immediate job-change reports instead of pre-prompt ones (manual, Jobs & Signals);
  see SH-010 for the `CHLD` trap in monitor mode and the SIGTTIN/SIGTTOU background-stop
  mechanics common to all shells ([bash.md SH-005](./bash.md#sh-005--async-jobs--wait-wait--n-and-job-control-in-scripts)).

## Related Topics

- [bash: `$?`, pipelines, traps, jobs](./bash.md) — `PIPESTATUS` vs `pipestatus` contrast
- [dash: POSIX-strict semantics](./dash.md) — the minimal baseline
- [Portability matrix](./index.md) — bash/dash/zsh/POSIX feature table
- [The life of an exit status](../exit-status/lifecycle.md) — kernel/wait layer
- [Conventions and their limits](../exit-status/conventions.md) — status interpretation classes
- [kill(2), raise(3), kill utility](../interfaces/kill-raise.md) — sending signals to zsh jobs
- [zsh](../../shell/zsh.md) — the book's general zsh chapter

## References

- zsh manual, *Parameters Used by the Shell* (`?`, `status`, `pipestatus`, array indexing legend, `<S>`/`<Z>` flags) — zsh project documentation sources — <https://zsh.sourceforge.io/Doc/Release/Parameters.html> (rendered), source: <https://github.com/zsh-users/zsh/blob/master/Doc/Zsh/params.yo>
- zsh manual, *Description of Options* (`PIPE_FAIL`, `ERR_EXIT`, `KSH_ARRAYS`) — zsh project — <https://zsh.sourceforge.io/Doc/Release/Options.html> (rendered), source: <https://github.com/zsh-users/zsh/blob/master/Doc/Zsh/options.yo>
- zsh manual, *Jobs & Signals* (`TRAPNAL`, async INT/QUIT ignore, monitor mode, job specs) — zsh project — <https://zsh.sourceforge.io/Doc/Release/Jobs-_0026-Signals.html>, source: <https://github.com/zsh-users/zsh/blob/master/Doc/Zsh/jobs.yo>
- zsh manual, *Shell Builtin Commands* (`trap`, `wait`, `ZERR`/`DEBUG`/`EXIT` trap semantics) — zsh project — <https://zsh.sourceforge.io/Doc/Release/Shell-Builtin-Commands.html>, source: <https://github.com/zsh-users/zsh/blob/master/Doc/Zsh/builtins.yo>
- zshparam(1) / zshmisc(1) man page renders (flag legend, trap function semantics) — zsh distribution — <https://man.archlinux.org/man/zshparam.1.en>, <https://man.archlinux.org/man/zshmisc.1.en>
- POSIX.1-2017 XCU Chapter 2 — The Open Group — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html>
