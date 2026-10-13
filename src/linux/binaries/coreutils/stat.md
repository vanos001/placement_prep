# stat — display file (inode) and filesystem status

## Overview

`stat` dumps the metadata the kernel keeps about a file — inode number, type,
mode, link count, ownership, sizes, and timestamps — or, with `-f`, the
metadata of the filesystem the file lives on. It is the script-facing window
onto the `stat(2)`/`statx(2)` syscalls: one operand in, one fixed report out,
no directory scan, no sorting, no locale-driven formatting.

It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at
`/usr/bin/stat`, maintained upstream as part of GNU coreutils. The tool was
written for Linux by Michael Meskes (originally distributed as its own
Debian package) and was absorbed into GNU coreutils in the 5.3 era
(2005). BSD systems carry a different `stat(1)` with an entirely different
flag set, and macOS ships the BSD one — the name is portable, the flags are
not. `stat` is most often confused with `ls -l` (same data, different job:
listing vs. reporting), with `du` (allocated space vs. inode facts), and
with `df` (filesystem capacity vs. file metadata). The rule of thumb is the
mirror of the `ls` rule: when you need *facts about one inode* in a stable,
parseable shape, reach for `stat`.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/stat` |
| First appeared / lineage | Michael Meskes, Linux, 1998; in GNU coreutils since the 5.3 era |
| Standards | none — GNU extension; absent from POSIX (BSD/macOS `stat` is a different tool) |

## Synopsis

```
stat [OPTION]... FILE...
```

Common one-line forms:

```
stat -c FORMAT FILE...    # print exactly FORMAT per operand
stat --printf=FORMAT F..  # like -c but interprets \n, no trailing newline
stat -f [-c FORMAT] FILE  # report the filesystem holding FILE
stat -t FILE              # terse one-line dump (machine-ish)
```

## How It Works

### One syscall, no content I/O

For each operand, `stat` calls `statx(2)` (modern kernels; `stat(2)` before
that) and formats the returned structure — it never opens or reads the file,
so a 100 GB image costs the same as a 4-byte stub. By default it behaves
like `lstat`: a symlink operand reports the *link*:

```bash
$ stat -c '%N %F' /bin
'/bin' -> 'usr/bin' symbolic link
$ stat -Lc '%N %F' /bin      # -L dereferences: describe the target
'/bin' directory
```

That default is the most common `stat` surprise: on usrmerge distros
`stat /bin` talks about the symlink, while `ls -ld /bin` dereferences
command-line operands.

### The default report, field by field

```text
  File: /etc/hostname
  Size: 33          Blocks: 8          IO Block: 4096   regular file
Device: 0,27    Inode: 20          Links: 1
Access: (0644/-rw-r--r--)  Uid: (    0/    root)   Gid: (    0/    root)
Access: 2026-10-09 09:31:32.797809091 +0000
Modify: 2026-10-09 07:51:16.824876000 +0000
Change: 2026-10-09 07:51:16.824876000 +0000
 Birth: -
```

| Line | Kernel datum | Format sequence |
| --- | --- | --- |
| `File:` | operand as typed (with quoting via `%N`) | `%n` / `%N` |
| `Size:` | `st_size` — apparent size in bytes | `%s` |
| `Blocks:` | `st_blocks` × 512 B actually allocated | `%b` (unit `%B`) |
| `IO Block:` | `st_blksize` — optimal I/O transfer hint | `%o` |
| (trailing word) | file type from `st_mode` | `%F` |
| `Device:` | `st_dev` of the holding filesystem | `%d`, `%D`, `%Hd`, `%Ld` |
| `Inode:` | `st_ino` | `%i` |
| `Links:` | `st_nlink` hard-link count | `%h` |
| `Access: (0644/...)` | `st_mode` decoded | `%a` (octal), `%A` (string) |
| `Uid:` / `Gid:` | `st_uid` / `st_gid`, numeric + resolved name | `%u`/`%U`, `%g`/`%G` |
| `Access:` (time) | `st_atim` — last read | `%x`, `%X` |
| `Modify:` | `st_mtim` — last content write | `%y`, `%Y` |
| `Change:` | `st_ctim` — last *inode* change | `%z`, `%Z` |
| `Birth:` | `statx` btime, when the filesystem provides it | `%w`, `%W` |

Two size numbers coexist and both matter: `Size` is what the file *claims*
(`st_size`), `Blocks × 512` is what the disk actually holds (`st_blocks`).
Sparse files make them diverge wildly — `truncate -s 1G x` yields
`%s=1073741824` and `%b=0`, and `du` then agrees with Blocks, not with
Size. The Device line's rendering has also changed across releases (older
coreutils printed a hex/decimal pair like `803h/2051d`; recent releases
print `major,minor`) — one more reason scripts should read fields via
`-c`, not by column position.

### The four (and a half) timestamps

```
atime  %x %X   read() touched it            (relatime: updates are lazy)
mtime  %y %Y   write() changed the data     (what backups and rsync key on)
ctime  %z %Z   inode metadata changed       (chmod, chown, ln, rename, write)
btime  %w %W   file came into existence     (statx-only, see below)
```

`ctime` is the perennial trap: it is *status change*, not creation time.
`chmod`, `chown`, a new hard link, a rename, or a write all bump it, and no
userland API can set it directly (`touch` can only forge atime and mtime).
`btime`, the real creation time, is the "half": it became visible only with
`statx(2)` (Linux 4.11, 2017) — the legacy `stat` syscall has no slot for it.

### Birth time availability

`%w` prints the birth time human-readable or `-` when unknown; `%W` prints
seconds since the Epoch or `0` when unknown — which makes `%W=0` ambiguous
with a genuinely ancient file, so treat `0` as "no data". Availability is a
filesystem question, not a stat question:

```bash
$ stat -c '%n %w' /etc/hostname /proc/1 /
/etc/hostname -                    # bind-mounted file, host fs won't say
/proc/1 -                          # procfs: no btime, ever
/ 2026-10-09 07:51:16.827876000 +0000
```

ext4, XFS, btrfs, and tmpfs on a ≥4.11 kernel report btime; procfs, sysfs,
and many network filesystems do not; NFS depends on the server protocol
version. Because recent coreutils probe `statx`, the same command may print
`-` on an old kernel and a timestamp on a new one — scripts must tolerate
both. Birth time is forensic gold: it survives renames (and usually moves
within a filesystem), is destroyed by `cp`, and cannot be backdated by
`touch`.

### Format sequences: the whole alphabet

`-c/--format` and `--printf` take a FORMAT string where each `%X` expands to
one fact; anything else is literal. `-c` appends a newline after each use of
the format; `--printf` does not, and additionally interprets backslash
escapes (`\n`, `\t`, `\\`, `\0`). `%m` (mount point) and `%C` (SELinux
context) are GNU additions.

| Group | Sequences | Meaning |
| --- | --- | --- |
| Name | `%n` `%N` | operand as given; quoted operand, with ` -> target` if a symlink |
| Ownership | `%u` `%U` `%g` `%G` | numeric and named UID / GID |
| Type & mode | `%F` `%A` `%a` `%f` | human type; mode string; octal perms; raw mode in hex |
| Size & links | `%s` `%b` `%B` `%o` `%h` | bytes; 512 B blocks; block unit; I/O hint; hard links |
| Timestamps | `%w` `%W` `%x` `%X` `%y` `%Y` `%z` `%Z` | birth / atime / mtime / ctime — lowercase human, uppercase epoch |
| Devices | `%d` `%D` `%Hd` `%Ld` | `st_dev` decimal/hex/major/minor (holding filesystem) |
| rdev | `%r` `%R` `%Hr` `%Lr` `%t` `%T` | `st_rdev` forms — nonzero only for device files |
| Misc | `%i` `%m` `%C` | inode number; mount point; SELinux context |

Numeric and time specifiers accept printf-style flags and precision, which
buys you zero-padding and sub-second epoch stamps:

```bash
$ stat -c '%.9Y' /etc/hostname      # mtime as epoch with nanoseconds
1791532276.824876000
```

### Filesystem mode: `stat -f`

`-f` swaps the target: instead of the inode, it reports the `statfs(2)`/
`statvfs(2)` data of the filesystem holding the operand — capacity, free
space, and inode inventory from the *filesystem's* point of view:

```text
  File: "/tmp"
    ID: 9c14b752d92cd089 Namelen: 255     Type: overlayfs
Block size: 4096       Fundamental block size: 4096
Blocks: Total: 2571077    Free: 2526035    Available: 2390867
Inodes: Total: 655360     Free: 647905
```

| Field | Kernel datum | Format | Relation to `df` |
| --- | --- | --- | --- |
| `ID:` | `f_fsid` | `%i` | — (fs identity hex) |
| `Namelen:` | `f_namelen` | `%l` | max filename length |
| `Type:` | fs magic | `%T` (name), `%t` (hex) | `df -T`'s Type column |
| `Block size:` | `f_bsize` | `%s` | transfer-size hint |
| `Fundamental block size` | `f_frsize` | `%S` | the unit all block counts use |
| `Blocks: Total/Free/Available` | `f_blocks`/`f_bfree`/`f_bavail` | `%b`/`%f`/`%a` | `df`'s 1K-blocks / the arithmetic behind Used and Available |
| `Inodes: Total/Free` | `f_files`/`f_ffree` | `%c`/`%d` | `df -i`'s Inodes/IFree |

The `Free` versus `Available` split is the reserved-blocks story `df` also
tells: `Free` (`f_bfree`) is all unallocated blocks, `Available`
(`f_bavail`) is what an unprivileged user may actually consume.

### Terse mode and why it exists

`-t` collapses everything to one blank-separated line — the help text
documents it as exactly this format: `%n %s %b %f %u %g %D %i %h %t %T %X
%Y %Z %W %o %C`. Grounded output on a non-SELinux host:

```bash
$ stat -t /tmp/stprobe
/tmp/stprobe 0 0 81b4 1001 1001 2c 269587 1 0 0 1791542045 1791542045 1791542045 1791542045 4096
```

Handy for eyeballing, treacherous for parsing: the trailing SELinux context
field appears only where SELinux data exists (here the line simply ends at
the I/O size, though an explicit `-c '%C'` would exit 1 with an error), and
the column layout has shifted across older releases. Automation should pass
an explicit, pinned `-c FORMAT` instead.

### stat vs ls — same data, different contract

| Dimension | `stat` | `ls -l` |
| --- | --- | --- |
| Data source | one `statx` per operand | `readdir` + per-entry `lstat` |
| Symlink operand | reports the link (lstat); `-L` follows | dereferences bare operands, lists links as links |
| Output shape | exactly what FORMAT says | locale-, tty-, and version-dependent |
| Cost | O(operands) syscalls | full directory scan + sort |
| Job | machine-readable facts about named inodes | human-oriented listing of directories |

For bulk reporting over many files, `find -printf` repeats stat's format
language inside a tree walk; `stat` is the point-tool when the shell or
`find` already picked the victims.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-c, --format=FORMAT` | Print FORMAT per operand, newline after each |
| `--printf=FORMAT` | FORMAT with backslash escapes, no trailing newline |
| `-f, --file-system` | Report the filesystem holding each operand instead |
| `-L, --dereference` | Follow symlinks — describe the target |
| `-t, --terse` | One-line abbreviated dump (fixed, release-dependent columns) |
| `--cached=MODE` | `always`/`never`/`default` — attribute-cache policy, mainly for NFS/remote fs (recent coreutils) |

## Usage Patterns

```bash
# Inspect everything the kernel knows about a file
stat /var/log/syslog

# Permissions + ownership in a stable, parseable form
stat -c '%a %U %G %n' /etc/shadow /etc/passwd
```

```bash
# File age in seconds — the bread-and-butter monitoring idiom
age=$(( $(date +%s) - $(stat -c %Y /tmp/heartbeat) ))
[ "$age" -gt 300 ] && echo "stale heartbeat"

# Newest files at a directory level, epoch-sortable
stat -c '%Y %n' ./* | sort -rn | head -3
```

```bash
# Does this filesystem even track creation time?
stat -c '%n birth=%w' /home/deploy/build.lock

# What does this symlink point at right now (no readlink needed)
stat -c '%N' /bin        # '/bin' -> 'usr/bin'
```

```bash
# NUL-safe bulk fact dump, safe for weird filenames
find . -maxdepth 1 -name '*.log' -print0 |
  xargs -0 stat --printf='%s\t%Y\t%n\0\n'
```

```bash
# Same-filesystem check before an atomic rename
[ "$(stat -c %d "$src")" = "$(stat -c %d "$dst_dir")" ] &&
  mv "$src" "$dst_dir/" || echo "cross-device: mv will copy"

# Which mount serves this path? (bind mounts, NFS, containers)
stat -c '%m %D' /home/deploy/data
```

```bash
# Filesystem facts for a path: type, free blocks (non-root view), free inodes
stat -f -c 'type=%T free_blocks=%a of %b free_inodes=%d of %c' /

# Sparse-file forensics: claims 1G, holds ~0
truncate -s 1G /tmp/sparse.img && stat -c 'apparent=%s blocks=%b' /tmp/sparse.img
```

```bash
# Poll until a file stops growing (size stable across 2s)
s1=$(stat -c %s big.log); sleep 2; s2=$(stat -c %s big.log)
[ "$s1" = "$s2" ] && echo "complete"
```

## Nuances and Gotchas

- **Symlinks are not followed by default.** `stat /bin` on a usrmerge distro
  describes the symlink; `ls -ld /bin` describes the directory. If `$path`
  may be a link, decide explicitly and use `-L` when you mean the target.
- **`%b` counts 512-byte blocks**, `st_blocks` units — while `du` prints
  1 KiB units by default and `ls -s` flips to 512 only under
  `POSIXLY_CORRECT`. Three tools, three block conventions; the invariant is
  `%b × %B` = bytes on disk.
- **`%C` errors on non-SELinux systems.** On a plain Debian/Ubuntu kernel it
  fails with `stat: failed to get security context ...: No data available`
  and exit 1 — not an empty string. Guard it: `stat -c '%C' f 2>/dev/null ||
  echo -`.
- **Birth time is best-effort.** `%W` returns `0` for "unknown"
  (indistinguishable from 1970-01-01); `%w` returns `-`. Support needs
  Linux ≥ 4.11 (statx) *and* a cooperative filesystem; never build logic
  that assumes btime exists.
- **ctime is not creation time.** Rename, chmod, chown, or a new hard link
  all bump ctime while mtime stays put — timestamp-only tamper checks miss
  metadata surgery, and `touch -d` cannot forge ctime at all.
- **Neither `-t` nor the pretty Device line is a stable interface.** The
  `-t` column set and the Device rendering (`803h/2051d` vs `major,minor`)
  have both changed across releases; parse `%Hd`/`%Ld` and pinned `-c`
  formats only.
- **/proc and /sys lie about size.** Many procfs files show `Size: 0` while
  reading them yields data; `stat -c %s` is useless there — read the file.
- **Multiple operands keep going.** `stat a missing b` prints what it can,
  errors on the miss, and exits 1 at the end — loop-scripts must check the
  exit code, not assume all-or-nothing.
- **Portability is by name only.** BSD/macOS `stat` uses `-f` for *format*
  (not filesystem) and has different sequences entirely; BusyBox stat
  supports a small subset. `%m`, `%C`, `--printf`, and `--cached` are GNU
  extensions. Anything shipped off Linux needs its own test pass.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Every operand was statted and the format parsed |
| 1 | Usage error, bad format string, or any operand failed (`cannot statx 'x': No such file or directory`) — reported after remaining operands are processed |

## Related Commands

- [`ls`](./ls.md) — the human-facing listing of the same inode data; never parse it, stat instead.
- [`du`](./du.md) — directory-wide allocated-space aggregates; the usage side of `stat -c %b`.
- [`df`](./df.md) — fleet-wide filesystem capacity, the layout-level twin of `stat -f`.
- [`touch`](./touch.md) — the tool that can (and cannot) forge which timestamps.
- [`ln`](./ln.md) — why the `Links:` column and `%h` look the way they do.
- [`readlink`](./readlink.md) — symlink-chain resolution for when `%N`'s one hop is not enough.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [find](../../shell/find.md) — `find -printf` speaks stat's format language over whole trees.
- [man pages](../../reference/man-pages.md) — where `stat(1)` and `statx(2)` are documented.

## Interview Questions

### Q: Walk through mtime, ctime, atime, and btime. Which does chmod change, and which can touch forge?

mtime records data modifications, ctime records any inode change (mode,
owner, link count, rename, and writes too), atime records reads, and btime
records creation. `chmod file` bumps ctime only; `touch` can set atime and
mtime arbitrarily but neither ctime nor btime — the kernel maintains ctime,
and btime is set once by the filesystem. That is why a forged mtime
(antidating a file) still leaves a ctime trail, a fact every forensic
checklist relies on.

### Q: How do you get a file's creation time on Linux, and when does that fail?

Via `stat -c %w` (or `%W`), which since the statx syscall (kernel 4.11, 2017)
can surface the filesystem's birth-time field. It fails — printing `-` or
`0` — when the kernel predates statx, or the filesystem does not track btime
(procfs, sysfs, many network filesystems), and results differ across NFS
servers. Because `%W` uses 0 for "unknown", which collides with the actual
Epoch, scripts must treat 0 as missing data rather than a date.

### Q: Why do scripts prefer `stat -c` over parsing `ls -l`?

`stat` reports one inode per invocation with a format you pin down to
delimiters and precision — no column wrapping, no locale collation, no
quoting-style surprises, and no dependence on how many entries happen to
exist. `ls -l` output is formatted for humans and changes shape with tty vs.
pipe, locale, and coreutils version. `stat` also costs one syscall per
operand instead of a directory scan, and `%Y`-style epoch fields make
arithmetic trivial in shell.

### Q: A file reports 1 GB from `stat -c %s` but occupies 8 KB of disk. Explain, and how do you copy it safely?

`%s` is `st_size`, the apparent size — how many bytes the file's logical
address space spans. Disk usage is `st_blocks × 512`, and a sparse file has
holes that were never written, so a few pages of allocation can back a 1 GB
size; `truncate -s 1G` produces the pure case with `%b=0` — zero blocks
allocated. Plain `cp` preserves sparseness by default (`--sparse=auto`);
`--sparse=never` materializes the full 1 GB, and `--sparse=always` tries to
recreate holes. `du` and `stat -c %b` agree on allocation; `ls -l` and `%s`
agree on apparent size — four tools, two different truths.

### Q: What does `stat -f` tell you that `df` doesn't, and vice versa?

`stat -f` answers "what are the filesystem facts for the filesystem *under
this exact path*" — type (`%T`), free blocks available to non-root (`%a`),
free inodes (`%d`), max filename length — taking any file operand, which
makes it ideal for per-path branching inside scripts. `df` answers
"inventory every mounted filesystem" — all mount points at once, with
human units and totals. In a script checking "can I write 5 GB here?",
`stat -f -c %a` on the target path is the one-shot tool; for a dashboard
of the whole machine, `df`.

### Q: A script that parsed `stat -t` broke after a distro upgrade. What happened and what is the fix?

Terse mode is a convenience format whose column layout has shifted across
coreutils releases and whose trailing context field exists only on SELinux
systems — so column positions are not an interface. The fix is to stop
parsing `-t` and pass an explicit `-c FORMAT` with exactly the fields,
order, and delimiters the script needs; that output is contractual across
versions. The same lesson applies to the default report's Device line,
whose rendering also changed between releases.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/stat.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
