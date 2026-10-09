# echo — write arguments to standard output

## Overview

`echo` writes its arguments followed by a newline to standard output. It is
the most-used command in shell scripts and, paradoxically, the least
portable: its handling of the `-n` flag and backslash escapes differs
between shells, between `/bin/echo` implementations, and across POSIX's
deliberately vague specification.

Two `echo`s exist on every Debian/Ubuntu system: the **shell builtin**
(bash's, dash's, zsh's — each with its own rules) and the standalone
**`/usr/bin/echo`** from the `coreutils` package. Scripts nearly always run
the builtin; `/bin/echo` matters for `env`, `find -exec`, `xargs`, and
scripts run by non-shell programs. The builtin's behavior is controlled by
the *shell*, not by this binary — `echo` is the canonical example of a
coreutils tool that is rarely the one actually executing.

The professional rule this page defends: **use `printf` for anything with
variables or escapes; use `echo` only for fixed literal strings**. The
reasons, the historical mess, and the exact behavioral matrix are below.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) for `/usr/bin/echo`; builtins ship with each shell |
| Section (man) | 1 |
| Path | `/usr/bin/echo` on modern Debian/Ubuntu |
| First appeared / lineage | Multics/1st Edition UNIX era; a builtin in every major shell since the Bourne shell days |
| Standards | POSIX.1-2018 (`echo`) — with results explicitly *unspecified* in the corners that matter |

## Synopsis

```
echo [STRING]...
echo [OPTION]... [STRING]...
```

Main forms (GNU /usr/bin/echo):

```bash
echo hello world           # -> hello world
echo -n no-newline         # -> no-newline (no trailing newline)
echo -e 'a\tb'             # -> a<TAB>b    (interpret escapes)
echo -E 'a\tb'             # -> a\tb       (literal backslashes, default)
```

## How It Works

`echo` concatenates its operands with single spaces, appends a newline, and
writes the result to stdout. The entire complexity lives in one question:
*are backslash sequences in the operands interpreted?*

### The four implementations you will actually meet

| Implementation | `echo 'a\tb'` (no flags) | `echo -e 'a\tb'` | `echo -n x` |
| --- | --- | --- | --- |
| GNU `/usr/bin/echo` | `a\tb` literal | `a<TAB>b` | no newline |
| bash builtin (default) | `a\tb` literal | `a<TAB>b` | no newline |
| dash builtin (`/bin/sh`) | `a<TAB>b` — interprets **by default** | `-e a<TAB>b` — `-e` is just a word! | no newline |
| zsh builtin | `a<TAB>b` — interprets by default | `a<TAB>b` | no newline |

Verified on this system: bash's builtin printed `a\tb` literally without
`-e`, while `/bin/sh` (dash) printed a real tab without any flag and treated
`-e` as an ordinary argument. Both are "correct".

### Why POSIX blesses the chaos

POSIX specifies `echo` so that it is almost useless as a contract: *if the
first operand is `-n`, or if any operand contains a backslash, the results
are implementation-defined*. This was a deliberate truce — System V echo
interpreted escapes and had no `-n`; BSD echo had `-n` and did not
interpret — and no behavior could be chosen that broke the other camp. The
standard then points every portable script at **`printf`**, whose format
semantics *are* fully specified.

### Escape sequences (GNU echo, bash builtin with -e, printf %b)

```
\a  alert (bell)        \b  backspace          \c  suppress further output
\e  escape              \f  form feed          \n  newline
\r  carriage return     \t  horizontal tab     \v  vertical tab
\\  backslash           \0nnn octal (1-3 digits)   \xHH hex (GNU)
```

`\c` is the odd one: with `-e`, it stops output entirely — including the
trailing newline — so `echo -e 'no newline here\c'` behaves like a
`printf '%s'`. Scripts relying on it break on shells without `-e`.

### bash builtin switches

Two shell options change bash's builtin, which is why "echo works on my
machine" is not a contract:

```bash
shopt -s xpg_echo   # builtin echo interprets escapes WITHOUT -e (XPG style)
set +o posix        # in POSIX mode bash echo DOES interpret escapes without -e
```

A bash script that behaves differently under `bash --posix`, or a function
sourced into another shell, can silently change every `echo` in scope.

### The exit status question

`echo` exits 0 after a successful write and nonzero only on a write error
(`echo hi >/dev/full` fails). It never inspects its arguments for meaning,
so `echo "$status"` cannot fail — people who want a conditional need
[`false`](./false.md), `test`, or `grep`, not echo.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-n` | Do not print the trailing newline |
| `-e` | Interpret backslash escapes in the operands |
| `-E` | Explicitly disable escape interpretation (GNU/bash default) |
| `--` | Not supported by all echos! `/usr/bin/echo -- x` prints `-- x`... GNU echo treats `--` normally, but the *builtin* may not — another portability trap |

Because option parsing itself is unspecified (dash treats `-e` as a word,
some echos accept `-n` only as the *first* operand), even the option table
above is only the GNU/bash behavior.

## Usage Patterns

```bash
# Fixed literal text: the one use where echo is fully safe
echo "=== deployment starting ==="
```

```bash
# Progress marker without newline (bash builtin)
echo -n "checking... "
```

```bash
# Multi-line literal with a here-doc instead of escapes
cat <<'EOF'
line one
line two
EOF
```

```bash
# Append a line to a file
echo "export PATH=$HOME/.local/bin:\$PATH" >> ~/.bashrc
```

```bash
# Debugging pipeline data (escape-safe via printf)
printf 'got: <%s>\n' "$value"
```

```bash
# Tab-separated output — explicit, portable
printf '%s\t%s\n' "$user" "$shell"
```

```bash
# /usr/bin/echo when the builtin is not available (find -exec context)
find . -maxdepth 1 -type d -exec /bin/echo dir: {} \;
```

```bash
# Compare builtin vs binary vs dash on the same input (portability lab)
echo 'a\tb'; /usr/bin/echo 'a\tb'; sh -c "echo 'a\tb'"
```

```bash
# Banner with real newlines from a single command (GNU)
echo -e "header\n-----\nbody"
```

```bash
# Test whether a program writes to a full disk (write error path)
echo test >/dev/full; echo "exit=$?"
```

## Nuances and Gotchas

- **Variables with backslashes are a silent data-corruption vector.**
  `echo "$logline"` where the line contains `\t` or `\n` prints them
  interpreted (dash, zsh, bash-with-xpg_echo) or literal (bash default).
  `printf '%s\n' "$logline"` prints the value verbatim, always.
- **The classic `-n` trap:** on some historical sh implementations
  `echo -n` printed `-n`. POSIX explicitly refuses to define it. If a
  prompt must not end in a newline, use `printf '%s' "prompt: "`.
- **dash treats `-e` as a word.** `echo -e 'a\tb'` under `/bin/sh` on
  Debian prints `-e a<TAB>b`. Scripts that start with `#!/bin/sh` and use
  `-e` are broken on the very systems they target.
- **`echo` concatenates with spaces and cannot suppress the separator**;
  building exact byte streams (NUL, CRLF, fixed columns) is `printf` work.
- **`echo` cannot print NUL bytes at all** — the shell cannot pass them as
  arguments — another reason `printf '\0'`/`-z`-style tools exist.
- **Leading `-` operands:** `echo -file` prints `-file` in bash and GNU
  echo but is ambiguous by POSIX (an operand starting with `-` may be
  parsed as an option). `printf '%s\n' -file` is safe everywhere.
- **`echo` in pipelines loses data only via SIGPIPE** (`echo seq | head
  -1` can exit 141 under `pipefail`) — surprising in scripts that check
  `$?` of a decorative echo.
- **`/bin/echo` vs `command echo`:** testing the *binary* is not testing
  the *builtin* your script will actually run. To force the binary:
  `/usr/bin/echo`; to force the builtin: `command echo` or `builtin echo`.
- **`xpg_echo`/`posix` mode flips bash's builtin silently** — CI runners
  that set `SHELL`/`BASH_ENV` differently have caused real production
  incidents around escape interpretation.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Output written successfully |
| nonzero | Write error (disk full, EPIPE without trap, closed stdout) |

Note the asymmetry with `printf`: printf's exit status reflects its own
format processing and can also fail on write errors; both are 0 on the
happy path.

## Related Commands

- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- [`false`](./false.md) — what to use when you need a *failing* command rather than printed text
- [`env`](./env.md) — how `/usr/bin/echo` gets invoked when no shell is involved (`env echo`, shebang trickery)
- [bash](../../shell/bash.md) — builtin vs external command resolution and `command`/`builtin` keywords
- [posix-shell](../../shell/posix-shell.md) — the POSIX shell rules that make `printf` the portable spelling

## Interview Questions

### Q: A script with `#!/bin/sh` uses `echo -e 'a\tb'` and works on the developer's machine but prints `-e a<TAB>b` in a Debian container. What happened?

On the developer's system `/bin/sh` is a shell (or symlink target) whose
builtin echo accepts `-e` and does not interpret escapes by default — e.g.
bash in some configurations. In the Debian container `/bin/sh` is dash,
whose builtin interprets escapes *by default* and therefore treats `-e` as
an ordinary word to print. The fix is to switch to `printf 'a\tb\n'`, whose
behavior is fully specified, or to make the script explicitly bash with a
proper shebang. The root cause is POSIX leaving echo's corners
implementation-defined.

### Q: When does the `/usr/bin/echo` binary actually run instead of a shell builtin?

Whenever no shell resolves the command name: `find -exec echo {} +`,
`xargs echo`, `env echo hi`, an `#!/usr/bin/echo` shebang trick, `execve`
from C or Python, and cron/CGI contexts that exec directly. Also when a
script writes `command echo` — no, that forces the *builtin*; the binary is
forced by an absolute path. Knowing which echo runs is prerequisite to
predicting escape behavior, since the two can differ on the same system.

### Q: Why does POSIX deliberately leave `echo`'s backslash and `-n` behavior unspecified instead of standardizing one behavior?

Because in 1992 the two installed bases were mutually incompatible: System V
echo interpreted escapes and lacked `-n`, BSD echo had `-n` and did not
interpret. Standardizing either behavior would have broken millions of
working scripts, so POSIX codified the disagreement as
"implementation-defined" and standardized `printf` as the portable
alternative instead. This is a designed case study in standards
engineering: where agreement was impossible, the standard added a new tool
rather than breaking either camp.

### Q: Give two concrete inputs where `echo "$var"` and `printf '%s\n' "$var"` produce different output, and explain which is "correct".

(1) `var='a\tb'`: bash's echo prints `a\tb` literally while dash's prints a
real tab — printf prints the literal characters under every shell, which is
the correct, predictable rendering of the variable's value. (2)
`var='-n'`: `echo $var` unquoted (or even quoted on some shells) is parsed
as the option, printing nothing, while printf prints `-n`. Both cases share
one moral: variable data must go through printf's `%s`, which treats its
argument as pure data.

### Q: `echo hi >/dev/full` fails — why does this matter for scripts, and what is the fix?

`/dev/full` always returns ENOSPC on write, so echo exits nonzero with a
diagnostic. In a `set -e` script any echo into a full filesystem aborts the
script — desirable — but scripts that use echo for decorative output
between real commands often never considered that an echo *can* fail. The
general lessons: check write errors on output-producing commands, prefer
`set -o pipefail` so pipeline echo failures surface, and remember that
stdout can be a full disk or a closed pipe in production exactly as it is
with `/dev/full` in tests.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/echo.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
