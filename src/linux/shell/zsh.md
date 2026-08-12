# Zsh (Z Shell)

## Introduction

Zsh (Z Shell) is an extended Bourne shell with many improvements over Bash: better tab completion, spell correction, themeable prompts, plugin architecture, and numerous small conveniences. It's the default shell on macOS (since Catalina) and is popular among developers for its productivity features.

## Key Features

### Superior Tab Completion

Zsh's completion system is its most celebrated feature:

```bash
# Basic completion
ls /u/l/b<TAB>
# Completes to /usr/local/bin/

# Partial completion
cd /u/lo/b<TAB>
# Completes to /usr/local/bin/

# Menu selection
cd <TAB>
# Shows interactive menu of directories

# Completion for commands
git ch<TAB>
# checkout  cherry-pick  cherry

# Completion with descriptions
git checkout <TAB>
# --conflict  -- style to use for conflicting hunks
# --detach    -- detach HEAD at named commit
# -f          -- force
```

### Configuration

```bash
# ~/.zshrc - Main configuration file

# History configuration
HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=100000
setopt HIST_IGNORE_DUPS       # Don't record duplicates
setopt HIST_IGNORE_SPACE      # Don't record lines starting with space
setopt HIST_FIND_NO_DUPS      # Don't show duplicates in search
setopt SHARE_HISTORY          # Share history between sessions
setopt EXTENDED_HISTORY       # Record timestamp

# Directory navigation
setopt AUTO_CD                # Type directory name to cd
setopt AUTO_PUSHD             # cd pushes to directory stack
setopt PUSHD_IGNORE_DUPS      # Don't push duplicates
setopt CDABLE_VARS            # cd to named directories

# Input/output
setopt CORRECT                # Spell correction for commands
setopt CORRECT_ALL            # Spell correction for arguments
setopt INTERACTIVE_COMMENTS   # Allow # comments in interactive shell
setopt NO_BEEP                # No beeps
```

## Oh My Zsh

Oh My Zsh is a framework for managing Zsh configuration:

### Installation

```bash
# Via curl
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

# Via wget
sh -c "$(wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O -)"

# Via package manager (some distros)
sudo apt install oh-my-zsh  # Not always available
```

### Directory Structure

```
~/.oh-my-zsh/
├── lib/              # Core functions
├── plugins/          # Bundled plugins
├── themes/           # Bundled themes
├── custom/           # User customizations
│   ├── plugins/      # Custom plugins
│   └── themes/       # Custom themes
└── templates/        # Templates
```

### Configuration

```bash
# ~/.zshrc with Oh My Zsh
export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="robbyrussell"  # or "agnoster", "powerlevel10k", etc.

plugins=(
    git
    docker
    kubectl
    zsh-autosuggestions
    zsh-syntax-highlighting
    zsh-completions
    history-substring-search
)

source $ZSH/oh-my-zsh.sh
```

## Popular Plugins

### Built-in Plugins

```bash
# Git aliases and functions
plugins=(git)
# Provides: gst, gco, gp, gl, gd, ga, gc, gb, etc.
# gco main    → git checkout main
# gst         → git status
# gcmsg "msg" → git commit -m "msg"

# Docker completion
plugins=(docker)
# docker <TAB> → full subcommand completion
# docker run <TAB> → image completion

# kubectl completion
plugins=(kubectl)
# kubectl get <TAB> → resource type completion
# kubectl get pods <TAB> → pod name completion

# History search
plugins=(history-substring-search)
# Use up/down arrows to search history with partial input
```

### External Plugins

```bash
# Install zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-autosuggestions \
    ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

# Install zsh-syntax-highlighting
git clone https://github.com/zsh-users/zsh-syntax-highlighting \
    ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting

# Install zsh-completions
git clone https://github.com/zsh-users/zsh-completions \
    ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-completions

# Add to .zshrc
plugins=(git zsh-autosuggestions zsh-syntax-highlighting zsh-completions)
```

### zsh-autosuggestions

Shows ghost text suggestions from history as you type:

```bash
# Accept suggestion: → (right arrow) or End
# Accept one word: Alt+F or Ctrl+→
# Clear suggestion: Esc

# Configuration
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=8"  # Dim gray
ZSH_AUTOSUGGEST_STRATEGY=(history completion)
ZSH_AUTOSUGGEST_BUFFER_MAX_SIZE=20
```

### zsh-syntax-highlighting

Real-time syntax highlighting:

```bash
# Commands are green
ls /tmp

# Unknown commands are red
nonexistent_command

# Strings are yellow
echo "hello world"

# Errors highlighted
echo "unterminated

# Configuration types
# main     - default
# brackets - matching brackets
# pattern  - pattern-based
# cursor   - cursor line
# line     - entire line
```

## Themes

### Powerlevel10k

The most popular Zsh theme:

```bash
# Install
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \
    ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k

# Set in .zshrc
ZSH_THEME="powerlevel10k/powerlevel10k"

# Run configuration wizard
p10k configure
```

### Theme Comparison

| Theme | Features | Speed |
|---|---|---|
| robbyrussell | Minimal, default | Fast |
| agnoster | Powerline, git info | Fast |
| powerlevel10k | Highly configurable, instant prompt | Fast |
| spaceship | Modular, many segments | Moderate |
| starship | Cross-shell, Rust-based | Fast |

### Custom Prompt

```bash
# Simple custom prompt
PROMPT='%F{green}%n@%m%f:%F{blue}%~%f$ '

# With git info
autoload -Uz vcs_info
precmd() { vcs_info }
zstyle ':vcs_info:git:*' formats '(%b)'
PROMPT='%F{green}%n%f:%F{blue}%~%f%F{yellow}${vcs_info_msg_0_}%f$ '

# Right prompt
RPROMPT='%F{gray}%D{%H:%M}%f'
```

## Vi Mode

Zsh has excellent vi mode support:

```bash
# Enable vi mode
bindkey -v

# Key timeout (for mode switching)
KEYTIMEOUT=1  # 10ms (default is 40ms)

# Vi mode status indicator
function zle-keymap-select {
    case $KEYMAP in
        vicmd) PROMPT='%F{blue} NORMAL%f $ ' ;;
        viins) PROMPT='%F{green} INSERT%f $ ' ;;
    esac
    zle reset-prompt
}
zle -N zle-keymap-select

# Useful bindings in insert mode
bindkey '^A' beginning-of-line
bindkey '^E' end-of-line
bindkey '^K' kill-line
bindkey '^R' history-incremental-search-backward
bindkey '^P' up-history
bindkey '^N' down-history

# Text objects (vi mode)
autoload -Uz select-bracketed select-quoted
zle -N select-bracketed
zle -N select-quoted
for m in viopp visual; do
    for c in {a,i}${(s..)^:-'()[]{}<>bB'}; do
        bindkey -M $m $c select-bracketed
    done
    for c in {a,i}{\',\",\`}; do
        bindkey -M $m $c select-quoted
    done
done
```

## Completion System

### Configuration

```bash
# Initialize completion system
autoload -Uz compinit
compinit -u  # -u: skip security check (faster)

# Completion styling
zstyle ':completion:*' menu select                    # Menu selection
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'  # Case insensitive
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
zstyle ':completion:*' group-name ''                  # Group by category
zstyle ':completion:*:descriptions' format '%F{yellow}-- %d --%f'
zstyle ':completion:*:warnings' format '%F{red}No matches%f'

# Completion caching
zstyle ':completion:*' use-cache on
zstyle ':completion:*' cache-path ~/.zsh/cache

# Kill process completion
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#)*=0=01;31'
zstyle ':completion:*:*:kill:*' menu yes select
zstyle ':completion:*:*:killall:*' menu yes select
```

### Custom Completion

```bash
# Define completion for a custom command
_mycommand() {
    local -a subcommands
    subcommands=(
        'start:Start the service'
        'stop:Stop the service'
        'restart:Restart the service'
        'status:Show service status'
    )

    _arguments \
        '1:command:->subcmds' \
        '2:arg:->args'

    case $state in
        subcmds) _describe 'command' subcommands ;;
        args)
            case $words[2] in
                start) _files ;;
                stop)  _pids ;;
            esac
    esac
}
compdef _mycommand mycommand
```

## History Features

```bash
# History search with arrows
bindkey '^[[A' history-search-backward   # Up arrow
bindkey '^[[B' history-search-forward    # Down arrow

# History substring search (with plugin)
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down

# Incremental search
bindkey '^R' history-incremental-search-backward

# History options
setopt HIST_IGNORE_ALL_DUPS    # Remove older duplicates
setopt HIST_REDUCE_BLANKS      # Remove leading/trailing spaces
setopt HIST_VERIFY             # Show command before executing
setopt INC_APPEND_HISTORY      # Write immediately, not on exit
```

## Useful Zsh Features

### Glob Qualifiers

```bash
# Files modified in last 24 hours
ls *(m-1)

# Files larger than 1MB
ls *(Lk+1000)

# Only regular files
ls *(.)

# Only directories
ls *(/)

# Symbolic links
ls *(@)

# Executable files
ls *(*)

# Empty files
ls *(L0)

# Sort by modification time
ls *(om)     # Newest first
ls *(Om)     # Oldest first

# Limit results
ls *(.[5])   # First 5 files
ls *(-5)     # Last 5 files
```

### Parameter Expansion

```bash
# Uppercase/lowercase
str="Hello World"
echo ${str:u}      # HELLO WORLD
echo ${str:l}      # hello world
echo ${str:u:0:1}  # H (first char uppercase)

# String length
echo ${#str}       # 11

# Array operations
arr=(one two three)
echo ${#arr[@]}    # 3
echo ${arr[-1]}    # three (last element)
echo ${arr[2,-2]}  # two (slice)

# Default values
echo ${var:-default}    # Use default if unset
echo ${var:=default}    # Assign default if unset
echo ${var:+alternate}  # Use alternate if set
```

### Named Directories

```bash
# Create named directory
hash -d projects=~/Documents/projects
hash -d downloads=~/Downloads

# Now you can use
cd ~projects
# or
ls ~downloads

# In prompts
PROMPT='%~$ '  # Shows named dirs as ~name
```

## Startup Files

Zsh reads startup files in a specific order, which differs from Bash:

### Startup File Order

```
┌──────────────────────────────────────────────────┐
│  Zsh Startup File Order                           │
├──────────────────────────────────────────────────┤
│                                                  │
│  1. /etc/zsh/zshenv      (system-wide, always)   │
│  2. ~/.zshenv             (user, always)          │
│  3. /etc/zsh/zprofile     (system, login)         │
│  4. ~/.zprofile           (user, login)           │
│  5. /etc/zsh/zshrc        (system, interactive)   │
│  6. ~/.zshrc              (user, interactive)     │
│  7. /etc/zsh/zlogin       (system, login)         │
│  8. ~/.zlogin             (user, login)           │
│  9. ~/.zlogout            (user, login exit)      │
│ 10. /etc/zsh/zlogout      (system, login exit)    │
└──────────────────────────────────────────────────┘
```

### What Goes Where

```bash
# ~/.zshenv — Always loaded (keep minimal)
# Environment variables
export EDITOR=vim
export PAGER=less

# ~/.zshrc — Interactive shell config
# Aliases, functions, prompt, plugins, completion
autoload -Uz compinit && compinit

# ~/.zprofile — Login-only (like .bash_profile)
# PATH setup, login-specific config
export PATH="$HOME/bin:$PATH"

# ~/.zlogin — After zshrc on login
# Commands to run at login
fortune

# ~/.zlogout — On login shell exit
clear
```

### Checking What's Loaded

```bash
# Show all startup files zsh would read
zsh -o SOURCE_TRACE -i -c exit 2>&1 | grep sourced

# Or use zprof
zmodload zsh/zprof
zprof
```

## Zsh Line Editor (ZLE)

ZLE provides powerful line-editing capabilities:

### Keymap Modes

```bash
# Default: emacs mode
bindkey -e

# Vi mode
bindkey -v

# Show current keybindings
bindkey -L        # List all bindings
bindkey -M emacs   # List emacs mode bindings
bindkey -M viins   # List vi insert mode bindings

# Bind a key
bindkey '^U' kill-whole-line          # Ctrl+U kills whole line
bindkey '^R' history-incremental-search-backward
bindkey '^P' up-history
bindkey '^N' down-history
bindkey '^A' beginning-of-line
bindkey '^E' end-of-line
```

### Custom Widgets

```bash
# Create a custom widget
my-widget() {
    LBUFFER+="Hello World"
}
zle -N my-widget
bindkey '^H' my-widget

# Edit command in editor
autoload -z edit-command-line
zle -N edit-command-line
bindkey '^X^E' edit-command-line

# Push line (save current input, execute something else)
bindkey '^Q' push-line-or-edit

# URL quoting
autoload -Uz url-quote-magic
zle -N self-insert url-quote-magic
```

### Bracketed Paste

```bash
# Zsh supports bracketed paste (prevents command execution on paste)
# Enabled by default in recent versions

# Disable if needed
# unset zle_bracketed_paste

# Paste safely — content is not interpreted until Enter
# This prevents malicious pasted commands from executing
```

## Arithmetic

Zsh supports both integer and floating-point arithmetic:

```bash
# Integer arithmetic (like Bash)
echo $((2 + 3))           # 5
echo $((10 / 3))          # 3

# Floating-point arithmetic (Zsh-specific!)
echo $((3.14 * 2))        # 6.28
echo $((10.0 / 3))        # 3.3333333333333335

# Variables in arithmetic
x=10; y=3
echo $((x ** y))          # 1000

# Math functions (requires zsh/mathfunc)
zmodload zsh/mathfunc
echo $(( sqrt(2.0) ))     # 1.4142135623730951
echo $(( sin(3.14159/2) )) # 1.0

# Arithmetic assignment
(( x = 5 + 3 ))
(( x += 10 ))
(( x++ ))

# Floating-point with typeset
typeset -F result=3.14
echo $result              # 3.1400000000

# Math with let
let "result = 5 * 3 + 2"
echo $result              # 17
```

## Spell Correction

Zsh can correct typos in commands and arguments:

```bash
# Enable command correction
setopt CORRECT

# Enable argument correction
setopt CORRECT_ALL

# Example interaction:
$ gti status
# zsh: correct 'gti' to 'git' [nyae]? y

# Correction behavior:
# y — accept correction
n — reject correction (execute as-is)
a — abort
# e — edit the command line

# Customize correction prompt
SPROMPT="zsh: correct '%R' to '%r'? [nyae] "

# Hash for directory spelling
cd /usrl/local     # Corrects to /usr/local
setopt CDABLE_VARS
correct_cd=true

# Ignore specific commands from correction
alias sudo='nocorrect sudo'
alias man='nocorrect man'
```

## Directory Stack

Zsh has an enhanced directory stack:

```bash
# Push directory
pushd /tmp
pushd /var/log
pushd /etc

# Show stack
dirs -v
# 0 /etc
# 1 /var/log
# 2 /tmp

# Pop directory
popd

# Navigate stack
cd ~1    # Go to stack entry 1

# AUTO_PUSHD: cd pushes automatically
setopt AUTO_PUSHD
setopt PUSHD_IGNORE_DUPS
cd /tmp
cd /var/log
cd /etc
dirs -v

# Push without changing
dirs -c    # Clear stack

# Named directories
hash -d proj=~/Documents/projects
cd ~proj
```

## Prompt Expansion

Zsh has extensive prompt escape sequences:

```bash
# Basic prompt escapes
PROMPT='%n@%m:%~$ '      # user@host:dir$
PROMPT='%F{green}%n%f@%F{blue}%m%f:%F{yellow}%~%f$ '

# Time and date
PROMPT='%D{%H:%M} %~$ '   # HH:MM dir$
PROMPT='%D{%Y-%m-%d} %~$ ' # YYYY-MM-DD dir$

# Exit status
PROMPT='%(?.%F{green}✓.%F{red}✗%?)%f %~$ '

# Git branch (with vcs_info)
autoload -Uz vcs_info
precmd() { vcs_info }
zstyle ':vcs_info:git:*' formats '(%b)'
PROMPT='%F{blue}%~%f%F{yellow}${vcs_info_msg_0_}%f$ '

# Conditional expressions
PROMPT='%(1j.%F{cyan}%j jobs%f .)%(?.%F{green}$.%F{red}$)%f '

# Right prompt
RPROMPT='%F{gray}%D{%H:%M}%f'

# Multiline prompt
PROMPT=$'\n%F{blue}%~%f\n%F{green}%(!.#.$)%f '

# Prompt escapes reference:
# %n  — username
# %m  — hostname (short)
# %M  — hostname (full)
# %~  — current dir (with ~ for home)
# %d  — current dir (full)
# %/  — current dir (full)
# %!  — history number
# %#  — # for root, % for normal
# %?  — exit status of last command
# %j  — number of jobs
# %D{fmt} — date/time
# %F{color} — start color
# %f  — reset color
# %B  — bold on
# %b  — bold off
# %U  — underline on
# %u  — underline off
```

## Zsh Scripting

Zsh has scripting features that differ from Bash:

### Arrays

```bash
# Zsh arrays are 1-indexed (not 0-indexed like Bash)
arr=(one two three)
echo $arr[1]         # one (first element)
echo $arr[2]         # two
echo $arr[-1]        # three (last element)
echo $arr[@]         # all elements
echo $#arr           # 3 (number of elements)

# Slice
echo $arr[2,3]       # two three

# Array operations
arr+=(four)          # Append
arr[2]=TWO           # Replace index 2

# Iterate
for item in $arr; do
    echo $item
done

# Associative arrays
typeset -A map
map[name]=Alice
map[age]=30
echo ${map[name]}
for key in ${(k)map}; do
    echo "$key: ${map[$key]}"
done
```

### String Operations

```bash
str="Hello World"

# Length
${#str}              # 11

# Substring (1-indexed)
${str[1,5]}          # Hello
${str[6,11]}         # World
${str[-5,-1]}        # World

# Case modification
${str:u}             # HELLO WORLD
${str:l}             # hello world
${str:u:0:1}         # H (first char uppercase)
${str:l:u}           # HELLO WORLD (lowercase then uppercase)

# Pattern removal
${str#* }            # World (remove shortest prefix up to space)
${str##* }           # World (remove longest prefix)
${str% *}            # Hello (remove shortest suffix from space)
${str%% *}           # Hello (remove longest suffix)

# Search and replace
${str/World/Zsh}     # Hello Zsh
${str//l/L}          # HeLLo WorLd (global)
```

### Zsh-Specific Conditionals

```bash
# Extended test (like [[ ]] in Bash)
[[ -f file && -r file ]]
[[ "$str" == pattern* ]]    # Pattern matching
[[ "$str" =~ regex ]]       # Regex matching

# Zsh-specific: glob qualifiers in conditionals
[[ -n *(N) ]]                # Any files exist?
[[ -f *.txt(N) ]]            # Any .txt files exist?

# Regular expression with capture groups
if [[ "$version" =~ '^([0-9]+)\.([0-9]+)\.([0-9]+)$' ]]; then
    echo "Major: $match[1]"    # Zsh uses $match array
    echo "Minor: $match[2]"
    echo "Patch: $match[3]"
fi
```

### Zsh Built-in Modules

```bash
# Load modules
zmodload zsh/mathfunc       # Math functions
zmodload zsh/complist        # Menu completion
zmodload zsh/parameter       # Parameter access
zmodload zsh/zprof           # Profiling
zmodload zsh/regex           # Regex support

# zsh/mathfunc
zmodload zsh/mathfunc
echo $(( sqrt(144) ))        # 12
echo $(( log(2.71828) ))     # ~1

# zsh/zprof — profile startup
zmodload zsh/zprof
# ... at end of .zshrc ...
zprof
```

## Zsh vs Bash

| Feature | Zsh | Bash |
|---|---|---|
| Tab completion | Superior, built-in | Good, with bash-completion |
| Autosuggestions | Plugin (zsh-autosuggestions) | Plugin (ble.sh) |
| Spell correction | Built-in (CORRECT) | ❌ |
| Glob qualifiers | `*(.)`, `*(m-1)`, `(Lk+1000)` | ❌ |
| Recursive glob | `**/*.txt` native | `shopt -s globstar` |
| Arrays | 1-indexed | 0-indexed |
| Associative arrays | ✅ | ✅ (Bash 4+) |
| Floating-point math | ✅ native `$((3.14*2))` | ❌ (need `bc`/`awk`) |
| Prompt themes | Oh My Zsh, p10k | Limited (PS1) |
| Plugin ecosystem | Oh My Zsh, zinit, antigen | bash-completion |
| Startup speed | ~80ms | ~40ms |
| Syntax highlighting | Plugin (zsh-syntax-highlighting) | ❌ |
| Regex captures | `$match` array | `$BASH_REMATCH` |
| String indexing | 1-based `${str[1]}` | 0-based `${str:0:1}` |
| Default on | macOS (since Catalina) | Most Linux distros |
| POSIX compliance | Mostly | Mostly (strict in `--posix` mode) |
| Line editor | ZLE (built-in) | Readline (library) |
| Hash/directory shortcuts | `hash -d name=path` | ❌ |
| Right prompt | `RPROMPT` | ❌ (limited via PS1 tricks) |

## Performance Optimization

```bash
# Lazy-load heavy plugins
zinit light zsh-users/zsh-autosuggestions

# Compile zsh files
zcompile ~/.zshrc
zcompile ~/.zsh_history

# Use turbo mode (zinit)
zinit ice wait lucid
zinit light zsh-users/zsh-syntax-highlighting

# Profile startup
time zsh -i -c exit
```

## References

- [Zsh Documentation](https://zsh.sourceforge.io/Doc/)
- [Oh My Zsh](https://ohmyz.sh/)
- [Zsh Users Guide](https://zsh.sourceforge.io/Guide/)
- [Powerlevel10k](https://github.com/romkatv/powerlevel10k)
- [Zsh Plugin Standard](https://zdharma-continuum.github.io/Zsh-Plugin-Standard/)
- [Zsh FAQ](https://zsh.sourceforge.io/FAQ/)
- [Zsh Mailing List Archive](https://www.zsh.org/mla/)
- [Awesome Zsh Plugins](https://github.com/unixorn/awesome-zsh-plugins)
- [zinit Wiki](https://zdharma-continuum.github.io/zinit/wiki/)

## Further Reading

- [From Bash to Zsh](https://scriptingosx.com/2019/06/moving-to-zsh/) — Migration guide
- [Zsh for Humans](https://github.com/romkatv/zsh4humans) — Opinionated Zsh framework
- [Prezto](https://github.com/sorin-ionescu/prezto) — Zsh configuration framework
- [antigen](https://github.com/zsh-users/antigen) — Plugin manager for Zsh

## Related Topics

- [Shell Overview](./overview.md) — shell types and fundamentals
- [Bash](./bash.md) — the most common Linux shell
- [Fish](./fish.md) — alternative modern shell
- [POSIX Shell](./posix-shell.md) — portable scripting
