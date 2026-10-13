# groupdel — delete a group (shadow low level)

## Overview

`groupdel` is the shadow suite's group removal tool: it deletes every entry referring to GROUP from `/etc/group` and `/etc/gshadow` and nothing else — no files are touched, no users are touched, no confirmation is asked. It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/groupdel`. It is deliberately minimal; most of its page is caveats rather than options, which tells you something about how much policy the authors were willing to take on.

`groupdel` is often confused with `userdel` (which removes a user *and*, under `USERGROUPS_ENAB yes` on Debian, the user's namesake primary group automatically), with `delgroup`/`deluser` (the adduser-family front ends that do more housekeeping and call groupdel underneath), and with the naive assumption that deleting a group somehow removes or reassigns the files that carry its GID — it does not. In practice you reach for `groupdel` to retire project/service groups, and for nothing else.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/groupdel |
| First appeared | System V lineage; shadow suite (Julianne F. Haugh, 1988+), now maintained by shadow-maint |
| Standards | Not POSIX; specified by LSB. Reads login.defs for MAX_MEMBERS_PER_GROUP only |

## Synopsis

```
groupdel [options] GROUP
```

Common one-line forms:

```
groupdel proj7                  # plain deletion, must not be a primary group
groupdel -f broken-legacy       # force even if it is somebody's primary group
groupdel -R /mnt/rootfs _nginx  # delete inside a staging root/chroot
```

## How It Works

### The primary-group guard

The single most important semantic: **you may not remove the primary group of any existing user.** Every account's `/etc/passwd` line names a GID that must keep resolving; if GROUP is that GID, groupdel refuses with exit 8 rather than leave a dangling primary group. The man page's CAVEATS states the remedy bluntly: remove the user first, then the group.

```
$ grep deploy /etc/passwd
deploy:x:2100:2100:service account:/srv/deploy:/usr/sbin/nologin
$ groupdel deploy
groupdel: cannot remove the primary group of user 'deploy'   # exit 8
$ userdel deploy && groupdel deploy                           # correct order
```

`-f/--force` overrides this guard. It exists for repair work — a group left behind by a botched user deletion, a stale NIS-era artifact — and will happily create users whose primary GID no longer exists. That state is legal but mostly unobservable: `ls -l` prints the bare number `2100`, `getent group 2100` returns nothing, and login tools may log warnings. Reserve `-f` for scripted cleanups where you know the referencing users are going away too.

### What actually changes

Two file edits under the shadow locks, then the entry is gone from:

```
/etc/group    proj7:x:2100:alice,bob   -->  (deleted)
/etc/gshadow  proj7:!::alice,bob       -->  (deleted)
```

Nothing else. Files previously owned by the group keep their numeric GID and become "orphaned" — visible as numbers in `ls -l` until you chgrp them or reuse the GID (which silently hands their access to the new group). The man page says you should manually check all filesystems for files still owned by the group:

```bash
groupdel proj7
find / -xdev -nogroup -ls      # everything that used to be proj7's
find / -xdev -nogroup -exec chgrp --reference=/some/ref {} +
```

### Name resolution and its limits

The GROUP argument is resolved through the local group database (`/etc/group`, plus `/etc/gshadow` for the shadow half). With NSS configured (files first, then LDAP/SSSD), `getent` may see groups that groupdel cannot manage: the tool only edits the flat files, so a group that resolves via LDAP is not groupdel's business and attempting it fails with "does not exist" unless it also exists locally. Deleted groups also linger in running processes: a member's supplementary group list (from PAM/login time) keeps the old GID until they re-login, so access revocation via groupdel is not instantaneous for existing sessions.

### Interaction with userdel

On Debian, `useradd`/`userdel` create and remove the per-user group automatically (`USERGROUPS_ENAB yes` in login.defs). The consequence most people trip on: for typical user accounts you rarely call groupdel at all — `userdel bob` already removed group `bob` — while for shared project groups `groupdel` is exactly the right tool because no single user owns them.

### The whole decision, at a glance

```
              groupdel GROUP
                    |
        GROUP resolves in local db? --no--> exit 6
                    | yes
        some user's primary GID?  --yes--> -f given? --no--> exit 8
                    |                          | yes (force)
                    | no                       |
                    +------------+-------------+
                                 |
                 lock /etc/group + /etc/gshadow
                 delete entries from both
                                 |
                 release locks; files keep old GID
                 (find / -xdev -nogroup becomes your to-do list)
```

Note what is absent: no dependency scan of sudoers, systemd units, ACLs, or NFS exports; no filesystem sweep; no prompt. The guard is the entire policy layer.

## Options That Matter

| Option | Effect |
| --- | --- |
| *(none)* | `groupdel GROUP` — the only positional form; GROUP must exist |
| `-f` | Force removal even when GROUP is some user's primary group (creates dangling primary GIDs — repair mode only) |
| `-R DIR` | Apply changes inside chroot DIR (image building; only absolute paths) |
| `-P DIR` | Prefix mode: edit DIR's /etc files without chroot (cross-compile staging) |

That is the whole option list. There is no dry-run, no verbose, no confirmation — check twice, run once.

## Usage Patterns

```bash
# Retire a finished project group (members keep their accounts)
groupdel proj7
```

```bash
# Cleanup sweep after deleting many users: groups with no members left
for g in $(getent group | awk -F: '$4 == "" && $3 >= 5000 {print $1}'); do
    getent passwd | grep -q ":$g$" || groupdel "$g"
done
```

```bash
# Remove a service group along with its account, package-manager style
userdel -r svc-backup 2>/dev/null; groupdel svc-backup 2>/dev/null || true
```

```bash
# Repair: a group is stuck as primary of a user that no longer exists
# (stale passwd entry without the user) - inspect first, then force
getent passwd | awk -F: '$4 == 2100 {print}'   # who references GID 2100?
groupdel -f legacy2100
```

```bash
# Find what a group owned before deleting it (the numbers you must reassign)
grp=$(getent group proj7 | cut -d: -f3); find / -xdev -group "$grp" -ls
```

```bash
# Same, by name, after deletion - now shows bare GIDs as -nogroup
groupdel proj7 && find / -xdev -nogroup -ls
```

```bash
# Inside a container image build (chroot form)
groupdel -R /mnt/rootfs builduser
```

```bash
# Cross-compile staging tree (prefix form)
groupdel -P /target oldbuild
```

```bash
# Idempotent delete for provisioning teardown
getent group proj7 >/dev/null && groupdel proj7 || true
```

```bash
# Verify the deletion and that nothing still references it
getent group proj7; getent passwd | awk -F: '$4 == 2100'; find / -xdev -nogroup
```

```bash
# Re-check supplementary-group state of live sessions after deletion
ps -eo user,pid,group | grep -i proj7 || echo "no live sessions in proj7"
```

```bash
# Move users off a group before retiring it (new primary), then delete
grep -E ':2100$' /etc/passwd | cut -d: -f1 | \
  xargs -r -n1 usermod -g users
groupdel proj7
```

```bash
# One-shot retirement runbook with audit trail (append-only log)
{
  getent group proj7
  find / -xdev -group "$(getent group proj7 | cut -d: -f3)" -ls
} >> /var/log/group-retire-$(date +%F).log
groupdel proj7
```

## Nuances and Gotchas

- **Exit 6 vs exit 8.** `group 'x' does not exist` is 6; `cannot remove the primary group of user 'y'` is 8. Both are "refused", but only the first means your group name was wrong — the second means someone depends on it, and `-f` is the (dangerous) override.
- **Deletion is not access revocation.** Existing sessions keep their supplementary group list until re-login, and root's ability to read files never depends on groups. If you need timely revocation, terminate sessions (`pkill -u`, `pkill --group`) in the same runbook step.
- **No confirmation, no undo.** The edit is two `sed`-like rewrites under lock. The only recovery is re-creating the group with the same name and GID (`groupadd -g OLDGID name`) — re-creating is also the *fix* if you delete by accident, precisely because file ownership is numeric.
- **`-f` creates unobservable state.** Users whose primary GID no longer exists break in confusing ways: `id` prints `gid=2100` with no name, `find -nogroup` lights up, and some tools refuse the account. The guard groupdel enforces is one of the few the suite gives you for free — defeating it should be a documented decision.
- **NSS visibility is not groupdel's reach.** With SSSD/LDAP in play, `getent group` can show groups groupdel cannot delete; conversely, groupdel can leave `/etc/group` fine but gshadow stale — which is what `grpck` catches.
- **userdel already handles the common case.** Deleting user `bob` removes namesake group `bob` on Debian defaults; following up with `groupdel bob` just earns you exit 6. Check `USERGROUPS_ENAB` before scripting.
- **Files are only half the residue.** Group membership also lives in `sudoers` (`%proj7`), `crontab` group fields, NFS exports, ACLs (`getfacl` shows group entries), and systemd unit `Group=` lines. None of them block deletion; all of them can break after it.
- **Running processes keep the GID open.** A daemon started with that group continues to run with it (numbers, again). Restart services that were group-bound, or the retirement is cosmetic.
- **Empty member list is not a deletion precondition.** groupdel happily deletes a group that still has supplementary members (they just lose that one bit of membership on next login); only *primary* membership is guarded. Scripts that want a softer retirement check `getent group GROUP` for a fourth field first.
- **Order matters for recovery tooling.** If you must rebuild, `groupadd -g OLDGID name` before the next group is allocated that number; `groupadd` picks "one past the highest used", so the longer the orphaned GID sits, the less likely a clean re-create is.
- **`find -nogroup` on huge trees is expensive.** The post-deletion sweep reads inodes across every filesystem you point it at; bound it with `-xdev`, target known trees first (`/srv /home /opt`), and schedule the full sweep off-peak. On NFS, other hosts' views may still hold the GID long after yours is clean.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 2 | invalid command syntax |
| 6 | specified group doesn't exist |
| 8 | can't remove user's primary group (unless `-f`) |
| 10 | can't update group file (lock contention, permission, stale `.lock` files) |

As elsewhere in the suite, the update is transactional: a refusal leaves both files untouched.

## Related Commands

- [`groupadd`](./groupadd.md) — the inverse operation; also how you recover a mistaken deletion at the same GID.
- [`groupmod`](./groupmod.md) — change name/GID when retirement is really a rename.
- [`userdel`](./userdel.md) — must run first when the group is a user's primary; also removes namesake groups itself.
- [`usermod`](./usermod.md) — move a user's primary group to a new GID before deleting the old one.
- [`gpasswd`](./gpasswd.md) — prune members one by one when you want to shrink rather than delete.
- [`grpck`](./grpck.md) — verifies the databases after scripted deletions.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together.
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: Why does groupdel refuse to delete a user's primary group, and what does -f actually do?

Every `/etc/passwd` entry carries a primary GID, and a lot of machinery assumes that number always resolves: login, `id`, file creation defaults, quota accounting. Deleting the group underneath a live account produces a primary GID with no name — legal at the kernel level (it is just a number) but unmanageable in practice. `-f` overrides the guard: the group is deleted anyway and the referencing users are left with a dangling primary GID. It exists for repair of already-broken state, not as a routine switch.

### Q: A developer deleted group `proj7` and now `ls -l` shows files owned by `2100`. Explain and fix.

Group ownership is stored as a number; after deletion nothing maps 2100 to a name, so `ls` prints the raw GID and `find -nogroup` finds everything. Two fixes depending on intent: re-create the group with the same GID (`groupadd -g 2100 proj7`) to make the numbers meaningful again, or reassign the files (`find / -xdev -nogroup -exec chgrp NEW {} +`) and let the GID go. What you must not do is ignore it — the next group allocated 2100 silently inherits every one of those files.

### Q: Order of operations to retire user `svc` and its group on Debian — and why?

`userdel svc` first: with `USERGROUPS_ENAB yes`, userdel removes the namesake group `svc` automatically, and it will refuse to delete a user while the *group* is still needed only if you did something exotic like `-f`ing the group away earlier. Trying `groupdel svc` first fails with exit 8 (it is svc's primary group). The only time groupdel leads is for *shared* groups with no primary owner — then it is `groupdel proj7` plus a filesystem sweep for orphaned GIDs.

### Q: What does groupdel NOT do that an interviewer expects you to name?

Three things: it does not touch any file owned by the group (you sweep with `find -nogroup` / `-group OLDGID` and `chgrp`); it does not terminate existing sessions whose supplementary group list still carries the GID (access persists until re-login); and it does not clean references in configuration such as sudoers `%group` rules, systemd `Group=`, ACLs, or NFS exports. Deleting the database entry is the trivial 10% of a group retirement.

### Q: When is `groupdel -f` legitimate?

When the referencing state is already broken and you are finishing the job: a group that is "primary" only because a corrupted or half-deleted passwd entry still names it, legacy artifacts from pre-shadow tooling, or migrations where you will delete the referencing users in the same controlled change window. It is a repair tool with a blast radius, so the legitimate uses all share one property: you have enumerated the referencing users first (`getent passwd | awk -F: '$4 == GID'`), and the dangling-primary window is zero or close to it.

### Q: You scripted `groupdel $g` in a loop and got exit 10 with "cannot lock /etc/group". What happened?

Exit 10 is the group-file update failure, and the message usually means lock contention or a stale `.lock` file: another shadow tool was mid-write, or an earlier killed run left `/etc/group.lock` behind. The fix is to serialize (don't run parallel group modifications), verify with `pgrep` that no shadow tool is running, remove stale lock files as root, and make the loop idempotent (`getent group $g >/dev/null && groupdel $g`) so a re-run after the fix is harmless.

### Q: Does deleting a group affect supplementary membership records, or primary ones, or both?

The database entry is one object: name, GID, password state, member list, administrators. Deleting it removes all of it in both files. The *effects* differ, though: primary membership (the GID in `/etc/passwd`) is protected by the exit-8 guard, while supplementary membership (being listed in the fourth field of other users' groups, or in `/etc/gshadow` member/administrator fields) just evaporates. Users who were supplementary members notice nothing until re-login; tools that resolve the group by name start failing immediately.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/groupdel.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
