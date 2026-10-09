# getopt — parse command options for shell scripts (GNU/enhanced getopt(1))

## Overview

`getopt` is an external helper that normalizes command-line arguments so shell scripts can parse them safely: it reorders options and operands, expands abbreviations of long options, validates the option string, and prints the result *quoted* in a shell-specific dialect, ready for `eval set --`. It is the long-option-capable big brother of the shell `getopts` builtin, which handles only short options and cannot reorder arguments.

It ships in the `util-linux` package at `/usr/bin/getopt` (the "enhanced" getopt, distinct from the minimal BSD variant still found on macOS). Reach for it whenever a script needs `--output=file`-style long options, `-b VALUE` with spaces in values, or operand reordering (`cmd -a file1 -b file2` → options first). It is often confused with the C function `getopt(3)` (whose optstring syntax it reuses), the `getopts` builtin, and with hand-rolled `while [ $# -gt 0 ]` loops (which break on every quoting edge).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/getopt |
| First appeared | 1990s "enhanced" public-domain rewrite; part of util-linux since then |
| Standards | None (getopt(3) optstring syntax is POSIX; getopt(1) itself is a GNU/BSD extension) |

## Synopsis

```
getopt <optstring> <parameters>
getopt [options] [--] <optstring> <parameters>
getopt [options] -o|--options <optstring> [options] [--] <parameters>
```

Common one-line forms:

```
getopt -o 'o:v' -l 'output:,verbose' -n "$0" -- "$@"
getopt -s bash -o 'a:b::' -l 'alpha:,beta::' -- "$@"
getopt -T            # version probe: exit 4 = enhanced getopt
```

## How It Works

### The canonical recipe

A script calls `getopt` with its own option grammar plus `"$@"`, and lets it produce a canonical, quoted argument list. `eval set --` then replaces the script's positional parameters with that list, and a `case` loop consumes it:

```bash
#!/bin/bash
out=; verbose=false
PARSED=$(getopt -o 'o:v' -l 'output:,verbose' -n "$0" -- "$@") || exit 1
eval set -- "$PARSED"
while true; do
    case "$1" in
        -o|--output) out="$2"; shift 2 ;;
        -v|--verbose) verbose=true; shift ;;
        --) shift; break ;;
        *) echo "internal error" >&2; exit 1 ;;
    esac
done
# remaining "$@" are the operands
```

### What getopt does to the arguments

It parses per the optstring grammar, reorders options before operands, normalizes long-option forms, attaches values, terminates with `--`, and *shell-quotes* everything:

```bash
$ getopt -o 'ab:' -l 'alpha,beta:' -n demo -- -a -b 1 file
 -a -b '1' -- 'file'
$ P=$(getopt -o ab: -l alpha,beta: -n demo -- --beta=2 -- x y); echo "$P"
 --beta '2' -- 'x' 'y'
```

Note in the second run: `--beta=2` and `--beta 2` are equivalent input forms and both normalize to `--beta '2'`; values containing spaces or globs arrive safely quoted, which is precisely why the raw output must go through `eval` (unquoted shell-builtin string splitting would destroy it) and why `-u, --unquoted` is dangerous.

The quoting has two flavors only — sh-like and csh-like — selected with `-s`; the csh variant escapes problem characters instead of wrapping:

```bash
$ getopt -s csh -o 'm:' -- x 'hi there' y
 -- 'hi'\ 'there' 'x' 'y'
$ getopt -o 'm:' -- -m "it's" x          # sh/bash dialect (the default)
 -m 'it'\''s' -- 'x'
```

### Scanning modes: what the first optstring character can do

The man page gives `+` and `-` as legal first characters of the short optstring, and they change *where non-options may appear*:

```bash
$ getopt -o '+ab:' -- x -a -b 1      # '+' mode: stop at first non-option
 -- 'x' '-a' '-b' '1'                # -a/-b are now plain operands!
$ getopt -o '-ab:' -- x -a -b 1      # '-' mode: emit non-options in place
 'x' -a -b '1' --
```

`+` is the POSIX-permutation-off mode: everything after the first operand is an operand, exactly like `getopts`/POSIX `getopt(3)` with `POSIXLY_CORRECT`. `-` keeps option parsing but interleaves operands in the output stream instead of collecting them after `--` (useful for filters like `grep pattern` + `grep -v pattern` argument mixing). The environment variable `POSIXLY_CORRECT` forces `+` behavior even without the optstring prefix.

### Compatibility mode (and the -T probe again)

If `GETOPT_COMPATIBLE` is set in the environment, or the script uses the ancient first calling form (`getopt optstring parameters`, no `-o`), output is *unquoted* — the traditional, whitespace-unsafe format — and `-T` reports exit 0 instead of 4. This is why the `-T` probe must run in the same calling style as the real parse: an enhanced getopt called in compatible form behaves like the old one. Any stray `GETOPT_COMPATIBLE` in the environment silently downgrades your quoting; `unset GETOPT_COMPATIBLE` in the preamble is cheap insurance.

### The optstring grammar (same as getopt(3)/getopts)

```
a      flag, no argument
b:     option requiring an argument     (-b VALUE or -bVALUE)
c::    option with OPTIONAL argument    (only -cVALUE / --cloop=VAL attach a value)
```

Long options are declared comma-separated with `-l 'name:,other'` (colon = requires argument, double colon = optional). `-n <name>` controls the program name used in error messages; `-q` suppresses the getopt(3) error text (the caller still sees the exit status); `-Q` suppresses the parsed output too (pure validation).

### Why the shell builtin is not enough

```
                 getopts (builtin)        getopt (this tool)
short options    yes                      yes
long options     no                       yes (-l)
reordering       no (options must         yes (options hoisted
                 precede operands)         before operands)
quoting safety   values arrive via        output quoted for
                 variables                eval set --
availability     POSIX, always there      external binary, GNU/
                                          BSD variants differ
```

Scripts targeting busybox/POSIX-only environments use `getopts`; scripts needing long options or robust operand ordering use `getopt`.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-o, --options <optstring>` | Short-option grammar (`a`, `b:`, `c::`) |
| `-l, --longoptions <longs>` | Comma-separated long options (`name:`, `name::`) |
| `-n, --name <progname>` | Program name used in error reports |
| `-s, --shell <shell>` | Quoting dialect: `sh`, `bash`, `csh`, `tcsh` (and `fish` in recent releases) |
| `-a, --alternative` | Also accept single-dash long options (`-output x`), legacy style |
| `-q, --quiet` | Suppress error reporting by getopt(3) |
| `-Q, --quiet-output` | No normal output either — validation only |
| `-u, --unquoted` | Print without shell quoting (word-splitting hazard) |
| `-T, --test` | Version probe: exit 4 if enhanced getopt, 0 if the old BSD variant |

## Usage Patterns

```bash
# Long options with values, the standard preamble
PARSED=$(getopt -o 'o:,h' -l 'output:,help' -n "$0" -- "$@") || exit 1
eval set -- "$PARSED"

# Optional-argument option: --color / --color=never both legal
PARSED=$(getopt -o '' -l 'color::' -- "$@"); eval set -- "$PARSED"
case "$1" in --color) color="${2:-auto}"; shift 2 ;; esac

# Detect macOS/BSD getopt (no long options) before using -l
getopt -T > /dev/null
if [ $? -ne 4 ]; then echo "need enhanced (GNU) getopt" >&2; exit 1; fi

# Validate-only mode: reject bad user input without echoing it
getopt -Q -o 'ab:' -l 'alpha,beta:' -- "$@" || { usage; exit 64; }

# Quoting for csh-family wrapper scripts
getopt -s tcsh -o 'ab:' -l 'alpha,beta:' -- "$@"

# Retry-friendly: parse subcommand arguments inside a loop
while getops-free; do :; done   # (getopt has no loop mode; parse once, then case)

# Correct eval hygiene: never split $PARSED yourself
PARSED=$(getopt -o 'a' -- "$@")    # ALWAYS capture into one variable
eval set -- "$PARSED"              # then let eval do the splitting

# -u for trusted, space-free input only (script-internal calls)
getopt -u -o 'ab:' -- -a -b x file   #  -a -b x -- file
```

```bash
# Subcommand dispatch: '+' mode keeps 'commit' and everything after it operand-only
ARGS=$(getopt -o '+h' -- "$@"); eval set -- "$ARGS"
sub=$1; shift            # first operand is the subcommand
case "$sub" in commit) ... ;; esac

# Long-option abbreviation: users may type unambiguous prefixes
getopt -o '' -l 'alpha' -- --alph    #  --alpha --   (normalized to the full name)

# Multiple -l options are cumulative (handy for generated grammars)
getopt -o '' -l 'alpha' -l 'beta:' -- --beta 1

# Optional-argument flag emits an EMPTY string when no value was glued
getopt -o '' -l 'color::' -- --color #  --color '' --
# ...so the case branch must treat "$2" = '' as "flag given without value"

# Parse-fail path with custom usage text (-q hides the getopt(3) message)
PARSED=$(getopt -q -o 'o:' -l 'output:' -- "$@") || { usage >&2; exit 64; }
```

## Nuances and Gotchas

- **`-T` is the portability canary.** BSD/macOS `getopt` lacks `-l`, `-s`, and `-o`; `getopt -T` exits 4 on the enhanced version and 0 on the old one. Gate any long-option usage behind it, or your script breaks on macOS in confusing ways.
- **`eval set -- "$PARSED"` is load-bearing.** The whole design assumes you capture output in a *single* variable and let `eval` re-split it; `eval set -- $PARSED` (unquoted) or piping through `xargs` reintroduces the word-splitting bugs getopt exists to fix.
- **Optional arguments (`::`) only attach when glued.** `--color=never` works; `--color never` hands `never` to the next operand. Document it or avoid `::`.
- **Exit codes are part of the contract.** `0` parsed; `1` parse error (unknown option, missing argument — message already on stderr); `4` getopt(3) itself failed (bad optstring, out of memory). A `set -e` script naturally dies on bad input; a polite one catches status 1 to print usage.
- **`-u, --unquoted` is a footgun.** Unquoted output means values with spaces or globs get re-split by the shell. Use it only for controlled, internal input.
- **Error messages go through getopt(3).** With `-q` they vanish (you print your own); `-n "$0"` makes them name your script instead of `getopt`, which users expect.
- **The optstring position needs `--`.** `getopt -o ab: -- "$@"` — without `--`, a user argument like `-o` would be eaten by getopt itself, not your grammar.
- **`getopts` (builtin) vs `getopt` (binary) naming collisions** in docs and autocomplete are a chronic source of bugs; the builtin cannot do long options, so any `getopts -l` attempt is a red flag in review.
- **csh quoting is real, rarely needed.** Wrapper scripts for (t)csh users need `-s csh`; bash/zsh scripts should not set `-s` at all (default is sh-compatible).
- **Abbreviation is a double-edged convenience.** `--alph` normalizes to `--alpha` only while unambiguous; the moment you add `--alphabet`, `--alph` becomes a parse *error* — user scripts that "worked" start failing after you extend the grammar. Pin full names in wrappers around other tools' CLIs.
- **`GETOPT_COMPATIBLE` is an environment booby trap.** Exported by legacy wrappers, it flips the binary into unquoted, old-style behavior and makes `-T` lie (exit 0). A script that "sometimes loses quoting" on one host is often this variable; unset it defensively.
- **Scanning modes change operand placement, not validity.** With a `+` optstring, `cmd file -v` treats `-v` as an operand — scripts that previously permuted args silently change meaning. State the mode you rely on; don't let it default by accident.

## Exit Status

- `0` — arguments parsed successfully (output is the canonical list, unless `-Q`).
- `1` — parse error: unknown option, missing argument, or operand misplaced; an explanatory message was printed to stderr.
- `4` — getopt(3) failure: invalid optstring or internal error; no diagnosis of the user's input is implied.
- `-T` probe mode — `4` when the binary is the enhanced getopt, `0` when it is the old BSD variant.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`flock`](./flock.md) — the other util-linux "shell programming helper".
- [`bash`](../../shell/bash.md) — `eval set --`, arrays, and the `getopts` builtin this tool complements.
- [`xargs`](../../shell/xargs.md) — the other place where quoting rules decide correctness.
- [`man-pages`](../../reference/man-pages.md) — where the getopt(3) optstring grammar is specified.
- [`commands`](../../reference/commands.md) — general command-line reference context.

## Interview Questions

### Q: Why does the standard recipe use `eval set -- "$PARSED"` — and why is eval safe here?

getopt prints arguments already shell-quoted, so `eval` performs exactly one legitimate re-splitting: the quoted values survive as single words. The danger would be `eval set -- $PARSED` (unquoted variable lets eval re-split quoted tokens — actually the reverse: the quoted output *needs* eval, but capturing into one variable prevents the shell from splitting it before eval sees it). The pattern is safe because getopt guarantees the quoting of every token it emits.

### Q: How do you make a script accept both `--color` and `--color=never`?

Declare the long option with an optional argument: `-l 'color::'`. In the case branch, `$2` exists only when the user attached a value; default it: `color="${2:-auto}"`. Note the grammar rule: optional arguments attach only in glued form (`--color=never`, `-cnever`) — `--color never` treats `never` as an operand.

### Q: Your script works on Debian but fails on macOS with "invalid option -- 'l'". What happened and what's the fix?

macOS ships the old BSD getopt(1), which has no `-l/--longoptions` (and no `-s`/`-o`). The fix is to probe with `getopt -T` (exit 4 = enhanced) and either fail with a clear message, fall back to a `getopts` loop, or require GNU getopt via Homebrew. This is the single most common getopt portability bug.

### Q: Compare the getopts builtin and getopt for a script that must parse `-o file` and `--output file`.

`getopts` handles short options only — `-o file` parses fine, but `--output file` must be emulated by hand (or matched as a literal case), and getopts never reorders operands. `getopt -o 'o:' -l 'output:' -- "$@"` handles both, hoists options before operands, and reports errors consistently. The price is an external binary and the eval pattern; POSIX-purists accept getopts, pragmatic scripts use getopt.

### Q: What does exit code 4 mean, and why is it different from 1?

4 signals that getopt(3) — the parsing library — itself failed: typically an invalid optstring (developer bug), not bad user input. 1 signals a parse error in the user's arguments. Distinguishing them lets `set -e` scripts crash on developer bugs while presenting friendly usage text on user errors.

### Q: A reviewer complains your script uses `-u, --unquoted`. What's the concrete risk?

Without quoting, any argument containing spaces, globs, or `$` is re-split and expanded when the caller consumes the output — `--name "a b"` becomes two arguments `a` and `b`, and `--name *` expands to the directory listing. `-u` is only defensible for internal, controlled inputs; user-facing parsing must keep the default quoting.

### Q: How do the `+` and `-` optstring prefixes change parsing, and when do you reach for each?

`+` disables permutation: the first non-option ends option parsing and everything after is an operand — the POSIX/getopts behavior, ideal for `script [global-opts] subcommand [sub-args]` where the subcommand's own flags must not be eaten. `-` keeps permutation but streams non-options back in input order instead of after `--`, which suits filter-style tools where operand position matters (file, then option, then file). Both are documented getopt(1)/getopt(3) features, not extensions — but portable scripts should test for them since the old BSD getopt has neither.

### Q: Your parse silently lost quoting on one host, and `getopt -T` reported exit 0 there. Diagnose.

The host has `GETOPT_COMPATIBLE` exported (or the script fell into the first calling form `getopt optstring parameters`, where the optstring is positional rather than `-o`-declared). Compatible mode makes even the enhanced getopt emit unquoted output and report itself as "old" to `-T`. Fix: invoke via the `-o/--options` form (which also requires `--` before the parameters), and `unset GETOPT_COMPATIBLE` at the top of the script; then re-probe with `-T` expecting 4.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/getopt.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
