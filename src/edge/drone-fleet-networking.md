# Drone Fleets: Networking Swarms in the Sky

A fleet of drones is a network that happens to fly. The autopilot solves one
vehicle; the fleet problem is everything around it: keeping a ground control
station (GCS) and many vehicles in one conversation over links that drop,
while spending radio watts without stealing them from the rotors. The survey
literature calls the resulting network a FANET -- Flying Ad hoc Network [1] --
and its difficulty traces to one energy-budget line: battery is flight time,
so every transmitted byte competes with propulsion, and an empty battery's
"retry" is an unplanned landing.

## What a FANET is -- and why it is not a VANET

The ad hoc lineage runs MANET (laptops), VANET (cars), FANET (UAVs).
Bekmezci et al. classify FANETs by node speed, topology-change rate, and node
degree [1]; Chung et al. survey the swarm-coordination layer above [2]. The
distinctions that change engineering decisions:

| Property | VANET (cars) | FANET (drones) | Why it changes the design |
|---|---|---|---|
| Mobility | 2D, road-constrained | 3D, free-space; altitude and bank vary | antenna geometry and propagation swing with attitude |
| Node density | dense in traffic | sparse: one fleet over a wide area | few neighbors, so mesh redundancy is thin |
| Energy source | alternator; radios nearly free | battery; radio wattage is flight time | every transmission trades against propulsion |
| Losing the link | coast to a safe stop | must keep flying | link loss is a flight-mode problem, not a session problem |
| Radio stack | one regulated answer (802.11p / C-V2X, see [V2X](./v2x.md)) | no single winner: MAVLink rides Wi-Fi, SiK-class radios, LTE/5G, satcom | the link is a per-mission choice |

That last row is the deep one. V2X is a standards fight over a licensed band;
drone fleets are closer to the IoT sprawl of [LoRaWAN](./lorawan.md) -- each
mission assembles its own link stack from whatever the physics and regulatory
budgets allow. Assume the stack is heterogeneous and fails often.

## The fleet air picture

Three traffic classes share the sky, with opposite requirements:

```text
   +-------------------+   Wi-Fi 2.4/5 GHz | SiK 433/915 MHz | LTE/5G | satcom
   | Ground control    |<---------------------------------------------->|  Drone A  |
   | station (GCS)     |   mission upload, telemetry, command           | autopilot |
   +-------------------+<--- one-way Remote ID broadcast (any listener) +-----+-----+
                                                                    inter-drone: state, relay
```

Control/telemetry traffic is small but must never stop: heartbeats, attitude,
mission state. Inter-drone traffic exists only where fleets share state or
relay, and its value depends on neighbor density. Remote ID is not a network
but a lighthouse: one-way, handshake-free, for regulators and other airspace
users. Onboard, a companion computer may bridge MAVLink to vision and
planning workloads; where that compute lands is the deployment question in
[Edge Computing](./edge-computing.md).

## MAVLink: the wire format the whole fleet speaks

MAVLink is the de facto lingua franca between GCS software (QGroundControl,
Mission Planner), open autopilots (PX4, ArduPilot), and companion computers;
it rides serial, UDP, TCP, or Wi-Fi. Addressing is two-level: a vehicle is a
*system* (sysid 1-255) and each device on it -- autopilot, camera, gimbal --
is a *component* (compid). Liveness is explicit: the HEARTBEAT message (id 0)
"shows that a system or component is present and responding" [5], and
ArduPilot's GCS failsafe is a heartbeat counter tripping after
FS_GCS_TIMEOUT seconds (default 5) without one [10].

```text
MAVLink 2 over-the-wire frame, byte by byte (mavlink.io serialization guide [4])

byte:   0       1       2        3        4      5        6        7-9       10..9+n    n+10 n+11   [n+12..n+24]
      +-------+-------+--------+--------+------+--------+--------+---------+----------+-----+-----+--------------+
      | 0xFD  |  LEN  | IFLAG  | CFLAG  | SEQ  | SYSID  | CMPID  |  MSGID  | PAYLOAD  | CKL | CKH |  SIGNATURE   |
      +-------+-------+--------+--------+------+--------+--------+---------+----------+-----+-----+--------------+
        STX     0-255   incompat  compat   0-255   1-255    1-255    24-bit    0-255 B          CRC-16/      13 B: linkID
        marker  payload flags:    flags:   seq per system   component msg id    little-endian,   MCRF4XX      1 B + ts 6 B
        (MAV-   length, MUST drop  safe to  sender the     (autopilot, (MAVLink  zero tail        over frame   + sha256-48
        Link 1: zero    if not    ignore   count  vehicle) camera,...) 1: one   bytes may        except STX,  6 B, only if
        0xFE)   tail    known     if not   detects                     byte)    be cut           CRC_EXTRA    IFLAG bit 0x01
header = 10 B | minimum frame = 12 B (ACK) | maximum = 280 B (signed, full payload)
```

MAVLink 2 is backward compatible: a parser that only knows MAVLink 1 skips
anything on the 0xFD marker [4]. The fleet-relevant changes: the message ID
widens to 24 bits (16,777,215), so vendors register dialects without
collisions; trailing zero payload bytes are truncated, cutting airtime; and
the flag bytes split duties -- *incompatibility* flags must be understood or
the frame is dropped, *compatibility* flags can be ignored [4]. Signing
(incompat flag 0x01) appends 13 bytes: an 8-bit link ID, a 48-bit timestamp
in 10 us units since 1 Jan 2015 GMT, and a 48-bit MAC [6] -- the first 48
bits of SHA-256 over the 32-byte shared key followed by the packet, link ID,
and timestamp. The timestamp must increase monotonically per link (the replay
defense), and the link ID keeps several channels' clocks from interfering [6].
Budget check with verified numbers: a maximum signed frame (280 B) costs
about 9 ms of airtime on a SiK-class link at its 250 kbps air rate [4][11].

## Link layer: what the mission actually flies on

| Link | Numbers worth quoting (verified) | Strengths | Watch out for |
|---|---|---|---|
| SiK-class telemetry radio | 433/915 MHz, FHSS, RX sensitivity -121 dBm, TX up to 20 dBm (100 mW), air rate up to 250 kbps, MAVLink framing built in [11] | long range for its power; made for MAVLink | narrow pipe: trim message streams; ISM rules are region-specific |
| Wi-Fi (2.4/5 GHz) | the ArduPilot telemetry page files ESP8266/ESP32 Wi-Fi links under "Short Range (<10 km)" [11] | high throughput; cheap; payload offload and video | congested band; short range; power-hungry onboard |
| LTE/5G | no fixed numbers: coverage is operator-dependent | city-scale fleets reuse cellular coverage | dead zones over water/rural; subscription; handover gaps |
| Satcom | beyond-line-of-sight anywhere | works over oceans and poles | low rate, real latency, cost, power draw on a battery aircraft |
| RC link | pilot override on its own radio | independent of the data link | PX4 and ArduPilot treat RC loss as its own failsafe [8][10] |

The pattern that survives reality: split the planes. Fly a thin, reliable
control/telemetry link (SiK-class or LTE) plus a fat, opportunistic payload
link (Wi-Fi or 5G) that may die without ending the mission. The thin link
then dictates MAVLink stream configuration -- message intervals, not
throughput -- so the byte-efficiency rules above are not trivia.

## Three ways to coordinate a fleet

Coordination architectures are decisions about *who may act on stale state*:
a centralized GCS decides everything but is a single point of failure;
leader-follower concentrates upstream bandwidth on one aircraft whose loss
orphans the formation; a decentralized mesh survives partitions but acts on
neighbor state that may be seconds old. Stock open-source stacks are
centralized out of the box: missions flow over MAVLink from the GCS, and
both PX4 and ArduPilot treat losing that link as a first-class failsafe
rather than a degraded mode [8][10]. Leader-follower is the common research
intermediate [2], while decentralized swarms inherit the distributed-systems
problems catalogued in [Intermittent Connectivity](./intermittent-connectivity.md):
a drone mesh is a peer-to-peer system with engines.

| Model | Who decides | Link cost | Dominant failure mode |
|---|---|---|---|
| Centralized (GCS in the loop) | GCS: waypoints, tasks, aborts | one live bidirectional link per vehicle | GCS or its uplink is a single point of failure; recovery = per-vehicle failsafe |
| Leader-follower | leader flies; followers track leader state | one broadcast source; followers subscribe | leader loss orphans the formation; must re-elect or fall back |
| Decentralized (mesh) | each vehicle, from neighbor state | local broadcast only; scales with density | partitions and stale neighbor state; disagreement instead of silence |

## Energy-aware task assignment (runnable)

Task assignment is where the network meets the battery: if the fleet shares
telemetry, the assigner can weigh distance, payload drain, and remaining
charge in one table. The model uses the linear cost Dorling et al. validated
for drone delivery -- energy roughly proportional to distance flown [3] --
with a per-drone drain rate standing in for payload weight: greedy
nearest-task in fleet order, versus exhaustive min-max assignment bounding
the worst fraction of any single battery spent.

```python
"""Energy-aware task assignment: 5 drones, 5 tasks, one drone per task.

Cost for drone i on task j = DIST_KM[i][j] * drain_i (%/km, payload-dependent).
Greedy: fleet order, nearest unassigned task. Balanced: exhaustive 5! search
minimizing the worst fraction of any single battery spent; landing below the
20% reserve is infeasible.
"""
from itertools import permutations

DRONES = [("D1", 92.0, 0.9), ("D2", 78.0, 1.1), ("D3", 84.0, 0.8),  # battery %,
          ("D4", 65.0, 1.3), ("D5", 97.0, 0.7)]                     # drain %/km
DIST_KM = [[5.0, 3.0, 8.5, 6.0, 9.5],   # distances (km) from each drone
           [7.5, 4.5, 2.5, 9.0, 6.5],   # to each task (T1..T5)
           [6.0, 8.0, 5.5, 3.5, 2.0],
           [3.5, 2.5, 9.0, 7.5, 6.0],
           [4.0, 2.0, 6.5, 5.5, 8.0]]
RESERVE = 20.0  # % battery that must remain on landing

def run(assign):
    spent = [DIST_KM[i][assign[i]] * d for i, (_, _, d) in enumerate(DRONES)]
    remain = [b - s for (_, b, _), s in zip(DRONES, spent)]
    frac = [s / b * 100.0 for (_, b, _), s in zip(DRONES, spent)]
    return remain, frac

def greedy():
    free, out = list(range(5)), []
    for i in range(5):
        t = min(free, key=lambda j: (DIST_KM[i][j], j))
        free.remove(t)
        out.append(t)
    return out

def balanced():
    best_key, best = None, None
    for perm in permutations(range(5)):
        remain, frac = run(perm)
        if min(remain) >= RESERVE:
            key = (max(frac), sum(DIST_KM[i][perm[i]] for i in range(5)), perm)
            if best_key is None or key < best_key:
                best_key, best = key, perm
    return best

def report(name, assign):
    remain, frac = run(assign)
    print(f"{name} (worst single-battery draw: {max(frac):.1f}%):")
    for i, (nm, batt, _) in enumerate(DRONES):
        print(f"  {nm} -> T{assign[i] + 1}  {DIST_KM[i][assign[i]]:4.1f} km  "
              f"spends {frac[i]:4.1f}%  battery {batt:4.1f} -> {remain[i]:6.2f}%")

ag, ab = greedy(), balanced()
report("greedy   nearest-task", ag)
report("balanced min-max-draw", ab)
print()
print(f"totals: distance {sum(DIST_KM[i][ag[i]] for i in range(5)):.1f} vs "
      f"{sum(DIST_KM[i][ab[i]] for i in range(5)):.1f} km | weakest landing "
      f"{min(run(ag)[0]):.2f}% vs {min(run(ab)[0]):.2f}%")
```

Real output:

```text
greedy   nearest-task (worst single-battery draw: 7.0%):
  D1 -> T2   3.0 km  spends  2.9%  battery 92.0 ->  89.30%
  D2 -> T3   2.5 km  spends  3.5%  battery 78.0 ->  75.25%
  D3 -> T5   2.0 km  spends  1.9%  battery 84.0 ->  82.40%
  D4 -> T1   3.5 km  spends  7.0%  battery 65.0 ->  60.45%
  D5 -> T4   5.5 km  spends  4.0%  battery 97.0 ->  93.15%
balanced min-max-draw (worst single-battery draw: 5.0%):
  D1 -> T1   5.0 km  spends  4.9%  battery 92.0 ->  87.50%
  D2 -> T3   2.5 km  spends  3.5%  battery 78.0 ->  75.25%
  D3 -> T5   2.0 km  spends  1.9%  battery 84.0 ->  82.40%
  D4 -> T2   2.5 km  spends  5.0%  battery 65.0 ->  61.75%
  D5 -> T4   5.5 km  spends  4.0%  battery 97.0 ->  93.15%

totals: distance 16.5 vs 17.5 km | weakest landing 60.45% vs 61.75%
```

Read it as an argument, not a scoreboard. Greedy in fleet order lets D1 (the
first, healthy drone) take the 3 km task the fragile drone D4 -- lowest
battery, highest drain -- also wanted; D4 then flies 3.5 km at 2.0%/km and
burns 7.0% of its battery. Balanced gives D4 the short leg and pays D1 to
fly the longer-but-cheaper 5 km one: fleet distance rises 1 km while the
worst-case draw falls from 7.0% to 5.0%. That 5.0% is exactly D4's floor
(2.5 km x 1.3%/km on a 65% battery), so the min-max answer is provably
optimal here. When the binding constraint is the weakest aircraft, optimize
the worst case, not total distance -- and treat the reserve as a hard cut.

## Failsafes: designing for the moment the link dies

The data-link-loss failsafe is the fleet's net. PX4 triggers Data Link Loss
when the connection to the last MAVLink ground station is lost: hold for
COM_FAIL_ACT_T seconds, then the configured action -- warning, hold, return,
land, disarm, or terminate, with per-mode exceptions via COM_DLL_EXCEPT [8].
ArduPilot counts MAVLink heartbeats instead: no beat for FS_GCS_TIMEOUT
seconds (default 5) and the vehicle does nothing, lands, RTLs, or flies
SmartRTL -- landing instead if the GPS position is unusable [10]. Battery
failsafes stage underneath through the same action list (PX4's Warn >
Failsafe > Emergency thresholds), return behavior is configurable (RTL_TYPE,
minimum return altitude) [8][9], and the geofence failsafe contains an
aircraft with zero connectivity, firing on a perimeter breach regardless of
link state [8] -- which matters because a dozen vehicles returning at once
share one home point and climb corridor.

## Interview drill

- **Walk me through a MAVLink 2 frame.** STX 0xFD; LEN (payload 0-255,
  zero-tail truncated); incompat flags (drop frame if unknown) and compat
  flags (ignore if unknown); per-sender SEQ for loss detection; SYSID/CMPID
  sender addressing; 24-bit MSGID; payload; CRC-16/MCRF4XX plus CRC_EXTRA.
  Header 10 bytes; minimum frame 12; maximum 280 signed [4].
- **How does MAVLink message signing stop replay and spoofing?** 32-byte
  shared key; signature = sha256-48 over key + packet + linkID + timestamp;
  the 48-bit timestamp (10 us units since 2015) must increase monotonically
  per link, so captured frames cannot be re-sent; link IDs keep per-channel
  clocks separate [6].
- **Why is greedy task assignment the wrong default for a fleet?** It
  optimizes distance, but the binding constraint is the weakest battery. In
  the demo, greedy burned 7.0% of the fragile drone's battery where the
  min-max assignment held the worst case at 5.0% for one extra
  fleet-kilometer -- reserve margin is the currency of fleet safety.
- **What does Remote ID mandate, and how does it map onto MAVLink?** Most
  drones must broadcast identity and location: operate a Standard Remote ID
  Drone, attach a Broadcast Module (visual line of sight), or fly inside an
  FAA-Recognized Identification Area [12]. MAVLink carries the payload via
  Open Drone ID -- OPEN_DRONE_ID_BASIC_ID is message 12900 in the common
  dialect [7]. It is one-way on purpose: a public lighthouse, not a command
  channel.

## References

1. I. Bekmezci, O. K. Sahingoz, S. Temel, "Flying Ad-Hoc Networks (FANETs): A survey," Ad Hoc Networks 11(3), 2013. DOI 10.1016/j.adhoc.2012.12.004 (Crossref-verified; the often-quoted ...2012.07.004 is a different paper).
2. S.-J. Chung, A. A. Paranjape, P. Dames, S. Shen, V. Kumar, "A Survey on Aerial Swarm Robotics," IEEE Trans. on Robotics 34(4), 2018. DOI 10.1109/TRO.2018.2857475 (Crossref-verified).
3. K. Dorling, J. Heinrichs, G. G. Messier, S. Magierowski, "Vehicle Routing Problems for Drone Delivery," IEEE Trans. SMC: Systems 47(1), 2017. DOI 10.1109/TSMC.2016.2582745 (Crossref-verified).
4. MAVLink Developer Guide, "Serialization" -- https://mavlink.io/en/guide/serialization.html ; "MAVLink 2" overview -- https://mavlink.io/en/guide/mavlink_2.html (both probed: OK).
5. MAVLink dialect definition, minimal.xml (HEARTBEAT, message id 0) -- https://raw.githubusercontent.com/mavlink/mavlink/master/message_definitions/v1.0/minimal.xml (probed: OK).
6. MAVLink Developer Guide, "Message Signing" -- https://mavlink.io/en/guide/message_signing.html (probed: OK).
7. MAVLink Developer Guide, "Open Drone ID" -- https://mavlink.io/en/services/opendroneid.html (probed: OK).
8. PX4 Guide, "Safety Configuration (Failsafes)" -- https://docs.px4.io/main/en/config/safety (probed: OK).
9. PX4 Guide, "Return Mode" -- https://docs.px4.io/main/en/flight_modes/return (probed: OK).
10. ArduPilot, "GCS Failsafe" -- https://ardupilot.org/copter/docs/gcs-failsafe.html ; failsafe overview -- https://ardupilot.org/copter/docs/failsafe-landing-page.html (both probed: OK).
11. ArduPilot, "SiK Telemetry Radio" -- https://ardupilot.org/copter/docs/common-sik-telemetry-radio.html (probed: OK).
12. FAA, "Remote Identification of Drones" -- https://www.faa.gov/uas/getting_started/remote_id (probed: OK).
