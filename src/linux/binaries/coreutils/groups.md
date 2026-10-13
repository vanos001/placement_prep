# groups — print group memberships of a user

## Overview

`groups` prints the groups a user belongs to. With no argument it reports
the *current process's* group set (primary group plus supplementary
groups); with a username argument it consults the user database and reports
that user's memberships. Output is a simple list of group names:

```bash
$ groups
z adm dialout sudo
$ groups www-data
www-data : www-data
```

Debian ships it in `coreutils` at `/usr/bin/groups` (historically
`/usr/bin/groups`, once `/usr/bin` vs `/bin` split across releases). It is
effectively a friendly formatter for the same data [`id`](./id.md) reports —
modern `id -Gn` prints the same names — and that redundancy is itself
exam material: which of the two reflects the *process* and which the
*database*, and why they can disagree.

You reach for `groups` in interactive sessions and quick checks ("am I in
the docker group?"); `id` is preferred in scripts because its exit status
and field selection (`-u`, `-g`, `-G`) are richer. Group membership
questions connect directly to permission checks — the group bits of
`ls -l`, `newgrp`, sudo rules — covered in the permissions and users-groups
pages of the admin part.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/groups` on modern Debian/Ubuntu |
| First appeared / lineage | BSD lineage; on older Debian releases shipped as a shell script wrapping `id -Gn`, now a compiled coreutils binary |
| Standards | Not POSIX-standardized (POSIX expresses membership via `id`) |

## Synopsis

```
groups [USER]...
```

```bash
groups              # current process's groups: "primary : supp..."
groups alice        # alice's groups per the user database
groups alice bob    # one line per user, each prefixed "user : ..."
```

## How It Works

### No argument: the process view

With no USER, `groups` reads the calling process's credential structure —
the same `getgroups(2)` data every permission check uses — and prints the
primary group first, then supplementary groups:

```
 login/PAM
    │ setgid(primary) + setgroups(supplementary list)
    ▼
 process credentials ──── getgroups(2) ────► groups (no arg)
    │                                            │
    ▼                                            ▼
 every open() group-bit check             "z : z adm docker"
```

The supplementary list is snapshotted at login (or `newgrp`/`sg`), which
has a famous consequence covered in Nuances: **adding a user to a group in
`/etc/group` does not change any running session.**

### With an argument: the database view

With USER, `groups` parses `/etc/nsswitch.conf`'s group source (files,
LDAP, SSSD...) via NSS and prints that user's primary and supplementary
groups — a fresh query, not a process snapshot. This is how you audit what
a user *will have* at next login:

```bash
$ groups deploy
deploy : deploy docker
```

For multiple users, each line is prefixed with the username. An unknown
user produces a diagnostic on stderr and a nonzero exit — per-user, so
`groups alice nosuchuser bob` still prints the lines for alice and bob.

### groups vs id

| Question | `groups` | `id` |
| --- | --- | --- |
| Names of current groups | `groups` | `id -Gn` |
| Numeric IDs | not available | `id -G` |
| Effective vs real distinction | none (process set only) | `-r` selects real; default shows effective-if-different |
| Per-user database query | `groups USER` | `id USER` |
| Exit-status granularity | 0 / nonzero | 0 / nonzero |
| SELinux context | no | `id -Z` |

For the current user, `groups` and `id -Gn` print the same names in the
same order (primary first). The differences that matter: `id` can select
real-vs-effective and print numbers, and on SELinux systems `id` (without
`POSIXLY_CORRECT`) appends a `context=` field to default output — `groups`
never does.

### Output format details

```bash
$ groups
z : z adm sudo docker
```

- No argument: no username prefix; `primary : supp1 supp2 ...`.
- The colon appears only in the argument form. (GNU: with a USER argument
  the line starts `USER :`.)
- Names, not GIDs — resolving GIDs to names uses the same NSS source; a
  GID with no name entry prints as the number.

## Options That Matter

| Option | Effect |
| --- | --- |
| `--help` / `--version` | As usual |

That is the entire option surface — `groups` is one of the few coreutils
tools with no functional flags at all. Every variation is positional.

## Usage Patterns

```bash
# "Am I in the docker group?" — the everyday check
groups | tr ' ' '\n' | grep -qx docker && echo yes
```

```bash
# List my groups, one per line, readable
groups | tr ' ' '\n'
```

```bash
# Audit a new hire's group assignments before their first login
groups alice
```

```bash
# Compare intended vs current membership in a provisioning script
want="deploy docker"; have=$(groups alice | sed 's/^[^:]*: //')
for g in $want; do case " $have " in *" $g "*) ;; *) echo "missing: $g";; esac; done
```

```bash
# Equivalent spelling when you already use id elsewhere in the script
id -Gn
```

```bash
# Check a service account's groups before a permission triage
groups www-data
```

```bash
# Verify newgrp picked up a freshly added supplementary group
newgrp docker <<<'groups'
```

```bash
# Count how many groups the invoking user carries (NGROUPS_MAX relevance)
groups | wc -w
```

## Nuances and Gotchas

- **Running sessions do not pick up `/etc/group` edits.** `getgroups(2)`
  returns the login-time snapshot; `usermod -aG docker $USER` only helps
  after a fresh login (or `newgrp`, which spawns a shell with the updated
  set for that group). "I added myself to the group and docker still
  fails" is a daily support ticket.
- **`groups` (no arg) vs `groups $USER` can disagree** — the former is the
  process snapshot, the latter a fresh database query. In scripts, be
  explicit about which question you are asking; for "what does this
  process have access to", the no-arg form is the truth.
- **Argument form drops the process context entirely:** `groups alice` as
  root tells you about alice's *database* entries, never about alice's
  running session.
- **Primary group placement:** the primary group is always listed first;
  scripts assuming alphabetical order break. If you need "the primary
  group", that is `id -gn`, not "first word of groups" (they coincide only
  because of the ordering guarantee).
- **Large group sets:** Linux caps supplementary groups (NGROUPS_MAX,
  default 65536 on modern kernels, historically 16). Environments syncing
  hundreds of LDAP groups can silently truncate memberships — `groups`
  shows the truncated reality.
- **Not POSIX:** portable scripts use `id -Gn`. busybox provides both.
  macOS's `groups` accepts the same shape (BSD lineage is where it came
  from).
- **Names vs numbers:** on systems with orphaned GIDs (no /etc/group
  entry), output shows raw numbers — a data-hygiene signal, not a bug.
- **`groups user` exit status reflects only user lookup**; it says nothing
  about whether the user *is currently* in those groups (see first bullet).

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | All requested information printed |
| nonzero | At least one USER could not be found (diagnostic on stderr; valid users still print) |

## Related Commands

- [`id`](./id.md) — the full-featured sibling: numeric IDs, `-Gn` name form, real-vs-effective, SELinux context
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- `newgrp`/`sg` — spawn a shell with a different active group (shadow suite; outside this collection)

## Interview Questions

### Q: A user was added to the `docker` group but `groups` (no argument) still doesn't show it. Why, and what are the two ways to fix the session?

Because argument-less `groups` reads the process's credentials, snapshotted
by PAM at login; the `/etc/group` edit does not propagate into running
sessions. Fixes: (1) log out and back in (or re-ssh) so PAM calls
`setgroups` afresh; (2) `newgrp docker` to start a shell whose group set
is rebuilt including docker (works for testing, awkward as a permanent
state). Meanwhile `groups $USER` already shows the new membership because
it queries the database live — the discrepancy is diagnostic gold.

### Q: What exactly does `groups` report with no argument, and where does that data come from?

The calling process's primary GID plus its supplementary group list, via
`getgroups(2)` (with the primary resolved to a name via NSS). That set was
installed when the session was created: login/PAM mapped the account's
primary group and supplementary list from the user database and applied
them to the process. It is the *authoritative* answer to "what group
permissions does this process actually have right now", which is precisely
why it can lag behind database edits.

### Q: Why is `id` preferred over `groups` in scripts, when `id -Gn` prints the same names?

`id` offers field selection (`-u`, `-g`, `-G`), numeric-vs-name output
(`-n`), real-vs-effective selection (`-r`), SELinux context (`-Z`), and
the same lookup-by-name behavior — so one binary covers membership, UID,
GID, and context questions with machine-parsable single-value outputs.
`groups` prints one formatted string whose shape differs between the
no-arg and argument forms (username prefix and colon appear only in the
latter), which makes parsing needlessly conditional. For interactive
"which groups am I in", either is fine; for automation, `id`.

### Q: What does the output `groups alice bob` look like, and what happens with a nonexistent user in the list?

One line per user, each prefixed with the username and a colon —
`alice : alice sudo` — and a nonexistent user yields a stderr diagnostic
plus a nonzero exit while the valid users still print. The "partial
success" exit semantics matter in loops: a provisioning script that checks
the exit status of a multi-user `groups` call must decide whether partial
information counts as success (GNU continues after the bad name).

### Q: How do supplementary group limits affect real environments, and how would you detect truncation?

Linux limits supplementary groups per process (NGROUPS_MAX; 65536 on
current kernels, 16 on ancient ones). Environments that sync hundreds of
LDAP/AD groups into /etc/group can hit configured limits in NSS or in
remote-auth daemons, after which `setgroups` stores only the first N —
permission checks then silently fail for the tail groups. Detection:
compare `groups $USER` (database view) against the *running session's*
`groups` (process view) after a fresh login; a shorter process list with
no error is the truncation signature. The fix is on the directory side:
trim memberships or raise the limit (`/proc/sys/kernel/...`-era knobs and
SSSD options).

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/groups.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
