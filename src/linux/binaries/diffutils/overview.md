# diffutils — comparing, merging, and patching files

## One question, four tools

Every administrative and development workflow eventually asks: *are these two things the same, and if not, what exactly changed?* The GNU `diffutils` package (Debian bookworm: GNU diffutils 3.8) is the classical answer — four binaries, one data model, one exit-code convention. A single source package ships all of them at `/usr/bin`:

```
┌────────────────────────────────────────────────────────────┐
│  diffutils — the file-comparison toolbox                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   diff    line-by-line compare -> hunks -> patch format    │
│      │                                                     │
│      ├── cmp     same question, byte-level, for binaries   │
│      ├── diff3   three files + a base -> automatic merge   │
│      └── sdiff   side-by-side view + interactive 2-way     │
│                  merge with a human at the % prompt        │
│                                                            │
│   output artifact: unified diffs consumed by `patch`       │
│   and by git apply — the interchange format of code review │
└────────────────────────────────────────────────────────────┘
```

The division of labor is by *input type* and *interaction model*, not by domain: text vs bytes, two-way vs three-way, report vs merge. The lineage is one of the oldest in userland: `diff` and `cmp` date to Bell Labs Unix (early 1970s), `diff3` arrived with the BSD three-way merge work, and the GNU rewrite of the mid-1980s (the basis of every modern Linux system) added unified format, recursion, and the flag surface used today. Four decades later the package still has four binaries and no dependencies to speak of — which is why it shows up in rescue shells, minimal containers, and interview questions alike.

## The four binaries

| Binary | Question it answers | Model | Page |
| --- | --- | --- | --- |
| `diff` | "Which lines changed between A and B?" | line-oriented, text | [`./diff.md`](./diff.md) |
| `cmp` | "Are these bit-identical? Where is the first divergent byte?" | byte-oriented, any file | [`./cmp.md`](./cmp.md) |
| `diff3` | "Two sides edited a common base — what merges cleanly, what conflicts?" | three-way merge | [`./diff3.md`](./diff3.md) |
| `sdiff` | "Show me both files side by side and let me pick line by line." | interactive two-way | [`./sdiff.md`](./sdiff.md) |

What each is routinely confused with — and how to keep them apart:

- **diff vs cmp**: diff is structural and wants text; cmp is positional and takes bytes. On binary inputs diff punts (`Binary files a and b differ`), cmp names the first divergent byte.
- **diff vs git diff**: separate implementations of the same algorithm family and output format. git adds index awareness, rename detection, coloring; the diffutils tools need no repository.
- **diff3 vs sdiff**: diff3 *automates* a merge using an ancestor file; sdiff makes *you* the merge algorithm, line by line, with no base.
- **any of them vs checksums**: `sha256sum` answers identity for many files at once; the diffutils tools answer *what changed*, which a digest cannot.

`diff` is the flagship and the one interviewers probe deepest: it carries the output-format zoo (`-u`, `-c`, normal, `-y`, `-e`, `-n`, `-D`), directory recursion, whitespace-lenience flags, and the exit-code contract the other three inherit.

## The diff → patch pipeline

`diff`'s most consequential output is not what you read in a terminal — it is the **unified diff** (`diff -u`), a self-contained set of edit instructions: file headers, `@@ -l,s +l,s @@` hunk headers, and context lines that let a receiver apply the changes even if their copy has drifted slightly. Larry Wall's `patch` program (1985) turned that output into the first distributed code-review workflow; the lineage runs unbroken through mailing-list-era kernel patches, `.patch`/`.diff` files attached to bug trackers, and into git, whose `git diff`/`git apply` reimplement the same format and the same Myers-algorithm family rather than shelling out to these binaries.

A real, generated example worth being able to read cold:

```
$ diff -u a.txt b.txt
--- a.txt       2026-10-09 16:33:31.322925999 +0000
+++ b.txt       2026-10-09 16:33:31.322925999 +0000
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

Anatomy: the `---`/`+++` headers name old and new files (with timestamps; `--label` overrides them); `@@ -1,5 +1,6 @@` says *old lines 1–5 became new lines 1–6* (a count of 1 is omitted, a count of 0 means "insert after this line"); ` `-prefixed lines are context, `-` is removed, `+` is added.

Three practical consequences of the patch lineage:

1. **The format is a contract.** Anything that emits valid unified hunks (`diff`, `git diff`, a hand-written script) can feed anything that consumes them (`patch`, `git apply`, review UIs). Tool-agnostic by construction.
2. **Context lines are the transport tolerance.** `-U3` is not decoration; `patch` locates hunks by context with fuzz, which is why patches survive upstream drift — and why `-U0` patches apply only when offsets are exact.
3. **Headers carry metadata.** File names and timestamps in `---`/`+++` lines drive target selection; `--label` (or git's `a/` `b/` prefixes) makes patches reproducible and rename-aware.

The round trip is the standard sanity check before sending a patch anywhere:

```bash
$ diff -u --label a/old.txt --label b/old.txt old.txt new.txt > fix.patch
$ cp old.txt work.txt && patch work.txt < fix.patch
patching file work.txt
$ diff -q work.txt new.txt && echo applied
applied
```

## Exit codes as data

All four binaries encode their verdict in the exit status — one of the cleanest "exit code is the answer" conventions in Unix userland, and the reason these tools compose so well in scripts:

| Exit | `diff` | `cmp` | `sdiff` | `diff3` |
| --- | --- | --- | --- | --- |
| 0 | identical | identical | identical | merge had no conflicts |
| 1 | differ | differ | differ | **conflicts** (bracketed/isolated) |
| 2 | trouble (missing file, I/O) | trouble | trouble (incl. `q`-aborted merge) | trouble |

The interview-grade subtlety: **1 is a normal, expected answer.** Under `set -e` a bare `diff a b` kills your script precisely when the files differ; `cmp -s` in an `if` is the idiomatic boolean test; `diff3 -m ... || handle-conflicts` is a control-flow construct, not error handling. Exit 2 is the only real failure — and it is distinct, so scripts can separate "the files disagree" from "I could not read the files".

```
$ diff -q a.txt a.txt; echo $?     # 0
$ diff -q a.txt b.txt; echo $?     # 1
$ diff -q a.txt /nope; echo $?     # 2
```

## Output formats at a glance

All line-oriented formats render the same internal hunk list (a longest-common-subsequence computation, Myers' algorithm family in GNU diff); pick per audience:

```
normal (default)      unified (-u)          context (-c)        side-by-side (-y)
  2c2                 --- a.txt             *** a.txt           bravo        |  bravoo
< bravo               +++ b.txt             --- b.txt
---                   @@ -1,5 +1,6 @@       ***************
> bravoo               alpha                *** 1,5 ****
                       -bravo                ! bravo
                       +bravoo               ...
```

Machine formats: `-e` ed script, `-n` RCS diff, `-D NAME` C preprocessor merge (diff3's ancestor idea in one binary). Of these, only unified matters for day-to-day patch exchange; the others appear in legacy tooling and interview trivia. Leniency flags (`-i` case, `-b`/`-w` whitespace, `-B` blank lines, `-I RE` matching lines, `--strip-trailing-cr` CRLF) tune the *comparison*, never rewrite the printed text.

## Directory and tree comparison

`diff` doubles as a tree differ — the base of every "what changed between these two releases" workflow that predates git:

```bash
$ diff -rq orig/ work/
Only in work: new.conf
Files orig/app.c and work/app.c differ
$ diff -ruN orig/ work/ > feature.patch     # complete patch incl. new/deleted files
```

- `-r` recurses into common subdirectories; without it the comparison is one level deep (a perennial trap).
- `Only in dir: name` marks asymmetric entries; `-N` instead treats missing files as empty so they appear as real hunks in the patch.
- `-x PAT` / `-X FILE` exclude build artifacts; `-q` reduces output to the verdict per file.

## Where diffutils ends

Adjacent tools cover what the four binaries deliberately do not:

- **`comm`** (coreutils) — set operations on *sorted* line files (only-in-A / only-in-B / common). Cheaper than diff when order does not matter and input can be sorted; no patch output.
- **`rsync --dry-run --itemize-changes`** — tree synchronization verdicts tuned for transfer; uses quick-check heuristics (size + mtime) that `diff`'s byte-honest comparison does not.
- **`git diff`** — repository-aware diffing with rename detection; same output format, different engine. Outside a repo, `git diff --no-index` is a convenient unified-diff generator.
- **checksum tooling** (`sha256sum`, et al.) — identity across many files, one digest each; never tells you *what* changed.
- **merge frontends** (`vimdiff`, `meld`, `git mergetool`) — interactive merges with better ergonomics and heavier dependencies; `sdiff`/`diff3` remain the POSIX-portable core.

Interviewers occasionally probe these boundaries: knowing *why* `comm` needs sorted input, or why `rsync`'s size+mtime quick check can miss same-size same-mtime edits, is diffutils-adjacent literacy that signals depth.

## Choosing the right comparison

```
        inputs text?
        ┌─── no ──> cmp (-b -l for detail, -s in scripts)
        │
       yes
        │
   need a merge?
        ├── three versions with a base ──> diff3 -m (check exit 1)
        ├── two versions, human decides ──> sdiff -o
        │
   just a report?
        ├── boolean only ──> diff -q / cmp -s (exit status)
        ├── patch to send ──> diff -u (then `patch`)
        └── eyeball review ──> diff -u | pager, or sdiff -w $COLUMNS
```

## Scripting recipes

```bash
# Config-drift watchdog: diff vs last-known-good, alert on exit 1
if ! diff -q /etc/ssh/sshd_config /var/backups/sshd_config.known-good >/dev/null; then
  logger -t drift "sshd_config changed: $(diff /var/backups/sshd_config.known-good /etc/ssh/sshd_config | head -5)"
fi
```

```bash
# Reproducible tree patch for a bug report (no timestamps, no artifacts)
diff -ruN --exclude '*.o' --exclude '*.d' orig/ work/ > repro.patch
```

```bash
# Two-way merge decided by policy, not by hand: keep the left side's value
printf 'l\n%.0s' $(seq 1 "$(diff -y --suppress-common-lines a b | wc -l)") \
  | sdiff -o merged.txt a b
```

```bash
# Conflict gate: never ship a file that still carries merge brackets
grep -rn '^<<<<<<<\|^>>>>>>>' --include='*.c' . && { echo "unresolved conflicts"; exit 1; } || true
```

```bash
# Golden-output test in a shell test harness (exit codes as assertions)
diff -u expected.txt <(./prog --emit) || { echo FAIL; exit 1; }
```

```bash
# Verify a mirrored directory without reading contents twice (name+size only first, then bytes)
diff -rq --no-dereference /data /mirror/data
```

```bash
# Watch for tampering in a critical file between two polling intervals
before=$(cksum /etc/crontab); sleep 300
after=$(cksum /etc/crontab)
[ "$before" = "$after" ] || echo "crontab changed within the last 5 minutes"
```

```bash
# Produce a per-file change summary across two trees, sorted by path
diff -rq orig/ work/ | sed 's/^Files \(.*\) and \(.*\) differ$/\1/' | sort
```

```bash
# Apply a patch only if it is dry-run clean (patch --dry-run first)
patch --dry-run -p1 < feature.patch && patch -p1 < feature.patch
```

## Quick answers

| Task | Command |
| --- | --- |
| Are these binaries identical? | `cmp -s a b; echo $?` |
| Where do two images first diverge? | `cmp a b` |
| Reviewable patch of one file | `diff -u --label a/f --label b/f f.orig f` |
| Patch of a whole tree incl. new/deleted | `diff -ruN orig/ work/` |
| Which files differ in two trees (names only) | `diff -rq dirA dirB` |
| Automatic merge against a base | `diff3 -m mine base yours > merged` |
| Manual line-by-line merge | `sdiff -o merged mine yours` |
| Ignore indentation/formatting churn | `diff -u -b` (or `-w`, `-Z`) |
| Compare CRLF-edited file to LF original | `diff --strip-trailing-cr -u a b` |
| Diff live command output vs saved file | `diff -u golden <(cmd)` |

## Interview threads this collection covers

- **Exit-code semantics** — 0/1/2 across all four tools; 1-is-success design; `set -e` interactions.
- **Unified format literacy** — hunk header grammar, context lines, `\ No newline at end of file`, `--label` for reproducibility.
- **Tree diffs** — `-r`, `Only in`, `-N` for complete patches, `-x` exclusions.
- **Merge models** — why three-way needs a base (diff3) and what two-way interactive (sdiff) costs; adjacency conflicts; conflict-marker hygiene.
- **Byte vs line orientation** — cmp's early exit, octal verbose output, prefix/EOF detection for truncation.
- **Ecosystem context** — diff → patch lineage; where git reuses the format and reimplements the engine.

## Inventory

| Page | Binary | Man section | Role in the family |
| --- | --- | --- | --- |
| [diff](./diff.md) | `/usr/bin/diff` | 1 | flagship: compare text, generate patches, recurse trees |
| [cmp](./cmp.md) | `/usr/bin/cmp` | 1 | byte-level equality and first-difference locator |
| [diff3](./diff3.md) | `/usr/bin/diff3` | 1 | three-way compare and merge against a base |
| [sdiff](./sdiff.md) | `/usr/bin/sdiff` | 1 | side-by-side view and interactive two-way merge |

## Reading order

1. **[diff](./diff.md)** first — formats, hunks, recursion, exit codes set the vocabulary.
2. **[cmp](./cmp.md)** — the same contract, byte-oriented; short and sharp.
3. **[diff3](./diff3.md)** — three-way model; maps directly onto git merge behavior.
4. **[sdiff](./sdiff.md)** — interactive layer; the `%` prompt and merge workflow.

## Related pages in this book

- [`find`](../../shell/find.md) — enumerate file pairs across trees to compare or patch.
- [`grep`](../../shell/grep.md) — scan diffs and merged files for conflict markers.
- [`xargs`](../../shell/xargs.md) — batch comparisons over `find` results.
- [bash](../../shell/bash.md) — process substitution: `diff <(...) <(...)`.
- [Man pages](../../reference/man-pages.md) — how to read the diffutils manual pages well.
- [Part overview](../overview.md) — every userland binary collection in this part.

## References

- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/diffutils/)
- [Source — Debian sources](https://sources.debian.org/src/diffutils/)
