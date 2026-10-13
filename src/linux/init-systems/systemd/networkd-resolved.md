# systemd-networkd and systemd-resolved

## Overview

`systemd-networkd` is systemd's configuration-driven network manager: it
reads declarative files describing links, virtual devices, and addressing,
then programs the kernel (addresses, routes, bridges, bonds, VLANs,
WireGuard peers) and keeps that state reconciled across reboots and
re-plugs. `systemd-resolved` is its companion *stub resolver*: a local DNS
daemon fronting glibc that adds caching, per-link upstream selection,
split-DNS, DNSSEC, DNS-over-TLS, and LLMNR/mDNS.

The pairing is deliberately minimalist. No GUI, no per-user config, no
roaming applets — configuration is text files under
`/etc/systemd/network`, state is visible with `networkctl` and
`resolvectl`, and every feature maps one-to-one onto a man page. That
makes the pair the default for servers, containers, embedded images, and
anywhere reproducibility beats interactivity, while NetworkManager keeps
the desktop. Distributions differ: Debian and Arch ship both, Fedora
uses NetworkManager on workstations, and RHEL standardizes on
NetworkManager with keyfiles.

This page covers the three configuration file kinds, complete examples
for common topologies, the `network-online.target` gate and its classic
boot-hang failure mode, and resolved's architecture from the stub
addresses down to the `nsswitch.conf` line that makes it work.

## Positioning: When to Choose networkd

### The NetworkManager comparison

| Aspect | systemd-networkd | NetworkManager |
|---|---|---|
| Audience | servers, containers, embedded, appliances | desktops, laptops, interactive users |
| Config | `.link`/`.netdev`/`.network` text files | keyfiles, dconf, GUI applets |
| Wifi/VPN | basic (wpa_supplicant handoff, WireGuard native) | rich GUI roaming, VPN plugins |
| GUI | none | full (GNOME/KDE applets) |
| Hooks | systemd units on link changes | dispatcher scripts per state change |
| Dependencies | none beyond systemd | wpa_supplicant, agent stack, more D-Bus |
| Boot integration | native units, `network-online.target` | NM service + dispatcher |

Rule of thumb: if a human switches Wifi and VPNs from an applet,
NetworkManager wins. If the set of networks is known in advance — bonded
server NICs, container bridges, one-uplink appliances — networkd's files
are small, reviewable in git, and identical across a fleet. Both can
coexist (NetworkManager even has a backend to manage interfaces *via*
networkd), but one interface has exactly one manager; the other reports
it as "unmanaged".

## Configuration File Kinds

networkd reads three file types, applied at different layers:

| Suffix | Layer | Purpose |
|---|---|---|
| `.link` | udev (`net_setup_link` builtin) | naming, MTU, MAC, offloads — runs at uevent time |
| `.netdev` | networkd | creates virtual devices: bridge, bond, vlan, macvlan, veth, dummy, tun/tap, wireguard, vxlan |
| `.network` | networkd | per-link addressing, routes, DNS, domains, DHCP client/server |

Files live in `/etc/systemd/network` (administrator), `/run/systemd/network`
(runtime), and `/usr/lib/systemd/network` (packages), searched in that
order; within a directory files sort by filename. For `.network` files
the **first file whose `[Match]` section matches a link configures it** —
later matches are ignored for that link (`.netdev` and `.link` files are
matched by name, not `[Match]`). Numeric prefixes are load-bearing:
`10-eth0.network` beats `20-main.network`, and shipped defaults use high
numbers (`80-container-host0.network`, `99-default.link`) so admin files
win.

### [Match] keys

| Key | Matches |
|---|---|
| `Name=` | interface name, with shell globs (`en*`, `veth*`) |
| `MACAddress=` | current MAC (`PermanentMACAddress=` for hardware MAC) |
| `Path=` | udev hardware path (`pci-0000:00:03.0`) |
| `Driver=` | kernel driver (`virtio_net`, `e1000`) |
| `Type=` | udev devtype (`ethernet`, `wlan`, `bridge`) |
| `Host=` | machine hostname, glob-capable |
| `Virtualization=` | `yes`/`no` — inside a VM or container |
| `KernelCommandLine=` / `KernelVersion=` | boot-time conditions |

The idiomatic server pattern is one file per *role*, matching on
something stable (`Driver=`, `Virtualization=`) instead of names.

## Complete Configuration Examples

### DHCP client

```ini
# /etc/systemd/network/20-wired.network
[Match]
Name=enp3s0

[Network]
DHCP=yes
```

### Static IPv4 and IPv6

```ini
# /etc/systemd/network/20-static.network
[Match]
Name=enp3s0

[Network]
Address=192.0.2.10/24
Gateway=192.0.2.1
DNS=192.0.2.53
Address=2001:db8:10::10/64
Gateway=2001:db8:10::1
IPv6AcceptRA=no
```

### Bridge with an enslaved port

```ini
# /etc/systemd/network/10-bridge.netdev
[NetDev]
Name=br0
Kind=bridge

[Bridge]
STP=yes

# /etc/systemd/network/20-bridge.network
[Match]
Name=br0

[Network]
DHCP=yes

# /etc/systemd/network/30-port.network  (physical NIC joins the bridge)
[Match]
Name=enp3s0

[Network]
Bridge=br0
```

The port carries no address; all addressing lives on `br0`. Prefixes
matter for the `.network` files — the port's file must sort after the
bridge's if both could match.

### VLAN

```ini
# /etc/systemd/network/20-vlan100.netdev
[NetDev]
Name=vlan100
Kind=vlan

[VLAN]
Id=100

# /etc/systemd/network/21-vlan100.network
[Match]
Name=vlan100

[Network]
Address=10.100.0.2/24
```

The parent must also allow the tag: `VLAN=vlan100` in the parent's
`.network` file creates the kernel binding (or `[BridgeVLAN]` on a
bridge port).

### WireGuard netdev sketch

```ini
# /etc/systemd/network/40-wg0.netdev
[NetDev]
Name=wg0
Kind=wireguard

[WireGuard]
PrivateKeyFile=/etc/wireguard/private.key
ListenPort=51820

[WireGuardPeer]
PublicKey=...base64...
AllowedIPs=10.200.0.0/24
Endpoint=203.0.113.7:51820

# /etc/systemd/network/41-wg0.network
[Match]
Name=wg0

[Network]
Address=10.200.0.2/24
```

`PrivateKeyFile=` keeps the secret out of the config; networkd creates
the device and applies peer roams natively, the advantage over
`wg-quick@` shell scripts.

### A built-in DHCP server

```ini
# /etc/systemd/network/20-ap.network
[Match]
Name=wlan-ap0

[Network]
Address=192.168.77.1/24
DHCPServer=yes
IPMasquerade=ipv4
```

networkd's DHCP server suits appliances and VM bridges; `IPMasquerade=`
installs the NAT rules that used to need hand-written iptables.

## Key [Network] and [DHCP] Directives

| Directive | Effect |
|---|---|
| `DHCP=` | which protocol to run: `yes`, `ipv4`, `ipv6`, `no` |
| `Address=` / `Gateway=` / `DNS=` | static addressing and resolvers |
| `Domains=` | search domains; a `~` prefix makes it a *routing* domain for split-DNS |
| `NTP=` | NTP servers handed to `systemd-timesyncd` |
| `IPForward=` | per-link `ipv4`/`ipv6` forwarding (writes sysctl, survives interface churn) |
| `IPv6AcceptRA=` | accept router advertisements (default: auto — yes unless static config exists) |
| `KeepConfiguration=` | keep addresses/DNS across restarts or renewals (`static`, `dhcp`, `on-stop`) |
| `LinkLocalAddressing=` | `ipv4`/`ipv6`/`no` — 169.254 autoconf, often disabled on bridge ports |
| `RequiredForOnline=` | operational state needed for `network-online.target` (`yes` = `routable`) |

Inside `[DHCP]`, the most-touched knobs are `UseDNS=` (accept resolvers
from the lease — required for split-DNS to see DHCP servers) and
`UseNTP=`. `DNS=`/`Domains=` set in `.network` files flow directly into
resolved as per-link configuration — the two daemons meet exactly here.

## wait-online and network-online.target

`systemd-networkd-wait-online.service` is pulled in by
`network-online.target` and blocks until every interface with
`RequiredForOnline=yes` reaches its required operational state. Services
that genuinely need working networking order themselves
`After=network-online.target` — it is a *gate*, not a dependency to
sprinkle everywhere.

The classic footgun: a machine sits two minutes at boot before anything
network-related starts. Cause: some interface has no `.network` file (a
NIC renamed by predictable naming, an extra bridge port), so wait-online
times out on it. Fixes, in order of preference:

1. Give every interface a matching `.network` file — even an empty
   `[Network]` section — so networkd manages all of them.
2. Set `RequiredForOnline=no` on links that never carry "online"
   semantics (bridge ports, container veth).
3. Exclude specific links via a service drop-in: `--ignore=enp4s0f1` or
   `--any` (succeed when *any* link is online).
4. Mask `systemd-networkd-wait-online.service` when nothing orders
   against `network-online.target` — last resort.

## systemd-resolved

### Two local listeners: 127.0.0.53 and 127.0.0.54

resolved binds `127.0.0.53:53` — the *stub* implementing all local
logic: caching, split-DNS routing, DNSSEC, LLMNR/mDNS, and the
D-Bus/varlink APIs. Recent releases also bind `127.0.0.54:53`, a
*transparent proxy* with none of that logic: it forwards query bytes to
the selected upstream and relays the reply, for clients that must bypass
the stub (own cache or DNSSEC stack, protocol edge cases). It is not a
general-purpose resolver.

### The nsswitch.conf hosts line, decoded

```text
hosts: files mymachines resolve [!UNAVAIL=return] dns myhostname
```

| Module | Role |
|---|---|
| `files` | `/etc/hosts` entries |
| `mymachines` (`nss-mymachines`) | names of local containers/VMs via `systemd-machined` |
| `resolve` (`nss-resolve`) | ask resolved over varlink — DNS, LLMNR, mDNS happen here |
| `[!UNAVAIL=return]` | if the previous module returned anything except `UNAVAIL`, stop and return |
| `dns` | classic glibc resolver reading `/etc/resolv.conf` — fallback when resolved is down |
| `myhostname` (`nss-myhostname`) | local hostname and `.localhost` without touching the network |

`UNAVAIL` means "service not available": with resolved alive, any answer
it gives — including NXDOMAIN — is final, and glibc never falls through
to the plain `dns` module; with resolved stopped, lookups proceed to the
`dns` fallback. A graceful-degradation switch, not decoration.

### /etc/resolv.conf and the stub

The package installs `/etc/resolv.conf` as a symlink to
`../run/systemd/resolve/stub-resolv.conf` containing
`nameserver 127.0.0.53`. Alternatives: a symlink/copy of
`/run/systemd/resolve/resolv.conf` (the *real* upstream nameservers, for
software that must bypass the stub — glibc skips resolved but the NSS
`resolve` module still works), or an admin static file (resolved is out
of the resolution path entirely). Deleting resolved without restoring a
real `resolv.conf` leaves a dangling symlink into `/run` — the "DNS
broken after uninstall" ticket in its purest form.

### resolvectl operation

```bash
resolvectl status                          # per-link DNS config, features, cache stats
resolvectl query example.com               # resolve through the full policy stack
resolvectl flush-caches                    # drop cache after DNS changes
resolvectl statistics                      # cache/transaction counters
resolvectl dns tun0 10.8.0.1               # set per-link DNS servers by hand
resolvectl domain tun0 ~corp.example       # set a routing domain for that link
```

`resolvectl status` is the first command for any DNS debugging here: it
shows which links carry which servers and domains — the state split-DNS
routes against.

### Per-link DNS and split-DNS

Each link carries its own DNS servers and *routing domains* (domains
with the `~` prefix). A name inside a routing domain goes only to links
claiming it; everything else goes to links acting as default resolvers:

```ini
DNS=10.8.0.1
Domains=~corp.example
```

Lookups for `git.corp.example` go to 10.8.0.1, `debian.org` to the home
router — simultaneously, with separate caches per scope. Surprises:
`dig @127.0.0.53 git.corp.example` exercises the same routing (dig
pointed elsewhere does not), and two links claiming the same routing
domain race each other.

### DNSSEC, DNSOverTLS, LLMNR and mDNS

`DNSSEC=` takes `yes`, `allow-downgrade` (validate only signed zones —
the upstream default), and `no`. Symptom of aggressive DNSSEC on
networks with broken middleboxes or a skewed clock: sudden `SERVFAIL`s
for domains that resolve fine elsewhere; check `resolvectl query` and
the resolved journal before flipping to `allow-downgrade`. `DNSOverTLS=`
is `no`/`opportunistic`/`yes`. `LLMNR=` and `MulticastDNS=` enable
local-segment name resolution without unicast DNS (`.local` for mDNS).
resolved caches positive and negative answers per scope.

## /etc/resolv.conf States

| State | Symptom when wrong | Recovery |
|---|---|---|
| symlink → `stub-resolv.conf` (correct default) | — | — |
| dangling symlink after removing resolved | every lookup times out on 127.0.0.53 | write a static file with real resolvers |
| static file with upstreams | per-link DNS and split-DNS silently off | accept, or restore the stub symlink |
| points at 127.0.0.53, resolved stopped | fast failures for all names | `systemctl start systemd-resolved` or swap the file |
| container with host's resolv.conf copied | 127.0.0.53 unreachable across network namespaces | give containers real resolvers (`--dns`, LAN resolver) |

The last row deserves emphasis: Docker copies the host's resolv.conf
into containers, filters localhost entries, and falls back to defaults —
so a resolved host seems fine until a container runs `apt-get update`.
The systemic fix is real resolvers inside containers, never loopback
addresses.

## Debugging Playbook

- **`resolvectl status` first** — confirm which link owns which servers
  and routing domains; half of "DNS is broken" is "the VPN link lost
  its Domains=".
- **Compare resolvers directly.** `dig @127.0.0.53 name` (through
  resolved policy) vs `dig @upstream name` (bypass) — a difference
  isolates the stub logic (split-DNS, DNSSEC, cache).
- **DNSSEC SERVFAILs.** `resolvectl query` prints validation state; the
  journal shows the specific DNSKEY/RRSIG failure. A clock far off
  breaks validation — check time sync before blaming zones.
- **networkd side.** `networkctl status <iface>` shows operational
  state, addressing, and which `.network` file matched — "why is my
  interface unconfigured" is usually "no file matched, the name
  changed".
- **Docker + stub** — see the states table; loopback never crosses
  network namespaces.

## When Not to Use resolved

Environments running a full resolver stack often disable resolved to
avoid two caches and two configurations: Kubernetes nodes, hosts with
unbound/dnsmasq for ad-blocking or PXE, setups where `resolv.conf` is
script-generated. networkd is independent of resolved — networkd plus a
classic static `resolv.conf` is the standard arrangement on minimal
servers. Conversely, resolved works fine under NetworkManager, which
configures per-link DNS through D-Bus.

## Interview Questions

### Q: What is the difference between 127.0.0.53 and 127.0.0.54?

127.0.0.53 is the DNS *stub*: full local logic — caching, split-DNS
routing, DNSSEC, LLMNR/mDNS, NSS integration. 127.0.0.54 is a
*transparent proxy*: it forwards queries verbatim to the selected
upstream and relays responses, bypassing stub logic for clients whose
behavior would clash with it (own DNSSEC stack, protocol quirks) and
for debugging what a raw upstream answers. Pointing resolv.conf at .54
in general use gives up every feature that motivated resolved.

### Q: Why does the hosts: nsswitch line contain [!UNAVAIL=return]?

It makes the `resolve` module authoritative *when running* and
transparent *when not*. Any result other than `UNAVAIL` — including
NXDOMAIN and DNS failures — ends the lookup, so glibc never re-queries
the same upstreams through the legacy `dns` module on a healthy system.
`UNAVAIL` (resolved not running) falls through to `dns`, so a system
degrades to classic resolution without manual intervention. Without the
action list, lookups run twice when healthy and behave
nondeterministically when broken.

### Q: A server hangs for two minutes at boot before the network starts. Diagnose.

`systemctl status systemd-networkd-wait-online.service` — if it hit its
timeout, some interface never reached the required operational state.
The usual cause: an interface present on the machine has no matching
`.network` file (predictable renaming changed a name), so it is
unmanaged and wait-online cannot consider it ready. Fix by matching all
interfaces, setting `RequiredForOnline=no` on non-uplinks, or using
`--ignore=`/`--any` in a service drop-in. Masking the unit is the last
resort — anything ordering after `network-online.target` then starts
unsynchronized.

### Q: systemd-resolved stops. What breaks and what keeps working?

Everything pointed at 127.0.0.53 loses DNS immediately. What keeps
working: anything answered from `/etc/hosts` (`files`), container names
via `nss-mymachines` (machined, not resolved), and the local hostname
via `nss-myhostname`. The `dns` NSS fallback technically exists, but on
a stock setup it reads the same resolv.conf — which lists the stub — so
it only helps when resolv.conf was switched to the static variant. Net
effect: on a default system, DNS dies with resolved; the fallback saves
only hosts configured with real upstream servers.

### Q: How do you make a link contribute addresses but no DNS to resolved?

Set `UseDNS=no` in that link's `[DHCP]` section (and in
`[IPv6AcceptRA]` for RA-provided resolvers): networkd still configures
addresses and routes, but the lease's resolvers are not exported to
resolved, so the link contributes no upstream. Combine with explicit
`DNS=` on another link or in `resolved.conf` — the fix when a captive
router advertising itself as DNS would otherwise win the split-DNS
default.

## References

- https://www.freedesktop.org/software/systemd/man/latest/systemd-networkd.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.network.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.netdev.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd-resolved.html
- https://www.freedesktop.org/software/systemd/man/latest/resolved.conf.html
- https://www.freedesktop.org/software/systemd/man/latest/nss-resolve.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd-networkd-wait-online.service.html
- https://manpages.debian.org/bookworm/systemd/systemd.network.5.en.html
- https://manpages.debian.org/bookworm/systemd/systemd.netdev.5.en.html
- https://manpages.debian.org/bookworm/systemd/systemd-networkd-wait-online.8.en.html
- https://manpages.debian.org/bookworm/systemd-resolved/systemd-resolved.8.en.html
- https://manpages.debian.org/bookworm/systemd-resolved/resolved.conf.5.en.html
- https://manpages.debian.org/bookworm/libnss-resolve/nss-resolve.8.en.html

## Cross-References

- [udevd.md](./udevd.md) — `.link` files run inside udev and produce predictable interface names.
- [boot-process.md](./boot-process.md) — where `network-online.target` ordering applies during boot.
- [dependency-management.md](./dependency-management.md) — wiring services to `network-online.target` and friends.
- [journald.md](./journald.md) — networkd and resolved log through the journal; debugging relies on it.
- [comparison.md](../comparison.md) — network management across init families.
- [README.md](../README.md) — init-systems section hub.
