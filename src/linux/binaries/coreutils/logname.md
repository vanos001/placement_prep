# logname — print the login name of the current session

## Overview

`logname` answers one question: *who logged into this session?* It calls
`getlogin(3)`, which asks the kernel for the name associated with the
controlling terminal of the calling process and cross-references the
`utmp` database (`/var/run/utmp` on Debian) where `login`, `sshd`, and
friends record sessions. That is a different question from "who am I
running as right now" — the one `whoami` and `id -un` answer from real and
effective UIDs.

The distinction matters most under `sudo`: your login name stays `alice`
while the effective user becomes `root`. `logname` is how a script recovers
the *original* human even when it is executing with elevated privileges.
It ships in the Debian `coreutils` package and lives at `/usr/bin/logname`.
It is often confused with `whoami`, `id -un`, and the `$USER`/`$LOGNAME`
environment variables — which are set by the shell, can be spoofed, and
survive `sudo` in confusing ways.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/logname` |
| First appeared | System V lineage; present in early Unix distributions |
| Standards | POSIX 2018 utility |

## Synopsis

```
logname [OPTION]
```

Main forms:

```
logname            # print the session's login name
logname --help     # usage text
logname --version  # version information
```

No operands, no behavior flags. The utility is a single question with a
single answer — or an error.

## How It Works

The kernel tracks, per process, the controlling terminal it was attached to
at session creation. `getlogin(3)` looks up that terminal in the `utmp`
file, where session-creating programs (`login`, `sshd`, `su -l`, display
managers) wrote an entry containing the user name, tty, and timestamps.
`logname` prints the `ut_name`/`ut_user` field of that record.

```
  sshd / login / display manager
        │  writes entry (user, tty, pid, time)
        ▼
  /var/run/utmp  ──────────────┐
                               │ keyed by controlling tty
  your process ── getlogin() ──┘
        │
        ▼
  "alice"        ← logname output
```

The chain has one fragile link: the controlling terminal. A process that
has none — cron jobs, daemons, most CI runners, container `exec` shells,
pipes detached via `setsid` — has no utmp session to be found, and
`logname` fails outright:

```bash
# Inside a cron job or docker exec (no login session recorded):
$ logname
logname: no login name
$ echo $?
1
```

Contrast with the identity-based lookups, which never need a terminal:

```bash
$ whoami          # effective UID  -> name (euid)
$ id -un          # same, standard form
$ logname         # utmp session   -> name (may fail, may differ)
```

Under `sudo`, the three diverge: `sudo whoami` prints `root`,
`sudo id -un` prints `root`, but `sudo logname` prints the invoking user
(`alice`) — if and only if the sudo session kept its controlling terminal.
That asymmetry is the entire reason the tool still exists.

## Options That Matter

| Option | Effect |
|---|---|
| `--help` | Print usage and exit |
| `--version` | Print version and exit |

No operands are accepted. POSIX allows implementations to reject extra
arguments; GNU does.

## Usage Patterns

```bash
# Attribute an action to the human who logged in, even under sudo
logger "deployment triggered by $(logname)"
```

```bash
# Fallback chain for contexts that may lack a login session
OWNER=$(logname 2>/dev/null || id -un)
```

```bash
# Detect "am I running under sudo?" — logname differs from euid
if [ "$(logname 2>/dev/null)" != "$(whoami)" ]; then
    echo "running with borrowed privileges"
fi
```

```bash
# chown files back to the invoking user in a root-run installer script
chown -R "$(logname 2>/dev/null || echo root):" ./output
```

```bash
# Who is at this workstation? (login name of *this* session only)
printf 'session owner: %s\n' "$(logname)"
```

```bash
# In a su(1) subshell: $USER still shows the su target, logname does not
su - nobody -c 'echo "$USER vs $(logname)"'
```

## Nuances and Gotchas

- **Fails in cron, CI, containers, and daemons.** No controlling terminal
  → no utmp entry → `logname: no login name`, exit `1`. Any script using
  it unguarded will break the moment it is scheduled. Ground rule: always
  pair it with a fallback (`logname 2>/dev/null || id -un`).
- **`sudo logname` is environment-dependent.** Classic `sudo` preserves the
  controlling terminal, so it prints the invoking user. But `sudo -i`,
  `su -`, or a sudo build that allocates a new session can leave no
  original utmp entry — then it fails or reports root. Never treat it as a
  guarantee; treat `SUDO_USER` (see below) with the same suspicion.
- **`$USER` and `$LOGNAME` are just variables.** They are set by login
  shells, inherited blindly by children, and trivially spoofable
  (`USER=root ./payload`). `logname` consults kernel/utmp state instead —
  the same reason POSIX specifies it for auditing-style use.
- **`whoami` is effective UID, not login name.** After `su`, `sudo`, or
  `setpriv`, they differ. `id -un` is the POSIX-preferred spelling of the
  same thing.
- **utmp can lie after process migration.** Long-lived screen/tmux sessions
  keep the *original* login name years later; re-login inside the session
  does not update `getlogin()` for already-running processes.
- **`utmp` is world-readable but session records are short-lived.** After
  logout the entry is recycled; a background process outliving its login
  may find its tty record gone and fail.
- **Portability is good but not total.** POSIX standardizes it; busybox
  implements it. Behavior when stdin/stdout are redirected is unchanged —
  the lookup is by *controlling terminal*, not by which fds are open.

## Exit Status

| Code | Meaning |
|---|---|
| `0` | Login name found and printed |
| `1` | No login name: no controlling terminal, no utmp entry, or lookup failure |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./pinky.md`](./pinky.md) — reads the same utmp database for all sessions.
- [`./nproc.md`](./nproc.md) — another "ask the environment, not a variable" tool.
- [`../../shell/bash.md`](../../shell/bash.md) — where `$USER`/`$LOGNAME` actually come from.

## Interview Questions

### Q: `logname` and `whoami` — what different questions do they answer?

`whoami` (or `id -un`) converts the process's *effective UID* into a name
from `/etc/passwd` — it answers "who am I running as right now". `logname`
walks controlling-terminal → utmp — it answers "who started this login
session". They agree for a plain login shell and diverge under `sudo`/`su`,
where the euid changes but the session (usually) does not.

### Q: A script that works interactively fails in cron with `logname: no login name`. Why?

Cron jobs have no controlling terminal and no utmp session record — the
cron daemon spawns the job detached from any login. `getlogin(3)` has
nothing to look up, so the utility exits `1`. Fix by falling back:
`USER=$(logname 2>/dev/null || id -un)` or by passing the owner explicitly.

### Q: Under `sudo`, what will `logname`, `whoami`, and `echo $USER` each print?

Typically: `logname` prints the invoking user (e.g. `alice`) because the
sudo process inherited the login session; `whoami` prints `root` because
the effective UID changed; `$USER` is *undefined by sudo* in default
config — it stays `alice` (env preserved for the invoking shell's variable
to be inherited only if `env_keep` allows, or becomes root's under
`sudo -H -i`). The exact values depend on sudoers policy, which is why
scripts prefer explicit mechanisms over variables.

### Q: Why does POSIX standardize a tool that just prints a name — why not use `$LOGNAME`?

Because environment variables are part of the *process environment*, which
any parent process can set to anything. `logname` consults kernel and
system-maintained state (the controlling terminal and utmp), so it cannot
be spoofed by exporting a variable. For accounting, auditing, or anything
security-relevant, a variable is a hint; `logname` is evidence — albeit
evidence with its own failure mode when no session exists.

### Q: When does `logname` succeed but give the "wrong" answer?

Long-running detached sessions: a `tmux` client or `screen` server started
years ago keeps the login name of the *original* session in utmp for every
process attached to it. If the user since did `su -`, the tool still
reports the original login — technically correct ("this session's login
name"), surprising for anyone expecting the current identity.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/logname.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — logname](https://pubs.opengroup.org/onlinepubs/9699919799/)
