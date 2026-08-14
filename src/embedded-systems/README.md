# Embedded Systems

## What Are Embedded Systems?

An **embedded system** is a computer designed to perform a dedicated function within a larger mechanical or electrical system. Unlike general-purpose computers, embedded systems are optimized for specific tasks with strict constraints on size, power consumption, cost, and real-time responsiveness.

They are everywhere: automotive ECUs, medical pacemakers, industrial PLCs, consumer electronics, IoT sensors, and aerospace flight controllers. For software engineers, embedded systems knowledge is increasingly valuable because the boundary between "embedded" and "general-purpose" software is blurring—especially with the rise of edge computing and IoT.

## Why Embedded Systems Matter for Interviews

Even if you are not targeting a dedicated embedded role, interviewers test this domain because it demonstrates:

- **Resource awareness**—writing code that respects memory and power budgets
- **Understanding of hardware-software interaction**—knowing what happens below the OS abstraction
- **Deterministic thinking**—reasoning about timing, interrupts, and real-time constraints
- **Systems thinking**—understanding the full stack from silicon to application

## Microcontrollers vs Microprocessors

| Aspect | Microcontroller (MCU) | Microprocessor (MPU) |
|--------|----------------------|----------------------|
| Integration | CPU + RAM + Flash + peripherals on-chip | CPU only; external RAM/Flash/storage |
| Clock speed | Typically 4–400 MHz | Typically 500 MHz–5 GHz |
| Power | Microwatts to milliwatts | Watts to hundreds of watts |
| Use case | Sensors, motor controllers, wearables | Smartphones, laptops, servers |
| OS | Bare-metal or RTOS | Linux, Windows, full OS |
| Cost | $0.10–$10 | $5–$500+ |
| Examples | STM32, ESP32, ATmega328P | ARM Cortex-A, x86, Apple Silicon |

## ARM Cortex-M Overview

ARM's Cortex-M family dominates the 32-bit MCU market. The key profiles are:

- **Cortex-M0/M0+**: Ultra-low-power, minimal gate count. Used in simple sensors, BLE beacons, and cost-sensitive products.
- **Cortex-M3**: General-purpose 32-bit. Good balance of performance and power. Found in industrial controllers and consumer electronics.
- **Cortex-M4**: Adds DSP instructions and optional single-precision floating-point (FPU). Ideal for audio processing, motor control, and signal conditioning.
- **Cortex-M7**: High-performance with dual-issue pipeline, L1 cache, and double-precision FPU. Used in advanced IoT gateways and automotive infotainment.
- **Cortex-M33**: TrustZone security extension, co-processor interface. Targets secure IoT and automotive applications.

All Cortex-M cores use the **Thumb-2** instruction set (mixed 16/32-bit encoding) and feature a **Nested Vectored Interrupt Controller (NVIC)** for deterministic interrupt handling.

## Core Constraints

### Memory Constraints

Embedded systems typically have 4–512 KB of SRAM and 16 KB–2 MB of Flash. This forces developers to:

- Avoid dynamic allocation (no `malloc` in production firmware)
- Use static allocation and memory pools
- Optimize data structures for size (packed structs, bitfields)
- Understand linker scripts and memory maps

### Power Constraints

Battery-powered devices must minimize energy consumption. Techniques include:

- **Sleep modes**: Stop, Standby, and Shutdown states that cut power to subsystems
- **Clock gating**: Disabling clocks to unused peripherals
- **DMA**: Offloading data transfer from CPU to reduce active time
- **Voltage/frequency scaling**: Reducing clock speed and supply voltage under light load

### Real-Time Constraints

Many embedded systems are **hard real-time**—a missed deadline is a system failure (e.g., airbag deployment). **Soft real-time** systems tolerate occasional deadline misses (e.g., video streaming). Real-time requirements dictate:

- Bounded interrupt latency (NVIC guarantees < 12 cycles on Cortex-M)
- Deterministic worst-case execution time (WCET) analysis
- Priority-driven preemptive scheduling

## Real-Time Operating Systems (RTOS)

An RTOS provides:

- **Multitasking** with priority-based preemptive scheduling
- **Inter-task communication**: queues, semaphores, mutexes, event groups
- **Timers**: one-shot and periodic software timers
- **Memory management**: heap allocation with deterministic bounds

Popular RTOS options include **FreeRTOS** (open-source, MIT license, widely used), **Zephyr** (Linux Foundation, comprehensive HAL), **RIOT** (IoT-focused), and **ThreadX** (commercial, used in automotive).

## IoT Overview

The Internet of Things connects embedded devices to the cloud. Key protocols:

- **MQTT**: Lightweight pub/sub protocol over TCP, ideal for constrained devices
- **CoAP**: RESTful protocol over UDP for resource-constrained networks
- **BLE**: Low-energy wireless for short-range communication
- **LoRaWAN**: Long-range, low-power wide-area network protocol
- **Thread/Matter**: IPv6-based mesh networking for smart home devices

## References

- [ARM Cortex-M Programming Guide](https://developer.arm.com/Architectures/Cortex-M)
- [FreeRTOS Documentation](https://www.freertos.org/Documentation/RTOS_book.html)
- [ARMv7-M Architecture Reference Manual](https://developer.arm.com/documentation/ddi0403/latest)
- [Embedded Systems - Wikibooks](https://en.wikibooks.org/wiki/Embedded_Systems)
- [Zephyr Project Documentation](https://docs.zephyrproject.org/)

## Interview Questions

1. What is the difference between a microcontroller and a microprocessor?
2. Why is dynamic memory allocation generally avoided in embedded firmware?
3. What is the NVIC and why is it important for real-time systems?
4. Explain the difference between hard real-time and soft real-time constraints.
5. When would you choose an RTOS over a bare-metal superloop?
6. What is the difference between Cortex-M0+ and Cortex-M4?
7. How does a device enter a low-power sleep state, and what wakes it up?
8. What is DMA and why does it matter for power efficiency?
9. Name three IoT communication protocols and when you would use each.
10. What is TrustZone and why is it relevant to modern embedded systems?