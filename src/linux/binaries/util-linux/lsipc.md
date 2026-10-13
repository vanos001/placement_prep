# lsipc — list System V IPC facilities (modern ipcs)

## Overview

`lsipc` is util-linux's modern replacement for `ipcs`: the same System V IPC inventory (shared memory, semaphores, message queues) with structured output modes — column selection, raw, JSON, export — and a unified limits view with usage percentages. Where `ipcs` renders fixed-width tables from the 1980s, `lsipc` is built to be parsed. Ships in the `util-linux` package (Debian bookworm) at `/usr/bin/lsipc`.

Reach for it in scripts, monitoring checks, and capacity reports ("SysV shared memory at 42% of SHMALL"); keep `ipcs` for the traditional eyeballing workflow. It is often confused with `ipcs` (same data, display-only formatting), with `ipcmk`/`ipcrm` (create/remove around what lsipc reports), and with the general `ls*` family (`lsblk`, `lscpu`, `lslocks`, `lsmem`) that util-linux grew for machine-friendly system inventory.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/lsipc |
| First appeared | util-linux addition (mid-2010s) |
| Standards | None (System V IPC introspection; no command standard) |

## Synopsis

```
lsipc [options]
```

Common one-line forms:

```
lsipc                    # resource limits overview (default)
lsipc -m                 # shared memory segments table
lsipc -s --json          # semaphores as JSON
lsipc -i 42              # full detail of one System V resource
```

## How It Works

### Two views: limits and objects

With no resource selector, `lsipc` prints the *system-wide limits* overview — one row per tunable, with current usage and a USE% column:

```bash
$ lsipc
RESOURCE DESCRIPTION                                               LIMIT USED  USE%
MSGMNI   Number of System V message queues                         32000    0 0.00%
MSGMAX   Max size of System V message (bytes)                         8K    -     -
MSGMNB   Default max size of System V queue (bytes)                  16K    -     -
SHMMNI   Shared memory segments                                     4096    1 0.02%
SHMALL   Shared memory pages                        18446744073692774399  256 0.00%
SHMMAX   Max size of shared memory segment (bytes)                   16E    -     -
SEMMNI   Number of semaphore identifiers                           32000    1 0.00%
...
```

This is `ipcs -l` plus usage — the fastest "are we near a limit?" read. With `-m`, `-s`, or `-q`, the view switches to the *object tables*:

```bash
$ ipcmk -S 2 >/dev/null && lsipc -s
KEY        ID      PERMS    OWNER  NSEMS
0xfcd16071 0       rw-r--r-- z        2

$ lsipc -s --json
{
   "semaphores": [
      {
         "key": "0xfcd16071",
         "id": "0",
         "perms": "rw-r--r--",
         "owner": "z",
         "nsems": "2"
      }
   ]
}
```

### One-resource detail

`-i <id>` dumps the `IPC_STAT`-style detail for a single System V object (uid/gid/cuid/cgid, mode, sizes, PIDs, timestamps) — the structured equivalent of `ipcs -m -i 42`. `-l, --list` forces the table view where the detail view would otherwise take over.

### Output modes are the point

- **`--json`** — stable JSON for `jq`.
- **`-r, --raw` / `-e, --export`** — column-oriented raw text and `KEY=value` export lines for shell sourcing (`eval`-style consumption).
- **`-y, --shell`** — column names transliterated into shell-variable-safe form.
- **`-o, --output <list>`** — pick columns (`KEY,ID,BYTES,NATTCH`); `--noheadings` and `--notruncate` produce clean rows for `awk`.
- **`-P, --numeric-perms`** — octal numeric permissions instead of `rwx` strings.
- **`-b, --bytes`** — disable the human-readable `8K`/`16E` formatting on size columns (JSON/raw consumers want plain integers).

### Where the data comes from

The same kernel interfaces as `ipcs` — `/proc/sysvipc/{shm,msg,sem}` and `IPC_INFO`-style queries — so both tools always agree on content; they differ only in presentation. Limits come from the namespace's tunables (`kernel.shm*`, `kernel.sem`, `kernel.msg*`), which is why the `LIMIT` column is namespace-scoped inside containers.

### The raw interface underneath

`/proc/sysvipc/*` exposes the same rows as plain text and is the fallback when neither tool is installed:

```bash
$ cat /proc/sysvipc/shm
       key      shmid perms                  size  cpid  lpid nattch ...
 558841829          2   644               1048576 26592     0      0 ...
```

Columns there are hex-free and stable (`key` in decimal, sizes in bytes, all timestamps as epoch seconds) — which is why robust monitoring often reads procfs directly and treats both `ipcs` and `lsipc` as convenience layers.

### ipcs vs lsipc, contract by contract

| Aspect | ipcs | lsipc |
| --- | --- | --- |
| Default view | object tables | limits overview with USE% |
| Machine formats | none | `--json`, `-r`, `-e`, `-y`, `-o` |
| Limits view | `-l` (no usage) | default + `-m/-q/-s -l` slices |
| Detail per id | `-i` (pretty text) | `-i` (same fields, structured modes) |
| Truncation | fixed widths, clips owners | `--notruncate` opt-out |
| Locale sensitivity | times/columns formatted | controllable via `--time-format` |

### Column vocabulary, per view

The `-o` names differ per table — knowing them is what makes one-liners possible:

```
shared memory (-m):  KEY ID PERMS OWNER SIZE NATTCH STATUS CTIME CPID LPID COMMAND
semaphores   (-s):  KEY ID PERMS OWNER NSEMS CTIME
queues       (-q):  KEY ID PERMS OWNER USED-BYTES MESSAGES LSPID LRPID SEND RECV CTIME
limits  (default):  RESOURCE DESCRIPTION LIMIT USED USE%
```

`COMMAND` (the creator's executable) is the cleanup-lifecycle gem: it answers "which program left this behind" without touching `/proc`.

### Export and eval workflows

`-e` emits `KEY="value"` lines designed for shell consumption:

```bash
$ lsipc -m -e -i 2 -o ID,SIZE
ID="2" SIZE="1M"
```

`-y` transliterates header names into variable-safe form for table-style processing. Either path beats screen-scraping; the trap is mixing `-y` names and `-o` display names — they are different vocabularies for the same columns.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m, --shmems` | Shared memory segments table |
| `-q, --queues` | Message queue table |
| `-s, --semaphores` | Semaphore table |
| `-i, --id <id>` | Full detail for one resource |
| `-o, --output <list>` | Select columns (`KEY,ID,BYTES,NATTCH`…) |
| `-l, --list` | Force list/table format |
| `-J, --json` | JSON output |
| `-r, --raw` / `-e, --export` | Raw text / export (`KEY=value`) formats |
| `-y, --shell` | Shell-variable-safe column names |
| `--noheadings` / `--notruncate` | Drop header row / never clip columns (long-only options) |
| `-b, --bytes` | Plain byte counts, no `K`/`E` suffixes |
| `-P, --numeric-perms` | Numeric (octal) permissions |
| `-t, --time` | Add time columns; `--time-format=<short\|full\|iso>` styles them |

## Usage Patterns

```bash
# Quick capacity check: how close are we to IPC limits?
lsipc

# Inventory of shared memory with byte-exact sizes for scripting
lsipc -m -b --noheadings -o KEY,ID,BYTES,NATTCH

# JSON for monitoring (feed to jq)
lsipc -m --json | jq -r '.shm[] | "\(.id) \(.bytes) \(.nattch)"'

# Orphan hunt: segments with zero attachments and a key
lsipc -m -o KEY,ID,NATTCH,STATUS --notruncate

# Clean sweep of test leftovers (ids collected programmatically)
lsipc -m -o ID --noheadings | xargs -r ipcrm -m

# Detail on one resource before deleting it
lsipc -i 0
ipcrm -m 0

# Export-style output for shell variables
eval "$(lsipc -m -e -i 0 -o ID,BYTES)"
echo "segment $ID holds $BYTES bytes"

# Semaphore array inventory with numeric perms
lsipc -s -P --noheadings

# Limits for a specific class (the -m slice of the overview)
lsipc -m -l

# Which program created each segment? (COMMAND column)
lsipc -m -o ID,NATTCH,COMMAND --notruncate

# Stuck-queue triage: bytes queued, message count, last sender/receiver PIDs
lsipc -q -o ID,CBYTES,QNUM,LSPID,LRPID --notruncate
lsipc -q -t

# Feed a capacity report from the JSON view, byte-exact
lsipc -m -b --json | jq '[.shm[].bytes | tonumber] | add'

# Numeric permissions and epoch times for an audit log
lsipc -s -P --time-format=iso --noheadings
```

## Nuances and Gotchas

- **Default view is limits, not objects.** Bare `lsipc` shows the LIMIT/USED table; people expecting an `ipcs`-style object list need `-m`/`-q`/`-s`. The USE% column is the giveaway.
- **Human sizes by default.** `SHMMAX: 16E`, `MSGMAX: 8K` are rounded for display; add `-b` before comparing against sysctl values or doing arithmetic.
- **JSON shape is per-view** (`shm[]`, `sem[]`, `msg[]` arrays) — write jq filters against the specific view you requested, and remember all values arrive as strings.
- **SysV only in bookworm.** The POSIX-IPC extensions (`-M/-Q/-S`, `/dev/shm`, `/dev/mqueue` visibility) arrived in later util-linux releases; on bookworm POSIX shared memory is audited with plain `ls /dev/shm`.
- **Same permission model as ipcs**: objects owned by other users appear (the tables are readable), but nothing here grants access to their contents — reading data still requires the object's permissions.
- **`-i` needs the resource to exist in *this* namespace** — container-external ids are "not found"; ids increment monotonically, so stale ids from before a cleanup fail even for the same-looking object.
- **Raw/export/-y are for machines**; mixing `-y` names with `-o` display names in one call wastes an hour — pick one vocabulary and stay in it.
- **Not a replacement everywhere.** busybox has no `lsipc`; BSD/macOS have neither it nor `ipcs` with these modes. Portable scripts fall back to reading `/proc/sysvipc/*` directly.
- **`COMMAND` is best-effort provenance.** It resolves the creator's executable from `/proc` at read time; a since-exited creator leaves it empty, and paths for deleted binaries show the kernel's placeholder. Use it as a hint, not a forensic chain.
- **Time formatting is view-dependent.** The object tables show short times by default (`13:57`), which silently drops the date; audit-style output should pass `--time-format=full` or `iso` so December-31 artifacts do not masquerade as recent activity.

## Exit Status

- `0` — report produced (empty tables still succeed).
- `1` — error: unknown column or option, non-existent id for `-i`, or failure reading the IPC tables.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`ipcs`](./ipcs.md) — the classic reporter; same data, fixed display format.
- [`ipcmk`](./ipcmk.md) — creates the objects lsipc inventories.
- [`ipcrm`](./ipcrm.md) — removes them; pair `lsipc -o ID --noheadings | xargs ipcrm -m` for sweeps.
- [`lsblk`](./lsblk.md) — sibling util-linux "ls-for-kernel-objects" tool, block devices edition.
- [`internals`](../../internals.md) — IPC namespaces, `/proc/sysvipc` export, and the limit tunables.

## Interview Questions

### Q: What does bare `lsipc` show, and how does that differ from bare `ipcs`?

Bare `lsipc` prints the limits overview — one row per kernel tunable (MSGMNI, SHMMAX, SEMMNI, …) with current USED and USE% — while bare `ipcs` prints the object tables (segments, queues, semaphores). In lsipc the object views need `-m`/`-q`/`-s`. The limits-with-usage view is lsipc's distinctive contribution; `ipcs -l` shows limits without usage.

### Q: You must alert when System V shared memory nears capacity. Design it with lsipc.

Poll `lsipc` (limits view) for SHMALL/SHMMNI USE% thresholds, or enumerate objects with `lsipc -m -b --json` and sum `bytes`. The USE% column makes the naive check a one-liner; JSON output keeps the parser honest across locales. Also watch SEMMNI/MSGMNI in the same pass — count-based exhaustion fails differently than byte-based.

### Q: Why do lsipc and ipcs exist side by side instead of ipcs gaining JSON?

`ipcs` is bound by decades of traditional output (POSIX/SVID-era expectations, scripts that grep it); changing its format breaks them. util-linux's pattern is to add a parallel `ls*` tool (`lsipc`, `lsblk`, `lslocks`) with structured output as the machine interface while the classic tool freezes for humans. Same sysfs/procfs data, two contracts.

### Q: A monitoring script parsed `lsipc -m --json` on one host and fails on another with missing fields. Why?

Column sets/views can differ across util-linux versions and the JSON keys follow the requested view; a script hardcoding fields present only on the newer build (or querying the limits view instead of `-m`) gets absent keys. Pin expectations by selecting explicit columns, treat all values as strings, and fall back to `/proc/sysvipc/shm` — the stable kernel interface both tools read.

### Q: How do you find and clean orphaned System V shared memory segments safely?

List with `lsipc -m -o KEY,ID,NATTCH,STATUS`, flag zero-`nattch` segments (optionally with `dest` status), verify no owner processes exist (`ipcs -m -p` for creator/last-op PIDs, cross-checked with `ps`), then `ipcrm -m <id>` each. The listing step is deliberately separate from the delete step — `ipcrm --all` as root wipes other services' objects, which the selective pipeline avoids.

### Q: Explain the difference between the LIMIT column values for SHMMAX shown as "16E" and what the kernel enforces.

`16E` is the display-rounded human formatting of the enormous default (`ULONG_MAX`-ish on 64-bit: effectively "no practical limit"); the kernel enforces the exact numeric value. Any arithmetic must use `-b` (plain bytes) — comparing the string `16E` against a sysctl or allocating "up to SHMMAX" from that string is meaningless. Display formatting is for eyes; `-b` output is for math.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/lsipc.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
