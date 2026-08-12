# Regular Expressions

Regular expressions (regex) are a powerful pattern-matching language used throughout Linux for text searching, filtering, and transformation. This chapter covers the major regex dialects found in Linux tools: BRE (Basic Regular Expressions), ERE (Extended Regular Expressions), and PCRE (Perl-Compatible Regular Expressions), along with practical usage in grep, sed, awk, and Bash.

## What Are Regular Expressions?

A regular expression is a sequence of characters that defines a search pattern. Regex engines match these patterns against text, enabling powerful text processing that would be difficult or impossible with simple string comparison.

### Regex in the Linux Ecosystem

```
┌─────────────────────────────────────────────────────────┐
│  Regex Dialects in Linux                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  BRE (Basic)        ERE (Extended)     PCRE (Perl)      │
│  ─────────────      ───────────────    ─────────────    │
│  grep               grep -E            grep -P          │
│  sed                 egrep              pcregrep         │
│  vi/vim              awk                vim              │
│                      sed -E             PHP, Python      │
│                      bash =~            Perl             │
│                                                         │
│  ◄── Least features              Most features ──►     │
│  ◄── POSIX standard              De facto standard ──► │
└─────────────────────────────────────────────────────────┘
```

## BRE — Basic Regular Expressions

BRE is the default dialect for `grep` and `sed`. It is the most portable regex dialect, standardized by POSIX.

### BRE Metacharacters

| Character | Meaning | Example |
|-----------|---------|---------|
| `.` | Any single character | `a.c` matches `abc`, `aXc` |
| `*` | Zero or more of preceding | `ab*c` matches `ac`, `abc`, `abbc` |
| `^` | Start of line | `^Hello` matches lines starting with `Hello` |
| `$` | End of line | `end$` matches lines ending with `end` |
| `[]` | Character class | `[aeiou]` matches vowels |
| `[^]` | Negated class | `[^0-9]` matches non-digits |
| `\` | Escape metacharacter | `\.` matches literal dot |
| `\{m,n\}` | Repeat m to n times | `a\{2,4\}` matches `aa`, `aaa`, `aaaa` |
| `\( \)` | Grouping/capture | `\(ab\)*` matches `ab`, `abab` |
| `\1`-`\9` | Backreference | `\(.\)\1` matches `aa`, `bb` |

### BRE Character Classes

```bash
# POSIX bracket expressions (portable)
grep '[[:alpha:]]' file.txt       # alphabetic characters
grep '[[:digit:]]' file.txt       # digits
grep '[[:alnum:]]' file.txt       # alphanumeric
grep '[[:space:]]' file.txt       # whitespace
grep '[[:upper:]]' file.txt       # uppercase letters
grep '[[:lower:]]' file.txt       # lowercase letters
grep '[[:punct:]]' file.txt       # punctuation
grep '[[:print:]]' file.txt       # printable characters
grep '[[:blank:]]' file.txt       # space and tab only
grep '[[:cntrl:]]' file.txt       # control characters
grep '[[:graph:]]' file.txt       # visible characters
grep '[[:xdigit:]]' file.txt      # hex digits [0-9a-fA-F]

# Range in BRE
grep '[a-z]' file.txt             # lowercase
grep '[A-Z]' file.txt             # uppercase
grep '[0-9]' file.txt             # digits
grep '[a-zA-Z0-9]' file.txt      # alphanumeric

# Combining classes
grep '[[:alpha:][:digit:]_]' file.txt   # word characters
```

### BRE Examples

```bash
# Lines starting with "Error"
grep '^Error' /var/log/syslog

# Lines ending with ".log"
grep '\.log$' /etc/rsyslog.conf

# Empty lines
grep '^$' file.txt

# Lines with exactly 3 characters
grep '^.\{3\}$' file.txt

# Lines with 3 or more characters
grep '^.\{3,\}$' file.txt

# Match IP addresses (simplified)
grep '[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}' access.log

# Repeated words
grep '\b\([a-zA-Z]\+\) \1\b' file.txt    # "the the", "is is"

# Lines with "start" and "end"
grep '^.*start.*end.*$' file.txt
```

### BRE Escaping Gotcha

In BRE, metacharacters `*`, `.`, `[`, `^`, `$` are special by default. To use them literally, escape with `\`. But `(`, `)`, `{`, `}`, `+`, `?`, `|` are **literal** by default in BRE and need `\` to become special:

```bash
# BRE: these are literal without \
grep 'file.txt' log        # matches "file.txt" (dot is special, matches any char)
grep 'file\.txt' log       # matches "file.txt" literally

# BRE: these need \ to be special
grep 'a\+' file            # one or more 'a's (BRE)
grep 'a\{2\}' file         # exactly two 'a's (BRE)
grep '\(hello\)' file      # grouping (BRE)

# Confusing? Yes. That's why ERE exists.
```

## ERE — Extended Regular Expressions

ERE is the dialect used by `grep -E` (or `egrep`), `awk`, and `sed -E`. It makes the metacharacter behavior more intuitive.

### ERE vs BRE Differences

| Feature | BRE | ERE |
|---------|-----|-----|
| `+` (one or more) | `\+` | `+` |
| `?` (zero or one) | `\?` | `?` |
| `|` (alternation) | `\|` | `\|` |
| `{m,n}` (repetition) | `\{m,n\}` | `{m,n}` |
| `()` (grouping) | `\(\)` | `()` |
| Backreferences | `\1`-`\9` | Not standard |

```bash
# ERE: metacharacters are special without \
grep -E 'a+' file         # one or more 'a's
grep -E 'colou?r' file    # "color" or "colour"
grep -E 'cat|dog' file    # "cat" or "dog"
grep -E 'a{2,4}' file    # 2 to 4 'a's
grep -E '(ab)+' file      # one or more "ab"

# Same in BRE:
grep 'a\+' file
grep 'colou\?r' file
grep 'cat\|dog' file
grep 'a\{2,4\}' file
grep '\(ab\)\+' file
```

### ERE Quantifiers

```bash
# Zero or more
grep -E 'ab*c' file       # ac, abc, abbc, abbbc, ...

# One or more
grep -E 'ab+c' file       # abc, abbc, abbbc (NOT ac)

# Zero or one
grep -E 'ab?c' file       # ac, abc

# Exactly n
grep -E 'a{3}' file       # aaa

# n to m
grep -E 'a{2,4}' file     # aa, aaa, aaaa

# n or more
grep -E 'a{2,}' file      # aa, aaa, aaaa, ...

# Zero to n (using {,n} — not POSIX but widely supported)
grep -E 'a{,3}' file      # empty, a, aa, aaa
```

### ERE Alternation and Grouping

```bash
# Alternation
grep -E 'error|warning|critical' syslog

# Grouping with alternation
grep -E '(error|warning):' syslog

# Capturing in tools that support it
echo "2024-07-21" | grep -oE '([0-9]{4})-([0-9]{2})-([0-9]{2})'
# Output: 2024-07-21

# Non-capturing groups (PCRE only, not standard ERE)
# grep -P '(?:error|warning):' file
```

### ERE Practical Examples

```bash
# Match email addresses (simplified)
grep -E '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' file

# Match URLs
grep -E 'https?://[a-zA-Z0-9./-]+' file

# Match MAC addresses
grep -E '([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}' file

# Match dates (YYYY-MM-DD)
grep -E '[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])' file

# Match CIDR notation
grep -E '([0-9]{1,3}\.){3}[0-9]{1,3}/([0-9]|[12][0-9]|3[0-2])' file

# Lines NOT matching pattern
grep -Ev '(debug|trace|verbose)' log.txt

# Match hex color codes
grep -E '#[0-9a-fA-F]{6}\b' file

# Match quoted strings
grep -E '"[^"]*"' file
```

## PCRE — Perl-Compatible Regular Expressions

PCRE is the most feature-rich regex dialect, available in Linux via `grep -P`, `pcregrep`, and many programming languages.

### PCRE-Specific Features

```bash
# grep -P enables PCRE
grep -P 'pattern' file

# Installation (if needed)
sudo apt install pcregrep    # Debian/Ubuntu
sudo yum install pcre-tools  # RHEL/CentOS
```

### Character Classes (PCRE Extensions)

```bash
# Shorthand character classes
grep -P '\d+' file           # digits: [0-9]
grep -P '\D+' file           # non-digits: [^0-9]
grep -P '\w+' file           # word chars: [a-zA-Z0-9_]
grep -P '\W+' file           # non-word chars
grep -P '\s+' file           # whitespace: [ \t\n\r\f]
grep -P '\S+' file           # non-whitespace

# Unicode properties (with /u flag in Perl, or pcregrep)
grep -P '\p{L}' file         # Unicode letters
grep -P '\p{N}' file         # Unicode numbers
grep -P '\p{Han}' file       # CJK characters (Chinese)
```

### Anchors and Boundaries

```bash
# Standard anchors
grep -P '^start' file         # start of line
grep -P 'end$' file           # end of line

# Word boundaries
grep -P '\bword\b' file       # whole word match
grep -P '\bword' file         # word at start
grep -P 'word\b' file         # word at end

# Non-word boundary
grep -P '\Bword\B' file       # word NOT at boundary

# Subject boundaries (PCRE)
grep -P '\Astart' file        # start of subject (ignores multiline)
grep -P 'end\z' file          # absolute end of subject
grep -P 'end\Z' file          # end of subject (before final newline)
```

### Lookahead and Lookbehind (Zero-Width Assertions)

```bash
# Positive lookahead: match if followed by pattern
grep -P 'foo(?=bar)' file     # "foo" only if followed by "bar"
# Matches "foo" in "foobar" but not in "foobaz"

# Negative lookahead: match if NOT followed by pattern
grep -P 'foo(?!bar)' file     # "foo" NOT followed by "bar"
# Matches "foo" in "foobaz" but not in "foobar"

# Positive lookbehind: match if preceded by pattern
grep -P '(?<=foo)bar' file    # "bar" only if preceded by "foo"
# Matches "bar" in "foobar" but not in "bazbar"

# Negative lookbehind: match if NOT preceded by pattern
grep -P '(?<!foo)bar' file    # "bar" NOT preceded by "foo"
# Matches "bar" in "bazbar" but not in "foobar"
```

### Practical Lookaround Examples

```bash
# Match numbers followed by "MB" or "GB"
grep -P '\d+(?=MB|GB)' file

# Match IP addresses not in 127.0.0.0/8
grep -P '(?<!127\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' file

# Match words not preceded by "#"
grep -P '(?<!#)\bTODO\b' source.c

# Match file sizes (extract number only)
echo "123KB 456MB 789GB" | grep -oP '\d+(?=MB)'
# Output: 456

# Password validation: at least 8 chars, one uppercase, one digit
grep -P '^(?=.*[A-Z])(?=.*\d).{8,}$' passwords.txt

# Match lines with "error" but not "debug error"
grep -P '(?<!debug )error' log.txt
```

### Non-Greedy (Lazy) Quantifiers

```bash
# Greedy (default): match as much as possible
echo '<b>hello</b> <b>world</b>' | grep -o '<b>.*</b>'
# Output: <b>hello</b> <b>world</b>

# Non-greedy: match as little as possible
echo '<b>hello</b> <b>world</b>' | grep -oP '<b>.*?</b>'
# Output: <b>hello</b>
#         <b>world</b>

# All quantifiers have lazy versions
grep -P 'a*?' file    # zero or more (lazy)
grep -P 'a+?' file    # one or more (lazy)
grep -P 'a??' file    # zero or one (lazy)
grep -P 'a{n,m}?' file # n to m (lazy)

# Practical: extract HTML tag content
echo '<p>Hello</p><p>World</p>' | grep -oP '<p>\K.*?(?=</p>)'
# Output: Hello
#         World
```

### PCRE Modifiers

```bash
# Case-insensitive matching
grep -Pi 'error' file         # matches ERROR, Error, error, etc.

# Multiline mode (^ and $ match at newlines)
grep -Pm '(?m)^line' file

# Dotall mode (. matches newlines)
grep -Ps '(?s)start.*end' file

# Extended mode (ignore whitespace in pattern)
grep -Px '(?x)
    \d{4}    # year
    -        # separator
    \d{2}    # month
    -        # separator
    \d{2}    # day
' file

# Combine modifiers
grep -Pi '(?im)^error' file   # multiline + case-insensitive
```

### `\K` (Reset Match Start)

```bash
# \K resets the match start (like lookbehind but more flexible)
echo "key=value" | grep -Po '=\K.*'
# Output: value

echo "Error: something failed" | grep -Po 'Error: \K.*'
# Output: something failed

# Extract content between quotes
echo 'name="Alice"' | grep -Po '"\K[^"]*'
# Output: Alice
```

### Named Captures (PCRE)

```bash
# Named capture groups
echo "2024-07-21" | grep -Po '(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
# Output: 2024-07-21

# In Perl/Python:
# match.group('year') → "2024"
# match.group('month') → "07"
```

### Recursive Patterns (PCRE)

```bash
# Match balanced parentheses
grep -P '\(([^()]*|\(([^()]*|\([^()]*\))*\))*\)' file

# PCRE recursive pattern (pcregrep)
pcregrep '\(([^()]*(?R)?)*\)' file

# Match balanced HTML tags (simplified)
pcregrep '<(\w+)>(?:(?R)|.)*?</\1>' file
```

## Character Classes Deep Dive

### POSIX vs ASCII Character Classes

```bash
# POSIX bracket expressions (must be inside [])
grep '[[:alpha:]]' file        # correct
grep '[:alpha:]' file          # wrong: matches :, a, l, h, etc.

# ASCII ranges (locale-dependent)
grep '[a-z]' file              # lowercase (in C locale)
grep '[A-Z]' file              # uppercase

# POSIX classes work correctly across locales
grep '[[:lower:]]' file        # lowercase in any locale
```

### Unicode and Multibyte Characters

```bash
# In UTF-8 locale
grep -P '\p{Han}' file         # Chinese characters
grep -P '\p{Arabic}' file      # Arabic script
grep -P '\p{Emoji}' file       # Emoji (PCRE2)

# With LC_ALL
LC_ALL=en_US.UTF-8 grep '[:alpha:]' file

# Byte matching (ignore locale)
LC_ALL=C grep '[\x80-\xff]' file   # non-ASCII bytes
```

### Character Class Subtraction (PCRE)

```bash
# Not directly in PCRE, but workarounds exist
# Match digits except 0
grep -P '[1-9]' file

# Match letters except vowels
grep -P '[b-df-hj-np-tv-z]' file

# Using negative lookahead in class (PCRE)
grep -P '(?=[a-z])(?![aeiou])[a-z]' file
```

## Backreferences

Backreferences match the same text captured by a previous group.

### BRE/ERE Backreferences

```bash
# Find repeated words
grep -E '\b(\w+) \1\b' file
# Matches: "the the", "is is", "hello hello"

# Find lines with repeated characters
grep -E '(.)\1' file           # any character repeated
grep -E '(.)\1\1' file         # three in a row (aaa, bbb)

# Find palindromes (3-letter)
grep -E '^(.)(.).\2\1$' file   # "abcba"

# Swap first two words
echo "hello world" | sed -E 's/(\w+) (\w+)/\2 \1/'
# Output: world hello

# Remove duplicate words
echo "the the cat sat on on the the mat" | sed -E 's/\b(\w+) \1\b/\1/g'
# Output: the cat sat on the mat
```

### PCRE Backreferences

```bash
# Same as ERE, plus:
# Recursive backreference
grep -P '(a(?1)?b)' file       # matches ab, aabb, aaabbb

# Conditional patterns
grep -P '(a)(?(1)b|c)' file    # if group 1 matched, match b, else c

# Backreference in lookahead
grep -P '(?=(.)\1)' file       # lookahead for repeated char
```

## Regex in Different Tools

### grep

```bash
# BRE (default)
grep 'pattern' file

# ERE
grep -E 'pattern' file
egrep 'pattern' file          # deprecated

# PCRE
grep -P 'pattern' file

# Common options
grep -i 'pattern' file        # case-insensitive
grep -v 'pattern' file        # invert match
grep -c 'pattern' file        # count matches
grep -l 'pattern' *           # files with matches
grep -n 'pattern' file        # show line numbers
grep -o 'pattern' file        # only matching part
grep -w 'pattern' file        # whole word match
grep -r 'pattern' dir         # recursive
grep -m 5 'pattern' file      # max 5 matches
grep -A 3 'pattern' file      # 3 lines after match
grep -B 3 'pattern' file      # 3 lines before match
grep -C 3 'pattern' file      # 3 lines context
```

### sed

```bash
# BRE (default)
sed 's/pattern/replacement/' file

# ERE
sed -E 's/pattern/replacement/' file

# PCRE (not natively; use perl instead)
perl -pe 's/pattern/replacement/' file

# See sed-awk.md for detailed sed usage
```

### awk

```bash
# ERE by default
awk '/pattern/ {print}' file

# With field matching
awk -F: '$1 ~ /root/' /etc/passwd

# See sed-awk.md for detailed awk usage
```

### Bash `=~` Operator

```bash
# ERE in [[ ]]
if [[ "$str" =~ ^[0-9]+$ ]]; then
    echo "All digits"
fi

# Capture groups
if [[ "$version" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    patch="${BASH_REMATCH[3]}"
fi

# Store regex in variable for complex patterns
re='^([0-9]{1,3}\.){3}[0-9]{1,3}$'
[[ "$ip" =~ $re ]] && echo "Valid IP"
```

## Common Regex Patterns

### Validation Patterns

```bash
# Email (simplified)
^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$

# IPv4
^([0-9]{1,3}\.){3}[0-9]{1,3}$

# IPv6 (simplified)
^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$

# URL
https?://[a-zA-Z0-9./-]+

# Date (YYYY-MM-DD)
^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$

# Time (HH:MM:SS)
^([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$

# Phone (US)
^\+?1?[ -.]?(\([0-9]{3}\)|[0-9]{3})[ -.]?[0-9]{3}[ -.]?[0-9]{4}$

# MAC address
^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$

# UUID
^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$
```

### Extraction Patterns

```bash
# Extract IP from log line
grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' access.log

# Extract domain from email
echo "user@example.com" | grep -oE '@(.*)' | cut -c2-

# Extract filename from path
echo "/usr/local/bin/script.sh" | grep -oE '[^/]+$'

# Extract version number
echo "package-1.2.3-4.el8.x86_64" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'

# Extract port from URL
echo "https://example.com:8080/path" | grep -oE ':[0-9]+(?=/)' | cut -c2-
```

### Transformation Patterns

```bash
# Remove HTML tags
sed -E 's/<[^>]*>//g' file

# Normalize whitespace
sed -E 's/[[:space:]]+/ /g' file

# Add commas to numbers
echo "1234567" | sed -E ':a; s/([0-9])([0-9]{3})(,|$)/\1,\2\3/; ta'
# Output: 1,234,567

# Convert camelCase to snake_case
echo "myVariableName" | sed -E 's/([a-z])([A-Z])/\1_\L\2/g'
# Output: my_variable_name

# Remove duplicate lines (preserving order)
awk '!seen[$0]++' file
```

## Regex Performance

### Optimization Tips

```bash
# 1. Anchor your patterns
grep '^pattern' file         # faster than
grep 'pattern' file          # unanchored (has to check every position)

# 2. Use character classes instead of alternation
grep -E '[abc]' file         # faster than
grep -E 'a|b|c' file         # alternation

# 3. Avoid unnecessary backtracking
grep -P '[^"]*' file         # faster than
grep -P '.*?' file           # non-greedy (more backtracking)

# 4. Use non-capturing groups when capture isn't needed
grep -P '(?:foo|bar)baz' file   # slightly faster than
grep -P '(foo|bar)baz' file     # capturing group

# 5. Use fixed strings when possible
grep -F 'fixed.string' file     # fastest (no regex at all)
grep 'fixed\.string' file       # slower (regex engine)

# 6. Limit grep scope
grep -m 1 'pattern' file        # stop after first match
grep -l 'pattern' *.txt         # just filenames
```

### Regex Complexity Comparison

```
┌─────────────────────────────────────────────────────┐
│  Regex Complexity Comparison                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Pattern              │ Relative Speed │ Notes      │
│  ─────────────────────┼────────────────┼─────────── │
│  fixed string (grep -F)│ ★★★★★         │ Fastest    │
│  anchored literal     │ ★★★★☆         │ Very fast  │
│  simple class [a-z]   │ ★★★★☆         │ Fast       │
│  dot-star .*          │ ★★★☆☆         │ Moderate   │
│  backreference \1     │ ★★☆☆☆         │ Slow       │
│  nested quantifiers   │ ★☆☆☆☆         │ Very slow  │
│  catastrophic backtr. │ ☆☆☆☆☆         │ Avoid!     │
└─────────────────────────────────────────────────────┘
```

### Catastrophic Backtracking

```bash
# This pattern can hang (exponential backtracking):
# (a+)+b against "aaaaaaaaaaaaaaaaaaaaac"
# Each a+ can match 1 to n a's, and the outer + repeats
# → exponential combinations to try before failing

# Fix: use atomic groups or possessive quantifiers (PCRE)
# (a++)+b          # possessive quantifier
# (?>a+)+b         # atomic group

# In practice, avoid nested quantifiers on overlapping patterns
# Bad:  (a+)+$
# Good: a+$
# Good: (a+)+b     # OK if b is present (fails fast on non-b)
```

## Regex Debugging

### Testing Regex Interactively

```bash
# Online tools
# - https://regex101.com/ (excellent, supports all dialects)
# - https://regexr.com/
# - https://www.debuggex.com/ (visual)

# Command-line testing
echo "test string" | grep -P 'pattern'

# Show what matched
echo "test123" | grep -oP '\d+'
# Output: 123

# Show match position
echo "test123end" | grep -obP '\d+'
# Output: 4:123

# Test multiple patterns
for pattern in '^\d+$' '^[A-Z]' 'test'; do
    echo "Pattern: $pattern"
    echo "abc123 TEST test" | grep -P "$pattern" && echo "  MATCH" || echo "  no match"
done
```

### Using `pcretest`

```bash
# Interactive PCRE testing
pcretest
re> /^(\d{4})-(\d{2})-(\d{2})$/
data> 2024-07-21
 0: 2024-07-21
 1: 2024
 2: 07
 3: 21
data> not-a-date
No match

# Show match details
pcretest -d
re> /\d+/
data> abc123def
 0: 123
```

## Cross-References

- [Bash](bash.md) — Pattern matching in Bash with `=~` and `[[ ]]`
- [Shell Scripting Fundamentals](scripting-fundamentals.md) — Quoting and globbing
- [sed and awk](sed-awk.md) — Using regex in text processing
- [Advanced Shell Scripting](scripting-advanced.md) — Pattern matching in scripts

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Regular-Expressions.info](https://www.regular-expressions.info/) — Comprehensive tutorial
- [PCRE2 Man Page](https://www.pcre.org/current/doc/html/) — Official PCRE documentation
- [regex101](https://regex101.com/) — Interactive regex tester with explanations
- [RexEgg](https://www.rexegg.com/) — Advanced regex techniques
- [Mastering Regular Expressions](https://www.oreilly.com/library/view/mastering-regular-expressions/0596528124/) — Jeffrey Friedl's definitive book
- [The POSIX Regular Expression Specification](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html) — POSIX standard
