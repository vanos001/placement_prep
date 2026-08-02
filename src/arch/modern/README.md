# Modern Processors

## Overview

This section covers the major processor architectures in use today: **x86-64** (Intel/AMD), **ARM** (mobile, server, Apple Silicon), and **RISC-V** (open-source). We also cover specific modern implementations: Apple Silicon, Intel Alder Lake, and AMD Zen. Understanding these architectures is essential for system design interviews.

## Architecture Comparison

| Architecture | ISA Type | Primary Market | Key Strength |
|-------------|----------|----------------|--------------|
| x86-64 | CISC | Desktop, Server | Legacy compatibility, high single-thread |
| ARM | RISC | Mobile, Server, Laptop | Power efficiency, scalable |
| RISC-V | RISC | Embedded, Emerging | Open-source, customizable |

## Modern Implementations

| Processor | Architecture | Market | Key Feature |
|-----------|-------------|--------|-------------|
| Intel Alder Lake | x86-64 | Desktop/Laptop | Hybrid P+E cores |
| AMD Zen 4 | x86-64 | Desktop/Server | Chiplet, 3D V-Cache |
| Apple M3 | ARM | Laptop/Desktop | Unified memory, Neural Engine |
| ARM Neoverse | ARM | Server (cloud) | Graviton, Ampere |
| SiFive P670 | RISC-V | Embedded | Open-source |

## Cross-References

- [x86-64](x86-64.md) — Intel/AMD architecture
- [ARM](arm.md) — ARM architecture
- [RISC-V](risc-v.md) — Open-source ISA
- [Apple Silicon](apple-silicon.md) — Apple's ARM implementation
- [Alder Lake](alder-lake.md) — Intel hybrid architecture
- [AMD Zen](amd-zen.md) — AMD's chiplet design
