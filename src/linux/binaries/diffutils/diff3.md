# diff3 — three-way comparison and merge against a base

## Overview

`diff3` compares three files line by line — canonically **MYFILE OLDFILE YOURFILE**, where OLDFILE is the common ancestor — and either reports the differences between all three or *merges* the two divergent edits back into one file, bracketing changes that collide. It ships in the `diffutils` package (Debian bookworm: GNU diffutils 3.8) at `/usr/bin/diff3`. It is the conceptual ancestor of every three-way merge you have used: git's conflict markers, `git merge-file`, and IDE merge dialogs all implement the base/ours/theirs model that diff3 standardized, with the same conflict-bracket rendering and the same "exit 1 means conflicts, not failure" convention.

`diff3` is often confused with running plain `diff` twice (which answers "what changed on each side" but cannot tell whether two changes *collide*), with `sdiff` (two-way, interactive, no ancestor), and with `git merge`/`git merge-file` (production merge machinery that borrows the model but adds rename detection, content filters, and its own marker set). When you are not in git, or when a merge must be scripted without a repository, diff3 is still the standard tool.

| Field | Value |
| --- | --- |
| Package | diffutils (Debian bookworm: GNU diffutils 3.8) |
| Man section | 1 |
| Path | /usr/bin/diff3 |
| First appeared | 4.3BSD-era three-way merge tool; GNU diffutils mid-1980s |
| Standards | POSIX.1-2018 (`diff3`) |

## Synopsis

```
diff3 [OPTION]... MYFILE OLDFILE YOURFILE
```

Common one-line forms:

```
diff3 -m mine base yours > merged   # merge; conflicts bracketed, exit 1
diff3 -m -E mine base yours         # merge, git-style markers (no base section)
diff3 mine base yours               # human-readable report of all three
diff3 -X mine base yours            # ed script covering only overlapping changes
```

Any file operand may be `-` (stdin), but only one input may be stdin. Up to three `-L LABEL` options rename the files in output (order: MYFILE, OLDFILE, YOURFILE).

## How It Works

### The three-way model

diff3 aligns all three files simultaneously and, for every region where the files differ, classifies each side as unchanged, older, or newer *relative to the base*. That classification is what a pair of two-way diffs cannot give you: knowing that both MYFILE and YOURFILE changed region X is only half the story — you need to know whether they changed it *differently*. The decision table:

```
              change in region X
 MYFILE       YOURFILE        diff3's verdict
 --------     ----------      ---------------------------
 unchanged    changed         take YOURFILE's change
 changed      unchanged       keep MYFILE's change
 changed      changed, same   take it (trivial agreement)
 changed      changed, diff.  CONFLICT -> bracket, exit 1
```

This is exactly the logic a human applies in a code review of two branches off the same base — and exactly what git's merge machinery does, minus the repository features.

### Default report format

With no merge option, diff3 prints a human-readable report: `====` separates regions; inside a region, `N:c`-style ranges name the file number (1 = MYFILE, 2 = OLDFILE, 3 = YOURFILE) and the affected lines, with ` ` (two-space prefix) lines quoting content:

```
$ diff3 mine.txt base.txt yours.txt
====
1:3c
  THREE-a
2:3c
  three
3:3c
  THREE-b
```

Read it as: all three files disagree about line 3. This format is for reading and grepping — it is not appliable by `patch` or `ed`.

### Merge mode (`-m`) and its two flavors

`-m` (`--merge`) makes diff3 perform the merge internally and print the merged file. Per the implementation, `-m` without any script option implies `-A`, whose conflict brackets carry the ancestor's version in the middle:

```
$ diff3 -m mine.txt base.txt yours.txt
one
two
<<<<<<< mine.txt
THREE-a
||||||| base.txt
three
=======
THREE-b
>>>>>>> yours.txt
four
five
$ echo $?
1
```

`-E` (`--show-overlap`) keeps only overlapping changes in play and renders git-style markers *without* the base section:

```
$ diff3 -m -E mine.txt base.txt yours.txt
one
two
<<<<<<< mine.txt
THREE-a
=======
THREE-b
>>>>>>> yours.txt
four
five
```

The markers look like git's but are labeled with file names (or your `-L` labels); git labels by ref and configures this same `-E`-style display via `merge.conflictStyle = diff3` to re-add the base section. Resolving means editing the bracketed region down to one version and stripping all bracket lines — there is no magic: `-m` output is plain text you post-process with an editor or `sed`.

Non-overlapping edits merge silently. Two facts worth internalizing from the algorithm's conservativeness: changes in *adjacent* lines (no blank context between them) count as overlapping and conflict, and an edit that merely touches the line next to the other side's insertion will conflict too. diff3 prefers noisy-but-safe over silent wrong merges — the same trade git makes.

### Ed-script modes (the POSIX half)

diff3 can also emit ed scripts instead of merged text, which is how POSIX specifies most of its surface:

- `-e` — ed script incorporating all changes of OLDFILE→YOURFILE into MYFILE.
- `-3` (`--easy-only`) — like `-e` but only the *non-overlapping* changes.
- `-x` (`--overlap-only`) — only the *overlapping* changes.
- `-A` (`--show-all`) — all changes, conflicts bracketed (the source of `-m`'s default rendering).
- `-E` / `-X` — bracketed variants of `-e` / `-x`.
- `-i` — append `w` and `q` to the ed script so it saves and quits when piped into `ed`.

The `-m` man-page note is the practical advice: diff3 merging *internally* is more robust than applying its ed scripts with `ed` for unusual input, which is why scripting merges should call `-m` rather than composing `-e` + `ed`.

### Labels and stdin

`-L LABEL` (repeat up to three times, in MYFILE/OLDFILE/YOURFILE order) rewrites the names in brackets — the standard trick for making diff3 output look like git's:

```
$ diff3 -m -L HEAD -L base -L feature mine.txt base.txt yours.txt | head -5
one
two
<<<<<<< HEAD
THREE-a
```

Pipelines work too: `git show branch:file | diff3 -m local base -` merges a remote branch's file into your working copy without a checkout.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m`, `--merge` | Output the merged file; conflicts bracketed (implies `-A` unless `-E`/`-X` given). |
| `-A`, `--show-all` | All changes; conflicts bracketed with the base section included. |
| `-E`, `--show-overlap` | Overlap-aware merge; git-style markers without base section. |
| `-3`, `--easy-only` | Ed script with only non-overlapping changes. |
| `-x`, `--overlap-only` | Ed script with only overlapping changes. |
| `-X` | Like `-x`, conflicts bracketed. |
| `-e` | Ed script, all changes (no brackets). |
| `-i` | Append `w`/`q` to ed scripts. |
| `-L LABEL` | Use LABEL instead of file name (repeat up to 3×, in operand order). |
| `-T`, `--initial-tab` | Prepend a tab so columns line up in reports. |
| `-a`, `--text` | Treat all files as text. |
| `--diff-program=PROG` | Use PROG for the underlying comparisons. |

## Usage Patterns

```bash
# Merge two divergent copies of a file; conflicts left bracketed for editing
diff3 -m config.mine config.base config.theirs > config.merged
grep -n '<<<<<<<\|>>>>>>>' config.merged   # locate the collisions
```

```bash
# Gate a script on conflict presence: exit 1 means conflicts, not failure
if diff3 -m mine base yours > merged; then
  echo "clean merge"
else
  echo "manual resolution needed"; exit 73
fi
```

```bash
# git-style markers for humans used to git's rendering
diff3 -m -E -L HEAD -L base -L feature mine base yours > merged
```

```bash
# Merge a branch file straight from git plumbing without checking out
git show origin/feature:src/app.c | diff3 -m src/app.c /tmp/base.c - > merged.c
```

```bash
# Who touched what? Default report names all three sides per region
diff3 deployed.conf staging.conf canary.conf | less
```

```bash
# Only the collisions, nothing else (quick conflict census)
diff3 -X mine base yours
```

```bash
# Only the safe, non-overlapping changes as an ed script
diff3 -3 mine base yours > safe.ed
```

```bash
# Verify a merge helper's claim that a file merged cleanly
diff3 -m theirs base mine | cmp - merged-result && echo "clean by construction"
```

```bash
# Same edit on both sides: diff3 takes it silently (agreement, not conflict)
printf 'a\nb\n' > b.txt; printf 'a\nB\n' > m.txt; printf 'a\nB\n' > y.txt
diff3 -m m.txt b.txt y.txt   # prints a, B; exit 0
```

```bash
# Ignore-only-casing drift between environments before merging for real
diff3 --diff-program='diff -i' -m mine base yours
```

## Nuances and Gotchas

- **Operand order is semantic, not arbitrary.** `MYFILE OLDFILE YOURFILE` — the middle operand is the ancestor. Swapping two operands does not produce a "different but valid" merge; it silently changes what is considered base, flipping which side's edits are applied. Name your variables `mine base yours` in scripts.
- **Exit 1 means conflicts, which is success for the workflow.** Scripts under `set -e` abort exactly when a merge needs attention — invert the test (`diff3 -m ... || :`) or branch on the status explicitly. 0 = clean, 1 = conflicts bracketed, 2 = trouble.
- **Adjacent changes conflict.** An edit on line N and an edit on line N+1 (or an insertion right after a changed line) are bracketed as overlapping even though a human might call them independent. Expect diff3 (and git) to be conservative; separate edits with context lines if you want them to merge cleanly.
- **`-m` alone shows the base section; `-E` does not.** The default `<<<<<<< file / ||||||| base / ======= / >>>>>>> file` block is `-A`-style; teams used to git's two-part markers should standardize on `-E` or their tooling will not recognize the middle section.
- **Markers are plain text in the output file.** A failed merge is *your* file now: a script that forgets to check for `<<<<<<<` can ship conflict markers to production. Grep for them as a post-merge gate.
- **Labels are names, not refs.** diff3 prints whatever strings you pass; nothing resolves branches or commits. The git resemblance is cosmetic — there is no rename detection, no content filters, no index.
- **No binary mode.** diff3 is line-oriented text tooling; merging binary blobs is out of scope (cmp and hexdump are your diagnostic tools, not diff3).
- **One stdin.** Only a single `-` operand is allowed; two pipes into one diff3 invocation is a usage error, so stage intermediate results in temp files.
- **Portability.** POSIX specifies the report format, `-e -3 -x -E -X -A` and the operand model; GNU adds `-m` as a first-class option (BSD diff3 has it too; ancient SVR4 diff3 required composing ed scripts). BusyBox has no diff3.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Merge/report produced with no conflicts. |
| 1 | Overlapping changes: conflicts bracketed (merge mode) or isolated (report mode). |
| 2 | Trouble: missing file, I/O error, bad usage. |

## Related Commands

- [`diff`](./diff.md) — two-way comparison; the engine under diff3's hood.
- [`cmp`](./cmp.md) — byte-level check when merged artifacts must be verified bit-for-bit.
- [`sdiff`](./sdiff.md) — interactive two-way merge; the human-in-the-loop sibling.
- [Collection overview](./overview.md) — the diffutils family and the patch ecosystem.
- [`grep`](../../shell/grep.md) — scan merged output for leftover conflict markers.
- [Part overview](../overview.md) — all userland binary collections.

## Interview Questions

### Q: Why does a three-way merge need the base file at all? Two files and a diff seem enough.

Without the ancestor you cannot distinguish "the other side changed this region" from "both sides changed it". The base classifies each region: unchanged-on-one-side means the other side's edit applies cleanly; changed-on-both-sides means a potential collision that must be surfaced. That classification is precisely what makes merges safe, and it is why every real merge tool — diff3 and git alike — is built around a common ancestor.

### Q: What are diff3's exit codes, and how should a script consume a merge?

0 = clean merge or report, 1 = conflicts (bracketed in `-m` output, isolated by `-X`), 2 = trouble. A robust script writes `diff3 -m mine base yours > merged`, branches on the status, and — regardless of status — greps the output for `<<<<<<<` before trusting it, because exit 0 with clean markers is the only acceptable artifact. Under `set -e`, remember that status 1 is the *expected* conflict signal, not a crash.

### Q: Explain the difference between diff3 -m and diff3 -m -E output.

`-m` implies `-A`: conflict brackets include the ancestor section (`||||||| base.txt`) so the resolver sees what the region originally said. `-E` renders only the two competing versions in git's two-part style. Functionally the merge is the same; presentationally `-A` carries more information (the base), which is why git offers `merge.conflictStyle = diff3` for exactly this view.

### Q: Two branches edit adjacent lines. What happens and why?

diff3 reports a conflict. Regions without unchanged context between them are treated as overlapping, because the merge cannot prove the edits are independent — an insertion after line N and a rewrite of line N+1 could both be describing the same logical change. The tool chooses a noisy, safe conflict over a silently wrong merge; the standard remedy is for developers to rebase so edits are separated by context, or to resolve manually.

### Q: How does diff3 relate to git's merge machinery — is git just running diff3?

No, git ships its own merge implementation (xdiff-based `git merge-file`, used by `git merge`), with rename detection, content filters, and multiple merge strategies layered on top. But the *model* — base/ours/theirs, overlap → conflict, bracket markers, `-E`-style two-part vs `-A`-style three-part display — is diff3's, and git can even display conflicts in diff3's base-including style. Knowing one transfers directly to the other.

### Q: You must merge two production config files on a server with no git and no network. Walk the workflow.

Copy the current file as the base reference (from backup or the package's `.dist` original), obtain both edited versions, then `diff3 -m local.conf base.conf remote.conf > merged.conf`. Check the exit status for conflicts, edit bracketed regions, grep for leftover markers, run the service's config validation, and reload. diff3 plus standard text tools is a complete offline merge kit — no repository required.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/diffutils/diff3.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/diffutils/)
