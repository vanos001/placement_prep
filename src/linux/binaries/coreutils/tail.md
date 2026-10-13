# tail — print the last lines or bytes of each file and follow growth

## Overview

`tail` copies the end of each input to standard output: by default the last
10 lines, or a caller-chosen number of lines or bytes. Its second life — and
the reason most people know it — is `-f`/`-F` "follow mode": tail keeps
running after printing the requested region and emits appended data as the
file grows, which makes it the default tool for watching logs.

It is the back-half of the head/tail pair — [`head`](./head.md) takes the
top, `tail` takes the bottom — and it has an extra, asymmetric trick: with a
*positive signed* count, `-n +K` prints **from line K to the end**, turning
tail into "skip the first K-1 lines", the standard way to strip headers in
shell pipelines. It is often confused with `head` (whose negative counts do
the mirror job) and with `less +F` (an interactive follower you must quit);
the sharpest confusion is `-f` vs `-F`, whose difference only shows during
log rotation — the single most probed tail interview question.

| Field | Value |
|---|---|
| Package | Debian `coreutils` (bookworm; Essential package) |
| Upstream | GNU coreutils |
| Section (man) | 1 |
| Path | `/usr/bin/tail` |
| First appeared / lineage | Classic AT&T UNIX utility (1970s); GNU implementation shipped in fileutils, merged into GNU coreutils (2003) |
| Standards | POSIX.1-2018 mandatory utility (`-n`, `-c`, `-f`, `+K` marked obsolescent) |

## Synopsis

```
tail [OPTION]... [FILE]...
```

Common forms:

```
tail file                    # last 10 lines
tail -n 25 file              # last 25 lines
tail -n +25 file             # from line 25 to the end (skips 24 header lines)
tail -f app.log              # print last 10 lines, then follow growth
tail -F app.log              # follow by NAME: survives rotation/re-creation
tail -f app.log --pid=$PID   # follow until the given process dies
```

## How It Works

### Count semantics: the sign is the mode

`tail` takes one count: lines (`-n`) or bytes (`-c`). A leading `+` is where
it differs from every other coreutils filter:

```
              ┌────────────────────────────────────────────────┐
              │  tail -n K / tail -c K — what is printed       │
              ├────────────────────────────────────────────────┤
              │  K > 0:   last K units                         │
              │            tail -n 3   → final 3 lines         │
              │            tail -c 512 → final 512 bytes       │
              │                                                │
              │  K < 0:   all but the last |K| units (GNU)     │
              │            tail -n -3  → same as -n 3 here     │
              │            tail -c -3  → all but final 3 bytes │
              │                                                │
              │  K > 0 with '+':  from unit K to the END       │
              │            tail -n +3  → lines 3,4,5,...       │
              │            tail -c +3  → bytes 3,4,5,...       │
              │            tail -n +1  → the whole file        │
              │            tail -n +11 beyond EOF → empty, 0   │
              │                                                │
              │  Mirror:  head -n -K = "all but last K"        │
              └────────────────────────────────────────────────┘
```

Verified on a 10-line file:

```bash
$ seq 1 10 > ten.txt
$ tail -n -3 ten.txt        # last 3 lines
8
9
10
$ tail -n +3 ten.txt | tr '\n' ' '   # from line 3 to the end — skip 2 lines
3 4 5 6 7 8 9 10
$ tail -c +20 ten.txt       # byte 20 onward (bytes are 1-based)
0
$ tail -n +11 ten.txt; echo "rc=$?"   # past EOF: empty output, success

rc=0
```

The `+K` form is `1`-based and *inclusive*: `-n +3` starts **at** line 3,
because POSIX defines it as "skip K-1 lines". Off-by-one errors here are the
most common tail bug in scripts; `-n +1` (print everything) is the mnemonic
anchor.

### How the last K lines are found

For a seekable input (regular file), GNU `tail` does not read the file
linearly: it seeks near the end, reads a block, counts newlines, and backs up
block by block until it has K of them — cost proportional to the tail, not
the file. Non-seekable input (pipes, FIFOs) forces a different strategy:
tail streams everything through a fixed-size ring buffer, so `tail -n 1000
huge.log` is cheap while `cat huge.log | tail -n 1000` pays full I/O plus
buffering.

### Follow modes: -f, -F, and the rotation problem

`-f` (long form `--follow`) has two flavors:

- `-f`, `--follow=descriptor` (default): tail keeps the **file descriptor**
  it opened and polls its end. If the file is renamed, the fd is still valid,
  so tail keeps following the *old inode* — it will happily print appends to
  `app.log.1` after rotation, and never see the new `app.log`.
- `-F` = `--follow=name --retry`: tail tracks the **name**. It reopens the
  path when it has been renamed/removed/recreated, and it tolerates the file
  not existing at startup.

Verified behavior — `-f` across `mv`:

```bash
# tail -f across rotation: appends to the RENAMED file still appear; the NEW f.log is ignored
$ timeout 6 tail -n 2 -f f.log
line1
line2
app1          # append detected while file was under its original name
old3          # append to f.log.1 AFTER mv — descriptor follow keeps the inode
```

Verified behavior — `-F` across rotation and late creation (and the contrast
with plain `-f`, which refuses a missing file at startup):

```bash
# -F started BEFORE h.log exists: warns, keeps waiting, picks it up
$ timeout 7 tail -n 5 -F h.log
tail: cannot open 'h.log' for reading: No such file or directory
tail: 'h.log' has appeared;  following new file
h1

# -F running when r.log is replaced mid-watch
$ tail -n 5 -F r.log
r1
r2
r4-oldfile                              # brief window: append to old inode
tail: 'r.log' has been replaced;  following new file
r3-newfile                              # now reading the replacement
```

Plain `-f` is different — started on a file that does not exist, it fails
immediately rather than waiting:

```bash
$ tail -f /tmp/nonexistent-xyz.log
tail: cannot open '/tmp/nonexistent-xyz.log' for reading: No such file or directory
tail: no files remaining          # exit status 1
```

Detection mechanics: on Linux, GNU `tail` uses **inotify** watches (file
and, for `-F`, the directory) so appends are reported without busy polling.
Where inotify is unavailable — unusual kernels, some sandboxes — it falls
back to a sleep loop: wake every `-s` seconds (default 1.0), compare sizes,
and for `--follow=name` reopen the path after `--max-unchanged-stats`
iterations (default 5) of no size change — the reason a rotated file can
take several seconds to be picked up on systems where the inotify path is
not active. Truncation is handled in both modes — the mechanism that makes
copytruncate-style rotation work:

```bash
$ truncate -s 0 u.log && printf 'c1\n' >> u.log   # while tail -f u.log runs
tail: u.log: file truncated
c1
```

### --pid: bounded following

`--pid=PID` makes tail exit once process PID is gone; tail checks PID at
least once per `-s` interval. This is the clean way to bound a follow inside
a script — no `timeout`, no killing, tail exits 0 on its own:

```bash
# Verified: tail prints the last 2 lines, waits, exits 0 when the
# background sleep (pid $P) dies ~3 s later.
$ sleep 3 & P=$!
$ tail -n 2 -f --pid=$P p.log; echo "tailrc=$?"
p1
p2
tailrc=0
```

`--pid` may be repeated to watch several processes; tail exits when all of
them are gone. Without `-f` (or `--follow`/`--retry`), `--pid` is ignored.

### Multiple files and headers

With more than one operand, output switches to header-per-file mode — for
the initial slice and continuously in follow mode:

```bash
$ tail -f ten.txt /etc/hostname
==> ten.txt <==
1
2
...
==> /etc/hostname <==
c-6ac89cf4-14810412-394312c537f8
```

`-q` suppresses headers, `-v` forces them even for one file; in follow mode
the header is re-emitted whenever the watched set changes (a `-F` rotation
re-announces the file).

## Options That Matter

| Option | Effect |
|---|---|
| `-n K`, `--lines=K` | Last K lines; `+K` prints from line K to the end; `-K` all but last K |
| `-c K`, `--bytes=K` | Last K bytes; `+K` from byte K (1-based) to the end; no line awareness |
| `-f`, `--follow[=descriptor]` | Follow the open file descriptor; keeps following a renamed file |
| `-F` = `--follow=name --retry` | Track the path: survive rotation, wait for late files, keep retrying inaccessible ones |
| `--pid=PID` | Exit automatically once PID is gone; repeatable; exit status 0 |
| `-s N`, `--sleep-interval=N` | Poll cadence in fallback mode (default 1.0 s); also the `--pid` check interval |
| `--max-unchanged-stats=N` | With `--follow=name`, reopen after N (default 5) unchanged size checks; rarely useful when inotify is active |
| `-q`, `--quiet`, `--silent` / `-v`, `--verbose` | Never / always print `==> file <==` headers |
| `-z`, `--zero-terminated` | Units are NUL-separated records instead of newline lines |

## Usage Patterns

```bash
# See how a service failed: the end of the log is where the crash lives
$ tail -n 50 /var/log/daemon.log
```

```bash
# Strip a CSV/JSON header before concatenating — the canonical +K idiom
$ tail -n +2 part1.csv > merged.csv && tail -n +2 part2.csv >> merged.csv
```

```bash
# Last 1000 lines of a huge file: seekable input, cost = the tail only
$ tail -n 1000 /var/log/huge.log

# Same on a STREAM: cat must deliver everything; tail rings last 1000 in RAM
$ cat huge.log | tail -n 1000
```

```bash
# Last KiB of a binary (e.g. appended metadata block)
$ tail -c 1K disk.img | od -A x -t x1z | tail -n 4
```

```bash
# Bounded follow inside a script: -F + --pid ends cleanly when the worker exits
$ some_worker & WPID=$!
$ tail -n 5 -F worker.log --pid=$WPID
```

```bash
# Skip everything up to and including a marker line: find its number, then +K
$ tail -n +$(($(grep -n '^## Section 4' manual.txt | cut -d: -f1) + 1)) manual.txt
```

## Nuances and Gotchas

- **`-f` vs `-F` is a rotation question.** With `-f`, after `mv app.log
  app.log.1` tail keeps reading the old inode — "live" output is silently a
  dead file. With logrotate's rename-based schemes use `-F`; `copytruncate`
  is the exception where plain `-f` suffices, because the inode never changes.
- **Exit-on-delete trap.** If the followed file is deleted (`rm`, not
  rotation), a `-f` tail keeps holding a valid fd to the orphaned inode —
  it follows forever, silently. `-F` notices and keeps retrying the name;
  a *startup* on a missing file is the one case plain `-f` refuses
  (`tail: ... no files remaining`, exit 1).
- **Stale-offset fragments after truncate+grow.** If a copytruncated log is
  rewritten faster than tail's next size check, tail may only observe growth
  and read from its old offset — printing a *fragment* of the new content
  (observed: appending to a truncated file made tail emit `trunc`, the tail
  of `after-trunc`). Pure truncation without intervening writes is detected
  cleanly (`tail: file: file truncated`).
- **`+K` is 1-based and inclusive.** `tail -n +2` skips exactly one line.
  Off-by-one header bugs come from mentally reading it as "skip 2". Negative
  `K` (`-n -3`) is a GNU extension; POSIX only blesses `+K` (obsolescent)
  and plain counts.
- **`--pid` without `-f` does nothing.** `tail --pid=$X file` alone just
  prints and exits; the flag is defined relative to following. Exit status
  is 0 when the watched PID dies — do not confuse that with "everything read".
- **Downstream consumers can kill your follow.** `tail -f log | grep -m1
  needle` ends the pipeline when grep exits; tail then dies of SIGPIPE
  (silently) — a monitoring one-liner that "randomly stops" is usually this.
- **Ring-buffer memory on pipes.** `tail -n 2000000` on a non-seekable input
  keeps ~2M lines resident; on a regular file the same request costs a few
  block reads. Redirect or process in place when memory matters.
- **BusyBox/minimal tails are a subset.** Alpine-style BusyBox `tail`
  supports the core `-n`/`-c`/`-f` but not every GNU flag (`--pid`,
  `--retry`, `-v` semantics and multi-file follow behavior differ). Check
  `tail --help` in the container image before scripting against it.
- **`-q`/`-v` change framing, not content.** Add a second operand or `-v`
  and your output suddenly contains `==> file <==` lines that break naive
  parsers downstream.
- **`tail -f` never ends on its own.** Scripts that forget `--pid`,
  `timeout`, or a killing consumer leak a tail process per run; in CI this
  is the classic "job hangs until timeout" cause.

## Exit Status

| Status | When |
|---|---|
| 0 | Slice printed (even for `+K` beyond EOF, which yields no output), or `--pid`'s process exited normally |
| 1 | Any operand could not be opened/read, invalid count, or — in follow mode — all watched files vanished (`tail: no files remaining`) |
| 141 | tail itself killed by SIGPIPE because a downstream consumer (e.g. `grep -m`) exited first |

## Related Commands

- [`head`](./head.md) — the mirror operation; its `-n -K` is the counterpart of tail's `-n +K`, and together they make cheap middle slices.
- [`cat`](./cat.md) — the whole-stream version of the same job; `tail` exists because the interesting end usually needs no full read.
- [`wc`](./wc.md) — line/byte totals; the arithmetic partner when a script computes a `tail -n +K` skip from a marker line.
- [`stdbuf`](./stdbuf.md) — fixes buffering on the *other* side of `tail -f app | grep ...` pipelines so live output stays live.
- [`grep`](../../shell/grep.md) — the standard downstream filter for followed logs; needs `--line-buffered` to preserve tail's latency.
- [`bash`](../../shell/bash.md) — pipeline/SIGPIPE and `PIPESTATUS` semantics that govern every `tail -f | ...` construction.
- [Overview — GNU Coreutils collection](./overview.md) — hub page for the collection.

## Interview Questions

### Q: What is the difference between `tail -f` and `tail -F`?

`-f` follows the file *descriptor*: tail keeps the inode it opened, so after
logrotate renames the file it continues reading the renamed (now inactive)
file and never sees the new one. `-F` follows the *name*: it re-checks the
path, tolerates the file missing at startup (`--retry` semantics), and
switches to the replacement, printing `has been replaced; following new
file`. Rule of thumb: `-f` for files nothing rotates, `-F` for anything
logrotate manages.

### Q: Your `tail -f app.log` shows nothing new after 10 minutes, but the app is logging. Diagnose.

First suspect rotation: if the app's writes are going to a freshly created
`app.log`, a `-f` tail is still attached to the old inode — switch to `-F`
and the missing lines appear immediately. Second suspect: copytruncate-style
truncation the follow has not re-detected yet. Third, the consumer side: a
downstream `grep -m` or pager exiting kills tail via SIGPIPE; `lsof` will
confirm which file tail's fd actually points at.

### Q: Explain `tail -n +5 file`. Why does it start at line 5, and what is the symmetric head idiom?

The `+K` form means "output from unit K to the end", units being 1-based, so
`-n +5` skips the first four lines — POSIX describes it as skipping K-1
lines, and `tail -n +1` is the whole file. The symmetric GNU head extension
is negative: `head -n -5` prints all but the last five lines. head has no
`+K` form and tail does, because "start at line K" only makes sense from the
top of a stream.

### Q: How do you make a `tail -f` inside a script exit deterministically?

Use `--pid=$PID`: start the producer, capture its PID, run
`tail -f --pid=$PID log`, and tail exits with status 0 once that process is
gone — verified behavior, no `kill` or `timeout` needed, and `--pid` may be
repeated to wait out several processes. Alternatives have sharp edges:
`timeout N tail -f` imposes an arbitrary wall clock, and piping into `grep
-m1` terminates tail via SIGPIPE at a data-dependent moment. Also remember
`--pid` requires `-f`/`--follow`/`--retry` to mean anything.

### Q: What does tail do when the file it is following is truncated, and why does logrotate's copytruncate work at all?

Tail compares the file size against its current read offset on every check
(or receives the inotify event); when the file shrank below its offset it
prints `tail: file: file truncated`, rewinds to the new end, and keeps
following — so copytruncate rotation, which zeroes the same inode the app
holds open, requires no tail restart. The subtle failure mode is
truncate-plus-fast-rewrite: if the app appends before tail observes the
shrink, tail may read from its stale offset and emit a fragment of a new
line instead of a clean boundary.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/tail.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
