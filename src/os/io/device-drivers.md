# Device Drivers

## Overview

A **device driver** is a kernel module that translates generic operating system I/O commands into device-specific operations. Each driver knows how to program a particular type of hardware — setting registers, managing DMA, handling interrupts, and presenting a uniform interface to the rest of the kernel.

## Motivation

The OS provides abstractions (files, sockets) that applications use for I/O. But hardware devices have wildly different interfaces — a SATA disk uses command queues, a USB device uses bulk transfers, a GPU uses command buffers. The driver bridges this gap:

```
Application: read(fd, buf, 4096)
     │
     ▼
VFS: find file → find device → find driver
     │
     ▼
Driver: translate to device-specific commands
     │
     ▼
Hardware: execute commands, transfer data
```

## Driver Architecture in Linux

```
┌─────────────────────────────────────────────────────────────┐
│                    Linux Driver Model                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              VFS / System Call Layer                 │    │
│  │         read(), write(), open(), ioctl()            │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                   │
│  ┌──────────────────────┴──────────────────────────────┐    │
│  │              Device Subsystems                       │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │  Block   │  │  Char    │  │  Network │          │    │
│  │  │  Layer   │  │  Layer   │  │  Stack   │          │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘          │    │
│  └───────┼──────────────┼──────────────┼───────────────┘    │
│          │              │              │                     │
│  ┌───────┴──────────────┴──────────────┴───────────────┐    │
│  │              Device Drivers                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │   ahci   │  │  usbhid  │  │  e1000e  │          │    │
│  │  │  (SATA)  │  │  (USB)   │  │  (NIC)   │          │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘          │    │
│  └───────┼──────────────┼──────────────┼───────────────┘    │
│          │              │              │                     │
│  ┌───────┴──────────────┴──────────────┴───────────────┐    │
│  │              Hardware Bus Subsystem                   │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │   PCI    │  │   USB    │  │ Platform │          │    │
│  │  │  Subsys  │  │  Subsys  │  │  Bus     │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Hardware                                │    │
│  │  Controllers, buses, devices                        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Device Types

| Type | Interface | Examples | Access |
|------|-----------|----------|--------|
| **Block** | Fixed-size blocks, buffered | HDDs, SSDs, NVMe | `/dev/sda`, `/dev/nvme0n1` |
| **Character** | Byte stream, unbuffered | Terminals, serial ports, sensors | `/dev/tty`, `/dev/ttyUSB0` |
| **Network** | Packet-based | NICs, WiFi adapters | `eth0`, `wlan0` (not in `/dev`) |
| **Miscellaneous** | Catch-all | Random, null, urandom | `/dev/random`, `/dev/null` |

```bash
# View device types
cat /proc/devices
# Character devices:
#   4 tty
#   5 /dev/tty
#   10 misc
#   226 drm
# Block devices:
#   8 sd
#   9 md
# 253 device-mapper
# 259 blkext

# Major/minor numbers
ls -la /dev/sda /dev/tty0 /dev/random
# brw-rw---- 1 root disk  8,  0 ... /dev/sda     (block, major 8)
# crw--w---- 1 root tty   4,  0 ... /dev/tty0     (char, major 4)
# crw-rw-rw- 1 root root  1,  8 ... /dev/random   (char, major 1)
```

## Driver Components

### 1. Module Initialization and Cleanup

```c
#include <linux/module.h>
#include <linux/kernel.h>

static int __init mydriver_init(void) {
    printk(KERN_INFO "mydriver: loaded\n");
    
    // Register with kernel subsystem
    // Allocate resources
    // Set up interrupt handlers
    // Initialize hardware
    
    return 0;  // Success
}

static void __exit mydriver_exit(void) {
    printk(KERN_INFO "mydriver: unloaded\n");
    
    // Release resources
    // Unregister from subsystems
    // Shut down hardware
}

module_init(mydriver_init);
module_exit(mydriver_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Author Name");
MODULE_DESCRIPTION("Example device driver");
```

### 2. File Operations (Char Device)

```c
// Define operations the driver supports
static const struct file_operations mydriver_fops = {
    .owner   = THIS_MODULE,
    .open    = mydriver_open,
    .release = mydriver_close,
    .read    = mydriver_read,
    .write   = mydriver_write,
    .unlocked_ioctl = mydriver_ioctl,
};

static int mydriver_open(struct inode *inode, struct file *filp) {
    // Called when user opens /dev/mydevice
    // Validate access, initialize per-open state
    return 0;
}

static ssize_t mydriver_read(struct file *filp, char __user *buf,
                             size_t count, loff_t *pos) {
    // Read data from device
    // Copy to user buffer
    if (copy_to_user(buf, kernel_buf, count))
        return -EFAULT;
    return count;
}

static ssize_t mydriver_write(struct file *filp, const char __user *buf,
                              size_t count, loff_t *pos) {
    // Copy from user buffer
    if (copy_from_user(kernel_buf, buf, count))
        return -EFAULT;
    // Send data to device
    return count;
}
```

### 3. Block Device Operations

```c
// Block device operations
static const struct block_device_operations mydisk_ops = {
    .owner   = THIS_MODULE,
    .open    = mydisk_open,
    .release = mydisk_release,
    .submit_bio = mydisk_submit_bio,  // Modern bio-based I/O
};

// Process I/O request
static void mydisk_submit_bio(struct bio *bio) {
    struct bio_vec bvec;
    struct bvec_iter iter;
    
    bio_for_each_segment(bvec, bio, iter) {
        // Get page, offset, length
        struct page *page = bvec.bv_page;
        unsigned int offset = bvec.bv_offset;
        unsigned int len = bvec.bv_len;
        
        // Program DMA, issue hardware command
        // ...
    }
    
    // Signal completion
    bio_endio(bio);
}
```

### 4. Interrupt Handler Registration

```c
static irqreturn_t mydriver_irq(int irq, void *dev_id) {
    struct mydevice *dev = dev_id;
    
    // Check if this device caused the interrupt
    u32 status = readl(dev->regs + STATUS_REG);
    if (!(status & INT_PENDING))
        return IRQ_NONE;  // Not our interrupt (shared IRQ)
    
    // Acknowledge interrupt
    writel(INT_ACK, dev->regs + STATUS_REG);
    
    // Read data, update state
    // Schedule bottom half if needed
    
    return IRQ_HANDLED;
}

// In probe function:
ret = request_irq(dev->irq, mydriver_irq, IRQF_SHARED,
                  "mydriver", dev);
```

### 5. DMA Setup

```c
// Allocate DMA buffer
void *buf = dma_alloc_coherent(&pdev->dev, buf_size,
                                &dma_handle, GFP_KERNEL);
if (!buf)
    return -ENOMEM;

// Program device with DMA address
writel(dma_handle, dev->regs + DMA_ADDR_REG);
writel(buf_size, dev->regs + DMA_LEN_REG);

// After DMA completes, use the data
process_data(buf);

// Cleanup
dma_free_coherent(&pdev->dev, buf_size, buf, dma_handle);
```

## Linux Driver Model (sysfs)

The Linux driver model provides a unified way to represent devices and drivers in sysfs:

```
/sys/
├── bus/
│   ├── pci/
│   │   ├── devices/          # PCI devices
│   │   │   ├── 0000:00:1f.2 -> ../../../devices/pci0000:00/0000:00:1f.2
│   │   │   └── ...
│   │   └── drivers/          # PCI drivers
│   │       ├── ahci/
│   │       │   ├── bind
│   │       │   ├── unbind
│   │       │   └── new_id
│   │       └── ...
│   └── usb/
│       ├── devices/
│       └── drivers/
├── class/
│   ├── net/                  # Network devices
│   │   ├── eth0 -> ../../devices/...
│   │   └── lo -> ../../devices/...
│   ├── block/                # Block devices
│   │   ├── sda -> ../../devices/...
│   │   └── nvme0n1 -> ../../devices/...
│   └── tty/                  # TTY devices
│       ├── tty0 -> ../../devices/...
│       └── ttyS0 -> ../../devices/...
└── devices/                  # Device tree
    ├── pci0000:00/
    │   ├── 0000:00:1f.2/     # SATA controller
    │   │   ├── driver -> ../../../../bus/pci/drivers/ahci
    │   │   ├── vendor
    │   │   ├── device
    │   │   ├── class
    │   │   └── ...
    │   └── ...
    └── platform/
```

### Device-Driver Binding

```bash
# View which driver is bound to a device
readlink /sys/bus/pci/devices/0000:00:1f.2/driver
# ../../../bus/pci/drivers/ahci

# Unbind device from driver
echo "0000:00:1f.2" | sudo tee /sys/bus/pci/drivers/ahci/unbind

# Bind device to a different driver
echo "0000:00:1f.2" | sudo tee /sys/bus/pci/drivers/vfio-pci/bind

# Load a driver module
sudo modprobe ahci

# View loaded modules
lsmod | grep ahci
# ahci                 40960  3
# libahci              45056  1 ahci
```

## Probe and Remove (Hot-Pluggable Drivers)

```c
// Called when device is detected or driver is loaded
static int mydriver_probe(struct pci_dev *pdev,
                          const struct pci_device_id *id) {
    // 1. Enable the device
    pci_enable_device(pdev);
    
    // 2. Request memory regions
    pci_request_regions(pdev, "mydriver");
    
    // 3. Map device registers (MMIO)
    void __iomem *regs = pci_iomap(pdev, 0, 0);
    
    // 4. Allocate driver data structure
    struct mydevice *dev = kzalloc(sizeof(*dev), GFP_KERNEL);
    
    // 5. Set up DMA
    dma_set_mask_and_coherent(&pdev->dev, DMA_BIT_MASK(64));
    
    // 6. Request interrupt
    request_irq(pdev->irq, mydriver_irq, 0, "mydriver", dev);
    
    // 7. Initialize hardware
    init_hardware(dev);
    
    // 8. Register with subsystem (block, char, net)
    register_device(dev);
    
    pci_set_drvdata(pdev, dev);
    return 0;
}

// Called when device is removed or driver is unloaded
static void mydriver_remove(struct pci_dev *pdev) {
    struct mydevice *dev = pci_get_drvdata(pdev);
    
    unregister_device(dev);
    free_irq(pdev->irq, dev);
    pci_iounmap(pdev, dev->regs);
    pci_release_regions(pdev);
    pci_disable_device(pdev);
    kfree(dev);
}

// PCI device ID table
static const struct pci_device_id mydriver_ids[] = {
    { PCI_DEVICE(VENDOR_ID, DEVICE_ID) },
    { 0, }
};
MODULE_DEVICE_TABLE(pci, mydriver_ids);

// PCI driver structure
static struct pci_driver mydriver_pci = {
    .name     = "mydriver",
    .id_table = mydriver_ids,
    .probe    = mydriver_probe,
    .remove   = mydriver_remove,
};
```

## Real-World Linux Examples

### Loading and Managing Drivers

```bash
# List all loaded kernel modules
lsmod

# Load a module
sudo modprobe e1000e

# Remove a module
sudo modprobe -r e1000e

# View module info
modinfo e1000e
# filename:    /lib/modules/.../e1000e.ko
# license:     GPL
# description: Intel(R) PRO/1000 Network Driver

# View module parameters
cat /sys/module/e1000e/parameters/*
# InterruptThrottleRate: 0
# ...
```

### Building a Kernel Module

```makefile
# Makefile for out-of-tree kernel module
obj-m += mydriver.o

KDIR := /lib/modules/$(shell uname -r)/build

all:
    $(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
    $(MAKE) -C $(KDIR) M=$(PWD) clean
```

```bash
# Build
make

# Load
sudo insmod mydriver.ko

# Check
dmesg | tail
# mydriver: loaded

# Remove
sudo rmmod mydriver
```

### Driver Development Tools

```bash
# Static analysis
make C=1  # Sparse static checker

# Dynamic analysis
# KASAN: kernel address sanitizer
# KMEMLEAK: memory leak detection
# KMSAN: memory sanitizer
# lockdep: lock dependency checker

# Trace driver behavior
echo 1 | sudo tee /sys/kernel/debug/tracing/events/mydriver/enable
cat /sys/kernel/debug/tracing/trace_pipe

# View device resources
cat /proc/ioports    # I/O port mappings
cat /proc/iomem      # Memory mappings
cat /proc/interrupts # IRQ assignments
```

## Interview Questions

### Beginner

**Q: What is a device driver?**
A: A device driver is a kernel module that translates generic OS I/O operations into device-specific commands. It knows how to program a particular hardware device's registers, handle its interrupts, and manage its DMA transfers. Applications interact with devices through the driver via the VFS layer.

**Q: What is the difference between block and character devices?**
A: Block devices transfer data in fixed-size blocks (sectors), support random access, and are buffered by the kernel (e.g., disks, SSDs). Character devices transfer data as a byte stream, are typically unbuffered, and don't support random access (e.g., terminals, serial ports, sensors).

### Intermediate

**Q: Explain the probe/remove pattern in Linux drivers.**
A:
- **probe()**: Called when the kernel discovers a matching device (via device ID table) or when the driver is loaded. It initializes the device — enables it, maps registers, requests IRQs, allocates resources, and registers with the kernel subsystem.
- **remove()**: Called when the device is physically removed or the driver is unloaded. It cleans up — unregisters, frees IRQs, releases resources.

This pattern supports hot-plugging (USB, Thunderbolt) and driver loading/unloading without rebooting.

**Q: Why must drivers use `copy_to_user()`/`copy_from_user()` instead of direct pointer access?**
A: User-space pointers are virtual addresses that may not be valid in kernel context. The user buffer might be:
- Unmapped (page fault in kernel context = crash)
- Swapped out
- A kernel address (security violation)
- Read-only when write is needed

`copy_to_user()`/`copy_from_user()` validate the pointer, handle page faults safely, and enforce access control. They return the number of bytes NOT copied (0 on success).

### FAANG-Level

**Q: Design a Linux device driver for a new custom NIC that supports 100Gbps with hardware timestamping, RDMA, and SR-IOV. Outline the key components and design decisions.**

A:

```
Architecture:

┌─────────────────────────────────────────────────────┐
│                 Custom NIC Driver                     │
│                                                       │
│  ┌───────────────────────────────────────────────┐   │
│  │  Netdev Interface (struct net_device)          │   │
│  │  • ndo_open, ndo_stop, ndo_start_xmit         │   │
│  │  • ndo_set_features, ndo_get_stats64          │   │
│  │  • ethtool_ops (configure offloads, rings)    │   │
│  └───────────────────────┬───────────────────────┘   │
│                          │                            │
│  ┌───────────────────────┴───────────────────────┐   │
│  │  Multi-Queue Layer                             │   │
│  │  • 256 TX/RX queue pairs                      │   │
│  │  • Per-CPU queue assignment (XPS)             │   │
│  │  • RSS (Receive Side Scaling)                 │   │
│  │  • RPS/RFS (software steering)                │   │
│  └───────────────────────┬───────────────────────┘   │
│                          │                            │
│  ┌───────────┬───────────┼───────────┬───────────┐   │
│  │  TX Path  │  RX Path  │  RDMA     │  SR-IOV   │   │
│  │           │           │           │           │   │
│  │ • DMA map │ • NAPI    │ • ib_verbs│ • VF mgmt │   │
│  │ • Ring    │ • GRO     │ • MR/PD   │ • VF-PF   │   │
│  │ • Doorbell│ • XDP     │ • QP/CQ   │  mailbox  │   │
│  │ • TSO/GSO │ • HW ts   │ • DMA MR  │           │   │
│  └─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┘   │
│        │           │           │           │          │
│  ┌─────┴───────────┴───────────┴───────────┴─────┐    │
│  │  Hardware Abstraction Layer (HAL)              │    │
│  │  • Register access (readl/writel)              │    │
│  │  • DMA operations                              │    │
│  │  • Interrupt management (MSI-X)                │    │
│  │  • Firmware communication                      │    │
│  └───────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘

Key Design Decisions:

1. Multi-queue with per-CPU affinity:
   - 256 queue pairs (one TX + one RX per queue)
   - Pin each queue to a CPU core (XPS + IRQ affinity)
   - Enables linear scaling with core count
   - RSS hash determines which queue handles each packet

2. Hardware timestamping:
   - Register PTP clock with kernel (ptp_clock_register())
   - Enable TX/RX timestamping in hardware
   - Expose via SO_TIMESTAMPING socket option
   - Synchronize with PHC (Physical Hardware Clock)

3. RDMA support:
   - Implement ib_device_ops (verbs interface)
   - Register with RDMA subsystem
   - Support: Queue Pairs, Memory Regions, Completion Queues
   - Zero-copy: user MR → NIC DMA directly
   - Use ODP (On-Demand Paging) for memory registration

4. SR-IOV:
   - Create VFs: echo 8 > /sys/class/net/eth0/device/sriov_numvfs
   - PF driver manages VF configuration
   - Mailbox for PF-VF communication
   - Each VF appears as separate PCI device
   - Can be passed to VMs (VFIO)

5. XDP (eXpress Data Path):
   - Implement ndo_bpf for XDP program attachment
   - Support XDP_DROP, XDP_TX, XDP_PASS, XDP_REDIRECT
   - Run XDP programs before network stack
   - Enables: firewall, load balancer, forwarder at line rate

6. Power management:
   - Runtime PM: dynamic power gating when idle
   - Suspend/resume: save/restore hardware state
   - Wake-on-LAN support

Performance targets:
- 100Gbps line rate (148.8 Mpps for 64-byte packets)
- < 2µs latency (XDP_DROP benchmark)
- Linear scaling to 64 cores
- RDMA latency < 1µs
```

## Common Mistakes

1. **Not handling errors from DMA/IRQ allocation**: Every allocation can fail. Check return values and clean up on failure.
2. **Sleeping in interrupt context**: Use `GFP_ATOMIC` for allocations in ISR; use workqueues for blocking operations.
3. **Race conditions in probe/remove**: Device may be removed while probe is running. Use proper locking and reference counting.
4. **Not releasing resources on error paths**: Use `goto` cleanup labels or devm_* (managed) APIs to avoid resource leaks.
5. **Ignoring endianness**: Device registers may be big-endian while CPU is little-endian. Use `readl()`/`writel()` which handle byte ordering.

## Summary

| Component | Purpose |
|-----------|---------|
| Module init/exit | Load/unload driver |
| File operations | Interface for char devices |
| Block operations | Interface for block devices |
| Probe/Remove | Device discovery and cleanup |
| IRQ handler | Process hardware interrupts |
| DMA setup | Data transfer without CPU |
| sysfs | User-space device information |
| ioctl | Device-specific commands |

## Cross-References

- [Hardware](hardware.md) — I/O hardware that drivers program
- [Interrupts](interrupts.md) — How drivers handle interrupts
- [DMA](dma.md) — How drivers manage DMA transfers
- [Software Layers](software-layers.md) — Where drivers fit in the I/O stack
- [Buffering](buffering.md) — How drivers manage buffers
