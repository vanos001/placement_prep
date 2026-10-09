# wdctl — show hardware watchdog status

## Overview

`wdctl` displays the status and feature flags of a Linux **hardware watchdog** device — by default `/dev/watchdog` — through the standard watchdog ioctl API. It shows the driver identity and version, the configured timeout and pre-timeout, the pre-timeout governor, and a table of `WDIOF_*` capability flags with their live status and boot-status bits. It ships in the Debian `util-linux` package at `/usr/sbin/wdctl` (section 8: it is a system-administration tool that also *mutates* settings).

You reach for it when verifying that a watchdog is actually armed (server with a BMC/IPMI watchdog, embedded board with a SoC watchdog), when tuning how long the box may hang before an automatic reset (`--settimeout`), or when wiring the pre-timeout to a graceful shutdown path. It is often confused with the *softdog* kernel module (a fake watchdog for testing), with `systemd`'s `RuntimeWatchdogSec=` (which programs the same device via its own manager), and with userspace keepalive daemons (`watchdogd`) — wdctl observes/programs the hardware side, it does not feed the dog.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/wdctl |
| First appeared | early-2010s util-linux, over the kernel watchdog API (`watchdog.h`) |
| Standards | none; Linux watchdog ioctl interface |

## Synopsis

```
wdctl [options] [device ...]
```

Main one-line forms:

```
wdctl                          # status of /dev/watchdog
wdctl /dev/watchdog1           # explicit device node
wdctl -s 30                    # set timeout to 30 seconds (privileged)
wdctl -x                       # only the flags table
wdctl -o FLAG,STATUS           # selected columns only
```

## How It Works

### The flag vocabulary

The `WDIOF_*` names you will actually see, with the meaning the kernel's `watchdog.h` gives them — worth memorizing a handful for interviews:

```
KEEPALIVE      driver supports the ping ioctl (always expected)
MAGICCLOSE     honors the 'V' magic character on close (allows stopping)
SETTIMEOUT     timeout is programmable (otherwise fixed by hardware)
NOWAYOUT       watchdog cannot be stopped once started (read via module param)
PRETIMEOUT     pre-timeout interrupt supported (early warning before reset)
TEMPERATURE    chip reports temperature
CARDRESET      last reset was caused by this card
POWERUNDER / POWEROVER / POWERTIMEOUT
               supply-voltage anomaly triggered the reset
EXTERNAL1 / EXTERNAL2  external event inputs fired
FANFAULT       fan failure condition
```

STATUS and BOOT-STATUS columns report which of these conditions are *currently* asserted and which were latched at boot — reading BOOT-STATUS after an unexplained reboot is the fastest hardware-level RCA available without a BMC console.

### softdog: practicing without hardware

No watchdog in your VM or CI box? Load the software watchdog:

```bash
sudo modprobe softdog nowayout=0
wdctl                       # Identity: Software Watchdog
```

`softdog` implements the same ioctl API in the kernel with a timer callback, making it the standard sandbox for wdctl, keepalive daemons, and systemd `RuntimeWatchdogSec=` experiments — with the caveat that it dies with the kernel, so it tests the *protocol*, not the hardware failure mode.

### The watchdog contract

A hardware watchdog counts down independently of the CPU; if nothing *feeds* it (writes the magic keepalive character) before the timeout expires, it resets the machine. The kernel exposes exactly one open-per-system device node per watchdog:

```
userspace                      kernel                      hardware
   │ open("/dev/watchdog")  ──> starts/claims watchdog ──> counter armed
   │ WDIOC_GETSUPPORT       ──> WDIOF_* capability bits
   │ WDIOC_GETSTATUS        ──> status flags (e.g. card reset seen)
   │ WDIOC_GETBOOTSTATUS    ──> what caused the last boot reset
   │ WDIOC_SETTIMEOUT       ──> reprogram countdown
   │ write "V" + close      ──> graceful stop (if NOWAYOUT is off)
   │ (no keepalive in time) ─────────────────────────────> hard reset
```

`wdctl` opens the device just long enough to issue the query ioctls, prints the result, and closes — using the magic-close character so a read-only inspection does not leave the watchdog stopping (where drivers support magic close and NOWAYOUT is off).

### What the output contains

```
Device:        /dev/watchdog
Identity:      iTCO watchdog  [driver/version line]
Timeout:       30 seconds
Pre-timeout:    0 seconds
Pre-timeout Governor: n/a

FLAG           DESCRIPTION               STATUS  BOOT-STATUS
KEEPALIVE      Keep alive ping reply        0            0
MAGICCLOSE     Supports magic close char    1            0
SETTIMEOUT     Set timeout (in seconds)     1            0
```

The flags table lists which `WDIOF_*` features the hardware supports (e.g. `TEMPERATURE`, `PRETIMEOUT`, `POWERUNDER`, `EXTERNAL1/2`, `CARDRESET`...), with STATUS reflecting the *live* condition bits and BOOT-STATUS reflecting the reset reason captured at boot. Content is entirely hardware-specific — some drivers expose a handful of flags, others almost none.

### Fallback path via sysfs

The device node allows only one opener at a time (the keepalive daemon usually holds it), and reading needs group `watchdog` or root. If the device is already used or the user lacks permission, `wdctl` silently falls back to reading the equivalent state from sysfs (`/sys/class/watchdog/...`), where the flags table may be missing — output shape stays, detail drops.

### Cloud and VM reality

Public-cloud VMs frequently expose *no* watchdog device (the hypervisor owns host watchdogs), and containers never do — which makes `wdctl` a tool whose absence-of-output is itself diagnostic. Where hardware exists, it is often the BMC/IPMI watchdog (dell_smbios, ipmi_watchdog driver) or a SoC watchdog (iTCO_wdt on Intel platforms). Knowing which driver backs your device (`ls /sys/class/watchdog/*/device/driver`) explains which flags appear and whether `--settimeout` is honored at all.

### Mutating operations

`--settimeout <sec>` issues `WDIOC_SETOPTIMEOUT`, `--setpretimeout <sec>` the pre-timeout ioctl (which fires an interrupt/NMI *before* the full reset so a graceful panic path can run), and `--setpregovernor <name>` selects the pre-timeout governor (e.g. `panic`). These require write permission on the device — practically root.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-s, --settimeout <sec>` | Program the watchdog timeout. |
| `-p, --setpretimeout <sec>` | Program the pre-timeout (pre-reset warning interrupt). |
| `-g, --setpregovernor <name>` | Set the pre-timeout governor (e.g. `panic`). |
| `-f, --flags <list>` | Show only the named flags. |
| `-o, --output <list>` | Columns: `FLAG`, `DESCRIPTION`, `STATUS`, `BOOT-STATUS`, `DEVICE`. |
| `-x, --flags-only` | Only the flags table (same as `-I -T`). |
| `-F, --noflags` / `-I, --noident` / `-T, --notimeouts` | Suppress the flags table / identity / timeouts sections. |
| `-O, --oneline` | All information on one line (parse-friendly). |
| `-r, --raw` / `-n, --noheadings` | Raw column format / no headers for scripts. |

## Usage Patterns

```bash
# Is the watchdog there and armed?
wdctl
# wdctl: No default device is available.    <- typical result in VMs/containers
```

```bash
# Inspect a specific node when several watchdogs exist
wdctl /dev/watchdog1
```

```bash
# What caused the last reboot?
wdctl -o FLAG,BOOT-STATUS
```

```bash
# Program a 30 s window (grace period the keepalive daemon must beat)
sudo wdctl -s 30
```

```bash
# Give the kernel a 5 s warning before reset to log a panic trace
sudo wdctl -p 5 && sudo wdctl -g panic
```

```bash
# Script-friendly single line for monitoring
wdctl -O -n
```

```bash
# Compare two watchdog devices on multi-device systems
wdctl /dev/watchdog0 /dev/watchdog1
```

```bash
# Check capability flags only, ignoring identity/timeout blocks
wdctl -x
```

```bash
# Verify after systemd reconfiguration
grep -r RuntimeWatchdog /etc/systemd/system.conf.d/ ; wdctl -T
```

```bash
# Load the software watchdog in a test VM and inspect it
sudo modprobe softdog && wdctl -x
```

```bash
# Grab identity and timeouts only, for a hardware inventory script
wdctl -F -I 2>/dev/null || echo "no watchdog device"
```

```bash
# Watchdog flag discovery before promising pre-timeout behavior
wdctl -x -o FLAG,DESCRIPTION | grep -iE 'pretimeout|settimeout|nowayout'
```

```bash
# Confirm what booted the box after an unexpected reboot (post-mortem)
wdctl -o FLAG,BOOT-STATUS; dmesg | grep -i watchdog
```

## Nuances and Gotchas

- **Reading is privileged-ish.** `/dev/watchdog` is `root:watchdog 0600`-ish on most systems; unprivileged `wdctl` shows the sysfs fallback or nothing. In VMs and containers there is often *no* watchdog device at all — the grounded error in this environment is `wdctl: No default device is available.`
- **One opener only.** If systemd, `watchdogd`, or a BMC client already holds the node, the ioctl path is unavailable; wdctl downgrades to sysfs and may omit the flags table. Don't "test" by holding the device open yourself — you may starve the real keepalive daemon.
- **NOWAYOUT vs magic close.** Many drivers honor writing the `V` character before close to *stop* the watchdog; with the `nowayout` module parameter set, the watchdog cannot be stopped once started — a deliberate anti-footgun for safety-critical boxes. Running `wdctl` is safe (it magic-closes), but ad-hoc scripts poking the device may leave the machine reset-bound.
- **`-s` is not universally supported.** `SETTIMEOUT` is itself a capability flag; some hardware only accepts fixed timeouts. A failed `wdctl -s` with `EINVAL` means the driver rejected the value — check the flags table first.
- **Pre-timeout is hardware-dependent.** `PRETIMEOUT` support and governor availability vary; on many drivers the pre-timeout is an NMI whose "governor" is fixed. Verify with the flags table before promising graceful warnings.
- **systemd owns the common case.** With `RuntimeWatchdogSec=` set, PID 1 feeds the device and reprograms it at boot; hand-tuned `wdctl -s` values get overwritten on reboot unless mirrored in `system.conf`. Similarly, `FixupRuntimeWatchdogSec` quirks may clamp your value.
- **Flags differ per driver.** Scripting against specific flag names (e.g. expecting `PRETIMEOUT` everywhere) breaks across hardware; treat the table as discovery output, enumerate with `-o FLAG` first.
- **Set operations are fire-and-forget.** `wdctl -s 30` returning 0 means the ioctl was accepted; some drivers round values, clamp to a max, or only apply at next open. Read back with a second `wdctl -T` instead of trusting the setter's silence.
- **watchdog group membership is the sane delegation.** Adding operators to the `watchdog` group lets them inspect (`wdctl`) without root; granting it also permits writing the device node — so decide deliberately whether inspection or control is being delegated, and audit keepalive daemons for the same node.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Device queried (and settings applied if requested) successfully. |
| 1 | Failure: no such device, permission denied, ioctl unsupported, or the set operation was rejected by the driver. |

## Related Commands

- [`dmesg`](./dmesg.md) — watchdog resets and pre-timeout panics land in the kernel ring buffer; the forensic partner.
- [`../../internals.md`](../../internals.md) — kernel/userspace interface context for device ioctls.
- [`../../admin/systemd.md`](../../admin/systemd.md) — systemd's `RuntimeWatchdogSec=` manages the same device.
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What exactly does a hardware watchdog protect against, and what feeds it in practice?

It protects against the machine being unable to make progress — kernel hang, scheduler lockup, stuck init — by hard-resetting when no keepalive arrives within the timeout. In practice a userspace daemon (classic `watchdogd`, systemd's PID 1 with `RuntimeWatchdogSec=`, or vendor agents) periodically writes to `/dev/watchdog`. wdctl's role is to show and program that hardware contract, not to feed it.

### Q: You run `wdctl` and get "No default device is available". Give three plausible causes.

No watchdog hardware/driver exists (typical VM or container — nothing registered `/dev/watchdog`); the module is simply not loaded (`softdog`/`iTCO_wdt` etc.); or the node exists but is inaccessible (permissions) so discovery fails. Distinguish with `ls /dev/watchdog*`, `ls /sys/class/watchdog/`, and `lsmod | grep -i wdt`.

### Q: Explain the difference between timeout and pre-timeout, and why the pre-timeout matters for debugging.

The timeout is when the hardware resets; the pre-timeout fires an interrupt earlier (e.g. 5 s before), letting the kernel run a panic/notify path — dump state, alert management, then still reset if unattended. Without a pre-timeout, a hang leaves no trace; with one (and a panic governor) you get post-mortem evidence plus the same eventual reset.

### Q: Why does wdctl sometimes fall back to sysfs, and what is lost there?

The watchdog device node permits a single opener; when the keepalive daemon already holds it (the normal production state) or the user lacks read permission, wdctl reads `/sys/class/watchdog/*/` instead. The identity and timeout state remain available, but driver-specific capability/status flag details may be missing because sysfs exposes a reduced view.

### Q: What is the NOWAYOUT semantics trap when experimenting with watchdog devices?

Many drivers stop the watchdog on a clean close preceded by the magic `V` write; if the `nowayout` module parameter is set (common on safety-oriented builds), the watchdog is one-way armed — once started it cannot be stopped except by reset. Casual scripting against the device without checking this can leave a server on a reset countdown that only a feed daemon (or reboot) can satisfy.

### Q: How do systemd's watchdog settings interact with wdctl?

`RuntimeWatchdogSec=` in `system.conf` makes PID 1 open, feed, and program the device each boot, so any timeout you set manually with `wdctl -s` is transient until the next reconfiguration/reboot. To make a timeout persistent you set it in systemd's config; wdctl then serves as the verification tool (`wdctl -T` to read back effective values).

### Q: A production box rebooted unexpectedly. What can wdctl contribute to the RCA, and what are its limits?

Its BOOT-STATUS column reports the latched hardware reset reason — e.g. CARDRESET, POWERUNDER, or an external trigger — which distinguishes "watchdog fired" from "power anomaly" at the silicon level, something logs alone cannot. Limits: only drivers that expose the relevant WDIOF bits report them, the latch may be cleared by subsequent reads or boots, and it says nothing about *why* the watchdog starved — for that you correlate with `dmesg`, kernel panic history, and the keepalive daemon's own logs. wdctl is the first fact, not the whole story.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/wdctl.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
