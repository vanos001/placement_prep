# diff — line-by-line file comparison and patch generator

## Overview

`diff` compares two files (or two directory trees) line by line and prints a minimal set of *change instructions* that transform one into the other: deletions, additions, and replacements, optionally surrounded by unchanged context lines. It ships in the `diffutils` package (Debian bookworm: GNU diffutils 3.8) at `/usr/bin/diff`, alongside its siblings `cmp`, `diff3`, and `sdiff`. The unified format (`-u`) that `diff` emits is the interchange format consumed by `patch`, `git apply`, code-review tools, and effectively every VCS on the planet, which makes `diff` one of the few Unix binaries whose output is a published, load-bearing artifact rather than a mere report.

`diff` is often confused with `cmp` (which compares byte by byte and stops at the first difference — right tool for binaries), with `patch` (which *applies* diff output), and with `git diff` (a separate, richer implementation using the same algorithm family, adding word-level coloring, rename detection, and submodule awareness). The classic division of labor: `diff` finds the difference, `patch` replays it, `cmp` answers "identical or not, and where first".

| Field | Value |
| --- | --- |
| Package | diffutils (Debian bookworm: GNU diffutils 3.8) |
| Man section | 1 |
| Path | /usr/bin/diff |
| First appeared | AT&T Unix Version 5 (1974); GNU rewrite mid-1980s |
| Standards | POSIX.1-2018 (`diff`) |

## Synopsis

```
diff [OPTION]... FILES
```

Common one-line forms:

```
diff -u old.txt new.txt          # unified diff — the patch format
diff -r dirA dirB                # recursively compare two trees
diff -q a b                      # report only whether files differ
diff -y -W 160 a b               # side-by-side view, 160 columns
diff -e old new                  # ed script for the changes
```

`FILES` is normally two paths; either may be `-` (stdin). If one operand is a directory and the other a file, `diff` compares the file against a same-named file in the directory. With `--from-file`/`--to-file` one side can be a directory compared against many operands.

## How It Works

### The difference engine

`diff` reads both inputs, splits them into lines, and computes a longest-common-subsequence (LCS) between the two line sequences. Lines present in both files anchor the alignment; everything between anchors is emitted as a *hunk* of deletions (`<` side) and additions (`>` side). GNU `diff` uses a bidirectional variant of Myers' O(ND) algorithm (1986), which is why the output is not just *a* valid transformation but usually the smallest one. Two tuning knobs change the trade-off:

```
-d, --minimal          try hard for the smallest possible edit script (slow)
-H, --speed-large-files assume large files with scattered small changes (fast, approximate)
```

The result is a list of hunks; the chosen output format is just a rendering of that list. Everything below is the same internal data wearing different coats.

```
 file A        file B
   │             │
   └──> split into lines <──┘
             │
      LCS / Myers algorithm
             │
      hunk list (old-range -> new-range)
             │
   ┌─────────┼──────────┬───────────┬──────────┐
   ▼         ▼          ▼           ▼          ▼
 normal     unified   context    side-by-side  ed/RCS/ifde
 (default)  (-u)      (-c)       (-y)          (-e -n -D)
```

### Unified format, decoded

Unified (`-u`) is the format that matters in practice — `patch`, `git apply`, and every code-review UI speak it. Real output:

```
$ diff -u a.txt b.txt
--- a.txt	2026-10-09 16:33:31.322925999 +0000
+++ b.txt	2026-10-09 16:33:31.322925999 +0000
@@ -1,5 +1,6 @@
 alpha
-bravo
+bravoo
 charlie
-delta
+DELTA
 echo
+foxtrot
```

Anatomy, line by line:

- `--- a.txt` / `+++ b.txt` — headers naming the *old* and *new* file, with mtime and timezone. `patch` uses these to find the target file; `--label X` replaces name+timestamp (how `git` produces `a/file b/file` headers).
- `@@ -1,5 +1,6 @@` — the hunk header: old start line 1, old line count 5; new start line 1, new count 6. The count is omitted when it is 1 (`@@ -2 +2 @@`), and a count of 0 means "insert after this line": `@@ -5,0 +6 @@` says *after old line 5*, add new line 6.
- Lines starting with ` ` (space) are context, `-` is deleted from the old file, `+` is added in the new file. A pure addition hunk contains only `+` lines; a pure deletion only `-` lines.
- `\ No newline at end of file` — emitted after the affected line when either file lacks the trailing newline.

`-U NUM` controls context width (`-U0` gives bare hunks, common in machine-generated patches and `git diff -U0`). Context lines are not decoration: they are how `patch` locates the hunk if the target file has drifted, and `patch` reports `.rej` files when offsets fail by more than the fuzz allowance.

### Context format (`-c`), decoded

The older context format renders each file's block separately with `!` for changed, `+` for added, `-` for removed lines:

```
*** a.txt	Fri Oct  9 16:33:31 2026
--- b.txt	Fri Oct  9 16:33:31 2026
***************
*** 1,5 ****
  alpha
! bravo
  charlie
! delta
  echo
--- 1,6 ----
  alpha
! bravoo
  charlie
! DELTA
  echo
+ foxtrot
```

You will meet it in old mailing-list archives and some vendor patch formats. It carries the same information as unified but is bulkier; `patch` accepts it too. Modern default advice: always produce unified.

### Normal format (the default), decoded

With no format flag, `diff` prints terse line-range commands inherited from ed:

```
$ diff a.txt b.txt
2c2
< bravo
---
> bravoo
4c4
< delta
---
> DELTA
5a6
> foxtrot
```

`2c2` reads "old line 2 changed into new line 2", `5a6` "after old line 5, add new line 6", `4,5d3` would read "old lines 4-5 deleted after new line 3". The `<`/`>` bodies are the old/new contents. It is compact and machine-readable, but ambiguous to parse casually (a `c` range can be `2c2`, `2,3c4` or `2,3c4,5`), and it is *not* what patch tools want by default. If you script `diff`, decide explicitly: `-u` for patches, `-q` for boolean checks, `--brief` plus exit status for automation.

### Directory mode

If both operands are directories, `diff` compares same-named files pairwise and reports asymmetric entries:

```
$ diff -r dir1 dir2
Only in dir1: only1.txt
Only in dir2: only2.txt
diff -r dir1/sub/cfg dir2/sub/cfg
1c1
< x=1
---
> x=2
```

Without `-r` only the top level is compared. With `-q` you get a summary (`Files dir1/sub/cfg and dir2/sub/cfg differ`, `Only in ...` lines) — the canonical pre-backup or pre-sync sanity check. `-N` treats files missing on one side as empty on the other, which turns "only in" into a real diff of the missing file versus nothing — the trick behind full-tree patches:

```
$ diff -ruN orig/ work/ > work.patch      # deletions AND additions captured
```

`-x PAT` / `-X FILE` exclude patterns (relative path names, shell globs), `-S FILE` resumes an interrupted directory comparison after a given file. Symbolic links are dereferenced by default; `--no-dereference` compares the links themselves.

### Non-diff renderings and merge output

Beyond human formats, `diff` emits executable data:

- `-e` — an ed script applying the changes (`5a` / `foxtrot` / `.` blocks). Append `w`+`q` and feed it to `ed`, or let `patch -e` handle it.
- `-n` — RCS-style diff, consumed by revision tools.
- `-D NAME` — a merged output where differing regions are wrapped in `#ifdef NAME ... #else ... #endif` C preprocessor directives; the ancestor of all three-way merge presentation.
- `--GTYPE-group-format`/`--line-format` — a small formatting language generalizing all of the above (this is how tools like `wdiff`-style word diffs were once built on top of `diff`).
- `-y` — side-by-side two columns with a gutter (`|` changed, `<` left-only, `>` right-only, blank same); `-W` sets total width, `--suppress-common-lines` strips identical rows.

For merging rather than just comparing, see `diff3 -m` (three-way with a base) and `sdiff -o` (interactive) in this collection — `-D`/`-y` are display devices, not merge engines.

### Exit codes are data

`diff` encodes its verdict in the exit status, deliberately overlapping with grep-style conventions:

- `0` — no differences (contents identical under the active ignore options).
- `1` — some differences were found (this is success for comparison purposes).
- `2` — trouble: missing file, I/O error, bad option.

Scripts must therefore write `if diff -q a b; then ...` or `diff ... || ...` and *not* run bare `diff` under `set -e` expecting silence. The same 0/1/2 convention is shared by `cmp`, `sdiff`, and (with "1 = conflicts") `diff3` — it is one of the cleanest "exit code as data" designs in userland.

## Options That Matter

### Output format

| Option | Effect |
| --- | --- |
| `-u` / `-U NUM` | Unified diff, NUM context lines (default 3). The patch format. |
| `-c` / `-C NUM` | Context diff (older patch format, `***`/`---` blocks). |
| `--normal` | Default terse `2c2`-style ed ranges. |
| `-q` | Say only whether files differ; prints nothing for identical pairs. |
| `-s` | Report when files *are* identical (`Files a and b are identical`). |
| `-y -W NUM` | Side-by-side columns within NUM print columns (default 130). |
| `-e` / `-n` | Emit ed script / RCS diff. |
| `-D NAME` | Emit merged file with `#ifdef NAME` around changed regions. |
| `-p` | Show the enclosing C function in each hunk header. |
| `-F RE` | Like `-p` but for any regex (e.g. shell or Python defs). |
| `--label LABEL` | Replace file name/timestamp in headers (repeatable; reproducible patches). |

### Recursive and directory comparison

| Option | Effect |
| --- | --- |
| `-r` | Recurse into common subdirectories. |
| `-N` | Treat absent files as empty (adds/deletions appear in diffs). |
| `--unidirectional-new-file` | Only absent *first* files count as empty. |
| `-x PAT`, `-X FILE` | Exclude files matching pattern / patterns listed in FILE. |
| `-S FILE` | Resume directory comparison starting at FILE. |
| `--from-file F1`, `--to-file F2` | Compare one operand against many. |

### Matching leniency (comparison, not output)

| Option | Effect |
| --- | --- |
| `-i` | Ignore case in content. |
| `-b` | Ignore *amounts* of whitespace (`a b` == `a  b`). |
| `-w` | Ignore all whitespace (`ab` == `a b`). |
| `-Z` | Ignore trailing whitespace per line. |
| `-E` | Ignore tab-expansion differences. |
| `-B` | Ignore hunks that are only blank lines. |
| `-I RE` | Ignore hunks where every changed line matches RE. |
| `-a` | Force text mode (diff a binary anyway). |
| `--strip-trailing-cr` | Ignore CRLF/LF differences (Windows vs Unix files). |

### Performance / plumbing

| Option | Effect |
| --- | --- |
| `-d` | Minimal edit script; slower, smaller diffs. |
| `-H` | Heuristic for large files, many small changes. |
| `--diff-program=PROG` | Shell out to an alternate diff for the comparison. |
| `-T` / `-t` | Initial tab / expand tabs for aligned columns. |

## Usage Patterns

```bash
# Produce a reviewable, appliable patch of a single file
diff -u config.conf.orig config.conf > config.patch
```

```bash
# Reproducible headers (no timestamps/timezones) for checked-in patches
diff -u --label a/app.c --label b/app.c app.c.orig app.c
```

```bash
# Verify a patch applies cleanly to a pristine copy, then ship it
cp old.txt work.txt && patch work.txt < fix.patch && diff -q work.txt new.txt
```

```bash
# Compare two directory trees before a rsync/migration (summary only)
diff -rq /etc/orig /etc/current
```

```bash
# Full tree patch including new and deleted files
diff -ruN orig/ work/ > feature.patch
```

```bash
# Did my command change the file? Process substitution, no temp files
diff <(sort names.txt) names.sorted
```

```bash
# Show only what changed between two runs, ignoring whitespace churn
diff -u -b run1.log run2.log | grep -v '^ '
```

```bash
# Which functions did the refactor touch?
diff -u old.c new.c | grep '^+++'   # headers; or use diff -p for per-hunk context
diff -p -u old.c new.c | head -20
```

```bash
# Side-by-side review on a wide terminal
diff -y -W 180 --left-column proposal-v1.md proposal-v2.md | less
```

```bash
# Boolean check in a script (exit status is the answer)
if diff -q deployed.conf staged.conf >/dev/null; then
  echo "in sync"
fi
```

```bash
# Generate an ed script and apply it (ed script needs w/q appended)
diff -e old.txt new.txt > e.diff
printf 'w\nq\n' >> e.diff
ed -s old.txt < e.diff
```

```bash
# CRLF pain: compare a Windows-edited file against the Unix original
diff --strip-trailing-cr -u unix.conf dos.conf
```

```bash
# Compare a command's output against a saved golden file
systemctl list-unit-files --no-pager | diff -u units.golden - | head
```

```bash
# Count hunks a patch will introduce
grep -c '^@@' <(diff -u old.c new.c)
```

## Nuances and Gotchas

- **Exit 1 is not an error.** Under `set -e`, a bare `diff a b` aborts your script whenever the files differ. Redirect into `if`/`||` or append `|| true` deliberately. The same trap in reverse: forgetting that `2` means trouble, so a missing input file looks like "differ" to scripts that only test nonzero.
- **Default output is normal format, not unified.** `diff a b > p.patch` produces something `patch` accepts, but nobody can review it and hunks lack context for fuzz matching. Make `-u` a reflex.
- **Headers carry local timestamps.** A unified diff generated twice differs byte-wise because of mtimes; `--label` (or git-style `a/` `b/` labels) is the fix when patches must be reproducible.
- **Binary inputs.** `diff` detects binary data and prints `Binary files x and y differ` — an exit-1 statement, never contents. For byte positions use `cmp`; to see a fake textual diff of binary data use `-a` knowingly.
- **CRLF makes every line differ.** Files edited on Windows acquire `\r`; a 1-line logical change becomes a whole-file diff. `--strip-trailing-cr` (or `dos2unix`) first.
- **Missing trailing newline** emits `\ No newline at end of file`; tools that concatenate patches can merge this marker into the next hunk and corrupt them. Keep a newline at EOF in source files.
- **Directory diffs are shallow without `-r`.** `diff dir1 dir2` only diffs same-named top-level files and prints `Only in` for the rest — a frequent interview trap.
- **`-N` asymmetry.** `-N` treats absent files as empty on *both* sides; `--unidirectional-new-file` restricts it to the first operand. Choose per intent when generating tree patches.
- **Whitespace flags change the comparison, not the output.** `diff -b` still prints the full original lines; it merely refuses to call them different. Reviewers who want normalized output need preprocessing, not `-w`.
- **`-i` is a byte-level fold** for the active locale and interacts with `-I` regex matching; in multibyte locales results can surprise. Verify against real data before relying on it in validation gates.
- **Pathological inputs.** Very large, very different files stress the LCS step (time and memory grow with the edit distance). `-H` trades minimality for speed; for "are these different at all", `cmp -s` is O(first difference) instead.
- **Portability.** POSIX specifies only a subset (`-c -e -f -h` legacy set plus basics); `-u`, `-y`, `-N`, `-i`, `-b`, `-w`, `-B`, `-r` in their GNU form are de-facto GNU/BSD conventions. BusyBox `diff` covers a reduced set. Scripts for minimal systems should test feature presence, not assume GNU flags.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Inputs identical (under active ignore options). |
| 1 | Inputs differ — a normal, expected result. |
| 2 | Trouble: missing/unreadable file, I/O error, bad usage. |

## Related Commands

- [`cmp`](./cmp.md) — byte-level comparison; first-difference location for binary files.
- [`diff3`](./diff3.md) — three-way comparison and merge against a common ancestor.
- [`sdiff`](./sdiff.md) — side-by-side rendering and interactive merge to a file.
- [Collection overview](./overview.md) — the diffutils family and the patch ecosystem.
- [`find`](../../shell/find.md) — generate file lists to feed tree comparisons.
- [bash](../../shell/bash.md) — process substitution (`diff <(...) <(...)`) patterns.
- [Part overview](../overview.md) — all userland binary collections.

## Interview Questions

### Q: What do exit codes 0, 1, and 2 from diff mean, and why does that design matter?

0 means the inputs are identical, 1 means they differ, 2 means trouble (missing file, I/O error, bad option). The design matters because the *interesting* result — "differ" — is a normal outcome, so pipelines can branch on the status without parsing output: `diff -q a b >/dev/null` is a boolean test. It also forces explicit handling of the trouble case, which naive `set -e` scripts get wrong since differing files abort them.

### Q: Why does every patch you see start with `---` and `+++` lines, and what is in a hunk header?

Those are the old-file and new-file headers produced by unified format; `patch` reads them to locate targets (including rename hints in the path). The hunk header `@@ -1,5 +1,6 @@` gives the old start/count and new start/count so tools can apply the hunk at the right offset even when surrounding lines changed, using the context lines and a fuzz allowance. Counts of 0 encode pure insertions ("after line N"), and a single-line range omits the count.

### Q: How do you make a complete patch of a directory tree including newly added and deleted files?

`diff -ruN orig/ work/`. `-r` recurses, `-u` makes it reviewable and appliable, and `-N` treats files missing on one side as empty, so additions appear as diffs against nothing and deletions as removals of every line. Without `-N` the patch silently misses new and deleted files — a classic incomplete-release bug.

### Q: You are asked whether two firmware images are identical and, if not, where they first diverge. Why is diff the wrong tool and what do you use?

`diff` is line-oriented and will just report `Binary files ... differ` with no position. `cmp` is byte-oriented: plain `cmp` prints the first differing byte number and line; `cmp -l` lists every differing byte with octal values (slow, no early exit); `cmp -n LEN` limits the range. diff's `-a` text-forcing would merely dump noise.

### Q: What is the difference between `-b`, `-w`, and `-Z`?

`-b` ignores changes in the *amount* of whitespace within a line (runs of spaces collapse, but whitespace is not deleted where absent); `-w` ignores *all* whitespace, so `ab` equals `a b`; `-Z` ignores only trailing whitespace at end of line. They affect the comparison verdict only — the diff still prints original lines. Code-review noise from indentation changes calls for `-b`, tab-vs-space arguments for `-E`, CRLF issues for `--strip-trailing-cr`.

### Q: How does diff relate to git diff — same program?

No. `git diff` is an independent implementation (xdiff) that reimplements the same Myers-algorithm family, then layers on index awareness, rename/copy detection, word-level and color rendering, and hunk-header function context (`-p` analog exists in GNU diff too). The *output* is unified-format compatible so `git diff > x.patch` remains consumable by classic `patch`, preserving the 1970s/1980s lineage: Bell Labs diff, unified format from the patch ecosystem, GNU diffutils as the free reference implementation.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/diffutils/diff.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/diffutils/)
