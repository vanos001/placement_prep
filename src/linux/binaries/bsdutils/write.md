# write — send a message to another user's terminal

## Overview

`write` opens a point-to-point text channel between two logged-in users: everything you type is copied, line by line, onto the other person's terminal until you press Ctrl-D. It ships in the `bsdextrautils` package at `/usr/bin/write` on Debian bookworm (util-linux upstream; it lived in `bsdutils` before Debian 11, and the split into `bsdextrautils` is purely packaging). It is one of the oldest pieces of the userland still in daily shapes — a direct descendant of the "two terminals, one message loop" design of early UNIX.

You reach for `write` when you need someone's attention *now*, in-band on a shared host: "I'm about to restart the service you're testing against." It is often confused with `wall` (one sender, all terminals — broadcast, not conversation), with `mesg` (the receive-side switch that decides whether `write` may touch your terminal at all), and with `talk` (the full-duplex, split-screen successor that solves the interleaving problem `write` inherently has).

| Field | Value |
| --- | --- |
| Package | bsdextrautils (Debian bookworm; in bsdutils before Debian 11) |
| Man section | 1 |
| Path | /usr/bin/write |
| First appeared | Version 6 AT&T UNIX |
| Standards | POSIX.1-2018 (`write`) |

## Synopsis

```
write user [ttyname]
```

Common one-line forms:

```
write alice                     # write to alice (her first logged-in tty)
write alice pts/2               # target a specific terminal
echo "done" | write alice       # send a one-shot note instead of typing
mesg n                          # (on the receiving side) refuse write/talk
```

## How It Works

### Establishing the channel

When you run `write alice`, the program resolves the recipient through `utmp` (the login-records database) and opens her terminal device for writing — possible for a normal user because `write` is installed setgid `tty`, and the tty group normally holds write permission on terminals. The recipient's terminal needs the group-write bit, which is exactly what `mesg y` sets and `mesg n` removes.

The first thing delivered is a banner so the recipient knows where the traffic is coming from:

```
Message from alice@server1 on pts/3 at 14:02 ...
```

After that, `write` copies your standard input to her terminal, one line per newline. There is no protocol, no framing, no synchronization — just bytes appended to someone else's screen, which is why full-screen programs on the receiving end (editors, pagers) get visually clobbered.

### Ending and replying

The session ends when you type your terminal's EOF character (Ctrl-D) or send an interrupt (Ctrl-C); the recipient sees `EOF` on their screen, marking the end of the conversation. If the other user wants to reply, they run `write` back — there is no built-in channel back to you. Because both sides type independently into each other's screens, output interleaves; the classic etiquette below exists to make the mess readable.

### The conversation loop

Once connected, `write` runs a dumb copy loop — your stdin, line by line, to their tty. A two-way exchange looks like this on each screen (both users wrote each other):

```
alice's terminal                         bob's terminal
────────────────                         ──────────────
Message from alice@srv on pts/3 ...      Message from bob@srv on pts/4 ...
                                         alice: looking at the flaky worker?
alice: looking at the flaky worker?      bob: yes, restarting it now
bob: yes, restarting it now              alice: o
alice: o                                 bob: oo
bob: oo                                  EOF
EOF
```

Each side sees the other's lines interleaved with whatever their own foreground programs print — the interleave problem the table below contrasts with `talk`. Ctrl-D ends your side (the other sees `EOF`); Ctrl-C also terminates `write` without a graceful `EOF` marker on the far end. There is no buffering worth mentioning: one newline, one delivered line.

### Sender-side details

The banner timestamps with the connection moment and names *your* terminal; from there `write` copies until EOF or interrupt. Because the copy loop reads whatever stdin provides, a redirected stdin (`echo msg | write bob`) delivers a one-shot note — the interactive conversation only exists when stdin is a terminal. Lines are delivered raw: a line longer than the recipient's terminal width wraps on *their* screen exactly as their tty wraps it, and no width normalization (unlike `wall`'s 79-column discipline) is applied.

### Multiple terminals

A user logged in from several places gets a warning and delivery to the first terminal in the login list — the observed util-linux behavior prints the chosen tty plus the other locations, e.g.:

```
alice is logged on more than one place.
You are connected to "pts/2".
Other locations are:
"pts/4"
```

Pass the terminal explicitly to override: `write alice pts/4`. The operand syntax `user ttyname` is what POSIX specifies and what the util-linux implementation accepts.

### Permission model

The receive side is a single mode bit on the terminal device node, toggled with `mesg(1)`:

```
mesg y:  crw--w----  user tty /dev/pts/3   # write/talk can deliver
mesg n:  crw-------  user tty /dev/pts/3   # open-for-write fails for non-root
```

Writing to a `mesg n` terminal fails with a permission error — unless the sender is root, who bypasses the bit entirely. Blocking `write` therefore also blocks `talk` (it delivers through the same tty), and the only unilateral escape from root broadcasts is logging out. The setgid-tty mechanism and the mode bits are covered in detail in the [`mesg`](../util-linux/mesg.md) page.

### write vs wall vs talk

| | `write` | `wall` | `talk` |
| --- | --- | --- | --- |
| Audience | one user/terminal | all terminals | one user |
| Direction | half-duplex (one sender at a time) | one-way broadcast | full-duplex split screen |
| Requires utmp | yes | yes | talkd lookup |
| Blocked by `mesg n` | yes (root exempt) | yes (root exempt) | yes |
| Interleaving hazard | high | n/a | solved by design |

## Options That Matter

`write` has essentially no options — only `--help`/`--version`. Its "options that matter" are really the operands and the surrounding commands:

| Operand/tool | Effect |
| --- | --- |
| `user` | recipient's login name, resolved via utmp |
| `ttyname` | optional terminal (e.g. `pts/2`) when the user is logged in more than once |
| `mesg y/n` | receive-side switch on the target terminal (see [`mesg`](../util-linux/mesg.md)) |
| Ctrl-D / Ctrl-C | ends your side; recipient sees `EOF` |

## Usage Patterns

```bash
# Classic two-way exchange: both run write on each other
write bob
# (bob replies with: write alice)
```

```bash
# Pick the terminal when the user is logged in twice
who | grep alice       # see which pts is active
write alice pts/4
```

```bash
# One-shot notification without an interactive session
echo "Your nightly build finished, 3 failures" | write bob
```

```bash
# Prepend your name on each line — standard etiquette when both sides type
write bob
#   alice: checking the logs now
#   alice: o                       <- "over", your turn
```

```bash
# Receive side: see and change your write permission
mesg                # "is y" / "is n"
mesg n              # block write (and talk) from non-root senders
```

```bash
# Ping everyone instead (broadcast, honors the same mesg bit)
wall "Queue processor restarting in 5 minutes"
```

```bash
# Root can reach a user who has messages turned off
sudo write bob pts/2 "Need your session for 5 min"
```

```bash
# End the exchange; the recipient sees EOF
<Ctrl-D>
```

```bash
# Per-login defaults: quiet people put this in their shell profile
grep -n mesg ~/.profile        # mesg n, optionally after signing in
```

```bash
# Split-screen note passing to yourself across two terminal panes
write $USER pts/1      # from pts/0 — messages appear on pts/1
```

```bash
# Notify first, log second: persistence lives in syslog, not scrollback
echo "Migration paused, need your call" | write bob && \
  logger -t migration -p daemon.warning "bob notified about pause"
```

```bash
# Find the right terminal to target before writing
who | awk '$1 == "bob" {print $1, $2}'     # login + tty pairs for bob
```

```bash
# Fan-out by hand when several people need the same one-shot note
for u in alice bob carol; do echo "Deploy paused, stand by" | write "$u" 2>/dev/null; done
# (or just wall once — broadcast handles the mesg/tty iteration for you)
```

## Nuances and Gotchas

- **Interleaving is the design, not a bug — but it hurts.** Two simultaneous `write` sessions mean lines from both sides land in one scrolling stream with no attribution. The long-standing etiquette: prefix your lines with the recipient's name or your initials, type in short lines, use a lone `o` ("over") to hand over the turn and `oo` ("over and out") to finish — or switch to `talk`, which splits the screen per side.
- **`mesg n` blocks you silently-ish.** Delivery to a tty with messages disabled fails with a permission error; users can only be reached by root. If your message "didn't arrive", that's the first thing to check.
- **First-tty selection.** With multiple logins, util-linux `write` warns and writes to the first utmp entry — which may be a stale SSH hop, not the session in front of the user. Always disambiguate with the tty operand when it matters.
- **Full-screen apps get clobbered.** Lines land wherever the recipient's cursor is; a `vim` session repaints and "eats" part of your message. This is inherent to raw tty writes — `talk` confines the damage to its own window.
- **You can `write` yourself.** `write $USER` opens a channel to your own terminal; occasionally useful for split-screen note-taking across panes, usually just confusing.
- **Not a logging tool.** Messages vanish with the terminal scrollback. For anything that must persist, use `logger`; for one-to-many, `wall`; for interactive, `talk`.
- **POSIX surface, util-linux behavior.** POSIX fixes the `user [terminal]` operand form and exit statuses; flag sets and multi-tty behavior vary across implementations (BSD `write` prompts `to whom?` in some variants instead of warning). Don't script around prompts.
- **Container/minimal systems.** No utmp entries → "user not logged on" errors even for valid accounts, because `write` has no way to find a terminal to open.
- **The sender's terminal matters too.** The banner names *your* tty, resolved from utmp; from a cron job or CI runner (no controlling terminal) the attribution is missing or misleading, and some implementations refuse to run. Terminal messaging is a logged-in-user tool, not a service-notification API — that's `logger`/mail territory.
- **`mesg` defaults are not contractual.** Whether a fresh login accepts messages (`mesg y`) depends on the distro's default tty mode and PAM stack; on stock Debian it is y, but hardened images ship `mesg n` in skeleton profiles. Never assume the bit is set — check before relying on write-based workflows.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Message stream delivered (conversation ended normally) |
| 1 | Recipient not logged on, tty unwritable (`mesg n`), or usage error |

Per POSIX, `write` exits 0 on success and >0 on failure; util-linux uses 1 for the failure cases above.

## Related Commands

- [`./wall.md`](./wall.md) — broadcast variant of the same tty-writing mechanism.
- [`../util-linux/mesg.md`](../util-linux/mesg.md) — the terminal permission bit `write` depends on; setgid-tty mechanics explained.
- [`./logger.md`](./logger.md) — when the message must persist: syslog/journald instead of a screen.
- [`./overview.md`](./overview.md) — the bsdutils collection hub and packaging rationale.
- [`../../admin/permissions.md`](../../admin/permissions.md) — file/device permission model behind "who may open your terminal".

## Interview Questions

### Q: How does `write` find and open the recipient's terminal, and what can stop it?

It resolves the login name through utmp to a terminal line, then opens `/dev/pts/N` for writing using its setgid-`tty` privilege. Delivery stops if the user ran `mesg n` (the terminal's group-write bit is gone, so the open fails for non-root), if the user isn't in utmp at all, or — with multiple logins — if the first-listed tty isn't the one the user is watching. Root bypasses the mesg restriction.

### Q: Explain the etiquette conventions around write sessions and why they exist.

`write` is half-duplex with no framing: both sides type into one shared visual stream. Conventions developed to compensate — prefix lines with the recipient's name (or your initials) so interleaved text stays attributable, type short lines, mark the end of your turn with `o` ("over") and the conversation with `oo` ("over and out"), and finish with Ctrl-D so the other side sees `EOF`. They exist because the tool provides no turn-taking of its own; `talk` was invented to solve this with a split-screen full-duplex design.

### Q: When would you pick `write` over `wall`, and `talk` over both?

`write` when a single person needs an interrupting, possibly conversational message — e.g. warning the one developer whose deploy you're about to break. `wall` when everyone must know at once (broadcasts, shutdown warnings). `talk` when the exchange becomes a real back-and-forth: it gives each side a dedicated screen half and keystroke-level turn independence, eliminating the interleaving that makes long `write` sessions unreadable.

### Q: What actually changes on the filesystem when a user runs `mesg n`?

The terminal device node loses its group-write bit: `crw--w---- user tty` becomes `crw------- user tty`. Delivery by `write`, `wall`, or `talk` requires opening that node for writing; non-root senders lack permission, while root and the setgid-`tty` tools combined with the mode decide the outcome — and only root's messages still get through. `mesg y` restores the bit.

### Q: A colleague is logged in on three terminals and your write went to the wrong one. What happened and what do you do?

util-linux `write` delivered to the first terminal in the utmp login list and printed a warning naming it plus the other locations — the first entry isn't necessarily the active session. Re-run with the explicit terminal operand (`write alice pts/4`), after checking `who` to see which session is attached to the user's foreground work.

### Q: Why does this ancient tool still matter for interviews about modern systems?

Because it teaches the primitives that still underpin terminal I/O and permissions: utmp as the session registry, device-node permission bits as an inter-user access control mechanism, setgid binaries as targeted privilege delegation, and signal/EOF-driven line protocols. Every terminal-multiplexer, notification, or broadcast feature since is a re-implementation of the same ideas with better ergonomics.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdextrautils/write.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/bsdutils/)
