# hwclock — query and set the hardware clock (RTC)

## Overview

`hwclock` reads and writes the hardware clock — the battery-backed Real Time Clock (RTC) that keeps time while the machine is off — and manages the drift-correction state in `/etc/adjtime`. Linux keeps two clocks: the RTC (coarse, no timezone, survives power-off) and the *system clock* (kernel, fine-grained, NTP-disciplined, resets at boot). `hwclock` is the bridge between them: it shows the RTC, syncs RTC→kernel (`--hctosys`, early boot) or kernel→RTC (`--systohc`), and applies/records systematic drift between syncs.

Debian bookworm ships it in the `util-linux-extra` package at `/usr/sbin/hwclock`. Reach for it at boot/initramfs time, when dual-booting with Windows (whose expectation of a *local-time* RTC forces `--localtime` bookkeeping), when diagnosing "clock is off by exactly N hours" bugs, or on systems without NTP where drift correction still matters. It is often confused with `date`/`timedatectl` (system clock and policy layer respectively), with `clock` (the historical name), and with the kernel's automatic RTC handling that makes manual use rare on NTP-synced systems.

| Field | Value |
| --- | --- |
| Package | util-linux-extra (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/hwclock |
| First appeared | Descends from the early Linux `clock` utility, extended into hwclock in the 1990s |
| Standards | None (Linux-specific; RTC interface via /dev/rtc) |

## Synopsis

```
hwclock [function] [options]
```

Common one-line forms:

```
hwclock -r                 # show the hardware clock (drift-corrected)
hwclock -s                 # hctosys: set system clock from RTC (boot time)
hwclock -w                 # systohc: set RTC from system clock
hwclock --set --date="2026-01-31 11:22:33"   # set RTC directly
```

## How It Works

### Two clocks, one bridge

```
        ┌──────────────────────────────────────────────────────────┐
        │                       RTC  (/dev/rtc0)                    │
        │   battery-backed, no timezone, second-ish resolution      │
        └───────▲───────────────────────────────────┬──────────────┘
                │ hwclock -w / --systohc            │ kernel hctosys at boot
                │ hwclock --set --date=...          │ (CONFIG_RTC_HCTOSYS)
        ┌───────┴───────────────────────────────────▼──────────────┐
        │              kernel system clock (CLOCK_REALTIME)         │
        │   fine-grained, UTC internally, disciplined by NTP        │
        └───────▲───────────────────────────────────────────────────┘
                │ hwclock -s / --hctosys        (userspace, early boot)
        userspace: date, applications, logs
```

The kernel can load the RTC at boot by itself (`CONFIG_RTC_HCTOSYS`, reading it as UTC); when it does not (or the RTC is in local time), an initramfs/early-service runs `hwclock -s`. Writing back is `hwclock -w` at shutdown — or, on NTP-synced systems, nothing at all: see the 11-minute mode below.

### The adjtime file: drift bookkeeping

`/etc/adjtime` is the state that makes `hwclock` smarter than a plain copy:

```
0.000000000 0 0.000000    # systematic drift (sec/day), last calibration, residual
0.000000000               # time of the last drift adjustment
UTC                       # hardware clock scale: UTC or LOCAL
```

- `--systohc` (or `--set`) *recalibrates*: it computes the drift observed since the last calibration, writes the new factors, and stamps the file. A fresh system's file is all zeros.
- `--adjust` applies the recorded drift to the RTC reading without changing the system clock — for machines that stay off for months.
- `-r, --show` reports the RTC *with* the drift correction applied; `--get` reports it *without* (raw); `--predict --date=<when>` answers the inverse question: what will the RTC read when the system clock reaches `<when>`.
- The third line is the scale decision. `timedatectl` edits exactly this file (plus policy) when you run `timedatectl set-local-rtc 1`.

### Localtime vs UTC — the dual-boot tax

The RTC stores seconds since an epoch with *no timezone*. Keeping it in UTC is the Unix convention and is DST-proof. Windows expects the RTC in *local* time; dual-boot machines therefore set the third adjtime line to `LOCAL`, which hwclock honors when converting. Local time is lossy around DST transitions (two UTC instants map to the same local wall-clock reading), so an RTC "one hour off" after a DST change is the classic symptom of a mismatched scale — the fix is one `timedatectl set-local-rtc 0` or `hwclock -w` after aligning the system clock.

### The 11-minute mode (why hwclock is rarely needed on NTP hosts)

When the kernel considers its system clock disciplined by NTP, it independently writes the RTC every 11 minutes. On such hosts, `hwclock -w` is unnecessary — and `--hctosys` at boot is often the only hwclock touchpoint left (or nothing at all, when `CONFIG_RTC_HCTOSYS` covers it). Modern systemd systems additionally manage scale policy through `systemd-timedated` rather than scripts calling hwclock.

Two kernel config switches govern the automatic half of this: `CONFIG_RTC_HCTOSYS` (load RTC→system clock during boot, device chosen by `CONFIG_RTC_HCTOSYS_DEVICE`) and `CONFIG_RTC_SYSTOHC` (periodically write system→RTC). The 11-minute writeback is the SYSTOHC path, and its precondition is subtle: the kernel only trusts its clock when an NTP implementation has cleared the `STA_UNSYNC` flag through `adjtimex(2)`. A plain `hwclock -s` sets the time but does not clear that flag — on an NTP-less box the RTC is never written back automatically, which is exactly where shutdown-time `hwclock -w` earns its keep.

### The device interface: /dev/rtc and the RTC class

`hwclock` talks through the kernel RTC class: `/dev/rtc` (a symlink to `/dev/rtc0`), driven with `ioctl(2)` requests — `RTC_RD_TIME`/`RTC_SET_TIME` fill a `struct rtc_time` with second resolution, `RTC_UIE_ON` enables the once-per-second update interrupt hwclock uses to time its reads. The same data is exposed as text in `/sys/class/rtc/rtc0/` (`date`, `time`, `since_epoch`), and the alarm attribute `wakealarm` there is what `rtcwake` drives. Boards with several RTCs enumerate `rtc0`, `rtc1`, …; `-f` picks among them.

```
cat /sys/class/rtc/rtc0/{date,time,since_epoch}
# three text lines: calendar date, wall time, epoch seconds — raw RTC,
# no adjtime correction applied (compare with hwclock --get)
```

Because the register read is whole-second, `hwclock` refines by spinning on the update interrupt and combining the captured boundary with the coarse value — which is why a simple `hwclock -r` can visibly take up to a second, and why scripts timing `hwclock -r` loosely see jitter.

### A boot timeline of the two clocks

```
power on
  │ RTC ticking on battery (wrong by drift since last sync)
  ▼
kernel early boot:  CONFIG_RTC_HCTOSYS? ── yes ─► system clock := RTC (as UTC)
  │                                              adjtime scale NOT consulted!
  ▼ no (or initramfs policy instead)
initramfs: hwclock -s       system clock := RTC, converted per adjtime scale
  ▼
real root up: timesyncd/chronyd steps system clock from NTP
  ▼ NTP discipline achieved (STA_UNSYNC cleared)
kernel SYSTOHC: RTC := system clock, every 11 minutes
  ▼
shutdown: (non-NTP hosts only) hwclock -w stamps the RTC one last time
```

Note the asymmetry the diagram exposes: the kernel's HCTOSYS path reads the RTC as UTC and knows nothing about `/etc/adjtime`, so on LOCAL-scale (dual-boot) machines the kernel's own early setting is systematically wrong — the historical reason distros disable HCTOSYS and do the conversion in userspace, where hwclock can apply the scale and drift correction.

## Options That Matter

### Read and write functions

| Option | Effect |
| --- | --- |
| `-r, --show` | Print the RTC time (drift-corrected from adjtime) |
| `--get` | Print the RTC time raw, no adjtime correction |
| `--predict` | Predict the RTC reading at a future `--date` |
| `-s, --hctosys` | Set the system clock from the RTC |
| `-w, --systohc` | Set the RTC from the system clock |
| `--systz` | Push system timezone/scale into the kernel (initramfs use) |
| `--set --date=<time>` | Set the RTC to the given time |
| `-a, --adjust` | Apply the recorded adjtime drift to the RTC |
| `-c, --compare` | Periodically compare RTC vs system clock (drift measurement) |

### Scale and device options

| Option | Effect |
| --- | --- |
| `-u, --utc` | Treat the RTC as UTC (the default assumption) |
| `-l, --localtime` | Treat the RTC as local time |
| `-f, --rtc <path>` | Use another RTC device (default `/dev/rtc0`) |
| `--adjfile <path>` | Alternative adjtime file (initramfs, testing) |
| `--noadjfile` | Don't read/write the adjtime file |
| `--directisa` | Legacy: access the CMOS ports directly instead of /dev/rtc |
| `--test` | Dry run: do everything except the actual set |
| `-D, --debug` / `-v, --verbose` | Diagnostics |

## Usage Patterns

```bash
# What does the RTC say right now (drift-corrected)?
hwclock -r
# 2026-02-11 09:30:12.481201+00:00

# Compare RTC and system clock to spot sync problems
date; hwclock -r

# Classic boot-time sync in an initramfs script
hwclock -s

# Shutdown-time writeback when no NTP discipline exists
hwclock -w

# Dual-boot with Windows: declare the RTC is local time, then sync
hwclock -l -w        # or better: timedatectl set-local-rtc 1

# Measure drift over an hour (no NTP interference)
hwclock -c           # Ctrl-C when done; prints deltas

# Set the RTC directly (offline machine)
hwclock --set --date="2026-02-11 09:31:00" --utc

# Predict what the RTC will read when the system hits a given time
hwclock --predict --date="2026-03-01 12:00:00"

# Work with the second RTC (some servers have two)
hwclock -r -f /dev/rtc1

# Dry-run a sync (scripted safety)
hwclock --test -w
```

```bash
# Which automatic sync paths did the running kernel build in?
grep -E 'CONFIG_RTC_HCTOSYS|CONFIG_RTC_SYSTOHC' "/boot/config-$(uname -r)"

# Rescue shell without a usable adjtime (chroot, initramfs):
hwclock -r --noadjfile          # raw RTC, no state file touched

# Keep test state out of the real file
hwclock --test -w --adjfile /tmp/adjtime.test

# Confirm scale consistency with rtcwake (it reads the same adjtime line)
timedatectl | grep -i 'RTC in' || grep . /etc/adjtime
```

## Nuances and Gotchas

- **The RTC has no timezone.** All timezone reasoning is bookkeeping in `/etc/adjtime` (`UTC`/`LOCAL`) plus conversion at read/write time. Blaming "the hardware clock" for TZ bugs is a category error — the scale flag is the bug.
- **`-r` applies drift, `--get` does not.** Comparing the two reveals how much correction adjtime is adding; on a fresh system they are identical. Scripts that diff RTC vs NTP time should use `--get` to avoid double-counting corrections.
- **Don't fight the 11-minute mode.** On NTP-synced kernels, manual `hwclock -w` can race the kernel's own RTC writes. If you must, disable NTP first or accept that the kernel will overwrite you within 11 minutes.
- **DST and LOCAL scale are inherently lossy.** Around a transition the same wall-clock reading maps to two instants; reads across the boundary can be off by an hour with nothing "broken". This is *the* argument for UTC-scale RTCs, and the reason dual-boot machines suffer.
- **Permissions.** Reading usually needs `rtc` group access to `/dev/rtc0`; setting requires root. In containers, `/dev/rtc*` is often absent or read-only — `hwclock` fails there by design.
- **VMs virtualize the RTC.** Hosts inject time into guests; inside a VM, `hwclock` manipulates a virtual RTC whose semantics depend on the hypervisor (qemu keeps it in UTC by default, matching `-u`).
- **`--directisa` is museum-grade.** It exists for ancient or broken BIOSes where the `/dev/rtc` interface fails; on anything modern it is cargo cult — and dangerous on multi-CMU systems.
- **busybox hwclock is a subset.** Embedded initramfs images often ship busybox's version: fewer options (no `--predict`, `--compare`), different error text. Scripts should tolerate both or require util-linux's.
- **`--hctosys` is a one-shot sync, not a daemon.** After it, NTP (chrony/systemd-timesyncd) takes over stepping the system clock; hwclock does not keep adjusting unless `--compare`/`--adjust` flows are used deliberately.
- **sysfs reads bypass everything hwclock does.** `cat /sys/class/rtc/rtc0/time` is the raw register; mixing it with `hwclock -r` (drift-corrected) in the same script produces phantom drift. Pick one access path per measurement.
- **`rtcwake` inherits your scale decision.** It reads the UTC/LOCAL line from the same `/etc/adjtime`; a machine flipped to LOCAL for dual-boot will schedule wakeups in local time too. Debug "why did the alarm fire an hour late/early" by checking the adjtime third line first.
- **`hwclock -s` does not arm the 11-minute mode.** Only an NTP daemon clearing `STA_UNSYNC` via `adjtimex(2)` does that. On NTP-less systems nothing writes the RTC back — the shutdown `hwclock -w` is not cargo cult there, it is the only writeback.
- **Adjtime has three lines, and all three mean something.** Line 1: drift rate (sec/day), last-calibration time, residual offset. Line 2: timestamp of the last drift adjustment. Line 3: `UTC` or `LOCAL`. A file truncated to one line, or hand-edited with a wrong scale, silently changes every hwclock conversion — diff it when time bugs appear after provisioning changes.

## Exit Status

- `0` — the requested operation succeeded.
- Nonzero — failure: cannot open the RTC device, insufficient privileges, invalid `--date` string, or the RTC does not respond (dead CMOS battery shows up as nonsense dates and erroring reads). `--test` performs everything except the write and reflects what would have happened.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`rtcwake`](./rtcwake.md) — suspends the system and schedules RTC-alarm wakeup; the RTC's other trick.
- [`systemd`](../../admin/systemd.md) — timedated/timesyncd policy that replaces manual hwclock calls.
- [`internals`](../../internals.md) — kernel timekeeping, CLOCK_REALTIME, and the RTC class subsystem.
- [`commands`](../../reference/commands.md) — where date/time tooling sits in the general command map.
- [`process-management`](../../admin/process-management.md) — early-boot ordering that decides who syncs first.

## Interview Questions

### Q: Why does a machine boot with the clock off by exactly one hour after a DST change?

Its RTC is kept in local time (`LOCAL` in /etc/adjtime, typically for Windows dual-boot) and the DST offset changed while the machine was off: the RTC still holds the old wall-clock, which now maps to an instant one hour away. UTC-scale RTCs don't have this failure mode because UTC has no transitions. Fix: set the correct scale (`timedatectl set-local-rtc 0` + resync) or resync after boot.

### Q: What is the difference between the system clock and the hardware clock, and who syncs what when?

The RTC is battery-backed, coarse (typically 1-second granularity read through /dev/rtc), and timezone-free; it exists to survive power-off. The kernel system clock is fine-grained, UTC-internally, and NTP-disciplined, but starts bogus at boot. Boot: kernel hctosys (if built in) or `hwclock -s` from initramfs. Shutdown: `hwclock -w` unless the kernel's 11-minute NTP mode is already writing the RTC continuously.

### Q: On an NTP-synced server, is `hwclock -w` in a shutdown script useful?

Usually redundant and occasionally racy: once the kernel is NTP-disciplined it enters 11-minute mode and writes the RTC itself, so a manual write just repeats what happens anyway — and can interleave with the kernel's write. The script is harmless on non-NTP hosts and useless on NTP hosts; the modern answer is to let timedated/timesyncd plus the kernel handle RTC writes.

### Q: What lives in /etc/adjtime and what do hwclock --show, --get, --adjust do with it?

Three lines: systematic drift (seconds/day) with the last calibration time and residual, the timestamp of the last drift adjustment, and the RTC scale (UTC/LOCAL). `--show` reads the RTC *with* drift correction applied; `--get` reads it raw; `--adjust` adds the accrued drift to the RTC (useful for machines kept powered off); `--systohc`/`--set` recalibrate and re-stamp the file. The third line is what timedatectl edits for local-RTC policy.

### Q: You're building a minimal initramfs. Which hwclock calls do you need and why?

At minimum `hwclock -s` (hctosys) early, so file timestamps and certificate validity checks see real time before the real root is up — provided the kernel lacks CONFIG_RTC_HCTOSYS. If your initramfs mounts / read-only and has its own adjtime, pass `--adjfile` explicitly or `--noadjfile` to avoid touching the wrong state, and make sure the busybox-vs-util-linux option set you use exists in the image.

### Q: How do you measure a machine's RTC drift without NTP?

`hwclock -c` compares RTC against the system clock at intervals and prints deltas; over hours the slope gives seconds/day. Alternative: record `hwclock --get` and `date +%s`, wait, repeat, and compute. Feed the measured drift into `--systohc` calibrations (which update adjtime) — this is exactly what pre-NTP Unix administration did.

### Q: Which kernel mechanisms move time between RTC and system clock without any hwclock call, and what are their limits?

Two build-time options: `CONFIG_RTC_HCTOSYS` copies the RTC into the system clock once, early in boot (device picked by `CONFIG_RTC_HCTOSYS_DEVICE`); `CONFIG_RTC_SYSTOHC` writes the system clock back to the RTC periodically — but only while the kernel believes the time is disciplined, i.e. an NTP client has cleared `STA_UNSYNC` via `adjtimex(2)`. Without NTP the writeback never runs, so offline machines still need explicit `hwclock -w`. Knowing which options your kernel has (check the config for the running release) tells you whether boot/shutdown hwclock calls are redundant or essential.

### Q: A datacenter appliance runs with no NTP. Where does hwclock fit in its time design, end to end?

Boot: `hwclock -s` (or RTC_HCTOSYS) gets the system clock into the right ballpark before logs and certificates are evaluated. Operation: measure drift with `hwclock -c`, and let periodic `--systohc` calls recalibrate adjtime so each boot starts closer than the last. Long power-offs: `--adjust` advances the RTC by the recorded drift before `--hctosys` reads it. Shutdown: `hwclock -w` stamps the last known-good system time. The adjtime file is the whole state machine — back it up with the machine's config.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux-extra/hwclock.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
