# Time Synchronization: NTP, PTP, and the Linux Time Stack

Three distributed-systems features silently depend on machines agreeing on what
time it is, and each fails differently when they don't:

- **Ordering**: timestamp-based conflict resolution (Spanner, CockroachDB) needs
  cross-node timestamps that respect real time; unbounded skew silently
  reorders commits.
- **Security**: X.509 certificates have `notBefore`/`notAfter` windows and
  Kerberos tickets have ±5-minute clocks - skew of hours breaks both TLS and
  auth in both directions.
- **Expiry**: leases, caches, and rate-limit windows are timeouts against a
  shared clock; skew converts them into correctness bugs
  (see [Leases](../../distributed/advanced/leases.md)).

The engineering problem is precise: quartz clocks drift tens of parts per
million (a few seconds per day), so every machine needs a continuous stream of
corrections, and the corrections themselves must be fault-tolerant because time
servers also lie, crash, and sit behind congested links. This page covers the
protocol stack that does this - NTP's timestamp algebra, Marzullo's
fault-tolerant intersection, PTP's hardware-grade variant, and the Linux
daemons that implement them. The logical-clock alternatives that sidestep
physical time entirely are covered in
[Clocks & Ordering](../../distributed/advanced/clocks-ordering.md) and
[Hybrid Logical Clocks](../../distributed/advanced/hybrid-logical-clocks.md).

## NTP: The Four-Timestamp Exchange

NTPv4 (RFC 5905) organizes servers into a hierarchy: stratum 0 is a reference
clock (GPS, cesium, rubidium), stratum 1 servers attach to one directly, and
each stratum-N server synchronizes to several stratum N-1 servers (up to
stratum 15; 16 means unsynchronized). Every client-server exchange is four
timestamps:

```text
client                              server (stratum N)
  |--- request,  t1 = client TX --->|
  |        t2 = server RX           |
  |<-- reply,    t3 = server TX ----|
  | t4 = client RX                  |

  offset  theta = ((t2 - t1) + (t3 - t4)) / 2
  delay   delta = (t4 - t1) - (t3 - t2)
```

The offset formula assumes one-way delay is symmetric: if the request leg took
d1 and the reply leg d2, then theta is exact when d1 = d2 and carries error
(d1 - d2)/2 otherwise. Asymmetric paths are the dominant error source on the
public internet, which is why datacenter deployments care about LAN-only or
in-rack synchronization. For an honest sample the offset can never exceed half
the measured round trip, so NTP rejects samples where abs(theta) > delta/2
("bogus" responses - a lying or badly configured server), keeps an 8-sample
shift register per server, and works with the sample of minimum delay, since
delay is a good proxy for queueing noise.

## Choosing Between Servers: Marzullo's Intersection

One server is a single point of failure; NTP clients poll several. Each server
sample i yields offset theta_i and delay delta_i, which defines a correctness
interval [theta_i - delta_i/2, theta_i + delta_i/2]: the true offset lies
inside it if the server is honest. Marzullo's algorithm (1983) finds the
interval agreed on by the largest number of sources; it tolerates f faulty
servers whenever f < n/2, returning a span that intersects at least n - f
honest intervals. The runnable demo at the end implements it against a rogue
server. Production NTP then goes further: a *modified* Marzullo intersection
(RFC 5905 section 10) discards falsetickers, and the *cluster algorithm*
(Mills) iteratively throws out statistical outliers among the survivors before
a combining loop weights the final estimate. The full loop runs continuously -
[the algorithm docs](https://www.eecis.udel.edu/~mills/ntp/html/cluster.html)
show the discard criteria.

Over the public internet, NTP lands within roughly 1-50 ms; on a quiet LAN,
about a millisecond or better. When milliseconds are too fat, you need the next
protocol.

## PTP (IEEE 1588): Sub-Microsecond Precision

The Precision Time Protocol (IEEE Std 1588-2019;
[a good summary](https://en.wikipedia.org/wiki/Precision_Time_Protocol)) attacks
NTP's two precision killers: kernel/network stack jitter (packets can sit
tens of microseconds in software queues) and switch residence delay. PTP's
message cycle, run as multicast between a grandmaster and slaves:

```text
grandmaster            switch                     slave
    |--- Sync ------------------->|-------------->|  t1 = master TX
    |-- Follow_Up (exact t1) ---->|-------------->|  (two-step mode)
    |<-------------- Delay_Req <- slave TX t3 ----|
    |<-------------- Delay_Resp (t4 = master RX)--|
```

- **Hardware timestamping**: PTP-capable NICs stamp Sync/Delay_Req at the PHY,
  on the wire, in hardware. This alone moves precision from tens of
  microseconds (software timestamps) to tens of nanoseconds on clean LANs;
  sub-microsecond end-to-end is routine in production datacenters.
- **Transparent clocks (TC)**: switches measure each frame's residence time and
  add it to the Follow_Up correction field, removing queueing jitter from the
  math without terminating the protocol. Boundary clocks (BC) instead terminate
  and regenerate PTP at every hop - each switch becomes a slave upstream and a
  master downstream, which scales better on large fabrics.
- **Grandmaster election (BMCA)**: every clock exchanges Announce messages
  carrying its quality dataset (priority1, clockClass, clockAccuracy,
  clock Stability, priority2, identity); the best dataset wins and becomes
  grandmaster. Losing your GPS receiver does not stop the protocol - the
  next-best clock takes over, which is the fault tolerance that matters in
  production.
- **Profiles** bundle options per industry (power utilities: IEEE C37.238;
  broadcast: SMPTE ST 2059-2) so devices interoperate with fixed assumptions.

Rule of thumb: NTP for milliseconds over WANs, PTP for microseconds inside a
datacenter. Spanner-class systems need something stronger still (below).

## The Linux Time Stack

Linux separates the hardware clock from the system clock. Each PTP-capable NIC
exposes a **PTP hardware clock (PHC)** as a character device (`/dev/ptp0`) with
its own free-running, nanosecond-resolution time; the kernel's
`CLOCK_REALTIME` is a separate thing entirely. The daemons:

- `ptp4l` ([linuxptp](https://linuxptp.nwtime.org/documentation/ptp4l/))
  implements PTP itself - it synchronizes either the PHC (hardware mode, the
  accurate one) or CLOCK_REALTIME (software mode, fallback).
- `phc2sys` feeds the NIC's PHC time into CLOCK_REALTIME, bridging the two.
- `ts2phc` aligns *many* PHCs to one source (GNSS or a 1PPS signal) - how you
  build a PTP grandmaster or keep a rack's NICs phase-aligned.
- `timemaster` arbitrates between chrony (for NTP uplinks) and ptp4l (for the
  PTP domain) so both can share CLOCK_REALTIME.

Application-side timestamping uses `SO_TIMESTAMPING` to get hardware RX/TX
stamps on sockets - see
[SO_TIMESTAMPING: Network Packet Timestamping](../../linux/kernel/networking/timestamping.md)
for that layer. For plain NTP, the modern choice is
[chrony](https://chrony-project.org/documentation.html) over the classic ntpd:

| Aspect             | chrony                             | ntpd                          |
|--------------------|------------------------------------|-------------------------------|
| Convergence        | minutes, even after large offsets  | hours after large offsets     |
| Intermittent links | designed for disconnected use      | assumes permanent connectivity|
| Correction style   | steps or slews, rate control       | slews; steps only on big jumps|
| Modern auth        | NTS (RFC 8915) supported           | legacy autokey only           |

chrony is the default NTP client/server on RHEL, SUSE, and Ubuntu server
images; ntpd remains the historical reference implementation.

## When Time Itself Fails: Leap Seconds

UTC occasionally inserts a 23:59:60 to track Earth's irregular rotation - and
a one-second step is a step function through every timestamp a system computes:

- **June 30, 2012**: when the leap second was inserted, the Linux kernel's
  hrtimer code deadlocked on some hosts, spinning CPUs at 100%; machines
  running Java, MySQL, and Cassandra (Reddit, Mozilla, LinkedIn among them)
  fell over until restarted.
- **January 1, 2017**: Cloudflare's RRDNS panicked at midnight. Go's
  `time.Now()` pairs a wall-clock reading with a monotonic reading; the wall
  clock was stepped back by half a second at the leap, a subtraction produced
  a negative sub-second value where zero was the floor, and the negative index
  crashed the DNS server mid-query
  ([post-mortem](https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns/),
  written by the engineer who debugged it at 2017-01-01 22:40 UTC).
- **The mitigation is smearing**: instead of a step, spread the extra second
  over 24 hours as a ~11.6 microsecond/second rate change (Google, AWS, and
  NTP-server vendors all smear; implementations must pick the *same* window or
  they will disagree during it).
- **The long game**: CGPM 2022 Resolution 2 commits metrologists to abolishing
  leap seconds by 2035 - until then, every system that touches wall time still
  needs a policy. Distribution-level notes live in
  [Hybrid Logical Clocks](../../distributed/advanced/hybrid-logical-clocks.md), and
  [Mills' leap-second page](https://www.eecis.udel.edu/~mills/leap.html) covers
  the mechanics.

## Bounding Error Instead of Trusting Clocks

NTP gives you a number with no error bar. Google's TrueTime, the engine under
[Spanner](../../distributed/fundamentals/spanner.md), is the counter-move: each
machine keeps a correctness *interval* `[earliest, latest]` from GPS and atomic
clock masters (1-7 ms wide typically), and the commit protocol *waits out* the
uncertainty before acknowledging a write, buying external consistency with
bounded - not zero - clock error. The full mechanism,
commit-wait proof, and the critique of "bold engineering workaround" are in
[TrueTime](../../distributed/fundamentals/truetime.md); the takeaway here is the
shape: NTP's job is feeding CLOCK_REALTIME to every process, TrueTime's job is
making the *uncertainty* itself a first-class API value.

## Leases and Expiry: Which Clock Do You Trust?

A lease is a grant valid until wall-clock time T, so a lease is only as correct
as the clock that checks T. Three practices keep them honest: expiry timers
should run on `CLOCK_MONOTONIC` so NTP steps cannot extend or kill them;
renewal periods must be sized against the *maximum* skew between grantor and
holder, not the average; and Chubby-style systems extend leases by the observed
maximum clock error, so time noise shows up as longer leases rather than split
brains. The full treatment - Gray & Cheriton's original argument, safety
analysis, failure modes - is in
[Leases](../../distributed/advanced/leases.md).

## Interview Angle

> "Client at t1=0 gets t2=8 ms, t3=9 ms, t4=4 ms. What is the offset?"

theta = ((8-0) + (9-4))/2 = 6.5 ms; delta = (4-0) - (9-8) = 3 ms. The client
clock is 6.5 ms behind the server, round trip 3 ms, and the sample is sane
because offset (6.5) is within delta/2 (1.5) - actually it isn't, so a real NTP
would flag this as bogus: an honest exchange cannot claim a 6.5 ms offset over
a 3 ms round trip. Saying that out loud is the part interviewers remember.

> "Why do datacenters run PTP when NTP is already there?"

Precision and where it is measured. NTP stamps in software, after queueing
delays of tens of microseconds, and drifts over WAN asymmetry; PTP stamps in
the NIC's PHY, has transparent clocks subtract switch residence time, and
holds sub-microsecond skew across a fabric - which is whatSpanner-style commit
waits and distributed tracing correlation actually need.

## Run It Yourself

Compute NTP offset/delay from four t1..t4 samples and run Marzullo's
intersection against a rogue server:

```python
# NTP offset/delay algebra from t1..t4 samples (RFC 5905 section 8),
# followed by Marzullo's intersection over four servers.
#
#   offset theta = ((t2 - t1) + (t3 - t4)) / 2
#   delay  delta = (t4 - t1) - (t3 - t2)
#   correctness interval = [theta - delta/2, theta + delta/2]
#
# All values are in seconds; printed in milliseconds.

samples = [
    # server    t1        t2        t3        t4
    ("ntp-a", 100.0000, 100.0070, 100.0080, 100.0050),
    ("ntp-b", 200.0000, 200.0075, 200.0085, 200.0040),
    ("ntp-c", 300.0000, 300.0070, 300.0075, 300.0070),
    ("ntp-d", 400.0000, 400.0240, 400.0250, 400.0030),   # rogue: fabricated
]                        # timestamps - large offset, tiny claimed delay

print(f"{'server':<8} {'offset_ms':>10} {'delay_ms':>9} {'r_ms':>7} {'interval_ms':>18}")
intervals = []
for name, t1, t2, t3, t4 in samples:
    theta = ((t2 - t1) + (t3 - t4)) / 2
    delta = (t4 - t1) - (t3 - t2)
    r = delta / 2
    lo, hi = theta - r, theta + r
    intervals.append((name, lo, hi))
    print(f"{name:<8} {theta*1000:10.3f} {delta*1000:9.3f} {r*1000:7.3f} "
          f"[{lo*1000:6.2f}, {hi*1000:6.2f}]")

def marzullo(ivs):
    # Marzullo (1983): find the interval agreed on by the most sources.
    # Tolerates f faulty intervals whenever f < n/2; returns (agreement, span).
    table = []
    for lo, hi in ivs:
        table.append((lo, -1))       # start marker: count goes up
        table.append((hi, +1))       # end marker: count goes down
    table.sort()                     # by time, then marker (-1 before +1)
    best, cnt, best_lo, best_hi = 0, 0, 0.0, 0.0
    for time, typ in table:
        cnt -= typ
        if cnt > best:
            best, best_lo = cnt, time
        if typ == +1 and best and cnt < best:
            best_hi = time
            break
    return best, (best_lo, best_hi)

n, (lo, hi) = marzullo([(lo, hi) for _, lo, hi in intervals])
chosen = (lo + hi) / 2
print()
print(f"marzullo: agreement = {n} of {len(intervals)} servers")
print(f"chosen interval = [{lo*1000:.2f}, {hi*1000:.2f}] ms")
print(f"synchronised offset = {chosen*1000:.3f} ms")
```

Output (Python 3.11):

```text
server    offset_ms  delay_ms   r_ms      interval_ms
ntp-a         5.000     4.000   2.000 [  3.00,   7.00]
ntp-b         6.000     3.000   1.500 [  4.50,   7.50]
ntp-c         3.750     6.500   3.250 [  0.50,   7.00]
ntp-d        23.000     2.000   1.000 [ 22.00,  24.00]

marzullo: agreement = 3 of 4 servers
chosen interval = [4.50, 7.00] ms
synchronised offset = 5.750 ms
```

The rogue server's interval `[22, 24]` ms is outvoted 3-to-1; the surviving
span [4.5, 7.0] ms is the intersection of the three honest intervals, and its
midpoint (5.75 ms) is the final offset estimate. Real NTP adds the sanity
filters and cluster stage described above on top of exactly this math.

## References

- RFC 5905, "Network Time Protocol Version 4: Protocol and Algorithms
  Specification" - https://www.rfc-editor.org/rfc/rfc5905.html
- David Mills, NTP clock discipline algorithm docs (intersection/cluster) -
  https://www.eecis.udel.edu/~mills/ntp/html/cluster.html
- linuxptp project documentation (ptp4l, phc2sys, ts2phc) -
  https://linuxptp.nwtime.org/documentation/ptp4l/
- John Graham-Cumming, "How and why the leap second affected Cloudflare DNS"
  (2017) - https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns/
- Corbett et al., "Spanner: Google's Globally-Distributed Database" (OSDI 2012,
  TrueTime design) - https://research.google/pubs/pub39966/
