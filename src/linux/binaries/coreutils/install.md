# install — copy files with mode and ownership control

## Overview

`install` is `cp` with opinions: it copies files *and* enforces destination mode, owner, and group in the same step, and it can create directory trees. It is the workhorse of `Makefile` `install:` targets, package-build recipes, and provisioning scripts that must place files with exact, repeatable attributes — not whatever mode the build happened to leave behind. It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at `/usr/bin/install`.

Despite the name it has nothing to do with package management ("installing" software in the apt sense); its help text even says so explicitly. It is often confused with `cp -p` (which preserves *source* attributes rather than imposing *specified* ones) and with `mkdir -p` (which `install -d` subsumes). BSD heritage tool: `install` appeared in 4.x BSD, and GNU's version has been part of fileutils/coreutils since the early days.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/install |
| First appeared | BSD heritage (4.x BSD); long part of GNU fileutils → coreutils (2003) |
| Standards | None (GNU/BSD convention; not in POSIX.1-2018) |

## Synopsis

```
install [OPTION]... [-T] SOURCE DEST
install [OPTION]... SOURCE... DIRECTORY
install [OPTION]... -t DIRECTORY SOURCE...
install [OPTION]... -d DIRECTORY...
```

The first three forms copy; the fourth creates directories (all components of each argument).

## How It Works

### Copy, then enforce attributes

For each SOURCE, `install` performs a copy (same read/write and fast-path machinery as `cp`) and then applies its own attribute rules to the destination:

- **mode**: defaults to `0755` (`rwxr-xr-x`) — executable-friendly — regardless of the source's mode and of what the source was. Override with `-m MODE` (chmod syntax, e.g. `-m 644`).
- **owner/group**: defaults to the invoking user and their current group; `-o USER` and `-g GROUP` set them (superuser only for `-o`).
- **timestamps**: destination gets the current time, like any fresh file; `-p` applies the source's access/modification times instead.

This "copy + chmod + chown" is precisely what a Makefile recipe would otherwise hand-roll with three commands — and unlike a hand-rolled sequence, `install` leaves no window where the destination exists with wrong permissions.

```
$ echo hi > src.bin && install src.bin mod.bin
$ ls -l mod.bin
-rwxr-xr-x 1 z z 3 Oct  9 09:34 mod.bin      # 0755 by default, not 0644!
```

### Modes are umask-immune

The sequence is: copy bytes, then set the destination's mode explicitly, then set ownership. Because the mode comes from `install` itself — default `0755` or whatever `-m` says — the process umask never touches the destination. This is the sharpest contrast with `cp`, where the new file's mode is `source & ~umask`:

```
$ ( umask 077; cp src.bin cp-style.bin;      ls -l cp-style.bin )
-rw------- 1 z z 3 ... cp-style.bin          # cp: umask bites (0600)
$ ( umask 077; install src.bin inst.bin;     ls -l inst.bin )
-rwxr-xr-x 1 z z 3 ... inst.bin             # install: 0755 regardless
$ ( umask 077; install -m 644 src.bin i644.bin; ls -l i644.bin )
-rw-r--r-- 1 z z 3 ... i644.bin             # -m 644 lands exactly as written
```

The same immunity applies to directories `install -d`/`install -D` create: under `umask 077` they still come out `0755` (verified on GNU coreutils 9.x), which is why provisioning scripts that must not depend on the caller's umask reach for `install` rather than `mkdir` + `chmod`.

### Directory creation: `-d` and `-D`

- `install -d a/b/c` creates **every component** of every argument, like `mkdir -p`. With `-m`, the mode applies to the created directories; with `-o`/`-g` they get the given owner/group.
- `install -D SOURCE DEST` creates all leading components of DEST *except the last*, then copies SOURCE to DEST — the "place a file deep in a tree that may not exist yet" one-liner. The leading components are created with default modes; `-m` applies to the final file.

```
$ install -D -m 644 src.bin ./opt/app/bin/prog
$ ls -l opt/app/bin/prog
-rw-r--r-- 1 z z 0 Oct  9 09:34 opt/app/bin/prog
```

### Idempotent updates with `-C`

`-C` (`--compare`) is the flag that turns `install` from a copier into a *synchronizer*: if the destination already exists with identical content, mode, and ownership, nothing is written — the destination keeps its inode and, crucially, its mtime. This matters in Make-based builds, where touching a file needlessly invalidates downstream rules. Without `-C`, every `make install` rewrites the files even when nothing changed.

### Staged installs: the DESTDIR convention

GNU packaging convention separates *where a file will live* (`--prefix=/usr`, hard-coded in the build) from *where it is placed right now* (`DESTDIR`, a staging root). `install` recipes take the staging root as a plain path prefix, and `install -D` makes each recipe a self-contained one-liner that materializes any missing directories:

```
build/app ──► install -D -m 755 ──► $(DESTDIR)/usr/local/bin/app
app.1     ──► install -D -m 644 ──► $(DESTDIR)/usr/share/man/man1/app.1

$(DESTDIR) = /tmp/pkgroot during packaging; empty ("/") for a real install
```

The packaged tree is then archived or handed to the packaging tool from the staging root — the paths *inside* the package stay correct because `DESTDIR` was never baked into the binaries. A failing `chown` (`-o` as non-root), a bad mode string, or an unwritable staging path aborts with exit 1, which is what makes `install` recipes trustworthy build steps: either the file is in place with the exact attributes requested, or `make` stops.

### Stripping and backups

`-s` runs `strip` on the installed binary (or `--strip-program=PROGRAM` for a custom one, e.g. a cross-toolchain's strip). `-b`/`--backup[=C]` and `-S SUFFIX` behave exactly like their `cp`/`mv` counterparts: each overwritten destination is renamed aside (suffix `~` by default). `-Z` sets default SELinux contexts on the file and any created directories.

```
$ ls -l t.bin                       # freshly built, unstripped (15,824 bytes)
-rwxrwxr-x 1 z z 15824 ... t.bin
$ install -s -m 755 t.bin t.stripped
$ ls -l t.stripped                  # stripped copy on disk (14,384 bytes)
-rwxr-xr-x 1 z z 14384 ... t.stripped
$ file t.stripped | grep -o stripped
stripped
```

Note what `-s` buys: the *source* build artifact stays unstripped for debugging, while the deployed copy is shrunk — and the strip happens before the mode/owner enforcement, so the deployed file ends up with the exact attributes requested.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-d` | Treat all arguments as directories; create all components (like `mkdir -p`) |
| `-D` | Create leading components of DEST, then copy SOURCE to DEST |
| `-m MODE` | Destination mode (chmod syntax); default `0755` |
| `-o USER`, `-g GROUP` | Destination owner/group (owner needs root) |
| `-C` | Skip the write when content+mode+ownership already match |
| `-p` | Apply source timestamps to the destination |
| `-s` | Strip symbol tables from the installed binary |
| `--strip-program=P` | Custom strip tool (cross-compilation) |
| `-t DIR`, `-T`, `--target-directory` | Target-directory plumbing, same semantics as cp/mv |
| `-b`, `--backup[=C]`, `-S SUF` | Back up overwritten destinations |
| `-Z` | Set default SELinux security context |
| `-v` | Print each created file or directory |

The long-ignored `-c` option exists for historical BSD compatibility and does nothing.

## Usage Patterns

```bash
# Put a binary where PATH expects it, mode 0755 (the default)
sudo install -m 755 mytool /usr/local/bin/mytool

# Data file: must override the 0755 default explicitly
sudo install -m 644 mytool.conf /etc/mytool.conf
```

```bash
# Place a file in a directory tree that may not exist yet
sudo install -D -m 644 app.service /etc/systemd/system/app.service
sudo install -D -m 755 app /opt/app/bin/app
```

```bash
# Create a directory scaffold with exact modes and owners
sudo install -d -m 750 -o root -g adm /var/log/myapp /var/lib/myapp
```

```bash
# Makefile recipe: idempotent, only rewrites when content changed
install: bin/mytool
        install -C -m 755 bin/mytool $(DESTDIR)/usr/local/bin/mytool
        install -C -m 644 mytool.1 $(DESTDIR)/usr/share/man/man1/mytool.1
```

```bash
# Preserve mtimes for files where timestamps are metadata (e.g. docs)
install -p -m 644 README.md /usr/share/doc/myapp/README.md

# Install a stripped release binary, keeping the unstripped original
install -s -m 755 build/app /usr/local/bin/app
```

```bash
# Cross-compiled build: strip with the toolchain's strip, not the host's
install --strip-program=${CROSS}-strip -m 755 target/arm/app rootfs/usr/bin/app
```

```bash
# Reinstall over an existing file but keep the previous one as file~
sudo install -b -m 644 nginx-site.conf /etc/nginx/sites-available/default
```

```bash
# Target-directory form for many files at once
install -t /usr/local/share/myapp -m 644 locale/*.mo
```

```bash
# Two-stage packaging: fill a staging root, then archive or ship it
install -D -m 755 build/app /tmp/pkgroot/usr/local/bin/app
install -D -m 644 app.1 /tmp/pkgroot/usr/share/man/man1/app.1
tar -C /tmp/pkgroot -cf app-staging.tar .
```

```bash
# Full provisioning unit: binary, unit file, and a locked-down state dir
install -m 755 myapp /usr/local/bin/myapp
install -D -m 644 myapp.service /etc/systemd/system/myapp.service
install -d -m 750 -o myapp -g myapp /var/lib/myapp
```

```bash
# One shared mode for a batch of libraries
install -t /usr/local/lib/myapp -m 644 build/lib/*.so
```

```bash
# Recursion workaround: install has no -r; mirror a tree with find + install
find src -type f -exec install -D -m 644 {} /opt/myapp/{} \;
```

## Nuances and Gotchas

- **The 0755 default is a trap for data files.** `install data.csv /srv/data/` produces an executable CSV. Always pass `-m` for non-executables; this default exists because `install` is optimized for binaries.
- **`-m` does not retroactively fix an existing destination's mode when only `-C` skips it.** `-C` compares mode as part of the match — a destination with the wrong mode *is* rewritten — but a plain copy (no `-m`) onto an existing file leaves the old mode in place, exactly like `cp`.
- **`-o` is superuser-only** and fails as a normal user even on your own files; `-g` works only for groups you belong to. Provisioning scripts usually run `install` under `sudo` precisely for this.
- **`-C` compares content, mode, and ownership — not timestamps or xattrs.** Two files with same content but different SELinux labels still count as "different" only in the attributes it checks; verify what your packaging flow needs.
- **`-D` and `-m` scope.** With `-D`, intermediate directories are created with default modes (0755 adjusted by umask); only the final file gets `-m`. If the tree itself needs locked-down modes, create it with `install -d -m ...` first.
- **Not POSIX.** BusyBox ships an `install`, and BSD/macOS have one, but flag sets differ (macOS's BSD `install` lacks `-C`-style compare and takes `-B suffix`). Core scripts should stick to `-d`, `-D`, `-m`, `-o`, `-g`, `-p`.
- **`-c` is vestigial.** Old recipes still pass it (it once meant "copy" vs BSD's historical "move" semantics); GNU ignores it. Don't cargo-cult it into new ones.
- **No recursion.** `install` has no `-r`/`-R`: directories in the source list are an error, not a tree copy. Mirroring a tree means `find ... -exec install -D ...` (see Usage Patterns) or `cp -r` followed by explicit `chmod`/`chown`.
- **One `-m` per invocation.** `-t DIR` applies the single mode (and owner/group) to every file in that call; mixed-permission installs need multiple invocations — batch by mode, not by directory.
- **`-s` depends on an external `strip`.** The symbol table is discarded by the strip *program*, not by install itself; if strip is missing or fails on the artifact, the installation fails. In cross builds this is exactly what `--strip-program` exists for.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All copies/directories succeeded |
| 1 | Any failure: missing source, denied chown, bad mode string, unwritable destination |

## Related Commands

- [`cp`](./cp.md) — plain copy without attribute enforcement.
- [`mkdir`](./mkdir.md) — directory creation alone; `install -d` adds mode/owner control.
- [`mv`](./mv.md) — move/rename semantics where the source should not remain.
- [`ln`](./ln.md) — alternatives to physically copying files into place.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [File permissions](../../admin/permissions.md) — what `-m`/`-o`/`-g` actually set.
- [systemd](../../admin/systemd.md) — where `install -D`-placed unit files get consumed.

## Interview Questions

### Q: Why do Makefiles use `install` instead of `cp`?

One command enforces the final state: copy + mode + owner + group, with no intermediate wrong-permission window and no dependency on the build artifacts' modes. `-C` makes the recipe idempotent — unchanged files are not rewritten, so their mtimes survive and downstream packaging/timestamp logic stays stable. `cp` would need a `chmod`/`chown` tail and would rewrite files unconditionally.

### Q: What does `install -D -m 644 app.conf /etc/app/conf.d/app.conf` do if `/etc/app/conf.d` doesn't exist?

It creates every leading component (`/etc/app`, `/etc/app/conf.d`) with default modes (0755 modulo umask), then copies `app.conf` to the destination and sets mode 644 on the file. If you need the directories themselves to have specific modes or owners, run `install -d -m 750 /etc/app/conf.d` first — `-m` on the `-D` form applies only to the final file.

### Q: What is the default mode of a destination created by `install`, and why is that design choice important to know?

`0755` (`rwxr-xr-x`), independent of the source's mode. It reflects `install`'s role of placing executables. Forgetting it means configs and data files installed via `install` are needlessly executable — and scripts that then check "is anything in /usr/local/bin unexpected?" get noise. Data files need an explicit `-m 644`.

### Q: How does `install -C` decide to skip a destination?

It compares the source and destination file contents and, in addition, the destination's mode and ownership against what it would enforce. If all match, it performs no write at all — the destination keeps its inode and mtime. This is the difference between a build that re-stamps every binary on each `make install` (breaking anything keyed on mtime) and one that only touches genuinely changed files.

### Q: When would you choose `install -d` over `mkdir -p`?

When the created directories need specific modes, owners, or groups in one step — `install -d -m 750 -o root -g adm /var/lib/myapp` replaces a `mkdir -p` plus `chown` plus `chmod` sequence, and it applies the mode/owner to *every* component it creates. For plain trees where umask defaults are fine, `mkdir -p` is equivalent and more portable.

### Q: Under `umask 077`, what mode does a freshly `install`ed file get, and why does the difference from `cp` matter?

`0755` — the default is applied as-is, and `-m` values land exactly as written; the umask never participates. `cp` under the same umask produces `0600` (source mode masked by umask). The difference matters wherever the calling environment is untrusted: a provisioning script run from cron, a container entrypoint, or a CI job may carry a surprising umask, and `install` is the copy tool whose output does not vary with it. The same immunity covers directories created by `-d`/`-D`.

### Q: What is the difference between `install -p` and `install -C`?

Both involve metadata, in opposite directions. `-p` always writes the destination file and then stamps it with the *source's* timestamps — the copy is fresh, the times are old. `-C` may not write anything at all: when content, mode, and ownership already match, the destination is left untouched, keeping its inode and its own mtime. Use `-p` when timestamps are part of the payload (docs, vendored data); use `-C` when unchanged files must not be disturbed (Make-driven installs feeding mtime-sensitive packaging).

### Q: What is DESTDIR, and how does it differ from `--prefix`?

`--prefix` is a *build-time* decision — the path compiled into binaries and used by configure-time logic — while `DESTDIR` is an *install-time* staging prefix prepended to every destination path. `make install DESTDIR=/tmp/pkgroot` puts the binary at `/tmp/pkgroot/usr/bin/app` even though the binary expects `/usr/bin/app` at runtime; the staged tree is what a packaging tool archives. `install` recipes honor this naturally because DESTDIR is just part of the destination path, and `install -D` creates any missing staging directories on the way.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/install.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
