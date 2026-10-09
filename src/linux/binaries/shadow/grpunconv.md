# grpunconv — disable shadowed groups (fold /etc/gshadow back into /etc/group)

## Overview

`grpunconv` is the reverse gear of the shadow suite's group conversion: it merges the password material from `/etc/gshadow` back into `/etc/group`, then removes `/etc/gshadow` entirely. It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/grpunconv`, sharing its man page with its three siblings (`pwconv`, `pwunconv`, `grpconv`). On a stock Debian system it has no routine job — gshadow is part of the platform — so its real habitats are legacy compatibility (an NIS master that must serve a single merged map, ancient tooling that cannot parse the shadowed model) and deliberate image surgery.

It is often confused with a "cleanup" tool (it is a *format downgrade* with permanent information loss) and with `pwunconv` (its user-side twin, which loses password aging the same way grpunconv loses group administrators). Interviewers like it because the obvious follow-up — "why would you ever do that?" — forces exactly the right answer: only when a concrete consumer cannot handle shadowed groups, and almost never on a modern Debian box.

Where `grpconv` is a healing pass (idempotent, lossless), `grpunconv` is the one tool in the group family that makes the system *less* capable than it found it: delegation data has no destination file, and password material returns to a world-readable path. Everything on this page follows from that single fact.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/grpunconv |
| First appeared | shadow suite (Julianne F. Haugh, 1988+) — the un-shadow half of the original design |
| Standards | Not POSIX. No operands; no login.defs keys of its own |

## Synopsis

```
grpunconv [options]
```

No group names, no file arguments — always the system's own pair (or the `-R` root's). There is no mode that names a subset of groups: the conversion is all-or-nothing, which is why scoping a downgrade to one machine (or one image) is done by *where* you run it, not by arguments:

```
grpunconv                     # merge gshadow into group, delete gshadow
grpck -r && grpunconv         # the documented safe order
grpconv                       # the way back (minus administrators, see below)
```

## How It Works

### The merge algorithm

The man page describes the un-conv pass (shared with `pwunconv`):

```
1. for every entry present in BOTH files:
     the /etc/group password field is updated from /etc/gshadow
     (a real hash replaces the 'x' placeholder; a locked '!' stays '!')
2. entries in /etc/group with no gshadow twin: left alone
3. /etc/gshadow is removed
```

Before/after on one entry:

```
BEFORE                                   AFTER
/etc/group                               /etc/group
consultants:x:1500:sam                   consultants:$6$hash...:1500:sam
                                         ^ world-readable again (0644 root:root)
/etc/gshadow
consultants:$6$hash...::sam              (file deleted)
             ^^ administrators field has nowhere to go: dropped
```

Two data movements deserve emphasis. First, the password: a *locked* group (`!`) un-converts harmlessly — `!` in a world-readable file gates nothing and cracks nothing — while a genuinely hashed group password becomes readable by every local user, which is the entire security inversion. Second, the fields that have no home in `/etc/group`'s four-column format: the **administrators** list (gpasswd `-A` delegation) simply ceases to exist. Members survive because the group file has a member field; administrators do not.

### What breaks afterward

The whole suite assumes the shadowed model once it exists. After grpunconv:

```
groupadd     still works, but writes single-file entries
gpasswd      group-password and -A administrator operations degrade
             (there is no administrators field to write to)
grpck        with no gshadow to check, half its check list is gone
grpconv      cleanly rebuilds gshadow — the way back (except admins)
newgrp       password-based joins now read the world-readable hash
```

The administrators loss is the quiet one: nothing errors, delegation just evaporates. If you use `gpasswd -A` at all, inventory it before un-converting:

```bash
sudo awk -F: '$3 != "" {print $1": admins="$3}' /etc/gshadow
```

Membership, by contrast, is preserved: gshadow's member field is reconciled into the group file's member field, so supplementary memberships survive the round trip. It is specifically the *administrators* (and any real password hashes' privacy) that do not.

### Requires clean input, like its sibling

The converter man page warns that errors in the group files can make the converters "loop forever or fail in other strange ways" — the merge is a name-keyed join, and duplicates make it ambiguous. The pipeline is therefore check → convert, then verify: `pwck`/`grpck` read-only before, `getent group` sanity after.

### A note on locks and timing

Like every writer in the suite, grpunconv takes the group/gshadow (and passwd/shadow) locks for the merge. It must not run concurrently with group-editing tools, and it must not run while a restore job is rewriting the same files — the merge reads both files and deletes one, so a mid-flight restore is exactly the race that produces the hybrid state described below. In runbooks it belongs in the same serialized step as its grpck pre-flight, not as a fire-and-forget cron entry.

### The state machine of a converted system

Group shadowing is a two-state design with the converters as the only transitions:

```
         grpconv (enable)
  UNSHADOWED  <---------------->  SHADOWED
  group 0644, hashes inside      group 0644, all 'x'
  no gshadow                     gshadow 0640 root:shadow
         grpunconv (disable)     hashes + admins + members

  transitions differ in information terms:
    enable:  loses nothing        (idempotent, doubles as healing)
    disable: loses administrators (and re-exposes any hashes)
```

Every other tool in the family lives *inside* the SHADOWED state — groupadd writes twin entries, gpasswd writes the shadow fields, groupmems edits shadow members, grpck checks the pair. grpunconv is the exit door, and the door only swings back partway.

## Options That Matter

| Option | Effect |
| --- | --- |
| *(none)* | Merge `/etc/gshadow` into `/etc/group`, then delete gshadow (the only mode) |
| `-R DIR` | Chroot into DIR and un-convert that tree's files (image surgery) |
| `-h` | Help |

The same minimal surface as `grpconv`: no operands, no dry-run, no backup, no prefix mode. That poverty of options is a design statement — there is no "safe" way to flatten a shadow database, only a snapshot-and-go one.

## Usage Patterns

```bash
# Pre-flight: enumerate what will be lost (administrators) before converting
sudo awk -F: '$3 != "" {print $1": "$3}' /etc/gshadow
```

```bash
# The documented safe pipeline (validate, then convert)
pwck -r && grpck -r && grpunconv
```

```bash
# State gate for provisioning: only flatten when intended (and log it)
test -f /etc/gshadow && { logger -t grpunconv "flattening group db"; grpunconv; }
```

```bash
# Snapshot both files first — the tool keeps no backups
sudo cp -a /etc/group /etc/gshadow /tmp/unconvbak/ && sudo grpunconv
```

```bash
# Verify the merge: every former gshadow password now lives in /etc/group
sudo paste -d: <(cut -d: -f1,2 /etc/group) <(sudo cut -d: -f1,2 /etc/gshadow 2>/dev/null)
```

```bash
# Image surgery: flatten a rootfs for a legacy consumer
grpunconv -R /mnt/rootfs
```

```bash
# Same, verified: the tree's group file now carries the merged fields
grpunconv -R /mnt/rootfs && awk -F: '{print $1, $2}' /mnt/rootfs/etc/group | head
```

```bash
# NIS master preparation: one merged map to export (legacy yeoman work)
grpunconv && cd /var/yp && make
```

```bash
# Undo path (minus administrators): re-enable shadow groups
grpconv && grpck -r && echo "shadow groups restored"
```

```bash
# Confirm the state change: gshadow gone, group world-readable again
ls -l /etc/group /etc/gshadow    # second line now absent
```

```bash
# Rehearse on a copied tree before touching a live one (root, in a chroot)
mkdir -p /tmp/lab/etc && cp /etc/group /etc/gshadow /tmp/lab/etc/
grpunconv -R /tmp/lab && cat /tmp/lab/etc/group
```

```bash
# Post-merge drift check: entries left without twins, malformed lines
getent group | awk -F: 'NF != 4 {print "bad:", $0}'
```

```bash
# Inventory what the platform expects: consumers of gshadow
sudo grep -rl gshadow /var/lib/dpkg/info/*.postinst 2>/dev/null | head
```

## Nuances and Gotchas

- **The security trade-off is the whole point — state it precisely.** `/etc/group` is 0644 root:root; `/etc/gshadow` is 0640 root:shadow. Un-converting moves any real group-password hash into the world-readable file — an offline-cracking target — while locked (`!`) groups are unaffected in practice. Since most groups are locked, the practical loss is usually the *administrators field*, not secrecy.
- **Administrators are destroyed, not moved.** There is no representation for gshadow's third field in `/etc/group`; `gpasswd -A` delegation is gone the moment the file is deleted, and `grpconv` cannot bring it back. Anything that must survive belongs in a backup taken before the run.
- **No backup, no dry-run, no undo button.** Recovery is: restore your snapshot, or accept that administrators are gone and rebuild gshadow with `grpconv` (which regenerates structure and locks, not deleted data).
- **Root required; lock failure is not contention.** As with grpconv (observed on its sibling): a non-root or read-only context yields `Permission denied.` then `cannot lock /etc/group; try again later.` The "try again later" phrasing is wrong for a permission failure — fix the privilege, not the loop.
- **It fights the platform.** Debian's `groupadd`, `useradd`, and packaging scripts all write gshadow-aware entries; after un-converting, the next group creation re-introduces partial shadowing (group file gets `x`-less single-file entries) and your system is a hybrid. Have a reason that outlives the next `apt upgrade`.
- **`x` placeholders un-convert to what they hid.** A group with password `x` and a locked gshadow twin ends up with `!` in `/etc/group` — correct, but surprising to people expecting empty fields.
- **Orphan handling differs from the conv direction.** The un-conv pass leaves `/etc/group` entries without twins untouched (unlike grpconv deleting shadow-only orphans); residue accumulates in the surviving file. A read-only `grpck` after the merge is the cheap way to catch drift.
- **NIS-era motivation, modern caveat.** The classic reason — serving one merged group map — assumes NIS is still the identity source. With SSSD/LDAP the local files are usually not what clients consume, and un-converting buys nothing.
- **Packages will partially undo you.** Debian package postinsts routinely call groupadd/gpasswd, both of which maintain the shadowed model; after grpunconv, the next package upgrade re-introduces shadow-ish state and your system becomes a hybrid (some groups with twins, some without). If the legacy consumer keeps breaking, the durable fix is teaching it gshadow, not re-running the downgrade on a schedule.
- **It has no prefix (-P) mode.** For staging trees you get `-R` (chroot, root only) — the same asymmetry with groupadd/groupmod that catches script authors copying option lists between tools.
- **Pair it with pwunconv only deliberately.** Flattening both shadow halves (users and groups) in one image is sometimes wanted for minimal appliances, but the two tools lose different data (aging vs administrators) and each needs its own pre-flight and snapshot. Running them together because they "look alike" doubles the blast radius of a single bad assumption.

## Exit Status

No exit-status table is documented for the converter family. As with its sibling `grpconv`: `0` on success (including the degenerate no-gshadow case, where there is nothing to merge) and nonzero on failure, with lock/permission failures the dominant real-world case. Diagnose by stderr shape, not by code archaeology:

```bash
grpunconv || { echo "un-convert failed"; journalctl -t grpunconv -n 5; }
```

## Related Commands

- [`grpconv`](./grpconv.md) — the inverse operation and the main recovery path after un-converting.
- [`grpck`](./grpck.md) — required pre-flight (the converter man page's own advice) and post-merge verifier.
- [`gpasswd`](./gpasswd.md) — owns the administrators field this tool deletes; inventory it first.
- [`groupadd`](./groupadd.md) — will start writing single-file entries on the un-shadowed system.
- [`groupmod`](./groupmod.md) — its `-p` now targets the world-readable group file.
- [`useradd`](./useradd.md) — creates groups with the shadowed model assumed; hybrid-state source after un-conversion.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together.
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: What exactly does grpunconv lose that grpconv cannot restore?

Two things, with different severity. The group password *values* move back into `/etc/group` and are recoverable by re-running grpconv — round-trip safe. The **administrators field** has no home in `/etc/group`'s format and is deleted with gshadow — permanent loss until someone re-runs `gpasswd -A` from a backup or memory. That asymmetry (numbers survive the round trip, delegation does not) is the precise answer interviewers want, and it is why the pre-flight one-liner is `awk -F: '$3 != ""' /etc/gshadow`.

### Q: A legacy NIS master requires a single merged group map. Walk through the change.

Check first (`grpck -r`, plus inventory administrators and any real group-password hashes), snapshot both files, run `grpunconv`, then regenerate the NIS maps (`cd /var/yp && make`). The merged `/etc/group` now carries real password fields — locked `!` for the overwhelming majority, hashes for any group that ever had one — and gshadow is gone. Name the trade-off out loud: hashes are now world-readable locally, delegation is lost, and the next Debian `groupadd` re-introduces hybrid shadowing. If the legacy consumer is the only justification, scope the downgrade to the NIS server and keep clients shadowed.

### Q: What happens to a group with password `!` (locked) when you run grpunconv?

The `!` is treated as the group's password value and merged into `/etc/group` as-is: the group file now shows `name:!:GID:members`. Nothing security-relevant changes — `!` matches no crypt(3) output, so password-based `newgrp` joins remain impossible, and a world-readable `!` leaks nothing. This is the common case (fresh groups are locked by default), and it is why the "world-readable passwords" alarm, while structurally true, is usually moot: the entries that mattered were the rare hashed ones.

### Q: Someone ran grpunconv on a production Debian host "to simplify auditing". What is your response plan?

Immediate: snapshot what remains (`/etc/group`) and check for damage — the run itself is merge-plus-delete, so the risk is the lost administrators field and the now-merged hashes. Recover: `grpconv` re-creates gshadow with correct structure and the `!`/hash values back in the protected file; administrators must be re-applied from the pre-change snapshot (`gpasswd -A`). Then close the process gap: un-converting a modern Debian system is a format downgrade that breaks delegation and re-exposes password hashes, "simplification" is not a consumer, and the audit tooling should learn gshadow rather than the database being flattened for it.

### Q: Why does the converter family's man page insist on running grpck first?

The conversion is a name-keyed join between two files, executed in multiple passes; duplicate group names or malformed lines make the join ambiguous, and the man page warns the converters may "loop forever or fail in other strange ways" on such input. grpck is the one tool with a reader dumb enough to address those entries (its prompted delete), and the suite's normal write tools cannot fix them. Hence the pipeline `grpck (-r or interactive) → grpunconv/grpconv → grpck -r to verify` is not ceremony; it is the difference between converting a database and converting a corruption.

### Q: Compare the information loss of pwunconv and grpunconv. Why are they asymmetric?

Both merge a shadowed file into its main twin and delete it, and both lose whatever the main file cannot represent. For users, `/etc/shadow` holds the hash *plus aging policy* (last change, min/max/warn, inactivity, expiry); `/etc/passwd` has a single password field, so pwunconv explicitly loses aging information — the man page says it "will convert what it can". For groups, `/etc/gshadow` holds the hash, the administrators, and a member view; `/etc/group` can carry the hash and members but not administrators, so grpunconv loses delegation. Same mechanism, field-specific losses — the design lesson is that shadow files are strictly richer, and downgrades are lossy in ways you must enumerate before pressing the button.

### Q: Is grpunconv idempotent? What does a second run do, and how do you detect the state idempotently?

Yes — trivially: with no `/etc/gshadow` there is nothing to merge, so a second run succeeds as a no-op (the degenerate case also covers systems that were never shadowed). That makes it safe in rerun-happy automation, but it also means the *state* check is what your script should key on, not the command's success: `ls -l /etc/gshadow` (present = shadowed, absent = flattened) or `test -f /etc/gshadow` in a provisioning gate. A robust image build asserts the intended state after the fact — `test -f /etc/gshadow` for the normal Debian posture — because both converters succeed whether or not they had work to do.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/grpunconv.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
