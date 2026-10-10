# Single-User Mode and sulogin

## Overview

Single-user mode is the sysvinit equivalent of an operating room: the system runs the minimum machinery needed to give a root shell on the console, with no services, no getties, and no network unless you start them yourself. It exists for exactly the situations where a normal boot or a running system cannot help you — a filesystem that fails its check, an `/etc/fstab` typo that stops the root mount, a root password that nobody remembers, or a service configuration change that must be made with the service guaranteed down.

The gatekeeper of this mode is `sulogin(8)`, the single-user login program. Unlike a normal getty/login pair, sulogin authenticates only root, runs on whatever console device init hands it, and — crucially — is wired into the boot machinery as a *fallback*: when a boot-critical script fails, distributions drop to sulogin instead of continuing, which is the origin of one of the most famous prompts in Unix operations, "Give root password for maintenance (or type Control-D to continue)".

This page covers the three ways to enter single-user mode, the exact semantics of runlevel S versus runlevel 1 (a subtle distinction that makes a good interview question), what sulogin does and does not do, a recovery cookbook for the classic breakage scenarios, and the contrast with systemd's `rescue.target` and `emergency.target`. The goal is that you can not only use single-user mode but also reason about *which* minimal environment you are in and what each one guarantees.

## Why Single-User Mode Exists

Four workloads justify the mode's existence, and each shapes its design:

- **Filesystem repair.** `fsck` on a mounted, writable root filesystem is undefined behavior in the best case and data destruction in the worst. Single-user mode gives you a console before services start, where remounting root read-only and running fsck is safe.
- **Boot-blocking repair.** When `checkroot.sh` cannot find or mount the root device because of an fstab error, the boot cannot proceed — but the system is *almost* up: kernel modules loaded, /proc and /dev populated, root mounted read-only or rw. Dropping to sulogin lets you fix one line in `/etc/fstab` and continue booting, rather than reaching for install media.
- **Password and account recovery.** Root password resets, correcting a corrupted `/etc/shadow` entry, or unlocking an account — all need privileged local access before any network service runs.
- **Deep service maintenance.** Some database and cluster software demands that nothing else on the host runs during certain operations. Single-user mode guarantees it.

The design consequence of these workloads is a tension: the environment must be *minimal* (nothing that could interfere with repair) but *sufficient* (device nodes, /proc, /sys, a usable terminal). sysvinit threads this needle through the inittab action classes: the `sysinit`, `boot`, and `bootwait` entries run regardless of the requested runlevel, so the plumbing exists even when booting straight into S (per `init(8)`), while all the per-runlevel stuff — getties, network, daemons — is skipped.

## Three Ways In

### 1. Kernel Command Line at Boot

Append one of these in the bootloader:

```text
single        # the classic keyword; init enters single-user mode after sysinit entries
S             # or the equivalent letter
1             # boot directly into runlevel 1
```

Per `init(8)`, when the kernel command line requests single-user operation, init still executes the `sysinit`, `boot`, and `bootwait` entries from `/etc/inittab` first — so virtual filesystems are mounted, udev has populated `/dev`, and the base boot scripts have run — and *then* enters single-user mode instead of switching to the default runlevel. This is why sulogin arrives with a functional environment rather than a bare kernel.

Debian's stock inittab wires the mode to sulogin with one line:

```text
# What to do in single-user mode.
su:S:wait:/sbin/sulogin
```

The `wait` action means init starts sulogin and blocks until it exits. When you exit the maintenance shell, the `wait` entry completes and init continues on its way into the default runlevel — so **exiting sulogin resumes the boot**. This surprises people who expected the machine to stay down; it is the documented behavior and the reason Ctrl-D at the sulogin prompt means "continue booting."

### 2. telinit from a Running System

From multiuser, `telinit 1` or `telinit S` both reach a maintenance state, but through different machinery:

| Aspect | `telinit 1` | `telinit S` |
|--------|-------------|-------------|
| Treated as | A normal runlevel change | Immediate single-user entry |
| rc scripts run? | Yes: K scripts of the old runlevel, then S scripts of `/etc/rc1.d/` | No rc run at all; init tears processes down and starts only the S-marked inittab entries |
| How you get sulogin | Debian ships a `single` init script (initscripts) started in runlevel 1; it hands the console to sulogin after the level-1 services settle | Directly, via the `su:S:wait:/sbin/sulogin` inittab entry |
| Speed | Slower (full service stop sequence) | Faster (kills and goes) |
| Use when | You want the *ordered* stop path exercised (e.g., testing K scripts) | You want a console now and accept abrupt process termination |

The runlevel-1 path is a superset: services actually get stopped in dependency order, which makes `telinit 1` the recommended way to exercise the stop half of a service's lifecycle (see [custom-init-scripts.md](./custom-init-scripts.md)). The S path is closer to "kill everything, give me a shell" — exactly what the K-script cascade would eventually accomplish, minus the ceremony.

### 3. Boot Failure Fallback

When a boot-critical script fails, the boot scripts invoke sulogin directly rather than continuing. The canonical case is the root filesystem check: if `fsck -a` on the root device fails (exit status 4 or higher signals unrepaired errors), or `checkroot.sh` cannot mount the root device at all, the script execs sulogin and you see:

```text
fsck died with exit status 4
Give root password for maintenance (or type Control-D to continue):
```

That message is printed by sulogin itself. Control-D makes sulogin exit, which completes the calling script with the failure path — behavior varies by script, but the usual outcome is that the boot either retries or halts. Logging in gives you the maintenance shell with the failure context (dmesg, the fsck output) still on the console above.

## S versus 1 versus the Default Runlevels

A focused comparison of what is actually running in each state (the full runlevel model is in [runlevels.md](./runlevels.md)):

| Property | Runlevel S | Runlevel 1 | Runlevels 2-5 |
|----------|-----------|------------|----------------|
| init itself | yes | yes | yes |
| sulogin | yes (inittab `wait` entry) | yes (via `single` script) | no |
| getties on consoles | no | no | yes |
| rc scripts | not run | rc1.d S scripts | full set |
| network | nothing configured | usually not | configured |
| syslog | not running unless started | depends on distro's rc1.d | running |
| who respawns things | init only, for inittab S entries | init, per rc1.d | init, per inittab |
| typical entry | boot `single`/`S`, boot failure fallback | `telinit 1` | normal boot |

The practical rule: **S means "init + sulogin + whatever you start by hand."** If you need syslog, bring it up yourself (`syslogd` from the console); if you need the network, configure it by hand (next section); if you need /var writable, check that it mounted — none of that is arranged for you in S. Runlevel 1 differs mainly in that the stop sequence of your previous runlevel actually executed, so it is cleaner for "take the service down properly, then work."

## sulogin(8) in Depth

`sulogin(8)` (shipped by util-linux on Debian) is invoked by init or by boot scripts. Its contract:

- **Authentication is root-only.** It prompts for the root password and verifies it against the system password database. There is no username prompt and no PAM stack — sulogin does its own check, which is deliberate: it must work when PAM configuration itself is broken.
- **The console is its terminal.** It takes over the device it was given (normally the console), sets it up as the controlling terminal for the shell it will start, and operates in raw line mode.
- **On success it starts a shell.** The shell is chosen by: the `$SUSHELL` (or `$sushell`) environment variable if set, then root's configured login shell from `/etc/passwd`, then `/bin/sh` as the fallback. The environment is minimal — do not expect your normal root profile, PATH quirks included.
- **On exit, the caller continues.** Since init runs it under a `wait` action, exiting the shell lets the boot proceed (or lets the failed script continue down its failure path).

Options worth knowing:

- `-e` — the emergency bypass. If the root password *cannot be obtained or verified* (locked account, missing or corrupted `/etc/shadow` entry), start the shell directly instead of failing. Note the precise scope: it is not a "skip the password" flag when the password is intact and simply unknown; it covers the case where authentication is impossible.
- `-p` — start a login-style shell rather than the default behavior.
- `-t SECONDS` — bound how long sulogin waits at the password prompt before giving up (used by callers that must not hang forever waiting for a human).

The mixed blessing of sulogin's design is that it bypasses PAM. When `/etc/pam.d` is broken, sulogin still works. But it also means no audit session, no pam_limits, and no environment setup — appropriate for a maintenance context, wrong for anything routine.

## sulogin versus init=/bin/sh versus init=/bin/bash

When the bootloader is available, there is a second family of rescue entry points: overriding PID 1 entirely with `init=/bin/sh` (or `/bin/bash`). They solve overlapping but different problems:

| Property | sulogin (single/S) | init=/bin/sh | init=/bin/bash |
|----------|--------------------|--------------|----------------|
| Root password required | yes (unless `-e` applies) | no | no |
| inittab read | yes | no | no |
| sysinit entries (mounts, udev) | yes | no — bare environment, /proc /dev may be unmounted | no |
| Orphan reaping | init is still PID 1 and reaps | PID 1 is sh; zombies accumulate | PID 1 is bash; zombies accumulate |
| Ctrl-D behavior | continues boot | terminates PID 1 → kernel panic | terminates PID 1 → kernel panic |
| Job control | proper (init's session) | shell has no controlling terminal handling; weird Ctrl-C behavior | similar caveats |
| Clean exit path | just `exit`; boot continues | manual: `sync`, remount ro, `reboot -f` or `exec /sbin/init` | same as sh |

Guidance:

- **Reach for sulogin first.** It gives you a real (if minimal) init above you: sysinit mounts done, orphan reaping handled, and a clean continuation when you are finished.
- **`init=/bin/sh` is for when sulogin cannot authenticate you** — the lost-root-password case, or when inittab itself is broken. The shell-as-PID1 caveats are real: job control misbehaves, orphans are never reaped (they pile up as zombies), and ending the session the wrong way panics the kernel. The disciplined exit is:

  ```sh
  mount -o remount,rw /
  # ... do the repair ...
  sync
  mount -o remount,ro /
  exec /sbin/init      # hand control to a real init, or use reboot -f
  ```

- **`init=/bin/bash` buys you line editing and history** in exchange for the same caveats. On systems where `/bin/bash` itself is broken (e.g., a botched libc or loader upgrade), neither works — see the recovery cookbook below.

Security note: any of these paths requires console or bootloader access, and none requires the root password. This is why physical/console security is the actual root security boundary, why bootloaders offer password protection, and why "we disabled root login over SSH" is not a security posture by itself.

## Recovery Cookbook

The standard sequence of a sysvinit rescue session. Every step assumes you are at the sulogin prompt with a minimal environment.

### Remount Root Read-Write

Boots that dropped to sulogin after a fsck failure usually have root mounted read-only (by design, so fsck could run):

```sh
mount -o remount,rw /
```

Without this, password changes, fstab edits, and package operations all fail with read-only errors. When finished, reverse it before rebooting:

```sh
sync
mount -o remount,ro /
```

### Filesystem Check on Root

Never run fsck against a read-write mounted filesystem. From single-user:

```sh
mount -o remount,ro /
fsck -f /dev/sda1        # -f forces a full check, not just journal replay
```

If the filesystem cannot be remounted read-only because a process holds files open, find it (`fuser -vm /` where available) and kill it first — in S there is little else running to get in the way, which is the point of the mode.

### Fixing a Broken /etc/fstab

The classic trap: a bad UUID or device name in `/etc/fstab` stops `checkroot.sh` from mounting root, dropping you to sulogin. Repair flow:

```sh
mount -o remount,rw /
lsblk -f                       # or blkid; find the real UUID/LABEL
vi /etc/fstab                  # fix the identifier (or use a stable LABEL)
mount -a                       # dry-validate everything else mounts
mount -o remount,ro /
exec /sbin/init                # continue the boot
```

Watch for the `noauto` interaction: options like `noauto` are correct for swap-like or manually mounted entries, but a fat-fingered `noauto` on a needed filesystem makes later boots "work" until something else fails. Also remember the ordering constraint that made the fstab matter in the first place: `$local_fs` and `$remote_fs` in LSB headers (see [lsb-headers.md](./lsb-headers.md)) exist precisely because script start order depends on mounts completing.

### Resetting a Lost Root Password

1. Reboot and set `init=/bin/sh` (or boot `single` if you still know the password — but in the lost-password case you do not, so sulogin cannot help).
2. `mount -o remount,rw /`
3. `passwd root` — or edit `/etc/shadow` directly if passwd is broken.
4. `sync; mount -o remount,ro /; exec /sbin/init` (or `reboot -f`).

Caveats: if the root account is *locked* rather than merely unknown, sulogin's normal authentication cannot succeed, which is the case where `sulogin -e` (arranged by the caller) or the `init=/bin/sh` path is required. On systemd systems the equivalent tricks are `rd.break` (dracut-based initramfs) or editing the kernel line to `systemd.unit=rescue.target` — see [../systemd/targets-runlevels.md](../systemd/targets-runlevels.md); the sulogin prompt still appears there because systemd's rescue target runs sulogin too.

### Recovering from a Broken /lib or Dynamic Loader

A failed glibc or loader upgrade can leave every dynamically linked binary dead (`error while loading shared libraries`). If `init=/bin/sh` works (dash is dynamically linked too, but the kernel's own initramfs tools may not be), you are limited to statically-linked tools. In practice: boot install/rescue media, mount the root filesystem, and either fix the tree by hand or chroot with a working set of libraries. The full live-media/chroot procedure is in [../../admin/rescue.md](../../admin/rescue.md); single-user mode on the broken system itself is usually *not* sufficient at this severity, because the tools you would repair with are the tools that are broken.

## Networking in Single-User Mode

Nothing configures the network for you in S. If you truly need it — fetching a package, copying logs off, reaching a remote console target — configure it manually with `ip(8)`:

```sh
ip link set eth0 up
ip addr add 192.0.2.10/24 dev eth0
ip route add default via 192.0.2.1
echo 'nameserver 192.0.2.53' > /etc/resolv.conf
```

Reasons to hesitate before doing this:

- No firewall rules are loaded (the firewall restore script never ran), so the host is wide open while exposed.
- Services you start by hand (sshd, for example) run outside any supervision and outside the usual hardening (root directly, no PAM session hardening).
- State you create by hand (addresses, routes) is exactly the kind that conflicts with the real network configuration when the boot continues.

The judgment call: bring up the network only as long as needed, for a bounded purpose, and tear it down (`ip addr flush dev eth0; ip link set eth0 down`) before continuing the boot.

## What Runs Around S During a Boot

Placing single-user mode in the boot timeline (see [boot-sequence.md](./boot-sequence.md) for the whole picture):

```text
kernel boots
  -> init reads /etc/inittab
  -> sysinit / boot / bootwait entries run   (mounts, udev, bootlogd)
  -> [booting 'single']  init enters runlevel S
        -> su:S:wait:/sbin/sulogin runs; console awaits root
        -> shell session happens
        -> sulogin exits
  -> init proceeds to the default runlevel (rc 2/3/...)
```

Two consequences worth internalizing: the base filesystem layout exists when you hit the sulogin prompt (that is the sysinit entries), and everything from getties onward does not (that is the runlevel you skipped). On systemd the same niche is filled by `rescue.target` (sulogin after sysinit, roughly "runlevel 1") and `emergency.target` (sulogin with only the root filesystem, used when basic mounts fail) — the mapping is in [../systemd/targets-runlevels.md](../systemd/targets-runlevels.md).

## Logging and Audit Considerations

Single-user sessions are, by design, poorly represented in the usual accounting files:

- sulogin does not run a PAM session, so the modules that normally write `utmp`/`wtmp` records and `lastlog` may not fire. Whether a maintenance session appears in `last` output depends on the implementation and the code path that invoked it — do not rely on it for audit.
- What you *can* rely on: kernel messages (console and `dmesg`), boot-time script output captured by `bootlogd(8)` into `/var/log/boot` where enabled (see [utilities.md](./utilities.md)), and wtmp records for the *runlevel changes themselves*, which init writes even when the sessions in between are invisible.
- If compliance requires evidence of maintenance access, sysvinit single-user mode is the wrong control surface — console access logging (serial console capture, BMC/sol logging) is the mechanism that actually works, because it records the physical/virtual console rather than trusting the OS.

## Interview Questions

### Q: What is the difference between telinit 1 and telinit S?

`telinit 1` is a normal runlevel change: init runs the K scripts of the current runlevel for services not present in runlevel 1, then the S scripts of `/etc/rc1.d/` — which on Debian include the `single` helper that ultimately hands the console to sulogin. `telinit S` bypasses rc entirely: init kills the current processes and starts only the entries marked for runlevel S in inittab (the sulogin line). In practice: 1 stops services in dependency order and is the right choice when you want the stop path exercised; S is the fast "kill and give me a shell" path.

### Q: You forgot the root password. Why can't sulogin help you, and what are your actual options?

Sulogin verifies the root password before starting a shell, so a forgotten password is a dead end there — it will never authenticate you. `sulogin -e` does not help either: it bypasses the password check only when authentication is *impossible* (locked or unreadable shadow entry), not when the password is intact and unknown. The real path is bootloader-based: `init=/bin/sh`, `mount -o remount,rw /`, `passwd root`, sync, remount read-only, and hand back to init or reboot. This requires console/bootloader access, which is exactly why bootloader passwords and console security exist.

### Q: Why do the sysinit entries still run when you boot with the single flag?

Because per `init(8)`, the `sysinit`, `boot`, and `bootwait` action classes are executed at boot before any runlevel is entered, regardless of which runlevel was requested. Their runlevel field is ignored by design. This is what gives single-user mode a usable environment — /proc, /dev (via udev), and the base mounts — without pulling in any per-runlevel services. Booting "into S" therefore means "full plumbing, no services," not "kernel plus shell."

### Q: What happens when you exit the sulogin shell, and why?

The `su:S:wait:/sbin/sulogin` entry is a `wait` action: init started sulogin and blocked on it. When your shell exits, sulogin exits, the wait completes, and init continues executing the boot — moving on to the default runlevel. That is why Control-D at the "Give root password for maintenance" prompt means "continue booting": it terminates the sulogin process, completing the wait entry. It is also why single-user mode is a *pause* in the boot, not a terminal state.

### Q: Why is running fsck on a mounted, read-write root filesystem dangerous, and what is the correct procedure?

fsck assumes its view of the filesystem metadata is authoritative while it repairs. Against a live filesystem, the kernel is concurrently mutating that metadata, so fsck's writes can race the kernel's — the result is corruption of exactly the structures fsck was trying to fix. The procedure is: get to single-user mode, `mount -o remount,ro /` (kill any straggler processes holding files open), then `fsck -f` against the device. In S almost nothing is running, which is the entire reason the mode exists for this job.

### Q: What does init=/bin/sh cost you compared to booting single into sulogin?

Everything init normally provides: sysinit mounts, orphan reaping (sh as PID 1 does not reap reparented zombies), inittab-driven respawns, and the clean continuation path. Job control behaves oddly because the shell is PID 1 without the usual session scaffolding, and typing Ctrl-D kills PID 1 and panics the kernel. The disciplined exit is `sync`, remount root read-only, then either `exec /sbin/init` or `reboot -f`. You reach for it only when sulogin cannot authenticate you or inittab itself is broken.

## References

- [sulogin(8) — util-linux](https://manpages.debian.org/bookworm/util-linux/sulogin.8.en.html)
- [init(8) — sysvinit](https://manpages.debian.org/bookworm/sysvinit-core/init.8.en.html)
- [inittab(5) — sysvinit](https://manpages.debian.org/bookworm/sysvinit-core/inittab.5.en.html)
- [shutdown(8) — sysvinit](https://manpages.debian.org/bookworm/sysvinit-core/shutdown.8.en.html)
- [agetty(8) — util-linux](https://manpages.debian.org/bookworm/util-linux/agetty.8.en.html)

## Cross-References

- [runlevels.md](./runlevels.md) — the full runlevel model S and 1 sit inside.
- [inittab.md](./inittab.md) — the `su:S:wait` entry, action classes, and respawn semantics.
- [boot-sequence.md](./boot-sequence.md) — where single-user entry lands in the overall boot timeline.
- [getty-terminals.md](./getty-terminals.md) — the normal-mode console machinery single-user bypasses.
- [shutdown-halt.md](./shutdown-halt.md) — the controlled way down when maintenance finishes.
- [../systemd/targets-runlevels.md](../systemd/targets-runlevels.md) — rescue.target and emergency.target, the systemd equivalents.
- [../../admin/rescue.md](../../admin/rescue.md) — live-media and chroot recovery beyond what single-user mode can fix.
- [../README.md](../README.md) — the init-systems section hub.
