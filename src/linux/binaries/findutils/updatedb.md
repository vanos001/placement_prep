# updatedb — rebuild the locate database

## Overview

`updatedb` walks the filesystem (or a chosen subtree), records every path it is allowed to index, and writes the result as the database that [locate](./locate.md) searches. On Debian bookworm it comes from the **plocate** package as a system tool (`/usr/sbin/updatedb`, man section 8), replacing the `updatedb` that GNU findutils and later mlocate historically shipped. It is not meant to be run by hand often: Debian schedules it through the `plocate-updatedb.timer` systemd unit (daily, with a randomized delay so fleets of machines do not all scan at the same second); manual runs are for "I just installed/generated a large tree and want it findable now".

`updatedb` is often confused with `find` (which searches live and writes nothing), with `sync` (name similarity, unrelated), and with backup/snapshot tooling (it records *names only* — zero file content). Its output is exactly one artifact: the database, `/var/lib/plocate/plocate.db` on Debian.

| Field | Value |
| --- | --- |
| Package | plocate (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/updatedb |
| First appeared | BSD lineage with locate; GNU findutils and mlocate rewrites; plocate 2020s |
| Standards | None (de-facto mlocate-compatible interface) |

## Synopsis

```
updatedb [OPTION]...
```

Common one-line forms:

```
updatedb                            # full system index (root; honors /etc/updatedb.conf)
updatedb -U /srv -o /tmp/srv.db     # index one subtree into a private db
updatedb -v                         # verbose: print every scanned path
updatedb --prunepaths '/tmp /mnt'   # one-off prune override
```

There are no file operands: the scan root comes from `-U` (default `/`) and all other behavior comes from options plus `/etc/updatedb.conf`.

## How It Works

### The scan

`updatedb` performs a full directory walk from the database root, recording the path of every entry it encounters, subject to three prune layers checked as it descends:

```
┌────────────────────────────────────────────────────────────┐
│  updatedb scan (root)                                      │
│                                                            │
│   for each directory reached:                              │
│     1. PRUNEFS      — is this on a filesystem type we skip?│
│        (proc, sysfs, tmpfs, nfs, cifs, autofs, ...)        │
│     2. PRUNEPATHS   — is the canonical path on the list?   │
│        (/tmp, /var/spool, /media, ...)                     │
│     3. PRUNE_BIND_MOUNTS = yes?  → skip bind mounts        │
│                                                            │
│   otherwise: record path, recurse into subdirectories      │
│                                                            │
│   output: temp db → atomic rename over the live db         │
└────────────────────────────────────────────────────────────┘
```

The last line matters: the database is written to a temporary file and renamed over the live one only when complete, so a crashed or killed `updatedb` leaves the previous, fully valid database in place — locate queries never observe a half-written index.

### The configuration file: /etc/updatedb.conf

A flat `KEY = value` file where value lists are space-separated; the names follow the mlocate tradition. An annotated, representative example:

```
# /etc/updatedb.conf — plocate/mlocate-style

# Skip bind-mount duplicates (same data indexed once, under its real path)
PRUNE_BIND_MOUNTS = "yes"

# Path prefixes never indexed: volatile trees, removables, junk
PRUNEPATHS = "/tmp /var/spool /media /mnt /home/.ecryptfs"

# Filesystem types never indexed: kernel pseudo-fs + network mounts
PRUNEFS = "tmpfs proc sysfs devtmpfs nfs nfs4 cifs autofs squashfs"
```

Reading rules into behavior:

- `PRUNEPATHS` — path prefixes to skip entirely. This is the knob administrators tune most: big volatile or remote trees that would bloat the index or slow the nightly scan.
- `PRUNEFS` — filesystem types to skip. Pseudo-filesystems (`proc`, `sysfs`, `devtmpfs`) are noise; network mounts (`nfs`, `cifs`, `autofs`) are usually excluded to keep the scan local and fast — indexing an NFS server's whole tree from every client is a classic misconfiguration.
- `PRUNE_BIND_MOUNTS` — whether bind-mount duplicates are skipped (typically `yes`, so the same underlying directory is indexed once under its original path).
- Visibility-related keys control whether the database is built with per-user visibility filtering enabled at all (see below).

Options override the file per run: `--prunepaths`, `--prunefs`, `--prune-bind-mounts yes|no`. Note the ordering effect: a path listed in `PRUNEPATHS` is skipped wherever it appears, which is why the file's comments (and the man page) stress that entries are prefixes, not exact matches.

### Scheduling: timer, not cron

Debian's plocate ships `plocate-updatedb.timer` + `plocate-updatedb.service` in place of mlocate's old `/etc/cron.daily` job. The timer fires daily with a randomized delay; the service runs `updatedb` as root with **low I/O and CPU scheduling priority**, so a scan of millions of directories degrades interactive latency minimally. plocate's build is deliberately I/O-friendly: directory reads are issued in parallel (`io_uring` on modern kernels) at idle priority — the "io niceness" the implementation is known for. Check and manage it like any timer:

```bash
systemctl list-timers --all | grep -i locate
systemctl cat plocate-updatedb.timer     # OnCalendar / randomized delay
sudo systemctl start plocate-updatedb.service   # force a rebuild now
```

On systems without the timer (containers, non-systemd images) `updatedb` simply never runs by itself — the database stays empty or stale until something invokes it, which is the root cause of most "locate returns nothing" support tickets.

### Root db vs user dbs

The lifecycle of a result, end to end — and where the staleness window opens:

```
  day 03:00      updatedb scans, db@03:10          (fresh)
  09:00          user creates /srv/big/report.csv  (invisible to locate)
  11:00          admin deletes /srv/old/report.csv (still findable — ghost)
  day+1 03:00    next updatedb                     (truth restored)
```

Everything in that middle window is where find and locate disagree — the standard interview scenario.

The system database is built by root (via timer or sudo), lands in `/var/lib/plocate/` as `root:plocate` group-readable, and is what plain `locate` queries with visibility checks filtering per-user results. Two variations:

- **Subtree scan for a private db**: `updatedb -U /srv/projects -o ~/projects.db` runs unprivileged, indexes only what *you* can read, and writes a db you own; query with `locate -d ~/projects.db ...`. Visibility filtering is meaningless there (it indexes only paths you could already see), which is why the visibility machinery is tied to whole-system dbs.
- **`--require-visibility`** controls whether the built database requests per-result visibility checks at query time; a root-built system db wants it on, a personal-subtree db does not need it.

Running the full system scan as a non-root user is possible but pointless: you would index only your own readable files, and the result would not be the system db.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-U PATH`, `--database-root=PATH` | Index only the subtree under PATH (default `/`). |
| `-o FILE`, `--database=FILE` | Write the database to FILE (default the system db). |
| `--prunepaths=PATHS` | Override `PRUNEPATHS` for this run. |
| `--prunefs=FS` | Override `PRUNEFS` for this run. |
| `--prune-bind-mounts=yes/no` | Override bind-mount pruning for this run. |
| `--require-visibility=yes/no` | Set whether locate should visibility-check results. |
| `--io-nice` | Run with idle I/O priority (plocate's background-friendly rebuild). |
| `-v`, `--verbose` | Print each path as scanned (also your debug view for prune rules). |

## Usage Patterns

```bash
# Refresh the index after a large install or generated tree
sudo updatedb
```

```bash
# Force the same rebuild the daily timer would do
sudo systemctl start plocate-updatedb.service
```

```bash
# Verify scheduling is actually in place on this machine
systemctl list-timers --all | grep -i locate
```

```bash
# See what the scanner is doing right now (verbose stream)
sudo updatedb -v 2>&1 | head -50
```

```bash
# Diagnose why a path is not indexed: watch it get (or not get) scanned
sudo updatedb -v 2>&1 | grep -c '^/var'   # is /var being walked at all?
```

```bash
# Build a private index over a project tree for instant name lookup
updatedb -U ~/src/bigproject -o ~/bigproject.db
locate -d ~/bigproject.db -b '*.go' | head
```

```bash
# One-off scan with extra prunes, without editing the config
sudo updatedb --prunepaths '/tmp /var/tmp /mnt /media'
```

```bash
# Inspect and tune the persistent prune configuration
cat /etc/updatedb.conf
sudoedit /etc/updatedb.conf   # add paths to PRUNEPATHS, then rebuild
```

```bash
# Keep a network mount out of every client's nightly scan (config, not flags)
#   PRUNEFS = "... nfs4 cifs autofs ..." in /etc/updatedb.conf
```

```bash
# Cron-style fallback on a non-systemd box
# /etc/cron.d/locate-db:  17 3 * * * root /usr/sbin/updatedb --io-nice
```

## Nuances and Gotchas

- **The db is a snapshot, and the timer is its only heartbeat.** Everything locate says is as of the last successful `updatedb`. Automation that *creates* files and then immediately `locate`s them is broken by design — use `find` in scripts that need same-second truth.
- **Tuning PRUNEPATHS changes cost, not correctness.** Every unpruned directory is read (metadata I/O) every night. Excluding `/tmp`, build dirs, caches, and network mounts keeps the scan cheap; forgetting to prune a huge mount makes the timer's idle-priority niceness irrelevant — it will still grind for hours.
- **Prefix semantics.** `PRUNEPATHS = "/tmp"` also skips `/tmpfs-projects` if such a path existed — entries are path prefixes. Add the trailing slash when you mean a directory exactly.
- **Failures do not destroy the old index.** The temp-file + atomic-rename design means an aborted scan leaves the previous db fully functional. But it also means a silently failing nightly scan (dying on a bad mount, out of space) can leave the index frozen at an old date — check db mtime (`ls -l /var/lib/plocate/plocate.db`), not just locate's silence.
- **Root runs need privilege for the system db.** Writing `/var/lib/plocate/plocate.db` requires root (or the packaged setgid arrangement); a bare `updatedb` as a normal user will fail or write elsewhere. Use `-o` for user-owned dbs.
- **`-U` changes the security story.** A subtree db contains only paths the scanning user could read — no visibility filtering needed, and conversely no leak. Do not `-o` a personal scan into the system db path.
- **PRUNE_BIND_MOUNTS and containers.** On hosts running many containers or chroots, bind mounts can explode the index with duplicate paths; leaving `PRUNE_BIND_MOUNTS = "yes"` is usually right, and pruning container overlay paths is common tuning.
- **The first scan after install is the expensive one.** Subsequent runs still walk everything unpruned, but page cache and plocate's compact index make steady-state cost manageable; the misconception that updatedb is "cheap" usually comes from never having watched `-v` on a large system.
- **No partial output, no progress bar.** Without `-v` the tool is silent until done; in scripts, judge success by exit status and db mtime, not by output.
- **`-v` is also your audit tool.** Prune-rule confusion ("why is X indexed?" / "why is Y missing?") is settled fastest by `updatedb -v` on a debug box and grepping the stream — faster than reasoning about prefix semantics from the config alone.
- **Implementation churn.** The interface is mlocate-compatible (deliberately), but this is plocate's reimplementation — flag sets like `--io-nice` are plocate additions, and GNU findutils' own `updatedb` differs in config keys and defaults. On minimal systems, check `updatedb --help` before scripting.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Database built and installed successfully. |
| nonzero | Scan or write failed (permission, I/O, bad config); the previous database remains in place. |

## Related Commands

- [`locate`](./locate.md) — the query side of the index updatedb builds.
- [`find`](../../shell/find.md) — live traversal; what to use when snapshot results are not good enough.
- [`xargs`](../../shell/xargs.md) — batch-act on paths found through the index.
- [systemd](../../admin/systemd.md) — the timer unit that schedules the nightly rebuild.
- [Collection overview](./overview.md) — find vs index: the findutils division of labor.
- [Part overview](../overview.md) — all userland binary collections.

## Interview Questions

### Q: What does updatedb actually do, and why is its output replaced atomically?

It walks the filesystem from the configured root, applying prune rules from `/etc/updatedb.conf` (`PRUNEPATHS`, `PRUNEFS`, bind mounts), records every visible path, compresses them into plocate's trigram index, and writes a temporary file that is renamed over the live database only on success. Atomic replacement means concurrent locate queries always see either the old or the new complete index — never a partial one — and a crashed scan costs nothing but time.

### Q: A server's locate results seem frozen weeks in the past. Walk your diagnosis.

First, check the heartbeat: `systemctl list-timers | grep locate` — is the timer enabled and last-firing? Then the artifact: `ls -l /var/lib/plocate/plocate.db` — is the mtime recent? If the timer fires but the db is old, look at the service logs (`journalctl -u plocate-updatedb.service`) for the scan dying — a bad network mount, a full filesystem, or a permission problem are the usual culprits. Finally, confirm nobody disabled the timer in a container image; on non-systemd systems nothing schedules updatedb automatically at all.

### Q: Why is indexing NFS mounts from every client a mistake, and what is the correct configuration?

It multiplies one scan by the client count: every machine's nightly updatedb walks the same remote tree over the network — slow, I/O-heavy on the server, and redundant. The standard fix is `PRUNEFS` entries for `nfs`/`nfs4`/`cifs`/`autofs` in `/etc/updatedb.conf` so each client indexes only local storage; if remote lookup is wanted, index the server itself or build one dedicated db with `updatedb -U` on the mount, shared read-only.

### Q: Explain root db vs user db in the plocate world.

The system db is built by root (via the systemd timer), stored group-readable under `/var/lib/plocate`, and searched by everyone through the setgid `locate`, which visibility-checks each result per user. A user db is built with `updatedb -U subtree -o file`, contains only what that user can read, needs no visibility filtering, and is queried with `locate -d file`. The split lets one shared, always-fresh system index coexist with cheap private indexes over project trees.

### Q: How does updatedb stay polite on a busy production machine?

Three layers: scheduling (Debian's timer fires daily with a randomized delay, and the service runs the scan with low CPU priority and idle I/O class), algorithm (plocate issues directory reads in parallel via io_uring at that low priority, and writes a compact index), and pruning (`/etc/updatedb.conf` keeps volatile and remote trees out of the nightly walk entirely). The interview-grade point: niceness limits *interference*, while pruning limits *total work* — you need both on large systems.

### Q: What happens if you delete the database file and never run updatedb again?

`locate` has nothing to search: depending on timing it errors or reports no matches — exit 1 forever. The timer will recreate it at the next scheduled run, but until then every locate query is quietly useless. The inverse also holds in weaker form: a *stale* db is more insidious than a missing one because ghost results look plausible. After deleting the db (or major tree surgery), run `sudo updatedb` explicitly rather than waiting for the timer.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/plocate/updatedb.8.en.html)
- [Source — Debian sources](https://sources.debian.org/src/plocate/)
