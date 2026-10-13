# env — run a command in a modified environment

## Overview

`env` sets or unsets environment variables and then executes a command with
the resulting environment. Given no command, it prints the current
environment. It is the standard tool for: running programs with a controlled
variable set (`env -i`, `env -u`), launching interpreters from scripts whose
absolute location you don't want to hardcode (`#!/usr/bin/env python3`), and
passing multiple arguments to that interpreter despite the kernel's
single-argument shebang limit (`#!/usr/bin/env -S python3 -u`).

Debian ships it in `coreutils` at `/usr/bin/env`. Its niche is precise: the
shell can prefix variables (`VAR=x cmd`) but only where a shell is involved;
`env` works anywhere an executable path is required — shebang lines,
`find -exec`, `xargs`, `sudo`, Makefile recipe lines, and
`execve(2)`-based launchers. The other coreutils member of the
"modified-context launcher" family, [`chroot`](./chroot.md), does the same
trick for the filesystem root instead of the environment.

`env` also does more than most people know: recent GNU versions can change
directory (`-C`), rename argv[0] (`-a`), and fix up signal dispositions
(`--default-signal`) — the last one solves a real POSIX shell limitation
that no pure-shell construct can.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/env` on modern Debian/Ubuntu |
| First appeared / lineage | GNU shellutils (early 1990s); `#!/usr/bin/env` convention spread through Perl and Python culture |
| Standards | POSIX.1-2018 (`env`) |

## Synopsis

```
env [OPTION]... [-] [NAME=VALUE]... [COMMAND [ARG]...]
env -[v]S'[OPTION]... [NAME=VALUE]... [COMMAND [ARG]...]'
env
```

Main forms:

```bash
env                          # print the environment
env VAR=1 VAR2= cmd          # run cmd with additions/overrides
env -u EDITOR cmd            # run cmd without EDITOR
env -i /usr/bin/mydaemon     # run with an EMPTY environment
env -S 'python3 -u -X utf8' script.py   # split-string mode
```

The first operand that contains no `=` is the command; everything before it
is environment modification, everything after it is argv.

## How It Works

`env` is a tiny exec wrapper. Its entire job, in order: apply requested
environment modifications with `setenv`/`unsetenv` (left to right — later
assignments win), optionally adjust directory and signals, then `execvp`
the command. The modifications affect **only the child**; the parent
process and its environment are untouched. That one-directional property is
why `env` (like `VAR=x cmd`) cannot be used to "export into the current
shell" — a sub-process can never edit its parent's memory.

```
   shell / caller                       child process
  ┌───────────────┐    execve     ┌────────────────────────┐
  │ env -u FOO    │ ────────────► │ environ: (original     │
  │  A=1 B= cmd   │               │   minus FOO, plus A=1, │
  │               │               │   B deleted... wait:   │
  │  1. unsetenv  │               │   B="")                │
  │  2. setenv    │               │ 3. execvp(cmd, argv)   │
  │  3. exec      │               │ 4. cmd never sees env  │
  └───────────────┘               │    modify itself       │
                                  └────────────────────────┘
```

### Assignment semantics

- `VAR=value` sets (creates or overrides) the variable.
- `VAR=` sets the variable to the **empty string** — visibly present to
  the child, different from unset. Some programs treat empty and unset
  alike; others (e.g. `EDITOR=`, locale logic, `LD_PRELOAD=`) do not.
- Modifications apply left to right; `env A=1 A=2 cmd` runs with `A=2`,
  the earlier assignment silently discarded.
- A lone `-` operand means `-i` (clear the environment first).
- `env - PATH="$PATH" foo` is the docs' example of clearing everything
  *except* PATH — with `-i` spelled as the dash.

### Finding the command

The program is resolved via the **modified** `PATH` — if you set or clear
PATH before the command, the search uses the new value:

```bash
env PATH=/opt/special/bin tool       # tool is searched in /opt/special/bin only
env - /usr/bin/ls                    # with no PATH, give an absolute path
```

This is also a hardening feature: `env -i /usr/bin/program` removes the
`PATH`-hijacking attack surface that inheriting a writable PATH creates.

### Printing mode

Without a command, `env` prints `NAME=value` lines of the resulting
environment — functionally `printenv`'s output, and it exits 0. The
differences from `printenv`: env sorts nothing, `printenv VAR` prints the
value of a named variable without the `NAME=` prefix, and `env` gains an
exit-code protocol for command mode (below).

### -i and the empty environment

`env -i cmd` execs with an environment of exactly the variables listed on
the line. Anything not listed is gone — including `PATH`, `HOME`, `LANG`,
`TERM`. Consequences are immediate and non-obvious:

```bash
$ env -i /bin/sh -c 'echo "[$PATH] [$(tput bold 2>&1)]"'
[] [tput: No value for $TERM and no -T specified]
```

Empty environments break programs in three classic ways: PATH lookup fails
(external commands "disappear" for shells), TERM-dependent tools misbehave,
and locale falls back to C/POSIX. `env -i` is therefore both the best
reproducibility tool ("no hidden config") and the reason "works in my
shell, fails in cron/systemd" bugs get diagnosed: both cron and systemd
units run with minimal environments, and `env -i` reproduces that locally.

### -u: unset precisely

`env -u VAR cmd` deletes exactly one variable. Repeating `-u` deletes more.
It matters for variables whose *presence* changes behavior — `LD_PRELOAD`,
`PYTHONPATH`, `http_proxy` — where an override to empty would still be
"present".

### Shebang mechanics and the -S split-string mode

The kernel's `execve` shebang handling passes *at most one optional
argument* after the interpreter path, and Linux (unlike some BSDs) does not
split it:

```
script line:    #!/usr/bin/env python3 -u
kernel argv:    ["/usr/bin/env", "python3 -u", "./script.py"]   # ONE arg!
env sees:       a command named "python3 -u"  → ENOENT
```

That is why `#!/usr/bin/env python3 -u` historically failed on Linux.
`env -S` (and `-vS` for debugging) parses its single argument with a
quoting-aware splitter — honoring single/double quotes, backslash escapes,
and `${VAR}` expansion in GNU's implementation of the FreeBSD syntax — and
turns it into multiple argv entries:

```bash
#!/usr/bin/env -S python3 -u
# kernel: ["/usr/bin/env", "-S", "python3 -u", "script.py"]
# env:    execvp("python3", ["python3", "-u", "script.py"])
```

`-S` exists *for* shebang lines (using it interactively is legal but
pointless), and `-v` before `-S` shows the exact split:

```bash
$ env -vS 'A=1 python3 -u'
unset:    (nothing)
setenv:   A=1
executing: python3
   arg[0]= 'python3'
   arg[1]= '-u'
```

### #!/usr/bin/env portability

`#!/usr/bin/env python3` finds `python3` via PATH at runtime, so the script
works across distributions, venvs, pyenv shims, and macOS without edits.
The trade-offs are real and interviewers probe them:

| | `#!/usr/bin/python3` | `#!/usr/bin/env python3` |
| --- | --- | --- |
| Interpreter location | fixed | whatever PATH finds first |
| Portable across systems | no | yes |
| Honors venv/pyenv/nix | no | yes |
| Extra args on Linux | yes | only via `-S` |
| Attack surface | none | a shadowing `python3` earlier in PATH wins |
| Breaks if interpreter missing | clear ENOENT | same, but *which* PATH entry matched is opaque |

Security-sensitive installers (system packages, setuid contexts) prefer
absolute paths precisely because `env` trusts the caller's PATH.

### Signal options: what shells cannot do

POSIX says a shell must not change the *inherited* signal state when
`trap` restores a default — so `trap - PIPE` inside `sh -c` is a no-op if
SIGPIPE was ignored by the parent. `env` executes no shell, so it can
genuinely reset dispositions:

```bash
trap '' PIPE
sh -c 'trap - PIPE; seq inf | head -n1'                 # still ignoring PIPE
sh -c 'env --default-signal=PIPE seq inf | head -n1'    # PIPE default again
```

Related: `--ignore-signal=INT` (child immune to Ctrl-C), `--block-signal`
(posix_spawn-level sigmask), `--list-signal-handling` (audit trail to
stderr).

## Options That Matter

| Option | Effect |
| --- | --- |
| `-i`, `--ignore-environment` | Start from an *empty* environment; a lone `-` means the same |
| `-u`, `--unset=NAME` | Remove NAME from the environment before exec |
| `-S`, `--split-string=STRING` | Split STRING (quoting-aware) into options/assignments/command — the shebang enabler |
| `-v`, `--debug` | Print every processing step (unset/setenv/executing/argv) |
| `-C`, `--chdir=DIR` | Change working directory before exec |
| `-a`, `--argv0=ARG` | Pass ARG as argv[0] instead of the command path |
| `-0`, `--null` | In printing mode, end lines with NUL instead of newline |
| `--default-signal[=SIG]` | Reset SIG handling to default before exec |
| `--ignore-signal[=SIG]` | Set SIG to ignore before exec |
| `--block-signal[=SIG]` | Block SIG delivery before exec |
| `--list-signal-handling` | Show non-default signal handling to stderr before exec |

## Usage Patterns

```bash
# Run a one-off command with an extra variable (works under find/xargs too)
env LOG_LEVEL=debug ./server
```

```bash
# Reproduce cron's minimal environment locally when debugging
env -i SHELL=/bin/sh PATH=/usr/bin:/bin HOME=/root /bin/sh -c 'env | sort'
```

```bash
# Unset a proxy for a tool that must connect directly
env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY curl -sI https://example.com
```

```bash
# Wipe everything but keep PATH and HOME (note the lone dash = -i)
env - PATH="$PATH" HOME="$HOME" make check
```

```bash
# Python script with unbuffered output and forced UTF-8, via -S shebang
#!/usr/bin/env -S python3 -X utf8 -u
```

```bash
# Interpreter chosen per-venv at runtime
#!/usr/bin/env python3
```

```bash
# Provide a variable for a command executed by make (no shell prefix needed)
env BUILD_SHA=$(git rev-parse --short HEAD) ./build.sh
```

```bash
# Rename argv[0] so ps/top shows a friendly process name
env -a my-worker /usr/lib/myapp/worker --queue a
```

```bash
# Start in the data directory without a cd in the wrapper
env -C /srv/data ./ingest --dry-run
```

```bash
# Null-delimited environment dump for lossless round-trips
env -0 | xargs -0 -n1 echo
```

```bash
# Ensure a backgrounded tool dies with SIGPIPE like a normal program
env --default-signal=PIPE ./streamer | head -n1
```

```bash
# Guard: verify what the child will actually see before shipping
env -v -u SECRET A=1 ./binary --check
```

## Nuances and Gotchas

- **`VAR=` (empty) ≠ unset.** `env FOO= cmd` gives the child `FOO=""`;
  only `-u FOO` removes it. Programs that test `[[ -n $FOO ]]` behave the
  same for both, but programs that test *presence* (`env | grep`, Python's
  `"FOO" in os.environ`) differ — a recurring misconfiguration class.
- **Assignments are consumed in order and the first `=`-free word ends
  them.** `env A=1 cmd B=2` passes `B=2` as an *argument* to cmd, not an
  environment change. The `--`/`env prog=` disambiguation tricks in the
  coreutils docs exist for pathological program names containing `=`.
- **PATH is used *after* modification.** `env PATH=/x tool` fails if tool
  is not in /x — including failing to find `/bin/sh` fallbacks. When
  clearing PATH, use absolute command paths.
- **`env -i` scripts break subtly:** missing `TERM`, `LANG`, `HOME` change
  program behavior even when nothing "fails". When reproducing a service
  environment, copy the real one (`systemctl show -p Environment`,
  `cat /proc/$pid/environ | tr '\0' '\n'`) instead of assuming.
- **Shebang portability of `-S`:** the flag arrived in coreutils in the
  8.30 era; older Debian (stretch and earlier), macOS's FreeBSD-derived
  env (recent versions have it), and busybox env (implemented later) may
  lack it — a shebang using `-S` fails there with a confusing "env:
  invalid option" *as the script's error*.
- **`#!/usr/bin/env` trusts PATH:** in multi-user contexts a hostile PATH
  shadows the interpreter; distro packages and anything running with
  elevated rights should hardcode paths.
- **env is not `export`:** it cannot add variables to the current shell,
  and scripts that try (`env VAR=x` alone) have merely printed their
  environment.
- **Signal options are GNU-only** and unknown to POSIX env — a `-S`
  shebang using them restricts the script to modern GNU systems.
- **Exit code 125 vs the child's 125:** automation that branches on
  specific exit codes cannot distinguish "env itself failed" from "the
  child exited 125" — the convention's known blind spot, shared with
  [`chroot`](./chroot.md).

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | No COMMAND given: environment printed successfully |
| 125 | `env` itself failed (bad option, exec setup failure) |
| 126 | COMMAND found but could not be invoked (permissions, bad interpreter) |
| 127 | COMMAND not found (PATH search exhausted) |
| other | The exit status of COMMAND |

## Related Commands

- [`chroot`](./chroot.md) — sibling launcher: modified filesystem root instead of modified environment
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- [`echo`](./echo.md) — the classic companion in `env -i` reproducibility recipes (`env -i sh -c 'echo ...'`)
- [bash](../../shell/bash.md) — shell-side alternative `VAR=x cmd` and export semantics
- [posix-shell](../../shell/posix-shell.md) — shebang processing and the POSIX signal-disposition rules the signal options work around

## Interview Questions

### Q: What exactly does `env -i bash -c 'ls'` do and why does it often fail, while `env -i /bin/ls` works?

`env` execs bash with an empty environment; bash inherits no `PATH`, so its
command lookup for `ls` falls back to bash's compiled-in default path
(which may or may not include the directory holding ls) — and any script
inside
relying on PATH is fragile. `env -i /bin/ls` needs no lookup at all. The
teaching point: empty environments break *search*, not execution, and the
fix is absolute paths or an explicit `PATH=` assignment in the same env
line (`env -i PATH=/usr/bin:/bin bash -c ls`).

### Q: Explain why `#!/usr/bin/env python3 -u` fails on Linux but `#!/usr/bin/env -S python3 -u` works.

Linux passes everything after the interpreter path in a shebang as a
*single* argument, so the kernel asks env to run a program literally named
`python3 -u`, which does not exist — env exits 127 with "No such file or
directory". `env -S` takes its one argument and splits it with
quoting-aware rules into `python3` and `-u`, then execs the interpreter
with the extra flag. FreeBSD splits shebang arguments natively, which is
why the non-`-S` form "works on macOS/BSD but not Linux" — a top-tier
portability gotcha.

### Q: What is the difference between `VAR=x cmd`, `env VAR=x cmd`, and `env -u VAR cmd`, and when must you use env?

`VAR=x cmd` is shell syntax: it only exists where a shell parses the line,
and it *also* leaves `VAR` set for builtins/assignments in ways that can
leak into special builtins per POSIX. `env VAR=x cmd` is a program: it
works identically from `find -exec`, `xargs`, Makefiles, `sudo`,
shebang lines, and `execve` callers — anywhere there is no shell to do the
prefix. `env -u VAR cmd` removes a variable, which the shell prefix cannot
express at all (short of `unset` in a subshell + exec gymnastics). Rule:
shell prefix for interactive/shell-only, env for launchers and
unsetting.

### Q: Why can `env --default-signal=PIPE` succeed where a shell `trap - PIPE` is a no-op?

POSIX requires that a shell not change inherited signal dispositions: a
parent that set SIGPIPE to ignore passes that ignore down, and the child
shell's `trap - PIPE` must leave it ignored (state is inherited through
exec). `env` performs no shell interpretation — it calls `sigaction` to
restore the default disposition directly, then execs. That is precisely
why the coreutils docs show the `trap '' PIPE && sh -c ...` example: env
is the only POSIX-compliant way to hand a grandchild a *genuinely default*
SIGPIPE.

### Q: You must run a service as an unprivileged user with a minimal, fixed environment. Sketch how env participates (compared with chroot) and name one env-specific pitfall.

The launcher chain does context modification in layers: `chroot` confines
the filesystem view, then `chroot --userspec=...` drops privileges, and
`env -i PATH=... HOME=... LANG=C.UTF-8 ./service` fixes the environment so
no inherited variable (LD_PRELOAD, PYTHONPATH, proxies) alters behavior.
The env-specific pitfall: `VAR=` vs unset — writing `LD_PRELOAD=` still
*sets* the variable to empty, which some loaders and libraries treat
differently from absent; use `-u`. Also remember env's exit 125 is
indistinguishable from a service exiting 125, so wrap exit-code handling
accordingly.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/env.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
