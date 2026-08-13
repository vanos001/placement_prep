# Shell Scripting Fundamentals

Shell scripting is the art of combining Unix commands into reusable programs executed by a shell interpreter. This chapter covers the foundational constructs every Linux administrator and developer needs to master: variables, conditionals, loops, functions, quoting rules, globbing patterns, and exit codes. These concepts apply across POSIX shells (sh, dash, bash, ksh, zsh) with Bash-specific extensions noted where relevant.

## Anatomy of a Shell Script

Every shell script begins with a shebang line that specifies the interpreter:

```bash
#!/bin/bash
# This is a comment
echo "Hello, World!"
```

The shebang (`#!`) tells the kernel which interpreter to use. Common choices:

| Shebang | Use Case |
|---------|----------|
| `#!/bin/bash` | Bash-specific scripts |
| `#!/bin/sh` | POSIX-compliant, portable scripts |
| `#!/usr/bin/env bash` | Portable Bash invocation |
| `#!/usr/bin/env python3` | Python scripts |

### Making Scripts Executable

```bash
chmod +x script.sh       # Make executable
./script.sh               # Run directly
bash script.sh            # Run with explicit interpreter
source script.sh          # Run in current shell
. script.sh               # POSIX equivalent of source
```

### Script Structure Template

```bash
#!/bin/bash
set -euo pipefail

# === Configuration ===
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly VERSION="1.0.0"

# === Functions ===
usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] FILE

Options:
  -h, --help     Show this help
  -v, --verbose  Verbose output
  -o, --output   Output file (default: stdout)
EOF
}

log() {
    printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

die() {
    log "ERROR: $*"
    exit 1
}

cleanup() {
    rm -f "$TEMP_FILE"
}

# === Main ===
trap cleanup EXIT
TEMP_FILE=$(mktemp)

# Parse arguments
VERBOSE=0
OUTPUT=""
while getopts "hvo:" opt; do
    case "$opt" in
        h) usage; exit 0 ;;
        v) VERBOSE=1 ;;
        o) OUTPUT="$OPTARG" ;;
        *) usage; exit 1 ;;
    esac
done
shift $((OPTIND - 1))

# Validate
[[ $# -ge 1 ]] || die "Missing required argument: FILE"
[[ -f "$1" ]] || die "File not found: $1"

# Process
log "Processing $1"
# ... main logic ...
```

## Variables

### Variable Assignment and Access

```bash
# Assignment (NO spaces around =)
name="Alice"
count=42
path="/usr/local/bin"

# Access (prefix with $)
echo "$name"
echo "$count files found"

# Braces for disambiguation
prefix="file"
echo "${prefix}_name.txt"    # file_name.txt
echo "$prefix_name.txt"      # empty! looks for $prefix_name
```

### Variable Scope

```bash
# Global by default
global_var="I'm global"

my_function() {
    # Local variable (Bash/ksh)
    local local_var="I'm local"
    
    # POSIX-compliant alternative (limited)
    # No 'local' in pure POSIX sh; use subshells instead
    
    echo "Inside: $global_var"   # accessible
    echo "Inside: $local_var"    # accessible
}

my_function
echo "Outside: $global_var"  # accessible
echo "Outside: $local_var"   # undefined/empty
```

### Environment Variables

```bash
# Export to child processes
export MY_VAR="visible"

# Or assign and export separately
MY_VAR="value"
export MY_VAR

# Unexport (remove from environment, keep as shell variable)
export -n MY_VAR

# View all environment variables
env
printenv
export -p
```

### Special Variables

```bash
$0          # Script name
$1, $2, ... # Positional parameters
$#          # Number of arguments
$@          # All arguments (as separate words)
$*          # All arguments (as single word when quoted)
$?          # Exit status of last command
$$          # PID of current shell
$!          # PID of last background command
$-          # Current shell flags
$_          # Last argument of previous command
```

### `$@` vs `$*` — Critical Difference

```bash
#!/bin/bash
# demo_args.sh

echo "--- Unquoted ---"
for arg in $@; do echo "  [$arg]"; done

echo "--- Quoted with @ ---"
for arg in "$@"; do echo "  [$arg]"; done

echo "--- Quoted with * ---"
for arg in "$*"; do echo "  [$arg]"; done

# Running: ./demo_args.sh "hello world" "foo bar"
# Unquoted: [hello] [world] [foo] [bar]
# "$@":     [hello world] [foo bar]     ← preserves separate arguments
# "$*":     [hello world foo bar]       ← merges into one string
```

### Readonly Variables

```bash
readonly PI=3.14159
declare -r CONFIG_FILE="/etc/myapp.conf"

PI=3.14     # bash: PI: readonly variable
```

## Conditionals

### `if` / `elif` / `else`

```bash
if [[ -f "/etc/passwd" ]]; then
    echo "File exists"
elif [[ -d "/etc" ]]; then
    echo "Directory exists, but file doesn't"
else
    echo "Neither exists"
fi
```

### Test Conditions

#### File Tests

```bash
[[ -e "$file" ]]    # exists
[[ -f "$file" ]]    # regular file
[[ -d "$dir" ]]     # directory
[[ -L "$link" ]]    # symbolic link
[[ -r "$file" ]]    # readable
[[ -w "$file" ]]    # writable
[[ -x "$file" ]]    # executable
[[ -s "$file" ]]    # non-empty
[[ -p "$pipe" ]]    # named pipe (FIFO)
[[ -S "$sock" ]]    # socket
[[ -b "$dev" ]]     # block device
[[ -c "$dev" ]]     # character device

[[ "$file1" -nt "$file2" ]]  # newer than
[[ "$file1" -ot "$file2" ]]  # older than
```

#### String Tests

```bash
[[ -z "$str" ]]        # empty string
[[ -n "$str" ]]        # non-empty string
[[ "$a" == "$b" ]]     # equal
[[ "$a" != "$b" ]]     # not equal
[[ "$a" < "$b" ]]      # lexicographic less than
[[ "$a" > "$b" ]]      # lexicographic greater than

# Pattern matching (Bash)
[[ "$file" == *.txt ]]        # glob pattern
[[ "$str" =~ ^[0-9]+$ ]]     # regex match (Bash 3.0+)

# Case-insensitive matching (Bash 4.0+)
shopt -s nocasematch
[[ "Hello" == "hello" ]]      # true
shopt -u nocasematch
```

#### Arithmetic Tests

```bash
[[ $a -eq $b ]]    # equal
[[ $a -ne $b ]]    # not equal
[[ $a -lt $b ]]    # less than
[[ $a -le $b ]]    # less than or equal
[[ $a -gt $b ]]    # greater than
[[ $a -ge $b ]]    # greater than or equal

# Arithmetic context (Bash) — C-like syntax
(( a == b ))
(( a != b ))
(( a < b ))
(( a > b ))
(( a <= b ))
(( a >= b ))
(( a % 2 == 0 ))   # even check
```

### `[[ ]]` vs `[ ]` vs `test`

```bash
# [ ] is POSIX, same as 'test'
[ -f "$file" ] && echo "exists"

# [[ ]] is Bash/Zsh, more powerful
# Advantages:
# - No word splitting on variables
# - Pattern matching with == and =~
# - Logical operators && || inside
# - No need to quote variables for empty check

# Safe comparison with [[ ]]
[[ -z "$var" ]]           # safe even if $var is empty
[ -z "$var" ]             # safe, but...
[ -z $var ]               # DANGEROUS if $var is empty!
# Becomes: [ -z ] which evaluates to true for wrong reason

# Pattern matching (only in [[ ]])
[[ "$filename" == *.tar.gz ]] && echo "tarball"

# Regex matching (only in [[ ]])
[[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]
```

### `case` Statement

```bash
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        start_service
        ;;
    status)
        check_status
        ;;
    --help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1" >&2
        exit 1
        ;;
esac

# Pattern matching in case
case "$filename" in
    *.tar.gz|*.tgz)    echo "gzip tarball" ;;
    *.tar.bz2|*.tbz2)  echo "bzip2 tarball" ;;
    *.tar.xz|*.txz)    echo "xz tarball" ;;
    *.zip)              echo "zip archive" ;;
    *.rpm)              echo "RPM package" ;;
    *.deb)              echo "Debian package" ;;
    *)                  echo "Unknown type" ;;
esac

# Fall-through with ;& (Bash 4.0+)
case "$num" in
    1)  echo "one" ;;&
    *)  echo "number" ;;
esac
# Input 1 prints: "one" then "number"

# Fall-through with ;;& (Bash 4.0+)
case "$str" in
    *test*)  echo "contains test" ;;&
    *demo*)  echo "contains demo" ;;&
    hello*)  echo "starts with hello" ;;
esac
```

### Logical Operators

```bash
# AND (&&) — short-circuit
[[ -f "$file" ]] && [[ -r "$file" ]] && cat "$file"

# OR (||) — short-circuit
[[ -d "$dir" ]] || mkdir -p "$dir"

# NOT (!)
[[ ! -f "$file" ]] && echo "File doesn't exist"

# Combining with grouping
if [[ $age -ge 18 && $age -le 65 ]]; then
    echo "Working age"
fi

# Ternary-like pattern
[[ $count -gt 0 ]] && echo "positive" || echo "zero or negative"
# WARNING: this is NOT a true ternary! If echo "positive" fails,
# the || branch also executes. Use if/else for critical logic.
```

## Loops

### `for` Loops

```bash
# List form
for name in Alice Bob Charlie; do
    echo "Hello, $name"
done

# Glob expansion
for file in *.txt; do
    [[ -f "$file" ]] || continue  # skip if no matches
    echo "Processing $file"
done

# C-style for loop (Bash)
for ((i = 0; i < 10; i++)); do
    echo "$i"
done

# Brace expansion (Bash)
for i in {1..10}; do
    echo "$i"
done

# With step
for i in {0..100..5}; do
    echo "$i"    # 0, 5, 10, ..., 100
done

# Iterate over array
declare -a files=("config.txt" "data.csv" "output.log")
for file in "${files[@]}"; do
    echo "File: $file"
done

# Iterate over command output
for user in $(cut -d: -f1 /etc/passwd | head -5); do
    echo "User: $user"
done

# Process substitution
for line in $(cat /etc/hosts); do    # WRONG: word splitting
    echo "$line"
done

# Correct way to iterate lines
while IFS= read -r line; do
    echo "$line"
done < /etc/hosts

# Or with process substitution
while IFS= read -r line; do
    echo "$line"
done < <(grep -v '^#' /etc/hosts)
```

### `while` Loops

```bash
# Basic while
count=0
while [[ $count -lt 5 ]]; do
    echo "Count: $count"
    ((count++))
done

# Read file line by line (correct method)
while IFS= read -r line; do
    echo "Line: $line"
done < /etc/passwd

# Read with field splitting
while IFS=: read -r user _ uid gid _ home shell; do
    printf "%-15s UID=%-5s Shell=%s\n" "$user" "$uid" "$shell"
done < /etc/passwd

# Read with timeout
while read -t 5 -p "Enter command: " cmd; do
    eval "$cmd"
done

# Infinite loop
while true; do
    check_service || restart_service
    sleep 60
done

# Alternative infinite loop
while :; do
    process_queue
    sleep 1
done
```

### `until` Loops

```bash
# Runs until command succeeds (opposite of while)
until ping -c1 -W1 server.example.com &>/dev/null; do
    echo "Waiting for server..."
    sleep 2
done
echo "Server is reachable!"

# Wait for file to appear
until [[ -f /tmp/ready.flag ]]; do
    sleep 0.5
done
```

### Loop Control

```bash
# break — exit loop
for i in {1..100}; do
    if [[ $i -eq 50 ]]; then
        break    # exit the for loop
    fi
    echo "$i"
done

# continue — skip to next iteration
for file in /var/log/*.log; do
    [[ -s "$file" ]] || continue    # skip empty files
    wc -l "$file"
done

# break/continue with levels (Bash 4.0+)
for i in {1..5}; do
    for j in {1..5}; do
        if [[ $j -eq 3 ]]; then
            break 2    # break out of both loops
        fi
        echo "$i $j"
    done
done

# break/continue from nested loops with labels
# (Not natively supported; use functions or flags)
process_files() {
    for dir in /var/log /tmp /etc; do
        for file in "$dir"/*.conf; do
            if [[ "$file" == *skip* ]]; then
                return 2    # acts like "break 2"
            fi
            echo "$file"
        done
    done
}
```

### Select Menus (Bash)

```bash
echo "Choose a color:"
select color in "Red" "Green" "Blue" "Quit"; do
    case "$color" in
        Red)   echo "You chose red" ;;
        Green) echo "You chose green" ;;
        Blue)  echo "You chose blue" ;;
        Quit)  break ;;
        *)     echo "Invalid choice" ;;
    esac
done
```

### Here Documents in Loops

```bash
# Process heredoc
while IFS= read -r line; do
    echo ">> $line"
done <<EOF
Line 1
Line 2
Line 3
EOF

# Tab-indented heredoc (strip tabs with <<-)
cat <<-EOF
	This line has a leading tab
	So does this one
EOF
```

## Functions

### Function Definition Styles

```bash
# Style 1: POSIX
my_function() {
    echo "Hello from function"
}

# Style 2: Bash 'function' keyword
function my_function {
    echo "Hello from function"
}

# Style 3: Both (redundant, but valid)
function my_function() {
    echo "Hello from function"
}
```

### Arguments and Return Values

```bash
# Arguments are positional parameters
greet() {
    local name="$1"
    local greeting="${2:-Hello}"
    echo "$greeting, $name!"
}

greet "Alice"              # Hello, Alice!
greet "Bob" "Hi"          # Hi, Bob!

# Return values via echo + command substitution
get_sum() {
    local result=$(( $1 + $2 ))
    echo "$result"
}

total=$(get_sum 5 3)
echo "Sum: $total"         # Sum: 8

# Return status (0-255)
is_even() {
    (( $1 % 2 == 0 ))
}

if is_even 4; then
    echo "4 is even"
fi

# Return via nameref (Bash 4.3+)
get_info() {
    local -n result=$1    # nameref to caller's variable
    result="some value"
}

get_info myvar
echo "$myvar"    # some value

# Return multiple values via nameref
get_user_info() {
    local -n _user=$1
    local -n _uid=$2
    local -n _shell=$3
    
    local line
    line=$(getent passwd "$4")
    IFS=: read -r _user _ _uid _ _ _shell <<< "$line"
}

get_user_info name uid shell "root"
echo "User=$name UID=$uid Shell=$shell"
```

### Local Variables in Functions

```bash
process_file() {
    local file="$1"
    local line
    local count=0
    
    while IFS= read -r line; do
        ((count++))
    done < "$file"
    
    echo "$count"
}

# Variables persist across calls unless declared local
counter=0
increment() {
    counter=$((counter + 1))    # modifies global
}

safe_increment() {
    local counter=0             # shadows global
    counter=$((counter + 1))    # modifies local only
}
```

### Function Libraries

```bash
# lib/common.sh
log() {
    printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

die() {
    log "FATAL: $*"
    exit 1
}

require_command() {
    command -v "$1" &>/dev/null || die "Required command not found: $1"
}

# main script
source "$(dirname "$0")/lib/common.sh"
require_command "curl"
require_command "jq"
log "Starting..."
```

### Recursive Functions

```bash
# Factorial
factorial() {
    local n=$1
    if (( n <= 1 )); then
        echo 1
    else
        local sub
        sub=$(factorial $((n - 1)))
        echo $((n * sub))
    fi
}

echo "$(factorial 5)"    # 120

# Directory tree walker
walk_tree() {
    local dir="$1"
    local indent="${2:-0}"
    
    for entry in "$dir"/*; do
        [[ -e "$entry" ]] || continue
        printf "%*s%s\n" "$indent" "" "$(basename "$entry")"
        [[ -d "$entry" ]] && walk_tree "$entry" $((indent + 2))
    done
}
```

## Quoting

Quoting is critical for safe shell scripting. Without proper quoting, word splitting and pathname expansion can corrupt variables.

### Types of Quoting

```bash
# Single quotes — literal, no expansion
echo 'Hello $USER'         # Hello $USER
echo 'It'\''s a test'      # It's a test (single quote inside)

# Double quotes — variable expansion, command substitution, arithmetic
echo "Hello $USER"         # Hello alice
echo "Today is $(date)"    # Today is Mon Jul 21 10:00:00 ...
echo "Result: $((2+3))"    # Result: 5

# Dollar sign not followed by special chars is literal
echo "$"                   # $
echo "Price: \$5"          # Price: $5

# Backslash escaping in double quotes
echo "Quote: \"hello\""    # Quote: "hello"
echo "Tab:\there"          # Tab:    here
echo "Newline:\nhere"      # Newline: (newline) here (with echo -e)
echo $'Tab:\there'         # $'...' — ANSI-C quoting
```

### When to Quote

```bash
# ALWAYS quote variable expansions
file="my file.txt"
cat "$file"              # CORRECT
cat $file                # WRONG: two arguments "my" and "file.txt"

# Quote command substitutions
count=$(wc -l < "$file")
echo "$count"

# Quote arrays properly
arr=("one" "two" "three")
for item in "${arr[@]}"; do   # preserves element boundaries
    echo "$item"
done

# Quote to prevent globbing
pattern="*.txt"
echo "$pattern"          # literal "*.txt"
echo $pattern            # expands to matching files

# Exceptions where quoting isn't needed (intentional splitting)
export PATH="$PATH:/usr/local/bin"    # quoting OK here
[[ -f $file ]]                        # safe inside [[ ]]
```

### ANSI-C Quoting `$'...'`

```bash
echo $'Line 1\nLine 2'    # Newlines
echo $'Tab\there'          # Tabs
echo $'Bell\x07'           # Hex escape
echo $'Unicode: \u2764'   # Unicode (Bash 4.4+)
echo $'Single: \''        # Single quote
```

### Here Strings and Here Docs

```bash
# Here string
grep "pattern" <<< "Search in this text"

# Here document
cat <<EOF
Hello, $USER!
Today is $(date +%A)
EOF

# Quoted heredoc (no expansion)
cat <<'EOF'
$USER is literal
$(date) is literal
EOF

# Indented heredoc (strip leading tabs)
if true; then
    cat <<-EOF
	Indented content
	More content
	EOF
fi
```

## Globbing (Filename Expansion)

Globbing expands patterns into matching filenames. It is **not** regular expressions.

### Basic Globs

```bash
*           # Match any string (including empty)
?           # Match any single character
[abc]       # Match any character in set
[a-z]       # Match any character in range
[!abc]      # Match any character NOT in set
[[:alpha:]] # POSIX character class

# Examples
ls *.txt                    # all .txt files
ls file?.log                # file1.log, fileA.log, etc.
ls [0-9]*                   # files starting with digit
ls *[!0-9]*                 # files NOT containing digits
ls *.{txt,log,csv}          # brace expansion (not glob per se)
```

### POSIX Character Classes

```bash
[[:alnum:]]    # Alphanumeric: [a-zA-Z0-9]
[[:alpha:]]    # Alphabetic: [a-zA-Z]
[[:blank:]]    # Space and tab
[[:cntrl:]]    # Control characters
[[:digit:]]    # Digits: [0-9]
[[:graph:]]    # Visible characters
[[:lower:]]    # Lowercase: [a-z]
[[:print:]]    # Printable characters
[[:punct:]]    # Punctuation
[[:space:]]    # Whitespace
[[:upper:]]    # uppercase: [A-Z]
[[:xdigit:]]   # Hex digits: [0-9a-fA-F]

# Examples
ls [[:upper:]]*            # files starting with uppercase
echo *[[:digit:]]          # files ending with digit
```

### Brace Expansion (Not Globbing)

```bash
# Brace expansion happens BEFORE globbing
echo {a,b,c}               # a b c
echo file{1..5}.txt        # file1.txt file2.txt file3.txt file4.txt file5.txt
echo {001..010..3}         # 001 004 007 010
echo pre{A,B,C}suf         # preAsuf preBsuf preCsuf

# Nesting
echo {a,b}{1,2}            # a1 a2 b1 b2
mkdir -p project/{src,bin,doc,lib}
```

### Shell Options Affecting Globbing

```bash
shopt -s nullglob      # Non-matching globs expand to nothing
shopt -s failglob      # Non-matching globs cause error
shopt -s dotglob       # Include dotfiles in *
shopt -s globstar      # ** matches recursively (Bash 4.0+)
shopt -s extglob       # Extended globbing patterns
shopt -s nocaseglob    # Case-insensitive matching

# Recursive glob with **
shopt -s globstar
for file in **/*.py; do
    echo "$file"       # finds all .py files recursively
done
```

### Extended Globbing (Bash)

```bash
shopt -s extglob

# Pattern operators
?(pattern)      # 0 or 1 occurrences
*(pattern)      # 0 or more occurrences
+(pattern)      # 1 or more occurrences
@(pattern)      # Exactly 1 occurrence
!(pattern)      # Anything except pattern

# Examples
ls *.+(jpg|png|gif)        # image files
rm !(*.txt|*.log)          # everything except .txt and .log
echo +(0-9)                # one or more digits
[[ "123" == +([0-9]) ]]    # true: all digits
[[ "12a" == +([0-9]) ]]    # false: contains non-digit
```

## Exit Codes

Exit codes (return codes, return statuses) indicate whether a command succeeded or failed.

### Standard Exit Codes

| Code | Meaning | Constant |
|------|---------|----------|
| 0 | Success | `EXIT_SUCCESS` |
| 1 | General error | — |
| 2 | Misuse of shell builtins | — |
| 126 | Command invoked cannot execute | — |
| 127 | Command not found | — |
| 128 | Invalid argument to exit | — |
| 128+N | Fatal signal N (e.g., 130 = SIGINT) | — |
| 130 | Terminated by Ctrl+C (SIGINT) | — |
| 137 | Terminated by SIGKILL (9+128) | — |
| 143 | Terminated by SIGTERM (15+128) | — |
| 255 | Exit status out of range | — |

### Checking Exit Codes

```bash
# $? holds the exit code of the last command
ls /etc/passwd
echo $?      # 0 (success)

ls /nonexistent
echo $?      # 2 (failure)

# Direct checking
if command; then
    echo "success"
else
    echo "failure: $?"
fi

# Short-circuit
command && echo "ok" || echo "fail"

# Capture exit code while using output
output=$(command) && status=0 || status=$?
echo "Exit code: $status"
```

### Setting Exit Codes

```bash
# Exit with specific code
exit 0      # success
exit 1      # error
exit $err   # use variable

# Return from function
my_function() {
    if ! some_check; then
        return 1    # failure
    fi
    return 0        # success
}

# Check function return
my_function
if [[ $? -ne 0 ]]; then
    echo "Function failed"
fi

# Idiomatic check
my_function || echo "Function failed"
```

### Exit Code Traps

```bash
# ERR trap (Bash)
trap 'echo "Error at line $LINENO (exit code: $?)" >&2' ERR

# Catch specific exit codes
trap 'case $? in
    1) echo "General error" ;;
    2) echo "Permission denied" ;;
    130) echo "Interrupted" ;;
esac' EXIT
```

### Common Pitfalls

```bash
# Pitfall 1: Pipelines return exit code of LAST command
false | true
echo $?    # 0 (true's exit code, not false's)

# Fix: pipefail
set -o pipefail
false | true
echo $?    # 1

# Pitfall 2: Subshells swallow exit codes
(some_command)
echo $?    # works correctly

# Pitfall 3: set -e doesn't catch everything
set -e
my_function    # if function returns non-zero, script exits
# But: commands in if/while conditions don't trigger set -e
if failing_command; then    # won't exit despite set -e
    echo "won't reach"
fi

# Pitfall 4: Exit code range is 0-255
exit 256    # becomes 0
exit -1     # becomes 255
exit 300    # becomes 44 (300 % 256)
```

### Best Practices for Exit Codes

```bash
#!/bin/bash
# Define meaningful exit codes
readonly E_SUCCESS=0
readonly E_GENERAL=1
readonly E_USAGE=2
readonly E_NOT_FOUND=3
readonly E_PERMISSION=4
readonly E_CONFIG=5

usage() {
    echo "Usage: $(basename "$0") [options]" >&2
    exit "$E_USAGE"
}

[[ $# -gt 0 ]] || usage
[[ -f "$1" ]] || { echo "File not found: $1" >&2; exit "$E_NOT_FOUND"; }
[[ -r "$1" ]] || { echo "Permission denied: $1" >&2; exit "$E_PERMISSION"; }

# ... main logic ...
exit "$E_SUCCESS"
```

## Putting It All Together

### Complete Script Example

```bash
#!/bin/bash
set -euo pipefail

# === Constants ===
readonly SCRIPT="$(basename "$0")"
readonly VERSION="2.0.0"
readonly LOG_FILE="/var/log/${SCRIPT%.sh}.log"

# === Functions ===
log() { printf "[%s] %s\n" "$(date '+%F %T')" "$*" | tee -a "$LOG_FILE" >&2; }
die() { log "FATAL: $*"; exit 1; }

validate_email() {
    local email="$1"
    [[ "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]
}

process_users() {
    local input="$1"
    local count=0
    
    while IFS=, read -r name email role; do
        [[ -n "$name" ]] || continue
        validate_email "$email" || { log "WARN: Invalid email: $email"; continue; }
        printf "%-20s %-30s %s\n" "$name" "$email" "$role"
        ((count++))
    done < "$input"
    
    log "Processed $count users"
}

# === Main ===
trap 'log "Script interrupted"; exit 130' INT TERM

[[ $# -ge 1 ]] || die "Usage: $SCRIPT <csv-file>"
[[ -f "$1" ]] || die "File not found: $1"
[[ -r "$1" ]] || die "Cannot read file: $1"

log "Starting $SCRIPT v$VERSION"
process_users "$1"
log "Done"
```

## Cross-References

- [Bash](bash.md) — Bash-specific features, builtins, and internals
- [Advanced Shell Scripting](scripting-advanced.md) — Traps, subshells, coprocesses, strict mode
- [Regular Expressions](regex.md) — Pattern matching with grep, sed, awk
- [sed and awk](sed-awk.md) — Text processing in scripts

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) — Industry-standard style
- [BashFAQ](https://mywiki.wooledge.org/BashFAQ) — Common pitfalls and solutions
- [Greg's Wiki](https://mywiki.wooledge.org/) — Comprehensive Bash knowledge
- [POSIX Shell Command Language](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html) — The POSIX standard
- [shellcheck.net](https://www.shellcheck.net/) — Static analysis tool
