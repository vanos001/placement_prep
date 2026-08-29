# GNSS Timing: How Satellites Discipline the World's Clocks

Every IEEE 1588 grandmaster and NTP stratum-1 server in a production network
ultimately points upward: to L-band radio signals from roughly two dozen
satellites at ~20,200 km altitude. GNSS is the cheapest way ever deployed to
buy UTC-traceable nanoseconds at any rooftop, and the protocol stack that
spends those nanoseconds - NTP's timestamp algebra, PTP's BMCA and hardware
timestamping - is covered in
[Time Synchronization: NTP, PTP, and the Linux Time Stack](./time-synchronization.md).
This page is the layer underneath that stack: how satellite ranging produces
a clock reading at all, how long that reading survives when the satellites
stop, and what happens when an adversary attacks the signal itself.

## One-Way Ranging With a Clock That Lies

A GNSS receiver measures code-phase arrival time from each satellite it can
hear. Each measurement looks like a range, but it is a *pseudorange*, because
the receiver's own clock is a cheap quartz, not an atomic standard:

```text
                 satellite i (Rb/Cs clock, ~20,200 km up)
                 |
  true range     |  broadcast: ephemeris + SV clock correction
                 v
        +------------------+
        | receiver         |   P_i = rho_i + c*(dt_rx - dt_sv_i)
        | dt_rx = receiver |         + I_i + T_i + eps_i
        | clock bias       |
        +------------------+

  4 satellites -> 4 equations -> 4 unknowns: x, y, z, dt_rx
```

The punchline for a timing engineer: **the fourth unknown is the product**.
Position is a byproduct; what a timing receiver sells is `dt_rx` - the offset
between the local clock and GNSS system time - emitted as a 1PPS pulse plus a
time-of-day message. A receiver with a surveyed, fixed antenna can treat
position as known and solve for time from fewer satellites; UTC laboratories
go further and use *common-view* comparisons (two sites observe the same
satellite, cancelling that satellite's clock error) for sub-10 ns scatter.

The satellites are not the fragile part. GPS spacecraft carry rubidium and
cesium atomic clocks, and the operational control segment continuously
compares them against UTC(USNO), uploading clock and ephemeris corrections
that receivers apply per IS-GPS-200N. The official US government commitment:
time transfer from the GPS signal in space is within **30 ns of UTC(USNO),
95% of the time**, using a fixed, specialized time transfer receiver.
Everything that eats into those nanoseconds happens between the satellite
and the local oscillator - the error budget below.

## The Error Budget, Term by Term

| Error term                    | Typical size on L1    | How timing receivers handle it                        |
|-------------------------------|-----------------------|-------------------------------------------------------|
| Satellite clock + ephemeris   | meters of range error | corrections broadcast per IS-GPS-200N                 |
| Ionosphere, single-frequency  | 5-30 m zenith delay   | Klobuchar model: ~50% RMS reduction, broadcast coeffs |
| Ionosphere, dual-frequency    | first order removed   | ionosphere-free combination (below)                   |
| Troposphere                   | ~2.5 m at zenith      | modeled; cm-to-dm residual at good sites              |
| Multipath                     | dm to m, site-dependent | choke-ring antennas, careful siting                 |
| Receiver noise, PPS quantizer | ns class              | hardware timestamping, discipline loop                |

The ionosphere dominates, which is why serious timing receivers use two or
more frequencies. Ionospheric group delay scales as `1/f^2`, so a weighted
difference of two code measurements cancels the first-order term - ESA's
Navipedia puts the first-order share at 99.9% - at the cost of roughly
tripling receiver noise:

```text
P_free = (f1^2 * P1 - f2^2 * P2) / (f1^2 - f2^2)
GPS L1/L2: f1 = 1575.42 MHz, f2 = 1227.60 MHz  ->  2.546*P1 - 1.546*P2
```

Single-frequency devices fall back to the Klobuchar model: eight broadcast
coefficients (`alpha`, `beta`) parameterizing a half-cosine of vertical
delay, good for about half the RMS ionospheric error worldwide. Two
timekeeper details complete the picture. In the ionosphere-free combination,
satellite clock corrections are referenced to the same combination, so
timing group delays cancel from the estimate. And GNSS delivers a time
*system*, not UTC: GPS time has no leap seconds, and the navigation message
carries the current offset (18 s since the last leap second, 1 January 2017)
- one reason grandmasters expose both "GNSS time" and "UTC" in their status
pages.

## Holdover: The Night the Satellites Stop

Between antenna and application sits a local oscillator that the GNSS 1PPS
continuously disciplines. While lock is healthy, the loop steers out the
oscillator's frequency error and averages down the 1PPS jitter. When GNSS
disappears - antenna fault, coax cut, jamming - the discipliner freezes its
last learned correction and the oscillator free-runs. This mode is
*holdover*, and its arithmetic is unforgiving:

```text
1 ppb frequency error x 86,400 s/day = 86.4 us of time error per day
```

A 1.5 us budget therefore allows an *average* frequency error of about
0.017 ppb over a day - nearly two orders of magnitude below a raw TCXO.
That single line of arithmetic explains the price ladder inside every GNSS
timing appliance: the oscillator, not the receiver module, is the expensive
part. Vendor holdover specs make the spread concrete (Meinberg's oscillator
options for GNSS receivers; conditions: free-running oscillator previously
disciplined by GNSS for at least 24 hours, constant temperature):

| Oscillator | 24 h holdover | 7 d holdover | 30 d holdover | Temp-dependent drift    |
|------------|---------------|--------------|---------------|-------------------------|
| TCXO       | +/- 4.3 ms    | +/- 128 ms   | +/- 1.1 s     | +/- 1e-6 over 90 C span |
| OCXO-LQ    | +/- 865 us    | +/- 32 ms    | +/- 330 ms    | +/- 2e-7 over 60 C span |
| OCXO-HQ    | +/- 10 us     | +/- 1.0 ms   | +/- 16 ms     | +/- 1e-8 over 65 C span |
| OCXO-DHQ   | +/- 4.5 us    | +/- 204 us   | +/- 3.3 ms    | +/- 2e-10 over 65 C span|
| Rubidium   | +/- 800 ns    | +/- 34 us    | +/- 370 us    | +/- 6e-10 over 95 C span|

Note the shape of that table: error growth is superlinear because aging
compounds under free-run - an oscillator that drifts 4.3 ms in a day drifts
16 seconds over a year. The temperature column is the quiet killer: a TCXO
that behaves on a climate-controlled bench degrades badly the moment the
HVAC fails. The model below makes that concrete - first-order: constant
residual frequency error plus a linear temperature coefficient, integrated
against a failing-HVAC profile:

```python
#!/usr/bin/env python3
"""GNSS holdover model (first-order). Frequency error in holdover:
f(t) = f0 + tempco*(T(t) - T0) in ppb; time error is its integral
(1 ppb over 1 s = 1 ns). f0 and tempco are derived from published
holdover specs (Meinberg GNSS receiver oscillator options):
f0 = 24 h phase-drift spec / 86400 s, tempco = temp-dependent
frequency-drift spec / temperature span. Aging is folded into f0, so
the 72 h column is optimistic; the HVAC profile is deliberately harsh."""
import math

DAY = 86400.0

def temp_c(t):  # 22 C room, +/- 5 C diurnal swing, +1.5 C/day HVAC creep
    return 22.0 + 5.0 * math.sin(2 * math.pi * t / DAY) + 1.5 * t / DAY

# (grade, f0 ppb, tempco ppb/C) -- see docstring for spec derivation
GRADES = [
    ("TCXO",     4.3e6 / DAY,  1e-6 / 90.0 * 1e9),   # 4.3 ms/24h, 1e-6 / 90 C
    ("OCXO-HQ",  10e3 / DAY,   1e-8 / 65.0 * 1e9),   # 10 us/24h, 1e-8 / 65 C
    ("Rubidium", 800.0 / DAY,  6e-10 / 95.0 * 1e9),  # 800 ns/24h, 6e-10 / 95 C
]
BUDGETS = [  # (sector requirement, limit in microseconds)
    ("PTP FTS end-to-end (G.8271.1)",        1.5),
    ("5G TDD cell phase sync (TS 38.133)",   3.0),
    ("MiFID II HFT UTC divergence (RTS 25)", 100.0),
    ("NTP over WAN, practical",              10000.0),
]
HORIZONS = [(1, 3600.0), (24, DAY), (72, 3 * DAY)]

def holdover_us(f0_ppb, tempco, horizon_s, dt=1.0):
    err_ns, t0 = 0.0, temp_c(0.0)
    for i in range(int(horizon_s / dt)):
        err_ns += (f0_ppb + tempco * (temp_c((i + 0.5) * dt) - t0)) * dt
    return err_ns / 1e3

def fmt_us(x):
    if x >= 1e6: return "%.2f s" % (x / 1e6)
    if x >= 1e3: return "%.2f ms" % (x / 1e3)
    return ("%.0f us" if x >= 10 else "%.2f us") % x

print("Holdover time error after GNSS lock loss (MODEL, see docstring)")
print("Temperature: 22 C base, +/- 5 C diurnal, +1.5 C/day creep")
print()
hdr = "%-9s %10s %10s | %12s %12s %12s" % ("grade", "f0 ppb", "ppb/C", "1h", "24h", "72h")
print(hdr + "\n" + "-" * len(hdr))
for name, f0, tc in GRADES:
    vals = [fmt_us(holdover_us(f0, tc, h)) for _, h in HORIZONS]
    print("%-9s %10.3f %10.3f | %12s %12s %12s" % (name, f0, tc, *vals))
print("\nVerdicts vs sector budgets (PASS/FAIL per horizon 1h/24h/72h):")
tags = ["TCXO", "OCXO", "Rb"]
for label, limit in BUDGETS:
    marks = ["P" if holdover_us(f0, tc, h) <= limit else "F"
             for name, f0, tc in GRADES for _, h in HORIZONS]
    cells = ["".join(marks[k * 3:(k + 1) * 3]) for k in range(3)]
    print("  %-38s <=%8.1f us : %s" % (label, limit,
          "  ".join("%s=%s" % (t, m) for t, m in zip(tags, cells))))
```

Output (the model is linearized, so treat it as an order-of-magnitude tool,
not a datasheet):

```text
Holdover time error after GNSS lock loss (MODEL, see docstring)
Temperature: 22 C base, +/- 5 C diurnal, +1.5 C/day creep

grade         f0 ppb      ppb/C |           1h          24h          72h
------------------------------------------------------------------------
TCXO          49.769     11.111 |       206 us      5.02 ms     19.38 ms
OCXO-HQ        0.116      0.154 |      0.79 us        20 us       120 us
Rubidium       0.009      0.006 |      0.05 us      1.21 us      6.08 us

Verdicts vs sector budgets (PASS/FAIL per horizon 1h/24h/72h):
  PTP FTS end-to-end (G.8271.1)          <=     1.5 us : TCXO=FFF  OCXO=PFF  Rb=PPF
  5G TDD cell phase sync (TS 38.133)     <=     3.0 us : TCXO=FFF  OCXO=PFF  Rb=PPF
  MiFID II HFT UTC divergence (RTS 25)   <=   100.0 us : TCXO=FFF  OCXO=PPF  Rb=PPP
  NTP over WAN, practical                <= 10000.0 us : TCXO=PPF  OCXO=PPP  Rb=PPP
```

- **A TCXO buys minutes-to-an-hour of grace, nothing more.** It passes only
  the loosest budget, and only while the room stays cool - acceptable in a
  low-end NTP appliance, unacceptable in a grandmaster.
- **A good OCXO is a bridge, not a shelter.** It holds nanosecond-class
  networks for about an hour and finance-class budgets for a day, then the
  aging trend takes over - hence alarms that escalate long before day one.
- **Rubidium is the standard answer for day-scale holdover**, passing the
  1.5 us and 3 us budgets for 24 h and failing by 72 h under a failing HVAC.
  Beyond that you need cesium, a repaired antenna path, or an alternative
  source (eLoran pilots, terrestrial radio stations, fiber time transfer) -
  holdover is a transition state, never a steady state.

## When the Sky Lies: Jamming and Spoofing

GNSS signals arrive around -130 dBm, below the thermal noise floor, so
disruption takes no sophistication. The two attacks differ in kind:

- **Jamming is denial.** The receiver loses lock and - if designed well -
  drops into holdover, which the previous section prices. Detection is easy
  (the receiver screams), and incidents are widespread: the C4ADS report
  "Above Us Only Stars" (2019) documented close to 10,000 GNSS interference
  and spoofing instances around Russia and Syria, including broad-area
  civil effects.
- **Spoofing is corruption**, and far nastier: forged signals that the
  receiver accepts as truth. A crude spoofer causes a visible jump; the
  dangerous variant is the *slow tug* - walk the victim's clock a few
  microseconds per day and every sanity check still passes while time
  quietly diverges. Meaconing (record-and-replay of genuine signals) sits
  between the two.

The main civilian cryptographic countermeasure is Galileo OSNMA (Open
Service Navigation Message Authentication), declared operational on
24 July 2025 by the EU Space Programme Agency after public testing from
November 2021 - the first open authentication service from any GNSS.
Receivers verify MACs over the navigation data using keys disclosed with a
delay (a TESLA-style construction), with root keys published via the Galileo
Service Centre. Read the guarantee precisely: OSNMA authenticates the
*origin of the navigation data*, so a spoofer can no longer forge ephemerides
or clock corrections - but it does not authenticate signal time-of-arrival,
so replay of genuine recordings remains possible, and jamming needs no
cryptography at all. Defense therefore stacks layers: multi-constellation,
multi-frequency receivers; antenna pattern and power monitoring; holdover
discipline (a spoofed sample must stay consistent with the oscillator's
short-term behavior); and drift detectors that compare GNSS against
independent network timing.

## Regulated Budgets: Who Is Not Allowed to Drift

Holdover engineering exists because regulators and radio physics both put
numbers on divergence:

| Sector / function             | Requirement                        | Instrument                    |
|-------------------------------|------------------------------------|-------------------------------|
| 5G TDD cell phase sync        | better than 3 us between cells     | 3GPP TS 38.133, clause 7.4    |
| BS-internal TX alignment      | 65 ns (MIMO) / 260 ns (contig. CA) | 3GPP TS 38.104, clause 6.5.3  |
| PTP full-timing-support chain | +/- 1.5 us end-to-end              | ITU-T G.8271.1                |
| EU finance, HFT timestamps    | 100 us from UTC; 0.1 us granularity| MiFID II RTS 25 (2025/1155)   |
| EU finance, voice trading     | 1 s from UTC                       | MiFID II RTS 25               |

Two attribution notes that make good interview corrections. The widely
quoted "1.5 us" for 5G is the ITU-T G.8271.1 end-to-end budget, not the 3GPP
inter-site number: TS 38.133's mandatory cell phase synchronization limit is
3 us, while 65/260 ns apply to transmitters *within one base station*. And
RTS 25 is not frozen: the original 2017/574 text required 100 us divergence
with 1 us timestamp granularity for HFT; the revised text (Delegated
Regulation 2025/1155, applying from 2 March 2026) keeps the 100 us
divergence and tightens granularity to 0.1 us - hardware-timestamping
territory.

How GNSS plugs into the PTP network: a grandmaster receives GNSS (1PPS plus
time-of-day), disciplines its OCXO or rubidium, and serves PTP downstream;
`ts2phc` performs the analogous alignment of NIC physical clocks to a 1PPS
source (see the [time synchronization page](./time-synchronization.md) for
daemon-level mechanics). The G.8271.1 allocation shows where GNSS sits in
the accounting: of the +/- 1.5 us end-to-end budget, only +/- 100 ns goes to
the GNSS receiver plus grandmaster combined; +/- 500 ns to a chain of ten
boundary clocks, +/- 300 ns to cable asymmetry, +/- 200 ns to the end
receiver, and +/- 200 ns to short-term holdover in the end application. TSN
inherits this directly: Qbv gate windows are offsets from a shared cycle
start (see [TSN](./tsn-time-sensitive-networking.md)), so a grandmaster in
holdover drifts every gate schedule that hangs from it.

## Interview Lens

- **Why four satellites?** Four unknowns: three coordinates plus the
  receiver's clock bias. With a surveyed fixed position, the bias alone can
  be solved from one satellite - exactly what fixed-site timing receivers do.
- **Why two frequencies instead of a better model?** The ionospheric term
  scales as 1/f^2, so a two-frequency combination *measures and removes*
  99.9% of it; Klobuchar's 50% is an estimate, the combination is a measurement.
- **Convert 1 ppb to time error over a day.** 1e-9 x 86,400 s = 86.4 us.
  That one multiplication is the entire holdover sizing problem.
- **Why is spoofing scarier than jamming?** Jamming ends in obvious lock
  loss and holdover; spoofing can pass every sanity check while slowly
  walking time. Detection compares GNSS against oscillator short-term
  stability and independent sources.
- **What does OSNMA certify?** The origin of the navigation data - not
  time-of-arrival, not replay or jamming resistance. It raises the spoofer's
  bar from "transmit plausible bits" to "record and replay real signals."

## References

1. GPS.gov, "GPS Accuracy" - official timing figure (<=30 ns vs UTC(USNO),
   95%) - https://www.gps.gov/gps-accuracy (HTTP 200)
2. GPS.gov, "Interface Control Documents (ICDs) & Interface Specifications"
   - IS-GPS-200N - https://www.gps.gov/interface-control-documents-icds-interface-specifications-iss
   (HTTP 200)
3. ESA Navipedia, "Ionosphere-free Combination for Dual Frequency
   Receivers" - https://gssc.esa.int/navipedia/index.php/Ionosphere-free_Combination_for_Dual_Frequency_Receivers
   (HTTP 200)
4. ESA Navipedia, "Klobuchar Ionospheric Model" (50% RMS figure) -
   https://gssc.esa.int/navipedia/index.php/Klobuchar_Ionospheric_Model
   (HTTP 200)
5. EUSPA, "Galileo OSNMA Service Now Available to Users" (operational
   declaration, 24 July 2025) -
   https://www.euspa.europa.eu/newsroom-events/news/testing-operations-galileo-osnma-service-now-available-users
   (HTTP 200)
6. Meinberg, "Oscillator Options for Meinberg GNSS Receivers" (holdover
   table used as demo inputs) - https://www.meinbergglobal.com/english/specs/gpsopt.htm
   (HTTP 200)
7. Commission Delegated Regulation (EU) 2017/574 (original RTS 25) -
   https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32017R0574
   (HTTP 200)
8. Commission Delegated Regulation (EU) 2025/1155 (revised RTS 25; clock
   articles apply from 2 March 2026) -
   https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32025R1155
   (HTTP 200)
9. ETSI TS 138 133 V15.10.0 (cell phase synchronization accuracy, clause
   7.4) - https://www.etsi.org/deliver/etsi_ts/138100_138199/138133/15.10.00_60/ts_138133v151000p.pdf
   (HTTP 200; text extracted and quoted)
10. ITU-T G.8271.1, "Network limits for time synchronization in packet
    networks with full timing support" -
    https://www.itu.int/rec/T-REC-G.8271.1-202211-I (HTTP 200)
11. Nokia, "IEEE 1588 for Frequency, Phase, and Time Distribution"
    (G.8271.1 budget breakdown) -
    https://documentation.nokia.com/acg/23-7-2/books/classic-cli-part-i/c072-acg-ieee-1588-fp-td.html
    (HTTP 200)
12. C4ADS, "Above Us Only Stars: Exposing GPS Spoofing in Russia and Syria"
    (2019) - https://c4ads.org/reports/above-us-only-stars (HTTP 403 to
    scripted clients; search-verified via GPS World coverage
    https://www.gpsworld.com/russia-practices-widespread-spoofing and
    multiple academic citations)
13. NIST, "Time Distribution" (WWVB/WWV radio and internet time service -
    the terrestrial fallback layer) -
    https://www.nist.gov/pml/time-and-frequency-division/time-distribution
    (HTTP 200)
