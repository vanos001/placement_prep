# rename — bulk file renames by literal string substitution

## Overview

`rename` renames many files at once by replacing a literal string in each filename: `rename .htm .html *.htm` turns every `foo.htm` into `foo.html`. It ships in the `util-linux` package — but on Debian the binary is installed as **`/usr/bin/rename.ul`** with the man page **`rename.ul(1)`**, because the name `/usr/bin/rename` is claimed by the *Perl* implementation (`perl`'s `prename`, and the separate `rename` package) via `update-alternatives`. Two completely different tools share one command name; knowing which one you invoked is the first interview question about it.

The util-linux `rename` is the minimal, predictable one: no regex, no expressions, first-occurrence substitution, plain `rename(2)` semantics. The Perl `rename` takes a Perl expression per file (`rename 's/\.htm$/\.html/' *.htm`) and can do anything Perl can. POSIX defines neither; portable scripts either call `rename.ul` explicitly or use `mv` loops.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 (installed as `rename.ul(1)`) |
| Path | /usr/bin/rename.ul (as `/usr/bin/rename` only where no Perl rename wins the alternatives slot) |
| First appeared | util-linux lineage since the 1990s; Debian `.ul` split since 2005-era |
| Standards | Not POSIX; conflicts with Perl `rename` on Debian |

## Synopsis

```
rename.ul [options] <expression> <replacement> <file>...
```

Main one-line forms:

```
rename.ul .htm .html *.htm          # first ".htm" in each name becomes ".html"
rename.ul foo foo0 foo?             # foo1 -> foo01? no: foo1 -> foo01 only if foo0 not in name
rename.ul ' ' _ *.txt               # first space in each name becomes underscore
rename.ul -v '' .bak- *             # prepend: replace nothing at position 0
```

## How It Works

### The substitution rule

For each file operand, `rename` computes the new name by replacing the **first occurrence** of `expression` with `replacement`. The match is a plain string search — no regex, no globs (globs belong to the *shell* that produced the file list):

```
name:      a.foo.bar     foo.txt      config.old.old
expr: foo  -> a.foo0.bar  foo0.txt     (config.old.old unchanged: no "foo")
expr: .old -> a.foo.bar   .old.txt?    -> config0.old (first occurrence only)
```

The tool never interprets the expression: there are no anchors (`^`/`$` are ordinary characters), no character classes, no case folding. Every pattern-like behavior you want must come from either the shell (which files are even passed in) or a different tool (Perl rename's `s///`).

The new name is produced by string surgery on the name *as you passed it*, then a `rename(2)` call moves the file. Consequences verified locally:

- **Silent overwrite.** `rename.ul one two one.txt` with an existing `two.txt` destroys it — `rename(2)` replaces the target without asking. There is no `-f` on bookworm because there is nothing to force.
- **First occurrence only.** `config.old.old` becomes `config0.old`, not `config0.old0`.

Bookworm's `rename.ul` has exactly two behavioral options (`-v`, `-s`). Recent upstream util-linux (2.41-era, verified locally) adds `-n/--no-act`, `-a/--all` (replace every occurrence), `-l/--last` (last occurrence), `-o/--no-overwrite`, `-i/--interactive` — do not use them in scripts that must run on stable distributions.

### rename(2) beneath the string surgery

Each operand results in one `rename(2)` call: old path → new path computed in memory first. The syscall's guarantees are what make the tool safe-ish: the move is **atomic within the filesystem** — an observer never sees a half-renamed file — and if the target exists and is a file, it is silently replaced in the same operation (that is the overwrite "feature", not a bug). Because the new name is derived from the old one by substitution, source and target are normally in the same directory: `EXDEV` (cross-filesystem) cannot happen, and the tool needs no copy fallback. The 2.41-era `/`-containing expression mode is the only way to move between directories, and even then the man page notes creating directories and crossing filesystems are unsupported.

Errnos surface directly: `ENOENT` ("not accessible: No such file or directory" per operand), `EACCES`, `EISDIR`/`ENOTDIR` when the substitution changes the file/dir nature of a path, `EINVAL` for renaming `.`/`..`. The batch continues after a failure — one missing file does not stop the rest.

### Edge cases the man page calls out

- **Empty expression** → replacement is prepended to the name (verified: `rename.ul '' PRE f` → `PREf`). With `--all` the replacement is inserted between *every* two characters plus both ends — an accidental `rename.ul -a '' X *` produces combinatorial garbage.
- **A `/` in expression or replacement** switches from final-component matching to full-path rewriting — the only way the tool moves files between directories (2.41-era; verified: with a plain expression, a `d1/f` operand matches only `f`, so an expression naming the directory does nothing).
- **`--no-act` is the 2.41-era dry run**; bookworm has none, so the shell-loop preview pattern below is the portable equivalent.
- **Exit codes widened on 2.41-era builds** (verified locally): `0` all renamed, `1` hard errors (missing/inaccessible), and `4` when the expression matched *nothing* — a silent no-op distinguishable from a real failure. Bookworm documents only 0/1.

### The Perl shadow on Debian

```
$ command -v rename
/usr/bin/rename
$ readlink -f "$(command -v rename)"   # which implementation won?
/usr/bin/prename                        # the Perl one
$ rename.ul --version                  # the util-linux one, always this path
rename.ul from util-linux 2.38.1
```

Scripts that need the util-linux semantics must call `rename.ul` by its real name; scripts that need Perl semantics should call `prename` or `file-rename` explicitly. Anything that calls bare `rename` depends on which packages happen to be installed and on the alternatives priority — a portability trap on every Debian-based system.

### How the Debian split is wired

The binary is `/usr/bin/rename.ul` (package `util-linux`, confirmable with `dpkg -S /usr/bin/rename.ul`). `/usr/bin/rename` itself is a *slave symlink* managed by `update-alternatives` when a competing implementation is installed:

```bash
$ ls -l /usr/bin/rename.ul                 # the util-linux binary, always here
$ command -v rename || echo "no rename at all"   # slim images: nothing else
$ update-alternatives --list rename        # lists contenders (perl prename, ...)
```

A minimal container (verified locally) has *only* `rename.ul` — no `rename` at all — while a desktop install with the `rename` package installed resolves bare `rename` to the Perl tool. That means "works in CI, fails on the workstation" or the reverse is expected behavior for unpinned calls, and the only robust script pins the name. On RHEL-family systems `rename` is the util-linux tool natively (no split), and BusyBox provides the same two-string syntax — three environments, three answers to "what is `rename`".

### What `-s, --symlink` really does

Without `-s`, a symlink operand is renamed itself: the link's *name* changes, its target string is untouched. With `-s`, the tool resolves each link and renames the *target*, leaving the link name and even the link's directory alone — the man page phrases it "do not rename a symlink but change where it points". Two consequences worth internalizing: the operation can reach a file you never passed (the target may live anywhere the link points, including another directory), and on 2.41-era builds `--symlink` plus `--no-overwrite` protects against clobbering an existing target rather than the link. Debug confusion by running `ls -l` on the link and its target before and after — the two names move independently.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-v`, `--verbose` | Print each rename performed |
| `-s`, `--symlink` | Act on the *target* of symlinks instead of renaming the link itself |
| `-h`, `--help` / `-V`, `--version` | Usage / version |

(Recent upstream adds `-n/--no-act`, `-a/--all`, `-l/--last`, `-o/--no-overwrite`, `-i/--interactive`; see the warning above.)

## Usage Patterns

```bash
# Fix an extension across a directory
rename.ul .jpeg .jpg *.jpeg
```

```bash
# Blank out spaces in downloaded filenames (first space only)
rename.ul ' ' _ *' '* 
```

```bash
# Prefix all logs with archive- (replace the empty string at the start)
rename.ul -v '' archive- 2024-*.log
```

```bash
# Renumber a date typo: 2023 -> 2024 in filenames
rename.ul 2023 2024 *.txt
```

```bash
# Update the symlink targets, not the links themselves
rename.ul -s .sh .bak *.sh
```

```bash
# See exactly what happened (bookworm's only safety net)
rename.ul -v old new *
```

```bash
# Dry-run equivalent that works on ANY version: list the planned moves first
for f in *.htm; do echo "mv $f ${f/.htm/.html}"; done
```

```bash
# Same job with explicit control, no rename at all (POSIX-safe)
for f in *.htm; do [ -e "${f%.htm}.html" ] || mv -n -- "$f" "${f%.htm}.html"; done
```

```bash
# Perl rename for jobs util-linux rename cannot express (different tool!)
prename 's/(\d{1,2})/sprintf("%02d",$1)/e' *.mp3
```

```bash
# 2.41-era dry run before committing (bookworm: use the shell-loop preview)
rename.ul -n -v .log .log.bak *.log
```

```bash
# Overwrite protection where available; on bookworm, pre-check with the loop
rename.ul -o .sh .sh2 *.sh 2>/dev/null || \
  for f in *.sh; do [ -e "${f%.sh}.sh2" ] || mv -- "$f" "${f%.sh}.sh2"; done
```

```bash
# Driven recursively by find (rename.ul only sees what you pass it)
find . -depth -name '*.JPEG' -exec rename.ul .JPEG .jpg {} +
```

```bash
# Directories rename like files (rename(2) works on dirs; children follow)
rename.ul 2023 2024 2023_reports/
```

```bash
# Audit trail: -v is your only bookworm-era record of what moved
rename.ul -v draft final chapter*.md 2>&1 | tee rename.log
```

```bash
# Which implementation is bare `rename` here? (run before trusting any recipe)
command -v rename && readlink -f "$(command -v rename)" || echo "rename absent"
```

```bash
# Case conversion rename.ul cannot express — parameter expansion loop instead
for f in *.JPG; do mv -n -- "$f" "${f%.JPG}.jpg"; done
```

## Nuances and Gotchas

- **Which `rename` did you run?** On Debian, bare `rename` may be the Perl tool. Its syntax (`rename 's/x/y/' files`) makes the util-linux call `rename old new files` a syntax error — and vice versa. Scripts must pin the implementation (`rename.ul`, `prename`, or `file-rename`).
- **Literal, first-occurrence substitution.** No regex anchors, no case folding, no `g` flag. `rename.ul a b apple banana` gives `bpple` and `bbnana`; `rename.ul ab c xabab` gives `xcab`, not `xc`.
- **Silent overwrites on bookworm.** No `-o` exists there; a colliding target is destroyed. The shell-level pre-check loop above (or the newer `-o` where available) is the guard.
- **The shell builds the file list.** An unmatched glob passes the literal pattern (`*.htm`) to rename, which then fails per-operand — `set -f`/`nullglob` hygiene in scripts; and files are not found recursively (pair `find -exec` for trees).
- **Order of operations.** `rename.ul 1 2 1.txt 2.txt` renames `1.txt→2.txt` (destroying the original `2.txt` *before* it would be renamed to `3.txt` in the same pass). Multi-step renames need temp names or `mv` loops.
- **`-s` follows link targets.** Renaming through symlinks is rarely what you want; double-check with `-v` what actually moved.
- **BusyBox `rename` mimics the two-string model** but is even more reduced; Alpine/BusyBox scripts can use the same syntax minus `-v` refinements. BSDs ship the Perl-style one as `rename` in some ports — another reason to prefer explicit `mv` loops in portable code.
- **The man page's own WARNING is the summary of this file.** "The renaming has no safeguards by default" — no dry run, no overwrite check, no interactive prompt on bookworm; the 2.41-era `-n/-o/-i` trio exists precisely because upstream acknowledged it. Treat every bookworm invocation as irreversible and preview with the loop.
- **No-match is not an error on 2.41-era builds.** A glob that matches nothing (or names that lack the expression) exits 4 with no output on recent util-linux, while bookworm-style builds report 1 only on real failures. Scripts branching on `$?` should decide explicitly whether "nothing matched" is a failure for them — and test on the target distro, not the dev laptop.
- **Substitution operates on the final path component only** (unless a `/` enters the expression/replacement on 2.41-era builds). An expression matching the directory part of a passed path silently does nothing — verified locally with `rename.ul d1 d2 d1/f.txt` (no-op) versus `rename.ul f g d1/f.txt` (renames in place).
- **`rename(2)` atomicity is per-file, not per-batch.** Each operand commits independently; a failure in file 7 leaves files 1–6 renamed. There is no transaction and no rollback — order the batch or pre-check targets if partial application matters.
- **Names are bytes, not characters.** Substitution is a byte-level search, so it works on invalid-UTF-8 filenames where Perl/regex tools choke — but it also means a multibyte character split across the expression boundary behaves byte-wise. Case conversion (`.JPG` → `.jpg` for all cases) is impossible to express; that is a loop or Perl-rename job.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Every file renamed successfully |
| 1 | At least one rename failed (missing file, permission, target exists and could not be replaced) — already-completed renames are not rolled back |

On 2.41-era builds a third value exists (verified locally): `4` — the expression matched nothing, so *no* rename was attempted; `1` is reserved for real per-file failures. Scripts written against bookworm's 0/1 table should treat any nonzero as "inspect output" rather than assuming a specific count of completed operations.

## Related Commands

- [`mv`](https://manpages.debian.org/bookworm/coreutils/mv.1.en.html) — single-file rename primitive; the loop construct above is the portable bulk rename.
- [`find`](../../shell/find.md) — `find -exec` drives renames recursively with full name control.
- [`bash`](../../shell/bash.md) — parameter expansion (`${f/.htm/.html}`) does the same substitution without spawning processes.
- [`overview`](./overview.md) — hub page of the util-linux collection.
- [`namei`](./namei.md) — trace which component of a moved path resolves where, when `-s` retargets links.

## Interview Questions

### Q: Why is util-linux's rename installed as rename.ul on Debian, and how do you check which rename you are using?

Because Debian's `/usr/bin/rename` slot belongs to the Perl implementation — perl ships `prename` and the `rename` package provides Larry Wall's script, with `update-alternatives` wiring whichever wins. util-linux therefore installs its binary as `rename.ul` with man page `rename.ul(1)`. Check with `command -v rename` plus `readlink -f`, or just call `rename.ul`/`prename` explicitly. The two have incompatible syntaxes, so un-pinned scripts break depending on which packages are installed.

### Q: Predict the result of `rename.ul old new x.oldold y.old` and explain the semantics.

`x.oldold` → `x.newold` (first occurrence only; the second `old` stays), `y.old` → `y.new`, and any file whose name contains no `old` is untouched. The rule: plain string search, first occurrence, no regex. If `y.new` already existed, it is silently overwritten by the `rename(2)` call — bookworm's rename.ul has no overwrite protection flag. Interviewers use this to check you read the man page instead of assuming sed-like behavior.

### Q: A teammate ran `rename.ul 1 2 1.txt 2.txt` and lost data. What happened and what is the safe pattern?

The pass renamed `1.txt` to `2.txt`, replacing the original `2.txt` before the tool ever reached it — sequential renames with collision-prone targets. Safe patterns: rename through temporary names in a first pass, use the shell loop with an existence check (`[ -e target ] || mv -n -- ...`), or a tool with `-n` dry-run plus `-o` no-overwrite where available. General lesson: bulk rename is a *ordering* problem, not just a substitution problem.

### Q: When is util-linux rename preferable to Perl rename or a bash loop?

When you want minimal, uniform, guessable semantics: literal first-occurrence substitution, no language runtime, deterministic failure, and availability in util-linux on every distro (as rename.ul on Debian). Perl rename wins for regex/programmatic renames; bash loops win for portability and per-file logic (checks, dry-runs, ordering). The senior answer names all three and states the collision/overwrite caveat rather than treating any one as safe by default.

### Q: Explain the safety properties of the underlying rename(2) call: what is atomic, what is not, and where EXDEV could ever come in?

A single rename(2) is atomic within one filesystem: the target name switches from old to new with no intermediate state, and an existing target file is replaced in that same operation — there is no window where `two.txt` is half of `1.txt` and half of the old file. What is *not* atomic is the batch: each operand is an independent syscall, so a mid-run failure leaves partial results. EXDEV cannot arise in the normal mode because the substitution keeps the new name in the same directory as the old; only the 2.41-era slash-expression mode can even name a different directory, and even that refuses cross-filesystem moves rather than copying.

### Q: Design a bulk rename that must not lose data even if interrupted halfway. Which tool do you pick and why?

A two-phase `mv`-based loop: first pass renames everything to unique temporary names (`f` → `.tmp-f`), second pass renames temporaries to final targets with an existence check (`[ -e t ] || mv -n`). util-linux rename.ul alone cannot express phase ordering or collision checks (one pass, first-occurrence substitution, silent overwrite on bookworm), and Perl rename's power makes it harder to audit. If the environment has 2.41-era flags, `rename.ul -n` previews and `-o` prevents clobbering, but ordering hazards like `rename.ul 1 2 1.txt 2.txt` still require the temp-name phase — the data-safety property lives in the *sequence*, not the tool.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/rename.ul.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
