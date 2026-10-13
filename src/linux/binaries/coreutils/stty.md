# stty — print or change terminal line settings

## Overview

`stty` ("set teletype") reports and reconfigures the *line discipline* of a
terminal device: baud rate, window size, special control characters
(`intr`, `eof`, `erase`...), and the dozens of mode flags that decide whether
your terminal echoes characters, maps CR to NL, or passes raw bytes. It is
the tool you reach for when a program leaves the terminal in a broken state
(`stty sane`), when you need a script to read a password without echo, or
when configuring a real serial console.

It ships in the Debian `coreutils` package. On modern Debian/Ubuntu it is
`/bin/stty` (historically) and `/usr/bin/stty` — with merged-`/usr` these are
the same file — and because rescue environments depend on it, it is present
in initramfs images and single-user shells. It descends from BSD and is
standardized by POSIX, so it exists essentially everywhere, though flag
coverage differs between GNU, BSD, and busybox implementations.

Two neighbours are often confused with it: `tty` (which only prints the
terminal's filename) and `termios`-level wrappers in scripting languages.
`stty` is the only one of the three that can change anything.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/stty` (`/bin` symlink on merged-`/usr`) |
| First appeared / lineage | PWB/UNIX and BSD lineage; in GNU coreutils |
| Standards | POSIX.1-2017 |

## Synopsis

```text
stty [-F DEVICE | --file=DEVICE] [SETTING]...
stty [-F DEVICE | --file=DEVICE] [-a|--all]
stty [-F DEVICE | --file=DEVICE] [-g|--save]
```

```bash
stty -a               # print all current settings on stdin's terminal
stty -g               # print settings as a single restore-able token
stty rows 50 cols 120 # set window size
stty -F /dev/ttyS0 115200   # configure a serial port
```

## How It Works

A Unix terminal is a line of software between your keyboard and the
application: the **line discipline**, configured through the `termios` API.
`stty` is a thin command-line wrapper around `tcgetattr(3)`/`tcsetattr(3)`
on the target device (stdin by default, `-F DEVICE` otherwise).

```text
keyboard ──▶ [line discipline] ──▶ application read()
             │  icrnl   CR→NL        ▲
             │  icanon  line editing │ isig: ^C → SIGINT
             │  echo    show chars   │ raw mode: none of this
             └─ tty driver ──────────┘
```

In the default **cooked** (canonical) mode the discipline buffers a line,
performs editing with `erase` (`^?`) and `kill` (`^U`), translates CR to NL
(`icrnl`), maps `^C` to `SIGINT` (`isig`), and echoes input. In **raw** mode
(`stty raw -echo`) all of that is disabled: bytes flow one at a time with no
editing, no echo, and no signal generation — which is how full-screen
programs and password prompts take over the terminal.

```bash
$ stty -a                      # inside an interactive shell
speed 38400 baud; rows 0; columns 0; line = 0;
intr = ^C; quit = ^\; erase = ^?; kill = ^U; eof = ^D; eol = <undef>;
start = ^Q; stop = ^S; susp = ^Z; rprnt = ^R; werase = ^W; lnext = ^V;
...
icrnl ixon -iutf8
```

Every line is meaningful: `speed` is the line rate (mostly relevant for real
serial ports; ptys report a nominal 38400 or 115200), `rows`/`columns` come
from the kernel's window-size structure (what `tput` and editors consult),
the `intr`/`erase`/... assignments are the remappable special characters,
and the long flag lines are the mode bits (`-icanon` style minus means off).

The window size is a separate `TIOCGWINSZ`/`TIOCSWINSZ` ioctl pair:

```bash
$ stty size            # rows and columns, in that order
0 0
$ stty rows 40 cols 100; stty size
40 100
```

`-g` serialises the entire termios state into one colon-separated token that
`stty` can replay later — the standard save/restore idiom in scripts:

```bash
$ stty -g
500:5:bf:8a3b:3:1c:7f:15:4:0:1:0:11:13:1a:0:12:f:17:16:0:0:...
```

## Options That Matter

### Reporting

| Option | Effect |
|---|---|
| `-a`, `--all` | Print all settings in human-readable form |
| `-g`, `--save` | Print all settings as one `stty`-replayable token |
| `size` | Print `rows cols` |
| `-F DEV`, `--file=DEV` | Operate on DEV instead of stdin |

### Modes and sizes

| Setting | Effect |
|---|---|
| `sane` | Restore a reasonable cooked terminal (the rescue command) |
| `raw` / `-raw` | Disable canonical processing, signals, flow control |
| `cooked` | Back to normal canonical mode |
| `-echo` / `echo` | Stop/show typed characters (password entry) |
| `rows N` / `cols N` | Set window size (some tools need `stty cols` after resize) |
| `speed N` | Set line rate (serial hardware) |
| `intr CHAR` | Remap the interrupt character, e.g. `stty intr ^]` |
| `min N` / `time N` | Non-canonical read blocking rules |

### Common flag toggles

| Flag | Effect |
|---|---|
| `icrnl` / `-icrnl` | Translate CR to NL on input |
| `ixon` / `-ixon` | Software flow control (`^S`/`^Q`) |
| `onlcr` | Translate NL to CR-NL on output |
| `iutf8` | Input is UTF-8 (affects erase handling of multibyte chars) |

## Usage Patterns

```bash
# Recover a terminal mangled by binary output or a crashed editor
stty sane
```

```bash
# After SSH connection drops mid-vim: reset + sane, or just `reset`
stty sane; clear
```

```bash
# Read a secret without echo, restoring state on exit
SAVED=$(stty -g); stty -echo; read -r PASS; stty "$SAVED"
```

```bash
# Save and restore around a raw-mode program in a script
RAW=$(stty -g); stty raw -echo; ./interactive-tool; stty "$RAW"
```

```bash
# Check your window size from a script (mirrors $COLUMNS only if exported)
stty size | cut -d' ' -f2
```

```bash
# Make ^] the interrupt key when ^C is intercepted by an app
stty intr ^]
```

```bash
# A stuck terminal: ^S froze output via software flow control
# type ^Q to resume — or permanently: stty -ixon
```

```bash
# Configure a real serial console (115200 8N1)
stty -F /dev/ttyS0 115200 cs8 -cstopb -parenb
```

```bash
# One non-blocking-ish read in non-canonical mode (min 1, no wait timer)
stty -icanon min 1 time 0
```

```bash
# Verify what a legacy mainframe link expects: no CR translation
stty -F /dev/ttyUSB0 -icrnl -onlcr raw
```

```bash
# Fix the "my backspace prints ^?" case over a weird SSH client
stty erase ^?
```

## Nuances and Gotchas

- **stty acts on stdin, not stdout.** In a script or pipeline its stdin may
  not be the terminal: `stty size | cat` fails. Use `stty -F /dev/tty size`
  or `stty size < /dev/tty` when inside pipelines. This is the single most
  common scripting mistake with stty.
- **`^S` freeze is flow control, not a hang.** With `ixon` on, `^S` stops
  output and `^Q` resumes. Novices kill their shell; the fix is one keypress
  or `stty -ixon` in your profile.
- **`stty sane` ≠ factory reset.** It applies a conservative cooked profile;
  window size, speed, and UTF-8 handling may still need attention. `reset`
  (from ncurses) does a fuller reinitialisation.
- **rows/cols vs `$LINES`/`$COLUMNS`.** The kernel window size and the shell
  variables are independent; after resizing, some remote programs need
  `stty rows N cols N` or `kill -WINCH` semantics to catch up. Old SSH
  sessions were notorious for stale sizes.
- **raw mode swallows `^C`.** With `-isig` there is no SIGINT from the
  keyboard; a hung raw program can only be killed from another terminal.
  Scripts that set raw mode must trap and restore.
- **Portability.** GNU stty supports `-F`, `sane`, and hundreds of flags;
  busybox stty covers the common subset; BSD stty uses `-f` instead of `-F`
  and lacks some flags. Stick to `-a`, `-g`, `raw`, `-echo`, `sane` for
  portable scripts.
- **`stty` without a terminal fails, exit 1**: `stty: 'standard input':
  Inappropriate ioctl for device` — in cron jobs there is no tty at all.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | Settings printed or applied successfully |
| 1 | stdin (or `-F` device) is not a terminal, or a setting was invalid |

```bash
$ stty size < /etc/hostname
stty: 'standard input': Inappropriate ioctl for device
$ echo $?
1
```

## Related Commands

- [`tty`](./tty.md) — print the terminal's filename; the read-only sibling.
- [`test`](./test.md) — `[ -t 0 ]` checks whether stdin is a terminal.
- [bash](../../shell/bash.md) — `read`, job control, and how shells interact with the discipline.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: A process crashed and left the terminal typing everything on one line with no prompt echo. What happened and what do you do?

The program died without restoring the termios state — typically left in raw
or no-echo mode. `stty sane` reapplies a canonical profile (echo, icanon,
icrnl, sane special characters) and usually fixes it instantly; `reset` is
the heavier alternative when the terminal state is worse. The lesson for
scripts: capture `stty -g` before changing modes and restore it in a trap.

### Q: How do you read a password in a shell script without it appearing on screen?

`stty -echo` around the read, then restore. The careful version captures
`SAVED=$(stty -g)`, sets `-echo`, reads, and replays `stty "$SAVED"` even on
interruption, because a plain `stty echo` afterwards loses unrelated state
the caller may have set. Bash's `read -s` is a convenience wrapper over the
same termios operation.

### Q: Why does `stty size | cat` print an error, and what is the fix?

stty queries the terminal on its *stdin*, and inside a pipeline its stdin is
the pipe, not a tty. Redirect explicitly: `stty size < /dev/tty`, or name the
device with `stty -F /dev/pts/3 size`. Understanding that stty's operand is
"the terminal on file descriptor 0" — not "my terminal" — explains most
surprises in non-interactive contexts.

### Q: What is the difference between cooked and raw mode, concretely?

Cooked (canonical) mode: the line discipline buffers by line, offers erase
and kill editing, translates CR to NL, echoes, and generates signals from
`^C`/`^\`/`^Z` (`isig`). Raw mode turns off canonical processing, echo,
signal generation, and usually flow control, delivering bytes as typed. It
is what editors, password prompts, and interactive TUIs request, and what a
forgotten `stty raw -echo` leaves behind.

### Q: What does `stty -g` give you that `stty -a` does not?

`-a` output is for humans and is not reliably parseable across
implementations. `-g` emits a single opaque token that the same `stty`
accepts as input to restore the exact state — including flags your script
never touched. It is the only portable save/restore mechanism, and it is
what well-behaved terminal-mangling scripts use in their cleanup traps.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/stty.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
