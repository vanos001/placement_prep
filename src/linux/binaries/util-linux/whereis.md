# whereis — locate binary, source, and manual files for commands

## Overview

`whereis` searches a fixed set of standard directories for the **binary, source, and manual-page** files associated with a command name, printing whatever it finds on one line. Unlike `find`, it walks no filesystem tree at runtime — it probes a hardcoded (but overridable) list of well-known locations, which makes it effectively instantaneous. It ships in the Debian `util-linux` package at `/usr/bin/whereis`.

You reach for it when you want "where does this command's program live, and where are its docs" in one shot — often to learn which package provides a tool or to check whether a man page is actually installed. It is often confused with `which` (searches `$PATH` only, and only for executables; also resolves shell aliases/builtins differently), `type` (the bash builtin that knows about aliases, functions and builtins), and `locate`/`find` (arbitrary filename search over an index/tree — slower, broader, not tied to command semantics). A modern complement is `dpkg -S <file>` (which *package* owns the file).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/whereis |
| First appeared | 3BSD (circa 1980); rewritten for util-linux in the early 2010s |
| Standards | none; BSD lineage |

## Synopsis

```
whereis [options] [-BMS <dir>... -f] <name>...
```

Main one-line forms:

```
whereis ls                  # binary + man (and source) paths for ls
whereis -b gcc              # binaries only
whereis -m printf           # manuals only
whereis -B /opt/bin -f mytool   # search binaries under /opt/bin
whereis -u -m *             # files in cwd lacking (unique) documentation
```

## How It Works

### Fixed-path probing, not a tree walk

`whereis` keeps internal lists of standard binary, manual, and source directories — on this system `-l` shows the effective set:

```bash
$ whereis -l
bin: /usr/bin
bin: /usr/sbin
bin: /usr/lib/x86_64-linux-gnu
bin: /usr/lib
bin: /etc
bin: /usr/local/bin
bin: /usr/local/sbin
...
```

For each *name* it constructs candidate paths by joining each directory with the name (and known suffixes such as `.gz`, extensions for man sections, and compression variants), then `stat`s them. Nothing is indexed and nothing is scanned recursively by default — hence the speed and, equally, the blind spots (see gotchas). Grounded example:

```bash
$ whereis ls
ls: /usr/bin/ls /usr/share/man/man1/ls.1.gz
$ whereis passwd
passwd: /usr/bin/passwd /etc/passwd /usr/share/man/man1/passwd.1.gz
```

Note how `passwd` finds `/etc/passwd` as a "binary-like" file — whereis matches *filenames* in its search dirs, not executables specifically.

### Restricting and redirecting each class

The `-b/-m/-s` triple selects which classes to report; the `-B/-M/-S` triple *replaces* the search path for that class. Because the path arguments are whitespace-separated lists, a literal `-f` is required to end them:

```
whereis -B /opt/tools /usr/local/bin -f mytool
        └──── binaries path ────┘┘   └ name
```

`-g` treats each name as a glob pattern (pathnames matching), which turns whereis into a cheap filename finder within the standard dirs; `-u` selects *unusual* entries.

### What `-m` actually searches

The manual class covers more than one directory convention:

```
/usr/share/man/man1 ... manN    classic sectioned pages (+ .gz/.bz2 variants)
/usr/share/man/<locale>/manN    localized pages
/usr/share/info                 GNU info manuals
/usr/share/man/whatis-style db  via the man database, not per-file probing
```

That is why `whereis -m ls` finds the *compressed* page (`ls.1.gz`): the probe knows the compression suffixes. It also explains why documentation in HTML or Markdown (increasingly common in modern packages) is invisible — `-m` predates and ignores anything outside the classic man/info trees.

### The probe algorithm, precisely

For name `foo`, whereis builds candidate paths as `<dir>/foo` plus a table of known suffixes (`foo.gz`, `foo.1.gz`, `foo.bz2`, ...), then `stat`s each candidate in the requested classes. Consequences worth stating in interviews:

- No file is read or executed — pure path existence, so results can be stale the moment a file moves (same as any non-atomic probe).
- Names are matched exactly (unless `-g` globs); `whereis python` does not find `python3`.
- The default dir lists include multiarch and libexec paths on Debian (`/usr/lib/x86_64-linux-gnu`), which is why library-shaped things sometimes appear in `-b` output.

### The `-u` unusual-entries trick

A file is "unusual" if it does not have exactly one entry of each requested type. The classic documentation-audit idiom:

```bash
$ whereis -m -u *
# files in the current directory that have no documentation
# (or more than one) — instant "which of my binaries lack man pages"
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-b` | Search only for binaries. |
| `-m` | Search only for manuals (and info documentation). |
| `-s` | Search only for sources. |
| `-B <dirs>` | Replace the binary search path (whitespace-separated list). |
| `-M <dirs>` | Replace the manual search path. |
| `-S <dirs>` | Replace the source search path. |
| `-f` | Terminate a `-B/-M/-S` directory list (required before names). |
| `-u` | Show unusual entries (missing or extra entries of requested types). |
| `-g` | Interpret names as glob patterns. |
| `-l` | Print the effective search paths and exit — the ground truth for "what does whereis look at". |

## Usage Patterns

```bash
# One-line answer: where is the program and its manual?
whereis tar
```

```bash
# Only executables, e.g. to spot PATH shadowing candidates
whereis -b python3
```

```bash
# Check whether a man page is installed for a tool
whereis -m systemd-run
```

```bash
# Search for a tool you installed outside the standard tree
whereis -B /opt/myapp/bin -f deployer
```

```bash
# Audit current directory for undocumented binaries
whereis -b -m -u .*
```

```bash
# Glob search inside standard locations (cheap 'locate')
whereis -g '*dev*'
```

```bash
# Custom man-tree search (e.g. after building docs locally)
whereis -M /usr/local/share/man -f mycmd
```

```bash
# Compare with which/type semantics
whereis -b ls; which ls; type ls
```

```bash
# Find where passwd-related files live beyond the binary
whereis passwd
```

```bash
# List every directory whereis would search
whereis -l
```

```bash
# Check source availability for a tool (rare on binary distros, common on Gentoo-like setups)
whereis -s bash
```

```bash
# Compare man-page coverage of the whole /usr/local toolbelt
whereis -m -u /usr/local/bin/*
```

```bash
# Find all documentation for the multicall busybox-style names
tool=grep; whereis -m "$tool"; man -w "$tool"
```

```bash
# Quick pre-flight in installers: is the binary where the postinst expects it?
[ -n "$(whereis -b dockerd | cut -d: -f2)" ] || echo "dockerd not found in standard dirs"
```

## Nuances and Gotchas

- **It only knows standard places.** A binary under `$HOME/bin`, `/opt/vendor/...`, or a conda/npm prefix is invisible unless you override the path with `-B/-M/-S`. Empty output means "not in the standard dirs", not "not installed" — the #1 misuse.
- **`which` vs `whereis` vs `type`.** `which` follows `$PATH` (user reality), `type` knows shell aliases/functions/builtins, `whereis` ignores both and probes fixed dirs including source and man paths. Answering "why does whereis find it but which doesn't" almost always means a PATH difference.
- **Filenames, not semantics.** `whereis passwd` returning `/etc/passwd` shows it matches *any* file named `passwd` in binary-class dirs (`/etc` is in the default bin list). Don't assume every hit is an executable.
- **The `-f` terminator is mandatory** after `-B/-M/-S` lists; omitting it makes whereis treat your command name as another directory.
- **`-u` depends on the requested classes.** `-m -u *` reports names with zero or multiple man entries; with `-b` added, "unusual" means something different. Read the man page sentence carefully — interviewers quote it.
- **Compressed and multi-section man pages.** whereis handles `.gz`-compressed pages and knows man section dirs, but alternative doc systems (HTML docs, info files beyond its list) are only partially covered by `-m`.
- **No recursion depth control.** The rewrite scans its standard dirs (with some depth) but is still bounded; on deep custom `-B` trees it is not a `find` replacement.
- **Exit status is not a match indicator.** whereis exits 0 regardless of whether anything was found; parse the output (or its absence) instead.
- **Multi-call and suffixed names.** `rename.ul`, `busybox`, versioned names (`python3.11`) need exact-name queries; the probe does no fuzzy matching, and package-suffixed binaries (Debian's `.ul` etc.) break naive loops.
- **man -w is the authoritative man lookup.** For documentation location, `man -w <page>` consults the actual man-db configuration (MANPATH, sections) rather than whereis's fixed lists; whereis is the fast approximation, not the reference.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Ran successfully — **whether or not any file matched**; empty output is the "nothing found" signal. |
| nonzero | Only on real errors (bad usage, inaccessible critical resources). |

## Related Commands

- [`../../shell/find.md`](../../shell/find.md) — the general recursive filename search whereis deliberately is not.
- [`../../reference/man-pages.md`](../../reference/man-pages.md) — where man pages live and how they are organized (the `-m` half of whereis).
- [`../../reference/commands.md`](../../reference/commands.md) — command lookup context (PATH, aliases, builtins).
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What is the actual difference between `whereis`, `which`, and `type` for resolving a command?

`which` searches the directories in `$PATH` for executables — what the shell would run (unless an alias/function shadows it). `type` is the shell builtin that reveals aliases, functions, builtins, and then PATH files. `whereis` ignores PATH entirely and probes fixed system directories for binaries, man pages, and sources — so it answers "where does this command's *installation* live", not "what will run".

### Q: `whereis mytool` prints nothing but the tool runs fine. What are your hypotheses?

The binary lives outside whereis's standard directory list (user-local bin, `/opt`, a version manager's prefix, a container overlay); or only the man page is missing while you expected `-m` output. Verify with `command -v mytool`/`type mytool` for the truth, and extend the search with `whereis -B <dir> -f mytool`. Empty whereis output never means "not installed".

### Q: How does the `-u` option behave, and give a concrete use.

With the requested classes, `-u` reports *unusual* names: entries lacking one of the requested types or having more than one. The documented idiom `whereis -m -u *` lists files in the current directory that have no documentation (or several man pages) — an instant doc-coverage audit for a directory of scripts or binaries.

### Q: Why is whereis so much faster than `find / -name ls` for the same question?

whereis does no general traversal: it joins each *name* against a fixed list of standard directories (plus known suffixes) and stats the candidates — O(directories) stat calls. `find` walks arbitrary trees with full predicate evaluation. The price is coverage: anything outside the fixed list is invisible, which is exactly the trade-off the tool accepts.

### Q: What does `whereis -l` give you and why is it the first thing to check when scripting against whereis?

It prints the effective binary/manual/source search paths. Because distributions and builds vary (multiarch dirs like `/usr/lib/x86_64-linux-gnu`, local prefixes), assuming whereis looks at the same dirs you do leads to false negatives; `-l` gives the ground truth to document or assert in scripts.

### Q: Why did `whereis passwd` return `/etc/passwd` along with the binary?

whereis matches file *names* within its search-class directories; `/etc` is part of its default binary-path set, so the data file `passwd` matches too. The lesson: whereis hits are name matches, not executable checks — pipe through `test -x` or use `-b`/`which` when only real programs are wanted.

### Q: You must inventory every installed command that lacks a man page. Sketch the approach and its blind spots.

Approach: walk the PATH directories (`IFS=:; for d in $PATH`) and run `whereis -m -u "$d"/*` (or filter `whereis -m` output for empties) to list binaries without documentation. Blind spots: whereis only probes its fixed man dirs, so localized/sectioned pages outside the defaults false-positive; setuid-suffixed or multi-call names need exact queries; and commands that are shell builtins or aliases have no file at all. For a distribution-grade answer, `man -k`/`apropos` over the man-db index is the more authoritative cross-check — whereis gives you the cheap 90% pass.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/whereis.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
