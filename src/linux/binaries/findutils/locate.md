# locate — instant filename lookup in a prebuilt index

## Overview

`locate` answers "where on this system is a file with this name?" in milliseconds by searching a **prebuilt index** of the filesystem instead of walking directories at query time. On Debian bookworm the `locate` name is provided by the **plocate** package (`plocate` ships `/usr/bin/locate` and `Provides: locate`), which reimplements the interface of the traditional tools on a much faster index. The database lives at `/var/lib/plocate/plocate.db` and is rebuilt by sibling `updatedb` — on Debian by a daily systemd timer, not interactively. GNU findutils upstream still maintains its own `locate`/`updatedb`, but Debian (like most current distributions) ships the plocate implementation because it scales to millions of files.

`locate` is often confused with `find` (authoritative, real-time traversal with rich predicates — see [`find`](../../shell/find.md)), with `which`/`type` (PATH lookup for executables only), and with `grep -r` (content search, entirely different question). The trade is always the same: locate is *fast but stale*; find is *slow but true*.

| Field | Value |
| --- | --- |
| Package | plocate (Debian bookworm) — `Provides: locate` |
| Man section | 1 |
| Path | /usr/bin/locate |
| First appeared | BSD lineage (early 1980s); mlocate mid-2000s; plocate 2020s |
| Standards | None (BSD/mlocate/plocate conventions; no POSIX spec) |

## Synopsis

```
locate [OPTION]... PATTERN...
```

Common one-line forms:

```
locate nginx.conf              # paths containing nginx.conf
locate -i readme               # case-insensitive
locate -c '*.conf'             # count matches only
locate -n 10 -i license        # first 10 matches
locate -0 -b id_rsa | xargs -0 ls -l   # NUL-safe pipeline
locate --regex '\.log$'        # POSIX extended regexp over whole paths
```

Multiple `PATTERN`s are allowed; a result matching *any* pattern is printed (OR semantics). `-A` requires *all* patterns to match instead.

## How It Works

### Query time vs index time

`find` pays the traversal cost on every query. `locate` moves that cost to *index time*: `updatedb` walks the filesystem (see [updatedb](./updatedb.md)) and writes a compact database of every indexed path; `locate` then searches that database — no `readdir` at query time at all.

```
 index time (daily, background)            query time (per search)
┌────────────────────────────┐            ┌─────────────────────────────┐
│ updatedb                   │            │ locate PATTERN              │
│  walk / (respecting prunes)│            │  decompose pattern          │
│  record every visible path │──db──────▶ │  look up trigram postings   │
│  compress into trigram     │            │  intersect candidate lists  │
│  postings + path strings   │            │  verify candidates in db    │
└────────────────────────────┘            │  visibility check per hit   │
 /var/lib/plocate/plocate.db              │  print matches (-0 for xargs)│
                                          └─────────────────────────────┘
```

plocate's specific trick is a **trigram index**: every indexed path is decomposed into overlapping 3-character sequences ("trigrams"), and the database stores, per trigram, the list of paths containing it (posting lists). A query like `systemd-networkd` becomes a small set of trigrams (`sys`, `yst`, `ste`, ...); locate intersects their posting lists to get a tiny candidate set, then confirms each candidate against the actual path strings. The result scales with the *query*, not with the filesystem — where mlocate scanned the whole (compressed) database linearly, plocate's search time stays roughly flat as the file count grows into the tens of millions. The build side uses Linux `io_uring` for parallel directory reads and I/O-scheduling niceness so the nightly rebuild stays background-friendly (see [updatedb](./updatedb.md)).

### Pattern semantics: glob by default, regex on request

The default matcher is a **glob** with an implicit wildcard wrapper: if the pattern contains no glob characters (`*`, `?`, `[`), it is searched as if it were `*PATTERN*`:

```
$ locate nginx.conf
/etc/nginx/nginx.conf
/usr/share/doc/nginx/nginx.conf.gz
...
```

- Matching is against the **whole path** by default (`-w`, `--wholename`, is the explicit form). `locate conf` therefore also matches `/etc/confsomething/...` and any path merely containing "conf" anywhere.
- `-b`, `--basename` matches only the final component: `locate -b nginx.conf` finds files *named* nginx.conf.
- `--regex` treats every pattern as a POSIX **extended** regular expression matched against the whole path (`locate --regex '\.log$'`); GNU/mlocate tradition also has `--regexp` for a single basic-regex pattern. With `--regex`, anchor deliberately (`$`, `/`) — an unanchored regex is the slow, noisy equivalent of the default substring behavior.
- Multiple patterns OR by default; `-A` (`--all`) requires every pattern to match the same entry, which is the portable way to build AND queries.

### Filtering and output options

| Option | Effect |
| --- | --- |
| `-i`, `--ignore-case` | Case-insensitive matching. |
| `-c`, `--count` | Print only the number of matches. |
| `-n N`, `--limit N` | Stop after N results (input-size guard for huge indexes). |
| `-0`, `--null` | Separate results with NUL — pairs with `xargs -0`. |
| `-b`, `--basename` | Match the final path component only. |
| `-w`, `--wholename` | Match the whole path (default, spelled out). |
| `-d DB`, `--database DB` | Search DB instead of the system database (comma-separated list allowed). |
| `-A`, `--all` | Print only entries matching all patterns. |
| `--regex` | Interpret all patterns as POSIX EREs. |

### Where locate sits among the finders

| Tool | Answers | Freshness | Cost per query | Scope |
| --- | --- | --- | --- | --- |
| `locate` | files whose *name/path* matches | snapshot (index time) | ~O(query), milliseconds | everything indexed, prunes applied |
| `find` | files matching arbitrary predicates | live | O(subtree traversal) | whatever you can traverse, now |
| `which` / `type -a` | executables on `$PATH` | live | trivial | `$PATH` only |
| `grep -r` / `rg` | files whose *content* matches | live | O(subtree × bytes) | contents, not names |

The rows are not competitors so much as different predicates; the recurring interview question is which row a given task actually needs.

### Custom databases

`-d DB` selects which database to search — the hook for private indexes. Build one over a subtree with `updatedb -U /srv/projects -o ~/projects.db` (see [updatedb](./updatedb.md)), then query it without touching the system index:

```
$ updatedb -U /srv/projects -o ~/projects.db
$ locate -d ~/projects.db -c '*'
# (count of every path indexed under /srv/projects — query your own tree,
#  not the system db)
```

A user-built db contains only what *you* could read when it was built, so the group-permission + visibility-check machinery is largely moot for it — the visibility model presumes a root-built, whole-system database. Point `-d` at several comma-separated databases to search them in one pass; `-` as a database name reads a prebuilt stream from stdin, which is how some tooling pipes pre-indexed archives through locate.

### The security model

A database containing every path on the system would leak names to any user — historically the point of failure for naive locate implementations (this is why the security-aware `slocate` fork existed before `mlocate`). The modern design, which plocate keeps:

- the database is owned `root:plocate` and readable only by group `plocate`;
- `/usr/bin/locate` runs setgid `plocate` so it can read the index;
- **before printing a result, locate checks that the invoking user could actually access that path** (stat-permission checks against your uid/gids) and silently drops entries you are not allowed to see.

So user A cannot discover `/home/b/secret.txt` from the index, even though it is in the database A's group can read. The cost is a per-result permission check and the inherent caveat that the check is a snapshot of *permissions at query time* on a *snapshot of paths at index time*.

Compare with `find`, which traverses with your own credentials and can only ever see what you can see — always true, but O(filesystem). Locate's security is a *faithful-but-stale* approximation, which is the right trade for an interactive "where is X" tool and the wrong one for security audits.

## Usage Patterns

```bash
# Where is the actual config file behind a service? (the 90% use case)
locate nginx.conf
```

```bash
# Files NAMED something, not paths containing it somewhere
locate -b sshd_config
```

```bash
# Case-insensitive, capped output — safe on huge indexes
locate -n 20 -i certificate
```

```bash
# Count instead of print (how much will this flood me?)
locate -c '*.py'
```

```bash
# NUL-safe handoff to xargs: filenames with spaces/newlines survive
locate -0 -b '*.service' | xargs -0 -r ls -l
```

```bash
# Regex search: all paths ending in .log under /var
locate --regex '^/var/.*\.log$'
```

```bash
# AND query: entries containing both tokens
locate -A networkd .conf
```

```bash
# Search a private index you built yourself (see updatedb -U)
locate -d ~/projects.db main.py
```

```bash
# Sanity-check the index state before trusting results
locate -c '' 2>/dev/null || echo "empty pattern matches everything indexed"
```

```bash
# Find recently-installed package files by name fragment
locate -n 15 sysctl
```

```bash
# Feed a pager when the answer set is large (limit OR page, not both blindly)
locate -i firmware | less
```

```bash
# Check whether an index entry still exists before acting on it
for f in $(locate -n 50 -b '*.conf' | head -50); do [ -e "$f" ] || echo "stale: $f"; done
```

```bash
# Measure index size vs file count before scripting against it
sudo ls -lh /var/lib/plocate/plocate.db
```

```bash
# Confirm which implementation you are actually running (packaging varies)
dpkg -S "$(command -v locate)"; locate --version | head -1
```

```bash
# All .desktop launchers whose name mentions a terminal, case-insensitively
locate -b -i '*terminal*.desktop'
```

```bash
# Clean up empty matches: run updatedb only when the db is missing entirely
[ -s /var/lib/plocate/plocate.db ] || sudo updatedb
```

## Nuances and Gotchas

- **Staleness is the defining gotcha.** Files created after the last `updatedb` run are invisible until the next one; files deleted since then are *ghost results* that fail on use. `locate foo && cat $(locate -n 1 foo)` can crash on a stale path. After bulk installs or big script-generated trees, run `sudo updatedb` (or use `find`, which never lies).
- **Pruned paths are invisible by design.** `/tmp`, `/var/spool`, mounts, and other entries in `PRUNEPATHS`/`PRUNEFS` are not indexed at all — `locate` finding nothing there is correct behavior, not a bug. See [updatedb](./updatedb.md).
- **Unquoted globs expand in your shell first.** `locate *.conf` glob-expands in the current directory before locate ever runs; the invocations you mean are `locate '*.conf'` or `locate \*.conf`. This is the single most common locate bug in the wild.
- **Whole-path matching by default.** `locate conf` matches any path *containing* "conf" — including `/etc/configuration...`. Use `-b` for name-based search; be explicit about intent.
- **Visibility checks can surprise in scripts.** A cron job running as a service user may see *fewer* results than your root shell did — the setgid+visibility model filters per effective user. Root sees everything; unprivileged service accounts see only what they could stat.
- **`-n` before `-c`.** `-c` counts all matches; `-n 10 -c` is not "count up to ten". Know which one your question needs.
- **Case sensitivity is opt-out, not opt-in.** Default is case-**sensitive**; interactive humans usually want `-i`, scripted lookups often do not care — pick deliberately.
- **Empty-ish patterns match everything.** `locate ''` (or a bare `*`) enumerates the whole visible index — millions of lines on a desktop system. Combine with `-c` or a pipe to `head`/`less` to stay safe.
- **plocate needs a modern kernel for full speed.** Its fast paths lean on `io_uring` (Linux 5.1+); on ancient kernels it degrades gracefully but is less impressive. Trigram posting lists also make the index *compact*, but the db format is plocate-specific — mlocate-era dbs are not interchangeable.
- **No content, ever.** locate matches *names*. Asking it for a string inside files is a `grep`/`rg` question — a confusion interviewers deliberately seed.
- **The database is not a security boundary by itself.** Anyone in the `plocate` group can read the raw index (that is how setgid locate works); the per-user filtering happens in the tool at print time. Do not treat group membership as authorization to *know* all paths — treat it as an implementation detail of the visibility check.
- **Prune edits require a rebuild to matter.** Changing `/etc/updatedb.conf` does nothing to the existing db until the next `updatedb` run; entries inside newly pruned paths remain findable until then.
- **Portability.** Flag sets differ across implementations: BSD locate, GNU findutils locate, mlocate, plocate all accept a similar core (`-i`, `-c`, `-n`, `-b`, `-d`, `-0`, `--regex`) but extras like `-A` are plocate additions. On minimal systems without plocate, `find / -name` is the fallback.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | At least one match was found (and printed, unless `-c` counted zero-visible). |
| 1 | No matches found. |
| 2 | Trouble: unreadable database, I/O error, bad usage. |

## Related Commands

- [`updatedb`](./updatedb.md) — builds and refreshes the database locate searches.
- [`find`](../../shell/find.md) — real-time traversal with rich predicates; the authoritative alternative.
- [`xargs`](../../shell/xargs.md) — the `-0` pipeline partner for acting on located paths.
- [`grep`](../../shell/grep.md) — search file *contents*; the tool locate is constantly mistaken for.
- [Collection overview](./overview.md) — the findutils story and the walk-vs-index trade.
- [Part overview](../overview.md) — all userland binary collections.

## Interview Questions

### Q: Why is locate fast, and what does it trade away for that speed?

It searches a prebuilt index rather than walking directories: `updatedb` records every visible path once (daily on Debian), and plocate adds a trigram index so a query touches small posting lists instead of scanning millions of paths. The trade is freshness — results reflect index time, not query time, so new files are missing and deleted files are ghosts until the next `updatedb`. It also matches names only, with no predicates beyond name/regex.

### Q: How does locate prevent users from learning filenames they should not see, given the database contains every path?

The database is readable only by a dedicated group (plocate's design: `root:plocate`, mode with group read), the `locate` binary is setgid to that group, and before printing any result the tool verifies the invoking user could actually access that path (permission check) — dropping entries you could not see. So the index is shared, but the *answers* are per-user. `find` needs no such machinery because it traverses with your own credentials and never sees what you cannot see.

### Q: A user complains that `locate report.pdf` shows a file, but `cat` on it fails. What happened?

The index is stale: the file was deleted after the last `updatedb` run, so locate returned a ghost entry. Diagnose with `ls`/`[ -e ]` on the path, refresh with `sudo updatedb` for an immediate fix, and reach for `find` when up-to-the-second accuracy matters. The same staleness hides *new* files until the next index rebuild.

### Q: Explain the default pattern semantics and the two classic matching mistakes.

Default is whole-path matching of a glob pattern, with implicit `*` wrapping when no glob characters are present — so `locate conf` matches every path containing "conf" anywhere. Mistake one: forgetting `-b` when you mean "files named X". Mistake two: leaving the pattern unquoted so the shell expands `*.conf` against the current directory before locate runs. The regex escape hatch is `--regex` (POSIX ERE) with explicit anchors.

### Q: Why did Debian move the locate/updatedb implementation from GNU findutils heritage to plocate?

Scale and efficiency. GNU's locate and mlocate scan/hold a linear (compressed) list of paths, which gets slower and I/O-heavier as filesystems grow; mlocate optimized rebuilds with timestamped directories, but queries still scale with database size. plocate rearchitected both sides — trigram posting lists for O(query) lookups, io_uring-based low-priority rebuilds, a compact index — while keeping the mlocate interface and security model, so it could drop in as `Provides: locate` without user-visible changes. GNU findutils continues upstream for find/xargs, which Debian still ships from that source package.

### Q: When must you use find even though locate exists?

Whenever the answer must reflect the filesystem *now* (freshly created or deleted files), when predicates beyond the name matter (size, mtime, permissions, type, `-exec`), when operating inside pruned trees (`/tmp`, mounts), or in security contexts where the index's snapshot semantics are unacceptable. locate is a convenience layer over exactly one predicate — the name — evaluated against a snapshot; find is the ground truth.

### Q: What is a trigram index, in one paragraph, and why does it make queries fast?

A trigram is a 3-character substring; plocate decomposes every indexed path into its overlapping trigrams and stores, per trigram, the list of paths containing it. A query is likewise decomposed — `sshd_config` yields `ssh`, `shd`, `hd_`, ... — and the tool intersects those posting lists, which narrows millions of paths down to a handful of candidates in a few set operations, then verifies each candidate against the stored paths. Because work scales with the query's trigrams rather than with the number of indexed files, lookup time stays near-flat as filesystems grow, unlike mlocate's linear scan of a compressed path list.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/plocate/locate.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/plocate/)
