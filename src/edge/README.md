# Edge Computing, IoT & Cyber-Physical Systems

This section covers the design principles, protocols, and architectures that power computation at the network periphery—where latency budgets are tight, connectivity is intermittent, and the physical world meets the digital.

## Chapter Overview

| Chapter | Title | Core Focus |
|---------|-------|------------|
| [Edge Computing](edge-computing.md) | Edge & Fog Architectures | Latency-sensitive computing tiers, caching, consistency, digital twins, federated learning |
| [IoT Protocols](iot-protocols.md) | IoT Protocol Internals | MQTT, CoAP, Thread, Matter, LoRaWAN, BLE mesh, industrial IoT |
| [Embedded AI](embedded-ai.md) | Embedded & Edge AI | TinyML, MCU inference, energy harvesting, V2X, autonomous vehicles |
| [Real-Time Systems](real-time-systems.md) | Real-Time & Safety-Critical | Scheduling theory, mixed-criticality, swarm robotics, autonomous systems |

## Why This Matters for Interviews

Edge and IoT sit at the intersection of distributed systems, networking, embedded engineering, and AI. Interviewers increasingly probe these areas for roles in:

- **Cloud/platform engineering** — multi-tier architectures, edge-cloud orchestration
- **Systems engineering** — real-time scheduling, resource-constrained environments
- **ML infrastructure** — edge inference, federated learning pipelines
- **Security** — attack surfaces unique to IoT, supply-chain trust in firmware

Expect questions that combine systems design thinking with hardware and networking constraints. Understanding the trade-offs between latency, bandwidth, energy, and consistency is essential.

## Key Themes

1. **Tiered latency budgets** — from millisecond local loops to seconds for cloud round-trips
2. **Resource constraints** — memory, compute, and energy budgets on MCUs and SoCs
3. **Intermittent & unreliable connectivity** — store-and-forward, DTN, opportunistic networking
4. **Temporal correctness** — deadlines, jitter, and temporal isolation in real-time systems
5. **Physical-digital convergence** — digital twins, sensor fusion, cyber-physical feedback loops
