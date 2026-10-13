# printenv — print (all or named) environment variables

## Overview

`printenv` prints the environment of the process that runs it. Called
with no arguments it dumps every variable as `NAME=value` lines; given
one or more NAMEs it prints just the values of the ones that exist, one
per line, and nothing (no error message) for the ones that don't. That
silent behavior plus a meaningful exit status makes it the standard
**existence test** for environment variables in scripts and CI:

```bash
if printenv GITHUB_ACTIONS >/dev/null; then ... fi
```

It looks trivial, and the interview questions it generates are anything
but: what printenv reads (its own inherited environment, not "the
shell's variables"), why `printenv MISSING` kills a `set -e` script, how
it differs from [`env`](./env.md) and from `echo "$VAR"`, and how to
inspect the environment of a process that isn't your shell.

Debian ships it in `coreutils` at `/usr/bin/printenv`. It is a BSD
original that never made it into POSIX.1-2018, but every mainstream
system carries it; GNU's version accepts multiple NAMEs at once.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/printenv` on modern Debian/Ubuntu |
| First appeared / lineage | BSD (3BSD era, circa 1980); carried into GNU shellutils, then coreutils |
| Standards | Not in POSIX.1-2018; universally available nonetheless |

## Synopsis

```
printenv [OPTION]... [NAME]...
```

Main forms:

```bash
printenv                 # whole environment, NAME=value lines
printenv HOME            # value of HOME, or nothing + exit 1
printenv HOME PWD USER   # GNU extension: several lookups at once
printenv -0              # NUL-terminated entries (round-trip safe)
```

## How It Works

### Two modes, one data source

printenv has exactly one data source: the `environ` array its parent
handed it at `exec` time. Dump mode prints the array in order; query
mode prints each NAME's value if present. It performs no sorting, no
filtering, no expansion — what you see is the inherited bytes.

```bash
$ printenv HOME
/home/z
$ printenv SHELL UV_CACHE_DIR PYTHONUNBUFFERED
/bin/bash
/var/cache/uv
1
$ printenv NO_SUCH_VAR_XYZ
$ echo $?
1
```

### The exit status is the API

| Invocation | stdout | exit |
| --- | --- | --- |
| `printenv` (no NAMEs) | all `NAME=value` lines | 0 |
| all NAMEs found | their values | 0 |
| some NAME missing | values of the found ones | 1 |
| NAME unset | nothing at all | 1 |

Note the asymmetries: a missing variable produces **no stderr message**
(it is data, not an error), and with multiple NAMEs printenv still
prints the ones it found before exiting 1. An **empty but set** variable
prints an empty line and exits 0 — visibly different from an unset one
only via the exit code:

```bash
$ EMPTY_VAR= printenv EMPTY_VAR | od -c
0000000  \n                                   # blank line, exit 0
$ printenv UNSET_XYZ | od -c
0000000                                       # zero bytes, exit 1
```

### Shell variables vs environment variables

printenv sees only **exported** variables. A plain shell assignment is
invisible to it; a command-scoped prefix assignment (`X=1 cmd`) *is*
exported to the child, which is why the two experiments below diverge:

```bash
$ bash -c 'X=1; printenv X; echo "rc=$?"'     # plain assignment
rc=1                                          # never exported
$ bash -c 'export X=2; printenv X; echo "rc=$?"'
2
rc=0
$ X=1 printenv X                              # prefix form exports to the child
1
```

### Versus env and echo "$VAR"

| | `printenv VAR` | [`env`](./env.md) | `echo "$VAR"` |
| --- | --- | --- | --- |
| Output for found var | bare value | `VAR=value` (dump mode) | value |
| Missing var | silent, exit 1 | silent (dump) | empty string (or abort under `set -u`) |
| Can modify env | no | yes (`-u`, `-i`, assignments) | no |
| Can exec a command | no | yes | no |
| Fork/exec cost | one process | one process | none (shell builtin) |
| Distinguishes empty vs unset | yes, via exit code | no (dump mode) | no |
| Works outside a shell | yes | yes | n/a |

`echo "$VAR"` is expanded by the shell before printenv-equivalent logic
ever runs, so it cannot tell `VAR=` from unset and it inherits `set -u`
behavior. printenv's exit code is the only silent, fork-cheap,
shell-agnostic presence test.

### Other processes' environments

printenv only ever reports its own inheritance. To read the environment
of a running process, read its procfs environ (same UID or root):

```bash
tr '\0' '\n' < /proc/1234/environ
sudo cat /proc/$(pgrep -f mydaemon | head -1)/environ | tr '\0' '\n'
```

This is also the standard way to answer "what environment does cron or
systemd actually give my job?" — run the job as a sleeping shell and
read it back, rather than guessing.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-0`, `--null` | End each output line with NUL instead of newline — lossless for values containing newlines, pairs with `xargs -0` |
| `--help`, `--version` | Standard GNU epilogue |

The option surface is nearly empty by design: printenv is a query, not
a transform. Everything interesting is in its argument and exit-status
protocol.

## Usage Patterns

```bash
# CI-friendly feature detection without bashisms
if printenv GITHUB_ACTIONS >/dev/null; then echo "on CI"; fi
```

```bash
# Hard requirement check with a clear failure
printenv DATABASE_URL >/dev/null || { echo "DATABASE_URL not set" >&2; exit 1; }
```

```bash
# Verify several variables in one shot (exit 1 if any missing)
printenv API_KEY API_URL >/dev/null || exit 1
```

```bash
# Distinguish empty from unset — echo cannot do this
printenv CONFIG_PATH >/dev/null && echo "set (maybe empty)" || echo "unset"
```

```bash
# Inspect the env a cron/systemd job will actually receive
tr '\0' '\n' < /proc/$$/environ | sort
```

```bash
# Lossless round-trip of the environment (values may contain newlines)
printenv -0 | xargs -0 -I{} echo "entry: {}"
```

```bash
# Compare two environments (e.g., login shell vs service shell)
diff <(bash -lc printenv) <(bash -c printenv)
```

```bash
# One-off injection test: does the child see the prefix assignment?
MY_FLAG=1 printenv MY_FLAG
```

```bash
# Debug which of many candidates is set, values and all
for v in HTTP_PROXY http_proxy ALL_PROXY; do printenv "$v" >/dev/null && echo "$v is set"; done
```

## Nuances and Gotchas

- **`set -e` eats scripts.** A bare `printenv MAYBE_MISSING` as a
  statement exits the shell with status 1 — verified: under `set -e`,
  the echo after it never runs. Guard it (`printenv X >/dev/null || ...`,
  `if printenv X; then`) or expect the script to vanish mid-run.
- **Missing is silent; empty is a newline.** `printenv UNSET` prints
  zero bytes and exits 1; `printenv EMPTY_SET_VAR` prints `\n` and exits
  0. Scripts that test only `$?` are correct; scripts that eyeball the
  output are being fooled.
- **It reads its own environment — nothing else.** "Print the
  environment" means the inherited one: plain shell variables are
  invisible until exported, and there is no way to aim printenv at
  another PID (that is `/proc/PID/environ` territory).
- **Multiple NAMEs are a GNU extension.** POSIX never standardized
  printenv; some BSD-derived implementations historically took one NAME.
  Loop over names (`for v in A B; do printenv "$v"; done`) for portable
  multi-lookup.
- **Values can contain newlines — line-based parsing breaks.** A env
  var holding a PEM block or multiline message corrupts
  `printenv | while read` loops; use `printenv -0 | xargs -0` for
  byte-exact handling.
- **Dumps leak secrets.** `printenv` in verbose logs, error reports, or
  CI annotations publishes tokens and connection strings; environments
  are world-readable to the same UID via `/proc/PID/environ` anyway, so
  treat "in the environment" as "readable by anything running as you".
- **Order is not alphabetical and not guaranteed.** The dump reflects
  the environ array order (effectively "insertion order" of the parent);
  anyone comparing two dumps should `| sort` first — see the diff
  pattern above.
- **`env` is not a drop-in query tool.** `env | grep '^VAR='` works but
  returns `VAR=...` and no exit-status semantics for one lookup; the
  pairing to remember is env = build an environment, printenv = ask
  about one.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | No NAMEs given: dump printed; or every NAME given was found |
| 1 | At least one specified NAME was not present in the environment |

There are no other statuses documented — printenv has no failure modes
beyond "not found" (and standard I/O errors).

## Related Commands

- [`env`](./env.md) — builds and launches with a modified environment; also dumps, but with `NAME=` prefixes and no query protocol
- [`echo`](./echo.md) — builtin expansion of `$VAR`; cheaper, but cannot distinguish empty from unset
- [`whoami`](./whoami.md) — identity the reliable way; `printenv USER`/`LOGNAME` can be spoofed or absent
- [`logname`](./logname.md) — login identity from the system, unlike environment-derived values
- [bash](../../shell/bash.md) — export/inheritance rules, `${VAR+set}` tests, and `set -u`/`set -e` interactions
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages

## Interview Questions

### Q: What does `printenv` exit with when a variable is missing, and why does that matter under `set -e`?

Exit 1, with no output and no stderr message — "not found" is a data
result, not an error. Under `set -e`, any simple command returning
nonzero ends the script, so a casual `printenv MAYBE_CONFIG` line will
silently terminate the run the moment the variable is absent. The safe
forms put printenv in a tested context: `if printenv X; then ...`, or
`printenv X >/dev/null || { ...; }`, where the status is consumed rather
than propagated.

### Q: How do you distinguish an empty variable from an unset one, and why can't `echo "$VAR"` do it?

`printenv VAR` prints an empty line and exits 0 for a set-but-empty
variable, and prints nothing at all with exit 1 for an unset one — the
exit code is the discriminator. `echo "$VAR"` renders both cases as the
empty string because the shell expands unset variables to nothing
(unless `set -u` aborts instead). Pure-shell alternatives exist
(`${VAR+set}` expands only when set), but printenv works identically
from any language that can exec a process.

### Q: Why does `X=1; printenv X` print nothing while `X=1 printenv X` prints 1?

The first form creates a plain shell variable that is never exported;
printenv reads only the inherited environment, so it sees nothing and
exits 1. The second form is a command-scoped assignment, which the shell
exports into the child's environment — printenv receives `X=1` in its
environ. The lesson generalizes: "shell variable" and "environment
variable" are different populations, and export/prefix is the bridge
between them.

### Q: You suspect a systemd service sees a different environment than your interactive shell. How do you prove it, and what is printenv's role?

printenv can only report the environment of the process running it, so
the trick is to get it (or a raw environ read) executed *in that
context*: `Environment=printenv`-style debug units, `ExecStart=/usr/bin/printenv`
redirection, or reading `/proc/$(systemctl show -p MainPID ...)/environ`
with `tr '\0' '\n'`. Then `diff <(bash -lc printenv) <(bash -c printenv)`
local reproduction. printenv's value is that its dump is the ground
truth of one process's inheritance — no shell interpolation in between.

### Q: Why does printenv have a `-0` flag, and when does it actually matter?

Because environment *values* may contain newlines (PEM keys, multiline
messages), so newline-delimited output is ambiguous and
`printenv | while read`-style parsing corrupts data. `-0` terminates
each entry with NUL, and NUL is the one byte guaranteed absent from
environment strings, so `printenv -0 | xargs -0` and similar are
byte-exact. It matters precisely when values are machine-generated
rather than simple tokens.

### Q: Compare printenv, `env`, and `echo "$VAR"` for reading one variable in a script.

`echo "$VAR"` is a builtin: zero fork cost, but it cannot distinguish
empty from unset and behaves differently under `set -u`. `printenv VAR`
costs a fork but gives a clean protocol: value on stdout, exit 0/1 for
found/not-found, no quoting hazards, and it works from any process, not
just shells. `env` is the wrong tool for queries — its dump includes
`NAME=` prefixes and offers no per-variable status — but it is the right
tool for *constructing* environments (`env -u X`, `env -i ...`). Pick by
need: builtin speed, portable status protocol, or environment
modification.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/printenv.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
