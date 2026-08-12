# POSIX Shell

## Introduction

POSIX shell refers to the command language interpreter specified by the POSIX standard (IEEE Std 1003.1). Writing POSIX-compliant shell scripts ensures portability across different UNIX-like systems and shell implementations. This chapter covers the mandated features, common pitfalls when writing portable scripts, and the differences between POSIX shell and Bash.

## POSIX Shell Standard

The POSIX Shell Command Language is defined in IEEE Std 1003.1-2017, Chapter 2 (Shell Command Language). It specifies a minimal set of features that all compliant shells must support.

### Compliant Shells

| Shell | POSIX Compliant | Notes |
|---|---|---|
| dash | ✅ Strict | Default `/bin/sh` on Debian/Ubuntu |
| bash | ✅ (in POSIX mode) | `bash --posix` or `sh` invocation |
| ash | ✅ Strict | BusyBox ash, lightweight |
| ksh | ✅ | KornShell, basis for many features |
| zsh | Mostly | Some differences in word splitting |
| fish | ❌ | Deliberately non-POSIX |

### Checking POSIX Compliance

```bash
# Run bash in POSIX mode
bash --posix

# Check script with checkbashisms (from devscripts)
sudo apt install devscripts
checkbashisms myscript.sh

# Use shellcheck for broader analysis
shellcheck -s sh myscript.sh
```

## Mandated Language Features

### Shell Grammar

POSIX defines these compound commands:

```sh
# If/elif/else
if command1; then
    commands
elif command2; then
    commands
else
    commands
fi

# For loop
for name in word1 word2 word3; do
    commands
done

# For without word list (uses "$@")
for name; do
    commands
done

# While/until
while command; do
    commands
done

until command; do
    commands
done

# Case
case word in
    pattern1) commands ;;
    pattern2) commands ;;
    *)        commands ;;
esac

# Grouping
{ commands; }

# Subshell
(commands)

# Function definition
fname() { commands; }
```

### Variable Assignment and Expansion

```sh
# Assignment (no spaces around =)
var=value
VAR="string with spaces"

# Expansion
echo "$var"
echo "${var}"
echo "${var:-default}"     # Default if unset or null
echo "${var:=default}"     # Assign default if unset or null
echo "${var:+alternate}"   # Alternate if set and non-null
echo "${var:?error}"       # Error if unset or null

# String length
echo "${#var}"

# Substring (POSIX, but poorly supported in dash)
echo "${var#pattern}"      # Remove shortest prefix
echo "${var##pattern}"     # Remove longest prefix
echo "${var%pattern}"      # Remove shortest suffix
echo "${var%%pattern}"     # Remove longest suffix

# Pattern substitution (NOT POSIX — Bash/Zsh only)
echo "${var/pattern/replacement}"  # NOT POSIX
```

### Special Parameters

```sh
$@      # All positional parameters (each as separate word)
$*      # All positional parameters (as single word when unquoted)
$#      # Number of positional parameters
$?      # Exit status of last command
$-      # Current shell options
$$      # PID of current shell
$!      # PID of last background command
$0      # Name of shell or script
$1-$9   # Positional parameters 1-9
${10}   # Positional parameters ≥ 10
```

### Quoting

```sh
# Single quotes: no interpretation
echo 'Hello $USER'      # Prints: Hello $USER

# Double quotes: variable expansion, command substitution
echo "Hello $USER"      # Prints: Hello john

# Backslash: escape single character
echo "Hello \"World\""  # Prints: Hello "World"

# In double quotes, these are special:
# $  `  \  "  (only)
# Globbing does NOT happen inside double quotes
echo "*.txt"            # Prints: *.txt (no expansion)
echo *.txt              # Expands to matching files
```

### Command Substitution

```sh
# POSIX: backtick syntax
result=`command`

# Also POSIX: $(command) — preferred, nestable
result=$(command)

# Nesting
outer=$(echo $(inner_cmd))
# vs backtick (needs escaping)
outer=`echo \`inner_cmd\``
```

## Built-in Commands (Mandatory)

POSIX mandates these built-in commands:

```sh
# Required builtins
. (source)   # Execute file in current shell
:            # No-op, always returns 0
break        # Exit for/while/until loop
cd           # Change directory
continue     # Skip to next loop iteration
eval         # Evaluate arguments as command
exec         # Replace shell with command
exit         # Exit shell
export       # Mark variables for export
readonly     # Mark variables as read-only
return       # Return from function
set          # Set shell options and positional params
shift        # Shift positional parameters
times        # Print shell and children CPU times
trap         # Set signal handlers
umask        # Set file creation mask
unset        # Remove variables or functions
```

### Test and [

```sh
# POSIX test (also available as [ command)
test -f /etc/passwd
[ -f /etc/passwd ]

# File tests
[ -f file ]      # File exists and is regular
[ -d dir ]       # Directory exists
[ -e path ]      # Path exists
[ -r file ]      # File is readable
[ -w file ]      # File is writable
[ -x file ]      # File is executable
[ -s file ]      # File has non-zero size
[ -L file ]      # File is a symlink

# String tests
[ -z "$var" ]    # String is empty
[ -n "$var" ]    # String is non-empty
[ "$a" = "$b" ]  # Strings are equal
[ "$a" != "$b" ] # Strings are not equal

# Numeric tests
[ "$a" -eq "$b" ]  # Equal
[ "$a" -ne "$b" ]  # Not equal
[ "$a" -gt "$b" ]  # Greater than
[ "$a" -lt "$b" ]  # Less than
[ "$a" -ge "$b" ]  # Greater or equal
[ "$a" -le "$b" ]  # Less or equal

# Combining tests
[ "$a" = "x" ] && [ "$b" = "y" ]  # AND
[ "$a" = "x" ] || [ "$b" = "y" ]  # OR
[ ! -f file ]                      # NOT
```

### Arithmetic

```sh
# POSIX arithmetic expansion
echo $((1 + 2))         # 3
echo $(($a * $b))       # Multiplication
echo $((a + b))         # Variables without $ inside $(( ))

# No floating point support in POSIX
# Use awk or bc for floating point
result=$(echo "scale=2; 3.14 * 2" | bc)
result=$(awk 'BEGIN { printf "%.2f", 3.14 * 2 }')

# Increment (POSIX way, no ++ operator)
i=$((i + 1))
```

## Non-POSIX Bash Features

### Arrays (NOT POSIX)

```bash
# Bash
arr=("one" "two" "three")
echo ${arr[0]}          # one
echo ${arr[@]}          # one two three
echo ${#arr[@]}         # 3

# POSIX equivalent using positional parameters
set -- "one" "two" "three"
echo "$1"               # one
echo "$@"               # one two three
echo "$#"               # 3
```

### [[ ]] (NOT POSIX)

```bash
# Bash
[[ -f file && -r file ]]
[[ "$str" == pattern* ]]    # Pattern matching
[[ "$str" =~ regex ]]       # Regex matching

# POSIX
[ -f file ] && [ -r file ]
case "$str" in pattern*) true;; esac  # Pattern matching
# No regex equivalent
```

### Process Substitution (NOT POSIX)

```bash
# Bash
diff <(cmd1) <(cmd2)

# POSIX equivalent: use temporary files
cmd1 > /tmp/out1
cmd2 > /tmp/out2
diff /tmp/out1 /tmp/out2
rm -f /tmp/out1 /tmp/out2
```

### Brace Expansion (NOT POSIX)

```bash
# Bash
echo {1..10}                    # 1 2 3 4 5 6 7 8 9 10
echo file{1,2,3}.txt            # file1.txt file2.txt file3.txt
echo {a..z}                     # a b c ... z

# POSIX: use seq or loops
seq 1 10
for i in $(seq 1 10); do echo $i; done
```

### Associative Arrays (NOT POSIX)

```bash
# Bash 4+
declare -A map
map[name]="John"
map[age]="30"
echo ${map[name]}

# POSIX: use grep/sed on a "database"
get_value() {
    echo "$DB" | grep "^$1=" | cut -d= -f2
}
DB="name=John
age=30"
get_value name
```

### Here Strings (NOT POSIX)

```bash
# Bash
read -r line <<< "hello world"

# POSIX: use echo and pipe
echo "hello world" | read -r line
# Note: read in pipe runs in subshell, variable not available
# Fix: use a here document
read -r line <<EOF
hello world
EOF
```

### String Operations (NOT POSIX)

```bash
# Bash
${var,,}     # Lowercase — NOT POSIX
${var^^}     # Uppercase — NOT POSIX
${var:0:5}   # Substring — NOT POSIX
${var/pat/rep}  # Replace — NOT POSIX

# POSIX equivalents
echo "$var" | tr '[:upper:]' '[:lower:]'  # Lowercase
echo "$var" | tr '[:lower:]' '[:upper:]'  # Uppercase
expr substr "$var" 1 5                     # Substring (limited)
echo "$var" | sed "s/pat/rep/"             # Replace
```

## Portable Scripting Best Practices

### Shebang

```sh
#!/bin/sh
# This should work on any POSIX system

#!/usr/bin/env sh
# More portable if sh is not in /bin
```

### Strict Mode

```sh
#!/bin/sh
set -eu  # Exit on error, error on unset variables
# Note: set -o pipefail is NOT POSIX
# Use separate checks for pipelines

# Portable pipefail check:
cmd1 | cmd2 || exit_code=$?
# Only checks cmd2's exit status
```

### Variable Quoting

```sh
# ALWAYS quote variables
echo "$var"         # Correct
echo $var           # WRONG: word splitting + globbing

# Special case: word splitting is intentional
for item in $list; do  # Intentional splitting
    echo "$item"
done

# But prefer:
for item in $list; do  # Still needs quoting in loop body
    echo "$item"
done
```

### Function Definitions

```sh
# POSIX function syntax (preferred)
myfunc() {
    echo "Hello, $1"
}

# Also POSIX but less portable in practice
function myfunc {   # "function" keyword is NOT POSIX
    echo "Hello, $1"
}

# Always use: name() { body; }
```

### Signal Handling

```sh
# POSIX signal handling
trap 'cleanup' EXIT        # On shell exit
trap 'cleanup' INT TERM    # On interrupt/terminate
trap '' INT                # Ignore interrupt
trap - INT                 # Reset to default

# Cleanup pattern
cleanup() {
    rm -f "$tmpfile"
}
trap cleanup EXIT
tmpfile=$(mktemp) || exit 1
```

### Temporary Files

```sh
# Portable temp file creation
tmpfile=$(mktemp) || exit 1
trap 'rm -f "$tmpfile"' EXIT

# Or with template
tmpfile=$(mktemp /tmp/myapp.XXXXXX) || exit 1
```

## dash: The Reference POSIX Shell

### Why dash?

- Extremely fast startup (~2ms vs ~40ms for bash)
- Strict POSIX compliance
- Used as `/bin/sh` on Debian/Ubuntu
- Ideal for system scripts

### dash Limitations

```sh
# dash does NOT support:
# - Arrays
# - [[ ]]
# - (( )) arithmetic
# - {a,b,c} brace expansion
# - $'...' ANSI-C quoting
# - ${var/pat/rep} pattern substitution
# - <(process substitution)
# - $RANDOM
# - read -p "prompt" (use printf + read)
# - local arrays
# - function keyword
# - &> redirect
```

### Testing with dash

```bash
# Run your script with dash to test portability
dash myscript.sh

# Or set /bin/sh to dash temporarily
sudo dpkg-reconfigure dash  # Choose "yes" to use dash as /bin/sh
```

## Common Pitfalls

### 1. Word Splitting

```sh
# WRONG: word splitting on $files
files="file1.txt file2.txt"
cat $files              # Might work, but fragile

# CORRECT: iterate properly
for f in $files; do
    cat "$f"
done
```

### 2. Globbing in Variables

```sh
# WRONG: glob expansion
pattern="*.txt"
ls $pattern             # Expands *.txt

# CORRECT: use find
find . -name "*.txt"
```

### 3. echo vs printf

```sh
# echo behavior varies across systems
echo -e "hello\n"       # -e not POSIX
echo "hello\n"          # May print literal \n

# printf is portable
printf "hello\n"
printf "Name: %s\n" "$name"
```

### 4. Command Substitution Stripping

```sh
# Command substitution strips trailing newlines
result=$(echo "hello

")
# result is "hello", not "hello\n\n"

# Preserve with quoting
result="$(cat file)"
```

### 5. Test String Comparisons

```sh
# WRONG: missing quotes
[ $var = "hello" ]      # Fails if $var is empty

# CORRECT: always quote
[ "$var" = "hello" ]
```

## Portable Script Template

```sh
#!/bin/sh
# POSIX-compliant script template
# Usage: script.sh [OPTIONS] ARGUMENTS

set -eu

# Constants
PROGNAME=$(basename "$0")
TMPDIR="${TMPDIR:-/tmp}"

# Functions
usage() {
    printf "Usage: %s [OPTIONS] ARGUMENTS\n" "$PROGNAME"
    printf "  -h    Show this help\n"
    printf "  -v    Verbose output\n"
}

log() {
    printf "%s: %s\n" "$PROGNAME" "$*" >&2
}

error() {
    log "ERROR: $*"
    exit 1
}

cleanup() {
    # Clean up temp files
    rm -f "${tmpfile:-}" 2>/dev/null || true
}
trap cleanup EXIT

# Parse options
verbose=0
while getopts "hv" opt; do
    case "$opt" in
        h) usage; exit 0 ;;
        v) verbose=1 ;;
        *) usage; exit 1 ;;
    esac
done
shift $((OPTIND - 1))

# Validate arguments
[ $# -ge 1 ] || error "Missing required argument"

# Main logic
main() {
    tmpfile=$(mktemp "${TMPDIR}/myapp.XXXXXX") || error "Cannot create temp file"

    [ "$verbose" -eq 1 ] && log "Processing $1"

    # ... do work ...

    log "Done"
}

main "$@"
```

## Portability Testing

### Testing Tools

```bash
# checkbashisms (from devscripts)
sudo apt install devscripts
checkbashisms myscript.sh
# Warns about Bash/Zsh-specific features

# shellcheck
shellcheck -s sh myscript.sh
# Catches many portability issues

# Run with dash (strict POSIX)
dash myscript.sh

# Run with different shells
for sh in bash dash ksh ash; do
    echo "Testing with $sh:"
    $sh myscript.sh
done
```

### Common Portability Issues

| Issue | Bash | POSIX |
|---|---|---|
| Arrays | `arr=(a b c)` | Use positional params `set -- a b c` |
| `[[ ]]` | `[[ -f file ]]` | `[ -f file ]` |
| `(( ))` arithmetic | `((x++))` | `x=$((x + 1))` |
| `$RANDOM` | Built-in | `awk 'BEGIN{srand(); print int(rand()*32768)}'` |
| `read -p` | `read -p "prompt"` | `printf "prompt"; read var` |
| `${var,,}` | Lowercase | `echo "$var" | tr '[:upper:]' '[:lower:]'` |
| `${var:0:5}` | Substring | `expr substr "$var" 1 5` |
| `${var/pat/rep}` | Replace | `echo "$var" | sed 's/pat/rep/'` |
| `<()` process subst | `diff <(a) <(b)` | Temp files |
| `&>` redirect | `cmd &> file` | `cmd > file 2>&1` |
| `$'...'` ANSI-C | `echo $'\n'` | `printf '\n'` |
| `{a,b,c}` brace | `echo {1..10}` | `seq 1 10` or loop |
| `select` menu | Built-in | Implement manually |
| `function` keyword | `function f {` | `f() {` |

### Script Portability Checklist

- [ ] Shebang: `#!/bin/sh`
- [ ] No `[[ ]]` — use `[ ]`
- [ ] No `(( ))` — use `$(( ))` or `expr`
- [ ] No arrays — use positional parameters
- [ ] No `${var/pat/rep}` — use `sed`
- [ ] No `${var,,}` — use `tr`
- [ ] No `$RANDOM` — use `awk` or `/dev/urandom`
- [ ] No `<()` process substitution — use temp files
- [ ] No `&>` — use `> file 2>&1`
- [ ] No `$'...'` ANSI-C quoting — use `printf`
- [ ] No brace expansion — use `seq` or loops
- [ ] No `function` keyword — use `name() {`
- [ ] No `read -p` — use `printf` + `read`
- [ ] Quote all variables: `"$var"` not `$var`
- [ ] Use `printf` instead of `echo` for portability
- [ ] Test with `dash` or `checkbashisms`

## References

- [POSIX Shell Command Language](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html)
- [POSIX.1-2017 Specification](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [dash(1) man page](https://man7.org/linux/man-pages/man1/dash.1.html)
- [ShellCheck](https://www.shellcheck.net/) — static analysis for shell scripts
- [checkbashisms](https://manpages.debian.org/bookworm/devscripts/checkbashisms.1.en.html)
- [Greg's Wiki - Bashism](https://mywiki.wooledge.org/Bashism)
- [Rich's sh (POSIX shell) tricks](https://www.etalabs.net/sh_tricks.html)
- [POSIX Shell Grammar](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_10)

## Further Reading

- [The Debian Policy on Shell Scripts](https://www.debian.org/doc/debian-policy/ch-scripts.html)
- [Alpine Linux ash documentation](https://wiki.alpinelinux.org/wiki/Alpine_Linux:FAQ)
- [Ubuntu dash as /bin/sh](https://wiki.ubuntu.com/DashAsBinSh)

## Related Topics

- [Shell Overview](./overview.md) — shell types and fundamentals
- [Bash](./bash.md) — the most common Linux shell
- [Zsh](./zsh.md) — extended shell with POSIX compatibility mode
- [Fish](./fish.md) — deliberately non-POSIX shell
- [grep](./grep.md) — POSIX-compatible text search
- [find](./find.md) — portable file search
