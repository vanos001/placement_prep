# Deterministic Simulation Testing

## The Core Idea

The reason distributed-system bugs are hard to reproduce is that the bug lives in a *schedule*: which message arrived before which local event, which disk write landed before the crash, which thread won which race. In production those schedules are produced by an uncontrolled universe — thread schedulers, NIC queues, disk firmware, wall clocks. Run the same test twice and you get two different programs.

**Deterministic simulation testing (DST)** replaces that universe with a controlled one. The system is written so that *everything below the application logic is simulated from a seeded pseudo-random generator*: the network (delays, drops, reorderings, partitions), the disk (latency, lost or torn writes after "power failure"), process lifecycle (crashes, reboots), and time itself. The whole "cluster" runs inside a single process under a deterministic scheduler. Now a run is fully specified by just two things — the code version and the seed — and a bug found on seed `0x5ecd` replays exactly, every time, forever.

This changes the economics of testing. A nondeterministic integration test that passes tells you almost nothing about tomorrow's race; a deterministic harness that passes on 10,000 seeds is a claim about 10,000 *entire failure histories*, each as reproducible as a unit test. Bugs can be bisected across code changes, minimized by shrinking the seed's trace, and fixed with the exact reproduction in hand.

## FoundationDB: The Proof of Concept

FoundationDB (Apple) is the flagship example. The SIGMOD 2021 paper describes a decade of development in which the database was *never run at scale on real machines until late* — most correctness work happened in simulation. The ingredients:

- **Deterministic execution everywhere.** FDB's actor runtime (Flow) runs single-threaded event loops; there are no threads with preemptive races in the logic, no reads of the wall clock, no nondeterministic syscalls in the data path. Every component draws randomness from seeded generators.
- **Simulated infrastructure.** A fake network delivers messages with simulated latency and can partition arbitrarily; a fake filesystem models fsync boundaries and can drop or corrupt writes on simulated "power failure"; "machines" (processes with their own simulated address spaces) reboot mid-protocol.
- **Buggify.** Named knobs that make rare conditions *likely*: force a disk to lose the last write, force a specific recovery path, force message duplication, force an fsync to lie. Rare production events become one-line test scenarios.
- **Scale by simulation.** A laptop runs "clusters" of thousands of simulated machines; the harness sweeps seeds continuously (including nightly runs with long simulated durations), and any assertion failure produces a replayable seed.

The payoff the FDB team reports is qualitative but blunt: simulation found correctness bugs — including ones that had survived years of real deployments — that other testing could not, and most serious correctness work happens against simulated clusters. The limits the same authors acknowledge are just as instructive: simulation does not find *performance* problems (simulated timing is not real timing), and it is only as good as its models — a fake disk that is more polite than a real SSD array will happily certify code that fails on real hardware. FDB therefore still runs real-cluster tests; simulation complements them, it does not replace the physical world.

## TigerBeetle, Antithesis, and madsim

**TigerBeetle** (the financial-accounting database) was built DST-first: deterministic single-threaded event loop over a seeded PRNG, a storage abstraction whose simulated device can inject torn writes and bit rot, and its own continuous fuzzing harness — the **VOPR** — that launches random-seed simulated clusters and replays any failing seed exactly. Their engineering log documents using it to hunt consensus edge cases (view-change corner cases, duplicate-message handling) the way one would fuzz a parser.

**Antithesis** productized the approach: run your (containerized) workload under a deterministic hypervisor that controls scheduling, networking, and fault injection; explore the space continuously; and when a bug is found, ship the customer the *seed* — the same failure every time — plus the call stack of the first cause rather than the eventual crash. The team includes FoundationDB simulation veterans, and the product is explicit about the same trade: determinism requires owning the entire stack under the workload.

**madsim** brings the pattern to ordinary Rust/tokio services: swap real tokio runtime, networking, and timers for simulated, seeded equivalents, and your integration tests become seed-reproducible — a low-friction entry point for teams that cannot rewrite their storage stack.

## What Determinism Actually Requires

Making a system deterministic is mostly a list of prohibitions:

| Nondeterminism source | What must be replaced | Typical mechanism |
|---|---|---|
| Threads and preemption | cooperative, single-threaded event loop per process | actors / coroutines with explicit yields |
| Wall-clock time | simulated clock advanced by the scheduler | logical time driven by the event queue |
| Networking | simulated network with sampled delays, drops, partitions | injectable transport under the RPC layer |
| Disks | simulated device with crash-consistency model | fsync-aware block device abstraction |
| Unseeded randomness | per-component seeded PRNG streams | seed derived from the master seed |
| Environment (PIDs, hostnames, map iteration order) | canonicalized or sorted | forbid `time.Now()`, `os random`, unordered map iteration in logic |
| Async libraries with hidden threads | audited or shimmed | "the simulation is the only universe" rule |

The hard part is organizational discipline, not cleverness: *one* `time.Now()` in a deep utility function silently breaks replay of everything above it. Systems that succeed (FDB, TigerBeetle) enforce the rule with linters, allowed-API lists, and panic-on-nondeterminism in debug builds.

## A Workable Micro-Harness

The essential machinery fits in one file: a simulated clock, a seeded scheduler that decides message delays and crash points, and the protocol under test. Below, a two-node commit protocol runs under 1,000 seeds; the same seed always produces the same outcome, which is the whole point. (Run it: `python3 dst_demo.py` — it is self-contained.)

```python
# Deterministic simulation of a tiny coordinator/replica commit protocol.
# One seed = one full failure history: delays, losses, crashes, and reboots
# are all drawn from a seeded RNG, so any failing run replays exactly.

import random

class SimNetwork:
    """Seeded network: delivery after 1-5 ticks, 10% of messages dropped."""

    def __init__(self, rng):
        self.rng = rng
        self.queue = []                      # (deliver_at, seq, dst, msg)

    def send(self, now, dst, msg):
        deliver_at = now + self.rng.randint(1, 5)
        if self.rng.random() > 0.10:
            self.queue.append((deliver_at, len(self.queue), dst, msg))

    def deliver(self, now, dst):
        due = [e for e in self.queue if e[0] == now and e[2] == dst]
        self.queue = [e for e in self.queue if e not in due]
        return [msg for (_, _, d, msg) in due]

class Node:
    def __init__(self, name):
        self.name = name
        self.alive = True
        self.log = []          # durable state (survives reboot)
        self.buffered = None   # volatile state (lost on reboot)

    def reboot(self):
        self.alive = True
        self.buffered = None

def simulate(seed):
    rng = random.Random(seed)
    net = SimNetwork(rng)
    coord, rep = Node("coord"), Node("replica")
    VALUE, DURATION = "v%d" % seed, 200

    for tick in range(DURATION):
        # Fault injection: crash with small probability, reboot more slowly.
        for node in (coord, rep):
            if node.alive and rng.random() < 0.02:
                node.alive = False
            if not node.alive and rng.random() < 0.05:
                node.reboot()

        if coord.alive and tick < 10 and not coord.log:
            coord.buffered = VALUE                    # phase 1: propose
            net.send(tick, "replica", ("prepare", VALUE))
        if rep.alive:
            for msg in net.deliver(tick, "replica"):
                if msg[0] == "prepare" and rep.buffered is None:
                    rep.buffered = msg[1]             # durable prepare
                    net.send(tick, "coord", ("ack",))
                if msg[0] == "commit" and not rep.log:
                    rep.log.append(msg[1])            # durable commit copy
        if coord.alive:
            for msg in net.deliver(tick, "coord"):
                if msg[0] == "ack" and not coord.log:
                    coord.log.append(coord.buffered)  # THE commit point
                    net.send(tick, "replica", ("commit", coord.log[0]))

    return (coord.log, rep.log)

def main():
    anomalies = []
    for seed in range(1_000):
        coord_log, rep_log = simulate(seed)
        # Safety invariant: once the coordinator durably commits, the
        # commit must eventually reach the replica's durable log.
        if coord_log and rep_log != coord_log:
            anomalies.append(seed)
    print(f"seeds with anomalies: {len(anomalies)} / 1000")
    if anomalies:
        seed = anomalies[0]
        print(f"seed {seed} replay 1: {simulate(seed)}")
        print(f"seed {seed} replay 2: {simulate(seed)}  <- identical, by determinism")

if __name__ == "__main__":
    main()
```

Actual output of this program:

```text
seeds with anomalies: 140 / 1000
seed 10 replay 1: (['v10'], [])
seed 10 replay 2: (['v10'], [])  <- identical, by determinism
```

The harness just *found a real protocol bug*: when the commit message is lost (10% drop rate) or the replica happens to be down at the delivery tick — and the coordinator later reboots, losing its volatile copy — the coordinator's durable commit never propagates, and 140 of the first 1,000 seeds violate the invariant. And because `simulate(seed)` is a pure function of the seed, the failing seed replays identically forever, like a unit test. The fix (have the coordinator re-send the commit from its durable log on recovery, or let the replica ask "did you commit?" when it recovers holding a prepare) drives the anomaly count to zero — turning protocol reasoning into a measurable regression.

Two properties of this toy are worth internalizing. First, a seed is a *complete failure history*: crashes, delays, drops, and reboots all come from `rng`, so failure is as debuggable as a failing unit test. Second, the invariant sits *outside* the protocol, so the harness can discover protocol bugs (crash points that violate the invariant) rather than just crashes that violate assertions. Real DST frameworks are this loop, scaled up and made exhaustive.

## DST vs. Jepsen-Style Testing

| Dimension | Jepsen-style fault injection | Deterministic simulation |
|---|---|---|
| Subject | real system on real machines | system compiled against simulated universe |
| Reproducibility | weak (schedules vary) | exact (seed + code version) |
| Rare interleavings | hard to hit | Buggify-style forcing makes them common |
| Environment realism | high (real TCP, disks, clocks) | bounded by simulator fidelity |
| Performance bugs | visible (real timing) | invisible (simulated timing) |
| Cost of adoption | low (black box) | high (determinism must be designed in) |

The maturity path most serious systems converge on: deterministic simulation for correctness-by-exploration, model checking for protocol kernels (see [Formal Methods](../../formal-methods/README.md)), and Jepsen-style black-box testing of the *real* artifact as the final audit against simulator/hardware gaps.

## Interview Angles

- **Why is exact reproducibility the game-changer?** Because debugging cost is dominated by reproduction, and because a corpus of explored seeds becomes a regression suite: today's bug becomes a permanent test case, and code changes can be checked against every previously-failing seed.
- **What can deterministic simulation never catch?** Anything its models idealize: performance (simulated timing lies), hardware misbehavior outside the disk/network models (NIC firmware, CPU errata), and operator errors on real deployments. Hence the FDB/TigerBeetle practice of still running real clusters.
- **You inherit a 200k-line service with threads, wall-clock calls, and a real broker. Path to DST?** Strangler approach: extract a deterministic core (state machines + storage model), simulate I/O at that boundary; or adopt a runtime-level simulator (madsim-style) before attempting full-system determinism.
- **Design the fault model for a simulated disk.** Cover fsync boundaries, torn sectors, lost writes after "power cut," slow-device stalls, and disk-full — each as a Buggify-style toggle with a tunable probability, and justify why *persistence* bugs (fsync ordering) deserve first-class injection points.

## References

- [Zhou et al., "FoundationDB: A Distributed Unbundled Transactional Key Value Store", SIGMOD 2021](https://dl.acm.org/doi/10.1145/3448016.3457559)
- [FoundationDB blog — the SIGMOD'21 paper announcement](https://www.foundationdb.org/blog/fdb-paper)
- [FoundationDB docs — simulation-based testing and Buggify](https://apple.github.io/foundationdb/testing.html)
- [TigerBeetle documentation — deterministic simulation testing](https://docs.tigerbeetle.com/)
- [Antithesis — deterministic testing infrastructure](https://antithesis.com/)
- [madsim — deterministic simulation runtime for Rust/tokio](https://github.com/madsim-rs/madsim)
