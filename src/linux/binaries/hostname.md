# hostname — show or set the system's host name

## Overview

`hostname` displays or sets the kernel's host name — the short name the system knows itself by before any directory service is consulted. It is one of the smallest tools on a system with one of the largest blast radii: the name it prints feeds shell prompts, log correlation, monitoring dashboards, SSH known-hosts matching, and every service that derives its own identity from the OS. Debian ships it in the dedicated `hostname` package (Priority: required) at `/usr/bin/hostname`, with `/bin/hostname` available through the usrmerge.

The same binary serves under four other names via symlinks — `dnsdomainname`, `domainname`, `ypdomainname`, `nisdomainname` — dispatching on `argv[0]` to display just the DNS domain or the NIS/YP domain. This Variants pattern predates multi-call busybox-style binaries by decades.

`hostname` is often confused with `hostnamectl` (the systemd manager, which owns the *static* name in `/etc/hostname`, the *transient* kernel name, and the *pretty* description together — see below), with `uname -n` (prints the same kernel value, read-only), and with DNS tooling like `dig` (which queries the resolver about arbitrary names; `hostname` reads local kernel and resolver state).

| Field | Value |
| --- | --- |
| Package | hostname (Debian; Priority: required) |
| Man section | 1 |
| Path | /usr/bin/hostname |
| First appeared | BSD heritage; rewritten for Debian Linux by Peter Tobias (1990s) |
| Standards | Not POSIX; ubiquitous Unix convention (gethostname/sethostname semantics) |

## Synopsis

```
hostname [-a|-A|-d|-f|-i|-I|-s|-y]     # display a formatted name
hostname [-b] {NAME|-F FILE}           # set the host name
```

The display family, as the usage banner renders it:

```
hostname                  # the kernel's current host name
hostname -f               # FQDN (fully qualified domain name)
hostname -s               # short name (cut at the first dot)
hostname -d               # DNS domain part
hostname -i               # IP address(es) the host name resolves to
hostname -I               # all IP addresses configured on the host
hostname -y               # NIS/YP domain name
hostname -V|--version|-h|--help   # print info and exit
```

## How It Works

### The kernel name and where it lives

The host name is a kernel property: `gethostname(2)` reads it, `sethostname(2)` writes it (requiring `CAP_SYS_ADMIN`, i.e. root), and it is capped at 64 bytes (`getconf HOST_NAME_MAX`). The live value is directly visible as `/proc/sys/kernel/hostname` and is settable through `sysctl kernel.hostname=` — `hostname` is a friendly front end over those two syscalls, nothing more.

The boot story is the part that matters operationally: at startup, the init system (systemd, or legacy init scripts) reads `/etc/hostname` — the **static** name — and calls `sethostname` to install it as the **transient** kernel name. Editing the file changes only the next boot:

```bash
$ cat /etc/hostname
c-6ac89cf4-14810412-394312c537f8
$ cat /proc/sys/kernel/hostname
c-6ac89cf4-14810412-394312c537f8
```

Because the value is a sysctl, `sysctl kernel.hostname=NAME` (or a root write to `/proc/sys/kernel/hostname`) is an equivalent setter — and the deeper fact behind that: the host name is a property of the **UTS namespace**, which is why containers and other namespace-isolated processes carry their own names on one kernel.

### FQDN, short name, and the resolution chain

`hostname -f` does **not** contain a stored FQDN — it runs the host name through the resolver (`getaddrinfo`) and reports the first canonical name returned, which typically comes from `/etc/hosts` before DNS is ever consulted. This is why the hostname(1) manual says the FQDN and DNS domain are changed *in `/etc/hosts`*: the tool has no `-f` setter because there is nothing to set in the kernel. `-s` truncates the result at the first dot; `-d` prints the domain part; `-A` prints every resolvable FQDN for the host; `-a` (legacy) asks for aliases, which modern resolver setups usually leave empty.

```
kernel name ──gethostname──▶ "web01"
                                 │ getaddrinfo("web01")
                                 ▼
                    /etc/hosts ▶ DNS ▶ ...
                                 │
        "web01.example.com" ◀────┘   (first canonical name = FQDN)
              │                  │
         -f / -s / -d       -i (addresses for that name)
```

On a box with no domain configured — as in this container — the chain collapses gracefully and each flag degrades rather than errors:

```bash
$ hostname          # kernel name, short here
c-6ac89cf4-14810412-394312c537f8
$ hostname -f       # no domain in /etc/hosts → FQDN == kernel name
c-6ac89cf4-14810412-394312c537f8
$ hostname -d       # no domain part → empty output
$ hostname -y       # NIS domain never configured
hostname: Local domain name not set
```

The `/etc/hosts` line is where the FQDN is authored — the Debian convention puts the FQDN as the *first* alias on the host's own line, with the short name after it:

```
127.0.0.1       localhost
127.0.1.1       web01.example.com web01
```

With that line in place, `hostname -f` reports `web01.example.com`, `-s` reports `web01`, and `-d` reports `example.com` — all from one resolver lookup of the kernel name.

### Address lookup: -i versus -I

`-i` answers "what addresses does *this host name* resolve to?" — a resolver question, and only as good as `/etc/hosts` and DNS make it. `-I` answers "what addresses does *this machine's network stack* have?" — enumerated from the interfaces, no resolver involved. They diverge on multihomed hosts, containers, and NAT, which is why scripts that need "the machine's IPs" use `-I` and scripts that need "what others reach me as" fix `/etc/hosts` and use `-i`.

```bash
$ hostname -i        # resolver: addresses for the configured name
21.0.10.227
$ hostname -I        # interface enumeration: everything configured
21.0.10.227
```

### Setting the name

Setting requires root and either a literal NAME or `-F FILE` (commonly `-F /etc/hostname` to apply the static file without rebooting). `-b`/`--boot` is the setter's polite mode: install the given name only if none is set, otherwise fall back to `localhost` — designed for early boot scripts that must never blank the name. A set operation changes the transient kernel value only; it does not touch `/etc/hostname`, so the change evaporates at the next reboot unless the file is updated too.

```bash
$ hostname web01           # as root: transient kernel name → web01
$ hostname                 # confirms
web01
$ hostname -F /etc/hostname   # apply the static file without reboot
```

### The boot-time handoff and the three-name model

The full identity lifecycle on a modern system runs through three names: **static** (`/etc/hostname`), **transient** (the kernel value), and **pretty** (a free-form description carried by systemd). At boot, systemd's `systemd-hostnamed` machinery reads the static name and installs it with `sethostname`; `hostnamectl set-hostname NAME` performs that two-part write interactively — file plus kernel — which is precisely the step raw `hostname` skips. The division of labor for interviews: `hostname` is the read-anywhere, set-transient-only tool; `hostnamectl` is the complete manager; `/etc/hostname` is the only persisted state.

### Name hygiene and limits

The kernel enforces exactly one rule that matters — a 64-byte maximum (`getconf HOST_NAME_MAX`) — and accepts almost any byte sequence within it. Everything else is convention imposed above the syscall, and each layer adds its own: DNS-safe names stick to lowercase letters, digits, and hyphens (no leading/trailing hyphen, no dots in the short name), `localhost` is reserved, and systemd's hostnamed layer applies its own validation to the static name before accepting it. The practical rule: choose names the strictest consumer (DNS, TLS certificates, SMTP HELO) will accept, because the kernel will not warn you.

### Variants: the argv[0] family

Four symlinked names dispatch to domain-display modes of the same binary — the usage banner documents the mapping itself:

```
Program name:
       {yp,nis,}domainname=hostname -y
       dnsdomainname=hostname -d
```

`dnsdomainname` prints the DNS domain part (never the full FQDN — it is *literally* `hostname -d`), and the three NIS-family names display the yellow-pages domain, a facility that survives mostly in legacy and cluster environments. Calling them under the wrong name does what the mapping implies:

```bash
$ ls -l /usr/bin/dnsdomainname /usr/bin/domainname
lrwxrwxrwx 1 root root 8 ... /usr/bin/dnsdomainname -> hostname
lrwxrwxrwx 1 root root 8 ... /usr/bin/domainname -> hostname
```

### Transient vs static vs pretty, and the hostnamectl handoff

systemd models three names: **static** (in `/etc/hostname`), **transient** (the kernel value, reset at boot), and **pretty** (a free-form description). `hostnamectl` reads and writes all three coherently — `hostnamectl set-hostname web01` updates the static file *and* the running kernel, the exact two-step that raw `hostname` leaves half-done. On systemd systems the professional flow is hostnamectl for changes and `hostname` for read-only checks in scripts; this page's tool remains the portable fallback everywhere else, including minimal containers.

## Options That Matter

| Option | Effect |
| --- | --- |
| *(none)* | Display the kernel host name |
| `-f`, `--fqdn` | FQDN: the host name resolved to its first canonical form |
| `-s`, `--short` | Name truncated at the first dot |
| `-d`, `--domain` | DNS domain part of the FQDN |
| `-A`, `--all-fqdns` | All resolvable FQDNs of the host |
| `-i`, `--ip-address` | Address(es) the host name resolves to (resolver-based) |
| `-I`, `--all-ip-addresses` | All addresses configured on the host's interfaces |
| `-y`, `--yp`, `--nis` | NIS/YP domain name (display or, as root, set) |
| `-F`, `--file` | Set the name (or NIS domain with `-y`) from FILE |
| `-b`, `--boot` | Set the name only if none is set; default to `localhost` |
| `-a`, `--alias` | Legacy alias display (usually empty today) |
| `-V` / `-h` | Version / help — the help screen doubles as a mode map |

## Usage Patterns

```bash
# The identity check every troubleshooting session starts with
hostname; hostname -f; hostname -I
```

```bash
# Apply a renamed machine's static config without rebooting
sudo hostname -F /etc/hostname
```

```bash
# Bootstrap-safety in early-boot scripts: never unset the name
hostname -b -F /etc/hostname
```

```bash
# Short name for prompt/log tags regardless of FQDN configuration
PS1="[\u@$(hostname -s) \W]\\$ "
```

```bash
# Sanity-check /etc/hosts: FQDN should appear as the first alias on the 127.0.1.1 line
hostname -f && hostname -d
```

```bash
# Inventory a fleet's addressing without depending on DNS
for h in $(cat hosts.txt); do echo "$h $(ssh $h hostname -I)"; done
```

```bash
# Legacy NIS environment: display the domain under its historical name
domainname
```

```bash
# Shell-neutral equivalent when hostname(1) is absent (busybox containers)
uname -n
```

```bash
# Cross-check identity after a rename: static file, kernel, and resolver
hostname; hostname -f; hostname -I; tail -2 /etc/hosts
```

```bash
# Legacy cluster: set the NIS domain at boot (root; same -y machinery)
domainname corp
```

```bash
# Read-only inspection via the manager on systemd hosts
hostnamectl status
```

```bash
# Capture identity once in long-running scripts (the name can change mid-run)
readonly HOST_TAG="$(hostname -s)"
```

## Nuances and Gotchas

- **Editing `/etc/hostname` does nothing to the running system** — it is read at boot; until `hostname -F` or `hostnamectl set-hostname` runs, prompts and new logs keep the old name, and log correlation across the boundary gets interesting.
- **`hostname` sets only the transient value** — no file is written, so a change made with the raw tool silently reverts at reboot. The classic "why did the name change back?" incident is this asymmetry; hostnamectl exists to close it.
- **`-f`/`-d` depend on the resolver, not on the kernel** — a missing or malformed `/etc/hosts` line (no FQDN alias on the hostname line) yields a bare short name for `-f` and empty output for `-d`, with no error to point at the cause.
- **`-i` is the wrong tool for "my IPs"** — it queries the resolver about the name and inherits every DNS/hosts inconsistency; `-I` enumerates interfaces directly and is what scripts almost always want.
- **64-byte limit, hard**: names beyond `HOST_NAME_MAX` (64) fail with an error; DNS-hygienic names (`[a-z0-9-]`, no leading/trailing hyphen) keep every consumer — from SMTP HELO to TLS SANs — out of trouble even where the kernel would accept more.
- **argv[0] behavior is real contract**: scripts that copy the `hostname` binary under another name (or run it in a multi-call context) get the `-d`/`-y` behaviors of that name — a portability surprise for toolbox-style containers.
- **BusyBox `hostname` is a subset** (roughly `-F -s -i -d -y`) — infrastructure scripts that lean on `-I`, `-A`, or `-b` should feature-test rather than assume.
- **`uname -n` reads the same kernel value** and is the POSIX-portable read; the reverse is not true — `uname` cannot set anything, which is exactly the division of labor.
- **`-I` output order is not specified** — with several interfaces the first address is whatever the kernel enumerates first; scripts needing a stable choice must filter (e.g. exclude `127.`, link-local, or docker0 ranges) rather than take the head.
- **Dotted short names make `-s` surprising**: `-s` cuts at the first dot, so a kernel name like `web01.eu` yields `web01` — a mismatch with `hostname` that confuses log taggers; keep dots out of the kernel name and put the domain in `/etc/hosts`.
- **The name is global and changes instantly** — daemons that cached it at startup keep reporting the old identity until restarted, which is why renames are maintenance events (restart logging and identity-aware services) rather than one-liners.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success (display, or successful set as root) |
| 1 | Operational failure: not root when setting (`you must be root to change the host name`), domain not set for `-y`, resolution failure for `-f`/`-i` |
| 255 | Option-parse error on this build (e.g. an unrecognized flag) |

## Related Commands

- [Networking configuration](../admin/networking-config.md) — where `/etc/hosts`, resolver order, and the FQDN this tool reports are actually configured.
- [systemd](../admin/systemd.md) — `hostnamectl`, the three-name model (static/transient/pretty), and the manager behind the boot-time handoff.
- [Internals](../internals.md) — the kernel side: `gethostname`/`sethostname` and `/proc/sys/kernel/hostname` as the sysctl view.

## Interview Questions

### Q: What is the difference between the transient and static host name, and which does `hostname` touch?

The static name lives in `/etc/hostname` and is what the init system installs into the kernel at boot; the transient name is the live kernel value in `/proc/sys/kernel/hostname`. Running `hostname NAME` (as root) changes only the transient value — nothing is persisted, so the next boot restores the static name. `hostnamectl set-hostname` updates both, which is why it is the preferred interface on systemd systems and why a raw `hostname` change is a reboot-reverting footgun.

### Q: How does `hostname -f` derive the FQDN, and why do you configure it in /etc/hosts rather than in the tool?

There is no FQDN stored in the kernel — `-f` takes the kernel name and passes it through the resolver, reporting the first canonical name that comes back, which `/etc/hosts` typically provides ahead of DNS. The tool therefore has no FQDN setter: adding `web01.example.com web01` as the hostname line's first alias is the configuration act, and a missing alias degrades `-f` to the short name silently.

### Q: When do `-i` and `-I` disagree, and which belongs in scripts?

`-i` asks the resolver what the configured host name resolves to; `-I` enumerates every address on the machine's interfaces without touching the resolver. They diverge on multihomed hosts (several NICs, only one named), behind NAT, and in containers with stale `/etc/hosts` entries. Scripts that need the machine's addresses use `-I` because it reflects the network stack as-is; `-i` answers the different question "by what addresses is my name reachable," which is a resolver policy statement.

### Q: Explain the dnsdomainname/domainname/ypdomainname commands.

They are symlinks to `hostname` that dispatch on `argv[0]`: `dnsdomainname` is exactly `hostname -d` (the DNS domain part of the FQDN, never the FQDN itself), while `domainname`, `ypdomainname`, and `nisdomainname` are `hostname -y` — the NIS/YP domain, a separate and largely legacy facility distinct from DNS. The multi-call design predates busybox; its practical consequence is that these names are contracts scripts rely on, so the symlink set ships with the package.

### Q: A machine shows the old host name in new log lines after an admin "renamed" it by editing /etc/hostname. What happened and what is the fix?

`/etc/hostname` is boot-time configuration: editing it changed the static name only, while the running kernel keeps the transient value, so every new log line still carries the old identity. The fix is applying it now — `hostname -F /etc/hostname` (the raw tool) or, better, `hostnamectl set-hostname NAME`, which writes the file and updates the kernel in one step — followed by the operational cleanup of correlating logs across the identity boundary.

### Q: What guarantees does the kernel give about the host name, and what limits exist?

The name is a 64-byte-maximum kernel string (`HOST_NAME_MAX`), readable by any process via `gethostname(2)` and writable only with `CAP_SYS_ADMIN` via `sethostname(2)` — no uniqueness, no DNS validity, no format enforcement at that layer. All the hygiene (lowercase, hyphens, FQDN aliasing, uniqueness in the fleet) is policy applied above the syscall, which is why invalid names surface later as TLS, mail, or service-discovery failures instead of as `hostname` errors.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/hostname/hostname.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/hostname/)
