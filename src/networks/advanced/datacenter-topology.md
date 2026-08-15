# Datacenter Network Topology

## The Topology Problem

A datacenter must connect tens of thousands of servers with high bisection bandwidth (any server can communicate with any other at full rate), low latency, fault tolerance, and cost efficiency. The choice of network topology determines the cost-performance trade-off.

## Clos Networks

### Origins

The Clos network (Charles Clos, 1953) was invented for telephone exchanges. A **3-stage Clos** network uses three layers of smaller switches to build a larger non-blocking fabric. The key insight: with the right number of middle-stage switches, any input can connect to any output without blocking.

### 3-Stage Clos Structure

```
          Ingress (Pod Edge)
         k ports    k ports    k ports
        ┌──────┐  ┌──────┐  ┌──────┐
        │  E0  │  │  E1  │  │  E2  │   ← k edge switches per pod
        │      │  │      │  │      │
        └──┬───┘  └──┬───┘  └──┬───┘
           │         │         │
     ──────┼─────────┼─────────┼────── Aggregation Layer (within pod)
           │         │         │
        ┌──┴───┐  ┌──┴───┐  ┌──┴───┐
        │  A0  │  │  A1  │  │  A2  │   ← k agg switches per pod
        └──┬───┘  └──┬───┘  └──┬───┘
           │         │         │
     ──────┼─────────┼─────────┼────── To Core
           │         │         │
     ┌─────┴─────────┴─────────┴──────┐
     │         Core Switches          │  ← n = (k/2) × p core switches
     │  C0    C1    C2    ...   Cn-1  │
     └───────────────────────────────┘
           │         │         │
     ──────┼─────────┼─────────┼────── To other pods
```

### Strictly Non-Blocking Condition

A 3-stage Clos is **strictly non-blocking** if the number of middle-stage (aggregation) switches satisfies:

```
n ≥ 2k - 1    (Clos theorem)
```

Where k = number of ingress/egress ports per switch, n = number of middle-stage switches. In practice, datacenters use the **rearrangeably non-blocking** condition: n ≥ k, which is cheaper but may require existing connections to be rearranged for new ones.

## Fat-Tree (Special Case of Clos)

### Al-Fares et al. Fat-Tree (2008)

The fat-tree is a Clos network where all switches are identical (same port count k), making it practical to build from commodity parts. A k-port fat-tree supports N = (k/2)³ servers using k³/4 switches:

```
k = 48 (common modern switch)
N = (48/2)³ = 13,824 servers
Switches: 48³/4 = 27,648 switches (but many are 48-port, which is expensive)

In practice, k=48 fat-trees are too large.
More common: k=48 pods with 20 Gbps links,
 or hierarchical designs with larger core.
```

### Key Properties

| Property | Value |
----------|-------|
 **Bisection bandwidth** | Full bisection (any-to-any at full rate) |
 **Over-subscription** | 1:1 (non-blocking) |
 **Number of hops** | ≤ 5 (server to server across pods) |
 **Fault tolerance** | Can tolerate any single switch failure (with rerouting) |
 **Cost** | O(N log N) switches for N servers |

### Path Diversity

Between any two servers in different pods, there are (k/2)² equal-cost paths through different core switches. ECMP spreads traffic across these paths.

## Leaf-Spine Architecture

The **leaf-spine** is the most common modern datacenter topology. It is a 2-tier Clos:

```
Server  Server  Server  Server  Server  Server
  |       |       |       |       |       |
 ┌─┴───────┴───────┴─┐ ┌─┴───────┴───────┴─┐
 │    Leaf 1 (ToR)   │ │    Leaf 2 (ToR)   │
 └──────┬──┬──┬──────┘ └──────┬──┬──┬──────┘
        |  |  |               |  |  |
   ┌────┴──┴──┴───────────────┴──┴──┴────┐
   │            Spine Layer               │
   │  Spine1  Spine2  Spine3  Spine4     │
   └────┬────┬────┬────┬────┬────┬──────┘
        |    |    |    |    |    |
   (connects to all leaf switches in the pod/fabric)
```

Every leaf connects to every spine (full mesh). Any two servers communicate in exactly **3 hops**: leaf → spine → leaf. This uniform hop count simplifies latency modeling and load balancing.

### Scaling Leaf-Spine

A single leaf-spine pod is limited by the spine switch port count. For a k-port spine switch:
- **Max leaves**: k (each spine needs one port per leaf)
- **Max servers per leaf**: k (remaining ports after connecting to spines)
- **Max servers per pod**: k × (k - #spines)

To scale beyond this, use a **multi-pod** design where core switches connect multiple leaf-spine pods (creating a 3-stage Clos).

## Expander Graphs

### Concept

An expander graph is a sparse graph with strong connectivity properties. Formally, every subset S of vertices has edges to at least (1-ε)|S| vertices outside S. This means: **any cut has many crossing edges** — the graph is highly connected despite being sparse.

### Why Expanders for Datacenters?

Expander topologies (e.g., Jellyfish, Xpander) replace the structured Clos with a random regular graph:

- **Jellyfish** (Singla et al., 2012): Connect switches randomly (each switch has the same degree). Any two servers have O(log N) expected hops.
- **Xpander** (Bhattacharya et al., 2020): Uses expander graph theory to optimize for maximum bisection bandwidth given a switch count and degree.

### Jellyfish vs. Fat-Tree

| Property | Fat-Tree | Jellyfish |
----------|----------|-----------|
 **Bisection BW** | Full (non-blocking) | ~90% of full (empirically) |
 **Hops** | ≤ 5 | O(log N), ~3–5 typically |
 **Wiring complexity** | Structured (cable management) | Random (harder to manage) |
 **Incremental expansion** | Hard (must add full pods) | Easy (add switches, rewire) |
 **Fault tolerance** | Well-understood | Better (many alternate paths) |

## Optical Datacenter Networks

### The Problem with Copper and Optical Transceivers

Modern datacenter switches use optical transceivers (SFP/QSFP) for distances >1m. Each switch has dozens of optical links. The transceivers (optical engines, DSPs, lasers) are expensive and power-hungry — they account for ~50% of switch cost and 30% of power.

### Optical Circuit Switching (OCS)

Optical Circuit Switches (e.g., MEMS-based) create **direct optical paths** between switches or servers. Unlike packet switches, OCS changes the circuit configuration slowly (milliseconds) but provides near-lossless, ultra-low-latency paths:

```
Configuration A:           Configuration B:
OCS: Port1 → Port3        OCS: Port1 → Port4
     Port2 → Port4             Port2 → Port5
     Port5 → Port1             Port3 → Port2
```

Google uses OCS in Jupiter datacenter fabric: optical circuit switches reconfigure the topology every few seconds based on traffic demand. During a reconfiguration, some flows are rerouted. This adds ~10ms of interruption, which is acceptable for bulk data transfers.

### Photonic Switching

Photonic switching uses **silicon photonics** — integrated optical circuits on a chip — to route light without O-E-O (optical-electrical-optical) conversion. Approaches:

- **MZI (Mach-Zehnder Interferometer)**: A silicon waveguide with phase shifters that route light between two outputs by controlling interference. Used in 2×2 switching elements.
- **AWG (Arrayed Waveguide Grating)**: A passive optical component that routes wavelengths to different ports. Fixed routing but no power consumption.
- **MEMS (Micro-Electro-Mechanical Systems)**: Tiny mirrors that physically redirect light beams. Slow (ms) but support many ports.

### Free-Space Optical Communication

Free-space optical (FSO) uses laser beams through air to transmit data between buildings or within a datacenter. Astra (UCSB) proposed using ceiling-mounted mirrors and steerable lasers to create reconfigurable wireless links inside a datacenter:

```
  Ceiling-mounted steerable laser
       ↓↓↓↓↓  (free-space optical beam)
  [Rack]     [Rack]     [Rack]

Advantages: No cabling, reconfigurable, high bandwidth (Tbps with WDM)
Challenges: Alignment, vibration, obstacles, eye safety
```

FSO is research-stage for intra-DC use. In practice, it's used for inter-building links where trenching fiber is impractical.

> **Interview Angle**: "Why don't all datacenters use optical switching?" — Optical switches are slow to reconfigure (ms–seconds vs. ns for electronic), can't perform packet inspection/processing, and are expensive for large port counts. Today's approach is hybrid: electronic packet switching for flexible per-packet routing, optical circuit switching for high-bandwidth inter-rack or inter-pod links. Full all-optical packet switching remains a research challenge (no practical optical buffer or logic gate).