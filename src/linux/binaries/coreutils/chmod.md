# chmod — change file permission bits

## Overview

`chmod` writes the permission bits of files: the nine `rwx` bits for owner, group, and others, plus the three special bits (setuid, setgid, sticky). It is how executable-ness, write protection, and sharing get encoded on Unix filesystems — `chmod 755 deploy.sh`, `chmod +x`, `chmod -R g+rwX /srv`. Every scripting or admin workflow eventually hits it, and almost every subtle permissions bug report traces back to a chmod that did not mean what its author thought.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/chmod`, from upstream GNU coreutils. It is POSIX-standardized, so the octal and basic symbolic grammar work identically on BSDs and BusyBox; several extensions (operator numeric modes like `=600`, the umask interaction rules, special-bit preservation on directories) are GNU-specific.

It is often confused with its neighbors: `chown`/`chgrp` change *who* owns the file, `chmod` changes *what they may do*; `umask` is not a chmod at all but a creation-time mask applied by the kernel when files are born; and `setfacl` manages the finer-grained ACLs that sit alongside (and interact with) these bits.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/chmod` |
| First appeared / lineage | AT&T Unix (first edition era); GNU coreutils implementation |
| Standards | POSIX.1-2018 (`chmod`; operator numeric modes are a GNU extension) |

## Synopsis

```
chmod [OPTION]... MODE[,MODE]... FILE...
chmod [OPTION]... OCTAL-MODE FILE...
chmod [OPTION]... --reference=RFILE FILE...
```

Main forms:

```
chmod 644 file            # absolute octal
chmod u+x,go-w file       # symbolic operations
chmod -R g+rwX /srv/app   # recursive, conditional execute
chmod --reference=ref f   # copy ref's mode
```

The MODE grammar accepted by GNU chmod is, verbatim from its help:

```
[ugoa]*([-+=]([rwxXst]*|[ugo]))+|[-+=][0-7]+
```

i.e. symbolic clauses, or an octal number with an optional leading `+`/`-`/`=` operator.

## How It Works

### The bits being written

Every file carries twelve mode bits: nine permission bits in three `rwx` triads plus three special bits, traditionally displayed as four octal digits. For directories the meanings shift: `r` is "list entries", `w` is "create/remove/rename entries", `x` is "traverse into the directory" — a directory without `x` is listable but unusable, one without `r` is traversable if you know the names.

```
   4 7 5 5
   │ │ │ └── others:    r-x        (4+1)
   │ │ └──── group:     r-x        (4+1)
   │ └────── owner:     rwx        (4+2+1)
   └────────── special: setuid     (4000)

   special:  4000 setuid   2000 setgid   1000 sticky
   owner:      400 r  200 w  100 x
   group:       40 r   20 w   10 x
   others:       4 r    2 w    1 x
```

### Octal modes: absolute, with GNU escape hatches

A numeric mode sets all bits absolutely — `chmod 644 f` gives `rw-r--r--`, discarding whatever was there. Three refinements matter:

- **Four digits are optional.** `chmod 644` and `chmod 0644` are the same; the special-bit digit defaults to zero. For *regular files*, `chmod 755` clears setuid/setgid; that is expected.
- **On directories GNU chmod preserves setuid/setgid unless you say otherwise.** This is a deliberate GNU extension so that mass-mode changes do not wreck setgid-shared trees:

```bash
$ mkdir d && chmod 2755 d && chmod 755 d
$ stat -c %a d
2755                # setgid survived the numeric mode
$ chmod =755 d      # operator numeric form DOES clear it
$ stat -c %a d
755
$ chmod 00755 d     # five digits also clear it explicitly
```

- **Operator numeric modes (`+440`, `-1`, `=600`) are a GNU extension.** They apply octal values relative to current bits: `chmod +110 f` adds execute for owner and group without touching read/write. Not portable to other implementations.

### Symbolic modes: who, operator, perms

A symbolic clause is `[ugoa][-+=]perms`, and clauses — or several operations after one `who` — may be comma- or contiguity-combined: `u=rwx,g=rx,o=`, `og+rX-w`, `a+r,go-w`. `+` adds, `-` removes, `=` sets exactly (empty perms with `=` clears, e.g. `go=`). The `who` letters are owner (`u`), group (`g`), others (`o`), all (`a` = ugo).

Beyond `rwx` there is a copy form: one of `u`, `g`, `o` as the *perms* part copies that category's current bits — `o+g` grants others whatever the group has, `u=g` makes the owner's bits equal the group's. And the special letters: `s` (with `u` or `g`: setuid/setgid), `t` (sticky), and `X` — the one people get wrong.

### Capital X: conditional executability

`x` sets execute unconditionally; `X` sets it **only if the file is a directory or some user already has execute permission**. It is the tool for "make the tree browsable without making every data file executable":

```bash
$ touch f && mkdir d && chmod a=rwX f d
$ stat -c '%a %n' f d
666 f               # plain file: no x added
777 d               # directory: x added
$ printf 'exe\n' > f2 && chmod 700 f2 && chmod a=rwX f2
$ stat -c %a f2
777                 # already executable for owner -> X added for all
```

The canonical recursive pattern combines `X` with umask-awareness:

```bash
chmod -R a=,+rwX dir   # wipe, then r/w for all, x only where sensible
```

`X` has no numeric equivalent — `chmod 664` never conditionally sets execute, which is exactly why `+X` exists.

### Umask interplay: only when `who` is omitted

Two different umask interactions are commonly conflated:

1. **At creation time** (not chmod's business): the kernel computes `mode & ~umask` for new files. `umask` never modifies an explicit `chmod 644`.
2. **Inside chmod itself**: if the symbolic mode *omits* the `who`, the operation applies to all users **except bits that are set in the process umask**. The umask becomes a safety filter:

```bash
$ umask 022; : > u1; chmod 400 u1
$ chmod +w u1; stat -c %a u1        # who omitted: umask masks g/o write
600                                 # owner only
$ : > u2; chmod 400 u2
$ chmod a+w u2; stat -c %a u2       # explicit who: umask ignored
622
```

The same rule can bite with `-`: `chmod -w f` under umask 022 leaves group-write in place and GNU chmod notices the mismatch:

```bash
$ umask 022; : > w2; chmod 664 w2
$ chmod -w w2
chmod: w2: new permissions are r--rw-r--, not r--r--r--
$ echo $?
1
```

That warning — "I did something different from `a-w`" — exists precisely because the who-omitted form is umask-filtered. In scripts prefer explicit `a-w`.

### Special bits on files vs directories

- **setuid (4000)** on an executable file: the process runs with the file owner's effective UID. On directories it means "inherit owner" on a few systems only — on Linux it is mostly ignored there.
- **setgid (2000)** on an executable file: runs with the file's group. On a **directory**: every file created inside inherits the directory's group and new subdirectories inherit the bit — the foundation of shared group trees. GNU chmod also clears a regular file's setgid bit if the acting user is not in the file's group (and lacks privileges).
- **sticky (1000)** on a directory: users may only delete or rename entries they own — the reason `/tmp` is `1777`:

```bash
$ stat -c '%a %A' /tmp
1777 drwxrwxrwt
```

- The kernel refuses setuid on interpreted scripts (binfmt scripts run unsuid), so `chmod u+s script.sh` is a no-op for privilege purposes — setuid exists for ELF binaries.
- Symbolically: `u+s`, `g+s`, plain `+s` (both), `+t`. `o+s` does nothing; on GNU, `u+t`/`g+t` do nothing and `o+t` behaves like `+t`.

### Symlinks and recursion

chmod **cannot** change a symlink's permissions — the kernel ignores the mode of links, which are `lrwxrwxrwx` everywhere. Symlinks named on the command line are dereferenced (their target is chmodded); symlinks encountered during `-R` traversal are ignored. The traversal default for chmod is `-H` — follow only command-line argument symlinks — and `-L` (follow everything) carries the documented privilege-escalation risk if the tree is writable by others.

### ACL mask interplay

When a file has a POSIX ACL (check for `+` in `ls -l` output), the group triad shown by chmod is actually the ACL's **mask** entry — the ceiling for the ACL's named users and groups. `chmod g=rwx` on such a file rewrites the mask, potentially re-enabling previously capped entries; `chmod g=` empties the mask, effectively freezing every named entry to no access while leaving the entries themselves in place. The entries survive; their effective rights follow the mask chmod just set.

## Options That Matter

| Option | Effect |
|---|---|
| `-c, --changes` | Report only files whose mode actually changes |
| `-f, --silent, --quiet` | Suppress most error messages |
| `-v, --verbose` | Report every file, changed or not |
| `--reference=RFILE` | Copy RFILE's mode instead of a MODE argument |
| `-R, --recursive` | Recurse into directories |
| `-H` / `-L` / `-P` | Traversal for `-R`; **`-H` is chmod's default** (follow CLI-arg dir symlinks / follow all / follow none) |
| `--preserve-root` | Refuse to recurse on `/` (not the default for chmod) |

## Usage Patterns

```bash
# The classic script/program mode
chmod 755 deploy.sh
```

```bash
# Private key: owner-only, ssh refuses world-readable keys otherwise
chmod 600 ~/.ssh/id_ed25519
```

```bash
# Make a script executable without caring about current bits
chmod +x run.sh
```

```bash
# Tree cleanup: remove group/other write, keep executability sane
chmod -R go-w /opt/app
```

```bash
# The recursive X pattern: browsable dirs, no surprise executable data files
chmod -R u=rwX,g=rX,o= /srv/internal
```

```bash
# Shared setgid directory: group-writable, sticky not wanted here
sudo chmod 2775 /srv/shared
```

```bash
# Copy a known-good mode
chmod --reference=/etc/hosts site.conf
```

```bash
# Strip setuid/setgid from a suspicious binary (numeric clears them on files)
chmod 755 /tmp/unknown-binary
```

```bash
# Setgid shared tree: reapply the dir bit numeric chmod just cleared
sudo chmod -R g+rwX /srv/app && sudo find /srv/app -type d -exec chmod g+s {} +
```

```bash
# World-readable but no write anywhere, umask-independent
chmod a=r,u+w report.md
```

```bash
# Operator numeric: add owner+group read without a lookup table
chmod +440 dump.rdb
```

```bash
# Guarded recursion of a large tree: only what changes gets printed
chmod -Rc g-x /var/cache/build | tail
```

## Nuances and Gotchas

- **`+X` vs `+x` is one keystroke of disaster.** `chmod -R +x dir` makes every file executable; `+X` restricts to directories and already-executable files. Any recursive chmod on a mixed tree should use `X` unless it really means "everything executes".
- **The who-omitted symbolic form consults your umask.** `chmod +w` under umask 022 does not grant group/other write; the same command under umask 000 does. Scripts that must behave identically everywhere use explicit `a+w`/`ug+w`.
- **Numeric modes on directories silently preserve setuid/setgid** (`chmod 755` on a `2755` dir is a no-op for the special bit). Use `=755`, `00755` (five digits), or symbolic `g-s` to clear them. The preservation is a GNU extension; other systems may differ, so portable scripts clear special bits symbolically.
- **Numeric modes on files do the opposite** — they clear setuid/setgid/sticky unless the fourth digit says otherwise. "I ran chmod 775 and lost setgid on the binary" is a real support ticket.
- **GNU chmod clears a regular file's setgid bit when the caller is not in the file's group** (unless privileged). Group-migration scripts that chmod after chgrp can undo their own setgid setup.
- **umask warnings can fail your script.** The `chmod -w file` mismatch warning exits 1; under `set -e` a harmless-looking cleanup line aborts the script. Use `a-w`.
- **`o+s`, `u+t`, `g+t` are silent no-ops** (GNU): sticky only exists as `+t`/`a=t`, setuid only via `u`. A typo there changes nothing and prints nothing.
- **With ACLs present, `g` bits manipulate the mask**, not the owning group's entry — after `setfacl`, a subsequent `chmod g=r` can silently strip effective rights of named ACL users. Inspect with `getfacl` before chmodding ACL'd files.
- **chmod does not apply to symlinks at all**; a `-R -L` traversal chmodding through attacker-writable links is a documented escalation risk. Keep the `-H` default or use `find -type f -exec chmod`.
- **Root permissions still lose to filesystem reality**: an immutable file (`chattr +i`) or a read-only mount refuses chmod with a clear error regardless of `u+s`-style arguments.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All operands processed successfully |
| nonzero (1 in practice) | Invalid mode, inaccessible operand, permission denied, or the who-omitted warning case; remaining operands are still processed |

## Related Commands

- [`chown`](./chown.md) — changes owner and/or group; the other half of every permissions fix.
- [`chgrp`](./chgrp.md) — changes group ownership only; membership-gated.
- [`chcon`](./chcon.md) — changes the SELinux context, a layer of control orthogonal to mode bits.
- [`stat`](./stat.md) — reads modes back (`%a` octal, `%A` symbolic, `%f` raw).
- [`install`](./install.md) — copies files and sets mode atomically (`install -m 755`).
- [`../../shell/find.md`](../../shell/find.md) — `find -perm` selects files by mode for targeted chmods.
- [`../../shell/bash.md`](../../shell/bash.md) — `umask`, the creation-time counterpart to chmod.
- [`../../admin/permissions.md`](../../admin/permissions.md) — the full permission model, ACLs included.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: What is the difference between `x` and `X` in a symbolic mode?

`x` sets execute/search unconditionally for the selected users. `X` sets it only when the file is a directory or *some* user already has execute permission — so `chmod -R u=rwX,g=rX,o=` makes directories traversable and keeps scripts runnable while leaving ordinary data files non-executable. `X` has no octal equivalent, which is why `chmod -R 744` on a mixed tree is the classic "every file became executable" mistake.

### Q: Explain how umask interacts with chmod.

Two separate mechanisms. Creation time: the kernel applies `mode & ~umask` to new files — nothing to do with chmod. Inside chmod: when the symbolic mode omits the `who`, GNU chmod applies the operation to all users except bits set in the umask — so with umask 022, `chmod +w f` grants write to the owner only, while `chmod a+w f` ignores the umask entirely. The who-omitted form is a convenience filter, not a bug, and GNU chmod even warns (exit 1) when `chmod -w` produces something different from `a-w` would.

### Q: Why does `chmod 755 dir` not remove the setgid bit from a 2755 directory, and what would?

GNU chmod deliberately preserves setuid/setgid on directories for plain numeric modes so that routine permission sweeps do not destroy setgid group-sharing trees. To clear the bit you must express it: symbolically (`chmod g-s dir`), with an operator numeric mode (`chmod =755 dir`), or with five octal digits (`chmod 00755 dir`). The preservation rule is a GNU extension — POSIX allows either behavior — which is exactly why portable scripts clear special bits symbolically.

### Q: You ran `chgrp` on a binary and its setgid bit disappeared. Why, and how do you guard against it?

Ownership changes go through `chown(2)`, and Linux clears setuid/setgid on regular files when ownership changes — partly because GNU chmod also strips setgid when the acting user is not a member of the file's group. Even a no-op chown/chgrp with identical owner and group can clear the bits. Guard by doing the ownership changes first and re-applying special bits after (`find ... -perm -2000` to audit, then `chmod g+s`), or run the change as a user who is a member of the file's group.

### Q: A file is `rw-r--r--+` and the group can't actually read it after `chmod g=r--`. What happened?

The trailing `+` means the file has a POSIX ACL, and in that state the group triad is the ACL **mask**, not the owning group's entry. `chmod g=r--` rewrote the mask, which caps the effective rights of every named user and group in the ACL to read-only (or nothing, if you had used `g=`). The fix is to think in ACL terms: `getfacl` to inspect, `chmod g=` entries via setfacl, and remember that chmod's group bits now manage the mask rather than a simple group permission.

### Q: Why do setuid shell scripts not work, and is that chmod's fault?

No — it is the kernel's deliberate policy: when the kernel executes an interpreter-led script (shebang), it drops the setuid/setgid bits so that `#!/bin/sh` scripts cannot be raced into arbitrary code execution with elevated privileges. `chmod u+s script.sh` sets the bit and `ls` shows it, but exec ignores it for scripts; setuid is only honored on real binaries. The standard workaround is `sudo` or a tiny setuid C wrapper, not more chmod.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/chmod.1.en.html)
