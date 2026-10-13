# inittab — The Master Configuration (inittab(5))

## Overview

`/etc/inittab` is the entire configuration surface of sysvinit's PID 1: a line-oriented table in which every boot-time action, every getty, every UPS reaction, and every shutdown hook is declared. There is no daemon to configure and no schema to compile — init re-reads this file live on `telinit q`, and every line is independently meaningful. Because the grammar has been stable since AT&T System III (1982–83), a line written for Solaris in 1995 is still syntactically valid on Debian in 2024; the *vocabulary of actions* is the part every administrator must know cold.

This page dissects the grammar field by field, then documents every action in the canonical set with a realistic example, annotates the actual Debian bookworm `inittab` block by block, and closes with field-tested recipes (serial consoles, autologin, display managers) and the mistakes that most often produce a machine that "boots to nothing." The authoritative source for every claim here is `inittab(5)` as shipped in `sysvinit-core`; where behavior is distro-specific it is marked as such.

## Grammar: id:runlevels:action:process

Every non-comment, non-empty line has four colon-separated fields:

```text
id:runlevels:action:process

# comments start with '#'; blank lines are ignored.
# long process lines may be continued with a trailing backslash.
```

### Field 1 — id (1–4 characters)

A unique identifier for the entry. The only hard rules are uniqueness within the file and a length limit of four characters (older systems allowed two). By overwhelming convention the id for a getty entry is the tty name suffix (`1` for `tty1`, `S0` for `ttyS0`), because init historically used the id as the utmp record identifier for the entry's processes — so `who` output and session bookkeeping look sane. Nothing enforces the convention; colliding with it merely makes accounting confusing.

### Field 2 — runlevels (a list, often empty)

The runlevels *for which this entry is active*, written as a plain concatenation of characters from `0123456789abcsS` — no separators (`2345` means "levels 2, 3, 4, and 5"; `s` and `S` both mean single-user). Which actions consult this field is action-specific, and getting this wrong is the most common inittab bug:

| Actions that USE the runlevel field | Actions that IGNORE it (field usually left empty) |
|---|---|
| `respawn`, `wait`, `once`, `off`, `ondemand` | `sysinit`, `boot`, `bootwait`, `initdefault` |
| | `powerwait`, `powerfail`, `powerokwait`, `powerfailnow` |
| | `ctrlaltdel`, `kbrequest` |

The ignored actions are event-driven — they fire on boot or on a signal, not on "entering runlevel N" — so their runlevel field is conventionally empty (`si::sysinit:...`). Writing a runlevel there is harmless but misleading.

### Field 3 — action (the verb)

Selects *when* and *how* the process runs. The complete canonical set follows in the next section; there are exactly fifteen of them in modern sysvinit, and no others.

### Field 4 — process (the command)

A shell command line. init runs it as `/bin/sh -c "<process>"` with init's standard child environment (`INIT_VERSION`, `RUNLEVEL`, `PREVLEVEL`, `CONSOLE`) — so pipes, redirects, and quoting all work, and quoting rules are shell rules. One special prefix exists: if the process field begins with `+`, init performs **no utmp/wtmp accounting** for that entry. This exists for gettys that manage their own session records (double-accounting is otherwise easy); you will see it in some historical configs, and it is a historical wart rather than a feature to build on.

### Lexical details worth knowing

- A line longer than fits comfortably can be continued by ending it with a backslash, exactly as in a Makefile or shell script — the continuation is joined before parsing, so the colon-field counting happens on the joined line.
- Comments start with `#` at the beginning of a line. There is no trailing-comment syntax: a `#` in the middle of a process field is a shell comment *inside the command*, which is usually not what the author intended.
- Fields are separated by `:` and there is no escaping mechanism for a literal colon — quote it inside the shell command if a command genuinely needs one.
- The parser is forgiving in exactly one direction: lines it cannot make sense of are logged to the console and skipped at boot, they do not stop init. A typo disables one entry, not the machine — a deliberately small blast radius that contrasts with, say, fstab.

## The Complete Action Set

Fifteen actions, each with a realistic line and the semantics that distinguish it from its neighbors. This table is the heart of the page — most interview questions about inittab are questions about one row of it.

| Action | Fires when | init waits? | Repeats? | Example |
|---|---|---|---|---|
| `respawn` | Process exits, while in a listed runlevel | no | yes, forever (throttled) | `1:2345:respawn:/sbin/getty 38400 tty1` |
| `wait` | Entering a listed runlevel | yes | once per entry | `l2:2:wait:/etc/init.d/rc 2` |
| `once` | Entering a listed runlevel | no | once per entry | `cl:3:once:/usr/local/bin/logrotate-boot` |
| `boot` | During system boot | no | once | `bo:boot:/usr/local/bin/mark-boot` |
| `bootwait` | During system boot | yes | once | `bw::bootwait:/usr/sbin/ntpdate gw` |
| `off` | Never (placeholder) | — | — | `9:3:off:/usr/bin/legacy-daemon` |
| `ondemand` | `telinit a/b/c` requested | per-process | once per request | `od:a:ondemand:/usr/local/bin/diag-shell` |
| `initdefault` | Initial boot | — | — | `id:2:initdefault:` |
| `sysinit` | First at boot, before boot/bootwait | yes | once | `si::sysinit:/etc/init.d/rcS` |
| `powerwait` | SIGPWR (power failed) | yes | each event | `pf::powerwait:/etc/init.d/powerfail start` |
| `powerfail` | SIGPWR, without waiting | no | each event | `pn::powerfail:/usr/local/bin/notify-power` |
| `powerokwait` | Power restored (SIGPWR clear) | yes | each event | `po::powerokwait:/etc/init.d/powerfail stop` |
| `powerfailnow` | UPS battery nearly empty | yes? (see note) | each event | `pw::powerfailnow:/etc/init.d/powerfail now` |
| `ctrlaltdel` | SIGINT from console Ctrl-Alt-Del | yes | each press | `ca:12345:ctrlaltdel:/sbin/shutdown -t1 -a -r now` |
| `kbrequest` | Special key combo (SIGWINCH) | no | each press | `kb::kbrequest:/bin/echo "kbd request"` |

Notes that separate correct answers from half-credit:

- `respawn` versus `wait` is the fork in the road: `respawn` means "keep it alive" (supervision, however primitive), `wait` means "block the runlevel change until it finishes" (ordering, however serial). `once` is `wait` without the blocking; `boot`/`bootwait` are `once`/`wait` pinned to the boot moment and ignoring runlevels.
- `off` exists so an entry can be disabled without deleting it — the inittab equivalent of commenting a cron line while keeping it visible.
- `ondemand` is the trick row: runlevels `a`, `b`, and `c` are *pseudo*-levels. `telinit a` does **not** leave the current runlevel; it merely executes the `a`-marked `ondemand` entries once. The current runlevel is unchanged, and later `telinit a` runs them again. It is a one-shot admin hook channel, and it is nearly forgotten — mentioning it in an interview reliably signals deep familiarity.
- `initdefault` takes the runlevel field as its *value*: `id:2:initdefault:` means "boot to level 2". If missing, init asks for a runlevel on the console at boot — a fallback most admins have never seen because `initdefault` is essentially never absent.
- The power family is driven by UPS monitoring software signaling init (SIGPWR and friends); which of the four fires depends on the event reported. They are wired on Debian to the `powerfail` script via the default lines shown below. `powerfailnow` specifically means "power is out and the battery is nearly empty — shut down NOW," and typically invokes a faster shutdown.
- `ctrlaltdel` receives the SIGINT that the keyboard driver generates for the three-finger salute. On servers, the standard hardening move is to either remove the line (the key combination then does nothing) or point it at a logging wrapper; on workstations, keep `shutdown -r now` for sanity. Debian's default uses `-a`, which consults `/etc/shutdown.allow` to restrict *who* (which logged-in users) may trigger it from the console.
- `kbrequest` fires when the console keyboard driver signals init that a special key combination was pressed — `Alt-UpArrow` under the default kbd keymap. It is a debug/toy action in practice, but it is part of the canonical set and worth being able to name.

## The Debian Bookworm inittab, Annotated

The stock Debian `inittab` (from `sysvinit-core`) is short — roughly 60 lines, half of them comments. Here it is, abridged to every functional line, with commentary:

```text
# The default runlevel: Debian boots to 2 (see runlevels.md for why 2 and not 3)
id:2:initdefault:

# Boot-time system initialization: the rcS phase (fsck, mounts, udev, loopback).
si::sysinit:/etc/init.d/rcS

# What to do in single-user mode. Debian runs sulogin and WAITS for it.
~~:S:wait:/sbin/sulogin

# Runlevel scripts: one 'wait' line per level 0..6.
l0:0:wait:/etc/init.d/rc 0
l1:1:wait:/etc/init.d/rc 1
l2:2:wait:/etc/init.d/rc 2
l3:3:wait:/etc/init.d/rc 3
l4:4:wait:/etc/init.d/rc 4
l5:5:wait:/etc/init.d/rc 5
l6:6:wait:/etc/init.d/rc 6

# Three-finger salute: -a checks /etc/shutdown.allow, -t1 gives 1s grace.
ca:12345:ctrlaltdel:/sbin/shutdown -t1 -a -r now

# (commented-out example) kbrequest hook:
#kb::kbrequest:/bin/echo "Keyboard Request -- edit /etc/inittab to let this work."

# UPS integration: Debian's powerfail script handles all three events.
pf::powerwait:/etc/init.d/powerfail start
pn::powerfailnow:/etc/init.d/powerfail now
po::powerokwait:/etc/init.d/powerfail stop

# getty lines. Note the runlevel gating:
#   tty1 comes up in 2,3,4,5;  tty2..tty6 only in 2 and 3.
# The 'id' is the tty suffix so utmp records line up.
1:2345:respawn:/sbin/getty 38400 tty1
2:23:respawn:/sbin/getty 38400 tty2
3:23:respawn:/sbin/getty 38400 tty3
4:23:respawn:/sbin/getty 38400 tty4
5:23:respawn:/sbin/getty 38400 tty5
6:23:respawn:/sbin/getty 38400 tty6

# Commented examples for a serial terminal (T0) and a modem line (T3).
#T0:23:respawn:/sbin/getty -L ttyS0 9600 vt100
#T3:23:respawn:/sbin/mgetty -x0 -s 57600 ttyS3
```

Four distro-specific details to notice, because they differ across distributions and often across machines:

1. **`~~:S:wait:/sbin/sulogin`** — the `~~` id and the explicit single-user entry mean that dropping to level S produces a *password-protected* single-user shell via sulogin. Not every distribution includes this line; some rely on rc1.d scripts or on the kernel.
2. **`id:2:initdefault:`** — Debian's default multiuser level is 2 (with 2–5 identical by convention); Red Hat-era defaults used 3 (text) or 5 (X11). The runlevel *numbers* have no intrinsic meaning; they mean what the distribution's scripts make them mean.
3. **getty runlevel gating** — `tty1` survives at levels 4–5 (where a display manager usually owns the console) while `tty2`–`tty6` exist only at 2–3. If you boot to level 4 on stock Debian and find fewer text consoles, this is why.
4. **`-t1 -a` on ctrlaltdel** — the grace second (`-t1`) lets active processes flush, and `-a` (allow-file check via `/etc/shutdown.allow`) is Debian's small concession to multi-user safety on the console.

## Recipes

### Serial console getty

The standard recipe for a headless box or a hypervisor console:

```text
# 115200 8N1, carrier ignore (-L), vt100 terminal type
T0:2345:respawn:/sbin/agetty -L 115200 ttyS0 vt100
```

Interplay with the kernel matters: `console=ttyS0,115200 console=tty0` on the kernel command line sends kernel messages to both, with the *last* `console=` becoming `/dev/console` (where init's boot entries print). For a truly headless system, make the serial port the last `console=` *and* add the getty line, and remember that getty and kernel console should be the same device if you expect login over the same link you watch kernel messages on. Embedded ARM boards follow the identical recipe with their tty names — `ttyAMA0` (older PL011 UARTs) or `ttyS0`/`ttyTHS1` depending on the SoC:

```text
S0:2345:respawn:/sbin/agetty -L 115200 ttyAMA0 vt100
```

The `-L` flag (ignore carrier detect) is the difference between "works on the bench" and "works in the rack without a null-modem's DCD line." Full flag coverage is in `agetty(8)`.

### Autologin (kiosk/embedded pattern)

agetty's `-a user` option logs a user in without a password — appropriate only on physically secured kiosks and test rigs:

```text
a1:2345:respawn:/sbin/agetty -a kiosk --noclear tty1 vt100
```

The `--noclear` keeps boot messages on screen behind the session, which kiosk builders often want for support. The security note writes itself: anyone with keyboard access *is* that user; never autologin root.

### A display manager or X on a console

The classical pattern for keeping X alive on a specific tty in level 5:

```text
x:5:respawn:/usr/sbin/lightdm
```

respawn does the supervision: X crashes, the entry restarts. It is crude — no dependency on a working DBus, no restart backoff beyond init's respawn throttle — but it is genuinely how X stayed up on sysvinit systems for decades, and it explains the `tty1`-only-in-2345 comment above: level 5 was historically "X owns a console" territory.

### Adding a service via inittab respawn

For a personal daemon that must never die, an inittab respawn line is a legitimate zero-dependency supervisor:

```text
my:2345:respawn:/usr/local/bin/myapp -c /etc/myapp.conf
```

Compare this with an init script (a proper LSB script gives you `start`/`stop`/`status`, `update-rc.d` integration, and ordering via headers — see [init-scripts.md](./init-scripts.md)) or a real supervisor (runit's `runsv` gives logging and control pipes — see [stages-services.md](../runit/stages-services.md)). The inittab line wins on zero moving parts and loses on everything else: no status verb, no clean stop without `telinit q`, no per-service log handling. Use it knowingly.

## Files and Runtime Reconfiguration

init consults exactly one configuration file, `/etc/inittab`, plus the control channel `/run/initctl` (the modern name for the legacy `/dev/initctl` FIFO) through which `telinit` sends commands. Everything else — `.depend.*` files, `rc*.d` directories — is consumed by `rc`, not by init. The exported child environment (`INIT_VERSION`, `RUNLEVEL`, `PREVLEVEL`, `CONSOLE`) is documented on the boot-sequence page.

Live changes follow a strict procedure:

1. Edit `/etc/inittab` (syntax-check by eye; init will log and skip lines it cannot parse).
2. `telinit q` — init re-reads the file (the `q`/`Q` telinit command, delivered over the initctl pipe).
3. New `respawn` entries start immediately if their runlevel is active; removed ones are killed; changed ones are restarted.

Practical corollary: to *stop* a service you started via respawn, first remove or `off` the line and run `telinit q`, then kill the process — otherwise init will simply restart it (possibly after the throttle delay, which makes the bug confusing to diagnose). Conversely, a respawn entry is a cheap guard against your own fat-fingered kills during maintenance.

## Common Mistakes

- **`respawn` with an empty runlevel field.** The entry is active in *no* runlevel, so it never runs — silent, and the most common "my respawn line does nothing" cause. Write `2345` or at least the levels you mean.
- **`wait` in a hot path.** Every `wait` entry blocks the runlevel change; two minutes of `bootwait` is two minutes added to every boot, once per entry. Audit `wait` lines for anything that can hang (DNS lookups, network waits).
- **Duplicate ids.** Two entries with id `1` — one getty, one custom respawn — produce undefined accounting and confusing `who` output; keep ids unique and tty-derived where applicable.
- **Forgetting `telinit q` after edits.** The file is read at boot and on `telinit q` — never polled. "I edited inittab and nothing happened" is almost always this.
- **Server ctrlaltdel.** Leaving `shutdown -r now` wired to Ctrl-Alt-Del on a multi-user console server invites accidental reboots from anyone at the keyboard (via iLO/KVM or the physical console). Harden it: remove the line, or gate with `/etc/shutdown.allow` and `-a`.
- **Disabling a respawn service by killing it.** init wins; the process returns (after the throttle). Remove the line and `telinit q` first — this ordering mistake generates a remarkable number of confused incident notes.
- **Assuming runlevel semantics.** `2` is not "multiuser without network" on Debian (that is a Red Hat meaning). The number means only what the `lN` lines and `rcN.d` content make it mean.

## Interview Questions

### Q: Walk me through the four fields and one subtlety per field.

`id` — up to four chars, must be unique; convention ties it to the tty name so utmp records line up. `runlevels` — a concatenated list from `0-6 a b c s S` with no separators, and ignored entirely by event-driven actions (`sysinit`, `boot*`, `power*`, `ctrlaltdel`, `kbrequest`). `action` — one of fifteen verbs; the runlevel-driven ones (`respawn`/`wait`/`once`) are re-evaluated on every runlevel change, the boot ones only at boot. `process` — a `/bin/sh -c` command line with init's exported environment, and a leading `+` suppresses init's utmp/wtmp accounting for the entry.

### Q: What are the ondemand runlevels a/b/c actually for, and what does `telinit a` do to the current runlevel?

Nothing — that is the point. Levels a, b, c are pseudo-levels: `telinit a` executes the entries marked `a:...:ondemand` once and leaves the current runlevel untouched. It is a one-shot administrative hook channel — run diagnostics, trigger a maintenance action, exercise a command — without disturbing services. Because respawn entries for a/b/c exist only "in" those pseudo-levels, they are started by the telinit request, not supervised across it.

### Q: You replaced getty with a binary that crashes instantly. What does init do, exactly?

It respawns, throttles, and waits. init restarts the entry; when respawn attempts exceed the rate limit (historically on the order of ten per two minutes), it delays roughly five minutes before trying again, logging the throttling. So the machine degrades gracefully: no getty on that tty, but no spin-loop either, and the console records the complaint. The operational lesson is that a broken respawn entry is visible in logs as repeated throttled-respawn messages — check `/var/log/boot` and syslog for them.

### Q: What is the `+` prefix on a process field, and where would you encounter it?

It suppresses init's utmp/wtmp accounting for that entry — no `LOGIN_PROCESS`/session records are written. It exists for getty-class programs that do their own session accounting, to avoid double records. You encounter it in old serial-terminal configurations and in some initramfs/embedded inittabs; it is a historical wart, harmless but puzzling if unexplained.

### Q: How do you add a service that must always run — inittab respawn entry or /etc/init.d script — and what decides it?

Decide by what you need beyond "keep it running." The respawn line gives you eternal restart with zero moving parts but no start/stop/status verbs, no ordering metadata, no clean disable (you must edit the line and `telinit q`), and no logging story. An LSB init script gives you the full lifecycle verbs, `update-rc.d` enablement, ordering via headers (or `.depend.*` under insserv), and integration with `invoke-rc.d`/`service` — at the cost of writing and maintaining a script. For anything a colleague might have to operate, the init script is the professional choice; the respawn line is the kiosk/embedded choice. Mentioning that supervision here is throttled-crude versus runit/s6's per-service supervisors scores the comparison point.

### Q: Where does telinit send its commands, and what changed there recently-ish?

Over the initctl channel: `/run/initctl` in modern sysvinit (3.x and late 2.8x), formerly the FIFO at `/dev/initctl`. `telinit` is literally a symlink to init; invoked as telinit it switches into command mode and writes the request (runlevel change, `q` re-read, single-user, and so on) for init to consume. If you find a system where `telinit` hangs, check that the pipe exists and that the running PID 1 is actually sysvinit — a container or chroot with the wrong PID 1 (or none listening on the pipe) fails in exactly this way.

## References

- [inittab(5) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/inittab.5.en.html) — the normative grammar and action definitions this page expands.
- [init(8) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/init.8.en.html) — boot ordering, respawn throttling, environment, initctl.
- [telinit(8) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/telinit.8.en.html) — the runtime control interface, including `q`.
- [agetty(8) — util-linux man page, Debian bookworm](https://manpages.debian.org/bookworm/util-linux/agetty.8.en.html) — flags used in every recipe above (`-L`, `-a`, `--noclear`, terminal types).
- [shutdown(8) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/shutdown.8.en.html) — the `-a`/`/etc/shutdown.allow` and `-t` semantics behind the ctrlaltdel line.

## Cross-References

- [The sysvinit Boot Sequence](./boot-sequence.md) — when and in what order these entries execute at boot.
- [Runlevels in Depth](./runlevels.md) — what "a runlevel" is, mechanically, behind the runlevels field.
- [Getty and Terminal Management](./getty-terminals.md) — deeper coverage of the respawn workhorse.
- [Shutdown and Halt Mechanics](./shutdown-halt.md) — the shutdown(8) side of ctrlaltdel and runlevel 0/6.
- [systemd — Targets and Runlevels](../systemd/targets-runlevels.md) — the declarative successor to this file's action set.
- [Init Systems Hub](../README.md) — section map and reading order.
