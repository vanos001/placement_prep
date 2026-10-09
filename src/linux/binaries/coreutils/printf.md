# printf — format and print data

## Overview

`printf` writes formatted text: it takes a FORMAT string plus arguments,
consumes conversion directives (`%s`, `%d`, `%f`, ...) from the format to
render each argument, and reuses the format until the argument list is
exhausted. It is the *safe* printing primitive of the shell — unlike
`echo`, its behavior does not change based on what the first argument
looks like, which makes it the only portable way to print variable data.

Two distinct programs share the name: the **bash builtin** (what you get
when you type `printf` interactively — `type -a printf` shows `shell
builtin` first) and the **GNU coreutils binary** at `/usr/bin/printf`
(Debian package `coreutils`), which is what POSIX describes and what
non-bash shells (dash, ksh — though many also have builtins) and `find
-exec`, `xargs`, and `env` would invoke. They agree on the POSIX core
(`%s`, `%d`, `%f`, `%b`, width/precision, escape processing) and diverge
on extensions: `-v VAR`, `%q` quoting style, and positional `%N$`
directives all differ, as detailed below.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) — `/usr/bin/printf` |
| Man section | 1 |
| Path | `/usr/bin/printf` (a bash builtin usually shadows it) |
| First appeared | BSD/System V era (4.3BSD-Reno, System V); C `printf(3)` lineage |
| Standards | POSIX 2018 utility (both builtin and binary aim at it) |

## Synopsis

```
printf FORMAT [ARGUMENT]...
```

Main forms:

```
printf 'hello\n'                 # format only, no arguments
printf '%s is %d years old\n' Alice 30
printf '%s\n' one two three      # format reused per argument
printf '%b\n' 'tab\there'        # expand escapes IN the argument
printf -v var 'x=%d' 5           # builtin only: assign instead of print
```

## How It Works

The engine walks FORMAT left to right. Literal text is copied verbatim
(after backslash-escape processing); each `%` directive converts the next
unused argument. When the arguments run out mid-format, the format is
*restarted* with the next argument batch; when directives outnumber
arguments, missing values render as empty string (for `%s`) or `0` (for
numeric directives) rather than erroring.

```
 FORMAT:  'error in %s: code %d\n'        ARGS: file1 42 file2 7
          ┌────────── pass 1 ─────────┐  ┌────────── pass 2 ─────────┐
 output:  │ error in file1: code 42   │  │ error in file2: code 7    │
          └───────────────────────────┘  └───────────────────────────┘
```

```bash
# Format reuse: one format line, four arguments, two output lines
$ printf '%s|%s\n' one two three four
one|two
three|four

# Missing arguments do not fail: %s -> empty, %d -> 0
$ printf '[%s][%d]\n'
[]][0]
```

### Conversion directives

| Directive | Meaning |
|---|---|
| `%s` | String argument |
| `%b` | String argument *with backslash escapes expanded* (`\n`, `\t`, `\0NNN`) — POSIX |
| `%q` | Argument quoted for shell reuse — extension (styles differ, see below) |
| `%d`, `%i` | Signed decimal integer |
| `%u` | Unsigned decimal |
| `%o`, `%x`, `%X` | Unsigned octal / lowercase hex / uppercase hex |
| `%f`, `%e`, `%g`, `%a` | Floating point (fixed, scientific, compact, hex-float) |
| `%c` | First character of the argument |
| `%%` | A literal percent sign |

### Width, precision, and flags

Between `%` and the letter you may place flags, a field width, and a
precision: `%[-][0][width][.precision]spec`. Width pads (right-align by
default; `-` left-aligns; `0` zero-pads numerics); precision truncates
strings or sets decimal places for floats. `*` takes the width or
precision *from the argument list*.

```bash
$ printf '%-8s|%8s|\n' left right
left    |   right|
$ printf '%.3f\n' 3.14159
3.142
$ printf '%5.2f|\n' 9.999        # rounding can overflow the width
10.00|
$ printf '%10.4s|\n' abcdefgh    # precision truncates, width pads
      abcd|
$ printf '%*d|\n' 5 42           # width 5 taken from an argument
   42|
$ printf '%*.*f\n' 8 3 2.718281828
   2.718
```

### Argument parsing rules for numbers (a classic trap)

Numeric directives use C `strto*` semantics: leading whitespace is
allowed, a leading `0` means **octal**, and `0x` means hexadecimal — for
the *argument*, regardless of the directive:

```bash
$ printf '%d\n' 010              # octal!
8
$ printf '%d\n' 0x1f             # hex accepted
31
$ printf '%d\n' " 42"            # leading whitespace fine
42
$ printf '%d\n' 3.5              # floats rejected for %d...
printf: 3.5: invalid number
3                                # ...but the valid prefix is still printed
$ printf '%u\n' -1               # negative silently wraps to unsigned max
18446744073709551615
```

Out-of-range values print a warning and clamp to the integer limit
(`9223372036854775807` on 64-bit); the GNU binary treats that as an error
(exit 1) while the bash builtin prints the value with only a warning.
Also note `%c` consumes the *first character* of the argument:
`printf '%c\n' 65` prints `6`, not `A`.

### Escapes and `%b`

The FORMAT string always processes escapes: `\n`, `\t`, `\\`, `\NNN`
(octal), `\xHH`, and on modern GNU and bash, `\uHHHH` /
`\UHHHHHHHH` (Unicode):

```bash
$ printf 'A\tB\n' | cat -A
A^IB$
$ printf '\u263A\n'
☺
```

`%b` applies the same processing to the *argument*, which is the POSIX
way to expand escapes stored in variables; `%s` never expands anything —
that distinction is the basis of safe printing.

### Builtin vs /usr/bin/printf: the differences that bite

| Behavior | bash builtin | GNU /usr/bin/printf |
|---|---|---|
| `-v VAR` assignment | Yes: `printf -v v '%d' 5` | Not an option — parsed as a format string, prints `-v`, warns about excess args |
| `%q` output style | Backslash/`$'...'` style: `hello\ world`, `$'a\tb'` | Single-quote style: `'a b'` |
| `%N$` positional directives (`%3$s`) | Not supported — `invalid format character` | Supported: `printf '%5$s\n' a b c d e` → `e` |
| `\u` escapes | Yes (bash 4.2+) | Yes (recent coreutils) |
| Format error exit status | `1` | `1` (write errors can differ) |

```bash
$ printf -v V '[%s]' ok; echo "$V"      # builtin only
[ok]
$ /usr/bin/printf -v V '[%s]' ok        # the binary chokes differently
-v
printf: warning: ignoring excess arguments, starting with 'V'
$ /usr/bin/printf '%5$s\n' a b c d e    # positional args, GNU extension
e
$ printf '%3$s\n' a b c d e             # builtin refuses
bash: printf: `$': invalid format character
```

## Options That Matter

`printf` has almost no options — operands are everything:

| Operand/flag | Effect |
|---|---|
| `FORMAT` | First argument; must contain the directives. A literal `--` before it guards against `-`-leading formats |
| `-v VAR` (builtin) | Store output in shell variable VAR instead of printing — avoids command substitution, preserves trailing newlines |

Everything else — width, precision, flags, escapes — lives inside the
format string. This "no flags" design is deliberate: the format string is
code, the arguments are data, and the two never mix (the core of the
injection-safety argument over `echo`).

## Usage Patterns

```bash
# The safe echo replacement: variable data can never be misread as flags
printf '%s\n' "$untrusted"
```

```bash
# Aligned reports
printf '%-20s %6d %10.2f\n' "$name" "$count" "$price"
```

```bash
# Build a row per record; format reused across the array
printf '%s=%s\n' "${envs[@]}" > env.list
```

```bash
# Zero-padded numbers for sort-friendly filenames
printf 'img%04d.png\n' $(seq 1 12) | head -3
```

```bash
# Shell-safe quoting of arbitrary strings (note the style difference)
printf '%q\n' "hello world"
```

```bash
# Assignment without a subshell — builtin -v keeps it in-process
printf -v ts '%(%Y-%m-%dT%H:%M:%S)T' -1   # bash 4.2+ time format
```

```bash
# Expand escapes that arrived as data (POSIX %b)
printf '%b\n' 'col1\tcol2\nrow1\trow2'
```

```bash
# Progress markers on one line
printf '\r%3d%%' "$pct"
```

```bash
# Debugging with type/precision in one place
printf 'pid=%d rss=%.1fMiB\n' "$pid" "$(awk '/VmRSS/{print $2/1024}' /proc/$pid/status)"
```

```bash
# NUL-separated output for find/xargs -0 pipelines
printf '%s\0' "${files[@]}" | xargs -0 rm --
```

## Nuances and Gotchas

- **`printf "$var"` is the injection bug.** If `$var` contains `%s`, the
  format consumes *other* arguments or garbage; if it contains `%n`-style
  dreams (not in shell) or malformed directives, behavior is undefined.
  Format is code: `printf '%s\n' "$var"` — never interpolate data into
  FORMAT.
- **Missing newline = swallowed output.** `printf 'processing...'` at the
  end of a script or subshell may leave output unterminated and, in some
  capture contexts, dropped. End formats with `\n` unless streaming a
  partial line deliberately.
- **Missing arguments are silent zeros.** `printf '%d-%s\n'` prints
  `0-` and exits 0. Typos in argument lists do not fail loudly; validate
  count for anything critical.
- **Octal/hex argument interpretation.** `printf '%d' 010` is 8, `0777`
  in a permissions script is 511 in decimal terms — same trap as shell
  arithmetic. Use `10#`-style explicitness in arithmetic and raw decimal
  in printf.
- **`%u` of a negative is silent wraparound**, not an error — a quick way
  to print nonsense in log parsers.
- **`%c` takes one character of the string**, and multibyte UTF-8 breaks
  it: `printf '%c\n' é` emits the first *byte*. There is no locale-aware
  character directive in POSIX printf.
- **`-v` is bash-specific.** dash's builtin has no `-v`; scripts under
  `/bin/sh` that use `printf -v` break. Also `/usr/bin/printf` does not
  support `-v` at all (it misparses it as a format).
- **`%q` and `%N$` are extensions** — `%q` in bash and GNU binary (with
  different quoting styles), `%N$` only in the GNU binary (and ksh/zsh
  builtins). Both are absent from strict POSIX and from dash.
- **Very large widths are a resource game.** `printf '%99999999999s\n' x`
  asks for a gigantic buffer; implementations either clamp, fail, or burn
  memory — don't let width/precision come from untrusted input.
- **Exit status nuance.** Format/argument errors exit nonzero (typically
  1); the GNU binary also exits 1 on out-of-range numerics where the bash
  builtin only warns — a subtle difference in strict pipelines using
  `set -e`.

## Exit Status

| Code | Meaning |
|---|---|
| `0` | All output written, format consumed without error (missing args still count as success) |
| `1` | Invalid directive, invalid or out-of-range numeric argument, or write error (GNU binary; builtin may differ on warnings) |
| `>1` | Write failures (e.g. `EPIPE`, full disk) may surface larger codes depending on implementation |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./seq.md`](./seq.md) — its default format is printf syntax (`%.PRECf`/`%g`).
- [`./pathchk.md`](./pathchk.md) — pre-flight validation for names printf emits.
- [`../../shell/bash.md`](../../shell/bash.md) — builtin commands, `-v`, and quoting mechanics.
- [`../../shell/posix-shell.md`](../../shell/posix-shell.md) — which printf features are portable.

`echo` is covered elsewhere in the book and intentionally not linked
from here; this page treats it only as the tool printf replaces.

## Interview Questions

### Q: Why is `printf '%s\n' "$var"` safer than `echo "$var"`?

`echo`'s behavior depends on its arguments: a variable starting with
`-n`/`-e`/`-E` changes flags, backslash sequences are interpreted
differently across bash/dash/`xpg_echo`, and POSIX admits multiple
behaviors — so printing arbitrary data is undefined. `printf` separates
format (code, fixed by the author) from arguments (data, never parsed for
options or escapes with `%s`), giving one deterministic output on every
POSIX shell. That is why style guides mandate printf for variable data.

### Q: What does `printf '%s|%s\n' one two three four` print, and what rule produces it?

`one|two` then `three|four`. The format is reused as long as arguments
remain: printf consumes directives until the argument list is exhausted,
then restarts the format. Corollary: leftover directives without
arguments render as empty string or 0 and *do not* fail —
`printf '%d\n'` prints `0` — so argument-count typos fail silently.

### Q: Explain `printf '%d\n' 010` printing 8.

Numeric arguments are parsed with C `strto*` semantics: a leading `0`
means octal, `0x` means hex. `010` is therefore 8. The same rule bites
in shell arithmetic and in code that treats file-mode strings as decimal.
Both the bash builtin and GNU binary share this behavior; to be explicit,
pass decimal-only values or normalize first.

### Q: Where do the bash builtin and /usr/bin/printf differ in practice?

Three visible places: `-v VAR` exists only in the builtin (the binary
parses `-v` as a format and warns about excess arguments); `%q` quotes
differently (bash: backslash/`$'...'` style; GNU: single-quote style);
and positional `%N$` directives work in the GNU binary but are rejected
by bash's builtin. For strict POSIX scripts, stick to `%s %d %f %b` and
escape processing in FORMAT, which both implement identically.

### Q: What is %b for, and how is it different from %s?

`%b` interprets backslash escapes *inside the argument* (`\n`, `\t`,
octal/hex escapes) — the POSIX-sanctioned way to expand escape sequences
that arrived as data, e.g. from a file or another program. `%s` never
touches backslashes. So `printf '%s\n' 'a\tb'` prints a literal `a\tb`,
while `printf '%b\n' 'a\tb'` prints a tab. It is also the portable
replacement for `echo -e`, whose flag support is not portable.

### Q: How do width, precision, and `*` interact in `printf '%*.*f\n' 8 3 2.718281828`?

The `*` placeholders pull their values from the argument list in order:
width 8, precision 3, then the value — yielding `   2.718` (three
decimals, right-aligned in 8 columns). Flags still apply (`%-8.3f`
left-aligns, `%08.3f` zero-pads). Star widths are POSIX and the standard
trick for column widths that are only known at runtime — but never let
untrusted data supply them, since huge widths allocate huge buffers.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/printf.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — printf](https://pubs.opengroup.org/onlinepubs/9699919799/)
