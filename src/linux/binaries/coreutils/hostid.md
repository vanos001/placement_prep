# hostid — print the numeric host identifier of the current host

## Overview

`hostid` prints a 32-bit numeric identifier for the host, in hexadecimal:

```bash
$ hostid
0015e30a
```

It takes no arguments and has no options beyond `--help`/`--version`. The
value comes from the libc `gethostid(3)` call, which reads whatever the
system's "host ID" was set to — via `sethostid(2)` at boot or
administratively — and, when nothing was ever set, historically derives it
from the machine's IPv4 address as known to hostname resolution.

Debian ships it in `coreutils` at `/usr/bin/hostid`. It is a survivor from
the Sun/Solaris world, where `hostid` was a real hardware identity token
(burned into NVRAM, used for license keys). On Linux it never had a
hardware anchor: the value is software-defined, frequently *unset*, often
identical across containers and cloned VMs, and byte-order-dependent in
derivation. Modern identity needs are served by `/etc/machine-id` (128-bit,
systemd-managed) or SMBIOS/DMI UUIDs.

The page is short because the tool is dormant — and that dormancy is
itself the interview content: why it exists, how it computed its value,
why it is useless as an identity today, and what replaced it.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/hostid` on modern Debian/Ubuntu |
| First appeared / lineage | BSD/SunOS heritage (hardware host ID); GNU version wraps `gethostid(3)` |
| Standards | Not POSIX-standardized; installed only on systems providing `gethostid()` |

## Synopsis

```
hostid
```

```bash
hostid            # -> 8 hex digits, e.g. 0015e30a
hostid --help     # usage (one of only two options)
hostid --version  # version banner
```

There are no operands and no functional flags; the man page's synopsis is
a bare command name.

## How It Works

### The chain of custody

```
 hardware? ──(no, on Linux)──► /etc/hostid file? ──► sethostid(2) value in
        (Solaris: NVRAM)            (glibc ext)        kernel utsname-adjacent
                                          │                     │
                                          ▼                     ▼
                                   gethostid(3) ◄──── derived from IPv4 of
                                   (libc)             the hostname if never set
                                          │
                                          ▼
                                    hostid(1) prints %08x
```

`hostid(1)` calls `gethostid(3)`. On glibc/Linux the identifier is:

1. The value set by `sethostid(2)` (root-only syscall storing a 32-bit
   number), or from `/etc/hostid` where supported;
2. else a value synthesized from the IPv4 address the *hostname* resolves
   to, byte-manipulated in a Sun-compatible layout. The coreutils manual
   is candid that the quantity "happens to be closely related to the
   system's Internet address, but that isn't always the case".

Neither source is a hardware identity. DHCP renumbering, `/etc/hosts`
defaults (Debian's `127.0.1.1` line), containers, and VM clones all feed
colliding or meaningless values into the same function.

### Why the Sun lineage matters

On SunOS/Solaris, `hostid` reported an NVRAM-stored ID used in licensing
(FlexLM-style) and asset tracking. The GNU tool replicates the *command
 surface* but not the *anchor*: Linux has no per-machine NVRAM identity
 exposed to `gethostid(3)`. Scripts and license schemes ported from Sun
 assumed uniqueness the Linux implementation cannot deliver — the root of
 the tool's reputational collapse.

### The 32-bit ceiling

Even in the best case the identifier is 32 bits: ~4 billion values. The
birthday bound makes collisions likely around ~65k machines; datacenters
and fleets exceed that trivially. `/etc/machine-id` (128-bit random) or
DMI UUIDs (128-bit, vendor-set) are the modern identities precisely
because they are wide and anchored.

### What replaced it

| Need | Old answer | Modern answer |
| --- | --- | --- |
| Stable machine identity | `hostid` | `/etc/machine-id` (`systemd-machine-id-setup`, first boot) |
| Hardware/firmware identity | Solaris NVRAM hostid | SMBIOS UUID (`dmidecode -s system-uuid`), DMI serials |
| Instance identity (cloud) | — | cloud metadata service instance ID |
| Network identity | derived IP | MACs, IP, DNS names — as appropriate |

`machine-id` deserves its reputation: first-boot generated, persisted,
read by every systemd service that needs "this machine" (journal
namespacing, DHCP client-ids, sd_bus machine scoping), and clonable only
by explicit admin action (`systemd-machine-id-setup` on the image).

## Options That Matter

| Option | Effect |
| --- | --- |
| `--help` | Usage text |
| `--version` | Version banner |

No functional options exist; the coreutils manual states the command
"accepts no arguments".

## Usage Patterns

```bash
# Print it (the whole API)
hostid
```

```bash
# See whether the value is IP-derived on this box: compare with hostname -i
hostid; hostname -I
```

```bash
# Demonstrate the container-collision problem
docker run --rm debian:bookworm hostid   # often identical across hosts/containers
```

```bash
# The modern identity you should use instead
cat /etc/machine-id
```

```bash
# Firmware identity, when DMI is available
dmidecode -s system-uuid 2>/dev/null || echo "no DMI (VM/container?)"
```

```bash
# Inventory script fragment: collect all identity tokens, not just one
printf 'hostid=%s machine-id=%s\n' "$(hostid)" "$(cat /etc/machine-id)"
```

```bash
# Confirm hostid is not a security boundary: it is a plain number
python3 - <<'EOF'
import ctypes; print(hex(ctypes.CDLL("libc.so.6").gethostid()))
EOF
```

## Nuances and Gotchas

- **Not an identity, let alone a security token.** It is a 32-bit,
  software-settable value (`sethostid(2)` needs root; nothing authenticates
  it). Using it for licensing or access control on Linux is a defect.
- **Derivation is hostname/IP-dependent:** change the hostname or DHCP
  lease and a never-explicitly-set hostid *changes* — the opposite of what
  an identifier should do.
- **Containers and cloned images collide:** every Debian container that
  resolves its hostname to `127.0.1.1` synthesizes the same value. Fleet
  inventories keyed on hostid merge unrelated machines.
- **Byte-order archaeology:** the IP→hostid derivation involves byte
  swaps in a Sun-compatible layout, so the same IP yields different
  literals on different endiannesses; nobody should be parsing the value,
  which is the point.
- **`gethostid(3)` is a legacy interface:** glibc keeps it for
  compatibility; new code should reach for `sd_id128_get_machine(3)`
  (machine-id) or DMI.
- **Existence is platform-conditional:** the coreutils manual warns that
  hostid is installed only where `gethostid` exists — portable scripts
  must not assume the binary.
- **Zero or garbage values** appear on systems with no resolvable
  hostname; treating the output as "8 stable hex digits" is wrong in
  exactly the environments (fresh installs, containers) where people
  try to use it.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Identifier printed |
| nonzero | `gethostid(3)`/write failure — rare; the call effectively always succeeds |

## Related Commands

- [`arch`](./arch.md) — sibling "report a system fact" command with the same no-options surface
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- `hostnamectl`/`machine-id` — the modern identity stack (systemd; outside this collection)

## Interview Questions

### Q: Where did `hostid` originally come from, and why does the Linux version fail to deliver the same guarantee?

The command and concept come from Sun hardware: Solaris `hostid` read an
NVRAM-stored per-machine identifier, unique by manufacture, used for
licensing and asset tracking. The GNU/Linux command wraps
`gethostid(3)`, which on Linux returns a value that is either explicitly
set (`sethostid(2)`) or synthesized from the hostname's IPv4 address —
software data with no hardware anchor. Same interface, radically weaker
guarantee: the value can collide (containers, clones) or change
(hostname/DHCP edits), so nothing that assumed Sun semantics survives the
port.

### Q: Why is `hostid` useless as a unique identifier in a container fleet?

Three compounding reasons: (1) the derivation depends on the hostname's
IPv4 resolution, and containers overwhelmingly resolve to loopback-style
defaults like 127.0.1.1, producing identical values fleet-wide; (2) the
value is 32-bit, so even honest uniqueness saturates quickly at fleet
scale; (3) it is root-settable software state, so it proves nothing about
provenance. `/etc/machine-id` (128-bit, first-boot generated, image-
clone-aware) or cloud instance IDs are the correct primitives.

### Q: What is the modern replacement, and what properties does it have that hostid lacks?

`/etc/machine-id`, managed by systemd. Properties: 128 bits of entropy
generated at first boot, persisted read-only across reboots, scoped per
installation (cloned images are supposed to reset it with
`systemd-machine-id-setup`), consumed by a broad software ecosystem
(journal, DHCP client-id, sd-bus) rather than being an orphaned legacy
call. For firmware-anchored identity: SMBIOS system UUID via `dmidecode`.
Both are 128-bit and anchored, versus hostid's 32-bit unanchored value.

### Q: A script checks `hostid` as part of a license enforcement scheme ported from Solaris. What is your review verdict?

Reject it. The value is trivially forgeable (`sethostid(2)` as root, or
LD_PRELOAD of `gethostid`), frequently identical across machines, and can
change without any hardware event — so it neither restricts copying nor
stably identifies the licensee. If licensing must run on Linux, key it on
machine-id or DMI UUID *plus* a cryptographic challenge/response, not on a
readable 32-bit integer; and if the port is from Solaris, budget for the
behavioral difference explicitly rather than inheriting it.

### Q: How can you demonstrate, on one machine, that hostid is IP-derived rather than hardware-fixed?

Compare `hostid` before and after changing the resolution of the hostname:
point the hostname at a different IPv4 in `/etc/hosts` (or change the
lease), run `hostid` again, and observe the value change — no hardware
event occurred. On a container host, running `hostid` inside two fresh
Debian containers typically prints the *same* value on two "different
machines", which is the collision demonstration. (Verify against the
glibc behavior on the specific system, since explicitly set IDs won't
move.)

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/hostid.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
