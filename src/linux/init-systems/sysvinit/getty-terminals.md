# getty, agetty and Terminal Management

## Overview

Between "the kernel is up" and "a user has a shell" sits a three-stage relay that most people use daily and rarely think about: init spawns **getty**, getty prepares the terminal and prints the login prompt, and a successful authentication makes getty `exec` into **login(1)**, which builds the session environment and finally starts your shell. On a sysvinit system every stage of this relay is visible in `/etc/inittab`, which makes it one of the best places to understand how init's `respawn` action, process accounting, and PAM all fit together.

This page covers the full terminal-management stack: the respawn chain and what happens on logout, real inittab line formats (including the busybox variant), the agetty option surface, the login/PAM flow in detail, the `utmp`/`wtmp`/`btmp` accounting files that the whole stack writes, serial console configuration (where the difference between the kernel's `console=` parameter and a getty line bites everyone at least once), and the troubleshooting patterns — "respawning too fast," hung PAM lookups, wrong TERM values, and baud mismatches.

The historical arc matters too: the static "one inittab line per console" model was replaced on modern systems by on-demand getty spawning under logind. Understanding both models — and why the old one is still the right answer on embedded and serial-console systems — is the difference between reciting history and actually knowing terminals.

## The Respawn Chain: init to getty to login to shell

The full life of a virtual console session:

```text
init (PID 1)
  |  respawn action, inittab entry 1:2345:respawn:/sbin/getty 38400 tty1
  |  fork/exec (see process management)
  v
getty on /dev/tty1
  |  - opens the tty, makes it the controlling terminal
  |  - sets termios: speed, flags; detects/handles carrier (serial era)
  |  - prints /etc/issue, prints "hostname login:"
  v
you type a username
  |  getty execs the login program, passing the username
  v
login(1)
  |  - prompts for password, authenticates via PAM
  |  - writes utmp/wtmp/lastlog records
  |  - sets up environment: HOME, SHELL, PATH, TERM, MAIL
  |  - changes uid/gid to the user, chdir to $HOME
  v
your login shell ($SHELL from /etc/passwd)
  |  ... work ... logout or terminal hangup
  v
shell exits -> session leader dies -> kernel sends SIGHUP to the session
  -> login/getty process long gone (it exec'd), so init's child exited
  -> init's SIGCHLD arrives; init records the DEAD_PROCESS bookkeeping
  -> respawn action fires again: a fresh getty appears on tty1
```

The mechanics that make the loop work:

- **`respawn` is init's supervision primitive.** init forks and execs the process, then waits on SIGCHLD. When the child dies, init re-spawns it — forever, unconditionally, with a rate limiter discussed below. This is the *only* supervision sysvinit provides, and getties are its flagship user (see [inittab.md](./inittab.md)).
- **getty ends its life by `exec`ing login.** The getty process image is replaced in place — same PID — so the chain init → getty → login → shell is one process becoming your shell. When you log out, that process exits, and init sees the death of the process it originally spawned.
- **Hangup cleanup is kernel work.** When the terminal closes (VC switch away does not do this; actual close does) or a modem drops carrier, the kernel sends SIGHUP to the session. The signal plumbing is covered in [../../../os/processes/ipc-signals.md](../../../os/processes/ipc-signals.md); the effect here is that the login shell dies and the chain unwinds back to init.
- **Fork/exec and reaping context** lives in [../../admin/process-management.md](../../admin/process-management.md); the short version is that init is the reaper of last resort, which is why DEAD_PROCESS records matter for the accounting files below.

## inittab Getty Lines in Practice

Classic Debian stock lines (sysvinit-core's inittab):

```text
1:2345:respawn:/sbin/getty 38400 tty1
2:23:respawn:/sbin/getty 38400 tty2
3:23:respawn:/sbin/getty 38400 tty3
4:23:respawn:/sbin/getty 38400 tty4
5:23:respawn:/sbin/getty 38400 tty5
6:23:respawn:/sbin/getty 38400 tty6
```

Reading one line field by field (`id:runlevels:action:process`): id `1` (also the `ut_id` used in utmp records), active in runlevels 2-5, `respawn` action, and the getty invocation. Two details repay attention:

- **Runlevel gating is real and deliberate.** tty1 is available in runlevels 2 through 5, while tty2-6 exist only in 2 and 3. Runlevels 4 and 5 were traditionally where a display manager would run — the idea being that graphical runlevels want fewer text consoles competing for attention. Whether your distribution actually configures it that way varies, but the gating mechanism is exactly the runlevel field of the inittab line.
- **The argument order looks backwards on purpose.** The classic line passes the speed first (`38400 tty1`), a relic of the old `getty(8)` convention. Modern **agetty** accepts the port and speed arguments in either order, which is why these decades-old lines keep working unchanged against the util-linux implementation. On Debian, `/sbin/getty` is agetty (the util-linux program).

The same idea on an embedded busybox system ([../../binaries/busybox.md](../../binaries/busybox.md)):

```text
::sysinit:/etc/init.d/rcS
tty1::respawn:/sbin/getty -L tty1 115200 vt100
ttyS0::respawn:/sbin/getty -L ttyS0 115200 vt100
::shutdown:/sbin/umount -a -r
```

busybox inittab reuses the four-field format but the runlevel field is effectively vestigial (empty `::` means "always"); the actions and respawn behavior are the same concepts with a smaller vocabulary. Note also the argument order here — tty first, then speed — which is the other common convention; implementations differ, and agetty's flexibility covers both.

The display-manager era added its own respawn pattern. The RHEL-style convention was an inittab line like:

```text
x:5:respawn:/etc/X11/prefdm -nodaemon
```

with runlevel 5 as "graphical." Debian instead ran display managers as ordinary rc scripts (`/etc/init.d/lightdm` and friends, started in the configured runlevel via the normal symlink machinery in [rc-symlinks.md](./rc-symlinks.md)). Both models share the key property: if the display manager exits, it comes back — either via init's respawn or via the display manager's own restart logic.

## agetty(8): The Modern Standard

agetty (util-linux) is the getty every current sysvinit distribution ships, and its option surface encodes thirty years of terminal history. The man page is [agetty(8)](https://manpages.debian.org/bookworm/util-linux/agetty.8.en.html); the options that matter in practice:

| Option | Purpose | Notes |
|--------|---------|-------|
| `-a USER` | Auto-login | Skips the login prompt and immediately runs login for USER. Boot debug consoles and kiosk setups; a security decision, not a convenience default. |
| `-l PROG` | Login program | Replace `/bin/login` with a custom program (used with `-n` for non-interactive flows). |
| `-n` | Skip login prompt | Only meaningful with `-l`; getty calls the login program directly without asking for a username. |
| `-f FILE` | Alternative issue file | Replaces `/etc/issue`; comma-separated list of files supported, first readable one wins. |
| `-i` | No issue | Do not print any issue text. |
| `-w` | Wait for CR/LF | Do nothing until the user presses Enter — the modem-era handshake; also useful on devices that emit garbage at connect. |
| `-t SEC` | Timeout | Exit if nothing is typed within SEC seconds; init respawns it. Prevents stuck consoles. |
| `-L` | Local line | Force CLOCAL: ignore carrier detect. Essential on serial lines without modem carrier (null-modem, virtual, embedded). |
| `-m` | Extract baud | Parse the baud rate from a modem's CONNECT message. Deep legacy, but explains why speed can be "auto". |
| `-H HOST` | Fake host | Write a chosen hostname into the utmp host field. |
| `-8` | 8-bit clean | Assume 8-bit, no parity processing — needed for UTF-8 terminals and modern serial. |
| `--noclear` | Do not clear screen | Keeps boot messages visible on the console instead of wiping them at the login prompt. |
| `--nohostname` | No hostname in prompt | For containers/embedded where the hostname is noise. |
| `--nonewline` | No newline before issue | Cosmetic control for the issue output. |
| `speed[,speed...]` | Baud list | Multiple comma-separated speeds make getty cycle through them until it receives Enter — the modem-era autobaud mechanism. |
| `term` (last arg) | TERM value | Sets the `TERM` environment variable for the session (`linux` for VCs, `vt100`/`vt220`/`xterm` for serial/dumb terminals). |

A serial line with all the modern essentials:

```text
T0:2345:respawn:/sbin/agetty -L -8 115200 ttyS0 vt100
```

Historical footnote for interviews: **mingetty** was a minimal getty restricted to virtual consoles (no serial support), popular in the 2000s for trimming footprint; busybox getty serves the same niche today. The old sysvinit `getty(8)` — a different program from agetty with its own two-step two-speed protocol — is long gone; on modern Debian the name `getty` on disk is agetty.

## login(1) and the PAM Stack

`login(1)` (Debian package `login`, man page [login(1)](https://manpages.debian.org/bookworm/login/login.1.en.html)) takes the username getty collected and runs the authentication and session-establishment gauntlet. The modules below live in `/etc/pam.d/login`; exact composition varies by distribution, but the roles are stable:

| PAM module | Role |
|------------|------|
| `pam_loginuid` | Sets the audit session ID (audit-era bookkeeping) |
| `pam_securetty` | Root may only log in on ttys listed in `/etc/securetty` |
| `pam_nologin` | Rejects non-root logins while `/etc/nologin` exists (see [shutdown-halt.md](./shutdown-halt.md)) |
| `pam_env` | Loads environment from `/etc/environment` and `/etc/security/pam_env.conf` |
| `pam_unix` | The classic password check against `/etc/shadow` |
| `pam_lastlog` | Prints the "Last login: ..." line and updates `lastlog` |
| `pam_mail` | Prints "You have mail." when the spool is non-empty |
| `pam_motd` | Prints `/etc/motd` (and generated motd fragments on newer distros) |
| `pam_limits` | Applies `ulimit`s from `/etc/security/limits.conf` |

Two of these deserve their own paragraphs.

### /etc/securetty

`pam_securetty` enforces that root can log in directly only on terminals listed in `/etc/securetty` — historically tty1-8 plus a few serial devices. The rationale was 1980s: modems were on ttys, and you did not want root passwords crossing a dial-up line or being tried on an unattended console equivalent. The mechanism is blunt (an allowlist of device names; pseudo-terminals like `pts/0` made it unwieldy) and its enforcement has been declining: modern distributions increasingly drop the module or ship it inert, because SSH is the actual remote-login path and direct root console login is rare. Cite it as `securetty(5)` — it has no stable man-page URL in our reference set, but the file and module remain findable on any Debian system. Interview framing: know that it exists, that it gates *root on specific ttys* via pam_securetty, and that it is a deprecated control, not a security boundary you should build on.

### issue, motd, and hushlogin

Three files, three moments in the login:

- `/etc/issue` — printed by **getty before** the login prompt. Contains pre-authentication text (distribution banner, legal warning) plus `\n`, `\s`, `\r` style escapes for hostname/kernel/tty. `/etc/issue.net` was its counterpart for network logins (telnet era).
- `/etc/motd` — printed **after** successful authentication (via pam_motd). "Message of the day": operational notices for people who are already in.
- `~/.hushlogin` — the user's opt-out: when it exists, login skips the "Last login" banner, the mail notice, and (on most configurations) the motd. Nothing mystical — just a per-user quiet flag.

## utmp, wtmp, btmp: The Accounting Trio

Every stage of the terminal chain leaves fingerprints in fixed-format binary files. Understanding them explains `who`, `w`, `last`, `lastb`, and half the "why does who show garbage" tickets in existence.

### The Records

Each record is a `struct utmp` — fixed-width fields, no variable-length strings:

| Field | Meaning |
|-------|---------|
| `ut_type` | Record type (see below) |
| `ut_pid` | PID of the recording process |
| `ut_line` | Terminal device name (`tty1`, `pts/0`) |
| `ut_id` | Short id — typically the inittab id field, linking a record back to its inittab line |
| `ut_user` | Login name |
| `ut_host` | Remote host (network logins) or display context |
| `ut_addr_v6` | Remote address |
| `ut_tv` | Timestamp |

Record types (`ut_type`) tell the story of a session:

| Type | Written by | Meaning |
|------|-----------|---------|
| `BOOT_TIME` | init | System boot — one record per boot |
| `RUN_LVL` | init | Runlevel change (this is what `runlevel(8)` reads) |
| `INIT_PROCESS` | init | A process spawned by init |
| `LOGIN_PROCESS` | getty | A getty is waiting on this line |
| `USER_PROCESS` | login | A user session is active |
| `DEAD_PROCESS` | init/cleanup | The process exited; the slot is free |
| `EMPTY`, `NEW_TIME`, `OLD_TIME`, `ACCOUNTING` | various | Slot zero, time changes, legacy accounting |

### The Files

| File | Content | Readers | Typical perms (Debian) |
|------|---------|---------|------------------------|
| `/var/run/utmp` | Current state: who is logged in *now* | `who`, `w`, `mesg`-era tools, `wall` target discovery | 0664 root:utmp |
| `/var/log/wtmp` | History: every login/logout/boot/runlevel change, appended | `last(1)` | 0664 root:utmp |
| `/var/log/btmp` | Failed login attempts | `lastb(1)` | 0660 root:utmp |

Writers, precisely: init writes the `BOOT_TIME`/`RUN_LVL`/`INIT_PROCESS` records and the `DEAD_PROCESS` records for its children (getties); getty writes `LOGIN_PROCESS`; login writes `USER_PROCESS` on success and appends the same pair to wtmp; failed attempts land in btmp. Anything that terminates without cleanup (kernel panic, power loss) leaves a dangling `USER_PROCESS` — which is why `last` reconstructs sessions from the *pair* of records and why stale `who` entries are a classic artifact after an unclean shutdown.

### Readers, Rotation, and Hygiene

- `who(1)` (coreutils) shows current sessions from utmp; `w(1)` (procps) joins them with per-process activity; `last(1)`/`lastb(1)` (util-linux — see [utilities.md](./utilities.md)) replay wtmp/btmp.
- All three files grow forever unless rotated. `logrotate` ships rules for wtmp and btmp (monthly, with `create` preserving owner/mode) — the "wtmp begins <date>" line in `last` output marks the start of the current rotation window, and forensic sessions before that line are in the rotated files.
- Programs writing utmp must lock records (`utmpx` locking) to avoid interleaved writes; getting this wrong is how "who" output becomes binary mush. Application authors on modern systems use libutempter-style helpers rather than writing the file by hand.

## Serial Consoles: console= versus a getty Line

The single most common serial-console confusion, worth stating as a rule: **the kernel's `console=` parameter gives you kernel messages and a /dev/console; it does not give you a login prompt.** For interactive login on a serial port you need a getty (or equivalent) spawned on that tty device.

```text
Kernel command line:
  console=ttyS0,115200n8 console=tty0

  - BOTH devices receive kernel printk output
  - the LAST console= named becomes /dev/console
    (where init's stdio goes and where interactive /dev/console reads/writes land)
  - order therefore matters: put the device you want for init
    interaction last
```

Full serial console recipe for a sysvinit system:

1. Kernel command line: `console=tty0 console=ttyS0,115200n8` — kernel messages on both, `/dev/console` (and thus init, and sulogin fallbacks) on the serial port. Reverse the order if you want the graphics console to own /dev/console.
2. inittab line: `T0:2345:respawn:/sbin/agetty -L -8 115200 ttyS0 vt100` — `-L` because there is no modem carrier, `-8` for 8-bit clean, speed matching the kernel's `115200n8`.
3. Verify from another machine with a USB serial adapter: `screen /dev/ttyUSB0 115200` (or `minicom`), where the client-side settings must mirror speed and framing exactly.

Device names worth recognizing in the wild:

| Device | Found on |
|--------|----------|
| `ttyS0`, `ttyS1` | Classic 16550 UARTs |
| `ttyAMA0`, `ttyAML0` | ARM boards (PL011 and Meson UARTs) |
| `ttyO0` | Older TI OMAP ARM boards |
| `hvc0` | Xen, PowerPC, and KVM with virtio-console |
| `ttyUSB0` | USB serial adapters (the *client* side of debugging, usually) |
| `tty0` | The *active* virtual console (aggregate), distinct from tty1..tty6 |

The same discipline applies on ARM single-board computers: `console=ttyAMA0,115200` in the bootloader plus an inittab (or busybox inittab) line for `ttyAMA0`. Miss the getty half and you get beautiful kernel boot logs followed by total silence at the login stage — the signature of this exact mistake.

## From Static Respawn to On-Demand Getty

The sysvinit model spawns six getties at boot whether anyone sits at the machine or not. systemd inverts this: logind autospawns a getty on a virtual console the first time you switch to it (`getty@ttyN` template instances), and `systemd-getty-generator` creates `serial-getty@` instances automatically for each `console=` device named on the kernel command line. The template-unit mechanism — `getty@.service` instantiated per port — is covered in [../systemd/unit-files.md](../systemd/unit-files.md).

What the old model does better, and why embedded systems keep inittab:

- **Simplicity of reasoning**: the console is either in inittab or it is not. No generator magic, no template resolution, no manager required — busybox init does the whole job in a few hundred bytes of logic.
- **Determinism on serial consoles**: the getty exists before the first human connects, which matters when the first thing you do on a wedged ARM board is open the serial port.
- **Rate-limiting semantics**: init's throttle (next section) is crude but predictable; systemd's start-rate limiting applies per-unit with different defaults and knobs.

The modern model's wins — zero idle cost, per-port instantiation, logind session tracking — are real, but they are systemd wins, not universal wins.

## Troubleshooting Getty and Login Problems

### "INIT: Id 'x' respawning too fast: disabled for 5 minutes"

The classic sysvinit console message. init detected that a respawn entry keeps dying almost immediately (a few seconds per life) and disabled that entry for five minutes to avoid burning CPU in a fork loop. Causes, in order of likelihood: a typo'd device name in the inittab line (getty can't open the tty), a missing getty binary or bad path, a misconfigured speed on a serial line, or a custom login program that exits instantly. The fix is always: correct the line, then either wait out the throttle or `telinit q` after editing inittab to reload it (see [inittab.md](./inittab.md)). Note the id in the message is the inittab first field — that is how you find the offending line.

### Login hangs after username entry

Almost always a blocking PAM module. The usual suspects: an NSS/PAM LDAP lookup against an unreachable directory server (with a long timeout), a hung `pam_systemd`-era equivalent on systemd systems, or an NFS-mounted home directory that cannot be reached (login completes the auth but hangs chdir-ing). Diagnosis: try a local-only account; if that works, it is the directory/homedir path. Break-glass: console/single-user mode (see [single-user-sulogin.md](./single-user-sulogin.md)) — which is also why you keep at least one working local root login configured everywhere.

### Garbage characters on a serial console

Baud/parity mismatch. The kernel's `console=ttyS0,115200n8` and the agetty line must use the same speed, and the client (screen/minicom) must match both. 115200 vs 9600 confusion is the classic; second place goes to a modem-era device that needs `-L` because carrier detect is floating.

### Wrong TERM, broken applications

If full-screen programs (editors, pagers) draw garbage, `TERM` is lying. VCs should be `linux`; serial terminals typically `vt100`/`vt220`; anything else and ncurses applications misrender. Fix it at the source: the last argument of the agetty line sets TERM for everyone on that line, better than per-user shellrc hacks.

### Console blanking at the login prompt

The kernel blanks virtual consoles after idle. On a machine whose job is to *show* the console (kiosk, dashboard, CI rack), disable it: `setterm -blank 0 -powersave off` from a boot script, or the `consoleblank=0` kernel parameter. Cosmetic, but it fills the "is the console frozen?" ticket queue.

## Interview Questions

### Q: Walk the full chain from power-on to a shell prompt on tty1 in a sysvinit system.

Kernel starts init; init reads inittab and runs the sysinit/boot/bootwait entries; on entering the default runlevel it processes the `1:2345:respawn:/sbin/getty 38400 tty1` entry — fork/exec getty on /dev/tty1. Getty opens the tty, sets termios, prints /etc/issue and the login prompt; the typed username is passed to login(1), which authenticates via PAM, writes utmp/wtmp records, sets up the environment, and (in the same PID, via exec-chain semantics down the line) starts the user's shell. On logout the session leader dies, the kernel delivers SIGHUP to the session, init's child exits, init records DEAD_PROCESS, and the respawn action spawns a fresh getty. The chain is one relay where each stage hands a more privileged, more configured process to the next.

### Q: The kernel is printing messages on the serial port. Why can't I log in there?

Because `console=` gives the kernel an output device and /dev/console, but a login prompt requires a userspace process that opens the tty, sets the line discipline, prints a prompt, and hands off to login — that is getty's job, and nothing spawns it unless an inittab line (or systemd's getty generator) asks for one. The fix is adding the respawn agetty line for the serial device with matching speed and `-L`. Kernel messages on a serial port with no getty is one of the most common serial-console misconfigurations.

### Q: What exactly goes into utmp and wtmp, and who writes which record?

utmp holds current state, wtmp is the append-only history. init writes BOOT_TIME, RUN_LVL, and INIT_PROCESS records (and DEAD_PROCESS when its children exit); getty writes LOGIN_PROCESS; login writes USER_PROCESS after successful authentication and appends to wtmp; failed attempts go to btmp, read by lastb. `who`/`w` read utmp; `last` replays wtmp. The inittab id field even survives as the ut_id, linking a session record back to the line that created it. After an unclean shutdown you expect stale entries, because the DEAD_PROCESS records never got written.

### Q: Why did distributions move away from /etc/securetty enforcement?

The mechanism is an allowlist of device names on which root may log in directly, enforced by pam_securetty — designed for a world of dial-up modems on ttys. It ages badly: every SSH session is a pts/N that the list cannot sensibly contain, so it only ever governed the local console, where root login is rare and physical access already implies near-total control. Modern distributions drop it or ship it inert. It survives as an interview topic because it illustrates the right lesson: security controls should attach to real attack surfaces (SSH config, console access policy), not to 1980s device names.

### Q: What does "Id 3 respawning too fast: disabled for 5 minutes" mean, and how do you fix it?

init's respawn throttle: the inittab entry with id 3 has exited almost immediately several times in a row, so init disabled it for five minutes to stop the fork loop. The id is the entry's first field, so you go straight to the line. Typical causes: nonexistent device (typo'd tty), missing binary, bad serial speed, or a custom login program exiting instantly. Fix the line, run `telinit q` to reload inittab (or wait out the throttle), and confirm a stable getty appears.

### Q: Why do embedded systems keep busybox-style inittab instead of something more modern?

It packages the entire console story — sysinit hook, respawn supervision for getties and serial consoles, shutdown hook — in a format with no runtime dependencies beyond busybox itself, no daemon to manage sessions, and deterministic behavior on serial-first hardware. For a device whose primary interface is a serial console and whose init budget is measured in kilobytes, the static inittab model is not legacy; it is the correct engineering choice. The modern on-demand getty model optimizes for multi-user workstations, which is a different problem.

## References

- [agetty(8) — util-linux](https://manpages.debian.org/bookworm/util-linux/agetty.8.en.html)
- [login(1) — login](https://manpages.debian.org/bookworm/login/login.1.en.html)
- [sulogin(8) — util-linux](https://manpages.debian.org/bookworm/util-linux/sulogin.8.en.html)
- [last(1) — util-linux](https://manpages.debian.org/bookworm/util-linux/last.1.en.html)
- [inittab(5) — sysvinit](https://manpages.debian.org/bookworm/sysvinit-core/inittab.5.en.html)
- [init(8) — sysvinit](https://manpages.debian.org/bookworm/sysvinit-core/init.8.en.html)

## Cross-References

- [inittab.md](./inittab.md) — the respawn action and entry format that drive all of this.
- [single-user-sulogin.md](./single-user-sulogin.md) — the maintenance console that bypasses the getty chain entirely.
- [runlevels.md](./runlevels.md) — why getty lines carry runlevel fields and how gating works.
- [shutdown-halt.md](./shutdown-halt.md) — pam_nologin and what happens to terminals during shutdown.
- [utilities.md](./utilities.md) — last/lastb/mesg/wall, the tools that read and write the accounting files.
- [../systemd/unit-files.md](../systemd/unit-files.md) — getty@ template units and the on-demand spawning model.
- [../../admin/process-management.md](../../admin/process-management.md) — fork/exec, session leadership, and reaping behind the respawn chain.
- [../../../os/processes/ipc-signals.md](../../../os/processes/ipc-signals.md) — SIGHUP and the hangup mechanics that close sessions.
- [../../binaries/busybox.md](../../binaries/busybox.md) — busybox init and getty in the embedded context.
- [../README.md](../README.md) — the init-systems section hub.
