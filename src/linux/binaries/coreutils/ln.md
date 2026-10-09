# ln — create hard and symbolic links

## Overview

`ln` creates links: additional directory-entry names that refer to existing data. A **hard link** is a second name bound to the same inode — indistinguishable from the original, counted, filesystem-local. A **symbolic link** (`-s`) is a small file whose content is a path string, resolvable lazily and allowed to dangle. Links underpin package managers (`/usr/bin` symlinks into versioned trees), config management (dotfile repos), atomic deployments, and deduplication farms. `ln` ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at `/usr/bin/ln`.

`ln` is often confused with `cp -l` (which is exactly "hard link instead of copy") and `cp -s` ("symlink instead of copy"), and with `mv` when people use links to "move" things. The distinction worth internalizing: copying creates a second inode; linking creates a second *name* for one inode.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/ln |
| First appeared | AT&T UNIX, Version 1 (1971) |
| Standards | POSIX.1-2018 (`ln`) |

## Synopsis

```
ln [OPTION]... [-T] TARGET LINK_NAME
ln [OPTION]... TARGET
ln [OPTION]... TARGET... DIRECTORY
ln [OPTION]... -t DIRECTORY TARGET...
```

One-line forms:

```
ln target link            # hard link
ln -s target link         # symbolic link
ln -sfn target dirlink    # the idempotent directory-symlink idiom
ln -sr /abs/path link     # symlink rewritten relative to link's location
```

With one TARGET, the link is created in the current directory using the target's basename. With multiple TARGETs (or `-t`), each target is linked into the directory.

## How It Works

### Hard links: names bound to an inode

A hard link is created with the `link(2)` syscall: it adds a new directory entry mapping LINK_NAME to TARGET's existing inode and increments the inode's link count. There is no "original": both names are equally primary. Deleting one merely decrements the count; the data lives until the count reaches zero (and no process holds it open).

```
$ echo data > a3
$ ln a3 h3                     # hard link
$ ls -li a3 h3
269444 -rw-rw-r-- 2 z z 5 Oct  9 09:33 a3
269444 -rw-rw-r-- 2 z z 5 Oct  9 09:33 h3     # same inode, nlink=2
$ rm a3                        # data still reachable as h3
$ cat h3
data
```

Consequences to reason about in interviews:

- Hard links must live on the same filesystem (an inode is a filesystem object; cross-device attempts fail with `EXDEV`).
- Directories cannot be hard-linked by users — the kernel reserves it to maintain a loop-free tree (`.`/`..` are the kernel's own links; `ln -d` is a root-only, effectively-always-failing historical stub).
- Everything about the file is shared: mode, mtime, ownership, data. Editing through one name edits the other.
- The link count is the `2` in `ls -l`'s second column, and `find -samefile`/`-links` traverse that relationship.

### Symbolic links: a stored path

A symlink is a new inode of type `l` whose data is a path string. Resolution happens at *access* time and is relative to the symlink's **own directory**, not the current working directory — the single most important symlink fact:

```
ln -s ../etc/app.conf /opt/app/current.conf   # stored text: "../etc/app.conf"
# resolves relative to /opt/app, i.e. /opt/etc/app.conf — usually a surprise
```

Symlinks can cross filesystems, can point to directories, and can dangle (target absent). `stat` follows them; `lstat` reads the link itself; `ls -l` uses `lstat` and prints the arrow, which is why a dangling link still shows up in listings. Symlink permissions are ignored on Linux — the target's permissions govern access.

```
 ┌────────── directory ──────────┐
 │ "a3"   → inode 269444 (nlink 2)│   hard links: two names,
 │ "h3"   → inode 269444          │   one inode, one data copy
 └────────────────────────────────┘
 "sym" → inode 269445 (type l) ──text──▶ "a3"    symlink: separate inode
                                                 holding a path string
```

### Form resolution and overwrite rules

Like the rest of the file utilities, `ln` copies into a directory when the last argument is an existing directory, and `-T`/`-t` pin the interpretation. Destination handling: by default an existing LINK_NAME is an error; `-f` removes it first; `-i` prompts. The infamous trap is `-sf` on a symlink *to a directory* — `ln` follows it and creates the new link *inside* the directory. `-n` (or `-T`) treats LINK_NAME as a normal file and fixes the idiom:

```
ln -sfn /opt/app-2.0 /opt/app/current   # classic deploy flip (with -n!)
```

For hard links to symlinks, `-P` links to the symlink itself (default), `-L` follows the symlink and links to its target. `-r --relative` computes the stored path of a symlink relative to the link's location — the fix for the resolution surprise above. `-b`/`-S` back up replaced links exactly like cp/mv.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-s` | Create a symbolic link (the option most people use daily) |
| `-f` | Remove existing destinations instead of failing |
| `-n` | Treat LINK_NAME as a normal file even if it symlinks to a directory |
| `-r` | With `-s`, store a path relative to the link's location |
| `-T` | LINK_NAME is always a normal name — never "into the directory" |
| `-t DIR` | Create all links inside DIR |
| `-i` | Prompt before removing destinations |
| `-L` / `-P` | Hard-link symlinks through their target / to the link itself |
| `-v` | Print each link created |
| `-b`, `--backup[=C]`, `-S SUF` | Back up overwritten links |
| `-d`, `-F` | Historical: allow root to *attempt* directory hard links (still fails) |

## Usage Patterns

```bash
# Hard-link deduplication of large unchanged artifacts
ln bigmodel.bin cache/bigmodel.bin

# Verify a hard link: same inode, same data, shared mtime
ls -li a3 h3
```

```bash
# Dotfile management: repo copy is the truth, home entries are links
ln -sf ~/dotfiles/vimrc ~/.vimrc
ln -sfn ~/dotfiles/tmux.conf ~/.tmux.conf
```

```bash
# Version-switching directory symlink, safe to re-run
ln -sfn /opt/app-2.0.1 /opt/app/current

# Absolute vs relative: relative survives mounting the tree elsewhere
ln -sr /opt/app-2.0.1 /opt/app/current    # stores "../app-2.0.1"
```

```bash
# Atomic service flip: build aside, then rename over (no window of absence)
ln -s /srv/releases/2024-10-09 /srv/current.tmp && mv -T /srv/current.tmp /srv/current
```

```bash
# Link a shared library before ldconfig notices it
sudo ln -sf /usr/lib/x86_64-linux-gnu/libfoo.so.1.2 /usr/lib/libfoo.so

# Point a command name at a variant without copying
ln -sf /usr/bin/vim.tiny /usr/local/bin/vi
```

```bash
# Recover the idiom when -f alone would nest the link inside a directory
ln -sfn /opt/newdir /opt/linkdir          # -n is what makes this replace, not nest

# Relative symlink to a sibling directory from within it
cd /var/www && ln -s ../shared/uploads uploads
```

```bash
# Hard-link a symlink itself (-P) vs what it points to (-L)
ln -P linkfile alias-of-link
ln -L linkfile alias-of-target

# Backup the replaced link when flipping versions
ln -sfb /opt/app-2.0.2 /opt/app/current   # old link kept as current~
```

## Nuances and Gotchas

- **`ln -sf target dir` nests.** If `dir` is a symlink to a directory (or a directory), plain `-f` follows it and creates `dir/basename(target)`. The cure is `-n` or `-T`; this is the most-quoted `ln` bug in shell history.
- **Relative symlinks resolve from the link's directory.** A link created with a relative target works only as long as the link and target keep their relative geometry — moving the link (or the tree) silently dangles it. `ln -r` stores the right relative path; `readlink -f` reveals what a link actually resolves to.
- **Deleting the original doesn't hurt hard links but kills symlinks.** A symlink stores a name, not an inode reference: remove the target and the link dangles. Hard links are inode references; the data survives until every name is gone.
- **Editing through one hard link changes both.** Only *replace* semantics (editor write-to-temp-and-rename, `mv`, `cp` onto a new inode) fork the data. A tool that truncates and rewrites in place will "corrupt" both views — which is exactly what hard-link farms exploit, and why `cp -al` snapshots break under in-place editors.
- **Cross-device and directory limits.** `ln` across filesystems fails with `EXDEV` (symlinks are the workaround); hard-linking directories fails for users regardless of privilege. `nlink` limits exist (`EMLINK`) and count toward backup tools' assumptions.
- **The link count in `ls -l` is a directory's hidden story.** A directory's nlink equals its subdirectory count plus two (`.` and `..`) on classic layouts — a trivia staple with real diagnostic value.
- **Symlink permissions don't exist on Linux** — `lrwxrwxrwx` is decorative. Access control happens at the target. (macOS/HFS+ behaves differently for GUI-created aliases, not POSIX symlinks.)
- **Portability.** `-r`, `-T`, `-t` are GNU; BSD `ln` shares `-s/-f/-i/-L/-P/-n`. BusyBox `ln` covers `-s/-f/-v/-n`. POSIX defines `-f`, `-i`, `-s`, `-L`, `-P` and the last-one-wins rule between `-L`/`-P`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All links created |
| 1 | Any failure: destination exists (without -f), EXDEV, EMLINK, permission denied |

## Related Commands

- [`cp`](./cp.md) — `cp -l`/`cp -s` delegate the actual link creation to the same syscalls.
- [`mv`](./mv.md) — rename within a filesystem is the atomic primitive links piggyback on.
- [`install`](./install.md) — when you need a real second copy with enforced attributes instead.
- [`ls`](./ls.md) — `ls -li` and the nlink column are how you *verify* link topology.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [Linux internals](../../internals.md) — inodes, dentries, and how name resolution walks symlinks.
- [File permissions](../../admin/permissions.md) — why symlink mode bits are ignored on Linux.

## Interview Questions

### Q: What is the difference between a hard link and a copy, and between a hard link and a symlink?

A copy writes new data with a new inode — independent content and metadata from then on. A hard link adds a second directory entry for the *same* inode: shared data, mode, mtime, and ownership; deleting one name leaves the data alive under the other. A symlink is a separate inode containing a path *string*; it can cross filesystems and dangle, resolves relative to its own directory, and its target's absence breaks it. Hard link = another name for data; symlink = a pointer to a name.

### Q: Why can't users hard-link directories?

The kernel reserves directory hard links to guarantee the filesystem stays a tree. Two names for one directory create cycles (a subtree reachable by two paths), which breaks every tree-walking algorithm, makes `..` ambiguous, and complicates consistency and quota accounting. The kernel itself maintains the only "links" a directory has: `.` and `..` — which is why a directory's link count is subdirectories + 2. `ln -d` exists as a root-only historical stub that effectively always fails on modern kernels.

### Q: Explain the `ln -sfn` idiom and what breaks without the `-n`.

`ln -sfn newtarget dirlink` atomically-ish replaces a directory symlink. Without `-n`, if `dirlink` currently points at a directory, `ln -f` follows it and creates `dirlink/basename(newtarget)` *inside* — leaving the old link in place and littering the target directory. `-n` tells `ln` to treat LINK_NAME as a plain file even though it resolves to a directory. (For a truly race-free flip, create the link under a temp name and `mv -T` it over — a rename replaces symlinks atomically.)

### Q: A script creates `ln -s config/app.conf /etc/app.conf` and later the link dangles after a packaging change. What actually went wrong?

The link stores the literal text `config/app.conf`, resolved relative to `/etc` — so it pointed at `/etc/config/app.conf`, and either worked by accident or never did. Relative symlink targets are relative to the link's *directory*, not the cwd at creation time. Fixes: store an absolute path, compute the correct relative path with `ln -r`, and verify with `readlink -f` (or `ls -l`) rather than trusting that creation succeeded.

### Q: How can you tell two files are hard links to the same data, and what operations break the pairing?

`ls -li` — identical inode numbers — or `stat`/`find -samefile`. The pairing survives deletion of either name and survives in-place edits (both views change together, that's the point). It breaks when one path is *replaced* by a new inode: `mv` of a new file over one name, editor save-by-rename, or `cp` with truncation semantics onto one path. After such a replace the two names have different inodes and diverge silently — the failure mode of hard-link-based dedup and backup schemes.

### Q: What does the second column of `ls -l` mean, and why is it often 2 for a plain file?

It is the inode's hard-link count — the number of directory entries naming it. A plain file normally shows 1; a 2 means another name somewhere refers to the same data (or a copy-time artifact like `cp -l`). For directories it's subdirectories + 2 on classic filesystems. The count is also the garbage-collection primitive: the kernel frees the inode's data when the count hits zero and no process holds it open.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/ln.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — ln](https://pubs.opengroup.org/onlinepubs/9699919799/)
