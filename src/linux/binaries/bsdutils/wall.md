# wall — write a message to all logged-in terminals

## Overview

`wall` ("write all") broadcasts a message to the terminals of every currently logged-in user. One invocation, everyone's screen. It ships in the `bsdutils` package at `/usr/bin/wall` (upstream util-linux; the name honors its BSD lineage). It is the transport behind the messages you see before a maintenance reboot — "The system is going down for reboot NOW!" — because `shutdown(8)` uses `wall` for its countdown announcements.

You reach for `wall` to warn interactive users of imminent disruption: reboots, storage migrations, load balancer drains. It is often confused with `write` (point-to-point conversation with one user), with `mesg` (the permission bit that controls who may write to *your* terminal), and with crude `echo > /dev/pts/N` loops (which skip the utmp lookup, the banner, the 79-column wrapping, and the permission handling `wall` does for you).

| Field | Value |
| --- | --- |
| Package | bsdutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/wall |
| First appeared | Version 7 AT&T UNIX |
| Standards | — (BSD/AT&T heritage; not in POSIX) |

## Synopsis

```
wall [-n] [-t timeout] [-g group] [message | file]
```

Common one-line forms:

```
wall "Reboot at 18:00"              # operand used as the message
wall /etc/maintenance-notice        # operand that opens as a file: its contents
echo "Backing up DB..." | wall      # no operand: message read from stdin
wall -g operators "Deploy in 10m"   # only members of a group
shutdown -h +10                     # shutdown(8) broadcasts via wall internally
```

## How It Works

### Message sourcing

`wall` takes at most one operand. The resolution order: an operand that can be opened as a file is read as file contents; otherwise the operand itself is the message; with no operand at all, standard input is read to EOF. The file-vs-string ambiguity is a real trap — `wall todo.txt` sends the file's contents, not the string "todo.txt" — so scripted broadcasts should prefer the unambiguous stdin form.

### Finding the recipients

`wall` does not scan `/dev/pts/*` blindly. It reads `utmp` (the login-records database, maintained by `login`/`sshd`/display managers) and collects the terminal line (`ut_line`) of each logged-in user, then opens each terminal device for writing:

```
 wall
   │ 1. read utmp → list of ut_line entries
   │ 2. (optional) filter by -g group membership
   ▼
 for each tty:
   ├─ open /dev/pts/N for write          ── fails if mesg n and invoker ≠ root
   ├─ write banner: Broadcast message from user@host (tty) (date):
   └─ write message, wrapped/padded to 79 columns, CRLF-terminated
```

Entries whose login name begins with `:` — X display sessions of the `wdm(1x)` variety — are skipped on purpose, to avoid write errors against pseudo-display devices. On systems where nothing populates utmp (minimal containers, for instance), `wall` finds nobody to notify and exits quietly with status 0.

### The banner, the padding, and -n

Every delivered message is framed by a banner identifying the sender. The compiled-in format string is `Broadcast message from %s@%s (%s) (%s):`, and `-n` controls whether the banner is sent at all.

`-n`/`--nobanner` suppresses the banner, but **only root may use it**: an unprivileged `wall -n` prints `wall: --nobanner is available only for root` on stderr and then proceeds anyway, banner attached, exit status 0 (verified). The rationale is spoofing prevention — without the banner, a message is unattributable and could pose as a system notice.

### What the recipient sees

Delivery is per-terminal, framed, and width-normalized. The compiled-in banner format is `Broadcast message from %s@%s (%s) (%s):` — sender, host, tty, timestamp — so a message arrives looking like:

```
Broadcast message from alice@server1 (pts/2) (Thu Oct  9 16:20:00 2025):
Disk migration starts in 10 minutes. Expect brief I/O stalls.
```

After the banner, each line of the message is wrapped at 79 columns and short lines are whitespace-padded out to 79, each terminated with carriage-return + newline. The padding is why wall output pasted into logs or diffs carries trailing spaces, and why the same message never looks "tight" the way `echo` output does.

### Permission model: the mesg bit

A terminal node is normally `crw--w---- owner:tty`. Writing to another user's tty therefore requires privilege, which is why `wall` (and `write`) are installed setgid `tty`: the group-write capability is granted by the group, not by running as root. Whether the *user* accepts messages is the `mesg(1)` setting — `mesg n` removes the group-write bit from the terminal so even `write` fails. `wall` has one special rule here:

- **Only the superuser can write on terminals of users who have chosen to deny messages** (`mesg n`), or whose session auto-denies them.

So a root `wall` is the only broadcast guaranteed to reach every terminal — one reason shutdown messaging runs as root.

### Timeout

`-t timeout` abandons a write attempt to a terminal after `timeout` seconds. The default is 300 seconds — a legacy of users dialed in over modem lines whose flow control could stall a write indefinitely. A wedged tty (hung NFS session, stopped process with a full tty buffer) otherwise makes `wall` hang for five minutes; scripts should pass `-t 5` or so.

### Role in the shutdown sequence

`shutdown(8)` composes the warning, schedules the action, and broadcasts the countdown through `wall` — "+5 minutes", "+1 minute", the final notice. In parallel it creates the nologin sentinel: `/run/nologin` under systemd (`/etc/nologin` classically), which makes `login(1)`/PAM (`pam_nologin(8)`) refuse *new* sessions and display that file's contents to the refused user. The two mechanisms cover disjoint audiences and are worth keeping straight in interviews:

```
new logins  ──► blocked by /run/nologin (pam_nologin shows its contents)
existing    ──► reached by wall broadcasts (countdown, "going down NOW")
```

A manual equivalent of the first half: create `/etc/nologin` with an explanation, then `wall < /etc/nologin` to tell the people already inside.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-n, --nobanner` | suppress the `Broadcast message from…` banner; root only |
| `-t, --timeout SECS` | per-terminal write timeout; default 300 s (modem-era legacy) |
| `-g, --group GROUP` | restrict recipients to members of GROUP (name or GID) |
| `-h, -V` | help / version |

There are no format options: content transformation is fixed (79-column wrap and pad, CRLF endings), and the banner can only appear or not.

## Usage Patterns

```bash
# Broadcast a literal message to everyone
wall "Fileserver reboot at 18:00. Save your work."
```

```bash
# The unambiguous scripted form: pipe the message
echo "Planned maintenance in 10 minutes" | wall
```

```bash
# Send the contents of a prepared notice file
wall /etc/maintenance-notice
```

```bash
# Tell only the operations group
wall -g operators "Failing over the DB primary now"
```

```bash
# Script-safe: don't hang five minutes on a wedged tty
wall -t 5 "Cache flush starting; brief UI stalls possible"
```

```bash
# Root-only: send a banner-less notice (spoof-resistant attribute: it will refuse non-root)
sudo wall -n "$(date '+%H:%M') deploy window begins"
```

```bash
# Half of a hand-rolled shutdown: block new logins and announce it
echo "Host entering maintenance at $(date '+%H:%M')" > /etc/nologin
wall < /etc/nologin
```

```bash
# Multiline message from a heredoc
wall <<'EOF'
planned work tonight:
  22:00 fsck on /scratch
  23:30 expected done
EOF
```

```bash
# Verify who would receive a message before sending (utmp view)
who            # utmp entries = wall's recipient list
users          # compact form
```

```bash
# Check the refusal behavior of -n as a normal user (observed)
wall -n "test"        # wall: --nobanner is available only for root
echo $?               # 0 — and the message still goes out with banner
```

```bash
# Pre-flight: confirm who would receive a -g broadcast before sending one
getent group operators           # member list wall -g operators will match
id -nG alice | tr ' ' '\n' | grep -x operators   # one user's membership
```

```bash
# Prove delivery behavior to yourself: block, then broadcast as user vs root
mesg n                            # in your own terminal
wall "can you see this?"          # another user's wall: you receive nothing
sudo wall "root test"             # this one gets through
mesg y
```

```bash
# Maintenance runbook pattern: log the event AND tell the humans
logger -t maintenance -p daemon.notice "fsck starting"
wall -t 5 "fsck on /scratch starting now; expect slowdowns"
```

```bash
# Stage a group broadcast: verify, send with timeout, confirm in syslog
getent group operators && wall -g operators -t 5 "Rolling restart of the API tier in 5m"
```

## Nuances and Gotchas

- **The operand file/string ambiguity.** `wall notes.txt` reads a *file* if one by that name opens; `wall "notes.txt"` (when no such file exists) sends the literal string. Same command, opposite meanings depending on the filesystem. Prefer `echo … | wall` in anything scripted.
- **`-n` is root-only and still "succeeds".** A non-root `wall -n` warns on stderr and broadcasts with banner anyway, exit 0 (verified). Never treat `wall -n` as access control.
- **`mesg n` users only get root's messages.** A user-level `wall` silently skips terminals with messages disabled. If your broadcast "missed" someone, have them run `mesg y`.
- **79-column wrap and pad.** Message text is force-wrapped at 79 chars and padded to 79 — output captured into a log file has trailing spaces on every line, which breaks naive `diff`/`grep` comparisons.
- **Graphical sessions are skipped.** utmp entries whose name starts with `:` (X display manager sessions) are deliberately excluded to avoid write errors; desktop users may not see your broadcast at all.
- **Default 300 s timeout.** One stuck terminal stalls the broadcast for five minutes. Use `-t` in any non-interactive context.
- **utmp dependence.** No utmp entries (containers, minimal chroots) → no recipients, silent success. `wall` cannot reach processes that are logged in via a mechanism that doesn't write utmp (some tmux/screen setups hide their ptys from it, depending on how the parent session was registered).
- **No exit-status contract.** The man page documents no exit codes; observed behavior is 0 for both successful delivery and the non-root `-n` refusal, 1 for usage errors (`wall: invalid timeout argument: 'abc'` → 1).
- **Broadcasts hit full-screen apps just like write does.** The banner plus padded lines land wherever the recipient's cursor is; `vim`/`less` sessions repaint over them. A wall message is an interruption, not a queue — anything critical should also go to `logger` or mail.
- **Portability.** BSD `wall` variants differ in flags (`-g` is util-linux/BSD-specific, `-n` semantics vary), and `mesg`-behavior details differ. Don't assume the util-linux flag set exists elsewhere; and `wall` is not a POSIX utility at all.
- **Group matching follows the standard group lookup.** `-g` accepts a group name or GID and matches against the user's group memberships as the system resolves them — keep that in mind when users rely on supplementary groups added after login; some session setups cache membership at login time.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Broadcast completed (also when no utmp recipients exist, and when non-root `-n` was refused — verified) |
| 1 | Usage error, e.g. invalid `-t` value (verified) |

Undocumented in the man page; the values above are observed behavior on util-linux.

## Related Commands

- [`./write.md`](./write.md) — the point-to-point sibling: one user, one terminal, conversation-style.
- [`../util-linux/mesg.md`](../util-linux/mesg.md) — the permission bit `wall` honors; how terminals accept or refuse messages.
- [`./logger.md`](./logger.md) — the "tell the *log*, not the people" alternative; pair both in maintenance runbooks.
- [`./overview.md`](./overview.md) — the bsdutils collection hub and packaging rationale.
- [`../../admin/permissions.md`](../../admin/permissions.md) — the tty ownership/group model that makes setgid-tty `wall` possible.

## Interview Questions

### Q: How does `wall` decide who receives a message?

It reads `utmp` and sends to the terminal line of every logged-in user, optionally filtered by `-g` group membership. It does not enumerate `/dev/pts` directly, which is why sessions that never registered in utmp are invisible to it, and why X display-manager entries (login names starting with `:`) are skipped. Delivery then depends on the target terminal accepting writes — `mesg n` terminals only accept messages from root.

### Q: What happens during `shutdown -h +10` — which messages go to whom, through what?

Shutdown schedules the halt, then broadcasts a countdown at intervals ("The system is going down for system halt at …!") using `wall`, so every currently logged-in terminal sees it. It also creates `/run/nologin` (systemd) so new login attempts are refused by PAM with the file's contents shown. In the last moments a final wall message goes out. The distinction matters: wall reaches *existing* sessions, the nologin file *new* ones.

### Q: Why is `wall -n` restricted to root?

The banner is the attribution mechanism — `Broadcast message from user@host` — that lets recipients judge whether a message is legitimate. A banner-less message could impersonate the system or another user, so only the superuser, who can already write to any terminal, may drop it. Notably, an unauthorized `wall -n` isn't a hard error: the tool warns and sends with the banner, still exiting 0.

### Q: You run `wall "deploy in 5"` from a script and it hangs for minutes. Diagnose.

`wall` writes to each terminal with a default 300-second timeout; one terminal with a full input buffer or a stopped reader (e.g. a suspended process over a flaky SSH connection) stalls the whole broadcast. Re-run with `-t 5` to cap per-terminal write attempts, and consider whether the stuck session should be terminated — the same wedged tty will affect `write` and any other direct-tty writer.

### Q: A user complains they never saw a broadcast everyone else got. What do you check?

Three things, in order: (1) `who`/utmp — is the user's session registered at all (some multiplexers and display sessions are not)? (2) `mesg` — is their terminal set to `n`, which only root broadcasts can override? (3) were they in the `-g` group if one was used. Each failure mode is silent — `wall` doesn't report skipped terminals.

### Q: Compare `wall`, `write`, and `logger` for notifying about a maintenance window.

`wall` is the only one that reaches humans on all terminals at once, with a banner and permission handling — the right default for imminent disruption. `write` targets one user/terminal for a conversation, so it scales badly and depends on the recipient's `mesg` setting. `logger` reaches no humans directly; it records into syslog/journald for later correlation. A good runbook uses all three: `logger` for the audit trail, `wall` for the human warning, and the nologin file to stop newcomers.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdutils/wall.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/bsdutils/)
