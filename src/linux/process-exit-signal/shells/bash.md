# Bash: `$?`, Pipelines, Traps, and Background Jobs (SH-001 — SH-006)

Bash is the reference shell for exit-status behavior in practice: the `128+N` convention,
`pipefail`, `PIPESTATUS`, and the `ERR` trap all come from its manual. This page documents
what bash *itself* guarantees, with minimal reproductions whose expected output was verified
against bash **5.2.37**; where a behavior is version-gated, the version note says so
explicitly. The other shells' equivalents are tabulated in
[shells/index](./index.md) — dash in [dash.md](./dash.md), zsh in [zsh.md](./zsh.md).

Everything here builds on the kernel/wait layer described in
[exit-status/lifecycle](../exit-status/lifecycle.md) and the interpretation table in
[exit-status/conventions](../exit-status/conventions.md).

## SH-001 — Pipeline status and `set -o pipefail`

POSIX baseline (XCU 2.9.2): "the exit status shall be the exit status of the last command
specified in the pipeline" (and with the leading `!`, its logical negation). Bash follows
this, and extends it with `pipefail` — per the Bash Reference Manual, §3.2.3 Pipelines:

> The exit status of a pipeline is the exit status of the last command in the pipeline,
> unless the `pipefail` option is enabled. If `pipefail` is enabled, the pipeline's return
> status is the value of the **last (rightmost) command to exit with a non-zero status, or
> zero if all commands exit successfully**.

```console
$ bash -c 'sh -c "exit 3" | true | cat; echo status=$?'
status=0                  # default: only the last command counts
$ bash -c 'set -o pipefail; sh -c "exit 3" | true | cat; echo status=$?'
status=3                  # pipefail: rightmost non-zero wins
$ bash -c '! true; echo status=$?'
status=1                  # ! negation
```

Notes:

- "If a pipeline is not executed asynchronously, the shell waits for all commands in the
  pipeline to terminate before returning a value. The return status of an asynchronous
  pipeline is 0" (per the manual, §3.2.3) — background pipelines do not fail.
- `pipefail` is **disabled by default** ("This option is disabled by default", §4.3.1 The
  Set Builtin). Version note: commonly attributed to bash 3.0; the current manual documents
  the option itself, but the NEWS/changelog file confirming the introduction version was
  unreachable at research time — treat "≥ 3.0" as unverified attribution.
- `pipefail` interacts with `set -e` and the `ERR` trap: `-e` fires for "any command in a
  pipeline but the last (**subject to the state of the pipefail shell option**)" (§4.3.1) —
  with pipefail on, a failing non-final pipeline element can kill a `-e` script.

## SH-002 — `$?`, `PIPESTATUS`, and what resets them

`$?` per the manual (§3.7.5): "The exit status of the last command is available in the
special parameter `$?`" — and POSIX 2.5.2 defines it as "the decimal exit status of the most
recent pipeline". One integer, last command only:

```console
$ bash -c 'sh -c "exit 3" | true | sh -c "exit 5"; echo st=$?'
st=5
```

For per-component statuses bash provides the `PIPESTATUS` array (§5.2 Bash Variables):
"a list of exit status values from the commands in the **most-recently-executed foreground
pipeline, which may consist of only a simple command**":

```console
$ bash -c 'sh -c "exit 3" | true | sh -c "exit 5"; echo st=$? ps=${PIPESTATUS[*]}'
st=5 ps=3 0 5
```

The defining property of `PIPESTATUS` is that it is **transient** — the manual's own list of
what re-sets it includes multi-element pipelines, timed and negated pipelines, *simple
commands*, subshells created with `(`, `[[`, `((`, and more:

```console
$ bash -c 'true | false; echo ps=${PIPESTATUS[*]}; echo x; echo after=${PIPESTATUS[*]}'
ps=0 1
after=0                  # the intervening `echo x' clobbered it
```

The documented usage pattern is therefore to copy or expand it *immediately*: 
`p=("${PIPESTATUS[@]}")` or `echo "${PIPESTATUS[@]}"` as the very next command. The same
manual section suggests `PROMPT_COMMAND`-based tracing for interactive audits (record
`PIPESTATUS`/`$?` before the next prompt). There is no `PIPESTATUS`-equivalent in POSIX —
scripts that must run under dash have no portable way to see per-element statuses (see
[dash.md](./dash.md)); zsh's array has the same purpose but a different name, case, and
indexing ([zsh.md](./zsh.md)).

## SH-003 — Command substitution and subshell propagation

POSIX 2.6.3 runs the substitution "in a subshell environment"; 2.9.1 fixes the status rule:
"If there is no command name, but the command contained a command substitution, the command
shall complete with the exit status of the last command substitution performed. Otherwise,
the command shall complete with a zero exit status." Bash matches:

```console
$ bash -c 'x=$(false); echo rc=$?'
rc=1                     # assignment-only command: last substitution's status
$ bash -c 'x=$(nosuchcmd 2>/dev/null); echo rc=$?'
rc=127                   # command-not-found inside a substitution propagates
$ bash -c 'echo $(echo inner; false); echo outer=$?'
inner
outer=0                  # the outer echo succeeded; the substitution status is masked
```

That last line is the classic footgun: a substitution *embedded in a larger command* cannot
fail the command — the outer command's own status (here builtin `echo` = 0) is what `$?`
sees. For bash's `${var| command; }`-style alternate substitution the side effects (including
`exit`) hit the current shell, per §3.5.4.

Subshells are the second propagation mechanism:

```console
$ bash -c '( exit 5 ); echo rc=$?'
rc=5
```

Two documented wrinkles (§3.7.5 / POSIX mode): **when not in POSIX mode, Bash clears `-e` in
the subshell created for command substitution**; the `inherit_errexit` shopt (SH-006)
controls exactly this. And trapped-but-not-ignored signals are reset to their original
values when a subshell is created (§trap; verified in SH-004).

## SH-004 — Traps and signal delivery

The `trap` builtin (per the manual, Bourne Shell Builtins):

- `trap 'action' sigspec...` — run *action* when a signal is caught.
- `trap '' INT` — **ignore**: "the signal specified by each sigspec is ignored by the shell
  and commands it invokes" (children inherit the ignore).
- `trap - INT` (or action absent) — **reset**: "each specified sigspec's disposition is reset
  to the value it had when the shell was started" (not necessarily the kernel default —
  the shell's *entry* disposition).
- `trap -p` / `trap` — display current traps in reusable form; `-l` lists names.

```console
$ bash -c 'trap "" INT; trap -p INT; trap - INT; trap -p INT; echo done'
trap -- '' SIGINT
done                     # after `trap -': no trap at all
```

sigspecs beyond signals (per the manual):

| sigspec | When the action runs |
|---------|----------------------|
| `0` / `EXIT` | When the shell exits — "Any trap on EXIT is executed before the shell terminates" (§exit builtin). The exit status is preserved through the trap unless the trap runs `exit` itself. |
| `ERR` | Whenever a pipeline, list, or compound command returns non-zero, **subject to the same exemptions as `errexit`** (see SH-006). |
| `DEBUG` | Before every simple command, `for`/`case`/`select`, `((` and `[[`, arithmetic `for`, and before the first command in a function. |
| `RETURN` | After each shell function or `.`/`source` script finishes. |

**When do signal traps run?** The manual (§3.7.6 Signals) and POSIX 2.11 agree, and this is
the single most load-bearing sentence for scripts: "If Bash is waiting for a command to
complete and receives a signal for which a trap has been set, it will not execute the trap
until the command completes." I.e., the trap is deferred until after the foreground child
finishes — a `sleep 100` in the foreground delays your `SIGTERM` cleanup unless the script
`wait`s instead. The paired rule: "If Bash is waiting for an asynchronous command via the
`wait` builtin, and it receives a signal for which a trap has been set, the `wait` builtin
will return immediately with an exit status **greater than 128**, immediately after which the
shell executes the trap." (POSIX 2.11 words the same rule; it also leaves the *order* of
multiple pending trap actions unspecified.)

**Delivery to shell vs children** (per §3.7.6):

- Non-builtin children inherit the shell's signal dispositions, *except* that anything the
  shell ignores is ignored by children too ("unless trap sets them to be ignored, in which
  case the child process will ignore them as well").
- Asynchronous commands (job control off) ignore `SIGINT` and `SIGQUIT` in addition to
  inherited dispositions — bash implements POSIX 2.11 ("the commands in the list shall
  inherit from the shell a signal action of ignored (SIG_IGN) for the SIGINT and SIGQUIT
  signals"). Verified consequence — you cannot SIGINT an async subshell from a script:

  ```console
  $ bash -c '( sleep 30 ) & p=$!; kill -INT $p 2>/dev/null; wait $p; echo rc=$?'
  rc=0                    # the async subshell ignored SIGINT; nobody died
  ```
- Commands run inside command substitution ignore the keyboard job-control signals
  `SIGTTIN`, `SIGTTOU`, `SIGTSTP` (per §3.7.6).
- Interactive-only defaults (§3.7.6): without traps, interactive bash ignores `SIGTERM`,
  catches and handles `SIGINT`, always ignores `SIGQUIT`, and with job control ignores
  `SIGTTIN`/`SIGTTOU`/`SIGTSTP`. Non-interactive shells (scripts) do none of this.

**Ignore/reset/inherit matrix** (per the trap builtin description): "When the shell is not
interactive, signals ignored upon entry to a non-interactive shell cannot be trapped or
reset" — a script started with SIGINT ignored can never trap SIGINT. "Trapped signals that
are not being ignored are reset to their original values in a subshell or subshell
environment when one is created" — `trap 'echo hi' TERM; ( trap )` shows an empty trap
table inside the subshell; dash documents the identical rule (§dash manual; see
[dash.md](./dash.md)).

`wait` under traps: while `wait` is interrupted by a trapped signal it returns `>128` as
above; otherwise `wait` returns "the exit status of the last id" waited for, and a bare
`wait` with no children returns 0 (verified below).

## SH-005 — Async jobs, `$!`, `wait`, `wait -n`, and job control in scripts

The async contract (POSIX 2.9.3 + bash manual): the exit status of an asynchronous list is 0
at launch; the real status arrives only via `wait`:

```console
$ bash -c '( sleep 30 ) & p=$!; kill -TERM $p 2>/dev/null; wait $p; echo rc=$?'
[1]- Terminated              ( sleep 30 )
rc=143                       # 128+15, per SH-001-style convention (bash manual §3.7.5)
$ bash -c 'sleep 0.1 & wait; echo rc=$?'
rc=0                         # bare `wait' waits for all; 0 if no unwaited children
$ bash -c 'sleep 0.1 & wait -n; echo rc=$?'
rc=0
```

- `$!` is "the process ID of the job most recently placed into the background" — for a
  background *pipeline* it is the last element's PID.
- `wait -n` "waits for any one of the ids or, if no ids are supplied, any job or process
  substitution, to complete and returns its exit status" (§7.2). Version note: introduced in
  the bash 4.3 series; the current manual documents it, but the NEWS confirming 4.3 was
  unreachable at research time — same caveat as `pipefail` (SH-001). dash has no `wait -n`
  (verified: `dash: wait: Illegal option -n`, exit 2); zsh's `wait` accepts jobspecs but no
  `-n` flag (§zsh manual; [zsh.md](./zsh.md)).
- `wait` accepts jobspecs (`wait %1`) as well as PIDs, and each "id may be a process ID pid
  or a job specification jobspec; if a jobspec is supplied, wait waits for all processes in
  the job" (§7.2).
- **Job control in scripts**: monitor mode (`set -m`) is off in non-interactive shells, so
  scripts have no job table behavior — background children run in the shell's process group,
  foreground children get no separate terminal group. Consequences documented in §3.7.6:
  because shell and command share the terminal's process group, keyboard-generated signals
  (Ctrl-C) hit both; and a background job reading/writing the terminal gets `SIGTTIN`/
  `SIGTTOU` (default action: stop, per signal(7)) — in a monitor-mode-off script nothing
  reports the stop, the child silently joins the stopped set, and `wait` blocks forever
  unless you use `WUNTRACED`-style waiting, which the bash `wait` builtin does not expose
  (see [lifecycle EX-007](../exit-status/lifecycle.md#ex-007--stopped-and-continued-children-wuntraced-wcontinued-and-waitid-idtypes)).
  Interactive bash (monitor on) ignores SIGTTIN/SIGTTOU/SIGTSTP itself and manages
  process groups per §3.7.6.
- `huponexit`/`disown`: on `SIGHUP` an interactive login shell resends SIGHUP to jobs
  ("Before exiting, an interactive shell resends the SIGHUP to all jobs, running or
  stopped", §3.7.6); `disown` removes a job from that fate. This is a shell-level courtesy,
  not a kernel rule — the kernel's orphan-reparenting rules are in
  [lifecycle EX-008](../exit-status/lifecycle.md#ex-008--zombies-orphans-sigchld-and-who-reaps).

## SH-006 — Status propagation: lists, conditionals, functions, `set -e`

The propagation rules (POSIX 2.9.3 + manual §3.7.5):

- **AND/OR lists**: "the exit status of an AND/OR list shall be the exit status of the last
  command executed in the list"; `&&` runs the right side only if the left returned zero,
  `||` only on non-zero. Verified: `false && true` → status of last *executed* = `false` = 1.
- **`if`/`while`/`until`/`for`/`case`**: status of the last command executed in the body, or
  0 if none ran (verified: `while false` → 0; `if true` → 0).
- **Functions**: `return N` sets the function's status; `exit N` terminates the *shell*
  (verified: `f(){ return 7; }; f; echo $?` → 7; after `g(){ exit 9; }` no later command
  runs). A `return` outside a function or sourced script is an error; a function without an
  explicit `return` reports the last command's status.
- **The shell's own exit**: bash exits with the last command's status unless a syntax error
  intervenes (§3.7.5); `exit N` passes `N & 0xFF` (truncation per
  [lifecycle EX-005](../exit-status/lifecycle.md)).

**`set -e` / errexit** — the manual's condition list (§4.3.1), abridged but precise: the
shell exits if a *pipeline* (which may be a single simple command), a *list*, or a *compound
command* returns non-zero — except where the failure was (a) part of the command list
following `while`/`until`, (b) part of the test following `if`/`elif`, (c) part of a `&&`/`||`
list other than the final command, (d) any command in a pipeline but the last (subject to
pipefail), or (e) a status inverted by `!`. Plus two documented subtleties: "If a compound
command other than a subshell returns a non-zero status because a command failed while `-e`
was being ignored, the shell does not exit. A trap on `ERR`, if set, is executed before the
shell exits." And: "This option applies to the shell environment and each subshell
environment separately... and may cause subshells to exit before executing all the commands
in the subshell."

Ignored-`-e` contexts also suppress the `ERR` trap for the same commands, and the ignored
state propagates *into functions* — verified:

```console
$ bash -c 'set -e; f(){ false; echo inner; }; f && echo then-branch; echo survived=$?'
inner
then-branch
survived=0               # -e ignored inside f because the call sits in a && list
```

zsh documents the same function-propagation rule explicitly ("if foo is a function, the
option is also ignored during its whole execution", zsh manual) — see
[zsh.md](./zsh.md) for where zsh's `ERR_EXIT` differs from bash's `-e`.

**`shopt -s inherit_errexit`** (per the Shopt list): "If set, command substitution inherits
the value of the errexit option, instead of unsetting it in the subshell environment. This
option is enabled when POSIX mode is enabled." Verified contrast:

```console
$ bash -c 'set -e; v=$(false; true); echo survived=$?'
survived=0               # without the option: -e unset inside $( ), `false' harmless
$ bash -c 'set -e; shopt -s inherit_errexit; v=$(false; true); echo survived=$?'
[no output]              # substitution aborted on `false'; assignment failed; shell exited
```

Version note: `inherit_errexit` is documented in the current manual; the usual attribution
to bash 4.4 rests on the NEWS file, which was unreachable at research time — unverified
attribution, feature verified present in 5.2.

**`set -e` practical reading**: it makes *untested* simple-command failures fatal only at
top level of the script and in subshell/compound contexts not listed above; it never fires
for condition contexts. Scripts that need "fail on the first pipeline failure" combine
`set -e` with `set -o pipefail` (SH-001); scripts that need per-command custom cleanup use
the `ERR` trap whose firing conditions are identical.

## Related Topics

- [dash: the POSIX minimal shell](./dash.md) — no `PIPESTATUS`, no `wait -n`, POSIX-only traps
- [zsh: PIPE_FAIL and TRAPNAL](./zsh.md) — lowercase `pipestatus`, `TRAPxxx` functions, `ERR_EXIT` nuance
- [Portability matrix](./index.md) — feature-by-feature bash/dash/zsh/POSIX table
- [The life of an exit status](../exit-status/lifecycle.md) — what `$?` is a projection of
- [Conventions and their limits](../exit-status/conventions.md) — interpreting 126/127/128+N correctly
- [kill(2), raise(3), kill utility](../interfaces/kill-raise.md) — sending signals to scripts and jobs
- [Standard signals](../signals/standard-signals.md) — dispositions bash inherits
- [bash](../../shell/bash.md) — the book's general bash chapter

## References

- Bash Reference Manual (Bash-5.2 edition) — Free Software Foundation; fetched from Chet Ramey's official distribution mirror (tiswww.case.edu) after gnu.org was unreachable from the research sandbox — <https://www.gnu.org/software/bash/manual/bash.html> (canonical), <https://tiswww.case.edu/php/chet/bash/bashref.html> (fetched)
- bash(1) man page — GNU Bash, distribution render — <https://man.archlinux.org/man/bash.1.en>
- POSIX.1-2017 XCU Chapter 2 (§2.5.2 `?`, §2.6.3 Command Substitution, §2.8.2 Exit Status, §2.9.2 Pipelines, §2.9.3 Lists, §2.11 Signals and Error Handling) — The Open Group — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html>
- bash NEWS (version attributions for pipefail / wait -n / inherit_errexit) — git.savannah.gnu.org — <https://git.savannah.gnu.org/cgit/bash.git/tree/NEWS> (unreachable from the research sandbox; version attributions in text are marked unverified accordingly)
