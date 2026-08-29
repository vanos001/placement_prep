# V2X: Vehicle-to-Everything Communication (DSRC vs C-V2X vs NR-V2X)

V2X is the direct radio link between vehicles, roadside units (RSUs), vulnerable
road users, and the network. It stacks four hard problems in one system:
millisecond latency budgets, MAC design without a base-station referee, spectrum
policy decided by regulators, and a privacy-preserving PKI at fleet scale.
[Embedded AI](./embedded-ai.md) covers the application taxonomy at survey level;
this page goes deep on radios, MACs, deadlines, and security, and checks the
advertised budgets with a runnable calculator.

## The 5.9 GHz fight: why three stacks exist

Every V2X stack traces back to one spectrum decision. In 1999 the FCC reserved
75 MHz at 5.850-5.925 GHz for DSRC (ratified as IEEE 802.11p in 2010); two
decades later it concluded the band was mostly idle and re-issued most of it.

- **FCC 20-164 First Report and Order, adopted Nov 18, 2020:** lower 45 MHz
  (5.850-5.895) to unlicensed U-NII-4; upper 30 MHz (5.895-5.925) retained for
  ITS with C-V2X as the required technology; DSRC licensees had one year from
  the effective date to vacate the lower 45 MHz.
- **FCC 24-123 Second Report and Order** (adopted Nov 20, 2024; Federal
  Register Dec 13, 2024): final C-V2X service rules for 5.895-5.925 GHz, after
  an interim April 2023 waiver decision let deployments use the upper 20 MHz.
- **EU:** Implementing Decision (EU) 2019/1345 harmonized 5875-5935 MHz for
  safety-related ITS -- technology-neutral, so ITS-G5 (the 802.11p family) and
  C-V2X coexist politically and physically.
- **China:** MIIT designated 5905-5925 MHz for LTE-V2X direct communications in
  Nov 2018 (no station license for in-vehicle/portable units); in Dec 2024 it
  optimized the configuration to allow 10 MHz or 20 MHz channels.

```text
5.850    5.895      5.905  5.925  GHz  (US band plan after FCC 20-164)
  |........|..........|......|
  | lower 45 MHz      | upper 30 MHz: ITS, C-V2X mandated
  | U-NII-4 unlicensed| deployments use upper 20 MHz (5.905-5.925)
  |                   | after the Apr 2023 waiver decision

EU: 5875-5935 MHz ITS (2019/1345)   China: 5905-5925 MHz LTE-V2X (2018)
```

Consequence: **802.11p kept the standards, C-V2X kept the spectrum in the US
and China, and Europe left the fight unresolved.** Everything below is
downstream of that sentence.

## Message classes and their deadlines

SAE J2735 defines the North American message set; the 2024 revision
(J2735_202409, eighth edition) renames the document from "DSRC Message Set
Dictionary" to "V2X Communications Message Set Dictionary" -- the DSRC-only
framing is gone. Europe slots ETSI CAM/DENM into the same architectural roles.
China's T/CSAE 53-2017 industry standard defines the BSM/RSM/SPAT/MAP/RSI
equivalents used in its deployments.

| Message | Sent by | Cadence | Purpose |
|---|---|---|---|
| BSM (Basic Safety Message) | vehicle | periodic, typically 10 Hz | kinematic state: position, speed, heading, acceleration |
| SPaT / MAP | RSU | per signal cycle / static | signal phase and timing plus lane geometry |
| PSM (Personal Safety Message) | pedestrian device | event/periodic | VRU presence to vehicles |
| RSM (Roadside Safety Message) | RSU (China, T/CSAE 53) | event | remote objects detected by roadside sensors |
| CAM / DENM (ETSI) | vehicle | CAM ~10 Hz, DENM event | European awareness and event messages |

Deadlines that matter (each verified against the cited document):

| Use case | Deadline | Reliability | Source |
|---|---|---|---|
| Forward collision warning | 100 ms | 99.99% | TR 22.885 PR.5.1.5-007 (also 10 msgs/s); 5GAA SLR Vol I 6.1.8 (300 B, 150 m) |
| Generic V2V / V2I-RSU | 100 ms | 90-95% at range | TR 22.885 CPR-014 / CPR-016 |
| Pre-crash sensing | 20 ms | - | TR 22.885 CPR-015 |
| Platooning, steady state | 50 ms | 99.9% | 5GAA SLR Vol II v2.0 (Nov 2024), 20 Hz, 100/300 B |
| Platooning, legacy figure | 10 ms | 99.99% | early 5GAA SLR editions, widely cited (e.g., Roger et al., 2024) |

The platooning budget people quote in interviews is 10 ms; the current 5GAA
catalog specifies 50 ms for platooning in steady state and keeps 100 ms for
collision warnings. Quote the version you read.

## Three radio stacks

### DSRC: IEEE 802.11p (and 802.11bd)

Wi-Fi halved in frequency domain: 10 MHz channels (the original US plan had
seven, channel 178 the control channel), PHY rates 3-27 Mbps, safety frames
usually at the QPSK rate-1/2 point (6 Mbps) for robustness. It runs in OCB mode
(Outside the Context of a BSS): no association, no MAC-level authentication,
every frame broadcast to everyone. Timing doubles vs 20 MHz Wi-Fi: 13 us slots,
32 us SIFS, 58 us DIFS. The MAC is EDCA CSMA/CA; the highest access class
(used for safety frames) has CWmin = 3, so uncontended access costs AIFS plus a
mean 1.5-slot backoff (~80 us), and contention collapse under load at high
density is the well-known weakness. The successor **802.11bd-2022** (published
Mar 2023, folded into the IEEE 802.11-2024 base revision) adds dual
half-bandwidth mode, LDPC, midambles for high-Doppler tracking, and a preamble
that lets 11p and 11bd devices detect each other -- but no regulator has handed
it new spectrum.

### C-V2X LTE sidelink: 3GPP Release 14

Rel-14 (2017) added the **PC5 sidelink** for direct vehicle-to-vehicle
transmission independent of base stations. TS 36.300 (cl. 23.1) defines two
resource allocation modes: "Scheduled resource allocation" (eNB schedules,
commonly **mode 3**) and "UE autonomous resource selection" (**mode 4**), where
the UE "performs sensing for (re)selection of sidelink resources" and may keep
up to two parallel resource reservations. Mode 4 sensing combines energy
detection with control-channel decoding; the chosen resource is held with
**sensing-based semi-persistent scheduling (SB-SPS)**, reserved every resource
reservation interval (100 ms in the Rel-14 evaluation assumptions) and
re-evaluated only occasionally. Rel-14 evaluations targeted 100 ms end-to-end
delivery -- which the grant cadence itself nearly consumes. Congestion control
is CBR-based (channel busy ratio drives power and packet rate).

### NR-V2X sidelink: 3GPP Release 16

TS 38.300 (cl. 5.7.2): "Two sidelink resource allocation modes are supported:
mode 1 and mode 2. In mode 1, the sidelink resource allocation is provided by
the network. In mode 2, UE decides the SL transmission resources in the
resource pool(s)." Rel-16 adds **unicast and groupcast** with HARQ feedback on
a new feedback channel (PSFCH), RLC acknowledged mode, and CSI reporting
(cl. 16.9) -- what platooning and cooperative driving need. Since grants can be
configured per slot (sub-millisecond periods), mode 2 removes mode 4's 50 ms
mean grant wait. TR 37.885 supplies the evaluation traffic models: periodic
300/190-byte patterns at 100 ms arrivals with a 100 ms deadline, and a
10 ms-arrival model with a 10 ms deadline.

```text
MAC access patterns for one 10 Hz periodic message

802.11p   each frame: DIFS + CSMA backoff + tx       ~80 us idle; collapses under load
LTE m4    sense... [grant][tx] .. 100 ms .. [grant][tx]     mean wait = RRI/2 = 50 ms
NR m2     CG slot every ~1 ms: [tx][tx][tx]...              mean wait ~0.5 ms
```

| Property | DSRC 802.11p | LTE-V2X (Rel-14) | NR-V2X (Rel-16) |
|---|---|---|---|
| Spectrum today | EU ITS-G5 pilots only | US upper 20 MHz, China 5905-5925 | trials, no dedicated band yet |
| MAC | CSMA/CA (EDCA), OCB | mode 3 scheduled / mode 4 SB-SPS | mode 1 network / mode 2 UE (CG or dynamic) |
| First-grant delay | ~80 us uncontended | mean 50 ms (RRI 100 ms) | sub-ms with configured grants |
| Reliability tools | none (blind broadcast) | blind broadcast (HARQ only on Uu) | PSFCH HARQ, RLC AM, CSI |
| Cast types | broadcast only | broadcast | unicast, groupcast, broadcast |
| Congestion control | ETSI DCC (power/rate) | CBR-adaptive power/rate | CBR-adaptive + more |

## Latency budget anatomy (runnable demo)

End-to-end latency decomposes into radio transmit time (packet/PHY rate), MAC
access, modem+stack processing, and propagation (3.34 ns/km -- negligible; at
300 km/h a vehicle covers 8.3 cm per ms, so range matters via link budget, not
time-of-flight). The demo computes all components for a 300-byte message -- the
size 5GAA's forward-collision-warning requirement states, "based on experience
from CAM/BSM" -- and checks pass/fail against the verified deadlines.

```python
#!/usr/bin/env python3
"""End-to-end latency budget calculator for three V2X radio stacks.

A 300-byte safety message goes through radio hop, MAC access, processing,
and propagation; the sum is checked against published deadlines
(3GPP TR 22.885 V14.0.0; 5GAA SLR Vol I/II v2.0, Nov 2024).

Stack parameters are MODEL INPUTS (typical safety-message operating
points), not standard-mandated constants:
- 802.11p: 6 Mbps (QPSK-1/2 class, 10 MHz); access = DIFS 58 us
  (SIFS 32 us + 2 slots) + mean backoff 1.5 slots x 13 us (CWmin = 3).
- LTE mode 4: sensing-based semi-persistent scheduling; a packet waits
  for the next grant, mean RRI/2 = 50 ms (RRI 100 ms in Rel-14 evals).
- NR mode 2: configured grant per ~1 ms slot; mean wait 0.5 ms; 12 Mbps
  (16QAM-1/2 class).
"""
from __future__ import annotations

C = 299_792_458.0                     # speed of light, m/s
PACKET_BYTES = 300                    # 5GAA FCW information requirement (CAM/BSM class)
TX_PROC_MS, RX_PROC_MS = 0.5, 1.0     # modem + stack pipeline (model input)

STACKS = [
    # (name, PHY rate Mbps, access model, params)
    ("802.11p",    6.0,  "csma", {"difs_us": 58.0, "slot_us": 13.0, "cw_min": 3}),
    ("LTE mode 4", 6.0,  "sps",  {"rri_ms": 100.0}),
    ("NR mode 2",  12.0, "cg",   {"cg_ms": 1.0}),
]

CASES = [
    # (use case, deadline_ms, range_m, source)
    ("Platooning (legacy SLR)",   10.0,  50, "5GAA early SLR: 10 ms / 99.99%"),
    ("Platooning (SLR v2.0)",     50.0,  50, "5GAA Vol II v2.0, Nov 2024"),
    ("Pre-crash sensing",         20.0,  50, "TR 22.885 CPR-015"),
    ("Forward collision warning", 100.0, 150, "TR 22.885 PR.5.1.5-007; 5GAA Vol I 6.1.8"),
    ("V2I signal-phase warning",  100.0, 300, "TR 22.885 CPR-016"),
]


def access_ms(kind, p):
    if kind == "csma":                    # AIFS + mean backoff draw
        return (p["difs_us"] + 0.5 * p["cw_min"] * p["slot_us"]) / 1000.0
    if kind == "sps":                     # wait for next semi-persistent grant
        return p["rri_ms"] / 2.0
    return p["cg_ms"] / 2.0               # wait for next configured grant


def e2e_ms(rate_mbps, kind, p, range_m):
    tx = PACKET_BYTES * 8 / (rate_mbps * 1e6) * 1000.0
    return tx + access_ms(kind, p) + TX_PROC_MS + RX_PROC_MS + range_m / C * 1000.0


def main():
    print(f"Packet: {PACKET_BYTES} B | processing: {TX_PROC_MS + RX_PROC_MS} ms | "
          f"prop: {1e9 / C:.2f} ns/km\n")
    print("Breakdown at 150 m, ms: tx / MAC access / proc / prop")
    for name, rate, kind, p in STACKS:
        tx = PACKET_BYTES * 8 / (rate * 1e6) * 1000.0
        print(f"  {name:<10s} {tx:7.3f} / {access_ms(kind, p):8.3f} / "
              f"{TX_PROC_MS + RX_PROC_MS:5.2f} / {150 / C * 1000.0:.4f}")
    print()
    hdr = (f"{'use case':28s} {'budget':>7s} |"
           + "|".join(f" {name:>17s} " for name, _, _, _ in STACKS))
    print(hdr)
    print("-" * len(hdr))
    for label, budget, rng, src in CASES:
        cells = []
        for _, rate, kind, p in STACKS:
            t = e2e_ms(rate, kind, p, rng)
            cells.append(f" {t:10.2f}ms {'pass' if t <= budget else 'FAIL':<4s} ")
        print(f"{label:28s} {budget:6.0f}ms |" + "|".join(cells))
    print()
    for label, _, _, src in CASES:
        print(f"  {label:28s} <- {src}")


if __name__ == "__main__":
    main()
```

Output (verbatim):

```text
Packet: 300 B | processing: 1.5 ms | prop: 3.34 ns/km

Breakdown at 150 m, ms: tx / MAC access / proc / prop
  802.11p      0.400 /    0.077 /  1.50 / 0.0005
  LTE mode 4   0.400 /   50.000 /  1.50 / 0.0005
  NR mode 2    0.200 /    0.500 /  1.50 / 0.0005

use case                      budget |           802.11p |        LTE mode 4 |         NR mode 2 
-------------------------------------------------------------------------------------------------
Platooning (legacy SLR)          10ms |       1.98ms pass |      51.90ms FAIL |       2.20ms pass 
Platooning (SLR v2.0)            50ms |       1.98ms pass |      51.90ms FAIL |       2.20ms pass 
Pre-crash sensing                20ms |       1.98ms pass |      51.90ms FAIL |       2.20ms pass 
Forward collision warning       100ms |       1.98ms pass |      51.90ms pass |       2.20ms pass 
V2I signal-phase warning        100ms |       1.98ms pass |      51.90ms pass |       2.20ms pass 

  Platooning (legacy SLR)      <- 5GAA early SLR: 10 ms / 99.99%
  Platooning (SLR v2.0)        <- 5GAA Vol II v2.0, Nov 2024
  Pre-crash sensing            <- TR 22.885 CPR-015
  Forward collision warning    <- TR 22.885 PR.5.1.5-007; 5GAA Vol I 6.1.8
  V2I signal-phase warning     <- TR 22.885 CPR-016
```

Read the table honestly: the 51.9 ms for LTE mode 4 is not a measurement, it is
the structural mean of waiting for the next semi-persistent grant -- and jitter
around it means the legacy 10 ms platooning budget is out of reach whenever a
message misses its grant slot. That is precisely why Rel-16 moved to
slot-granular configured grants. 802.11p's 1.98 ms assumes an uncontended
channel; under dense load the CSMA term dominates instead. Processing (1.5 ms)
is a model input -- real modems add signature verification and filtering there.
This budget discipline transfers to [real-time systems](./real-time-systems.md)
and to wired in-vehicle networks via
[TSN](../networks/advanced/tsn-time-sensitive-networking.md).

## Security: pseudonym certificates at fleet scale

Every safety message is signed, never encrypted -- it is broadcast to strangers
-- with ECDSA signatures carried in IEEE 1609.2-2022 message and certificate
formats. Vehicles hold many short-lived **pseudonym certificates** that
authenticate BSMs without a stable identity; rotation defeats cross-rotation
tracking, and enrollment vs authorization duties split across credential types
(IEEE 1609.2.1). The regions differ in who runs the trust hierarchy: the US
uses the **SCMS** (Security Credential Management System, the federated CA
design documented by the USDOT ITS JPO), Europe runs **CCMS** with the
European Certificate Trust List operated through the Commission's C-ITS Point
of Contact (CPOC). Receivers must also flag attackers and buggy senders, so
both architectures add misbehavior reporting -- a distributed-detection problem
interviews increasingly probe.

## Deployment reality by region

- **US:** C-V2X won by regulation. DSRC vacated the lower 45 MHz after the
  one-year transition; the April 2023 waiver and FCC 24-123 cemented C-V2X in
  the upper band. State DOT corridors (transit signal priority, work-zone
  warnings) migrated DSRC to C-V2X; Audi's Virginia traffic-light-information
  deployment was the marquee automaker migration (announced 2020).
- **EU:** no winner declared. C-Roads pilots run ITS-G5, the Commission kept
  5875-5935 MHz technology-neutral, and industry statements keep asking
  Brussels to commit to a path. With a European supplier, expect both
  vocabularies (CAM/DENM over ITS-G5, C-V2X trials).
- **China:** LTE-V2X PC5 at scale via the vehicle-road-cloud program: RSUs on
  city corridors and highways, the T/CSAE 53 message sets, and the Dec 2024
  channel re-configuration (10/20 MHz) as deployments grow.

Summary: **the US chose technology by spectrum policy, Europe chose not to
choose, and China built the largest deployment on the remaining technology.**

## Interview drill

- **Why did mode 4 struggle with a 10 ms platooning budget?** SB-SPS holds a
  resource every reservation interval (100 ms in Rel-14 evals); mean wait is
  RRI/2 = 50 ms, so grant cadence alone exceeds the budget.
- **What is OCB, and why does 802.11p need it?** Outside the Context of a BSS:
  frames broadcast without association/authentication because every car and RSU
  is a transient peer; security moves up to 1609.2 signatures.
- **What do Rel-16 unicast/groupcast add over broadcast?** PSFCH HARQ feedback,
  RLC acknowledged mode, CSI -- reliability for platooning and cooperative
  maneuvers rather than best-effort awareness.
- **Why sign BSMs but not encrypt them?** Receiver set is unknown and ad hoc;
  the goal is authenticity, and privacy comes from pseudonym rotation.
- **Where do 100 ms and 10 Hz for forward collision warning come from?**
  TR 22.885 PR.5.1.5-007/-008 and the 5GAA SLR (100 ms, 99.99%, 300 B, 150 m).
- **Where does V2X meet edge computing?** V2N2V paths and RSU sensor fusion
  (RSM/RSI) terminate on multi-access edge nodes -- see
  [Edge Computing](./edge-computing.md) and MEC latency tiers in
  [5G](../networks/wireless/5g.md).

## References

1. FCC, First Report and Order, ET Docket 19-138, FCC 20-164 (Nov 18, 2020) --
   https://docs.fcc.gov/public/attachments/FCC-20-164A1.pdf (probed: OK)
2. FCC, Second Report and Order, FCC 24-123, Federal Register (Dec 13, 2024) --
   https://www.federalregister.gov/documents/2024/12/13/2024-28980/use-of-the-5850-5925-ghz-band (probed: OK)
3. 3GPP TR 22.885 V14.0.0, Study on LTE support for V2X services --
   https://www.3gpp.org/ftp/Specs/archive/22_series/22.885/22885-e00.zip (probed: OK)
4. 3GPP TS 36.300 V14.0.0, E-UTRA and E-UTRAN Overall Description, cl. 23.1 --
   https://www.3gpp.org/ftp/Specs/archive/36_series/36.300/36300-e00.zip (probed: OK)
5. 3GPP TS 38.300 V16.6.0, NR and NG-RAN Overall Description, cl. 5.7, 16.9 --
   https://www.3gpp.org/ftp/Specs/archive/38_series/38.300/38300-g60.zip (probed: OK)
6. 3GPP TR 37.885 V15.0.0, NR V2X evaluation methodology --
   https://www.3gpp.org/ftp/Specs/archive/37_series/37.885/37885-f00.zip (probed: OK)
7. 5GAA, C-V2X Use Cases and Service Level Requirements, Vol I / Vol II v2.0
   (Nov 2024) -- https://5gaa.org/publications/c-v2x-use-cases-and-service-level-requirements/ (probed: OK)
8. SAE J2735_202409, V2X Communications Message Set Dictionary --
   https://www.sae.org/standards/j2735-v2x-communications-message-set-dictionary
   (sae.org blocks scripted probes; verified via SAE Mobility and ANSI listings)
9. IEEE 802.11bd-2022, Amendment 5: Enhancements for Next Generation V2X --
   https://standards.ieee.org/ieee/802.11bd/7451/ (standards.ieee.org returns
   403 to scripted probes; verified via IEEE Xplore, published Mar 2023)
10. IEEE 1609.2-2022, Security Services for Applications and Management
    Messages -- https://standards.ieee.org/ieee/1609.2/10258/ (same bot-wall note)
11. Commission Implementing Decision (EU) 2019/1345 (5875-5935 MHz ITS) --
    https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32019D1345 (probed: OK)
12. USDOT ITS JPO, Security Credential Management System --
    https://www.its.dot.gov/resources/scms.htm ; EC C-ITS Point of Contact --
    https://cpoc.jrc.ec.europa.eu/ (both probed: OK)
