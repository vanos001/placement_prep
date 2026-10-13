# pwunconv — disable shadowed passwords (merge /etc/shadow back into /etc/passwd)

## Overview

`pwunconv` is the undo button for shadow passwords: it copies every password hash from `/etc/shadow` back into the password field of `/etc/passwd`, deletes the shadow file, and leaves the system in classic pre-shadow form. It ships in the `passwd` package and lives in `/usr/sbin/pwunconv`. Its man page is shared with `pwconv`, `grpconv`, and `grpunconv` — this is the "un" arm of the user-side pair, with `grpunconv` doing the same for groups.

It is one of the rarest commands in the suite to see in the wild, and deliberately so. Unconverting means every hash becomes world-readable (`/etc/passwd` must stay readable by all), and password-aging information is dropped on the floor. Modern PAM, `chage`, and the rest of the account tooling all assume shadow. You run pwunconv to emulate very old Unix behavior, in lab exercises about the shadow mechanism itself, or to satisfy some legacy appliance that cannot read a shadow file — and then you run `pwconv` again.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/pwunconv |
| First appeared | System V lineage (the pwconv/pwunconv pair is an SVR-era mechanism); part of the shadow suite since the Haugh codebase (1988+) |
| Standards | Not POSIX; specified by LSB. Behavior partly configured via /etc/login.defs |

## Synopsis

```
pwunconv [options]
```

One-line forms:

```
pwunconv              # merge /etc/shadow into /etc/passwd, then delete shadow
pwunconv -R /mnt/img  # do it to a chroot or mounted image, not the live system
```

No operands, no verbosity flags: like its sibling `pwconv`, the entire behavior is defined by the two input files.

## How It Works

### The merge algorithm

The man page defines pwunconv (and grpunconv) symmetrically to pwconv:

```
step 1: for every passwd entry that HAS a matching shadow entry,
        the password field in /etc/passwd is UPDATED from /etc/shadow
step 2: entries that exist in passwd but not in shadow are LEFT ALONE
        (they keep whatever placeholder or hash they already carry)
step 3: /etc/shadow is REMOVED
```

Step 1 is the only data movement, and it moves exactly one field: the encrypted password. The hash format is unchanged — a yescrypt hash starting `$y$` (Debian bookworm's default) or any other crypt scheme simply becomes field 2 of the passwd line:

```
shadow era:   z:x:1001:1001::/home/z:/bin/bash
              z:$y$j9T$...hash...:19900:0:99999:7:::        (in /etc/shadow)

unconverted:  z:$y$j9T$...hash...:1001:1001::/home/z:/bin/bash
              (and /etc/shadow no longer exists)
```

Step 2 preserves the invariant that a passwd-only entry is already self-contained: users whose password field is `*`, `!`, or an `x`-era leftover from a user with no shadow row keep working, since NSS treats a non-`x` password field as the literal hash or lock.

### What is lost in translation

The shadow file's remaining seven fields are aging data with **no home in `/etc/passwd`** — there is nowhere to put them, so they are dropped:

```
/etc/shadow fields:  name : hash : lastchg : min : max : warn : inact : expire : flag
                      |      |      all of these are LOST          |
                      |      +-- survives, into passwd field 2
                      +-- redundant (key)
```

The man page says it directly: "Some password aging information is lost by pwunconv. It will convert what it can." After an unconvert, `chage` has nothing to manage, and any expiry date that would have disabled an account on schedule never fires. Re-running `pwconv` re-creates shadow rows, but seeded from `login.defs` defaults — the previous per-user aging values are gone for good.

### The lock-and-rename mechanics

Like pwconv, pwunconv acquires the shadow-suite locks, works through temporary files (the `/etc/npasswd`-style temp names documented for the converter family), and renames results into place before removing the shadow file. The same dash-suffix backup convention applies. And the same man-page BUGS warning applies: convert from corrupt files and the result is undefined — `pwck -r` first, always.

### The security trade-off, concretely

The entire reason shadow exists is that `/etc/passwd` must be world-readable while hashes must not be:

```
$ stat -c '%n %A %U:%G' /etc/passwd /etc/shadow
/etc/passwd -rw-r--r-- root:root
/etc/shadow -rw-r----- root:shadow
```

Group `shadow` is not "everyone": after pwunconv, every local account (and every process, every CGI, every compromised service) can read every hash and take them offline for brute-forcing. Pre-shadow Unix survived this because hashes were slow DES crypt and the threat model was gentler; that calculation no longer holds. This is the answer to "why is pwunconv rarely used": not because it is broken, but because its output is strictly less secure and loses policy data.

### A worked unconversion

Before:

```
# /etc/passwd
z:x:1001:1001::/home/z:/bin/bash
svc:x:990:990::/var/lib/svc:/usr/sbin/nologin

# /etc/shadow
z:$y$j9T$abc...:19900:0:99999:7:::
svc:!:19900:0:99999:7:::
```

After `pwunconv`:

```
# /etc/passwd — hashes inline; lock states carried over verbatim
z:$y$j9T$abc...:1001:1001::/home/z:/bin/bash
svc:!:990:990::/var/lib/svc:/usr/sbin/nologin

# /etc/shadow — removed entirely
```

The aging fields of both rows (lastchg 19900, min 0, max 99999, warn 7) are gone; if `svc`'s expire field had held a date, that scheduled disable would now exist nowhere. Note also what did *not* happen: `svc` remains locked — `!` is just a field value, and a field value is all the merge moves.

### The round trip

Running `pwunconv` then `pwconv` is lossy in exactly one direction:

```
hashes        survive both directions intact
lock states   survive both directions (they are just field values)
aging fields  destroyed by pwunconv, re-seeded from login.defs by pwconv
```

So the only true undo is the file backup taken before the run. `pwconv` after the fact restores the *format*, not the *policy*: rows come back with today's login.defs defaults rather than the per-user aging values that were dropped. Backup-first is not ceremony; it is the reversibility plan.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-h`, `--help` | Display help and exit. |
| `-R`, `--root DIR` | Unconvert `DIR/etc/passwd` + `DIR/etc/shadow` instead of the live system. Absolute paths only. |

As with `pwconv`, the flag surface is minimal and there is no dry-run mode; preview by copying the file pair elsewhere (or via `-R` on a prepared directory) first.

## Usage Patterns

```bash
# Lab exercise: show the pre-shadow state on throwaway copies
mkdir -p /tmp/unc/etc && cp /etc/passwd /etc/shadow /etc/login.defs /tmp/unc/etc/
pwunconv -R /tmp/unc
grep '^z:' /tmp/unc/etc/passwd          # hash is now inline
ls /tmp/unc/etc/shadow                  # gone

# Legacy emulation for an appliance that only reads passwd
cp -a /etc/passwd /etc/passwd.bak && cp -a /etc/shadow /etc/shadow.bak
pwunconv

# Validate input before unconverting (converter family BUGS rule)
pwck -r && pwunconv

# Verify no aging data survives the round trip you are about to make
chage -l z > /tmp/aging-before.txt; pwunconv; pwconv; chage -l z

# After unconv, confirm hashes are world-readable (the whole point of alarm)
stat -c '%n %A' /etc/passwd

# Undo it — back to normal Debian posture
pwconv && grpconv

# Clean up the group side the same way (rarely, and with the same caveats)
grpunconv

# Scripted guardrail: refuse to unconvert if any account has an expiry date
if awk -F: '$8 != "" {found=1} END {exit found ? 1 : 0}' /etc/shadow; then
    pwunconv
else
    echo "expiry data present, unconv would destroy it" >&2
    exit 1
fi

# Prove the world-readable exposure you just created (the audit evidence)
namei -l /etc/passwd

# Checksum your backups so the undo is provably intact
sha256sum /etc/passwd.bak /etc/shadow.bak > /root/unconv-backup.sha256
sha256sum -c /root/unconv-backup.sha256

# Round-trip drill on copies: see exactly what survives
mkdir -p /tmp/rt/etc && cp /etc/passwd /etc/shadow /etc/login.defs /tmp/rt/etc/
pwunconv -R /tmp/rt && pwconv -R /tmp/rt
diff /etc/shadow /tmp/rt/etc/shadow   # hashes match; aging re-seeded to defaults
```

The `namei -l` line is the quick demonstration for reviews: it prints the path components with their permissions, showing that every directory to `/etc/passwd` is traversable and the file itself is world-readable.

## Nuances and Gotchas

- **Destructive by design.** pwunconv removes `/etc/shadow` outright. Unlike pwconv's reconcile no-op, running pwunconv always changes the system. Take `cp -a` backups of both files first.
- **Aging data loss is permanent.** Last-change, min, max, warn, inactive, and expiry fields do not survive. Re-converting with `pwconv` does not restore them — new rows are seeded from login.defs. Export with `chage -l` per user if you need an undo trail.
- **World-readable hashes.** The whole security posture regresses: any local user or any service running as a non-root UID can read all hashes. Offline cracking becomes a local-privilege-escalation afterthought.
- **Tooling drift.** `chage` has nothing to manage without shadow, `expiry` loses its enforcement hook, and Debian's default configuration of the whole suite assumes the shadowed state.
- **You must be root.** Same failure shape as pwconv — permission denied on the shadow file, then a lock failure, exit 5 (observed on this container for the sibling command; pwunconv fails identically because it opens the same pair).
- **Corrupt input, strange output.** The shared BUGS section applies verbatim: run `pwck` and `grpck` first or the conversion may loop or misbehave.
- **The reverse direction is the default state.** Modern installers run pwconv/grpconv as a matter of course; pwunconv is the abnormal direction. If you find a system unconversioned in an audit, that is a finding, not a quirk.
- **`grpunconv` additionally exposes group administrator lists** (the third gshadow field), not just group password hashes — group-level trust relationships become world-readable too.
- **No dry run, no verbose mode.** Preview on copies via `-R` as shown; there is nothing else to interrogate.
- **Locked accounts stay locked, silently.** `!`- and `*`-prefixed field values merge over verbatim, so a locked account remains locked after unconv — convenient, but it also means lock hygiene errors (a stray `!` on an account that should authenticate) become *less* visible once there is no shadow file to diff against.
- **You cannot 'partially' unconvert.** The password field of `/etc/passwd` must hold a real value for every account, and the file must stay world-readable — chmod'ing passwd 0640 instead is not a middle ground; it breaks every tool that resolves names as non-root.
- **Repeated scripted use is a design smell.** If a pipeline keeps calling pwunconv, the actual problem is a consumer that cannot read `/etc/shadow`; fix the consumer (NSS, getent, or a root-owned reader) rather than downgrading the system each run.

## Exit Status

The man page documents no exit-status table for the converter family. In practice on Debian's shadow 4.13-4.17:

- `0` — merge completed and shadow removed.
- non-zero — failure to open, lock, read, or write the files (non-root runs fail with permission + lock errors and exit 5, as observed for this family).

Since success is *destructive*, scripts should check exit status *and* verify `/etc/shadow` is gone before declaring victory.

## Related Commands

- [`pwconv`](./pwconv.md) — the normal direction and the immediate remedy: recreate and repopulate /etc/shadow.
- [`pwck`](./pwck.md) — pre-flight validation; the converter family's BUGS section demands it.
- [`chage`](./chage.md) — the aging fields whose data pwunconv destroys; export before you convert.
- [`expiry`](./expiry.md) — enforcement that depends on shadow aging data.
- [`passwd`](./passwd.md) — continues to work after unconv (field 2 becomes the hash), but policy tooling around it does not.
- [`vipw`](./vipw.md) — `-s` edits /etc/shadow; after pwunconv there is nothing for it to edit.
- [overview](./overview.md) — the shadow suite collection and why shadow is the default state.
- [users-groups](../../admin/users-groups.md) — the read-world-readable-passwd problem this command resurrects.

## Interview Questions

### Q: What exactly does pwunconv do to the two files, and what data does not survive?

It updates each password field in `/etc/passwd` from the matching `/etc/shadow` entry, leaves passwd-only entries untouched, and then deletes `/etc/shadow`. Only the hash survives the trip. The shadow aging fields — last change, min, max, warn, inactive, expire — have no corresponding column in passwd and are dropped; the man page concedes it "converts what it can". Re-running pwconv later rebuilds rows from login.defs defaults, so the loss is permanent.

### Q: Why was the shadow file invented, and what does that make pwunconv?

`/etc/passwd` must be world-readable (every tool resolves UIDs through it), but since the 1980s password hashes in it could be read by any user and attacked offline. The shadow mechanism moved hashes into a root-only `/etc/shadow`, leaving the `x` placeholder behind. pwunconv inverts that hardening: by design it makes every hash world-readable again. It is not a bug or a legacy accident — it is the faithful restoration of a weaker, historical state, which is why it exists but is almost never used.

### Q: A legacy appliance requires hashes in /etc/passwd. How do you deploy pwunconv responsibly?

Take `cp -a` backups of `/etc/passwd` and `/etc/shadow`; run `pwck -r` first per the converter family's BUGS note; export the aging state (`chage -l` per user) since it will be destroyed; convert on copies via `pwunconv -R` on a prepared directory before touching the live system; and schedule a `pwconv && grpconv` to return to the normal posture as soon as the appliance no longer needs the legacy view. Also document the exposure window: during it, every local account can read every hash.

### Q: Does authentication keep working after pwunconv? What breaks?

Authentication keeps working: NSS/PAM treat a non-`x` password field as the literal hash, so logins and `su` proceed exactly as on pre-shadow Unix. What breaks is policy tooling: `chage` has no shadow rows to read or write, expiry no longer fires, `expiry` loses its data source, and any PAM configuration or audit script that assumes shadow semantics misreports. The system is not broken — it is downgraded.

### Q: How do you make a pwunconv operation reversible, given that pwconv does not restore aging policy?

Two artifacts, taken before the run: a `cp -a` backup of both `/etc/passwd` and `/etc/shadow` (the real undo), and an export of per-user aging state via `chage -l` (the audit trail). pwconv after the fact rebuilds the shadow *format* but seeds rows from login.defs, so policy values are only recoverable from the backup or the export. The professional framing: pwunconv is a one-way format conversion, and reversibility is an operational property you build around it, not a tool property.

### Q: Compare the data-flow risks of pwunconv and pwconv. Which one can lose data, and why?

Only pwunconv can lose data. pwconv moves hashes into a file that has *more* columns, re-seeding missing aging fields from login.defs — nothing has nowhere to go, and it is idempotent. pwunconv squeezes nine-column shadow rows into a seven-column passwd format; seven fields map into one, and six are discarded by the format itself. That asymmetry — expandable one way, lossy the other — is the interview-level reason the man page warns "some password aging information is lost" only on the unconv side.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/pwunconv.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
