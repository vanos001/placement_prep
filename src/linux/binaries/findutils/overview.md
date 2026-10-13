# findutils — finding files: walk it, index it, delegate it

## Two strategies, four tools

Every "where is that file?" question on Linux resolves to one of two strategies: **walk** the filesystem live and test each candidate, or **query a prebuilt index** and accept its snapshot semantics. GNU findutils is organized exactly around that split:

```
┌─────────────────────────────────────────────────────────────────┐
│  findutils — the file-finding toolbox                           │
│                                                                 │
│   STRATEGY A: walk the tree now              STRATEGY B: query  │
│  ┌───────────────────────────────┐        the index            │
│  │ find   traverse + predicates  │      ┌─────────────────────┐ │
│  │        + actions (-exec ...)  │      │ locate  name lookup │ │
│  │   └─ feeds ─▶ xargs           │      │ (db built by)       │ │
│  │          batch-act on paths   │      │ updatedb  nightly   │ │
│  └───────────────────────────────┘      └─────────────────────┘ │
│                                                                 │
│   Debian bookworm packaging: find + xargs ship from the GNU     │
│   findutils source package; locate/updatedb ship from plocate.  │
└─────────────────────────────────────────────────────────────────┘
```

`find` and `xargs` already have deep-dive pages in the shell collection — [`find`](../../shell/find.md) and [`xargs`](../../shell/xargs.md) — and this collection does not duplicate them. The pages here cover the *index* side: [`locate`](./locate.md) and [`updatedb`](./updatedb.md), the pair that trades freshness for milliseconds.

## The division of labor

| Tool | Strategy | Answers | Latency | Freshness | Page |
| --- | --- | --- | --- | --- | --- |
| `find` | walk | files matching *any* predicate (name, size, time, perms, type) + run actions | O(subtree) | live truth | [shell/find](../../shell/find.md) |
| `xargs` | delegate | run a command efficiently once per *batch* of arguments | O(batches) | as fresh as its input | [shell/xargs](../../shell/xargs.md) |
| `locate` | index | files whose *name/path* matches | milliseconds | as of last `updatedb` | [locate](./locate.md) |
| `updatedb` | index build | — (writes the database) | O(filesystem), nightly | n/a | [updatedb](./updatedb.md) |

The canonical pairings:

- **find + xargs** — the automation workhorse: `find . -name '*.log' -mtime +30 -print0 | xargs -0 rm`. `-print0`/`-0` makes the pipeline safe against spaces and newlines in names.
- **locate (alone)** — the interactive lookup: "where did the package put `nginx.conf`?" Answer in milliseconds, no traversal.
- **find instead of locate** — whenever the moment of truth is *now*: files created seconds ago, deleted files, predicates beyond the name, security-sensitive audits.

## Why locate/updatedb moved to plocate packaging

The history is a case study in how userland evolves without changing its interface:

1. **BSD locate** (early 1980s) introduced the concept: walk the filesystem periodically, store every path in a compact database, search it instantly.
2. **GNU findutils** adopted its own `locate`/`updatedb`, which for decades shipped as part of the same source package as `find` and `xargs`.
3. **slocate / mlocate** (mid-2000s) fixed the security hole — a shared database leaking every filename to every user — with group-readable databases plus per-result visibility checks, and mlocate added timestamped incremental rebuilds.
4. **plocate** (2020s) rearchitected both sides for modern scale: a **trigram index** (posting lists per 3-character sequence) makes query cost scale with the *query* instead of the file count, `io_uring`-based parallel I/O makes the rebuild background-friendly, and the index is remarkably compact — while keeping the mlocate-compatible interface and security model.

Debian bookworm ships `plocate` as the provider of the `locate` command (`Provides: locate`), replacing the findutils-provided implementation; the GNU source package still builds `find` and `xargs`, which is why this collection's locate/updatedb pages document plocate's man pages. The user-visible contract survived four implementations — a rare and instructive interface-stability win.

On any given machine, the split is one command away:

```bash
dpkg -S "$(command -v find)" "$(command -v xargs)"   # → findutils
dpkg -S "$(command -v locate)"                        # → plocate
```

The interview value is not the dpkg trivia — it is knowing that "findutils" is simultaneously a *source package* (find, xargs on Debian), a *tool family* (historically also locate/updatedb), and an *upstream project* whose locate implementation most distributions have now replaced. Using the three meanings interchangeably in an answer is a small but visible credibility leak.

## The find expression language, in one screen

The full language lives on the [find deep-dive](../../shell/find.md); what follows is the shape of it, because every other tool in this family is measured against it:

```bash
find [paths...] [options] [tests] [actions]
```

- **Options** tune traversal: `-maxdepth 2`, `-xdev` (stay on one filesystem), `-L` (follow symlinks).
- **Tests** filter: `-name '*.c'`, `-type f`, `-size +100M`, `-mtime -7`, `-perm -u+x`, `-user alice`, `-newer marker` — combined left-to-right with implicit AND and explicit `-a`/`-o`/`!` and `\( \)` grouping.
- **Actions** do the work: `-print` (default), `-print0` (NUL-safe), `-exec cmd {} +` (batched), `-exec cmd {} \;` (per file), `-delete`, `-ls`.

```bash
# The shape of a real production find: filter, guard, act
find /var/log -xdev -type f -name '*.log' -mtime +30 -print0 | xargs -0 -r gzip
```

Evaluation order and the implicit-AND surprise (`-name a -o -name b -print` prints less than you think) are the interview-grade material — covered in depth on the find page.

## xargs in one screen

`xargs` converts stdin words into command arguments, batching to stay under `ARG_MAX` — the fix for `find -exec` per-file process cost and for `cmd $(find ...)` argument-list explosions:

```bash
find . -name '*.tmp' -print0 | xargs -0 -r rm -v      # -0: NUL-safe, -r: skip empty input
find . -type f | xargs -P 4 -n 100 gzip               # 4 parallel workers, 100 args each
```

Its exit-code algebra (123 = some invocation failed, 124 = argv overflow, 125/126/127...) is documented on the [xargs page](../../shell/xargs.md). With locate, the pair is `-0` on both ends — the only safe handoff when filenames contain anything but ASCII letters.

## The locate data path, end to end

```
 nightly (timer)                per query (milliseconds)
┌───────────────────┐          ┌─────────────────────────────┐
│ plocate-updatedb  │          │ locate -b '*.service'       │
│ .timer 03:00+rand │          │  1. glob/regex parse        │
│   └─▶ updatedb    │          │  2. trigram lookup + AND/OR │
│       walk + prunes│   db    │  3. verify candidates in db │
│       trigram index│───────▶ │  4. visibility check per hit│
│       atomic rename│          │  5. print / -c / -n / -0    │
└───────────────────┘          └─────────────────────────────┘
```

Each numbered step is a separate failure domain, and each has a page: the walk and its prunes are [updatedb](./updatedb.md); steps 1–5, the security check, and the staleness consequences are [locate](./locate.md).

## Pruning: what is deliberately not in the index

`updatedb` excludes, by configuration in `/etc/updatedb.conf`: pseudo-filesystems (`PRUNEFS`: proc, sysfs, tmpfs...), network mounts (nfs, cifs, autofs), path prefixes (`PRUNEPATHS`: /tmp, /var/spool, /media...), and bind-mount duplicates (`PRUNE_BIND_MOUNTS`). Two consequences interviewers probe:

- `locate` finding nothing under `/tmp` is *correct*, not a failure — and the same is true for anything you add to the prune lists.
- Editing the config changes nothing until the next rebuild; the existing database keeps serving stale entries from newly pruned paths.

## Scripting recipes across the family

```bash
# Package file lookup: which installed package owns a located file
dpkg -S "$(locate -b -n 1 '50-cloud-init.yaml' 2>/dev/null)" 2>/dev/null || echo "not indexed or not from a pkg"
```

```bash
# Same-second truth: find beats locate when the file was just created
find /srv/uploads -maxdepth 1 -type f -mmin -5 -name '*.csv'
```

```bash
# Clean 30-day-old logs in one pipeline (find filter + xargs batching)
find /var/log/myapp -type f -name '*.log.*' -mtime +30 -print0 | xargs -0 -r rm
```

```bash
# Locate-first triage: is the name anywhere on the box, then verify live
for p in $(locate -n 20 -b 'trivy'); do [ -x "$p" ] && echo "executable: $p"; done
```

```bash
# Rebuild the index right now after a bulk data load (don't wait for the timer)
sudo updatedb && locate -c newdataset
```

```bash
# Private index for a huge project tree; query it without root or the system db
updatedb -U ~/src -o ~/src.db
alias locsrc="locate -d ~/src.db"
```

```bash
# Audit what the index knows about a path prefix
locate -c /var/www && locate -n 10 /var/www
```

```bash
# Guard a pipeline against stale entries: drop ghosts before xargs acts
locate -0 '*.deb' 2>/dev/null | xargs -0 -r sh -c 'for p; do [ -e "$p" ] && printf "%s\n" "$p"; done' _
```

```bash
# Verify the nightly job ran (staleness monitoring for dashboards)
[ -z "$(find /var/lib/plocate -name plocate.db -mmin -1440)" ] && echo "index older than 24h"
```

```bash
# The classic anti-pattern, shown for the interview answer (never do this)
for f in $(find . -name '*.txt'); do echo "$f"; done   # breaks on spaces/newlines
```

## The walk-vs-index decision

```
                  Do you need the truth as of NOW?
                   │yes                        │no
                   ▼                           ▼
         Is the predicate more than      locate the name/index
         a name? (size, time, perms,    ──────────────────────
         type, content, -exec)?              fast answer, accept
                   │yes                the staleness window
                   ▼
              find (walk)
                   │
        many results to act on?
                   │yes
                   ▼
             pipe to xargs -0
```

Rules of thumb worth internalizing:

- **Scripts and CI**: `find` — snapshot semantics are a bug generator (ghost paths, invisible new files).
- **Interactive "where is X?"**: `locate` — humans forgive staleness; they do not forgive 30-second directory walks.
- **Acting on many files**: `find ... -print0 | xargs -0 cmd` (or `find ... -exec cmd {} +`) — never `for f in $(find ...)` (word-splitting bug).
- **Fresh install and you need it findable**: `sudo updatedb`, then `locate`.

## Exit-code conventions

The family keeps the Unix "exit code is the answer" discipline, with per-tool meanings:

| Tool | 0 | 1 | >1 |
| --- | --- | --- | --- |
| `find` | traversal completed | — | trouble (syntax, unreadable start point; 1 on errors) |
| `xargs` | all invocations succeeded | any invocation exited 1-125 (GNU: 123) | 124 (exited 255), 125 (killed), 126/127 (not runnable/found) |
| `locate` | at least one match | no matches | 2 trouble (db/IO) |
| `updatedb` | database rebuilt | — | scan/write failure; previous db left intact |

The practical asymmetry: locate's 1-vs-2 split lets scripts distinguish "the index has no such name" from "the index is broken", mirroring the diffutils family's differ-vs-trouble convention.

## Security trade-offs: walk vs index

- **find** traverses with *your* credentials: it can only ever report what you can reach. Zero leakage, zero staleness — the audit-grade tool.
- **locate** answers from a shared database (group-readable, accessed via setgid) and applies per-result visibility checks before printing, so users cannot fish names out of the index that they could not `stat` themselves. The residual caveats: results reflect permissions at *index time* for paths captured at *query time* — two snapshots of one moving filesystem — and anyone in the index group can read the raw database.

Interviewers like this exact contrast because it forces the insight that the index is a *cache of the namespace*, not of file contents — and caches inherit every consistency question caches always have.

## Interview threads this collection covers

- **Walk vs index trade-off** — when the snapshot lies (new files, ghost files, pruned trees) and when milliseconds beat truth.
- **Safe pipelines** — `-print0 | xargs -0` vs word-splitting `for f in $(find ...)`; why the unsafe form survives until the first filename with a space.
- **The find expression grammar** — options/tests/actions, implicit AND, `\( \)` grouping, short-circuit evaluation cost.
- **xargs batching** — ARG_MAX, `-n`, `-P`, and its exit-code algebra (123/124/125...).
- **Packaging archaeology** — why `locate` on bookworm is plocate, what GNU findutils still ships, and how `Provides:` swaps implementations invisibly.
- **Security models** — find's credential traversal vs locate's shared index plus per-result visibility checks; what each can and cannot leak.
- **Operational hygiene** — timer scheduling, db mtime monitoring, prune tuning, and the "index older than 24h" alert.

## Inventory

| Page | Deep-dive location | Topic |
| --- | --- | --- |
| [locate](./locate.md) | this collection | indexed filename search (plocate), pattern semantics, security model, staleness |
| [updatedb](./updatedb.md) | this collection | database rebuilds, /etc/updatedb.conf pruning, systemd timer scheduling, root vs user dbs |
| [find](../../shell/find.md) | shell collection | full traversal language: predicates, operators, -exec, performance |
| [xargs](../../shell/xargs.md) | shell collection | argument batching, -0/-d, parallelism, exit-code algebra |

## Reading order

1. **[find](../../shell/find.md)** — the foundation; every other tool here is an optimization of some find workload.
2. **[xargs](../../shell/xargs.md)** — how find's output becomes efficient action, safely.
3. **[locate](./locate.md)** — the index query side; pattern semantics and the security model.
4. **[updatedb](./updatedb.md)** — the index maintenance side; prunes, timers, and staleness management.

## Related pages in this book

- [Part overview](../overview.md) — every userland binary collection in this part.
- [bash](../../shell/bash.md) — pipelines, process substitution, and the word-splitting traps around find/xargs.
- [regex](../../shell/regex.md) — the pattern language behind `find -regex` and `locate --regex`.
- [grep](../../shell/grep.md) — content search; the tool that answers what name search cannot.
- [permissions](../../admin/permissions.md) — the traversal-permission model that makes find's results per-user.
- [systemd](../../admin/systemd.md) — timer units scheduling updatedb on modern Debian.

## References

- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/findutils/)
- [Source — Debian sources](https://sources.debian.org/src/findutils/)
