# "localhost means the loopback interface, so it stays on this machine"

## Overview

This page audits the claim that turns "localhost" into a security and
correctness guarantee: because the name maps to the loopback interface,
traffic to localhost never leaves the machine, services reached through it
are private, and a configuration that connects over localhost is
automatically local and safe. The mapping half of this is real and
standardized: RFC 5735 reserves the entire 127.0.0.0/8 block for loopback,
RFC 4291 defines `::1` for IPv6, and RFC 6761 requires resolvers to answer
queries for the name `localhost` locally rather than forwarding them. The
kernel is solid — packets to loopback addresses do not traverse a physical
interface. What the claim deletes is every quantifier that makes the
guarantee usable: *which* loopback address (127.0.0.1 is one of 16.7
million; `::1` is a different family that rejects different listeners),
*whose* machine (loopback is per network namespace, so in a container
"this machine" is the container), *what the name resolves through* (hosts
files and resolver configuration precede any mandate), and the inversion
that privacy is decided by the address the server *binds*, not the address
the client *dials*. This page states the claim fairly and works each
broken precondition with concrete configurations.

## The Claim, Stated Fairly

The strongest common form is: "The database binds to localhost, so it is
only reachable from the machine it runs on; and our service connects to it
via `localhost`, so the traffic never leaves the box." Stated this way,
the claim is not a strawman. It appears in docker-compose files, in
on-call runbooks, in security answers ("the admin interface is on
localhost"), and in the configuration of a million development machines
where it is simply true: the name resolves to loopback, the packets
terminate in the kernel, and no wire is involved.

The kernel deserves its fairness because the standardization is genuine.
RFC 6761 Section 6.3 directs stub resolvers to answer `localhost` queries
from their own knowledge; RFC 5735's reservation means routers do not
forward 127/8; the kernel's loopback device delivers the packets without a
physical hop. Development workflows built on this work every day. The
audit question is which of the claim's four implied guarantees — one
address family, this machine, this name, this privacy — each standard
actually provides.

## Verdict

**Incomplete.** The claim is true in the regime it silently assumes: a
desktop or host-resident process, an IPv4 resolver that answers
`localhost` with 127.0.0.1, a server bound to that same address, and no
network-namespace boundary between client and server. Each deleted
precondition has a common, ordinary violation. The name can resolve to
`::1` while the server listens only on IPv4 — the classic
works-on-my-machine connection refusal. The "machine" is a network
namespace, so inside a container `localhost` reaches only that container.
The hosts file precedes the RFC mandate and can remap or drop the name.
And the privacy inference is inverted: loopback restricts what the
*client* dialed, while exposure is decided by the addresses the *server*
bound — a service bound to `0.0.0.0` that one developer reaches via
localhost is equally reachable at its LAN address by everyone else.

## Why People Believe It

Three forces keep this claim alive. First, it is *usually true*, on the
environment where most engineers form their intuitions: a laptop, where
client, server, and resolver live in one namespace and `/etc/hosts` ships
with the canonical mapping. A rule that holds on every machine a
developer has owned is indistinguishable from a law.

Second, the standards genuinely exist, and quoting one feels like proof.
RFC 6761 does mandate local resolution of `localhost`; RFC 5735 does
reserve 127/8. But each standard governs one layer — the name, the
address block — and the claim stacks four guarantees on two mandates.
The gap between "the address is reserved" and "the service is private"
is exactly the width of the bind-address mistake, and no RFC fills it.

Third, the failure modes are environmental, so they arrive labeled as
someone else's bug. The `::1` refusal looks like a broken service; the
container loopback surprise looks like a broken deployment; the remapped
hosts file looks like a broken VPN tool. Because each incident arrives
attached to a tool, the claim itself — the actual cause — is never
audited.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "localhost is 127.0.0.1" | The name conventionally maps to loopback, which includes all 2^24 - 2 addresses of 127/8 (RFC 5735) and `::1` (RFC 4291); which one the resolver answers is a per-system configuration question |
| "It never leaves the machine" | Packets to loopback addresses terminate in the kernel's loopback device — but "the machine" is a network namespace, and containers make the namespace the operative boundary |
| "The name is guaranteed" | RFC 6761 mandates local resolution of `localhost`, but hosts files and resolver configuration precede and can override the mandate in practice |
| "So the service is private" | Privacy is a property of the *bind* address, not the dial address; a service bound to `0.0.0.0` reached via localhost is equally reachable at every interface address |
| "Loopback means only my processes" | Loopback is a network boundary, not an authentication boundary: every local user and process that can open sockets can reach a loopback listener unless the service authenticates |
| "Binding matters little" | Binding to 127.0.0.1 is the real control; it is also one address of 16.7 million — a listener on 127.0.0.2 is as network-hidden but as host-shared as 127.0.0.1 |

The correct sentence: "`localhost` is a name that standard practice and
RFC 6761 tie to the loopback addresses reserved by RFC 5735 (127/8) and
RFC 4291 (`::1`), and packets to those addresses do not cross a physical
interface. The name chooses no address family, crosses no network
namespace, authenticates no local caller, and constrains nothing about
the other addresses at which the service may also be listening — exposure
is decided by bind addresses and firewalls, never by the address a client
dialed."

## Where It Breaks

**The address-family split, worked end to end.** A service starts with
`--bind 127.0.0.1:8080` on a dual-stack host. The resolver answers
`localhost` with both `127.0.0.1` and `::1`, and the client library tries
the IPv6 answer first (many do, per getaddrinfo ordering). Every connection
is refused, while the identical command with `127.0.0.1` succeeds — the
diagnosis eats an afternoon because the claim says the two are the same.
The inverse bite is quieter: PostgreSQL's host-based authentication file
treats `127.0.0.1` and `::1` as different lines with potentially different
rules, so a migration that flips the driver's resolved address silently
changes which authentication rule applies. Neither failure involves the
network leaving the machine; both involve the claim's equation of one
address with an entire interface — 2^24 - 2 IPv4 addresses plus one IPv6
address that happen to share a name.

**The namespace boundary.** In a container, the loopback device belongs to
the container's network namespace: `localhost:5432` from the application
container reaches the application container, and refuses, because
PostgreSQL runs in another namespace. The claim's "this machine" silently
meant "this network stack", and containerization made the network stack
smaller than the machine. The standard fixes — a shared network namespace
for sidecars, a service name resolving through the platform's DNS — are
all departures from `localhost`, which is why the twelve-factor rule to
attach backing services via configuration exists: the localhost assumption
is exactly the coupling that breaks when the deployment topology changes.

**The name is a name.** RFC 6761 tells stub resolvers what to answer;
`nsswitch.conf` tells glibc to consult `/etc/hosts` first, and the hosts
file is a mutable, managed artifact. A VPN client that rewrites it, a
configuration-management tool that regenerates it without the localhost
line, or a minimal container image that ships without one — each produces
a system where `getaddrinfo("localhost")` fails or returns something
else. The mandate covers the resolver's *own* answer for the name; it
cannot reach into every hosts file, and history offers no shortage of
tools that shipped localhost hijacks as features. Treat the name as
configuration, not as physics.

**The privacy inversion, worked end to end.** A Redis instance starts
with its default bind to all interfaces and no password. A developer on
the host tests it with `redis-cli` pointed at localhost, concludes "it is
only reachable locally", and the security review — reading the same claim
— passes it. A scanner from the adjacent subnet connects to
`10.0.0.5:6379` immediately. Nothing about the localhost *connection* was
false: those packets stayed on the host. The exposure was decided by the
bind address, which the dial address never constrains. The corrected
review question is not "how do we reach it?" but "what addresses is it
bound to, and what authenticates callers?" — and the honest answer often
reveals the second half of the inversion: loopback does not separate
*users*, only networks. On a shared host, any local principal that can
open sockets can reach a loopback listener, which is why services that
fear co-tenants bind Unix domain sockets with filesystem permissions
instead.

**What survives the audit.** The kernel remains valuable: binding a
service to 127.0.0.1 genuinely removes it from the network — it is the
correct default for admin interfaces and development databases, and the
loopback reservations make the addresses useless for spoofing from
outside. The discipline the claim needs is to keep the guarantees on
their layers: bind addresses and firewalls for exposure, namespace design
for "the machine", explicit addresses or pinned hostnames in
infrastructure code, and authentication in front of anything sensitive —
because loopback has never been an authentication boundary.

## Practical Implications

- In infrastructure and application configs, prefer explicit addresses or
  service names over `localhost`, and pin the address family when a
  listener is bound to one (`127.0.0.1` vs `::1` vs both).
- Audit exposure from the server side: enumerate every bind address
  (`0.0.0.0`, `::`, per-interface) and treat "we connect via localhost"
  as zero evidence about reachability.
- In containers and schedulers, never rely on localhost across component
  boundaries; use shared namespaces for sidecars that truly need it and
  platform DNS for everything else.
- Treat `/etc/hosts` as mutable configuration in build and VPN tooling:
  verify that `localhost` resolution survives image minimization and
  agent installation.
- For co-tenant isolation on a shared host, reach for Unix domain sockets
  with filesystem permissions or loopback plus authentication — loopback
  alone separates networks, not principals.

## Interview Questions

### A client connects to `localhost:8080` and gets connection refused, but `127.0.0.1:8080` works. What happened?

The name resolved to an address the listener is not bound to — typically
`::1` on a dual-stack host where the service bound IPv4 only, or a
hosts-file entry pointing elsewhere. `localhost` maps to a set of loopback
addresses across two families, not to one address, and client resolver
ordering decides which is tried first. The fix is pinning the family on
both sides or binding the listener to both.

### Is a service reachable only via localhost therefore private? What is the correct review question?

No. Privacy is decided by the bind address, not the address the client
dialed: a service bound to all interfaces that one user reaches via
localhost is reachable from every interface it bound. The review questions
are "what addresses is it bound to?" and "what authenticates callers?" —
and on multi-tenant hosts, additionally "can other local principals open
sockets?", because loopback is a network boundary, not a user boundary.

### Why does `localhost` fail inside a container when the database runs in a sibling container?

Loopback is per network namespace. The application container's `localhost`
is its own stack, and the database's listener lives in a different
namespace. "This machine" in the claim always meant "this network stack",
and containers made the stack smaller than the machine. The fixes are a
shared network namespace for genuine sidecars, or platform service
discovery for everything else.

### What do RFC 5735, RFC 4291, and RFC 6761 each actually guarantee for `localhost`?

RFC 5735 reserves 127.0.0.0/8 for IPv4 loopback; RFC 4291 defines `::1`
as the IPv6 loopback; RFC 6761 directs resolvers to answer queries for
the name `localhost` locally rather than forwarding them. None of them
choose which address a client uses first, override hosts files, cross
network namespaces, or authenticate callers — each guarantee is
single-layer, and the claim's four guarantees stack on top of all three.

## Key Takeaways

- `localhost` is a name tied to a *set* of loopback addresses — 2^24 - 2
  IPv4 addresses plus `::1` — and which one is used is a resolver and
  binding question, not a constant.
- Loopback is per network namespace: in containers, "the machine" is the
  container, and localhost-based discovery breaks exactly there.
- Exposure follows bind addresses, not dial addresses; "we connect over
  localhost" is not evidence that a service is private.
- Loopback is a network boundary, not an authentication boundary: local
  principals and other namespaces' routing decisions live outside it.
- The RFCs (5735, 4291, 6761) are real and single-layer; the claim fails
  by stacking four guarantees on three address-layer mandates.

## Cross-References

- [Assumptions Hunt: Network & Distributed](../assumptions-hunt/network-distributed.md)
  — the hidden-assumptions sweep for "the network behaves like my laptop",
  of which this claim is the addressing instance.
- [Misconception: "The network is reliable"](./the-network-is-reliable.md)
  — the sibling first-fallacy audit: both claims smooth a layered system
  into one guaranteed hop.
- [Misconception: "Containers are lightweight VMs"](./containers-are-vms.md)
  — the namespace mechanics that make "this machine" smaller than it
  looks, and why the loopback surprise is structural, not a bug.
- [Networks: DNS Resolution](../../networks/dns/resolution.md) — how names
  become addresses through hosts files and resolvers, the machinery the
  claim assumed was fixed.
- [Networks: IPv6](../../networks/tcp-ip/ipv6.md) — the dual-stack
  addressing whose `::1` half produces the classic localhost refusal.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- R. Bush, D. Meyer. *Special-Use IPv4 Addresses*. RFC 5735, January 2010
  — the reservation of 127.0.0.0/8 for IPv4 loopback (registry role later
  carried forward by RFC 6890, cited by title).
  <https://www.rfc-editor.org/rfc/rfc5735.html>
- R. Hinden, S. Deering. *IP Version 6 Addressing Architecture*. RFC 4291,
  February 2006 — Section 2.5.3 defines the IPv6 loopback address `::1`.
  <https://www.rfc-editor.org/rfc/rfc4291.html>
- S. Cheshire, M. Krochmal. *Special-Use Domain Names*. RFC 6761,
  February 2013 — Section 6.3, the `localhost` special-use resolution
  requirements.
  <https://www.rfc-editor.org/rfc/rfc6761.html>
