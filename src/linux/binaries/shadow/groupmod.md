# groupmod — modify an existing group (rename, re-GID, members)

## Overview

`groupmod` is the shadow suite's group-edit tool: it changes the definition of an existing group in the group database — most importantly its name (`-n`) and its numeric ID (`-g`), plus (on recent shadow) its member list (`-U`, with `-a` to append). It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/groupmod`. Where `groupadd` and `groupdel` bracket the group's life, `groupmod` is what you reach for when reality changes around a group that must keep existing — a department rename, a GID collision with another system, a policy shift to a dedicated service GID.

It is often confused with `usermod` (same verb, different object: users vs groups — and `usermod -g`/`-G` sets a *user's* group attachments), with `chgrp` (which changes file ownership, the thing groupmod deliberately does not do), and with `groupmems`/`gpasswd` (member-list editors; groupmod's member editing arrived only in recent shadow releases). The two operations interviewers probe — `-n` rename and `-g` re-GID — are exactly the ones with surprising blast radii, because one is referenced by *name* across config files and the other by *number* across the filesystem.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/groupmod |
| First appeared | System V lineage; shadow suite (Julianne F. Haugh, 1988+), now maintained by shadow-maint |
| Standards | Not POSIX; specified by LSB. Ignores GID_MIN/GID_MAX for -g by design |

## Synopsis

```
groupmod [options] GROUP
```

Common one-line forms:

```
groupmod -n proj7-old proj7      # rename proj7 to proj7-old
groupmod -g 2100 deploy          # change deploy's GID
groupmod -g 2100 -o legacy       # accept a duplicate GID deliberately
groupmod -U alice,bob qa         # replace member list (recent shadow)
groupmod -a -U carol qa          # append instead of replace (recent shadow)
```

## How It Works

### Renaming (-n): what changes and what does not

`groupmod -n NEW OLD` rewrites the name field of the matching entries in `/etc/group` and `/etc/gshadow` under the shadow locks. That is the entire write. Membership, GID, password state are untouched. Crucially, **nothing else on the system is keyed by group name** — file ownership is the GID, process credentials are GIDs — so the rename itself cannot break file access. What *is* keyed by name is configuration text that humans wrote:

```
references that survive the rename:   files, processes, ACLs (numeric GIDs)
references that silently break:       /etc/sudoers (%deploy), NFS exports,
                                      scripts grepping group names,
                                      systemd unit Group= (by name),
                                      application configs, crontab group use
```

Name conflicts are refused before any write:

```
$ groupmod -n users qa
groupmod: group 'users' already exists          # exit 9
```

A real-world quirk worth knowing: the new name is not re-validated against the group-name rules on some recent releases — a rename to a syntactically invalid name (say `5bad`) was observed to succeed on a recent shadow build where `groupadd 5bad` would exit 3. Treat `groupmod -n` as unsanitized input handling: validate in the script, not by trusting the tool.

### Re-GID (-g): the passwd side is fixed, files are not

`groupmod -g NEWGID GROUP` changes the GID in both group files and — the part people miss — updates every `/etc/passwd` entry whose primary GID was the old number, so users keep this as their primary group under the new number:

```
before:  deploy:x:1200:          alice:x:1001:1200:...   (alice's primary)
after:   deploy:x:2100:          alice:x:1001:2100:...   (updated)
         /srv/deploy/* (owned by 1200)                   (NOT updated)
```

The man page is explicit that files carrying the old GID "must have their group ID changed manually", and equally explicit that **no checks are performed against `GID_MIN`, `GID_MAX`, `SYS_GID_MIN`, or `SYS_GID_MAX`** — `-g` is the one place the login.defs ranges are not enforced. Uniqueness is still enforced unless `-o`:

```
$ groupmod -g 100 deploy
groupmod: GID '100' already exists               # exit 4
```

The filesystem half is a find/chgrp dance you script yourself:

```bash
oldgid=$(getent group deploy | cut -d: -f3)
groupmod -g 2100 deploy
find / -xdev -group "$oldgid" -exec chgrp 2100 {} +
```

### Member editing (-U / -a): recent shadow only

Modern releases gained `-U user1,user2` to set (replace) the member list and `-a -U ...` to append, matching the groupmems/gpasswd vocabulary. Debian bookworm's `groupmod` (4.13) has no such options — membership there is `usermod -aG` / `gpasswd` / `groupmems` territory. Scripts using `-U` must gate on the release.

### The update sequence, end to end

```
        groupmod -g NEWGID -n NEWNAME GROUP
                        |
        GROUP exists in local db? --no--> exit 6
                        | yes
        NEWNAME taken?            --yes--> exit 9   (no write yet)
        NEWGID used (no -o)?      --yes--> exit 4   (no write yet)
                        | no conflicts
        lock group + gshadow (+ passwd/shadow for the -g fixup)
        rewrite entries in /etc/group and /etc/gshadow
        rewrite /etc/passwd GID fields pointing at the old number
                        |
        release locks          <-- db done; filesystem NOT done
                        |
        (your job) find / -xdev -group OLDGID -exec chgrp NEWGID {} +
```

The diagram's punchline: the tool's own part of a re-GID is three file rewrites; the fourth (the filesystem) is intentionally yours.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-n NEW_GROUP` | Rename. Refused with exit 9 if the name is taken |
| `-g GID` | Change the GID; passwd primary-group references follow; files do not; no MIN/MAX checks; unique unless `-o` |
| `-o` | Allow the new GID to be a duplicate (alias groups) |
| `-p HASH` | Replace the group's encrypted password (crypt(3) output); leaks via `ps` like everywhere in the suite |
| `-U USERS` | Set member list (recent shadow); combine with `-a` to append |
| `-a` | With `-U`: append rather than replace |
| `-R DIR` | Chroot into DIR (image building) |
| `-P DIR` | Prefix mode for staging trees (NIS/LDAP not verified; PAM uses host files) |

## Usage Patterns

```bash
# Department rename, with the config references swept in the same change
groupmod -n analytics proj7
grep -rn '%proj7' /etc/sudoers /etc/sudoers.d/   # now fix these by hand
```

```bash
# Escape a GID collision with a mounted volume's baked-in group
groupmod -g 2100 deploy
```

```bash
# Full GID migration with the filesystem sweep (order matters)
oldgid=$(getent group deploy | cut -d: -f3)
groupmod -g 2100 deploy && find / -xdev -group "$oldgid" -exec chgrp 2100 {} +
```

```bash
# Same-number alias: two names, one access set (migration shim)
groupmod -o -g 2100 deploy-legacy
```

```bash
# Pin a service group below the human range without touching login.defs
groupmod -g 350 _metrics
```

```bash
# Set the member list declaratively (recent shadow; replaces existing members)
groupmod -U "$(paste -sd, /etc/roster/qa.txt)" qa
```

```bash
# Append without clobbering (recent shadow)
groupmod -a -U contractor1,contractor2 qa
```

```bash
# Replace the group password with a precomputed hash (see gotchas)
groupmod -p "$(openssl passwd -6 'grouppass')" consultants
```

```bash
# Lock down the group password again after a temporary open period
groupmod -p '!' consultants
```

```bash
# Image build: adjust the group inside a staging root
groupmod -R /mnt/rootfs -g 900 _nginx
```

```bash
# Verify before/after state in scripts (names AND numbers)
getent group deploy; getent passwd | awk -F: '$4 == 2100 {print $1}'
```

```bash
# Post-change integrity gate
grpck -r && echo "group db consistent" || echo "investigate before proceeding"
```

```bash
# Rename back out of trouble (rename is its own inverse)
groupmod -n proj7 proj7-badname && getent group proj7
```

```bash
# Fleet-consistent GIDs: check a candidate against a golden host's export
ssh golden 'getent group deploy'   # deploy:x:2100:
groupmod -g 2100 deploy            # align this host to the golden GID
```

## Nuances and Gotchas

- **`-g` renumbers the passwd entries but not the files — and that is by design.** The dangerous window is between `groupmod -g` and your `find -exec chgrp`: files owned by the old number are temporarily "orphaned", and if a new group is allocated that number first, they silently change hands. Do the sweep immediately, on quiet systems, or take the tree offline.
- **No range checks on `-g`.** `-g 99999` is accepted even though it is far outside `GID_MAX`; the man page says so outright. Auto-GID allocation (`groupadd`) enforces ranges, manual assignment (`groupmod -g`) does not — a deliberate asymmetry interviewers like.
- **Exit 4 vs exit 9 again.** `GID 'N' already exists` is 4; `group 'name' already exists` is 9. Same pair of meanings as groupadd; same scripting consequence — distinguish them if you want actionable errors.
- **Rename breaks name-keyed config, and nothing warns you.** The rename is atomic and quiet; `%deploy` in sudoers keeps referencing a now-nonexistent name. Sweep `sudoers`, NFS exports, systemd units, and app configs in the same change window, and re-check with `getent group NEWNAME`.
- **`-o` aliases are an audit hazard.** After `groupmod -o -g 2100 deploy-legacy`, `ls -l` and permission checks cannot tell the two names apart (they share a number). Fine as a migration shim, terrible as a permanent structure.
- **`-p` hashes land on the process list** (`ps`, `/proc/*/cmdline`) while the command runs, and land in shell history if typed literally. Generate off-band, and remember the sane default is a locked (`!`) group password — most groups should never have one.
- **`-U` (replace) clobbers.** The append form needs the separate `-a` flag; `groupmod -U "$x"` with a one-element list empties the group of everyone else. Bookworm's groupmod has no `-U` at all — gate on capability.
- **PAM codes exist.** On PAM builds groupmod can fail with 11/12/13 (cleanup-service setup, username determination, PAM error — see syslog facility `groupmod`). If you only ever tested as root, your script has never seen them.
- **`-P` prefix mode probes the host db.** GID/name uniqueness checks resolve via the host's NSS in prefix mode, so results can disagree with the target tree's contents. Trust `-P` output only after a follow-up `grpck` on the staging files.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 2 | invalid command syntax |
| 3 | invalid argument to option |
| 4 | group id already in use (without `-o`) |
| 6 | specified group doesn't exist |
| 9 | group name already in use |
| 10 | can't update group file |
| 11 | can't set up cleanup service (PAM builds) |
| 12 | can't determine your username for use with PAM |
| 13 | PAM returned an error (details in syslog, facility `groupmod`) |

Updates are transactional under the shadow locks: any of the nonzero paths leaves the databases as they were.

## Related Commands

- [`groupadd`](./groupadd.md) — creates the object groupmod edits; also the recovery tool after a bad rename (`-n` back).
- [`groupdel`](./groupdel.md) — removal; refuses primary groups just like you would expect.
- [`usermod`](./usermod.md) — the user-shaped twin; its `-g`/`-G` edit the user side of the same relationship.
- [`groupmems`](./groupmems.md) — member-list editing on older releases (where `-U` does not exist).
- [`gpasswd`](./gpasswd.md) — passwords, administrators, and membership with prompts instead of argv hashes.
- [`grpck`](./grpck.md) — post-change integrity check for the files groupmod rewrites.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together.
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: What are the side effects of `groupmod -n old new` — name three things that break and three that don't?

Break (name-keyed): `%old` rules in sudoers, group references in scripts/application configs, NFS export lists and systemd `Group=` lines that name the group. Don't break (number-keyed): file ownership, setgid directories, process credentials, ACL entries — all of those store the GID and are untouched by a rename. The asymmetry is the interview point: the group database change is trivial, the configuration sweep is the real work, and `getent group new` plus a grep for the old name is the verification pair.

### Q: After `groupmod -g 2100 deploy`, what state is the system in, and what are the next two commands you run?

The database is consistent: `deploy` is GID 2100 in `/etc/group`/`/etc/gshadow`, and every user whose primary group was `deploy` now has 2100 in `/etc/passwd`. The filesystem is not: files owned by the old GID now show a bare number. Next: `find / -xdev -group OLDGID` to enumerate the damage, then `find / -xdev -group OLDGID -exec chgrp 2100 {} +` to reattach. And you do it promptly — the old number is now free for allocation, and whoever grabs it inherits those files.

### Q: Why does `groupmod -g` not enforce GID_MIN/GID_MAX, and what's the operational consequence?

Manual assignment is treated as a deliberate administrator decision — the man page states no checks are performed against the login.defs ranges. The ranges exist to keep auto-allocation (`groupadd`, `useradd`) inside bands so that, say, system identities stay below 1000 and humans above; nothing stops you from hand-placing a group anywhere. Consequence: GID hygiene is now your problem. Runbooks should pin service GIDs explicitly and audit for outliers (`getent group | awk -F: '$3 > 60000'`), because the tool will not do it.

### Q: Your rename script does `groupmod -n "$new" "$old"`. It once succeeded with a name `groupadd` would have rejected. Explain.

Group creation and group renaming validate differently: `groupadd` enforces the group-name grammar (letters, digits, underscore, dash, optional trailing `$`, no leading dash, not fully numeric, ≤32 chars) because a bad name would be born broken. `groupmod -n` on the tested recent release accepted a syntactically invalid name — re-validation at rename time is not guaranteed. Lesson: validate in the script (`case`/regex), and never treat the tool's acceptance as a correctness certificate.

### Q: What is `-o` for, and when is a duplicate GID actually the right answer?

`-o` relaxes the uniqueness check so a group can share a GID with another. The legitimate cases are all migrations: a legacy group name that must keep resolving onto an existing access set while you rename references over, or a filesystem baked with a foreign GID that a local name must map onto. As a permanent design it is an audit hazard — `ls -l`, ACLs, and permission checks show numbers, so two names with one GID are indistinguishable after the fact, and membership changes to one alias appear to "leak" to the other.

### Q: Script checks `if groupmod ...; then` but prod failures showed exit 13 with no stderr detail. What is 13?

Exit 13 is `E_PAM_ERROR`: on PAM-enabled builds, groupmod consults PAM (account/session phases) and PAM refused or errored — the man page says the detail goes to syslog under facility `groupmod`, not to your terminal. It is one of three PAM-shaped codes (11 cleanup service, 12 username determination, 13 PAM error) that only appear when PAM is in the path. Debug with `journalctl`/syslog for the pam modules involved; the groupmod-level message is intentionally terse.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/groupmod.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
