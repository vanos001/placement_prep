# NAPI: The Scheduling Machine Between Interrupts and Polling

NAPI ("New API") is the kernel's answer to one question: at what packet rate does an
interrupt per packet stop being a delivery mechanism and become the workload? It is a
state machine that flips each RX queue between interrupt-driven delivery and pure
polling, with precise rules for when to switch. This page covers that machine —
`napi_struct`, budget, re-arm, threading, busy polling, and interrupt moderation. The
softirq context it runs in is documented in
[the softirq page](../interrupts/softirqs.md), and the device side (`net_device`,
queue selection) in [the netdev page](./netdev.md).

## The problem NAPI was built for

With a hardirq per frame, a flood of small packets produces an interrupt storm: each
irq costs a few microseconds (register access, IPI, ISR), and each one schedules the
same NET_RX softirq that could have drained a whole ring. At 1.5 Mpps of 64-byte
frames, a 4 µs irq budget alone saturates a core before the stack has seen a packet.
NAPI's fix, in one sentence: *take one interrupt, then poll until the ring is empty or
the budget is gone, and only then re-arm interrupts.* Note what it does **not** do:
NAPI is not pure polling. At low rates it degenerates to interrupt delivery, which is
the correct behavior — idle systems should sleep.

## napi_struct: the unit of scheduling

Each RX queue (not each device) carries a `napi_struct`:

| Field | Role |
|---|---|
| `poll` | Driver callback: `int (*poll)(struct napi_struct *, int budget)` |
| `weight` | Legacy per-poll cap, normally `NAPI_POLL_WEIGHT` = 64 |
| `budget` | Per-napi budget value passed to poll |
| `state` | Atomic bit flags driving the state machine (below) |
| `list` / `poll_list` | Links into the per-CPU `softnet_data.poll_list` |
| `gro_list` | GRO aggregation state (see [offloads page](./rx-offloads-gro-gso-tso.md)) |
| `thread` | kthread for threaded NAPI mode |
| `dev` | Owning `net_device` |

Two consequences of this design: a multi-queue NIC has one napi per MSI-X vector, so
polling work is spread across cores by irq affinity, and the *budget* the driver sees
is whatever the core loop hands it — bounded both per-napi and globally.

### State bits

The current tree defines (among others): `NAPI_STATE_SCHED` (poll is scheduled),
`NAPI_STATE_MISSED` (irq arrived while scheduled — remember to poll again),
`NAPI_STATE_LISTED`, `NAPI_STATE_NO_BUSY_POLL`, `NAPI_STATE_IN_BUSY_POLL`,
`NAPI_STATE_PREFER_BUSY_POLL`, `NAPI_STATE_THREADED` and
`NAPI_STATE_SCHED_THREADED` (threaded mode), plus `NAPI_STATE_HAS_NOTIFIER`. The
`SCHED` bit is the lock: `napi_schedule()` uses it as a test-and-set so that ten
irqs arriving together produce one scheduled poll, with `MISSED` guaranteeing no lost
wakeups in between.

## The state machine

```text
                    IRQ: ring has work (driver masks its irqs)
                                   |
                                   v
                 +---------- napi_schedule() --------+
                 |   test&set NAPI_STATE_SCHED       |
                 |   raise NET_RX softirq            |
                 +-----------------------------------+
                                   |  softirq runs (or NAPI thread wakes)
                                   v
                        +---------------------+
                        |   napi_poll() loop  |<--------------+
                        |  drv->poll(budget)  |               |
                        +---------------------+               |
                          |            |                      |
             work < budget|            | work == budget       |
             (ring empty) |            | (still busy)         |
                          v            v                      |
                   re-arm irq     n->budget consumed:        |
                   clear SCHED    napi_gro_flush,            |
                   (idle state)   keep SCHED, requeue on ----+
                                  poll_list ("repoll")
```

Two details people get wrong. First, the driver masks its own irq when scheduling
NAPI and re-enables it only when a poll finishes under budget — that masking is what
makes the poll loop safe. Second, "budget exhausted" means the *poll returns exactly
the budget it was given*; the kernel documentation is explicit that returning exactly
`budget` signals "I may have more work", and that this must not be conflated with
finishing precisely when the last packet was processed (return `budget - 1` in that
edge case, per `Documentation/networking/napi.rst`).

## One trip through net_rx_action

The NET_RX softirq handler consumes its per-CPU poll list under two global caps
(`include/net/hotdata.h`, initialized in `net/core/hotdata.c`):

| Cap | Default | Meaning |
|---|---|---|
| `netdev_budget` | 300 packets | Total packets across *all* napis on this CPU per softirq cycle |
| `netdev_budget_usecs` | 2000 µs | Wall-clock limit for the same cycle |
| per-napi `weight` | 64 | Max work one poll call claims |
| `dev_rx_weight` / `dev_tx_weight` | 64 | Defaults for RX/TX napi weight at registration |

If the packet budget or the time limit expires, remaining napis are moved to the
`repoll` list and the softirq raises *itself* again — without re-arming device irqs.
Under sustained load this is exactly how NAPI becomes a polling system: irq stays
masked, softirq re-raises, ring drains. Only a poll that finished under budget lets
the driver re-enable interrupts. CPU time spent here is visible as `NET_RX` in
`/proc/softirqs` and per-CPU `si.<cpu>` time; ksoftirqd spill-over (when softirqs run
in the backlog kthread instead of the interrupted context) is covered in
[the softirq page](../interrupts/softirqs.md).

## Weight, budget, and the 64-packet rhythm

Why cap a single poll at 64 packets when the ring holds thousands? Latency fairness.
A poll that drains an entire deep ring monopolizes its CPU and delays everything else
scheduled there — including other napis on the same list. The 64-packet rhythm keeps
the poll invocation short, and the *global* 300-packet budget keeps one NIC from
starving the others. Drivers with big rings and 100G+ line rates raise weight via
`netif_napi_add_weight()`, and `netdev_max_backlog` (default 1000) bounds the
non-NAPI backlog path that RPS feeds. The numbers interact: at budget=300 and three
busy queues, each queue gets roughly two polls of 64 plus change per softirq cycle.

## Simulation: interrupts vs polls under load

The model below runs a deterministic 100 ms window. Interrupt-only delivery pays
`IRQ_COST` per packet; NAPI pays one irq per schedule plus `POLL_SETUP` per poll call
and per-packet cost in both modes. Bursts of 20 packets model coalescer/aggregate
arrival patterns.

```python
#!/usr/bin/env python3
"""NAPI budget/re-arm simulation.

Compares interrupt-per-packet delivery against the NAPI state machine
(IRQ -> schedule -> poll up to budget -> re-arm only when work drains)
over a deterministic load sweep. All arithmetic is integer microseconds;
no RNG, so the output is byte-for-byte reproducible.
"""

TIME_US = 100_000            # simulated window: 100 ms
BUDGET = 64                  # NAPI_POLL_WEIGHT default per poll call
IRQ_COST_US = 4              # hardirq + schedule overhead per interrupt
POLL_SETUP_US = 5            # net_rx_action dispatch per poll invocation
PKT_COST_US = 2              # per-packet driver/stack cost
SOFTIRQ_DRAIN_US = 1         # cost to run softirq loop once more (repoll)


def arrivals(rate_pps: int, burst: int = 1):
    """Deterministic arrival times: exactly (rate * TIME_US / 1e6) packets,
    sent in bursts of `burst` spaced evenly across the window (no RNG)."""
    n = (rate_pps * TIME_US) // 1_000_000
    events = max(1, -(-n // burst))             # number of burst events
    out = []
    for i in range(events):
        t = (i * TIME_US) // events
        for _ in range(min(burst, n - len(out))):
            out.append(t)
    return out


def interrupt_mode(pkts):
    """One hardirq per packet, handler copies it up immediately."""
    return len(pkts), len(pkts) * IRQ_COST_US + len(pkts) * PKT_COST_US


def napi_mode(pkts):
    """NAPI: first arrival raises IRQ, driver schedules poll, IRQ masked.
    Poll drains up to BUDGET packets that have already arrived; packets
    arriving *during* the poll are also counted (single RX ring model).
    Re-arm the IRQ only when a poll finishes without filling the budget."""
    idx = 0
    n = len(pkts)
    now = 0
    irqs = 0
    polls = 0
    cpu_us = 0
    while idx < n:
        # interrupt on next packet
        irqs += 1
        cpu_us += IRQ_COST_US
        now = pkts[idx]
        # schedule + poll loop
        while idx < n:
            polls += 1
            cpu_us += POLL_SETUP_US
            deadline = now + BUDGET * PKT_COST_US   # poll occupies the CPU
            work = 0
            while work < BUDGET:
                if idx < n and pkts[idx] <= deadline:
                    idx += 1
                    work += 1
                else:
                    break
            cpu_us += work * PKT_COST_US
            now = deadline
            if work == BUDGET:
                cpu_us += SOFTIRQ_DRAIN_US          # repoll, IRQs stay masked
                continue
            break                                    # drain done -> re-arm
    return irqs, polls, cpu_us


print(f"{'pps':>8} {'burst':>5} {'pkts':>6} | {'irq-only':>8} {'cpu/us':>8} | "
      f"{'napi irq':>8} {'polls':>6} {'pkts/irq':>8} {'cpu/us':>8} {'saved':>6}")
for rate in (1_000, 10_000, 50_000, 100_000, 400_000):
    for burst in (1, 20):
        pk = arrivals(rate, burst)
        n_int, cpu_int = interrupt_mode(pk)
        irq, polls, cpu_napi = napi_mode(pk)
        saved = 100 * (cpu_int - cpu_napi) // cpu_int
        ratio = irq and f"{len(pk) / irq:8.1f}"
        print(f"{rate:>8} {burst:>5} {len(pk):>6} | {n_int:>8} {cpu_int:>8} | "
              f"{irq:>8} {polls:>6} {ratio:>8} {cpu_napi:>8} {saved:>5}%")
```

Output (verified byte-for-byte against a run of this exact script):

```text
     pps burst   pkts | irq-only   cpu/us | napi irq  polls pkts/irq   cpu/us  saved
    1000     1    100 |      100      600 |      100    100      1.0     1100   -84%
    1000    20    100 |      100      600 |        5      5     20.0      245    59%
   10000     1   1000 |     1000     6000 |      500    500      2.0     6500    -9%
   10000    20   1000 |     1000     6000 |       50     50     20.0     2450    59%
   50000     1   5000 |     5000    30000 |      715    715      7.0    16435    45%
   50000    20   5000 |     5000    30000 |      250    250     20.0    12250    59%
  100000     1  10000 |    10000    60000 |      770    770     13.0    26930    55%
  100000    20  10000 |    10000    60000 |      500    500     20.0    24500    59%
  400000     1  40000 |    40000   240000 |      770    770     51.9    86930    63%
  400000    20  40000 |    40000   240000 |      667    667     60.0    86003    64%
```

Read the negative rows first: with isolated arrivals (burst=1), NAPI is *worse* at
low rates — every poll invocation finds one packet, so the model pays poll setup on
top of the irq it still needs. That is real: it is why drivers combine NAPI with
interrupt coalescing, and why the state machine re-arms instead of spinning at idle.
The positive rows are the design goal — with bursts or sustained load, amortization
takes over: one schedule per 20–60 packets, savings plateau around 60%, and at
400 kpps the system is effectively polling (770 schedules for 40000 packets) at a
third of the interrupt-only cost.

## Where the poll actually runs: softirq, ksoftirqd, or a NAPI thread

Three execution venues, in order of escalation:

1. **Softirq in interrupted context** — the common case; runs on whatever CPU the irq
   landed on, at the expense of the interrupted task.
2. **ksoftirqd** — if softirqs are raised in a loop, the per-CPU kthread takes over
   (`NET_RX` share of `top` is this).
3. **A NAPI thread** — since kernel 5.12, `napi_threaded_poll()` runs each napi in its
   own kthread (`napi/<ifname>-<id>` in `ps`). Drivers opt in via
   `napi_enable_threaded()`; the `threaded` sysfs attribute on the netdev toggles it
   at runtime (`/sys/class/net/eth0/threaded`). The thread is a normal SCHED_OTHER
   kthread, so it can be given realtime priority, pinned, or cgroup-constrained —
   a favorite trick for low-jitter gateways: `chrt` the `napi/*` threads and take
   NET_RX out of your server threads' way.

Threaded mode is also the escape hatch from the softirq time-budget pathology: a
`netdev_budget` exhaustion that would spin softirqs becomes ordinary thread
scheduling. For the boot-parameter `threadirqs` (which threads *hardirqs*, a
different mechanism), see [the interrupt overview](../interrupts/overview.md).

## Busy polling: mixed mode

`CONFIG_NET_RX_BUSY_POLL` adds a third mode where *the socket* does the polling:
`epoll_wait`/`recvmsg` with `SO_BUSY_POLL` set spin for up to
`net.core.busy_read`/`busy_write` microseconds (0 = off) directly calling the napi's
poll under `NAPI_STATE_PREFER_BUSY_POLL`/`IN_BUSY_POLL` bookkeeping, while
`net.core.busy_poll` bounds the spin inside `poll`/`select`. The socket option itself,
its per-socket override, and XDP's variant (`SO_BUSY_POLL_BUDGET`) are covered in
[the netdev page](./netdev.md) and [the XDP advanced page](./xdp-advanced.md); the
kernel-side contract is: busy polling bypasses irq latency entirely (sub-5 µs RTT on
loopback-like paths) at the cost of burning a core, so it belongs on latency-critical,
duty-cycled workloads — trading floors, not web farms. The sysctls live in
[the net sysctl reference](https://docs.kernel.org/admin-guide/sysctl/net.html).

### IRQ suppression instead of polling: deferred hardirqs and DIM

Two knobs reduce the irq count *without* full polling:

- `napi_defer_hard_irqs` (per-napi, driver-enabled) + `gro_flush_timeout` (sysctl,
  µs): keep irqs masked for a grace period after a poll and let a timer re-trigger
  polling — interrupt avoidance with a bounded latency floor.
- **DIM** (Dynamic Interrupt Moderation, `lib/dim/net_dim.c`): samples events-per-packet
  and packet rates per queue, then walks a 5-step profile table (per direction, EQE vs
  CQE flavors) to raise coalescing under load and lower it at low rate. It is why
  mlx5/mlx4/i40e queues appear to "tune themselves": the driver never adjusts irq
  moderation by hand; DIM does, on completion-event boundaries. The kernel documents
  the algorithm in [Net DIM](https://docs.kernel.org/networking/net_dim.html).

## GRO inside the poll loop

The poll callback is also where receive coalescing happens: drivers call
`napi_gro_receive()` per packet, GRO accumulates per-flow aggregates on the
`napi_struct`'s gro lists (8 hash buckets), and the merged or deferred packets are
flushed to the stack — either when the aggregate is full, or in batches of
`gro_normal_batch` (default 8) to keep list churn low. The coalescing rules, GRO
entry points from tunnels (`gro_cells`), and what breaks when checksum offloads lie
are the subject of [the GRO/GSO/TSO page](./rx-offloads-gro-gso-tso.md).

## Tunables quick reference

| Knob | Scope | Default | Effect |
|---|---|---|---|
| `net.core.netdev_budget` | global (per softirq cycle) | 300 | Packets per NET_RX cycle, all devices |
| `net.core.netdev_budget_usecs` | global | 2000 µs | Time limit for the same cycle |
| per-napi `weight` | queue | 64 | Max per poll call (`NAPI_POLL_WEIGHT`) |
| `net.core.busy_poll` | global | 0 (off) | Spin budget for poll/select (µs) |
| `net.core.busy_read` / `busy_write` | global | 0 (off) | Spin budget for socket reads/writes (µs) |
| `gro_flush_timeout` | device | 0 | Grace period deferring irqs after a poll (µs) |
| `napi_defer_hard_irqs` | device/napi | driver | Poll-only runs before re-arming irqs |
| `net.core.gro_normal_batch` | global | 8 | Packets batched out of GRO per flush |
| `/sys/class/net/<dev>/threaded` | device | off | Move napi polls into `napi/*` kthreads |

## Interview-grade recap

- NAPI is not "polling mode"; it is a per-queue state machine that degenerates to
  interrupts at low load and to softirq self-rescheduling under load.
- The driver masks its irq when scheduling NAPI and re-arms only after an
  under-budget poll — losing that pairing is a lost-interrupt bug.
- `budget` vs `weight`: weight is the per-poll cap a driver registered with; budget is
  the global per-CPU packet allowance the core enforces (300/2000 µs).
- Threaded NAPI (5.12+) moves polls out of softirq context entirely; realtime
  priority on the `napi/*` threads is a legitimate latency tool.
- DIM is interrupt moderation driven by measured traffic shape, not a static sysctl.

## References

- [NAPI — kernel documentation](https://docs.kernel.org/networking/napi.html) — poll
  method contract, budget-return semantics, threaded mode.
- [net/core/dev.c](https://github.com/torvalds/linux/blob/master/net/core/dev.c) —
  `net_rx_action`, `napi_poll`, `napi_threaded_poll`, busy-poll loop. (The canonical
  `git.kernel.org` path blocks scripted clients with HTTP 403; GitHub mirror cited.)
- [NAPI legacy doc](https://www.kernel.org/doc/Documentation/networking/napi.rst) —
  the original design rationale, still served by kernel.org.
- [Net DIM — generic dynamic interrupt moderation](https://docs.kernel.org/networking/net_dim.html).
- [network sysctls](https://docs.kernel.org/admin-guide/sysctl/net.html) —
  `busy_poll`, `busy_read`, `netdev_budget`, `gro_normal_batch` semantics.
- [netdevices](https://docs.kernel.org/networking/netdevices.html) — driver-side
  registration and the `net_device` contract the napi lives in.
