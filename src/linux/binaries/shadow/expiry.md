# expiry — check and enforce password expiration at login time

## Overview

`expiry` is the shadow suite's password-aging *enforcer*: it checks whether the invoking user's password has expired according to `/etc/shadow` and, depending on mode, forces the change conversation to happen right now. It ships in the `passwd` package (upstream shadow suite) at `/usr/bin/expiry` — setgid `shadow`, the privilege shape that says "needs to read the shadow file, not to write it". Root quality control is not its job; it is a hook for login shells, profile scripts, and cron, from an era when password aging had to be enforced *outside* the login program.

That placement is its whole story. Modern `login`, `sshd` (with PAM), and display managers run the equivalent checks themselves, so most users never invoke `expiry` by hand. It remains relevant in three places: minimal/embedded systems without PAM-aware login flows, `~/.profile`-based enforcement on bastion hosts, and cron-driven nag scripts. Interviewers reach for it when probing whether you understand *where* in the login chain password aging is enforced and what setgid-shadow implies.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 1 |
| Path | /usr/bin/expiry (setgid shadow) |
| First appeared | shadow suite original (1990s, shadow-utils lineage) |
| Standards | None (shadow-specific); not POSIX, not LSB |

## Synopsis

```
expiry [options]
```

Common one-line forms:

```
expiry            # force the change if the password is expired
expiry -c         # check only: exit 0 = fine, non-zero = expired
expiry -f         # force the change even in edge cases
```

Note the operand-free interface: there is no LOGIN argument. `expiry` always operates on the *invoking* user, which is what makes it safe to call from a profile script and what limits it to self-service.

## How It Works

### What it reads and decides

The decision uses the same shadow fields every aging tool shares:

```
shadow fields consumed by expiry
  field 3  last password change (days since epoch)
  field 5  max days before expiry        -> is 3 + 5 in the past?
  field 7  inactivity after expiry       -> has the rot grace also passed?
```

Decision flow:

```
read own shadow entry (setgid shadow)
        |
        v
entry has aging data? --no--> exit 0 (system accounts: never "expired")
        |yes
        v
today > lastchg + max (field 5)? --no--> exit 0 (healthy)
        |yes
        v
inactivity (field 7) also lapsed? --yes--> expired AND disabled:
        |no                                 root must reset (chage -I)
        v
-c mode? --yes--> exit 1, change nothing
        |no (default / -f)
        v
run the interactive change flow for self  -> new field 3 written on success
```

```
$ expiry -c ; echo "rc=$?"
rc=0                     # password not expired (this container's user z)

expired account, check mode:
$ expiry -c ; echo "rc=$?"
Your password has expired; choose a new password.   (or silent, rc=1)

expired account, force mode:
$ expiry
Your password has expired; choose a new password.
Changing password for z
(current) UNIX password:           <- the change flow, right here
New password: ...
```

Check mode (`-c`) is read-only and is the scriptable half: profile scripts and cron jobs branch on the exit code instead of parsing shadow files. Force mode (default and `-f`) runs the interactive password-change flow for the invoking user when the password is expired — it is, functionally, `passwd` with a gate in front.

### Why setgid shadow

`/etc/shadow` is mode 640 root:shadow. A non-root process that needs to know "has *my* password expired?" must read it, and shadow's answer for tools that only read (and never write) is setgid shadow rather than setuid root:

```
$ ls -l /usr/bin/chage /usr/bin/expiry /usr/bin/passwd
-rwxr-sr-x 1 root shadow 113848 ...  /usr/bin/chage
-rwxr-sr-x 1 root shadow  31256 ...  /usr/bin/expiry
-rwsr-xr-x 1 root root    70888 ...  /usr/bin/passwd
```

`chage` (read + write aging fields via setgid when self-service, or run as root) and `expiry` (read-only self check) take the group route; `passwd` and the editors take the root route because they must write. Explaining that split — least privilege between setuid-root and setgid-shadow — is the classic interview point hidden in this little binary.

### Where it fits in the login chain

```
login/sshd authentication
  |-> PAM account phase: checks account expiry, inactivity (pam_unix)
  |-> session opens, shell starts
  |-> password-expired? PAM-aware login forces the change itself
  |
  |  ... systems WITHOUT that enforcement (or as a belt-and-suspenders hook):
  |-> ~/.profile / /etc/profile.d/*.sh runs:
        expiry -c || expiry        # nag or force, shell-era style
  |
cron: daily `expiry -c` per-user mails are the historical nag pattern
```

On a modern Debian host the PAM path (pam_unix's account + password phases) already covers it, and `expiry` is dormant. The tool is the portable fallback for environments where login is not aging-aware: busybox-ish inits, restricted shell menus, su-driven workflows.

### The -c / -f pair

- `-c` (`--check`): evaluate only, exit code carries the verdict. No prompts, no writes, safe in non-interactive contexts (with the caveat that stderr/stdout still gets the expired-message).
- `-f` (`--force`): force the password change if expired — the man page wording — i.e. the same outcome as running bare `expiry`, provided for explicit scripting. Bare `expiry` without flags already behaves as "force if expired"; `-f` makes the intent legible.
- Neither mode can *un*-expire anything or touch other users: operand-free, self-only.

## Options That Matter

| Option | Effect |
| --- | --- |
| (no options) | force the password change if the invoking user's password is expired |
| -c | check only: report via exit status (0 = not expired) |
| -f | force the change if expired (explicit form of the default) |

## Usage Patterns

```bash
# Check whether your own password is expired (read-only)
expiry -c && echo "password fine" || echo "password expired"
```

```bash
# Bastion-host profile hook: force the change conversation at shell start
# /etc/profile.d/expiry-check.sh
if ! expiry -c; then
  expiry        # runs the change flow before the user gets a prompt
fi
```

```bash
# Cron-driven nag: weekly mail to users whose password is expired
# (root's crontab, iterating human accounts)
for u in $(awk -F: '$3 >= 1000 {print $1}' /etc/passwd); do
  su - "$u" -c 'expiry -c' >/dev/null 2>&1 || \
    echo "$u: password expired" | mail -s "expiry report" root
done
```

```bash
# Verify the privilege shape (setgid shadow, not setuid)
ls -l /usr/bin/expiry
```

```bash
# Simulate the aging state safely on a scratch user (root)
useradd -m -K PASS_MAX_DAYS=7 qa-test
passwd -d qa-test && passwd qa-test         # set something
chage -d 40 qa-test                          # pretend last change was 40 days ago
su - qa-test -c 'expiry -c; echo rc=$?'      # expired verdict
userdel -r qa-test
```

```bash
# Use it as the check inside a login-menu shell (kiosk/appliance pattern)
case "$(expiry -c 2>/dev/null; echo $?)" in
  0) exec /usr/bin/menu ;;      # healthy: straight to the menu
  *) expiry ;;                  # expired: change first, menu next login
esac
```

```bash
# Aging sweep report for the weekly security mail (root)
for u in $(awk -F: '$3 >= 1000 && $7 !~ /nologin|false/ {print $1}' /etc/passwd); do
  printf '%-12s ' "$u"
  su - "$u" -c 'expiry -c >/dev/null 2>&1' && echo OK || echo EXPIRED
done
```

```bash
# Confirm the check really is read-only: shadow mtime before and after
stat -c '%y' /etc/shadow; expiry -c; stat -c '%y' /etc/shadow
```

## Nuances and Gotchas

- **It is self-service only.** No LOGIN operand, no root "check that user" mode — use `chage -l USER` or `passwd -S USER` for that. Passing it extra arguments is a syntax error, not a target.
- **Exit codes are the API.** `-c` success/failure is the only machine-readable surface; output text is human-facing and has changed across shadow versions. Never parse the prose.
- **`expiry -c` on an *expired* account returns non-zero but changes nothing** — safe in check loops. Bare `expiry` in the same loop would try to start the interactive change flow and hang or fail in cron; that distinction is the #1 scripting mistake with this tool.
- **Cron environments are non-interactive.** The force-mode change flow needs a TTY; from cron it fails. Cron use is check-and-report, the change happens at a real login.
- **PAM renders it redundant on modern hosts.** pam_unix already refuses expired-password logins and forces the change; a profile-level `expiry` is redundancy, not a control. Its home ground is aging-unaware login paths.
- **setgid shadow must survive image hardening.** Stripping setgid/setuid bits ("chmod -R o-g /usr/bin" style sweeps) breaks `expiry` and `chage` for non-root users with permission errors, even though root keeps working.
- **Inactivity interplay:** once field 7 (inactivity) is also exceeded, the account is *disabled*, not merely expired — `expiry` reports expired, but the real fix is root-level (`chage -E -1 -I -1` or a password reset), not a self-service change.
- **It never considers `-x`/min-age.** Only the expired-or-not verdict; rotation policy details belong to chage/passwd.
- **Empty/missing shadow aging fields read as "never expires".** The same property that keeps system accounts immune also means a corrupted shadow line silently disables enforcement — audit with `chage -l` rather than trusting absence of complaints.
- **Watch the umask/TTY when embedding in profiles.** The forced-change flow expects a TTY; wrapping it in scripts that close stdin/stdout (or in `exec`-heavy login chains) turns it into an immediate failure rather than a dialog.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | password not expired (check mode verdict) |
| 1 | password expired |
| non-zero | invalid argument, or the shadow entry is unreadable/malformed |

Treat "expired" as a *diagnostic* exit, not an error: profile scripts branch on it by design.

## Related Commands

- [`chage`](./chage.md) — set and list the aging fields expiry reacts to.
- [`passwd`](./passwd.md) — the change flow expiry invokes; -e produces the expired state.
- [`usermod`](./usermod.md) — -f writes the inactivity grace period.
- [`useradd`](./useradd.md) — seeds the fields from login.defs at creation.
- [`chfn`](./chfn.md) / [`chsh`](./chsh.md) — the other self-service shadow tools.
- [`gpasswd`](./gpasswd.md) — group-side administration, same collection.
- [overview](./overview.md) — the shadow suite collection hub.
- [users-groups](../../admin/users-groups.md) — shadow file mechanics behind the verdict.

## Interview Questions

### Q: What is `expiry` for, and why does it still exist on modern PAM systems?

It enforces password aging *outside* the login program: a self-service check (`-c`) or forced change for the invoking user, reading `/etc/shadow` via setgid shadow. Modern PAM-aware login/sshd already force expired passwords to change, so on a standard Debian host expiry is dormant — but it remains the hook for aging-unaware login paths (minimal inits, menu shells, profile-script enforcement) and for check-only cron audits. It exists because aging enforcement used to be, and in places still is, a shell-era problem.

### Q: Why is expiry setgid shadow while passwd is setuid root?

Expiry only needs to *read* /etc/shadow (mode 640 root:shadow), so membership in the shadow group suffices — least privilege, no identity switch to root. passwd must *write* the hash through a PAM transaction, historically including file-level updates, so it takes setuid root. The pair demonstrates shadow's two privilege shapes: setgid-shadow for read-class operations (also chage), setuid-root for write-class ones (also chfn/chsh).

### Q: You put bare `expiry` into a user's crontab to auto-fix expired passwords. What goes wrong?

Force mode runs the interactive password-change flow, which needs a TTY and user input; cron has neither, so it fails (and depending on the PAM stack may lock things further). The correct cron pattern is `expiry -c` for detection plus notification; the change itself happens at the next real login, where PAM or a profile hook invokes the change flow.

### Q: What does `expiry -c` returning 1 actually tell you, and what does it NOT tell you?

That the invoking user's password is past its max-age expiry (fields 3 and 5 of their shadow entry). It does not tell you the account is disabled — that needs the inactivity field (7) or account expiry (8) to have also lapsed, which `chage -l` or `passwd -S` reveal. It also says nothing about lock state (`!` hash) or SSH-key access. Expiry answers exactly one question; the rest of the account state needs the other tools.

### Q: How would you safely simulate an expired password to test this flow?

Create a scratch user, set a password, then backdate the last-change field with `chage -d 40` (older than the account's max days, or pair with `chage -M 7`), then `su - user -c 'expiry -c'` and observe the exit code. Clean up with `userdel -r`. The chage backdating is the key trick — it manipulates the aging fields directly instead of waiting a week, and it demonstrates that expiry is purely a consumer of those fields.

### Q: Where in the login chain is password aging normally enforced on a modern Debian system, and what enforces it?

In PAM: the account phase (pam_unix) evaluates expiry/inactivity/account-expiry when the session is established, and the password phase forces the change conversation after successful authentication of an expired password. login, sshd, and display managers all consult the same stack. expiry duplicates the verdict for non-PAM or shell-level contexts. Answering with the PAM phases — not "expiry does it" — is the point of the question.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/expiry.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
