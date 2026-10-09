# gpasswd — administer /etc/group and /etc/gshadow

## Overview

`gpasswd` is the group-side administrator of the shadow suite: it manages group membership, group *administrators*, and group passwords in `/etc/group` and `/etc/gshadow`. Root defines who may self-manage a group (`-A` administrators) and who is in it (`-M` members); group administrators then add and remove members (`-a`/`-d`) and set the group password that lets outsiders join via `newgrp`. It ships in the `passwd` package (upstream shadow suite) at `/usr/bin/gpasswd`, setuid root because it edits root-owned files.

It is often confused with `usermod -aG` (the user-side view of the same `/etc/group` lines), with `newgrp` (the consumer of the group passwords gpasswd sets), and with `groupadd`/`groupmod`/`groupdel` (which manage the *existence* of groups, not their membership/administration). The man page's own framing is the mental model: every group can have administrators, members, and a password — and gpasswd is the only tool that exposes all three.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 1 |
| Path | /usr/bin/gpasswd (setuid root) |
| First appeared | shadow suite original (1990s, shadow-utils lineage) |
| Standards | None (shadow-specific); not POSIX, not LSB |

## Synopsis

```
gpasswd [option] GROUP
```

Common one-line forms:

```
gpasswd docker                       # set the group password (self, if admin)
gpasswd -a bob docker                # add bob (admin of the group, or root)
gpasswd -M alice,bob root            # root: set exact member list
gpasswd -A alice root                # root: make alice the group's admin
gpasswd -R docker                    # restrict newgrp to members
gpasswd -r docker                    # remove the group password entirely
```

The help output ends with a constraint that shapes every script: **"Except for the -A and -M options, the options cannot be combined."** One action per invocation; `-A` and `-M` may share a call.

## How It Works

### The two files and their four fields

```
/etc/group    docker:x:999:alice,bob
                       |   |
                       |   + member list (plain names)
                       + group password placeholder ("x" = see gshadow)

/etc/gshadow  docker:$y$5$hash::alice,bob
                        |    |    |
                        |    |    + administrators list  <- -A
                        |    + group password            <- bare gpasswd / -r / -R
                        + encrypted password or markers
```

The gshadow password field accepts three states with distinct meanings:

```
<hash>   non-members can newgrp in after typing this password
!        restricted: only members may join / use the group  (-R)
empty    no password: newgrp by non-members is refused unless an admin opens it
```

`-r` removes the password entirely (empties the field); `-R` writes `!` — the deliberate "members only" marker. Both are group-admin or root actions on most configurations.

### Who may do what

```
role                 -a -d   set password   -M   -A   -R -r
root                 yes     yes            yes  yes  yes
group administrator  yes     yes (prompt)   no   no   yes
plain member         no      no             no   no   no
anyone else          no      no             no   no   no
```

The design is the reason the tool exists: delegate *membership management* of one group (say, `docker` on a build box) to a team lead without handing them root or letting them touch other groups. The man page spells out the delegation mechanics — "System administrators can use the -A option to define group administrator(s)" — and notes root implicitly holds every right.

The verified failure path for the not-your-group case, from this container (user `z`, group `sudo`, no membership, no admin rights):

```
$ gpasswd -a z sudo
gpasswd: Permission denied.        (exit 1)
```

### Group passwords and newgrp: the point of it all

A group password exists to let non-members *enter* a group with `newgrp`:

```
alice (not a member of docker):
  $ newgrp docker
  Password: ********        <- the password gpasswd set
  (now shell runs with docker as primary group; SGID-writable dirs open up)

with -R applied instead:
  $ newgrp docker
  Password: ...             <- even the correct password does not help
  newgrp: Permission denied
```

Members never need the password (`newgrp` lets them in silently); that is the man page's note — "If a password is set the members can still use newgrp without a password, and non-members must supply the password." The security trade-off is stated just as bluntly in the same section: a group password is "an inherent security problem since more than one person is permitted to know the password", which is why Debian-family guidance prefers explicit membership (`gpasswd -a`, `usermod -aG`) over shared passwords, and why `-R`/`-r` exist to close the door.

### The admin-only password prompt

`gpasswd GROUP` with no options — invoked by a group administrator — prompts for a new group password. Root gets the same behavior; a plain member gets "Permission denied". There is no flag to *set* the password per se: the bare invocation is the set-password verb. That asymmetry (every other action has a flag; the password is the default) comes straight from the original shadow design and still surprises people.

## Options That Matter

| Option | Effect |
| --- | --- |
| (no option) | set/change the group password (admin or root) |
| -a USER | add USER to the group (admin or root) |
| -d USER | remove USER from the group (admin or root) |
| -M USER,... | set the exact member list (root) |
| -A ADMIN,... | set the exact administrator list (root) |
| -R | restrict: write `!` so only members may join (admin or root) |
| -r | remove the group password (admin or root) |
| -Q CHROOT_DIR | operate inside a chroot (note: -Q, not -R, on this tool) |

Combinability: `-A` and `-M` may appear together; everything else is one verb per call. `gpasswd -a` and `-d` cannot be batched in one line — loop over the names.

## Usage Patterns

```bash
# Root hands a group to a team lead: admin rights, seed members in one call
gpasswd -A tlara -M tlara,dev1,dev2 docker
```

```bash
# The team lead now self-services membership (no root involved)
gpasswd -a dev3 docker
gpasswd -d dev1 docker
```

```bash
# Root sets the exact member list wholesale (idempotent CM style)
gpasswd -M alice,bob,carol docker
```

```bash
# Open the group to outsiders with a password... (not recommended, but know it)
gpasswd docker
# New password / Re-enter new password

# ...or close the door: members-only (newgrp refuses non-members)
gpasswd -R docker
```

```bash
# Remove a shared group password a predecessor left behind
gpasswd -r docker
grep '^docker:' /etc/gshadow
# docker:::alice,bob
```

```bash
# Check who can administer and who is in the group
grep '^docker:' /etc/gshadow | awk -F: '{print "admins:", $3, "members:", $4}'
```

```bash
# Rotate membership for a leaver across two groups
gpasswd -d leaver docker
gpasswd -d leaver qa
```

```bash
# Bulk add a list of users (one verb per call, per the man page)
for u in $(cat build-team.txt); do gpasswd -a "$u" docker; done
```

```bash
# Manage a group inside a mounted image
gpasswd -Q /mnt/rootfs -a user1 docker
```

```bash
# Audit every group that still carries a password or restrict marker
sudo awk -F: '$2 != "" && $2 != "x" && $2 != "!" {print "PASSWORD:", $1}
             $2 == "!" {print "RESTRICTED:", $1}' /etc/gshadow
```

```bash
# Diff current members against a desired list, then converge (CM-ish)
getent group docker | cut -d: -f4 | tr ',' '\n' | sort > /tmp/now.txt
sort build-team.txt > /tmp/want.txt
comm -13 /tmp/now.txt /tmp/want.txt | while read -r u; do gpasswd -a "$u" docker; done
comm -23 /tmp/now.txt /tmp/want.txt | while read -r u; do gpasswd -d "$u" docker; done
```

## Nuances and Gotchas

- **`gpasswd -R` and `-r` are one keystroke apart with opposite outcomes.** `-R` writes the restrict marker `!` (members only, even with a password); `-r` removes the password (field empty — non-members are refused unless an admin opens it). Auditing scripts that grep for `!` in gshadow are looking for `-R`'s fingerprint.
- **The man page calls group passwords an inherent security problem.** Shared secrets rotate badly, never expire, and outlive their admins. Prefer `-a`/`-M` membership or `-R` restriction; treat a password-bearing gshadow entry as a finding.
- **Options don't combine.** `gpasswd -a x -a y group` is a syntax error, and `-a`/`-d` are not batchable. Only `-A` + `-M` share a call. Loops, not one-liners.
- **-A is exclusive, not additive.** `gpasswd -A alice docker` *replaces* the administrator list — any previous admins not re-listed lose their rights, same semantics as `usermod -G` without `-a`. There is no `-aA` append form.
- **Admins can remove themselves and each other.** The model has no hierarchy among administrators; delegation is co-equal. Hand out `-A` accordingly.
- **`-Q` is the chroot flag here** (not `-R` — that means restrict). Copying the `-R CHROOT_DIR` habit from useradd/usermod produces a surprising membership change.
- **Empty password vs `!`:** an *empty* password field does not mean "passwordless join" — non-member `newgrp` is refused; a *set* password admits non-members who know it; `!` refuses everyone but members. The three-state logic is the interview nugget.
- **Changes are next-login visible** for supplementary-group purposes: `newgrp GROUP` applies immediately in the current shell, but a normal new session picks up group memberships at login; long-running sessions do not retro-gain groups.
- **NIS/LDAP groups** are out of scope: gpasswd edits local files; directory-backed groups change in the directory.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | permission denied (not admin/root, PAM failure) |
| 2 | invalid combination of options |
| 3 | unexpected failure, nothing done |
| 4 | unexpected failure, group file missing |
| 5 | group file busy, try again |
| 6 | invalid argument to option |

The 0-6 family mirrors `passwd`'s codes because both tools share the shadow suite's common exit conventions — a tell that they are siblings from the same codebase.

## Related Commands

- [`usermod`](./usermod.md) — the user-side way to change the same memberships (-aG).
- [`passwd`](./passwd.md) — the account-password sibling sharing gpasswd's exit-code family.
- [`chage`](./chage.md) / [`expiry`](./expiry.md) — aging enforcement in the same collection.
- [`useradd`](./useradd.md) — creates accounts and their per-user groups that gpasswd then administers.
- [`userdel`](./userdel.md) — removal end of the account lifecycle.
- [`chfn`](./chfn.md) / [`chsh`](./chsh.md) — the other self-service editors.
- [overview](./overview.md) — the shadow suite collection hub.
- [users-groups](../../admin/users-groups.md) — group mechanics, gshadow anatomy, and newgrp interplay.

## Interview Questions

### Q: What are the three things a group can have in shadow's model, and which tool manages them?

Administrators, members, and a password. `gpasswd` manages all three: `-A` sets administrators, `-M` sets members, bare `gpasswd` sets the password, with `-r`/`-R` clearing it or marking members-only. `/etc/group` holds the public member list; `/etc/gshadow` holds the password and administrator lists. usermod/useradd can touch membership but cannot delegate administration — gpasswd is the only tool with the full surface.

### Q: Explain what `gpasswd -R group` does and how it differs from `gpasswd -r group`.

`-R` writes the restrict marker `!` into the gshadow password field: non-members are refused by `newgrp` even if they know a password — members-only access. `-r` removes the password entirely: non-members are also refused (there is nothing to type), but the semantics differ — the group is back to "no password defined" state, and a later bare `gpasswd group` can set one. In both cases current members are unaffected; the flags only govern the *entry* path for outsiders.

### Q: How does a non-member actually get into a password-protected group, and why do most sites avoid this feature?

`newgrp group` prompts for the group password; on success the shell switches its primary group to it (opening SGID-shared directories). Sites avoid it because a group password is a shared, non-rotating, non-auditable secret — the man page itself calls it an inherent security problem. Explicit membership via `gpasswd -a` or `usermod -aG` keeps identity per-person and revocable.

### Q: `gpasswd -A alice docker` was run and bob lost admin rights. What happened?

`-A` sets the complete administrator list — it is a replace, not an append. To keep both: `gpasswd -A alice,bob docker` in one call (the one allowed combination with `-M`). The same replace-vs-append design note as `usermod -G` without `-a`, and the same fix pattern: list the full desired set, and audit after delegation changes.

### Q: Which users can run `gpasswd -a user docker` on a stock Debian box, and what does everyone else see?

Root and any administrator listed for `docker` in `/etc/gshadow` succeed. Everyone else — including current *members* (membership does not confer administration) — gets "gpasswd: Permission denied." with exit 1. This distinction between being in a group and administering it is the core access model of the tool and the reason `-A` exists.

### Q: Why does gpasswd have `-Q` for chroot while useradd/usermod use `-R`?

Historical flag budget within the shadow suite: in gpasswd, `-R` was already taken for "restrict access to the group", so the chroot option landed on `-Q`. It is a portability trap for scripts that template one chroot flag across the suite. The lesson: these are independent binaries with independent flag conventions, not one tool with subcommands.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/gpasswd.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
