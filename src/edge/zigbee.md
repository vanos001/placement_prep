# Zigbee: The 802.15.4 Mesh That Runs Your Lights

Zigbee is why "smart bulb" became a product category: a self-organizing, low-power mesh that
has shipped in hundreds of millions of devices since 2004, and a great interview subject
because it forces stack-wide reasoning -- radio physics, mesh routing, key management,
application modeling -- on a network that is deliberately *not* the internet. Thread shares
Zigbee's radio but replaces everything above the MAC with IP; differences are called out
throughout and summarized in the [Thread and Matter deep dive](./thread-matter.md). The BLE
counterpart is in the [BLE deep dive](./ble-deep.md); gateway protocols are in
[iot-protocols-deep](./iot-protocols-deep.md).

## 1. The Radio: What Zigbee Borrows From 802.15.4

Zigbee sits on IEEE 802.15.4's PHY and MAC. The 2.4 GHz PHY uses O-QPSK with half-sine pulse
shaping (effectively MSK) plus direct-sequence spread spectrum: each 4-bit symbol maps to one
of 16 near-orthogonal 32-chip PN sequences at 2.0 Mchip/s, giving 62.5 ksym/s x 4 bits =
250 kb/s net and about 9 dB of processing gain. Frames are tiny -- 127 bytes at the PHY,
roughly 80 usable above the MAC header -- and the 802.15.4 sensitivity floor is -85 dBm at
2.4 GHz, though vendor radios typically reach the mid -90s dBm, which lets milliwatt
transmitters hold 10-30 m indoor hops.

| Band (region)    | Channels | Center frequency    | Modulation  | Data rate (original PHY) |
|------------------|----------|---------------------|-------------|--------------------------|
| 868 MHz (EU)     | 0        | 868.3 MHz           | BPSK DSSS   | 20 kb/s                  |
| 915 MHz (NA)     | 1-10     | 906 + 2*(k-1) MHz   | BPSK DSSS   | 40 kb/s                  |
| 2.4 GHz (global) | 11-26    | 2405 + 5*(k-11) MHz | O-QPSK DSSS | 250 kb/s                 |

Channel choice is the classic coexistence answer: channel 26 (2480 MHz) escapes Wi-Fi channel
11; 15, 20, and 25 dodge other common plans. Against Wi-Fi's OFDM, Zigbee trades three orders
of magnitude of throughput for a 5 MHz footprint, ~9 dB spreading gain, mW-class TX power, and
years of battery life -- and it forwards at the NWK layer instead of relying on one access
point (BLE's mesh is a managed flood above the radio). The MAC runs CSMA/CA with random
backoff and immediate MAC ACKs; most Zigbee networks are **non-beacon**, so routers listen
always (mains power) while battery devices poll their parent on their own schedule.

## 2. Device Roles, Formation, and the Trust Center

| Role        | Sleeps? | Forwards? | Powered by | Defining behavior                          |
|-------------|---------|-----------|------------|--------------------------------------------|
| Coordinator | no      | yes       | mains      | Exactly one; forms network; usually the TC |
| Router      | no      | yes       | mains      | Joins/extends mesh, admits children        |
| End device  | yes     | never     | battery    | One parent only; all traffic via parent    |

The coordinator scans channels, picks the quietest, sets the PAN ID; routers join a parent and
receive a short address. An end device does not route and holds one parent: if that parent
dies, its traffic stops until it times out and re-homes (some vendor devices famously never
do, and sit orphaned until re-paired).

Do not conflate the coordinator with the **Trust Center (TC)**. The TC is a *security* role,
nearly always on the coordinator in Zigbee 3.0: it authenticates joiners and distributes keys.
Zigbee PRO also defines **distributed security networks** with no TC at all -- routers admit
devices directly, as in some Touchlink lighting nets -- the standard "centralized vs
distributed security" interview question.

## 3. The Stack and Its Two Addresses

```text
+--------------------------------------------------------------+
|  ZCL profiles: clusters / attributes on endpoints 1-240      |
+--------------------------------------------------------------+
|  APS: endpoint demux, binding, groups, APS acks, key mgmt    |
+--------+-----------------------------------------------------+
|  ZDO   |  discovery, joining, network management (ep 0)      |
+--------+-----------------------------------------------------+
|  NWK:  AODV-like / tree / many-to-one routing, hop crypto,   |
|        16-bit addresses, broadcast radius, frame counters    |
+--------------------------------------------------------------+
|  802.15.4 MAC: CSMA/CA, acks | PHY: O-QPSK DSSS, 250 kb/s    |
+--------------------------------------------------------------+
```

The data path is textbook primitives: an application calls **APSDE-DATA.request** with an
endpoint, profile, cluster, and destination (short address + endpoint, or a group); APS frames
it and hands it to **NLDE-DATA.request** with a hop radius and optional source route. Each
layer can acknowledge -- MAC per hop, NWK retries per mesh hop, APS end-to-end with duplicate
rejection when asked. Every device carries a permanent 64-bit IEEE (EUI-64) address plus a
16-bit **short address** used on the wire. The coordinator is always 0x0000; 0xFFFE means "no
short address yet"; broadcasts are 0xFFFF (all), 0xFFFD (non-sleepy), 0xFFFC (routers), each
bounded by the frame's radius field. The short address is *topological* -- assigned by parent
or TC, changeable after a rejoin -- so applications address by IEEE address and let the stack
resolve. That instability is exactly what Thread fixed with IPv6
([Thread and Matter deep dive](./thread-matter.md)).

## 4. Endpoints, Clusters, Attributes: ZCL on the Wire

APS demultiplexes to **endpoints** 1-240; endpoint 0 is the ZDO (device/service discovery),
endpoint 240 (0xF0) carries Green Power (Section 7), 241-254 are reserved, 255 is
broadcast-to-all-endpoints. Each endpoint hosts **clusters**; each cluster owns **attributes**
(state) and **commands**. The Zigbee Cluster Library supplies the global commands -- Read
Attributes (0x00), Write Attributes (0x02), Configure Reporting (0x06), Report Attributes
(0x0A) -- plus per-cluster commands.

A light's On/Off cluster is 0x0006, its boolean attribute 0x0000 is the state, and its
cluster-specific commands are Off = 0x00, On = 0x01, Toggle = 0x02. A hub "turns on" a bulb by
sending an APS frame to the bulb's endpoint with cluster 0x0006 and payload byte 0x01 -- often
groupcast to a "room" group. Two APS features make big networks tractable:

- **Binding**: a static source (endpoint, cluster) to destination (address + endpoint, or
  group) map in a binding table, so a sensor can drive a bulb peer-to-peer without the hub.
- **Reporting**: the hub sends Configure Reporting (min interval, max interval, reportable
  change); the device then pushes attribute reports itself -- heartbeat plus delta -- which is
  how battery sensors sleep for a year.

## 5. Security: Network Keys, Link Keys, Install Codes

Every NWK frame is encrypted with **AES-128-CCM\*** -- note the star: 802.15.4 specifies
CCM\*, a CCM variant that also permits authentication-only and encryption-only modes. Two key
families coexist:

| Key                   | Scope             | Layer | Delivered how                                  |
|-----------------------|-------------------|-------|------------------------------------------------|
| Network key           | entire network    | NWK   | Transported by TC under the TC link key        |
| Trust Center link key | device <-> TC     | APS   | Install code (Zigbee 3.0) or legacy well-known |
| Pairwise link keys    | device <-> device | APS   | Optional, per application or key establishment |

Every frame carries the sender's **frame counter** plus the key sequence number; receivers
reject counters that move backwards (replay protection), and the TC rotates the network key
before any node's counter exhausts. The legacy footgun: devices long joined using the
spec-published well-known TC link key, ASCII "ZigBeeAlliance09", so anyone with the spec could
decrypt network-key transport. **Zigbee 3.0 answered with install codes**: an out-of-band
secret of 6, 8, 12, or 16 bytes plus a CRC-16, printed on box or QR, hashed on both sides with
a Matyas-Meyer-Oseas (AES-based) hash into the preconfigured TC link key that then protects
the network-key transport. Certified Zigbee 3.0 devices must support install-code joining; the
well-known key survives only for backward compatibility, and Zigbee PRO 2023 tightened join
authentication further. Practical pitfall: counters must survive reboots -- a device that
loses counter state after a battery swap sends "stale" counters and is silently dropped until
it rejoins.

## 6. Mesh Routing: AODV-Like Discovery, Tree Fallback, Many-to-One

Zigbee NWK routing is stripped-down AODV (Ad hoc On-demand Distance Vector): a source with no
route floods a Route Request (RREQ); each router records the reverse path; the destination, or
an intermediate router that already holds a route, unicasts a Route Reply (RREP) back, and
each hop installs the forward route. Discovery is bidirectional-cost-aware -- path costs come
from link quality (LQI), and discovery uses links in one direction to find a route in the
opposite direction, because low-power links are asymmetric. Three companions matter:

- **Tree routing**: fallback that walks the hierarchical address tree by address arithmetic
  when discovery is disabled or fails. Zero discovery traffic, but it breaks whenever the real
  topology deviates from the address tree -- a favorite trap question.
- **Route repair**: on an acknowledged-unicast timeout, the upstream router attempts local
  repair before dropping the packet; the demo in Section 9 models exactly this event.
- **Many-to-one routing**: nearly all traffic flows to the hub, so the hub (a "concentrator")
  periodically broadcasts a many-to-one route request; routers record a reverse route to it,
  and it accumulates **source routes** from route-record messages carried by real traffic.
  Low-RAM concentrators keep state only for recent talkers. This periodic refresh is why large
  commercial Zigbee nets stay stable.

Versus Thread: Thread routes IPv6 datagrams to per-node RLOCs with leader-elected topology --
no tree routing, no 16-bit source-route lists, no hub-centric concentrator. Same radio,
different scaling physics.

## 7. Green Power: Switches With No Battery

Zigbee Green Power (GP) defines **GPDs** (Green Power Devices) for energy-harvesting,
batteryless products -- kinetic switches powered by the press that sends the frame. A GPD
speaks a compact Green Power Data Frame (GPDF), not the full stack, and is identified by a
32-bit source ID instead of short addresses. Every router acts as a **GP proxy**, flooding the
GPDF a bounded number of hops toward a **GP sink** (usually the hub), which translates it into
normal ZCL traffic; security uses slimmed-down GP keys and MICs, with limited bidirectional
operation for feedback. The hub represents GPDs locally at endpoint 240. CSA shipped Green
Power 1.1.2 in March 2024; GP remains the reference answer to "how can a batteryless switch
control a mesh?"

## 8. Bridging to Matter: The Reality Check

Bridging is real and shipped: a bridge joins a Matter fabric and exposes each Zigbee device as
a Matter endpoint, translating ZCL clusters to Matter clusters. The mapping is natural --
Matter's cluster library descends from the same CSA lineage -- but the seams show: the device
is one bridge reboot from unreachable; there is no multi-admin below the bridge (one Zigbee
network, one TC, one ecosystem's keys); every bulb now carries a short address, an IEEE
address, and a Matter node ID; group and OTA semantics do not compose across the seam.
Bridging is a migration path, not a merger -- which is why CSA built Thread-based Matter
rather than Matter-over-Zigbee.

## 9. Model Demo: Route Discovery and Repair Under Failure

The script below is a **model**, not a bit-accurate simulator: unit-disk links, BFS as a
stand-in for AODV's min-hop discovery, one failing transit router (the one carrying the most
discovered paths), 20 ms/hop forward latency, and a one-shot 150 ms discovery penalty charged
to rerouted sources. "rerouted" counts sources that kept connectivity but had to re-discover a
different path; "unreach" counts sources with no route after the failure.

```python
#!/usr/bin/env python3
"""MODEL: AODV-style route discovery + repair in a Zigbee mesh.
Unit-disk links, BFS = min-hop discovery, one dead transit router."""
import math, random

AREA, HOP_MS, DISCOVERY_MS = 40.0, 20.0, 150.0  # meters, ms/hop, discovery ms

def build(n, radius, frac, rng):
    pts = [(rng.uniform(0, AREA), rng.uniform(0, AREA)) for _ in range(n)]
    pts[0] = (AREA / 2, AREA / 2)                # node 0 = coordinator, centered
    kind = ["router" if rng.random() < frac else "end" for _ in range(n)]
    kind[0] = "router"
    routers = [i for i in range(n) if kind[i] == "router"]
    adj = {r: set() for r in routers}            # router forwarding graph
    for a in routers:
        for b in routers:
            if a < b and math.dist(pts[a], pts[b]) <= radius:
                adj[a].add(b); adj[b].add(a)
    parent = {}                                  # end device -> single parent
    for i in range(n):
        if kind[i] == "end":
            c = [r for r in routers if math.dist(pts[i], pts[r]) <= radius]
            if c:
                parent[i] = min(c, key=lambda r: math.dist(pts[i], pts[r]))
    return pts, kind, routers, adj, parent

def route(net, src):                             # BFS min-hop route to node 0
    if src == 0:
        return [0]
    prev, q = {src: None}, [src]
    for n in q:
        for m in sorted(net[3][n]):
            if m not in prev:
                prev[m] = n
                if m == 0:
                    path = [m]
                    while prev[path[-1]] is not None:
                        path.append(prev[path[-1]])
                    return path[::-1]
                q.append(m)
    return None

def measure(net):                                # full path per live source
    _, kind, routers, _, parent = net
    paths, lost = {}, []
    for i in range(1, len(kind)):
        if kind[i] == "router" and i not in routers:
            lost.append(i); continue             # failed router
        if kind[i] == "end" and i not in parent:
            lost.append(i); continue             # orphaned end device
        p = route(net, parent.get(i) if kind[i] == "end" else i)
        if p is None:
            lost.append(i)
        else:
            paths[i] = (i,) + tuple(p)
    return paths, lost

if __name__ == "__main__":
    print("MODEL: unit-disk graph, BFS min-hop discovery, %g ms/hop, %g ms discovery"
          "\n          ----- before failure ----- | ------ after repair ------    routes"
          "\ndensity nodes radius routers  hops    ms     hops    ms     rerouted unreach"
          % (HOP_MS, DISCOVERY_MS))
    for label, radius in (("sparse", 7.0), ("medium", 9.0), ("dense", 11.0)):
        net = build(80, radius, 0.50, random.Random(42))
        before, _ = measure(net)
        load = {}                                # transit-router load
        for p in before.values():
            for x in p[1:-1]:
                load[x] = load.get(x, 0) + 1
        dead = max(load, key=load.get)           # fail the busiest transit router
        pts, kind, routers, adj, parent = net
        routers = [r for r in routers if r != dead]
        adj = {r: {n for n in ns if n != dead} for r, ns in adj.items() if r != dead}
        parent = {i: p for i, p in parent.items() if p != dead}
        for i in [i for i in range(len(kind)) if kind[i] == "end" and i not in parent]:
            c = [r for r in routers if math.dist(pts[i], pts[r]) <= radius]
            if c:                                # re-attach to nearest router
                parent[i] = min(c, key=lambda r: math.dist(pts[i], pts[r]))
        after, lost = measure((pts, kind, routers, adj, parent))
        redisc = sum(1 for i in after if i in before and after[i] != before[i])
        hb = sum(len(p) - 1 for p in before.values()) / len(before)
        ha = sum(len(p) - 1 for p in after.values()) / len(after)
        ma = sum((len(p) - 1) * HOP_MS + (DISCOVERY_MS if i not in before
                                          or before[i] != p else 0.0)
                 for i, p in after.items()) / len(after)
        print("%-7s %4d %4.0fm  %6d  %5.2f %6.1f   %5.2f %6.1f     %9d %4d"
              % (label, 80, radius, len(routers), hb, hb * HOP_MS, ha, ma,
                 redisc, len(lost)))
```

Real run of the script above (Python 3.11, fixed seed, byte-identical across re-runs):

```text
MODEL: unit-disk graph, BFS min-hop discovery, 20 ms/hop, 150 ms discovery
          ----- before failure ----- | ------ after repair ------    routes
density nodes radius routers  hops    ms     hops    ms     rerouted unreach
sparse    80    7m      40   5.34  106.9    5.75  115.0             0   51
medium    80    9m      40   3.82   76.4    4.24  163.0            37    8
dense     80   11m      40   3.37   67.4    3.44  114.8            23    4
```

Read it the way an interviewer would: the sparse mesh has the *longest* paths (5.34 hops) and
its busiest transit router is a cut vertex -- losing it partitions the network (unreach 51),
and no AODV repair can help where no alternate links exist. The dense mesh has the shortest
paths and enough redundancy that repair reroutes 23 sources with barely a hop-count change.
The medium row shows the repair cost: after-ms includes the one-time 150 ms discovery penalty
averaged over rerouted routes; steady state would return to roughly hops x 20 ms.

## 10. Interview Drill

- **Why O-QPSK DSSS instead of Wi-Fi-style OFDM?** Milliwatt radios, ~9 dB spreading gain,
  5 MHz channels at low duty cycle; throughput was never the goal.
- **Coordinator vs Trust Center?** Formation role vs security role; distributed security
  networks have no TC at all.
- **A bulb joins with the well-known key: exposure?** "ZigBeeAlliance09" is public, so a
  passive attacker decrypts network-key transport and follows all traffic. Fix: install codes
  hashed (MMO) into per-device TC link keys, mandatory in Zigbee 3.0.
- **Why does a bulb vanish after a hub update?** Short addresses are topological and
  ephemeral; cached bindings/groups point at nothing until re-resolved by IEEE address.
- **Zigbee routing vs Thread routing?** AODV-like discovery + tree fallback + many-to-one
  source routing to a hub over 16-bit addresses, versus IPv6 over RLOCs with leader-elected
  topology.
- **How does a batteryless switch reach the mesh?** Green Power: GPDF flooded by GP proxies
  to the GP sink, 32-bit source ID, no network address, GP keys, optional bidirectional reply.
- **What breaks in a Zigbee-to-Matter bridge?** Single translation point, no multi-admin
  below the bridge, unmapped group/OTA semantics.

## References

1. Zigbee2MQTT docs, "Zigbee network" -- device types, single-parent end-device behavior, coordinator/router semantics: https://www.zigbee2mqtt.io/advanced/zigbee/01_zigbee_network.html (HTTP 200)
2. Silicon Labs, "Zigbee Fundamentals: Routing Concepts" -- table routing, asymmetric links, route repair on unicast timeout, many-to-one/source routing, layer-by-layer ACKs: https://docs.silabs.com/zigbee/latest/zigbee-fundamentals/04-zigbee-routing-concepts (HTTP 200)
3. Silicon Labs, "Zigbee Standard Security" -- install codes (6/8/12/16 bytes + CRC-16), Matyas-Meyer-Oseas derivation, the well-known "ZigBeeAlliance09" key, network-key frame counters and TC key rotation: https://docs.silabs.com/zigbee/8.2.3/zigbee-security/03-standard-security (HTTP 200)
4. Espressif ESP-Zigbee SDK documentation -- vendor Zigbee 3.0 stack for ESP32-H2-class SoCs: https://docs.espressif.com/projects/esp-zigbee-sdk/en/latest/esp32h2/index.html (HTTP 200)
5. TI SimpleLink Zigbee User's Guide, "Green Power Application Overview" -- GPD energy harvesting, 32-bit source ID, GP security levels and keys: https://software-dl.ti.com/simplelink/esd/simplelink_lowpower_f3_sdk/latest/exports/docs/zigbee/html/zboss/gpd_application_overview-cc23xx.html (HTTP 200)
6. zigpy (Python Zigbee stack behind Home Assistant's ZHA): https://github.com/zigpy/zigpy (HTTP 200); Zigbee2MQTT: https://github.com/Koenkk/zigbee2mqtt (HTTP 200)
7. CSA newsroom, "Zigbee PRO 2023 Improves Overall Security While Simplifying Experience" (April 2023) -- join-authentication tightening, sub-GHz EU 800 / NA 900 MHz support: https://csa-iot.org/newsroom/zigbee-pro-2023-improves-overall-security-while-simplifying-experience (HTTP 403 to scripted fetches; verified by search and the accessible PR Newswire mirror, HTTP 200: https://www.prnewswire.com/news-releases/zigbee-pro-2023-improves-overall-security-while-simplifying-experience-301795113.html)
8. zigpy discussion #1708, "Zigbee 4.0 and Suzi" (November 2025) -- CSA's announced Zigbee 4.0 and its sub-GHz variant: https://github.com/zigpy/zigpy/discussions/1708 (HTTP 200)
