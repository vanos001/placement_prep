# chgrp — change group ownership of files

## Overview

`chgrp` sets the group that owns one or more files — the `gid` half of every inode's ownership pair. It is the tool behind shared-directory workflows: giving a `www-data` group access to a web root, handing log directories to an `adm`-style audit group, or fixing ownership after extracting a tarball as root. Where `chmod` decides *what* a group may do, `chgrp` decides *which* group is in the picture at all.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/chgrp`, from upstream GNU coreutils. It is POSIX-standardized and available on every Unix-like system, so scripts can rely on the core invocation `chgrp GROUP FILE...` being there.

It is often confused with two siblings. `chown :group file` does the same job through the same `chown(2)` system call — `chgrp` exists for clarity and for its group-only grammar. And `chmod g+rw` looks similar but touches permission bits, not ownership.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/chgrp` |
| First appeared / lineage | Early AT&T Unix; GNU coreutils implementation |
| Standards | POSIX.1-2018 (`chgrp`, incl. `-H`/`-L`/`-P` traversal) |

## Synopsis

```
chgrp [OPTION]... GROUP FILE...
chgrp [OPTION]... --reference=RFILE FILE...
```

Main forms:

```
chgrp staff file.txt          # group -> staff, symlinks dereferenced
chgrp -h staff link           # change the symlink itself
chgrp -R -H staff /srv/app    # recursive, follow CLI-arg symlinks
chgrp --reference=ref.txt f1  # copy ref.txt's group onto f1
chgrp +1001 file              # numeric gid, forced (no name lookup)
```

`GROUP` is a group name or numeric gid. With `--reference`, the group is taken from `RFILE` instead. A `-` operand means standard input where that makes sense.

## How It Works

### The membership rule

`chgrp` is a thin wrapper over `chown(2)`/`fchownat(2)` with only the group field set. The kernel enforces the policy: an unprivileged process may change a file's group **only if it owns the file and is a member of the target group**. Changing a file to a group you do not belong to would let you launder ownership, so it is refused:

```bash
$ chgrp adm report.txt
chgrp: changing group of 'report.txt': Operation not permitted
$ echo $?
1
```

The GNU manual words it as system-dependent, but the portable behavior — the one Linux implements — restricts you to groups you are a member of. Only `CAP_CHOWN` (effectively root) bypasses the check. Sessions snapshot supplementary groups at login, so if you were just added to a group, `chgrp` keeps failing until you re-login or run `newgrp`.

```bash
# Check membership before blaming chgrp
$ id -Gn | tr ' ' '\n' | grep -x staff || echo "not a member"
```

### Symlinks: dereference is the default

Given a symlink on the command line, `chgrp` changes the group of the file the link *points to*; the link itself keeps its group. `-h`/`--no-dereference` inverts this and relabels the link itself (Linux supports this via `lchown(2)`). This matters when a tree contains links to shared data — the link is a separate inode with its own ownership:

```
file (gid: staff)  <─── link ── chgrp devs link  ──> file becomes group devs
                              └─ chgrp -h devs link ─> link itself becomes devs
```

### Recursive traversal: -R with -H, -L, -P

With `-R`, three mutually exclusive flags control symlink handling; **only the last one on the command line wins, and `-P` is the default**:

```
            ┌────────────────────────┬────────────────────────────┐
            │ symlink to a dir as    │ symlink to a dir found     │
  mode      │ a command-line arg     │ inside the tree            │
────────────┼────────────────────────┼────────────────────────────┤
  -R (-P)   │ not traversed          │ not traversed; the link    │
            │                        │ itself is relabeled        │
  -R -H     │ traversed              │ not traversed              │
  -R -L     │ traversed              │ traversed (recursively)    │
────────────┴────────────────────────┴────────────────────────────┘
```

`-L` is the aggressive option: every directory symlink met during the walk is descended into, which can loop (coreutils detects cycles) or — if an attacker can write to the tree — relabel targets outside the intended scope. `-H` follows only the arguments you actually typed. GNU chose `-P` as chgrp's default so that recursion never escapes the tree; note the family inconsistency that `chmod -R` defaults to `-H` instead.

### Reference and guard options

`--reference=RFILE` copies `RFILE`'s group onto every operand — handy for "make it look like that one"; the reference file is always dereferenced if it is a symlink. `--from=OWNER[:GROUP]` gates the change: files not matching the current owner/group spec are skipped. It exists to shrink the race window in migrations (see Nuances). `-c` reports only files that actually changed, `-v` reports every operand, `-f` swallows most error messages — the trio follows the common coreutils verbosity convention.

## Options That Matter

| Option | Effect |
|---|---|
| `-c, --changes` | Verbose output only for files whose group actually changes |
| `-f, --silent, --quiet` | Suppress most error messages (bulk jobs, cron) |
| `-v, --verbose` | Diagnostic for every file processed |
| `-h, --no-dereference` | Change the symlink itself, not its target (uses `lchown`) |
| `--dereference` | Change the referent of each symlink (the default) |
| `--reference=RFILE` | Use RFILE's group instead of naming a GROUP |
| `--from=OWNER[:GROUP]` | Only change files whose current owner/group matches |
| `-R, --recursive` | Operate on directories and their contents |
| `-H` / `-L` / `-P` | Traversal policy for `-R`: follow CLI-arg symlinks / follow all / follow none (default) |
| `--preserve-root` | Refuse to recurse on `/`; NOT the default (unlike `rm`) |

## Usage Patterns

```bash
# Hand a web tree to the web server's group, then grant it write access
sudo chgrp -R www-data /srv/app && sudo chmod -R g+rwX /srv/app
```

```bash
# Make a shared drop box self-maintaining: group + setgid bit
sudo chgrp staff /srv/shared && sudo chmod 2775 /srv/shared
```

```bash
# Copy the group from a known-good file instead of naming it
chgrp --reference=/var/log/auth.log app.log
```

```bash
# Relabel a symlink itself without touching the (shared!) target
chgrp -h deploy /srv/releases/current
```

```bash
# Recursive with explicit traversal policy: follow only CLI-arg symlinks
chgrp -R -H staff /u
```

```bash
# Audit a big tree: -c shows only what changed
sudo chgrp -Rc staff /srv/share | tail
```

```bash
# UID migration with a guard: only files currently group 'deploy'
sudo chgrp -R --from=:deploy staff /srv/legacy
```

```bash
# Verify membership first — the most common cause of "Operation not permitted"
id -Gn | tr ' ' '\n' | grep -x staff || newgrp staff
```

```bash
# Find what is in a group afterwards
find /srv -group staff | head
```

```bash
# Bulk job in cron: ignore unreadable stragglers
chgrp -f staff /var/lib/collector/*.dat 2>/dev/null || true
```

```bash
# Numeric gid, forcing interpretation as an ID even if a group named "1001" exists
chgrp +1001 payload.bin
```

## Nuances and Gotchas

- **Membership is checked at call time, against your session's groups.** Groups added via `/etc/group` or `usermod -aG` do not apply to already-running shells; `chgrp` keeps returning `Operation not permitted` until you re-login or `newgrp`. This trips up most provisioning scripts run from long-lived sessions.
- **A successful chgrp/chown can clear setgid (and setuid) bits from regular files.** The kernel strips special bits on `chown(2)` — even a no-op call with identical owner/group clears them (verified: `chmod g+s f; chown :z f` dropped the bit). If you chgrp files *inside* a setgid-managed tree, re-check the bits afterwards.
- **`-P` is chgrp's traversal default; `-H` is chmod's.** The four attribute tools do not agree, so muscle memory from `chmod -R` is wrong here. Spell the traversal flag out in scripts.
- **`-R` combined with dereferencing is a documented security risk.** During traversal an attacker able to write to the tree can swap in a symlink to `/etc`; with `-L` (or `--dereference`-style behavior) your chgrp lands on the target. Prefer the `-P`/`-H` defaults, or `find ... -exec chgrp` for full control.
- **`--preserve-root` is not the default.** `chgrp -R GROUP /` is happily attempted; `rm` protects `/` by default, chgrp/chown/chmod do not. Put `--preserve-root` in an alias or wrapper for interactive use.
- **`--reference` dereferences its argument.** `chgrp --reference=link f` copies the *target's* group, not the link's — surprising when the link was deliberately relabeled with `-h`.
- **Numeric specs are name-lookups first.** POSIX says `chgrp 42 f` first tries a group *named* `42`; only if that fails is it a gid. On a system where someone created group `42`, you would set a different group than intended. Prefix `+` to force numeric: `chgrp +42 f`.
- **Exit status is a summary, not a stop signal.** chgrp continues past failing operands and reports a nonzero status at the end; a `set -e` script sees `1` only after processing everything. Parse `-c`/`-v` output if you need a change log.
- **Filesystems without Unix ownership (vfat, some FUSE mounts) reject chgrp** with `Operation not permitted` regardless of membership; nothing is wrong with your groups.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All operands processed successfully |
| nonzero (1 in practice) | Any failure: not a group member, nonexistent operand, permission denied; later operands are still processed |

## Related Commands

- [`chown`](./chown.md) — changes owner and group; `chown :group f` is the chgrp equivalent.
- [`chmod`](./chmod.md) — changes the permission bits that the (new) group maps onto.
- [`chcon`](./chcon.md) — changes the SELinux security context: a third ownership-like axis.
- [`stat`](./stat.md) — shows current owner/group (`%U`, `%G`, `%g`) and supports `-c '%G'` formatting.
- [`groups`](./groups.md) — prints your group memberships, the thing chgrp validates against.
- [`install`](./install.md) — copies files while setting owner/group/mode in one step.
- [`../../admin/permissions.md`](../../admin/permissions.md) — the permission model chgrp plugs into.
- [`../../admin/users-groups.md`](../../admin/users-groups.md) — where groups come from and how membership is set.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why does `chgrp staff file` fail with "Operation not permitted" even though the file is mine?

Because unprivileged users may only reassign a file to a group they themselves belong to — otherwise you could hand the file to any group on the system. Check `id -Gn` for membership; if the group was just granted, your session still carries the old group set from login, so re-login or use `newgrp staff` before retrying. Root (`CAP_CHOWN`) is exempt.

### Q: Explain the difference between `chgrp -R -H`, `-L`, and `-P`.

They only matter with `-R`. `-P` (the default) never traverses symlinks: links met inside the tree are relabeled themselves but their targets are untouched. `-H` additionally traverses symlinks to directories that appear as command-line arguments. `-L` traverses every directory symlink encountered during the walk, recursively. `-L` can escape the intended tree (loops, or relabeling attacker-planted targets), which is why GNU made the safer `-P` the default for chgrp/chown.

### Q: Is there any difference between `chgrp staff f` and `chown :staff f`?

Functionally no — both end in the same `chown(2)` call with only the group changed, and both impose the same membership requirement. The differences are surface: chgrp's grammar takes the group as a plain operand, while chown uses the `[OWNER][:GROUP]` notation; chown additionally supports `user:` to set the group to the user's login group. Choose chgrp in scripts to make the intent (group-only change) obvious.

### Q: What happens to a file's setgid bit when you chgrp it?

On Linux, a successful ownership change — including a chgrp that sets the "same" group — clears the setgid (and setuid) bits of regular files; the kernel does this so elevated-execution bits cannot outlive an ownership change. GNU chmod goes further and documents that chmod itself clears setgid when the acting user is not in the file's group. Practical consequence: after scripted re-ownership of a tree, audit special bits with `find -perm -2000` and reapply them deliberately.

### Q: What problem does `chgrp --from` solve that a plain recursive chgrp does not?

It narrows the race window in mass re-ownership. The naive pattern `find / -group OLD | xargs chgrp NEW` tests the group and then changes it as separate steps — files created or re-grouped in between are changed too. With `chgrp -R --from=:OLD NEW /path` the check and the change happen inside one call per file, so only files that still carried the old group at the moment of the syscall are touched. It is a mitigation, not a guarantee, but it is the documented safer recipe.

### Q: How do you make a directory where all new files automatically belong to a shared group?

You do not use chgrp per file: set the directory's group once with chgrp, then set its setgid bit (`chmod 2775` or `chmod g+s`). The kernel then assigns the directory's group to every file and subdirectory created inside it, and new subdirectories inherit the setgid bit themselves. chgrp is the one-time setup; the setgid bit is the ongoing mechanism — which is also why clearing that bit accidentally with numeric chmod is so costly.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/chgrp.1.en.html)
