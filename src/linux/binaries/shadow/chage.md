# chage — change and inspect password-aging information

## Overview

`chage` ("change age") is the shadow suite's aging tool: it reads and writes the password-lifetime and account-expiry fields of `/etc/shadow` for an account. As root you set the minimum/maximum password age, warning period, post-expiry inactivity grace, and the hard account-expiry date; any user may list their own aging state with `chage -l`. It ships in the `passwd` package (upstream shadow suite) at `/usr/bin/chage`, implemented as a setgid-`shadow` binary — it reads `/etc/shadow` through group membership rather than setuid root, a telling detail about which direction its privilege needs go.

`chage` overlaps `passwd -n/-x/-w/-i` and `usermod -e/-f` (they edit the same fields), so the real skill is knowing the division of labor: `chage` is the only one with a *human-readable listing* (`-l`) and with an `-i`/`--iso8601` date display, and the only self-service one. When an interviewer asks "how do you force a password change at next login" or "why can't this user log in anymore", the answer usually starts here.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 1 |
| Path | /usr/bin/chage (setgid shadow) |
| First appeared | shadow suite original (1990s, shadow-utils lineage) |
| Standards | None (shadow-specific); not POSIX, not LSB |

## Synopsis

```
chage [options] LOGIN
```

Common one-line forms:

```
chage -l alice                # list aging state (self or root)
chage -M 90 -W 14 alice       # 90-day rotation with 14-day warning
chage -E 2025-12-31 alice     # account dies at that date
chage -d 0 alice              # force password change at next login
```

## How It Works

### The six aging fields and where they live

`chage` operates on fields 3-8 of the nine-field shadow record:

```
alice:$y$5$...:19900:0:99999:7:-1:20000:
                     |    |    |   |  |  |
last change   (3) ----+    |    |   |  |  + account expiry (8)     <- -E
min days      (4) ---------+    |   |  +   inactivity    (7)     <- -I
max days      (5) --------------+   +    warn days      (6)     <- -W
```

The fields are day counts, except field 3 (days since epoch of the last change) and field 8 (days since epoch of expiry; modern chage accepts and displays `YYYY-MM-DD`). An empty field 3 (as useradd leaves for `-r` accounts) means "no aging at all" — `chage -l` shows it, and any `chage -d` you run converts the record to a fully-aged one.

### Reading: chage -l

The listing is the best mental model of the whole system. Verified output for this container's own user:

```
$ chage -l z
Last password change                                    : Sep 21, 2026
Password expires                                        : never
Password inactive                                       : never
Account expires                                         : never
Minimum number of days between password change          : 0
Maximum number of days between password change          : 99999
Number of days of warning before password expires       : 7
```

Each line maps 1:1 to a shadow field (3 through 8, top to bottom). "never" is the -1 / empty representation. Run as non-root, `chage -l` works only for your own login; asking for someone else's is refused because the shadow file itself is unreadable:

```
$ chage -l root
chage: Permission denied.
```

Root can list anyone; members of the `shadow` group could too, via the setgid bit.

### The two clocks: password aging vs account expiry

`chage` manages two independent timelines and conflating them is the classic mistake:

```
password timeline (recoverable):
  last change --min--> changeable --max--> EXPIRED (force change at next
                                           login) --inactive days--> account
                                           auto-disabled (field 7)

account timeline (hard):
  field 8 date reached --> logins refused outright, password irrelevant
```

- Expiry (`-M`) makes the user *change their password*: annoying, self-healing, works over SSH password auth.
- Inactivity (`-I`) is the days *after expiry* before the account is locked out entirely — a policy knob for "rot or retire stale accounts".
- Account expiry (`-E`) is a wall-calendar kill date: after it, authentication fails regardless of password freshness, with "Your account has expired" at the console. Contractors, interns, temporary vendor accounts.

Setting `-E 1` (1970-01-02) is the standard idiom for "already expired" — the deliberate-disable pair with `usermod -L`/`passwd -l`.

### Writing: date formats and semantics

All date-taking options accept `YYYY-MM-DD` (and `chage -d`/`-E` also accept days-since-epoch integers):

- `-d 0` zeroes the last-change field: the password counts as infinitely old, so the next login is a forced change. The provisioning idiom, equivalent to `passwd -e`.
- `-E 2025-12-31` sets the account kill date; `-E -1` clears it.
- `-I -1`, `-m 0` are the "never"/"no limit" resets.
- `-M 99999` (this container's login.defs default) is Debian's "effectively never" for max age.

One chage invocation may combine several options; they are all written in the same locked transaction.

## Options That Matter

### Listing

| Option | Effect |
| --- | --- |
| -l | list aging state in human form (self-service allowed) |
| -i | render listing dates as YYYY-MM-DD instead of locale text |

### Password lifetime

| Option | Effect |
| --- | --- |
| -d LAST_DAY | set last-change date (0 = force change at next login) |
| -m MIN_DAYS | minimum days between changes (0 = change any time) |
| -M MAX_DAYS | maximum days before the password expires |
| -W WARN_DAYS | days of warning before expiry (login-time message) |

### Disablement

| Option | Effect |
| --- | --- |
| -I INACTIVE_DAYS | days after expiry before auto-disable (-1 = never) |
| -E EXPIRE_DATE | hard account expiry date (-1 = none) |

### Scoping

| Option | Effect |
| --- | --- |
| -R CHROOT_DIR | operate inside a chroot |
| -P PREFIX | use PREFIX/etc files without chrooting |

## Usage Patterns

```bash
# List your own aging state (the only non-root use)
chage -l
```

```bash
# Corporate policy: rotate every 90 days, warn 14, never auto-disable
chage -M 90 -W 14 -I -1 alice
```

```bash
# Force a change at next login after an initial secret was set
passwd alice && chage -d 0 alice
```

```bash
# Contractor account: hard expiry plus post-expiry grace of 0 days
chage -E 2025-09-30 -I 0 contractor
```

```bash
# Release a suspended account: clear expiry and inactivity
chage -E -1 -I -1 contractor
```

```bash
# Retro-apply max-age to a population that predates the policy
for u in $(awk -F: '$3 >= 1000 {print $1}' /etc/passwd); do
  chage -M 90 "$u"
done
```

```bash
# Audit: who expires within 30 days, ISO dates for scripts
chage -l -i alice | grep -i 'account expires'
```

```bash
# Full machine audit of password state in one pass (root)
passwd -S -a | awk '$2 != "P" {print}'        # locked / passwordless first
for u in alice bob; do chage -l "$u" | head -4; done
```

```bash
# Repair a system-user record that got aging fields by accident
chage -M -1 -m 0 -E -1 -I -1 svc-backup 2>/dev/null || true
```

```bash
# Check aging for a user inside a mounted image
chage -R /mnt/rootfs -l rescueuser
```

## Nuances and Gotchas

- **Non-root can only read self.** `chage -l otheruser` is "Permission denied." — the setgid-shadow binary still enforces the shadow file's confidentiality. Root (or shadow group) for everyone else; `passwd -S -a` is the terse bulk alternative.
- **`-d 0` vs `-E 1`:** one forces a password change (user recovers by logging in), the other kills the account (nobody logs in, period). Mixing them up in a disable script either fails to disable or bricks the account permanently.
- **Empty field 3 means no aging**, which is how system accounts ship; the first `chage -d` on such an account silently activates aging for it. Daemons do not log in, so it is usually harmless, but batch "apply policy to all users" scripts should exclude UID < 1000.
- **Inactivity is measured from password expiry**, not from last login. A user who never logs in again after expiry crosses into `-I` disablement on schedule — that is the point, but it surprises people expecting "days since last login".
- **Date parsing is locale-sensitive in display but ISO in input**: `chage -E 12/31/2025` fails or misbehaves; use `2025-12-31`. The `-i` flag only affects output formatting.
- **`chage` does not validate against login.defs defaults.** It writes exactly what you say; nothing recalculates when login.defs later changes. Policy changes require re-running chage across the population (login.defs only seeds *new* accounts).
- **SSH with keys ignores all of this except field 8.** Password aging never triggers for key-based logins (there is no password being checked); only hard account expiry `-E` stops a key user. Security teams repeatedly discover this after deploying rotation-only policy.
- **The warn message is login-time only.** `-W` produces a console/SSH-pre-auth message; GUI logins, cron, and daemons never see it. It is not a notification system.
- **`chage -l` output format is not API-stable** across shadow versions (date rendering changed more than once). Scripts should prefer `passwd -S` (stable, one-line) or read shadow fields via `getent shadow` as root.
- **`-R`/`-P` are for images and recovery**, and both read `/etc/login.defs` from *inside* the target tree — date range defaults may differ from the host's.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | permission denied (non-root asking about another user, or PAM failure) |
| 2 | invalid command syntax |
| 15 | can't find the shadow password file |

The narrow code set reflects the narrow job: parse, read/write two files, done.

## Related Commands

- [`passwd`](./passwd.md) — sets passwords and a subset of these fields; -S for terse status.
- [`usermod`](./usermod.md) — -e/-f write the same fields from the account-editing side.
- [`useradd`](./useradd.md) — seeds these fields from login.defs at account creation.
- [`expiry`](./expiry.md) — login/cron-time enforcement of the state chage configures.
- [`userdel`](./userdel.md) — the end of the lifecycle these dates govern.
- [`chfn`](./chfn.md) / [`chsh`](./chsh.md) — the other self-service account tools.
- [`gpasswd`](./gpasswd.md) — group-side administration.
- [overview](./overview.md) — the shadow suite collection hub.
- [users-groups](../../admin/users-groups.md) — shadow file anatomy and login-time enforcement details.

## Interview Questions

### Q: How do you force a user to change their password at next login, and what happens exactly?

`chage -d 0 user` (or `passwd -e user`): the last-change field is zeroed, so the password is treated as expired immediately. At the next login the authentication succeeds, PAM reports the password must be changed, and the session is forced through `passwd`-style change prompts before continuing. The user's access is never blocked — unlike `-E`, which refuses logins outright.

### Q: Explain the difference between password expiry, password inactivity, and account expiry.

Password expiry (field 5, `-M`): after max days the password must be changed at next login — recoverable. Inactivity (field 7, `-I`): days *after expiry* with no successful change before the account is auto-disabled — needs root to reset. Account expiry (field 8, `-E`): an absolute date after which logins are refused no matter what. The first two are password-lifecycle policy; the third is account-lifecycle policy, and it is the only one that stops SSH key-based logins.

### Q: A user's password is fine but they cannot log in; `chage -l` shows "Account expires: Mar 1, 2025". What happened and what do you do?

The hard expiry date passed: shadow field 8 is in the past, so login is refused before authentication even matters. Fix with `chage -E -1 user` (or a new future date). The diagnostic point: `passwd -S` and successful `su - user` from root vs failed console logins is the discriminating pattern; expired accounts and locked passwords present differently ("account expired" vs authentication failure).

### Q: Why does `chage -l alice` work as alice but `chage -l root` fails for alice?

Non-root `chage` is permitted only for the invoking user's own record: the setgid-shadow binary can technically read `/etc/shadow`, but it deliberately refuses other users' records to preserve shadow-file confidentiality. Root has no such restriction. The setgid-shadow (rather than setuid-root) design shows the intended privilege direction: read access to one file, no identity assumption needed.

### Q: You need 90-day rotation for all humans on a fleet where accounts were created years ago. Why is editing login.defs not enough, and what is the plan?

login.defs (`PASS_MAX_DAYS`) only seeds records at *creation*; existing shadow entries keep their stored max days. The plan is a bulk `chage -M 90` over UID >= 1000 (excluding system accounts), ideally paired with `-W 14` warning and a `-d 0` for anyone whose password is already older than 90 days — otherwise the new policy only bites after their next voluntary change. Verify with `passwd -S -a`.

### Q: What does an empty "Last password change" tell you about an account, and why do system accounts look like that?

An empty field 3 means no aging has ever been applied — `useradd -r` writes system accounts that way and the shadow man pages document that system users get no aging. Any future `chage -d` activates aging. Batch scripts that sweep "all users" into password policy therefore accidentally age out daemon accounts, which matters if anything ever does authenticate as them; exclude UID < UID_MIN.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/chage.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
