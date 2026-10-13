# passwd — change a user's password (self-service or as root)

## Overview

`passwd` is the password-changing front door of the shadow suite: as an ordinary user it changes *your own* password (after authenticating you with the current one), as root it changes anyone's, sets aging fields, locks and unlocks accounts, and reports password status. It ships in the `passwd` package (upstream shadow suite) at `/usr/bin/passwd` — setuid root, because writing `/etc/shadow` requires privilege. Its defining modern property is that it does **not** implement password changes itself: the work is delegated through PAM (`/etc/pam.d/passwd`), so complexity checks, history, and hashing live in PAM modules (typically `pam_unix` plus a quality-check module such as `pam_pwquality`).

It is often confused with three siblings: `chage` (which owns aging fields but cannot set a password), `usermod -p` (a raw hash-insertion tool, not a password changer), and the `passwd` *database* referred to by `getent passwd` — same word, different objects. There is also the historical `yppasswd`/`smbpasswd` family, which exist because PAM lets other backends plug into the same user experience.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 1 |
| Path | /usr/bin/passwd (setuid root) |
| First appeared | AT&T UNIX, early versions (1970s); shadow suite rewrite (1988+) |
| Standards | POSIX.1-2018 (User Portability); LSB |

## Synopsis

```
passwd [options] [LOGIN]
```

Common one-line forms:

```
passwd                       # change your own password
passwd alice                 # root: change alice's password (no old password asked)
passwd -S alice              # password status, one line
passwd -l alice              # lock the password
passwd -e alice              # expire: force change at next login
```

## How It Works

### Self-change vs root change

Two very different flows hide behind one binary:

```
ordinary user                root
  |                            |
  authenticate with            no authentication
  CURRENT password (PAM)       required at all
  |                            |
  PAM stack runs               PAM stack runs
  chauthtok: quality           (root bypasses policy
  checks, history rules        on complexity per config)
  |                            |
  write new hash               write new hash
  to /etc/shadow               to /etc/shadow
```

The authentication step is what makes `passwd` a security boundary rather than a database editor: a user cannot change someone else's password, and cannot change their own without proving the current one. Root skips the old-password question (that is the point of root) and, depending on PAM configuration, is also exempt from complexity rules — which is why "root set a weak password" works and why `passwd` as root is the standard first-login provisioning step.

The setuid bit does the privilege lifting for the non-root path; the shadow group membership of tools like `chage` shows the same idea implemented the other way (setgid shadow instead of setuid root).

### PAM pluggability

`man passwd`'s CAVEATS section is blunt: "passwd uses PAM to authenticate users and to change their passwords." Consequences worth internalizing:

- The password *policy* (length, classes, history, dictionary checks) comes from `/etc/pam.d/passwd` → usually `common-password` → modules like `pam_pwquality` and `pam_unix`. The binary has no complexity rules of its own.
- The *hash* algorithm comes from PAM/`pam_unix` configuration (`/etc/login.defs` `ENCRYPT_METHOD`, typically SHA512/`yescrypt` on modern Debian), not from a passwd flag.
- Backends are replaceable: point the stack at an LDAP/Kerberos module and `passwd` transparently changes directory or Kerberos credentials. NIS is the documented classic case — the man page notes users may not be able to change passwords when NIS is enabled and they are not on the NIS server.

### The shadow entry it edits

`passwd` writes fields 2 and 3 (and, with aging options, 4-7) of the nine-field shadow record:

```
alice:$y$5$...$hash:19900:0:99999:7:::
  |       |          |   |   |   |  | |
  |       |          |   |   |   |  | + field 9 reserved
  |       |          |   |   |   | + field 8 account expiry (-E via chage)
  |       |          |   |   | + field 7 inactivity (-i)
  |       |          |   | + field 6 warn days (-w)
  |       |          | + field 5 max days (-x)
  |       |          + field 4 min days (-n)
  |       + field 3 last change (days since epoch)
  + field 2 encrypted password
```

A leading `!` on field 2 means locked; `passwd -l` adds it, `-u` removes it, `-d` empties the field entirely (empty = passwordless login — a dangerous state, see Gotchas). `passwd -S` renders the same data as one line:

```
$ passwd -S z
z L 2026-09-21 0 99999 7 -1
  |     |        |  |    | |
  |     |        |  |    | + inactivity (-1 = disabled)
  |     |        |  + max days
  |     |        + min days
  |     + last change
  + P usable password / L locked / N no password
```

Non-root users may only run `-S` on themselves; reading someone else's shadow state is root business (the underlying file is mode 640 root:shadow).

### Lock, unlock, delete, expire

- `-l` / `-u`: the `!` prefix dance, identical in effect to `usermod -L`/`-U`. Locks only *password* authentication; SSH keys and running sessions are unaffected.
- `-d`: delete the password. The account becomes passwordless — legitimate for locked-down console-only appliances, catastrophic anywhere else. On many PAM stacks SSH refuses empty passwords (`PermitEmptyPasswords no`), which makes `-d` a trap: the account looks "open" locally and mysteriously still fails remotely.
- `-e`: expire the password immediately (sets field 3 to a past/zero state). The next login — console or SSH with a password — is forced through a change cycle. This is the standard "set initial password, force rotation at first login" pair: `passwd alice` as root, then `passwd -e alice`.
- `-n/-x/-w/-i`: min/max/warn/inactivity aging fields — a subset of `chage`'s vocabulary aimed at the same shadow fields. `passwd -x 90 -w 14 alice` is the root idiom for "90-day rotation, 14-day warning".

### Interplay with chage

`chage` and `passwd` overlap on four fields (min, max, warn, inactivity) and `chage -d 0` duplicates `passwd -e`. The division of labor: `passwd` sets *passwords* and a quick aging knob; `chage` *inspects* (`chage -l` has no passwd equivalent except the terse `-S`) and owns the full aging surface, including account expiry `-E`, which passwd has no flag for. If you remember one mapping: `passwd -e alice` == `chage -d 0 alice`; `passwd -i` == `chage -I`.

```
task                        passwd            chage              usermod
set the password            default action    -                  -p (raw hash)
force change at next login  -e                -d 0               -
min / max / warn / inactive -n -x -w -i       -m -M -W -I        -f (inactive only)
account expiry date         (none)            -E                 -e
list status                 -S (terse)        -l (verbose)       -
```

### The forced-change flow, end to end

What `-e` (or an aged-out password) actually looks like from both seats:

```
root:   passwd alice ; passwd -e alice
        (initial hash installed, field 3 zeroed/expired)

alice:  login: alice
        Password: *********              <- the initial secret still works
        You are required to change your password immediately (root enforced)
        New password: **************     <- PAM quality checks apply here
        Retype new password: **************
        passwd: password updated successfully
        ... session continues ...

shadow: field 3 rewritten to today; min/max/warn drive future prompts:
        - as field 3 + max approaches, login warns for `warn` days
        - past max, every login is a forced change (aging, not lockout)
        - past max + `inactive`, the account is disabled (field 7)
```

The distinction between *aging* (annoying but recoverable: forced change at next login) and *inactivity* (account auto-disabled: needs root to reset) is exactly what field 5 vs field 7 encodes, and the source of most "user can't log in" tickets on machines with strict `PASS_MAX_DAYS`.

## Options That Matter

| Option | Effect |
| --- | --- |
| (no args) | change your own password interactively |
| LOGIN | root: change that account's password |
| -S | one-line status: name, state, last change, aging fields |
| -a | with -S: status for all accounts (root) |
| -l / -u | lock / unlock the password (`!` prefix on the hash) |
| -d | delete the password (passwordless account) |
| -e | expire the password now; force change at next login |
| -n DAYS | minimum days between changes |
| -x DAYS | maximum days before a change is forced |
| -w DAYS | warning period before expiry |
| -i DAYS | inactivity: days after expiry until auto-disable (-1 = never) |
| -k | keep-tokens: only change when expired (Kerberos-flavored) |
| -R CHROOT_DIR | operate inside a chroot |
| -P PREFIX | use PREFIX/etc files without chrooting |

## Usage Patterns

```bash
# Change your own password (prompts for current, then twice for new)
passwd
```

```bash
# Root sets an initial password, then forces rotation at first login
passwd alice
passwd -e alice
```

```bash
# Check an account's password state before blaming sshd
passwd -S alice
# alice P 2026-09-01 0 99999 7 -1     P = usable password
```

```bash
# Quick lock when someone leaves (password side only - see usermod for the rest)
passwd -l contractor
passwd -S contractor
```

```bash
# Aging: 90-day max, 14-day warning, 3-day minimum between changes
passwd -x 90 -w 14 -n 3 alice
```

```bash
# Force a change at next login for every account with a stale password
for u in alice bob; do passwd -e "$u"; done
```

```bash
# Read all statuses at once (root) - spot locked or passwordless accounts
passwd -S -a | awk '$2 != "P" {print}'
```

```bash
# Expired-password flow seen from the user's seat
passwd
# Current password: ****
# You must change your password now (root enforced)   <- -e state
# New password: ****
```

```bash
# The PAM wiring behind it all (Debian)
cat /etc/pam.d/passwd
grep ENCRYPT_METHOD /etc/login.defs
```

```bash
# chrooted image maintenance: fix the root password of a mounted system
passwd -R /mnt/targetfs root
```

```bash
# Turn on inactivity: disable the account 30 days after its password expires
passwd -i 30 alice
passwd -S alice        # last field becomes 30 instead of -1
```

```bash
# Verify what the lock looks like in the raw file (root or shadow group)
sudo grep '^contractor:' /etc/shadow | cut -c1-12
# contractor:!$y$5$...
```

## Nuances and Gotchas

- **`passwd -d` creates a passwordless account.** Field 2 becomes empty; console logins drop straight in unless PAM forbids it. The only safe use is appliance/console accounts where you *want* no password, and even then `nologin` shells are usually better. Auditors flag empty password fields instantly.
- **`-l` does not stop SSH keys.** Same story as usermod -L: the lock prefixes the hash; `authorized_keys` keeps authenticating. Disabling an account is `-l` **plus** expiry (`chage -E 1`) **plus** key removal.
- **Policy lives in PAM, not passwd.** A "strong password" that passwd accepts on one host may be rejected on another with identical binaries but different `pam_pwquality` config. When debugging rejections, read `/etc/pam.d/common-password` first — the error text ("passwd: Authentication token manipulation error") never names the module.
- **Root bypasses the old-password check but not necessarily the quality check** — pam_unix is usually configured with `nullok`-ish root behavior, but quality modules vary. Don't promise in scripts that root-set passwords will always pass policy.
- **`-S` date format and fields.** The status line is name, state, last-change date, min, max, warn, inactive. `L` can mean locked *or* "no usable password"; distinguish with the raw shadow field (`!` prefix vs empty) as root.
- **`-e` vs `-d` confusion.** `-e` forces a change (safe, standard provisioning); `-d` removes the password entirely (rarely what you meant). One character apart, opposite security outcomes.
- **NIS/remote backends change everything.** The man page warns that NIS users on non-servers cannot change passwords; with LDAP, "passwd changed the password" may mean "the directory changed it" — replica lag can make new passwords fail on other hosts for a while.
- **`-k keep-tokens`** only matters with Kerberos-style backends; on a plain pam_unix box it is a no-op and its presence in a script usually signals copied cargo cult.
- **Very recent shadow added `-s/--stdin`** (feed the new token programmatically); bookworm's passwd does not have it — the portable scripted route is `chpasswd`.
- **The setuid design is load-bearing.** `passwd` works for ordinary users because of setuid root plus PAM; if you `chmod u-s /usr/bin/passwd`, self-service changes break with cryptic PAM errors. File-permission checks belong in the troubleshooting flow.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | permission denied (wrong current password, non-root touching another user) |
| 2 | invalid combination of options |
| 3 | unexpected failure, nothing done |
| 4 | unexpected failure, password file missing |
| 5 | password file busy, try again (lock contention) |
| 6 | invalid argument to option |

Code 1 doubles as "authentication failed", which in PAM terms can be a policy rejection rather than a wrong old password — read stderr, not just the code.

## Related Commands

- [`chage`](./chage.md) — the full aging surface: listing, account expiry, same shadow fields.
- [`usermod`](./usermod.md) -L/-U/-p — database-level lock and hash insertion without PAM.
- [`useradd`](./useradd.md) — creates the `!`-locked entry that passwd unlocks.
- [`userdel`](./userdel.md) — the removal end of the account lifecycle.
- [`chfn`](./chfn.md) / [`chsh`](./chsh.md) — the other setuid self-service tools (GECOS and shell).
- [`expiry`](./expiry.md) — login-time enforcement of the expiration state passwd -e sets.
- [`gpasswd`](./gpasswd.md) — the group-password analog of this tool.
- [overview](./overview.md) — the shadow suite collection hub.
- [users-groups](../../admin/users-groups.md) — /etc/shadow anatomy and authentication flow in depth.

## Interview Questions

### Q: A user reports "passwd: Authentication token manipulation error". Walk through the diagnosis.

The message is PAM's generic failure, so the binary is fine and something in the stack failed: wrong current password, shadow file immutable/readonly (`chattr +i` on /etc/shadow is a classic), full disk (`pwck`, `df`), a broken `/etc/pam.d/passwd` or common-password module, or LDAP down. Check `/var/log/auth.log` for the module that actually refused, verify shadow writability and locks, and re-run with `passwd --debug`-style tracing if available. The point is knowing the error is not descriptive and the trail leads through PAM logs.

### Q: Explain exactly what `passwd -l` does and name two ways it fails to "disable" an account.

It prepends `!` to the crypt hash in field 2 of `/etc/shadow`, so no password can match. It fails to disable the account in that SSH public keys still authenticate (sshd ignores the hash when keys are offered), and running sessions/cron are unaffected. Real disablement combines `-l` with account expiry (`chage -E 1` or `usermod -e 1`) and removal of authorized keys.

### Q: What is the difference between `passwd -d` and `passwd -e`?

`-d` deletes the hash: the account becomes passwordless (empty field 2), letting console logins through with a bare Enter on permissive PAM. `-e` expires the *current* password: the next login still requires the old password and then forces a new one. Provisioning uses `-e` after root sets an initial secret; `-d` is for deliberate no-password appliances and is otherwise a finding.

### Q: Where does password complexity checking actually live, and how do you change it?

In the PAM stack, not in the passwd binary. `/etc/pam.d/passwd` includes `common-password`, which loads `pam_pwquality` (minlen, dcredit, dictcheck...) and `pam_unix` (hashing via login.defs `ENCRYPT_METHOD`). Change policy in `/etc/security/pwquality.conf` and the include files; the binary stays untouched. This pluggability is the reason the same `passwd` command serves local files, LDAP, or Kerberos depending on configuration.

### Q: What does `passwd -S` output mean, field by field?

Name; state (P usable, L locked/no usable password, N none); date of last change (YYYY-MM-DD in modern shadow, days-since-epoch in older); then min, max, warn, inactive — the four aging numbers from shadow fields 4-7, with -1 meaning disabled. It is the one-line audit tool: `passwd -S -a` as root sweeps the whole account base for locked (L) or passwordless entries.

### Q: Why can root change a password without knowing the old one, and what are the security implications?

Root skips the authentication half of the PAM chauthtok transaction (the current-password prompt exists to protect the user from others, not root from anyone), and complexity policy is commonly relaxed for root so provisioning can install initial secrets. Implications: anyone with root already owns the account, so no boundary is crossed; but scripts passing secrets to `passwd` as argv leak them to `ps`, so use `chpasswd`/stdin or `openssl passwd -6` + `usermod -p` carefully, and audit `history` hygiene.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/passwd.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
