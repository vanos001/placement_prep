# findmnt — search and display mounted (or configured) filesystems

## Overview

`findmnt` is the modern libmount-based replacement for eyeballing `/proc/mounts`, `cat /etc/mtab`, and `mount | grep`. It lists mounted filesystems from the kernel mount table by default, but the same query engine also searches `/etc/fstab` (`-s`), `/etc/mtab` (`-m`), or an arbitrary tab file (`-F`), and can filter by device, mountpoint, path, filesystem type, or mount options. Output is a mount tree by default, with machine-readable list/raw/pairs/JSON modes for scripts.

It ships in the `util-linux` package at `/usr/bin/findmnt`. Reach for it when you want to answer "what filesystem is this path on?", "what options was this device mounted with?", "which mounts exist under /var?", or "did my mount happen yet?" — questions that are awkward with plain `mount` output. It is often confused with `mount` (which mounts and dumps, but has no query/filter engine) and with `lsblk` (which walks block devices, not mount points).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/bin/findmnt |
| First appeared | util-linux 2.18 (2010), part of the libmount rewrite |
| Standards | None (util-linux/Linux-specific) |

## Synopsis

```
findmnt [options]
findmnt [options] <device> | <mountpoint>
findmnt [options] <device> <mountpoint>
findmnt [options] [--source <device>] [--target <path> | --mountpoint <dir>]
```

Common one-line forms:

```
findmnt                      # tree of all mounted filesystems
findmnt -T /etc/passwd       # which filesystem holds this path
findmnt -S /dev/sdb1         # all mounts of that device (bind mounts included)
findmnt -rn -o TARGET,FSTYPE # script-friendly: raw, no headings
```

## How It Works

### Data sources

`findmnt` does not parse kernel memory directly; it reads one of four tab sources through libmount and answers queries against that table. The default source is the kernel's view, which is why `findmnt` reflects bind mounts, overmounts, and propagation flags that `fstab`-based tools cannot see.

```
┌──────────────────┬──────────────────────────────┬─────────────────────────┐
│ option           │ file read                    │ viewpoint               │
├──────────────────┼──────────────────────────────┼─────────────────────────┤
│ (default) / -k   │ /proc/self/mountinfo         │ kernel, live state      │
│ -m, --mtab       │ /etc/mtab                    │ mount(8) records        │
│ -s, --fstab      │ /etc/fstab                   │ configured, not mounted │
│ -F, --tab-file   │ any file in fstab/mtab format│ containers, chroots     │
└──────────────────┴──────────────────────────────┴─────────────────────────┘
```

`/proc/self/mountinfo` is richer than the classic `/proc/mounts`: every entry carries a mount ID, its parent mount ID, and the root of the filesystem the mount is exposed from. That parent chain is exactly what the default tree output is built from.

### The tree

Given entries like `36 1 8:2 / / rw` (mount ID 36, parent ID 1), findmnt grafts each mount under its parent. Bind mounts and btrfs subvolumes additionally carry a *root path* — the subpath inside the source filesystem — which is displayed as `source[/subpath]`:

```bash
$ findmnt -T /mnt/chroot/usr
TARGET      SOURCE            FSTYPE OPTIONS
/mnt/chroot /dev/sdb1[/usr]   ext4   rw,relatime
#           ^^^^^^^^ fs root: this mount exposes the /usr subtree of sdb1
```

`-v, --nofsroot` hides that suffix; `-c, --canonicalize` resolves symlinks in printed paths; `-e, --evaluate` translates `LABEL=`/`UUID=` tags to real device names.

### Matching semantics

- `<device>` or `<mountpoint>` operand: exact match on source or target.
- `-T, --target <path>`: the path may be *anywhere inside* the filesystem — `findmnt -T /etc/passwd` reports the mount covering the file. This is the mode used most.
- `-M, --mountpoint <dir>`: the argument must be the mountpoint itself.
- `-S, --source <string>`: matches device names, `maj:min`, `LABEL=`, `UUID=`, `PARTUUID=`, `PARTLABEL=`.
- `-t, --types`, `-O, --options`: filter by filesystem type list or mount options.
- `-R, --submounts`: include child mounts of each match; `-f, --first-only`; `-i, --invert`; `-A, --all` disables built-in filters; `-U, --uniq` drops duplicate targets.

```bash
$ findmnt -T /etc
TARGET SOURCE    FSTYPE OPTIONS
/      /dev/sda2 ext4   rw,relatime
```

### Output formats

Default output is a tree with columns `TARGET SOURCE FSTYPE OPTIONS`. Scripts should pin the format explicitly:

```
-l  list        flat lines, no tree glyphs
-r  raw         TAB-separated, spaces escaped      (awk-able)
-P  pairs       key="value" shell-quotable pairs
-J  json        {"filesystems": [ {...}, ... ]}
-D  df-style    adds SIZE USED AVAIL USE% columns
-I  df-i-style  inode counts instead of blocks
-b  bytes       numeric byte counts, no KiB/MiB/GiB
-n  noheadings  drop the header row
-u  notruncate  don't clip long values to column width
-o  output      column list, e.g. -o TARGET,SOURCE,FSROOT
```

`findmnt -p, --poll` switches to monitoring mode: it re-reads the mount table and reports `mount`, `umount`, `remount`, and `move` events, optionally restricted to a column list (`-p TARGET,OPTIONS`) and bounded by `-w <ms>`.

### Poll mode in detail

In poll mode the first line of output is the *current* state of the matching filesystem, then every detected change adds a line whose `ACTION` column names what happened (`mount`, `umount`, `remount`, `move`). The columns you list control what is shown per event; `OLD-TARGET` and `OLD-OPTIONS` columns exist specifically to describe the pre-change state:

```bash
$ findmnt --poll remount,umount -M /mnt/data -o ACTION,TARGET,OPTIONS
ACTION  TARGET    OPTIONS
umount  /mnt/data  rw,relatime        # device unplugged
```

Without `-w` the loop runs until interrupted; scripts should always bound it.

### Diffing configured vs live

Because the same query engine runs against both fstab and the kernel table, drift detection is two queries apart:

```bash
# entries configured but not currently mounted
findmnt -rn -s -o TARGET,SOURCE | while read -r t s; do
    findmnt -M "$t" >/dev/null || echo "not mounted: $t ($s)"
done
```

fstab-only columns appear in `-s` mode: `FREQ` (dump period) and `PASSNO` (the fsck pass number), which is a handy way to audit pass-number hygiene from the command line.

## Options That Matter

### Query and data source

| Option | Effect |
| --- | --- |
| `-s, --fstab` | Search `/etc/fstab` instead of the kernel table |
| `-m, --mtab` | Search `/etc/mtab` (includes userspace mount options) |
| `-k, --kernel` | Search the kernel mount table (the default) |
| `-N, --task <tid>` | Query another process's namespace via `/proc/<tid>/mountinfo` |
| `-F, --tab-file <path>` | Read an alternative tab file (container rootfs, saved table) |
| `-T, --target <path>` | Find the filesystem containing `<path>` |
| `-S, --source <string>` | Filter by device, `UUID=`, `LABEL=`, `maj:min` |
| `-M, --mountpoint <dir>` | Exact mountpoint match |
| `-t, --types <list>` | Limit to filesystem types (`ext4,xfs`, `noats`...) |
| `-O, --options <list>` | Limit by mount options (`ro`, `noexec`, ...) |
| `-R, --submounts` | Print all submounts of matches too |
| `-A, --all` | Disable built-in filters, print everything |
| `-i, --invert` | Invert the match |
| `--shadowed` | Print only filesystems over-mounted by another (recent releases) |

### Output control

| Option | Effect |
| --- | --- |
| `-l, --list` | Flat list instead of tree |
| `-r, --raw` | TAB-separated raw output |
| `-P, --pairs` | `key="value"` output, safe for shell eval |
| `-J, --json` | JSON output |
| `-D, --df` / `-I, --dfi` | df(1)-style sizes / inode usage |
| `-o, --output <list>` | Choose columns; `--output-all` for everything |
| `-b, --bytes` | Sizes in raw bytes, not human units |
| `-n, --noheadings` | Suppress the header line |
| `-u, --notruncate` | Never clip column contents |
| `-e, --evaluate` | Resolve LABEL/UUID tags to device names |
| `-v, --nofsroot` | Hide the `[/subpath]` root suffix of bind mounts |
| `-p, --poll[=<list>]` | Monitor mount table changes; `-w <ms>` bounds the wait |

## Usage Patterns

```bash
# What filesystem is this file on? (the single most useful query)
findmnt -T /var/lib/docker

# Which mounts come from this device, including bind mounts?
findmnt -S /dev/nvme0n1p2

# Confirm a mount finished before continuing a script
findmnt -M /mnt/backup >/dev/null && do_backup

# Script-friendly: raw output of target and type
findmnt -rn -o TARGET,FSTYPE | grep -v tmpfs

# df-like view with sizes for a specific mount
findmnt -D -T /home

# Show the configured /etc/fstab entry, not the live mount
findmnt -s -S UUID=8f3c1d2a-4b5e-6f70-8a9b-0c1d2e3f4a5b

# Every mount whose options contain "ro"
findmnt -O ro

# All mounts under /var, including submounts
findmnt -R /var

# Machine-readable pairs for eval in a provisioning script
findmnt -P -n -o TARGET,FSTYPE -T /data

# JSON for a monitoring agent
findmnt -J -t ext4,xfs

# Watch for unmounts of /mnt/usb for 30 seconds
findmnt --poll umount -M /mnt/usb -w 30000

# Inspect the mount table of a container's PID namespace
findmnt -N 4215

# Which configured filesystems are NOT mounted right now?
findmnt -rn -s -o TARGET | while read -r t; do
    findmnt -M "$t" >/dev/null || echo "missing: $t"
done

# Audit fstab pass numbers (fsck ordering) without opening an editor
findmnt -rn -s -o TARGET,PASSNO,FSTYPE | sort -k2

# Watch for remounts (e.g. someone flipping a fs read-only)
findmnt --poll remount -w 60000
```

## Nuances and Gotchas

- **Tree glyphs vs scripts.** The default output is a tree and column widths are optimized for a human terminal (values get truncated). Any scripted use should set `-n` plus `-r`, `-P`, or `-J`; otherwise your parser will eventually meet a long `OPTIONS` string with spaces.
- **`-T` is path-based, `-M` is exact.** `findmnt -T /etc/nsswitch.conf` finds the mount covering the path, while `findmnt -M /etc` only matches if `/etc` *is* a mountpoint. Mixing them up produces confusing empty results.
- **`source[/root]` suffix.** Bind mounts show `tmpfs[/export/data]`-style sources. Grep-ing for the device name still works, but comparing the whole SOURCE string does not; use `-v` or the `FSROOT` column if you need to reason about it.
- **Live table ≠ fstab.** `findmnt` (default) shows reality; `findmnt -s` shows intent. A line missing from the default view means "not mounted", which is exactly what you want to test after `mount -a`.
- **Pseudo-filesystems and filters.** findmnt applies a few built-in sanity filters; `-A` disables them. If an expected mount seems invisible, try `findmnt -A -T <path>` before concluding it does not exist.
- **Truncation lies.** Long option lists are clipped to the column width. `findmnt -u` prints them in full — comparing mount options without `-u` can compare truncated strings.
- **Namespaces.** In containers, your mount table is per-namespace. `-N <pid>` queries another namespace (needs access to its `/proc`); this is the standard trick for inspecting a running container's mounts from outside.
- **`--poll` is a loop, not a snapshot.** It re-reads mountinfo and diffs; high-frequency mount churn (FUSE autofs, systemd mount units) can produce bursts of events. Bound it with `-w` in scripts.
- **Autofs and churn.** Autofs-triggered mounts appear and vanish within milliseconds of a stat; a naive `findmnt | grep nfs` can race the automounter. Query the path itself (`-T`) rather than listing and grepping — `-T` triggers the automount just like any other path access.
- **Overmounts hide what you think is there.** If something was mounted *over* `/srv/data`, the original mount is invisible in the tree — it is shadowed. Recent findmnt releases expose `--shadowed` to list exactly these; without it, a mysterious empty or different-looking directory is the classic symptom.
- **Column sets move between releases.** New columns (`SOURCES`, `UNIQ-ID`, poll columns) appear as libmount grows; a script pinned to `--output-all` will one day meet a column it cannot parse. Always enumerate the columns you need.

## Exit Status

- `0` — success (a match was found and printed, or poll ended normally).
- Nonzero — wrong call/usage error, no match found, or runtime failure (permissions, unreadable tab file). Scripts should test zero vs nonzero only.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`mount`](./mount.md) — performs the mounts that findmnt then reports.
- [`umount`](./umount.md) — unmounts; pair with `findmnt --poll umount` to observe.
- [`lsblk`](./lsblk.md) — block-device tree; findmnt is the mounted-filesystem view of the same world.
- [`blkid`](./blkid.md) — resolves the `LABEL=`/`UUID=` tags that `-S` and `-e` consume.
- [`mountpoint`](./mountpoint.md) — minimal "is this a mountpoint?" test.
- [`lslocks`](./lslocks.md) — the same libmount-adjacent reporting style for file locks.
- [`systemd`](../../admin/systemd.md) — mount units and `.mount` automounts behind many entries.
- [`internals`](../../internals.md) — how `/proc/self/mountinfo` reflects the VFS mount tree.

## Interview Questions

### Q: How do you find out which filesystem a given file resides on, from a script?

`findmnt -T /path/to/file -n -o TARGET,SOURCE,FSTYPE`. `-T` accepts any path inside the mount and returns the deepest mount covering it — unlike `df /path/to/file`, findmnt gives you parseable columns and can also show submounts with `-R`, bind-mount roots via the `FSROOT` column, and options that `df` does not print.

### Q: Why does findmnt show a source like `tmpfs[/export/data]`, and how do you hide that suffix?

That syntax means the mount exposes only the `/export/data` subtree of the source filesystem — a bind mount (or btrfs subvolume mount). The string before the brackets is the real device/superblock, the bracketed part is the filesystem root (`FSROOT` column). `-v, --nofsroot` suppresses the suffix when you want plain device names.

### Q: What is the difference between `findmnt` with no arguments and `findmnt -s`?

No arguments reads the kernel mount table (`/proc/self/mountinfo`) — what is actually mounted right now, including mounts never listed in fstab. `-s` reads `/etc/fstab` — what the system is *configured* to mount, mounted or not. Diffing the two views is a standard way to detect failed mounts after `mount -a` or a broken fstab edit.

### Q: How would you write a script that waits until a network filesystem is mounted, with a timeout?

```
findmnt -M /mnt/nfs >/dev/null
```

in a retry loop, or `findmnt --poll mount -M /mnt/nfs -w 60000`, which blocks until a mount event for that target arrives or the 60 s timeout expires. The poll form avoids a fixed sleep interval and reacts immediately; both rely on findmnt reading the live kernel table rather than mtab caches.

### Q: Which findmnt output modes would you use for (a) awk parsing, (b) shell eval, (c) a monitoring agent, and why?

(a) `-r` raw: TAB-separated single lines, spaces escaped, no tree glyphs. (b) `-P` pairs: every field printed as `KEY="value"`, directly evaluable. (c) `-J` JSON with an explicit `-o` column list: stable schema and types. All three should be combined with `-n` (no headings) and an explicit column list so output never depends on terminal width or locale.

### Q: A teammate greps `mount | grep nfs` in CI and gets flaky results. What do you suggest and why?

Replace it with `findmnt -t nfs,nfs4 -n` and an exit-code test. `mount`'s dump output is for humans (variable columns, locale-dependent), while findmnt queries libmount directly, supports type/option filters, and exits nonzero when nothing matches — no fragile grep over formatted text.

### Q: What is a shadowed (over-mounted) filesystem, and how does findmnt help diagnose one?

Mounting a filesystem over an already-mounted directory hides the underlying mount from the tree — only the top entry is visible. Symptoms are "this directory shows different content after an update job" or data written to a path that silently landed on the old, now hidden, mount. Recent findmnt releases provide `--shadowed` to list over-mounted targets directly; the forensic fallback is comparing `/proc/self/mountinfo` (which keeps every mount, shadowed or not) against the findmnt tree.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/findmnt.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
