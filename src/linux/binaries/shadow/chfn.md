# chfn — change your GECOS (finger) information

## Overview

`chfn` edits the GECOS field of a user's `/etc/passwd` entry: full name, office room, office phone, home phone, and the catch-all "other" slot. As an ordinary user it changes your own record (after PAM authentication and within the policy limits in `/etc/login.defs`); root changes any field for anyone, including the free-form `other` area reserved to root. It ships in the `passwd` package (upstream shadow suite) at `/usr/bin/chfn`, setuid root like its self-service siblings `chsh` and `passwd`.

The name is a fossil: GECOS stands for *General Electric Comprehensive Operating System*, whose batch output the field originally described on early Unix systems. The data still matters operationally — display managers, mailers, `finger`, `getent`-based LDAP sync, and countless provisioning tools read it — but its content is legacy-trusting: it is the one passwd field users were historically allowed to write freely, which is exactly why `CHFN_RESTRICT` exists.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 1 |
| Path | /usr/bin/chfn (setuid root) |
| First appeared | BSD heritage; shadow suite rewrite (1988+) |
| Standards | POSIX.1-2018 (User Portability, optional); LSB |

## Synopsis

```
chfn [options] [LOGIN]
```

Common one-line forms:

```
chfn                        # interactive: prompts for each allowed field
chfn -f "Ann Doe"           # set full name only
chfn -r 4B -w +49-30-1234   # room and office phone
chfn -f "Root Account" root # root editing another account
```

## How It Works

### The GECOS field, field by field

The fifth colon-separated field of `/etc/passwd` is the GECOS comment, itself comma-separated:

```
alice:x:1000:1000:Ann Doe,4B,+49-30-1234,+49-30-5678,jira:AL1000:/home/alice:/bin/bash
                                   |    |          |            |    |
                                   |    |          |            |  + other (-o, root only)
                                   |    |          |            + home phone (-h)
                                   |    |          + office phone (-w)
                                   |    + room (-r)
                                   + full name (-f)
```

`chfn -f -r -w -h` map onto the first four subfields; `-o` rewrites everything after the fourth comma and is root-only ("the undefined portions of the GECOS field"). Historical Unix put `plan`/`project` data in `other` for `finger`; today it is where directory-sync metadata often hides.

Interactive `chfn` (no flags) prompts for the fields the policy allows, showing current values as defaults; flag mode changes exactly the given fields and leaves the rest alone.

### Character restrictions

The man page is specific: fields must not contain colons (they would forge extra passwd fields), and except for `other` they should not contain commas or `=` (commas forge subfield boundaries; `=` has mailer/UMA history). Non-ASCII is discouraged but only *enforced* for phone numbers. These checks are what keep a user's name from breaking the file format — the reason a bare `chfn` refuses `Ann:Doe` rather than writing it and corrupting `/etc/passwd`.

### CHFN_RESTRICT: Debian's policy switch

`/etc/login.defs` `CHFN_RESTRICT` lists the fields ordinary users may change, as a letter set:

```
f = full name   r = room   w = work phone   h = home phone
```

This container ships `CHFN_RESTRICT rwh` — full name is *not* changeable by users, room and phones are. That is Debian's deliberate default (the chfn man page states it plainly: "The default configuration is to prevent users from changing their fullname"). Consequences:

```
$ chfn -f "Anything I Want"
chfn: Permission denied.
```

Root ignores `CHFN_RESTRICT` entirely. An empty/unset `CHFN_RESTRICT` means all four fields are self-service. Site policy (multi-user labs, universities) commonly sets `CHFN_RESTRICT frwh` to freeze the whole field for self-service, keeping identity data directory-managed. Note the asymmetry with the man page's phrasing on other systems: on Debian the option is *compiled in and honored*; some distributions ship with it unset.

### The transaction

`chfn` authenticates the user (PAM), validates characters, applies `CHFN_RESTRICT` (unless root), locks `/etc/passwd`, rewrites the single line, unlocks. The setuid-root binary is what lets an unprivileged process perform that locked rewrite of a root-owned file. Verified refusal path on this container (PAM prompt cut off):

```
$ chfn -f x
Password: <eof>
chfn: Permission denied.        (exit 1)
```

### Interactive mode, step by step

Flagless `chfn` is a five-prompt dialog, each prompt showing the current value:

```
$ chfn
Password: ********                <- PAM auth (skipped for root editing others)
Changing the user information for alice
Enter the new value, or press return for the default
        Full Name [Ann Doe]:      <- prompt 1 (skipped if CHFN_RESTRICT has f)
        Room Number [4B]:         <- prompt 2
        Work Phone [+1-555-0100]: <- prompt 3
        Home Phone []:            <- prompt 4
        Other [empid=E12345]:     <- prompt 5 (non-root: shown, not changeable
                                     on restricted configs; -o is root-only)
```

Empty input keeps the current value; a lone `.` in older dialects also kept the value. Scripts should prefer the flag forms — the interactive loop reads stdin line by line and does not mix well with automation.

### Who actually consumes GECOS today

```
consumer                     field used
display managers (gdm, sddm) full name for the greeter
mail tools (mailx headers)   full name for the From: gecos expansion
finger (legacy, rarely on)   all five
quota -v / edquota output    full name as the label
third-party identity sync    other (empid, costcenter metadata)
LSB/nss-based tooling        full name via getent passwd field 5
```

That breadth is the operational argument for `CHFN_RESTRICT`: a field a user can edit is a field that shows up on someone else's screen, header, or report.

## Options That Matter

| Option | Effect |
| --- | --- |
| -f FULL_NAME | set the full-name subfield |
| -r ROOM | set the room/office subfield |
| -w WORK_PHONE | set the office phone subfield |
| -h HOME_PHONE | set the home phone subfield |
| -o OTHER | rewrite the "other" area — **root only** |
| -R CHROOT_DIR | operate inside a chroot |
| -P PREFIX | use PREFIX/etc files without chrooting |

No-flags mode is interactive; flags imply non-interactive for the named fields. There is no "clear a field" flag — pass an empty string (`chfn -f ""` clears the name).

## Usage Patterns

```bash
# Interactive self-service: prompts field by field with current defaults
chfn
```

```bash
# Set your displayed name (allowed unless CHFN_RESTRICT includes f)
chfn -f "Ann Doe"
finger "$(whoami)" | head -2    # see it reflected
```

```bash
# Office metadata in one call
chfn -r "4B" -w "+1-555-0100"
```

```bash
# Clear a field you no longer want published
chfn -h ""
```

```bash
# Root fixes a display name that provisioning mangled
chfn -f "Doe, Ann (contractor)" alice
```

```bash
# Root writes directory-sync metadata into the root-only 'other' area
chfn -o "empid=E12345;costcenter=42" alice
getent passwd alice | cut -d: -f5
```

```bash
# Check which fields your site allows users to change
grep CHFN_RESTRICT /etc/login.defs
# CHFN_RESTRICT rwh        <- 'f' missing: users cannot rename themselves
```

```bash
# Inspect what display managers and mailers will show
getent passwd "$(whoami)" | cut -d: -f5
```

```bash
# Edit a user inside a mounted image
chfn -R /mnt/rootfs -f "Rescue User" 1000
```

```bash
# Bulk-fix display names from an HR export (root, one GECOS subfield at a time)
while IFS=: read -r u name; do chfn -f "$name" "$u"; done < names.tsv
```

```bash
# Show the full GECOS of every human account, subfield-split
getent passwd | awk -F: -v OFS='|' '$3 >= 1000 {split($5,g,","); print $1, g[1], g[2]}'
```

```bash
# Prove that usermod -c replaces the WHOLE field (keep a backup first)
getent passwd alice | cut -d: -f5 > /tmp/alice.gecos
sudo usermod -c "Temp" alice && getent passwd alice | cut -d: -f5
```

## Nuances and Gotchas

- **`CHFN_RESTRICT` is why your `-f` failed.** On Debian the shipped default (`rwh`) blocks self-service *full name* changes specifically; the error is a bare "Permission denied" with no hint. Read `/etc/login.defs` before assuming PAM is broken.
- **`-o` is root-only everywhere**, not policy-gated: the "other" subfield is where accounting/SSO metadata lives, and letting users write it would be an injection point for whatever parses it.
- **Colons, commas, `=`**: validation failures look like generic refusals. The colon rule protects the passwd file format itself; commas would silently split your name into room/phone subfields.
- **finger is mostly dead; the field is not.** GECOS feeds display-manager greeters, `mail` headers, quota reports, and third-party identity sync. Changing it is a *publication* act on many systems, which is exactly why sites restrict it.
- **Empty-string clears; whitespace does not.** `chfn -f " "` stores a space — visible in every login banner. Empty string is the reset.
- **Locale and UTF-8**: modern chfn accepts UTF-8 names on modern locales, but consumers vary wildly in rendering them; the man page still recommends avoiding non-US-ASCII outside phone enforcement.
- **setuid placement**: chfn's privilege comes from setuid root (unlike chage's setgid shadow) because it must *write* `/etc/passwd`, not merely read `/etc/shadow`. `chmod u-s` breaks self-service with PAM errors.
- **NIS/LDAP-backed users**: like passwd, chfn edits the local file; directory-served accounts need the directory's own tools, and the change silently does not replicate.
- **`-R`/`-P` read the target tree's login.defs**, so CHFN_RESTRICT inside a mounted image governs non-root edits there, not the host's policy.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | permission denied (authentication failed, restricted field, non-root on -o/other user) |
| 2 | invalid command syntax |
| 3 | invalid argument to option |

Non-zero here is dominated by the permission-denied family: wrong PAM password, `CHFN_RESTRICT`, editing someone else's record as non-root, or `-o` without root all collapse into exit 1.

## Related Commands

- [`chsh`](./chsh.md) — the sibling self-service tool for the login-shell field.
- [`passwd`](./passwd.md) — the self-service password tool sharing the same setuid + PAM pattern.
- [`usermod`](./usermod.md) — `-c` rewrites the whole GECOS comment from the admin side.
- [`useradd`](./useradd.md) — `-c` seeds the field at creation time.
- [`chage`](./chage.md) — the other per-account self-service reader.
- [`gpasswd`](./gpasswd.md) — group-side administration in the same collection.
- [`expiry`](./expiry.md) — login-time password enforcement.
- [overview](./overview.md) — the shadow suite collection hub.
- [users-groups](../../admin/users-groups.md) — /etc/passwd field anatomy in depth.

## Interview Questions

### Q: What is the GECOS field, what are its subfields, and where does the name come from?

Field 5 of `/etc/passwd`, comma-separated: full name, room, office phone, home phone, other. The name comes from the General Electric Comprehensive Operating System, whose print jobs early Unix spooled through systems that recorded these details; the label stuck. It is displayed by `finger`, greeters, and mail tools, and `other` (root-only via `chfn -o`) is a common spot for directory-sync attributes.

### Q: A user cannot change their full name with chfn but can change their office phone. Explain.

`CHFN_RESTRICT` in `/etc/login.defs` whitelists changeable fields as a letter set (`f` full name, `r` room, `w` work phone, `h` home phone). Debian ships `CHFN_RESTRICT rwh`, deliberately excluding `f` so users cannot misrepresent identity data; phones and rooms are considered cosmetic. Root bypasses the restriction entirely. The fix for the user is administrative, not technical.

### Q: Why can an ordinary user run chfn at all when it edits a root-owned file?

`/usr/bin/chfn` is setuid root: the process gains root euid, authenticates the user through PAM, applies policy checks (ownership of the record, `CHFN_RESTRICT`, character validation), then performs the locked rewrite of `/etc/passwd`. The security argument is that the policy check happens *after* privilege is acquired but the code path is fixed — the same reasoning as passwd, and the reason stripping the setuid bit silently breaks self-service.

### Q: What stops a user from setting their name to `x:x:0:0:hacker`?

Character validation: GECOS subfields may not contain colons (which would add forged passwd fields), and except for `other` no commas or `=`. chfn rejects the input rather than sanitizing it. The deeper point is that `/etc/passwd` is a colon-delimited database and every field-level tool must enforce its delimiter discipline; the same reason `useradd` rejects bad login names.

### Q: What are the operational differences between `chfn -f`, `usermod -c`, and editing /etc/passwd by hand?

`chfn -f` validates the subfield, honors CHFN_RESTRICT, authenticates, and edits only that subfield of the comma structure. `usermod -c` rewrites the *entire* GECOS comment from root with no policy gate — it is the admin tool and will happily replace all five subfields. Hand-editing (`vipw`) bypasses validation and locking discipline; `vipw` at least provides locking and syntax checks. Scope and guardrails, not different data.

### Q: Your site uses LDAP for identity. What happens when a user runs chfn?

It edits the local `/etc/passwd` line if one exists — and on a properly NSS-configured host there usually is not one, so the change fails or affects a stale cache entry, and never reaches the directory. Identity attributes must be changed in LDAP itself (or the directory's client tools). This is the general rule with all shadow tools: they are local-file tools; NSS backends need backend-native administration.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/chfn.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
