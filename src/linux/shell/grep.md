# grep: Text Search

## Introduction

`grep` (Global Regular Expression Print) is one of the most fundamental UNIX tools, searching input for lines matching a pattern. Named after the `ed` command `g/re/p` (global/regular expression/print), it's the go-to tool for text search in shell pipelines. This chapter covers BRE, ERE, recursive search, context lines, performance, and modern alternatives like ripgrep.

## Basic Usage

```bash
# Search for a pattern in a file
grep "pattern" file.txt

# Search multiple files
grep "error" *.log

# Search stdin
cat file.txt | grep "pattern"

# Case-insensitive
grep -i "error" logfile.txt

# Show line numbers
grep -n "TODO" source.c

# Invert match (lines NOT matching)
grep -v "debug" logfile.txt

# Count matching lines
grep -c "error" logfile.txt

# Show only matching part
grep -o "error [0-9]*" logfile.txt

# List files with matches
grep -l "pattern" *.txt

# List files without matches
grep -L "pattern" *.txt
```

## Regular Expressions

### BRE (Basic Regular Expressions)

The default mode uses POSIX Basic Regular Expressions:

```bash
# Literal characters
grep "hello" file.txt

# Anchors
grep "^start" file.txt     # Start of line
grep "end$" file.txt       # End of line
grep "^$" file.txt          # Empty lines

# Quantifiers (BRE: no ?, +, or |)
grep "ab*" file.txt         # a followed by zero or more b
grep "ab\{2,4\}" file.txt   # a followed by 2-4 b's

# Character classes
grep "[aeiou]" file.txt     # Any vowel
grep "[^aeiou]" file.txt    # Not a vowel
grep "[0-9]" file.txt       # Any digit
grep "[a-zA-Z]" file.txt   # Any letter

# Special characters in BRE
grep "." file.txt           # Any single character
grep "\." file.txt          # Literal dot (escape required)

# BRE quantifiers summary
grep "ab*" file.txt         # zero or more b
grep "ab\{2\}" file.txt    # exactly 2 b
grep "ab\{2,\}" file.txt   # 2 or more b
grep "ab\{2,5\}" file.txt  # 2 to 5 b
```

### ERE (Extended Regular Expressions)

With `-E` or `egrep`, use Extended Regular Expressions:

```bash
# ERE: no escaping needed for ?, +, |, {}, ()
grep -E "ab?" file.txt          # a followed by optional b
grep -E "ab+" file.txt          # a followed by one or more b
grep -E "a|b" file.txt          # a or b
grep -E "(foo|bar)" file.txt    # foo or bar
grep -E "ab{2,4}" file.txt     # a followed by 2-4 b's (no escaping)

# ERE vs BRE comparison
# BRE                          ERE
grep "ab\{2\}" file.txt       grep -E "ab{2}" file.txt
grep "ab\{2,4\}" file.txt     grep -E "ab{2,4}" file.txt
# No ? or + in BRE             grep -E "ab?" file.txt
# No | in BRE                  grep -E "a|b" file.txt
# No () grouping in BRE        grep -E "(foo|bar)" file.txt
```

### POSIX Character Classes

```bash
# POSIX character classes (portable, work in BRE and ERE)
grep "[[:alnum:]]" file.txt    # Alphanumeric
grep "[[:alpha:]]" file.txt    # Alphabetic
grep "[[:digit:]]" file.txt    # Digits
grep "[[:lower:]]" file.txt    # Lowercase
grep "[[:upper:]]" file.txt    # Uppercase
grep "[[:space:]]" file.txt    # Whitespace
grep "[[:punct:]]" file.txt    # Punctuation
grep "[[:print:]]" file.txt    # Printable characters
grep "[[:blank:]]" file.txt    # Space and tab
grep "[[:xdigit:]]" file.txt   # Hex digits

# Combining classes
grep "[[:alpha:][:digit:]]" file.txt  # Letters and digits

# Word boundaries (GNU grep)
grep -w "word" file.txt        # Match whole word only
grep "\bword\b" file.txt       # Same (GNU extension)
```

## Context Lines

```bash
# Show N lines before match
grep -B 3 "error" logfile.txt

# Show N lines after match
grep -A 5 "error" logfile.txt

# Show N lines before and after
grep -C 2 "error" logfile.txt

# Example output
$ grep -C 2 "FATAL" /var/log/syslog
Jul 21 16:59:58 host kernel: [12345.678] INFO: normal operation
Jul 21 17:00:01 host app[1234]: Processing request
Jul 21 17:00:02 host app[1234]: FATAL: connection refused
Jul 21 17:00:03 host app[1234]: Retrying connection
Jul 21 17:00:04 host app[1234]: Connection restored
```

## Recursive Search

```bash
# Search recursively through directories
grep -r "pattern" /path/to/dir

# Follow symbolic links
grep -r "pattern" /path/to/dir -R  # or --dereference-recursive

# Include specific file types
grep -r --include="*.py" "import os" /path/to/dir

# Exclude directories
grep -r --exclude-dir=".git" "TODO" /path/to/dir

# Exclude specific files
grep -r --exclude="*.o" "function" /path/to/dir

# Multiple patterns
grep -r --include="*.py" --include="*.js" "async" /path/to/dir
```

## Output Control

```bash
# Show only matching filenames
grep -l "error" *.log

# Show only non-matching filenames
grep -L "error" *.log

# Count matches per file
grep -c "error" *.log

# Show only matching text
grep -o "error [0-9]*" logfile.txt

# Null-separated output (for xargs -0)
grep -rlZ "pattern" /path/ | xargs -0 rm

# Color output
grep --color=auto "pattern" file.txt
# or set GREP_OPTIONS:
export GREP_COLOR='1;32'  # Bold green

# Binary file handling
grep -a "pattern" binary_file    # Treat binary as text
grep -I "pattern" /path/         # Skip binary files
```

## Advanced Features

### Multiple Patterns

```bash
# OR: multiple patterns (ERE)
grep -E "error|warning|fatal" logfile.txt

# OR: basic pattern (BRE)
grep "error\|warning\|fatal" logfile.txt

# AND: multiple patterns (grep chain)
grep "error" logfile.txt | grep "critical"

# AND: single pattern with lookaround (PCRE, GNU grep -P)
grep -P "(?=.*error)(?=.*critical)" logfile.txt

# Pattern file
grep -f patterns.txt logfile.txt
```

### Fixed Strings

```bash
# Treat pattern as fixed string (no regex)
grep -F "exact.match" file.txt     # . is literal
grep -F "$variable" file.txt       # No regex interpretation
fgrep "pattern" file.txt           # Deprecated alias

# Multiple fixed patterns
grep -F -e "pattern1" -e "pattern2" file.txt
```

### Perl-Compatible Regular Expressions (PCRE)

```bash
# GNU grep supports -P for PCRE
grep -P "\d{3}-\d{4}" file.txt    # Phone numbers
grep -P "(?i)error" file.txt      # Case-insensitive (inline flag)
grep -P "foo(?=bar)" file.txt     # Positive lookahead
grep -P "foo(?!bar)" file.txt     # Negative lookahead
grep -P "(?<=foo)bar" file.txt    # Positive lookbehind
grep -P "(?<!foo)bar" file.txt    # Negative lookbehind

# Non-greedy matching (PCRE only)
grep -P '"[^"]*"' file.txt        # Greedy: match longest
grep -P '"[^"]*?"' file.txt       # Non-greedy: match shortest
```

## grep in Pipelines

```bash
# Find processes
ps aux | grep "[n]ginx"   # Pattern trick: exclude grep itself

# Count lines
wc -l < <(grep "pattern" file.txt)

# Sort and deduplicate
grep "error" logfile.txt | sort | uniq -c | sort -rn

# Extract fields
grep "ERROR" app.log | awk '{print $3, $5}'

# Process substitution
diff <(grep "old" file1) <(grep "new" file2)

# Multi-stage filtering
cat server.log | \
    grep -i "error" | \
    grep -v "DEBUG" | \
    grep -E "[0-9]{4}-[0-9]{2}" | \
    sort | uniq -c | sort -rn | head -20
```

## Performance Tips

### Use Fixed Strings When Possible

```bash
# Slow: regex engine
grep "exact.string" large_file.txt

# Fast: literal string matching (Boyer-Moore)
grep -F "exact.string" large_file.txt
```

### Use LC_ALL for Speed

```bash
# Faster: skip locale-aware character classification
LC_ALL=C grep "pattern" file.txt
```

### Limit Output

```bash
# Stop after first match
grep -m 1 "pattern" file.txt

# Stop after N matches
grep -m 10 "pattern" file.txt
```

### Parallel grep

```bash
# GNU parallel with grep
find /path -name "*.log" | parallel -j8 grep -l "error" {}

# xargs with parallel
find /path -name "*.log" -print0 | xargs -0 -P8 grep -l "error"
```

### Avoid Unnecessary Features

```bash
# Slow: line numbers (must scan all preceding lines)
grep -n "pattern" large_file.txt

# Faster: just list files
grep -l "pattern" large_file.txt

# Slow: recursive with many exclusions
grep -r --exclude-dir=.git --exclude-dir=node_modules "pattern" .

# Faster: use find + xargs
find . -not -path '*/.git/*' -not -path '*/node_modules/*' \
    -name "*.py" -print0 | xargs -0 grep -F "pattern"
```

## ripgrep: Modern Alternative

[ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) is a modern grep replacement that's faster and more user-friendly:

### Installation

```bash
# Install
sudo apt install ripgrep        # Debian/Ubuntu
brew install ripgrep             # macOS
cargo install ripgrep            # From source (Rust)
```

### Basic Usage

```bash
# Search current directory recursively (respects .gitignore)
rg "pattern"

# Search specific file
rg "pattern" file.txt

# Case insensitive
rg -i "pattern"

# Fixed string
rg -F "exact.string"

# Show line numbers
rg -n "pattern"

# Show only filenames
rg -l "pattern"

# Count matches
rg -c "pattern"
```

### ripgrep Advantages

```bash
# 1. Respects .gitignore by default
# Skips .git/, node_modules/, etc.
rg "TODO"   # Only searches tracked files

# 2. Faster than grep (Rust, parallel, memory-mapped)
time rg "pattern" large_file.txt
time grep "pattern" large_file.txt
# rg is typically 2-10x faster

# 3. Better defaults
rg "pattern"            # Recursive, color, line numbers
rg -t py "import"       # By file type
rg -T js "pattern"      # Exclude file type

# 4. File type filtering
rg -t py "def main"     # Python files
rg -t rs "fn main"      # Rust files
rg -t sh "set -e"       # Shell scripts
rg --type-list           # Show all types

# 5. Smart case
rg -S "error"           # Case insensitive if lowercase
rg -S "Error"           # Case sensitive if has uppercase

# 6. PCRE2 support
rg -P "\d{3}-\d{4}"    # Perl regex
```

### ripgrep vs grep

| Feature | grep | ripgrep |
|---|---|---|
| Speed | Good | Excellent (2-10x faster) |
| .gitignore | No | Yes (default) |
| Recursive | `-r` flag | Default |
| Line numbers | `-n` flag | Default |
| Color | `--color=auto` | Default |
| File types | `--include` | `-t` / `-T` |
| PCRE | `-P` (GNU) | `-P` (built-in) |
| Unicode | Locale-dependent | Built-in |
| Encoding | Locale-dependent | Auto-detect |
| Platform | Everywhere | Cross-platform (Rust) |

### When to Use Each

```bash
# Use grep when:
# - Scripting for maximum portability
# - Simple one-file search
# - On minimal/embedded systems
# - Using POSIX BRE/ERE features

# Use ripgrep when:
# - Searching codebases (respects .gitignore)
# - Speed matters
# - Interactive use
# - Working with Unicode
```

## GNU grep vs BSD grep

| Feature | GNU grep | BSD grep (macOS) |
|---|---|---|
| PCRE (`-P`) | ✅ | ❌ |
| `--include` | ✅ | ❌ (use find) |
| `--exclude-dir` | ✅ | ❌ (use find) |
| `-o` (only matching) | ✅ | ✅ |
| `\b` (word boundary) | ✅ | ❌ |
| `-m` (max count) | ✅ | ✅ |
| Color | `--color=auto` | `--color=auto` |

```bash
# Portable alternatives for missing features
# Instead of grep -r --include="*.py":
find . -name "*.py" -exec grep -H "pattern" {} +

# Instead of \b:
grep -w "word" file.txt    # POSIX word boundary

# macOS: install GNU grep
brew install grep          # Installs as ggrep
```

## Practical Examples

### Log Analysis

```bash
# Find all errors in last hour
grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" /var/log/app.log | grep -i error

# Count errors by type
grep -oE "ERROR: [A-Z_]+" app.log | sort | uniq -c | sort -rn

# Find slow queries (> 1000ms)
grep -oP "query_time: \K[0-9]+" slow.log | awk '$1 > 1000' | wc -l

# Extract IP addresses
grep -oE "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" access.log | sort | uniq -c | sort -rn
```

### Code Search

```bash
# Find function definitions
grep -n "def \|function " *.py *.js

# Find TODO/FIXME comments
grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.{py,js,c,h}"

# Find unused imports (simple case)
grep "^import " file.py | while read -r line; do
    module=$(echo "$line" | awk '{print $2}')
    count=$(grep -c "$module" file.py)
    [ "$count" -eq 1 ] && echo "Unused: $line"
done

# Find duplicate lines
sort file.txt | uniq -d
```

### Configuration File Search

```bash
# Find non-comment, non-empty lines
grep -Ev "^\s*(#|$)" /etc/nginx/nginx.conf

# Find active configuration
grep -Ev "^\s*#" /etc/ssh/sshd_config | grep -Ev "^\s*$"

# Find values for a key
grep -E "^\s*server_name" /etc/nginx/sites-enabled/*
```

## grep Exit Codes

```bash
grep "pattern" file.txt
# Exit code 0: match found
# Exit code 1: no match found
# Exit code 2: error (file not found, etc.)

# Use in scripts
if grep -q "error" logfile.txt; then
    echo "Errors found"
fi

# Suppress errors
grep -s "pattern" nonexistent.txt  # No error message

# Count vs exit code
grep -c "pattern" file.txt    # Prints count, exit 0 if > 0
grep -q "pattern" file.txt    # No output, exit 0 if match

# Multiple files: exit 0 if ANY file has match
grep -l "pattern" *.txt      # Lists matching files, exit 0 if any
```

## Binary File Handling

```bash
# Default: binary files are skipped or matched as "Binary file matches"
grep "pattern" file.bin

# Treat binary as text
grep -a "pattern" file.bin
grep --text "pattern" file.bin

# Search binary for strings
strings file.bin | grep "pattern"

# Skip binary files entirely
grep -I "pattern" /path/
grep --binary-files=without-match "pattern" /path/

# Search specific bytes in binary
grep -P -bo "\x89PNG" image.png    # Show byte offset of match
```

## grep with Multibyte/Unicode

```bash
# grep respects locale settings
LC_ALL=en_US.UTF-8 grep "café" file.txt

# Byte matching (ignore locale)
LC_ALL=C grep '[\x80-\xff]' file.txt  # Non-ASCII bytes

# Match Unicode characters
grep -P '\x{00E9}' file.txt           # é (Unicode)
grep -P '\p{Han}' file.txt            # Chinese characters
grep -P '\p{Emoji}' file.txt          # Emoji (PCRE2)

# Portable Unicode matching
grep '[[:alpha:]]' file.txt           # Works in any locale
```

## Common grep Mistakes

```bash
# 1. Forgetting to escape regex metacharacters
grep "file.txt" log        # . matches any character
grep "file\.txt" log       # Correct: literal dot

# 2. Not quoting patterns
grep *.txt file             # Shell expands *.txt first!
grep "*.txt" file           # Correct: pass pattern to grep

# 3. Using grep for fixed strings (use -F)
grep "192.168.1.1" log     # . matches any char
grep -F "192.168.1.1" log  # Correct: literal match

# 4. Grepping ps output (matches itself)
ps aux | grep nginx         # Shows grep process too
ps aux | grep "[n]ginx"     # Correct: excludes grep
pgrep nginx                 # Better: use pgrep

# 5. Not using -r for directories
grep "pattern" /path/       # Error: is a directory
grep -r "pattern" /path/    # Correct

# 6. Losing line context with -o
grep -o "error" log         # Just "error", no context
grep -o ".*error.*" log     # Whole line with error

grep -B2 -A2 "error" log   # Better: use context lines

# 7. Forgetting -- for end of options
grep -e "pattern" -- -file.txt  # File named -file.txt
grep "pattern" -- -file.txt     # Also works
```

## References

- [grep(1) man page](https://man7.org/linux/man-pages/man1/grep.1.html)
- [GNU grep manual](https://www.gnu.org/software/grep/manual/)
- [ripgrep documentation](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)
- [POSIX Regular Expressions](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html)
- [Regular-Expressions.info](https://www.regular-expressions.info/)
- [POSIX grep specification](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/grep.html)

## Related Topics

- [find](./find.md) — file search (complementary to grep)
- [xargs](./xargs.md) — argument processing for grep pipelines
- [POSIX Shell](./posix-shell.md) — portable grep usage
- [Regular Expressions](./regex.md) — pattern syntax reference
