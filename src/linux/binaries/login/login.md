# login — begin a session on the system

## Overview

`login` is the program that turns a terminal into an authenticated user session: it asks who you are, verifies your credentials through PAM, initializes your UID/GID, environment, and working directory, records the session, and finally execs your login shell. It lives in `/usr/bin/login` (the legacy `/bin/login` path is kept as a usrmerge symlink) and ships in Debian's binary package `login`. On a stock Linux system it is execed by the terminal responder `agetty` on virtual consoles and serial lines; historically remote servers such as `telnetd`/`rlogind` execed it too, which is exactly why its `-h` and `-f` options exist. It is *not* used by `sshd` (OpenSSH implements sessions itself) and not by `su`/`sudo` (those change credentials inside an existing session without creating a login session).

`login` has an outsized lineage for a small binary, and that lineage is a real interview trap. Through Debian 12 (bookworm) `/usr/bin/login` was the shadow suite's implementation. Debian 13 (trixie) switched the `login` binary package to the util-linux implementation — `login -V` there prints `login from util-linux 2.41.5`. Upstream util-linux had carried its own login for years, and it is PAM-based like its predecessor. Both implementations do the same job and are driven by `/etc/pam.d/login` plus `/etc/login.defs`, but details (MOTD handling, `securetty` support, faillog/lastlog toggles) differ between them, so always check which implementation your target host runs before quoting behavior.

People confuse `login` with three neighbors: `su` (new credentials inside the current session, no utmp entry), [`sulogin`](./sulogin.md) (root-only maintenance shell for boot failures), and [`nologin`](./nologin.md) (the refusal shell) — plus the `/etc/nologin` *file*, which gates system-wide logins during maintenance windows. This collection has a page for each.

| Field | Value |
| --- | --- |
| Package | login (Debian; built from source package `util-linux` since trixie, from `shadow` through bookworm) |
| Man section | 1 |
| Path | /usr/bin/login (legacy /bin/login symlink) |
| First appeared | Research Unix `login(1)`; 4.4BSD and System V lineages; util-linux variant, shadow variant in Debian until 4.16 |
| Standards | Not POSIX-specified; PAM-based on Debian; configured via /etc/login.defs |

## Synopsis

```
login [-p] [-h host] [-H] [[-f] username]
```

Common one-line forms:

```
login                      # prompt for username, then password
login ann                  # username known; prompt for password only
login -f ann               # skip authentication (getty autologin path)
login -p -h lab-host root  # server form: keep env, record remote host
```

## How It Works

### The session-entry pipeline

```
 agetty (console)           telnetd (historic)         root shell
    │ prints /etc/issue,          │                        │
    │ prompts "host login:"       │                        │
    ▼                             ▼                        ▼
    └─────────────── exec /usr/bin/login ───────────────────┘
                        │
        ┌───────────────▼─────────────────┐
        │ PAM stack, service name "login" │
        │ (service name "remote" if -h):  │
        │   auth:    pam_faildelay        │
        │            pam_nologin          │
        │            common-auth          │
        │   account: expiry checks        │
        │   session: pam_env, pam_motd    │
        │            pam_limits, pam_mail │
        └───────────────┬─────────────────┘
                        │ success
        setuid/setgid (root: primary gid only)
        env: HOME USER LOGNAME SHELL PATH MAIL; TERM kept
        chdir($HOME); utmp + wtmp + lastlog records
                        │
                        ▼
                 exec("-bash")  → your session
```

On Debian the stack behind `/etc/pam.d/login` looks like this (Debian 13, abridged, line numbers preserved):

```bash
$ grep -nE 'pam_|include' /etc/pam.d/login | grep -v '^#.*pam' | head -12
9:auth       optional   pam_faildelay.so  delay=3000000
17:auth       requisite  pam_nologin.so
27:session    required     pam_loginuid.so
33:session    optional   pam_motd.so motd=/run/motd.dynamic
34:session    optional   pam_motd.so noupdate
57:@include common-auth
63:auth       optional   pam_group.so
78:session    required   pam_limits.so
88:session    optional   pam_mail.so standard
94:@include common-account
95:@include common-session
96:@include common-password
```

### Authentication, retries, and delays

- With no argument, `login` prompts for a username, then for the password with echoing disabled; verification happens in the PAM `auth` phase (`common-auth`, i.e. pam_unix against `/etc/shadow`).
- After `LOGIN_RETRIES` bad passwords (Debian ships 5; the util-linux man page documents a compiled default of 3) `login` exits and the connection is dropped.
- Two delay mechanisms throttle brute force: the shipped stack uses `pam_faildelay.so delay=3000000` (3 seconds), and `login.defs` has a `FAIL_DELAY` item (the util-linux man page documents a default of 5 seconds). `pam_faillock` can hard-deny an account after N failures regardless of retries.
- `LOGIN_TIMEOUT` (60 seconds) bounds the whole prompt exchange; a stale `login:` prompt is reaped instead of holding the terminal forever.
- Password aging: an expired password forces the user through a change (old password + new password) before the shell starts.
- `/etc/nologin` is checked by `pam_nologin` (marked `requisite` above): if that file exists, non-root users are refused and shown its contents; root passes.

### Credentials, environment, and exec

- UID/GID come from `/etc/passwd`, and the supplementary group list is built with initgroups — with one deliberate exception: for UID 0 only the *primary* GID is set. The man page explains why: this lets an administrator log in even when the group/NSS database is broken.
- The environment is rebuilt from the password entry: `HOME`, `USER`, `LOGNAME`, `SHELL`, `PATH`, `MAIL`. `TERM` is preserved; variables provided by PAM are always preserved; everything else is destroyed unless `-p` is given (`LOGIN_ENV_SAFELIST` can rescue a few names without `-p`).
- `PATH` defaults come from `login.defs`. On a Debian system:

```bash
$ grep -E '^ENV_(PATH|SUPATH)' /etc/login.defs
ENV_SUPATH	PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV_PATH	PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games
```

- The shell is the passwd shell, else `/bin/sh`; a shell field containing a space is treated as a shell script; a missing home directory falls back to `/`.
- Finally `login` execs the shell with `argv[0]` prefixed by a dash (`-bash`), which is what makes profile scripts run — that is the definition of a *login shell*.

### Session accounting

- **utmp**: a `USER_PROCESS` record in `/run/utmp` — what `who` and `w` read.
- **wtmp**: the same record appended to `/var/log/wtmp` — what `last` replays.
- **lastlog**: the per-UID record in `/var/log/lastlog`. The man page states it plainly: if `/var/log/lastlog` exists, the last login time is printed and the current login is recorded. That is the `Last login: ...` banner. See [`lastlog`](./lastlog.md).
- **btmp**: failed console attempts land in `/var/log/btmp` on Debian (examine with `lastb`); the shadow implementation also maintained per-UID failure counters — see [`faillog`](./faillog.md).
- **MOTD**: util-linux `login` prints the colon-separated `MOTD_FILE` list (directories supported since util-linux 2.36); Debian instead relies on `pam_motd` (the dynamic MOTD generated into `/run/motd.dynamic`). The mechanisms overlap; on Debian, PAM wins.

### Quiet logins

```bash
# ~/.hushlogin (HUSHLOGIN_FILE in /etc/login.defs, default ".hushlogin")
$ touch ~/.hushlogin
```

The quiet-login marker suppresses the MOTD, the `Last login:` line, and the mail check for that account — the standard fix for noisy kiosk consoles. Debian's shipped `login.defs` carries `HUSHLOGIN_FILE .hushlogin`; pointing it at a central list file is a supported alternative.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p` | Preserve the incoming environment (identity variables are still set). Used by getty. |
| `-f username` | Skip authentication; the caller vouches for the user. Designed for getty's `--autologin`; treat as root-only. |
| `-h host` | Record `host` in utmp/wtmp as the origin. Superuser only — and it switches the PAM service name from `login` to `remote`. |
| `-H` | Suppress the hostname in the `login:` prompt (`LOGIN_PLAIN_PROMPT` is the config-file equivalent). |
| `--help`, `-V` | Usage and version (which also tells you *which* login implementation you have). |

### login.defs knobs worth knowing

| Item | Meaning |
| --- | --- |
| LOGIN_RETRIES | Password attempts before exit (Debian ships 5) |
| LOGIN_TIMEOUT | Seconds allowed for the whole prompt exchange (60) |
| FAIL_DELAY | Delay after a failed attempt (man default 5 s; Debian uses pam_faildelay) |
| LOGIN_KEEP_USERNAME | Re-prompt only the password after a bad one |
| LOGIN_ENV_SAFELIST | Variables a `-p`-less login may keep |
| HUSHLOGIN_FILE | Quiet-login marker (default `.hushlogin`) |
| MOTD_FILE / MOTD_FIRSTONLY | MOTD list; stop after first accessible item |
| ENV_PATH / ENV_SUPATH | PATH for normal users / root |
| TTYPERM / TTYGROUP | Login tty permissions (0620 tty on many systems) |

## Usage Patterns

```bash
# 1. Identify which implementation you are debugging (bookworm: shadow, trixie: util-linux)
$ login -V
login from util-linux 2.41.5
```

```bash
# 2. Read the effective PAM stack before touching console auth
$ grep -vE '^($|#)' /etc/pam.d/login
```

```bash
# 3. What a systemd console runs: the getty unit execs agetty, agetty execs login
ExecStart=-/sbin/agetty --noclear %I $TERM
```

```bash
# 4. Kiosk autologin: agetty vouches for the user, login receives -f internally
ExecStart=-/sbin/agetty --noclear --autologin kiosk tty1 9600,38400,57600 vt100
```

```bash
# 5. Maintenance lockout: refuse all non-root logins; root still gets in
$ sudo touch /etc/nologin && echo "logins disabled"
$ sudo rm -f /etc/nologin
```

```bash
# 6. Per-user quiet login for a clean kiosk session
$ sudo -u kiosk touch /home/kiosk/.hushlogin
```

```bash
# 7. Check the retry/timeout policy you inherit
$ grep -E 'LOGIN_RETRIES|LOGIN_TIMEOUT' /etc/login.defs
LOGIN_RETRIES		5
LOGIN_TIMEOUT		60
```

```bash
# 8. What login will exec for a given user (shell + home from passwd)
$ getent passwd z
z:x:1001:1001::/home/z:/bin/bash
```

```bash
# 9. Session accounting files it feeds (fresh container: all empty)
$ ls -l /var/log/wtmp /var/log/lastlog /var/log/btmp
-rw-rw---- 1 root utmp 768 Oct  9 14:09 /var/log/btmp
-rw-rw-r-- 1 root utmp   0 May  5 00:00 /var/log/lastlog
-rw-rw-r-- 1 root utmp   0 May  5 00:00 /var/log/wtmp
```

```bash
# 10. Who is logged in right now (utmp readers; empty in a container without sessions)
$ who
$ w
```

## Nuances and Gotchas

- **sshd never execs `/bin/login`.** OpenSSH runs the user's shell directly and has its own PAM stack (`/etc/pam.d/sshd`). Testing console-login changes by SSHing in proves nothing.
- **`-h` silently changes the PAM service name to `remote`.** Any policy you tuned under `login` (faillock, limits, motd) does not apply unless you maintain `/etc/pam.d/remote` too.
- **Root gets no supplementary groups.** Only the primary GID is set for UID 0, on purpose (NSS-resilience). Scripts assuming root's full group list are wrong on login sessions.
- **Environment nuking is the default.** Without `-p`, everything not in the identity set disappears; exported variables from a remote client do not survive. PAM-provided variables always survive.
- **`/etc/nologin` (file) vs `/usr/sbin/nologin` (shell)** are unrelated despite the name: one gates the whole machine for maintenance (root exempt, contents shown to victims), the other denies a single account. Maintenance scripts should create the file, not edit shells.
- **`pam_securetty`/`/etc/securetty` are gone from current Debian stacks.** Old runbooks that restrict root to listed consoles via that file describe bookworm-era-and-earlier behavior; trixie ships no `/etc/securetty`.
- **Delays live in PAM on Debian** (`pam_faildelay`, 3 s), not in `FAIL_DELAY` from `login.defs`; the item still exists for other implementations.
- **The bookworm → trixie implementation switch moved behavior**: MOTD handling, `FAILLOG_ENAB`/`LASTLOG_ENAB` login.defs keys removed, no setuid bit on the binary (it expects to be execed by a privileged getty). Automation that parsed shadow-only flags or output needs review.
- **`login` is execed, not forked, by getty**, so the terminal's session leader becomes your shell; misconfigured PAM `session` modules that block leave the console dead with no shell — check `journalctl` rather than the tty.

## Exit Status

- After successful authentication `login` *execs* the shell, so the exit status observed by the parent is the shell's, not `login`'s.
- Failure paths exit non-zero — `1` in practice: retries exhausted, `LOGIN_TIMEOUT` exceeded, `/etc/nologin` rejection, unusable terminal, bad options.
- There is no documented table of codes; treat any non-zero as "no session was created".

## Related Commands

- [`sulogin`](./sulogin.md) — password-gated root shell for rescue/emergency boots, a different entry path from login.
- [`nologin`](./nologin.md) — the refusal shell for accounts, plus the same-named `/etc/nologin` gate file.
- [`lastlog`](./lastlog.md) — the per-UID database behind the `Last login:` banner.
- [`faillog`](./faillog.md) — shadow-era failed-login counters enforced by login.
- [`newgrp`](./newgrp.md) and [`sg`](./sg.md) — "group login" helpers that reuse the same re-credential-and-exec idea.
- [Overview — the login collection](./overview.md) — how these session-entry tools fit together.
- [Users and groups](../../admin/users-groups.md) — passwd/shadow/group files that login consumes.
- [systemd](../../admin/systemd.md) — getty units, rescue/emergency targets, and logind sessions around login.

## Interview Questions

### Q: Does sshd use /usr/bin/login?

No. OpenSSH performs its own authentication and session setup and runs the user's shell directly; it consults `/etc/pam.d/sshd` when `UsePAM` is on. `/bin/login` is the *console/terminal* entry path (agetty), with `-h`/`-f` leftovers from the telnetd/rlogind era. This matters when debugging: fixes to `/etc/pam.d/login` do not affect SSH.

### Q: Where does the "Last login: ..." banner come from, and how do you suppress it?

From the per-UID record in `/var/log/lastlog`, read at login time and updated after a successful login (login does this itself; sshd has equivalent code). Suppress it per user by creating `~/.hushlogin` (or via `HUSHLOGIN_FILE`), which also disables the MOTD and mail check. Note the record is written even when the banner is suppressed.

### Q: What is the difference between /etc/nologin and /usr/sbin/nologin?

`/etc/nologin` is a flag *file*: while it exists, PAM's `pam_nologin` (in the `login` and typically `sshd` stacks) refuses all non-root logins and shows the file's contents — a maintenance mode. `/usr/sbin/nologin` is a program placed in an account's shell field that always prints a message and exits 1 — a per-account denial. Same word, completely different mechanisms and scopes.

### Q: Why does root's login session show fewer groups than `su -`?

By design, `login` sets only the primary GID for UID 0 instead of the full initgroups list, so that root can still authenticate and get a shell when the group database or NSS is unavailable. `su`/`sudo` run with the full supplementary list. Interviewers like this because it shows you read man pages rather than assuming symmetry.

### Q: How would you slow down or block password brute-force at the login prompt?

Layered answers: `pam_faildelay` (shipped at 3 s) to slow each attempt, `LOGIN_RETRIES` to cap attempts per invocation, `pam_faillock` (or older `pam_tally2`) to lock the account after N failures, plus `/etc/nologin` for maintenance windows. Mentioning that sshd is a separate PAM stack and that `lastb`/btmp records the failures gets full credit.

### Q: A user reports their session has no PATH entries they exported in a wrapper script. Why?

`login` deliberately rebuilds the environment: only `HOME`, `USER`, `LOGNAME`, `SHELL`, `PATH`, `MAIL` (plus `TERM` and PAM-provided variables) survive, and `PATH` is forced from `ENV_PATH`/`ENV_SUPATH`. Preserving arbitrary variables requires `-p` (which getty passes) or the `LOGIN_ENV_SAFELIST` whitelist. The fix is to export after login (profile files), not before it.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/login/login.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
