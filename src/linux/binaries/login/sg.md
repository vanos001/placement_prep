# sg — execute a command under a different group

## Overview

`sg` is `newgrp` with a command attached: it re-credentials the caller with a different group ID and runs one command, then returns — no interactive subshell to exit, no parent shell changed. The classic form is `sg group -c command`. It exists because the interactive `newgrp` ritual (enter shell, do work, exit, remember which shell you're in) is wrong for scripts, and because "am I allowed to do this as group X?" should be answerable in one line.

On Debian the tool changed shape across releases. Through bookworm, `sg` was its own shadow-suite binary (`/usr/bin/sg`, man page `sg(1)`, documenting that the command runs under `/bin/sh` and that `sg` exits with the command's exit status). Debian 13 (trixie) merged it into util-linux's 2.41 port of `newgrp`: `sg` is now a symlink to the setuid `newgrp`, and the two share one man page. Semantics that matter to users — membership/password gating, one-shot execution, exit-status forwarding — survived the merge intact, and the exit-status forwarding is verifiable on any system.

| Field | Value |
| --- | --- |
| Package | login (Debian; shadow on bookworm, util-linux 2.41+ on trixie — sg is a symlink to newgrp there) |
| Man section | 1 |
| Path | /usr/bin/sg (symlink to /usr/bin/newgrp on Debian 13) |
| First appeared | shadow suite (companion to newgrp); merged into util-linux's newgrp in 2.41 |
| Standards | Not POSIX (newgrp is; sg is a Unix convention) |

## Synopsis

```
sg [-] [group [-c] command]
```

(Debian 13 help text, after the merge: `sg <group> [[-c] <command>]`.)

Common one-line forms:

```
sg docker -c 'docker ps'     # run one command with docker as the new GID
sg - devs -c 'make'          # shadow-era: re-initialize environment too
sg devs                      # no command: behaves like interactive newgrp
```

## How It Works

### The re-credential-and-exec pattern

`sg` performs the same three steps as `newgrp` — verify the caller may enter the group, fork and set the new GID (and group access list) in the child, exec — but the exec target is your command instead of an interactive shell:

```
 parent shell (gid=z) ──► sg ──► fork
                                   │  setgid(target) + group list
                                   ▼
                              exec(shell -c 'command')
                                   │
                                   ▼
                            command exits ──► sg exits with its status
```

The parent is untouched; nothing is written to utmp/wtmp/lastlog; there is no PAM session. Gating is identical to `newgrp`: members (primary or listed) walk in, non-members need a group password via `/etc/gshadow` on the shadow implementation, and the superuser is never prompted.

### The membership gate, field by field

```
 /etc/group   line:  groupname : x : GID : member,member,...
 /etc/gshadow line:  groupname : encrypted_password : admins : members
                     perms on Debian: -rw-r----- root:shadow
```

The gate evaluates, in order: the caller's primary GID (from `/etc/passwd`), the members list, and — only for non-members — the gshadow password (empty or `!`-locked means refuse). That last field is the reason the binary carries privilege: unprivileged processes cannot read `/etc/gshadow` at all, so `sg`/`newgrp` must be a setuid-root program (Debian 13: `/usr/bin/sg` is a symlink to setuid `/usr/bin/newgrp`) that reads the file, decides, performs the setgid/setgroups as root, and drops back to the invoking user.

### How far the new GID reaches

The re-credentialing applies to the child command only, and only to group-based checks:

- **Reads/executes**: files group-owned by the target group and mode bits allowing it become accessible (that is the point — e.g. a `docker`- or `archive`-gated socket/directory).
- **Writes**: new files created by the command get the target group as their GID (subject to the parent directory's setgid bit and the umask) — a side effect that surprises people who only wanted read access.
- **Unaffected**: root-owned paths, other users' processes, and anything keyed to your UID rather than GID.

### Which shell runs the command — an implementation difference that bites

- **shadow (bookworm)**: the man page states the command is executed with `/bin/sh`.
- **util-linux 2.41+ (trixie)**: the command is passed to the *user's shell* with `-c`. Grounded on this system (user `z`, login shell `/bin/bash`):

```bash
$ sg z -c 'ps -o comm= -p $$; echo "shell=$0"'
bash
shell=/bin/bash
```

Payloads sensitive to shell flavor (bashisms, quoting rules) should be shipped as a script with an explicit shebang and invoked as `sg group -c /path/script.sh` — portable across both implementations.

### Exit status is the contract

The whole point of a one-shot wrapper is scriptability, and `sg` honors it: it exits with the exit status of the command it ran. Verified locally:

```bash
$ sg z -c 'exit 7'; echo "forwarded=$?"
forwarded=7
$ sg z -c 'true'; echo "ok=$?"
ok=0
```

Refusals (unknown group, membership denied) produce failure statuses of their own — so a script can distinguish "the command failed" (its code) from "I never got to run" (sg's error path).

### Identity arithmetic

Inside the command, the target group is the GID used for permission checks; the UID, environment, umask (unless the shadow `-` form re-initializes it), and working directory are the caller's. Under the shadow implementation the child's supplementary group list is replaced by the target group — the same collapse `newgrp` exhibits — so verify with `id -Gn` inside if other memberships matter.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-c command` | Run `command` instead of an interactive shell; exit status is forwarded. |
| `-` (positional, shadow) | Re-initialize the environment as after a login before running the command/shell. |
| (no command) | Falls back to `newgrp` behavior: interactive subshell you must exit. |
| `-h`, `-V` | Usage / version (after the merge these report the newgrp implementation). |

## Usage Patterns

```bash
# 1. One-shot command under a group you are a member of
$ sg docker -c 'docker ps'
```

```bash
# 2. Scriptable group-gated build step, with real exit-code handling
$ if sg devs -c 'make'; then echo built; else echo "build failed ($?)"; fi
```

```bash
# 3. Prove which implementation you are on before relying on flags
$ readlink -f "$(command -v sg)"; sg -V 2>&1 | head -1
/usr/bin/newgrp
```

```bash
# 4. Check the identity you actually got inside
$ sg devs -c 'id -Gn'
```

```bash
# 5. Equivalent form on util-linux 2.41+ (trixie): newgrp grew a -c
$ newgrp docker -c 'docker images'
```

```bash
# 6. Avoid quoting hell: ship the payload as a script, not an inline one-liner
$ cat > /usr/local/bin/nightly-sync.sh <<'EOF'
#!/bin/bash
set -euo pipefail
rsync -a /srv/data/ /mnt/archive/data/
EOF
$ sg archive -c /usr/local/bin/nightly-sync.sh
```

```bash
# 7. Non-member with a group password (shadow implementation): one prompt, then it runs
$ sg archive -c 'id -Gn'
Password:
```

```bash
# 8. Root sanity-testing group permissions without switching accounts
$ sudo sg devs -c 'touch /srv/dev/.write-test && rm /srv/dev/.write-test'
```

```bash
# 9. Failure path: unknown group reports and exits nonzero, parent shell intact
$ sg nosuchgroup -c 'true'; echo "rc=$?"
```

```bash
# 10. Scheduled group-gated job: cron runs as the user, sg supplies the group
* * * * * z sg archive -c /usr/local/bin/nightly-sync.sh
```

```bash
# 11. Audit who can enter a group without a password (members list; gshadow needs root)
$ getent group archive
archive:x:1500:ann,bob
$ sudo getent gshadow archive
archive:*::ann,bob
```

```bash
# 12. Watch the group ownership of files the command creates (side effect check)
$ sg archive -c 'touch /tmp/x' && ls -l /tmp/x && rm /tmp/x
```

## Nuances and Gotchas

- **Double shell evaluation.** The `-c` payload is parsed by an inner shell; `sg g -c "echo $HOME"` interpolates in the *outer* shell before sg ever runs. Single-quote payloads or move them into scripts.
- **Shell flavor differs by implementation** (`/bin/sh` under shadow, user's shell under util-linux 2.41+). Bashisms in inline payloads are a portability bug; the explicit-shebang script sidesteps it.
- **Supplementary group collapse** (shadow implementation): inside the command you are only the target group, not your full membership. Assertions like "I'm also in wheel so this is fine" are false in there.
- **Exit-status layering**: the forwarded status comes through an `sh -c` run — a not-found command surfaces as 127, a permission failure as 126 (standard shell semantics). Design your script's contract accordingly.
- **The setuid story lives in newgrp**: on Debian 13 `sg` is a symlink to setuid-root `/usr/bin/newgrp`, which reads `/etc/gshadow` (0640 root:shadow) during the gate. Damaged symlinks or stripped setuid bits break group-password entry silently.
- **No policy, no audit.** `sg` is not `sudo -g`: nothing is logged, no sudoers rule constrains it, and group membership is the only gate. If accountability matters, delegate through sudo and let sudoers handle group targeting.
- **`sg group` without a command is newgrp** — interactive, nested, and easily stacked. In scripts, always pass `-c`.
- **Not POSIX**: scripts targeting POSIX-only environments should treat `sg` as a Linux/shadow-ism (or use the util-linux `newgrp -c` equivalent where available); BusyBox systems ship `newgrp` but not `sg`.
- **The write side-effect cuts both ways.** Files created inside the command carry the target GID — desirable for shared workspaces, a data-classification problem when the target group is broader than the one the data was meant for. For durable sharing, setgid directories (see the users-groups chapter) do the job without a wrapper command.

## Exit Status

- The exit status of the executed command (verified locally; documented for the shadow implementation: upon successful completion `sg` exits with the command's status).
- Non-zero (`1` in practice) when the group login itself fails: unknown group, refused membership, wrong password.
- Standard shell `-c` semantics pass through: 126 command found but not executable, 127 command not found.

## Related Commands

- [`newgrp`](./newgrp.md) — the interactive sibling; on Debian 13 `sg` is a symlink to it and both accept `-c`.
- [`login`](./login.md) — the session-entry program whose credential-setting sg borrows for a single group.
- [Overview — the login collection](./overview.md) — the session-entry tool family in context.
- [Users and groups](../../admin/users-groups.md) — group membership, /etc/gshadow, and setgid-directory alternatives.

## Interview Questions

### Q: What does `sg docker -c 'docker ps'` actually change about the process, and for how long?

It forks a child, sets the target group as the child's GID (shadow implementation: replacing the supplementary list too), and execs the command through a shell; the parent shell and its credentials are untouched, and the change lives exactly as long as the command. No session records are written. The "for how long" is the heart of the answer: one command, not the session.

### Q: Your script does `sg devs -c 'make'` and needs to react to build failures. What guarantees do you have on the exit code?

`sg` forwards the command's exit status — verified trivially with `sg <grp> -c 'exit 7'; echo $?`. Through the inner `sh -c`, 126/127 semantics also pass through for non-executable/not-found commands. The failure mode to distinguish is sg's own refusal (unknown/denied group), which never ran your command at all; log both paths separately.

### Q: Why might a payload that works on Debian 12 fail on Debian 13 without any sg bug?

The implementation switched from shadow's `sg` (command run under `/bin/sh`) to util-linux's merged `newgrp` (command run via the *user's shell* with `-c`), and `sg` became a symlink. Bashisms or dash-isms in inline payloads, plus scripts asserting on `command -v sg` output, behave differently. Fix: explicit-shebang script payloads and `readlink -f` checks.

### Q: Compare sg with sudo -g for running a command under another group.

`sg` gates on *membership* (or a gshadow group password), performs a pure GID change, forwards the exit status, and logs nothing. `sudo -g` gates on a sudoers policy, applies sudo's environment/target handling, logs the invocation, and is auditable. Use `sg` for convenience within your own memberships; use `sudo -g` when delegation is a *policy* decision. Knowing both exist — and that only one leaves a trail — is the point.

### Q: What are the dangers of the shadow-era `sg -` form?

It re-initializes the environment like a login (umask, PATH, HOME from login.defs) inside the command run — surprising for payloads that inherited environment from the caller (API keys, PATH extensions), and it is not portable to the util-linux port, which dropped the form. Side effects are silent: the command behaves differently under `-` with no visible cue.

### Q: Design question: why must sg (via newgrp) be setuid root at all?

Two operations in its gate need privilege that a user process lacks: reading `/etc/gshadow` (mode 0640 root:shadow — group passwords and locked fields must not be world-readable) and calling `setgid`/`setgroups` to the target group before execing the command. A world-readable `/etc/group` is not enough for the password path, and letting users setgid themselves without a trusted broker would erase the point of group permissions. Hence one small, auditable setuid binary that validates membership first and drops privilege immediately after.

### Q: How does a non-member end up running a command under a group they do not belong to?

Only through the group-password path: `gpasswd group` stores a password in `/etc/gshadow`, and `sg group -c ...` (shadow implementation) prompts for it, admitting the user for that one command. It is a legacy access path — worth auditing on inherited systems, since a group password grants membership without any groupmod trace in /etc/group's member list.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/login/sg.1.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
