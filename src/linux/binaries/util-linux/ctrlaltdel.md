# ctrlaltdel — set the kernel's handling of Ctrl-Alt-Del

## Overview

`ctrlaltdel` is a tiny Linux-specific administration tool that selects what the
kernel does when the Ctrl-Alt-Del key combination is pressed on a virtual console:

- **soft** — the kernel sends `SIGINT` to the `init` process (PID 1), which then
  performs whatever orderly shutdown its configuration prescribes (runlevel
  changes in sysvinit's `/etc/inittab`, `ctrl-alt-del.target` under systemd).
- **hard** — the kernel reboots immediately, without syncing disks and without
  consulting any userspace process — the BIOS-era "three-finger reset" behavior.

It works by writing the `/proc/sys/kernel/ctrl-alt-del` sysctl (`0` = soft,
`1` = hard), so the setting is visible and settable through `sysctl` too; the
command exists because the traditional way to set it was from boot scripts
(`/etc/rc`, inittab actions). It requires root privileges and takes exactly one
argument. In Debian bookworm it ships in the `util-linux` package at
`/usr/sbin/ctrlaltdel`.

The tool is mostly relevant for sysvinit and busybox-init systems and as an
interview probe of how PID 1, the kernel, and console input interact. On
systemd systems the practical behavior is governed by
`systemd.ctrl-alt-del.target`, but the kernel-side mechanism this command
controls is still the plumbing underneath.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Section (man) | 8 |
| Path | /usr/sbin/ctrlaltdel |
| Lineage | util-linux original; Linux-only (VT keyboard driver + init signal) |
| Standards | None — Linux-specific interface |

## Synopsis

```
ctrlaltdel hard|soft
```

Both call shapes:

```
ctrlaltdel soft        # SIGINT to PID 1 → orderly shutdown path
ctrlaltdel hard        # immediate kernel reboot, no sync, no userspace
```

## How It Works

### The kernel side

On PC-style systems the kernel's keyboard driver for virtual consoles (VT)
recognizes the Ctrl-Alt-Del chord and consults the
`kernel.ctrl-alt-del` sysctl:

```
                Ctrl-Alt-Del pressed on a VT
                            │
              ┌─────────────┴──────────────┐
   ctrl-alt-del = 0 (soft)       ctrl-alt-del = 1 (hard)
              │                            │
   kernel sends SIGINT to          immediate reboot
   init (PID 1)                    (no sync, no shutdown
              │                     scripts, may lose data)
   init's policy decides
   (inittab ctrlaltdel action /
    systemd ctrl-alt-del.target)
```

The soft route is the safe default: it delegates to whatever shutdown policy the
system is configured with, e.g. the classic sysvinit inittab line:

```
# /etc/inittab (sysvinit): run shutdown when the kernel signals init
ca::ctrlaltdel:/sbin/shutdown -t1 -a -r now
```

### The command itself

`ctrlaltdel soft` writes `0`, `ctrlaltdel hard` writes `1` to
`/proc/sys/kernel/ctrl-alt-del`. That is the entire mechanism — which is why the
manual page notes the same result via:

```bash
$ cat /proc/sys/kernel/ctrl-alt-del    # 0 = soft (default on most distros)
0
$ sysctl -w kernel.ctrl-alt-del=1      # equivalent to: ctrlaltdel hard
```

Writing it requires `CAP_SYS_ADMIN`/root; an unprivileged invocation fails with
"Permission denied". The value is **not persistent** across reboots: anything that
needs it is set in boot scripts (the historical placement for this command).

### Where the key combo is (and is not) seen

Ctrl-Alt-Del is recognized by the *VT keyboard driver* — the combination is
synthesized from raw scan codes on a local console. It is therefore invisible to
serial consoles, SSH sessions, and most virtualization setups (the hypervisor may
map the chord itself). "Reboot a server remotely by pressing ctrl-alt-del" only
works through layers that forward it, such as some IPMI/KVM implementations.

### A brief lineage note

The "three-finger salute" predates Linux: on PC DOS it reset the machine, and
early Linux inherited both the chord and the two possible reactions — the raw
BIOS-style reset (`hard`) and the polite "tell init" path (`soft`), which was
the innovation of multi-user operating systems. `ctrlaltdel(8)` is simply the
switch between the two philosophies, kept alive because embedded and legacy
systems still boot inits that rely on it.

### systemd's takeover

Under systemd, PID 1 receives the SIGINT and starts
`ctrl-alt-del.target` — which is *usually* an alias of `reboot.target`, i.e. an
orderly reboot. Systemd also has its own handling knobs (masking the target
disables the behavior). The `hard` setting is almost never used on production
systems: it bypasses filesystem sync and every shutdown script, and its use is
a data-loss hazard akin to a hardware reset.

## Options That Matter

There are no options — only the two arguments:

| Argument | Effect |
| --- | --- |
| `soft` | Kernel sends SIGINT to init; orderly shutdown policy applies |
| `hard` | Immediate kernel reboot without sync or userspace involvement |

Any other argument is a usage error.

## Usage Patterns

```bash
# Check the current mode (0 = soft, 1 = hard)
cat /proc/sys/kernel/ctrl-alt-del
```

```bash
# Switch to the safe, orderly-reboot mode (classic boot-script line)
sudo ctrlaltdel soft
```

```bash
# From a boot script (rc.local style), make the console chord reboot politely
[ -x /usr/sbin/ctrlaltdel ] && /usr/sbin/ctrlaltdel soft
```

```bash
# Verify with sysctl (same knob, two spellings)
sysctl kernel.ctrl-alt-del
```

```bash
# sysvinit: define what 'soft' means via inittab, then reload init
grep '^ca:' /etc/inittab          # ca::ctrlaltdel:/sbin/shutdown -t1 -a -r now
sudo kill -HUP 1                  # make init re-read inittab (pre-systemd)
```

```bash
# systemd: what actually runs when the chord is pressed
systemctl list-dependencies ctrl-alt-del.target
```

```bash
# systemd: disable the chord entirely (mask the target)
sudo systemctl mask ctrl-alt-del.target
```

```bash
# busybox/embedded init: verify what PID 1 will do on the soft signal
head -1 /proc/1/comm        # e.g. systemd / init / busybox — the policy owner differs
```

## Nuances and Gotchas

- **Not persistent.** The sysctl resets at boot; the command belongs in boot
  scripts, not in your shell history. Forget `sudo ctrlaltdel hard` typed once
  — it silently changes console behavior until the next reboot.
- **`hard` bypasses everything.** No sync, no remount-ro, no shutdown scripts.
  On ext4/xfs the journal recovers, but dirty-page loss and fsck time are real;
  never use `hard` as a "quick reboot".
- **Only on virtual consoles.** SSH sessions, serial consoles, and many VMs never
  see the chord; testing `soft`/`hard` remotely usually does nothing at all.
- **Root required.** Both the command and direct sysctl writes fail for normal
  users — a permissions question in disguise (`CAP_SYS_ADMIN`).
- **systemd ignores your inittab.** On systemd systems the inittab `ca:` line is
  dead text; the behavior is `ctrl-alt-del.target`. Mixing the two models in an
  interview answer is a classic tell.
- **Busybox systems differ.** Embedded inits implement the SIGINT handler
  themselves; the kernel sysctl is still the same, but what "soft" then does
  depends on that init's code.
- **`soft` is not "safe" by itself.** The safety comes from what init is
  configured to do; if PID 1 has no ctrlaltdel action (sysvinit) or the target
  is masked (systemd), the chord does nothing at all — which is its own
  surprise when someone relies on it.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Mode was set successfully |
| 1 | Usage error (missing/unknown argument) or permission denied |

## Related Commands

- [`overview`](./overview.md) — index of all util-linux collection pages
- [systemd](../../admin/systemd.md) — how PID 1 (systemd) turns the soft signal into ctrl-alt-del.target

## Interview Questions

### Q: What exactly happens on ctrlaltdel soft versus hard?

`soft` makes the kernel send SIGINT to PID 1; init then runs its configured
shutdown policy — a sysvinit inittab `ctrlaltdel` action (typically
`shutdown -r now`) or systemd's `ctrl-alt-del.target`. `hard` makes the kernel
reboot immediately with no sync and no userspace involvement — equivalent to a
hardware reset, with corresponding data-loss risk.

### Q: Where does the command persist its setting, and why does that matter?

It writes `/proc/sys/kernel/ctrl-alt-del` — a runtime sysctl that resets on
reboot. Persistence requires invoking it from a boot script (or a sysctl.d
fragment for `sysctl`). This is why the man page frames the tool as something
"usually called from /etc/rc".

### Q: Why would ctrl-alt-del do nothing on your server over SSH?

The chord is detected by the kernel's virtual-terminal keyboard driver from raw
console input. SSH and serial consoles deliver ordinary input streams; there is
no VT key chord to recognize. Only local consoles (or forwarded chords via
IPMI/KVM) reach the code path `ctrlaltdel` configures.

### Q: How do systemd and sysvinit differ in handling the soft signal?

sysvinit reads an explicit `ca::ctrlaltdel:` action from `/etc/inittab` and
executes that command. systemd intercepts the SIGINT itself and starts
`ctrl-alt-del.target`, which normally aliases `reboot.target`; masking that
target disables the chord. The kernel-side mechanism (SIGINT to PID 1) is the
same — the policy layer above it differs.

### Q: When is ctrlaltdel hard ever justified?

Almost never on production systems: it skips disk sync and shutdown scripts,
turning a key press into a potential filesystem-consistency event. It exists to
replicate the hardware reset switch (e.g. kiosk/lab machines where an orderly
shutdown path may be broken) and to demonstrate that the kernel, not the BIOS,
has final say over the reset behavior.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/ctrlaltdel.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
