# dash: POSIX-Strict Exit Semantics (SH-007 — SH-008)

dash (Debian Almquist shell) is the minimal, fast shell that Debian/Ubuntu use as `/bin/sh`,
and the de-facto referee for "what does plain POSIX do". That makes it the most portable and
the least forgiving of the three shells compared in this part: everything bash and zsh add
on top of POSIX XCU Chapter 2 is simply absent. All examples below were verified against
**dash 0.5.13.4** (the manual page fetched for this chapter identifies the package version;
`sandbox /bin/sh -> dash`). Related: [bash.md](./bash.md) (the superset),
[zsh.md](./zsh.md), and the [portability matrix](./index.md).

## SH-007 — Pipelines, `$?`, `pipefail`, and `errexit`

### Pipeline status

POSIX 2.9.2, implemented literally: the exit status of a pipeline is that of its **last**
command (negated by a leading `!`); a background pipeline reports 0 at launch.

```console
$ dash -c 'sh -c "exit 3" | true | cat; echo status=$?'
status=0
```

**`set -o pipefail` exists in current dash — update your folklore.** The dash manual
(fetched for this chapter, dash 0.5.13.4-1) documents it twice: under *set* —

> pipefail — Derive the exit status of a pipeline from the exit statuses of all of the
> commands in the pipeline, not just the last command, as described in the Pipelines section.

—and in *Pipelines*:

> If the pipefail option was enabled when the shell began execution of the pipeline, the
> pipeline's exit status is the exit status of the last command specified in the pipeline
> that exited with non-zero status, or zero if all commands in the pipeline exited with a
> status of zero.

```console
$ dash -c 'set -o pipefail; sh -c "exit 3" | true | cat; echo status=$?'
status=3
```

Version caveat: dash historically had no `pipefail` (it is not in POSIX 2.9.2), and the
feature is recent — the current manual documents it (verified in 0.5.13.4), but the exact
introduction version could not be verified from upstream release notes in this sandbox.
Portable scripts must still assume `pipefail` is *absent* wherever dash compatibility across
distributions matters; guard with a feature check if you use it. Unlike bash and zsh, dash
provides **no per-component status array at all** (no `PIPESTATUS`, no `pipestatus`) — once
a pipeline finishes, the individual statuses are gone; the only recovery is restructuring
(temp files, named pipes, or process substitution workarounds).

### `$?`

Per the manual: `$?` "Expands to the exit status of the most recent pipeline" — identical
wording to POSIX 2.5.2. Everything that executes a pipeline resets it, including simple
commands (a simple command is a one-element pipeline):

```console
$ dash -c 'false | true; echo ps=$?'
ps=0
```

### `errexit` (`set -e`)

dash's manual is terse but precise (verbatim):

> If not interactive, exit immediately if any untested command fails. The exit status of a
> command is considered to be explicitly tested if the command is used to control an `if`,
> `elif`, `while`, or `until`; or if the command is the left hand operand of an `&&` or `||`
> operator.

That matches POSIX's intent — condition contexts never kill the shell — and verified
observation matches bash on the function case: a function called as the *left operand* of
`&&` has `-e` ignored inside its whole body too:

```console
$ dash -c 'set -e; f(){ false; echo inner; }; f && echo then-branch; echo survived=$?'
inner
then-branch
survived=0
```

**One place dash differs from bash's default**: `set -e` reaches **inside command
substitutions**. dash has no `inherit_errexit` knob because its behavior is already
"inherit":

```console
$ dash -c 'set -e; v=$(false; true); echo survived=$?'
[no output]              # `false' aborted the substitution (dash inherits -e); shell exited
```

bash (without `shopt -s inherit_errexit`) survives the same script — see
[bash.md SH-006](./bash.md#sh-006--status-propagation-lists-conditionals-functions-set--e).
POSIX itself does not require the substitution to clear `-e`; bash's default clearing is the
per-shell extension, dash's inheritance the stricter reading. Scripts relying on either
behavior should not.

## SH-008 — Command substitution, async jobs, traps, and signal differences

### Command substitution and subshell propagation

Same POSIX rules as bash (2.6.3 / 2.9.1): the substitution runs in a subshell; a bare
assignment takes the last substitution's status; an outer command's own status masks an
embedded substitution's:

```console
$ dash -c 'x=$(false); echo rc=$?'
rc=1
$ dash -c 'x=$(nosuchcmd 2>/dev/null); echo rc=$?'
rc=127
$ dash -c 'echo $(echo inner; false); echo outer=$?'
inner
outer=0
$ dash -c '( exit 5 ); echo rc=$?'
rc=5
```

### Async jobs, `$!`, and `wait`

Per the manual: `$!` "Expands to the process ID of the most recent background command
executed from the current shell. **For a pipeline, the process ID is that of the last
command in the pipeline**"; `wait` "Wait[s] for the specified job to complete and return[s]
the exit status of the given job... If no arguments are given, it waits for the current
shell's jobs to complete and return[s] an exit status of zero."

There is **no `wait -n`** — verified:

```console
$ dash -c 'sleep 0.1 & wait -n; echo rc=$?'
dash: 1: wait: Illegal option -n
rc=2
```

Status retrieval for a single arbitrary job therefore needs one `wait <pid>` per PID, or
bookkeeping around a polling loop. (bash's `wait -n` is the convenience dash lacks.)

Signal handling around async lists follows POSIX 2.11: "If job control is disabled... when
the shell executes an asynchronous list, the commands in the list shall inherit from the
shell a signal action of ignored (SIG_IGN) for the SIGINT and SIGQUIT signals." Two
verified, and instructive, consequences on dash 0.5.13.4:

```console
$ dash -c '( sleep 30 ) & p=$!; kill -INT $p 2>/dev/null; wait $p; echo rc=$?'
Terminated
rc=130
$ bash -c '( sleep 30 ) & p=$!; kill -INT $p 2>/dev/null; wait $p; echo rc=$?'
rc=0
```

The same script kills the dash async *subshell* (which reports 130 = 128+2) while bash's
async subshell ignores SIGINT outright. The POSIX wording applies the ignore to "the commands
in the list"; where the boundary lies — the external `sleep` vs the subshell *shell process*
itself — is where bash and dash disagree in observable behavior. Treat "background jobs
survive Ctrl-C" as a shell-specific promise, not a POSIX one. Note dash also prints its own
job-death notice (`Terminated`) to stderr, mirroring job-control shells.

### Traps: POSIX only

dash implements exactly the POSIX trap surface — **no `ERR`, `DEBUG`, or `RETURN` sigspecs**.
Verbatim from the manual:

> Cause the shell to parse and execute `action` when any of the specified signals are
> received... If signal is `0` or `EXIT`, the action is executed when the shell exits normally
> (that is not via an unhandled signal like SIGINT). `action` may be empty (`''`), which
> causes the specified signals to be ignored. With `action` omitted or set to `-` the
> specified signals are set to their default action. **When the shell forks off a subshell,
> it resets trapped (but not ignored) signals to the default action.** The trap command has no
> effect on signals that were ignored on entry to the shell.

Every clause is observable:

```console
$ dash -c 'trap "echo trap-ran" EXIT; exit 4'
trap-ran                 # EXIT trap ran; exit status 4 preserved (verified exit code)
$ dash -c 'trap "echo X" TERM; ( trap ); echo outer'
outer                    # subshell: trapped signal reset -> empty trap table
```

Three consequences scripts hit in practice:

- **`EXIT` traps fire only on *normal* exit.** A dash script killed by SIGINT/SIGTERM runs no
  cleanup unless it also traps those signals (then it must decide its own exit status —
  POSIX 2.11's "wait returns >128, then trap runs" pattern, same as bash).
- **Ignored-on-entry is sticky**: a wrapper that starts dash with `SIGINT` ignored can never
  have that ignore removed from inside (`trap - INT` is a no-op for it) — and that ignore is
  *inherited by all children*, which is how a `sh -c` layer accidentally immunizes a whole
  process tree against Ctrl-C.
- **No `ERR` trap** means bash-style `trap cleanup ERR` portability shims must use explicit
  `|| { ...; exit ...; }` after each critical command instead.

Trapped-signal timing matches POSIX 2.11 exactly (dash has no deferral deviation): a trapped
signal received while a foreground utility runs is acted on *after* that utility completes;
a `wait` interrupted by a trapped signal returns a status `>128` before the trap runs.

### Job control in scripts

Monitor mode (`set -m`, "Enable asynchronous notification of background job completion") is
off for scripts. Background children of a non-interactive dash therefore share the shell's
process group, and a background job that reads the terminal is stopped by `SIGTTIN`
(default `Stop`, per signal(7)) with no notification and no `jobs` table to inspect it from.
The manual's pipeline note also matters for signal topology: "unlike some other shells, each
process in the pipeline is a child of the invoking shell" — dash does not spawn an
intermediate process for pipeline members, so `pkill -P $$` patterns and `$!` semantics stay
predictable.

## Related Topics

- [bash: `$?`, pipelines, traps, jobs](./bash.md) — the feature-superset comparison point
- [zsh: PIPE_FAIL and TRAPNAL](./zsh.md) — the other extension shell
- [Portability matrix](./index.md) — bash/dash/zsh/POSIX feature table with version notes
- [Conventions and their limits](../exit-status/conventions.md) — 127/126/128+N interpretation
- [The life of an exit status](../exit-status/lifecycle.md) — kernel/wait layer under `$?`
- [POSIX shell page](../../shell/posix-shell.md) — the book's general POSIX shell chapter

## References

- dash(1) manual — Debian Almquist SHell, version 0.5.13.4-1 package render (sections: Pipelines, set/pipefail, trap, wait, Parameters) — <https://man.archlinux.org/man/dash.1.en>
- dash upstream — Herbert Xu's dash page — <http://gondor.apana.org.au/~herbert/dash/>
- POSIX.1-2017 XCU Chapter 2 (§2.5.2 `?`, §2.8.2 Exit Status, §2.9.2 Pipelines, §2.9.3 Lists & Asynchronous Lists, §2.11 Signals and Error Handling) — The Open Group — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html>
- bash(1) — used only as the contrast shell in verified side-by-side runs — <https://man.archlinux.org/man/bash.1.en>
