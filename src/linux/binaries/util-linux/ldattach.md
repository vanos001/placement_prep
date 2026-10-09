# ldattach — attach a line discipline to a serial line

## Overview

`ldattach` attaches a **line discipline** to a serial (tty) device and then goes into the background holding it. A line discipline is a kernel-side processing module stacked between the raw tty driver and userspace: it decides how bytes flowing through a serial port are interpreted — as a terminal (the default `N_TTY`), as SLIP network packets, as PPP frames, as PPS time pulses, and so on. `ldattach` is the tool that performs the `TIOCSETD` ioctl from the command line, optionally configuring the serial parameters (speed, parity, stop bits) first. Ships in the `util-linux` package (Debian bookworm) at `/usr/sbin/ldattach`.

Reach for it when a kernel subsystem expects a serial line with a non-default discipline: SLIP over a legacy serial link, a GPS receiver whose PPS (pulse-per-second) line needs `N_PPS`, GSM multiplexing (`N_GSM0710`), serial-CAN adapters (`N_SLCAN`), or obscure protocols like `GIGASET_M101`. It is often confused with `stty` (termios settings only, no discipline switching), with `pppd` (which manages the PPP discipline itself and does not need `ldattach`), and with `getty`/`agetty` (which put a *login* on the port with the default discipline).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/ldattach |
| First appeared | util-linux (2000s) |
| Standards | None (Linux `TIOCSETD` line-discipline API) |

## Synopsis

```
ldattach [options] <ldisc> <device>
```

Common one-line forms:

```
ldattach SLIP /dev/ttyS0            # SLIP discipline on COM1
ldattach 18 /dev/ttyS0              # N_PPS via numeric discipline id
ldattach -s 9600 -8 -n -1 GIGASET_M101 /dev/ttyS0
ldattach -d N_PPS /dev/ttyS0        # debug: stay in the foreground
```

## How It Works

### Where the line discipline sits

```
   userspace process           ldattach's job
        │  read()/write()            ┌──────────────────────────┐
        ▼                            │ tty driver (/dev/ttyS0)  │
   ┌──────────────┐    ▲             │  ┌────────────────────┐  │
   │ userspace    │────┘             │  │ line discipline    │  │
   └──────────────┘                  │  │ N_TTY / N_SLIP /   │  │
                                     │  │ N_PPS / N_PPP ...  │  │
                                     │  └────────────────────┘  │
                                     └──────────────┬───────────┘
                                                    ▼ UART hardware
```

The discipline processes both directions: `N_TTY` implements canonical mode, echo, and line editing; `N_SLIP` turns the byte stream into a network interface (`sl0`); `N_PPS` converts level transitions on the port into precise time events exposed as `/dev/pps0`; `N_SLCAN` decodes serial-CAN frames into a `slcan0` interface. Userspace then talks to the *result* (socket, pps device, netdev) instead of raw bytes.

### What the command does

1. Opens the device and (unless told otherwise) programs termios: speed (`-s`), character size (`-7`/`-8`), parity (`-n`/`-e`/`-o`), stop bits (`-1`/`-2`).
2. Optionally sends an intro string (`-c`) and pauses (`-p`) — e.g. waking a modem before switching disciplines.
3. Applies input-mode flags with `-i` (set/clear `ISTRIP`, `INLCR`, `IXON`, …).
4. Issues `TIOCSETD` with the requested discipline, then daemonizes (with `--debug` it stays in the foreground printing what it does) and keeps the device open — the attachment lives as long as some process holds the tty open.

### Kernel side: registry, modules, and lifetime

Disciplines live in a kernel registry; `/proc/tty/ldiscs` shows what the running kernel has (a bare container typically shows just the essentials):

```
n_tty       0        # the default terminal discipline
n_null     27        # swallow-everything discipline
```

`TIOCSETD` triggers a reference-counted switch: the kernel takes a reference on the new discipline's ops, calls its `open`, and drops the old one's reference. If the requested discipline is built as a module that is not loaded, the tty layer can autoload it (`modprobe slip`, `slcan`, `n_gsm`, `pps_ldisc` are the usual suspects); if neither module nor builtin exists, the ioctl fails and `ldattach` exits nonzero. Numeric ids beyond the classic list kept growing — `N_NULL` is 27 here — which is exactly why the symbolic names exist.

Lifetime is the part people get wrong: the discipline is a property of the *open tty*, not of the ioctl. When the last file descriptor closes, the tty's discipline resets to the default. That is why `ldattach` daemonizes and holds the fd for its whole life — and why the man page states the detach procedure plainly: **kill the ldattach process** (or attach `TTY`/0 over it). The daemon itself does nothing after `TIOCSETD`; it is a living reference, nothing more.

### Naming disciplines

The first argument is a symbolic name (case-insensitive, as the kernel's `tty.h` names them) or the numeric id. Common ones:

```
TTY (0)      default terminal processing        SLCAN (17)   serial-CAN adapters
SLIP (1)     serial line IP                     PPS (18)     pulse-per-second timing
MOUSE (2)    legacy serial mice                 GSM0710 (21) GSM multiplexing
PPP (3)      point-to-point protocol            HDLC (13)    hdlc framing
6PACK (7)    amateur-radio packet               R3964 (8)    Siemens r3964
IRDA (11)    infrared                           HCI (15)     Bluetooth UART
```

Availability depends on what the running kernel has (built-in or module-loaded): attaching `SLIP` on a kernel without the `slip` module fails until `modprobe slip` succeeds. `/proc/tty/ldiscs` lists what is currently registered.

### Verifying and undoing

```bash
cat /proc/tty/ldiscs          # registered disciplines
stty -F /dev/ttyS0 -a         # termios state ldattach configured
```

There is no `--detach`: to remove a discipline, attach the default one over it — `ldattach TTY /dev/ttyS0` (discipline 0) — or close whatever holds the device. This asymmetry surprises everyone once.

### Worked pipeline: GPS pulse-per-second

The most common modern use is timekeeping. A GPS receiver emits a 1 Hz electrical pulse on a control line (typically DCD) aligned to the UTC second; `N_PPS` turns those edges into kernel events:

```
GPS RX ── pulse on DCD ──► UART pin ──► N_PPS ldisc ──► PPS subsystem
                                                         │
                                         /dev/pps0 ◄─────┘
                                         events consumed by chrony/ntp
                                         (PPS API: time_pps_create)
```

```bash
sudo ldattach PPS /dev/ttyS0        # attach the discipline
sudo ppstest /dev/pps0              # watch edges: assert/clear timestamps
```

The NMEA sentences carrying absolute time travel over the *same* port as ordinary data (often read by gpsd with the plain `N_TTY` discipline in another setup); the PPS discipline exists so the kernel itself can timestamp the edges interrupt-precisely instead of trusting application read timing. A time daemon such as chrony then combines "NMEA says 12:00:01" with the kernel-stamped pulse edge to discipline the clock to sub-millisecond accuracy. This is why `ldattach PPS` is glue no daemon provides: without a discipline attached there is no `/dev/ppsX` node at all, and PPS-API consumers need that node to exist.

## Options That Matter

| Option | Effect |
| --- | --- |
| `<ldisc>` | Discipline name (`SLIP`, `PPS`, …) or numeric id |
| `<device>` | Serial device (`/dev/ttyS0`, `/dev/ttyUSB0`, …) |
| `-s, --speed <baud>` | Set the line speed before attaching |
| `-7/-8` | 7-bit / 8-bit character size |
| `-n/-e/-o` | Parity: none / even / odd |
| `-1/-2` | One / two stop bits |
| `-i, --iflag [-]<flag>` | Set (or clear with `-`) a termios input flag, e.g. `-i ISTRIP` |
| `-c, --intro-command <str>` | String sent to the device before attaching |
| `-p, --pause <secs>` | Delay between intro and attachment |
| `-d, --debug` | Verbose messages; stays in the foreground |

## Usage Patterns

```bash
# Attach SLIP: the port becomes network interface sl0
sudo ldattach SLIP /dev/ttyS0
ip link show sl0

# GPS timing: N_PPS exposes the pulse-per-second edge as /dev/pps0
sudo ldattach PPS /dev/ttyUSB0
ls /dev/pps*          # with ppsLDisc module loaded

# Serial-CAN adapter: discipline 17, then bring up the CAN interface
sudo ldattach -s 115200 SLCAN /dev/ttyUSB0
sudo ip link set slcan0 up type can

# GIGASET base station (the man page's own example): full termios spec
sudo ldattach -s 9600 -8 -n -1 GIGASET_M101 /dev/ttyS0

# Debug an attachment: foreground, verbose, watch it fail loudly
sudo ldattach -d PPS /dev/ttyS0

# Send a wake string to a modem, wait, then attach
sudo ldattach -c 'ATZ' -p 2 SLIP /dev/ttyS0

# Check what the port is set to after attachment
stty -F /dev/ttyS0 -a | head -3

# List kernel-registered disciplines before choosing a name
cat /proc/tty/ldiscs

# Strip the 8th bit for a 7-E-1 legacy device
sudo ldattach -7 -e -1 -i ISTRIP SLIP /dev/ttyS0

# Undo: return the port to normal terminal processing
sudo ldattach TTY /dev/ttyS0
```

```bash
# GSM CMUX: switch the modem to multiplexing, wait, then attach
sudo ldattach -c 'AT+CMUX=0' -p 2 GSM0710 /dev/ttyS0
ls /dev/gsmtty*          # virtual channels appear as tty devices

# Set and clear input flags in one -i (comma-separated, minus clears)
sudo ldattach -i ISTRIP,INLCR,-IXON SLIP /dev/ttyS0

# Neutralize a port during debugging: N_NULL discards all traffic
sudo ldattach 27 /dev/ttyUSB0

# Verify the PPS device actually pulses (pps-tools)
sudo ppstest /dev/pps0   # prints source, sequence, and edge timestamps

# Detach cleanly: kill the daemon holding the reference
pkill -f 'ldattach PPS /dev/ttyS0' && sleep 1 && cat /proc/tty/ldiscs
```

## Nuances and Gotchas

- **Root required.** `TIOCSETD` and termios reconfiguration need privileges; unprivileged runs fail with `EPERM` — a common container/sandbox dead end (serial devices are usually not passed in at all).
- **The device must be free.** A `getty`/`agetty` or `ModemManager` holding the port blocks attachment (`EBUSY`). Disable the getty for that port (`systemctl stop serial-getty@ttyS0.service`) and mask ModemManager probing on embedded boxes.
- **Names are kernel-dependent.** `ldattach` does not load modules; `PPS` fails with `ENOIOCTLCMD`/`ENODEV` until `pps_ldisc` (and friends: `slip`, `slcan`, `n_gsm`) is available. Check `/proc/tty/ldiscs`, then `modprobe`.
- **No detach command.** Reattach `TTY` (0) to revert, or close all openers. People who never learned this leave ports in SLIP mode "forever".
- **ldattach must stay alive.** The attachment depends on an open fd; the daemonized process holding the port is the anchor. Killing it may drop the discipline (with autoclose semantics) — do not `pkill ldattach` casually on production boxes.
- **PPP does not need it.** `pppd` sets `N_PPP` itself; attaching `PPP` by hand usually just blocks the port. `ldattach` is for disciplines *no* userspace daemon manages (PPS, SLCAN, SLIP legacy links).
- **Intro/pause are raw strings**, not AT-command scripts — no modem result-code parsing; use `-p` to give slow modems time before `TIOCSETD`.
- **`-i` flag names are termios names** (`ISTRIP`, `INLCR`, `IXOFF`, `IGNBRK`, …); unknown flags abort. Order matters: termios options apply before the discipline switch.
- **Numeric ids are kernel-version dependent** — prefer names in scripts; ids beyond ~19 grew over the years (`GSM0710` = 21, later additions beyond).
- **`-p` has a default of one second**, and `-c`/`-p` only make sense together for devices that need waking (the man page's own example pairs `AT+CMUX=0` with GSM0710). If the modem answers slowly, a too-short pause means the intro string lands before the device listens and the discipline attaches to a modem still in AT mode.
- **Killing ldattach IS the documented detach.** The daemon holds the tty reference; SIGTERM closes it, the tty's last fd closes, and the kernel resets the discipline. SIGKILL works the same way (no cleanup hook involved) — the reset is kernel-side, not process-side.
- **`-i` accepts numbers or names, sets or clears.** A numeric value is the raw `c_iflag` bitmask (octal in the termbits headers: `ISTRIP` is 0040, `INLCR` is 0100); mixing symbolic and numeric entries in one comma list is supported, which is handy when a flag name is missing on old toolchains. Clear-list items need the minus *per item*, not once for the group.
- **Attach survives, termios may not.** The discipline is keyed to the open tty, but termios settings written before `TIOCSETD` can be reset by later openers that call their own `tcsetattr` (ModemManager, a stray `stty`). If speed/parity drifts during operation, re-check `stty -F /dev/ttyS0` and put both termios and discipline setup into one udev `RUN+=` or systemd unit so nothing else races it.
- **Serial consoles complicate everything.** A port used as `console=ttyS0` has the kernel printk path pinned to it; disciplines can still be attached, but log output interleaves with protocol bytes. Choose a non-console port for SLCAN/PPS duty whenever you control the hardware.

## Exit Status

- `0` — attachment succeeded; the process continues in the background (foreground with `--debug`).
- `1` — failure: unknown discipline, unreadable/busy device, insufficient privileges, or the kernel refused `TIOCSETD`. With `--debug`, stderr explains which step failed.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`agetty`](./agetty.md) — the opposite use of a serial port: a login terminal with the default discipline.
- [`blockdev`](./blockdev.md) — sibling ioctl-driven configuration tool, for block devices instead of ttys.
- [`dmesg`](./dmesg.md) — kernel messages about module loads and tty driver registration.
- [`internals`](../../internals.md) — the tty layer: drivers, disciplines, and the `TIOCSETD` switch.

## Interview Questions

### Q: What is a line discipline, and what does the default one do?

A kernel processing module stacked on a tty that translates raw byte streams into structured input/output. The default `N_TTY` implements canonical (line) mode, echo, signals from control characters (Ctrl-C → SIGINT), and line editing. Other disciplines reinterpret the stream entirely: SLIP builds network packets, PPS converts level edges into time events, SLCAN decodes CAN frames. `ldattach` performs the `TIOCSETD` switch from the shell.

### Q: Why does a GPS timekeeping setup need ldattach at all?

The receiver's pulse-per-second output wired to a serial control line must be converted into kernel timekeeping events; that is the `N_PPS` discipline, which exposes `/dev/pps0` consumed by `chrony`/`ntp` via the PPS subsystem. Nothing else (no daemon) attaches that discipline, so `ldattach PPS /dev/ttyX` is the canonical glue step — plus ensuring the `pps_ldisc` module exists.

### Q: ldattach fails with "device busy" — what holds the port?

Almost always a `serial-getty@ttySx` unit, ModemManager, or a leftover `screen`/`minicom` session. Identify with `fuser -v /dev/ttyS0` or `lsof /dev/ttyS0`, stop the getty unit for that port, configure ModemManager udev filters, and retry. The discipline switch needs exclusive control of the tty's termios state.

### Q: How do you verify a discipline attached successfully, and how do you undo it?

Success signals: the command returns 0 and daemonizes; `/proc/tty/ldiscs` lists the discipline as loaded; discipline-specific artifacts appear (`sl0`/`slcan0` network interfaces, `/dev/pps0`); `stty -F ... -a` reflects the configured termios. Undo by attaching the default discipline — `ldattach TTY /dev/ttyS0` — or closing all openers of the device; there is no dedicated detach option.

### Q: Why is PPP listed as a discipline yet pppd never needs ldattach?

`pppd` manages its own port lifecycle: it opens the device, configures termios, sets `N_PPP` via `TIOCSETD`, negotiates LCP/IPCP, and tears everything down on exit. Hand-attaching `PPP` with ldattach leaves the port in a discipline nobody negotiates with — typically just a stuck port. `ldattach` exists for disciplines that have no managing daemon: PPS, SLIP, SLCAN, GSM0710 muxes, legacy protocols.

### Q: A script uses `ldattach 17` for SLCAN on two kernel versions and fails on one. Why, and what is the fix?

Numeric discipline ids are kernel ABI: they can shift or be absent when the discipline is not built/loaded. The fix is to use the symbolic name (`SLCAN`), ensure the module is available (`/proc/tty/ldiscs`, `modprobe slcan`), and fail loudly with `ldattach -d` when the kernel lacks support. Names resolve through the running kernel's registered set, surviving id renumbering across versions.

### Q: Explain the lifetime rules: why does the discipline disappear when the daemon dies, and how do you hand an attachment to another process?

`TIOCSETD` binds the discipline to the open tty, and the tty layer resets to the default discipline when the last descriptor closes — so ldattach's daemonized fd *is* the attachment. To hand it off, another process must open the same device and hold it before ldattach exits (a small wrapper can `exec` the consumer after attaching), or the consumer can perform its own `TIOCSETD`. There is no kernel-level "persistent attachment": if you need one, run ldattach (or an equivalent fd holder) under a supervisor instead of expecting the setting to survive.

### Q: Design: why does the kernel model SLIP/PPS/SLCAN as line disciplines rather than plain device drivers?

Because they all sit on a serial byte stream and need the tty layer's existing plumbing: termios for speed/parity, the input/output flip buffers, and flow control. The discipline interface lets each protocol plug exactly one processing layer into that stream — no duplicated serial drivers — while `TIOCSETD` makes the choice runtime-configurable per port. The cost is the API ldattach exposes: anyone who wants the processing must manage the tty lifecycle (open, termios, keep-open) around the discipline.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/ldattach.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
