# The sysvinit Toolset — pidof, killall5, last, wall and Friends

## Overview

Beyond init itself, the sysvinit ecosystem ships a constellation of small utilities that exist *because* an init system needs them: finding a daemon's PID without ps, signaling every process on the machine from a stop script, replaying login history, broadcasting a message to every terminal, and testing whether a directory is really a mountpoint. Individually they are trivial; collectively they define the vocabulary that rc scripts, halt paths, and sysadmin muscle memory are written in. They are also, one by one, the tools that systemd replaced with native mechanisms — which makes them excellent interview material precisely at their retirement.

This page is a field guide. It maps every tool to its Debian package (so you know what a minimal container actually has), documents the option surface that matters in practice, shows the canonical usage patterns from real rc scripts, and ends with a retirement table mapping each tool to its systemd-era successor. Cross-references point to the pages where each tool does its main work: `killall5` in the shutdown path, `last` and the accounting files in the terminal stack, `startpar` in parallel booting.

## Package Map

Where each tool lives on Debian bookworm (the package boundaries matter when you build minimal images or chroots):

| Package | Ships | Role |
|---------|-------|------|
| `sysvinit-core` | `init(8)`, `telinit(8)`, `shutdown(8)`, `halt(8)` (incl. reboot/poweroff names), `runlevel(8)`, `inittab(5)` | PID 1 and the runlevel machinery |
| `sysvinit-utils` | `pidof(8)`, `killall5(8)`, `fstab-decode(8)`, `init-d-script(5)` | The scripting toolkit rc scripts depend on |
| `util-linux` | `sulogin(8)`, `agetty(8)`, `mesg(1)`, `last(1)`, `lastb(1)`, `mountpoint(1)` | Terminal and login-adjacent utilities |
| `bsdutils` | `wall(1)` | The broadcast tool |
| `bootlogd` | `bootlogd(8)` | Console capture during boot |
| `startpar` | `startpar(1)` | Parallel init-script execution |
| `init-system-helpers` | `update-rc.d(8)`, `invoke-rc.d(8)`, `service(8)` | Service registration and invocation front-ends |

Two facts worth internalizing from this table. First, `pidof` and `killall5` are in `sysvinit-utils`, which is *essential* priority on Debian — they appear in almost every rootfs, including many containers that never ran sysvinit as PID 1. Second, the terminal tools (`sulogin`, `agetty`, `last`) belong to util-linux, not to sysvinit — the init system and its tooling have always been separable layers, which is exactly what later init-system debates exploited (see [migration-modern.md](./migration-modern.md)).

## pidof(8)

`pidof(8)` answers one question: which PIDs are running the named program? It scans `/proc`, comparing each process's program name against the argument — no full ps fork, no regex, designed for use inside shell scripts:

```sh
#!/bin/sh
# The canonical init-script status idiom:
pid=$(pidof -s myapp) || { echo "myapp is not running"; exit 3; }
echo "myapp is running as pid $pid"
```

Options that matter:

| Option | Meaning |
|--------|---------|
| `-s` | Return a single PID (the first found) |
| `-c` | Only return processes with the same root directory as the caller — chroot/container awareness |
| `-x` | Also match shells running the named *scripts*, not just binaries |
| `-o PID` | Omit a PID; the magic `-o %PPID` omits the calling shell's parent — how scripts exclude themselves |

Exit codes are LSB-friendly and script-friendly: 0 if at least one matching process was found, 1 if none. A nice piece of trivia with operational relevance: **pidof and killall5 are the same program**, dispatching on `argv[0]` — the same multiplexing trick halt/reboot/poweroff use ([shutdown-halt.md](./shutdown-halt.md)).

### pidof versus pgrep

| Property | `pidof` | `pgrep -x` (procps) |
|----------|---------|---------------------|
| Match basis | Program name as init-scripts see it | Exact process name (`comm`), or full cmdline with `-f` |
| Shell script matching | With `-x` | Via `-f` patterns |
| Container/root scoping | `-c` | Namespaces handled differently (procps sees what /proc shows) |
| Output control | `-s`, `-o` | Rich: `-l` list names, `-n`/`-o` newest/oldest, counts |
| Typical home | sysvinit-utils, always present | procps, essentially always present |

Rule of thumb for scripts: `pidof` where sysvinit conventions matter (status actions, `start-stop-daemon` alternatives), `pgrep` when you need pattern power. On systemd systems neither is the primary mechanism anymore — the manager knows the main PID (`systemctl show -p MainPID`), and `$MAINPID` is passed into `ExecReload=` lines; sysvinit scripts replicate that knowledge with pidof.

## killall5(8)

`killall5(8)` is the SysV "signal every process on the system" tool. It exists because the shutdown path cannot know every daemon's PID: rc scripts need a sledgehammer that hits everything except the machinery doing the hitting. Its protections are built in: it never signals itself, its parent, or processes in its own session — which is why it can be called from an rc script without killing the rc script, the console shell, or init.

| Option | Meaning |
|--------|---------|
| `-s SIGNAL` | Signal to send (name or number); default is TERM |
| `-o PID` | Omit a PID; repeatable — how rc scripts protect recorded stragglers |
| `-l` | List signal names (like `kill -l`) |

The real-world usage is Debian's stop path ([shutdown-halt.md](./shutdown-halt.md) walks the full sequence). The `sendsigs` script in rc0/rc6 does:

```sh
# Essence of /etc/init.d/sendsigs (simplified):
#   1. Collect PIDs to protect from /run/sendsigs.omit* files
#      (services register PIDs here when they need a graceful window)
#   2. Signal everything else, politely:
killall5 -15 -o $OMITTED_PIDS
#   3. Wait for the timeout...
#   4. Then stop asking:
killall5 -9  -o $OMITTED_PIDS
```

The rc1 counterpart `killprocs` does the same with SIGKILL for the runlevel-1 path. The `-o`/omit mechanism is the coordination point: any init script that needs a few more seconds before the mass-kill writes its PIDs (or a pidfile path) into `/run/sendsigs.omit*`.

### The Dangers

`killall5` is a precision instrument pointing in every direction at once:

- **Namespace blindness.** It signals every process it can see. Run by mistake in the wrong context (an `nsenter`-ed shell, a debugging container), it will signal that whole world — its session protections save the caller, not the bystanders.
- **Kernel threads are excluded**, but everything userland is fair game — including your editor on tty2, your SSH session, and anything else you forgot was "a process."
- **It is the wrong tool for one service.** Scripts that reach for killall5 because pidof felt unreliable usually want `start-stop-daemon` with a pidfile (see [custom-init-scripts.md](./custom-init-scripts.md)).

The systemd-era replacement is structural rather than a command: services live in cgroups, and stopping a unit kills the *cgroup* (`KillMode=`), which cannot miss a forked child the way a pidfile can. That single idea — kill by grouping, not by enumeration — is why killall5 has no direct successor: it solves a problem modern process management made disappear.

## last(1) and lastb(1)

`last(1)` replays `/var/log/wtmp` backwards; `lastb(1)` replays `/var/log/btmp` (failed logins). Both are util-linux; the record format and writers are covered in [getty-terminals.md](./getty-terminals.md) — this section is about reading them.

Representative output with the pieces labeled:

```text
$ last -x -n 5
reboot   system boot  6.1.0-13-amd64   Fri Nov  3 07:41   still running
myuser   pts/0        203.0.113.7      Fri Nov  3 07:39 - 09:12  (01:33)
runlevel (to lvl 3)  6.1.0-13-amd64   Fri Nov  3 07:39 - 09:12  (01:33)
shutdown system down  6.1.0-13-amd64   Fri Nov  3 02:15 - 07:41  (05:26)

wtmp begins Mon Oct  2 04:00:01 2023
```

Columns: user (or pseudo-user `reboot`/`shutdown`/`runlevel`), tty, remote host (or kernel version for system events), timestamp, logout time, and duration in parentheses. Options worth knowing:

| Option | Meaning |
|--------|---------|
| `-n N` | Limit output to N lines (same as `-N` on some implementations) |
| `-F` | Full dates and times instead of the compact format |
| `-x` | Include shutdown entries and runlevel changes — the system-events view |
| `-d` | Resolve remote hostnames from IPs (queries DNS — offline it stalls) |
| `-a` | Put the hostname in the last column (easier to `awk`) |
| `-s WHEN` / `-t WHEN` | Show records since / until a time |
| `-p WHEN` | Who was present at a given moment — the "when did the outage start" query |

The uptime-estimation recipe that every SRE should know cold:

```sh
# Five most recent boot/shutdown boundaries, newest first:
last -x reboot shutdown -n 10 | head -10

# How long did the previous boot last? (durability math for incidents)
last -x reboot shutdown -F | head -5
```

Caveats that make the difference between a correct and an incorrect incident report:

- **Rotation gaps.** `wtmp begins <date>` marks the start of the current file; older history lives in `wtmp.1` (logrotate handles wtmp/btmp monthly on Debian). "The logs don't show it" often means "check the rotated file."
- **Unclean shutdowns leave holes.** A system that lost power has a boot record with *no* preceding shutdown record — itself diagnostic information.
- **btmp permissions matter**: 0660 root:utmp, because it contains usernames attackers tried. `lastb` needs root (or utmp group) — and it is the first place to look for brute-force forensics on pre-journald systems: `lastb -n 20` or a quick `lastb | awk '{print $3}' | sort | uniq -c | sort -rn | head` to rank source hosts.

## mesg(1)

`mesg(1)` controls whether *other users* may write to your terminal — it toggles the write-permission bits on your tty device node:

```console
$ mesg          # query current state
is y
$ mesg n        # refuse incoming writes (wall, write, talk)
$ mesg
is n
```

Exit codes are meaningful for scripts: 0 when read/write access is currently allowed, 1 when not. The consumers of this setting are the person-to-person tools: `wall(1)` and `write(1)` honor it (root's writes still get through, since root can open any tty). Two usage notes with real operational weight: this is the mechanism `shutdown`'s warnings ride on (users with `mesg n` never see the countdown — see [shutdown-halt.md](./shutdown-halt.md)), and historically some admin shell profiles set `mesg n` defensively, which is why broadcast campaigns on shared systems mysteriously miss people.

## wall(1)

`wall(1)` (bsdutils) writes a message to every logged-in user's terminal. It reads the message from a file operand, or from stdin, or from its arguments, and prefixes a banner identifying the sending user, host, and tty:

```console
$ echo "Reboot to apply kernel updates at 18:00. Contact ops@ for issues." | wall

Broadcast message from admin@prod-db1 (pts/2) (Fri Nov  3 17:45:02 2023):

Reboot to apply kernel updates at 18:00. Contact ops@ for issues.
```

Mechanics worth knowing: it discovers targets by scanning `utmp` for active sessions, then attempts to open and write each terminal device — silently skipping the ones that refuse (mesg n, non-root sender). The `-n` flag suppresses the banner (root-restricted on some implementations — an un-bannered message claiming to be from someone is a social-engineering primitive). The `-t` timeout bounds how long it tries to write stuck terminals before giving up.

Where it fits today: still shipped, still scriptable, still the tool for "tell everyone on this box right now." On systemd systems the shutdown machinery has its own broadcast implementation, but the `wall(1)` interface is preserved for scripts and operators — one more compat surface documented in [migration-modern.md](./migration-modern.md).

## mountpoint(1) and fstab-decode(8)

Both live in the mount-adjacent corner of the toolkit and both exist to make shell scripts *correct* rather than merely working.

### mountpoint(1)

`mountpoint(1)` (util-linux) answers "is this directory actually a mountpoint?" — comparing device identity rather than guessing:

```console
$ mountpoint /mnt/data
/mnt/data is a mountpoint
$ mountpoint -q /mnt/data && echo mounted || echo not-mounted
mounted
$ mountpoint -d /mnt/data
/mnt/data: /dev/sdb1[8:17]
```

Why `[ -d /mnt/data ]` is the classic bug: it only tests directory existence, which is true whether or not anything is mounted there. The failure mode is ancient and reliable: the mount failed at boot, the empty directory is still there, the script happily writes "into the mount" — landing on the root filesystem until the next remount hides or truncates it. `mountpoint -q` (quiet, exit-status only) is the correct guard in start scripts, and `-d` (print the major:minor) and `-x DEV` (check a device node is a block device) round out the surface. Exit codes: 0 = is a mountpoint, 1 = not — LSB-style, made for `&&` chains.

### fstab-decode(8)

`fstab-decode(8)` (sysvinit-utils) decodes the escape sequences `/etc/fstab` uses to encode characters that would otherwise be illegal in its fields — `\040` for space, `\011` for tab, `\012` for newline, `\134` for backslash. Without it, a mount point containing an encoded space breaks every shell loop that iterates over fstab fields:

```sh
# The canonical usage, straight out of the umount stop scripts:
fstab-decode umount $(awk '$3 == "vfat" { print $2 }' /etc/fstab)
```

awk prints the fstab-encoded second field; fstab-decode decodes it and execs umount with the real path. It is a niche tool, but it is the difference between "our rc scripts handle every legal fstab" and "our rc scripts handle fstabs without spaces" — and interviewers love it for exactly that reason.

## bootlogd(8)

`bootlogd(8)` (package `bootlogd`) captures what goes to the console during boot and writes it to `/var/log/boot`. It exists because the boot is the one phase of system life with no persistent logging otherwise: kernel messages scroll past, rc script output scrolls past, and if the boot fails at script 14 of 40, you have a photograph of a screen, not a log.

Operation on a sysvinit system:

1. An early boot script starts bootlogd (it must begin early — its whole value is the window before syslog runs).
2. bootlogd opens the console devices, reads everything written there, and appends timestamped lines to `/var/log/boot` (its pidfile and output file are configurable; see [bootlogd(8)](https://manpages.debian.org/bookworm/bootlogd/bootlogd.8.en.html)).
3. A stop-side boot script ends it once the system is up (or shut down), finalizing the file.
4. Enable/disable historically via `/etc/default/bootlogd` (`BOOTLOGD_ENABLE`).

What it is used for: measuring boot time (timestamps per line — see [parallel-booting.md](./parallel-booting.md)), diagnosing hangs (the last lines before silence are the suspect), and post-mortems on machines with serial consoles where the human was not watching. On systemd systems the journal subsumes it — kernel and early-boot output land in the journal from the start ([../systemd/journald.md](../systemd/journald.md)) — which is precisely why bootlogd feels like archaeology today and why it is still installed on every sysvinit box.

## runlevel(8)

`runlevel(8)` (sysvinit-core) prints the previous and current runlevel as letters, read from the `RUN_LVL` record init keeps in utmp:

```console
$ runlevel
N 3          # N = no previous runlevel (fresh boot straight to 3)
$ telinit 1
$ runlevel
3 1
```

`N` in the first position means the system has not changed runlevels since boot. The scripting idiom:

```sh
if [ "$(runlevel | awk '{print $2}')" = "S" ]; then
    echo "in single-user mode"
fi
```

On systemd systems, treat `runlevel(8)` output with suspicion: runlevels are emulated, the utmp `RUN_LVL` record is no longer the engine of state, and the native answers are `systemctl get-default` and `systemctl list-units --type=target` (mapping table in [../systemd/targets-runlevels.md](../systemd/targets-runlevels.md)). `who -r` (coreutils) reads the same record for the curious.

## The Session Files Behind the Tools

One paragraph of connective tissue, because half the tools above read or write the accounting trio: `utmp` (current sessions — scanned by `wall` for targets, by `who`/`w` for display, updated by login), `wtmp` (history — replayed by `last`, appended with boot/runlevel/shutdown records by init), and `btmp` (failed logins — replayed by `lastb`). The record formats, writer-by-writer breakdown, permissions, and rotation are covered in depth in [getty-terminals.md](./getty-terminals.md). When `last` output looks wrong, the cause is almost never `last` — it is a writer that died uncleanly, a rotation that lost history, or permissions that stopped a writer from appending.

## Retirement Table: Where Each Tool Went

The systemd mapping, tool by tool — useful both for migration work and as a compact summary of what "init system" means in each era:

| sysvinit-era tool | systemd-era replacement | What changed structurally |
|-------------------|--------------------------|---------------------------|
| `pidof` | `systemctl show -p MainPID`, `$MAINPID` in units | The manager *knows* the main PID; scripts no longer guess |
| `killall5` | cgroup-scoped kill (`KillMode=control-group`) | Kill by group membership, not by enumeration — forked children cannot escape |
| `last` / `wtmp` | `journalctl --list-boots`, `_COMM`-filtered queries, boot IDs | Structured, timestamped, indexed; wtmp retained mainly for compat |
| `lastb` / `btmp` | journal filters on failed auth units (sshd logs) | Per-service logs replace the single global failure file |
| `wall` | built-in shutdown/logind broadcast | Native implementation; `wall(1)` still shipped for scripts |
| `bootlogd` | the journal (early-boot output included) | Persistent journal from first userspace message |
| `runlevel` | `systemctl get-default`, `systemctl isolate` | Runlevels became targets; utmp record no longer authoritative |
| `mountpoint` | survives unchanged | Still the right tool — mount detection was never an init-system problem |
| `pidof -c`/namespace care | manager-per-container, `systemd-run` scoping | The manager lives *inside* the same namespace, so queries are naturally scoped |

The pattern across the table: systemd did not reimplement these tools so much as remove the *need* for them — persistent process groups and a structured journal replace guessing and scraping. That observation is the one-sentence version of the whole migration debate (see [migration-modern.md](./migration-modern.md) and [../systemd/systemctl-cli.md](../systemd/systemctl-cli.md)).

## Interview Questions

### Q: How does killall5 avoid killing the very scripts that call it?

It excludes itself, its parent, and everything in its own session. rc scripts run in init's session tree with their own session identity during the stop sequence, so the mass-signal leaves the calling script, its console, and init untouched — while hitting every unrelated process. For finer control, `-o PID` omits specific processes; Debian's sendsigs uses this to honor PIDs registered in `/run/sendsigs.omit*` by services that need a graceful window before the SIGKILL pass.

### Q: Why can pidof give a wrong answer for a daemon that forked twice, and what is the modern fix?

A double-forking daemon's final working process has a different PID from the one the start command knew, and depending on how it set its process name, the name pidof matches may differ too — so pidof can miss the real worker or match a stale leftover. The sysvinit-era mitigation is the pidfile (written by the daemon or via `start-stop-daemon --make-pidfile`) plus a `/proc/<pid>` existence check. The structural fix is cgroup-based process tracking: the manager records every descendant at fork time, so no name matching is involved — `systemctl show -p MainPID` and cgroup-scoped kills replace pidof entirely.

### Q: How would you reconstruct a system's reboot history and spot an unclean shutdown from wtmp?

`last -x` — the `-x` includes shutdown and runlevel records, not just logins. Healthy cycles alternate `shutdown` and `reboot` entries with sensible durations. The diagnostic signature of an unclean shutdown is a `reboot system boot` record with *no* preceding `shutdown system down` record: the boot was recorded, the teardown never was — power loss, kernel panic, or a `reboot -f`. For an incident report, `last -x reboot shutdown -F` gives the full boundary list; remember `wtmp begins <date>` means older history is in the rotated wtmp files.

### Q: What does /etc/nologin have to do with mesg and wall?

They are independent mechanisms that meet at shutdown etiquette. `shutdown` broadcasts its countdown via wall, which writes to every terminal of logged-in users — but only those whose owners have not run `mesg n`, since wall honors the tty write-permission bits that mesg toggles. Separately, shutdown creates `/etc/nologin` to block *new* non-root logins via pam_nologin. So the two controls cover the two audiences: mesg/wall reach the people already logged in, /etc/nologin stops people from joining. A user with `mesg n` misses the broadcast entirely; a user arriving after nologin exists never gets in.

### Q: What is mountpoint for, and why is "[ -d /mnt/data ]" wrong?

`[ -d ]` tests that a directory exists — which is true whether or not a filesystem is mounted on it. If the mount failed, the script writes into the empty directory on the root filesystem: data silently goes to the wrong place, and a later remount makes it vanish from view. `mountpoint(1)` answers the actual question by comparing device identity: `mountpoint -q /mnt/data` exits 0 only if something is really mounted there. It also offers `-d` (print the underlying major:minor) and `-x` (validate a device node). Any start script that writes "into a mount" should gate on mountpoint, not on directory existence.

### Q: What is the one-sentence structural reason killall5 and pidof lost their jobs?

Systemd tracks processes in cgroups rather than by enumeration: the manager knows exactly which processes belong to a service from fork time onward, so "find the daemon's PID" and "kill everything the service spawned" become property lookups instead of name-matching scans — killing by group membership cannot miss a forked child, and knowing the main PID needs no pidfile heuristic.

## References

- [pidof(8) — sysvinit-utils](https://manpages.debian.org/bookworm/sysvinit-utils/pidof.8.en.html)
- [killall5(8) — sysvinit-utils](https://manpages.debian.org/bookworm/sysvinit-utils/killall5.8.en.html)
- [fstab-decode(8) — sysvinit-utils](https://manpages.debian.org/bookworm/sysvinit-utils/fstab-decode.8.en.html)
- [init-d-script(5) — sysvinit-utils](https://manpages.debian.org/bookworm/sysvinit-utils/init-d-script.5.en.html)
- [last(1) — util-linux](https://manpages.debian.org/bookworm/util-linux/last.1.en.html)
- [lastb(1) — util-linux](https://manpages.debian.org/bookworm/util-linux/lastb.1.en.html)
- [mesg(1) — util-linux](https://manpages.debian.org/bookworm/util-linux/mesg.1.en.html)
- [sulogin(8) — util-linux](https://manpages.debian.org/bookworm/util-linux/sulogin.8.en.html)
- [mountpoint(1) — util-linux](https://manpages.debian.org/bookworm/util-linux/mountpoint.1.en.html)
- [agetty(8) — util-linux](https://manpages.debian.org/bookworm/util-linux/agetty.8.en.html)
- [wall(1) — bsdutils](https://manpages.debian.org/bookworm/bsdutils/wall.1.en.html)
- [bootlogd(8) — bootlogd](https://manpages.debian.org/bookworm/bootlogd/bootlogd.8.en.html)
- [runlevel(8) — sysvinit-core](https://manpages.debian.org/bookworm/sysvinit-core/runlevel.8.en.html)
- [init(8) — sysvinit-core](https://manpages.debian.org/bookworm/sysvinit-core/init.8.en.html)

## Cross-References

- [init-scripts.md](./init-scripts.md) — the scripts these tools were built to serve.
- [rc-symlinks.md](./rc-symlinks.md) — where in the rc sequence tools like killall5 and fstab-decode actually run.
- [getty-terminals.md](./getty-terminals.md) — utmp/wtmp/btmp formats and the writer side of the accounting trio.
- [shutdown-halt.md](./shutdown-halt.md) — killall5 in sendsigs, wall in the shutdown broadcast, wtmp records.
- [single-user-sulogin.md](./single-user-sulogin.md) — sulogin, the util-linux neighbor of these tools.
- [../systemd/systemctl-cli.md](../systemd/systemctl-cli.md) — the manager CLI that replaced the status/signal scripting idioms.
- [../systemd/journald.md](../systemd/journald.md) — the journal that absorbed bootlogd and wtmp's roles.
- [../comparison.md](../comparison.md) — the section-wide init-system comparison.
- [../README.md](../README.md) — the init-systems section hub.
