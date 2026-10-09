# usermod — modify an existing user account

## Overview

`usermod` edits accounts that already exist: it rewrites `/etc/passwd` and `/etc/shadow` fields (name, UID, GID, shell, GECOS, home, expiry), adjusts group membership in `/etc/group`/`/etc/gshadow`, moves home directories, locks or unlocks passwords, and manages subordinate ID ranges. It ships in the `passwd` package (upstream shadow suite) at `/usr/sbin/usermod`, next to `useradd` and `userdel`, and — like them — is scriptable and non-interactive, which is why configuration management tools call `usermod` rather than any interactive wrapper.

The one-line summary hides how many side effects are *not* performed. `usermod` changes database rows; it does not chase your files around the filesystem, it does not rename mail spools or crontabs, and one of its most-used flag combinations (`-G`) is destructive by default. Most production incidents with this binary come from assuming it does more than the man page promises.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/usermod |
| First appeared | System V lineage; shadow suite (Julianne F. Haugh, 1988+), maintained by shadow-maint |
| Standards | Not POSIX; specified by LSB |

## Synopsis

```
usermod [options] LOGIN
```

Common one-line forms:

```
usermod -aG docker,adm alice   # append supplementary groups (never forget -a)
usermod -L alice               # lock the password ('!' prefix in /etc/shadow)
usermod -d /srv/home/alice -m alice   # move home to a new path
usermod -s /usr/sbin/nologin svc1     # disable interactive login
```

## How It Works

### Transaction model

Each `usermod` run locks `/etc/passwd`, `/etc/shadow`, `/etc/group`, and `/etc/gshadow` (the `.lock` files), rewrites the affected entries, and releases the locks. Changes across files are consistent at exit — there is no intermediate state where the new group exists but the user does not. What is *not* transactional is the filesystem around the database: home moves copy files, UID changes re-chown only selected trees, and everything else on disk keeps its old ownership until you act. The man page's CAVEATS section is short but strict: do not run this on a user who is executing processes, and change crontab/at ownership manually.

Checking whether the user is "logged in" is done properly on Linux — usermod refuses (exit 8) if processes owned by the account are running, not merely if a utmp entry exists.

### The -aG trap: replace vs append

`-G` sets the complete supplementary group list. Without `-a`, every group the user belonged to and did not re-list is removed:

```
before:            alice : alice sudo docker lpadmin
usermod -G docker alice
after:             alice : alice docker            # sudo and lpadmin GONE
usermod -aG docker alice
after:             alice : alice sudo docker lpadmin docker
```

The `-a` flag is only valid together with `-G` and exists solely to turn "set" into "append". Every Ansible module, cloud-init, and worst-practices thread devotes paragraphs to this because the failure mode is silent: the command exits 0, `id` still works, and the user's sudo access evaporates until someone re-adds it. The symmetric partner is `-r` (with `-G`): remove *only* the listed groups, keeping the rest.

If the same run passes `-aG` for a group the user already has, shadow de-duplicates; membership is a set in `/etc/group`, not a multiset.

### Lock and unlock: -L / -U

`-L` prepends `!` to the encrypted-password field in `/etc/shadow`; `-U` removes one `!`:

```
shadow before:   alice:$y$5$AbCd...:19900:0:99999:7:::
usermod -L alice
shadow after:    alice:!$y$5$AbCd...:19900:0:99999:7:::
```

Three things matter here. First, this locks *password* authentication only: SSH keys in `authorized_keys` keep working, because sshd does not consult the password hash. Second, `-L`/`-U` refuse to combine with `-p` in the same invocation. Third, the classic interview detail: the man page notes that locking only the password is usually not enough — if you mean "disable this account", also set the expiry date (`-e 1`, i.e. 1970-01-02), otherwise key-based and service-based access paths survive. Conversely, `-U` cannot rescue a field that contains more than one stray `!` (nested locks from multiple tools); edit the hash deliberately or use `passwd -d` and start over.

### -l: rename and everything it does not rename

`usermod -l new old` changes the login name in `/etc/passwd` (and the shadow entry name). Because file ownership is tracked by UID, not name, all files keep working; `ls -l` now displays the new name. But name-keyed artifacts are untouched:

```
/home/oldname/               home path unchanged (-d -m is a separate move)
/var/spool/mail/oldname      mail spool unchanged
/var/spool/cron/crontabs/old   crontab unchanged (man: rename manually)
at jobs                      at(1) spool entries unchanged
```

The account works after the rename, but mail delivery and cron continue to key off the *old* name until you move those artifacts. The man page states the crontab caveat verbatim: "You must change the owner of any crontab files or at jobs manually."

### -u: UID change — half-automated

`usermod -u 2200 alice` updates the passwd entry and then re-chowns the files **in the user's home directory tree** to the new UID. Files outside the home directory — `/var/www` content the user owned, `/tmp` strays, project trees under `/srv` — keep the old numeric UID, which now maps to no name (`ls -l` shows `2200` instead of a username). The standard sweep afterwards:

```bash
find / -xdev -uid 2100 -exec chown alice {} +
```

`-o` permits the new UID to collide with an existing one (the same escape hatch as useradd). The man page again: the user must not be executing processes while their UID changes, because any process holding the old UID keeps writing files that now look foreign.

### -d with -m: moving home

`-d NEWPATH` rewrites the home *path*; adding `-m` also moves the contents. Shadow first tries `rename(2)` (instant when old and new live on the same filesystem) and falls back to copying and deleting when they do not. If the new directory does not exist it is created; the move preserves symlinks rather than following them. Without `-m`, the database points at a path that may not exist — the user logs into a fresh, empty, nonexistent directory (`bash` complains and lands in `/`), and their old files are still parked at the old path. `-m` is only valid together with `-d`.

For the same "no running processes" reason, do this from a session that is not the user's own login.

### -g vs -G

`-g GROUP` changes the *primary* group (the GID in `/etc/passwd`). It does not chown the user's files to the new group; existing files keep their old group ownership, so new-file group semantics change while old files stay behind. `-G` (with or without `-a`) manages the *supplementary* list in `/etc/group`. The pair is orthogonal: `usermod -g staff -aG docker alice` is a legitimate single call.

### Which verb touches which file

```
verb              /etc/passwd   /etc/shadow   /etc/group    filesystem
-l  rename        name          name          member names  nothing (artifacts manual)
-u  set UID       UID           -             -             home tree re-chowned
-g  set primary   GID           -             members list  nothing (old files keep GID)
-G  set supplem.  -             -             members list  nothing
-d  set home      home          -             -             nothing
-dm move home    home          -             -             copy/rename + delete old
-L/-U lock       -             hash prefix   -             nothing
-e/-f aging      -             fields 7,8    -             nothing
-p  set hash     -             hash          -             nothing
-v/-V/-w/-W      -             -             -             /etc/subuid, /etc/gid
-s/-c            shell/GECOS   -             -             nothing
```

Reading that table column-wise is the fastest way to see why "usermod did it" and "the system reflects it" diverge: most verbs change one database cell and zero filesystem bytes.

### -e and -f: aging knobs

`-e EXPIRE_DATE` writes the account-expiration field (shadow field 8): after that date logins are refused regardless of password correctness. `-f INACTIVE` writes shadow field 7: the number of days *after a password expires* before the account is auto-disabled; `-1` disables the mechanism. These overlap with `chage` (`chage -E`, `chage -I`) and `passwd -i` — three front doors to the same two fields, which is a favorite trivia point. `usermod -e ""` clears an existing expiration.

### Subordinate ID management

`-v/-V` add/remove `/etc/subuid` ranges and `-w/-W` do the same for `/etc/subgid` (`usermod -v 200000-265536 alice`). These matter for rootless containers: a user's subordinate range is what `unshare -U`/`podman` map into the namespace. Note the asymmetry with `useradd`, which auto-allocates subid ranges at creation time; usermod only manages them on request.

## Options That Matter

### Identity and shell

| Option | Effect |
| --- | --- |
| -l NEWLOGIN | rename the account (home, mail, crontabs NOT renamed) |
| -u UID | new UID; home tree re-chowned, rest of filesystem manual |
| -o | allow duplicate UID (with -u) |
| -g GROUP | new primary group (existing files unchanged) |
| -s SHELL | new login shell (not validated against /etc/shells when root runs it) |
| -c COMMENT | rewrite the GECOS comment field |

### Groups

| Option | Effect |
| --- | --- |
| -aG LIST | **append** to supplementary groups (the safe daily form) |
| -G LIST | **replace** the whole supplementary list (destructive without -a) |
| -rG LIST | remove only the listed supplementary groups |

### Home, lock, expiry

| Option | Effect |
| --- | --- |
| -d HOME | new home path (path only) |
| -d HOME -m | new home path + move contents (rename(2), fallback copy) |
| -L / -U | lock / unlock password ('!' prefix on the shadow hash) |
| -e DATE / -e "" | set / clear account expiration |
| -f DAYS | days after password expiry before auto-disable (-1 = never) |
| -p HASH | write a crypt(3) hash directly |

### Subordinate IDs and special modes

| Option | Effect |
| --- | --- |
| -v / -V FIRST-LAST | add / remove subordinate UID range |
| -w / -W FIRST-LAST | add / remove subordinate GID range |
| -R CHROOT_DIR | operate inside a chroot |
| -P PREFIX | use PREFIX/etc files without chrooting |
| -Z SEUSER | SELinux user mapping |

## Usage Patterns

```bash
# Add a user to a group WITHOUT nuking their other memberships
usermod -aG docker alice
id alice                      # verify before and after
```

```bash
# Disable interactive login for a service account
usermod -s /usr/sbin/nologin svc-backup
```

```bash
# Fully disable an account (password AND any key-based path)
usermod -L -e 1 alice         # lock hash + expire account in the same call
```

```bash
# Move a home directory onto a bigger disk
usermod -d /srv/home/alice -m alice
ls -ld /srv/home/alice
```

```bash
# Rename an account, then fix the name-keyed artifacts yourself
usermod -l alice2 alice
usermod -d /home/alice2 -m alice2
mv /var/spool/mail/alice /var/spool/mail/alice2
```

```bash
# Re-number a UID after an NFS merge; sweep the rest of the disk after
usermod -u 2200 alice
find / -xdev -uid 2100 -exec chown alice {} + 2>/dev/null
```

```bash
# Change primary group and append one supplementary group in one shot
usermod -g developers -aG docker alice
```

```bash
# Unlock an account that was disabled for the contractor's leave
usermod -U -e "" contractor
```

```bash
# Set an absolute expiry for an intern account
usermod -e 2025-09-30 intern1
```

```bash
# Give a rootless-container user an explicit subordinate range
usermod -v 300000-365535 -w 300000-365535 builder
```

```bash
# Rotate a compromised password hash immediately (then force change at login)
usermod -p "$(openssl passwd -6 'NewInitial!')" alice
passwd -e alice
```

```bash
# Patch users inside a mounted image, not on the running host
usermod -R /mnt/targetfs -s /bin/bash rescueuser
```

```bash
# Remove just one membership while keeping everything else (the -G mirror of -aG)
usermod -rG docker alice
id -nG alice
```

```bash
# Audit before a -G replace so you can restore the exact set afterwards
id -nG alice | tr ' ' '\n' > /tmp/alice.groups
```

```bash
# Move a user into a subid-managed workflow: check the ranges usermod manages
grep '^alice:' /etc/subuid /etc/subgid
```

## Nuances and Gotchas

- **`-G` without `-a` is a REPLACE.** The single most expensive character in Linux administration is the missing `-a`. It is silent: exit 0, working account, revoked sudo. Institutionalize `usermod -aG` and have reviewers grep for `usermod -G`.
- **`-L` does not stop SSH keys.** The lock only neutralizes the password hash. "We locked the account" and "the attacker still has shell access" coexist; pair with `-e 1` and remove keys.
- **Double-lock is sticky.** If two tools each prepended `!` (usermod and passwd), a single `-U` removes one and shadow refuses to unlock a multiply-locked hash without manual intervention. Inspect `/etc/shadow` directly when unlock behaves oddly.
- **`-l` renames only the database row.** Home path, mail spool, crontabs, at jobs, and anything name-keyed in `/var` are yours to migrate. The man page calls out crontab/at specifically.
- **`-u` chowns only the home tree.** Every other file on disk keeps the old numeric UID. A `find -uid OLD` sweep is part of the operation, not an optional extra.
- **`-m` will not fight a running user.** Shadow checks for the account's processes and exits 8 — which surprises people doing `usermod` on their own account. Log the user out (or work from another admin session) first.
- **`-d` without `-m`** leaves the account pointing at a directory that may not exist: shell falls back weirdly, dotfiles never load. If you only wanted the path registered for a *new* directory, create and populate it yourself.
- **`-g` does not re-group old files.** New files follow the new primary group; old files keep the previous GID. Use `chgrp -R` (or `chown -R :group`) if the intent was a full migration.
- **`-p` is a footgun for secrets.** The hash goes through argv (`ps` snapshot) and possibly shell history. Prefer `passwd` (interactive) or `chpasswd` (stdin) for real secret delivery.
- **Root is often exempt from validation.** When run as root, `-s` does not check `/etc/shells`, so typos create unbootable logins discovered only at next login. Non-root invocations are additionally gated by PAM authentication.
- **SELinux and chroot flags change the blast radius.** `-R`/`-P` make it easy to modify the wrong filesystem's `/etc` — double-check which prefix you are pointing at in recovery scenarios.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | permission denied (or password-file update refused) |
| 2 | invalid command syntax (e.g. -a without -G) |
| 3 | invalid argument to option |
| 4 | specified user doesn't exist |
| 6 | specified group doesn't exist |
| 8 | user currently logged in / has running processes |
| 9 | new username (or UID) already in use |
| 10 | can't update password file |
| 11 | out of memory |
| 12 | can't move home directory |

Codes 8 and 12 deserve scripting attention: 8 means "retry after logging the user out", 12 means the database may have been updated but the filesystem step failed — verify state rather than blindly retrying.

## Related Commands

- [`useradd`](./useradd.md) — creates the account usermod edits; defaults live in /etc/default/useradd.
- [`userdel`](./userdel.md) — removal, with a different home-directory policy than usermod's move.
- [`passwd`](./passwd.md) — the PAM-integrated way to change passwords and lock/unlock.
- [`chage`](./chage.md) — same aging fields as -e/-f, with a friendlier listing mode.
- [`chfn`](./chfn.md) — GECOS field editor (a safer alternative to -c for full names).
- [`chsh`](./chsh.md) — shell changes with the /etc/shells gate usermod skips.
- [`gpasswd`](./gpasswd.md) — group-admin view of the /etc/group entries -G rewrites.
- [`expiry`](./expiry.md) — login-time enforcement of the expiry state -e configures.
- [overview](./overview.md) — the shadow suite collection hub.
- [users-groups](../../admin/users-groups.md) — how /etc/passwd, /etc/group and the shadow files model identity.

## Interview Questions

### Q: What is the difference between `usermod -L` and actually disabling an account?

`-L` prepends `!` to the password hash, which kills password authentication only. SSH public keys, cron jobs, and any service using the account do not care about the hash. To truly disable: `usermod -L -e 1 user` (lock plus account-expiration date), and remove/rotate `authorized_keys`. The interview point is knowing that the shadow hash is only one of several authentication paths into an account.

### Q: A colleague ran `usermod -G docker alice` and Alice lost sudo. Reconstruct what happened.

Without `-a`, `-G` sets the *complete* supplementary group list to exactly `docker`, removing every other membership including the `sudo` group. The fix is `usermod -aG sudo alice` (and -aG for anything else that vanished — check `/etc/group-` backups or a config-management history). Prevention: always `usermod -aG`; in tooling, use modules that compute the desired *set* rather than shelling out `-G` blindly.

### Q: Why does `usermod -u` not change ownership of all the user's files, and what is the cleanup?

usermod re-chowns only files under the (old) home directory. File ownership on Linux is numeric, and usermod deliberately does not walk the whole filesystem. The cleanup is `find / -xdev -uid OLDUID -exec chown user {} +`, run promptly before another account reuses the UID. Files in other filesystems need the sweep per-mount (`-xdev` skips them), which is exactly the detail interviewers want next.

### Q: `usermod -l newname oldname` succeeded, but the user's cron jobs stopped working. Why, and what else is likely broken?

Crontab entries are stored name-keyed (Debian: `/var/spool/cron/crontabs/oldname`), and the rename did not touch them; the man page states crontab/at ownership must be fixed manually. Also expect the mail spool (`/var/spool/mail/oldname`) and the home path to still reflect the old name — hence the usual follow-up: `usermod -d /home/newname -m newname`, `mv` the mail spool, and migrate the crontab (`crontab -u newname` from a saved file).

### Q: Explain what `usermod -d /newhome -m user` does when /newhome is on a different filesystem.

Shadow rewrites the home path in `/etc/passwd`, then moves the contents: it tries `rename(2)` first (which fails across filesystems) and falls back to copying the tree and removing the original. The new directory is created if absent. The user must have no running processes (exit 8 otherwise). It is the supported one-command alternative to `mkdir`/`cp -a`/`chown`/edit-passwd, and it preserves symlinks rather than dereferencing them.

### Q: When would you use `usermod -o -u 0 serviceacct`, and why is the answer usually "never"?

`-o` allows a duplicate UID, so `serviceacct` shares UID 0 with root — historically used for "root-equivalent but different name" logins to preserve accountability *in the passwd file only*. It is almost never justified: sudo already provides named, audited root access; duplicate UIDs break every tool that assumes UID uniqueness (quota, ps attribution, backups), and the accountability gain is illusory since the kernel sees root. The honest answer is "audit requirement corner cases during migrations; then remove it".

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/usermod.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
