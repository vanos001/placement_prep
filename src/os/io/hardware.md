# I/O Hardware

## Overview

I/O hardware consists of physical devices, device controllers, buses, and the electrical/electronic interfaces that connect them. Understanding this hardware foundation is essential because the OS must interact with it at the lowest level to manage I/O operations.

## Key Concepts

### Device Controllers

A **device controller** is an electronic unit that acts as an intermediary between the CPU and a physical device. Each device controller manages one or more devices of a specific type.

**Components of a device controller:**
- **Control register**: Receives commands from the CPU
- **Status register**: Reports device state (busy, ready, error)
- **Data register**: Holds data being transferred
- **Local buffer**: Temporary storage for data in transit

```
┌──────────┐     Bus      ┌───────────────────┐     Cable     ┌─────────┐
│          │◄────────────►│  Device Controller │◄────────────►│  Device │
│   CPU    │              │  ┌──────────────┐  │              │ (Disk,  │
│          │              │  │ Control Reg   │  │              │  NIC,   │
│          │              │  │ Status Reg    │  │              │  etc.)  │
│          │              │  │ Data Reg      │  │              │         │
│          │              │  │ Local Buffer  │  │              │         │
│          │              │  └──────────────┘  │              │         │
└──────────┘              └───────────────────┘              └─────────┘
```

### I/O Port Addresses

Each device controller is mapped to a set of **I/O port addresses**. The CPU uses these addresses to communicate with specific controllers.

**Methods of device communication:**

| Method | Description | Used By |
|--------|-------------|---------|
| **I/O Port (Port-mapped I/O)** | Dedicated address space for I/O registers, accessed via special instructions (`in`, `out` on x86) | Traditional PCs |
| **Memory-Mapped I/O (MMIO)** | Device registers mapped into the physical memory address space; accessed with normal load/store instructions | Modern systems, ARM, RISC-V |
| **Hybrid** | Both methods available | x86 (e.g., VGA uses both) |

```c
// Port-mapped I/O (x86 assembly concept)
outb(0x3F8, data);  // Write 'data' to COM1 serial port
data = inb(0x3F8);  // Read from COM1

// Memory-Mapped I/O (concept)
volatile uint32_t *uart_reg = (uint32_t *)0xFE201000;  // Raspberry Pi UART
*uart_reg = 'A';  // Write character via memory store
```

### Buses

A **bus** is a shared communication pathway connecting the CPU, memory, and I/O devices.

```
┌──────────────────────────────────────────────────────┐
│                     System Bus                        │
│  ┌───────┐  ┌───────┐  ┌──────────┐  ┌───────────┐  │
│  │  CPU  │  │ Memory│  │  Bridge  │  │   PCIe    │  │
│  └───────┘  └───────┘  └────┬─────┘  └───────────┘  │
│                              │                        │
│                    ┌─────────┴─────────┐              │
│                    │   Expansion Bus   │              │
│                    │  ┌────┐ ┌────┐   │              │
│                    │  │NIC │ │GPU │   │              │
│                    │  └────┘ └────┘   │              │
│                    │  ┌────┐ ┌────┐   │              │
│                    │  │USB │ │SATA│   │              │
│                    │  └────┘ └────┘   │              │
│                    └───────────────────┘              │
└──────────────────────────────────────────────────────┘
```

**Common bus types:**

| Bus | Speed | Use Case |
|-----|-------|----------|
| **PCIe Gen4** | ~16 GT/s per lane | GPUs, NVMe SSDs, NICs |
| **PCIe Gen5** | ~32 GT/s per lane | Next-gen devices |
| **USB 3.2** | 20 Gbps | Peripherals |
| **SATA III** | 6 Gbps | HDDs, SATA SSDs |
| **NVMe** | PCIe-based | High-speed SSDs |
| **I²C / SPI** | Low speed | Sensors, embedded |

### Memory-Mapped I/O vs Port-Mapped I/O

```
┌────────────────────────────────────────────┐
│         Port-Mapped I/O                    │
│                                            │
│  ┌──────────────┐   ┌──────────────────┐   │
│  │ Memory Space │   │  I/O Port Space  │   │
│  │  0x00000000  │   │   0x0000 - 0xFFFF│   │
│  │  ...         │   │                  │   │
│  │  0xFFFFFFFF  │   │ (Separate addr   │   │
│  │              │   │  space, special  │   │
│  │ (Normal load │   │  in/out instrs)  │   │
│  │  /store)     │   │                  │   │
│  └──────────────┘   └──────────────────┘   │
├────────────────────────────────────────────┤
│         Memory-Mapped I/O                  │
│                                            │
│  ┌──────────────────────────────────────┐  │
│  │         Unified Address Space        │  │
│  │  0x00000000 ─ Memory (RAM)           │  │
│  │  ...                                 │  │
│  │  0xFE000000 ─ Device Registers       │  │
│  │  ...                                 │  │
│  │  0xFFFFFFFF                          │  │
│  │                                      │  │
│  │  (Same load/store instructions for   │  │
│  │   both memory and devices)           │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

**Tradeoffs:**

| Aspect | Port-Mapped I/O | Memory-Mapped I/O |
|--------|----------------|-------------------|
| Address space | Separate | Shared with memory |
| Instructions | Special (`in`/`out`) | Normal (`load`/`store`) |
| Speed | Slower (special bus cycle) | Faster |
| Protection | Hardware-enforced | Need page-table tricks |
| Caching | Not cached | Must disable cache for device regions |

### I/O Mechanisms: Polling vs Interrupts vs DMA

```
┌────────────────────────────────────────────────────────────────┐
│                   I/O Mechanism Comparison                      │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. PROGRAMMED I/O (Polling)                                   │
│     CPU ───check status───► Device                             │
│     CPU ───check status───► Device  (busy-wait)                │
│     CPU ───check status───► Device                             │
│     CPU ───transfer data──► Device  ✓                          │
│     ⚠ CPU is 100% busy during transfer                         │
│                                                                │
│  2. INTERRUPT-DRIVEN I/O                                       │
│     CPU ───command───► Device                                  │
│     CPU does other work...                                     │
│     Device ───interrupt───► CPU                                │
│     CPU ───transfer data──► Device  ✓                          │
│     ✓ CPU freed during device work                             │
│     ⚠ Still one interrupt per byte/word                        │
│                                                                │
│  3. DMA (Direct Memory Access)                                 │
│     CPU ───command + count + addr───► DMA Controller           │
│     CPU does other work...                                     │
│     DMA Controller ───transfers block───► Memory               │
│     DMA Controller ───interrupt───► CPU                        │
│     ✓ One interrupt per block                                  │
│     ✓ CPU completely free during transfer                      │
└────────────────────────────────────────────────────────────────┘
```

## Real-World Linux Examples

### Viewing I/O Hardware Information

```bash
# List all PCI devices (controllers)
lspci
# Example output:
# 00:1f.2 SATA controller: Intel Corporation 82801JI (ICH10 Family) SATA AHCI Controller

# List USB devices
lsusb

# View I/O port mappings
cat /proc/ioports
# Example:
# 03f8-03ff : serial
# 0400-0403 : ACPI PM1a_EVT_BLK

# View memory-mapped I/O regions
cat /proc/iomem
# Example:
# fe200000-fe2000b3 : bcm2835 (Raspberry Pi peripherals)

# View interrupt assignments
cat /proc/interrupts
```

### Detecting Device Controllers in Linux

```bash
# Detailed hardware info
sudo lshw -class disk
sudo lshw -class network

# Block devices
lsblk
# NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
# sda      8:0    0 238.5G  0 disk
# ├─sda1   8:1    0   512M  0 part /boot
# └─sda2   8:2    0   238G  0 part /

# Check if NVMe
nvme list
```

## Interview Questions

### Beginner

**Q: What is the role of a device controller?**
A: A device controller is an electronic unit that bridges the CPU and a physical device. It contains control, status, and data registers that the CPU reads/writes to command the device, check its status, and transfer data. Each controller manages one or more devices of a specific type.

**Q: What is the difference between port-mapped I/O and memory-mapped I/O?**
A: Port-mapped I/O uses a separate address space with special CPU instructions (`in`/`out` on x86). Memory-mapped I/O maps device registers into the regular memory address space, allowing the CPU to use standard load/store instructions. Memory-mapped I/O is faster and more common on modern architectures (ARM, RISC-V).

### Intermediate

**Q: Why must the OS disable caching for memory-mapped I/O regions?**
A: If device registers were cached, the CPU might read stale status values from the cache instead of the actual register, or write commands to the cache without them reaching the device. The OS marks these memory regions as uncacheable in the page tables to ensure every load/store hits the actual hardware register.

**Q: Explain the three I/O mechanisms and their tradeoffs.**
A:
- **Polling (Programmed I/O)**: CPU repeatedly checks device status. Simple but wastes CPU cycles. Good for very fast devices where the check overhead is negligible.
- **Interrupt-driven I/O**: CPU issues a command and resumes work; the device interrupts when done. Better CPU utilization but has per-transfer interrupt overhead.
- **DMA**: CPU programs a DMA controller with source, destination, and byte count. The DMA controller transfers data directly to memory without CPU involvement and interrupts only when the entire block is complete. Best for large transfers; has setup overhead.

### FAANG-Level

**Q: Design the I/O path for a network packet arriving on an NIC and being delivered to a user-space application. Trace the hardware and software components involved.**

A:
1. **Hardware**: NIC receives Ethernet frame → DMA transfers frame into kernel ring buffer in host memory → NIC raises interrupt (MSI-X)
2. **Interrupt handler**: CPU dispatches to NIC driver's interrupt handler → handler acknowledges interrupt, schedules NAPI poll
3. **NAPI polling**: Driver polls ring buffer, builds `sk_buff` structures → passes up the network stack (IP → TCP/UDP)
4. **Socket layer**: Data placed in socket receive buffer → process waiting on `read()`/`recv()` is woken up
5. **System call return**: Kernel copies data from kernel buffer to user buffer → `read()` returns with data

```
NIC → DMA → Ring Buffer → Interrupt → Driver → Network Stack → Socket Buffer → User App
```

Key optimizations:
- **NAPI**: Avoids interrupt storms by switching to polling under high load
- **Zero-copy (io_uring, DPDK)**: Can map ring buffers directly to user space
- **RSS**: Receive Side Scaling distributes packets across CPU cores

## Common Mistakes

1. **Confusing controller with device**: The controller is the electronic interface; the device is the physical peripheral. One controller may manage multiple devices.
2. **Assuming polling is always bad**: For very fast devices (e.g., network at line rate), polling can outperform interrupts because interrupt overhead dominates.
3. **Forgetting about byte ordering**: Device registers may use big-endian while the CPU is little-endian. The driver must handle byte order conversion.
4. **Ignoring memory barriers**: With memory-mapped I/O, writes to device registers may be reordered by the CPU. Memory barriers (`mb()`, `wmb()`, `rmb()` in Linux) ensure correct ordering.

## Summary

| Concept | Key Point |
|---------|-----------|
| Device Controller | Intermediary with control/status/data registers |
| Port-Mapped I/O | Separate address space, special instructions |
| Memory-Mapped I/O | Device registers in memory space, normal instructions |
| Buses | Shared pathways (PCIe, USB, SATA, etc.) |
| Polling | CPU busy-waits; simple but wasteful |
| Interrupts | Device signals CPU; better utilization |
| DMA | Controller transfers data; minimal CPU involvement |

## Cross-References

- [Interrupts](interrupts.md) — Deep dive into interrupt mechanisms
- [DMA](dma.md) — Direct Memory Access in detail
- [Device Drivers](device-drivers.md) — How drivers interact with hardware
- [Software Layers](software-layers.md) — The complete I/O software stack


## Cross References

- [DMA](dma.md)
- [Interrupts](interrupts.md)
- [Buses](../../arch/io/buses.md)
- [I/O Architecture](../../arch/io/README.md)
