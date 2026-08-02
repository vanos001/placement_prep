# I/O Systems

## Overview

Input/Output (I/O) is one of the most critical and complex subsystems of an operating system. The OS must manage a vast array of peripheral devices — disks, network cards, keyboards, displays, sensors — each with different speed characteristics, data formats, and control mechanisms. The I/O subsystem provides a uniform abstraction so that applications can interact with devices without knowing hardware-specific details.

## Motivation

Why is I/O so important?

1. **Performance bottleneck**: CPU operates in nanoseconds; disks in milliseconds. A single disk I/O can take as long as millions of CPU instructions.
2. **Heterogeneity**: Hundreds of device types exist, each with unique protocols. The OS must hide this complexity.
3. **Concurrency**: Multiple processes may request I/O simultaneously; the OS must schedule, multiplex, and arbitrate.
4. **Reliability**: I/O failures (disk errors, network timeouts) must be handled gracefully without crashing the system.

## I/O Subsystem Architecture

```
┌─────────────────────────────────────────────┐
│              User Applications              │
├─────────────────────────────────────────────┤
│           System Call Interface             │
│         (read, write, open, close)          │
├─────────────────────────────────────────────┤
│          Device-Independent I/O Layer       │
│    (buffering, caching, spooling, naming)   │
├─────────────────────────────────────────────┤
│            Device Drivers                   │
│    (translate generic → device-specific)    │
├─────────────────────────────────────────────┤
│        Interrupt Handlers                   │
│    (handle hardware signals)                │
├─────────────────────────────────────────────┤
│          Hardware                           │
│    (controllers, buses, devices)            │
└─────────────────────────────────────────────┘
```

## Topics in This Chapter

| Topic | Description |
|-------|-------------|
| [Hardware](hardware.md) | I/O hardware: ports, buses, controllers |
| [Software Layers](software-layers.md) | The layered I/O architecture |
| [Buffering](buffering.md) | Buffering strategies and their tradeoffs |
| [Disk Scheduling](disk-scheduling.md) | Overview of disk scheduling algorithms |
| [FCFS](disk-fcfs.md) | First-Come First-Served disk scheduling |
| [SSTF](disk-sstf.md) | Shortest Seek Time First |
| [SCAN / Elevator](disk-scan.md) | SCAN algorithm |
| [C-SCAN](disk-cscan.md) | Circular SCAN algorithm |
| [LOOK / C-LOOK](disk-look.md) | LOOK variants |
| [Interrupts](interrupts.md) | Interrupt-driven I/O |
| [DMA](dma.md) | Direct Memory Access |
| [Device Drivers](device-drivers.md) | Device driver architecture |

## Interview Focus

- Explain why I/O is the bottleneck and how OS mitigates it
- Compare polling, interrupt-driven, and DMA-based I/O
- Know disk scheduling algorithms cold — FAANG interviews love them
- Understand the layered architecture and why each layer exists
- Be able to trace a `read()` system call from user space to hardware and back

## Quick Revision

- **I/O hierarchy**: Hardware → Interrupt handlers → Device drivers → Device-independent layer → User space
- **Three I/O methods**: Programmed I/O (polling), Interrupt-driven I/O, DMA
- **Buffering types**: Single, double, circular, buffer pool
- **Disk scheduling**: FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK
- **Key tradeoff**: Throughput vs. latency vs. fairness
