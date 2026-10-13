# uname — print kernel and system identification

## Overview

`uname` ("unix name") prints identification data about the running kernel
and the machine: system name, network node name (hostname), kernel release
and build version, hardware architecture, and — as GNU extensions — the
processor type, hardware platform, and operating system. It is how shell
scripts answer "which kernel am I running on" and "am I on x86_64 or
aarch64".

It ships in the Debian `coreutils` package at `/usr/bin/uname` and
implements a single syscall: `uname(2)`, which fills a `struct utsname` from
kernel memory. Everything `uname` prints comes from that syscall — it never
reads `/etc/os-release`, never shells out, and never consults
configuration. This is the single most common misconception about it: `uname`
reports the *kernel*, not the *distribution*. Two machines running Debian 12
and Ubuntu 24.04 on the same kernel can print identical `uname` output.

It is often confused with `hostname` (which prints only the node name, from
a different syscall), with `lsb_release`/`cat /etc/os-release` (distribution
identity), and with `arch` (which is exactly `uname -m`).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/uname` |
| First appeared / lineage | PWB/UNIX, then System III/V; in GNU coreutils |
| Standards | POSIX.1-2017 (`-a`, `-s`, `-n`, `-r`, `-m`, `-v`) |

## Synopsis

```text
uname [OPTION]...
```

```bash
uname          # kernel name only (default: -s)
uname -a       # everything, in fixed field order
uname -r       # kernel release — feature gating in scripts
uname -m       # machine architecture — binary/package selection
```

## How It Works

`uname(2)` fills seven kernel-maintained strings; each flag selects one of
them (or the GNU extras). The `utsname` struct maps directly onto the flags:

```text
struct utsname field        flag    example value on this machine
────────────────────────    ────    ─────────────────────────────
sysname  (kernel name)      -s      Linux
nodename (hostname)         -n      c-6ac89cf4-14810412-394312c537f8
release  (kernel release)   -r      5.10.134-013.15.kangaroo.al8.x86_64
version  (build stamp)      -v      #1 SMP Thu Jul 30 12:54:59 UTC 2026
machine  (architecture)     -m      x86_64
domainname                  (rarely set; not exposed by coreutils flags)

GNU extensions (not from struct utsname):
processor type              -p      unknown
hardware platform           -i      unknown
operating system            -o      GNU/Linux
```

`-a` prints everything in the fixed order `-s -n -r -v -m -p -i -o`,
omitting `-p` and `-i` when they are unknown:

```bash
$ uname -a
Linux c-6ac89cf4-14810412-394312c537f8 5.10.134-013.15.kangaroo.al8.x86_64 #1 SMP Thu Jul 30 12:54:59 UTC 2026 x86_64 GNU/Linux
$ uname -s; uname -n; uname -r; uname -m; uname -o
Linux
c-6ac89cf4-14810412-394312c537f8
5.10.134-013.15.kangaroo.al8.x86_64
x86_64
GNU/Linux
```

The distribution boundary is worth demonstrating: nothing in `uname` output
says *which distro* this is, because the kernel does not know. That data
lives in userspace:

```bash
$ uname -o          # kernel's opinion: "GNU/Linux" — no distro name
GNU/Linux
$ . /etc/os-release && echo "$PRETTY_NAME"    # distro identity lives here
```

The processor/platform fields are a portability story of their own. On
x86_64 Linux the kernel does not expose a distinct "processor type" or
"hardware platform" the way older or proprietary Unices did, so GNU `uname`
prints `unknown` for `-p` and `-i` on such systems — this machine included.
POSIX does not standardize `-p` or `-i` precisely because they are not
portably defined, and the coreutils man page labels them *non-portable*.
Scripts that need an architecture must use `uname -m`.

## Options That Matter

| Option | Effect |
|---|---|
| `-a`, `--all` | All fields, in the fixed order `-s -n -r -v -m -p -i -o` (skip unknown `-p`/`-i`) |
| `-s`, `--kernel-name` | Kernel name: `Linux` (the default when no flags are given) |
| `-n`, `--nodename` | Hostname as the kernel knows it |
| `-r`, `--kernel-release` | Kernel release string (feature/driver gating) |
| `-v`, `--kernel-version` | Kernel build stamp (compile date, SMP flags) |
| `-m`, `--machine` | Hardware architecture: `x86_64`, `aarch64`, ... |
| `-p`, `--processor` | Processor type — non-portable, frequently `unknown` |
| `-i`, `--hardware-platform` | Hardware platform — non-portable, frequently `unknown` |
| `-o`, `--operating-system` | GNU extension: `GNU/Linux` |

## Usage Patterns

```bash
# Pick the right binary download by machine architecture
case "$(uname -m)" in
    x86_64)  URL=".../tool-linux-amd64.tgz" ;;
    aarch64) URL=".../tool-linux-arm64.tgz" ;;
    *) echo "unsupported arch" >&2; exit 1 ;;
esac
```

```bash
# Gate a feature on a kernel version (e.g. io_uring needs newer kernels)
KMAJOR=$(uname -r | cut -d. -f1); KMINOR=$(uname -r | cut -d. -f2)
[ "$KMAJOR" -gt 5 ] || { [ "$KMAJOR" -eq 5 ] && [ "$KMINOR" -ge 1 ]; } \
  && echo "io_uring available"
```

```bash
# Short kernel identity in prompts or logs
echo "$(uname -sr)"
```

```bash
# Distinguish kernel release from build version
uname -r; uname -v
```

```bash
# Sanity check that we booted the kernel we installed
uname -r; ls /boot | grep "^vmlinuz-$(uname -r)$" || echo "running kernel not in /boot?!"
```

```bash
# Node name for identifying the host inside containers (see gotchas)
uname -n
```

```bash
# Recognize the platform family for package manager choice
if [ "$(uname -o)" = "GNU/Linux" ]; then echo "linux packaging paths"; fi
```

```bash
# `arch` is exactly `uname -m`; confirm
[ "$(arch)" = "$(uname -m)" ] && echo same
```

## Nuances and Gotchas

- **`uname` says nothing about the distribution.** Kernel data only. For
  distro identity read `/etc/os-release` (systemd-standardized) or
  `lsb_release -a`. Asking uname for the distro is the canonical interview
  trap.
- **In containers, `uname` reports the *host's* kernel.** Docker/Podman
  share the host kernel, so `uname -r` inside a Debian container on a
  CentOS host prints the CentOS vendor kernel string. Debugging "why does
  uname disagree with my os-release" starts here.
- **`-p` and `-i` are legitimately `unknown`** on x86_64 Linux and cannot be
  relied on anywhere — the fields date from systems (Sun, DEC) where
  processor and machine genuinely differed (e.g. `sparc` processor on
  `sun4u` hardware). Use `-m` and only `-m`.
- **`x86_64` ≠ `amd64` ≠ `x64`.** `uname -m` says `x86_64`; Debian/Ubuntu
  package architecture is `amd64`. Mapping tables are the norm in build
  scripts, not a bug to fix.
- **`-m` reflects the *running kernel*, not the CPU or userland**: a 32-bit
  userland on a 64-bit kernel reports `x86_64`, and ARMv7 hardware may
  report `armv7l` while packages expect `armhf`. For userland ABI,
  `dpkg --print-architecture` (or `getconf LONG_BIT`) is the truthful
  answer.
- **`uname -n` vs `hostname`**: both usually agree, but `hostname` reads/sets
  the *userland* notion (and UTS namespace), while `uname -n` reads the
  kernel's current value for this UTS namespace. Containers rename hosts by
  changing the UTS namespace — the two commands stay consistent, but both
  differ from the physical host.
- **`-a` field order is fixed and locale-stable**, which makes naive
  `uname -a | awk '{print $3}'` parsing common but fragile; prefer explicit
  flags (`uname -r`) in scripts.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | Information printed successfully |
| nonzero | Write error or invalid option (GNU diagnostic to stderr) |

There are no "interesting" failure statuses: the syscall does not fail on a
running Linux system in practice.

## Related Commands

- [`whoami`](./whoami.md) — the user-identity counterpart: who am I vs what system is this.
- [`tty`](./tty.md) — another "report one environment fact" coreutils utility.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: Why does `uname` not tell you the Linux distribution?

Because it only formats the `struct utsname` returned by the `uname(2)`
syscall, and the kernel has no concept of distributions — that is userspace
configuration. Distro identity lives in `/etc/os-release` (with
`lsb_release` as an older front-end). This separation is by design: the same
kernel binary can boot any distro, and `uname` output is identical on two
distros sharing a kernel build.

### Q: What is the history behind `uname -p` printing "unknown" on x86_64 Linux?

`-p` (processor type) and `-i` (hardware platform) come from systems where
the CPU family and the machine model were genuinely independent — classic
examples are SPARC processors on sun4u chassis. On PC-derived x86_64 Linux
the kernel does not expose a distinct processor/platform identifier, so
coreutils prints `unknown`, and the man page marks both options
non-portable. POSIX deliberately left them out of the standard set, which
is why architecture detection scripts standardize on `uname -m`.

### Q: Inside a Docker container, why can `uname -r` disagree with the distro's expected kernel?

Containers share the host kernel — there is no kernel virtualization. The
container's userland (its `/etc/os-release`) says Debian, but `uname`
reports the host's running kernel, possibly with a foreign vendor suffix in
the release string. Anything kernel-dependent (eBPF features, cgroup
version, module availability) must be assessed from `uname -r`, not from
the distro files.

### Q: Which flag would you use to select binaries in an install script, and what are its limits?

`uname -m` — it is the only portable, standardized-ish source for machine
architecture. Its limits: it reflects the kernel architecture, not the
userland ABI (32-bit userland on 64-bit kernel still reports `x86_64`), and
its naming (`x86_64`, `armv7l`, `aarch64`) does not match package-manager
architectures (`amd64`, `armhf`, `arm64`), so scripts need a small mapping.
For userland ABI questions, `dpkg --print-architecture` is authoritative on
Debian-family systems.

### Q: What is the difference between `uname -n` and `hostname`?

In normal operation they print the same string: the kernel's node name for
the current UTS namespace. `hostname` is the userland front-end that can
also *set* the name and read files like `/etc/hostname`; `uname -n` is a
read-only view of kernel state. In containers, both track the UTS namespace
the process lives in, so a container's `uname -n` differs from the physical
host's — a detail that matters when correlating logs across namespace
boundaries.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/uname.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
