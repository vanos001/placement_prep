# chacl — change access control lists (IRIX heritage)

## Overview

`chacl` sets, removes, and lists POSIX ACLs using the grammar of SGI's IRIX operating system — the dialect the Linux ACL implementation originally imitated when XFS was ported from IRIX to Linux. It ships in Debian's `acl` package at `/usr/bin/chacl` next to `setfacl` and `getfacl`, drives exactly the same kernel state (`system.posix_acl_access` and `system.posix_acl_default` xattrs), and survives on modern systems mostly because old XFS administration scripts and dump/restore tooling still call it.

Its design point — and the reason to know it even if you never type it — is the **complete-replacement philosophy**: every invocation names the entire ACL you want, comma-separated, in one argument. There is no `-m`-style merge, no recursive mode, no auto-recalculated mask, and no backup format. `setfacl` subsumes all of it, which is why the [collection overview](./overview.md) positions `chacl` as the compatibility tool of the three.

| Field | Value |
| --- | --- |
| Package | acl (Debian bookworm: 2.3.x) |
| Man section | 1 |
| Path | /usr/bin/chacl |
| First appeared | IRIX (SGI); ported to Linux with XFS in the late 1990s |
| Standards | IRIX ACL syntax; POSIX 1003.1e draft 17 kernel semantics |

## Synopsis

```
chacl acl pathname...
chacl -b acl dacl pathname...
chacl -d dacl pathname...
chacl -R pathname...
chacl -D pathname...
chacl -B pathname...
chacl -l pathname...
```

The five verbs at a glance:

| Form | Verb | Target |
| --- | --- | --- |
| `chacl ACL path...` | replace the access ACL | any file or directory |
| `chacl -b ACL DACL path...` | replace access **and** default ACLs | directories |
| `chacl -d DACL path...` | replace only the default ACL | directories |
| `chacl -R path...` | remove the access ACL | any file or directory |
| `chacl -D path...` | remove the default ACL | directories |
| `chacl -B path...` | remove both ACLs | directories |
| `chacl -l path...` | list ACLs in short form | any file or directory |

## How It Works

### The one-argument ACL format

The `acl` argument is the whole policy: entries separated by commas, no spaces, using tag letters `u`, `g`, `m`, `o` with qualifiers where meaningful. Permissions are the familiar `rwx` letters and `-` placeholders:

```
u::rwx,g::r-x,o::---                                      # minimal (mode bits)
u::rwx,u:deploy:rw-,g::r--,g:oncall:r-x,m::rwx,o::---     # extended
u::rwx,g::r-x,o::---,g:oncall:r-x,m::r-x                  # mask spelled out
```

Format rules worth keeping in one place:

- **Base entries are mandatory** — `u::`, `g::`, and `o::` must be present; the format has no partial ACL and no merge, so every call restates the complete policy.
- **Qualifiers are names or numeric IDs** — `u:deploy`, `u:1001`, `g:oncall`, `g:1500`; resolution happens through NSS at call time, same as `setfacl`.
- **No whitespace inside the argument** — commas are the separators; a space silently truncates the ACL string into separate shell words and an argument-position filename.
- **The mask tag is `m::`** — qualifier position is tolerated but conventional usage is always the bare form.

Because the argument is one comma-packed token, shell quoting is trivial (no spaces to escape), which made `chacl` attractive to IRIX-era scripts that assembled the ACL as a single string and to `xargs`-driven pipelines — and it is why a stray space in a generated ACL string does not merely fail, it can silently become a separate argument interpreted as a pathname.

```bash
# Numeric-ID qualifier works where names do not resolve
chacl u::rw-,g::r--,o::---,u:1001:rw-,m::rw-    /srv/app/config.ini
```

### The mask is your job

Unlike `setfacl`, which recalculates the mask from the group class after every merge, `chacl` does not compute one for you: when named entries are present, an explicit `m::perms` entry belongs in the list, and the kernel applies the mask as the ceiling over named users, named groups, and the owning group. Omitting it — or leaving it narrower than the grants you wrote — means the effective policy is not what you wrote, with nothing warning you. `getfacl`'s `#effective:` comments are the post-hoc audit for exactly this miss, and the discipline of appending `m::` to every extended ACL is the IRIX-grammar lesson that `setfacl`'s default quietly solved.

### -b and -d: default ACLs, IRIX-style

Directories can carry the inheritance template (default ACL) as well as an access ACL. `chacl -b access_acl default_acl dir` sets both in one call; `chacl -d default_acl dir` sets only the template. The semantics after the call are the Linux-standard ones from the [collection overview](./overview.md): new children inherit the default as their access ACL, the mask is intersected with each child's creation mode, and subdirectories pass the template downward.

```bash
# Team directory: access grant today, inheritance template for tomorrow
chacl u::rwx,g::r-x,o::---,g:oncall:rwx,m::rwx /srv/proj
chacl -b u::rwx,g::r-x,o::---,g:oncall:rwx,m::rwx \
      u::rwx,g::r-x,o::---,g:oncall:rx,m::rx  /srv/proj
```

### Removal flags: the -R trap

The removal flags operate on the stored ACLs, not on trees — and this is the tool's most dangerous collision with modern muscle memory. In `chacl`, `-R` **removes the access ACL** (the file returns to its minimal mode-bit ACL); in `setfacl`, `-R` **recurses**. An admin who pattern-matches the flag across tools can strip ACLs from the wrong targets while believing they walked a tree. `-D` strips the default ACL, `-B` both. There is no recursion anywhere in the tool: applying an ACL to a tree means wrapping `chacl` in `find` yourself.

### Listing without backup semantics

`chacl -l` prints each pathname followed by its ACL in bracketed short form — a quick interactive check that answers "what did that old script set?". It is deliberately *not* a backup format: there is no counterpart flag that consumes `chacl -l` output, no comment headers, no absolute/relative path handling. Anything you need to restore belongs in the `getfacl` / `setfacl --restore` pair instead.

### Porting a chacl script to setfacl

Because both tools drive the same kernel state, every chacl form has a mechanical translation:

| chacl | setfacl equivalent |
| --- | --- |
| `chacl ACL file` | `setfacl --set=ACL file` |
| `chacl -R file` (strip access ACL) | `setfacl -b file` |
| `chacl -D dir` (strip default ACL) | `setfacl -k dir` |
| `chacl -B dir` (strip both) | `setfacl -b dir && setfacl -k dir` |
| `chacl -d DACL dir` | `setfacl -d --set=DACL dir`, or `d:`-prefixed entries with `-m` |
| `chacl -b ACL DACL dir` | `setfacl --set=ACL dir` plus a `d:`-prefixed call |
| `chacl -l path` | `getfacl path` (adds headers and restore semantics) |

What has no translation is the workflow loss: `-m` merges, automatic mask recalculation, recursion, and `--restore` are capabilities `setfacl` adds, not renames of chacl features.

## Options That Matter

| Option | Effect |
| --- | --- |
| *plain form* | Replace the access ACL of each pathname with the given ACL |
| `-b ACL DACL` | Replace both the access ACL and the default ACL (directories) |
| `-d DACL` | Replace only the default ACL of a directory |
| `-R` | Remove the access ACL (file returns to mode-bit minimal) |
| `-D` | Remove the default ACL |
| `-B` | Remove access and default ACLs |
| `-l` | List the ACL(s) of each pathname in short form |

## Usage Patterns

```bash
# Set a complete minimal ACL — equivalent to chmod 750, in ACL notation
chacl u::rwx,g::r-x,o::--- /srv/app
```

```bash
# Grant a named user read-write alongside the existing mode bits
chacl u::rw-,g::r--,o::---,u:deploy:rw-,m::rw- /srv/app/config.ini
```

```bash
# Give a group traverse/read on a shared directory, mask spelled out
chacl u::rwx,g::r-x,o::---,g:oncall:r-x,m::r-x /srv/proj
```

```bash
# Install a default ACL template on a directory (default ACL only)
chacl -d u::rwx,g::r-x,o::---,g:oncall:rx,m::rx /srv/proj
```

```bash
# Set access and default ACLs together in one invocation
chacl -b u::rwx,g::r-x,o::---,g:team:rwx,m::rwx \
      u::rwx,g::r-x,o::---,g:team:rx,m::rx /srv/shared
```

```bash
# Grant by numeric ID for an account that does not resolve locally
chacl u::rw-,g::r--,o::---,u:1500:rw-,m::rw- /data/export/share.csv
```

```bash
# Check what an old XFS-era script actually set
chacl -l /srv/proj
```

```bash
# Strip a file back to plain mode bits (note: NOT recursive)
chacl -R /srv/app/config.ini
```

```bash
# Remove an inheritance template left behind by a deprecated flow
chacl -D /srv/proj/frozen
```

```bash
# Apply one complete ACL to a whole tree — chacl has no -R recursion,
# so find does the walking and xargs batches the calls
find /srv/proj -exec chacl u::rw-,g::r--,o::---,g:oncall:r--,m::r-- {} +
```

```bash
# Clear every ACL under a tree the chacl way (compare setfacl -R -b)
find /srv/oldproj -exec chacl -R {} + && find /srv/oldproj -exec chacl -D {} +
```

```bash
# Verify what the legacy script left behind, with the modern tool
getfacl /srv/proj
```

```bash
# Deny a specific account outright: named user checked before groups
chacl u::rwx,g::r-x,o::---,u:former-admin:---,m::rwx /srv/secret
```

```bash
# List, then strip, then confirm — the roundtrip on one file
chacl -l /srv/app/config.ini && chacl -R /srv/app/config.ini && chacl -l /srv/app/config.ini
```

## Nuances and Gotchas

- **`-R` does not mean recursive here.** In `setfacl`, `-R` recurses; in `chacl`, it *removes* the access ACL. Migrating muscle memory between the two tools is a genuine data-permission hazard, and the single best reason new scripts should not use `chacl`.
- **No recursion, period.** Applying an ACL to a tree means wrapping `chacl` in `find ... -exec ... +` yourself — one more reason `setfacl -R` dominates, and one more place where a glob or find predicate mistake edits real permissions.
- **No mask auto-calculation**: supply `m::` whenever named entries exist, or the effective policy will not match the written one and nothing warns you.
- **Complete replacement every time**: there is no merge, so every call must restate base entries plus every surviving grant; "additive" edits mean you script the read-modify-write cycle (via `getfacl`) that `setfacl -m` gives you natively.
- **No backup format**: `chacl -l` is for eyeballs; the getfacl/setfacl text pair is the auditable, restorable artifact.
- **Same filesystem dependencies as the rest of the package**: no ACL support in the filesystem (vfat, `noacl` mounts) means failure regardless of which tool you call.
- **The removal flags are absolute**: `-R`/`-D`/`-B` strip ACLs without prompting and without the `-i`-style interactive safety that other tools offer on bulk paths.
- **Historic scripts embed the full grammar** — reading old XFS provisioning scripts means reading complete ACL strings with no `+/-` cues; translate them entry by entry when porting to `setfacl`.
- **chacl's capability set is a strict subset of setfacl's** — there is no operation chacl performs that setfacl cannot; choosing chacl is a compatibility decision, never a functional one.
- **The IRIX heritage is grammar, not filesystem scope** — chacl drives the same `system.posix_acl_*` xattrs as the rest of the package, so it works identically on ext4, Btrfs, and XFS alike.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested ACL operations succeeded |
| nonzero | At least one operation failed (syntax, unsupported filesystem, permission denied) |

## Related Commands

- [`setfacl`](./setfacl.md) — the modern setter that subsumes this tool: merge grammar, recursion, mask recalculation, restore.
- [`getfacl`](./getfacl.md) — the dump/list tool with actual backup semantics; prefer it over `chacl -l` for anything scripted.
- [Collection overview](./overview.md) — the shared ACL model and evaluation order behind this grammar.
- [Permissions](../../admin/permissions.md) — the mode-bit layer the minimal ACL maps onto.
- [Binaries part overview](../overview.md) — the chapter hub.

## Interview Questions

### Q: Why does chacl still exist on modern Debian systems?

Lineage: the Linux ACL implementation followed the IRIX model (XFS's home), and `chacl` is that grammar's reference tool — kept in the `acl` package for IRIX-era and early-XFS scripts, dump/restore tooling, and admin habit. It drives the same kernel xattrs as `setfacl`; nothing requires it on a modern system, which is exactly why interviews use it to test whether candidates understand the layer beneath the tooling.

### Q: Contrast the chacl and setfacl grammars.

`chacl` is one-shot replacement: a single comma-packed ACL argument, complete every time, mask included by hand, with separate `-b`/`-d` forms for default ACLs and no recursion. `setfacl` is an editor: `-m` merges, `-x` removes subjects, `--set` replaces, masks recalculate automatically unless `-n`, `-R` recurses, and `--restore` consumes `getfacl` dumps. Same kernel state, two generations of ergonomics — and one trap: `chacl -R` removes an ACL where `setfacl -R` recurses.

### Q: What happens if you add a named-user entry with chacl but forget the mask entry?

The named entry sits in the group class, and the mask is the ceiling over that class — with the mask absent or narrower than intended, the effective rights of your grant (and of the owning group) are clamped, silently. `setfacl` avoids the failure mode by recomputing the mask as the union of group-class permissions; with `chacl` the discipline of appending `m::perms` to every extended ACL is on you, and `getfacl`'s `#effective:` comments are how you audit for the miss.

### Q: What exactly do chacl's -R, -D, and -B do, and what is the classic mistake around them?

They remove stored ACLs: `-R` strips the access ACL back to the minimal mode-bit form, `-D` strips a directory's default ACL, `-B` strips both. The classic mistake is importing `setfacl` muscle memory, where `-R` recurses — a "recursive" chacl attempt neither recurses nor preserves anything; it deletes the very grants you meant to propagate. Ported scripts must translate `chacl -R` to `setfacl -b` and do any walking with `find` or `setfacl -R` itself.

### Q: How would you replace a chacl-based ACL script with a setfacl equivalent?

Translate the complete ACL argument into `setfacl --set` (which, like chacl, demands base entries, making the semantics match), convert any `chacl -R` ACL-stripping into `setfacl -b`, and replace default-ACL handling (`chacl -b`/`-d`) with `d:`-prefixed entries or `-d -m`. Anything that looped `chacl` over `find` output collapses to a single `setfacl -R -m`, and the mask line usually disappears entirely because setfacl recalculates it.

### Q: When would you deliberately choose chacl over setfacl today?

Rare but real cases: applying a fully pre-built ACL string from legacy tooling without a read-modify-write step, matching the conventions of an existing XFS-era codebase, or environments where the IRIX syntax is the documentation (Solaris/IRIX mixed shops migrating to Linux). For everything else — incremental grants, recursion, mask hygiene, backups — `setfacl` with `getfacl` is strictly more capable, and presenting that trade-off honestly is the interview answer.

### Q: Is there anything chacl can do that setfacl cannot?

No — both manipulate the same kernel xattrs through the same POSIX-draft semantics, so the capability sets coincide: set access ACLs, set default ACLs, remove them, list them. Everything that differs is ergonomics: chacl's single-string replacement is convenient when the ACL already exists as a string; setfacl's merge grammar, mask recalculation, recursion, and restore flow cover every other need. The honest summary for an interview: chacl is a compatibility surface, not a feature gap-closer.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/acl/chacl.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/acl/)
