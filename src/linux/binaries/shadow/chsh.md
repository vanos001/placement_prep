# chsh — change your login shell

## Overview

`chsh` changes the login-shell field (field 7) of a user's `/etc/passwd` entry. As an ordinary user it changes your own shell — after PAM authentication and only if the requested shell is listed in `/etc/shells`; root changes anyone's shell to anything. It ships in the `passwd` package (upstream shadow suite) at `/usr/bin/chsh`, setuid root like its self-service siblings `passwd` and `chfn`.

The interesting part of `chsh` is not the one-line edit — it is the *gate*: `/etc/shells` exists precisely because a login shell is an executable a user is being allowed to choose. The file is consulted by `chsh` itself, by `usermod`/`useradd` validation on some configurations, and historically by FTP daemons deciding whether an account may log in. Understanding why that list exists and who reads it is the actual interview content around this small tool.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 1 |
| Path | /usr/bin/chsh (setuid root) |
| First appeared | BSD heritage; shadow suite rewrite (1988+) |
| Standards | POSIX.1-2018 (User Portability, optional); LSB |

## Synopsis

```
chsh [options] [LOGIN]
```

Common one-line forms:

```
chsh                    # interactive: prompts for the new shell
chsh -s /bin/zsh        # non-interactive, self
chsh -s /usr/sbin/nologin alice   # root: lock out interactive logins
chsh -s /usr/bin/rbash dev1      # root: hand a restricted shell to a user
```

## How It Works

### The /etc/shells gate

For a non-root invocation, the requested shell must appear in `/etc/shells`:

```
$ cat /etc/shells
# /etc/shells: valid login shells
/bin/sh
/usr/bin/sh
/bin/bash
/usr/bin/bash
/bin/rbash
/usr/bin/rbash
/usr/bin/dash
```

Rules around the gate:

- the entry must match exactly (absolute path, no arguments, no `~` tricks);
- root is exempt — root may set any path, valid or nonsense, for any account;
- if `/etc/shells` is missing entirely, the man page documents the fallback of accepting only standard shells (`/bin/sh`, `/bin/csh` lineage);
- the gate applies at *chsh time*, not at login time: a shell removed from `/etc/shells` after being set keeps working until something changes it again.

Why the gate at all? A login shell is spawned by `login`/`sshd` as the account's program. Letting users pick arbitrary binaries means letting them pick setuid games, debuggers, or interpreters with odd file-descriptor behavior — a footgun on multi-user systems. `/etc/shells` is also read by FTP daemons (classic `ftpd` refused accounts whose shell was not listed) and by `useradd`-adjacent tooling as the "known good shells" notion. Modern equivalents: `pam_shells` enforces the same list as a PAM module, which is how telnet/rlogin-era checks survive into PAM.

### The transaction

```
user runs chsh -s /usr/bin/zsh
  |-> PAM authentication (current password; root skips)
  |-> non-root: verify /usr/bin/zsh is in /etc/shells
  |-> lock /etc/passwd
  |-> rewrite field 7 of the user's line
  |-> unlock; effective at NEXT login (running shells unaffected)
```

Verified refusal path on this container (PAM prompt closed early):

```
$ chsh -s /bin/bash
Password: <eof>
chsh: PAM: Authentication failure        (exit 1)
```

The current session keeps its old shell; `exec $NEW_SHELL` is the immediate-apply trick.

### Who consumes field 7

```
reader                       behavior
login / sshd (via PAM+shell) exec the field as the session program
su - USER                    runs the target's login shell
cron / at / systemd user     service user's shell for command interpretation
getent-based audits          field 7 is how "interactive account" is classified
FTP daemons / pam_shells     refuse accounts whose shell is not in /etc/shells
```

Note the last two rows: the shell field is read for *policy*, not only execution. That is why an invalid or exotic shell can break subsystems that never spawn it — they just pattern-match the field.

### nologin, false, and friends as "shells"

`/usr/sbin/nologin` and `/bin/false` are ordinary executables commonly *set* as shells to make an account non-interactive:

```
$ getent passwd daemon
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
```

The distinction that matters: `nologin` prints a polite refusal ("This account is currently not available") and exits; `false` exits silently with status 1. Both block interactive logins. Neither is in `/etc/shells` — deliberately, so a *user* cannot chsh themselves to them, but root can set them freely. Compare with `passwd -l` (locks the password but keys/cron still work): a `nologin` shell blocks the interactive path regardless of authentication method, which is why service accounts get both.

`rbash` (restricted bash) is the flip side: in `/etc/shells` so that it *can* be granted, and root assigns it when a user should have a sandboxed interactive environment — with the standing caveat that rbash is escapable if PATH contains writable directories early.

### Debian vs elsewhere

BSD `chsh` has a `-l` option to list `/etc/shells`; Debian's shadow chsh does not (use `cat /etc/shells` or `getent`… there is no listing flag here). util-linux's `chsh` (present on some distros as an alternative implementation) also honors `/etc/shells` but has a different flag surface — a portability wrinkle when the same box hosts both toolkits. On Debian, `/usr/bin/chsh` is the shadow one.

## Options That Matter

| Option | Effect |
| --- | --- |
| -s SHELL | set the login shell (validated against /etc/shells unless root) |
| -R CHROOT_DIR | operate inside a chroot |
| -P PREFIX | use PREFIX/etc files without chrooting |

That is the entire interface. Flagless mode is the interactive prompt (current shell shown as default). The narrowness is the design: no listing flag, no bulk mode, no field editing beyond the shell.

## Usage Patterns

```bash
# Interactive self-service change
chsh
# Changing the login shell for z
# Enter the new value, or press return for the default
#       Login Shell [/bin/bash]: /bin/zsh
```

```bash
# Direct, non-interactive (your own account)
chsh -s /usr/bin/zsh
```

```bash
# See what you are allowed to pick, then verify the result
cat /etc/shells
getent passwd "$(whoami)" | cut -d: -f7
```

```bash
# Root disables interactive logins for a service account (standard practice)
chsh -s /usr/sbin/nologin svc-backup
su - svc-backup -c id     # demo the refusal message
```

```bash
# Harder variant: silent refusal (no message, pure exit 1)
chsh -s /bin/false svc-old
```

```bash
# Root grants a restricted shell to a semi-trusted user
chsh -s /usr/bin/rbash trainee
# and pre-set a read-only PATH/skelfiles: rbash blocks cd/PATH changes at runtime
```

```bash
# Root sets an exotic shell by fiat (bypasses /etc/shells)
chsh -s /usr/local/bin/fish alice
```

```bash
# Apply the new shell immediately without logging out
chsh -s /usr/bin/zsh && exec /usr/bin/zsh -l
```

```bash
# Audit every account with an interactive-capable shell
getent passwd | awk -F: '$7 !~ /nologin|false/ && $3 >= 1000 {print $1, $7}'
```

```bash
# Fix a user's shell inside a mounted image during recovery
chsh -R /mnt/rootfs -s /bin/bash rescueuser
```

```bash
# Find accounts whose shell vanished (binary deleted or image changed)
while IFS=: read -r u _ _ _ _ _ sh; do
  [ -x "$sh" ] || echo "BROKEN SHELL: $u -> $sh"
done < <(getent passwd)
```

```bash
# One-off self check of what you would be allowed to choose
comm -13 <(ls /usr/bin/bash /usr/bin/zsh 2>/dev/null | sort) <(sort /etc/shells) 2>/dev/null
```

## Nuances and Gotchas

- **The check is exact-string membership.** `/bin/bash` and `/usr/bin/bash` are distinct lines; a request for an unlisted but valid path fails with "chsh: Invalid entry: ... /etc/shells" style errors until the file lists it. Adding a shell to `/etc/shells` is a one-line file edit and instantly widens user choice.
- **Root bypasses the gate — including into nonsense.** `chsh -s /nonexistent` as root succeeds and creates an account that cannot log in (sshd/login fail to exec). Recovery is the same command with a real path, or editing via `vipw` in a rescue environment.
- **Changing the shell does not affect running sessions.** Only the next login picks it up; scripts that `chsh` then expect new behavior in the current session need `exec`.
- **`nologin`/`false` are absent from /etc/shells on purpose.** They are disable-verbs, not choices; users cannot self-select them, root can. Some sites *do* list them, which removes that asymmetry — check the file before reasoning about policy.
- **The gate protects chsh-time choice, not login-time execution.** `/etc/shells` does not stop root-assigned shells, does not re-validate at login, and says nothing about `Exec=` in display managers. It is a narrow, historical, still-useful control.
- **FTP-era readers still exist.** Any daemon with `pam_shells` or homegrown `/etc/shells` checks treats an unlisted shell as "no service for this account" — a reason an unlisted-but-valid shell can break FTP-era tooling even though SSH works.
- **Two chsh implementations exist in the wild** (shadow vs util-linux on some distros). Flag behavior and PAM wording differ; Debian bookworm ships the shadow one in `passwd`.
- **Setuid dependency**: like passwd/chfn, self-service depends on the setuid bit surviving image hardening scripts; stripped setuid yields authentication-free failures.
- **NIS/LDAP users**: local-file tool again; directory-served shells change in the directory, not in `/etc/passwd`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | permission denied (PAM auth failure, shell not in /etc/shells, non-root on another account) |
| 2 | invalid command syntax |
| 3 | invalid argument to option |

As with chfn, most real-world non-zero exits are the permission-denied family; the shell-not-listed case is the one worth reading stderr for.

## Related Commands

- [`chfn`](./chfn.md) — the sibling self-service editor for the GECOS field.
- [`passwd`](./passwd.md) — the self-service pattern's original: setuid + PAM.
- [`usermod`](./usermod.md) — admin-side shell change (`-s`) with no /etc/shells gate as root.
- [`useradd`](./useradd.md) — `-s` seeds the field; SHELL= in /etc/default/useradd is the default.
- [`chage`](./chage.md) — self-service aging view in the same collection.
- [`gpasswd`](./gpasswd.md) / [`expiry`](./expiry.md) — group administration and login-time expiry enforcement.
- [overview](./overview.md) — the shadow suite collection hub.
- [users-groups](../../admin/users-groups.md) — the passwd field layout and login chain.

## Interview Questions

### Q: What is /etc/shells for, and who reads it?

It is the whitelist of acceptable login shells. chsh enforces it for non-root changes; PAM's `pam_shells` and historical FTP daemons read it to decide whether an account gets service; and it doubles as documentation of what the system considers a valid shell. The design intent is that users may not make arbitrary executables their login program on a shared machine.

### Q: What is the difference between locking an account with `passwd -l`, and setting its shell to /usr/sbin/nologin?

`passwd -l` prefixes the password hash, blocking *password* authentication only — SSH keys, cron, and running sessions continue. A `nologin` shell blocks the interactive login path itself regardless of how authentication would succeed (keys included), and prints a refusal message. Real disablement uses both, plus account expiry; service accounts typically ship with a locked password *and* a nologin shell from birth.

### Q: Why can root set a shell that is not in /etc/shells, and what is the risk?

The gate exists to constrain *user choice*, not root authority; root already owns the system and may need to set recovery or experimental shells (or precisely `nologin`/`false`, which are intentionally absent from the list). The risk is typing: root can install a nonexistent path, and the account silently loses the ability to log in until it is fixed. Double-check with `getent passwd USER | cut -d: -f7` after any root chsh.

### Q: A user ran `chsh -s /usr/local/bin/myshell` and got an invalid-entry error, but the file exists and is executable. Why?

`/etc/shells` gates non-root requests by exact string match, and `/usr/local/bin/myshell` is not listed. The fix is either root performs the change (bypassing the gate) or the administrator adds the path to `/etc/shells` — which is a policy decision, since it makes that shell selectable by every user of the host.

### Q: Does changing your login shell affect your current session? How do you apply it immediately?

No — the change is a database edit read at login time; running processes keep their existing shell. Immediate application is `exec <newshell> -l` in the current session, which replaces the shell process itself. Worth knowing because provisioning scripts that chsh mid-login-session otherwise appear broken.

### Q: Where does rbash fit into this, and what is its standing caveat?

`rbash` (restricted bash) appears in Debian's `/etc/shells`, so root can `chsh -s /usr/bin/rbash user` to hand out a restricted environment: it forbids changing PATH, `cd`ing, invoking commands with absolute paths outside PATH, and redirecting output. The caveat: restriction depends on startup setup — if the user can run arbitrary binaries that reset restrictions or PATH is writable early, rbash is escapable. It is a convenience fence, not a security boundary; containers and jailing via PAM/systemd are the serious tools.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/chsh.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
