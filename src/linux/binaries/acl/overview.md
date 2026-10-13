# POSIX ACLs — Collection Overview

Access control lists extend the nine-bit `rwxrwxrwx` permission model with *named* per-user and per-group entries: the ability to say "and user `deploy` may write this file" or "group `oncall` may read this whole tree" without reshaping your users and groups around every exception. Mode bits stop scaling the moment a second team needs different access to the same tree — you either invent groups per exception (`release-readers`, `staging-writers`, ...) or you use ACLs. Linux implements the model of POSIX 1003.1e draft 17 — a withdrawn standard whose ACL part nevertheless became the de-facto specification every Unix except the OpenBSDs followed. This collection covers the three userland tools that drive it — `getfacl`, `setfacl`, and `chacl` — one page each, with this page carrying the shared model.

| Field | Value |
| --- | --- |
| Package | acl (Debian: getfacl, setfacl, chacl) |
| Man section | 1 (tools), 5 (`acl` entry syntax) |
| Path | /usr/bin/getfacl, /usr/bin/setfacl, /usr/bin/chacl |
| Lineage | POSIX 1003.1e draft 17 (withdrawn); Linux libacl |
| Standards | POSIX-draft ACL semantics; kernel xattrs `system.posix_acl_access` / `system.posix_acl_default` |

## The Model: Entries and Classes

An ACL is an ordered set of entries, each naming a subject class and a permission triple. Every file has at least the three **base** entries, which are exactly the classic mode bits; anything more makes it an **extended** ACL.

```
entry = tag[:qualifier]:perms            perms ⊆ {r,w,x,-}

user::rwx          owning user  (the file owner bit field)
user:deploy:rw-    named user   (per-account grant)
group::r--         owning group (the group bit field)
group:oncall:r-x   named group  (per-group grant)
mask::rwx          maximum perms the group class may receive
other::r--         everyone else (the other bit field)
```

| Tag | Class | Qualifier | Meaning |
| --- | --- | --- | --- |
| `user` | owner or named-user class | optional | `user::` is the owner's mode bits; `user:name` is a grant to one account |
| `group` | group class | optional | `group::` is the owning group's bits; `group:name` grants one group |
| `mask` | group class | none | ceiling over all group-class entries; exists only on extended ACLs |
| `other` | other class | none | everyone who matched nothing above |

The `mask` entry is the model's load-bearing wall. Named users and groups, together with the owning group, form the *group class*, and the mask caps the effective permissions of every entry in that class. Granting `user:deploy:rwx` on a file whose mask is `r--` gives deploy effectively `r--` — nothing more — which is how one `chmod` through the group bits can silently throttle every fine-grained grant on the file. (`setfacl`'s `X` permission is input shorthand — "execute only if some x bit already exists or the file is a directory" — it never appears stored.)

## Evaluation Order

Kernel access checks walk the classes in order, first match wins, and the mask is applied *after* the class match but *before* the decision:

```
process asks for access
  ├─ euid == file owner?        → user:: entry, decide
  ├─ euid matches a named user? → that entry ANDed with mask, decide
  ├─ egid/supplementary groups match owning or named group?
  │                             → best-matching group entry ANDed with mask, decide
  └─ else                       → other:: entry, decide
```

Three consequences worth internalizing. Ownership trumps everything: the owner's `user::` entry ignores the mask entirely, so an owner with `---` in the owner bits is locked out even with a permissive mask. Named users are checked before any group, so a per-account entry overrides group-based denials. And "no match anywhere in the group class" falls straight through to `other::` — a named-group entry you don't qualify for neither helps nor hurts you.

```bash
# Worked example on: user::rwx, user:deploy:rw-, group::r--, group:oncall:r-x,
#                    mask::rw-, other::---
# alice (owner), wants w           → user::rwx             → allowed
# deploy, wants w                  → user:deploy:rw- ∧ mask → rw-    allowed
# member of oncall, wants x        → group:oncall:r-x ∧ mask → rw-   denied
# anyone else, wants r             → other::---             → denied
```

## Minimal ACLs Are Mode Bits

A file with only the three base entries has a *minimal* ACL, and its storage and meaning are exactly the traditional mode: `chmod 640` and the `user::rw-, group::r--, other::---` triple are two views of the same data. Tools therefore translate freely — `ls -l` shows the base entries as the familiar string, `getfacl` prints them as entries even on files with no extended ACL, and `setfacl -b` strips a file back to that minimal form.

```bash
$ chmod 640 report.odt && getfacl report.odt
# file: report.odt
# owner: alice
# group: proj
user::rw-
group::r--
other::---
```

The moment a named entry is added, three things change: a `mask` entry appears, `ls -l` appends a `+` to the mode string, and the **group bit field of `chmod` now edits the mask** rather than the owning-group entry. That last rule is the single most common ACL surprise: after `setfacl -m u:deploy:rw file` and later `chmod g-w file`, deploy's effective rights shrink too, and only `getfacl` (with its `#effective` comments) or `ls -e` shows why.

## The Mask and the Group Class

Because the mask is a *ceiling* rather than a grant, its lifecycle deserves its own walkthrough:

```bash
$ setfacl -m u:deploy:rw- report.odt   # mask auto-computed: union of group class
$ getfacl report.odt | grep -E 'deploy|mask'
user:deploy:rw-
mask::rw-
$ chmod g-w report.odt                 # group bits edit the MASK on extended ACLs
$ getfacl report.odt | grep -E 'deploy|mask'
user:deploy:rw-                        #effective:r--
mask::r--
```

Rules to memorize: `setfacl -m`/`--set` recalculates the mask as the union of all group-class permissions unless you pass an explicit `m::` entry or suppress it with `-n`; `chmod`'s group bits *edit* the existing mask once the ACL is extended; and removing entries with `-x` does not shrink the mask — only dropping the last extended entry (back to minimal) makes the mask disappear. Auditing for the clamp is `getfacl`'s `#effective:` comments or `ls -e`.

## Default ACLs: Inheritance for Directories

Directories can carry a second ACL, the **default ACL**, which is not checked for access at all — it is a template stamped onto everything newly created beneath that directory. A child file receives the default's entries as its access ACL (the mask is intersected with the creating process's requested mode, and execute bits can only appear if the create call asked for them); a child directory additionally inherits the default ACL itself, so inheritance cascades down the tree:

```bash
# Every new file under /srv/proj grants oncall read; new dirs keep the template
$ setfacl -d -m g:oncall:rx /srv/proj
$ mkdir /srv/proj/2026 && touch /srv/proj/2026/notes.txt
$ getfacl /srv/proj/2026/notes.txt
# file: srv/proj/2026/notes.txt
...
group:oncall:r-x                       #effective:r--
mask::r--
```

Rules that govern the template: it affects only *future* files (existing trees need a one-time `setfacl -R -m` alongside it); a file created with `0666` intent never gains `x` from a default ACL, by design; and without any default ACL, new files inherit nothing but the owning group (and then only under the setgid bit). Default ACLs are the standard answer to "how do I make a shared directory actually work for a team," and `setfacl -d -m` plus `setfacl -R -m` shipped together is the deployment idiom.

## Kernel and Filesystem Support

ACLs live in kernel-managed extended attributes — `system.posix_acl_access` on files, `system.posix_acl_default` on directories — so support is a property of the filesystem, not of the tools:

| Filesystem | ACL support | Notes |
| --- | --- | --- |
| ext2/ext3/ext4 | yes | enabled by default; historically the `acl` mount option |
| XFS | yes | native IRIX heritage; the reason `chacl` exists on Linux |
| Btrfs, F2FS, JFS | yes | full POSIX-draft semantics |
| tmpfs | yes | applies to `/tmp`-style trees and initramfs |
| vfat/exfat | no | no xattr backing; tools fail with `Operation not supported` |
| proc, sysfs, devpts | no | pseudo-filesystems reject ACL metadata |

Modern kernels enable ACL support by default on native filesystems (the mount-time `acl` option is default-on and switchable off with `noacl`). Diagnostics follow the layers: `Operation not supported` from `setfacl` means the filesystem, `ls -l`'s trailing `+` means an extended ACL exists, and `ls -e` or `getfacl` shows the entries themselves.

### The diagnostic chain

The tools compose into a fixed interrogation sequence, cheapest first:

```bash
$ ls -l /srv/proj/notes.txt          # 1. is there anything extended? ('+')
-rw-rwx---+ 1 alice proj 0 Oct  9 16:35 /srv/proj/notes.txt
$ getfacl -e /srv/proj/notes.txt     # 2. what exactly, with mask clamps shown
$ ls -le /srv/proj/notes.txt         # 3. cross-check rendered inline by ls
```

Interviewers like this chain because each step answers a different question — existence, contents, effective rights — and skipping straight to `getfacl` without the `ls` signal check is how people miss ACLs on files they assumed were mode-bit-only.

## Backup and Migration

Backups must be *told* to carry ACLs; the default for most tools is to drop them silently:

| Mechanism | Carries ACLs? | Notes |
| --- | --- | --- |
| `tar --acls` | yes | GNU tar 1.27+; pair with `--xattrs` for the full picture |
| `rsync -A` | yes | `-X` adds xattrs; the delta-sync workhorse |
| `cp -a` | yes | `--preserve=all` includes xattr-backed ACLs |
| plain `cp`, `mv` across filesystems, editor save-by-rename | no | fresh inode, no ACL |
| `getfacl -R` + `setfacl --restore` | yes | text artifact, diffable, reviewable in change tickets |

The text round-trip deserves emphasis because it doubles as an audit format: a `getfacl -R` dump under version control is simultaneously the record of intended policy and the executable restore script.

## The Tool Inventory

| Tool | Role | Grammar style |
| --- | --- | --- |
| [`getfacl`](./getfacl.md) | Dump ACLs of files/trees; the backup and audit format | read-only text output |
| [`setfacl`](./setfacl.md) | Create/modify/remove ACLs; default ACLs; recursive; restore | `u:g:o:m` entry grammar, `-m`/`-x`/`--set` |
| [`chacl`](./chacl.md) | IRIX-heritage setter, complete-ACL replacement | single comma-separated ACL string |

`setfacl` is the workhorse — its modify grammar, mask auto-recalculation, recursive operation, and `--restore` backup flow subsume what `chacl` does, which survives for IRIX/XFS script compatibility. The cross-check pair to remember for interviews: `ls -l` shows *whether* an extended ACL exists (`+`), `getfacl` shows *what* it is, and `ls -e` bridges the two.

## Usage Patterns

```bash
# Grant a service account write on one file, leaving the world untouched
setfacl -m u:deploy:rw /srv/app/config.ini
```

```bash
# Make a shared project directory usable by a team, now and for future files
setfacl -m g:oncall:rwx /srv/proj && setfacl -d -m g:oncall:rx /srv/proj
```

```bash
# Snapshot every ACL under a tree, then re-apply after a migration
cd /srv && getfacl -R proj > /root/proj.acl && setfacl --restore=/root/proj.acl
```

```bash
# Audit which files carry extended ACLs at all
ls -lR /srv/proj | grep -- '+$'
```

```bash
# Explain a grant that "isn't working": read the entry and its mask clamp
getfacl -e /srv/app/config.ini
```

```bash
# Archive a tree with its ACLs intact for a true cross-host move
tar --acls --xattrs -cpf proj.tar /srv/proj
```

```bash
# Numeric-ID dump for config management, immune to passwd differences
getfacl -cnR /etc/app
```

```bash
# Strip legacy ACL sprawl from a tree before a chmod-based cleanup
setfacl -R -b /srv/oldproj
```

```bash
# Per-account deny: zero-permission named entry checked before any group
setfacl -m u:former-admin:--- /srv/secret
```

```bash
# Bulk-apply entries from a file — getfacl output is valid -M input
getfacl /etc/app/base.conf > /tmp/base.entries
setfacl -M /tmp/base.entries /etc/app/conf.d/*
```

## Nuances and Gotchas

- **The mask is a ceiling, not an entry you usually set.** `setfacl` recomputes it from the group class unless told otherwise, but `chmod g=...` rewrites it — pairing an ACL grant with a later `chmod` is how grants quietly stop being effective.
- **`cp` vs `cp -p` vs `cp -a`**: plain `cp` does not copy ACLs; only mode-preserving variants and `rsync -A` do. The same applies to editors that save via rename, which produce a fresh inode with no ACL.
- **Default ACLs cannot add execute where none was requested**: a file created with mode `0666` intent never gains `x` from a default ACL, by design.
- **`getfacl` strips leading slashes in its `# file:` headers by default** — deliberate, because `setfacl --restore` re-applies the dump relative to the current directory.
- **Filesystems without ACL support fail late and opaquely** (`Operation not supported`), so scripts that must survive mixed mounts should test one known file first.
- **Named grants can mask design debt**: a user's effective access is the union of owner/named/group/other evaluation, so removing one entry may not remove access that arrived via another class — audit with `getfacl`, not with assumptions.
- **The `+` in `ls -l` is a tripwire, not a diagnosis**: it says "extended access method present"; only `getfacl`/`ls -e` say what it is, and it may also appear for non-ACL alternate access methods.
- **`setfacl -b` is destructive and unlogged**: keep a `getfacl -R` dump before mass cleanup, or the previous policy exists only in backups taken before it existed.
- **Setgid directories and default ACLs are complementary inheritance channels**: the setgid bit propagates the *owning group* to new children, default ACLs propagate *entries*; team-shared trees usually want both, and audits should check both.
- **Empty output is a valid result** — `getfacl -Rs` printing nothing means no extended ACLs exist under the tree, which is often exactly the proof a change ticket needs.

## Interview Questions

### Q: What does the mask entry do, and when does it change?

The mask caps the effective permissions of the entire group class — named users, named groups, and the owning group — so `user:deploy:rwx` under `mask::r--` is effectively read-only. `setfacl` recalculates the mask as the union of group-class permissions whenever it modifies entries without an explicit mask (and `--no-mask`/`-n` suppresses that); `chmod`'s group bits edit the existing mask once the ACL is extended; `getfacl`'s `#effective` comments and `ls -e` expose the clamp when it bites.

### Q: How do a minimal ACL and the traditional mode bits relate?

They are the same data. A minimal ACL is exactly the three base entries — owning user, owning group, other — which is what the nine mode bits encode, so `chmod` and `setfacl` manipulate one store through two grammars. Adding any named entry or mask extends the ACL, appends `+` in `ls -l`, and from then on routes the group portion of `chmod` at the mask instead of the owning-group entry.

### Q: Walk through how the kernel decides access for a named group member when a mask is present.

First the class match: the process's euid is not the owner and not a named user, so the group class is consulted — the best-matching entry among the owning group and named groups is selected. Then the mask applies: that entry's permissions are ANDed with the mask entry. Then the decision: the resulting triple must contain the requested access, otherwise the check falls through to... nothing — a group-class match that fails *does not* fall through to `other`; the masked result is the answer. Confusing the fall-through rules (named users and groups never consult `other`) is a classic interview slip.

### Q: What are default ACLs and what are their limits?

A default ACL attaches to a directory, is never consulted for access, and serves as the inheritance template stamped onto newly created children — files receive its entries as an access ACL with the mask intersected against the creating process's mode, subdirectories also receive the default ACL itself so inheritance cascades. Limits: they affect only new files (existing trees need `setfacl -R`), execute bits can only be inherited when the create call asks for them, and they ride on filesystem support, not on the tools.

### Q: How would you move a directory tree between machines without losing ACLs?

Three workable flows, in decreasing fidelity: `tar --acls --xattrs -cpf` over ssh (metadata inside the stream), `rsync -A -X` (ACLs plus xattrs, with delta transfer), or the text round-trip `getfacl -R . > acls.bak` on the source and `setfacl --restore=acls.bak` in the target directory. Plain `cp`, plain `tar`, and editor-saved files all drop ACLs silently, which is why the `+` audit (`ls -lR | grep -- '+$'`) before and after is the professional habit.

### Q: Where do ACLs physically live, and what breaks when the storage layer disagrees?

In kernel-managed extended attributes: `system.posix_acl_access` for the access ACL, `system.posix_acl_default` on directories for the inheritance template. That grounding explains the whole failure surface: filesystems without xattr backing (vfat) or with ACL support compiled out (`noacl`) reject the tools with `Operation not supported`; copies that recreate inodes (plain `cp`, editor rename) lose the xattr; and backups only keep ACLs when their format carries them (`tar --acls`, `rsync -A`) — the tool layer is thin over a storage-layer contract.

## References

- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/acl/)
- [Source — Debian sources](https://sources.debian.org/src/acl/)
