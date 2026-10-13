# grpck — verify integrity of the group files

## Overview

`grpck` is `fsck` for the group database: it checks that every entry in `/etc/group` and `/etc/gshadow` is well-formed, internally valid, and consistent with its twin file, and — interactively — offers to delete entries that cannot be repaired any other way. It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/grpck`. Its sibling `pwck` does the same for `/etc/passwd` and `/etc/shadow`; the pair exists because the suite's write path assumes sane input, and a corrupted group file can wedge every other tool in it.

`grpck` is often confused with a "repair" command — it is primarily a *verifier* with a narrow, prompted delete capability — and with plain greps over `/etc/group`, which catch none of the cross-file conditions (an entry present in `/etc/group` but missing from `/etc/gshadow`, members that are not real users, group password fields that forgot to become `x`). It is also the tool the man pages of `grpconv`/`grpunconv` tell you to run *first*: those converters are documented to "loop forever or fail in other strange ways" on corrupted files.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/grpck |
| First appeared | System V lineage; shadow suite (Julianne F. Haugh, 1988+), now maintained by shadow-maint |
| Standards | Not POSIX. Interactive by design; exit taxonomy shared with pwck |

## Synopsis

```
grpck [options] [group [gshadow]]
```

Common one-line forms:

```
grpck -r                          # read-only audit of /etc/group + /etc/gshadow
grpck                             # interactive: prompts to delete bad entries
grpck -s                          # sort both files by GID
grpck /mnt/rootfs/etc/group /mnt/rootfs/etc/gshadow   # alternate files
```

## How It Works

### The check list

Per the man page, each entry must have:

```
1. the correct number of fields            (4 in /etc/group, 4 in /etc/gshadow)
2. a unique and valid group name
3. a valid group identifier                (/etc/group only)
4. a valid list of members and administrators
5. a corresponding entry in the twin file  (group <-> gshadow)
```

The severity split is the design's core:

```
FATAL (entry unusable):
  wrong number of fields   -> prompted: delete the line? (decline = stop
                              checking that entry entirely)
  duplicate group name     -> prompted: delete? (remaining checks continue)

WARNINGS (entry salvageable, fix with groupmod/grpconv):
  nonexistent member or administrator names
  missing twin entry in the other file
  group password field not 'x' while a gshadow entry exists
  (suppressed by -S, the "controversial" class)
```

The man page's justification for the delete prompts is a sharp operational fact: **the commands that normally operate on the group files cannot alter corrupted or duplicated entries** — their parsers assume uniqueness and well-formedness, so the very state you need to fix is the state their write path cannot address. grpck's simple line-oriented reader is the one tool that can.

### Reading a run

Real transcript on a deliberately corrupted pair (field-count break, duplicate name, ghost members, missing gshadow entries), all prompts answered `no`:

```
$ grpck -r etc/badgroup etc/badgshadow
invalid group file entry
delete line 'badline:x'? No
duplicate group entry
delete line 'users:x:100:alice,bob'? No
group users: no user alice
delete member 'alice'? No
group users: no user bob
delete member 'bob'? No
no matching group file entry in etc/badgshadow
add group 'users' in etc/badgshadow? No
duplicate group entry
delete line 'users:x:101:'? No
no matching group file entry in etc/badgshadow
add group 'users' in etc/badgshadow? No
no matching group file entry in etc/badgshadow
add group 'testers' in etc/badgshadow? No
grpck: no changes
$ echo $?
2
```

And the password-drift warning — the exact condition `grpconv` fixes:

```
$ grpck -r /etc/group /etc/gshadow
group testers has an entry in /etc/gshadow, but its password field
in /etc/group is not set to 'x'
```

Read it like `fsck` output: each stanza is one defect class, the quoted line is what would be deleted or rewritten, and the exit code (2 = bad entries found) is what your monitoring keys on.

### Modes and files

Interactive mode prompts; `-r` answers `no` to every prompt automatically — an audit, never a fix. `-s` rewrites both files sorted by GID (a normalization, not a check). The two positional arguments let you point at *other* files — a chroot's or a staging tree's group db — without installing anything; in that mode non-root use works as long as you can read the files (note: plain `/etc/gshadow` is mode 0640 root:shadow, so the default run wants root).

### What it deliberately does not check

Keeping scope expectations straight is half the battle:

```
not grpck's business:
  - passwords' strength or aging        (that is the user side / chage)
  - whether members SHOULD be members   (policy, not integrity)
  - GID collisions across the range     (uniqueness is per-name; -o aliases are legal)
  - NSS-only groups                     (SSSD/LDAP entries never touch these files)
  - file ownership on disk              (find -nogroup is the tool for residue)
```

A clean `grpck -r` certifies exactly one thing: the two files are well-formed and mutually consistent. Everything above still needs its own check.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-r` | Read-only: report errors and warnings, answer every delete/fix prompt `no` |
| `-s` | Sort entries of both files by GID (rewrites the files; cannot be combined with `-r`) |
| `-S` | Silence the controversial warnings (notably group/gshadow member-list divergence) |
| `group gshadow` | Positional: operate on alternate files instead of `/etc/*` |
| `-R DIR` | Chroot into DIR and check its /etc files |

## Usage Patterns

```bash
# The audit gate: run before and after any scripted group surgery
grpck -r && echo OK || echo "group db unhealthy (exit $?)"
```

```bash
# Monitoring/cron check: read-only, exit-code driven, no prompts ever
grpck -r 2>&1 | logger -t grpck; [ $? -le 1 ] || systemctl start fix-groups.target
```

```bash
# Pre-flight for the converters (their man page demands it)
pwck -r && grpck -r && grpconv
```

```bash
# Interactive repair of a file too broken for groupmod to parse
grpck                                   # answer the delete prompts deliberately
```

```bash
# Normalize ordering after a messy merge (diff-friendly rewrite)
grpck -s && git diff /etc/group         # only ordering changed
```

```bash
# Check a container image's group db without starting it
grpck -r /mnt/rootfs/etc/group /mnt/rootfs/etc/gshadow
```

```bash
# CI: fail the build if a baked-in group db is corrupt
grpck -r rootfs/etc/group rootfs/etc/gshadow || exit 1
```

```bash
# Divergence triage: is the member list the same in both files?
grpck -r ; grpck -S -r   # messages only in the first run = the suppressed class
```

```bash
# Ghost-member sweep the way grpck's warning implies: names minus real users
comm -23 <(getent group | cut -d: -f4 | tr ',' '\n' | sort -u) \
         <(getent passwd | cut -d: -f1 | sort) | grep -v '^$'
```

```bash
# After repair, verify normal tools can parse everything again
getent group | awk -F: 'NF != 4 {print "bad:", $0}'
```

```bash
# Stand up a scratch pair and rehearse the repair (learn the prompts safely)
cp /etc/group /tmp/g; cp /etc/gshadow /tmp/gs && chmod 600 /tmp/gs
echo 'broken:x' >> /tmp/g; grpck /tmp/g /tmp/gs
```

## Nuances and Gotchas

- **Interactive by default is a cron hazard.** Plain `grpck` prompts on stdin; in a non-interactive context it either hangs (waiting on a closed terminal) or consumes your script's next lines as answers. Anything scheduled must pass `-r` (or redirect `</dev/null`, which makes every prompt fail closed).
- **`-r` answers no — it never fixes.** The read-only run reports and exits 2; a different tool (you, groupmod, grpconv, or an interactive grpck) does the fixing. There is no `-y`/auto-fix mode; the suite deliberately keeps a human in the delete path.
- **`-r` and `-s` are mutually exclusive.** Sorting is a write; read-only is a read. The man page states it, and the tool enforces it.
- **Exit 2 is the signal, not stderr.** "one or more bad group entries" — CI and monitoring should branch on it. 3/4/5 (open, lock, update failures) are environmental, not data, problems and deserve a different alert.
- **The warnings class is opinionated.** Member-list divergence between group and gshadow is a warning (and `-S`-able) because some setups intentionally keep them different; do not blanket-`-S` in scripts or you will also lose the nonexistent-member and twin-entry findings.
- **gshadow is not world-readable.** The default run reads `/etc/gshadow` (0640 root:shadow) — fine as root, "cannot open" as everyone else. Non-root audits must target their own readable copies (the positional-files mode) or run under sudo.
- **`-s` rewrites files — plan for drift.** Sorted output changes line order, so idempotence-checking tools and file-integrity monitors (AIDE, etckeeper) will flag the change. Sort once, deliberately, not in loops.
- **It checks the local files only.** NSS-visible groups (SSSD/LDAP) are not grpck's subject; a "clean" report says nothing about directory-service consistency, only that `/etc/group`+`/etc/gshadow` are coherent.
- **Pair it with pwck as one operation.** Half the conditions (a user in a group but absent from passwd) span both file pairs; the man pages of the converters run both before converting. One without the other is a half-audit.
- **Alternate files are not alternate worlds.** Checking `/mnt/rootfs/etc/group` against `/etc/passwd`-derived names still uses the *host's* user database for member validation; a staging tree with different accounts will produce ghost-member warnings that are artifacts of the check, not of the files.
- **`grpck` changes nothing unless you let it.** But answering a prompt wrongly deletes real data — the prompts look innocent (`delete line 'users:x:101:'?`) and the tool is line-exact. On production, the safe repair is: `-r` run to enumerate defects, fix warnings with groupmod/grpconv, and only take an interactive delete pass to a maintenance window with a backup of both files.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success — no problems found |
| 1 | invalid command syntax |
| 2 | one or more bad group entries found |
| 3 | can't open group files (missing, unreadable — e.g. gshadow as non-root) |
| 4 | can't lock group files (concurrent shadow tool, stale `.lock`) |
| 5 | can't update group files (write-back failure, e.g. after a `-s` sort) |

Codes 0/2 describe the data; 3/4/5 describe the environment. Only 2 means "fix your files".

## Related Commands

- [`grpconv`](./grpconv.md) — fixes the password-drift class grpck warns about (non-`x` fields); its man page demands a grpck pass first.
- [`grpunconv`](./grpunconv.md) — the reverse converter, equally documented to require clean input.
- [`groupmod`](./groupmod.md) — the man page's prescribed fixer for the warning-class defects.
- [`groupadd`](./groupadd.md) / [`groupdel`](./groupdel.md) — recreate or remove entries that grpck deleted.
- [`gpasswd`](./gpasswd.md) — legitimate source of member/administrator lists grpck then validates.
- [`usermod`](./usermod.md) — renames users; the other common source of ghost-member warnings.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together (including pwck, the passwd/shadow twin of this tool).
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: Which grpck findings are fatal and which are warnings, and why does the distinction matter operationally?

Fatal: wrong field count and duplicate group names — the entry (or a line) cannot be parsed or keyed, so grpck prompts to delete it, and declining a field-count error skips further checks on that entry. Warnings: nonexistent members/administrators, missing twin entries, password-field drift — the entry is parseable and can be repaired with groupmod/grpconv. Operationally: warnings can be auto-remediated in scripts (grpconv is literally the fix for the `x`-drift warning), while the fatal class requires the prompted delete path — the one write capability grpck has and normal tools don't.

### Q: Why do the man pages say ordinary group tools can't fix a corrupted group file, and what does that make grpck?

groupadd/groupmod/gpasswd read the database into structured records keyed by unique names before writing; a malformed or duplicated line breaks the assumptions of that path — it may refuse, mis-target, or (per the grpconv man page) even loop. grpck uses a deliberately dumber, line-oriented reader so it can address exactly the lines the smart tools choke on. That makes grpck the surgeon of last resort: verifier by default, interactive scalpel for deletion of unparseable/duplicated entries.

### Q: You need a nightly integrity check of the group db in a headless cron job. Write the shape of it.

`grpck -r` — read-only so every prompt is auto-answered `no` and nothing can hang on stdin — with output sent to the logger and the exit code driving the alert: 0 is healthy, 2 means data defects (open a ticket, name the lines from the output), 3/4/5 mean environmental trouble (permissions, stale locks) rather than bad data. The two classic mistakes to avoid: running bare `grpck` in cron (it prompts) and treating any nonzero as "data corrupted" (only 2 is).

### Q: What exactly does `grpck -s` do, and when would you use it on a live system?

It rewrites `/etc/group` and `/etc/gshadow` with entries ordered by GID — a normalization, not a validation (and it cannot be combined with `-r`). Use cases: after a merge or migration that left the files in chaotic order, to make `diff`s and review sane; or as a one-time hygiene pass. Cautions: it is a write (run the read-only check first), it churns file-integrity monitors, and it does nothing about content defects — sort order is not correctness.

### Q: A converter (grpconv) behaved erratically on a server. What is the documented relationship between the two tools?

The grpconv/grpunconv man page warns that errors in the group files "may cause these programs to loop forever or fail in other strange ways" and tells you to run grpck first. The converters do multi-pass rewrites (matching entries across two files, moving passwords, adding missing entries) — exactly the operations a duplicate or malformed entry corrupts. So the documented pipeline is `grpck -r` (or interactive repair) → then convert; skipping the check converts the corruption instead of the database.

### Q: grpck warns "group X has an entry in /etc/gshadow, but its password field in /etc/group is not set to 'x'". What happened and what fixes it?

Someone or something wrote a real password hash (or a non-`x` placeholder) into `/etc/group`'s password field while a gshadow entry for the group exists — usually hand-editing or a restore from a non-shadow system. The invariant is: with shadow groups enabled, the group file's password field is the `x` placeholder and the real state lives in gshadow (locked `!` or a hash). Fix: `grpconv` (which moves any real password into gshadow and normalizes the field to `x`) — after a `grpck` pass, per the converter's own man page.

### Q: Design a repair workflow for a group db with five defects of mixed severity. What order, and why?

First `grpck -r` to enumerate (exit 2 confirms defects; capture the stanzas). Second, backup both files (`cp -a` — the interactive path deletes lines irrecoverably). Third, fix warning-class defects with their purpose-built tools: groupmod/grpconv for drift, gpasswd/groupmems for membership. Fourth, only for entries still unparseable (field-count, duplicates), run interactive grpck in a maintenance window and answer its delete prompts line by line. Fifth, re-run `grpck -r` expecting exit 0 and re-verify that normal tools parse the files (`getent group | awk -F: 'NF != 4'`). The ordering rule: least-destructive, most-auditable fix first; the line-delete pass last and only when nothing else can address the entry.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/grpck.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
