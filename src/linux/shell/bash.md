# Bash — The Bourne Again Shell

Bash (Bourne Again SHell) is the most widely used Unix shell and the default interactive shell on most Linux distributions. Originally written by Brian Fox for the GNU Project in 1989, Bash is a free software replacement for the Bourne Shell (`sh`) that incorporates features from the Korn Shell (`ksh`) and C Shell (`csh`). It serves both as a powerful interactive command interpreter and as a full-featured scripting language.

## History and Design Philosophy

Bash was created to provide a POSIX-compliant shell that was freely available under the GNU General Public License. Its design philosophy centers on backward compatibility with the Bourne Shell while adding modern conveniences:

- **Command-line editing** via the GNU Readline library
- **Tab completion** for commands, files, and variables
- **Command history** with persistent storage
- **Arrays and associative arrays** for data manipulation
- **Extended parameter expansion** for string manipulation
- **Arithmetic evaluation** with C-like syntax
- **Process substitution** for inter-process data flow

## Bash Startup and Invocation

Understanding how Bash starts is critical for knowing which configuration files are read and what environment is established.

### Invocation Modes

```bash
# Login shell: reads /etc/profile, then ~/.bash_profile, ~/.bash_login, or ~/.profile
bash --login
bash -l

# Interactive non-login shell: reads ~/.bashrc
bash

# Non-interactive shell (scripts): reads $BASH_ENV
bash script.sh

# POSIX mode: disables Bash-specific features
bash --posix

# Restricted shell: limits certain operations
bash --restricted
```

### Startup File Sequence

```
┌─────────────────────────────────────────────┐
│              Bash Startup                    │
├─────────────────────────────────────────────┤
│                                             │
│  Login Shell?                                │
│  ├── Yes → /etc/profile                      │
│  │         ~/.bash_profile (or alternatives) │
│  │         ↓ (if source ~/.bashrc inside)    │
│  │         ~/.bashrc                         │
│  └── No  → $BASH_ENV (if set)               │
│                                             │
│  Interactive?                                │
│  ├── Yes → ~/.bashrc (non-login)            │
│  └── No  → $BASH_ENV only                   │
│                                             │
│  Logout → ~/.bash_logout                    │
└─────────────────────────────────────────────┘
```

### Example: Login Shell Detection

```bash
# Check if current shell is a login shell
shopt login_shell
# login_shell    on    # ← this is a login shell

# Check shell options
echo $-
# himBhs        # flags present in $-

# Show which startup files Bash would source
# (Bash 4.4+)
bash -c 'echo "Login: $0"; shopt login_shell' --login
```

## Built-in Commands (Builtins)

Builtins are commands implemented internally within the Bash binary. They execute faster than external commands because no process forking is required.

### Essential Builtins

| Builtin | Purpose | Example |
|---------|---------|---------|
| `cd` | Change directory | `cd /usr/local` |
| `type` | Identify command type | `type cd` → `cd is a shell builtin` |
| `echo` | Output text | `echo "Hello"` |
| `printf` | Formatted output | `printf "%-20s %d\n" "name" 42` |
| `read` | Read input | `read -p "Name: " name` |
| `declare` | Declare variables | `declare -i count=0` |
| `local` | Local variables in functions | `local var=value` |
| `export` | Mark for environment | `export PATH=$PATH:/new` |
| `source` / `.` | Execute file in current shell | `source ~/.bashrc` |
| `eval` | Evaluate arguments as command | `eval "$cmd"` |
| `exec` | Replace shell process | `exec > logfile 2>&1` |
| `set` | Set shell options | `set -euo pipefail` |
| `shopt` | Shell options (Bash-specific) | `shopt -s globstar` |
| `trap` | Catch signals | `trap 'cleanup' EXIT` |
| `getopts` | Parse options | `getopts "a:b:c" opt` |
| `mapfile` | Read lines into array | `mapfile -t lines < file` |
| `printf` | Formatted output | `printf '%x\n' 255` |
| `builtin` | Force builtin execution | `builtin echo "hi"` |
| `command` | Bypass functions/aliases | `command ls -la` |
| `enable` | Enable/disable builtins | `enable -n kill` |

### The `type` Command — Identifying Commands

```bash
$ type -a echo
echo is a shell builtin
echo is /usr/bin/echo

$ type -t cd
builtin

$ type -t ls
file

$ type -t alias_name
alias

$ type -t my_function
function
```

### `printf` — The Superior Output Command

`printf` provides C-style formatted output and is preferred over `echo` for portable, predictable behavior:

```bash
# Basic formatting
printf "Name: %-15s Age: %3d\n" "Alice" 30
# Output: Name: Alice           Age:  30

# Hex and octal
printf "Hex: %x  Octal: %o\n" 255 255
# Output: Hex: ff  Octal: 377

# Zero-padded numbers
printf "%05d\n" 42
# Output: 00042

# String truncation
printf "%.5s\n" "Hello, World!"
# Output: Hello

# Variable-width formatting
width=20
printf "%*s\n" $width "right-aligned"
```

### `read` — Input Processing

```bash
# Basic input
read -p "Enter name: " name

# Silent input (for passwords)
read -sp "Password: " pass
echo

# Timeout
read -t 5 -p "Quick! Type something: " input

# With delimiter
IFS=':' read -r user _ uid gid _ home shell <<< "$(grep root /etc/passwd)"
echo "$user $uid $home"

# Read into array
read -ra words <<< "one two three four"
echo "${words[2]}"  # three

# Mapfile (read lines into array)
mapfile -t lines < /etc/hosts
echo "Hosts file has ${#lines[@]} lines"
```

## Variables and Data Types

### Variable Declaration with `declare`

```bash
# Integer variable (arithmetic context)
declare -i count=0
count=count+5      # treated as arithmetic
echo $count        # 5
count="hello"      # assigned 0 (invalid arithmetic → 0)

# Read-only variable
declare -r PI=3.14159
PI=3.14            # bash: PI: readonly variable

# Array
declare -a fruits=("apple" "banana" "cherry")

# Associative array (Bash 4.0+)
declare -A config
config[host]="localhost"
config[port]="8080"

# Export to environment
declare -x MY_VAR="visible to children"

# Uppercase/lowercase transformation (Bash 4.0+)
declare -u upper="hello"    # HELLO
declare -l lower="HELLO"    # hello

# Trace attribute (debugging)
declare -t debug_var=1
```

## Arrays

Bash supports both indexed arrays and associative arrays.

### Indexed Arrays

```bash
# Declaration methods
declare -a colors
colors=("red" "green" "blue" "yellow")

# Alternative declaration
colors[0]="red"
colors[1]="green"
colors[2]="blue"

# Read from command into array
mapfile -t lines < /etc/passwd
# Or using read
readarray -t lines < /etc/passwd

# Access elements
echo "${colors[0]}"          # red
echo "${colors[-1]}"         # yellow (Bash 4.3+)
echo "${colors[@]}"          # all elements
echo "${#colors[@]}"         # number of elements

# Slicing
echo "${colors[@]:1:2}"      # green blue (start at index 1, length 2)

# Append
colors+=("purple" "orange")

# Remove element
unset colors[1]               # removes "green"

# Iterate
for color in "${colors[@]}"; do
    echo "$color"
done

# Iterate with indices
for i in "${!colors[@]}"; do
    echo "Index $i: ${colors[$i]}"
done

# Array operations
a=(1 2 3)
b=(4 5 6)
c=("${a[@]}" "${b[@]}")     # concatenate: 1 2 3 4 5 6

# Pattern removal from array
files=("file1.txt" "file2.txt" "file3.log")
echo "${files[@]%.txt}"      # file1 file2 file3.log

# Sort an array
sorted=($(printf '%s\n' "${colors[@]}" | sort))
```

### Associative Arrays (Bash 4.0+)

```bash
declare -A user

# Assign values
user[name]="Alice"
user[age]=30
user[role]="admin"

# Bulk declaration
declare -A server=(
    [host]="192.168.1.100"
    [port]="22"
    [user]="deploy"
)

# Access
echo "${server[host]}:${server[port]}"

# All keys
echo "${!server[@]}"         # host port user

# All values
echo "${server[@]}"

# Number of entries
echo "${#server[@]}"

# Iterate over key-value pairs
for key in "${!server[@]}"; do
    printf "%-10s = %s\n" "$key" "${server[$key]}"
done
# Output:
# host       = 192.168.1.100
# port       = 22
# user       = deploy

# Check if key exists
if [[ -v server[port] ]]; then
    echo "Port is set"
fi

# Delete a key
unset server[port]
```

## Parameter Expansion

Parameter expansion is Bash's most powerful feature for string and variable manipulation. It replaces many uses of external commands like `sed`, `awk`, and `cut`.

### Basic Syntax

```bash
${parameter}               # Value of parameter
${parameter:-default}       # Use default if unset or null
${parameter:=default}       # Assign default if unset or null
${parameter:+alternate}    # Use alternate if set and non-null
${parameter:?error_msg}    # Error if unset or null
```

### String Length

```bash
str="Hello, World!"
echo ${#str}               # 13

arr=("a" "bb" "ccc")
echo ${#arr[@]}            # 3 (number of elements)
echo ${#arr[1]}            # 2 (length of element at index 1)
```

### Substring Extraction

```bash
str="Hello, World!"

echo ${str:7}              # World!
echo ${str:0:5}            # Hello
echo ${str: -6}            # World! (note the space before -)
echo ${str:(-6)}           # World! (alternative)
echo ${str:7:-1}           # World (from pos 7, remove last char)
```

### Pattern Removal

```bash
path="/home/user/documents/report.tar.gz"

# Shortest match from beginning
echo ${path#*/}            # home/user/documents/report.tar.gz

# Longest match from beginning
echo ${path##*/}           # report.tar.gz (basename equivalent)

# Shortest match from end
echo ${path%.*}            # /home/user/documents/report.tar

# Longest match from end
echo ${path%%.*}           # /home/user/documents/report

# Practical examples
filename="script.sh.bak"
echo "${filename%.bak}"    # script.sh
echo "${filename%%.*}"     # script
echo "${filename#*.}"      # sh.bak

# Remove prefix/suffix patterns
var="Hello_World"
echo "${var#*_}"           # World
echo "${var%_*}"           # Hello
```

### Search and Replace

```bash
str="foo bar foo baz foo"

# Replace first occurrence
echo "${str/foo/FOO}"      # FOO bar foo baz foo

# Replace all occurrences
echo "${str//foo/FOO}"     # FOO bar FOO baz FOO

# Replace at beginning
echo "${str/#foo/FOO}"     # FOO bar foo baz foo

# Replace at end
echo "${str/%foo/FOO}"     # foo bar foo baz FOO

# Delete pattern (replace with nothing)
echo "${str//foo}"         # bar baz
```

### Case Modification (Bash 4.0+)

```bash
str="Hello World"

# Uppercase first character
echo "${str^}"             # Hello World (H already uppercase)

str="hello world"

# Uppercase first character
echo "${str^}"             # Hello world

# Uppercase all characters matching pattern
echo "${str^^[a-m]}"      # Hello World  (H, l→L not matched since l>a-m... wait)

# Actually let me be more careful:
str="hello world"
echo "${str^^}"            # HELLO WORLD (all uppercase)
echo "${str^}"             # Hello world (first char uppercase)

# Lowercase
str="HELLO WORLD"
echo "${str,}"             # hELLO WORLD (first char lowercase)
echo "${str,,}"            # hello world (all lowercase)

# Toggle case (Bash 4.4+)
echo "${str~}"             # hELLO WORLD (toggle first char case)
echo "${str~~}"            # hello world (toggle all chars case)
```

### Indirect Reference

```bash
varname="HOME"
echo "${!varname}"         # /home/user (value of $HOME)

# Dynamic variable names
for i in 1 2 3; do
    declare "var_$i=$((i * 10))"
done
echo "${var_1} ${var_2} ${var_3}"  # 10 20 30
```

### Variable Transformation (Bash 4.4+)

```bash
# Quote special characters
str="hello world & goodbye"
echo "${var@Q}"            # 'hello world & goodbye'

# Escape for re-use as input
echo "${var@E}"            # expanded form

# Properly quoted for shell re-entry
echo "${var@A}"            # var='hello world & goodbye'
```

## Process Substitution

Process substitution allows a command's input or output to appear as a file. It bridges the gap between pipelines and file-based operations.

### Output Process Substitution `>(command)`

```bash
# Write to two commands simultaneously
echo "Hello World" | tee >(tr '[:lower:]' '[:upper:]') >(wc -w)
# Creates temp file descriptors like /dev/fd/63

# Practical: log and process simultaneously
exec > >(tee -a /var/log/myscript.log) 2>&1
echo "This goes to both stdout and log file"

# Compare outputs of two commands
diff <(ls /dir1) <(ls /dir2)

# Sort two files and merge
sort -m <(sort file1.txt) <(sort file2.txt)
```

### Input Process Substitution `<(command)`

```bash
# Feed command output as a file to another command
while IFS= read -r line; do
    echo "Processing: $line"
done < <(grep -v '^#' /etc/hosts)

# Compare two directories
diff <(ls -la /tmp/dir1) <(ls -la /tmp/dir2)

# Multiple sorted inputs
paste <(cut -d: -f1 /etc/passwd) <(cut -d: -f3 /etc/passwd)

# Read from multiple sources
cat <(head -5 /var/log/syslog) <(tail -5 /var/log/syslog)

# Compare command outputs
comm <(sort file1) <(sort file2)
```

### Combining Process Substitutions

```bash
# Three-way comparison
diff3 <(sort file1) <(sort file2) <(sort file3)

# Merge multiple log files sorted by timestamp
sort -t' ' -k1,2 <(grep "ERROR" /var/log/app.log) \
                  <(grep "ERROR" /var/log/syslog)

# Complex data pipeline
join -t, <(sort -t, -k1 data1.csv) <(sort -t, -k1 data2.csv)
```

### Process Substitution Internals

```
┌─────────────────────────────────────────────┐
│  Process Substitution Internals              │
├─────────────────────────────────────────────┤
│                                             │
│  diff <(ls dir1) <(ls dir2)                 │
│                                             │
│  Bash creates:                               │
│  1. Named pipe (FIFO) or /dev/fd/N          │
│  2. Subprocess for each >(cmd) or <(cmd)    │
│  3. Passes path to main command              │
│                                             │
│  Internally translates to:                   │
│  /dev/fd/63  →  (ls dir1)                   │
│  /dev/fd/62  →  (ls dir2)                   │
│  diff /dev/fd/63 /dev/fd/62                 │
│                                             │
│  On Linux: uses /dev/fd → symlink to pipe   │
│  On systems without /dev/fd: uses FIFOs     │
└─────────────────────────────────────────────┘
```

## Arithmetic Evaluation

Bash provides multiple ways to perform arithmetic:

```bash
# Arithmetic expansion $((...))
echo $((2 + 3))           # 5
echo $((10 / 3))          # 3 (integer division)

# Arithmetic command ((...))
((count++))
((total += 5))
if ((x > 10)); then ...; fi

# Variables in arithmetic context (no $ needed)
x=10; y=3
echo $((x + y))           # 13
echo $((x ** y))          # 1000 (exponentiation)
echo $((x % y))           # 1 (modulo)

# Bitwise operations
echo $((0xff & 0x0f))     # 15
echo $((1 << 4))          # 16

# Ternary operator
max=$((a > b ? a : b))

# Arithmetic with assignment
((x *= 2))
((x <<= 3))

# Base conversion
echo $((16#ff))           # 255 (hex to decimal)
echo $((2#1010))          # 10  (binary to decimal)
printf '%x\n' 255         # ff  (decimal to hex via printf)

# let command (similar to (()))
let "result = 5 * 3"
let "count++"
```

## Readline Library

GNU Readline provides line-editing capabilities for Bash and other programs. It supports Emacs (default) and Vi editing modes.

### Emacs Mode Keybindings

```bash
# Movement
Ctrl+A          # Beginning of line
Ctrl+E          # End of line
Alt+F           # Forward one word
Alt+B           # Backward one word
Ctrl+F          # Forward one character
Ctrl+B          # Backward one character

# Editing
Ctrl+D          # Delete character at cursor
Ctrl+K          # Kill from cursor to end of line
Ctrl+U          # Kill from cursor to beginning of line
Ctrl+W          # Kill word before cursor
Alt+D           # Kill word after cursor
Ctrl+Y          # Yank (paste) from kill ring
Alt+Y           # Cycle through kill ring (after Ctrl+Y)

# History
Ctrl+R          # Reverse incremental search
Ctrl+P          # Previous command (↑)
Ctrl+N          # Next command (↓)
Alt+.           # Last argument of previous command
Ctrl+G          # Abort search/edit

# Transposition
Ctrl+T          # Transpose characters
Alt+T           # Transpose words

# Case
Alt+U           # Uppercase word
Alt+L           # Lowercase word
Alt+C           # Capitalize word
```

### Vi Mode

```bash
# Enable vi mode
set -o vi

# In insert mode:
# Esc        → switch to command mode
# In command mode:
# h/j/k/l    → movement (left/down/up/right)
# w/b/e      → word movement
# dd         → delete line
# yy         → yank (copy) line
# p          → paste
# /pattern   → search history
```

### Custom Readline Configuration (`~/.inputrc`)

```bash
# ~/.inputrc

# Enable case-insensitive completion
set completion-ignore-case on

# Show all matches if ambiguous
set show-all-if-ambiguous on

# Color completion by file type
set colored-stats on

# Append '/' to directory names on completion
set mark-directories on
set mark-symlinked-directories on

# Show common prefix first
set show-all-if-unmodified on

# Vi mode
#set editing-mode vi

# Custom bindings
"\C-p": history-search-backward
"\C-n": history-search-forward

# Alt+Shift+J to cd .. (custom)
"\ej": "cd ..\n"

# Bind Ctrl+Alt+E to edit current command in $EDITOR
"\e\C-e": "\C-x\C-e"
```

### Programmable Completion

```bash
# Simple completion function
_ssh_hosts() {
    local hosts
    hosts=$(awk '/^Host / {print $2}' ~/.ssh/config 2>/dev/null)
    COMPREPLY=($(compgen -W "$hosts" "${COMP_WORDS[1]}"))
}
complete -F _ssh_hosts ssh

# Completion with options
_mycommand() {
    local cur prev opts
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--help --version --output --verbose"

    case "${prev}" in
        --output)
            COMPREPLY=($(compgen -f -- "$cur"))
            return 0
            ;;
    esac

    COMPREPLY=($(compgen -W "$opts" -- "$cur"))
}
complete -F _mycommand mycommand

# Load completions from /etc/bash_completion.d/
source /etc/bash_completion
```

## Traps and Signal Handling

Traps allow scripts to respond to signals and other events, enabling graceful cleanup.

### Signal List

```bash
# Display available signals
$ kill -l
 1) SIGHUP       2) SIGINT       3) SIGQUIT      4) SIGILL
 5) SIGTRAP      6) SIGABRT      7) SIGBUS       8) SIGFPE
 9) SIGKILL     10) SIGUSR1     11) SIGSEGV     12) SIGUSR2
13) SIGPIPE     14) SIGALRM     15) SIGTERM     16) SIGSTKFLT
17) SIGCHLD     18) SIGCONT     19) SIGSTOP     20) SIGTSTP
21) SIGTTIN     22) SIGTTOU     23) SIGURG      24) SIGXCPU
25) SIGXFSZ     26) SIGVTALRM   27) SIGPROF     28) SIGWINCH
29) SIGIO       30) SIGPWR      31) SIGSYS
```

### Basic Trap Usage

```bash
# Cleanup on exit
trap 'rm -f /tmp/myapp.$$' EXIT

# Handle Ctrl+C
trap 'echo "Interrupted!"; exit 1' INT

# Handle termination
trap 'echo "Terminated!"; cleanup; exit 1' TERM

# Ignore a signal
trap '' HUP

# Reset trap to default
trap - INT

# Multiple signals
trap cleanup EXIT INT TERM

# Debug trap (executed before each command)
trap 'echo "Executing: $BASH_COMMAND"' DEBUG

# ERR trap (executed on command failure)
trap 'echo "Error on line $LINENO"; exit 1' ERR

# RETURN trap (executed when function/script returns)
trap 'echo "Returning from function"' RETURN
```

### Practical Trap Patterns

```bash
#!/bin/bash
# Robust trap handling with cleanup

CLEANUP_DONE=0

cleanup() {
    if (( CLEANUP_DONE )); then
        return
    fi
    CLEANUP_DONE=1

    echo "Cleaning up..."
    # Remove temporary files
    rm -f "$TEMP_FILE" "$LOCK_FILE"
    # Release lock
    [ -f "$LOCK_FILE" ] && rm -f "$LOCK_FILE"
    # Kill background jobs
    jobs -p | xargs -r kill 2>/dev/null
    echo "Cleanup complete."
}

trap cleanup EXIT
trap 'echo "Caught SIGINT"; exit 130' INT
trap 'echo "Caught SIGTERM"; exit 143' TERM

# Create temp file
TEMP_FILE=$(mktemp /tmp/myapp.XXXXXX)
LOCK_FILE="/var/lock/myapp.lock"

# Ensure lock file is created
touch "$LOCK_FILE"

# Main logic
echo "Running..."
sleep 100 &
wait
```

### Trap with Pseudo-Signal Names

```bash
# EXIT: runs when shell exits (most common)
trap 'echo "Goodbye!"' EXIT

# ERR: runs on non-zero exit (with set -e)
set -e
trap 'echo "Command failed at line $LINENO: $BASH_COMMAND"' ERR

# DEBUG: runs before every command (use with caution — performance impact)
trap 'printf "+ %s\n" "$BASH_COMMAND"' DEBUG

# RETURN: runs when function or sourced script returns
trap 'echo "Function returned"' RETURN
```

## Bash Options and Shell Settings

### `set` Options (POSIX)

```bash
set -e          # Exit on error
set -u          # Error on undefined variables
set -o pipefail # Pipeline returns rightmost non-zero exit code
set -x          # Print commands before execution (trace)
set -f          # Disable globbing
set -n          # Read commands but don't execute (syntax check)
set -C          # Prevent overwrite on redirection (noclobber)
set -a          # Auto-export all variables

# Combined
set -euo pipefail

# Long options
set -o errexit      # same as -e
set -o nounset      # same as -u
set -o pipefail     # see scripting-advanced.md
set -o xtrace       # same as -x
set -o noclobber    # same as -C
set -o vi           # vi editing mode
set -o emacs        # emacs editing mode (default)

# Check current options
echo $-              # himBhs (flags)
set -o               # shows all options and their on/off state
```

### `shopt` Options (Bash-Specific)

```bash
shopt -s extglob       # Enable extended globbing
shopt -s globstar      # Enable ** recursive glob
shopt -s nullglob      # Expand non-matching globs to nothing
shopt -s failglob      # Error on non-matching globs
shopt -s dotglob       # Include dotfiles in globs
shopt -s nocasematch   # Case-insensitive pattern matching
shopt -s checkwinsize  # Update LINES/COLUMNS on window resize
shopt -s histappend    # Append to history instead of overwrite
shopt -s cmdhist       # Save multi-line commands as single entry
shopt -s lithist       # Save with embedded newlines
shopt -s dirspell      # Correct directory spelling on cd
shopt -s cdspell       # Correct minor spelling errors in cd
shopt -s hostcomplete  # Complete hostnames on @
shopt -s complete_fullquote  # Quote all special chars in completions
shopt -s interactive_comments  # Allow # comments in interactive shell

# Disable option
shopt -u extglob

# Query option
shopt -p globstar      # shopt -s globstar
```

## Command History

```bash
# History expansion
!!              # Last command
!n              # Command number n
!-n             # n commands ago
!string         # Last command starting with string
!?string        # Last command containing string
!$              # Last argument of previous command
!^              # First argument of previous command
!*              # All arguments of previous command

# Substitution
!!:s/old/new    # Replace first occurrence in last command
^old^new^       # Quick substitution (same as !!:s/old/new)
!!:gs/old/new   # Global substitution

# History configuration
HISTSIZE=10000          # Commands in memory
HISTFILESIZE=20000      # Lines in history file
HISTFILE=~/.bash_history
HISTCONTROL=ignoreboth  # Ignore duplicates and space-prefixed
HISTIGNORE="ls:cd:pwd:exit:bg:fg:history"
HISTTIMEFORMAT="%F %T " # Timestamp format

# Useful settings
shopt -s histappend     # Don't overwrite history file
shopt -s cmdhist        # Save multi-line commands
```

## Bash-Specific Features

### Extended Globbing (`extglob`)

```bash
shopt -s extglob

# ?(pattern) - 0 or 1 occurrence
ls *.?(tar.)gz           # matches .gz and .tar.gz

# *(pattern) - 0 or more occurrences
echo *(foo)              # empty, foo, foofoo, foofoofoo, ...

# +(pattern) - 1 or more occurrences
rm +(backup).*           # matches backup.*, backup.*, backup.*, ...

# @(pattern) - exactly one
echo @(foo|bar)          # foo or bar

# !(pattern) - anything except
ls !(*.o|*.d)            # everything except .o and .d files

# Practical examples
# Match files NOT ending in .bak
rm !(*.bak)

# Match version numbers
[[ "1.2.3" == +([0-9]).+([0-9]).+([0-9]) ]] && echo "version"
```

### Coprocesses

```bash
# Start a coprocess
coproc myproc { while read line; do echo "Got: $line"; done; }

# Write to coprocess stdin
echo "hello" >&"${myproc[1]}"

# Read from coprocess stdout
read -r response <&"${myproc[0]}"
echo "$response"   # Got: hello

# Close the coprocess
exec {myproc[1]}>&-
wait "$myproc_PID"
```

### Built-in String Manipulation

```bash
# Case conversion (Bash 4.0+)
str="Hello World"
echo "${str^^}"    # HELLO WORLD
echo "${str,,}"    # hello world
echo "${str^}"     # Hello World

# Search and replace
echo "${str//o/0}"  # Hell0 W0rld

# Pattern removal
file="archive.tar.gz"
echo "${file%.gz}"     # archive.tar
echo "${file%%.*}"     # archive
echo "${file#*.}"      # tar.gz
```

### `mapfile` / `readarray`

```bash
# Read file into array
mapfile -t lines < /etc/passwd
echo "Users: ${#lines[@]}"

# Skip first 2 lines
mapfile -t -s 2 lines < /etc/passwd

# Read only 5 lines
mapfile -t -n 5 lines < /etc/passwd

# With callback
mapfile -t -c 1 -C 'echo "Read: $line"' lines < /etc/passwd

# Process substitution
mapfile -t sorted < <(sort /etc/passwd)
```

### Here Strings

```bash
# Feed string to command stdin
cat <<< "Hello World"
grep "pattern" <<< "Search in this string"
read -r first rest <<< "Hello World Bash"
echo "$first"   # Hello
echo "$rest"    # World Bash

# Arithmetic with here string
bc <<< "scale=4; 22/7"
```

## Debugging Bash Scripts

```bash
# Syntax check without execution
bash -n script.sh

# Trace execution (print each command)
bash -x script.sh

# Selective tracing
set -x          # Enable trace
# ... code to debug ...
set +x          # Disable trace

# Debug trap
trap 'printf "%s:%d: %s\n" "$BASH_SOURCE" "$LINENO" "$BASH_COMMAND"' DEBUG

# Custom debug function
DEBUG=1
debug() {
    if (( DEBUG )); then
        printf "DEBUG [%s:%d] %s\n" "${BASH_SOURCE[1]}" "${BASH_LINENO[0]}" "$*" >&2
    fi
}

debug "Processing file: $filename"
```

## Best Practices

1. **Always quote variables**: `"$var"` not `$var`
2. **Use `[[ ]]` over `[ ]`** for conditionals
3. **Set `set -euo pipefail`** in scripts
4. **Use `printf` over `echo`** for portable output
5. **Use `read -r`** to prevent backslash interpretation
6. **Prefer `${var:-default}`** over inline conditionals
7. **Use `local` variables** in functions
8. **Check `shellcheck`** for common mistakes
9. **Use `mktemp`** for temporary files
10. **Always trap EXIT** for cleanup

## Cross-References

- [Shell Scripting Fundamentals](scripting-fundamentals.md) — Variables, conditionals, loops, and functions
- [Advanced Shell Scripting](scripting-advanced.md) — Traps, subshells, coprocesses, and strict mode
- [Regular Expressions](regex.md) — Pattern matching in Bash and tools
- [sed and awk](sed-awk.md) — Text processing with stream editors

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [GNU Bash Manual](https://www.gnu.org/software/bash/manual/bash.html) — Official reference
- [Bash Hackers Wiki](https://wiki.bash-hackers.org/) — Community knowledge base
- [The Art of Command Line](https://jvns.ca/blog/2024/02/03/the-art-of-command-line/) — Julia Evans' guide
- [BashGuide](https://mywiki.wooledge.org/BashGuide) — Greg's Wiki
- [ShellCheck](https://www.shellcheck.net/) — Static analysis for shell scripts
- [Advanced Bash-Scripting Guide](https://tldp.org/LDP/abs/html/) — TLDP comprehensive guide
- [Pure Bash Bible](https://github.com/dylanaraps/pure-bash-bible) — Pure bash alternatives to external commands
