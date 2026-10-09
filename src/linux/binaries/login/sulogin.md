# sulogin — single-user maintenance login

## Overview

`sulogin` is the password gate in front of a root shell when the system is half-broken. It is invoked by init (or by systemd through its rescue/emergency machinery) when the machine is brought up in single-user mode or when a boot step fails badly enough that the normal multi-user boot cannot continue. It prints the classic prompt:

```
Give root password for system maintenance (or type Control-D for normal startup):
```

and, on success, starts a root shell — nothing more. No full session is created: no PAM session stack, no utmp/wtmp/lastlog bookkeeping, no environment rebuild. When you exit that shell (or press Control-D at the prompt), the boot continues. On Debian it lives in `/usr/sbin/sulogin` and ships in the `util-linux` binary package; upstream it was written by Miquel van Smoorenburg for sysvinit and later ported to util-linux by Dave Reisner and Karel Zak, so — unlike `login` and `nologin` — this one has always been util-linux's binary on Debian.

`sulogin` is not `login`: it authenticates only root, creates no session, and exists for recovery. It is also not `init=/bin/bash`: that kernel argument bypasses authentication entirely. On Debian 13, systemd does not exec `sulogin` directly anymore — its `systemd-sulogin-shell` helper wraps it — but the semantics below are the binary's.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian source package `util-linux`) |
| Man section | 8 |
| Path | /usr/sbin/sulogin |
| First appeared | sysvinit era (Miquel van Smoorenburg); ported to util-linux 2.x |
| Standards | Not POSIX; wired into sysvinit inittab and systemd rescue/emergency service units |

## Synopsis

```
sulogin [options] [tty]
```

Common one-line forms:

```
sulogin                    # prompt on the current terminal
sulogin /dev/console       # attach to an explicit device (boot scripts)
sulogin -t 300 /dev/ttyS0  # serial rescue: give up after 5 minutes
sulogin -e /dev/console    # forced mode: fall back to raw password files
```

## How It Works

### Who invokes it

```
 kernel cmdline: systemd.unit=rescue.target / emergency.target
        │
        ▼
 rescue.service / emergency.service
   ExecStart=-/usr/lib/systemd/systemd-sulogin-shell rescue|emergency
        │
        ▼
   sulogin on the console
        │
        ├── password ok ────────► root shell (SUSHELL → root's shell → /bin/sh)
        ├── Control-D ───────────► exit; boot continues normally
        ├── wrong password ──────► re-prompt (bounded attempts)
        └── root locked, no -e ──► cannot authenticate → other recovery path
```

On a Debian 13 system the wiring is visible in the unit files:

```bash
$ grep ExecStart /lib/systemd/system/rescue.service /lib/systemd/system/emergency.service
/lib/systemd/system/rescue.service:22:ExecStart=-/usr/lib/systemd/systemd-sulogin-shell rescue
/lib/systemd/system/emergency.service:23:ExecStart=-/usr/lib/systemd/systemd-sulogin-shell emergency
```

Sysvinit did the same job through `/etc/inittab` (`~~:S:wait:/sbin/sulogin`), and initramfs/boot scripts sometimes call `sulogin /dev/console` directly when mounting the root filesystem fails. Only root may run it by hand — as an unprivileged user you get:

```bash
$ sulogin
sulogin: only superuser can run this program
```

### Authentication

The user is prompted for the root password, which is verified against the hash in the account database obtained through `getpwnam(3)` (i.e. NSS — files, LDAP, whatever the resolver is configured to do). Verification uses `crypt(3)` directly; there is no PAM involvement, so no faillock, no limits, no account-expiry logic apply. Pressing Control-D at the prompt is a deliberate escape hatch: `sulogin` exits and the system continues booting.

Two degenerate cases matter in practice:

- **Empty root password**: nothing to verify, so the shell starts without a prompt. Broken setups only — but explains why boot scripts sometimes drop straight to a shell.
- **Locked root account** (shadow hash prefixed with `!` or `*`): without `-e` there is no valid password to match, so authentication simply keeps failing. Recovery then requires a different lever: boot with `init=/bin/bash`, or use the initramfs `break=` hooks, or boot rescue media.

### The `-e` (forced) mode

From the man page, verbatim semantics: if obtaining the root password via `getpwnam(3)` fails, `sulogin -e` examines `/etc/passwd` and `/etc/shadow` directly. And if those files are damaged or nonexistent — or the root account is locked by `!` or `*` at the start of the hash — `sulogin` **starts a root shell without asking for a password**. The man page's own warning is blunt: only use `-e` when you are sure the console is physically protected against unauthorized access.

This makes `-e` the designed escape hatch for "NSS is broken but the files are fine" situations: a botched LDAP/NSS configuration can make `getpwnam(root)` fail even though `/etc/shadow` is intact, and `-e` bypasses the resolver.

### Shell selection and environment

- The shell is taken from the environment variable `SUSHELL` (or `sushell`) if set; otherwise root's shell from `/etc/passwd`; if that fails, `/bin/sh`.
- `-p` starts it as a *login shell* (argv[0] gets the dash, profile files run); the default is a plain non-login shell.
- The environment is minimal — you inherit whatever the boot environment had plus a usable `PATH`. No `pam_env`, no `umask` from `/etc/login.defs`, no limits. Scripts that assume a normal root session need their assumptions relaxed.
- No session accounting is written: don't look for a utmp/wtmp/lastlog entry from a maintenance shell.

### Lifespan

When the user exits the single-user shell, or presses Control-D at the prompt, the system continues to boot. Under systemd, leaving `rescue.target` cleanly is `systemctl default` (or `exit` for emergency); the emergency banner even prints those instructions. `sulogin` itself just exits — the *init system* decides what happens next.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-e`, `--force` | Fall back to reading /etc/passwd and /etc/shadow directly if getpwnam fails; start an unauthenticated root shell if the files are damaged or root is locked. Physically-protected consoles only. |
| `-p`, `--login-shell` | Start the shell as a login shell (dash-prefixed argv[0], profiles sourced). |
| `-t`, `--timeout seconds` | Give up waiting for input after N seconds; default is forever. Used by headless/serial boot scripts. |
| `-h`, `--help` | Usage. |
| `-V`, `--version` | Version (identifies the util-linux build). |

## Usage Patterns

```bash
# 1. Ask systemd exactly how maintenance mode gets its shell
$ systemctl cat rescue.service | grep -E 'ExecStart|Environment'
ExecStart=-/usr/lib/systemd/systemd-sulogin-shell rescue
```

```bash
# 2. Drop a running system into rescue mode deliberately
$ sudo systemctl isolate rescue.target
```

```bash
# 3. Boot into rescue/emergency from the bootloader instead
#    (append to the kernel command line in grub)
systemd.unit=rescue.target     # multi-user-ish maintenance
systemd.unit=emergency.target  # bare minimum, after init failed
```

```bash
# 4. Force a specific maintenance shell even if root's shell is broken
$ sudo systemctl edit rescue.service
# add:  [Service]
#       Environment=SUSHELL=/bin/bash
```

```bash
# 5. Serial console rescue with a timeout so a hung line can't block boot
$ sudo sulogin -t 300 /dev/ttyS0
```

```bash
# 6. NSS/LDAP is broken but the local files are intact: bypass the resolver
$ sudo sulogin -e /dev/console
```

```bash
# 7. Locked root account: sulogin can't help without -e; classic recovery is
#    an unauthenticated shell via the kernel command line
init=/bin/bash
# then inside:
# mount -o remount,rw /
# passwd root          # or: usermod -U root
# sync && mount -o remount,ro / && reboot -f
```

```bash
# 8. Verify which implementation your host ships (it also encodes build features)
$ sulogin -V
sulogin from util-linux 2.41.5 (features: selinux, plymouth, keyboard mode, widechar, serial-info)
```

```bash
# 9. Check that a maintenance session left no accounting traces afterwards
$ last -f /var/log/wtmp | head -3   # no entry appears for the sulogin shell
```

## Nuances and Gotchas

- **Control-D is "continue boot", not "abort"** — the documented behavior at the prompt. Operators who expect Control-D to cancel maintenance and re-prompt will be surprised when the machine boots on.
- **`-e` is a loaded gun on exposed consoles.** With damaged or missing password files, or a locked root hash, it starts a root shell with no password at all. The man page restricts it to physically protected consoles for exactly this reason.
- **A locked root hash (`!`/`*`) makes plain sulogin useless.** Many hardened images lock root and rely on sudo; pressing Enter forever at "Give root password" achieves nothing. Know the `init=/bin/bash` / initramfs-`break` escape routes in advance.
- **systemd wraps it.** Since systemd 248 the units exec `systemd-sulogin-shell`, which prints the "You are in emergency mode..." banner and then invokes `sulogin`. Environment overrides (like `SUSHELL`) go through the unit, not through sulogin's argv.
- **No PAM session means no pam_limits, no umask policy, no loginuid setup** — maintenance shells behave differently from real root sessions, and audit tooling notices the missing `pam_loginuid` session.
- **Root-only launcher.** `sulogin` refuses to run for non-root users ("only superuser can run this program"), so you cannot use it as a generic "become root" tool.
- **Serial consoles need the tty argument.** When invoked with a device (`/dev/ttyS0`, `/dev/console`), sulogin attaches there; omitting it on headless hardware is a classic way to "lose" the rescue shell.
- **The prompt text differs between implementations and systemd versions** — "Give root password for system maintenance (or type Control-D for normal startup)" here, other wordings elsewhere. Don't write grep rules against the banner.

## Exit Status

- `0` on normal completion — the shell was started and exited, or Control-D ended the wait and boot continues.
- Non-zero when it cannot proceed: refused for non-root callers, no usable terminal, or timeout without authentication. The man page documents no numeric table; scripts should treat any failure as "no maintenance shell was provided".

## Related Commands

- [`login`](./login.md) — the full session-entry program; sulogin deliberately skips most of its machinery.
- [`nologin`](./nologin.md) — refusal shell; a locked root account is effectively "nologin at the boot gate".
- [`newgrp`](./newgrp.md) and [`sg`](./sg.md) — the same re-credential-and-exec pattern applied to groups.
- [Overview — the login collection](./overview.md) — session-entry tools and how they differ.
- [Users and groups](../../admin/users-groups.md) — the passwd/shadow layout sulogin authenticates against.
- [systemd](../../admin/systemd.md) — rescue/emergency targets, unit overrides, and boot flow around sulogin.

## Interview Questions

### Q: Who invokes sulogin on a modern Debian system?

systemd's `rescue.service` and `emergency.service` — via the `systemd-sulogin-shell` helper — and various boot/initramfs failure paths that exec `sulogin /dev/console` directly. Historically sysvinit's inittab did it. The point behind the question: the maintenance shell is *requested by init*, not started by the user, and its lifetime is governed by the init system, not the shell.

### Q: What exactly does `sulogin -e` change?

It tells sulogin to stop trusting `getpwnam(3)` (NSS) and read `/etc/passwd` and `/etc/shadow` directly. If the resolver is broken, the files are damaged, or root's hash is locked (`!`/`*`), it starts a root shell **without asking for a password**. That last part is why the man page says only to use it when the console is physically protected — it trades authentication for availability.

### Q: Root's password hash is locked. What are your recovery options at the boot prompt?

`-e` (physically protected console), the kernel argument `init=/bin/bash` followed by `mount -o remount,rw /`, an initramfs break (`rd.break`/`break=mount` on dracut systems), or rescue media. `sulogin` without `-e` cannot authenticate a locked hash, so the classic "Give root password" prompt becomes a dead end — a favorite debugging scenario.

### Q: Why doesn't sulogin use PAM like login does?

It runs at the earliest, most fragile moments of boot: PAM modules may be missing, misconfigured, or depend on services (NSS, LDAP, D-Bus) that are exactly the reason you are in rescue mode. sulogin needs a minimal, dependency-free path to a root shell — direct shadow-hash verification with `crypt(3)`. The cost is that none of the PAM-side controls (faillock, limits, session modules) apply.

### Q: How do you change which shell sulogin starts when root's shell itself is broken?

Set `SUSHELL` (or `sushell`) in sulogin's environment — under systemd, via a drop-in on `rescue.service`/`emergency.service` (`Environment=SUSHELL=/bin/bash`). Otherwise it tries root's shell from `/etc/passwd` and falls back to `/bin/sh`. `-p` additionally makes it a login shell. This is a small but complete answer that shows knowledge of the documented environment hook.

### Q: You exited the maintenance shell and the machine booted. What did the session leave in utmp/wtmp?

Nothing. sulogin performs no session accounting — no utmp record, no wtmp append, no lastlog update. That is one of the cleanest ways to distinguish a maintenance shell from a real login, and a reason auditors treat rescue sessions as untracked unless the console itself is logged (journald/serial console capture).

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/sulogin.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
