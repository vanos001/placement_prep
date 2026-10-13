# userdel — delete a user account and its identity

## Overview

`userdel` removes an account from the system databases: the `/etc/passwd` and `/etc/shadow` entries, the per-user group (when `USERGROUPS_ENAB` made useradd create one), and subordinate ID ranges. It ships in the `passwd` package (upstream shadow suite) at `/usr/sbin/userdel`. Crucially, it is conservative about the filesystem: by default it deletes **no files at all** — not the home directory, not the mail spool. Only `-r` removes those two specific paths, and everything the user owned anywhere else on the system remains, orphaned into numeric-UID ownership.

This restraint is the tool's defining characteristic and the source of most interview questions about it. Deletion on Unix is a database operation, not a filesystem purge: the man page explicitly instructs admins to "manually check all file systems to ensure that no files remain owned by this user". Tools like Debian's `adduser --deluser` (via `deluser`) wrap userdel with extra filesystem policy, but the shadow primitive does one transactional thing.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/userdel |
| First appeared | System V lineage; shadow suite (Julianne F. Haugh, 1988+), maintained by shadow-maint |
| Standards | Not POSIX; specified by LSB |

## Synopsis

```
userdel [options] LOGIN
```

Common one-line forms:

```
userdel bob            # databases only; files untouched
userdel -r bob         # also remove home directory and mail spool
userdel -f bob         # force despite running processes / non-owned home files
```

## How It Works

### What is removed, in order

```
/etc/passwd     LOGIN line deleted
/etc/shadow     LOGIN line deleted
/etc/group      per-user group deleted (if USERGROUPS_ENAB-created and empty-safe)
/etc/gshadow    matching secure entry
/etc/subuid     subordinate UID range line
/etc/subgid     subordinate GID range line
--- with -r only ---
/home/LOGIN     home directory tree (as recorded in passwd)
/var/spool/mail/LOGIN   mail spool file
```

The database edits happen under the standard shadow locks, so the removal is atomic across files: either the account is gone everywhere or nowhere (an error mid-way leaves the account intact). The home deletion with `-r` happens after the database update and is the only part that can fail messily — hence the dedicated exit code 12.

If the login also appears as a *member* of other groups in `/etc/group`, those membership slots are cleaned from the group lists; groups with remaining members stay.

### The default: keep everything

Without `-r`, the home directory and mail spool survive, along with every file the user ever touched elsewhere (`/var/www`, `/tmp` strays, cron outputs, NFS content). This is safer than it sounds and less useful than it looks. Safe, because UID-reuse accidents — the next user getting the old UID and inheriting the old home — are exactly what this design prevents at the DB level while leaving files for a human to adjudicate. Less useful, because most operators *do* want the files gone and must run `-r` or clean up by hand.

The canonical post-deletion audit:

```bash
# find every file still owned by the deleted account's numeric UID
find / -xdev \( -nouser -o -uid 2100 \) -print 2>/dev/null
```

`-nouser` matches files whose UID no longer maps to a name — the direct signature of a deleted account. NFS-mounted trees need the same sweep per mount, since `-xdev` stops at filesystem boundaries.

### A complete offboarding sequence

```
1. record ownership       id LOGIN; getent passwd LOGIN > offboarding.log
2. archive the home       tar czf archive.tgz "$(getent passwd LOGIN | cut -d: -f6)"
3. soft-disable           usermod -L -e 1 LOGIN          (kill logins now)
4. stop processes         loginctl terminate-user LOGIN; pkill -u LOGIN
5. purge name-keyed data  crontab -r -u LOGIN; atq | ...; mail spool review
6. delete the account     userdel -r LOGIN
7. sweep the disk         find / -xdev -nouser -ls
8. review groups          getent group | grep LOGIN   (should be empty)
```

Steps 3-4 are why exit 8 exists: doing them *before* userdel makes the force flag unnecessary. Steps 6-7 embody the tool's philosophy — the database operation and the filesystem sweep are separate, human-reviewable actions.

### When deletion refuses

userdel checks for running processes owned by the account (on Linux, properly — not just utmp) and exits 8 if any exist. The man page's recommended sequence is to kill the processes, or lock the password/account first and delete later. `-f` overrides this, plus one more case: deleting an account whose home directory is owned by *someone else* (a situation that itself signals a prior mistake). `-f` is deliberately narrow — it exists for automation and recovery, not as a default.

Another refusal: shadow-based group handling will not delete the per-user group if `USERGROUPS_ENAB` says the group is tied to the account while other users still name it as primary.

### NIS and external databases

userdel only operates on local files. On a NIS client, account data lives on the server and the man page states you cannot remove NIS attributes locally. The same boundary applies conceptually to LDAP/SSSD-backed users: userdel will happily fail or do nothing useful, because `/etc/passwd` never contained them. Know which identity store an account came from before deleting it.

### The per-user group question

When `useradd` created a same-name primary group (`USERGROUPS_ENAB yes`, the Debian/Fedora default), userdel removes that group together with the account. Two complications:

```
case A: the group is empty and named after the user   -> removed
case B: the group has other members or is referenced  -> kept, deletion of the
        group is skipped rather than breaking the other users
```

The man page ties this to `USERGROUPS_ENAB` explicitly. If the account's primary group was instead some shared group (`-g staff` at creation), nothing happens to that group — userdel never deletes groups that predate the user. Group surgery beyond the per-user group is `gpasswd`/`groupdel` territory.

### userdel vs the wrappers

| Tool | Layer | Home policy | Extra behavior |
| --- | --- | --- | --- |
| userdel | shadow primitive (C) | keep unless -r | strict database transaction |
| deluser (Debian) | Perl wrapper around userdel | flag-driven (--remove-home, --remove-all-files) | adduser.conf policy, backups, hooks |
| SSSD/LDAP admin tools | directory service | n/a | not local accounts at all |

`deluser --remove-all-files` exists precisely because userdel will not chase files across the filesystem; it runs a system-wide find and chowns/deletes by UID. In interviews, describing this layering correctly ("userdel is the transactional primitive, deluser adds filesystem policy") signals you know where the boundaries are.

## Options That Matter

| Option | Effect |
| --- | --- |
| -r | remove the home directory (per the passwd entry) and the mail spool |
| -f | force: delete even with running processes, and even if home is not owned by the user |
| -R CHROOT_DIR | operate inside a chroot (image building, recovery) |
| -P PREFIX | use PREFIX/etc files without chrooting |
| -Z | remove any SELinux user mapping for the account |

There is no "dry run" and no "archive home" flag. Archival is `tar`/`mv` before the call, which is why so many shop runbooks make offboarding a script rather than a one-liner.

## Usage Patterns

```bash
# Plain deletion: databases only, all files preserved for manual adjudication
userdel departed
find / -xdev -nouser -ls 2>/dev/null | head     # what did they leave behind?
```

```bash
# Standard offboarding: remove account, home, and mail spool
userdel -r departed
```

```bash
# Archive first, then delete (the responsible default for real users)
tar czf /srv/departed-home.tar.gz /home/departed
userdel -r departed
```

```bash
# Refusal path: the account still has processes (exit 8)
userdel departed         # userdel: user departed is currently used by process 4471
loginctl terminate-user departed 2>/dev/null; sleep 1
userdel -r departed
```

```bash
# Soft-disable now, delete in a maintenance window
usermod -L -e 1 departed       # lock + expire (see usermod)
# ...later...
userdel -r departed
```

```bash
# Delete a service account that never had a home
userdel -r svc-old         # -r is a no-op for files if no home/spool exists
```

```bash
# Recycle the UID consciously: audit what the old UID still owns first
getent passwd 2100 || find / -xdev -uid 2100 -exec ls -ld {} + 2>/dev/null
```

```bash
# Remove a user inside a mounted image during a rebuild
userdel -R /mnt/rootfs -r olduser
```

```bash
# Confirm the per-user group was removed but shared groups survived
getent group departed || echo "per-user group gone"
getent group docker && echo "shared groups untouched"
```

```bash
# Verify the shadow side is clean too (root or shadow-group member)
sudo grep -c '^departed:' /etc/shadow /etc/passwd 2>/dev/null
```

```bash
# Batch offboarding with per-user logging and safe failure handling
while read -r u; do
  if userdel -r "$u" 2>>offboard.log; then echo "deleted $u"; else
    echo "FAILED $u (rc=$?)" >> offboard.log; fi
done < leavers.txt
```

## Nuances and Gotchas

- **Home is NOT deleted by default.** The single most-tested fact about userdel. `-r` is opt-in; comparing with `deluser --remove-home` (Debian wrapper) or `userdel -r` on other Unices trips up people who switch dialects.
- **`-r` follows the passwd entry.** If the account's home path was bogus or shared (`/home`, `/`), `-r` operates on that path — historically, bugs and abuses around `-r` and a manipulated home field are why `-f` exists and why you should sanity-check `getent passwd LOGIN` before deleting.
- **Orphaned files become `-nouser`.** After deletion, `ls -l` shows numbers instead of names. If a *new* account later reuses the UID, those files silently change ownership to the new user — the real security hazard of sloppy offboarding.
- **Running processes block deletion (exit 8).** Cron jobs, lingering `tmux`, systemd user units — any of these hold the UID. `-f` will force it, but the processes keep running as an account that no longer exists, and anything they write becomes `-nouser` or gets re-homed by the next UID reuse.
- **Cron and at jobs are not removed.** userdel has no opinion on `/var/spool/cron/crontabs/LOGIN`; the man page for usermod says the same about renames. Offboarding scripts must `crontab -r -u LOGIN` and purge at jobs explicitly.
- **The per-user group may be skipped.** If `USERGROUPS_ENAB` ties the group to the account and shadow considers it unsafe to remove (other users referencing it), the group survives. Verify with `getent group LOGIN`.
- **NIS/LDAP users are out of scope.** Exit 6 (user doesn't exist) is the typical result when the account lived in a directory service. Remove it where it is defined.
- **No undo.** There is no shadow trash can; the only rollback data is the `-` backup files (`/etc/passwd-`, `/etc/shadow-`) from the last edit. Treat deletion like `rm` on the database: verify the login name twice, especially in scripts looping over a list.
- **SELinux mappings need -Z.** On SELinux systems, the mapping survives deletion unless `-Z` is passed, leaving stray policy references.
- **Deletion order matters in scripts.** Delete the account *after* archiving its home but *before* reusing the UID; and run the `-nouser` sweep before any new account takes the number. Scripts that create-and-delete test users in CI are a common source of stray UID-1001 files under `/tmp`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | can't update password file |
| 2 | invalid command syntax |
| 6 | specified user doesn't exist |
| 8 | user currently logged in (has running processes) |
| 10 | can't update group file |
| 12 | can't remove home directory |

Exit 8 with exit 12 stack the failure modes of "still in use" and "files wouldn't go"; both are the cases where `-f` gets reached for — usually a sign to look at process lists first.

## Related Commands

- [`useradd`](./useradd.md) — the creation tool whose defaults (USERGROUPS_ENAB, home policy) userdel's cleanup mirrors.
- [`usermod`](./usermod.md) — soft-disable (-L, -e) is the usual prelude to userdel in offboarding.
- [`passwd`](./passwd.md) — lock semantics on the password side.
- [`gpasswd`](./gpasswd.md) — adjust group memberships that userdel only prunes.
- [`chage`](./chage.md) — expiry-based suspension as a non-destructive alternative.
- [`expiry`](./expiry.md) — login-time enforcement of aging state.
- [overview](./overview.md) — the shadow suite collection hub.
- [users-groups](../../admin/users-groups.md) — the underlying /etc files and UID ownership model.

## Interview Questions

### Q: What exactly does `userdel` delete, and what does it deliberately leave?

It deletes the account's rows in `/etc/passwd`, `/etc/shadow`, `/etc/group`/`/etc/gshadow` (the per-user group) and its subuid/subgid lines. By default it leaves the home directory, mail spool, crontabs, at jobs, and every file the UID owns anywhere. Only `-r` adds home + mail spool removal; crontabs/at jobs are never touched and must be removed manually.

### Q: Why is the "no file deletion by default" design a good idea, and when does it backfire?

It prevents the UID-reuse hazard: if files were deleted eagerly you lose evidence and restore options, but if they are *kept* without an audit, a future account that reuses the UID silently inherits them. It backfires on busy systems where nobody runs the `find -nouser` sweep, so orphaned files accumulate or get re-homed by accident. The design pushes a human decision to the filesystem layer.

### Q: `userdel -r` failed with exit 8. What does that tell you, and what are your options?

Exit 8 means the user currently has running processes — shadow checks this properly on Linux. Options: log them out (`loginctl terminate-user`, kill the PIDs), then retry; or soft-disable first (`usermod -L -e 1`) and delete during a maintenance window; or force with `-f`, accepting that the surviving processes now run as a nonexistent account and their future writes become `-nouser` files. Force-deleting a live session user is almost always the wrong fix.

### Q: How do you find all files that still belong to an account you just deleted?

`find / -xdev -nouser` — files whose owner UID maps to no name in `/etc/passwd`. Or search the specific old UID with `-uid N` if you recorded it. Run it per filesystem (drop `-xdev` per mount) because userdel does not touch anything outside the databases, and NFS trees need their own sweep. The result is also your checklist for deciding delete, chown, or archive.

### Q: Why can't you userdel an LDAP-backed user on a machine with SSSD?

Because userdel edits local files only. The account never had an entry in `/etc/passwd`; it is resolved at NSS level from the directory. Exit 6 ("user doesn't exist") is the usual outcome. The account must be removed where it is defined (LDAP entry, or an id range/provider policy), then caches invalidated. Interviewers use this to test the boundary between the shadow file tools and NSS-based identity.

### Q: A script does `userdel -r "$u"` for a list of users read from a file. Give two failure modes beyond "user doesn't exist".

First: exit 8 mid-loop when any listed user still has processes — with `set -e` the loop dies halfway, leaving a partially processed list. Second: the home-path hazard — if an entry's home field was tampered with or points at a shared directory, `-r` recursively deletes that path; sanity-check `getent passwd "$u"` (home under an expected base, owned by the user) before the call. Both are reasons offboarding scripts log and verify instead of trusting the loop.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/userdel.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
