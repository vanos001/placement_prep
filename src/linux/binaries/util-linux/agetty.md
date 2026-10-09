# agetty — open a tty port, print the login prompt, run login

## Overview

`agetty` is the program that turns a raw terminal device into a login
prompt. It opens a tty (virtual console, serial port, or any device), sets
line discipline and speed, displays `/etc/issue`, waits for a username, and
execs `login(1)` with that name. Every text-mode login screen you see on a
Debian/Ubuntu console is an `agetty` instance that systemd started on your
behalf via `getty@.service`. It ships in the `util-linux` package at
`/usr/sbin/agetty`.

It descends from the classic BSD `getty` ("get tty") of the init/serial
lineage, which is also why the name history is confusing: traditional init
systems ran a program called `getty`, Debian ships util-linux's improved
variant `agetty` ("alternative getty"), and the package installs a symlink
`/usr/sbin/getty -> agetty` so old habits and old scripts keep working. It
is often confused with `login` (which it execs, but never replaces in
memory), with `getent` (unrelated name-resolution tool), and with display
managers, which handle graphical logins by different machinery.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/agetty (symlink /usr/sbin/getty) |
| First appeared | getty in BSD; agetty in util-linux (1990s) |
| Standards | BSD lineage; behavior governed by termios(3) and login(1) |

## Synopsis

```
agetty [options] <line> [<baud_rate>,...] [<termtype>]
agetty [options] <baud_rate>,... <line> [<termtype>]
```

Main one-line forms:

```
agetty tty1 38400 vt100          # console on virtual terminal 1
agetty -L ttyS0 115200 vt100     # serial console, no carrier detect
agetty -a ubuntu tty1            # autologin on console 1
agetty --reload                  # make running agettys re-read /etc/issue
```

`<line>` may be a bare name relative to `/dev` (`ttyS0`) or a full path
(`/dev/ttyS0`). `<termtype>` becomes the `TERM` value for the login session.

## How It Works

### Lifecycle of one login prompt

```
        systemd (getty@.service)  or  /etc/inittab (sysvinit)
                       │  spawns
                       ▼
   ┌──────────────────────────────────────────────┐
   │ agetty  <line> <baud> <term>                 │
   │  1. open /dev/<line>, become session leader  │
   │  2. vhangup(), set termios: speed, 8N1, ...  │
   │  3. print /etc/issue (+ escape expansion)    │
   │  4. print "host login:" and read username    │
   │  5. exec login -f/-h ... -- <username>       │
   └──────────────────────────────────────────────┘
                       │  exec (same PID)
                       ▼
                  login(1)  ->  shell
   # when the shell exits, login exits, systemd respawns agetty
```

Step 2 is where agetty earns its keep: it resets the line discipline to a
known-good state (`-c` skips that), optionally cycles through a list of baud
rates until the terminal answers (`-m`/`-s`), and handles the messy serial
details (carrier detect, flow control, CR/LF translation) that plain
`login` never could. `vhangup()` (or the `-R` variant) yanks other
processes off the tty so the previous session cannot keep reading it.

### The issue file

`/etc/issue` (or the files given with `-f`, which may be directories to walk)
is printed *before* the login prompt, with backslash escapes expanded:

```
$ agetty --show-issue -f /etc/issue      # inspect without touching a tty
Debian GNU/Linux 12 \n \l

# escapes:  \s kernel name   \n nodename   \r release
#           \v version       \m machine    \o domain
#           \l tty line      \4 IPv4 of the host  \6 IPv6
#           \d date          \t time       \u sessions  \U sessionsmax
```

`-i` suppresses the issue entirely; `-N` suppresses the newline before it;
`-J` (noclear) suppresses the screen clear that agetty normally does on
virtual consoles — important when you want boot messages or panic output to
remain visible at the login prompt.

### Baud handling on serial lines

```
agetty -L -s 115200,9600 ttyS0 vt100
#        │  └── keep the line's current speed if it is in the list
#        └───── ignore carrier (modem) line; local line
#  the comma list is tried in order: useful when the peer speed is unknown
#  -m reads the CONNECT message from modems to *extract* the actual speed
```

For virtual consoles the baud argument is ignored in practice (the kernel
console has no UART), but sysvinit-era `/etc/inittab` lines still carry it,
which is why examples always show a number.

### How systemd drives it

On a systemd system there is no static list of gettys. `systemd-getty-generator`
starts one `agetty` per `console=` kernel parameter (so a serial console
kernel argument automatically gets a serial agetty) and `getty@ttyN` for the
virtual consoles, honoring `logind`'s configuration. To change flags
globally you override `getty@.service`:

```
# /etc/systemd/system/getty@.service.d/override.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty -o '-p -- \\u' --noclear %I $TERM
```

The `-o '-p -- \u'` idiom passes the username to `login -p`, so the prompt
asks for the password only.

## Options That Matter

| Option | Effect |
| --- | --- |
| `<line>` | tty name relative to /dev, or a full path |
| `<baud>,...` | One or more speeds; with -m/-s the list is cycled |
| `<termtype>` | Sets TERM for the login session |
| `-a, --autologin <user>` | Skip the username prompt; exec login as that user |
| `-n, --skip-login` | Do not ask for a username (must be combined with -l) |
| `-l, --login-program <file>` | Replacement for /bin/login |
| `-o, --login-options <opts>` | Extra arguments passed to the login program |
| `-f, --issue-file <list>` | Alternative issue files/directories (comma list) |
| `-i, --noissue` | Do not display an issue file |
| `-J, --noclear` | Do not clear the screen before the prompt |
| `-N, --nonewline` | Do not print a newline before the issue text |
| `-L, --local-line[=<mode>]` | Force/permit local line; ignore carrier detect |
| `-m, --extract-baud` | Parse modem CONNECT to learn the speed |
| `-s, --keep-baud` | Keep the existing speed if it appears in the list |
| `-w, --wait-cr` | Wait for CR/lf from the peer before continuing |
| `-8, --8bits` | Assume 8-bit clean tty; no parity stripping |
| `-U, --detect-case` | Turn on upper-case-only terminal detection |
| `-t, --timeout <sec>` | Give up (exit) if nobody logs in within the timeout |
| `-r, --chroot <dir>` | Chroot before running the login program |
| `--reload` | Signal running agettys to re-read the issue file |
| `--show-issue` | Print the current issue text and exit |
| `--list-speeds` | Print supported baud rates and exit |

## Usage Patterns

```bash
# What systemd actually runs on console 1
systemctl cat getty@tty1.service | grep ExecStart
# ExecStart=-/sbin/agetty --noclear %I $TERM
```

```bash
# Serial console at 115200, carrier ignored (the classic rescue line)
sudo agetty -L 115200 ttyS0 vt100
```

```bash
# Autologin for a kiosk or VM image (do NOT do this on multiuser hosts)
sudo agetty -a kiosk --noclear tty1 linux
```

```bash
# Custom login program with fixed options, no username prompt
sudo agetty -n -l /usr/local/bin/restricted-shell tty1
```

```bash
# Pass the typed username through to login with -p (password-only prompt)
sudo agetty -o '-p -- \\u' -J tty3 linux
```

```bash
# Annoyance fix: keep boot messages visible at the login screen
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
printf '[Service]\nExecStart=\nExecStart=-/sbin/agetty -J %%I %%TERM\n' \
  | sudo tee /etc/systemd/system/getty@tty1.service.d/noclear.conf
```

```bash
# Preview what a user would see, without occupying the tty
agetty --show-issue -f /etc/issue
```

```bash
# Refresh all running agettys after editing /etc/issue
sudo agetty --reload
```

```bash
# Discover valid baud rates before writing an inittab-style entry
agetty --list-speeds
```

```bash
# Dial-in server line with hardware flow control and a hard timeout
sudo agetty -h -t 60 -m 115200,57600,9600 ttyS1 vt220
```

```bash
# Debug a serial console end-to-end from another box
#   peer:      agetty -L 115200 ttyS0
#   here:      screen /dev/ttyUSB0 115200
```

## Nuances and Gotchas

- **getty vs agetty naming.** Debian's `/sbin/getty` is a symlink to
  agetty; documentation, inittab examples, and muscle memory say "getty"
  while the process name is `agetty`. BSDs run an unrelated `getty(8)`.
- **`-a` autologin is a footgun.** It execs login with the `-f` flag, which
  bypasses authentication for that user. Confine it to VM images, kiosks,
  and serial consoles you physically control; logind sessions created this
  way are still audited as the autologin user.
- **`--noclear` trade-off.** Clearing the screen hides the last boot
  messages; not clearing leaks old output (and occasionally passwords typed
  at the console before the prompt appeared) to the next person at the
  keyboard. Datacenter images often ship `-J` for debuggability.
- **Serial: carrier detection hangs.** Without `-L`, agetty waits for the
  Data Carrier Detect line; a null-modem cable without DCD wired up makes
  agetty sit silent forever. The `-w` flag similarly waits for a
  carriage return — good against line noise, fatal if the peer never sends one.
- **Escapes are agetty's, not printf's.** `/etc/issue` escapes (`\n`, `\4`,
  `\l`) are expanded by agetty itself; they will not expand in `cat` or in
  issue files printed by other getty implementations.
- **TERM matters.** Omitting `<termtype>` on serial lines leaves `TERM`
  unset for login, and tools like `vi` misbehave. Always pass the terminal
  type for remote/historical terminals.
- **Not for pseudo-terminals.** agetty is for real tty devices; SSH logins
  are spawned by `sshd` allocating a pty, which never involves agetty.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | The login session ended (the login program returned) |
| >0 | Fatal error: bad device, no such line, failed to exec login program |

agetty itself never stays in the process tree for the session — after the
prompt it is *replaced* by login via `exec(2)`, so the PID that systemd
supervises is the same one from prompt to logout.

## Related Commands

- [`../../admin/systemd.md`](../../admin/systemd.md) — getty@.service, systemd-getty-generator, and why gettys respawn
- [`../../admin/users-groups.md`](../../admin/users-groups.md) — what login(1) does with the username agetty collected
- [`choom`](./choom.md) — another tiny util-linux process-launcher wrapper
- [util-linux overview](./overview.md) — session and terminal tools in this collection

## Interview Questions

### Q: Explain the difference between agetty, login, and a display manager.

agetty owns the *device*: it opens the tty, resets termios, prints the
banner, and collects a username. It then execs `login(1)`, which performs
authentication (PAM), sets up the session environment, and starts the shell.
A display manager does the equivalent for graphical sessions — X/Wayland
selection and PAM — but talks to virtual terminals directly and starts an X
session instead of a shell. Only one of the three strategies should own a
given tty.

### Q: Why does agetty call vhangup and become a session leader?

`vhangup()` forcibly disconnects any other processes that still have the tty
open — without it, the previous session (or a sniffer) could keep reading
keystrokes. Becoming a session leader and acquiring the tty as controlling
terminal is what makes job control (Ctrl-Z, SIGINT delivery) and login
accounting (`utmp`) work for the new session.

### Q: How does a serial console get a login prompt on a systemd system with zero configuration?

The kernel command line's `console=ttyS0,115200n8` is visible in
/proc/console; `systemd-getty-generator` reads it and instantiates
`getty@ttyS0.service`, whose ExecStart is agetty with the right serial
settings. That is why adding a `console=` parameter is sufficient to get a
serial login on modern Debian — no inittab editing required.

### Q: A system shows a login prompt but typing produces no reaction on the serial line. Diagnose with agetty knowledge.

Classic causes map to agetty flags: the peer's cable lacks the DCD wire and
agetty is waiting for carrier (fix: `-L`); the speed is mismatched (fix: a
baud list with `-s`, or `-m`); flow control is mismatched (`-h` on only one
side); or the line discipline is wedged from a previous session without a
proper hangup. The `\l` escape in /etc/issue showing the wrong tty name is a
quick tell that agetty was started on the wrong device.

### Q: What does `agetty --reload` do and when do you need it?

It signals each running agetty instance to re-read its issue file, so
edits to /etc/issue appear on existing console logins without restarting
getty@.service units (which would terminate in-flight sessions). It only
refreshes the *prompt text* — options like -a or -l are fixed at spawn time
and need a service restart.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/agetty.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
