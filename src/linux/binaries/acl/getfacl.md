# getfacl — dump file access control lists

## Overview

`getfacl` prints the ACL of files and directory trees in a stable text format — the format `setfacl --restore` consumes and the format ACL audits and backups are made of. It ships in Debian's `acl` package at `/usr/bin/getfacl`, one directory walk away from showing you exactly why a file's permissions are what they are, including the `#effective` comments that expose mask clamps `ls -l` cannot.

Where `ls -l` answers "does anything unusual exist here?" with a trailing `+`, `getfacl` answers "what, precisely, is the policy?" — base entries, named grants, mask, other, and the default ACLs that only exist on directories. It is often confused with `ls -e` (which renders the same entries inside long listings, less machine-friendly), with `stat` (mode bits only, no ACL awareness), and with `chacl -l` (short-form listing with no backup semantics).

| Field | Value |
| --- | --- |
| Package | acl (Debian bookworm: 2.3.x) |
| Man section | 1 |
| Path | /usr/bin/getfacl |
| First appeared | Linux ACL project late 1990s (IRIX/Solaris model ported) |
| Standards | POSIX 1003.1e draft 17 semantics (withdrawn draft, de-facto Linux standard) |

## Synopsis

```
getfacl [-aceEsnpRLPvh] FILE...
getfacl [-aceEsnpRLPvh] -R DIR...
```

Common one-line forms:

```
getfacl file                 # full ACL of one file
getfacl -R /srv/proj         # recursive dump of a tree
getfacl -p /etc/passwd       # keep the absolute path in the header
getfacl -d dir               # show the default ACL only
getfacl -n file              # numeric UIDs/GIDs, no name lookups
```

## How It Works

### The output format, field by field

Every file starts with comment headers (owner, group, and setuid/setgid/sticky flags), followed by one line per ACL entry in a fixed order — user entries, group entries, mask, other, with default entries prefixed by `default:`:

```bash
$ getfacl /srv/proj/report.odt
# file: srv/proj/report.odt
# owner: alice
# group: proj
user::rw-
user:deploy:rw-                 #effective:rw-
group::r--
group:oncall:r-x                #effective:r--
mask::rw-
other::---
```

Read it as the evaluation table from the [collection overview](./overview.md): `user::` is the owning user's mode bits, the two `group::`-class lines are capped by `mask::`, and `other::` catches everyone else. The `#effective:` comments appear only where the mask clamps an entry below its stored permissions — they are the fastest diagnostic for "the grant is there but nobody got it." A file with no extended ACL still prints, as pure base entries (`user::rw-, group::r--, other::r--` for mode 644), which makes getfacl the canonical *mode-bits-to-ACL-text* converter too.

### A directory with a default ACL

Directories with an inheritance template list the access ACL first, then repeat every entry under the `default:` prefix — the template is itself a complete ACL:

```bash
$ getfacl /srv/shared
# file: srv/shared
# owner: alice
# group: proj
user::rwx
user:deploy:rw-
group::r-x
group:oncall:r-x
mask::rwx
other::---
default:user::rwx
default:user:deploy:rw-
default:group::r-x
default:group:oncall:r-x
default:mask::rwx
default:other::---
```

That shape is why `setfacl --restore` can rebuild both layers from one dump: the entries and their `default:`-prefixed copies are the complete permission state of the tree.

### The order is part of the format

The entry lines come in a fixed order — user entries, group entries, mask, other, then the `default:`-prefixed block in the same internal order — and the headers are always first. The stability is a feature: `diff` between two dumps is a policy diff, and config-management tools can parse dumps without heuristics. Never sort or reorder entries when post-processing; the position of `mask::` and the `default:` block is what makes dumps round-trippable.

### Comment headers are load-bearing

The `# file:` header is not decoration: `setfacl --restore` reads these dumps back, and the path in the header is where the entries get applied. By default getfacl **strips leading slashes** from the header path (`# file: srv/proj/...` for an argument of `/srv/proj`), deliberately, so a dump re-applies relative to the current directory at restore time. `-p`/`--absolute-names` preserves the original absolute path for archives that must restore in place.

```bash
# Relative dump + relative restore = relocatable ACL backup
cd /srv && getfacl -R proj > /root/proj.acl
cd /mnt/newroot/srv && setfacl --restore=/root/proj.acl
```

### Selection flags: what gets dumped

- `-R` recurses into trees — the backup idiom's backbone, always paired with relative paths.
- `-d` dumps only the default ACL, `-a` only the access ACL; a directory typically has both.
- `-s`/`--skip-base` omits files whose ACL is just the mode bits, so audits list only genuinely extended objects.
- `-n`/`--numeric` prints UIDs/GIDs instead of resolving names — the portable dump for machines crossing hosts where accounts differ.
- `-e`/`--effective` (default behavior for the `#effective` comments) and `-E`/`--no-effective` control the annotation.
- `-c`/`--omit-header` drops the comment headers, leaving bare entries for diffing two files' ACL policy.

```bash
# Compare ACL policy between two environments, headers and names removed
getfacl -c -n -R /srv/proj > a.txt
getfacl -c -n -R /mnt/other/proj > b.txt
diff a.txt b.txt
```

### Cross-checking against ls

`ls -l` appends `+` to the mode string exactly when an extended ACL (or other xattr-backed mode extension) exists, and `ls -e` renders the ACL entries beneath the long-format line. The two tools disagree on nothing — but `getfacl` shows the mask and effective clamps that `ls -e` summarizes, so interviews treat the pair as the "is there one?" / "what is it?" question chain:

```bash
$ ls -l /srv/proj/report.odt
-rw-rw----+ 1 alice proj 0 Oct  9 16:35 /srv/proj/report.odt
```

`ls -e` appends the ACL entries on indented lines beneath a `ls -le` listing — handy inline, but it is a rendering, not a dump format: no tool re-applies it, and it carries neither the `# file:` headers nor the restore semantics of getfacl output. For anything scripted, getfacl is the interface.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-R` | Recurse into directory trees (dump everything below) |
| `-p` | Do not strip leading `/` from `# file:` headers |
| `-d` | List the default ACL (directory inheritance template) |
| `-a` | List the access ACL only |
| `-s` | Skip files that carry only the minimal (mode-bit) ACL |
| `-n` | Print numeric UIDs/GIDs; no passwd/group lookups |
| `-e` / `-E` | Show / hide `#effective:` mask annotations |
| `-c` | Omit comment headers (bare entries) |
| `-t` | Tabular output: one compact table per file |
| `-L` / `-P` | Follow / never follow symlinks on recursive walks |

### Machine processing

The dump is deliberately line-oriented and grep-friendly: headers start with `#`, entries never do, and one file's section runs until the next `# file:` header. Filters like `getfacl -R . | grep -c '^# file:'` count objects, `grep -v '^#'` isolates entries, and `-c` removes headers entirely when only entries matter. For human review, `-t` trades the strict format for a tabular layout — never feed `-t` output to `setfacl --restore`.

## Usage Patterns

```bash
# The ACL backup: full tree dump into one text artifact
cd /srv && getfacl -R proj > /root/proj.acl
```

```bash
# Restore on a new root, relative paths intact
cd /mnt/newroot/srv && setfacl --restore=/root/proj.acl
```

```bash
# Audit: only the files that actually carry extended ACLs
getfacl -Rs /srv 2>/dev/null
```

```bash
# Why does deploy have write here? Read the grant and its mask clamp
getfacl -e /srv/app/config.ini
```

```bash
# Machine-readable dump for config management (numeric, no headers)
getfacl -cn /etc/app/*.conf
```

```bash
# Inspect a directory's inheritance template in isolation
getfacl -d /srv/shared
```

```bash
# Pre-migration inventory: absolute paths preserved for in-place restore
getfacl -Rp /etc/app > /root/etc-app.acl
```

```bash
# Spot-check with ls: '+' first, then the entries behind it
ls -l /srv/proj | grep -- '+$' && getfacl "$(ls -d /srv/proj/* | head -1)"
```

```bash
# Count objects in a tree dump without parsing entries
getfacl -R /srv/proj 2>/dev/null | grep -c '^# file:'
```

```bash
# In-place restore from an absolute-path dump (captured with -p)
setfacl --restore=/root/etc-app.acl
```

```bash
# Feed one file's ACL straight into a bulk modify (getfacl output is -M input)
getfacl /etc/app/base.conf > /tmp/base.entries
setfacl -M /tmp/base.entries /etc/app/conf.d/*
```

```bash
# Snapshot before a setfacl -b cleanup so policy is recoverable
getfacl -Rs /srv/oldproj > /root/oldproj.pre-cleanup.acl
```

## Nuances and Gotchas

- **Header paths are relative by design** — getfacl strips the leading `/` so `--restore` re-applies from the current directory. Scripts that assume absolute paths in dumps must pass `-p` explicitly or they will restore somewhere unexpected.
- **`#effective:` is display-only** — the stored entry and mask keep their values; tools recompute the clamp. Never "fix" a clamp by editing the dump's `#effective` text; fix the mask with `setfacl`.
- **Default ACLs only exist on directories** and print under `default:` prefixes; `getfacl -d` on a plain file shows nothing — that is not an error.
- **`-R` follows the same symlink rules as the rest of the package**: `-P` (default) never follows, `-L` opts in; dumps of symlink farms reflect the link entries, not targets, unless you say otherwise.
- **Name resolution changes the output**: dumps taken with resolved names stop being portable across hosts with different accounts; `-n` freezes UIDs/GIDs into the artifact.
- **Files without extended ACLs still dump** — that is a feature (mode-bits round-trip via `setfacl --restore`), but it means `getfacl file | wc -l` is not a count of "special" ACLs; filter with `-s` for that.
- **Recursive dumps of huge trees are per-file xattr reads** — a full `getfacl -R /` walks every inode; scope the walk, use `-s` to skip base-only files, and remember `tar --acls` captures the same metadata inside the archive stream instead.
- **Dumps resolve names through NSS at dump time** — an account deleted after the dump prints numeric fallbacks or stale names; artifacts meant to be re-applied should be captured with `-n` so they keep meaning.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested files were dumped |
| nonzero | At least one file could not be read or an argument was invalid |

## Related Commands

- [`setfacl`](./setfacl.md) — the write side; `--restore` consumes this tool's output verbatim.
- [Collection overview](./overview.md) — entry types, mask semantics, and the evaluation order this output encodes.
- [`chacl`](./chacl.md) — the IRIX-heritage setter with its own short-form listing mode.
- [Permissions](../../admin/permissions.md) — the mode-bit layer whose bits are this tool's base entries.
- [Binaries part overview](../overview.md) — the chapter hub.

## Interview Questions

### Q: What does the `#effective:` comment in getfacl output mean, and when does it appear?

It appears only when the mask entry clamps a group-class entry below its stored permissions — `user:deploy:rw-` under `mask::r--` prints `#effective:r--`. The comment is diagnostic: the stored entry and mask are unchanged, and the fix belongs in `setfacl` (recalculate or set the mask), not in the dump text. Interviews use it as the tell for "grant present, access absent" mysteries.

### Q: Why does getfacl strip leading slashes from its output, and how do you keep them?

The dump is designed to be re-applied by `setfacl --restore` relative to wherever you stand, so `# file: srv/proj/x` (from an argument of `/srv/proj/x`) makes backups relocatable — dump from inside `/srv`, restore inside the new root's `/srv`. `-p`/`--absolute-names` preserves the original path for in-place restores. Getting this wrong silently applies ACLs to the wrong tree, which is the tool's most operational gotcha.

### Q: How would you prove that no file under /srv carries a hidden extended ACL?

`getfacl -Rs /srv` — `-s` skips base-ACL files, so output lists only extended objects; empty output is the proof. Cross-check with `ls -lR | grep -- '+$'`, since both signals come from the same kernel state (`system.posix_acl_access` beyond the three base entries). For machine diffing across hosts, add `-c -n` to strip headers and freeze numeric IDs.

### Q: What is the relationship between getfacl output and setfacl input?

They are the same format by design: getfacl's comment headers carry the filename, the entry lines are setfacl's entry grammar, and `setfacl --restore=FILE` applies a whole dump. The practical consequences: `getfacl file1 | setfacl --set-file=- file2` clones policy, `getfacl -R . > backup` is the backup, and any audit report you build from getfacl is simultaneously an executable restore script — one reason to keep dumps under change control.

### Q: When do you choose getfacl -n over name-resolved output?

When the dump must survive a trip across machines or into config management: numeric UIDs/GIDs avoid dependence on the local passwd/group databases, keep diffs stable, and prevent silent grants to the *wrong* account after name remapping. Names are for humans reading a live system; `-n` is for artifacts that will be re-applied or diffed later.

### Q: You need to prove the ACL policy of /srv/proj is identical in staging and production. What is the workflow?

Dump both trees with identity-normalized output — `getfacl -cnR /srv/proj` on each host (numeric IDs, no headers) — and `diff` the two files; because entry order is fixed by the format, any difference is a real policy difference, not formatting noise. Where they diverge, regenerate the production side from the approved dump with `setfacl --restore`. Doing the same with `ls -e` output fails because its rendering is not stable input for diffing or restoring.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/acl/getfacl.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/acl/)
