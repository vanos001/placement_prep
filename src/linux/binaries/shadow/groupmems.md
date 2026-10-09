# groupmems — edit a group's member list (delegated administration)

## Overview

`groupmems` is the shadow suite's member-list editor: add a user to a group, delete one, purge the list, or print it — writing `/etc/group` and `/etc/gshadow` under the usual locks. Its distinguishing idea is *delegation*: the man page opens by saying it lets a user administer their own group membership list "without the requirement of superuser privileges", and describes itself as a tool for systems that configure users into their own namesake groups (the man page names Red Hat as the model). It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/groupmems`.

It is often confused with `gpasswd` (which owns the *group password* and the *administrators* field in addition to membership, and knows nothing about namesake-group self-service), with `usermod -aG` (one user, many groups — groupmems is one group, many users), and with `groupadd`/`groupdel` (which create and remove the group object itself). On Debian servers the delegation mode is rarely wired up — most shops manage membership centrally with `usermod`/`gpasswd`/directory services — so on stock systems `groupmems` mostly earns its keep as a root tool for scripted membership edits.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/groupmems |
| First appeared | shadow suite (Julianne F. Haugh, 1988+); self-service design documented for Red-Hat-style namesake groups |
| Standards | Not POSIX; not in LSB. PAM-aware on Debian builds; behavior partly configured via /etc/login.defs |

## Synopsis

```
groupmems -a USER  | -d USER  | -l  | -p     # one operation per run
groupmems -g GROUP -a USER                   # root: target an arbitrary group
```

Common one-line forms:

```
groupmems -g qa -a alice        # add alice to qa
groupmems -g qa -d bob          # remove bob from qa
groupmems -g qa -l              # list qa's members
groupmems -g qa -p              # purge: empty qa's member list
```

## How It Works

### Two authorization modes

**Root mode.** Root may target any group with `-g GROUP` and combine it with exactly one operation (`-a`, `-d`, `-l`, or `-p`). This is the mode you use in scripts.

**Group-admin (namesake) mode.** A non-root user, by design, may administer only the group bearing their own username — their "namesake" group. The intent: in a system where every user owns a personal primary group, that user can decide who else joins it, without sudo. Whether this mode is usable depends on setup (below): the binary must be able to write `/etc/gshadow` on the user's behalf, which stock Debian permissions do not allow.

```
as user 'alice' (primary group 'alice'):
    groupmems -a bob          -->  adds bob to group alice
    groupmems -g qa -a bob    -->  refused (not alice's namesake group)
as root:
    groupmems -g alice -a bob -->  same result, explicit targeting
```

### The SETUP recipe (per the man page)

To enable group-admin mode, the man page prescribes a setgid arrangement — the binary runs with group `shadow` so a member of that group can act through it:

```
$ groupadd -r shadow
$ chown root:shadow /usr/sbin/groupmems
$ chmod 2710 /usr/sbin/groupmems      # rwxr-s--x
```

Be aware of the tension before deploying it: on a stock Debian system `/etc/gshadow` is `root:shadow 0640` — the shadow group may *read* it, not *write* it — and membership in `shadow` also grants read access to `/etc/shadow`. The recipe is the man page's blueprint for a delegation-capable host, not something Debian turns on for you; audit both file modes and the shadow-group roster before relying on it. In practice most Debian admins answer the delegation question with `sudo` rules (limited to `/usr/sbin/groupmems -g <specific group>`) or `gpasswd -A` administrators instead, both of which keep `/etc/shadow` out of users' reach.

### PAM

On Debian's PAM-enabled build, a non-root `groupmems` run is mediated by PAM: the tool invokes the `groupmems` service (`/etc/pam.d/groupmems`, wired to the `common-account`/`common-auth`/`common-session` stacks) to authenticate the caller before touching the databases. Root invocations skip the prompt. This is the same pattern as `chsh`/`chfn`/`gpasswd`; if you disable that PAM file you change who can run groupmems non-interactively — audit it like any other sudo-shaped policy file.

### What gets written

Membership is stored in the member field of both files, kept in sync:

```
/etc/group    qa:x:2200:alice,bob
/etc/gshadow  qa:!::alice,bob
```

`-a` appends, `-d` removes, `-p` empties the field. With `MAX_MEMBERS_PER_GROUP` set in login.defs, long lists are split across repeated lines with the same name/GID — another reason to leave that variable at 0 (default) unless you serve NIS. Note what groupmems never touches: the group password (`!` stays `!`) and the administrators field — those belong to `gpasswd`.

### The four gshadow fields, and who owns each

```
  qa:!::alice,bob
  |  |  |   |
  |  |  |   +-- members          <- groupmems (-a/-d/-l/-p)
  |  |  +------ administrators   <- gpasswd -A (may change password/members)
  |  +--------- group password   <- gpasswd (-r removes, -R restricts)
  +------------ group name       <- groupadd/groupmod/groupdel
```

This division of labor is the cleanest mental model of the whole group-tool family: one field per tool, with groupmems owning exactly the fourth.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a USER` | Add USER to the target group's member list |
| `-d USER` | Remove USER from the member list |
| `-l` | List the group's members (members only — not administrators, not the password) |
| `-p` | Purge: remove all members from the group |
| `-g GROUP` | Target GROUP; required for root, and (by design) refused for non-root users unless GROUP is their namesake group |
| `-R DIR` | Chroot into DIR and edit its /etc files |
| `-P DIR` | Prefix mode: edit DIR's /etc files without chroot (cross-compile staging) |

One operation per invocation; the man page's synopsis is literally an alternation (`-a USER | -d USER | [-g GROUP] | -l | -p`), not a free combination.

## Usage Patterns

```bash
# Add a user to a group (root; the scripted equivalent of gpasswd -a)
groupmems -g docker -a alice
```

```bash
# Remove one member without disturbing the rest
groupmems -g docker -d mallory
```

```bash
# Read the member list in scripts (parse-free: comma-separated names)
members=$(groupmems -l -g docker)
```

```bash
# Idempotent membership add for provisioning
groupmems -l -g deploy | grep -qx "$u" || groupmems -g deploy -a "$u"
```

```bash
# Bulk-add a roster (root loop; one lock cycle per user is fine at this scale)
for u in $(cat /etc/roster/qa.txt); do groupmems -g qa -a "$u"; done
```

```bash
# Purge a group cleanly before re-adding a fresh roster (revoke-all pattern)
groupmems -g qa -p && for u in $(cat /etc/roster/qa-new.txt); do
  groupmems -g qa -a "$u"; done
```

```bash
# Difference from gpasswd in one line each: members vs password+admins
groupmems -g qa -a alice          # member list
gpasswd -A alice qa               # make alice an ADMINISTRATOR of qa
```

```bash
# Difference from usermod: per-group vs per-user view of the same data
groupmems -g docker -a bob        # one group, many users
usermod -aG docker bob            # one user, many groups
```

```bash
# Group-centric roster from a source-of-truth file, replacing drift
current=$(groupmems -l -g qa); desired=$(cat /etc/roster/qa.txt)
for u in $current; do echo "$desired" | grep -qw "$u" || groupmems -g qa -d "$u"; done
for u in $desired; do echo "$current" | grep -qw "$u" || groupmems -g qa -a "$u"; done
```

```bash
# Verify both files agree after scripted edits
grpck -r /etc/group /etc/gshadow && echo "group db consistent"
```

```bash
# Container image build: edit the staging tree's group db
groupmems -R /mnt/rootfs -g _svc -a _app
```

```bash
# Cross-compile staging (prefix mode)
groupmems -P /target -g build -a tester
```

```bash
# Namesake self-service, once the SETUP recipe is in place (as the user):
groupmems -a teammate             # teammate joins MY group
```

```bash
# Report: members per group from the tool itself (no gshadow read needed as root)
for g in docker deploy qa; do printf '%-8s %s\n' "$g:" "$(groupmems -g $g -l)"; done
```

```bash
# Mirror a group's membership onto another group (access-parity pattern)
for u in $(groupmems -l -g staging); do groupmems -g staging-readonly -a "$u"; done
```

## Nuances and Gotchas

- **Delegation is not on by default.** Stock Debian ships `/etc/gshadow` as `root:shadow 0640` — not writable by the shadow group — so the man-page SETUP recipe needs a matching permission change (and hands the shadow group read access to `/etc/shadow`). If you just chmod the binary on a whim, the self-service mode fails at write time. Decide deliberately: setgid recipe, sudo policy, or `gpasswd -A` administrators.
- **`-g` is root-shaped.** Non-root `-g qa ...` is refused unless `qa` is the invoking user's namesake group; scripts running under a service account must use sudo, not groupmems alone.
- **`-l` is not the whole story.** It prints the member list only. Group administrators (`gpasswd -A`, third gshadow field) and the group password state are invisible to groupmems; a "full" group report needs `getent group` + `getent gshadow`... via `sudo` — gshadow is not world-readable.
- **`-p` is the fire button.** Purge empties the member list with no confirmation and no undo. In provisioning, prefer `-d` per member or re-derive the list from source-of-truth files; reserve `-p` for explicit revoke-all runbooks.
- **Membership changes need re-login.** Like every membership tool, groupmems edits the database; existing sessions keep their old supplementary group list until they log in again. Revocation is database-immediate, access-immediate only for new sessions.
- **Namesake model is a distro culture choice.** Debian has `USERGROUPS_ENAB yes` (users get namesake primary groups) but administers membership centrally; the Red-Hat-style self-service assumption that groupmems is built around is rarely enabled end-to-end. Don't promise a user "you can manage your own group" until you've tested the whole chain, including PAM and file modes.
- **The binary may simply be absent.** Minimal and container images routinely drop groupmems; a playbook that calls it should check `command -v groupmems` or fall back to `gpasswd`/`usermod`. (On this writing container, for example, it is not installed, while groupadd/groupmod are.)
- **Split-group lines interact with edits.** With `MAX_MEMBERS_PER_GROUP` set, membership is spread over repeated lines; tools that parse `/etc/group` naively will miss members. Another reason the split feature stays off.
- **No long options.** Unlike most of the suite, groupmems historically exposes only single-letter options (`-a -d -g -l -p`); scripts written against `--add`-style spellings from other tools' habits will fail. Keep scripts on the short forms.
- **The namesake check is exact, not inherited.** Self-service compares the target group name to the invoking *username*, not to their primary GID's name after renames. If accounts and groups have drifted out of naming sync (renamed user, reused group), the delegation either misses or hits unexpectedly — audit the pairing before enabling the recipe.
- **-a does not validate that the user exists... until it does.** Member names are stored as strings; shadow tools warn about nonexistent members during `grpck` runs rather than at write time on every release. Prefer pre-checking `getent passwd "$u"` in scripts so typos do not become permanent ghost members.

## Exit Status

The man page for groupmems documents no exit-status table — unusual for the suite. Expect `0` on success and nonzero on failure; by analogy with its siblings, `1` (invalid command syntax), `6` (group doesn't exist, via `-g`), and `10` (can't update group file, including the `cannot lock /etc/gshadow` lock-failure case) are the plausible values, but verify against your release before scripting around specific codes. Check success by effect, not by decoding the number:

```bash
groupmems -g qa -a alice && getent group qa | grep -q "alice" || echo "add failed"
```

## Related Commands

- [`gpasswd`](./gpasswd.md) — the other membership tool: group passwords and the administrators field.
- [`usermod`](./usermod.md) — the per-user view of membership (`-aG`), the most common Debian idiom.
- [`groupadd`](./groupadd.md) / [`groupdel`](./groupdel.md) — create and remove the group object groupmems edits.
- [`groupmod`](./groupmod.md) — rename/re-GID; recent shadow also gained `-U` member editing here.
- [`grpck`](./grpck.md) — verifies the two files groupmems keeps in sync.
- [`useradd`](./useradd.md) — creates the namesake group that the self-service mode assumes.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together.
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: When would you reach for groupmems instead of usermod -aG?

Orientation: `usermod -aG` answers "which groups should THIS user be in?" — you enumerate the user's groups and must re-supply all of them, since the list replaces. `groupmems -g GROUP -a USER` answers "who should be in THIS group?" — one group, incremental, no need to know the user's other memberships. For roster-driven workflows (a team file, a CI group, a docker-access list) the group-centric edit is the natural primitive; for "grant this new hire access" the user-centric one is. Under the hood both edit the same two files.

### Q: The man page says groupmems lets users administer their own groups without root. How is that possible on Linux?

Through a setgid arrangement the SETUP section prescribes: the binary is mode 2710, owned `root:shadow`, so a member of the shadow group executes it with an effective group of `shadow`, letting the tool act on the group databases on the user's behalf — while the tool's own logic restricts a non-root caller to their namesake group. The catch is file permissions and blast radius: shadow-group membership also grants read access to `/etc/shadow` (both files are `root:shadow`-owned, 0640), and stock Debian gshadow is not group-writable. So the delegation only works if the admin has deliberately arranged the modes, which is why most Debian sites use `sudo` or `gpasswd -A` delegation instead.

### Q: A script did `groupmems -g qa -p` to "reset" the group. What are the immediate and delayed effects?

Immediate: the member list of `qa` is emptied in both `/etc/group` and `/etc/gshadow` under the locks — every former member's database membership is gone. Delayed: sessions already logged in keep their old supplementary group list until they re-login, so file access through the group persists for live sessions; and anything that assumed membership (sudoers `%qa` rules, CI runners) now fails for new sessions. The one-line lesson: `-p` is a database operation, not an access-control cutoff — pair it with session termination if revocation must be timely.

### Q: What does groupmems deliberately NOT manage about a group?

Two fields: the group's encrypted password (the `!`/hash in gshadow's second field, owned by `gpasswd`) and the administrators list (third gshadow field, also `gpasswd -A`). It also never touches the GID or the group's existence — that is `groupadd`/`groupmod`/`groupdel` territory. The suite's split is clean: groupmems is the member list only. Interviewers like this question because it maps the four gshadow fields to the tools that own them.

### Q: How would you verify that a fleet of scripted groupmems edits left the databases healthy?

Run `grpck -r /etc/group /etc/gshadow` (read-only) and require exit 0, plus consistency checks: every name in `/etc/group`'s member field should also appear in the matching gshadow member field and vice versa, every member should be a real account (`getent passwd`), and no name should appear twice. The grpck warning family covers exactly these — unmatched entries, nonexistent users, group-password-field drift — which is why it, not a hand-rolled grep, is the audit primitive.

### Q: Design question: would you enable the setgid self-service mode on a multi-user server, and why?

Usually no, and the reasoning is the interesting part. The benefit is narrow — users can share their personal group — while the costs are structural: members of the shadow group gain read access to `/etc/shadow` (offline cracking target for every hash on the box), the write-path depends on hand-tuned file modes that packages and audits may "fix" back, and PAM plus binary permissions become a custom security configuration to defend. The same need is met with less privilege by `gpasswd -A alice qa` (a named administrator, mediated by prompts and the existing PAM stack) or by a narrowly scoped sudo rule. A strong answer acknowledges the one legitimate fit: workstations or lab machines where the namesake-group culture is already the norm and shadow access is an accepted local risk.

### Q: How do groupmems, gpasswd, and usermod divide responsibility, and why does it matter operationally?

groupmems owns the member list of one group; gpasswd owns the group password and the administrator list (and can also add/remove members, interactively or via `-M`); usermod owns one user's complete group attachment list. Operationally the split matters for automation scope and audit: a roster pipeline wants the group-centric primitive (groupmems/gpasswd -M) because it converges on a desired list; a per-employee provisioning pipeline wants usermod because the change record is "this user". Mixing them without a source of truth produces silent conflicts — both write the same two files, and the last writer wins.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/groupmems.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
