# mesg — control write access to your terminal by other users

## Overview

`mesg` flips your terminal between "others may write to me" and "others may not". The consumers are the classic terminal-messaging commands — `write(1)`, `talk(1)`, and broadcast tools like `wall(1)` — which respect this setting before dumping text onto someone's screen. With no argument it reports the current state; `y` allows and `n` forbids.

It ships in the `util-linux` package at `/usr/bin/mesg`. The command is ancient (mid-1970s AT&T UNIX, standard on BSD too) and — unusually for this family — is standardized by POSIX.1-2018, so its two exit statuses are contractual across implementations. It is often confused with `write` (which *sends* messages), with `wall` (broadcasts, honors the same bit), and with terminal permissions set manually via `chmod g+t`-style commands — `mesg` is the sanctioned, portable interface to that mode bit.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/mesg |
| First appeared | AT&T UNIX, mid-1970s (also classic BSD) |
| Standards | POSIX.1-2018 (`mesg`) |

## Synopsis

```
mesg [option] [n|y]
```

Common one-line forms:

```
mesg              # report: "is y" or "is n"
mesg n            # forbid write/talk on this terminal
mesg y            # allow it again
mesg n; echo $?   # 0 = allowed, 1 = not allowed (status query form)
```

## How It Works

### What actually changes: the terminal's group-write bit

A tty device node is normally mode `crw--w----` — the owner may read/write it, the `tty` group has write access (that is how the setgid `write` program, installed setgid `tty`, can open other users' terminals), and others have nothing. `mesg y` adds the group-write bit to your terminal device node; `mesg n` removes it:

```
before mesg n:  crw--w----  user tty /dev/pts/3   ← write(1) can deliver
after  mesg n:  crw-------  user tty /dev/pts/3   ← open for write fails
```

That is the entire mechanism: there is no kernel messaging registry, no daemon flag. `write`/`wall` try to open the target terminal and either succeed or get EPERM. Root is unaffected by the bit — root can always write to any terminal.

### Where the default bits come from

The `crw--w----` shape is not an accident: devpts mounts with `gid=5,mode=620` on a stock Debian system (verify with `grep devpts /proc/mounts`), so every new pty is owned by the creating user, group-owned by `tty`, and group-writable — exactly the combination that lets a setgid-`tty` messenger open it after `mesg y` has left the write bit, and blocks it after `mesg n` cleared it. `mesg` itself performs a `chmod(2)` on the device node identified from stdin; changing the bit requires owning the node, so a chmod on someone else's pty fails with EPERM — which is why messaging preference is strictly the terminal owner's decision.

### Which terminal?

The POSIX contract requires the terminal to be the one open on standard input, and util-linux `mesg` follows that: it stats the stdin device. Old BSD implementations consulted `/dev/tty` instead. The practical consequence shows in redirections: `mesg n < /dev/pts/5` affects pts/5, not the shell's controlling terminal — occasionally useful, more often a surprise.

### The write/talk/wall ecosystem around it

`mesg` regulates a small family of commands, and knowing their mechanics explains the design:

- `write user [tty]` — copies lines from your stdin to the target's terminal until EOF. Needs a specific terminal: `who` output tells you which ptys exist; the `tty` argument disambiguates users with several sessions.
- `wall` — the same delivery, broadcast to every terminal (or every terminal of a group with `wall -g`); terminals with `mesg n` are skipped rather than erroring.
- `talk`/`ntalk` — the two-pane interactive chat, mediated by a talk daemon in the classic setup; mostly extinct, but the reason `mesg y` existed in every 1990s `.profile`.

The delivery program opens the target device node; the setgid-`tty` arrangement gives it the group privilege to do so. `mesg n` removes that group-write permission, so delivery fails with EPERM before any text appears. This is also why messaging is per-terminal: nothing global is consulted — each pty's own mode decides.

### Query semantics and exit codes

Bare `mesg` prints `is y` or `is n` and encodes the answer in its exit status, which makes it usable in shell conditionals: `mesg` (0 when allowed, 1 when not, ≥2 on error). The argument forms are for changing state. This dual role — query and toggle — is standardized by POSIX, so scripts can rely on it across GNU, BSD, and busybox.

### The two failure modes in practice

`mesg` fails closed in two distinct ways, and scripts should tell them apart. With stdin a pipe or a file (`echo hi | mesg`, `mesg n < /etc/hosts`), there is no terminal to act on at all — the POSIX "error" outcome (util-linux exits 2). With a real terminal you do not own — say, after redirecting stdin onto another user's pty — the `chmod` itself fails with EPERM. Guards come in pairs: `tty -s` for "is there a terminal", and acceptance that ownership checks make foreign ptys fail by design.

### Why it still exists

Multi-user hosts, shared serial consoles, and sysadmin broadcasts are alive in server rooms even if desktop talk died. `wall` announcements ("rebooting in 5 minutes") honor `mesg n` users; login shells historically defaulted to `y` so administrators could reach everyone, while modern setups increasingly default to `n` (privacy-first) and require an explicit `mesg y` in `.profile` for write/talk to work.

The economic view: `mesg` is one bit of per-terminal policy with zero moving parts, and it composes with login infrastructure (`who`, `wall`, PAM-created ptys). Its continued POSIX presence means scripts written in 1992, 2002, and 2024 all behave the same. For interviews, the interesting part is not the command's simplicity but the whole permission chain it fronts: pty ownership, the `tty` group, setgid delivery binaries, and EPERM as the enforcement mechanism — a compact case study in how Unix composes small mechanisms instead of a messaging service.

### Defaults over the decades

The default state of a fresh terminal has shifted with culture, and the shift itself is instructive:

- 1980s–90s multi-user servers: ptys created *writable* — messaging was a workplace tool, and admins relied on reaching every session.
- 2000s: distributions began shipping login defaults of `mesg n`, driven by both privacy expectations and `talkd`'s decline.
- Today: the common state on a modern distro is `n` by default (check with bare `mesg`), and most users never notice — write/wall traffic has migrated to tmux broadcast, chat, and incident tooling.

The lesson generalizes: `mesg` did not change; the threat model and social defaults around shared terminals did. Commands that encode policy (rather than mechanism) age exactly this way.

## Options That Matter

| Option | Effect |
| --- | --- |
| `y` | Allow write access to this terminal (adds group-write on the tty) |
| `n` | Forbid write access (removes group-write) |
| *(no argument)* | Report current state; exit status 0 = allowed, 1 = not allowed |
| `-h, --help` / `-V, --version` | Help and version (non-POSIX extras) |

Note there are no long options for the y/n actions — the single letters are the standard interface.

## Usage Patterns

```bash
# Check whether your terminal currently accepts messages
mesg
```

```bash
# Silence write/wall during a long console task
mesg n
./run-long-job.sh
mesg y
```

```bash
# Status query usable in scripts: 0 = allowed
if mesg; then echo "terminal is writable by others"; fi
```

```bash
# Opt in to write/talk for this session (add to ~/.profile)
mesg y
```

```bash
# Watch the mode bit move on the actual device node
ls -l "$(tty <&-)"   # record; run mesg n; compare
mesg n; ls -l /dev/pts/3
```

```bash
# Demonstrate the block: other user cannot write to you
mesg n            # your side
# other side: write yourname pts/3  -> fails silently or errors
mesg y
```

```bash
# Affect a specific terminal via stdin redirection (POSIX stdin rule)
mesg n < /dev/pts/5
```

```bash
# Guard against noisy broadcasts on shared build boxes
mesg n && echo "messages disabled"
```

```bash
# In a script, detect "no controlling terminal" (cron/CI) before failing
tty -s || { echo "no tty, mesg pointless"; exit 0; }
mesg n
```

```bash
# Equivalent to what mesg does, shown explicitly (understand the mechanism)
ls -l /dev/pts/3          # before
mesg n
ls -l /dev/pts/3          # group-write bit gone
```

```bash
# See which terminals exist and who is on them (the write targeting problem)
who
```

```bash
# Test the whole loop on a single host with two terminals
# terminal A: mesg y   ->  terminal B: write $USER pts/N  (message arrives)
# terminal A: mesg n   ->  terminal B: write ... (fails / suppressed)
mesg y
```

```bash
# Restore the default at session end (cleanup in .bash_logout)
mesg y
```

```bash
# Idempotent quieting for root shells on shared rescue consoles
tty -s && mesg n
```

```bash
# Audit every terminal's messaging state on a shared box (as the users' owner)
for p in /dev/pts/*; do printf '%s: ' "$p"; mesg < "$p"; done 2>/dev/null
```

```bash
# Reproduce what mesg does, explicitly (mechanism, not magic)
t=$(tty) && chmod g-w "$t"   # == mesg n   (chmod g+w "$t" == mesg y)
# Query the bit without mesg: group-write char of the mode string
[ "$(stat -c %A "$(tty)" | cut -c6)" = w ] && echo writable-by-tty-group
```

```bash
# Maintenance-window silencing with guaranteed restore, even on Ctrl-C
mesg n; trap 'mesg y' EXIT; ./long-build.sh
```

## Nuances and Gotchas

- **It needs a terminal on stdin.** Run from cron or CI, stdin is not a tty and `mesg` errors out (the POSIX ">1" error status, util-linux uses 2). Scripts that call `mesg n` unconditionally in non-interactive contexts fail noisily — guard with `tty -s`.
- **`mesg n` does not stop root.** The mode bit constrains ordinary users; root bypasses file permissions. Security thinking must not treat `mesg n` as an access-control boundary — it is a courtesy switch.
- **Each pty has its own state.** tmux panes, screen windows, and every SSH connection get fresh terminal devices with the default mode. Enabling `y` in one pane does nothing for others; the setting belongs in shell startup files.
- **The mechanism is a chmod in disguise.** Anything that changes your tty's mode bits (or its ownership) outside `mesg` defeats or fakes its answer. Conversely, restoring a tty with `stty sane` does *not* restore mesg state — permissions and line discipline are separate axes.
- **Group membership matters.** Write access flows through the `tty` group: the `write` binary is setgid `tty` and needs group-write on your terminal. On systems where messaging tools are absent or the group is mishandled, `mesg y` alone may not revive `talk`.
- **Portability is strong but not absolute.** POSIX fixes behavior for `y`/`n` and exit statuses; some historical implementations printed different query strings and BSD variants used `/dev/tty`. Modern util-linux, BSD, and busybox all honor the contract.
- **Bare `mesg` output is not parsed.** The human string is `is y`/`is n`; scripts must branch on `$?`, not on scraping the text.
- **Redirection surprises.** Because POSIX fixes the terminal to stdin, `mesg n < somewhere-else` modifies a different tty than the visual one. In pipelines, stdin may be the pipe — another reason the tool errors loudly when there is no terminal.
- **Reconnecting screens/serial consoles.** A serial console or `screen`/`minicom` session has a tty like any other; `mesg n` there silences broadcasts too — sometimes unwanted on consoles where `wall` warnings (reboots!) are exactly what you want.
- **State is not persisted anywhere.** A new login, a new SSH connection, a reboot — each starts from the pty default. Anything that must hold across sessions belongs in shell startup files; `mesg` itself remembers nothing.
- **It cannot target other users' terminals.** `mesg` changes *your* terminal (or the one on stdin). Setting mode bits on someone else's pty is a filesystem-permission operation outside mesg's scope — by design, messaging preferences belong to the terminal's owner.
- **Pipelines break it.** Inside `some_cmd | sh` or under a redirected stdin, the error status (2) propagates and trips `set -e`/`pipefail`; put `mesg` calls on their own line with the terminal as stdin.
- **devpts mount options are the fleet default.** Remounting devpts with `mode=600` (no group write) makes every new pty start closed — a system-wide lever that lives in fstab/kernel cmdline, not in mesg; a distro changing devpts options changes mesg's visible default with no mesg change at all.

## Exit Status

- `0` — write access is (now) allowed; for a bare query, the terminal currently allows messages.
- `1` — write access is (now) forbidden; for a bare query, it currently does not.
- `>1` (util-linux: 2) — error: no terminal on stdin, wrong argument, or permission problem.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`users and groups`](../../admin/users-groups.md) — the tty-group/setgid mechanism that makes write access work.

## Interview Questions

### Q: What does mesg y actually change on disk?

The permission bits of your terminal device node: it adds group-write (e.g. `crw--w----` to `crw-rw----`-style group access on `/dev/pts/N`). That is all — no daemon state, no registry. `write(1)` (setgid `tty`) then succeeds in opening your terminal, which is why the `tty` group's existence is part of the mechanism.

### Q: What are mesg's exit statuses and why do they matter for portability?

POSIX fixes them: 0 when messages are allowed, 1 when not, greater than 1 on error. The bare (no-argument) invocation doubles as a status query, so `if mesg; then ...` works identically on GNU util-linux, BSD, and busybox. Parsing the human-readable `is y` string instead would be the non-portable mistake.

### Q: A user says mesg n did not stop an admin from writing to their terminal. Why?

Root bypasses file permission checks, and the entire mechanism is the terminal's mode bit. `mesg n` is a courtesy control against peer users, not a security boundary. Similarly, broadcast tools may skip denied terminals rather than error, so "no message" can mean suppression, not delivery failure.

### Q: Why would mesg fail inside a cron job or CI runner?

POSIX requires the terminal to be open on standard input; in cron/CI stdin is not a tty, so mesg cannot resolve a device to modify and exits with the error status (util-linux: 2). The correct pattern is `tty -s && mesg n` — guard on terminal presence first. This also explains why the setting must live in interactive startup files, not global cron scripts.

### Q: You open three tmux panes and run mesg y in one. A colleague's write reaches only that pane. Explain.

Every pane is a distinct pty with its own device node and its own permission bits, initialized independently. mesg y changed one node only. Terminal messaging state is per-terminal, not per-user — which is why opt-in setups put `mesg y` in `.profile`/`.tmux.conf` hooks rather than typing it per pane.

### Q: How does write(1) know which of your terminals to deliver to, and where does mesg fit?

It does not know automatically: the caller names the user and optionally the tty (from `who`/`w` output, which list every terminal with its device). Without a tty argument, write picks one of the user's active terminals — and each candidate may independently allow or forbid delivery via its own mesg state. mesg is therefore not a user-level switch but a per-terminal valve; multi-session users are messaged only on the terminals that opt in.

### Q: Why is /usr/bin/write setgid tty, and what breaks if that bit is removed?

The setgid bit lets write open *other* users' terminals: it runs with the `tty` group's privilege, and terminals are group-owned by `tty`. mesg y grants group-write to that group specifically so this delivery path works. Remove the setgid bit and every write/wall to other users fails with permission errors regardless of mesg — a real-world regression when admins "fix" suspicious setgid binaries without understanding the terminal messaging chain.

### Q: mesg is nearly 50 years old and still in POSIX. What design properties kept it relevant?

Minimalism with a contract: two letters, two meaningful exit codes, one file-permission effect, no daemon or config. The contract (POSIX) froze the interface so scripts survive across implementations, while the mechanism (plain mode bits) never rots — it works identically on ptys invented decades after the command. It is a good interview example of "small mechanism, long life": features decay, but well-scoped permissions primitives tend to outlive their ecosystems.

### Q: Where does the default state of a new terminal come from, and how would you flip it fleet-wide?

From the pty allocator and login environment, not from mesg itself: new terminals inherit whatever mode the creating process (sshd, login, tmux) leaves. Fleet-wide policy therefore lives in startup files (`.profile` with `mesg n` or `y`), PAM/session configuration, or tmux/sshd hooks — not in a system-wide mesg setting, because none exists. The interview point: mesg changes one terminal's bits now; persistent policy must hook the process that creates terminals.

### Q: Implement mesg in shell. What does the exercise teach?

`mesg n` is `chmod g-w "$(tty)"`, `mesg y` is `chmod g+w "$(tty)"`, and a query is a group-bit test on `stat -c %A`. The exercise exposes the whole stack: the terminal is an ordinary device node, the "policy" is one permission bit, enforcement is EPERM at `open(2)` time inside write(1), and the portability contract is just which bit plus which exit codes. The edges fall out too: `tty` fails without a controlling terminal (the cron trap), and chmod on a foreign pty needs ownership — precisely mesg's two error modes.

### Q: What enforces mesg at the kernel level, and can anything besides root bypass it?

Ordinary VFS permission evaluation when the messenger opens the device node for writing: with group-write cleared, a non-owner non-root process gets EPERM — the setgid-`tty` binary provides group membership, not root privilege. Anything acting with the file owner's identity or CAP_DAC_OVERRIDE bypasses it: root, and any sufficiently privileged daemon. So mesg is enforced by DAC on a device node — correct against peer users, powerless against privileged processes, which is exactly why it is a courtesy control rather than a security boundary.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/mesg.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
