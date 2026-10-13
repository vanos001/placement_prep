# newgrp — log in to a new group

## Overview

`newgrp` changes the group identification of its caller "analogously to login(1)", as the man page puts it: the same person stays logged in and the working directory does not move, but from that point permission checks against files are performed with respect to the new group ID. It is how a user picks up a secondary group (typically after being added to one) *without* logging out and back in. With no argument it re-enters the login GID; since util-linux 2.41 it can also run a single command instead of an interactive shell (`newgrp group -c command`).

Debian ships two implementations across releases, and the difference is interview-relevant. Through bookworm it was the shadow suite's `newgrp`, which consults `/etc/gshadow`, prompts for group passwords, and supports the traditional `newgrp -` "re-initialize environment" form. Debian 13 (trixie) switched to util-linux's fresh port: `/usr/bin/newgrp` is setuid root, `/usr/bin/sg` is now a *symlink* to it, and the man page lists only `/etc/group` and `/etc/passwd` as files. POSIX (XSI) specifies `newgrp` itself; the command is as old as V7 Unix.

| Field | Value |
| --- | --- |
| Package | login (Debian; shadow on bookworm, util-linux 2.41+ on trixie) |
| Man section | 1 |
| Path | /usr/bin/newgrp (setuid root; /usr/bin/sg is a symlink to it on Debian 13) |
| First appeared | V7 Unix; POSIX (XSI) `newgrp`; shadow implementation for decades; util-linux port in 2.41 |
| Standards | POSIX (XSI); `-c` and `-` forms are implementation extensions |

## Synopsis

```
newgrp [-] [group]
newgrp [-c command] [group]        # util-linux 2.41+ (also reachable as sg)
```

Common one-line forms:

```
newgrp              # re-login into your primary group
newgrp docker       # interactive subshell with docker as the new GID
newgrp - devs       # shadow-era form: like above, re-initialize environment
sg devs -c 'make'   # one-shot command form — see ./sg.md
```

## How It Works

### Why it must start a new shell

A running process cannot sanely rewrite its own real GID, effective GID, and group access list in mid-flight — everything it has already opened and every credential check queued would be ambiguous. So `newgrp` does the only correct thing: fork a child, re-credential the child, exec a fresh shell.

```
 before                          after `newgrp docker`
 ─────────                       ─────────────────────
 bash  (gid=z)                   bash  (gid=z)          ← untouched parent
    │ your session                  │
    │                               ├── newgrp → exec bash (gid=docker)
    │                               │        └── work that needs group docker
    │                               │        └── exit → back to the parent
    └── ...                         └── ...
```

`exit` returns you to the original shell with the original groups; the two shells are stacked (check `$SHLVL`). This is also why scripts should never call `newgrp` expecting the *rest* of the script to run with the new GID — the rest of the script keeps running in the parent, unchanged.

### What changes and what does not

- **Changed**: real and effective GID of the new shell; file permission calculations (create, open, execute) now use the new group.
- **Unchanged**: UID, home directory, current directory (per the man page), inherited environment (unless the shadow `-` form re-initializes it).
- **Group access list**: the shadow implementation replaces the supplementary group list with the target group inside the new shell — other memberships do not apply there. Implementation-dependent across the shadow/util-linux split, so verify rather than assume:

```bash
$ id -Gn                 # outside
z
$ sg z -c 'id -Gn'       # inside a group shell (single-group user here)
z
```

- **Not a login**: nothing is written to utmp/wtmp/lastlog; the session accounting of your real login is untouched.

### Membership and the password path

The gate is membership:

- If the target group is your primary group (from `/etc/passwd`) or you are listed in its member list, you enter without prompting.
- Otherwise the *shadow* implementation consults `/etc/gshadow` (root-readable only, which is why the binary is setuid root):

```bash
$ ls -l /usr/bin/newgrp /etc/gshadow
-rwsr-xr-x 1 root root 18816 Jul 31 15:34 /usr/bin/newgrp
-rw-r----- 1 root shadow 436 Sep 21 11:41 /etc/gshadow
```

  - group has a password (set with `gpasswd`) → you are prompted; the correct password admits you for that shell;
  - group password is empty or locked (`!`) → refused.
- The util-linux 2.41 port documents only `/etc/group` and `/etc/passwd`; on systems where group passwords live in `/etc/gshadow` (any shadow-managed system), the shadow implementation is the one that fully supports the prompt path. The superuser is never prompted.

### Command mode

Modern util-linux accepts a command directly — the man page: an optional command is invoked after the group change *instead of the user's shell*, passed to the user's shell with `-c`. Grounded on this system (user `z`, shell `/bin/bash`):

```bash
$ sg z -c 'ps -o comm= -p $$; echo "shell=$0"'
bash
shell=/bin/bash
$ sg z -c 'exit 7'; echo "forwarded=$?"
forwarded=7
```

The shadow-era binary had the same capability only through its `sg` sibling; on trixie `sg` and `newgrp -c` are literally the same program.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-` (positional, shadow) | Re-initialize the environment as after a login (umask, PATH, HOME from login.defs), like `su -`. |
| `-c`, `--command CMD` (util-linux 2.41+) | Run CMD via the user's shell `-c` instead of an interactive shell; exit status is forwarded. |
| (no args) | Re-enter the login GID from /etc/passwd. |
| `-h`, `-V` | Usage / version (also identifies the implementation). |

POSIX also specifies a `-l` ("login environment") form for `newgrp`; support varies by implementation — treat it as non-portable.

## Usage Patterns

```bash
# 1. Pick up a group you were just added to, without re-logging-in
$ newgrp docker
```

```bash
# 2. One-shot group-scoped command, no nested shell to exit
$ sg docker -c 'docker ps'        # (util-linux: newgrp docker -c 'docker ps')
```

```bash
# 3. Verify where you landed before doing work
$ newgrp devs
$ id -Gn
$ exit
```

```bash
# 4. Scripted entry: feed the inner shell your commands, then exit it
$ printf 'id -Gn\nmake\nexit\n' | newgrp devs
```

```bash
# 5. Shadow-era: reset environment too (fresh PATH/umask inside the group shell)
$ newgrp - devs
```

```bash
# 6. Let non-members in via a group password (shadow implementation + gpasswd)
$ sudo gpasswd devs        # prompts for the new group password, stored in /etc/gshadow
```

```bash
# 7. Check which implementation you are running before relying on flags
$ newgrp --version; readlink -f "$(command -v sg)"
newgrp from util-linux 2.41.5
/usr/bin/newgrp
```

```bash
# 8. See who may enter a group directly (members list) as root
$ getent group devs
devs:x:1500:ann,bob
```

```bash
# 9. Confirm the parent shell is untouched after the child exits
$ newgrp devs
$ exit
$ id -Gn          # back to the original groups
```

## Nuances and Gotchas

- **Nested shells pile up.** Every `newgrp` is one more shell to `exit`; `newgrp` inside `newgrp` is a classic way to lose track of which identity you are. Check `$SHLVL` and `id -Gn` before blaming permissions.
- **Supplementary groups collapse** (shadow implementation) inside the group shell — you are *only* the new group there. Code that assumes the full membership list breaks; verify with `id -Gn` inside.
- **The util-linux port dropped the `-` login-reinit form** (its help documents only `-c`); the shadow and POSIX `-`/`-l` forms are not portable across the split. Probe with `newgrp --help` on the target host.
- **Group passwords are a legacy door.** They live in `/etc/gshadow`, are managed by `gpasswd`, and are disabled by a locked field. Audit `/etc/gshadow` if you inherit a system — an old group password is an unmonitored membership path.
- **setuid root by design**: to read `/etc/gshadow` (mode 0640 root:shadow) the binary needs privilege; it drops to the user immediately after. Never "fix" a permissions warning by removing the bit.
- **It does not create a session**: no utmp/wtmp/lastlog writes, no PAM session modules — despite the man page's "analogously to login" phrasing.
- **umask subtlety**: the shadow `-` form applies the login-defs umask; the plain form inherits your current umask, and files you create inside the group shell get the new GID (subject to the directory's setgid bit). For durable shared-directory semantics, setgid directories beat `newgrp` rituals.
- **`newgrp` is not `sudo -g`**: no policy engine, no logging, no environment module — just a GID change gated by membership. Accountability tools do not see it as privilege escalation.

## Exit Status

- When a command is run (`-c`), its exit status is forwarded (verified locally: `sg z -c 'exit 7'` → 7).
- Without a command, the status is that of the shell it started, i.e. the value the inner shell exits with.
- `1` when the group login fails outright: unknown group, non-member with no/passwordless gshadow entry, wrong password.

## Related Commands

- [`sg`](./sg.md) — the one-shot command form; on Debian 13 literally a symlink to newgrp.
- [`login`](./login.md) — the full session entry whose credential-setting newgrp imitates for one group.
- [Overview — the login collection](./overview.md) — the session-entry tool family in context.
- [Users and groups](../../admin/users-groups.md) — /etc/group, /etc/gshadow fields, setgid directories, and membership mechanics.

## Interview Questions

### Q: Why does newgrp start a new shell instead of just changing the group ID?

Because credential state is not meaningfully swappable mid-process: the shell's already-resolved identities, open file descriptions, and subsequent exec semantics all assume a stable ID set. `newgrp` forks, sets the new GID (and group access list) in the child, and execs a fresh shell; `exit` unwinds to the untouched parent. Any answer that claims the current shell "just changes" should be checked against `$SHLVL` before and after.

### Q: A user was added to the docker group but `docker ps` still fails until they re-login. How does newgrp help?

Group membership is baked into the process credential at login (initgroups), so existing sessions keep the old list. `newgrp docker` (or `sg docker -c 'docker ps'`) starts a shell/command with docker as the GID immediately. The durable fix is still re-login; newgrp is the session-time bridge — and it is exactly the answer interviewers want when they ask how to apply group changes without logging out.

### Q: How can a non-member enter a group with newgrp?

Via the group password path of the shadow implementation: if `/etc/gshadow` carries a password for the group (set with `gpasswd`), `newgrp group` prompts, and the correct password admits the user for that shell. Empty or `!`-locked password fields refuse non-members; the util-linux port documents only `/etc/group`/`/etc/passwd`, so verify implementation before relying on the prompt.

### Q: What happens to your other supplementary groups inside a newgrp shell?

Under the shadow implementation, the group access list is replaced by the target group — you are effectively only that group inside. This surprises people whose scripts check `id -Gn` for other memberships. The util-linux behavior should be verified per release; either way, "check with id inside" is the safe operational habit.

### Q: Why is /usr/bin/newgrp setuid root, and why does that make sense here?

It must read `/etc/gshadow` (0640 root:shadow) to resolve membership and group passwords, and then it must perform the setgid/setgroups dance as root before dropping back to the invoking user. The privilege window is tiny and the program is a small, auditable setuid binary — the classic justification pattern for setuid tools that mediate account-database access.

### Q: newgrp vs sg vs sudo -g — when do you reach for each?

`sg`/`newgrp -c` for a one-shot command under a group you may enter (membership or password) — no policy engine, exit status forwarded. Interactive `newgrp` for a working session in that group. `sudo -g` when a sudoers policy should govern the delegation (logging, per-command rules, environment management) — it is privilege *administration*, not group membership convenience. Reaching for `sudo` where a GID change suffices, or vice versa, is the design smell the question probes.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/login/newgrp.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
