# Direct Memory Access (DMA)

## Overview

**Direct Memory Access (DMA)** is a feature that allows hardware devices to transfer data directly to and from main memory without involving the CPU for each byte. The CPU sets up the transfer (source, destination, byte count) and the DMA controller handles the actual data movement, interrupting the CPU only when the entire transfer is complete.

## Motivation

Without DMA, the CPU must handle every byte of data transfer (programmed I/O). For a 1MB disk read at 4 bytes per CPU cycle on a 1GHz CPU, that's 250,000 CPU cycles wasted on data shuffling. DMA frees the CPU to do useful work during the transfer.

```
Without DMA (Programmed I/O):
  CPU: read byte from device → write to memory
  CPU: read byte from device → write to memory
  CPU: read byte from device → write to memory
  ... (repeated for every byte/word)
  CPU: 100% busy during transfer, can't do anything else

With DMA:
  CPU: "DMA controller, transfer 1MB from device to memory address 0x1000"
  CPU: [goes back to doing useful work]
  DMA: transfers 1MB directly to memory (no CPU involvement)
  DMA: "Hey CPU, transfer complete!" (interrupt)
  CPU: handles completion
```

## DMA Controller Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    System Architecture                       │
│                                                             │
│  ┌───────┐         ┌───────────┐         ┌─────────┐       │
│  │       │◄───────►│           │◄───────►│         │       │
│  │  CPU  │         │  System   │         │ Memory  │       │
│  │       │         │   Bus     │         │  (RAM)  │       │
│  └───────┘         │           │         └─────────┘       │
│                    │           │                             │
│                    │           │         ┌─────────┐        │
│                    │           │◄───────►│  DMA    │        │
│                    │           │         │Controller│        │
│                    └─────┬─────┘         └────┬────┘        │
│                          │                    │              │
│                    ┌─────┴─────┐              │              │
│                    │ Expansion │              │              │
│                    │   Bus     │◄─────────────┘              │
│                    └─────┬─────┘                             │
│                          │                                   │
│                    ┌─────┴─────┐                              │
│                    │  Device   │                              │
│                    │Controller │                              │
│                    └───────────┘                              │
└─────────────────────────────────────────────────────────────┘

Note: DMA controller sits on the system bus and can access memory
independently of the CPU. Both CPU and DMA share the bus (arbitration needed).
```

## DMA Transfer Process

```
┌──────────────────────────────────────────────────────────────┐
│              DMA Transfer Steps                               │
│                                                              │
│  1. CPU Programs DMA Controller:                             │
│     • Source address (device register or memory)             │
│     • Destination address (memory)                           │
│     • Byte count                                             │
│     • Transfer direction (to/from device)                    │
│     • Control flags                                          │
│     │                                                        │
│  2. CPU enables DMA transfer and resumes work                │
│     │                                                        │
│  3. DMA Controller takes over the bus (bus mastering)        │
│     │                                                        │
│  4. DMA transfers data:                                      │
│     • Reads from source (device/memory)                      │
│     • Writes to destination (memory/device)                  │
│     • Decrements byte count                                  │
│     • Repeats until count = 0                                │
│     │                                                        │
│  5. Transfer complete:                                       │
│     • DMA controller raises interrupt                        │
│     • CPU handles completion (wake process, update state)    │
└──────────────────────────────────────────────────────────────┘
```

## DMA Modes

```
┌──────────────────────────────────────────────────────────────┐
│                    DMA Transfer Modes                         │
│                                                              │
│  1. BURST MODE (Block Transfer)                              │
│     ┌─────────────────────────────────────┐                  │
│     │ DMA: [████████████████████] → Memory │                  │
│     │      Transfer entire block           │                  │
│     │      CPU can't use bus during this   │                  │
│     └─────────────────────────────────────┘                  │
│     ✓ Fastest transfer                                       │
│     ✗ CPU blocked from bus (starved)                         │
│     Use: Large transfers, when CPU doesn't need bus          │
│                                                              │
│  2. CYCLE STEALING                                           │
│     ┌───────────────────────────────────────────────┐        │
│     │ DMA: [██][CPU][██][CPU][██][CPU][██][CPU]     │        │
│     │      Transfer one word, let CPU use bus,       │        │
│     │      then transfer next word, repeat           │        │
│     └───────────────────────────────────────────────┘        │
│     ✓ CPU not starved                                        │
│     ✗ Slower transfer (bus shared)                           │
│     Use: Real-time systems, interleaving with CPU            │
│                                                              │
│  3. TRANSPARENT MODE                                         │
│     ┌───────────────────────────────────────────────┐        │
│     │ DMA: uses bus only when CPU doesn't need it    │        │
│     │      (during CPU internal operations)           │        │
│     └───────────────────────────────────────────────┘        │
│     ✓ CPU never delayed                                      │
│     ✗ Slowest transfer (only idle bus cycles)                │
│     Use: When CPU utilization is high                        │
└──────────────────────────────────────────────────────────────┘
```

## Scatter-Gather DMA

Modern DMA controllers support **scatter-gather** — transferring data to/from multiple non-contiguous memory regions in a single transfer.

```
Without scatter-gather:
  Transfer 1: Device → Memory region A (4KB)
  Transfer 2: Device → Memory region B (4KB)
  Transfer 3: Device → Memory region C (4KB)
  3 separate DMA setups, 3 interrupts

With scatter-gather:
  DMA descriptor chain:
  ┌─────────┐    ┌─────────┐    ┌─────────┐
  │ Addr: A │───►│ Addr: B │───►│ Addr: C │───► NULL
  │ Len: 4K │    │ Len: 4K │    │ Len: 4K │
  └─────────┘    └─────────┘    └─────────┘
  
  1 DMA setup, transfers all regions, 1 interrupt at end
```

```c
// Linux scatter-gather DMA (simplified)
struct scatterlist sg[3];

sg_init_table(sg, 3);
sg_set_buf(&sg[0], buf_a, 4096);
sg_set_buf(&sg[1], buf_b, 4096);
sg_set_buf(&sg[2], buf_c, 4096);

// Map scatter-gather list for DMA
dma_map_sg(dev, sg, 3, DMA_FROM_DEVICE);

// Program device with DMA addresses
for_each_sg(sg, s, nents, i) {
    dma_addr_t addr = sg_dma_address(s);
    size_t len = sg_dma_len(s);
    // Program hardware with addr and len
}
```

## DMA and Cache Coherency

```
Problem: DMA bypasses the CPU cache!

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Device    │     │  DMA to     │     │    CPU      │
│  writes     │────►│  Memory     │     │   Cache     │
│  data       │     │  (RAM)      │     │  (stale!)   │
└─────────────┘     └─────────────┘     └─────────────┘

If CPU reads the DMA buffer, it might get stale cached data!

Solutions:
1. Cache flushing (software-managed):
   - Before DMA read: flush cache → ensure RAM has latest data
   - After DMA write: invalidate cache → force re-read from RAM

2. Cache-coherent hardware (hardware-managed):
   - Hardware snoops the cache during DMA
   - Automatically invalidates/updates cache lines
   - Common on modern x86, some ARM

3. Non-cacheable memory regions:
   - Map DMA buffers as uncacheable in page tables
   - No coherency issue, but slower CPU access
```

```c
// Linux DMA mapping API handles cache coherency
dma_addr_t dma_addr;

// Allocate coherent (non-cached) DMA memory
void *buf = dma_alloc_coherent(dev, 4096, &dma_addr, GFP_KERNEL);
// buf is CPU virtual address, dma_addr is device-visible physical address
// No cache management needed — memory is non-cached

// Or use streaming DMA with explicit sync
void *buf = kmalloc(4096, GFP_KERNEL);
dma_addr = dma_map_single(dev, buf, 4096, DMA_FROM_DEVICE);

// ... device does DMA ...

dma_unmap_single(dev, dma_addr, 4096, DMA_FROM_DEVICE);
// After unmap, cache is invalidated — CPU sees fresh data from device
```

## IOMMU (I/O Memory Management Unit)

```
Without IOMMU:
  Device uses physical addresses directly
  Device must be able to reach all of physical memory
  No isolation between devices

With IOMMU:
  ┌─────────┐    ┌─────────┐    ┌─────────┐
  │ Device  │───►│  IOMMU  │───►│ Memory  │
  │ (uses   │    │ (maps   │    │ (actual │
  │  IOVA)  │    │  IOVA→  │    │  phys)  │
  │         │    │  phys)  │    │         │
  └─────────┘    └─────────┘    └─────────┘
  
  IOVA = I/O Virtual Address (device's view of memory)

Benefits:
1. Isolation: Device can only access its mapped regions
2. Remapping: Physical memory can be scattered; IOMMU provides contiguous view
3. Protection: Prevents rogue DMA from corrupting kernel memory
4. Virtualization: Guest VMs use IOMMU for direct device assignment (VFIO)
```

```bash
# View IOMMU information on Linux
dmesg | grep -i iommu
# DMAR: IOMMU 0: reg_base_addr fed90000 ver 1:0 cap ...

# Check IOMMU groups (for device passthrough)
ls /sys/kernel/iommu_groups/
# 0/ 1/ 2/ 3/ ...

# IOMMU must be enabled in BIOS and kernel
# Kernel parameter: intel_iommu=on (Intel) or amd_iommu=on (AMD)
```

## Real-World Linux Examples

### Viewing DMA Information

```bash
# DMA pool statistics
cat /proc/meminfo | grep -i dma
# Not directly shown, but DMA zones in:
cat /proc/zoneinfo | grep -A5 DMA

# View DMA-capable devices
lspci -v | grep -i dma

# DMA mapping debug (kernel config: DMA_API_DEBUG)
# Checks for DMA API misuse at runtime
```

### Network DMA Example

```
NIC receive path with DMA:

1. NIC receives packet on wire
2. NIC's DMA engine writes packet data directly to ring buffer in host memory
   - Ring buffer allocated by driver with dma_alloc_coherent()
   - NIC writes via DMA without CPU involvement
3. NIC raises MSI-X interrupt
4. Driver's interrupt handler:
   - Reads descriptor ring (which entries have new data)
   - Builds sk_buff pointing to DMA buffer (zero-copy possible)
   - Passes up network stack
5. When done with buffer, driver recycles it back to ring

TX path:
1. Driver builds TX descriptor pointing to packet in memory
2. NIC's DMA engine reads packet from host memory
3. NIC transmits packet on wire
4. NIC raises TX completion interrupt
5. Driver frees the buffer
```

### NVMe DMA

```
NVMe SSD I/O path with DMA:

1. Driver creates submission queue entry (SQE):
   - Command (read/write)
   - LBA (logical block address)
   - PRP (Physical Region Page) list — scatter-gather DMA addresses
2. Driver writes SQE to submission queue in host memory
3. Driver writes doorbell register (MMIO write to NVMe controller)
4. NVMe controller reads SQE via DMA
5. NVMe controller reads/writes data via DMA to PRP addresses
6. NVMe controller writes completion queue entry (CQE)
7. NVMe controller raises MSI-X interrupt
8. Driver reads CQE, completes the I/O request

All data transfer is DMA — CPU only programs the descriptors.
```

## Interview Questions

### Beginner

**Q: What is DMA and why is it needed?**
A: DMA allows devices to transfer data directly to/from memory without CPU involvement for each byte. Without DMA, the CPU would have to read every byte from the device and write it to memory (programmed I/O), wasting millions of cycles. DMA frees the CPU to do useful work during large data transfers.

**Q: How does the CPU know when a DMA transfer is complete?**
A: The DMA controller raises a hardware interrupt when the transfer is complete. The CPU's interrupt handler then processes the completion — waking up waiting processes, updating buffers, etc.

### Intermediate

**Q: What is scatter-gather DMA and when is it useful?**
A: Scatter-gather DMA allows a single DMA transfer to read/write multiple non-contiguous memory regions. The DMA controller follows a chain of descriptors, each specifying a different memory address and length. This is useful because:
- Network packets may span multiple pages
- File data may not be physically contiguous in memory
- Reduces the number of separate DMA setups and interrupts

**Q: Explain the cache coherency problem with DMA. How is it solved?**
A: DMA bypasses the CPU cache — when a device writes data to memory via DMA, the CPU's cache may still contain stale data for that memory region. Solutions:
1. **Cache flush/invalidate**: Software explicitly manages cache before/after DMA
2. **Cache-coherent hardware**: Hardware snoops cache during DMA (common on x86)
3. **Non-cacheable mappings**: DMA buffers mapped as uncacheable (simple but slower)

Linux's DMA API (`dma_map_single`, `dma_sync_*`) handles this transparently.

### FAANG-Level

**Q: Design a zero-copy network path from NIC to application using DMA. How do you eliminate all data copies?**

A:

```
Traditional path (4 copies):
  NIC → DMA → Ring Buffer → Kernel Buffer → Socket Buffer → User Buffer
         ①         ②              ③              ④

Zero-copy path:
  NIC → DMA → Ring Buffer ──────────────────► User Buffer
         ①         (mapped directly via mmap/io_uring)

Design:

1. DMA Ring Buffer Setup:
   - Allocate ring buffer pages with dma_alloc_coherent()
   - Map same physical pages into user space via mmap()
   - NIC writes packets directly to user-visible memory

2. Descriptor Management:
   - Each ring entry has: buffer pointer, length, flags
   - Kernel maintains ownership metadata
   - User gets read-only view via mmap

3. Packet Reception:
   ┌─────────────────────────────────────────────┐
   │  NIC receives packet                         │
   │  NIC DMA writes to ring buffer page          │
   │  (page is mapped in both kernel and user)    │
   │  NIC raises interrupt                        │
   │  Kernel updates descriptor (length, status)  │
   │  User sees new data immediately (zero copy!) │
   └─────────────────────────────────────────────┘

4. io_uring integration:
   - Register ring buffer with io_uring
   - Application submits recv() via SQE
   - Completion arrives via CQE with buffer index
   - No copy, no syscall per packet

5. AF_XDP (Linux):
   - UMEM: shared memory region between kernel and user
   - RX ring: packet descriptors (not data!) to user
   - TX ring: user submits packets for transmission
   - Fill/Completion rings for buffer management

   ┌──────────────────────────────────────────┐
   │              AF_XDP Socket                │
   │                                          │
   │  ┌──────────┐  ┌──────────┐              │
   │  │ RX Ring  │  │ TX Ring  │  Descriptors │
   │  └────┬─────┘  └────┬─────┘              │
   │       │              │                    │
   │       ▼              ▼                    │
   │  ┌──────────────────────────┐             │
   │  │        UMEM              │  Data pages │
   │  │  (shared with NIC DMA)   │             │
   │  └──────────────────────────┘             │
   └──────────────────────────────────────────┘

Performance:
- Traditional: ~1M pps (packets per second)
- Zero-copy (AF_XDP): ~24M pps
- DPDK (kernel bypass): ~48M pps (but loses kernel networking)
```

**Q: A device driver is corrupting kernel memory via rogue DMA. How would you diagnose and prevent this?**

A:

```
Diagnosis:
1. Enable DMA API debug: CONFIG_DMA_API_DEBUG=y
   - Catches DMA API misuse (unmapped addresses, wrong direction)
   - Check dmesg for warnings

2. Use IOMMU:
   - Enable intel_iommu=on / amd_iommu=on
   - IOMMU will fault on invalid DMA addresses
   - dmesg shows: "DMAR: DRHD: handling fault status reg 2"
   - Fault address tells you which device and what address

3. Hardware watchpoints:
   - Set hardware watchpoint on corrupted memory address
   - When DMA writes to that address, CPU traps
   - Stack trace reveals the device/driver

4. DMA address restrictions:
   - Check dma_set_mask() — is device limited to correct address range?
   - 32-bit devices on 64-bit systems may DMA to wrong addresses

Prevention:
1. IOMMU (primary defense):
   - Maps device-visible addresses to physical addresses
   - Device can only access its allocated regions
   - Violation triggers IOMMU fault (not silent corruption)

2. DMA API best practices:
   - Always use dma_map_*() before DMA
   - Always use dma_unmap_*() after DMA
   - Use DMA_BIT_MASK() to set correct address width
   - Check return values of DMA mapping functions

3. Bounce buffers:
   - For devices with limited DMA addressing
   - Kernel allocates low-memory bounce buffer
   - Data copied between bounce buffer and actual buffer
   - Adds a copy but ensures device stays in bounds
```

## Common Mistakes

1. **Using physical addresses directly**: Modern systems have IOMMU; use DMA mapping API (`dma_map_single`), not raw physical addresses.
2. **Forgetting cache synchronization**: On non-coherent architectures (ARM), you must explicitly sync cache before/after DMA.
3. **DMA to stack memory**: Never DMA to stack-allocated buffers — stack addresses may not be physically contiguous or may be below DMA addressable range.
4. **Not checking DMA mask**: 32-bit devices can't DMA to memory above 4GB. Use `dma_set_mask_and_coherent(dev, DMA_BIT_MASK(32))`.
5. **Reusing buffer before DMA completes**: Don't touch a buffer until `dma_unmap_*()` is called, which guarantees DMA is finished.

## Summary

| Concept | Key Point |
|---------|-----------|
| DMA | Device transfers data directly to/from memory |
| CPU role | Setup + completion handling only |
| Burst mode | Transfer entire block, CPU blocked |
| Cycle stealing | Transfer word-by-word, CPU interleaved |
| Scatter-gather | Multiple non-contiguous regions in one transfer |
| Cache coherency | DMA bypasses cache; must sync |
| IOMMU | Maps device addresses, provides isolation |
| Completion | DMA raises interrupt when done |

## Cross-References

- [Hardware](hardware.md) — DMA controller hardware
- [Interrupts](interrupts.md) — DMA completion uses interrupts
- [Device Drivers](device-drivers.md) — How drivers use DMA
- [Buffering](buffering.md) — DMA buffers and the page cache


## Cross References

- [Interrupts](../os/io/interrupts.md)
- [I/O Hardware](../os/io/hardware.md)
- [Buses](../arch/io/buses.md)
- [PCIe](../arch/io/pcie.md)
