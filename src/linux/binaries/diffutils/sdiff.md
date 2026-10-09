# sdiff — side-by-side diff and interactive two-way merge

## Overview

`sdiff` shows two text files side by side in two columns separated by a gutter, and — with `-o FILE` — turns into a *line-oriented interactive merge editor*: at every difference it stops, prints a `%` prompt, and lets you choose the left version, the right version, both, or edit a variant of your own, assembling the choices into an output file. It ships in the `diffutils` package (Debian bookworm: GNU diffutils 3.8) at `/usr/bin/sdiff`. Historically it predates colorized terminals and `vimdiff`; it remains the POSIX-blessed way to do a visual compare and a merge in a bare terminal with nothing but a shell.

`sdiff` is often confused with `diff -y` (which produces the same two-column *rendering* but is not interactive), with `diff3 -m` (three-way, automatic merge with conflict markers, no ancestor concept here), and with `vimdiff`/`meld` (full-screen TUI/GUI editors built on the same idea). sdiff's niche: zero dependencies beyond diffutils, scriptable via stdin, and merge output you fully control line by line.

| Field | Value |
| --- | --- |
| Package | diffutils (Debian bookworm: GNU diffutils 3.8) |
| Man section | 1 |
| Path | /usr/bin/sdiff |
| First appeared | 4.3BSD era (1980s); GNU diffutils rewrite; POSIX.1-2018 |
| Standards | POSIX.1-2018 (`sdiff`) |

## Synopsis

```
sdiff [OPTION]... FILE1 FILE2
```

Common one-line forms:

```
sdiff -w 160 a.c b.c            # wide side-by-side view
sdiff -s a.c b.c                # only the differing lines
sdiff -o merged.txt a.c b.c     # interactive merge, output to merged.txt
printf 'l\nr\n' | sdiff -o m.txt a.c b.c   # scripted (non-tty) merge
```

A `FILE` of `-` reads standard input. Exit status follows the diffutils convention: 0 identical, 1 different, 2 trouble.

## How It Works

### Two-column rendering

sdiff splits the terminal width (default 130 print columns, `-w` to override) between the two files and prints a one-character gutter between columns:

```
$ sdiff -w 40 s1.txt s2.txt
left-A		   |	right-A
left-B			left-B
common			common
right-C		   |	right-C2
```

Gutter legend:

```
 blank   lines are identical on both sides
   |     lines differ (left vs right)
   <     line exists only in FILE1 (right column blank)
   >     line exists only in FILE2 (left column blank)
```

`-l` (`--left-column`) prints only the left copy of common lines (denser), `-s` (`--suppress-common-lines`) hides common lines entirely (difference-only view). Tabs are handled with `--tabsize`, expanded with `-t` so columns cannot drift; `-d` (`--minimal`) asks the underlying diff engine for the smallest possible change set, `-H` for the large-file heuristic.

Under the hood, GNU sdiff is a thin driver over `diff`: it invokes the diff engine (its own or `--diff-program=PROG`) with side-by-side formatting, then either prints the result or — in merge mode — walks the hunk list interactively. That design explains two things: sdiff accepts essentially diff's ignore flags (`-i`, `-b`, `-w`, `-B`, `-I`, `-Z`, `--strip-trailing-cr`), and its output inherits diff's diff-alignment quirks. POSIX documents sdiff as a first-class utility, but the GNU implementation is this wrapper.

### Merge mode: the `%` prompt

With `-o FILE`, sdiff changes personality. It still renders side by side, but at each difference it prompts:

```
left-A			     |	right-A
%_
```

The commands are single letters (some two):

| Command | Effect |
| --- | --- |
| `l` | Use the left version (FILE1). |
| `r` | Use the right version (FILE2). |
| `s` | Include the common lines of this region. |
| `q` | Quit; the merge so far is kept, the rest abandoned. |
| `el` / `e1` | Edit the left version in `$EDITOR`, then use the result. |
| `er` / `e2` | Edit the right version in `$EDITOR`, then use the result. |
| `eb` / `e3` | Edit both versions together in `$EDITOR`, then use the result. |
| `ed` | Edit both versions, each stripped of a trailing newline. |

Editing commands run `$EDITOR` on a temporary copy and install what you save — the escape hatch for "neither side is right". The `s` command matters when common lines were suppressed or when you want the surrounding context included in the merged output around a conflict.

A full session, choosing left for the first conflict and right for the second:

```
$ printf 'l\nr\n' | sdiff -o merged.txt -w 60 s1.txt s2.txt
$ cat merged.txt
left-A
left-B
common
right-C2
```

The prompt loop reads from stdin whatever it is connected to. In a terminal that is your keyboard; in a pipe it is the pipe — which is why `printf 'l\nr\n'` works as a scripted merge. There is no "take left everywhere" command-line switch; a loop of `l` answers *is* the batch form.

### Merge-mode semantics worth memorizing

```
$ printf 'r\nq\n' | sdiff -o m3.txt s1.txt s2.txt   # quit mid-merge
$ cat m3.txt
right-A
left-B
common
$ echo $?                                            # exit status 2
2
```

Quitting keeps what was decided and discards the pending difference, exiting with **2** (trouble). Two consequences: a `q`-terminated merge is *partial*, and the exit status does not mean the merge failed catastrophically — but the output file is incomplete, so treat any nonzero exit after `-o` as suspect.

## Options That Matter

### Display

| Option | Effect |
| --- | --- |
| `-w NUM`, `--width=NUM` | Total output width in print columns (default 130). |
| `-l`, `--left-column` | Print only the left column for common lines. |
| `-s`, `--suppress-common-lines` | Show only differing lines. |
| `-t`, `--expand-tabs` | Expand tabs to spaces so columns stay aligned. |
| `--tabsize=NUM` | Tab stops every NUM columns (default 8). |

### Merge mode

| Option | Effect |
| --- | --- |
| `-o FILE`, `--output=FILE` | Enable interactive merge, write result to FILE. |
| `--diff-program=PROG` | Use PROG as the comparison engine. |

### Comparison leniency (shared with diff)

| Option | Effect |
| --- | --- |
| `-i` | Ignore case. |
| `-b` / `-w` | Ignore whitespace amounts / all whitespace. |
| `-Z` / `-E` | Ignore trailing whitespace / tab expansion. |
| `-B` | Ignore hunks of only blank lines. |
| `-I RE` | Ignore hunks whose lines all match RE. |
| `--strip-trailing-cr` | Ignore CRLF/LF differences. |
| `-a`, `--text` | Force text mode. |
| `-d` / `-H` | Minimal diff / large-files heuristic. |

## Usage Patterns

```bash
# Quick visual compare of two config revisions on a wide terminal
sdiff -w 200 /etc/nginx/nginx.conf /etc/nginx/nginx.conf.orig | less
```

```bash
# Only the differences — a fast conflict list
sdiff -s -w 160 old.c new.c
```

```bash
# Denser view: show common lines once, from the left
sdiff -l -w 160 services.yaml services.yaml.new
```

```bash
# Interactive merge into a new file (decide each hunk: l, r, s, or el/er)
sdiff -o resolved.txt deploy.sh.mine deploy.sh.theirs
```

```bash
# Neither side is right? At the % prompt: eb, fix both in $EDITOR, save
sdiff -o resolved.txt mine.txt yours.txt
```

```bash
# Scripted merge: take left for everything, no human in the loop
for i in $(seq 1 50); do printf 'l\n'; done | sdiff -o all-left.txt a.txt b.txt
```

```bash
# Scripted merge driven by a policy: pick the side that contains the marker
paste -d'\n' <(yes l | head -20) /dev/null | sdiff -o m.txt a.txt b.txt  # crude; prefer diff3 for logic
```

```bash
# Whitespace-only churn should not produce merge prompts
sdiff -b -Z -o clean-merge.txt formatted.c original.c
```

```bash
# Compare process output against a file, both columns
sdiff -w 140 <(df -h) df-last-week.txt
```

```bash
# Post-merge sanity: no markers, and it should differ from neither parent wholesale
grep -n '[<>|]' merged.txt | head      # gutter chars cannot leak; conflict-edit leftovers can
```

## Nuances and Gotchas

- **Default width 130 is not terminal-aware.** On an 80-column terminal sdiff happily emits 130 columns and your pager wraps it into noise. Pass `-w $COLUMNS` (or a literal width) habitually.
- **`q` exits with status 2 and leaves a partial merge.** Any `-o` run that ends in `q` (or is interrupted) produces a half-merged file indistinguishable from a complete one without diffing it against the inputs. Gate on the exit status and verify the result.
- **Piped commands work but prompt echoes interleave.** With stdin not a tty, sdiff echoes `%` prompts into the visible output; the *file* written by `-o` is clean. Don't parse sdiff's stdout in merge mode — parse the `-o` file.
- **sdiff is a diff wrapper in GNU diffutils.** Its minimal/heuristic behavior, ignore-flag semantics, and bug surface are diff's; `--diff-program` can swap the engine entirely. Don't expect sdiff-specific behavior beyond rendering and prompting.
- **It is two-way, not three-way.** sdiff has no base/ancestor concept; overlapping edits are just another difference to adjudicate by hand. When a base exists, `diff3 -m` automates the easy 90% first.
- **The `s` command is easy to misread.** It does not "skip" — it includes the common lines of the current region in the merge output. Skipped/undecided input aborts the run.
- **Ignore flags affect matching, not the text written.** `sdiff -b` will happily write both spellings of a whitespace-differing line into the merge; normalization is your job afterwards.
- **No color, no mouse, no word-diff.** On modern systems `git diff --color-words` or `vimdiff` render more informatively; sdiff wins on portability and scriptability, not on ergonomics.
- **Portability.** POSIX specifies the side-by-side format, `-o`, and the core prompt commands (`l r s e q` family); GNU adds the `-e*` editor variants and long options. BSD sdiff is the same lineage; BusyBox has no sdiff.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Inputs identical (no prompts needed in merge mode; nothing written if `-o` absent). |
| 1 | Inputs differ (normal outcome; in merge mode, a merge completed end-to-end). |
| 2 | Trouble — including a merge abandoned with `q` (partial output file). |

## Related Commands

- [`diff`](./diff.md) — the engine and format reference; `diff -y` is sdiff's non-interactive half.
- [`diff3`](./diff3.md) — three-way automatic merge when a base file exists.
- [`cmp`](./cmp.md) — byte-level comparison for binary inputs.
- [Collection overview](./overview.md) — the diffutils family and the patch ecosystem.
- [bash](../../shell/bash.md) — process substitution feeding both columns.
- [`find`](../../shell/find.md) — enumerate file pairs to compare across trees.
- [Part overview](../overview.md) — all userland binary collections.

## Interview Questions

### Q: What is the difference between sdiff and diff -y, given they look identical?

`diff -y` only *renders* two columns; it prints and exits. `sdiff -o FILE` uses the same presentation as the front end of an interactive merge loop: it stops at each difference, prompts with `%`, and assembles an output file from your `l`/`r`/`s`/`e` decisions. In GNU diffutils sdiff is literally a driver over diff, but merge mode is sdiff-only functionality.

### Q: Describe the interactive commands available at sdiff's % prompt.

`l` takes the left version, `r` the right, `s` includes the region's common lines, `q` quits (keeping decisions made so far and exiting 2). The `e` family runs `$EDITOR` before installing the result: `el`/`er` edit one side, `eb` edits both together — the standard answer when neither version is correct. There are no wildcards or "apply to all" commands; batch decisions are made by piping an answer script into stdin.

### Q: You scripted a merge with `printf 'l\nr\n' | sdiff -o m.txt a b` and the exit status was 2. What happened?

Status 2 in merge mode usually means the merge was abandoned via `q` (or hit trouble) — the decisions before the quit were written, the rest was dropped. For a two-conflict file the shown sequence is fine, but as a rule: after any scripted `sdiff -o`, check the exit status *and* verify the output (line count, or diff against both parents) before consuming it, because a partial merge file is valid text.

### Q: When would you choose sdiff over diff3 -m for a merge?

When there is no reliable base file, when every difference needs a human judgment call anyway, or when you want per-line control rather than automatic application plus conflict markers. diff3 automates the non-overlapping majority and brackets only collisions; sdiff makes you decide everything but gives complete control over the result. They also compose: diff3 -m first, then sdiff to polish the remaining markers into a decision.

### Q: Why does sdiff output look broken on a narrow terminal, and how do you fix it?

sdiff's default width is 130 print columns regardless of your terminal; anything narrower wraps the columns and destroys the alignment. Fix with `-w` (e.g. `-w $COLUMNS`), expand tabs with `-t` when tab-indented code misaligns, and add `-s` when you only care about differences. The rendering is fixed-width text, so width management is the caller's responsibility.

### Q: Where does sdiff sit in the diffutils family, and what is its modern competition?

It is the family's interaction layer: diff computes, cmp tests bytes, diff3 merges three-way, sdiff shows and merges two-way with a human in the loop. Modern alternatives — `vimdiff`, `meld`, `git mergetool`, `delta` — offer color, word-level highlighting, and mouse support, but require more infrastructure. sdiff remains the POSIX-specified, dependency-free choice for servers and rescue environments.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/diffutils/sdiff.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/diffutils/)
