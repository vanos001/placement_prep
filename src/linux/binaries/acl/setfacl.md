# setfacl — set file access control lists

## Overview

`setfacl` is the primary tool for attaching and editing POSIX ACLs on files and directories: it grants named users and groups permissions beyond the nine mode bits, manages the `mask` ceiling over the group class, and installs the *default* ACLs that make new files under a directory inherit policy. It ships in Debian's `acl` package at `/usr/bin/setfacl` alongside `getfacl` (the dump/read side) and `chacl` (the IRIX-heritage setter).

The mental model to bring: an ACL is a small table of `(class, subject, permissions)` entries stored in the `system.posix_acl_access` kernel xattr, and `setfacl` is its editor — with `-m` merging entries, `-x` removing them, `--set` replacing the whole table, and `-d` switching the operation to a directory's default ACL instead of its access ACL.

It is often confused with `chmod` (which it complements, not replaces: `chmod` maps to the three base entries and, once an ACL is extended, to the mask), with `chown` (ownership is not an ACL concept — the `user::` entry *is* the owner's mode bits), and with `chacl` (same kernel state, older one-shot grammar).

| Field | Value |
| --- | --- |
| Package | acl (Debian bookworm: 2.3.x) |
| Man section | 1 |
| Path | /usr/bin/setfacl |
| First appeared | Linux ACL project late 1990s (IRIX/Solaris model ported) |
| Standards | POSIX 1003.1e draft 17 semantics (withdrawn draft, de-facto Linux standard) |

## Synopsis

```
setfacl [-bkndRLPvh] {-m|-M|-x|-X} ACL_ENTRIES FILE...
setfacl [-bkndRLPvh] --set=ACL_ENTRIES|--set-file=FILE FILE...
setfacl [-bkndRLPvh] {-b|-k} FILE...
setfacl [-bkndRLPvh] --restore=FILE
setfacl [-bkndRLPvh] --test ACL_ENTRIES FILE...
```

The operation families:

```
setfacl -m u:deploy:rw file          # modify/merge entries
setfacl -x u:deploy file             # remove specific entries
setfacl --set u::rw-,g::r--,o::---,u:deploy:rw file   # replace whole ACL
setfacl -b file                      # strip to the minimal (mode-bit) ACL
setfacl -k dir                       # remove a directory's default ACL
setfacl --restore=/root/proj.acl     # re-apply a getfacl dump
```

## How It Works

### Entry grammar

Entries are `tag[:qualifier]:permissions`, comma-separated, run together without spaces; `X` is the smart-execute bit (grant `x` only where the file already has it for someone or is a directory):

```
u[:name]:perms        user entry — no name = the file's owning user
g[:name]:perms        group entry — no name = the file's owning group
m[:name]:perms        the mask (qualifier ignored; m:: is conventional)
o[:name]:perms        other (no qualifier meaningful)
d:ENTRY               prefix applying ENTRY to the default ACL of a directory
```

Permissions may be the `rwx-`/`X` letters, octal digits (`u:deploy:6`), or zero (`u:deploy:-`). Numeric IDs work where names are unnecessary: `setfacl -m u:1000:rx file` on a system without passwd entries. A leading `default:` (or `d:`) turns the entry into default-ACL material, which is only legal on directories.

```bash
# Same grant, three spellings
setfacl -m u:deploy:rw- file
setfacl -m u:deploy:6 file
setfacl -m u:1000:6 file
```

The command shape decomposes cleanly, and interviews probe each slot:

```
setfacl  -d  -m  g:oncall:rx  /srv/proj
   │      │    │        │          │
   │      │    │        │          └─ path (a directory, because -d)
   │      │    │        └─ tag:qualifier:perms — one ACL entry
   │      │    └─ operation: merge (vs -x remove, --set replace)
   │      └─ scope switch: target the DEFAULT ACL, not the access ACL
   └─ the tool
```

### -m merges, --set replaces

`-m` and `-M` (entries from a file) merge: unspecified entries survive untouched. `--set` and `--set-file` replace the entire ACL, and because a valid ACL always needs the three base entries, `--set` refuses anything that omits them — that refusal is the feature: you cannot accidentally drop `other::` or the owning entries into an invalid state. The copy idiom leans on the pair:

```bash
# Clone ACLs from a template file onto a whole tree
getfacl template.conf | setfacl --set-file=- -R /etc/app/conf.d/
```

`-M` and `-X` take their entries from a file (or stdin), one entry per line, and accept `#` comment lines — which is precisely why getfacl output is valid input: the tool tolerates the headers and applies the entries. That makes bulk changes reviewable: the entry file goes into the change ticket, the command in the runbook.

`-b` removes every extended entry (back to pure mode bits), `-k` removes a directory's default ACL, and `-x`/`-X` delete specific named entries — `-x u:deploy file`, not `-x u:deploy:rw`, since it matches on the subject.

### Mask recalculation rules

The mask is the ceiling applied to every group-class entry (named users, named groups, owning group). Its lifecycle is where most ACL bugs live:

- With `-m`/`-M`/`--set`, if you do not pass a mask entry, `setfacl` **recalculates** it as the union of all group-class permissions, so the default behavior never creates a grant that is instantly masked away.
- Passing an explicit `m::perms` entry sets the ceiling by hand; `-n`/`--no-mask` keeps the existing mask untouched (use it when a policy engine owns the mask).
- `chmod` on an extended-ACL file edits the mask through the group bit field — `chmod g-w` after granting `u:deploy:rw` drops deploy's effective write too. `getfacl` renders the clamp as `#effective:` comments.
- Removing entries with `-x` does not shrink the mask; once the last extended entry is gone the ACL collapses back to minimal and the mask disappears with it.

### Default ACLs and inheritance

With `-d` (or the `d:` entry prefix), the operation targets the directory's default ACL — the inheritance template for new children, not an access policy:

```bash
# Team-shared tree: access ACL now, plus template for everything created later
setfacl -m g:oncall:rwx /srv/proj
setfacl -d -m g:oncall:rx  /srv/proj
$ touch /srv/proj/newfile && getfacl /srv/proj/newfile
group:oncall:r-x                       #effective:r--
```

Inheritance intersects with the creating process's mode: a file created as `0666` intent never gains `x` from the default ACL, and subdirectories receive the default ACL again, cascading policy down the tree. Existing files are untouched — defaults only speak to the future, which is why real rollouts pair `setfacl -d -m` with a one-time `setfacl -R -m`.

The `-d` flag and the `d:` entry prefix are two spellings of the same operation, and scripts mix them freely:

```bash
# Identical results:
setfacl -d -m g:oncall:rx /srv/proj
setfacl -m d:g:oncall:rx /srv/proj

# The prefix form wins when one call touches both ACLs:
setfacl -m g:oncall:rwx,d:g:oncall:rx /srv/proj
```

### Recursion and symlinks

`-R` walks trees applying the operation to every file and directory; `-L` follows symlinks encountered, `-P` (the default) never does. Recursive *modification* (`-R -m`) and recursive *restore* (`--restore`) are the two bulk flows, and they behave differently with masks: `-R -m` recalculates masks per file, while `--restore` applies the dumped ACLs verbatim.

### The --restore backup flow

`getfacl -R` and `setfacl --restore` are designed as a pair: getfacl emits its `# file:` comment headers with leading slashes stripped by default, so a dump taken from inside a directory re-applies relative to wherever you run the restore:

```bash
# Backup and reproduce a whole tree's ACL state
$ cd /srv && getfacl -R proj > /root/proj.acls
$ cd /mnt/newroot/srv && setfacl --restore=/root/proj.acls
```

`--restore` reads exactly the getfacl format (comment headers carry the filename), which is also why getfacl output doubles as the audit artifact reviewed in change tickets. `--test` prints what a modification *would* do without touching anything — the dry run for scripted rollouts.

### When it fails

Failure modes cluster by layer, and naming the layer is half the diagnosis:

- **Filesystem layer**: on vfat, pseudo-filesystems, or `noacl` mounts, every operation fails with `Operation not supported`. Gate bulk scripts on one probe call against a known-writable file.
- **Entry layer**: malformed grammar, missing base entries under `--set` (which requires `u::`, `g::`, and `o::`), permissions on `-x` entries (subjects only — `-x u:deploy:rw` is rejected), or qualifiers that do not resolve to accounts. Entry errors abort before anything is modified.
- **Scope layer**: `d:`-prefixed or `-d`-targeted entries applied to plain files fail — default ACLs exist only on directories.
- **Permission layer**: lacking write access to the file's metadata (owner, or `CAP_FOWNER`) fails individual files during a `-R` walk; with recursion the walk continues and the tool exits nonzero at the end.

## Options That Matter

### Operations

| Option | Effect |
| --- | --- |
| `-m` | Merge/modify entries given on the command line |
| `-M FILE` | Merge entries read from FILE (or `-` for stdin) |
| `-x` / `-X` | Remove specific entries (subject-matched, permissions ignored) |
| `--set=` / `--set-file=` | Replace the complete ACL; base entries required |
| `-b` | Remove all extended entries (file returns to mode-bit ACL) |
| `-k` | Remove the default ACL of a directory |
| `--restore=FILE` | Re-apply a `getfacl` dump; paths come from its `# file:` headers |
| `--test` | Print the result without modifying anything |

### Scope

| Option | Effect |
| --- | --- |
| `-R` | Recurse into directories |
| `-L` / `-P` | Follow / never follow symlinks during recursion |
| `-d` | Operate on the default ACL (entries or `d:` prefix) |
| `-n` | Do not recalculate the mask (keep the existing one) |

## Usage Patterns

```bash
# Grant a deployment account write access to one config file
setfacl -m u:deploy:rw /srv/app/config.ini
```

```bash
# Revoke a single named grant without touching anything else
setfacl -x u:intern /srv/app/config.ini
```

```bash
# Shared directory: group write now, read/traverse template for new files
setfacl -m g:team:rwx /srv/shared && setfacl -d -m g:team:rx /srv/shared
```

```bash
# Roll the same grant across an existing tree and its future
setfacl -R -m g:oncall:rx /srv/proj && setfacl -d -m g:oncall:rx /srv/proj
```

```bash
# Cap everything: explicit mask so no group-class entry exceeds read+execute
setfacl -m m::rx /srv/proj
```

```bash
# Clone one file's ACL onto its siblings
getfacl good.conf | setfacl --set-file=- /etc/app/*.conf
```

```bash
# Preview a mass change before applying it (dry run to stdout)
setfacl --test -R -m u:audit:rX /var/log/app
```

```bash
# Clean a file back to plain mode bits before handing it to chmod workflows
setfacl -b legacy.cfg
```

```bash
# Remove the inheritance template once a tree is finalized
setfacl -k /srv/proj/frozen
```

```bash
# Full-tree backup and later restore of ACL state
cd /srv && getfacl -R proj > /root/proj.acl
cd /mnt/restore/srv && setfacl --restore=/root/proj.acl
```

```bash
# Grant execute only where it already exists somewhere (the X permission)
setfacl -m u:ci:rX /opt/app/bin/
```

```bash
# Numeric UID grant for an account that does not resolve on this host
setfacl -m u:1500:rw /data/export/share.csv
```

```bash
# Per-user deny: a zero-permission named entry short-circuits group evaluation
# for that account (named users are checked before groups, so --- wins there)
setfacl -m u:former-admin:--- /srv/secret
```

```bash
# Repair a mask that a chmod clamped: set it back to the group-class union
setfacl -m m::rw /srv/app/config.ini
```

```bash
# Bulk-apply reviewed entries from a file (comments and headers tolerated)
setfacl -M /tmp/reviewed.entries /etc/app/conf.d/*
```

```bash
# Remove a named group grant without disturbing anything else
setfacl -x g:oncall /srv/proj/2026/notes.txt
```

```bash
# Keep the existing mask while adding an entry (policy engines own the mask)
setfacl -n -m u:deploy:rw /srv/app/config.ini
```

## Nuances and Gotchas

- **`chmod` after `setfacl` rewrites the mask**, not the owning-group entry, once the ACL is extended. The failure signature is a grant that "was working yesterday": look for `#effective:` in `getfacl` output before blaming the grant.
- **`-x` matches subjects, not permissions** — `setfacl -x u:deploy:rw` is rejected because `-x` entries take no permission field; write `setfacl -x u:deploy`.
- **`--set` demands base entries**; using it with a fragment is a hard error, while `-m` would have merged the fragment. Choose deliberately: merge for grants, replace for policy resets.
- **Recursive operations on symlink farms**: `-P` (default) never follows symlinks, so `-R -m` on a tree of links quietly modifies nothing behind them; `-L` is the opt-in and a loop risk.
- **Filesystem support is silent and fatal**: on vfat or a `noacl` mount, `setfacl` fails with `Operation not supported` — gate scripts on one probe call before bulk runs.
- **Backups that ignore ACLs are the default**: `cp`, plain `tar`, and editor-rename saves all drop them; only `cp -a`-class copies, `tar --acls`, `rsync -A`, or the getfacl/setfacl text pair preserve state.
- **Named-entry grants on files writable via group membership can mislead audits** — a user's effective access is the union of owner/named/group/other evaluation, so removing one entry may not remove access that arrived via another class.
- **Default ACLs never act retroactively** — shipping `setfacl -d -m` without the paired `setfacl -R -m` is the half-deployed state every reviewer should catch.
- **Zero-permission entries are not no-ops**: `u:app:---` creates a named-user entry that the evaluation order checks *before* any group, so that account loses even group-derived access — a per-user deny mechanism, not a style error.
- **ACLs are inode properties, so hard links share them**: an entry added through one name appears on every link to the same inode — ACL state does not follow directory-entry names the way your mental model probably does.
- **Names and numeric IDs are resolved at call time**: mixing `u:deploy` and `u:1500` spellings across hosts with differing UID maps can grant the *wrong* account; pick one convention per codebase and freeze it in the getfacl dump (`-n`) that reviews it.
- **`--restore` expects the getfacl dump format, not bare entries** — feeding it a plain entry list fails because there are no `# file:` headers to derive paths from; use `-M`/`-m` for entry lists and `--restore` for dumps.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested ACL modifications succeeded |
| nonzero | At least one operation failed (bad entry, unsupported filesystem, permission denied) |

## Related Commands

- [Collection overview](./overview.md) — the ACL model, evaluation order, mask semantics, filesystem support.
- [`getfacl`](./getfacl.md) — the read side of every setfacl operation; its output is `--restore`'s input.
- [`chacl`](./chacl.md) — the IRIX-heritage one-shot setter driving the same kernel state.
- [Permissions](../../admin/permissions.md) — the mode-bit model setfacl extends and the `chmod`-edits-mask interplay.
- [Users and groups](../../admin/users-groups.md) — where the subjects of named entries come from.
- [Binaries part overview](../overview.md) — the chapter hub.

## Interview Questions

### Q: What is the difference between `setfacl -m` and `setfacl --set`?

`-m` merges the given entries into the existing ACL — base entries and other grants survive — while `--set` replaces the entire ACL and therefore requires the base entries (`u::`, `g::`, `o::`) to be present in the input, refusing an invalid fragment. Practically: `-m` for incremental grants and revocations, `--set` (or `--set-file` fed by `getfacl`) for authoritative policy application.

### Q: A user reports losing access after an admin ran `chmod` on an ACL-managed file. Walk through the mechanism.

Once an ACL is extended, `chmod`'s group bits edit the `mask` entry, and the mask caps every group-class grant including named users. So `chmod g-w` on a file carrying `u:deploy:rw` silently drops deploy to the mask's remainder, and `getfacl` shows it as `#effective:r--`. The fix is recalculating the mask (`setfacl -r` or an explicit `-m m::...`) or changing the owning-group entry instead of the mask.

### Q: How do you make a directory grant apply to files created in the future?

Two-layer answer: `setfacl -R -m g:team:rx /srv/proj` covers what exists today, and `setfacl -d -m g:team:rx /srv/proj` installs the default ACL that new children inherit — files receive it intersected with their creation mode (no `x` unless the create call asked), subdirectories also receive the default ACL itself so inheritance cascades. Defaults are templates only: they never alter existing files.

### Q: What does `setfacl -b` do, and why is it useful before audits?

It removes every extended entry — named users, named groups, mask — leaving the minimal three-entry ACL that is exactly the mode bits. That normalizes a file back into the pure `chmod` world, which is how you clean up legacy ACL sprawl before an audit and how you prove "this file's access is only the mode bits" without reading entries.

### Q: How do you copy one file's ACL to many files?

Dump it and feed the dump back: `getfacl good.conf | setfacl --set-file=- -R /etc/app/conf.d/`. The pipe works because getfacl's output format is precisely setfacl's input format (`--set-file` for full replacement), and the `-` makes setfacl read the stream. For whole trees, the same pair appears as `getfacl -R . > backup` plus `setfacl --restore=backup`, which is also the standard ACL backup idiom.

### Q: Where does setfacl actually store the entries, and what happens on a filesystem without support?

Entries live in the kernel xattr `system.posix_acl_access` (and `system.posix_acl_default` on directories), so support is a filesystem property: ext4, XFS, Btrfs, F2FS, tmpfs implement it; vfat and pseudo-filesystems do not and `setfacl` fails with `Operation not supported`. That storage model also explains why metadata-preserving copies need explicit flags and why ACLs never survive a copy that recreates the inode.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/acl/setfacl.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/acl/)
