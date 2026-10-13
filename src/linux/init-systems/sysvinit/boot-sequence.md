# The sysvinit Boot Sequence

## Overview

The boot sequence is where sysvinit's whole architecture is visible in one pass: firmware hands control to the kernel, the kernel starts `/sbin/init` as PID 1, init reads `/etc/inittab`, executes the `sysinit`/`boot`/`bootwait` entries (on Debian, the `rcS` phase), enters the default runlevel and runs the per-runlevel `rc` pass, and finally spawns the `respawn` entries — the gettys — that make login possible. Every step is synchronous and observable: you can stand at a shell prompt and replay each phase by hand. That is the defining property of this sequence and the reason it remains the reference point against which systemd's parallelized boot is explained.

This page walks the full chain in order, with Debian bookworm script names, the environment init exports to its children, PID 1's special process semantics, boot accounting (utmp/wtmp and bootlogd), and — critically for interviews and for real incidents — the failure paths: missing or broken `inittab`, `init=/bin/sh` escapes, fsck failures that drop you to `sulogin`, and the initramfs handoff that sits between the kernel and real init on every modern distribution.

## From Firmware to PID 1

The chain begins before Linux exists. The firmware (BIOS or UEFI) selects a boot device and loads a bootloader (GRUB2 on modern Debian), which loads the kernel and optional initramfs into memory and jumps to the kernel entry point with a command line. The kernel initializes drivers, mounts the root filesystem (directly, or via the initramfs), and then must answer one question: *which userspace program runs first?* The kernel command line controls this:

```text
init=/sbin/init      # explicit PID 1 (the kernel default when init= is absent)
rdinit=/bin/sh       # PID 1 inside the initramfs, before the real root is mounted
single | S | 1..5    # request an initial runlevel instead of initdefault
```

If no `init=` is given, the kernel tries a fixed list of historical candidates — `/sbin/init`, then `/etc/init`, then `/bin/init`, then `/bin/sh` — which is why a system with a damaged `/sbin/init` falls back to a raw shell rather than a kernel panic. The firmware and bootloader stages are covered in depth in [bios-uefi.md](../../../os/boot/bios-uefi.md) and [bootloader.md](../../../os/boot/bootloader.md); kernel-side startup details (including how the initramfs is unpacked and `execute_command` dispatches to PID 1) are in [kernel-boot.md](../../kernel/core/kernel-boot.md).

From this point the kernel's role is mostly passive: PID 1 is now an ordinary process as far as scheduling goes, but a very special one as far as process semantics go (see [PID 1 Semantics](#pid-1-semantics-what-makes-init-unkillable) below).

## What init Does First

`/sbin/init` (from package `sysvinit-core`) performs a short, fixed startup sequence before anything else in userspace happens:

1. **Open the console.** init opens `/dev/console` for its own messages. If it cannot, the boot is over before it began — there is nowhere to report the failure.
2. **Install signal handlers.** Handlers are registered for SIGPWR (UPS power events), SIGINT (the Ctrl-Alt-Del key sequence on the console), SIGWINCH (special key combinations from the keyboard driver), and SIGCHLD (child termination, i.e., the reaping duty). A separate pipe, `/run/initctl` (legacy location `/dev/initctl`), carries commands from `telinit`.
3. **Read `/etc/inittab`.** The whole file is parsed into an internal table of entries: `id:runlevels:action:process`. If the file cannot be opened, init *does not crash* — it behaves as if the file were empty, which has consequences discussed under [Failure Paths](#failure-paths). Parsing errors in individual lines are reported to the console and that line is skipped.
4. **Process the boot entries in canonical order.** `sysinit` entries run first, then `boot`, then `bootwait` — regardless of where they appear in the file. All three ignore the runlevel field. init *waits* for `sysinit` and `bootwait` processes (not for `boot`); nothing else happens until they exit.

Only after the boot entries complete does init look for the `initdefault` entry to decide the initial runlevel (falling back to asking on the console if `initdefault` is missing), and then execute the `wait` entries — on Debian, `l2:2:wait:/etc/init.d/rc 2` — for that runlevel.

The flags `init -b` (emergency: skip `sysinit`/`boot`/`bootwait` entirely, boot straight to a single-user shell) and `init -s` (single-user) modify this sequence and are normally reached via the kernel command line (`init=/sbin/init -b` in the bootloader) rather than typed by hand.

## The rcS Phase: One-Shot System Setup

On Debian, the `sysinit` entry is the single line `si::sysinit:/etc/init.d/rcS`. That script is a tiny driver: it sources `/lib/lsb/init-functions`, sets up the logging helpers, and executes every `S*` symlink in `/etc/rcS.d/` in lexical order, calling each target script with `start`. The `rcS.d` set is *not* a runlevel in the service sense — it is the one-shot "make the machine minimally usable" phase, and it must complete before any service logic runs.

Representative order (exact numbering varies by release; the sequence semantics do not):

```text
/etc/rcS.d/S01mountkernfs.sh    proc, sysfs, devtmpfs on /proc /sys /dev
/etc/rcS.d/S01udev              start udev, populate /dev from kernel events
/etc/rcS.d/S02mountdevsubfs.sh  devpts, tmpfs, shm under /dev
/etc/rcS.d/S03hostname.sh       set the hostname
/etc/rcS.d/S05checkroot.sh      fsck the root filesystem, remount it rw
/etc/rcS.d/S06checkfs.sh        fsck all other filesystems
/etc/rcS.d/S07mountall.sh       mount everything in /etc/fstab
/etc/rcS.d/S07mountall-bootclean.sh   clean /tmp, /run lock dirs
/etc/rcS.d/S08networking        configure loopback (and static interfaces)
/etc/rcS.d/S09bootlogd stop?    bootlogd runs much earlier; see below
```

Three properties of this phase are worth internalizing because interviewers probe them:

- **It is strictly sequential.** fsck of `/` must finish before `mountall.sh` runs; udev must be live before device-dependent scripts start. There is no parallelism here by design.
- **It is idempotent-ish and non-respawning.** Nothing in `rcS.d` is long-running (udev's daemon starts, then the script returns). If a script fails, `rcS` logs and continues where it safely can — a failed fsck being the exception that triggers the `sulogin` path below.
- **It runs regardless of the eventual runlevel.** Single-user, multiuser, rescue — `sysinit` entries always run first, which is why mounting filesystems lives here and not in `rc2.d`.

`VERBOSE=yes` in the legacy `/etc/default/rcS` (or its modern equivalent setting) makes `rcS` echo each script before running it — the poor man's boot tracing when `bootlogd` is not capturing output.

## The Default Runlevel and the rc Pass

With `rcS` complete, init reads `id:2:initdefault:` (Debian's default) and executes the matching `wait` entry:

```text
l0:0:wait:/etc/init.d/rc 0
l1:1:wait:/etc/init.d/rc 1
l2:2:wait:/etc/init.d/rc 2      <-- Debian default path
l3:3:wait:/etc/init.d/rc 3
l4:4:wait:/etc/init.d/rc 4
l5:5:wait:/etc/init.d/rc 5
l6:6:wait:/etc/init.d/rc 6
```

`/etc/init.d/rc <N>` — a shell script shipped by sysvinit-core, not part of the `init` binary — walks `/etc/rcN.d/`: first the `K*` stop links (relevant on transitions *out* of a runlevel; on a fresh boot there is nothing to stop), then the `S*` start links in `NN` order, calling each `/etc/init.d/<name>` with `start`. On dependency-mode systems, the order is taken from the `.depend.start`/`.depend.stop` files that insserv generated from LSB headers rather than from raw symlink names. The mechanics — including how `K` scripts decide whether to actually stop anything, and how `update-rc.d` builds these directories — are the subject of [rc-symlinks.md](./rc-symlinks.md); the runlevel model itself is covered in [runlevels.md](./runlevels.md).

When `rc` returns, init starts all `respawn` entries whose runlevel field includes the new level: the gettys on `tty1`–`tty6` (on Debian, `tty1` in levels 2–5, `tty2`–`tty6` in 2–3), and anything else marked `respawn`. From this moment the system is *live*: login prompts exist, and init settles into its steady-state loop — waiting on children, reaping orphans, restarting respawned processes that exit, and reacting to signals.

### Getty respawn: when login becomes possible

The getty entries are worth a precise look because they are the only long-lived supervision init performs. A typical Debian line:

```text
1:2345:respawn:/sbin/getty 38400 tty1
```

init forks and execs `/sbin/getty` on `tty1`; getty prints the prompt and execs `login`; login execs your shell. If that process chain ever exits — you log out, the session dies, someone kills it — init notices via SIGCHLD and starts the line again, forever. Two guard rails apply: respawn *throttling* (a process that dies too fast is not restarted immediately; init delays on the order of five minutes when a spawn rate limit is exceeded, logging the fact, so a broken getty line does not spin the CPU) and utmp/wtmp accounting (getty entries normally do their own accounting; entries whose process field starts with `+` suppress init's, a detail reserved for [inittab.md](./inittab.md)). Note the boot-order consequence: no getty exists until `rc` finishes, so a hung boot script means no login prompt — the visible symptom that maps a "can't log in" report back to a specific phase of this sequence.

A realistic Debian boot timeline, compressed:

```text
t0  firmware POST; bootloader loads kernel + initramfs
t1  kernel unpacks initramfs, runs its /init (busybox or systemd-based)
t2  initramfs loads drivers, finds root FS, switch_root -> real root
t3  kernel execs /sbin/init as PID 1 (sysvinit 3.09 on bookworm w/ sysvinit-core)
t4  init opens /dev/console, installs handlers, reads /etc/inittab
t5  si::sysinit  -> /etc/init.d/rcS -> rcS.d/S*: udev, fsck /, fsck rest, mounts, lo
t6  initdefault 2 -> l2:2:wait:/etc/init.d/rc 2
t7  rc 2: S01cron, S01dbus, S01rsyslog, ... S02ssh, ... S99rc.local (in .depend order)
t8  respawn: getty tty1..tty6; login becomes possible
t9  steady state: init waits on SIGCHLD, restarts dead respawn entries
```

## The initramfs Handoff

Every modern distribution boots through an initramfs, and the handoff is a common interview trap because there are *two inits in sequence*. Inside the initramfs, PID 1 is a small program — BusyBox `init` or a shell script (Debian's `initramfs-tools` uses shell), or even a stripped-down systemd in some distributions — whose only jobs are: load the modules needed to see the real root device (storage, dm-crypt, RAID, NFS), assemble the root filesystem, and call `switch_root` (or `pivot_root`) to replace the initramfs with the real root. The initramfs init then execs the real init on the new root — `/sbin/init` — which starts *its* life as PID 1 from that moment.

Two details worth stating precisely:

- `rdinit=` selects PID 1 *inside* the initramfs; `init=` selects PID 1 *after* the switch. They are different processes at different times.
- The real init never sees the initramfs. If you pass `init=/bin/sh`, you bypass the real init entirely — no `rcS`, no runlevels, no gettys — which is exactly why it is a rescue tool and not a configuration (see [Failure Paths](#failure-paths)).

The BusyBox init dialect is a simplified `inittab` with actions like `::sysinit:`, `tty1::respawn:` and no runlevel directories; it is documented in [busybox.md](../../binaries/busybox.md). The same dialect appears in initramfs images and in many embedded systems, so it is worth being able to read it side by side with the full grammar in [inittab.md](./inittab.md).

## The Environment init Provides

Every process init starts (rc scripts, gettys, sulogin) inherits a small environment that makes the boot context introspectable from inside scripts:

| Variable | Meaning | Typical use in scripts |
|---|---|---|
| `INIT_VERSION` | sysvinit version string, e.g. `sysvinit-3.09` | Detect that the script really runs under sysvinit |
| `RUNLEVEL` | Current (or newly entered) runlevel | `rc` uses it to select `/etc/rcN.d`; scripts branch on it |
| `PREVLEVEL` | Previous runlevel (`N` if none) | Lets `rc` and scripts distinguish boot from transition |
| `CONSOLE` | The console device, `/dev/console` | Where to write boot-time diagnostics |

This is how `/etc/init.d/rc` knows which directories to walk and which direction the transition goes, and how a script can say "only do this on boot, not on runlevel changes" by checking `PREVLEVEL=N`. Note that these variables are set by init for its children — they are not shell profile variables, and they are absent in processes started by other means (cron, an interactive login), which is a classic source of "works at boot, fails by hand" (or vice versa) bugs.

## PID 1 Semantics: What Makes init Unkillable

Everything sysvinit does rests on three kernel-level privileges and duties of being PID 1:

1. **It cannot be killed.** The kernel refuses fatal signals to PID 1 unless the process installs a handler for them. You cannot `kill -9 1` a healthy sysvinit; even a wedged init keeps its slots. (You can, however, ask it to change behavior — `telinit 0` triggers a clean shutdown path rather than a kill.)
2. **It is the orphan reaper.** When a parent dies before its children, the orphans are reparented to PID 1, and when *they* exit, init must reap them or they become zombies. A sysvinit init does this in its main loop as a matter of course; a process that is PID 1 by accident is not, which is the core of the `init=/bin/sh` problem below.
3. **It has no controlling terminal and is in its own session.** Job-control signals from the console do not reach it, and it survives terminal hangs up.

The wider consequences of PID 1 semantics — signal defaults, zombie reaping, why containers ship `tini` or `--init` flags, what happens when PID 1 exits in a PID namespace — are treated in [creation.md](../../../os/processes/creation.md) and [daemons.md](../../../os/processes/daemons.md). For this page, the operational takeaway is: PID 1 is not just "the first process"; it is a role with kernel-enforced duties, and sysvinit's main loop is a minimal implementation of that role.

## Replaying the Boot by Hand

Because every phase is an ordinary program invocation, the whole sequence can be rehearsed in a rescue shell or a container — an invaluable skill for debugging boot problems offline. The manual equivalent of each automatic step:

```console
# Phase t4 equivalent: init would open the console and read inittab.
# You can preview what init WILL do by parsing the same file:
grep -Ev '^(#|$)' /etc/inittab

# Phase t5 equivalent: the entire rcS pass, verbatim, by hand:
/etc/init.d/rcS
# (run it again and it is mostly harmless: fsck -a on clean FS, mounts already mounted)

# Phase t6-t7 equivalent: enter runlevel 2 manually from single-user.
# init normally does this; by hand you must provide what init provides:
export RUNLEVEL=2 PREVLEVEL=S INIT_VERSION=sysvinit-3.09 CONSOLE=/dev/console
/etc/init.d/rc 2

# Phase t8 equivalent: spawn one getty exactly as a respawn entry would:
/sbin/agetty --noclear tty3 38400 vt100     # foreground; Ctrl-C ends it

# Account for the boot as init would have (utmp records):
who -r                                      # shows "run-level N" if utmp has a RUN_LVL record
```

Two cautions when rehearsing. First, running `rc 2` without exporting `RUNLEVEL`/`PREVLEVEL` produces a degraded, order-only approximation: modern `rc` consults those variables (and the `.depend.*` files) to decide what to start and stop, so an unexported manual run may start services in a different order than the real boot did. Second, starting services by hand in a rescue environment starts them *in your session* — with your controlling terminal, your umask, and your environment — which is precisely the difference a real boot avoids by starting them from init. Use the rehearsal to find failures, not to run production.

The phase map, for quick reference while reading the rest of this section:

| Phase | Actor | Input | Output / side effect | Failure mode |
|---|---|---|---|---|
| Firmware handoff | BIOS/UEFI + bootloader | boot device order | kernel cmdline, loaded kernel+initramfs | wrong device, bad cmdline |
| initramfs | rdinit (busybox/shell) | embedded scripts | drivers loaded, root found, switch_root | missing storage driver -> "no root device" |
| PID 1 start | kernel exec of /sbin/init | `init=` param | console open, handlers, inittab parsed | /sbin/init missing -> /bin/sh fallback |
| Boot entries | init | `sysinit`/`boot`/`bootwait` lines | rcS phase run | inittab unreadable -> inert init |
| rcS | /etc/init.d/rcS | /etc/rcS.d/S* links | udev, fsck, mounts, loopback | fsck fail -> sulogin |
| Default runlevel | init + rc | `initdefault` + `lN` line | rcN.d K*/S* pass, services up | wrong level -> services missing |
| Respawn | init | `respawn` entries | gettys on tty1-6, login live | bad getty line -> throttled respawn loop |
| Steady state | init | signals + SIGCHLD | orphan reaping, respawn restarts | n/a (stateless) |

## Boot Accounting: utmp, wtmp, and bootlogd

Two separate recording systems document a boot, and they answer different questions:

| File | Written by | Contains | Read by |
|---|---|---|---|
| `/var/run/utmp` | init, getty/login | Current system state: `RUN_LVL`, `BOOT_TIME`, `LOGIN_PROCESS`, `USER_PROCESS` records | `who`, `w`, `runlevel(8)` |
| `/var/log/wtmp` | init, login, shutdown | History: every boot, shutdown, runlevel change, login/logout | `last`, `last -x` |
| `/var/log/btmp` | login (and friends) | Failed login attempts | `lastb` |

At boot, init writes a `BOOT_TIME` record and a `RUN_LVL` record (encoding previous runlevel `N` and current runlevel); each subsequent `telinit` writes a new `RUN_LVL` record. `runlevel(8)` reads utmp's `RUN_LVL` entry and prints `N 2`; `last -x` reconstructs the boot/reboot history from wtmp. This is why "what runlevel am I in" is answered from a file, not from PID 1 — the statelessness principle again. The utmp/wtmp formats and the `+` prefix rule in `inittab` (entries whose process field starts with `+` skip utmp/wtmp accounting) are covered in [inittab.md](./inittab.md).

Console output during boot is a separate problem: before syslog is up, everything printed to `/dev/console` would be lost to scrollback. `bootlogd` (its own Debian package, `bootlogd`) is a small daemon started early in `rcS` that sits on the console, copies everything to `/var/log/boot`, and flushes it at boot end. Historically it was enabled via `BOOTLOGD_ENABLE=Yes` in `/etc/default/bootlogd`; modern Debian starts it unconditionally when the package is installed. Reading `/var/log/boot` is the standard way to reconstruct what the `rcS` and `rc` phases printed — invaluable when a boot-time script printed an error that no later log captured.

## Failure Paths

### Missing or unreadable /etc/inittab

init does not refuse to run; it behaves as if `inittab` were empty. The machine reaches PID 1 and then *nothing else happens*: no `rcS`, no mounts beyond what the kernel did, no gettys, no login prompts. The console shows init's complaint and silence. This is a classic boot disaster with a classic fix — boot the same kernel with `init=/bin/sh` (or use the bootloader's recovery entry), repair `/etc/inittab` from the raw shell, and reboot. Note what that raw shell *lacks*, because it matters for diagnosis: no orphan reaping (zombies accumulate), no respawn (a dead process stays dead), no signal handling beyond the shell's defaults, and no `exec init` unless you remember to do it deliberately.

### init=/bin/sh as a rescue tool

The correct procedure at the `init=/bin/sh` prompt is: remount root read-write (`mount -o remount,rw /`), perform the repair, then `sync` and either `exec /sbin/init` (to continue a semi-normal boot) or reboot cleanly. Simply exiting the shell is a bug — PID 1 exiting triggers a kernel panic. The `exec` matters for another reason: it turns the shell into init, so the system's reaping and respawn machinery comes up instead of being absent.

### fsck failures and sulogin

When `checkroot.sh` or `checkfs.sh` cannot bring a filesystem up cleanly (uncorrectable fsck errors, a missing device), the rcS logic drops to `sulogin` — the single-user login from util-linux, which prompts for the root password on the console (on some systems it is reached via the `~~:S:wait:/sbin/sulogin` inittab entry). After repairs, `exit` from the sulogin shell lets the boot continue from where it paused. The full single-user workflow, including bypassing the root password when you have physical access and no password, is covered in [single-user-sulogin.md](./single-user-sulogin.md).

### A wedged or missing real init

If `/sbin/init` itself is corrupt or missing, the kernel's fallback list ends at `/bin/sh` — the same raw-shell state as `init=/bin/sh`. If init is wedged (rare; it has no deadlock-prone state by design), the pragmatic recovery is a hard reset: sysvinit holds no state that can be lost, which is one of the quiet advantages of statelessness. What *does* hold state is the filesystem — hence the emphasis above on remounting rw and syncing deliberately.

## Interview Questions

### Q: In what order does init execute inittab entries at boot?

Canonical order: all `sysinit` entries first, then all `boot` entries, then all `bootwait` entries — in that order, regardless of their position in the file, and with init waiting on `sysinit` and `bootwait` processes. After those complete, init looks up `initdefault` to choose the initial runlevel and runs that runlevel's `wait` entries (on Debian, `/etc/init.d/rc 2`). Saying "top to bottom" is the classic wrong answer — order is determined by action class, not file position.

### Q: What is the difference between the kernel's `init=` and `rdinit=` parameters, and why do modern systems effectively have two init programs?

`rdinit=` selects PID 1 *inside the initramfs* (typically a BusyBox init or shell script that loads drivers and finds the real root); `init=` selects PID 1 *after* the initramfs switch_roots to the real root — the real sysvinit. Because every modern distro boots through an initramfs, there are literally two init processes in sequence, and only the second one reads `/etc/inittab` and runs `rcS`/`rc`. They also fail independently: a bad `rdinit=` leaves you inside the initramfs; a bad `init=` gets you the kernel's fallback chain ending at `/bin/sh`.

### Q: You boot with `init=/bin/sh` to fix a system. Why is `exec /sbin/init` at the end better than just rebooting?

Three reasons. First, PID 1 exiting causes a kernel panic, so "exit the shell" is the worst option. Second, `exec` *replaces* the shell with the real init in the same PID 1 slot, so the system continues booting (rcS, runlevels, gettys) without a reboot — often enough to avoid a full cycle. Third, until the exec, the shell is a PID 1 without the duties: it does not reap orphans, so zombies accumulate, and it has no respawn table, so nothing gets restarted. The exec restores the kernel-enforced PID 1 contract that sysvinit's main loop implements.

### Q: init exports INIT_VERSION, RUNLEVEL, PREVLEVEL, and CONSOLE to children. Name one subtle bug this explains.

The classic: a script that behaves differently "at boot" versus "when I run it by hand." At boot it inherits `RUNLEVEL=2 PREVLEVEL=N`; from your SSH session it inherits your login environment instead. A script checking `RUNLEVEL` or `PREVLEVEL` to skip work on boot, or a script whose behavior depends on `PATH`/`HOME` it only has interactively, will diverge in exactly this way. The general lesson: init-provided environment exists only for init's direct descendants, and init scripts should set their own complete environment rather than assume one.

### Q: Where does the system record "the machine booted at time T into runlevel 2", and which commands read it?

Twice, in two files: a `BOOT_TIME`/`RUN_LVL` record in `/var/run/utmp` (current state; read by `who -r` and `runlevel(8)`) and a permanent history record in `/var/log/wtmp` (read by `last -x`). Separately, everything the boot printed to the console is captured to `/var/log/boot` by `bootlogd` if installed. The complete picture of a suspicious boot is therefore `last -x`, `who -r`, and `/var/log/boot` — none of which require asking PID 1 anything, consistent with sysvinit's stateless design.

### Q: What exactly happens if /etc/inittab is deleted and the machine reboots?

init starts (the kernel's default `/sbin/init` is still present), opens the console, installs its handlers, fails to open `inittab`, and treats it as empty. No `sysinit` entry runs — so `/etc/init.d/rcS` never executes: no udev, no fsck, no `mountall`, no loopback networking. No `initdefault` exists, and no `wait`/`respawn` entries exist, so there are no services and no gettys. The system sits at a console with init alive and idle. Recovery is booting with `init=/bin/sh`, restoring the file, and rebooting — or, if a getty had been configured out-of-band, the outage ends at "system boots to single shell, no services," not to a kernel panic.

## References

- [init(8) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/init.8.en.html) — PID 1 startup order, signal handling, environment, inittab fallback behavior.
- [inittab(5) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/inittab.5.en.html) — action classes and their boot-order semantics.
- [telinit(8) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/telinit.8.en.html) — runtime control of init and runlevel changes.
- [bootlogd(8) — bootlogd man page, Debian bookworm](https://manpages.debian.org/bookworm/bootlogd/bootlogd.8.en.html) — console capture to /var/log/boot.
- [agetty(8) — util-linux man page, Debian bookworm](https://manpages.debian.org/bookworm/util-linux/agetty.8.en.html) — the program behind the respawn entries that end the sequence.
- [sulogin(8) — util-linux man page, Debian bookworm](https://manpages.debian.org/bookworm/util-linux/sulogin.8.en.html) — the single-user login used on fsck failure.

## Cross-References

- [inittab — The Master Configuration](./inittab.md) — the file this sequence parses, field by field and action by action.
- [rc0.d–rc6.d, rcS.d — Symlink Sequencing Mechanics](./rc-symlinks.md) — what `rc` actually does with the directories it walks.
- [Runlevels in Depth](./runlevels.md) — the state model that `initdefault` selects into.
- [Single-User Mode and sulogin](./single-user-sulogin.md) — the rescue paths referenced by the failure section.
- [systemd — Boot Process](../systemd/boot-process.md) — the parallelized, dependency-driven counterpart of this page.
- [BusyBox](../../binaries/busybox.md) — the simplified init/inittab dialect used in initramfs and embedded systems.
- [Kernel Boot](../../kernel/core/kernel-boot.md) — the kernel-side stages before and around the initramfs handoff.
- [Bootloaders](../../../os/boot/bootloader.md) — how the kernel command line (init=, rdinit=, single) gets set.
- [Process Creation](../../../os/processes/creation.md) — fork/exec and PID 1 semantics underlying this page.
- [Init Systems Hub](../README.md) — section map and reading order.
