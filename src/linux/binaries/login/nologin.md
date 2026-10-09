# nologin — politely refuse a login

## Overview

`/usr/sbin/nologin` is a shell that exists to say no. Placed in an account's shell field in `/etc/passwd`, it prints a message that the account is not available and exits with status 1 — nothing else. It is the standard way to keep system accounts (`daemon`, `bin`, `sshd`, service users) from being used interactively while keeping them otherwise functional. On Debian it ships in the `login` binary package; through bookworm that was the shadow implementation, and since trixie the package is built from util-linux (`nologin` appeared in 4.4BSD, and the util-linux man page still documents that lineage).

The page has to cover **two unrelated things that share a name**, and interviewers love the distinction:

- `/usr/sbin/nologin` — the *program*: a per-account refusal shell, exit status always 1, message from `/etc/nologin.txt` if present.
- `/etc/nologin` — the *file*: while it exists, the PAM module `pam_nologin` refuses all non-root logins to the machine (maintenance mode) and shows the file's contents; root still gets in.

A third near-miss is `/bin/false`, which exits 1 *silently* — same denial, zero explanation for the user staring at a dead terminal.

| Field | Value |
| --- | --- |
| Package | login (Debian; built from source package `util-linux` on trixie, from `shadow` on bookworm) |
| Man section | 8 |
| Path | /usr/sbin/nologin (historic /sbin/nologin) |
| First appeared | 4.4BSD |
| Standards | Not POSIX; a Unix convention honored by account tooling and /etc/shells consumers |

## Synopsis

```
nologin [-V] [-h]
```

It also *accepts and ignores* common shell options (`-c`, `-i`, `-l`, `-r`, `--noprofile`, `--norc`, `--posix`, `--rcfile`, `--init-file`) so that callers like sshd — which exec `shell -c command` — get a clean refusal instead of an option error.

Common one-line forms:

```
nologin            # print refusal message, exit 1
usermod -s /usr/sbin/nologin svc   # the usual way to install it
```

## How It Works

### The refusal, demonstrated

```bash
$ nologin; echo "exit=$?"
This account is currently not available.
exit=1
```

The message goes to stderr, the exit status is always 1 (documented in the man page), and no child process is ever started. Compare the silent twin from coreutils:

```bash
$ /bin/false; echo "exit=$?"
exit=1
```

An SSH user whose shell is `nologin` authenticates fine and then sees the message before the connection closes; with `/bin/false` the connection just closes. That diagnostic difference is the entire reason to prefer `nologin` for accounts a human might touch.

### Custom message

If `/etc/nologin.txt` exists, its contents are shown instead of the default:

```bash
$ echo "Host is under maintenance until 18:00" | sudo tee /etc/nologin.txt
# the refused user now sees that text instead of "This account is ..."
```

The file changes the *message only* — access is refused regardless.

### Why the ignored shell options matter

sshd runs the user's shell as `shell -c command` for remote commands and as `shell` for interactive sessions. A program that rejected unknown options would make `ssh service@host cmd` fail with an *option-parsing error* before printing anything. The util-linux man page lists the accepted-and-ignored set explicitly (`-c`, `-i`, `-l`, `-r`, `--noprofile`, `--norc`, `--posix`, `--rcfile`, `--init-file`), so the refusal is always clean:

```bash
$ nologin -c "uptime"; echo "exit=$?"
This account is currently not available.
exit=1
```

### The name collision: /etc/nologin, the gate file

```
 ┌──────────────────────┬───────────────────────────────────────────────┐
 │ /usr/sbin/nologin    │ shell: denies ONE account, always exit 1      │
 │ /etc/nologin.txt     │ file: custom message for nologin(8)           │
 │ /etc/nologin         │ file: pam_nologin gate — ALL non-root logins  │
 │ /var/run/nologin     │ file: alternate gate path (tmpfs)             │
 └──────────────────────┴───────────────────────────────────────────────┘
```

`pam_nologin` sits in the `auth` phase of the login stack (Debian marks it `requisite`):

```bash
$ grep -n pam_nologin /etc/pam.d/login
17:auth       requisite  pam_nologin.so
```

While `/etc/nologin` (or `/var/run/nologin`) exists, non-root authentication fails with the file's contents shown; root passes. The file is checked by PAM at *authentication* time, which is why it also affects sshd on stacks that include `pam_nologin` — and why it is the right tool for maintenance windows, unlike editing shells one account at a time.

### Where nologin shells already live

```bash
$ getent passwd | awk -F: '$7=="/usr/sbin/nologin"' | head -3
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
```

Every stock Debian/Ubuntu system has dozens of such accounts. They still run cron jobs and systemd services, because those mechanisms execute commands through `/bin/sh` and sudo-like tools — the login shell is only consulted by *login-session* machinery.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-h`, `--help` | Usage. |
| `-V`, `--version` | Version. |
| *(no options)* | Print refusal (default message, or /etc/nologin.txt), exit 1. |
| shell-style flags | `-c`, `-l`, `-i`, `-r`, `--noprofile`, `--norc`, `--posix`, `--rcfile`, `--init-file` are accepted and ignored, so `shell -c cmd` invocations fail cleanly. |

## Usage Patterns

```bash
# 1. Turn off interactive access for an existing service account
$ sudo usermod -s /usr/sbin/nologin buildbot
```

```bash
# 2. Create a locked-down system account from scratch
$ sudo useradd -r -s /usr/sbin/nologin svc-backup
```

```bash
# 3. Inventory accounts that cannot log in (and spot wrong paths)
$ getent passwd | awk -F: '$7 ~ /nologin/ {print $1, $7}' | head -3
daemon /usr/sbin/nologin
bin /usr/sbin/nologin
sys /usr/sbin/nologin
```

```bash
# 4. Custom refusal message for a planned migration window
$ echo "buildbot is retired; see wiki/BuildbotMigration" | sudo tee /etc/nologin.txt
```

```bash
# 5. Verify a user's shell without guessing
$ getent passwd ann | cut -d: -f7
/bin/bash
```

```bash
# 6. Restore access
$ sudo usermod -s /bin/bash ann
```

```bash
# 7. Whole-machine maintenance gate (root exempt, message shown to users)
$ sudo touch /etc/nologin
$ sudo rm -f /etc/nologin
```

```bash
# 8. chsh interplay: nologin is not a valid interactive shell for mortals
$ grep nologin /etc/shells || echo "not listed in /etc/shells"
not listed in /etc/shells
```

```bash
# 9. What a refused SSH user experiences (message appears, then the session closes)
$ ssh buildbot@lab-1
This account is currently not available.
Connection to lab-1 closed.
```

```bash
# 10. Jobs still run for nologin accounts — check, don't assume
$ sudo crontab -u svc-backup -l
```

## Nuances and Gotchas

- **The typo trap**: `usermod -s /etc/nologin` puts the *file* into the shell field. The field must be the binary `/usr/sbin/nologin`. A missing/unexecutable shell field makes sshd refuse the session with a different error, which confuses everyone.
- **`nologin` vs `/bin/false`**: both exit 1; only `nologin` explains. Prefer it for any account a human might reach; `false` is fine for pure plumbing accounts.
- **It does not stop scheduled work.** cron, systemd timers/services, and `sudo -u` / `setpriv` execution all bypass the login shell. If the goal is "account can run nothing", you need password+key locking (`passwd -l`/`usermod -L` plus removing authorized_keys) or a policy engine — not a shell swap.
- **`/etc/shells` interplay**: Debian does not list `nologin` there, so FTP daemons and `chsh` (for unprivileged users) treat it as invalid. Root setting the shell with `usermod` is unaffected; that asymmetry is by design.
- **`/etc/nologin` (gate) applies at PAM auth time and is root-exempt**; forgetting to remove it after maintenance is a classic "nobody can SSH in" ticket. `/run/nologin` is the tmpfs twin that vanishes on reboot.
- **Implementation drift**: bookworm's shadow nologin and trixie's util-linux nologin agree on the default message text and exit 1, but the ignored-flags list and `-V` support are util-linux-era features; very old systems also install it as `/sbin/nologin`.
- **BusyBox systems** (Alpine) ship `/sbin/nologin` as a built-in applet: same idea, different message, no `/etc/nologin.txt` support — don't assume the message file exists.
- **Messages leak intent.** `/etc/nologin.txt` contents are shown to anyone attempting to log in, including attackers; keep maintenance notes bland and factual.

## Exit Status

- Always **1** — documented as such in the man page and reproducible locally.
- The status is not configurable and does not depend on whether a message file was found.

## Related Commands

- [`login`](./login.md) — the session-entry program whose PAM stack consults both nologin mechanisms.
- [`sulogin`](./sulogin.md) — the opposite end of the spectrum: a root-only maintenance shell.
- [`newgrp`](./newgrp.md) — the other "shell that swaps identity" in this collection, for groups.
- [Overview — the login collection](./overview.md) — session-entry tools at a glance.
- [Users and groups](../../admin/users-groups.md) — the passwd/shell field, /etc/shells, and account-locking mechanics.

## Interview Questions

### Q: A service account has /usr/sbin/nologin. Will its cron job still run?

Yes. Cron (and systemd) execute scheduled commands through `/bin/sh` (or `SHELL=` from the crontab/unit) and never consult the account's login shell. `nologin` only blocks *login sessions* — ssh, console, su. Candidates who think nologin disables the account entirely usually conflate it with password/key locking.

### Q: How do you deny a single user, deny all non-root users, and explain a denial — three different goals?

Single user: set the shell to `/usr/sbin/nologin` (`usermod -s`). All non-root: `touch /etc/nologin` — `pam_nologin` gates every login stack that includes it, root exempt. Explanation: `nologin` prints its message (customizable via `/etc/nologin.txt`) while `/bin/false` exits silently. Three mechanisms, one shared name, exactly the confusion this page exists to fix.

### Q: Why does sshd show "This account is currently not available." for one account but closes silently for another?

The first shell is `nologin`, which prints its message to stderr before exiting 1 — sshd relays it and then closes the session. The second is `/bin/false`, which produces no output, so the client just reports a closed connection. Diagnostic takeaway: prefer `nologin` on any account a human might accidentally target, and check the shell field (`getent passwd user`) when SSH "authenticates but drops".

### Q: What breaks if you replace /usr/sbin/nologin with a script that logs refusal attempts?

Plenty, in order of likelihood: sshd requires the shell to be a real executable (it checks and execs it directly — a script can work but adds interpreter dependency at session time), FTP daemons compare the shell against `/etc/shells`, and a typo in the field turns every refusal into "shell does not exist" errors. If you need logging, PAM already records denials and `lastb` reads btmp; keep the stock binary.

### Q: Where does the "account is not available" text come from, and how do you change it?

From `/usr/sbin/nologin` itself: if `/etc/nologin.txt` exists its contents are displayed, otherwise a compiled-in default ("This account is currently not available."). Access is refused regardless of the file. The similar-looking `/etc/nologin` *file* has nothing to do with this message — it is the pam_nologin maintenance gate.

### Q: `usermod -L` and `nologin` both "disable" an account — what's the difference?

`usermod -L` prepends `!` to the shadow hash: password authentication fails, but key-based SSH still works (sshd checks the shell and authorized_keys, not the hash, when keys are used). `nologin` allows authentication to succeed and then refuses the session — including key-based ones. Full disablement needs both, plus removal of authorized_keys/cron; that layered answer is what interviewers are fishing for.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/login/nologin.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
