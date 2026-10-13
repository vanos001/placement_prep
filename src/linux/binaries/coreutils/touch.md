# touch — change file timestamps (and create empty files)

## Overview

`touch` sets a file's access time (atime) and/or modification time (mtime) — to the current time, to a parsed date string, or to another file's times. As a side effect of its most common invocation it also *creates* empty files, which is why `touch file` is the universal shell idiom for making markers, lock files, and placeholders. Under the hood it is a thin wrapper over `utimensat(2)`, giving it nanosecond-precision control over exactly two of an inode's four timestamps. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/touch`.

The two halves of `touch`'s personality matter in different jobs. As a timestamp editor it drives build systems (`make` rebuilds what is newer than its inputs), test fixtures (deterministic mtimes for reproducible archives), and atime experiments. As a file creator it is the cheapest way to assert "this path exists now" — cheaper and safer than `> file` because it never clobbers and can be told not to create with `-c`. What `touch` can never do is set the *status change time* (ctime) — the kernel updates that itself on every metadata write — which makes sloppy backdating detectable.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/touch |
| First appeared | Version 7 AT&T UNIX (1979) |
| Standards | POSIX.1-2018 (`touch`); `-d`, `-h`, `--time` are GNU extensions; `-f` accepted and ignored |

## Synopsis

```
touch [OPTION]... FILE...
```

One line per mode:

```
touch FILE...                    # set atime+mtime to now; create if missing
touch -c FILE...                 # ...but never create (-c: no-create)
touch -d STRING FILE...          # GNU date string: 'yesterday', '@1700000000'
touch -t [[CC]YY]MMDDhhmm[.ss] FILE...   # POSIX timestamp format
touch -r REF FILE...             # clone REF's atime and mtime
```

## How It Works

### The four timestamps

An inode carries four times. `touch` can write exactly two of them:

| Time | Meaning | Settable by touch? |
| --- | --- | --- |
| atime | last **a**ccess (read) | yes (`-a`) |
| mtime | last **m**odification (data write) | yes (`-m`) |
| ctime | last inode **c**hange (metadata: mode, size, links, times) | no — kernel-managed |
| btime | file **b**irth (creation) | no — kernel/filesystem-managed |

The ctime rule is the security-relevant one: any successful `touch` bumps ctime to *now*, because changing atime/mtime is itself an inode change. `stat` exposes it as `%z` — a backdated file still wears the fingerprint of when it was touched.

### The syscall and the two permission rules

Modern GNU `touch` calls `utimensat(2)` (or `futimens`), which accepts nanosecond-resolution timespecs — the days of 1-second `utime(2)` granularity are gone on Linux. Who may touch what follows POSIX:

- Setting times to the **current time** requires only **write permission** on the file (that is what any writer would do anyway).
- Setting times to an **arbitrary value** requires **ownership** of the file (or appropriate privilege). This stops users with write-only access from rewriting history.

For symlinks, `touch` follows the link by default; `-h`/`--no-dereference` (with kernel support via `utimensat`'s `AT_SYMLINK_NOFOLLOW`) alters the link's own timestamps, on filesystems that keep them.

### Creating files

Without `-c`, `touch` creates any missing operand with `open(O_CREAT)`, mode `0666` filtered by your umask, then closes it without writing a byte. The result is an empty regular file owned by you, timestamped now. With `-c` the `O_CREAT` flag is dropped: existing files are updated, missing operands are silently skipped *and are not an error* (exit status stays 0). That asymmetry is the basis of the `-c` idiom for idempotent scripts and typo safety.

### The three time specifications

```
-t 202401151200.30      strict POSIX format: [[CC]YY]MMDDhhmm[.ss]
                        → 2024-01-15 12:00:30 local time
-d '2024-01-15 12:00'   GNU date parser: ISO 8601, '3 days ago',
                        'next monday', '@1700000000' (epoch seconds)
-r other.dat            copy atime AND mtime from the reference file
```

`-t` is fixed-format and interpreted in the **local timezone** (no timezone field exists in the format); two-digit years map into the 1969–2068 window per POSIX. `-d` accepts the same flexible grammar as GNU `date` — relative offsets, English weekday names, ISO timestamps, and the `@epoch` form — which makes it the better choice for scripts that already speak `date(1)`. `-r` is the "timestamps are data" idiom: it transfers both times in one call, exactly what you want after reconstructing a file whose content you restored by other means.

### Which time gets changed?

```
              no flags ──────────► set atime AND mtime = now
             /
 touch ─────┤── -a ────────────► set atime only
             \
              ├── -m ───────────► set mtime only
              \
               └── -d/-t/-r ────► same targets, but that value instead of now

 ALWAYS, any successful call:      ctime ← now   (kernel, not settable)
 file did not exist?               create it (unless -c, then skip silently)
```

The ctime line is worth a second read: it is unconditional. There is no flag combination that leaves ctime alone, because the kernel considers a changed atime/mtime an inode change — this is a kernel behavior, not a `touch` implementation choice.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a` | Change only the access time (atime) |
| `-m` | Change only the modification time (mtime) |
| `-c`, `--no-create` | Never create files; missing operands are not an error |
| `-d`, `--date=STRING` | Parse STRING (GNU `date` grammar, incl. `@epoch`) instead of now |
| `-t STAMP` | POSIX format `[[CC]YY]MMDDhhmm[.ss]` instead of now |
| `-r`, `--reference=FILE` | Use REF's atime and mtime instead of now |
| `--time=WORD` | Choose the time: `access`/`atime`/`use` or `modify`/`mtime` (long forms of `-a`/`-m`) |
| `-h`, `--no-dereference` | Affect the symlink itself, not its target |
| `-f` | Accepted and silently ignored (BSD compatibility) |

Passing neither `-a` nor `-m` changes both times. `--time=access,--time=mtime` in one invocation is how GNU parses a combined request, but the flags are clearer.

## Usage Patterns

```bash
# The classic: create an empty file (lock files, flags, .gitkeep)
touch /tmp/deploy.lock
```

```bash
# Idempotent scripts: update if present, never create, never fail on absence
touch -c /var/run/worker.pid
```

```bash
# Force make to rebuild a target by making its input "newer"
touch src/parser.y
```

```bash
# POSIX -t format: backdate a fixture (local time; note the .30 seconds part)
touch -t 202401312359.30 testdata.log
```

```bash
# GNU -d strings: ISO, relative, and epoch forms
touch -d '2024-01-15 12:00:00' a.txt
touch -d '3 days ago' b.txt
touch -d '@1700000000' epoch.bin
```

```bash
# Set only the access time (simulate an old read without touching mtime)
touch -a -d '2024-02-01 09:00' report.pdf
```

```bash
# Clone both timestamps from a reference file after reconstructing content
touch -r original.dat restored.dat
```

```bash
# Mark every header as changed before a forced full rebuild
find src -name '*.h' -exec touch {} +
```

```bash
# Deterministic mtimes for reproducible test archives (CI-friendly: UTC epoch)
find fixtures -type f -exec touch -d '@1577836800' {} +
tar --sort=name -cf fixtures.tar fixtures/
```

```bash
# Touch the symlink itself rather than its target (where the fs supports it)
touch -h mylink
```

```bash
# Age out everything in a staging dir for retention testing
touch -d 'last year' staging/*
```

```bash
# Guard a create-on-demand path so a typo cannot silently make a stray file
touch -c "$CONFIG_DIR/app.conf" || exit 1
```

```bash
# Normalize two files' times before a timestamp-sensitive sync/diff test
touch -r expected.bin actual.bin
```

```bash
# Blank out atime noise before measuring what a workload really reads
find /srv/dataset -type f -exec touch -a -d '@0' {} + && run_benchmark
```

Verified behavior for the time formats (from `stat -c %y`):

```
$ touch -t 202401151200 f && stat -c '%y' f
2024-01-15 12:00:00.000000000 +0000
$ touch -d '@1700000000' f && stat -c '%y' f
2023-11-14 22:13:20.000000000 +0000
$ touch -a -d '1999-12-31 23:59:59' f && stat -c 'atime=%x mtime=%y' f
atime=1999-12-31 23:59:59.000000000 +0000 mtime=2023-11-14 22:13:20.000000000 +0000
```

## Nuances and Gotchas

- **Backdating is always visible.** ctime moves to *now* on every touch, and birth time cannot be set at all. Forensics lesson, interview favorite: `stat` (`%z`, `%w`) exposes files whose mtime claims 1995.
- **`-f` is a no-op in GNU touch.** It exists only so BSD-era scripts keep running. Other implementations give `-f` real meaning, so scripts that "worked because of it" break silently in port — never rely on it.
- **Future timestamps poison incremental tools.** `touch -d tomorrow` makes `make` treat the file as perpetually newer than everything, `tar` warns `file is in the future`, and `rsync` may re-transfer until time catches up. Undo with `touch file` (reset to now).
- **`-t` and `-d` interpret local time.** The same command yields different absolute times in different TZ environments — a classic nondeterminism source in CI. For anything machine-consumed, prefer `-d '@<epoch>'` (UTC by construction).
- **`-c` changes the error contract.** Without it, a missing file in a nonexistent directory is an error (exit 1); with it, absence is success (exit 0). Scripts checking exit status of `touch` must know which mode they are in.
- **Permission rules differ by mode.** Touching to *now* needs write permission; touching to an *arbitrary* time needs ownership. A user who can write a file cannot backdate it — which is the point.
- **Filesystem granularity lies.** FAT/exFAT store mtimes with 2-second resolution; network filesystems may round or drop nanoseconds; some filesystems reject pre-epoch or far-future times. Verify with `stat`, not `ls`.
- **relatime and atime.** Under the default `relatime` mount policy, *reads* update atime only under conditions (once per day, or when atime was older than mtime/ctime) — but an explicit `touch -a` always writes the value you asked for.
- **`touch -` touches stdout's file.** GNU `touch` treats a lone `-` operand as "the file behind standard output" — surprising in pipelines where stdout is a redirect, harmless elsewhere.
- **BusyBox/BSD differences.** BusyBox `touch` supports the common flags but historically lacks some GNU extensions (`-d` relative strings may be missing); BSD/macOS `touch` uses different `-d` grammar entirely. Portable scripts stick to `-a`, `-m`, `-c`, `-r`, `-t`.
- **Symlink timestamp support is uneven.** `-h` depends on both kernel (`AT_SYMLINK_NOFOLLOW`) and filesystem storing link times; on many filesystems (procfs, some network fs) it fails. Test on the target fs, not in theory.
- **Timestamps can outlive their filesystem.** Copying (without `-p`), extracting archives, or moving across filesystems regenerates times — but `mv` within one filesystem is a rename and *keeps* mtime. When a "same file" mysteriously has a fresh mtime, check whether something copied rather than renamed it.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All operands updated or created — including missing files when `-c` was given |
| 1 | Any operand failed: nonexistent directory, permission denied, bad date string |

Verified: `touch /no/such/dir/x` exits 1; `touch -c /no/such/dir/x` exits 0.

## Related Commands

- [`sync`](./sync.md) — flushing metadata to storage after metadata writes.
- [`truncate`](./truncate.md) — the other "modify a file in place without opening an editor" tool.
- [`date`](./date.md) — the parser behind `-d`; convert epoch↔human there first.
- [`stat`](./stat.md) — reads exactly the times `touch` writes (`%x`, `%y`, `%z`, `%w`).
- [`ls`](./ls.md) — displays and sorts by these timestamps (`-t`, `--full-time`).
- [`cp`](./cp.md) — `-p`/`-a` preserve timestamps; `touch -r` restores them.
- [`find`](../../shell/find.md) — `-newer`, `-mmin`, `-atime` predicates consume the same clock.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.

## Interview Questions

### Q: What are the four file timestamps, and which of them can `touch` set?

atime (last read), mtime (last data modification), ctime (last inode status change — mode, links, size, *or the other two times*), and btime (birth/creation, exposed by `statx` on modern kernels). `touch` sets atime and/or mtime only. ctime is kernel-managed and moves to now on any metadata write — including a touch itself — so backdating is always detectable via `stat -c %z`. btime is filesystem-managed and immutable; copying a file yields a new inode with a *new* birth time.

### Q: You find a file with mtime `1995-01-01` but ctime of ten minutes ago. What happened?

Someone ran `touch -d`/`touch -t` (or `utimensat` from a program) on it recently. Setting atime/mtime is itself an inode change, so ctime was stamped with the moment of the touch — it cannot be faked from userspace. This is the standard way to detect tampering or "evidence preparation" in an image, and the reason scripts that replay archive timestamps (`touch -r`) still leave a ctime trail. Bonus: birth time, where available, also tells the true creation story.

### Q: Why do scripts use `touch -c` instead of plain `touch`?

Two reasons. Idempotency: a rerun of the script must not create files that a previous step decided not to — `-c` makes absence a no-op. Typo safety: plain `touch "$CONGIG_FILE"` happily creates a misspelled file and returns 0; with `-c` the same typo exits 1 (the parent directory of a *typo'd name in an existing dir* still succeeds, but a wrong path fails), and more importantly no phantom file appears. In short: plain `touch` when creation is intended; `-c` when only restamping existing files is intended.

### Q: How does `make` decide what to rebuild, and how does `touch` manipulate it?

`make` compares the mtime of each target against its prerequisites: if any prerequisite is newer than the target, the target rebuilds. `touch` a prerequisite and every dependent target becomes out of date — the standard "force a full rebuild of this subtree" move (`find src -name '*.h' -exec touch {} +`). The flip side: an accidental future-dated file (clock skew, restored archive) keeps everything "up to date" incorrectly or loops `make` forever, which is why `touch file` to reset to now is part of every build troubleshooter's toolkit.

### Q: What is the difference between `touch -t 202401151200.30` and `touch -d '2024-01-15 12:00:30'`?

`-t` is the POSIX fixed format `[[CC]YY]MMDDhhmm[.ss]` — rigid, terse, no timezone field, interpreted in local time, two-digit years folded into 1969–2068. `-d` is the GNU extension: free-form strings parsed by the same engine as GNU `date` — ISO 8601, relative (`'2 hours ago'`), weekday names, and `@<epoch>` for raw seconds. Use `-t` for POSIX-portable scripts and `-d '@epoch'` when you need TZ-independent determinism; use human `-d` strings for interactive work.

### Q: A hardlinked pair of files — do they share timestamps? What about after touching one?

Hard links are one inode with several names, so atime/mtime/ctime/btime are shared by construction; touching one name "touches" all of them. This is a favorite debugging trap: restamping one path in a link farm restamps its twins, and `find -newer` results then look inconsistent because two "different" files always share times. Check with `stat -c '%i %y' file1 file2` — equal inode numbers explain equal times.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/touch.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — touch](https://pubs.opengroup.org/onlinepubs/9699919799/)
