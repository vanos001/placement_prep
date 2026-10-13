# setterm — set terminal attributes via escape sequences and console ioctls

## Overview

`setterm` configures terminal behavior from scripts. It has two distinct
mechanisms under one name: (1) options that compute and print a terminal
*escape sequence* to stdout based on the current `TERM` (colors, bold,
clear screen, cursor visibility) — these work anywhere the receiving
terminal understands the sequence, including xterm and ssh sessions; and
(2) options that issue *Linux console ioctls* on the virtual terminal
(screen blanking, VESA powersave, kernel message level, console bell,
screen dumps) — these only work on the real VT console. It ships with
the `util-linux` package (Debian bookworm) at `/usr/bin/setterm`.

`setterm` is often confused with `tput` (generic terminfo queries and
capes), with `stty` (line-discipline settings like echo and baud — a
different layer), and with `dmesg`'s console-level controls (setterm can
change where kernel messages appear).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/setterm |
| First appeared / lineage | BSD-descended console tool, long part of util-linux |
| Standards | None — terminfo sequences plus Linux VT ioctls |

## Synopsis

```
setterm [options]
```

Common one-line forms:

```
setterm -clear                       # clear screen (escape output)
setterm -bold on -underline on       # attribute changes (escape output)
setterm -blank 10                    # console blanking after 10 min (VT only)
setterm -msg off                     # silence kernel messages on console (VT only)
```

## How It Works

### Escape-sequence options: write to stdout

For display-oriented options, setterm looks up the appropriate control
sequence for `$TERM` (or `--term`) and writes it to standard output. The
program itself opens no terminal — a pipe receives the raw bytes:

```bash
$ TERM=xterm setterm -clear | cat -v
^[[H^[[2J
$ TERM=xterm setterm -bold on | cat -v
^[[1m
```

That stdout-based design is why `setterm -clear` is a common shell-script
substitute for `clear`, and also why you must *not* blindly append its
output to files that will later be parsed.

### Console-only options: ioctls on the VT

A second family does not print anything; it acts on the virtual console
through `ioctl(2)` calls — blanking timers, VESA powersave states, the
kernel `printk` console log level, bell pitch/length, keyboard repeat,
and text dumps read from the `/dev/vcsaN` devices. On a non-console
`TERM` these refuse with a message (observed):

```bash
$ TERM=xterm setterm -blank 5
setterm: terminal xterm does not support --blank
$ echo $?
0
$ TERM=xterm setterm -msglevel 3
setterm: terminal xterm does not support --msglevel
```

Note the exit status: **0** despite the error — a scripted trap.

### Option families at a glance

```
┌───────────────────────┬───────────────────────────┬──────────────────┐
│ family                │ examples                  │ works via        │
├───────────────────────┼───────────────────────────┼──────────────────┤
│ attributes/colors     │ -bold -underline -reverse │ escape to stdout │
│                       │ -foreground -ulcolor      │                  │
│ screen control        │ -clear -reset -initialize │ escape to stdout │
│                       │ -default -store -tabs     │                  │
│ cursor/keys           │ -cursor -appcursorkeys    │ console ioctl /  │
│                       │ -repeat -linewrap         │ escape           │
│ console power/timing  │ -blank -powersave         │ VT ioctl only    │
│                       │ -powerdown -blength       │                  │
│ kernel messages       │ -msg -msglevel            │ VT ioctl only    │
│ console snapshots     │ -dump -append -file       │ /dev/vcsa only   │
└───────────────────────┴───────────────────────────┴──────────────────┘
```

Options are processed left to right, so one invocation can combine an
attribute change and a screen action.

## Options That Matter

### Display and attributes (escape output)

| Option | Effect |
| --- | --- |
| `-clear[=all\|rest]` | Clear screen (and home cursor); `=rest` clears below cursor. |
| `-bold`, `-half-bright`, `-blink`, `-underline`, `-reverse`, `-inversescreen` | Toggle text attributes, `on\|off`. |
| `-foreground <color>`, `-background <color>` | Set default colors (`black red green yellow blue magenta cyan white` or `default`). |
| `-ulcolor [bright] <color>` | Underlined-text color. |
| `-cursor on\|off` | Show/hide the cursor. |
| `-reset`, `-initialize`, `-default`, `-store` | Power-on reset, init string, defaults, save-current-as-default. |

### Screen and keyboard (escape/ioctl mix)

| Option | Effect |
| --- | --- |
| `-tabs[=n...]`, `-clrtabs[=n...]`, `-regtabs[=1-160]` | Tab stop management. |
| `-linewrap on\|off` | Wrap-at-margin behavior. |
| `-repeat on\|off` | Keyboard auto-repeat (console). |
| `-blength[=0-2000]`, `-bfreq[=hz]` | Bell duration (0 = off) and pitch. |

### Console-only (VT ioctl)

| Option | Effect |
| --- | --- |
| `-blank[=0-60\|force\|poke]` | Minutes of inactivity before the console blanks; `poke` unblanks. |
| `-powersave on\|vsync\|hsync\|powerdown\|off` | VESA powersaving modes. |
| `-powerdown[=0-60]` | VESA powerdown interval. |
| `-msg on\|off`, `-msglevel 0-8` | Whether kernel messages print on the console, and at which log level. |
| `-dump[=n]`, `-append`, `-file <name>` | Snapshot the text of VT *n* from `/dev/vcsa` into a file (needs access to those devices). |

## Usage Patterns

```bash
# Clear the screen in a script without depending on tput
setterm -clear
```

```bash
# Highlight warnings in a report piped to a color-capable pager
echo "ERROR: quota exceeded" | setterm -bold on >/dev/tty; cat
```

```bash
# Turn off the console bell system-wide (a classic laptop rc tweak)
setterm -blength 0
```

```bash
# Blank the console after 10 idle minutes (run on a VT, e.g. from rc or getty)
setterm -blank 10
```

```bash
# Silence kernel printk on the console without touching syslog
setterm -msg off
# (equivalent to lowering the console log level; dmesg still logs)
```

```bash
# Reset a terminal wedged by binary output
setterm -reset
```

```bash
# Save current attributes as defaults, then restore them later
setterm -store && setterm -bold on -red; setterm -default
```

```bash
# Snapshot the text of virtual console 1 (root; reads /dev/vcsa1)
setterm -dump 1 -file /tmp/vt1.txt
```

```bash
# Force a different terminfo entry than TERM suggests
TERM=unknown setterm -term xterm -clear
```

```bash
# Redraw a corrupted ssh session display
setterm -initialize
```

## Nuances and Gotchas

- **Two incompatible mechanisms, one binary.** The display family works
  over ssh and in tmux (it is just bytes on stdout); the power, message
  and dump family works only on the Linux VT console. Running the second
  family remotely does nothing except print a refusal.
- **Unsupported features still exit 0.** Observed: `setterm: terminal
  xterm does not support --blank` followed by exit status 0 — scripts
  cannot detect failure from the exit code and must not try.
- **Escape output goes wherever stdout goes.** `setterm -clear >
  /var/log/app.log` writes `ESC[H ESC[2J` into your log. Redirect to the
  terminal (`>/dev/tty`) or keep it on stdout deliberately.
- **`-blank` is not a screen lock.** It blanks the VT backlight/console
  drawing; under X, Wayland or a desktop session the DPMS/lock policy
  belongs to the display server, not setterm. Machines "blanked" this
  way are neither locked nor suspended.
- **`--term` overrides the environment, not reality.** Emitting xterm
  sequences at a `linux` console (or vice versa) prints garbage; the
  option is for mismatched environments, not for forcing features.
- **Dumps need device access.** `-dump`/`-append` read `/dev/vcsaN`,
  which is root or tty-group territory; they capture text only, and only
  from the *console* virtual terminals.
- **Options are processed in order** and later ones can undo earlier
  ones (`-bold on -bold off`); keep invocations minimal and ordered.
- **`setterm` says nothing when stdout is not a terminal** — the escape
  bytes go to the pipe/file silently. Combine with `test -t 1` if a
  script must decide.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Options processed — including cases where a console-only feature printed "does not support" (observed). |
| non-zero | Usage errors: unknown option, invalid argument values. |

Do not script against exit codes for feature detection; parse stderr or
gate on `$TERM`/tty type instead.

## Related Commands

- [`dmesg`](./dmesg.md) — kernel messages whose console visibility `-msg`/`-msglevel` control.
- [`mesg`](./mesg.md) — another per-tty housekeeping switch (who may write to your terminal).
- [`more`](./more.md) — a consumer of terminal attributes that setterm can preconfigure.
- [Internals](../../internals.md) — where the VT console and tty layer sit in the kernel.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: Why does setterm -blank work on the console but appear to do nothing over SSH?

`-blank` (and `-powersave`, `-powerdown`, `-msglevel`, `-dump`) are
implemented as ioctls against the Linux virtual terminal, not as escape
sequences. Over ssh your terminal is a pty handled by a terminal
emulator; there is no VT to ioctl, so setterm refuses (and, notably,
still exits 0). Screen dimming over remote sessions is the client
emulator's business.

### Q: What is the difference between setterm, tput and stty?

`setterm` is a fixed menu of terminal behaviors, implemented as either
terminfo-derived escape output or console ioctls. `tput` is a generic
terminfo query engine — any capability of any terminal, but no console
ioctls. `stty` configures the tty *line discipline* (echo, control
characters, flow control) — a lower layer that does not touch rendering
at all.

### Q: A script writes setterm -clear into a log file by accident. What happened and how do you prevent it?

The script redirected stdout to the log while setterm's entire action
*is* stdout — the escape bytes `ESC[H ESC[2J` landed in the file.
Prevent by writing to the terminal explicitly (`setterm -clear
>/dev/tty`), gating on `test -t 1`, or reserving escape output for
contexts where stdout is a terminal.

### Q: How do you stop kernel messages from overprinting a console getty login prompt?

`setterm -msg off` (or lower `-msglevel`) on that console: it adjusts
the console printk behavior via ioctl so kernel messages stop hitting
the VT. It is runtime-only — it does not change `kernel.printk` sysctl
persists — and `dmesg` still records everything.

### Q: Why is setterm -blank not a screen lock, and what actually locks a console?

Blanking only stops drawing on the VT; the shell and keyboard remain
fully live. Locking requires a mechanism that gates input and requires
reauthentication (vlock, or a display-manager lock under X/Wayland).
Conflating the two is a security-relevant misconception.

### Q: How would you capture the current text of another virtual console from a script?

`setterm -dump N -file out.txt` as root — it reads the text-mode screen
content of VT N through the `/dev/vcsaN` devices. Limits: text only (no
pixels), console VTs only, and device permissions apply. It is handy for
headless debugging of serial-console-style setups.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/setterm.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
