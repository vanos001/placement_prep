# Real-Time Systems

## Overview

Real-time systems are characterized by **temporal correctness**—a correct result delivered after its deadline is a wrong result. This chapter covers scheduling theory, mixed-criticality systems, safety-critical design, and their application in autonomous systems, drone fleets, and swarm robotics.

## Real-Time Scheduling Fundamentals

### Task Model

A real-time task is defined by:

- **Period (T)**: time between successive releases
- **Deadline (D)**: time by which the task must complete (often equals period)
- **WCET (Worst-Case Execution Time)**: upper bound on execution time
- **Priority**: determines scheduling order

### Utilization

CPU utilization for a periodic task: **U_i = C_i / T_i**. Total system utilization: **U = Σ C_i / T_i**.

For uniprocessor systems: **U ≤ 1.0** is necessary but not always sufficient for schedulability (depends on scheduling algorithm and deadline constraints).

## Rate-Monotonic Scheduling (RM)

**Rate-Monotonic Scheduling** is a fixed-priority algorithm where priorities are assigned inversely proportional to periods—the shorter the period, the higher the priority. It is **optimal** among fixed-priority preemptive schedulers.

### Utilization Bound (Liu & Layland, 1973)

For a task set of **n** tasks, RM guarantees schedulability if:

```
U ≤ n(2^(1/n) - 1)

n=2: 0.828  |  n=3: 0.779  |  n=∞: 0.693 (ln 2)
```

If utilization exceeds this bound, exact analysis is required using **response-time analysis** (RTA): compute worst-case response time for each task iteratively, accounting for interference from higher-priority tasks.

### RM Example

```
Task τ1: C=2, T=5, U=0.40  → Priority 1 (highest)
Task τ2: C=3, T=8, U=0.375 → Priority 2
Task τ3: C=2, T=12, U=0.17 → Priority 3

Total U = 0.945 — exceeds Liu-Layland bound for n=3 (0.779)
But exact RTA may still confirm schedulability if phasing is favorable.

Worst-case response time for τ3:
R3 = C3 + ceil(R3/T1)*C1 + ceil(R3/T2)*C2
Iterate: R3^0 = 2 → R3^1 = 2 + 1*2 + 1*3 = 7 → R3^2 = 2 + 2*2 + 1*3 = 9 → R3^3 = 2 + 2*2 + 2*3 = 12 → R3^4 = 2 + 3*2 + 2*3 = 14 (diverges → unschedulable under RM)
```

## Earliest-Deadline-First (EDF)

**EDF** is a dynamic-priority algorithm: at each scheduling decision, the task with the earliest absolute deadline runs. EDF is **optimal** among preemptive uniprocessor schedulers:

- **Schedulable if and only if** U ≤ 1.0 (for implicit-deadline tasks where D = T)
- Achieves up to **100% utilization** vs. RM's 69.3% asymptotic bound

### Comparison: RM vs. EDF

| Property | RM (Fixed Priority) | EDF (Dynamic Priority) |
|----------|--------------------|------------------------|
| Optimality | Optimal among fixed-priority | Optimal overall (uniprocessor) |
| Utilization bound | 69.3% (asymptotic) | 100% |
| Implementation | Simple, static priorities | Requires deadline tracking |
| Predictability | Easy to audit | Harder to reason about overload behavior |
| Overload transients | Predictable (lowest-priority misses first) | Cascading misses possible |
| Industry adoption | Common (OSEK/VDX, AUTOSAR) | Academic, limited production use |

EDF's weakness is **transient overload behavior**: when utilization exceeds 100%, missed deadlines can cascade unpredictably. RM degrades gracefully—only the lowest-priority task misses.

## Temporal Isolation

Temporal isolation ensures that a task's timing behavior is not affected by other tasks, even faulty ones. Mechanisms include:

- **Constant-bandwidth server (CBS)**: each task is allocated a fixed bandwidth budget; if it exceeds its budget, it is throttled
- **SPORADIC servers**: tasks receive execution credits that replenish over time
- **Partitioned scheduling (multiprocessor)**: each core runs an independent scheduler; tasks are pinned to cores, eliminating cross-core interference

## Mixed-Criticality Systems

Real-world systems integrate tasks at different **criticality levels** (e.g., DO-178C Level A through E in avionics, SIL 1–4 in IEC 61508). **Mixed-criticality systems (MCS)** allow tasks of different criticalities to share hardware, improving resource utilization while maintaining safety guarantees.

### The MCS Scheduling Problem

In a mixed-criticality system, WCET estimates depend on the assurance level:

- **LO-criticality WCET (C_LO)**: estimated using standard analysis
- **HI-criticality WCET (C_HI)**: estimated using conservative analysis (often 2–10x C_LO)

When a HI-criticality task exceeds its LO WCET, the system must **abandon** LO-criticality tasks to guarantee HI-criticality deadlines. Vestal's model (2007) formalizes this:

```
Mode LO: all tasks scheduled, use C_LO estimates
Mode HI: only HI-criticality tasks run, use C_HI estimates
Transition: triggered when any HI task exceeds C_LO but within C_HI
```

### Practical Approaches

- **IMA (Integrated Modular Avionics)**: ARINC 653 partitioning—each criticality level gets a fixed time and space partition, enforced by a hypervisor
- **AUTOSAR**: run-time monitoring with deadline monitoring and execution-time budgets
- **Safety island**: an isolated, independently verified compute unit that takes over critical functions when the main system fails

## Safety-Critical Systems

Safety-critical systems require rigorous development processes:

- **DO-178C** (avionics): software lifecycle processes, traceability from requirements to object code
- **IEC 61508** (industrial): SIL (Safety Integrity Level) 1–4; determines required design rigor
- **ISO 26262** (automotive): ASIL A–D; hardware and software safety requirements
- **EN 50128** (railway): software for railway control and protection

Key principle: **freedom from interference**—a fault in a lower-criticality component must not propagate to a higher-criticality one. Achieved through memory isolation (MMU/MPU), temporal isolation (time partitioning), and communication isolation (verified message passing).

## Autonomous Systems

Autonomous systems combine real-time scheduling with perception, planning, and control:

### Control Loop Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Sensors  │────▶│Perception│────▶│Planning  │────▶│ Control  │
│ (1-10 ms)│     │(10-100ms)│     │(50-200ms)│     │(1-10 ms) │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     ▲                                              │
     └──────────────────────────────────────────────┘
                    Physical Feedback
```

The inner control loop (1–10 ms) runs at the highest rate and priority. Perception and planning run at lower rates. This creates a **multi-rate scheduling** problem where tasks have different periods and criticality levels.

### Temporal Fault Detection

- **Watchdog timers**: hardware or software timers that reset the system if a high-priority task fails to check in
- **Deadline monitoring**: detect when a task misses its deadline and trigger fallback behavior
- **Health monitoring**: continuous assessment of system state; trigger graceful degradation

## Drone Fleets

Drone fleet management adds distributed real-time challenges:

- **Distributed consensus**: fleet-wide state agreement (formation position, task allocation) under communication delays
- **Geofencing enforcement**: real-time boundary checking with fail-safe return-to-home
- **Coordination loops**: 10–50 ms deadlines for formation control; 1–5 ms for individual flight stabilization

Systems like PX4/ArduPilot use a modular architecture with priority-based scheduling on RTOS (NuttX, FreeRTOS), where flight control runs at the highest priority, navigation at medium, and mission planning at lowest.

## Swarm Robotics

Swarm robotics applies principles from biological swarms to large groups of simple robots:

- **Decentralized coordination**: no central controller; each robot makes local decisions based on neighbor communication
- **Emergent behavior**: global patterns (flocking, foraging, formation) arise from simple local rules
- **Scalability**: the control strategy must work from 10 to 10,000 robots without reconfiguration

Communication patterns: local broadcast (within radio range), relay chains for beyond-line-of-sight coordination, and stigmergy (communication through environmental modification, e.g., pheromone-inspired markers).

Real-time requirements in swarms are **softer** than in safety-critical systems but still require bounded-latency communication for collision avoidance and formation maintenance.

## Interview Angle

> **"When would you use RM vs. EDF scheduling?"**

Use RM when simplicity and predictability under overload are more important than maximizing utilization. RM is preferred in safety-critical systems (avionics, automotive) where you need predictable degradation. Use EDF when utilization is close to 100% and you need to squeeze every cycle—but have a plan for overload (admission control, graceful degradation). In practice, most production systems use fixed-priority (RM) because overload behavior is well-understood.

> **"How would you design a mixed-criticality system for an autonomous drone?"**

Flight control (attitude, motor control) is highest criticality—runs on a safety island with lockstep cores, ASIL-D or DAL-A. Navigation and obstacle avoidance are medium criticality—can be scheduled on the main processor with temporal isolation. Mission planning and telemetry are lowest criticality—best-effort, can be preempted or dropped when critical tasks need resources. Use ARINC 653-style time partitioning: each frame (e.g., 10 ms) is divided into slots with fixed allocation per criticality level.

## Key References

- Liu & Layland, "Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment" (1973)
- Vestal, "Preemptive Scheduling of Multi-criticality Systems with Varying Degrees of Execution Time Assurance" (2007)
- ARINC 653 — Avionics Application Software Standard Interface
- ISO 26262 — Road Vehicles Functional Safety
- Sha, Abdelzaher, et al., "Real-Time Scheduling Theory: A Historical Perspective" (2004)
