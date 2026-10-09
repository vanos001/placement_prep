# grpconv — enable shadowed groups (move group passwords into /etc/gshadow)

## Overview

`grpconv` is one of the shadow suite's four one-shot converters (`pwconv`, `pwunconv`, `grpconv`, `grpunconv`, which share a man page): it creates `/etc/gshadow` from `/etc/group` plus any pre-existing `/etc/gshadow`, moving group password material out of the world-readable group file and replacing it with the `x` placeholder. It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/grpconv`. On Debian it has effectively already run — `/etc/gshadow` exists and `groupadd` writes both files — so modern usage is repair and assurance: after a restore from a non-shadow backup, after hand-editing, on minimal images where someone deleted gshadow, or before you trust a freshly debootstrapped tree.

It is often confused with `pwconv` (same algorithm, user side: `/etc/passwd`+`/etc/shadow`), with `grpunconv` (the inverse: fold gshadow back into group and delete it), and with a security hardening step in general — the real security property is narrower: it removes password fields from a world-readable file. Group *membership* was never secret, and group *passwords* are almost always the locked `!` anyway.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/grpconv |
| First appeared | shadow suite (Julianne F. Haugh, 1988+) — the "shadow" in the suite's name is this operation |
| Standards | Not POSIX. No operands, no login.defs keys of its own (MAX_MEMBERS_PER_GROUP aside) |

## Synopsis

```
grpconv [options]
```

Takes no group name, no file arguments — it always operates on the system's `/etc/group` and `/etc/gshadow` (or the `-R` root's). Common forms:

```
grpconv                    # the whole job
grpck -r && grpconv        # the documented safe pipeline
grpconv -R /mnt/rootfs     # convert an image's tree, not the running system
```

## How It Works

### The four-step algorithm

The man page describes the shared conv algorithm; for `grpconv` it is:

```
1. entries in /etc/gshadow with no matching /etc/group   -> removed
   (shadow-only entries are orphans, not data)
2. /etc/group entries whose password field is NOT 'x':
     - ensure a matching /etc/gshadow entry exists (added if missing)
     - the real password is carried into gshadow's password field
3. /etc/group entries with no gshadow entry at all:
     - a new gshadow entry is added (locked '!' password)
4. every /etc/group password field is replaced with 'x'
```

Before/after on one entry carrying a real group password:

```
BEFORE                                  AFTER
/etc/group                              /etc/group
consultants:$6$hash...:1500:sam         consultants:x:1500:sam

(/etc/gshadow absent)                   /etc/gshadow    (created, 0640 root:shadow)
                                        consultants:$6$hash...::sam
                                                      ^ password now root-only
```

The place where the conversion actually matters is file permissions: `/etc/group` is 0644 (`root:root`) on Debian — every local user can read whatever sits in that second field — while `/etc/gshadow` is `root:shadow` 0640, readable only by root and the shadow group. A group password hash readable by all users is a small offline-cracking target (small because there is usually nothing to crack — see below); grpconv closes it.

### Why 'x'

`x` is a convention, not encryption: it tells every reader of `/etc/group` — NSS, `getent`, the shadow tools themselves — "the meaningful password state for this entry is in the shadowed file". This is why the suite's editors always write `x` there once gshadow exists, and why `grpck` warns when the two files disagree. The reverse convention is what makes `grpunconv` possible: fold the real passwords back in, delete gshadow, and the `x` placeholders are replaced by actual (now world-readable) values.

### Idempotence — the quiet superpower

Run it twice and the second run is a no-op: every group entry already has `x`, so step 2 and 4 find nothing to do, and every gshadow entry already has its twin. That property makes `grpconv` safe to put in provisioning and image-build scripts unconditionally — "ensure shadow groups" becomes one line with no existence checks. It is also *healing*, not just initial conversion: if a hand edit or a restore leaves a password sitting in `/etc/group`, the next grpconv sweeps it into gshadow. (For structural damage — duplicate names, wrong field counts — run `grpck` first; the converter's man page warns it can "loop forever or fail in other strange ways" on corrupted input.)

### Debian context

A stock Debian system is already converted: `/etc/gshadow` exists (mode `0640 root:shadow`), `groupadd`/`gpasswd` maintain both files, and the `shadow` group's only special member privilege is reading the shadowed files. So on Debian, grpconv in practice runs (a) never, (b) in image builds, or (c) after restores/hand-edits. The tool matters most conceptually — it is the answer to "what does shadow *mean* in the shadow suite".

### One algorithm, four tools

The shared man page covers pwconv/pwunconv/grpconv/grpunconv; the group pair differs from the user pair only in which files and which extra fields are involved:

```
tool          direction         main file      shadow file    what moves
pwconv        enable            /etc/passwd    /etc/shadow    password + aging
pwunconv      disable           /etc/passwd    /etc/shadow    password (aging lost)
grpconv       enable            /etc/group     /etc/gshadow   password (+ twin entries)
grpunconv     disable           /etc/group     /etc/gshadow   password (admins dropped)
```

Symmetric pairs, opposite data loss: converting *on* loses nothing, converting *off* loses what the main file cannot represent (aging for users, administrators for groups). That asymmetry is why "disable" tools exist mostly for legacy compatibility and image surgery, while "enable" tools double as healing passes.

### The locks, briefly

Like every writer in the suite, grpconv takes the group/gshadow locks (and the passwd pair) for the duration. The practical bit for scripts: it fails fast if it cannot create the lock files, so a read-only or non-root context produces `grpconv: Permission denied.` followed by `grpconv: cannot lock /etc/group; try again later.` — the second line is the misleading one, since no amount of waiting fixes a permission problem.

### Why the man page warns about "loop forever"

The converter's BUGS section is unusually candid: errors in the group files "may cause these programs to loop forever or fail in other strange ways." The reason is structural: the conversion is a join between two files keyed by name, and a *duplicated* group name makes the join ambiguous — the converter may match, mismatch, or revisit the same entries repeatedly. This is why the only sanctioned pipeline is check → convert, and why a converter that misbehaved is a reason to suspect duplicates before anything else: `getent group | cut -d: -f1 | sort | uniq -d` answers that in one line.

## Options That Matter

| Option | Effect |
| --- | --- |
| *(none)* | Convert `/etc/group` + `/etc/gshadow` in place (the only mode) |
| `-R DIR` | Chroot into DIR and convert that tree's files (image building) |
| `-h` | Help |

That is the entire option surface — no file operands, no dry-run, no verbose, no prefix mode. Consequence: rehearse on copies of the files (or a scratch chroot), not on production, and treat a live run as a write you should have snapshotted.

## Usage Patterns

```bash
# Ensure shadow groups after building a minimal rootfs by hand
grpconv -R /mnt/rootfs
```

```bash
# The documented safe pipeline before any conversion
pwck -r && grpck -r && grpconv
```

```bash
# Heal a hand-edit that put a password hash back into /etc/group
grep '^consultants:' /etc/group        # shows the hash - world-readable
grpconv && grep '^consultants:' /etc/group   # now shows x
```

```bash
# Idempotence check: second run must change nothing
cp -a /etc/group /tmp/g.before && cp -a /etc/gshadow /tmp/gs.before
grpconv && diff /tmp/g.before /etc/group && diff /tmp/gs.before /etc/gshadow
```

```bash
# Restore-from-backup triage: backup predates shadow groups
cp /backup/etc/group /etc/group && grpconv   # regenerates a sane gshadow
```

```bash
# Image build pipeline: users+groups, then normalize both shadow halves
useradd -R /mnt/rootfs -r _svc ; grpconv -R /mnt/rootfs ; pwconv -R /mnt/rootfs
```

```bash
# Verify the security property you actually wanted
ls -l /etc/group /etc/gshadow     # 0644 root:root vs 0640 root:shadow
sudo awk -F: '$2 != "x" && $2 != "" {print FILENAME": "$1}' /etc/group
```

```bash
# Confirm every group got its twin after conversion
grpck -r && echo "group and gshadow agree"
```

```bash
# Scripted "already done?" test for provisioning
[ -f /etc/gshadow ] && grpconv   # harmless either way; file presence optional
```

```bash
# Rehearse on copies, never on production (the tool has no dry-run)
mkdir -p /tmp/lab/etc && cp /etc/group /tmp/lab/etc/
sudo grpconv -R /tmp/lab         # -R chroot form works on a copy tree as root
```

```bash
# After conversion, prove the group db is structurally sound (twin entries)
grpck -r && sudo getent gshadow | awk -F: '{print $1, $2}' | head
```

```bash
# Pre-conversion duplicate check (the 'loop forever' trigger)
getent group | cut -d: -f1 | sort | uniq -d    # empty output = safe to convert
```

```bash
# Snapshot both files as a unit, convert, show the exact delta
sudo cp -a /etc/group /etc/gshadow /tmp/convbak/
sudo grpconv && sudo diff /tmp/convbak/group /etc/group
```

```bash
# In a Dockerfile / cloud-init: unconditional, because idempotent
RUN grpconv
```

## Nuances and Gotchas

- **No backup, no dry-run, no undo.** grpconv rewrites two live files under lock and keeps no `.bak`. If you care, `cp -a /etc/group{,.convbak}` first — cheap insurance before any tool that rewrites your account database.
- **It silently deletes gshadow orphans.** Step 1 removes gshadow entries without group twins; if a bad merge left *only* gshadow holding data you wanted (administrators lists, membership), that data is gone. Run `grpck -r` and eyeball the gshadow file before converting.
- **Root required — and lock failures look like corruption.** A non-root run fails to create the lock files: `grpconv: Permission denied.` then `grpconv: cannot lock /etc/group; try again later.` (observed exit 5 on a recent build). The "try again later" wording is misleading — for non-root it is a permanent permission failure, not contention.
- **Group passwords are nearly always `!` — so the headline feature is rarely exercised.** Fresh groups are locked; `newgrp` password joins are a museum feature. The conversion's *real* routine value is creating missing gshadow entries and enforcing the `x` convention.
- **`x` is a placeholder, not a feature of the hash.** Don't "fix" an `x` back to a hash in `/etc/group` because a tool "couldn't see the password" — the password state is in gshadow by design, and putting it back re-opens the world-readable hole.
- **`/etc/gshadow` itself gets created with restrictive modes, but verify.** The point of the tool is the permission boundary; on unusual filesystems or overlay containers, check the resulting `ls -l /etc/gshadow` rather than assuming 0640 root:shadow.
- **NIS-era split groups apply here too.** With `MAX_MEMBERS_PER_GROUP` set, membership spans repeated lines; conversion and parsing tools that don't understand the split will miscount members.
- **It pairs with pwconv, not substitutes.** Shadow *groups* say nothing about shadow *passwords*; a full "shadowed system" check is `pwconv` + `grpconv` (and `pwck -r && grpck -r` before either).
- **The `!` lock survives conversion.** Group passwords move verbatim; a locked group stays locked. Nothing in the conversion unlocks or sets passwords — that remains gpasswd's job.
- **Converting inside containers/images needs the -R form, not -P.** grpconv has no prefix mode; for a staging tree either chroot (-R, needs root) or copy the files into a scratch tree you chroot to. This asymmetry with groupadd/groupmod (which have -P) catches script authors copying option lists between tools.
- **Empty password fields convert too.** A group whose `/etc/group` password field is empty (some ancient or hand-built entries) is treated as a non-`x` field: gshadow gets a (locked) entry and the field is normalized. That is the desired outcome — but it means "conversion changed N lines" is normal, not a sign of trouble.
- **Run it once per change window, not in loops.** Idempotent does not mean free: each run takes the full shadow lock set and rewrites both files. In provisioning, one unconditional call at the start of the group-management step is the pattern; calling it inside per-group loops just serializes your own tooling against itself.

## Exit Status

The shared converter man page documents no exit-status table. Grounded observations on a recent build:

| Code | When |
| --- | --- |
| 0 | conversion completed (including the no-op idempotent case) |
| 5 | observed on failure to lock the files (lock files not creatable — non-root, read-only `/etc`) |

Treat any nonzero as "nothing was converted" and diagnose via stderr (`Permission denied` vs `try again later` distinguishes privilege from contention). Do not build retry loops on the lock failure: retrying suits a busy lock, not a missing privilege.

## Related Commands

- [`grpunconv`](./grpunconv.md) — the inverse: fold gshadow back into group and remove it.
- [`grpck`](./grpck.md) — the pre-flight the converter's man page demands; also detects the drift grpconv fixes.
- [`gpasswd`](./gpasswd.md) — what writes real group passwords into gshadow after conversion.
- [`groupadd`](./groupadd.md) — already writes twin entries on a converted system.
- [`groupmod`](./groupmod.md) — its password edit (-p) targets the gshadow field once conversion is in place.
- [`usermod`](./usermod.md) — the user-side counterpart machinery; pwconv/pwunconv are its converters.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together (pwconv and the user-side pair included).
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: What problem does grpconv solve, exactly, and what does it NOT solve?

It solves password-field exposure: group password hashes sit in `/etc/group`, which is world-readable (0644), so grpconv moves them into `/etc/gshadow` (0640 root:shadow) and leaves the `x` placeholder behind; it also creates missing gshadow entries and removes orphans, making the two files structurally consistent. It does not solve: weak passwords, membership sprawl, ghost members (grpck's domain), or anything about user passwords (pwconv's domain). And in practice on Debian the password-exposure part is nearly moot because group passwords are almost always the locked `!`.

### Q: Is it safe to run grpconv twice? Why does that matter for automation?

Yes — the algorithm is idempotent: on a converted system, every group password is already `x`, so steps 2 and 4 find nothing to do, and every gshadow entry already has its twin, so step 3 adds nothing. That matters because "ensure shadow groups" becomes a single unconditional line in provisioning scripts and image builds with no existence checks, no `if [ ! -f /etc/gshadow ]` guard, and no state to track. The one caveat is step 1's orphan deletion — if gshadow uniquely held data after a bad merge, idempotence does not protect it; grpck first.

### Q: Someone hand-edited /etc/group and put a real hash in the password field. Walk through the exposure and the fix.

Exposure: `/etc/group` is mode 0644 root:root, so every local user can read the hash and take it offline for cracking; the group password it protects gates `newgrp` joins — probably low value, but it is a needless leak. Also, the two files now disagree, so `grpck` flags the drift. Fix: `grpconv`, which carries the hash into gshadow's password field and normalizes `/etc/group` back to `x`; verify with `grpck -r` (exit 0) and `getent gshadow consultants` (hash present, gshadow-only). The deeper lesson: gshadow is the single source of truth for group password state, and hand edits should never reassign that truth to the readable file.

### Q: What does the 'x' in /etc/group's second field actually mean, and where else does the convention appear?

It is the standard placeholder for "real credential state lives in the shadowed twin file": an instruction to NSS and the shadow tools to consult `/etc/gshadow` (or for users, `/etc/shadow`) instead of trusting this field. The same convention holds `x` in `/etc/passwd`'s password field once `pwconv` has run. Variants: an empty field means no password semantics for groups; `*` or `!` (in the shadow files) mean locked. A hash appearing in the main file after conversion is drift, and is precisely what grpck's password-field warning and grpconv's rewrite exist to repair.

### Q: When would you deliberately run grpunconv instead — and what would convince you not to?

Deliberately: legacy software that cannot parse the four-field gshadow model or an NIS master that must serve a single merged map; forensic simplification of an image; a system being handed to tooling that rewrites `/etc/group` directly. What should convince you not to: the security inversion — group passwords (rare but real) return to a world-readable file, and the administrators field of gshadow has no representation in `/etc/group` at all, so delegation data is lost; plus the fact that everything modern (useradd/usermod/gpasswd/groupmems) assumes gshadow exists. Unless a concrete, named consumer is broken, conversion backward is a regression.

### Q: You inherited a server where `/etc/gshadow` is missing but `/etc/group` has only `x` in password fields. What state is this, and what does grpconv do?

This is the broken half-converted state: someone deleted gshadow (or restored group from a shadowed host without its twin), leaving placeholders with nothing behind them — `newgrp`/`gpasswd` semantics are undefined-ish and `grpck` will report unmatched-file complaints. grpconv rebuilds cleanly: since no group entry carries a real password (all `x`), step 2 has nothing to move, but step 3 adds a fresh locked (`!`) gshadow entry for every group. The system ends up in the standard Debian posture. The pre-step is still `grpck -r`: if the group file itself has duplicates or malformed lines, the converter may misbehave — fix those with grpck/groupmod first.

### Q: Where does grpconv sit in a disaster-recovery runbook for /etc, and why there?

After any restore that touches `/etc/group` and before any verification that group semantics work: restore brings back the file pair as it was at backup time, which may predate shadow groups, carry hand edits, or lack the twin entirely. The runbook order is: restore → `grpck -r` (structural triage, fix fatal entries) → `grpconv` (normalize passwords into gshadow, add missing twins) → `grpck -r` again expecting exit 0 → only then re-enable logins/services. Placing grpconv before the integrity gates wastes the gates; placing it after them without a second gate trusts the converter on a file you have not validated.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/grpconv.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
