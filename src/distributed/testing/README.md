# Testing Distributed Systems

Testing a distributed system is categorically different from testing a single-process program. The subject under test is not one code path but the *interleaving* of concurrent code paths across machines, combined with partial failure: messages arrive late, in any order, duplicated, or never; clocks skew; processes crash and recover mid-protocol; disks lie about fsync. Every schedule the scheduler can produce is a program you must get right, and you cannot step through most of them in a debugger.

The chapters in this section cover the two approaches that have actually found real correctness bugs in production databases and coordination services:

- [Jepsen](./jepsen.md) — black-box *fault injection* against real clusters: install a real system on real machines, torture it with network partitions, clock skew, and crash-restarts, then check the recorded history of operations against the consistency model the system promises.
- [Deterministic Simulation](./deterministic-simulation.md) — *world replay*: port the system so that networking, scheduling, disks, and time are simulated from a seeded RNG, making every bug reproducible and every execution exhaustible — the FoundationDB approach, refined by TigerBeetle and turned into a product by Antithesis.

The two techniques are complementary. Jepsen tests the real artifact and the real network, at the cost of nondeterminism (a bug that depends on a rare interleaving may not reproduce); simulation buys reproducibility and density of rare interleavings, at the cost of an admissible-reality gap (the simulator must faithfully model the weird parts of real hardware and networks, or it certifies a fantasy). Mature projects run both, plus model checking of protocol specs (see [Formal Methods](../../formal-methods/README.md) for TLA+/TLAPS verification of consensus protocols).

A practical reading order: understand what **linearizability** and the other consistency models promise (see [Consistency Models](../fundamentals/consistency.md)), then read the Jepsen chapter to see how those promises are *checked*, then the simulation chapter to see how they are *proven by exhaustion* at design time.
