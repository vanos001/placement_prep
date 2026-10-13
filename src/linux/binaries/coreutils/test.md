# test / [ — evaluate conditional expressions

## Overview

`test` evaluates a condition — file types and permissions, string
comparisons, integer comparisons — and reports the answer through its exit
status: 0 for true, 1 for false. Nothing is printed. Together with the
shell's `if`, `&&`, and `||`, this exit-status-as-boolean contract is the
foundation of every decision a shell script makes.

`[` is not a different program: it is `test` under an alternative name,
distinguished only by the requirement that its last argument must be the
literal `]`, which exists purely for visual balance. Both exist twice on a
Linux system: as a shell builtin (bash, dash, busybox ash all have one) and
as a real binary at `/usr/bin/test` and `/usr/bin/[` from the Debian
`coreutils` package. The builtin always wins when you type `test` or `[` in
a shell; the binary matters for `#!/bin/sh` portability edge cases and for
programs that `execve` it directly.

`[[ ... ]]` is a *different* construct: a bash/ksh/zsh keyword with relaxed
quoting rules, pattern matching, and `&&`/`||` inside the brackets. It is
not in POSIX, and this page treats it as the shell-flavoured sibling of
POSIX `test`.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) for `/usr/bin/test` and `/usr/bin/[` |
| Section (man) | 1 |
| Path | `/usr/bin/test`, `/usr/bin/[` (plus shell builtins) |
| First appeared / lineage | Unix v7 (1979); `[` spelling the same era |
| Standards | POSIX.1-2017 (`test` and `[`); `[[ ]]` is not standardized |

## Synopsis

```text
test EXPRESSION
test
[ EXPRESSION ]
[ ]
```

```bash
test -f /etc/passwd           # file test
[ "$name" = root ]            # the bracket spelling (needs the final ])
[ -z "$1" ] && usage          # gate on a missing argument
[ $# -eq 0 ] || { ...; }      # numeric arity check
```

## How It Works

`test` is defined almost entirely by its **exit status** and by an
**argument-count grammar**. Understanding the grammar explains nearly every
surprising error message.

```text
#  exit status carries the boolean:
#      0  → true         1  → false         2  → syntax error
#
#  the POSIX argument-count algorithm:
┌─────────────────────────────────────────────────────────────┐
│ 0 args   → false (exit 1)                                   │
│ 1 arg    → true iff the argument is non-empty               │
│ 2 args   → "!" negates; otherwise unary op on $2            │
│ 3 args   → binary op: $1 OP $3 (with ! and ( ) handled)     │
│ 4+ args  → implementation-defined; -a/-o algorithms apply   │
└─────────────────────────────────────────────────────────────┘
```

The one-argument rule makes `[ missing ]` *true* (a non-empty string is
true), and the two-argument rule is what `[ ! -d x ]` relies on. The
four-plus argument territory is where quoting accidents land, because
unquoted variables change the argument count:

```bash
$ test; echo $?                # 0 args → false
1
$ test missing; echo $?        # 1 arg, non-empty → true
0
$ VAR="hello world"; [ $VAR = foo ]; echo $?   # 4 args → error
bash: [: too many arguments
2
$ VAR=""; [ $VAR = foo ]; echo $?              # 2 args (=, foo) → error
bash: [: =: unary operator expected
2
$ VAR=""; [ "$VAR" = foo ]; echo $?            # quoted: 3 args, correct
1
```

Operator precedence is `!` (highest), then `-a` (AND), then `-o` (OR), with
parentheses escaped from the shell as `\(` `\)`. `-a` and `-o` are marked
obsolescent by POSIX — modern style combines tests with shell `&&`/`||`
between separate `[ ]` commands:

```bash
# Obsolescent but still working:
[ -f /etc/passwd -a -r /etc/passwd ]
# Preferred:
[ -f /etc/passwd ] && [ -r /etc/passwd ]
# Grouping, when genuinely needed:
[ \( -f a -o -f b \) -a -f c ]
```

Bash's `[[ ]]` keyword relaxes the grammar: no word splitting or glob
expansion of operands, so quoting variables is optional (though still good
practice), `==` does glob pattern matching, `<`/`>` compare lexically
without escaping, and `&&`, `||`, and unescaped `( )` work inside:

```bash
$ [[ 5 > 10 ]]; echo $?        # lexical: "5" sorts after "1..."
0
$ [[ hello == hel* ]]; echo $? # pattern match
0
$ [ 5 \> 10 ]; echo $?         # POSIX: must escape < and > for the shell
0
```

File tests follow `stat(2)`/`access(2)`-family semantics; the file tests
distinguish existence (`-e`), type (`-f`, `-d`, `-L`, ...), non-zero size
(`-s`), and permissions. Numeric comparisons (`-eq`, `-lt`, ...) parse
leading-zero operands as *decimal* — unlike shell arithmetic, where `$((010))`
is octal:

```bash
$ test 010 -eq 10; echo $?     # decimal: 10 == 10
0
$ echo $((010))                # shell arithmetic: octal
8
```

The shell builtin and `/usr/bin/test` share the same core semantics (POSIX
requires it), so behaviour differences are rare — mostly in extras like
bash's `-v VAR` or GNU's `-N`, which are non-portable either way.

## Options That Matter

### File tests

| Option | Effect |
|---|---|
| `-e FILE` | Exists (any type) |
| `-f FILE` | Exists and is a regular file |
| `-d FILE` | Exists and is a directory |
| `-L FILE` | Exists and is a symbolic link (`-h` is the same) |
| `-s FILE` | Exists and has size greater than zero |
| `-r` / `-w` / `-x` | Readable / writable / executable (access(2)-style) |
| `-t FD` | FD is open and refers to a terminal |
| `-p` / `-b` / `-c` / `-S` | FIFO / block device / character device / socket |
| `-O` / `-G` | Owned by (effective) user / group |
| `-nt` / `-ot` / `-ef` | Newer than / older than / same device+inode (GNU) |

### String tests

| Option | Effect |
|---|---|
| `-z STR` | True if the string is empty (zero length) |
| `-n STR` | True if the string is non-empty |
| `S1 = S2` | True if identical (`==` is a bash builtin extra) |
| `S1 != S2` | True if different |
| `S1 < S2` / `S1 > S2` | Lexical comparison; escape as `\<` `\>` inside `[ ]` |

### Numeric tests

| Option | Effect |
|---|---|
| `N1 -eq N2` | Equal |
| `N1 -ne N2` | Not equal |
| `N1 -gt` / `-ge` / `-lt` / `-le` | Greater, greater-or-equal, less, less-or-equal |

Negation and grouping: `!` negates any expression; `\( \)` groups (escaped
in `[ ]`, plain in `[[ ]]`).

## Usage Patterns

```bash
# Gate a script on its argument
[ $# -eq 1 ] || { echo "usage: $0 <file>" >&2; exit 1; }
```

```bash
# Classic file checks before acting
[ -f /etc/hostname ] && echo "host config present"
[ -d /var/log ] || mkdir -p /var/log
```

```bash
# Distinguish "unset" from "empty" is impossible with test —
# but -z covers both, which is usually what you want
[ -z "$CONFIG" ] && CONFIG=/etc/default/app
```

```bash
# The exit-status-as-boolean idiom in one line
[ -w /tmp ] && echo writable || echo "not writable"
```

```bash
# Numeric loop over arguments (arg parsing skeleton)
while [ $# -gt 0 ]; do
    case $1 in
        -v) VERBOSE=1 ;;
        *)  echo "unknown arg: $1" >&2; exit 2 ;;
    esac
    shift
done
```

```bash
# Integer comparison, not lexical: -gt knows 9 < 10
[ "$count" -gt 9 ] && rotate_log
```

```bash
# Lexical version comparison — fast but only safe for equal-format strings
[ "2.10" \< "2.9" ] && echo "lexically true, numerically wrong"
```

```bash
# Terminal check before interactive prompts
[ -t 0 ] && read -r -p "continue? " answer || answer=y
```

```bash
# Same check via the external binary (identical semantics)
/usr/bin/test -t 0 && echo interactive
```

```bash
# Negation and the 1-arg rule biting at the same time
[ ! "" ]; echo $?      # ! of empty-string(false) → 0
[ "" ]; echo $?        # 1 arg, empty → 1
```

```bash
# set -e safety: a failing test as a *condition* is fine,
# a failing standalone [ aborts the script
set -e
[ -f /tmp/lock ] || true          # guarded
if [ -f /tmp/lock ]; then :; fi   # condition position, safe
```

```bash
# Non-zero size vs plain existence: -s catches truncated downloads
[ -s data.tar.gz ] || { rm -f data.tar.gz; echo "download failed" >&2; }
```

```bash
# Compare two files' freshness for build steps (GNU extension)
[ Makefile -nt binary ] && make binary
```

## Nuances and Gotchas

- **Unquoted variables change the argument count.** `[ $var = foo ]` with
  `var="hello world"` becomes a four-argument test: `too many arguments`,
  exit 2. With `var=""` it becomes two arguments: `unary operator expected`,
  also exit 2. Ancient Bourne shells could even evaluate such input as
  *true* instead of erroring. Always quote: `[ "$var" = foo ]`.
- **Missing final bracket is a syntax error, not a false test.**
  `[ -f /tmp/x` without `]` yields `bash: [: missing \`]'` and exit 2 —
  scripts under `set -e` die here. The `]` is an ordinary argument; it must
  be separated by spaces (`[ -f x]` does not work).
- **`<` and `>` are shell redirections.** Inside `[ ]` they must be escaped
  (`[ "$a" \> "$b" ]`) or quoted; unescaped they redirect stdin/stdout and
  the test sees different arguments. `[[ ]]` needs no escaping.
- **String vs numeric operators are not interchangeable.** `[ 5 \< 10 ]`
  compares strings lexically and is *false* ("5" > "1"); `[ 5 -lt 10 ]` is
  the numeric truth. Conversely `-lt` on non-numbers errors.
- **Leading zeros are decimal in test but octal in arithmetic.**
  `test 010 -eq 10` is true; `$((010))` is 8. Version strings with leading
  zeros (`07`) behave differently in the two worlds.
- **`-a`/`-o` are obsolescent** and have precedence surprises; split tests
  into separate `[ ]` commands joined by `&&`/`||`. Note the precedence
  trap: `[ -f a -o -f b -a -x c ]` groups as OR-then-AND, which is rarely
  what the author meant.
- **`[[ ]]` is not POSIX.** Scripts with `#!/bin/sh` (dash) fail on `[[`.
  Use it in bash-only code for pattern matching and unquoted operands;
  keep `[ ]` for anything claiming POSIX portability (see
  [posix-shell](../../shell/posix-shell.md)).
- **`[ -r file ]` under root.** Permission tests use access(2)-style checks;
  for root, `-x` is true if *any* execute bit is set, and ACLs/capabilities
  can make `-r` disagree with an actual successful open.
- **`-e` vs `-f` vs `-s`.** `-e` is true for directories, sockets, and
  broken symlinks' *targets* (`-e` does not see a dangling link; use `-L`
  on the link itself), `-f` only regular files, `-s` only non-empty files.
  Picking the wrong one is a classic off-by-one-type bug.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | The expression is true |
| 1 | The expression is false (including zero-argument `test`) |
| 2 | Syntax error: missing `]`, wrong argument count, unknown operator |

Status 2 is how `[` signals "I could not parse this" — distinct from false,
which matters greatly under `set -e` and in `&&`/`||` chains.

## Related Commands

- [`true`](./true.md) — the unconditional-true building block that shares the exit-status-as-boolean model.
- [`tty`](./tty.md) — `tty -s` and `[ -t 0 ]` are two spellings of the same terminal check.
- [bash](../../shell/bash.md) — `[[ ]]`, arithmetic, and how the shell parses brackets.
- [POSIX shell](../../shell/posix-shell.md) — portable conditionals and why `[[ ]]` is out of scope there.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: What is the difference between `test`, `[`, and `[[`?

`test` and `[` are the same utility (POSIX-specified), with `[` requiring a
final `]` argument for aesthetics; both exist as shell builtins and as
`/usr/bin` binaries with identical core semantics. `[[` is a bash/ksh/zsh
*keyword*, not a command: it parses its operands itself, so no word splitting
or globbing occurs, it supports `&&`, `||`, unescaped parentheses, regex and
glob matching with `=~`/`==`, and lexical `<`/`>` without escaping — but it
is not POSIX and breaks in dash.

### Q: Explain why `[ $var = foo ]` fails and how the failure modes differ.

The shell expands `$var` *before* `test` parses its arguments, so the
argument count changes with the variable. `var="hello world"` produces four
arguments: `too many arguments` (exit 2). `var=""` produces two arguments,
and `test`'s grammar then tries to read `=` as a unary operator:
`unary operator expected` (exit 2). Quoting — `[ "$var" = foo ]` — freezes
the count at three regardless of content, which is the invariant the POSIX
grammar is designed around.

### Q: Why does `[ 5 \> 10 ]` return true while `[ 5 -gt 10 ]` returns false?

`\>` performs a *string* comparison using the current locale's collation:
lexicographically "5" sorts after "10" because "5" > "1". `-gt` performs an
*integer* comparison: 5 < 10. Both are correct for their own domains; the
bug is choosing the string operator for numbers. This is also why escaping
is needed: unescaped `>` inside `[ ]` would be parsed by the shell as a
redirection before `test` ever ran.

### Q: A script does `[ -f "$file" ] && process` under `set -e` and dies when the file is missing. Why, and what are the fixes?

A standalone `[ ... ] && ...` list returns the test's status (1) when the
last executed command in the list fails, and `set -e` treats a non-zero
status outside a condition context as fatal. Fixes: put the test in an `if`
condition (condition contexts are exempt), append `|| true`, or restructure
as `[ -f "$file" ] && process || true` — understanding that `&&`/`||` lists
inherit the last status is the point being probed.

### Q: What does `test` do with zero and one arguments, and why should a script author care?

Zero arguments is false; one argument is true if and only if it is a
non-empty string. This means `[ "$flag" ]` is the idiomatic "is this set to
a non-empty value" test, and it also means accidental one-argument
invocations — `[ "$a" "$b" ]` with an empty variable where an operator
should be — silently test a string instead of erroring. The
argument-count grammar is the mental model that makes every `test`
diagnostic message predictable.

### Q: How would you check "file exists and is non-empty" vs "path exists but is a dangling symlink"?

`[ -s "$f" ]` covers exists-and-non-empty (a plain `-e` would accept a
zero-byte file). For the dangling symlink case, `-e` follows the link and
reports false, while `-L "$f"` inspects the link itself and reports true —
the pair `[ ! -e "$f" ] && [ -L "$f" ]` identifies exactly a broken link.
Knowing that `-e`/`-f`/`-d` dereference while `-L` does not is the tested
skill.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/test.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
