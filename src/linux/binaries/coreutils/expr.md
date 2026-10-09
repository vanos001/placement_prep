# expr — evaluate expressions (legacy arithmetic, regex, matching)

## Overview

`expr` evaluates a single expression — arithmetic, string comparison, pattern
matching, substring/index/length operations — and prints the result. It is
the ancestor of shell arithmetic: before `$(( ))` existed (ksh 1980s, POSIX
1992, bash 2.0), `i=$(expr $i + 1)` was *the* way to count in a shell script,
at the price of a fork per increment and a quoting minefield around every
operator.

Debian ships it in `coreutils` at `/usr/bin/expr`. It still works, still
appears in old build scripts,configure.ac fragments, and Makefiles, and
still defines the exit-status semantics that trip up everyone who meets it
fresh: `expr` exits **1** when the expression's value is 0 or null, which
makes `if expr ...` do the opposite of what newcomers expect for zero.

Today its remaining legitimate niches are narrow: POSIX-strict environments
lacking `$(( ))` (which no modern shell is), and its regex-match form
`expr string : pattern` which returns the matched substring length or a
`\(...\)` capture. For arithmetic use `$(( ))`; for matching use bash's
`[[ =~ ]]`, `grep`, or `sed` — covered in the cross-linked pages.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/expr` on modern Debian/Ubuntu |
| First appeared / lineage | PWB/UNIX and 7th Edition UNIX era; GNU expr since early GNU utils |
| Standards | POSIX.1-2018 (`expr`) |

## Synopsis

```
expr EXPRESSION
expr OPTION
```

Main forms:

```bash
expr 3 + 4               # -> 7         (arithmetic)
expr 3 \* 4              # -> 12        (multiplication needs quoting)
expr "a b" : 'a \(.*\)'  # -> b         (regex capture)
expr length hello        # -> 5
expr substr hello 2 3    # -> ell
expr index hello l       # -> 3         (first l is 3rd char)
```

## How It Works

`expr` parses its arguments as one expression grammar with precedence,
evaluates, prints the result, and chooses an exit status by the result's
*type* — the behavior that makes it unique and dangerous. Operators:

| Precedence (low→high) | Operators | Result |
| --- | --- | --- |
| 1 | `\|` | first argument if non-null/nonzero, else second |
| 2 | `&` | first argument if *both* non-null/nonzero, else 0 |
| 3 | `< <= = == != >= >` | 1 or 0 (numeric if both numeric, else string compare) |
| 4 | `+ -` | sum/difference |
| 5 | `* / %` | product/quotient/remainder |
| 6 | `: ` regex match | length of match, or `\(...\)` capture |
| words | `length`, `substr`, `index`, `match` | string ops |

### Arithmetic

```bash
$ expr 3 + 4
7
$ expr 3 + 4 \* 2        # precedence applies: 3 + 8
11
$ expr \( 3 + 4 \) \* 2  # parentheses must be quoted too
14
$ expr 7 / 2             # integer division, truncating
3
$ expr 7 % 2
1
```

Every token is a separate argv entry, which is why each shell metacharacter
(`*`, `(`, `)`, `<`, `>`, `|`, `&`) must be quoted or backslashed — unquoted
`expr 3 * 4` glob-expands the working directory into expr's arguments and
errors out. GNU expr performs arbitrary-precision arithmetic (verified:
`expr 99999999999999999999999999 + 1` prints the full 27-digit result),
removing the old overflow objection, though portable scripts still assume
64-bit at most.

### Comparison and the exit-status design

```bash
$ expr 2 \> 1
1
$ expr 1 \> 2 ; echo "exit=$?"
0
exit=1                   # value 0 → exit status 1
```

The exit contract: **0** if the expression is neither null nor 0; **1** if
the value is null or 0; **2** if the expression is syntactically invalid;
**3** on evaluation errors (e.g. division by zero). This lets 1990s scripts
write `if expr "$a" : '.*' >/dev/null` as a truthiness test — and makes
every modern `result=$(expr ...)` followed by `if [ $? -eq 0 ]` wrong
whenever the *value* zero is legitimate. Separate value from status
explicitly.

### Regex matching with :

```bash
$ expr "a b" : 'a \(.*\)'
b
$ expr abcdef : 'abc'
3                        # length of the anchored match
$ expr abcdef : 'xyz'
0                        # no match: value 0, exit 1
$ expr match abcdef 'abc'
3                        # match is a synonym for ':'
```

The pattern is an *anchored* BRE: it must match from the start of the
string. Without `\(...\)` the result is the match length; with one
parenthesized group the result is the captured text (empty string when the
group didn't participate, still exit 0 if the match itself succeeded).

### String functions

```bash
$ expr length hello
5
$ expr substr hello 2 3      # 1-based positions!
ell
$ expr index hello l         # position of first 'l'
3
```

These predate `${#var}`, `${var:1:3}`, and `${var%%l*}` — all of which are
builtin, fork-free, and the correct choice in any modern shell.

## Options That Matter

`expr` has essentially one flag surface:

| Option | Effect |
| --- | --- |
| `--help` / `--version` | As usual |

Everything else is expression syntax. The "options that matter" are really
the quoting rules:

| Token | Must be quoted? | Why |
| --- | --- | --- |
| `*` | always (`\*`) | glob expansion otherwise |
| `(` `)` | always (`\(`) | shell grouping otherwise |
| `<` `>` `<=` `>=` | always (`\>`) | shell redirection otherwise |
| `|` `&` | always (`\|`, `\&`) | pipeline/AND otherwise |
| `:` | no | not a shell metacharacter |

## Usage Patterns

```bash
# Read legacy scripts: increment the old way
i=0; i=$(expr $i + 1); echo "$i"
```

```bash
# The modern equivalent you should write instead
i=$((i + 1))
```

```bash
# Extract a version major from a dotted string (anchored BRE capture)
v=3.12.1; major=$(expr "$v" : '\([0-9]*\)\.'); echo "$major"
```

```bash
# Same capture with bash builtins — no fork, no BRE quirks
v=3.12.1; major=${v%%.*}
```

```bash
# Numeric comparison in a POSIX-strict script
if expr "$n" \> 10 >/dev/null; then echo big; fi
```

```bash
# Truthiness idiom from old scripts: exit status follows the value
if expr "$comment" : '.' >/dev/null; then echo "non-empty"; fi
```

```bash
# Validate an integer argument the expr way (exit 1 = not numeric)
expr "$1" : '-\{0,1\}[0-9]*$' >/dev/null || { echo "need int" >&2; exit 2; }
```

```bash
# Same validation with case — the preferred POSIX spelling
case $1 in (*[!0-9]*|'') echo "need int" >&2; exit 2;; esac
```

```bash
# Length without forking
len=$(expr length "$s")     # legacy
len=${#s}                   # modern
```

```bash
# Count occurrences of a substring using index in a loop (historical style)
s=hello; pos=$(expr index "$s" l); echo "l at $pos"
```

## Nuances and Gotchas

- **Exit status 1 means "value was 0/null", not "error".** The single most
  quoted expr trap. `v=$(expr "$x" - "$y")` followed by a status check
  breaks exactly when the legitimate answer is zero.
- **Unquoted `*` globs.** `expr 3 * 4` in a directory with files passes
  filenames as operands → syntax error; in an *empty* directory it
  sometimes "works", which makes the bug intermittent. Always `\*`.
- **`+` can be an option-like operand.** Historical exprs choked on
  operands starting with `-`; GNU accepts `expr -5 + 3` but portable
  scripts spell negative numbers carefully (`expr 0 - 5`).
- **`:` patterns are anchored and BRE-only.** No ERE alternation
  `(a|b)`, no `\b`. And a *null* pattern matches everything
  (`expr abc : ''` → 0), another exit-status surprise.
- **Numeric-vs-string comparison is automatic:** `expr 10 = 10.0`
  compares numerically (integers only; 10.0 forces string compare → 0),
  and `expr "10" = 010` is numeric equality (1). Locale-free, but
  precision surprises are real.
- **Division by zero exits 3**, distinct from syntax errors (exit 2) —
  automation checking only `!= 0` lumps them together.
- **Performance:** every expr is a fork+exec; a 1000-iteration loop with
  `expr $i + 1` costs measurable milliseconds where `$(( ))` costs
  microseconds. This is the historical reason shells grew arithmetic.
- **`expr` is for scalars only.** No arrays, no floating point (use `awk`
  or `bc`), no bitwise ops (`$(( ))` has them).

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Expression evaluated to a non-null, non-zero value |
| 1 | Expression evaluated to null or 0 (not an error!) |
| 2 | Invalid expression (syntax) |
| 3 | Evaluation error (e.g. division by zero) |

## Related Commands

- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- [bash](../../shell/bash.md) — `$(( ))` arithmetic and `[[ =~ ]]` regex that replaced expr's two main jobs
- [posix-shell](../../shell/posix-shell.md) — the POSIX shell grammar under the quoting rules expr demands
- [`false`](./false.md) — the other coreutils command whose exit status encodes "false", not "error"

## Interview Questions

### Q: `result=$(expr "$a" - "$b"); [ $? -eq 0 ] && use $result` — under what data does this misbehave, and what is the correct pattern?

Whenever `$a - $b` equals zero (or the expression yields an empty string):
expr prints `0` and exits **1**, the script concludes failure, and the
correct-but-zero result is discarded. Worse, with `set -e` the assignment
kills the script. Correct pattern: capture the value and validate
separately — `result=$(expr ...)` then test the *value* (`[ "$result" -gt 0 ]`)
or use `$((a - b))` which has no value-coupled exit status (its exit is
shell arithmetic success).

### Q: Why does `expr 3 * 4` sometimes work and sometimes explode with a syntax error?

The shell glob-expands the unquoted `*` before expr sees it. In a directory
with at least one file, `*` becomes those filenames and expr receives an
invalid operand list (syntax error, exit 2). In an empty directory the glob
stays literal `*` (no match, no expansion under default nullglob off), so
expr sees `3 * 4` and prints 12. The intermittence is the lesson: shell
expansion happens *before* the command runs, and correct scripts write
`expr 3 \* 4` or `expr 3 '*' 4`.

### Q: What two jobs did expr own historically, and which modern constructs replaced each?

Arithmetic (`expr $i + 1`) was replaced by POSIX shell arithmetic `$(( ))` —
builtin, fork-free, with bitwise ops and shorter syntax — and by `let`/`((...))`
in bash. Pattern matching and substring work (`expr "$s" : '...'`,
`substr`, `index`, `length`) were replaced by parameter expansion
(`${var%%.*}`, `${var:2:3}`, `${#var}`) and, for real regex, bash's
`[[ $var =~ ERE ]]` or grep/sed. Expr survives in configure-era scripts and
as a POSIX-safe fallback where even those constructs are unavailable.

### Q: Explain the anchoring and capture rules of `expr string : pattern` precisely.

The pattern is a Basic Regular Expression that must match starting at the
string's first character (as if `^` were prepended). If it matches and
contains no `\(...\)` group, the result is the *length* of the match. With
exactly one group, the result is the group's captured text (or empty if the
group did not participate — the match still counts). Multiple groups are
not allowed. No match yields 0 — which as a *value* means exit 1, tying
back to the exit-status contract.

### Q: You inherit a 5000-line script full of `expr` arithmetic. What are the migration risks of mechanically converting to `$(( ))`?

Three classes: (1) semantics of the operators — expr's `|` and `&` return
*operand values* (first non-null/nonzero), while `$(( ))`'s `|`/`&` are
bitwise, so blind conversion flips logic; (2) exit-status coupling — some
legacy control flow deliberately relies on expr's status-as-truthiness and
will invert behavior; (3) word splitting and quoting differences —
expressions inside `$(( ))` need no quoting of `*` and `(`, but embedded
variable names previously passed as separate argv words may reference
undefined names that expr treated as 0 and bash arithmetic also treats as
0 — until the variable is an environment variable, where they diverge.
Convert with tests, not sed.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/expr.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
