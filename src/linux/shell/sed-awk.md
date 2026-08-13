# sed and awk

`sed` (stream editor) and `awk` (named after Aho, Weinberger, and Kernighan) are the two most important text-processing tools in the Linux ecosystem. Together they form the backbone of command-line data manipulation, log analysis, configuration file editing, and report generation. This chapter covers both tools in depth with practical examples.

## sed — The Stream Editor

`sed` reads input line by line, applies editing commands, and writes the result to stdout. It is non-interactive and ideal for scripted transformations.

### How sed Works

```
┌─────────────────────────────────────────────────────┐
│  sed Processing Model                                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Input ──► Read line ──► Pattern Space ──► Apply    │
│  Stream     into memory    (working copy)   commands │
│                                                     │
│                     │                               │
│                     ▼                               │
│              Hold Space                              │
│              (temp storage)                          │
│                                                     │
│                     │                               │
│                     ▼                               │
│              Output Stream                           │
│              (stdout or -i file)                     │
└─────────────────────────────────────────────────────┘
```

### Basic sed Syntax

```bash
sed [OPTIONS] 'COMMAND' [FILE...]
sed [OPTIONS] -e 'CMD1' -e 'CMD2' [FILE...]
sed [OPTIONS] -f SCRIPT [FILE...]
```

### Essential Options

```bash
sed -n 'command' file        # Suppress default output (print only what's asked)
sed -i 'command' file        # Edit file in-place
sed -i.bak 'command' file   # In-place with backup
sed -E 'command' file        # Use ERE instead of BRE
sed -e 'cmd1' -e 'cmd2' file # Multiple commands
sed '{cmd1;cmd2}' file       # Multiple commands (alternative)
sed -f script.sed file       # Read commands from file
```

### The `s` Command (Substitution)

The most commonly used sed command:

```bash
# Basic syntax: s/pattern/replacement/flags

# Replace first occurrence per line
sed 's/old/new/' file

# Replace all occurrences on each line
sed 's/old/new/g' file

# Case-insensitive replacement
sed 's/old/new/gi' file

# Print only modified lines
sed -n 's/old/new/p' file

# Use different delimiters
sed 's|/usr/local|/opt|g' file     # pipe
sed 's#/usr/local#/opt#g' file     # hash
sed 's@old@new@g' file             # at sign

# Backreferences in replacement
echo "hello world" | sed -E 's/(\w+) (\w+)/\2 \1/'
# Output: world hello

# Use & for matched text
echo "123" | sed 's/[0-9]*/(&)/'
# Output: (123)

# Multiple substitutions
sed -e 's/foo/bar/g' -e 's/baz/qux/g' file
sed 's/foo/bar/g; s/baz/qux/g' file
```

### sed Addresses

Addresses control which lines a command applies to:

```bash
# Line number
sed '5s/old/new/' file              # Only line 5
sed '3,7s/old/new/' file            # Lines 3 through 7
sed '3,+4s/old/new/' file           # Line 3 and next 4 lines

# First N lines
sed '1,10d' file                     # Delete first 10 lines

# Every Nth line (step)
sed '0~2d' file                      # Delete every 2nd line (even lines)
sed '1~2d' file                      # Delete every 2nd line starting at 1 (odd)

# Regex address
sed '/pattern/s/old/new/' file       # Lines matching pattern
sed '/^#/d' file                     # Delete comment lines
sed '/^$/d' file                     # Delete blank lines

# Negated address
sed '/pattern/!s/old/new/' file      # Lines NOT matching pattern
sed '3!s/old/new/' file              # All lines except line 3

# Range with regex
sed '/start/,/end/s/old/new/' file   # Between patterns

# Range with line number and regex
sed '1,/^$/d' file                   # Delete from start to first blank line
```

### sed Commands Reference

#### Delete (`d`)

```bash
# Delete specific lines
sed '1d' file                # Delete first line
sed '$d' file                # Delete last line
sed '3,5d' file              # Delete lines 3-5
sed '/pattern/d' file        # Delete matching lines
sed '/^#/d' file             # Delete comments
sed '/^$/d' file             # Delete empty lines
sed '1,10d' file             # Delete first 10 lines
```

#### Print (`p`)

```bash
# Print specific lines (with -n)
sed -n '5p' file             # Print only line 5
sed -n '3,7p' file           # Print lines 3-7
sed -n '/pattern/p' file     # Print matching lines
sed -n '/start/,/end/p' file # Print between patterns

# Print line numbers
sed -n '/pattern/=' file     # Print line numbers of matches
```

#### Insert and Append (`i`, `a`)

```bash
# Insert before line
sed '1i\# Header added by script' file

# Append after line
sed '$a\# Footer added by script' file

# Insert before pattern
sed '/pattern/i\New line before' file

# Append after pattern
sed '/pattern/a\New line after' file
```

#### Change (`c`)

```bash
# Replace entire line
sed '3c\New content for line 3' file

# Replace matching lines
sed '/pattern/c\Replacement line' file
```

#### Transform (`y`)

```bash
# Character-by-character translation (like tr)
sed 'y/abc/ABC/' file        # a→A, b→B, c→C
sed 'y/ABCDEFGHIJKLMNOPQRSTUVWXYZ/abcdefghijklmnopqrstuvwxyz/' file  # to lowercase
```

#### Working with Multiple Lines

```bash
# N: Append next line to pattern space
sed 'N;s/\n/ /' file         # Join pairs of lines

# P: Print up to newline in pattern space
sed 'N;P;D' file             # Sliding window of 2 lines

# D: Delete up to newline in pattern space
sed '/pattern/{N;D}' file    # Delete matching line and next

# Hold space commands
# h: Copy pattern space to hold space
# H: Append pattern space to hold space
# g: Copy hold space to pattern space
# G: Append hold space to pattern space
# x: Exchange pattern and hold spaces

# Reverse file (tac equivalent)
sed -n '1!G;h;$p' file

# Print last line only
sed -n '$p' file

# Delete last line
sed '$d' file
```

### Practical sed Examples

```bash
# Remove comments and blank lines
sed '/^#/d; /^$/d' config.conf

# Add line numbers
sed = file | sed 'N; s/\n/\t/'

# Extract lines between two patterns
sed -n '/START/,/END/p' file

# Replace in specific line range
sed '10,20s/old/new/g' file

# Remove trailing whitespace
sed 's/[[:space:]]*$//' file

# Remove leading whitespace
sed 's/^[[:space:]]*//' file

# Double-space a file
sed 'G' file

# Triple-space a file
sed 'G;G' file

# Comment out a line
sed -i 's/^#Port 22/Port 2222/' /etc/ssh/sshd_config

# Add prefix to each line
sed 's/^/PREFIX: /' file

# Convert Windows line endings
sed 's/\r$//' file

# Extract section from config file
sed -n '/^\[section\]/,/^\[/p' config.ini | sed '$d'

# Replace multi-line pattern
sed -N 's/\n/ /g' file       # Join all lines

# Insert file contents at pattern
sed '/pattern/r insert.txt' file
```

### sed Scripting

```bash
# Multi-command sed script
cat > transform.sed <<'EOF'
# Remove comments
/^#/d

# Remove blank lines
/^$/d

# Normalize whitespace
s/[[:space:]]\+/ /g

# Trim
s/^ //; s/ $

# Add header
1i\Name,Value
EOF

sed -f transform.sed data.txt
```

## awk — Pattern Processing

`awk` is a complete programming language designed for text processing. It excels at field-based data manipulation.

### awk Program Structure

```
┌─────────────────────────────────────────────────────┐
│  awk Program Structure                               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  awk 'pattern { action }' file                      │
│                                                     │
│  For each input line:                                │
│  1. Read line into $0                                │
│  2. Split into fields: $1, $2, ..., $NF             │
│  3. Test pattern                                     │
│  4. If pattern matches, execute action               │
│  5. Print $0 if no action specified                  │
│                                                     │
│  Special patterns:                                   │
│  BEGIN { }    → Before first line                    │
│  END { }      → After last line                      │
└─────────────────────────────────────────────────────┘
```

### Basic awk Usage

```bash
# Print entire line
awk '{print}' file
awk '{print $0}' file

# Print specific fields
awk '{print $1, $3}' file    # Fields 1 and 3

# Print last field
awk '{print $NF}' file

# Print second-to-last field
awk '{print $(NF-1)}' file

# Print with custom separator
awk -F: '{print $1, $3}' /etc/passwd

# Multiple field separators
awk -F'[,;]' '{print $1}' file

# Regex field separator
awk -F'[:/]+' '{print $1, $2}' file
```

### awk Patterns

```bash
# Regular expression
awk '/error/ {print}' file

# Negated regex
awk '!/debug/ {print}' file

# Field matching
awk '$1 ~ /^[0-9]+$/ {print}' file

# Comparison
awk '$3 > 100 {print $1, $3}' file
awk '$1 == "root" {print}' /etc/passwd

# Range patterns
awk '/start/,/end/ {print}' file

# Line number
awk 'NR == 5 {print}' file     # Line 5
awk 'NR >= 3 && NR <= 7' file  # Lines 3-7

# Combine patterns
awk '/error/ && $3 > 50 {print}' file
awk '/error/ || /warning/ {print}' file

# BEGIN and END
awk 'BEGIN {print "Start"} {print} END {print "End"}' file
```

### awk Variables

```bash
# Built-in variables
NR      # Number of records (lines) read so far
NF      # Number of fields in current record
FS      # Input field separator (default: whitespace)
OFS     # Output field separator (default: space)
RS      # Input record separator (default: newline)
ORS     # Output record separator (default: newline)
FILENAME # Current input filename
ARGC    # Argument count
ARGV    # Argument array
OFMT    # Output format for numbers (default: %.6g)
CONVFMT # Conversion format (default: %.6g)
SUBSEP  # Subscript separator (default: \034)

# Examples
awk 'BEGIN {FS=":"; OFS=","} {print $1, $3}' /etc/passwd
awk '{print NR, $0}' file          # Add line numbers
awk 'END {print NR}' file          # Count lines
awk '{print NF, $0}' file          # Show field count
```

### awk Actions and Statements

```bash
# Print
awk '{print $1}' file
awk '{printf "%-20s %5d\n", $1, $3}' file

# Variables
awk '{sum += $3} END {print sum}' file
awk '{count++} END {print count}' file

# Conditionals
awk '{if ($3 > 50) print $1, "HIGH"; else print $1, "LOW"}' file

# Loops
awk '{for (i=1; i<=NF; i++) print $i}' file     # One field per line
awk 'BEGIN {for (i=1; i<=10; i++) print i}'      # Numbers 1-10

# Arrays
awk '{words[$1]++} END {for (w in words) print w, words[w]}' file

# Delete array element
awk '{a[$1]=$2} END {delete a["skip"]; for (k in a) print k, a[k]}' file
```

### awk Functions

#### String Functions

```bash
length(s)           # String length
substr(s, i, n)     # Substring starting at i, length n
index(s, t)         # Position of t in s (0 if not found)
split(s, a, sep)    # Split s into array a by sep
sub(r, s, t)        # Replace first match in t
gsub(r, s, t)       # Replace all matches in t
match(s, r)         # Match regex r in s
sprintf(fmt, ...)   # Formatted string
tolower(s)          # Lowercase
toupper(s)          # Uppercase

# Examples
awk '{print length($0)}' file                    # Line lengths
awk '{print substr($1, 1, 3)}' file              # First 3 chars of field 1
awk '{n=split($0, a, ":"); print n}' file        # Count fields
awk '{gsub(/[0-9]+/, "NUM"); print}' file        # Replace numbers
```

#### Math Functions

```bash
int(x)          # Truncate to integer
sqrt(x)         # Square root
exp(x)          # e^x
log(x)          # Natural logarithm
sin(x), cos(x)  # Trigonometric
atan2(y, x)     # Arctangent
srand(seed)     # Seed random number generator
rand()          # Random number [0, 1)

# Examples
awk '{print int($3 * 1.5)}' file
awk 'BEGIN {srand(); print rand()}'               # Random number
awk '{sum+=$1; sumsq+=$1*$1} END {print "avg:", sum/NR, "stddev:", sqrt(ssq/NR - (sum/NR)^2)}' file
```

### awk Arrays

```bash
# Associative arrays (default)
awk '{count[$1]++} END {for (word in count) print word, count[word]}' file

# Multi-dimensional (simulated with SUBSEP)
awk '{a[$1,$2]++} END {for (key in a) {split(key, k, SUBSEP); print k[1], k[2], a[key]}}' file

# Sorting array traversal (GNU awk)
awk '{a[$1]++} END {
    n = asorti(a, sorted)
    for (i=1; i<=n; i++) print sorted[i], a[sorted[i]]
}' file

# Check if key exists
awk '{if ($1 in seen) print "dup:", $1; seen[$1]=1}' file

# Delete array elements
awk '{a[$1]=$2} END {for (k in a) if (a[k] == 0) delete a[k]; for (k in a) print k, a[k]}' file
```

### awk Control Structures

```bash
# if/else
awk '{
    if ($3 > 100)
        print $1, "high"
    else if ($3 > 50)
        print $1, "medium"
    else
        print $1, "low"
}' file

# for loop
awk '{for (i=1; i<=NF; i++) if ($i ~ /error/) print NR, $i}' file

# while loop
awk '{
    i = 1
    while (i <= NF) {
        if (length($i) > 20) print NR, "long field:", $i
        i++
    }
}' file

# do-while
awk 'BEGIN {
    do {
        print "Enter value: "; getline val
    } while (val != "quit")
}'

# break and continue
awk '{
    for (i=1; i<=NF; i++) {
        if ($i == "skip") continue
        if ($i == "stop") break
        print $i
    }
}' file

# next — skip to next record
awk '/^#/ {next} {print}' file      # Skip comments

# nextfile — skip to next file
awk 'FNR == 1 && /^#!/ {nextfile} {print}' *.sh  # Skip shebang lines

# exit — terminate awk
awk '/CRITICAL/ {print; exit} {print}' file
```

### awk User-Defined Functions

```bash
# Function definition
awk '
function abs(x) {
    return (x < 0) ? -x : x
}
function max(a, b) {
    return (a > b) ? a : b
}
{
    print abs($1), max($1, $2)
}' file

# Function with local variables
awk '
function stats(arr, n,    i, sum, sumsq) {
    sum = 0; sumsq = 0
    for (i = 1; i <= n; i++) {
        sum += arr[i]
        sumsq += arr[i] * arr[i]
    }
    avg = sum / n
    stddev = sqrt(sumsq/n - avg*avg)
    printf "avg=%.2f stddev=%.2f\n", avg, stddev
}
{a[NR] = $1}
END {stats(a, NR)}
' file

# Recursive function
awk '
function factorial(n) {
    if (n <= 1) return 1
    return n * factorial(n - 1)
}
BEGIN { print factorial(10) }
'
```

### awk with Multiple Files

```bash
# Process multiple files
awk '{print FILENAME, $0}' file1 file2 file3

# File-specific processing
awk '
FILENAME == "config" { config[$1] = $2; next }
FILENAME == "data" && $1 in config { print $0, config[$1] }
' config data

# NR vs FNR
awk '{print "NR="NR, "FNR="FNR, $0}' file1 file2
# NR counts across all files; FNR resets per file
```

### GNU awk (gawk) Extensions

```bash
# BEGINFILE and ENDFILE
awk 'BEGINFILE {print "=== " FILENAME " ==="} {print}' *.txt

# Directories
awk '@include "filefuncs"'
awk '@load "time"'

# Network connections (gawk 4.0+)
awk 'BEGIN {
    server = "/inet/tcp/8080/0/0"
    while (1) {
        server |& getline request
        print "HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nHello" |& server
        close(server)
    }
}'

# Two-way I/O (|)
awk 'BEGIN {
    cmd = "sort"
    print "banana" |& cmd
    print "apple" |& cmd
    print "cherry" |& cmd
    close(cmd, "to")
    while ((cmd |& getline line) > 0) print line
    close(cmd)
}'
```

## Common One-Liners

### File Operations

```bash
# Number lines
awk '{print NR, $0}' file
cat -n file                        # Alternative

# Remove duplicate lines (preserve order)
awk '!seen[$0]++' file

# Remove duplicate lines (sorted)
sort -u file

# Print lines between patterns
sed -n '/START/,/END/p' file
awk '/START/,/END/' file

# Print first N lines
sed -n '1,10p' file
awk 'NR <= 10' file
head -10 file

# Print last N lines
tail -10 file

# Print line N
sed -n '5p' file
awk 'NR == 5' file

# Print every Nth line
awk 'NR % 3 == 0' file            # Every 3rd line

# Print longest line
awk '{if (length > max) {max = length; line = $0}} END {print line}' file

# Print line with max value in column
awk 'BEGIN {max=-999999} {if ($3 > max) {max=$3; line=$0}} END {print line}' file
```

### Field Processing

```bash
# Extract column
awk '{print $2}' file
cut -d' ' -f2 file                # Alternative

# Swap columns
awk '{print $2, $1}' file

# Sum column
awk '{sum += $1} END {print sum}' file

# Average column
awk '{sum += $1; n++} END {print sum/n}' file

# Frequency count
awk '{count[$1]++} END {for (k in count) print k, count[k]}' file

# Sort by column
sort -t' ' -k2 -n file            # sort by 2nd column, numeric

# Join lines with same first field
awk '{if ($1 == prev) printf ", %s", $2; else {if (NR>1) print ""; printf "%s: %s", $1, $2}; prev=$1} END {print ""}' file

# Transpose rows and columns
awk '{
    for (i=1; i<=NF; i++) a[i][NR] = $i
    if (NF > maxnf) maxnf = NF
}
END {
    for (i=1; i<=maxnf; i++) {
        for (j=1; j<=NR; j++)
            printf "%s%s", a[i][j], (j<NR ? OFS : "\n")
    }
}' file
```

### Log Analysis

```bash
# Count errors by hour
awk '/ERROR/ {split($3, t, ":"); hour[t[1]]++} END {for (h in hour) print h, hour[h]}' access.log | sort

# Top 10 IPs
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -10

# Response time statistics
awk '{
    times[$7] += $NF
    counts[$7]++
}
END {
    for (url in times)
        printf "%s avg=%.2fms count=%d\n", url, times[url]/counts[url], counts[url]
}' access.log

# Bandwidth per IP
awk '{bytes[$1] += $10} END {for (ip in bytes) printf "%s %.2fMB\n", ip, bytes[ip]/1048576}' access.log | sort -t' ' -k2 -rn

# Status code distribution
awk '{print $9}' access.log | sort | uniq -c | sort -rn

# Requests per minute
awk '{split($4, t, ":"); key = t[1]":"t[2]; count[key]++} END {for (k in count) print k, count[k]}' access.log | sort

# 404 errors with referrers
awk '$9 == 404 {print $7, $11}' access.log
```

### Configuration File Processing

```bash
# Extract ini section
awk '/^\[section\]/,/^\[/' config.ini | awk '!/^\[/'

# Convert ini to export statements
awk -F= '/^[^#[]/ && NF==2 {gsub(/^[ \t]+|[ \t]+$/, "", $1); gsub(/^[ \t]+|[ \t]+$/, "", $2); printf "export %s=\"%s\"\n", toupper($1), $2}' config.ini

# Remove comments and blank lines
awk '!/^#/ && !/^$/' file

# Extract key=value pairs
awk -F= 'NF==2 {print $1, $2}' config

# Merge two config files (second overrides first)
awk -F= 'NF==2 {a[$1]=$2} END {for (k in a) print k"="a[k]}' config1 config2
```

### Data Transformation

```bash
# CSV to TSV
awk -F, '{for(i=1;i<=NF;i++) printf "%s%s", $i, (i<NF?"\t":"\n")}' data.csv

# TSV to CSV
awk -F'\t' '{for(i=1;i<=NF;i++) printf "%s%s", $i, (i<NF?",":"\n")}' data.tsv

# Add header
awk 'BEGIN {print "Name,Age,Score"} {print}' data.csv

# Add footer
awk '{print} END {print "--- END OF FILE ---"}' data

# Conditional CSV processing
awk -F, '$3 > 100 && $2 == "active" {print $1, $4}' users.csv

# Pivot table
awk -F, '{
    row[$1] = row[$1] ? row[$1]","$3 : $3
    cols[$2] = 1
}
END {
    for (c in cols) printf ",%s", c
    print ""
    for (r in row) print r","row[r]
}' data.csv
```

### System Administration

```bash
# Process memory usage by user
ps aux | awk '{mem[$1]+=$6} END {for (u in mem) printf "%s %.2fMB\n", u, mem[u]/1024}' | sort -t' ' -k2 -rn

# Disk usage summary
df -h | awk 'NR>1 {gsub(/%/, "", $5); if ($5 > 80) print "WARNING:", $6, $5"% used"}'

# Network connections by state
ss -tan | awk 'NR>1 {state[$1]++} END {for (s in state) print s, state[s]}'

# Top processes by CPU
ps aux | awk 'NR>1 {print $3, $11}' | sort -rn | head -10

# User login summary
last | awk '{print $1}' | sort | uniq -c | sort -rn

# Parse /proc/meminfo
awk '/MemTotal|MemFree|MemAvailable|Buffers|Cached/ {
    gsub(/[^0-9]/, "", $2)
    printf "%-20s %8.1f MB\n", $1, $2/1024
}' /proc/meminfo
```

## Combining sed and awk

```bash
# sed for simple transformations, awk for complex logic
# Use pipes to combine them

# Example: parse log, transform, report
cat access.log \
    | sed 's/\[//g; s/\]//g' \
    | awk '{print $1, $4, $7, $9}' \
    | sort | uniq -c | sort -rn | head -20

# Example: config file manipulation
sed '/^#/d; /^$/d' config.conf \
    | awk -F= '{gsub(/^ +| +$/, "", $2); print $1, $2}' \
    | sort

# Example: extract and format
grep 'ERROR' app.log \
    | sed -E 's/.*\[([0-9-]+ [0-9:]+)\].*/\1/' \
    | awk '{split($2, t, ":"); print $1, t[1]":00"}' \
    | sort | uniq -c

# Use awk for processing, sed for output formatting
awk -F: '{print $1, $3, $7}' /etc/passwd \
    | sed 's/ /  |  /g' \
    | column -t
```

## Performance Considerations

```bash
# When to use what:

# sed: Simple, line-by-line transformations
# - Substitution, deletion, insertion
# - Single-pass processing
# - When you need in-place editing

# awk: Field-based processing with logic
# - Column extraction and manipulation
# - Aggregation and statistics
# - Conditional processing
# - Multi-file processing

# grep: Simple pattern matching
# - Finding lines matching a pattern
# - When you need speed (grep is fastest for simple searches)

# sort/uniq: Sorting and deduplication
# - Frequency counting
# - Ordering data
# - These are faster than awk for simple cases

# Performance tips:
# 1. grep first, then process (reduce data early)
grep 'ERROR' huge.log | awk '{print $1, $7}'   # Better than:
awk '/ERROR/ {print $1, $7}' huge.log           # grep is faster for simple patterns

# 2. Use LC_ALL=C for ASCII data
LC_ALL=C grep 'pattern' file    # Much faster for byte-level matching

# 3. Avoid unnecessary pipes
awk '{print $1}' file           # Better than:
cat file | awk '{print $1}'     # Useless use of cat

# 4. Use fixed strings when possible
grep -F 'fixed' file            # Faster than regex
```

## Cross-References

- [Bash](bash.md) — Using sed/awk output in scripts
- [Shell Scripting Fundamentals](scripting-fundamentals.md) — Quoting and variable expansion
- [Regular Expressions](regex.md) — BRE, ERE, and PCRE patterns used in sed/awk
- [Advanced Shell Scripting](scripting-advanced.md) — Complex text processing pipelines

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [sed Manual (GNU)](https://www.gnu.org/software/sed/manual/sed.html) — Official GNU sed documentation
- [gawk Manual (GNU)](https://www.gnu.org/software/gawk/manual/) — Official GNU awk documentation
- [The AWK Programming Language](https://ia800609.us.archive.org/10/items/pdfy-MgN0H1joIoDVoIC7/The_AWK_Programming_Language.pdf) — The original book by Aho, Weinberger, Kernighan
- [sed One-Liners Explained](https://catonmat.net/sed-one-liners-explained) — Peteris Krumins' collection
- [awk One-Liners Explained](https://catonmat.net/awk-one-liners-explained) — Peteris Krumins' collection
- [Effective awk Programming](https://www.oreilly.com/library/view/effective-awk-programming/9781491904930/) — Arnold Robbins' definitive guide
