# busybox — the multi-call binary that replaces a whole userland

## Overview

BusyBox is a single executable that implements a few hundred Unix utilities —
"applets" — inside one small binary. Kernel and C library are the only
dependencies, so a complete bootable userland fits in a megabyte-scale file:
embedded firmware, initramfs images, rescue disks, and minimal container base
images (Alpine above all) are built on it.

The mechanics are the interview-worthy part: BusyBox is the canonical
multi-call binary — one ELF file, one compiled-in applet table, dispatch on
`argv[0]` or the first argument. The same pattern explains Alpine's `/bin`,
Docker `scratch` images, and uutils' `coreutils` binary (see
[uutils](./uutils/overview.md) — same idea, different scope).

BusyBox implements the POSIX core of each utility plus a small subset of GNU
conveniences — **not** a drop-in GNU coreutils replacement: flags drift,
output formats differ, behavior is simplified. Debian's `busybox` package
installs the binary at `/usr/bin/busybox`; `busybox-static` is the variant
rescue tooling pulls in when no shared libraries exist. Don't confuse it
with toybox, the BSD-licensed multi-call project Android ships.

| Field | Value |
|---|---|
| Upstream | BusyBox project |
| Debian package | `busybox` (dynamic); `busybox-static` variant |
| Path | `/usr/bin/busybox` |
| Man section | 1 |
| First appeared | 1996–1999, written by Bruce Perens for Debian's boot/rescue floppies |
| License | GPLv2 |
| Standards | POSIX subset per applet; long options mostly absent; GNU extensions partial |
| Where it ships | Alpine Linux, kernel initramfs, rescue/installer images, minimal containers |

## Synopsis

```
busybox [APPLET] [ARGS]...
busybox --list
busybox --list-full
busybox --install [-s] [DIR]
```

- `busybox ls -l` — the `ls` applet through the first-argument form; with a
  symlink farm installed, plain `ls` dispatches on `argv[0]` instead.

## How It Works

### Applet dispatch: argv[0] and the first-argument form

BusyBox compiles a table of applet names and entry points into the binary —
exactly the applets the build configuration selected:

```
        ┌───────────────────────────────────────┐
        │         one ELF file: busybox         │
        └───────────────────┬───────────────────┘
                            │
   argv[0] = "/bin/ls"      │      argv[1] = "ls"
                            ▼
        ┌───────────────────────────────────────┐
        │ basename(argv[0]) or argv[1] matched  │
        │ against the compiled-in applet table; │
        │ that applet's main() runs with the    │
        │ remaining argv and sets the exit code │
        └───────────────────────────────────────┘
```

```bash
$ busybox ls -l /etc/hostname   # first-argument form: applet is argv[1]
$ ls -l /etc/hostname           # argv[0] form: the farm's /bin/ls symlink
```

The first-argument form is the rescue tool: even where the symlink farm is
broken, `busybox <applet>` always works as long as the binary is reachable.
An unknown applet fails locally with `frobnicate: applet not found` — no
PATH search. `--list` prints one applet name per line, `--list-full` prints
install paths; that list is the ground truth: applets are build properties.

### Why BusyBox exists

BusyBox was written by Bruce Perens in 1996–1999 to put a bootable, fixable
Debian system on a single floppy disk: kernel plus one userland binary. The
constraint — maximum capability per byte — never stopped being the design
goal, and the use cases interviews probe follow from it:

- **initramfs** — early userspace unpacks a compressed cpio archive and runs
  `/init` from it, no distro behind it; static BusyBox + a hand-written
  `/init` is the standard recipe.
- **embedded systems** — routers, set-top boxes, IoT firmware, where 300+
  utilities must cost one file out of a megabyte-scale flash budget.
- **Alpine Linux** — `/bin/sh` is BusyBox `ash` and the base utilities are
  applets, a large part of why the `alpine` image stays a few megabytes.
- **rescue and installer images** — when the root filesystem is toast, the
  shell you drop into is usually BusyBox: drifting flags, no bash. Knowing
  that is the difference between fixing and flailing.

### The symlink farm: --install -s

An installed system is a farm of links, one per applet, all pointing at the
same binary. BusyBox builds the farm itself:

```bash
$ busybox --install -s          # symlinks -> /bin, /sbin, /usr/bin, /usr/sbin
$ busybox --install             # hard links instead (same filesystem)
```

1. `--install` locates *itself* through `/proc/self/exe`, so `/proc` must be
   mounted — the classic fresh-initramfs failure.
2. The links cover every applet in *this build's* table.
3. Applets work without the farm: it is a PATH convenience, not a mechanism.

The recipe behind countless minimal images:

```bash
$ mkdir -p tree/bin tree/proc tree/dev tree/sys
$ cp /path/to/busybox-static tree/bin/busybox
$ mount --bind /proc tree/proc           # so /proc/self/exe resolves
$ chroot tree /bin/busybox --install -s
$ chroot tree /bin/sh                    # a full (POSIX) shell environment
```

## The Applet Matrix

A full modern build carries 300+ applets — `busybox --list` prints them all.
The matrix covers the ~50 you will actually be asked about, grouped by job.

### Shell and scripting

| Applet | One-liner |
|---|---|
| `sh` / `ash` | The shell: a POSIX Almquist-shell descendant, not bash |
| `awk` | Pattern scanning and text transforms — a usable POSIX awk subset |
| `sed` | Stream editing; short options only, GNU long forms absent |
| `grep` | Pattern search: the POSIX/short-flag set, no PCRE |
| `env` | Run a command with a modified environment |
| `test` / `[` | File and condition checks for shell scripts |

### File operations

| Applet | One-liner |
|---|---|
| `ls` | List files; short flags, raw (unquoted) special filenames |
| `cp` / `mv` | Copy and move/rename; `-a` archive mode included |
| `rm` | Remove files and trees (`rm -rf` needs no introduction) |
| `ln` | Hard and symbolic links — the farm's own building block |
| `find` | Directory search: a practical subset of tests and actions |
| `xargs` | Build command lines from stdin |
| `dd` | Block copies — the boot-image and device workhorse |
| `tar` | Archive with `-z`/`-j`/`-J` chosen explicitly; no `-a`, no `--sort` |
| `df` / `du` | Filesystem capacity; directory disk usage |
| `cpio` | The archive format the kernel's initramfs itself uses |

### Text processing

| Applet | One-liner |
|---|---|
| `head` / `tail` | First and last lines/bytes; follow mode in fuller builds |
| `wc` | Count lines/words/bytes |
| `cut` | Slice fields/columns |
| `tr` | Translate/delete characters |
| `sort` | Sort lines (POSIX flags; no `--parallel`) |
| `uniq` | Collapse adjacent duplicates |
| `md5sum` / `sha256sum` | Checksums; same output format as GNU |
| `vi` | A real (small) vi — the editor you have in single-user rescue |

### Sysadmin and system

| Applet | One-liner |
|---|---|
| `init` | PID 1 for BusyBox systems; its own `/etc/inittab` dialect (`::respawn`, ...) |
| `halt` / `reboot` / `poweroff` | The shutdown verbs, talking to init |
| `mount` / `umount` | Mount tables; `-o` covers the common filesystems |
| `fdisk` | Partition tables (MBR plus GPT depending on config) |
| `mdev` | Mini-udev: populates `/dev` from `/sys` on hotplug events |
| `su` | Become another user; `passwd` changes passwords |
| `crond` / `crontab` | Scheduled jobs, self-contained |
| `syslogd` / `logger` | Local logging ring plus a log-write command |

### Networking

| Applet | One-liner |
|---|---|
| `ip` | Address/route/link manipulation — BusyBox's modern net tool |
| `ifconfig` / `route` | The legacy pair, still present in scripts |
| `ping` / `traceroute` | Connectivity and path debugging |
| `netstat` | Sockets/routes table (there is no `ss`) |
| `wget` | HTTP(S) fetch; HTTPS only if the build has TLS support |
| `httpd` | Tiny HTTP server with CGI support |
| `tftp` | TFTP get/put — bootloader and PXE land |
| `nc` | netcat: raw TCP/UDP, `-l -p` to listen |
| `udhcpc` | DHCP client; needs a hook script to apply leases |

### Process

| Applet | One-liner |
|---|---|
| `ps` | Bare process table — see the flag-drift section before using `-o` |
| `top` | Interactive process monitor (real, just minimal) |
| `free` / `uptime` | Memory summary and load line |
| `kill` / `killall` | Signal by PID or by name |
| `pgrep` / `pkill` | Find/signal processes by pattern |
| `timeout` | Run with a time limit |

## GNU Flag Drift

BusyBox applets accept the POSIX/short-flag core of each utility and omit
most GNU extensions — long options included. The five high-traffic cases:

### ls

```bash
$ ls --sort=time --time-style=full-iso   # GNU: fine
$ busybox ls --sort=time                 # busybox: unrecognized option
```

GNU `ls` also shell-escapes odd filenames by default
(`--quoting-style=shell-escape`, coreutils 8.25+) while BusyBox prints them
raw — parse listings with `find -print0 | xargs -0` instead.

### sed

```bash
$ sed --null-data 's/\x00/,/g'   # GNU: -z/--null-data exist
$ busybox sed -z 's/\x00/,/g'    # no -z; no long options at all
```

BusyBox `sed` is a solid POSIX sed (addresses, `s///`, `y///`, a/i/c).
Missing: `--posix`, `--null-data`, long forms, and GNU's in-place suffix
form `sed -i.bak` — check `busybox sed --help` on the target build first.

### tar

```bash
$ tar -a -cf out.tar.gz dir/         # GNU: -a auto-compresses by suffix
$ busybox tar -czf out.tar.gz dir/   # busybox: name the compression yourself
```

BusyBox `tar` takes `-z`/`-j`/`-J` explicitly and auto-detects compression on
extract; GNU-only `-a`, `--sort=name` (reproducible archives), and
`--transform` do not exist.

### grep

```bash
$ grep -P '\d{4}-\d{2}-\d{2}' f.txt        # GNU: PCRE
$ busybox grep -P '\d{4}-\d{2}-\d{2}' f.txt
grep: unrecognized option: P
```

No PCRE, no `--color`, no `--exclude-dir`/`--include`; the POSIX/short set
(`-E`/`-F`, `-r`, `-v`, `-q`, `-c`, `-A`/`-B`/`-C`, `-l`, `-o`) is intact.

### ps

```bash
$ ps aux          # procps: full BSD-style listing
$ ps aux          # minimal busybox: arguments SILENTLY IGNORED
PID   USER     TIME   COMMAND
    1 root      0:02   /sbin/init
```

procps defaults to `PID TTY TIME CMD` with the `aux` trio and rich `-o`
keywords; BusyBox defaults to `PID USER TIME COMMAND`, silently ignores
arguments on trimmed builds, and accepts only a small `-o` subset.

## Build-Time Trimming: CONFIG_

Every applet and feature is behind a Kconfig symbol: `make defconfig`
enables the conventional full set, `make menuconfig` carves it down:

```
CONFIG_LS=y
CONFIG_FEATURE_LS_COLOR=y
CONFIG_FEATURE_TAR_LONG_OPTIONS=y
CONFIG_STATIC=y
```

- **Same version, different builds, different tools.** Vendor firmware and
  Alpine can both ship "busybox 1.3x" with different applet sets.
- **Applets are removed, not stubbed.** Unset `CONFIG_LS` and there is no
  `ls` at all — symlink farm or not.
- **Size is the knob.** Every disabled feature is code not compiled in;
  careful configs drop the binary well below the megabyte scale.

## Static Linking: glibc vs musl

For initramfs and scratch containers the binary must be static — there is no
libc in the image to load. Static glibc works, but NSS-based calls pull
shared libraries at runtime anyway — hence the linker warnings about
`getaddrinfo`/`getpwuid`. musl is designed for static linking: small,
self-contained, no NSS machinery; Alpine's `busybox-static` is musl-based,
which is why it drops into any `scratch` image cleanly. The tradeoff is
musl's simpler resolver (no `nsswitch.conf`). A fully featured static
BusyBox against musl lands in the one-to-few-megabytes range people mean by
"about a megabyte".

## Networking Applets Worth Knowing

Five applets cover most "the machine is broken but has TCP" scenarios:

```bash
$ busybox httpd -f -p 8080 -h /var/www   # serve a dir; CGI if built in
$ busybox tftp -g -r firmware.bin 10.0.0.1   # pull from a TFTP server
$ busybox wget -O - http://10.0.0.5:8080/status  # HTTPS needs build TLS
$ busybox nc -z 10.0.0.1 5432            # is anything listening?
$ busybox udhcpc -i eth0 -s /usr/share/udhcpc/default.script  # get a lease
```

`httpd` doubles as a recovery channel for files off a damaged box; `tftp`
exists because bootloaders (U-Boot, PXE) speak TFTP, not HTTP; `udhcpc`
shows that even DHCP is script-driven here — the lease hook is a readable,
fixable script on the box (Debian ships `/usr/share/udhcpc/default.script`).

## Usage Patterns

```bash
# What is this userland, really? Two commands answer everything
$ busybox | head -3 && busybox --list | wc -l

# scratch-image debugging: copy busybox in, get a shell
$ docker cp busybox-static c0:/bb && docker exec -it c0 /bb sh

# Alpine container: the shell is ash, the tools are applets
$ docker run --rm -it alpine sh -c 'readlink /bin/sh; ps'
```

## Nuances and Gotchas

- **ash is not bash.** No arrays, no `[[ ]]`, no `<()`; scripts for Alpine
  or initramfs must be POSIX — see [bash](../shell/bash.md).
- **Flag drift is versioned twice** — by BusyBox build (CONFIG_ symbols) and
  by GNU version on the other side; same "1.3x" string, different behavior.
- **`ps` lies by omission on trimmed builds** — arguments are ignored, so a
  monitor that "checks" with `ps aux` gets the same short table everywhere.
- **musl vs glibc resolver** — no `nsswitch.conf` on musl systems; lookups
  go straight to `/etc/resolv.conf`, so NSS-dependent identity differs.
- **`busybox init` has its own inittab dialect** (`::sysinit`, `::respawn`,
  `::ctrlaltdel`) — not SysV, not systemd.
- **Exit codes are approximations** — applets simplify upstream edge cases;
  do not build fine-grained logic on exit 1 vs 2 in a BusyBox applet.

## Exit Status

| Invocation | Status |
|---|---|
| `busybox --list` / `--list-full` | 0 on success |
| `busybox` with no arguments | prints usage, exits non-zero |
| `busybox notanapplet` | `notanapplet: applet not found`, non-zero |
| applet invocation (`busybox ls`, `/bin/ls`) | the applet's own exit code |

## Related Commands

- [Part overview](./overview.md) — where BusyBox sits among the collections.
- [GNU Coreutils](./coreutils/overview.md) — the full-featured counterpart.
- [tar](./tar/tar.md) — GNU tar semantics versus the BusyBox applet; [ps](./procps/ps.md) —
  procps-ng's real option grammar behind the drift.
- [grep](../shell/grep.md), [sed + awk](../shell/sed-awk.md) — deep pages for
  the widest-drift applets.

## Interview Questions

### Q: You exec into a container and `ls` is missing but `sh` works. What shipped, and what do you do?

A multi-call binary shipped and the farm is incomplete — classically a
`scratch`-style image or a trimmed BusyBox. Check what PID 1 really is
(`/proc/1/exe`); if it is busybox, use the first-argument form: `busybox ls`
and `busybox --list`, which separates "missing" from "compiled out".

### Q: Why is BusyBox the standard initramfs userland, and what are its limits there?

The initramfs is a compressed cpio archive with no distro behind it — it must
carry its own shell, mount, and module tools in as few bytes as possible, and
a static BusyBox delivers 300+ applets for roughly a megabyte. Limits follow
from the same constraint: POSIX-subset flags, ash not bash, hardware tools
possibly compiled out. Write `/init` by hand, mount `/proc`, pivot with
`switch_root`.

### Q: Explain argv[0] dispatch and one way it can break.

BusyBox looks up `basename(argv[0])` in its compiled-in applet table, so a
symlink named `ls` pointing at the binary makes exec run the ls applet;
alternatively the first argument to `busybox` names the applet. It breaks
when `/proc` is unmounted (`--install` resolves itself via `/proc/self/exe`),
when a stale farm points at a rebuild that dropped the applet, or via a
crafted argv[0].

### Q: Design question: when would you not use BusyBox as a container userland?

When GNU-behavior compatibility matters more than image size: scripts relying
on GNU long options or sed/tar extensions, full procps output, locale/i18n
behavior, NSS-backed identity — or teams that would spend more time debugging
drift than they save in megabytes. Debian slim images keep GNU coreutils for
this reason; weigh bytes against the long tail, and measure first.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/busybox/busybox.1.en.html)
- [BusyBox project](https://www.busybox.net/)
- [BusyBox manual](https://www.busybox.net/downloads/BusyBox.html)
