# su — run a shell or command with another user's identity

## Overview

`su` ("substitute user") starts a shell — or runs a single command — with
the user and group IDs of another account, defaulting to `root`. Unlike
`sudo` it has no policy engine: you authenticate *as the target user*
(PAM decides how), and from then on the process is that user. Debian
bookworm ships the util-linux implementation in package `util-linux` at
`/usr/bin/su` (on merged-usr systems `/bin/su` is the same file).

`su` is often confused with `sudo` (policy-driven privilege *granting*
with logging; asks for *your* password by default), with `runuser`
(root-only, no authentication at all — the scripted variant of su), and
with `setpriv` (raw credential syscalls, no PAM and no shell).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/su (merged-usr: /bin/su is the same binary) |
| First appeared / lineage | AT&T/BSD heritage; later shadow-utils; modern Debian ships the util-linux su |
| Standards | None — POSIX does not define su; behavior is shaped by PAM |

## Synopsis

```
su [options] [-] [<user> [<argument>...]]
```

Common one-line forms:

```
su -                     # login shell as root
su alice                 # shell as alice, environment mostly kept
su -c 'id -un' bob       # run one command through bob's shell
su -s /bin/sh -c 'cmd' svcuser   # force a shell (service accounts)
```

## How It Works

### Authentication goes through PAM

`su` is PAM-compiled: it starts the service named `su` (or `su-l` for
login shells) and the decision "who may become whom, with what proof"
lives in `/etc/pam.d/su`, not in the binary. Debian's shipped file makes
three points visible:

1. **`pam_rootok.so` as `sufficient`** — root calling `su` succeeds
   immediately, without any password. That is why root's `su` to any
   account is password-free.
2. **Commented-out wheel lines.** Uncommenting
   `auth required pam_wheel.so use_uid` restricts `su` to members of the
   `wheel` group; `use_uid` checks the *calling* user's UID (not the
   target), so it cannot be bypassed by su-chaining. A `trust` variant
   lets wheel members skip the password; a `deny` variant can blacklist
   a group. Until uncommented, any user may try to authenticate.
3. **The session stack** (`pam_env`, `pam_mail nopen`, `pam_limits`,
   plus the `common-*` includes) sets locale/mail variables, applies
   `/etc/security/limits.conf` for the target, and audits the session —
   failed and successful attempts land in the auth log.

Then the credential switch happens (`setgroups`, `setresgid`,
`setresuid`) and `su` execs the target shell — your shell's child in the
normal case, a new session leader with `--login` semantics per PAM
session.

```
 caller shell ── su ──► PAM: auth stack (rootok? unix? wheel?)
                        │
                        ├─ setgroups/setresgid/setresuid → target IDs
                        │
                        └─ exec $SHELL [-c command]   (login flags if -)
```

### Environment: plain `su` vs `su -`

This distinction is the perennial interview question:

| Aspect | `su user` | `su - user` |
| --- | --- | --- |
| Environment | mostly preserved | cleared to a minimal set (`-w` can whitelist) |
| `HOME`, `SHELL`, `USER`, `LOGNAME` | set to target | set to target |
| Working directory | unchanged | target's home |
| `PATH` | caller's (root gets a safe default) | distro-defined default |
| Shell flags | none | login shell (reads profile files) |

`-c command` does not open an interactive shell at all: the command
string is passed to the target's shell as `shell -c 'command'`, so the
*string* is parsed by the target shell while the *quoting* you wrote was
parsed by the calling shell first.

Verified failure modes on a real system (unprivileged caller):

```bash
$ su -c 'id -un' root
Password:
su: Authentication failure
$ echo $?
1
$ su nosuchuser777
su: user nosuchuser777 does not exist or the user entry does not contain all the required fields
$ echo $?
1
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-`, `-l, --login` | Login shell: cleared environment, chdir to target home, profile startup. A bare `-` means `su - root`. |
| `-c, --command <cmd>` | Run one command string via the target's shell (`shell -c`). |
| `--session-command <cmd>` | Like `-c` but no new session is created (init-script style). |
| `-s, --shell <shell>` | Use this shell instead of the target's passwd shell (subject to `/etc/shells` for non-root callers). |
| `-m, -p, --preserve-environment` | Keep the caller's environment (does not reset `HOME`/`SHELL`/etc. beyond the default). |
| `-w, --whitelist-environment <list>` | Keep listed variables even through a login-style reset. |
| `-g, --group <group>` | Use this primary group instead of the target's default (root only). |
| `-G, --supp-group <group>` | Add a supplementary group (root only, repeatable). |
| `-P, --pty` | Allocate a fresh pseudo-terminal for the session. |
| `-T, --no-pty` | Never allocate a pty (rarely wanted; documented as a bad idea). |
| `-f, --fast` | Pass `-f` to the shell (csh/tcsh heritage, meaningless for bash). |

## Usage Patterns

```bash
# Become root with a full login environment
su -
```

```bash
# Run one command as another user and stay put
su alice -c 'whoami; id'
```

```bash
# Root working as a service account for a quick check (no password needed)
su -s /bin/bash www-data -c 'tail -5 /var/www/html/app.log'
```

```bash
# Service users have /usr/sbin/nologin — force a real shell
su -s /bin/sh -c 'pg_ctl status' postgres
```

```bash
# Compare environments to understand the dash
su root -c 'echo $PATH'; su - root -c 'echo $PATH'
```

```bash
# Apply the target's limits from /etc/security/limits.conf (session stack)
su - buildbot -c 'ulimit -n'
```

```bash
# Keep only specific variables through the environment reset
su -w TERM,SSH_AUTH_SOCK - root
```

```bash
# Override group identity while switching (root only)
su -g docker - alice
```

```bash
# Init scripts: run a command without creating a new utmp session
su --session-command 'reload' mydaemon
```

```bash
# Check whether an account is locked without logging in as it
passwd -S alice
```

## Nuances and Gotchas

- **`su` vs `su -` changes more than cosmetics.** Scripts that "work as
  root" but miss `JAVA_HOME`/rbenv/etc. usually ran without `-` and
  inherited a half-reset environment. Decide deliberately per use.
- **The password prompt belongs to the *target* account.** `su alice`
  asks for alice's password — the security model is "prove you are
  alice", not "you are trusted like with sudo".
- **`pam_rootok` is why root needs no password**; removing or
  reordering that line changes root's own behavior. The wheel lines are
  shipped disabled — a hardened system enables `pam_wheel.so use_uid`
  and populates `wheel`.
- **`nologin` shells break `-c`.** `su svc -c 'cmd'` execs
  `/usr/sbin/nologin -c cmd`, which prints the rejection and exits.
  Use `-s /bin/sh`.
- **Double parsing of `-c` strings.** `su user -c "echo $HOME"` expands
  `$HOME` in *your* shell (you) before su ever runs; single quotes defer
  expansion to the target shell. This is the single most common quoting
  bug with su.
- **`-s` is restricted for non-root callers** by `/etc/shells` — a
  normal user cannot `su -s /bin/sh root` as a way around a restricted
  shell.
- **Nothing sudo-grade is audited.** Successful and failed
  authentication is logged via PAM/syslog, but there is no per-command
  policy, no `sudoers` grammar and no timestamp tickets. Compliance
  regimes that demand command-level attribution want sudo.
- **`su` always runs a shell layer.** Even `-c` pays the cost of shell
  parsing; for exec-exact semantics (no shell, no PAM) there is
  `setpriv`, and for root-only scripted switching `runuser`.
- **BusyBox su exists** but is typically PAM-less — its behavior
  (especially wheel/rootok semantics) does not carry over.

## Exit Status

| Code | Meaning |
| --- | --- |
| exit status of the shell/command | Normal case: su propagates what it ran. |
| 1 | su's own failures: authentication failure, unknown user, PAM denial (observed values). |
| 126 / 127 | Conventional shell statuses for "found but not executable" / "not found" surface through the `-c` shell. |

With `-c`, a command that does not exist is reported by the *target
shell* as 127, so codes look normal even though nothing ran.

## Related Commands

- [`runuser`](./runuser.md) — the root-only, password-free su variant for scripts.
- [`setpriv`](./setpriv.md) — credential changes at the syscall level: no PAM, no shell.
- [login collection overview](../login/overview.md) — the interactive login path and its PAM stack.
- [`agetty`](./agetty.md) — the console side of "become a user" before su ever runs.
- [Users and groups](../../admin/users-groups.md) — account resolution, wheel group and shadow passwords.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: What is the difference between su and sudo?

`su` switches identity: you authenticate as the target (root by
default) and then everything you run is that user, with no per-command
policy. `sudo` grants *commands*: you prove your own identity, a policy
file decides what you may run, every invocation is logged individually,
and credentials can be time-limited. Operationally: su = "become
someone", sudo = "do this one thing with elevated rights, audited".

### Q: Why can root run su without entering a password?

`/etc/pam.d/su` lists `auth sufficient pam_rootok.so` first. That module
succeeds whenever the calling process's real UID is 0, and because it is
`sufficient`, the stack short-circuits — no password is ever collected.
Removing that line would make root type the target's password too.

### Q: How does the wheel-group restriction work, and what does use_uid mean?

Debian ships wheel lines commented out in `/etc/pam.d/su`. When
`auth required pam_wheel.so use_uid` is enabled, only wheel members may
use su at all. `use_uid` tells the module to check the UID of the
*calling* process rather than any argument — so `su root; su victim`
chaining cannot launder identity: each su attempt is judged by whoever
is actually running it. `trust` variants skip the password for wheel
members; `deny` variants can exclude a group instead.

### Q: su postgres -c 'pg_ctl status' fails with "account is not currently available". Why, and what now?

The postgres account's shell is `/usr/sbin/nologin` (or the account is
locked), and su honors the passwd shell even for `-c`. Fix with
`su -s /bin/sh -c 'pg_ctl status' postgres` (root can override the
shell), or use `runuser`, which is the intended root-only path for
service accounts. The nologin shell exists to block *interactive*
logins, not to prevent root from running commands on the account's
behalf.

### Q: Explain the quoting hazard in su user -c "echo $HOME".

The calling shell expands `$HOME` *before* su runs, so the target shell
receives a literal path — your home, not the user's. Single-quote the
command (`su user -c 'echo $HOME'`) to defer expansion to the target
shell. Remember there are always two parsers in play: yours and the
target account's login shell.

### Q: You need to reproduce a user's exact login environment in a cron job. What do you use and why?

`su - user -c 'cmd'` — the dash gives the cleared environment, the
target's HOME and PATH, and profile startup, which is as close to a real
login as a command-line switch gets. `su` without `-` inherits the
caller's environment and produces the classic "works in my shell" bugs.
For service-style execution where PAM session modules should still apply
(limits, keyrings), `runuser - user` is the root-only equivalent.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/su.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
