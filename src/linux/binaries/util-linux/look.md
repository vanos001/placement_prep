# look — display lines beginning with a given prefix (sorted-file binary search)

## Overview

`look` prints every line of a sorted file that begins with a given string — a prefix lookup, not a substring search. Because the input must be sorted, `look` can run a binary search: it homes in on the first matching line and prints the run of matches, making it dramatically faster than `grep` on huge sorted lists. If no file is given, it searches the system dictionary `/usr/share/dict/words` and assumes dictionary order and case-insensitive comparison. Ships in the `bsdextrautils` package (Debian bookworm) at `/usr/bin/look` — the binary is util-linux upstream code with BSD lineage.

Reach for it in three places: dictionary/word games (`look py`), prefix completion against any sorted list (usernames, package names, host lists), and quick "does this token exist" checks in large sorted data files. It is often confused with `grep` (substring, unsorted input, scans everything), with `grep '^py'` (same prefix result but O(n) scan), and with `sort -u` pipelines that recreate what look's sorted-input requirement is there for.

| Field | Value |
| --- | --- |
| Package | bsdextrautils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/look |
| First appeared | BSD (4.3BSD-Reno era) |
| Standards | None (BSD command; not POSIX-specified) |

## Synopsis

```
look [options] <string> [<file>]
```

Common one-line forms:

```
look py                          # words starting with "py" from the dict
look py /usr/share/dict/words    # explicit file (comparison is case-sensitive here)
look -f do file.txt              # ignore case
look -t: deploy sorted.tsv       # compare only up to ':' (first field)
```

## How It Works

### Binary search over a sorted file

```
 sorted file                       look "ap"
 ┌──────────┐                      binary search for the first line
 │ apple    │                      whose prefix >= "ap"
 │ apply    │            ┌───────────────┐
 │ apricot  │  ◄─ match  │ mid, mid, mid │──► land on "apple",
 │ banana   │            └───────────────┘    print while prefix matches
 └──────────┘
 O(log n) seeks + O(matches) output, versus grep's O(n) full scan
```

Steps: seek to the file midpoint, compare that line against the prefix using the active collation (`-d` dictionary order, `-f` ignore case), recurse left or right, then stream every consecutive line starting with the prefix. Nothing is loaded into memory; the kernel page cache does the heavy lifting, so repeated `look` calls on the same file are essentially free.

### Comparison rules

Two modifiers change what "begins with" means:

- **`-d, --dictionary-order`** — only letters, digits, and blanks count in comparisons (punctuation and symbols are ignored), matching `sort -d`'s dictionary collation.
- **`-f, --ignore-case`** — case-insensitive comparison, matching `sort -f`.

When no file operand is given, `look` uses `/usr/share/dict/words` with `-d`/`-f` behavior assumed — the dictionary is maintained in that collation. With an explicit file, comparison is bytewise unless you pass the flags yourself.

### `-t` — cut the search key short

`-t <char>` terminates the compared string at the first occurrence of `<char>`: the prefix *and* each line are truncated there before comparison. Against a colon-separated sorted table, `look -t: deploy table.txt` matches on the first field only, regardless of what follows the colon — the poor admin's indexed lookup.

### The contract: sorted input

`look` never checks sortedness. Feed it an unsorted file and it performs a correct binary search on garbage: some prefixes return nothing, others return wrong subsets — silently. The standing pipeline is:

```bash
sort -o sorted.txt data.txt && look py sorted.txt
```

and when you rely on `-d`/`-f` semantics, the file must be sorted *the same way* (`sort -d -f -o sorted.txt data.txt`).

### The implementation, in memory

`look` maps the file (`mmap(2)`) and binary-searches line-aligned positions: it probes byte offsets, snaps to a line boundary when a probe lands mid-line, and compares from there. Nothing is read wholesale — the kernel faults in only the probed pages plus the matching run. On repeated queries against the same file (the intended use), everything after the first call is RAM-speed; on a cold multi-GB file the first query pays the page-in cost for the probed region.

### Where the O(log n) claim bends

Binary search finds the *first* match in O(log n) line comparisons; printing K matches costs O(K), and each comparison is O(prefix length). Worst case — every line matches, e.g. a file of identical prefixes — degrades to reading everything; the win is for selective prefixes over big files. Also note the input must be a real, seekable file: `look key <(sort data.txt)` fails because a pipe cannot be mmap'ed — materialize sorted output to a temp file first.

### Exit-path details scripts rely on

`look` exits 0 when it printed at least one match and 1 when it did not — a free boolean prefix-membership test with the matches as a bonus. A missing or unreadable file is also nonzero (with a diagnostic on stderr), so `look key file >/dev/null 2>&1` is the safe probe idiom in scripts; do not branch on stderr text.

### The default dictionary, precisely

The no-file form searches `/usr/share/dict/words` with `-d -f` assumed. Two legacy details survive from BSD: `-a, --alternate` switches to the alternate dictionary `/usr/share/dict/web2`, and both paths come from the `dictionaries-common`/word-list packages — not from look itself. Because the dict is maintained in dictionary order case-insensitively, `look py` and `look py /usr/share/dict/words` can return different sets on the same machine: the explicit-file form compares case-sensitively bytewise.

## Options That Matter

| Option | Effect |
| --- | --- |
| `<string>` | Prefix to search for (no regex — it is a literal string) |
| `[<file>]` | Sorted file to search; default `/usr/share/dict/words` with `-d -f` assumed |
| `-d, --dictionary-order` | Compare only letters, digits, and blanks (as `sort -d`) |
| `-f, --ignore-case` | Case-insensitive comparison (as `sort -f`) |
| `-t, --terminate <char>` | Stop comparing both key and lines at the first `<char>` |
| `-a, --alternate` | Use the alternate dictionary (legacy BSD option) |

## Usage Patterns

```bash
# Dictionary games: every word starting with "py"
look py
# python
# pythagoras

# Sorted word list of your own (logrotate knows this pattern)
printf 'apple\napply\nbanana\n' | sort -o /tmp/w.txt
look app /tmp/w.txt

# Does this hostname exist in the inventory? (fast, exit-code testable)
look db-prod-01 sorted-hosts.txt >/dev/null && echo exists

# Prefix completion for usernames
look deb /etc/aliases.sorted

# Case-insensitive prefix search
look -f SHELL sorted-commands.txt

# First-field lookup in a sorted colon table
look -t: deploy inventory.sorted
# deploy@prod:10.0.0.14

# Feed completion candidates to a shell function
_complete_host() { compgen -W "$(look -t, "$1" hosts.sorted | cut -d, -f1)"; }

# Same result as grep -^, but binary-searched on a big file
look ERR sorted-syslog-index.txt

# Build the sorted index once, query many times (the look workflow)
cut -d, -f1 sales.csv | sort -u -o names.sorted
for p in Acme Globe Zen; do look "$p" names.sorted; done

# Enforce the sorted contract before trusting results (fail loudly)
sort -c sorted-hosts.txt || { echo "index needs resorting" >&2; exit 1; }
look db-prod-01 sorted-hosts.txt

# Locale-proof pipeline: produce and query in the same collation
LC_ALL=C sort -o users.sorted users.raw
LC_ALL=C look "$u" users.sorted >/dev/null && echo known || echo unknown

# Batch miss-report: one sorted index, many keys, misses logged
while read -r key; do
  look "$key" inventory.sorted >/dev/null || echo "miss: $key"
done < keys.txt

# Build a lookup index out of system data (here: usernames from passwd)
cut -d: -f1 /etc/passwd | LC_ALL=C sort -o users.sorted
look -t: "$USER" users.sorted 2>/dev/null || echo "no such user"

# Completion candidates for a shell function, from a sorted service list
_complete_service() {
  local matches
  matches=$(look "$1" services.sorted 2>/dev/null) || return 1
  compgen -W "$matches" -- "$1"
}

# Check the index health in CI: sortedness is cheap to assert
LC_ALL=C sort -c users.sorted && echo "index ok" || echo "index corrupt"
```

## Nuances and Gotchas

- **Unsorted input fails silently.** No error, no warning — just wrong or empty results. Any wrapper script should sort (or verify sortedness with `sort -c`) before trusting `look`.
- **Collation must match the sort.** `sort` under your locale may ignore punctuation/case differently than `look`'s bytewise default; `-d`/`-f` on *both* sides (`sort -d -f` ↔ `look -d -f`) is the reliable pairing. Locale mismatch is the classic "works on my machine" bug.
- **Prefix, not substring.** `look err` does not find `buffering`; that is `grep`'s job. Conversely `grep '^err'` on a sorted file is equivalent-but-linear — `look` wins only on large files and repeated queries.
- **The default dictionary may not exist.** `/usr/share/dict/words` comes from `wamerican`/`wbritish` (via `dictionaries-common`), which is not installed everywhere; without it `look` errors on the no-file form. For guaranteed behavior, always pass a file.
- **Case sensitivity flips with the default dict.** No-file lookups are `-d -f` (case-insensitive); explicit-file lookups are case-sensitive unless flagged. Scripts that mix both forms get "inconsistent" results.
- **No regex, no anchoring options** — the prefix is a literal string; `-t` is the only key-shaping tool.
- **BSD/macOS differences:** macOS ships a BSD `look` with the same core contract (sorted input, `-df`, default dictionary); option surface varies slightly, so keep scripts to `-d`/`-f`/`-t`.
- **It exits 1 on "no match"** — handy for `if look ... >/dev/null; then` logic, but remember to redirect stdout or the matches pollute your output.
- **Appended lines poison the tail.** A file with an unsorted tail — typically an index a logger keeps appending to — yields wrong or empty results for keys in that region, silently. Snapshot or re-sort before querying; never `look` a growing file.
- **`-t` has no escaping.** Comparison stops at the *first* occurrence of the terminator in each line, so keys containing the terminator cannot be expressed. Pick a separator that never appears inside keys, or pre-split the field into its own file.
- **No stdin, no process substitution.** The file operand must be a real, seekable file (it gets mmap'ed); `look key <(sort data.txt)` fails. Write sorted output to a temp file, then query it.
- **Under `-d`, punctuation is invisible.** Two lines differing only in punctuation compare equal, so near-duplicate keys (`foo-bar` vs `foobar`) are indistinguishable — look prints whichever run it lands on. Sort and query with identical flags, and keep `-d` off when keys are punctuation-sensitive.
- **Duplicate keys print as a run — all of them.** Every line whose prefix matches is printed, including exact duplicates; `sort -u` the index if one line per key is the contract.
- **The run can start mid-file.** Binary search finds the first prefix match from the current sorted state; if a key's "block" was split by an out-of-order insertion elsewhere, look still finds only the contiguous run at the sorted position — another reason `sort -c` belongs in the pipeline.
- **Trailing content beyond the last newline is still a line.** A file whose final line lacks a newline participates normally in searches; when *building* indexes, terminate every line — some downstream tools are less forgiving than look.
- **Empty files and empty keys.** `look '' file` matches from the top (every string starts with the empty prefix) — the whole file prints; a zero-byte file matches nothing and exits 1. Both are correct but rarely what a buggy variable interpolation intended.
- **The dict default is a convenience, not a contract.** Anything relying on `/usr/share/dict/words` existing (games, tests) should probe for it once and degrade to an explicit sorted file — dictionary packages are optional even on desktop installs.

## Exit Status

- `0` — at least one matching line was found and printed.
- `1` — the prefix was not found (or the file could not be searched/read).

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`grep`](../../shell/grep.md) — full-content pattern search; unsorted input, regex, linear scan.
- [`regex`](../../shell/regex.md) — the pattern language `look` deliberately avoids in favor of literal prefixes.
- [`sed-awk`](../../shell/sed-awk.md) — the heavier text-processing artillery for jobs beyond prefix lookup.
- [`bash`](../../shell/bash.md) — completion functions that pair well with `look -t` over sorted lists.
- [`overview`](../overview.md) — the userland-binaries part intro.

## Interview Questions

### Q: Why does look require sorted input, and what does it gain from it?

Sortedness enables binary search: O(log n) comparisons to find the first match plus the cost of printing matches, versus a full O(n) scan in `grep`. For a multi-million-line sorted index queried repeatedly, that is the difference between page-cache-fast and disk-bound. The cost is the contract: unsorted input yields silently wrong answers, so `sort` (with matching collation flags) must precede `look`.

### Q: What do the -d and -f flags change, and why do they matter beyond the search itself?

`-d` restricts comparisons to letters/digits/blanks (dictionary order); `-f` ignores case. They matter on both sides of the contract: the file must be sorted with the *same* collation (`sort -d -f`) or the binary search lands in the wrong place. They also explain the no-file default — `/usr/share/dict/words` is maintained in dictionary order case-insensitively, so `look` assumes `-d -f` there.

### Q: Design a fast "does this user exist" check for 10 million usernames. Where does look fit?

`cut -d: -f1 /etc/passwd.all | sort -u -o users.sorted` once, then `look -t: "$u" users.sorted >/dev/null` per query — binary search on the page cache, exit code as the boolean. For update-heavy data an actual key-value store or indexed database is the real answer, but for a mostly-static list `sort` + `look` is zero dependencies and constant memory.

### Q: What is the difference between `look foo f` and `grep '^foo' f`, and when do you pick each?

Both print lines starting with `foo` — when `f` is sorted and unmodified. `grep` scans every line (O(n)) and works on any input; `look` binary-searches (O(log n) seeks) and requires the sorted contract. Pick `look` for large, static, sorted lists and repeated queries; pick `grep` (or `grep -m`) for unsorted files, streaming input, or when you need regex.

### Q: You get different results from the same `look` command on two machines. Debug it.

First suspect collation: `look`'s comparison is locale/collation-sensitive and the sorted file was probably produced under a different locale — a `sort` that ignored punctuation on one host and not the other breaks the binary search invariants. Reproduce with `sort -c`, standardize with `LC_ALL=C sort` ↔ explicit `look` flags, and check whether the no-file form was used (which silently assumes `-d -f` against `/usr/share/dict/words` that may even be missing).

### Q: How does `-t` turn look into a poor man's indexed lookup?

`-t <char>` truncates both the search string and every candidate line at the first occurrence of that character, so comparison happens on the first field only. A file sorted by first field (`sort -t: -k1,1`) then becomes a key→row index: `look -t: key table` returns every row whose key starts with the string. It is limited (prefix semantics, single key) but needs no database.

### Q: Why is look paired so often with sort, and what invariants must hold exactly?

The binary search assumes the file is sorted under exactly the collation look will use: same `-d`/`-f` treatment, same locale. Violate any of the three and probes land on the wrong side of the target — silently. Hence the idiom: one command produces the index (`sort -d -f -o`), every query passes the same flags (`look -d -f`), and a CI check runs `sort -c` to catch drift between producers and consumers.

### Q: Could you replace look with `grep -m1 '^key'`? What do you gain and lose?

Correctness-wise they agree on a sorted file; performance-wise grep reads everything up to the match's offset (O(position)) while look probes O(log n) lines — decisive only for large files and repeated queries. What look lacks: regex, substring matching, streaming input, and tolerance of unsorted data. What it gives: near-constant-time queries against a page-cached index and a trivial exit-code membership test. Hot paths over static sorted data → look; everything else → grep.

### Q: Design a "spell-check this document" tool with look. What are the steps and pitfalls?

Tokenize, normalize case, then batch against the dictionary. The tempting loop (`for w in $(cat tokens); do look -f "$w" || echo "$w"; done`) makes O(n log m) page-cached probes — workable for interactive spot checks. Pitfalls: dictionary order is `-d -f`, so tokens with digits or punctuation compare oddly under `-d` — strip punctuation first; the default dictionary may be missing (`wamerican` not installed); and for bulk checks a one-pass set difference (`comm -23` between the sorted token list and the dictionary) beats per-word lookups. look is the interactive half; the batch job belongs to sort/comm.

### Q: Where does look sit in the tool lineage, and why is it in bsdextrautils?

It is BSD code (4.3BSD-Reno era) that util-linux adopted and maintains alongside its other text utilities; Debian packages it in `bsdextrautils` with the rest of the historic BSD userland rather than in util-linux proper. Practical consequence: on minimal Debian installs it may be absent even when util-linux is present, and on macOS you get the BSD original with the same core contract. Scripts that must run everywhere should treat look as optional and keep a grep fallback.

### Q: How would you build a prefix-completer over a million-entry list with sub-50 ms latency?

Index once: sort the list (`LC_ALL=C sort -u -o big.sorted`), keep it resident (the page cache holds it after first touch), then per keystroke run `look "$prefix" big.sorted | head -10` — O(log n) probes over mapped pages, no daemon, no memory of your own. Pin the index with `vmtouch`-style warming or a pre-read loop if cold-start latency matters. Compare alternatives honestly: trie in a real language beats it on scale, but for a shell tool with zero dependencies, sorted-file + look is the whole design.

### Q: What does look do with an empty search string, and what does that reveal about the comparison model?

`look '' file` matches every line — the empty string is a prefix of everything — so it prints the whole file starting from the top and exits 0. That falls straight out of the model: comparison is "does this line begin with the key", and the empty key trivially holds. It is also the most common scripting accident: an unquoted empty variable turns your targeted lookup into a full-file dump. Quote the key and reject empty input in wrappers.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdextrautils/look.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
