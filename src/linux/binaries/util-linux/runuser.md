# runuser — run a command as another user, without authentication (root only)

## Overview

`runuser` runs a command with the user and group IDs of another account.
It is `su(1)` minus the interactive ceremony: it never prompts for a
password, can only be invoked by root, and is designed for non-interactive
callers such as init scripts, cron jobs and service wrappers
(`runuser -u www-data -- php-fpm -F`). It ships with the `util-linux`
package (Debian bookworm) at `/usr/sbin/runuser`.

`runuser` is often confused with `su` (anyone may call it; it performs
PAM *authentication* and may prompt), with `sudo` (a policy engine with
per-command grants and logging), and with `setpriv` (a raw syscall-level
wrapper with no PAM, no shell and no user-database semantics).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/sbin/runuser |
| First appeared / lineage | util-linux addition of the 2010s, modeled on su |
| Standards | None — Linux-specific |

## Synopsis

```
runuser [options] -u <user> [[--] <command> [<argument>...]]
runuser [options] [-] [<user> [<argument>...]]
```

Common one-line forms:

```
runuser -u www-data -- ls /var/www       # execute one command
runuser postgres -c 'pg_ctl status'      # shell -c form
runuser - alice                          # login shell as alice
runuser -u backup -- mysqldump db        # typical script use
```

## How It Works

### Identity switch without authentication

`runuser` assumes the caller is root and *skips the authentication stack
entirely*. Called by anyone else it refuses immediately:

```bash
$ runuser -u nobody true
runuser: may not be used by non-root users
$ echo $?
1
```

Under the hood it performs the same sequence a root shell would: resolve
the target account in the user/group databases, set supplementary groups
and the real/effective GID and UID (`setgroups`, `setresgid`,
`setresuid`), then either `execvp` the command directly (with `-u`) or
start the target's shell (with `-c` or no command).

### PAM: no auth stack, but the session stack runs

Even though no password is checked, `runuser` is PAM-aware. It opens a
PAM session with the service name `runuser` (or `runuser-l` for login
shells), which on Debian bookworm runs exactly these modules from
`/etc/pam.d/runuser`:

```
#%PAM-1.0
auth            sufficient      pam_rootok.so
session         optional        pam_keyinit.so revoke
session         required        pam_limits.so
session         required        pam_unix.so
```

The single `auth` line is `pam_rootok.so` — "succeed if the caller's real
UID is 0" — which is the formal statement that no credentials are ever
collected. The `session` lines matter in practice: `pam_limits.so` applies
`/etc/security/limits.conf` for the *target* user, and `pam_keyinit`
rebuilds the kernel session keyring. So `ulimit`/limits behavior differs
from a bare `setpriv` drop.

### Environment handling

Default (non-login) invocation preserves the caller's environment except
that `HOME`, `SHELL`, `USER` and `LOGNAME` are set to the target account.
`runuser - user` (login mode) additionally clears the environment to a
minimal set, changes to the target's home directory and starts a login
shell. `-m/-p` preserves more of the environment; `-w LIST` keeps named
variables through a login-style reset.

```
caller (root) ── runuser ──► PAM session (limits, keyring)
                     │
                     ├─ setgroups() + setresgid() + setresuid()
                     │
                     ├─ -u form:  execvp(command)          [no shell]
                     └─ else:     exec $SHELL [-c command] [login flags]
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-u, --user <user>` | Target user for the direct-command form; mutually exclusive with `-c`, `-f`, `-l`, `-s`. |
| `-c, --command <cmd>` | Pass one command string to the target's shell via `-c`. |
| `--session-command <cmd>` | Same as `-c`, but no new session is created (keeps session bookkeeping of the caller). |
| `-, -l, --login` | Login shell: cleared environment, chdir to target home. |
| `-g, --group <group>` | Override the primary group instead of the target's default. |
| `-G, --supp-group <group>` | Add a supplementary group (repeatable). |
| `-m, -p, --preserve-environment` | Keep the caller's environment variables. |
| `-w, --whitelist-environment <list>` | Comma-separated variables kept even in a reset environment. |
| `-s, --shell <shell>` | Run this shell instead of the target's passwd shell. |
| `-P, --pty` | Allocate a fresh pseudo-terminal for the child. |

## Usage Patterns

```bash
# Run one command as a service account, with no shell involved (root)
runuser -u www-data -- ls -l /var/www
```

```bash
# Shell -c form: quoting is done by the target's shell
runuser postgres -c 'pg_ctl status -D /var/lib/postgresql/data'
```

```bash
# Login-style environment, e.g. to test a user's real dotfiles
runuser - alice -c 'echo $PATH; ulimit -n'
```

```bash
# Database dumps from cron as the database user
runuser -u postgres -- pg_dump mydb > /backups/mydb.sql
```

```bash
# Apply the target's limits from /etc/security/limits.conf (via pam_limits)
runuser - jenkins -c 'ulimit -a'
```

```bash
# Override the primary group, e.g. write with a project group identity
runuser -u deploy -g www-data -- touch /srv/site/index.html
```

```bash
# Keep locale variables through the environment reset
runuser -w LANG,LC_ALL -u user -- date
```

```bash
# Init-script style: same command but no new session record
runuser --session-command 'status' mysqld
```

```bash
# Pick a different shell than the account's (service users often have nologin)
runuser -s /bin/sh -u git -- git-upload-pack /srv/git/repo.git
```

## Nuances and Gotchas

- **Root only, by design.** There is no password prompt and no fallback.
  Scripts running as a normal user fail with exit 1 and the message
  `runuser: may not be used by non-root users`.
- **Use `--` before the command.** With `-u`, everything after the target
  user is the command and its arguments; a leading `--` stops option
  parsing and prevents arguments like `-l` from being eaten as runuser
  options.
- **No authentication also means no audit trail of "who approved this".**
  The caller is root, so all the accounting says is that root ran
  something; `sudo` exists precisely to add per-command policy and
  logging.
- **PAM session, but no auth**: `pam_limits` applies the target's
  `limits.conf` entries, yet nothing checks passwords, expiry or account
  lock status. A locked account (`passwd -l`) is still usable through
  `runuser` — that can surprise during incident response.
- **Environment surprises in scripts.** Without `-` you inherit root's
  `PATH`, so a target-user binary in `~/bin` will not be found. Prefer
  absolute paths, or `runuser - user` when you want the target's normal
  login environment.
- **`-c` goes through the target's shell.** The command string is parsed
  twice (once by your shell, once by the target shell) — single-quote the
  whole string and escape carefully, or use the `-u` form which has no
  shell layer at all.
- **`--session-command` vs `-c`** differ only in session bookkeeping
  (utmp-style session creation); init scripts use it to avoid leaving
  stale session entries.
- **BusyBox does not ship runuser**; portable scripts on minimal images
  use `su -s /bin/sh -c ... user` (as root, no password) or `setpriv`.

## Exit Status

| Code | Meaning |
| --- | --- |
| exit status of the command | Normal case: runuser propagates the child's status. |
| 1 | runuser's own failures: non-root caller, unknown user, PAM/session failure. |
| 126 | The command was found but is not executable. |
| 127 | The command could not be found at all. |

## Related Commands

- [`su`](./su.md) — the interactive sibling: performs PAM authentication, usable by any user.
- [`setpriv`](./setpriv.md) — syscall-level uid/gid/capability control with no PAM and no shell.
- [login collection overview](../login/overview.md) — where interactive login and PAM sessions live in this book.
- [`sulogin`](../login/sulogin.md) — single-user-mode root shell, another special-purpose identity switcher.
- [Users and groups](../../admin/users-groups.md) — UID/GID resolution and supplementary group mechanics.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: Why does runuser exist when su already exists?

Because scripts need `su`'s identity switch without `su`'s interactive
contract. `runuser` never prompts, refuses non-root callers outright, and
skips the authentication stack while still running the PAM *session*
modules (limits, keyring). That makes it deterministic under automation
— no tty, no password plumbing, no questions asked — which is why init
scripts and packaging snippets prefer it.

### Q: What does pam_rootok.so do, and how does it relate to runuser?

`pam_rootok` succeeds if the calling process's real UID is 0. In `su`'s
PAM config it is listed as `sufficient` precisely so root can `su`
without a password. `runuser` goes further: its PAM file contains only
that auth module, so authentication is structurally impossible to fail
for root and structurally unavailable to everyone else (enforced outside
PAM by the binary itself).

### Q: How do you run a command as user alice with the primary group changed to devs?

`runuser -u alice -g devs -- command` (or the su-style `runuser -g devs
alice -c ...`). The `-g` option overrides the primary group from
passwd/gshadow; `-G` adds supplementary groups. If you need full control
over group membership without consulting the databases at all, that is
`setpriv --groups=...` territory.

### Q: A systemd user service running as "deploy" calls runuser and fails with "may not be used by non-root users". What are your options?

`runuser` cannot de-escalate — it only re-escalates from root, by
definition. Options: run the parent unit as root with `User=deploy`
instead and drop runuser; use `sudo -u` with a policy rule if controlled
de-escalation is genuinely needed; or restructure so the privileged step
is a small root-owned helper. Note `setpriv` cannot help either, since
nothing can gain privileges it does not hold.

### Q: What is the difference between runuser -u x -- cmd and runuser - x -c cmd?

The `-u` form execs the command directly — no shell in the middle, no
quoting round-trip, args passed verbatim. The `-c` form builds a command
string and hands it to the target's login shell, so shell parsing,
profile scripts and exit-status quirks all apply. Login-shell form also
resets the environment and changes directory to the target's home.

### Q: Which PAM modules still run for runuser, and why do they matter?

On Debian: `pam_keyinit revoke` and `pam_limits` (plus `pam_unix` in the
session stack). They matter because they give the target user fresh
session keyrings and enforce `/etc/security/limits.conf` — so resource
limits observed inside `runuser - user -c 'ulimit -a'` are the *configured*
limits, not the caller's inherited ones, unlike a bare `setpriv` drop.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/runuser.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
