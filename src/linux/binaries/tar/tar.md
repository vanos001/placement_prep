# tar — create, list, and extract archive files

## Overview

`tar` (tape archive) bundles a set of files and directory trees into a single stream — originally for magnetic tape, today for tarballs, source releases, container image layers, and pipe-to-ssh transfers. It is the oldest archiver still in daily use on Unix: the streaming container format and the mode-based CLI (`-c` create, `-x` extract, `-t` list) have been stable since Seventh Edition UNIX in 1979, which means every tar invocation you write is readable by an admin from any decade.

Debian ships it in the `tar` package (Priority: required) at `/usr/bin/tar`, with `/bin/tar` provided through the usrmerge. The GNU implementation is what Linux distributions carry; `bsdtar` (libarchive) is the common alternative on macOS and FreeBSD and reads GNU archives, but its option semantics differ in several traps documented below.

`tar` is often confused with `zip` (compresses and archives in one container with random access; tar archives alone are uncompressed streams), with `cp -a` (copies trees but not into one portable file), and with `rsync` (network delta sync rather than a self-contained archive). Compression is a layer *around* the tar stream: `gzip`/`gunzip`, `bzip2`, `xz`, and `zstd` are separate tools that tar can invoke for you.

| Field | Value |
| --- | --- |
| Package | tar (Debian; Priority: required) |
| Man section | 1 |
| Path | /usr/bin/tar |
| First appeared | AT&T UNIX, Seventh Edition (1979) |
| Standards | POSIX.1-2018 (`tar` utility), ustar/pax archive formats; GNU extensions beyond |

## Synopsis

```
tar [OPTION]... [FILE]...
```

The operational mode is expressed by one leading option letter; everything else modifies it:

```
tar -c [-f ARCHIVE] [OPTIONS] [MEMBER...]   # create an archive
tar -t [-f ARCHIVE] [MEMBER...]             # list contents
tar -x [-f ARCHIVE] [OPTIONS] [MEMBER...]   # extract
tar -r [-f ARCHIVE] [MEMBER...]             # append files to an uncompressed archive
tar -u [-f ARCHIVE] [MEMBER...]             # append only newer than what is archived
tar -d [-f ARCHIVE] [MEMBER...]             # diff archive against filesystem
tar -A [-f TARGET] [-f ADDEND]              # concatenate archives
```

## How It Works

### The mode is the first decision

`tar` is a verb-first program: exactly one operational mode is in effect per invocation, and the same letters mean different plumbing depending on it. This mode table is worth knowing cold:

```
Mode  Option          Reads     Writes    Typical use
----  --------------  --------  --------  ---------------------------
c     --create        fs        archive   tar -cf a.tar dir/
t     --list          archive   stdout    tar -tf a.tar
x     --extract       archive   fs        tar -xf a.tar
r     --append        both      archive   tar -rf a.tar newfile
u     --update        both      archive   tar -uf a.tar dir/
d     --diff          both      stdout    tar -df a.tar dir/
A     --catenate      archives  archive   tar -Af big.tar extra.tar
```

`-r`, `-u`, and `-A` rewrite the archive in place, which is only possible on seekable files — they cannot run on a compressed archive or a pipe.

### Archive anatomy

A tar file is a flat sequence of 512-byte blocks: a header block (name, mode, owner, size, mtime, checksum, type flag), the file data padded to a block multiple, the next header, and so on, terminated by two consecutive zero blocks. The default record size is 20 blocks (`-b 20`), which you can see in this build's compiled defaults:

```
$ tar --show-defaults
--format=gnu -f- -b20 --quoting-style=escape --rmt-command=/usr/sbin/rmt ...
```

Three observations with real consequences hide in that line: the **default archive is `-` (stdin/stdout)** — that is why `tar cf - dir | ssh host tar xf -` works without `-f -`; the **default format is `gnu`**, not POSIX `pax`; and blocking to 20×512 bytes keeps tape and pipe throughput sane. `tar -tvf` prints one line per member with mode, owner/group, size, and timestamp:

```
$ tar -tvf plain.tar
drwxrwxr-x z/z               0 2026-10-09 16:35 src/
-rw-rw-r-- z/z               6 2026-10-09 16:35 src/b.log
-rw------- z/z               6 2026-10-09 16:35 src/a.txt
```

### Creating archives

Member arguments are files or directories; directories are archived recursively by default. The classic layout is `tar -cf archive.tar files...`, and `-C dir` changes directory *at the point it appears* on the command line, which is how you control what the stored member names look like:

```bash
# Store members relative to /var/www: archive contains html/, not var/www/html/
$ tar -C /var/www -cf site.tar html
```

The ordering trap deserves its own example, because modern GNU tar detects it and fails loudly (exit 2):

```bash
$ tar -cf o2.tar sub/c.txt -C src
tar: The following options were used after non-option arguments.  These options
are positional and affect only arguments that follow them.  Please, rearrange
them properly.
tar: -C ‘src’ has no effect
tar: sub/c.txt: Cannot stat: No such file or directory
tar: Exiting with failure status due to previous errors
```

`-C` (and `--exclude`, see below) is **positional**: it affects only operands that follow it. Put options before file operands, or interleave them deliberately — `tar -cf a.tar -C /etc passwd -C /var log` is legal and meaningful.

### Compression: integrated vs piped

For **creation** you must request compression: `-z` (gzip), `-j` (bzip2), `-J` (xz), `--zstd` (zstd, supported by GNU tar 1.31+), or `-a`/`--auto-compress`, which picks the program from the archive filename suffix (`.tar.gz`, `.tgz`, `.txz`, ...). For **reading**, GNU tar auto-detects the compression from the stream's magic bytes — no flag needed:

```bash
$ tar -czf gz.tar.gz src
$ tar -tf gz.tar.gz          # no -z; format recognized on read
src/
src/b.log
```

The pipeline form is equivalent and sometimes preferable when you want a different compressor, a specific compression level, or no intermediate file:

```bash
$ tar -cf - src | gzip -9 > src.tar.gz
$ gzip -dc src.tar.gz | tar -xf -
```

The archive itself never contains compression metadata — a compressed tarball is just `gzip(tar stream)`, which is why `-r`/`-u`/`-A` cannot touch `.tar.gz` files and why corruption in a gzip stream destroys everything after the bad block.

### Extraction rules

`tar -xf` recreates the tree under the current directory using the stored member names. Extraction has permission semantics that depend on who you are:

- **As root**, extraction defaults to `--same-owner --same-permissions`: ownership is restored from the archive, which is what you want for system restores and containers, and a security review point when unpacking anything else.
- **As an ordinary user**, tar defaults to `--no-same-owner` (chown would fail anyway); modes are applied through your umask unless you pass `-p`/`--preserve-permissions`.

Leading slashes are stripped at creation time with a warning — an archive built with `tar -cf a.tar /tmp/tarlab/src` stores members as `tmp/tarlab/src/...`:

```
tar: Removing leading `/' from member names
```

Names with `..` are rejected on extraction by current GNU tar rather than followed, closing the classic path-traversal attack. `--strip-components=N` removes the first N path components on extraction (the `tar -xf linux.tar.xz --strip-components=1` idiom for kernel trees), and `--no-same-owner -m` gives you the "just the content, my metadata" extraction used when validating untrusted archives.

### Pattern matching grammar

GNU tar's wildcard defaults are asymmetric, and this is a reliable interview probe:

- `--exclude` patterns **glob by default**, and a pattern without `/` matches against the end of each member name, so `--exclude='*.log'` strips `src/b.log` even though the full stored name is `src/b.log`:

```bash
$ tar -cf ex.tar --exclude='*.log' src
$ tar -tf ex.tar
src/
src/sub/
src/sub/c.txt
src/a.txt
```

- Member names given to `-t`/`-x` are **literal by default**; a quoted pattern needs `--wildcards`:

```bash
$ tar -tf plain.tar '*.txt'
tar: Pattern matching characters used in file names
tar: Use --wildcards to enable pattern matching, or --no-wildcards to suppress this warning
tar: *.txt: Not found in archive
tar: Exiting with failure status due to previous errors
$ tar -tf plain.tar --wildcards '*.txt'   # works
```

`--wildcards-match-slash` controls whether `*` crosses directory separators (off by default), and `--no-wildcards` makes even exclude patterns literal.

### Rewriting names with --transform

`--transform` takes a `sed`-style `s/regexp/replacement/` expression applied to member names at write time (use `g` to hit nested components), and the transformed names are what `-t` shows:

```bash
$ tar -cf tr.tar --transform 's/^src/renamed/' src/a.txt
$ tar -tf tr.tar
renamed/a.txt
```

This is the clean way to strip, prefix, or relocate top-level directories without staging a copy of the tree.

### Incremental backups: --listed-incremental

`-g/--listed-incremental=SNAPSHOT` implements dump-style levels. The first run (level 0) archives everything and writes a snapshot file recording each file's inode metadata; later runs consult the snapshot and archive only new and changed files, then refresh the snapshot:

```
$ tar -cf i0.tar --listed-incremental=snap src   # level 0: full dump
$ head -1 snap
GNU tar-1.35-2
$ echo changed2 > src/b.log
$ tar -cf i1.tar --listed-incremental=snap src   # level 1: only b.log + dirs
```

Restoring is the part people get wrong: apply the base archive, then each incremental **in order**, passing a throwaway snapshot file (`-g /dev/null`) so tar applies every member instead of diffing against a snapshot you do not have:

```bash
$ tar -xf i0.tar -C restore/
$ tar -xf i1.tar -C restore/ -g /dev/null
```

Aging of directory entries in the snapshot is also how `tar -cf i1.tar ...` knows a directory was *renamed* — the old name appears with a `D`-style deletion marker internally and the extract pass removes it, which is the feature `rsync`-based mirrors do not give you for free.

### Streams: -f - and where -v writes

`-f -` selects stdin/stdout explicitly (it is the compiled default anyway), enabling `tar -cf - . | ssh host 'tar -xf - -C /dest'` migrations with no intermediate file. One consequence surprises scripters: when the archive itself goes to stdout, **verbose listing goes to stderr**, so `-v` never pollutes the stream:

```bash
$ tar -cvf - src 2>/dev/null | wc -c     # pure archive bytes
10240
```

### Security notes: bombs and traversal

Two attack classes to name in an interview. A **tar bomb** is an archive that expands to absurd size or file count (or drops thousands of files into the current directory); defenses are `tar -tf` inspection first, extraction into a fresh directory, and `df`/quota watch dogs on hostile input. **Path traversal** archives carry `../../etc/passwd`-style members or absolute paths; GNU tar strips leading `/` and refuses `..` members on extraction, but older or non-GNU tars have not — so untrusted archives get extracted as an unprivileged user in a throwaway directory, never as root.

Metadata beyond mode/owner is opt-in per class: `--acls` stores POSIX ACLs, `--xattrs` and `--selinux` cover extended attributes, and `-S` preserves sparse-file holes.

## Options That Matter

### Operational modes

| Option | Effect |
| --- | --- |
| `-c` | Create a new archive (truncates an existing archive file) |
| `-x` | Extract; members replace existing files |
| `-t` | List contents; with member names, filters |
| `-r` / `-u` | Append members / append only newer (uncompressed, seekable archives only) |
| `-d` | Compare archive against filesystem; reports differences |
| `-A` | Concatenate archives onto the first |

### Selection and naming

| Option | Effect |
| --- | --- |
| `-f FILE` | Archive name; `-` = stdin/stdout (the compiled default) |
| `-C DIR` | chdir to DIR before the operands that follow (positional) |
| `--exclude=PAT` | Skip matching names (globs by default; positional) |
| `--wildcards` | Enable globbing for member patterns on `-t`/`-x` |
| `--transform=s/.../.../` | sed-style member name rewrite at creation |
| `--strip-components=N` | Drop N leading path components when extracting |
| `--no-recursion` | Archive directory entries without descending |
| `-T FILE`, `--files-from=FILE` | Take member names from FILE (`-` = stdin); with `--null`, names are NUL-separated |
| `--one-file-system` | Do not descend into directories on other filesystems |

### Metadata and permissions

| Option | Effect |
| --- | --- |
| `-p` | Restore permissions (default for root) |
| `--same-owner` / `--no-same-owner` | Restore / ignore archived ownership (root default: same) |
| `--numeric-owner` | Store/restore UIDs numerically; skips name lookups |
| `--acls` / `--xattrs` | Include POSIX ACLs / extended attributes |
| `-m` | Do not restore mtimes (files get extraction time) |
| `-S` | Handle sparse files efficiently |

### Compression

| Option | Effect |
| --- | --- |
| `-z` / `-j` / `-J` | Filter through gzip / bzip2 / xz at creation |
| `--zstd` | Filter through zstd (GNU tar 1.31+) |
| `-a` | Auto-compress: pick filter from the archive suffix |

## Usage Patterns

```bash
# Classic source-tree tarball, one top-level directory, gzipped
tar -czf project-$(date +%F).tar.gz --transform 's,^,project/,' -C /srv project
```

```bash
# Relative-path backup of a config dir (store etc/, not the absolute path)
tar -C / -czf etc-backup.tar.gz etc
```

```bash
# Inventory an archive before trusting it: types, sizes, owners
tar -tvf untrusted.tar | head -40
```

```bash
# Extract only one subtree out of a big archive
tar -xf big.tar --wildcards '*/doc/*'
```

```bash
# Copy a tree across hosts with ownership preserved (root to root)
tar -C /var/www -cf - . | ssh root@host 'tar -C /var/www -xpf -'
```

```bash
# Nightly level-1 incremental off a weekly level-0
tar -cf mon.tar   --listed-incremental=/var/backups/snap /data
tar -cf tue.tar   --listed-incremental=/var/backups/snap /data
```

```bash
# Verify a backup actually restored: archive vs filesystem diff
tar -df backup.tar
```

```bash
# Ship a directory to a container without a temp file
tar -cf - app | kubectl exec -i pod -- tar -xf - -C /srv
```

```bash
# Append today's log to an uncompressed archive, then list
tar -rvf logs.tar app.log.2 && tar -tf logs.tar | tail
```

```bash
# Kernel-source style extraction: drop the linux-6.x/ prefix
tar -xf linux.tar.xz --strip-components=1 -C build/
```

```bash
# Dump a tree excluding node_modules and VCS metadata (exclude globs by default)
tar -cf rel.tar --exclude='node_modules' --exclude='.git*' src
```

```bash
# Preserve ACLs and xattrs in a root filesystem migration
tar --acls --xattrs -C / -cpf rootfs.tar .
```

```bash
# Archive exactly the files find selected — NUL-safe for any filename
find /srv -type f -mtime -7 -print0 | tar --null -T - -czf weekly.tar.gz
```

```bash
# Backup one mounted filesystem only (skip /proc-style and NFS crossings)
tar -cpf root.tar --one-file-system /
```

## Nuances and Gotchas

- **Options are positional after operands.** `tar -cf a.tar dir --exclude='*.log'` errors with `--exclude '*.log' has no effect` and exits 2 — yet the archive of `dir` still gets written, including the `.log` files. Same rule for `-C`. Rearranging matters more than in any other common tool.
- **`-v` output lands on stderr when the archive is stdout.** `tar -cvf - . 2>/dev/null | wc -c` is clean; scripts that parse `-v` listing must capture stderr deliberately, and parsing it at all is fragile (locale-dependent date format, quoting).
- **Wildcard defaults are asymmetric**: `--exclude` globs, member patterns on `-t`/`-x` do not (need `--wildcards`), and `*` does not match `/` unless `--wildcards-match-slash`. The same pattern string behaves differently on each side of the operation.
- **Ownership on extraction is an identity question.** As root, archives restore their original UIDs/GIDs — extracting a malicious archive as root plants files owned by `bin` or `daemon` by design. Use `--no-same-owner` for content you only want the bytes of.
- **`-r`/`-u`/`-A` cannot touch compressed archives** — there is no seekable tar inside a `.tar.gz`; you decompress, modify, recompress. A surprisingly common production mistake.
- **ustar format limits bite silently**: with `--format=ustar` (the POSIX interchange default) file sizes cap at 8 GiB and long paths need prefix juggling; GNU format relaxes both, and `pax` is the portable choice for huge files. Mixing tools (bsdtar writes pax by default) can change member metadata in ways old GNU tars flag.
- **bsdtar vs GNU tar differ in the traps**: bsdtar's `--exclude` is global rather than positional and its member-pattern globbing defaults differ; scripts moving between macOS (`bsdtar`) and Linux (`gnu tar`) should pin explicit flags (`--wildcards`, `--no-same-owner`) instead of leaning on defaults.
- **Compression choice is a throughput decision**: gzip for compatibility, xz for size, zstd for the size/speed middle ground; `-a` matches the filter to the suffix but only warns-not-fails if the suffix is unknown.
- **Exit code 1 is not always an error for `-c`/`-x` flows** — it is documented for `--diff` ("some files differ"), while 2 means fatal trouble; a wrapper that treats any nonzero as failure will misreport `-d`-based verification runs.
- **Locale dates in `-tv` listings are not parseable input**: they exist for humans; machines should use `--null -t` with `--names-...` flows or list via `tar -tf` only.
- **`-T` member lists obey positional options too** — a `-C` recorded before the `-T` argument applies to the names inside it, and without `--null` each line is one name (find `-print0` output without `--null` will mangle filenames containing newlines).

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Operation fully succeeded |
| 1 | "Some files differ" — documented for `-d` comparisons (also used for a class of recoverable warnings) |
| 2 | Fatal error: unreadable inputs, bad options, misused positional options |

## Related Commands

- [GNU Coreutils collection](../coreutils/overview.md) — the file-manipulation layer around archives; compression companions `gzip`/`gunzip` and `zip` live outside it and are referenced here without dedicated pages.
- [Permissions](../../admin/permissions.md) — what `--same-owner`, `-p`, and `--numeric-owner` actually restore, and why extraction as root is an ownership trust decision.
- [Binaries part overview](../overview.md) — the chapter hub this collection hangs from.

## Interview Questions

### Q: Why does `tar -xf archive.tar.gz` work without `-z`, but `tar -cf archive.tar.gz dir` produce an uncompressed file?

On read, GNU tar sniffs the stream's magic bytes and spawns the matching decompressor automatically. On write there is nothing to sniff yet — the filter must be requested explicitly with `-z`/`-j`/`-J`/`--zstd` or delegated to `-a`, which picks it from the filename suffix. Without any of them you get a gzip-named plain tar file, a classic support ticket.

### Q: What does `--listed-incremental` give you that "rsync to a new directory each night" does not?

Dump-style levels with deletion tracking: the snapshot file records inode metadata, later runs archive only changed/new files, and a renamed or removed directory is represented in the incremental so restores reproduce the removal. Restores must replay the level-0 archive and each level in order, passing `-g /dev/null` so members are applied rather than diffed against a missing snapshot.

### Q: A teammate ran `tar -cf site.tar html --exclude='*.html'` and got a full archive plus exit code 2. Explain.

`--exclude` is positional in GNU tar: placed after the `html` operand it affects nothing that follows, so tar warns `--exclude '*.html' has no effect`, still writes the archive, and exits 2. The fix is option ordering — `tar --exclude='*.html' -cf site.tar html` — and knowing that `-C` obeys the same positionality.

### Q: Why do extract jobs run as root use `--no-same-owner`, and what is the default instead?

Root extraction defaults to `--same-owner --same-permissions`, restoring archived UIDs/GIDs bit-for-bit — correct for disaster recovery, dangerous for untrusted content because ownership becomes attacker-chosen metadata. `--no-same-owner` makes everything owned by the extracting user; ordinary users always get that default because chown would fail anyway.

### Q: How would you defend a pipeline against a tar bomb?

List first (`tar -tvf`) and eyeball sizes and member paths; extract in a dedicated empty directory with an unprivileged account and a quota, keeping `--no-same-owner -m` so neither ownership nor old timestamps carry meaning; rely on GNU tar's stripping of leading `/` and refusal of `..` members; and cap the blast radius with `ulimit`/disk quotas rather than trusting the archive's self-description.

### Q: What is stored inside a tar member header, and why can you not append to a `.tar.gz`?

Each member is a 512-byte header (name, mode, uid/gid, size, mtime, checksum, type flag) followed by size-padded data blocks, ending in two zero blocks. Appending (`-r`, `-u`, `-A`) rewrites the archive in place after truncating the end-of-archive marker, which requires seekability and raw tar blocks; a `.tar.gz` is a gzip stream over those blocks, where random-position edits and suffix truncation are meaningless — hence decompress, modify, recompress.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/tar/tar.1.en.html)
- [GNU tar manual](https://www.gnu.org/software/tar/manual/)
- [Source — Debian sources](https://sources.debian.org/src/tar/)
