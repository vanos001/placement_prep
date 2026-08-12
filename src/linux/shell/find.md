# find: File Search

## Introduction

`find` is the standard UNIX utility for searching directory trees based on various criteria: name, type, size, time, permissions, and more. It can also execute actions on matching files. This chapter covers predicates, actions, `-exec`, `xargs` integration, and modern alternatives like `fd`.

## Basic Syntax

```bash
find [path...] [expression]
```

The expression consists of **options**, **tests**, and **actions**, evaluated left-to-right with implicit AND.

```bash
# Find files by name
find /etc -name "*.conf"

# Find directories
find /var -type d -name "log*"

# Find in current directory
find . -name "*.txt"

# Multiple paths
find /home /tmp -name "*.bak"
```

## Tests (Predicates)

### Name and Path Tests

```bash
# Name matching
find . -name "*.txt"            # Case-sensitive glob
find . -iname "*.TXT"           # Case-insensitive
find . -name "*.txt" -o -name "*.md"  # OR

# Path matching
find . -path "*/src/*.py"       # Full path pattern
find . -ipath "*/SRC/*.py"      # Case-insensitive path
find . -wholename "*/src/*.py"  # Same as -path

# Regex matching (POSIX ERE)
find . -regex ".*\.\(py\|js\)$"
find . -iregex ".*\.py$"

# Name without leading directories
find . -name "README.md" -not -path "*/node_modules/*"
```

### Type Tests

```bash
find . -type f    # Regular file
find . -type d    # Directory
find . -type l    # Symbolic link
find . -type b    # Block device
find . -type c    # Character device
find . -type p    # Named pipe (FIFO)
find . -type s    # Socket

# Multiple types
find . \( -type f -o -type l \) -name "*.conf"
```

### Size Tests

```bash
find . -size +100M    # Larger than 100 MB
find . -size -1k      # Smaller than 1 KB
find . -size 0        # Empty files
find . -size +1G      # Larger than 1 GB

# Size suffixes:
# c  - bytes
# k  - kilobytes (1024)
# M  - megabytes
# G  - gigabytes

# Find largest files
find / -type f -size +100M -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh
```

### Time Tests

```bash
# Modified time
find . -mmin -30     # Modified in last 30 minutes
find . -mtime -7     # Modified in last 7 days
find . -mtime +365   # Modified more than 1 year ago
find . -newer file.txt  # Modified more recently than file.txt

# Access time
find . -amin -60     # Accessed in last 60 minutes
find . -atime -1     # Accessed in last 1 day

# Change time (inode change)
find . -cmin -30     # Changed in last 30 minutes
find . -ctime -7     # Changed in last 7 days

# Birth time (Linux 4.11+, GNU findutils 4.9+)
find . -newerBm -7   # Created in last 7 months

# Time comparison
find . -newer reference_file    # Modified after reference
find . -anewer reference_file   # Accessed after reference
find . -cnewer reference_file   # Changed after reference
```

### Permission and Ownership Tests

```bash
find . -perm 644        # Exact permissions
find . -perm -644       # At least these permissions (all must match)
find . -perm /644       # Any of these permissions (any must match)

# Symbolic notation
find . -perm -u+x       # User executable
find . -perm /a+w       # Anyone writable
find . -perm -g+w,o+w   # Group and other writable

# Ownership
find . -user john
find . -group developers
find . -nouser           # No valid user
find . -nogroup          # No valid group

# Find world-writable files
find / -type f -perm /002 2>/dev/null

# Find SUID/SGID files (security audit)
find / -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null
```

### Depth Tests

```bash
find . -maxdepth 1    # Only current directory (no recursion)
find . -maxdepth 3    # Up to 3 levels deep
find . -mindepth 2    # At least 2 levels deep
find . -mindepth 1 -maxdepth 3  # Between 1 and 3 levels

# Process directory contents before directory itself
find . -depth          # Depth-first traversal
```

## Logical Operators

```bash
# AND (implicit)
find . -type f -name "*.txt" -size +1M

# AND (explicit)
find . -type f -a -name "*.txt"

# OR
find . -name "*.txt" -o -name "*.md"

# NOT
find . -not -name "*.txt"
find . ! -name "*.txt"

# Grouping with parentheses (must be escaped)
find . \( -name "*.txt" -o -name "*.md" \) -size +1M

# Complex expression
find . \( -type f -name "*.log" \) -o \( -type d -name "tmp" \)

# Precedence: NOT > AND > OR
# Use parentheses to override
```

## Actions

### Print Actions

```bash
# Print (default action)
find . -name "*.txt"
find . -name "*.txt" -print     # Same as above

# Print0 (null-separated, for xargs -0)
find . -name "*.txt" -print0

# Printf
find . -name "*.txt" -printf "%p %s %t\n"   # path, size, time
find . -name "*.txt" -printf "%f\n"          # filename only
find . -name "*.txt" -printf "%h/%f\n"       # directory/file

# Printf format specifiers:
# %p  - full path
# %f  - filename (basename)
# %h  - directory (dirname)
# %s  - size in bytes
# %t  - modification time
# %u  - user name
# %g  - group name
# %m  - permissions (octal)
# %y  - type (f, d, l, etc.)
# \n  - newline
```

### Delete Action

```bash
# Delete matching files
find . -name "*.tmp" -delete

# Delete empty directories
find . -type d -empty -delete

# Safe delete: preview first
find . -name "*.tmp" -print    # Preview
find . -name "*.tmp" -delete   # Execute

# Delete with confirmation
find . -name "*.bak" -ok rm {} \;
```

### Execute Action

```bash
# Execute command for each file ({} is replaced with filename)
find . -name "*.txt" -exec cat {} \;

# With user confirmation (-ok instead of -exec)
find . -name "*.txt" -ok cat {} \;

# Multiple files per invocation (efficient)
find . -name "*.txt" -exec grep "pattern" {} +

# Show file details
find . -name "*.txt" -exec ls -lh {} \;

# Change permissions
find . -type f -name "*.sh" -exec chmod +x {} +

# Move files
find . -name "*.log" -exec mv {} /var/log/ \;

# Complex commands with -exec
find . -name "*.bak" -exec sh -c 'echo "Removing $1"; rm "$1"' _ {} \;
```

## Combining with xargs

### Safe Patterns

```bash
# CORRECT: null-separated (handles spaces, quotes, etc.)
find . -name "*.txt" -print0 | xargs -0 grep "pattern"

# WRONG: breaks on filenames with spaces
find . -name "*.txt" | xargs grep "pattern"

# Parallel execution
find . -name "*.txt" -print0 | xargs -0 -P4 grep "pattern"

# Limit arguments per invocation
find . -name "*.txt" -print0 | xargs -0 -n10 grep "pattern"

# With placeholder
find . -name "*.py" -print0 | xargs -0 -I{} cp {} /backup/
```

### Performance: -exec + vs xargs

```bash
# -exec + is similar to xargs but avoids the pipe
find . -name "*.txt" -exec grep "pattern" {} +

# xargs allows parallel execution
find . -name "*.txt" -print0 | xargs -0 -P8 grep "pattern"

# Benchmark comparison
time find . -name "*.txt" -exec grep -l "pattern" {} +
time find . -name "*.txt" -print0 | xargs -0 grep -l "pattern"
# Typically similar, but xargs -P wins with parallelism
```

## Practical Examples

### Cleanup

```bash
# Remove old temporary files
find /tmp -type f -mtime +7 -delete

# Remove empty directories
find . -type d -empty -delete

# Remove build artifacts
find . -name "*.o" -o -name "*.pyc" -o -name "__pycache__" -delete

# Find and remove .DS_Store files
find . -name ".DS_Store" -delete
```

### File Organization

```bash
# Find duplicate filenames
find . -type f -printf "%f\n" | sort | uniq -d

# Find files by extension
find . -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn

# Find recently modified files
find . -type f -mmin -60 -printf "%T+ %p\n" | sort -r

# Find large files
find . -type f -size +100M -printf "%s %p\n" | sort -rn | head -20

# Group files by size range
find . -type f -printf "%s\n" | awk '
    $1 < 1024          { tiny++ }
    $1 < 1048576       { small++ }
    $1 < 104857600     { medium++ }
    $1 >= 104857600    { large++ }
    END { print "Tiny:", tiny, "Small:", small, "Medium:", medium, "Large:", large }
'
```

### Security Auditing

```bash
# Find SUID/SGID binaries
find / -type f \( -perm -4000 -o -perm -2000 \) -ls 2>/dev/null

# Find world-writable files
find / -type f -perm -0002 -ls 2>/dev/null

# Find files with no owner
find / -nouser -o -nogroup 2>/dev/null

# Find files modified in the last 24 hours (potential compromise)
find / -type f -mtime -1 -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null

# Find hidden files in home directory
find ~ -name ".*" -type f -not -name ".bashrc" -not -name ".profile"
```

### Code Analysis

```bash
# Count lines of code by language
find . -name "*.py" -exec cat {} + | wc -l
find . -name "*.js" -not -path "*/node_modules/*" -exec cat {} + | wc -l

# Find TODO/FIXME comments
find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.c" \) \
    -exec grep -Hn "TODO\|FIXME\|HACK" {} +

# Find files with no newline at end
find . -type f -name "*.py" -exec sh -c '
    [ "$(tail -c 1 "$1" | wc -l)" -eq 0 ] && echo "$1"
' _ {} \;

# Find symlinks
find . -type l -ls
```

### Backup and Sync

```bash
# Find files changed today
find . -type f -mtime 0 -print0 | tar -czf today.tar.gz --null -T -

# Find files larger than 1MB for separate handling
find . -type f -size +1M -print0 | tar -czf large_files.tar.gz --null -T -

# Find and archive old logs
find /var/log -name "*.log.*" -mtime +30 -print0 | \
    xargs -0 tar -czf old_logs_$(date +%Y%m%d).tar.gz
```

## fd: Modern Alternative

[fd](https://github.com/sharkdp/fd) is a fast, user-friendly alternative to `find`:

### Installation

```bash
sudo apt install fd-find        # Debian/Ubuntu (binary: fdfind)
brew install fd                  # macOS
cargo install fd-find            # From source
```

### Basic Usage

```bash
# Simple search (regex by default)
fd "pattern"                    # Search current directory
fd "pattern" /path              # Search specific path

# Equivalent to find
fd -e txt                       # By extension (like -name "*.txt")
fd -t f                         # Files only
fd -t d                         # Directories only
fd -H                            # Include hidden files
fd -I                            # Don't respect .gitignore
fd -s                            # Case-sensitive
fd -S +1M                        # Size > 1MB
fd -E ".git"                     # Exclude pattern

# Execute commands
fd -e py -x python3 -c "
import ast, sys
for f in sys.argv[1:]:
    try: ast.parse(open(f).read())
    except: print(f'Syntax error: {f}')
" {}
```

### fd Advantages

```bash
# 1. Respects .gitignore by default
fd "pattern"    # Skips .git/, node_modules/, etc.

# 2. Colorized output
fd "pattern"    # Directories in blue, executables in green

# 3. Regex by default (no need for -regex)
fd "\.py$"      # Find Python files

# 4. Smart case
fd "readme"     # Case-insensitive (all lowercase)
fd "README"     # Case-sensitive (has uppercase)

# 5. Parallel execution
fd -e py -x wc -l {}    # Runs in parallel by default

# 6. Faster than find
time fd "pattern" /path
time find /path -name "*pattern*"
# fd is typically 5-10x faster
```

### find vs fd

| Feature | find | fd |
|---|---|---|
| Regex default | No (glob) | Yes |
| .gitignore | No | Yes (default) |
| Color output | No | Yes |
| Parallel exec | No (via xargs) | Yes (built-in) |
| Speed | Good | Excellent |
| Syntax | Verbose | Concise |
| POSIX | Yes | No |
| Install | Everywhere | Manual |

### When to Use Each

```bash
# Use find when:
# - Writing portable scripts
# - On minimal/embedded systems
# - Need POSIX compliance
# - Already available on system

# Use fd when:
# - Interactive use
# - Searching codebases
# - Speed matters
# - Want nicer defaults
```

## locate and mlocate

### Overview

`locate` searches a pre-built database of filenames, making it extremely fast but potentially outdated:

```bash
# Update the database (usually run via cron)
sudo updatedb

# Search
locate "*.conf"
locate -i "readme"       # Case-insensitive
locate -c "*.py"         # Count matches
locate -e "*.conf"       # Verify existence
```

### locate vs find

```bash
# locate: fast but potentially stale
time locate "*.conf"     # Very fast (~10ms)
# find: accurate but slow
time find / -name "*.conf"  # Slow (~30s)

# Use locate for quick lookups
# Use find for current state
```

### Security

```bash
# locate indexes ALL files (including those you can't read)
# Use mlocate for permission-aware indexing
sudo -u nobody locate secret.txt  # Only shows files nobody can read

# Plocate (modern replacement, faster)
sudo apt install plocate
```

## Complex Expressions

```bash
# Find files, exclude multiple directories, match multiple extensions
find . \
    -not -path "*/.git/*" \
    -not -path "*/node_modules/*" \
    -not -path "*/__pycache__/*" \
    \( -name "*.py" -o -name "*.js" -o -name "*.ts" \) \
    -type f \
    -printf "%s %p\n" | sort -rn

# Find and process with shell logic
find . -name "*.log" -print0 | while IFS= read -r -d '' file; do
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file")
    if [ "$size" -gt 104857600 ]; then
        echo "Large log: $file ($((size / 1048576))MB)"
        gzip "$file"
    fi
done

# Find files with specific content
find . -name "*.py" -exec grep -l "import os" {} +

# Find and rename (batch)
find . -name "*.jpeg" -exec sh -c 'mv "$1" "${1%.jpeg}.jpg"' _ {} \;
```

## find Limitations and Edge Cases

### Race Conditions

```bash
# TOCTOU (Time of Check, Time of Use) race condition
# find reads directory entries, then processes them
# Files can appear/disappear between those steps

# Safe pattern: check before action
find . -name "*.tmp" -print0 | while IFS= read -r -d '' file; do
    [ -f "$file" ] && rm "$file"  # Re-check existence
done

# find -delete is atomic enough for most uses
find . -name "*.tmp" -delete
```

### Symlink Handling

```bash
# Default: follow symlinks for tests only (not traversal)
find . -type l        # Find symlinks themselves
find . -type f        # Does NOT follow symlinks during traversal

# Follow symlinks during traversal
find -L . -type f     # Follow symlinks (careful with loops!)

# Find broken symlinks
find . -type l ! -exec test -e {} \; -print

# Find symlinks pointing to specific target
find . -type l -lname "*.conf"
```

### Filesystem Boundaries

```bash
# Stay on same filesystem (don't cross mount points)
find . -xdev -name "*.log"

# Practical: search root without /proc, /sys
find / -xdev -type f -name "*.conf" 2>/dev/null

# Cross filesystem boundaries (default behavior)
find / -name "*.conf" 2>/dev/null  # Searches all mounted filesystems
```

### Very Large Directory Trees

```bash
# Limit depth to avoid long searches
find / -maxdepth 4 -name "*.conf" 2>/dev/null

# Exclude expensive directories
find / -path /proc -prune -o -path /sys -prune -o -name "*.conf" -print

# Use -quit to stop after first match
find . -name "config.txt" -print -quit

# Parallel find for large trees
find / -maxdepth 3 -type d -print0 | xargs -0 -P8 -I{} find {} -maxdepth 1 -name "*.conf"
```

### find vs locate vs fd

```bash
# find: real-time, flexible, slow on large trees
find / -name "*.conf" 2>/dev/null    # ~30s on full system

# locate: pre-built database, very fast, may be stale
locate "*.conf"                        # ~10ms
sudo updatedb                          # Update database

# fd: modern, fast, respects .gitignore
fd "pattern"                           # ~5ms, parallel by default

# When to use each:
# find  → scripts, portability, precise current state
# locate → quick lookups, "where is that file?"
# fd    → interactive use, codebases, developer workflows
```

## References

- [find(1) man page](https://man7.org/linux/man-pages/man1/find.1.html)
- [GNU findutils manual](https://www.gnu.org/software/findutils/manual/)
- [fd documentation](https://github.com/sharkdp/fd/blob/master/README.md)
- [locate(1) man page](https://man7.org/linux/man-pages/man1/locate.1.html)
- [plocate](https://plocate.sesse.net/)
- [POSIX find specification](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/find.html)

## Related Topics

- [grep](./grep.md) — searching file contents
- [xargs](./xargs.md) — processing find output
- [POSIX Shell](./posix-shell.md) — portable find usage
- [Shell Overview](./overview.md) — shell fundamentals
