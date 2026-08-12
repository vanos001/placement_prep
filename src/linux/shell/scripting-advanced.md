# Advanced Shell Scripting

This chapter covers advanced shell scripting techniques that go beyond basic variables, loops, and conditionals. These patterns are essential for writing production-quality scripts that handle errors gracefully, manage complex data flows, and operate reliably in adversarial environments.

## Strict Mode: `set -euo pipefail`

The single most important line in any shell script:

```bash
#!/bin/bash
set -euo pipefail
```

### Breaking Down Each Flag

```bash
set -e          # Exit immediately on command failure
set -u          # Treat unset variables as errors
set -o pipefail # Pipeline returns rightmost non-zero exit code
```

#### `set -e` (errexit)

```bash
#!/bin/bash
set -e

echo "Before"
false           # Script exits here
echo "After"    # Never reached
```

**Exceptions where `set -e` does NOT trigger:**
```bash
# Commands in if conditions
if false; then echo "no"; fi    # Script continues

# Commands after || or &&
false || echo "fallback"         # Script continues
true && echo "ok"                # Script continues

# Commands in while/until conditions
while false; do echo "no"; done  # Script continues (loop just doesn't run)

# Negated commands
! false                          # Script continues

# Commands in && or || chains inside functions called from if
check() { false; }
if check; then echo "yes"; fi   # Script continues
```

#### `set -u` (nounset)

```bash
#!/bin/bash
set -u

echo "$undefined_var"   # bash: undefined_var: unbound variable
echo "${undefined_var:-default}"   # OK: uses default value

# Common patterns to handle optional variables
config_file="${CONFIG_FILE:-/etc/myapp.conf}"
verbose="${VERBOSE:-0}"
```

#### `set -o pipefail`

```bash
#!/bin/bash
set -o pipefail

# Without pipefail:
false | true | echo "hello"
echo $?    # 0 (echo's exit code)

# With pipefail:
false | true | echo "hello"
echo $?    # 1 (false's exit code — first failure in pipeline)

# Check all components
set -o pipefail
result=$(grep "pattern" file.txt | wc -l)
# If grep fails (file not found), $? is non-zero even though wc succeeds
```

### Recommended Strict Mode Variants

```bash
# Standard strict mode
set -euo pipefail

# With trace for debugging
set -euxo pipefail

# Strict with better error messages
set -euo pipefail
trap 'echo "Error at line $LINENO" >&2' ERR

# Even stricter with inherit_errexit (Bash 4.4+)
shopt -s inherit_errexit
set -euo pipefail
# Without inherit_errexit, command substitutions don't inherit set -e
```

### Strict Mode Gotchas

```bash
# Gotcha 1: set -e and command substitution
set -e
# This WON'T catch the error:
output=$(false)      # command substitution in simple assignment
echo "continues..."  # still runs

# Fix with explicit check:
output=$(false) || die "Command failed"

# Gotcha 2: set -e and functions
set -e
my_func() {
    local x
    x=$(false)      # doesn't trigger set -e inside function
    echo "continues inside function"
}
my_func              # DOES trigger set -e here (function returns non-zero)

# Gotcha 3: set -u with $@, $* when no arguments
set -u
echo "$@"            # Error if no arguments passed
echo "${@:-}"        # Safe: empty string if no args

# Gotcha 4: set -e and arithmetic
set -e
count=0
((count++))          # Returns 1 (0 was false) → triggers set -e!
# Fix:
((count++)) || true
count=$((count + 1))  # Safe: assignment doesn't have exit status issue
```

## Subshells and Command Grouping

### Subshells `()`

A subshell is a child process that inherits a copy of the parent's environment. Changes in a subshell don't affect the parent.

```bash
# Basic subshell
(cd /tmp && ls)   # cd doesn't affect parent shell
pwd               # still in original directory

# Subshell for isolation
(
    set -e
    cd /var/log
    rm -f *.tmp
)   # set -e and cd only affect subshell

# Capture output in subshell
current_dir=$(cd /some/dir && pwd)

# Subshell in pipeline (each segment runs in subshell)
echo "hello" | read -r greeting
echo "$greeting"    # EMPTY — read ran in subshell

# Fix: process substitution or lastpipe
shopt -s lastpipe   # Bash 4.2+: run last pipeline component in current shell
echo "hello" | read -r greeting
echo "$greeting"    # "hello"
```

### Subshell Inheritance

```bash
# Variables: copied (not shared)
parent_var="original"
(
    parent_var="modified"
    echo "Inside: $parent_var"   # modified
)
echo "Outside: $parent_var"     # original

# File descriptors: inherited
exec 3>/tmp/output.txt
(
    echo "from subshell" >&3    # writes to fd 3
)
exec 3>&-

# Shell options: inherited
set -x
(
    echo "trace is on here too"
)
set +x

# Traps: inherited
trap 'echo cleanup' EXIT
(
    # EXIT trap inherited
    echo "subshell"
)   # trap fires when subshell exits
```

### Command Grouping `{}`

Unlike subshells, command grouping runs in the **current** shell:

```bash
# Redirect a group of commands
{
    echo "Header"
    date
    echo "Footer"
} > output.txt

# Error handling for group
{
    command1
    command2
    command3
} || {
    echo "Something failed in the group" >&2
    exit 1
}

# Conditional grouping
[[ -f config ]] && {
    source config
    echo "Config loaded"
}
```

### Subshell vs Command Grouping

```
┌─────────────────────────────────────────────────────┐
│  Subshell () vs Command Grouping {}                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Feature          │  () Subshell  │  {} Group       │
│  ─────────────────┼───────────────┼──────────────── │
│  Runs in          │  Child process│  Current shell  │
│  Variable changes │  Lost         │  Preserved      │
│  cd affects       │  Subshell only│  Current shell  │
│  set changes      │  Subshell only│  Current shell  │
│  Performance      │  Fork overhead│  No fork        │
│  Syntax           │  (cmds)       │  { cmds; }      │
│  Semicolon before │  Not needed   │  Required: {    │
│  Semicolon after  │  Not needed   │  Required: ;}   │
└─────────────────────────────────────────────────────┘
```

## Coprocesses

Coprocesses allow two-way communication between the current shell and a background command.

### Basic Coprocess Usage

```bash
# Start a coprocess (Bash 4.0+)
coproc myproc { bc -l; }

# Write to coprocess stdin
echo "scale=4; 22/7" >&"${myproc[1]}"

# Read from coprocess stdout
read -r result <&"${myproc[0]}"
echo "Pi ≈ $result"    # Pi ≈ 3.1428

# Close the coprocess
exec {myproc[1]}>&-    # close stdin
wait "$myproc_PID"     # wait for exit
```

### Coprocess for Persistent Connections

```bash
# Persistent SSH connection via coprocess
coproc ssh_conn { ssh -o BatchMode=yes user@server "bash -s"; }

# Send commands
echo "uptime" >&"${ssh_conn[1]}"
read -r output <&"${ssh_conn[0]}"
echo "Server uptime: $output"

echo "df -h /" >&"${ssh_conn[1]}"
read -r output <&"${ssh_conn[0]}"
echo "Disk: $output"

# Cleanup
exec {ssh_conn[1]}>&-
wait "$ssh_conn_PID"
```

### Coprocess for Interactive Programs

```bash
# Control gdb programmatically
coproc GDB { gdb -q ./myprogram; }

echo "break main" >&"${GDB[1]}"
echo "run" >&"${GDB[1]}"

# Read until prompt
while IFS= read -r -t 5 line <&"${GDB[0]}"; do
    echo "GDB: $line"
    [[ "$line" == *"(gdb)"* ]] && break
done

echo "continue" >&"${GDB[1]}"
```

### Coprocess Communication Pattern

```
┌───────────────────────────────────────────────────┐
│  Coprocess Communication                           │
├───────────────────────────────────────────────────┤
│                                                   │
│  Parent Shell          Coprocess                  │
│  ┌──────────┐          ┌──────────┐               │
│  │          │──stdin──▶│          │               │
│  │          │  fd[1]   │          │               │
│  │          │          │  (bc)    │               │
│  │          │◀──stdout─│          │               │
│  │          │  fd[0]   │          │               │
│  └──────────┘          └──────────┘               │
│                                                   │
│  coproc NAME { command; }                         │
│  ${NAME[0]} → stdout pipe (read from coproc)      │
│  ${NAME[1]} → stdin pipe  (write to coproc)       │
│  ${NAME_PID} → coprocess PID                      │
└───────────────────────────────────────────────────┘
```

## Here Documents and Here Strings

### Here Documents (Heredocs)

```bash
# Basic heredoc
cat <<EOF
Hello, $USER!
Today is $(date +%A)
Working directory: $(pwd)
EOF

# Quoted heredoc (no expansion)
cat <<'EOF'
$USER is literal
$(date) is not executed
$((1+2)) is not evaluated
EOF

# Tab-indented heredoc (strip leading tabs)
if true; then
    cat <<-EOF
	Line with leading tab (tab stripped)
	Another line (tab stripped)
	EOF
fi

# Here doc to variable
read -r -d '' help_text <<'EOF'
Usage: script.sh [options]

Options:
  -h  Show help
  -v  Verbose
EOF

# Here doc as function argument
send_email <<EOF
Subject: Report
From: $USER@$(hostname)
Body: Report attached.
EOF
```

### Heredocs in Pipelines and Redirections

```bash
# Heredoc to pipeline
grep "error" <<EOF
line 1: ok
line 2: error found
line 3: ok
EOF

# Heredoc to variable via read
IFS= read -r -d '' sql <<'EOF'
SELECT u.name, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.name
ORDER BY order_count DESC;
EOF

echo "$sql"
```

### Here Strings

```bash
# Feed string to command's stdin
grep "pattern" <<< "Search in this string"

# Read from here string
IFS=: read -r user pass uid gid <<< "$(grep root /etc/passwd)"

# Arithmetic with here string
bc <<< "scale=10; sqrt(2)"

# Multi-word into array
read -ra words <<< "one two three four five"
echo "${words[2]}"    # three
```

### Here Document Gotchas

```bash
# Gotcha: indentation
if true; then
cat <<EOF    # This is flush-left, looks ugly
indented content
EOF
fi

# Fix with <<- (but tabs, not spaces!)
if true; then
    cat <<-EOF
	This must use tabs, not spaces
	EOF
fi

# Gotcha: delimiter must be exact
cat <<EOF
content
EOF    # OK: exact match

cat <<EOF
content
  EOF    # FAIL: has spaces before EOF
EOF      # This EOF ends the heredoc
```

## Named Pipes (FIFOs)

Named pipes (FIFOs) are filesystem objects that allow unrelated processes to communicate.

### Creating and Using FIFOs

```bash
# Create a named pipe
mkfifo /tmp/mypipe

# Writer process
echo "Hello from writer" > /tmp/mypipe &

# Reader process
cat /tmp/mypipe

# The writer blocks until a reader connects (and vice versa)
```

### Practical FIFO Patterns

```bash
# Pattern 1: Process substitution equivalent
mkfifo /tmp/logpipe
gzip -c < /tmp/logpipe > output.gz &
some_command > /tmp/logpipe    # compressed output

# Pattern 2: Decouple producer and consumer
mkfifo /tmp/requests /tmp/responses

# Server side
while read -r req < /tmp/requests; do
    echo "Processed: $req" > /tmp/responses
done

# Client side
echo "task1" > /tmp/requests
cat /tmp/responses

# Pattern 3: Rate limiting
mkfifo /tmp/ratelimit
# Token bucket
while true; do
    echo "token" > /tmp/ratelimit
    sleep 1    # one token per second
done &
# Consumer
while read -r _ < /tmp/ratelimit; do
    process_next_item
done

# Pattern 4: Multiplexing
mkfifo /tmp/fifo_{1,2,3}
# Multiple producers write to separate FIFOs
# Single reader merges them
tail -f /tmp/fifo_1 /tmp/fifo_2 /tmp/fifo_3 &
```

### FIFO Behavior

```bash
# FIFOs block on open until both reader and writer are present
mkfifo /tmp/blocking_pipe
exec 3<>/tmp/blocking_pipe    # Opens for both read and write (non-blocking)

# Non-blocking open
exec 3>/tmp/blocking_pipe     # Blocks until reader
exec 3</tmp/blocking_pipe     # Blocks until writer

# Cleanup
rm /tmp/blocking_pipe
exec 3>&-
```

### FIFO vs Temporary Files

```
┌─────────────────────────────────────────────────────┐
│  FIFO vs Temp File                                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Feature        │  FIFO          │  Temp File       │
│  ───────────────┼────────────────┼───────────────── │
│  Storage        │  Memory (no disk)│ Disk           │
│  Size limit     │  ~64KB buffer  │  Disk space      │
│  Persistence    │  Named, stays  │  Until deleted   │
│  Blocking       │  Yes           │  No              │
│  Bidirectional  │  No (one-way)  │  Yes             │
│  Use case       │  IPC streams   │  Complex data    │
│  Cleanup        │  rm after use  │  rm after use    │
└─────────────────────────────────────────────────────┘
```

## Advanced Signal Handling with Traps

### Multi-Signal Trap Patterns

```bash
# Trap multiple signals with same handler
cleanup() {
    rm -f "$LOCK_FILE" "$TEMP_FILE"
    jobs -p | xargs -r kill 2>/dev/null
    exit
}
trap cleanup EXIT INT TERM HUP

# Signal-specific handlers
trap 'echo "Reloading config..."; reload_config' HUP
trap 'echo "Interrupted"; exit 130' INT
trap 'echo "Terminated"; exit 143' TERM
trap 'echo "Pipe closed"' PIPE
trap 'echo "Window resized"; update_cols' WINCH
```

### Trap Stacking and Chaining

```bash
# Save and restore traps
save_traps() {
    # Bash 4.4+: trap -p outputs trap commands
    trap -p EXIT
}

original_trap=$(trap -p EXIT)
trap 'new_cleanup' EXIT

# Later, restore:
eval "$original_trap"
```

### Debug Traps

```bash
# Trace every command
trap 'printf "+ %s\n" "$BASH_COMMAND"' DEBUG

# Selective tracing
TRACE=0
toggle_trace() {
    if (( TRACE )); then
        TRACE=0
        trap - DEBUG
    else
        TRACE=1
        trap 'printf "+ %s\n" "$BASH_COMMAND"' DEBUG
    fi
}

# Line-by-line execution with prompt
trap 'printf "Line %d: %s? [y/n] " "$LINENO" "$BASH_COMMAND"; read -r ans; [[ "$ans" == y ]]' DEBUG
```

### ERR Trap Patterns

```bash
# Global error handler
set -e
trap 'echo "Error at $BASH_SOURCE:$LINENO: $BASH_COMMAND (exit $?)" >&2' ERR

# Function-level error handling
handle_error() {
    local exit_code=$?
    local line_no=$1
    local command=$2
    echo "ERROR: Command '$command' failed at line $line_no (exit code $exit_code)" >&2
    # Could send alert, write to syslog, etc.
}

trap 'handle_error $LINENO "$BASH_COMMAND"' ERR

# ERR trap with inheritance in functions (Bash 4.4+)
shopt -s inherit_errexit
set -e
trap 'echo "Error caught"' ERR

my_function() {
    false    # ERR trap fires here with inherit_errexit
}
```

## Advanced Pattern Matching

### `=~` Regex Operator (Bash 3.0+)

```bash
# Basic regex
if [[ "$str" =~ ^[0-9]+$ ]]; then
    echo "All digits"
fi

# Capture groups (Bash 3.0+)
if [[ "$version" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    patch="${BASH_REMATCH[3]}"
    echo "Version: $major.$minor.$patch"
fi

# Named captures (Bash 5.1+) — not standard, but regex supports (?P<name>)
# More commonly, use indexed groups

# Complex regex
ip_regex='^([0-9]{1,3}\.){3}[0-9]{1,3}$'
if [[ "$input" =~ $ip_regex ]]; then
    echo "Valid IP format"
fi

# Store regex in variable (recommended for complex patterns)
re='^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
if [[ "$email" =~ $re ]]; then
    echo "Valid email"
fi
```

### `case` with Extended Patterns

```bash
shopt -s extglob

case "$input" in
    +([0-9]))          echo "All digits" ;;
    +([a-z]))          echo "All lowercase" ;;
    @(+|-)+([0-9]))    echo "Signed integer" ;;
    +([0-9]).+([0-9])) echo "Decimal number" ;;
    *)                  echo "Other" ;;
esac
```

## Advanced Array Techniques

### Sparse Arrays

```bash
# Arrays can have gaps
declare -a sparse
sparse[0]="a"
sparse[100]="b"
sparse[1000]="c"

echo "${#sparse[@]}"    # 3 (actual elements, not range)
echo "${!sparse[@]}"    # 0 100 1000 (indices)

# Iterate only over set indices
for i in "${!sparse[@]}"; do
    echo "Index $i: ${sparse[$i]}"
done
```

### Array Manipulation Functions

```bash
# Reverse array
reverse_array() {
    local -n _arr=$1
    local -a result=()
    for ((i = ${#_arr[@]} - 1; i >= 0; i--)); do
        result+=("${_arr[$i]}")
    done
    _arr=("${result[@]}")
}

# Array contains
contains() {
    local -n _arr=$1
    local target="$2"
    for item in "${_arr[@]}"; do
        [[ "$item" == "$target" ]] && return 0
    done
    return 1
}

# Array unique
unique() {
    local -n _arr=$1
    local -A seen=()
    local -a result=()
    for item in "${_arr[@]}"; do
        if [[ -z "${seen[$item]+_}" ]]; then
            seen[$item]=1
            result+=("$item")
        fi
    done
    _arr=("${result[@]}")
}

# Array intersection
intersection() {
    local -n _result=$1
    local -n _arr1=$2
    local -n _arr2=$3
    local -A set2=()
    _result=()
    
    for item in "${_arr2[@]}"; do
        set2["$item"]=1
    done
    
    for item in "${_arr1[@]}"; do
        [[ -n "${set2[$item]+_}" ]] && _result+=("$item")
    done
}

# Usage
a=(1 2 3 4 5)
b=(3 4 5 6 7)
intersection result a b
echo "${result[@]}"    # 3 4 5
```

### Associative Array as Data Structure

```bash
# Stack (LIFO)
declare -A stack=()
stack_idx=0

push() { stack[$((stack_idx++))]="$1"; }
pop() {
    if (( stack_idx == 0 )); then
        echo "Stack empty" >&2; return 1
    fi
    echo "${stack[$((--stack_idx))]}"
    unset "stack[$stack_idx]"
}

push "first"
push "second"
push "third"
echo "$(pop)"    # third
echo "$(pop)"    # second

# Simple map/dictionary
declare -A config=(
    [host]="localhost"
    [port]="8080"
    [debug]="true"
)

# Merge two maps
declare -A defaults=([timeout]=30 [retries]=3)
declare -A user_config=([timeout]=60)

for key in "${!defaults[@]}"; do
    config[$key]="${user_config[$key]:-${defaults[$key]}}"
done
```

## Process Management in Scripts

### Background Jobs and `wait`

```bash
#!/bin/bash
set -euo pipefail

# Run tasks in parallel
pids=()
for server in server{1..5}.example.com; do
    (
        ssh "$server" "uptime"
    ) &
    pids+=($!)
done

# Wait for all and collect exit codes
errors=0
for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
        ((errors++))
    fi
done

echo "Completed with $errors errors"
exit "$errors"
```

### Job Control in Scripts

```bash
# Named background jobs (Bash 4.0+)
download_file() {
    curl -sO "$1"
}

# Start background jobs
download_file "https://example.com/file1" &
pid1=$!

download_file "https://example.com/file2" &
pid2=$!

# Wait with timeout
timeout=30
if ! wait "$pid1" 2>/dev/null; then
    echo "Download 1 timed out"
fi

# Check if job is still running
if kill -0 "$pid2" 2>/dev/null; then
    echo "Download 2 still running"
fi
```

### Resource Limits

```bash
# Limit memory usage
ulimit -v 524288    # 512MB virtual memory

# Limit file size
ulimit -f 102400    # 100MB max file size

# Limit CPU time
ulimit -t 300       # 5 minutes CPU time

# Limit open files
ulimit -n 1024      # 1024 file descriptors

# In subshell for isolation
(
    ulimit -v 524288
    memory_intensive_command
)
```

## Debugging Techniques

### Selective Tracing

```bash
# Enable/disable tracing around specific code
set -x
# ... code to trace ...
set +x

# Debug function
debug() {
    (( DEBUG_LEVEL >= ${1:-1} )) && printf "DEBUG[%d]: %s\n" "$1" "${*:2}" >&2
}

DEBUG_LEVEL=2
debug 1 "This shows (level 1)"
debug 3 "This doesn't show (level 3)"
```

### `BASH_SOURCE` and `LINENO`

```bash
# Get script location reliably
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Error handler with full context
on_error() {
    local frame
    echo "Traceback (most recent call last):" >&2
    for ((frame = 1; frame < ${#BASH_SOURCE[@]}; frame++)); do
        printf "  File \"%s\", line %d, in %s\n" \
            "${BASH_SOURCE[$frame]}" \
            "${BASH_LINENO[$frame-1]}" \
            "${FUNCNAME[$frame]}" >&2
    done
    echo "Error: $1" >&2
}

trap 'on_error "Command failed"' ERR
```

### `xtrace` Customization (Bash 5.1+)

```bash
# Customize trace prefix
export BASH_XTRACEFD=2    # Send trace to stderr
export PS4='+ ${BASH_SOURCE[0]}:${LINENO}: '

# More detailed PS4
export PS4='+ ${BASH_SOURCE[$i]:-${BASH_SOURCE}}:${LINENO}:${FUNCNAME[0]:+${FUNCNAME[0]}():} '

# Line-by-line execution with pause
trap 'read -p "Press Enter to continue..."' DEBUG
```

## Portable Scripting (POSIX sh)

When targeting multiple Unix systems or when Bash isn't available:

```bash
#!/bin/sh
# POSIX-compliant script — avoid Bash-specific features

# No arrays → use functions and positional parameters
set -- "one" "two" "three"
echo "$#"    # 3
echo "$1"    # one

# No [[ ]] → use [ ] with proper quoting
if [ -f "$file" ]; then
    echo "exists"
fi

# No ${var,,} → use tr
lower=$(echo "$var" | tr '[:upper:]' '[:lower:]')

# No ${var//old/new} → use sed
replaced=$(echo "$var" | sed 's/old/g/g')

# No readarray → use while loop
i=0
while IFS= read -r line; do
    eval "line_$i=\"\$line\""
    i=$((i + 1))
done < file.txt

# No process substitution → use temp files
diff_file=$(mktemp)
sort file1 > "$diff_file"
sort file2 | diff "$diff_file" -
rm -f "$diff_file"
```

## Real-World Script Patterns

### Lock File Pattern

```bash
#!/bin/bash
set -euo pipefail

LOCK_FILE="/var/lock/myapp.lock"

acquire_lock() {
    if ! mkdir "$LOCK_FILE" 2>/dev/null; then
        local pid
        pid=$(cat "$LOCK_FILE/pid" 2>/dev/null)
        if kill -0 "$pid" 2>/dev/null; then
            echo "Already running (PID $pid)" >&2
            exit 1
        fi
        echo "Stale lock found, removing" >&2
        rm -rf "$LOCK_FILE"
        mkdir "$LOCK_FILE"
    fi
    echo $$ > "$LOCK_FILE/pid"
}

release_lock() {
    rm -rf "$LOCK_FILE"
}

trap release_lock EXIT
acquire_lock
# ... main logic ...
```

### Retry with Exponential Backoff

```bash
retry() {
    local max_attempts=$1
    local delay=1
    shift
    
    for ((attempt = 1; attempt <= max_attempts; attempt++)); do
        if "$@"; then
            return 0
        fi
        
        if ((attempt < max_attempts)); then
            echo "Attempt $attempt failed, retrying in ${delay}s..." >&2
            sleep "$delay"
            delay=$((delay * 2))
        fi
    done
    
    echo "All $max_attempts attempts failed" >&2
    return 1
}

retry 5 curl -sf "https://api.example.com/health"
```

### Configuration File Parser

```bash
parse_config() {
    local file="$1"
    local section=""
    
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// /}" ]] && continue
        
        # Section header
        if [[ "$line" =~ ^\[([^]]+)\]$ ]]; then
            section="${BASH_REMATCH[1]}"
            continue
        fi
        
        # Key=value
        if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]// /}"
            local value="${BASH_REMATCH[2]}"
            # Trim whitespace
            value="${value#"${value%%[![:space:]]*}"}"
            value="${value%"${value##*[![:space:]]}"}"
            
            # Store in associative array
            if [[ -n "$section" ]]; then
                config["${section}.${key}"]="$value"
            else
                config["$key"]="$value"
            fi
        fi
    done < "$file"
}

declare -A config=()
parse_config "/etc/myapp.conf"
echo "Database host: ${config[database.host]}"
```

## Cross-References

- [Bash](bash.md) — Bash-specific features and builtins
- [Shell Scripting Fundamentals](scripting-fundamentals.md) — Variables, conditionals, loops, functions
- [Regular Expressions](regex.md) — Pattern matching syntax
- [sed and awk](sed-awk.md) — Text processing tools

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [BashFAQ - Greg's Wiki](https://mywiki.wooledge.org/BashFAQ) — Answers to common questions
- [Bash Pitfalls](https://mywiki.wooledge.org/BashPitfalls) — Common mistakes and fixes
- [Defensive BASH Programming](https://defensive-shell-programming.name/) — Writing robust scripts
- [Writing Robust Bash Shell Scripts](https://www.davidpashley.com/articles/writing-robust-shell-scripts/) — David Pashley's guide
- [The Lost Manual to Bash Strict Mode](https://www.dvv.io/bash-strict-mode/) — Deep dive into `set -euo pipefail`
